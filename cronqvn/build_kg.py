"""Phase 1: Build KG từ Wikidata dump (giống tkbc, label VN hoặc EN).

Pipeline:
  Step 0. Tự download dump bz2 (~100GB) nếu chưa có, resume được.
  Step 1. Pass dump lần 1 → cache {qid: {vi, en}} cho mọi entity có VN HOẶC EN.
  Step 2. Pass dump lần 2 → extract fact temporal mà s VÀ o đều có label.
          - Mọi P-property (không filter relation)
          - Có ít nhất 1 trong P580/P585/P582 (start/point/end)
          - Sentinel YEAR_MIN/YEAR_MAX cho missing start/end
  Step 3. Lọc relation hiếm (< BUILD_MIN_RELATION_FACTS).
  Step 4. Lọc entity hiếm  (< BUILD_MIN_ENTITY_FACTS).

Output: cache/{P*.jsonl} + cache/labels.json
  Mỗi label entry: {"vi": str|None, "en": str|None}
  Generate.py sẽ ưu tiên vi, fallback en.

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
        # Log progress mỗi 5s (Colab cần để thấy live)
        "--summary-interval=5",
        "--console-log-level=notice",
        "--show-console-readout=false",  # tắt readout 1 line update,
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

try:
    import orjson as _json   # nhanh hơn json ~3x
    _decode_json = _json.loads
except ImportError:
    _decode_json = json.loads


def stream_entities(path: Path) -> Iterator[dict]:
    """Stream entity từ dump bz2.

    Ưu tiên pbzip2 (parallel decompress, ~4-8x nhanh hơn).
    Fallback bz2.open() single-thread.
    """
    if shutil.which("pbzip2"):
        # pbzip2 -dc decompress to stdout, parallel theo CPU cores.
        proc = subprocess.Popen(
            ["pbzip2", "-dc", str(path)],
            stdout=subprocess.PIPE, bufsize=1 << 20,
        )
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
    """Extract MỌI fact có timestamp, không filter relation (giống tkbc).

    Logic timestamp:
      - P585 (point in time)        → start = end = year (event 1 thời điểm)
      - P580 (start) + P582 (end)   → khoảng đầy đủ
      - P580 only (ongoing)         → start = year, end = YEAR_MAX (sentinel)
      - P582 only (unknown start)   → start = YEAR_MIN (sentinel), end = year
      - không có qualifier time     → bỏ
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
            # Ưu tiên P580/P582; nếu thiếu cả 2 mà có P585 → point in time
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
# Step 1: Pass dump lần 1, collect labels của entity có VN
# ====================================================================

LABELS_CKPT = Path(CACHE_DIR) / "_step1_labels.json"


def step1_collect_labels(dump_path: Path,
                          limit: Optional[int]) -> dict[str, dict]:
    """Trả {qid: {"vi": str|None, "en": str|None}} cho entity có VN HOẶC EN.
    Có checkpoint: nếu file tồn tại → load thẳng (skip)."""
    if LABELS_CKPT.exists():
        labels = json.loads(LABELS_CKPT.read_text())
        print(f"  [skip] checkpoint {len(labels):,} entity có label")
        return labels

    labels: dict[str, dict] = {}
    pbar = tqdm(desc="step1: labels", unit="ent")
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
        en = get_label(entity, "en")
        if not vi and not en:
            continue                        # bỏ entity không có label nào
        labels[qid] = {"vi": vi, "en": en}
        if len(labels) % 200000 == 0:
            pbar.set_postfix(qids=len(labels))
            LABELS_CKPT.parent.mkdir(parents=True, exist_ok=True)
            LABELS_CKPT.write_text(json.dumps(labels, ensure_ascii=False))
    pbar.close()

    LABELS_CKPT.parent.mkdir(parents=True, exist_ok=True)
    LABELS_CKPT.write_text(json.dumps(labels, ensure_ascii=False))
    print(f"  → checkpoint saved: {LABELS_CKPT}")
    return labels


# ====================================================================
# Step 2: Pass dump lần 2, extract fact strict (s VÀ o đều có VN)
# ====================================================================

FACTS_CKPT = Path(CACHE_DIR) / "_step2_facts.jsonl"


