"""Tái tạo chuỗi op gold cho mỗi qtype (deterministic, suy từ KG + annotation),
rồi verify-by-execution.

Không annotate tay. Với các qtype mơ hồ về thứ tự head/tail hoặc hướng
before/after, first/last, ta sinh vài biến thể rồi để verify-by-execution tự
chọn biến thể cho ra đúng ``q["answers"]``.

Verify nghiêm ngặt (``gold ⊆ got``) để nhãn sạch. Hệ quả: một số câu bị loại
vì ngữ nghĩa vượt khỏi bộ op atomic — ``time_join`` (đồng-thời = interval
overlap, không biểu diễn được bằng filter 1 năm) và ``simple_time`` (đáp án là
năm *end* hoặc cả khoảng ``[start, end]`` trong khi op trả ``start``). Tỉ lệ
giữ thực tế in ra ở ``ce_data.build_dataset`` — đây là đánh đổi có chủ đích,
ưu tiên độ sạch của nhãn hơn số lượng.
"""
from __future__ import annotations
import itertools

from .kg import KG
from .actions import Action, execute, op_get_time


def _A(kg: KG, op: str, args: tuple) -> Action:
    """Tạo Action với display khớp định dạng enumerate_actions (để match pool)."""
    if op == "get_tail_entity":
        qid, rel, yr = args
        disp = f'$get_tail_entity("{kg.label(qid)}", "{kg.rlabel(rel)}", {yr if yr else "no time"})$'
    elif op == "get_head_entity":
        qid, rel, yr = args
        disp = f'$get_head_entity("{kg.label(qid)}", "{kg.rlabel(rel)}", {yr if yr else "no time"})$'
    elif op == "get_time":
        h, rel, o = args
        disp = f'$get_time("{kg.label(h)}", "{kg.rlabel(rel)}", "{kg.label(o)}")$'
    elif op == "get_before":
        disp = f"$get_before({{entities}}, {args[0]})$"
    elif op == "get_after":
        disp = f"$get_after({{entities}}, {args[0]})$"
    elif op in ("get_first", "get_last"):
        disp = f"${op}({{entities}})$"
    elif op == "answer":
        disp = f"$answer({args[0]})$"
    else:
        disp = f"${op}{args}$"
    return Action(op, args, disp)


def _anchor_year(kg: KG, head: str, rel: str, tail: str) -> int | None:
    res = op_get_time(kg, head, rel, tail)
    return res[0][2] if res else None


def _exec_path(kg: KG, path: list[Action]):
    prev = []
    for a in path:
        prev = execute(kg, a, prev)
        if not isinstance(prev, list):
            return []
    return prev


def _matches(kg: KG, q: dict, prev) -> bool:
    if not prev:
        return False
    gold = {str(g).strip().lower() for g in q.get("answers", [])}
    if not gold:
        return False
    if q.get("answer_type") == "time":
        got = {str(e[2]) for e in prev if e[2] is not None}
    else:
        got = {str(e[0]).strip().lower() for e in prev}
        if q["qtype"] == "time_join":
            got.discard(kg.label(q["entities"][0]).strip().lower())
    return gold.issubset(got)


def _candidate_paths(kg: KG, q: dict) -> list[list[Action]]:
    """Sinh các biến thể path (chưa verify) cho qtype."""
    qt = q["qtype"]
    ents = q.get("entities") or []
    rel = q.get("relation")
    year = q.get("year")
    paths: list[list[Action]] = []

    if qt == "simple_entity":
        tail = ents[0]
        for yr in (year, None):
            paths.append([_A(kg, "get_head_entity", (tail, rel, yr))])
            paths.append([_A(kg, "get_tail_entity", (tail, rel, yr))])

    elif qt == "simple_time":
        for h, o in itertools.permutations(ents[:2], 2):
            paths.append([_A(kg, "get_time", (h, rel, o))])

    elif qt == "first_last":
        head = ents[0]
        for base in ("get_tail_entity", "get_head_entity"):
            for sel in ("get_first", "get_last"):
                paths.append([_A(kg, base, (head, rel, None)), _A(kg, sel, ())])

    elif qt == "before_after":
        for head, tail in itertools.permutations(ents[:2], 2):
            anchor = _anchor_year(kg, head, rel, tail)
            if anchor is None:
                continue
            for base in ("get_tail_entity", "get_head_entity"):
                for flt in ("get_before", "get_after"):
                    paths.append([
                        _A(kg, base, (head, rel, None)),
                        _A(kg, flt, (anchor,)),
                    ])

    elif qt == "time_join":
        for seed in ents[:2]:
            paths.append([_A(kg, "get_head_entity", (seed, rel, year))])
            paths.append([_A(kg, "get_tail_entity", (seed, rel, year))])

    return paths


def reconstruct_gold_path(kg: KG, q: dict) -> list[Action] | None:
    """Trả về path (executable, năm cụ thể) verify khớp answers; None nếu không có."""
    for path in _candidate_paths(kg, q):
        if _matches(kg, q, _exec_path(kg, path)):
            return path
    return None


def verify_path(kg: KG, q: dict, path: list[Action]) -> bool:
    return _matches(kg, q, _exec_path(kg, path))


def gold_answer_actions(kg: KG, q: dict, prev) -> list[Action]:
    """Tập answer-action đúng tại bước cuối (positive set)."""
    gold = {str(g).strip().lower() for g in q.get("answers", [])}
    out, seen = [], set()
    for (l, _id, y) in prev:
        v = y if q.get("answer_type") == "time" else l
        if v is None or str(v) in seen:
            continue
        seen.add(str(v))
        if str(v).strip().lower() in gold:
            out.append(_A(kg, "answer", (v,)))
    return out
