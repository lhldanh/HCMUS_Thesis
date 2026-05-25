"""Learning phase: run N samples without methodology, then induce M_C per cluster."""
from __future__ import annotations
import argparse
import json
import random
from pathlib import Path

from . import config
from .agent import run_question
from .kg import get_kg
from .memory import build_memory_bank, trace_to_record
from .prompts import FALLBACK_METHODOLOGY


def stratified_sample(questions: list[dict], n: int, seed: int = 0) -> list[dict]:
    random.seed(seed)
    by_t: dict[str, list[dict]] = {}
    for q in questions:
        by_t.setdefault(q["qtype"], []).append(q)
    per = max(1, n // max(1, len(by_t)))
    out: list[dict] = []
    for t, qs in by_t.items():
        random.shuffle(qs)
        out.extend(qs[:per])
    random.shuffle(out)
    return out[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=config.N_MEMORY_SAMPLES)
    ap.add_argument("--k", type=int, default=config.N_CLUSTERS)
    ap.add_argument("--questions", default=str(config.QUESTIONS_FILE))
    ap.add_argument("--out", default=str(config.ARTIFACTS_DIR / "memory_bank.json"))
    ap.add_argument("--records-out",
                    default=str(config.ARTIFACTS_DIR / "history_records.json"))
    args = ap.parse_args()

    print(f"[learn] loading KG ...")
    kg = get_kg()
    print(f"[learn] facts={len(kg.facts)} qids={len(kg.qid2label)} pids={len(kg.pid2label)}")

    with open(args.questions, encoding="utf-8") as f:
        all_q = json.load(f)
    samples = stratified_sample(all_q, args.n)
    print(f"[learn] sampled {len(samples)} questions ({len({q['qtype'] for q in samples})} qtypes)")

    records: list[dict] = []
    for i, q in enumerate(samples, 1):
        trace = run_question(kg, q, methodology=FALLBACK_METHODOLOGY)
        rec = trace_to_record(trace, entity_qids=q.get("entities"))
        records.append(rec)
        if i % 10 == 0 or i == len(samples):
            n_ok = sum(1 for r in records if r["correct"])
            print(f"[learn] {i}/{len(samples)}  acc-so-far={n_ok / i:.3f}")

    Path(args.records_out).write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print(f"[learn] wrote {args.records_out}")

    print(f"[learn] inducing {args.k} methodologies via K-means ...")
    bank = build_memory_bank(records, k=args.k, out_path=Path(args.out))
    print(f"[learn] wrote {args.out} ({len(bank['clusters'])} clusters)")


if __name__ == "__main__":
    main()
