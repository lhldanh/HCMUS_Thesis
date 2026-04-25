"""Phase 1: Build KG từ Wikidata dump, strict 100% VN label.

Pipeline (giống tkbc nhưng filter VN ở cả subject và object):
  Step 0. Tự download dump bz2 (~100GB) nếu chưa có, resume được.
  Step 1. Pass dump lần 1 → cache {qid: {vi, en}} cho mọi entity CÓ VN label.
  Step 2. Pass dump lần 2 → extract fact temporal mà s VÀ o đều có VN label.
          (discretize timestamp về năm)
  Step 3. Lọc relation hiếm (< BUILD_MIN_RELATION_FACTS).
  Step 4. Lọc entity hiếm  (< BUILD_MIN_ENTITY_FACTS).

Output: cache/{P*.jsonl} + cache/labels.json (toàn bộ s_label, o_label đều VN).

→ Vì cache 100% VN, KHÔNG cần translate.py nữa. Chạy thẳng generate.py.

Usage:
  python build_kg.py
  python build_kg.py --limit 1000000   # test 1M entity
  python build_kg.py --skip-download
"""
from __future__ import annotations

import argparse
import bz2
import json
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, Optional

import requests
from tqdm import tqdm

from config import (BUILD_MIN_ENTITY_FACTS, BUILD_MIN_RELATION_FACTS, CACHE_DIR,
                    DATA_DIR, DUMP_FILE, RELATIONS, YEAR_MAX, YEAR_MIN)

DUMP_URL = "https://dumps.wikimedia.your.org/wikidatawiki/entities/latest-all.json.bz2"
PIDS = set(RELATIONS.keys())

# Concurrent connection cho aria2c (Wikimedia chặn nếu > 4-5)
DOWNLOAD_CONCURRENCY = 4


# ====================================================================
# Step 0: Download dump (resume support)
# ====================================================================

