"""Atomic action templates and executor.

An action is a dict: {"op": str, "args": (...)}. `args` reference either qids,
relation pids, years, or a reference to a prior step's entity list ("$prev").

The executor returns a result of type ``EntitySet`` — list of ``(label, qid, year)``
triples — or a literal answer.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from .kg import KG, Fact


EntitySet = List[Tuple[str, str, Optional[int]]]  # (label, qid, year)


@dataclass
class Action:
    op: str
    args: tuple
    display: str  # human-friendly string shown to LLM

    def to_jsonable(self) -> dict:
        return {"op": self.op, "args": list(self.args), "display": self.display}


# ---------- helpers ----------

def _fact_year(f: Fact, prefer: str = "start") -> int | None:
    if prefer == "start" and f.start is not None:
        return f.start
    if prefer == "end" and f.end is not None:
        return f.end
    return f.start if f.start is not None else f.end


def _in_window(f: Fact, year: int) -> bool:
    if f.start is None and f.end is None:
        return False
    a = f.start if f.start is not None else f.end
    b = f.end if f.end is not None else f.start
    return min(a, b) <= year <= max(a, b)


# ---------- atomic operations ----------

def op_get_tail_entity(kg: KG, head_qid: str, relation: str, year: int | None) -> EntitySet:
    out: EntitySet = []
    for f in kg.by_s.get(head_qid, []):
        if f.relation != relation:
            continue
        if year is not None and not _in_window(f, year):
            continue
        out.append((kg.label(f.o_qid), f.o_qid, _fact_year(f)))
    return out


def op_get_head_entity(kg: KG, tail_qid: str, relation: str, year: int | None) -> EntitySet:
    out: EntitySet = []
    for f in kg.by_o.get(tail_qid, []):
        if f.relation != relation:
            continue
        if year is not None and not _in_window(f, year):
            continue
        out.append((kg.label(f.s_qid), f.s_qid, _fact_year(f)))
    return out


def op_get_time(kg: KG, head_qid: str, relation: str, tail_qid: str) -> EntitySet:
    out: EntitySet = []
    for f in kg.by_s.get(head_qid, []):
        if f.relation == relation and f.o_qid == tail_qid:
            y = _fact_year(f)
            if y is not None:
                out.append((kg.label(head_qid), head_qid, y))
    return out


def op_get_before(ents: EntitySet, year: int) -> EntitySet:
    return [(l, q, y) for (l, q, y) in ents if y is not None and y < year]


def op_get_after(ents: EntitySet, year: int) -> EntitySet:
    return [(l, q, y) for (l, q, y) in ents if y is not None and y > year]


def op_get_between(ents: EntitySet, y1: int, y2: int) -> EntitySet:
    lo, hi = min(y1, y2), max(y1, y2)
    return [(l, q, y) for (l, q, y) in ents if y is not None and lo <= y <= hi]


def op_get_first(ents: EntitySet) -> EntitySet:
    es = [e for e in ents if e[2] is not None]
    if not es:
        return []
    m = min(e[2] for e in es)
    return [e for e in es if e[2] == m]


def op_get_last(ents: EntitySet) -> EntitySet:
    es = [e for e in ents if e[2] is not None]
    if not es:
        return []
    m = max(e[2] for e in es)
    return [e for e in es if e[2] == m]


# ---------- executor ----------

def execute(kg: KG, action: Action, prev: EntitySet | None) -> Any:
    op, args = action.op, action.args
    if op == "get_tail_entity":
        head_qid, relation, year = args
        return op_get_tail_entity(kg, head_qid, relation, year)
    if op == "get_head_entity":
        tail_qid, relation, year = args
        return op_get_head_entity(kg, tail_qid, relation, year)
    if op == "get_time":
        head_qid, relation, tail_qid = args
        return op_get_time(kg, head_qid, relation, tail_qid)
    if op == "get_before":
        (year,) = args
        return op_get_before(prev or [], year)
    if op == "get_after":
        (year,) = args
        return op_get_after(prev or [], year)
    if op == "get_between":
        y1, y2 = args
        return op_get_between(prev or [], y1, y2)
    if op == "get_first":
        return op_get_first(prev or [])
    if op == "get_last":
        return op_get_last(prev or [])
    if op == "answer":
        return args[0]
    raise ValueError(f"unknown op: {op}")


def format_entset(ents: EntitySet, limit: int = 8) -> str:
    if not ents:
        return "[]"
    head = ents[:limit]
    extra = f" ... (+{len(ents) - limit})" if len(ents) > limit else ""
    return "[" + ", ".join(f"({l}, {y})" for (l, _, y) in head) + "]" + extra