def step2_extract_facts(dump_path: Path, labels: dict[str, dict],
                         limit: Optional[int]) -> list[dict]:
    """Pass 2 → extract fact temporal mà s và o đều trong labels (vi hoặc en).
    Append vào checkpoint file (resume được)."""
    facts: list[dict] = []
    if FACTS_CKPT.exists():
        with FACTS_CKPT.open() as f:
            for line in f:
                try:
                    facts.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        meta = FACTS_CKPT.with_suffix(".done")
        if meta.exists():
            print(f"  [skip] đã có {len(facts):,} fact từ checkpoint")
            return facts
        print(f"  [resume cũ không hoàn tất] reset, chạy lại")
        facts = []
        FACTS_CKPT.unlink()

    FACTS_CKPT.parent.mkdir(parents=True, exist_ok=True)
    pbar = tqdm(desc="step2: facts", unit="ent")
    seen = 0
    with FACTS_CKPT.open("w") as ckpt:
        for entity in stream_entities(dump_path):
            seen += 1
            if limit and seen > limit:
                break
            pbar.update(1)
            qid = entity.get("id", "")
            if qid not in labels:
                continue                          # subject phải có label
            for f in extract_temporal_facts(entity):
                if f["o_qid"] not in labels:
                    continue                      # object cũng phải có label
                facts.append(f)
                ckpt.write(json.dumps(f) + "\n")
            if len(facts) % 5000 == 0 and len(facts) > 0:
                pbar.set_postfix(facts=len(facts))
                ckpt.flush()
    pbar.close()
    FACTS_CKPT.with_suffix(".done").write_text("ok")
    print(f"  → checkpoint saved: {FACTS_CKPT} ({len(facts):,} fact)")
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
                needed: set[str]) -> None:
    def lab(qid: str) -> str:
        d = labels[qid]
        return d.get("vi") or d.get("en")     # ưu tiên vi, fallback en

    by_rel: dict[str, list[dict]] = defaultdict(list)
    for f in facts:
        by_rel[f["relation"]].append({
            "s_qid": f["s_qid"], "s_label": lab(f["s_qid"]),
            "o_qid": f["o_qid"], "o_label": lab(f["o_qid"]),
            "start": f["start"], "end": f["end"],
            "relation": f["relation"],
        })

    cache = Path(CACHE_DIR)
    cache.mkdir(parents=True, exist_ok=True)
    # Ghi mọi relation pass filter, sort theo số fact giảm dần để dễ xem
    sorted_rels = sorted(by_rel.items(), key=lambda x: -len(x[1]))
    for pid, items in sorted_rels:
        path = cache / f"{pid}.jsonl"
        with path.open("w") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        marker = "★" if pid in PIDS else " "
        print(f"  {marker} {pid}: {len(items):>7,} fact -> {path}")

    # Chỉ ghi label của QID xuất hiện trong fact final (giảm size)
    used = {q: labels[q] for q in needed if q in labels}
    (cache / "labels.json").write_text(
        json.dumps(used, ensure_ascii=False, indent=2))
    total = sum(len(v) for v in by_rel.values())
    vi_count = sum(1 for d in used.values() if d.get("vi"))
    print(f"\n[done] {total:,} fact, {len(used):,} entity")
    print(f"       VN coverage: {vi_count:,}/{len(used):,} "
          f"({vi_count/max(len(used),1)*100:.1f}%)")


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

    print(f"\n[Step 1] Pass 1 → cache labels của entity có VN hoặc EN…")
    labels = step1_collect_labels(args.dump, args.limit)
    print(f"          {len(labels):,} entity có label")

    print(f"\n[Step 2] Pass 2 → extract fact (s và o đều có label)…")
    facts = step2_extract_facts(args.dump, labels, args.limit)
    print(f"          {len(facts):,} fact thô")

    print(f"\n[Step 3] Lọc relation hiếm (≥ {BUILD_MIN_RELATION_FACTS}):")
    facts = step3_filter_relations(facts)

    print(f"\n[Step 4] Lọc entity hiếm (≥ {BUILD_MIN_ENTITY_FACTS}):")
    facts, needed = step4_filter_entities(facts)

    print(f"\n[Output] Ghi cache (label vi ưu tiên, fallback en)…")
    write_cache(facts, labels, needed)


if __name__ == "__main__":
    main()
