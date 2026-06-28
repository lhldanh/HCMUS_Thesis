"""Inference + evaluation phase.

Hỗ trợ ARI (đầy đủ), các ablation và các baseline để dựng Bảng 5.3/5.4/5.5.

ARI & ablation (cùng engine `agent.run_question`):
    python3 -m ari.evaluate                        # ARI đầy đủ
    python3 -m ari.evaluate --no-methodology       # ablation: w/o Abstract Guidance
    python3 -m ari.evaluate --no-action-filter     # ablation: w/o Action Filter
  (w/o History Cluster  -> learn --k 1 --resume rồi --bank memory_bank_k1.json)
  (w/o Incorrect Examples -> learn --no-incorrect --resume rồi --bank ...)

Baseline:
    python3 -m ari.evaluate --method llm-only
    python3 -m ari.evaluate --method kg-rag
    python3 -m ari.evaluate --method cot-kb
    python3 -m ari.evaluate --method react-kb

Cross-encoder: đặt USE_CROSS_ENCODER=True trong config.py rồi chạy --method ari.

Mỗi run ghi trace ra file riêng (mặc định eval_<tag>.json) để không đè nhau.
"""
from __future__ import annotations
import argparse
import json
import random
from collections import Counter
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


def _run_tag(args) -> str:
    """Nhãn ngắn để đặt tên file output, phản ánh phương pháp + ablation."""
    if args.method != "ari":
        return args.method
    if args.no_methodology:
        return "ari_no-methodology"
    if args.no_action_filter:
        return "ari_no-action-filter"
    if config.USE_CROSS_ENCODER:
        return "ari_cross-encoder"
    # nếu dùng bank khác mặc định (vd no-cluster / no-incorrect) thì gắn tên bank
    default_bank = str(config.ARTIFACTS_DIR / "memory_bank.json")
    if args.bank != default_bank:
        return "ari_" + Path(args.bank).stem
    return "ari"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="ari",
                    choices=("ari", "llm-only", "kg-rag", "cot-kb", "react-kb"),
                    help="ari (mặc định) | baselines")
    ap.add_argument("--bank", default=str(config.ARTIFACTS_DIR / "memory_bank.json"))
    ap.add_argument("--questions", default=str(config.QUESTIONS_FILE))
    ap.add_argument("--n", type=int, default=config.TEST_SAMPLE_SIZE)
    ap.add_argument("--no-methodology", action="store_true",
                    help="Ablation: bỏ hướng dẫn trừu tượng (w/o Abstract Guidance)")
    ap.add_argument("--no-action-filter", action="store_true",
                    help="Ablation: bỏ lọc top-K ngữ nghĩa (w/o Action Filter)")
    ap.add_argument("--out", default=None,
                    help="Mặc định: artifacts/eval_<tag>.json")
    args = ap.parse_args()

    tag = _run_tag(args)
    out_path = Path(args.out) if args.out else (config.ARTIFACTS_DIR / f"eval_{tag}.json")

    kg = get_kg()
    print(f"[eval] method={args.method} tag={tag} facts={len(kg.facts)} "
          f"cross_encoder={config.USE_CROSS_ENCODER}")

    # Methodology bank chỉ cần cho ARI có hướng dẫn.
    bank = None
    if args.method == "ari" and not args.no_methodology and Path(args.bank).exists():
        bank = load_bank(Path(args.bank))
        print(f"[eval] loaded bank with {len(bank['clusters'])} clusters "
              f"({Path(args.bank).name})")
    elif args.method == "ari":
        print("[eval] no methodology (ablation hoặc bank thiếu)")

    with open(args.questions, encoding="utf-8") as f:
        all_q = json.load(f)
    samples = stratified_sample(all_q, args.n)
    print(f"[eval] {len(samples)} questions")

    # Baselines single-shot dùng module riêng (lazy import: torch không cần).
    baseline_fn = None
    if args.method in ("llm-only", "kg-rag", "cot-kb"):
        from . import baselines
        baseline_fn = baselines.run_baseline

    traces: list[dict] = []
    c_qt, t_qt = Counter(), Counter()
    c_at, t_at = Counter(), Counter()
    c_ql, t_ql = Counter(), Counter()

    SAVE_EVERY = 5
    for i, q in enumerate(samples, 1):
        if baseline_fn is not None:
            rec = baseline_fn(kg, q, args.method)
        else:  # ari | react-kb
            if args.method == "react-kb":
                trace = run_question(kg, q, methodology=FALLBACK_METHODOLOGY,
                                     action_filter=not args.no_action_filter,
                                     react=True)
            else:
                methodology = (select_methodology(bank, q) if bank
                               else FALLBACK_METHODOLOGY)
                trace = run_question(kg, q, methodology=methodology,
                                     action_filter=not args.no_action_filter)
            rec = trace_to_record(trace, entity_qids=q.get("entities"),
                                  template=q.get("template"))
            rec["method"] = args.method

        traces.append(rec)
        qt, at = q["qtype"], q["answer_type"]
        ql = q.get("qlabel", "?")
        t_qt[qt] += 1; t_at[at] += 1; t_ql[ql] += 1
        if rec["correct"]:
            c_qt[qt] += 1; c_at[at] += 1; c_ql[ql] += 1

        if i % SAVE_EVERY == 0 or i == len(samples):
            acc = sum(1 for t in traces if t["correct"]) / i
            print(f"[eval] {i}/{len(samples)}  acc={acc:.3f}")
            tmp = out_path.with_suffix(out_path.suffix + ".tmp")
            tmp.write_text(json.dumps(traces, ensure_ascii=False, indent=2),
                           encoding="utf-8")
            tmp.replace(out_path)

    out_path.write_text(json.dumps(traces, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    total = len(traces)
    correct = sum(1 for t in traces if t["correct"])
    print("=" * 60)
    print(f"[{tag}] Overall:  {correct}/{total} = {correct / total:.3f}")
    print("By qtype:")
    for k in sorted(t_qt):
        print(f"  {k:16s}  {c_qt[k]}/{t_qt[k]}  = {c_qt[k] / t_qt[k]:.3f}")
    print("By answer_type:")
    for k in sorted(t_at):
        print(f"  {k:10s}  {c_at[k]}/{t_at[k]}  = {c_at[k] / t_at[k]:.3f}")
    print("By qlabel:")
    for k in sorted(t_ql):
        print(f"  {k:10s}  {c_ql[k]}/{t_ql[k]}  = {c_ql[k] / t_ql[k]:.3f}")
    print(f"[eval] wrote {out_path}")


if __name__ == "__main__":
    main()
