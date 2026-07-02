"""Fine-tune PhoBERT cross-encoder cho action reranking.

Cần: torch + transformers + sentence-transformers + pyvi
(`pip install -r ari/requirements-ce.txt`).

Split theo CÂU HỎI để tránh leak (mọi step của một câu nằm cùng phía). Sau train
in Hit@K / MRR trên val theo từng nhóm (question, step).
"""
from __future__ import annotations
import argparse
import json
import random
from pathlib import Path

from . import config
from . import ce_serialize as S


def load_examples(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def split_by_question(rows: list[dict], val_frac: float = 0.15, seed: int = 319):
    qs = sorted({r["question"] for r in rows})
    random.Random(seed).shuffle(qs)
    n_val = int(len(qs) * val_frac)
    val_q = set(qs[:n_val])
    train = [r for r in rows if r["question"] not in val_q]
    val = [r for r in rows if r["question"] in val_q]
    return train, val


def _to_input_example(r: dict):
    from sentence_transformers import InputExample
    return InputExample(
        texts=[S.segment(r["context_text"]), S.segment(r["action_text"])],
        label=float(r["label"]),
    )


def evaluate_ranking(model, val: list[dict], top_k: int = 12) -> tuple[float, float, int]:
    """Hit@K / MRR theo nhóm (question, step): xếp hạng action positive trong nhóm."""
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for r in val:
        groups[(r["question"], r["step"])].append(r)
    hit, mrr, n = 0, 0.0, 0
    for rows in groups.values():
        if not any(r["label"] == 1 for r in rows):
            continue
        pairs = [[S.segment(r["context_text"]), S.segment(
            r["action_text"])] for r in rows]
        scores = model.predict(pairs)
        order = sorted(range(len(rows)), key=lambda i: -scores[i])
        best = min(rank for rank, i in enumerate(
            order, 1) if rows[i]["label"] == 1)
        n += 1
        hit += 1 if best <= top_k else 0
        mrr += 1.0 / best
    if not n:
        return 0.0, 0.0, 0
    return hit / n, mrr / n, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(config.CE_DATASET))
    ap.add_argument("--out", default=str(config.CE_MODEL_DIR))
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    args = ap.parse_args()

    from sentence_transformers import CrossEncoder
    from torch.utils.data import DataLoader

    rows = load_examples(Path(args.dataset))
    train, val = split_by_question(rows)
    print(f"[ce_train] train={len(train)} val={len(val)} "
          f"(pos train={sum(r['label'] for r in train)})")

    train_ex = [_to_input_example(r) for r in train]
    loader = DataLoader(train_ex, shuffle=True, batch_size=args.batch)

    model = CrossEncoder(config.CE_BASE_MODEL, num_labels=1,
                         max_length=config.CE_MAX_LEN)
    warmup = int(len(loader) * args.epochs * 0.1)
    model.fit(train_dataloader=loader, epochs=args.epochs, warmup_steps=warmup,
              optimizer_params={"lr": args.lr}, output_path=args.out)

    model.save(args.out)
    print(f"[ce_train] saved -> {args.out}")

    hit, mrr, n = evaluate_ranking(model, val, top_k=config.TOP_K_ACTIONS)
    print(f"[ce_train] val Hit@{config.TOP_K_ACTIONS}={hit:.3f} MRR={mrr:.3f} "
          f"({n} groups)")


if __name__ == "__main__":
    main()
