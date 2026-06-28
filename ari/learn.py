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
from .ollama_client import openai_chat, openai_embed
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
    ap.add_argument("--llm", choices=("openai", "ollama"), default="openai",
                    help="Chat LLM cho action select + methodology induction "
                         "(default: openai = GPT-4o, theo paper)")
    ap.add_argument("--embed", choices=("openai", "ollama"), default="ollama",
                    help="Embedding provider cho cluster K-means + select_methodology "
                         "(default: ollama — match eval phase để tránh dim mismatch)")
    ap.add_argument("--resume", action="store_true",
                    help="Bỏ qua bước chạy 200 câu, load --records-out có sẵn rồi induce methodology ngay")
    ap.add_argument("--no-incorrect", action="store_true",
                    help="Ablation w/o Incorrect Examples: chỉ chắt lọc methodology từ ví dụ ĐÚNG")
    args = ap.parse_args()

    chat_fn = openai_chat if args.llm == "openai" else None  # None = default ollama
    embed_fn = openai_embed if args.embed == "openai" else None
    chat_model = config.OPENAI_MODEL if args.llm == "openai" else config.LLM_MODEL
    embed_model = config.OPENAI_EMBED_MODEL if args.embed == "openai" else config.EMBED_MODEL
    print(f"[learn] chat={args.llm} ({chat_model})   embed={args.embed} ({embed_model})")

    if args.resume:
        recs_path = Path(args.records_out)
        if not recs_path.exists():
            raise SystemExit(f"--resume cần file {recs_path} tồn tại")
        records = json.loads(recs_path.read_text(encoding="utf-8"))
        n_ok = sum(1 for r in records if r["correct"])
        print(f"[learn] resume từ {recs_path}: {len(records)} records, "
              f"acc={n_ok}/{len(records)} = {n_ok/len(records):.3f}")
    else:
        print(f"[learn] loading KG ...")
        kg = get_kg()
        print(f"[learn] facts={len(kg.facts)} qids={len(kg.qid2label)} pids={len(kg.pid2label)}")

        with open(args.questions, encoding="utf-8") as f:
            all_q = json.load(f)
        samples = stratified_sample(all_q, args.n)
        print(f"[learn] sampled {len(samples)} questions ({len({q['qtype'] for q in samples})} qtypes)")

        records = []
        for i, q in enumerate(samples, 1):
            trace = run_question(kg, q, methodology=FALLBACK_METHODOLOGY,
                                  chat_fn=chat_fn)
            rec = trace_to_record(trace, entity_qids=q.get("entities"),
                                   template=q.get("template"))
            records.append(rec)
            if i % 10 == 0 or i == len(samples):
                n_ok = sum(1 for r in records if r["correct"])
                print(f"[learn] {i}/{len(samples)}  acc-so-far={n_ok / i:.3f}")

        Path(args.records_out).write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"[learn] wrote {args.records_out}")

    print(f"[learn] inducing {args.k} methodologies via K-means ...")
    bank = build_memory_bank(records, k=args.k, out_path=Path(args.out),
                              chat_fn=chat_fn, embed_fn=embed_fn,
                              use_incorrect=not args.no_incorrect)
    print(f"[learn] wrote {args.out} ({len(bank['clusters'])} clusters)")


if __name__ == "__main__":
    main()
