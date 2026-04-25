"""Phase 1: Build KG từ Wikidata dump (1-pass + post-filter).

Pipeline:
  Step 0. Tự download dump bz2 (~100GB) nếu chưa có, resume được.
  Step 1. Stream dump 1 LẦN duy nhất:
           - Mỗi entity → lưu label (vi/en) vào dict in-memory.
           - Extract MỌI fact temporal → ghi raw vào file.
  Step 2. Filter facts: giữ fact mà s và o đều có label.
  Step 3. Lọc relation hiếm (< BUILD_MIN_RELATION_FACTS).
  Step 4. Lọc entity hiếm (< BUILD_MIN_ENTITY_FACTS).
  Output. Ghi cache/{P*.jsonl} + cache/labels.json + cache/relation_labels.json.

So với 2-pass cũ: stream dump 1 lần thay vì 2 → ~2x nhanh hơn.

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
DOWNLOAD_CONCURRENCY = 4


# ====================================================================
# Step 0: Download dump (resume support)
# ====================================================================

def _download_aria2(url: str, target: Path) -> bool:
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
        "--summary-interval=5",
        "--console-log-level=notice",
        "--show-console-readout=false",
        "--enable-color=false",
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
    if _download_aria2(url, target):
        return
    _download_requests(url, target)


# ====================================================================
# Stream + helpers
# ====================================================================

try:
    import orjson as _json
    _decode_json = _json.loads
except ImportError:
    _decode_json = json.loads


def stream_entities(path: Path) -> Iterator[dict]:
    if shutil.which("pbzip2"):
        proc = subprocess.Popen(["pbzip2", "-dc", str(path)],
                                 stdout=subprocess.PIPE, bufsize=1 << 20)
        try:
            for raw in proc.stdout:
                line = raw.strip().rstrip(b",")
                if not line or line in (b"[", b"]"):
                    continue
                try:
                    yield _decode_json(line)
                except (ValueError, TypeError):
                    continue
        finally:
            proc.stdout.close()
            proc.wait()
    else:
        with bz2.open(path, "rb") as f:
            for raw in f:
                line = raw.strip().rstrip(b",")
                if not line or line in (b"[", b"]"):
                    continue
                try:
                    yield _decode_json(line)
                except (ValueError, TypeError):
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


def _qual_year(quals: dict, prop: str) -> Optional[int]:
    if prop not in quals:
        return None
    try:
        t = quals[prop][0]["datavalue"]["value"].get("time", "")
        return parse_year(t)
    except (KeyError, IndexError, TypeError):
        return None


def extract_temporal_facts(entity: dict) -> list[dict]:
    """Extract MỌI fact temporal (mọi P-prop có timestamp).
    Logic: ưu tiên P580/P582; nếu thiếu cả 2 mà có P585 → point in time.
    """
    qid = entity["id"]
    claims = entity.get("claims", {})
    facts = []
    for pid, pclaims in claims.items():
        if not pid.startswith("P"):
            continue
        for c in pclaims:
            try:
                obj = c["mainsnak"]["datavalue"]["value"]["id"]
            except (KeyError, TypeError):
                continue
            if not isinstance(obj, str) or not obj.startswith("Q"):
                continue
            quals = c.get("qualifiers", {})
            p580 = _qual_year(quals, "P580")
            p582 = _qual_year(quals, "P582")
            p585 = _qual_year(quals, "P585")
            if p580 is None and p582 is None and p585 is None:
                continue
            if p580 is None and p582 is None:
                start = end = p585
            else:
                start = p580 if p580 is not None else YEAR_MIN
                end   = p582 if p582 is not None else YEAR_MAX
            facts.append({
                "s_qid": qid, "o_qid": obj,
                "start": start, "end": end,
                "relation": pid,
            })
    return facts


# ====================================================================
# Step 1: SINGLE PASS — collect labels + extract all temporal facts
# ====================================================================

LABELS_CKPT     = Path(CACHE_DIR) / "_step1_labels.json"
REL_LABELS_CKPT = Path(CACHE_DIR) / "_step1_rel_labels.json"
ALL_FACTS_CKPT  = Path(CACHE_DIR) / "_step1_all_facts.jsonl"
PASS_DONE       = Path(CACHE_DIR) / "_step1.done"


def step1_single_pass(dump_path: Path, limit: Optional[int]
                       ) -> tuple[dict[str, dict], dict[str, dict], Path]:
    """1 pass duy nhất qua dump:
      - Lưu label (vi/en) cho mọi Q và P entity có label.
      - Extract MỌI temporal fact, ghi raw ra disk (ALL_FACTS_CKPT).
    Return (ent_labels, rel_labels, all_facts_path).
    """
    if PASS_DONE.exists():
        ent = json.loads(LABELS_CKPT.read_text())
        rel = json.loads(REL_LABELS_CKPT.read_text())
        n_facts = sum(1 for _ in ALL_FACTS_CKPT.open())
        print(f"  [skip] checkpoint: {len(ent):,} entity, "
              f"{len(rel):,} relation, {n_facts:,} fact thô")
        return ent, rel, ALL_FACTS_CKPT

    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    # Reset checkpoint nếu pass cũ chưa hoàn thành
    for p in (LABELS_CKPT, REL_LABELS_CKPT, ALL_FACTS_CKPT):
        if p.exists():
            p.unlink()

    ent_labels: dict[str, dict] = {}
    rel_labels: dict[str, dict] = {}
    pbar = tqdm(desc="step1: scan", unit="ent")
    seen = 0
    facts_total = 0

    with ALL_FACTS_CKPT.open("w") as ckpt:
        for entity in stream_entities(dump_path):
            seen += 1
            if limit and seen > limit:
                break
            pbar.update(1)
            qid = entity.get("id", "")
            if not qid or qid[0] not in "QP":
                continue
            vi = get_label(entity, "vi")
            en = get_label(entity, "en")

            # Lưu label
            if vi or en:
                if qid[0] == "Q":
                    ent_labels[qid] = {"vi": vi, "en": en}
                else:
                    rel_labels[qid] = {"vi": vi, "en": en}

            # Extract fact temporal (chỉ cho Q-entity, P-prop không có claims thường dùng)
            if qid[0] == "Q":
                for fact in extract_temporal_facts(entity):
                    ckpt.write(json.dumps(fact) + "\n")
                    facts_total += 1

            if seen % 200000 == 0:
                pbar.set_postfix(qids=len(ent_labels), pids=len(rel_labels),
                                 facts=facts_total)
                ckpt.flush()
                LABELS_CKPT.write_text(json.dumps(ent_labels, ensure_ascii=False))
                REL_LABELS_CKPT.write_text(json.dumps(rel_labels, ensure_ascii=False))
    pbar.close()

    LABELS_CKPT.write_text(json.dumps(ent_labels, ensure_ascii=False))
    REL_LABELS_CKPT.write_text(json.dumps(rel_labels, ensure_ascii=False))
    PASS_DONE.write_text("ok")
    print(f"  → saved: {len(ent_labels):,} entity, {len(rel_labels):,} "
          f"relation, {facts_total:,} fact thô")
    return ent_labels, rel_labels, ALL_FACTS_CKPT


# ====================================================================
# Step 2: Filter facts theo label
# ====================================================================

def step2_filter_by_labels(all_facts_path: Path,
                            labels: dict[str, dict]) -> list[dict]:
    """Đọc all_facts.jsonl, giữ fact mà cả s_qid và o_qid đều có label."""
    facts = []
    pbar = tqdm(desc="step2: filter labels", unit="fact")
    with all_facts_path.open() as f:
        for line in f:
            try:
                fact = _decode_json(line)
            except Exception:
                continue
            pbar.update(1)
            if fact["s_qid"] in labels and fact["o_qid"] in labels:
                facts.append(fact)
    pbar.close()
    print(f"  fact: {pbar.n:,} → {len(facts):,} (giữ {len(facts)/max(pbar.n,1)*100:.1f}%)")
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

def write_cache(facts: list[dict], labels: dict[str, dict],
                needed: set[str], rel_labels: dict[str, dict]) -> None:
    def lab(qid: str) -> str:
        d = labels[qid]
        return d.get("vi") or d.get("en")

    def rel_lab(pid: str) -> Optional[str]:
        d = rel_labels.get(pid)
        if not d:
            return None
        return d.get("vi") or d.get("en")

    by_rel: dict[str, list[dict]] = defaultdict(list)
    for f in facts:
        pid = f["relation"]
        by_rel[pid].append({
            "s_qid": f["s_qid"], "s_label": lab(f["s_qid"]),
            "o_qid": f["o_qid"], "o_label": lab(f["o_qid"]),
            "start": f["start"], "end": f["end"],
            "relation": pid, "r_label": rel_lab(pid),
        })

    cache = Path(CACHE_DIR)
    cache.mkdir(parents=True, exist_ok=True)
    sorted_rels = sorted(by_rel.items(), key=lambda x: -len(x[1]))
    for pid, items in sorted_rels:
        path = cache / f"{pid}.jsonl"
        with path.open("w") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        marker = "★" if pid in PIDS else " "
        print(f"  {marker} {pid}: {len(items):>7,} fact -> {path}")

    used_ent = {q: labels[q] for q in needed if q in labels}
    (cache / "labels.json").write_text(
        json.dumps(used_ent, ensure_ascii=False, indent=2))

    used_rel_pids = {f["relation"] for f in facts}
    used_rel = {p: rel_labels[p] for p in used_rel_pids if p in rel_labels}
    (cache / "relation_labels.json").write_text(
        json.dumps(used_rel, ensure_ascii=False, indent=2))

    total = sum(len(v) for v in by_rel.values())
    vi_ent = sum(1 for d in used_ent.values() if d.get("vi"))
    vi_rel = sum(1 for d in used_rel.values() if d.get("vi"))
    print(f"\n[done] {total:,} fact, {len(used_ent):,} entity, "
          f"{len(used_rel)} relation")
    print(f"       entity VN: {vi_ent:,}/{len(used_ent):,} "
          f"({vi_ent/max(len(used_ent),1)*100:.1f}%)")
    print(f"       relation VN: {vi_rel}/{len(used_rel)} "
          f"({vi_rel/max(len(used_rel),1)*100:.1f}%)")


# ====================================================================
# Main
# ====================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=Path(DUMP_FILE))
    ap.add_argument("--url",  default=DUMP_URL)
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--limit", type=int, default=None,
                    help="duyệt N entity đầu (test)")
    args = ap.parse_args()

    if not args.skip_download:
        download_dump(args.url, args.dump)
    if not args.dump.exists():
        print(f"[error] không có dump {args.dump}")
        return

    size_gb = args.dump.stat().st_size / 1e9
    print(f"\n[dump] {args.dump} ({size_gb:.1f} GB)")
    if args.limit:
        print(f"[limit] {args.limit:,} entity")

    print(f"\n[Step 1] Single pass: collect labels + extract facts…")
    ent_labels, rel_labels, all_facts_path = step1_single_pass(
        args.dump, args.limit)

    print(f"\n[Step 2] Filter facts (s và o đều có label):")
    facts = step2_filter_by_labels(all_facts_path, ent_labels)

    print(f"\n[Step 3] Lọc relation hiếm (≥ {BUILD_MIN_RELATION_FACTS}):")
    facts = step3_filter_relations(facts)

    print(f"\n[Step 4] Lọc entity hiếm (≥ {BUILD_MIN_ENTITY_FACTS}):")
    facts, needed = step4_filter_entities(facts)

    print(f"\n[Output] Ghi cache (label vi ưu tiên, fallback en)…")
    write_cache(facts, ent_labels, needed, rel_labels)


if __name__ == "__main__":
    main()
