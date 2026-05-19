"""Inference + evaluation phase."""
from __future__ import annotations
import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from . import config
from .agent import run_question
from .kg import get_kg
from .memory import load_bank, select_methodology, trace_to_record
from .prompts import FALLBACK_METHODOLOGY


def stratified_sample(questions: list[dict], n: int, seed: int = 1) -> list[dict]:
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
    ap.add_argument("--bank", default=str(config.ARTIFACTS_DIR / "memory_bank.json"))
    ap.add_argument("--questions", default=str(config.QUESTIONS_FILE))
    ap.add_argument("--n", type=int, default=config.TEST_SAMPLE_SIZE)
    ap.add_argument("--no-methodology", action="store_true",
                    help="Ablation: skip abstract guidance")
    ap.add_argument("--out", default=str(config.ARTIFACTS_DIR / "eval_traces.json"))
    args = ap.parse_args()

    kg = get_kg()
    print(f"[eval] facts={len(kg.facts)}")

    bank = None
    if not args.no_methodology and Path(args.bank).exists():
        bank = load_bank(Path(args.bank))
        print(f"[eval] loaded bank with {len(bank['clusters'])} clusters")
    else:
        print("[eval] no methodology (ablation or bank missing)")

    with open(args.questions, encoding="utf-8") as f:
        all_q = json.load(f)
    samples = stratified_sample(all_q, args.n)
    print(f"[eval] {len(samples)} questions")

    traces = []
    by_qtype_correct = Counter()
    by_qtype_total = Counter()
    by_anstype_correct = Counter()
    by_anstype_total = Counter()
    by_qlabel_correct = Counter()
    by_qlabel_total = Counter()

    for i, q in enumerate(samples, 1):
        methodology = select_methodology(bank, q["question"]) if bank else FALLBACK_METHODOLOGY
        trace = run_question(kg, q, methodology=methodology)
        rec = trace_to_record(trace)
        traces.append(rec)
        by_qtype_total[q["qtype"]] += 1
        by_anstype_total[q["answer_type"]] += 1
        by_qlabel_total[q.get("qlabel", "?")] += 1
        if rec["correct"]:
            by_qtype_correct[q["qtype"]] += 1
            by_anstype_correct[q["answer_type"]] += 1
            by_qlabel_correct[q.get("qlabel", "?")] += 1
        if i % 10 == 0 or i == len(samples):
            acc = sum(1 for t in traces if t["correct"]) / i
            print(f"[eval] {i}/{len(samples)}  acc={acc:.3f}")

    Path(args.out).write_text(json.dumps(traces, ensure_ascii=False, indent=2))

    total = len(traces)
    correct = sum(1 for t in traces if t["correct"])
    print("=" * 60)
    print(f"Overall:  {correct}/{total} = {correct / total:.3f}")
    print("By qtype:")
    for k in sorted(by_qtype_total):
        print(f"  {k:16s}  {by_qtype_correct[k]}/{by_qtype_total[k]}  "
              f"= {by_qtype_correct[k] / by_qtype_total[k]:.3f}")
    print("By answer_type:")
    for k in sorted(by_anstype_total):
        print(f"  {k:10s}  {by_anstype_correct[k]}/{by_anstype_total[k]}  "
              f"= {by_anstype_correct[k] / by_anstype_total[k]:.3f}")
    print("By qlabel:")
    for k in sorted(by_qlabel_total):
        print(f"  {k:10s}  {by_qlabel_correct[k]}/{by_qlabel_total[k]}  "
              f"= {by_qlabel_correct[k] / by_qlabel_total[k]:.3f}")
    print(f"[eval] wrote {args.out}")


if __name__ == "__main__":
    main()
