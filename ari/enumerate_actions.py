"""Candidate action enumeration and filtration (paper §3.3).

We enumerate, for the seed entities of the question and for the previous-step
result, all atomic actions that are non-empty when executed. We then rank by
semantic similarity to the question (Ollama embeddings) and keep top-K.
"""
from __future__ import annotations
import math

from .kg import KG
from .actions import (
    Action, EntitySet, execute,
    op_get_tail_entity, op_get_head_entity, op_get_time,
)
from . import config


def _cos(a: list[float], b: list[float]) -> float:
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return s / (na * nb)


def _years_for(kg: KG, qid: str, relation: str) -> list[int]:
    years: set[int] = set()
    for f in kg.by_s.get(qid, []) + kg.by_o.get(qid, []):
        if f.relation != relation:
            continue
        if f.start is not None:
            years.add(f.start)
        if f.end is not None:
            years.add(f.end)
    return sorted(years)


def enumerate_initial(kg: KG, seed_qids: list[str], relation: str | None,
                       year: int | None) -> list[Action]:
    """Enumerate get_tail_entity / get_head_entity / get_time from seeds.

    If `relation` is None, all relations participating with the seeds are
    considered (relies on downstream semantic top-K filter to narrow).
    """
    out: list[Action] = []
    relations = [relation] if relation else None

    for qid in seed_qids:
        rels_here = set()
        for f in kg.by_s.get(qid, []) + kg.by_o.get(qid, []):
            if relations and f.relation not in relations:
                continue
            rels_here.add(f.relation)

        for rel in rels_here:
            rlabel = kg.rlabel(rel)
            qlabel = kg.label(qid)

            # get_tail_entity (qid acts as head)
            tail_ents = op_get_tail_entity(kg, qid, rel, year)
            if tail_ents:
                disp = f'$get_tail_entity("{qlabel}", "{rlabel}", {year if year else "no time"})$'
                out.append(Action("get_tail_entity", (qid, rel, year), disp))
            # also without time
            if year is not None:
                te2 = op_get_tail_entity(kg, qid, rel, None)
                if te2:
                    disp = f'$get_tail_entity("{qlabel}", "{rlabel}", no time)$'
                    out.append(Action("get_tail_entity", (qid, rel, None), disp))

            # get_head_entity (qid acts as tail)
            head_ents = op_get_head_entity(kg, qid, rel, year)
            if head_ents:
                disp = f'$get_head_entity("{qlabel}", "{rlabel}", {year if year else "no time"})$'
                out.append(Action("get_head_entity", (qid, rel, year), disp))
            if year is not None:
                he2 = op_get_head_entity(kg, qid, rel, None)
                if he2:
                    disp = f'$get_head_entity("{qlabel}", "{rlabel}", no time)$'
                    out.append(Action("get_head_entity", (qid, rel, None), disp))

            # get_time: pair head/tail across seeds
            for other in seed_qids:
                if other == qid:
                    continue
                # qid as head, other as tail
                if op_get_time(kg, qid, rel, other):
                    disp = f'$get_time("{qlabel}", "{rlabel}", "{kg.label(other)}")$'
                    out.append(Action("get_time", (qid, rel, other), disp))

    return out


def enumerate_followups(prev: EntitySet, year_hint: int | None) -> list[Action]:
    """Actions usable on a non-empty previous result.

    Always emits `get_before/get_after/get_between` with a `{your specified time}`
    placeholder so the LLM can fill in a year derived from earlier steps
    (matching the reference paper's action template). `year_hint` (if set)
    additionally emits a concrete-year shortcut.
    """
    out: list[Action] = []
    if not prev:
        return out
    if len(prev) > 1:
        out.append(Action("get_first", (), "$get_first({entities})$"))
        out.append(Action("get_last", (), "$get_last({entities})$"))

    # Placeholder versions (paper-style) — LLM must replace placeholder with a year
    out.append(Action("get_before", (None,),
                      "$get_before({entities}, {your specified time})$"))
    out.append(Action("get_after", (None,),
                      "$get_after({entities}, {your specified time})$"))
    out.append(Action("get_between", (None, None),
                      "$get_between({entities}, {your specified start time}, {your specified end time})$"))

    # Concrete-year shortcut when the question itself supplies a year
    if year_hint is not None:
        out.append(Action("get_before", (year_hint,),
                          f"$get_before({{entities}}, {year_hint})$"))
        out.append(Action("get_after", (year_hint,),
                          f"$get_after({{entities}}, {year_hint})$"))
    return out


def enumerate_answers(prev: EntitySet, answer_type: str) -> list[Action]:
    """answer(...) actions: one per distinct candidate value in prev."""
    out: list[Action] = []
    seen: set = set()
    for (l, q, y) in prev or []:
        v = y if answer_type == "time" else l
        if v is None or v in seen:
            continue
        seen.add(v)
        out.append(Action("answer", (v,), f"$answer({v})$"))
        if len(out) >= 10:
            break
    return out


def filter_actions(actions: list[Action], question: str, embed_fn,
                   top_k: int = config.TOP_K_ACTIONS) -> list[Action]:
    """Keep top-K actions by cosine similarity of their display string to question."""
    if len(actions) <= top_k:
        return actions
    texts = [question] + [a.display for a in actions]
    vecs = embed_fn(texts)
    qv = vecs[0]
    scored = sorted(
        zip(actions, vecs[1:]),
        key=lambda x: _cos(qv, x[1]),
        reverse=True,
    )
    return [a for a, _ in scored[:top_k]]
