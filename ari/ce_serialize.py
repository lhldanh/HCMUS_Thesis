"""Serialize (question, reasoning history, action) into a PhoBERT cross-encoder
pair.

``action_to_vi`` / ``build_context_text`` are pure (stdlib only); ``segment``
lazily imports pyvi so importing this module stays cheap on the default path.
"""
from __future__ import annotations
import re

from .actions import Action, EntitySet

_OP_VI = {
    "get_tail_entity": 'Tìm thực thể mà "{e}" có quan hệ "{r}"{t}',
    "get_head_entity": 'Tìm thực thể có quan hệ "{r}" tới "{e}"{t}',
    "get_time":        'Tìm thời gian "{e}" có quan hệ "{r}" với "{o}"',
    "get_before":      "Lọc các kết quả trước năm {y}",
    "get_after":       "Lọc các kết quả sau năm {y}",
    "get_between":     "Lọc các kết quả trong khoảng năm {y1}–{y2}",
    "get_first":       "Lấy kết quả sớm nhất theo thời gian",
    "get_last":        "Lấy kết quả muộn nhất theo thời gian",
}

_QUOTED = re.compile(r'"([^"]*)"')
_YEAR = re.compile(r"\b(\d{4})\b")


def _quoted(a: Action) -> list[str]:
    return _QUOTED.findall(a.display or "")


def action_to_vi(a: Action) -> str:
    """Dịch một Action sang câu tiếng Việt tự nhiên. Ưu tiên label người-đọc
    trong display; fallback sang args."""
    op = a.op
    q = _quoted(a)
    if op in ("get_tail_entity", "get_head_entity"):
        e = q[0] if len(q) > 0 else (str(a.args[0]) if a.args else "")
        r = q[1] if len(q) > 1 else (str(a.args[1]) if len(a.args) > 1 else "")
        yr = a.args[2] if len(a.args) > 2 else None
        if yr is None:  # display có thể chứa năm dù args rỗng
            ys = _YEAR.findall(a.display or "")
            yr = ys[0] if ys else None
        t = f" vào năm {yr}" if yr else ""
        return _OP_VI[op].format(e=e, r=r, t=t)
    if op == "get_time":
        e = q[0] if len(q) > 0 else (str(a.args[0]) if a.args else "")
        r = q[1] if len(q) > 1 else (str(a.args[1]) if len(a.args) > 1 else "")
        o = q[2] if len(q) > 2 else (str(a.args[2]) if len(a.args) > 2 else "")
        return _OP_VI[op].format(e=e, r=r, o=o)
    if op in ("get_before", "get_after"):
        y = a.args[0] if a.args else None
        if y is None:
            ys = _YEAR.findall(a.display or "")
            y = ys[0] if ys else None
        if y is None:  # placeholder (chưa điền năm) — khớp với cái LLM thấy
            kw = "trước" if op == "get_before" else "sau"
            return f"Lọc các kết quả {kw} mốc thời gian đã xác định"
        return _OP_VI[op].format(y=y)
    if op == "get_between":
        if len(a.args) >= 2 and a.args[0] is not None:
            y1, y2 = a.args[0], a.args[1]
        else:
            ys = _YEAR.findall(a.display or "")
            if len(ys) >= 2:
                y1, y2 = ys[0], ys[1]
            else:
                return "Lọc các kết quả trong khoảng thời gian đã xác định"
        return _OP_VI[op].format(y1=y1, y2=y2)
    if op in ("get_first", "get_last"):
        return _OP_VI[op]
    if op == "answer":
        val = a.args[0] if a.args else (q[0] if q else "")
        return f"Trả lời: {val}"
    return a.display or ""


def compress_entities(ents: EntitySet, max_items: int = 3) -> str:
    """Nén entity-list: sort theo thời gian, giữ 2 đầu + 1 cuối."""
    if not ents:
        return "[]"
    s = sorted(ents, key=lambda e: (e[2] is None, e[2] if e[2] is not None else 0))
    if len(s) > max_items:
        items = s[:2] + ["…"] + s[-1:]
    else:
        items = s
    def fmt(e):
        return "…" if e == "…" else f"({e[0]}, {e[2]})"
    return "[" + ", ".join(fmt(e) for e in items) + "]"


def _is_dict(x) -> bool:
    return isinstance(x, dict)


def _step_action_vi(step) -> str:
    chosen = step.get("chosen") if _is_dict(step) else getattr(step, "chosen", None)
    op = step.get("op") if _is_dict(step) else getattr(step, "op", None)
    if op:
        return action_to_vi(Action(op, (), chosen or ""))
    return chosen or ""


def _step_entities(step) -> EntitySet:
    if _is_dict(step):
        ents = step.get("step_entities") or step.get("entities")
    else:
        ents = getattr(step, "entities", None)
    return [tuple(e) for e in (ents or [])]


def build_context_text(question: str, steps: list) -> str:
    parts = [question]
    for i, s in enumerate(steps):
        parts.append(f"Bước {i}: {_step_action_vi(s)} -> {compress_entities(_step_entities(s))}")
    return " [SEP] ".join(parts)


def make_pair(question: str, steps: list, action: Action) -> tuple[str, str]:
    """Trả về (context_text, action_text) — CHƯA segment."""
    return build_context_text(question, steps), action_to_vi(action)


_SEG = None


def segment(text: str) -> str:
    """Word-segment tiếng Việt cho PhoBERT (lazy import pyvi)."""
    global _SEG
    if _SEG is None:
        from pyvi import ViTokenizer
        _SEG = ViTokenizer.tokenize
    return _SEG(text)
