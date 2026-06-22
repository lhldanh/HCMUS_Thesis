"""Sinh dataset cross-encoder: gold-path induced-from-KG (positive) + pool
negatives + hard negatives từ trace LLM sai.

Chạy được bằng stdlib + numpy (data-gen GIỮ TOÀN BỘ pool để lấy negative — bỏ
qua cosine top-K, vốn chỉ dùng lúc inference).
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from . import config
from .kg import get_kg
from .actions import Action, execute
from .enumerate_actions import (
    enumerate_initial, enumerate_followups, enumerate_answers,
)
from . import ce_goldpath as G
from . import ce_serialize as S

# Các op mà pool hiển thị dạng placeholder (chưa điền năm) — positive khớp theo
# op, vì gold-path dùng năm cụ thể còn pool chỉ có placeholder.
_PLACEHOLDER_OPS = {"get_before", "get_after", "get_between"}


class _FakeStep:
    """Mô phỏng StepLog cho ce_serialize.build_context_text (duck-typed)."""
    def __init__(self, action: Action, prev):
        self.chosen = action.display
        self.op = action.op
        self.entities = list(prev)


def _enumerate_pool(kg, seeds, last_relation, year, prev, answer_type, used):
    initial = enumerate_initial(kg, seeds, last_relation, year)
    follow = enumerate_followups(prev, year) if prev else []
    answers = enumerate_answers(prev, answer_type) if prev else []
    seen, uniq = set(), []
    for a in (initial + follow + answers):
        if a.display in seen:
            continue
        if a.op != "answer" and a.display in used:
            continue
        seen.add(a.display)
        uniq.append(a)
    return uniq


def _is_positive(cand: Action, pos_actions: list[Action]) -> bool:
    for g in pos_actions:
        if g.op in _PLACEHOLDER_OPS:
            if cand.op == g.op:
                return True
        elif cand.display == g.display:
            return True
    return False


def examples_for_question(kg, q) -> list[dict]:
    path = G.reconstruct_gold_path(kg, q)
    if path is None or not G.verify_path(kg, q, path):
        return []
    seeds = list(q.get("entities") or [])
    year = q.get("year")
    answer_type = q.get("answer_type", "entity")
    last_relation = q.get("relation")
    prev, steps, used = [], [], set()
    out: list[dict] = []

    def emit(pos_actions, pool, step_i):
        for cand in pool:
            ctx, act = S.make_pair(q["question"], steps, cand)
            pos = _is_positive(cand, pos_actions)
            out.append({
                "question": q["question"], "qtype": q["qtype"], "step": step_i,
                "context_text": ctx, "action_text": act,
                "label": 1 if pos else 0,
                "source": "gold" if pos else "pool",
            })

    # các bước reasoning (mỗi bước có đúng 1 gold action)
    for step_i, gold_action in enumerate(path):
        pool = _enumerate_pool(kg, seeds, last_relation, year, prev,
                               answer_type, used)
        # đảm bảo có ít nhất 1 positive trong pool (placeholder hoặc concrete)
        if not any(_is_positive(c, [gold_action]) for c in pool):
            pool = pool + [gold_action]
        emit([gold_action], pool, step_i)
        used.add(gold_action.display)
        prev = execute(kg, gold_action, prev)
        steps.append(_FakeStep(gold_action, prev))
        if gold_action.op in ("get_tail_entity", "get_head_entity", "get_time"):
            last_relation = gold_action.args[1]

    # bước answer cuối: positive = tập gold_answer_actions
    pos = G.gold_answer_actions(kg, q, prev)
    if pos:
        pool = _enumerate_pool(kg, seeds, last_relation, year, prev,
                               answer_type, used)
        pool_disp = {c.display for c in pool}
        for a in pos:
            if a.display not in pool_disp:
                pool.append(a)
        emit(pos, pool, len(path))
    return out


def _hard_negatives(kg, records: list[dict], max_steps: int = 2) -> list[dict]:
    """Từ trace LLM SAI: action LLM chọn (op != answer) ở vài bước đầu -> negative
    khó. Context dựng theo chính trace của LLM (step_entities có sẵn trong record)."""
    out = []
    for rec in records:
        if rec.get("correct"):
            continue
        steps_so_far = []
        for s in rec.get("steps", []):
            op = s.get("op")
            if op in (None, "noop", "answer"):
                break
            ctx = S.build_context_text(rec["question"], steps_so_far)
            act = S.action_to_vi(Action(op, (), s.get("chosen", "")))
            out.append({
                "question": rec["question"], "qtype": rec.get("qtype"),
                "step": len(steps_so_far),
                "context_text": ctx, "action_text": act,
                "label": 0, "source": "hard",
            })
            steps_so_far.append(s)
            if len(steps_so_far) >= max_steps:
                break
    return out


def build_dataset(kg, questions, history_path: Path | None = None) -> list[dict]:
    data, kept, dropped = [], 0, 0
    by_qt_keep, by_qt_tot = {}, {}
    for q in questions:
        by_qt_tot[q["qtype"]] = by_qt_tot.get(q["qtype"], 0) + 1
        exs = examples_for_question(kg, q)
        if exs:
            kept += 1
            by_qt_keep[q["qtype"]] = by_qt_keep.get(q["qtype"], 0) + 1
        else:
            dropped += 1
        data.extend(exs)
    n_hard = 0
    if history_path and Path(history_path).exists():
        recs = json.load(open(history_path, encoding="utf-8"))
        hard = _hard_negatives(kg, recs)
        n_hard = len(hard)
        data.extend(hard)
    keep_str = ", ".join(f"{qt}:{by_qt_keep.get(qt,0)}/{by_qt_tot[qt]}"
                         for qt in sorted(by_qt_tot))
    print(f"[ce_data] giữ {kept} câu, rớt {dropped}  ({keep_str})")
    n_pos = sum(1 for d in data if d["label"] == 1)
    print(f"[ce_data] {len(data)} examples — pos={n_pos}, "
          f"neg={len(data)-n_pos} (hard={n_hard})")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(config.QUESTIONS_FILE))
    ap.add_argument("--history",
                    default=str(config.ARTIFACTS_DIR / "history_records.json"))
    ap.add_argument("--out", default=str(config.CE_DATASET))
    args = ap.parse_args()
    kg = get_kg()
    qs = json.load(open(args.questions, encoding="utf-8"))
    data = build_dataset(kg, qs, Path(args.history))
    with open(args.out, "w", encoding="utf-8") as f:
        for d in data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"[ce_data] wrote {args.out}")


if __name__ == "__main__":
    main()