def _download_aria2(url: str, target: Path) -> bool:
    """Tải bằng aria2c nếu có sẵn. Return True nếu thành công."""
    if not shutil.which("aria2c"):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "aria2c",
        "-x", str(DOWNLOAD_CONCURRENCY),
        "-s", str(DOWNLOAD_CONCURRENCY),
        "-k", "10M",
        "--file-allocation=none",
        "--max-tries=10",
        "--retry-wait=30",
        "--continue=true",
        "--user-agent=Mozilla/5.0 (cronqvn-research)",
        "-d", str(target.parent),
        "-o", target.name,
        url,
    ]
    print(f"[download] aria2c -x {DOWNLOAD_CONCURRENCY} → {target}")
    try:
        subprocess.run(cmd, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[warn] aria2c thất bại, fallback sang requests")
        return False


def _download_requests(url: str, target: Path,
                        chunk_size: int = 1 << 20) -> None:
    """Fallback: tải bằng requests single-thread, có resume."""
    target.parent.mkdir(parents=True, exist_ok=True)
    head = requests.head(url, allow_redirects=True, timeout=30)
    head.raise_for_status()
    total = int(head.headers.get("content-length", 0))

    existing = target.stat().st_size if target.exists() else 0
    if existing == total and total > 0:
        print(f"[skip] dump đã đủ ({existing/1e9:.1f} GB)")
        return
    if existing > total:
        target.unlink(); existing = 0

    headers = {"Range": f"bytes={existing}-"} if existing else {}
    mode = "ab" if existing else "wb"
    print(f"[download] requests {total/1e9:.1f} GB"
          + (f" (resume từ {existing/1e9:.2f} GB)" if existing else ""))

    with requests.get(url, headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        pbar = tqdm(total=total, initial=existing, unit="B",
                    unit_scale=True, unit_divisor=1024, desc="download")
        with target.open(mode) as f:
            for chunk in r.iter_content(chunk_size):
                f.write(chunk); pbar.update(len(chunk))
        pbar.close()


def download_dump(url: str, target: Path) -> None:
    """Ưu tiên aria2c (multi-thread, ~3-5x nhanh hơn). Fallback requests."""
    if _download_aria2(url, target):
        return
    _download_requests(url, target)


# ====================================================================
# Stream + helpers
# ====================================================================

def stream_entities(path: Path) -> Iterator[dict]:
    with bz2.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip().rstrip(",")
            if line in ("[", "]", ""):
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_year(time_str: str) -> Optional[int]:
    if not time_str:
        return None
    try:
        y = int(time_str[1:5] if time_str[0] in "+-" else time_str[:4])
        return y if YEAR_MIN <= y <= YEAR_MAX else None
    except (ValueError, IndexError):
        return None


def get_label(entity: dict, lang: str) -> Optional[str]:
    return entity.get("labels", {}).get(lang, {}).get("value")


def extract_temporal_facts(entity: dict) -> list[dict]:
    qid = entity["id"]
    claims = entity.get("claims", {})
    facts = []
    for pid in PIDS & set(claims):
        for c in claims[pid]:
            try:
                obj = c["mainsnak"]["datavalue"]["value"]["id"]
            except (KeyError, TypeError):
                continue
            quals = c.get("qualifiers", {})
            start = end = None
            for prop, tag in (("P580", "s"), ("P585", "s"), ("P582", "e")):
                if prop not in quals:
                    continue
                try:
                    t = quals[prop][0]["datavalue"]["value"].get("time", "")
                    y = parse_year(t)
                except (KeyError, IndexError, TypeError):
                    continue
                if y is None:
                    continue
                if tag == "s" and start is None:
                    start = y
                elif tag == "e":
                    end = y
            if start is None:
                continue
            facts.append({
                "s_qid": qid, "o_qid": obj,
                "start": start, "end": end or start,
                "relation": pid,
            })
    return facts


# ====================================================================
# Step 1: Pass dump lần 1, collect labels của entity có VN
# ====================================================================

def step1_collect_vi_labels(dump_path: Path,
                             limit: Optional[int]) -> dict[str, dict]:
    """Trả {qid: {"vi": str, "en": str|None}} cho mọi entity có VN label."""
    labels: dict[str, dict] = {}
    pbar = tqdm(desc="step1: VN labels", unit="ent")
    seen = 0
    for entity in stream_entities(dump_path):
        seen += 1
        if limit and seen > limit:
            break
        pbar.update(1)
        qid = entity.get("id", "")
        if not qid.startswith("Q"):
            continue
        vi = get_label(entity, "vi")
        if not vi:
            continue
        labels[qid] = {"vi": vi, "en": get_label(entity, "en")}
        if len(labels) % 100000 == 0:
            pbar.set_postfix(vi_qids=len(labels))
    pbar.close()
    return labels


# ====================================================================
# Step 2: Pass dump lần 2, extract fact strict (s VÀ o đều có VN)
# ====================================================================

def step2_extract_strict_facts(dump_path: Path, vi_labels: dict[str, dict],
                                limit: Optional[int]) -> list[dict]:
    facts: list[dict] = []
    pbar = tqdm(desc="step2: facts", unit="ent")
    seen = 0
    for entity in stream_entities(dump_path):
        seen += 1
        if limit and seen > limit:
            break
        pbar.update(1)
        qid = entity.get("id", "")
        if qid not in vi_labels:
            continue
        for f in extract_temporal_facts(entity):
            if f["o_qid"] not in vi_labels:
                continue   # ← strict: object cũng phải có VN
            facts.append(f)
        if len(facts) % 50000 == 0 and len(facts) > 0:
            pbar.set_postfix(facts=len(facts))
    pbar.close()
    return facts


# ====================================================================
# Step 3: Lọc relation hiếm
# ====================================================================

def step3_filter_relations(facts: list[dict]) -> list[dict]:
    counts = Counter(f["relation"] for f in facts)
    keep = {r for r, c in counts.items() if c >= BUILD_MIN_RELATION_FACTS}
    out = [f for f in facts if f["relation"] in keep]
    print(f"  relation: {len(counts)} → {len(keep)} "
          f"(≥ {BUILD_MIN_RELATION_FACTS} fact)")
    print(f"  fact:     {len(facts):,} → {len(out):,}")
    return out


# ====================================================================
# Step 4: Lọc entity hiếm
# ====================================================================

def step4_filter_entities(facts: list[dict]) -> tuple[list[dict], set[str]]:
    counts = Counter()
    for f in facts:
        counts[f["s_qid"]] += 1
        counts[f["o_qid"]] += 1
    keep = {q for q, c in counts.items() if c >= BUILD_MIN_ENTITY_FACTS}
    out = [f for f in facts
           if f["s_qid"] in keep and f["o_qid"] in keep]
    print(f"  entity:   {len(counts):,} → {len(keep):,} "
          f"(≥ {BUILD_MIN_ENTITY_FACTS} fact)")
    print(f"  fact:     {len(facts):,} → {len(out):,}")
    needed = {q for f in out for q in (f["s_qid"], f["o_qid"])}
    return out, needed


# ====================================================================
# Output
# ====================================================================

def write_cache(facts: list[dict], vi_labels: dict[str, dict],
                needed: set[str]) -> None:
    by_rel: dict[str, list[dict]] = defaultdict(list)
    for f in facts:
        s = vi_labels[f["s_qid"]]["vi"]
        o = vi_labels[f["o_qid"]]["vi"]
        by_rel[f["relation"]].append({
            "s_qid": f["s_qid"], "s_label": s,
            "o_qid": f["o_qid"], "o_label": o,
            "start": f["start"], "end": f["end"],
            "relation": f["relation"],
        })

    cache = Path(CACHE_DIR)
    cache.mkdir(parents=True, exist_ok=True)
    for pid in sorted(PIDS):
        items = by_rel.get(pid, [])
        path = cache / f"{pid}.jsonl"
        with path.open("w") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        print(f"  {pid}: {len(items):>7,} fact -> {path}")

    # Chỉ ghi label của QID needed (giảm size)
    used_labels = {q: vi_labels[q] for q in needed if q in vi_labels}
    (cache / "labels.json").write_text(
        json.dumps(used_labels, ensure_ascii=False, indent=2))
    total = sum(len(v) for v in by_rel.values())
    print(f"\n[done] {total:,} fact, {len(used_labels):,} entity")
    print(f"       → 100% VN label, sẵn sàng chạy generate.py")


# ====================================================================
# Main
# ====================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=Path(DUMP_FILE))
    ap.add_argument("--url",  default=DUMP_URL)
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--limit", type=int, default=None,
                    help="duyệt N entity đầu mỗi pass (test)")
    args = ap.parse_args()

    if not args.skip_download:
        download_dump(args.url, args.dump)
    if not args.dump.exists():
        print(f"[error] không có dump {args.dump}")
        return

    size_gb = args.dump.stat().st_size / 1e9
    print(f"\n[dump] {args.dump} ({size_gb:.1f} GB)")
    if args.limit:
        print(f"[limit] {args.limit:,} entity/pass")

    print(f"\n[Step 1] Pass 1 → cache labels của entity có VN…")
    vi_labels = step1_collect_vi_labels(args.dump, args.limit)
    print(f"          {len(vi_labels):,} entity có VN label")

    print(f"\n[Step 2] Pass 2 → extract fact strict (s VÀ o đều VN)…")
    facts = step2_extract_strict_facts(args.dump, vi_labels, args.limit)
    print(f"          {len(facts):,} fact thô")

    print(f"\n[Step 3] Lọc relation hiếm (≥ {BUILD_MIN_RELATION_FACTS}):")
    facts = step3_filter_relations(facts)

    print(f"\n[Step 4] Lọc entity hiếm (≥ {BUILD_MIN_ENTITY_FACTS}):")
    facts, needed = step4_filter_entities(facts)

    print(f"\n[Output] Ghi cache 100% VN…")
    write_cache(facts, vi_labels, needed)


if __name__ == "__main__":
    main()
