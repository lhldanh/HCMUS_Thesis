"""ARI reasoning agent: knowledge-agnostic decision over knowledge-based actions."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Callable

from . import config
from .kg import KG
from .actions import Action, EntitySet, execute, format_entset
from .enumerate_actions import (
    enumerate_initial, enumerate_followups, enumerate_answers, filter_actions,
)
from .ner import link_entities
from .ollama_client import chat, embed
from .prompts import (
    ACTION_SELECT_SYSTEM, ACTION_SELECT_TEMPLATE,
    FALLBACK_METHODOLOGY,
)


_ACTION_RE = re.compile(r"\$([^$]+)\$")
_YEAR_RE = re.compile(r"\b(\d{4})\b")
_PLACEHOLDER_OPS = {"get_before", "get_after", "get_between"}


@dataclass
class StepLog:
    candidates: list[str]              # display strings
    chosen: str                        # display string $action$
    op: str                            # op name
    result_summary: str                # short string
    reply: str = ""                    # full LLM reply (Action + Reason) — paper uses this for induction
    entities: list = field(default_factory=list)  # raw EntitySet of `prev` after this step


@dataclass
class TraceLog:
    question: str
    qtype: str
    relation: str | None
    year: int | None
    answer_type: str
    methodology: str
    steps: list[StepLog] = field(default_factory=list)
    final_answer: object = None
    gold: list = field(default_factory=list)
    correct: bool = False


def _parse_placeholder_years(text: str) -> list[int]:
    return [int(y) for y in _YEAR_RE.findall(text)]


def _bind_placeholder(a: Action, llm_text: str) -> Action | None:
    """If `a` is a placeholder action (year=None), substitute years parsed
    from the LLM's literal pick. Returns:
      - concrete Action (placeholder filled) when bind succeeds
      - `a` unchanged when `a` is not a placeholder action
      - `None` when `a` IS a placeholder but no year could be parsed
        (caller must skip this candidate to avoid TypeError in execute).
    """
    if a.op == "get_before" and a.args == (None,):
        ys = _parse_placeholder_years(llm_text)
        if not ys:
            return None
        y = ys[0]
        return Action("get_before", (y,), f"$get_before({{entities}}, {y})$")
    if a.op == "get_after" and a.args == (None,):
        ys = _parse_placeholder_years(llm_text)
        if not ys:
            return None
        y = ys[0]
        return Action("get_after", (y,), f"$get_after({{entities}}, {y})$")
    if a.op == "get_between" and a.args == (None, None):
        ys = _parse_placeholder_years(llm_text)
        if len(ys) < 2:
            return None
        y1, y2 = ys[0], ys[1]
        return Action("get_between", (y1, y2),
                      f"$get_between({{entities}}, {y1}, {y2})$")
    return a


def _pick_action(reply: str, actions: list[Action]) -> Action | None:
    """Pick a single Action matching the LLM's reply. All return paths go
    through `_bind_placeholder` so a placeholder action without a year is
    silently skipped instead of crashing `execute`."""
    candidates = _ACTION_RE.findall(reply)
    if candidates:
        # exact display match (LLM may have copied placeholder verbatim — bind
        # ngay tại đây, nếu không bind được thì coi như không match, thử tiếp)
        for c in candidates:
            ctxt = f"${c.strip()}$"
            for a in actions:
                if ctxt == a.display:
                    bound = _bind_placeholder(a, c)
                    if bound is not None:
                        return bound
        # loose: prefix match on op name (typical placeholder→concrete-year)
        for c in candidates:
            head = c.strip().split("(", 1)[0].strip()
            for a in actions:
                if a.op == head:
                    bound = _bind_placeholder(a, c)
                    if bound is not None:
                        return bound
    # very loose fallback: substring of full reply
    for a in actions:
        if a.display in reply:
            bound = _bind_placeholder(a, reply)
            if bound is not None:
                return bound
    return None


def _format_history(steps: list[StepLog]) -> str:
    if not steps:
        return "(chưa có bước nào)"
    lines = []
    for i, s in enumerate(steps):
        lines.append(f"Step {i}: action={s.chosen}  →  result={s.result_summary}")
    return "\n".join(lines)


def _normalize_answer(v) -> str:
    if isinstance(v, int):
        return str(v)
    return str(v).strip().lower()


def _judge(kg: KG, pred, gold: list, answer_type: str) -> bool:
    """Accept a hit when:
    - pred (string/int) matches any gold entry (case-insensitive); OR
    - pred is a qid whose label matches a gold entry; OR
    - pred is a label whose qid matches a gold entry (handles gold-as-qid).
    """
    if pred is None:
        return False
    p = _normalize_answer(pred)
    gold_norm = {_normalize_answer(g) for g in gold}
    if p in gold_norm:
        return True
    # Try qid -> label
    try:
        lbl = kg.label(str(pred))
        if lbl and _normalize_answer(lbl) in gold_norm:
            return True
    except Exception:
        pass
    # Try label -> qid (gold may store qids)
    try:
        qids = kg.label2qids.get(str(pred).strip().lower(), [])
        for q in qids:
            if _normalize_answer(q) in gold_norm:
                return True
    except Exception:
        pass
    return False


def run_question(kg: KG, q: dict, methodology: str | None = None,
                 embed_fn: Callable | None = None,
                 chat_fn: Callable | None = None) -> TraceLog:
    chat_fn = chat_fn or (lambda prompt, system=None: chat(prompt, system=system))
    embed_fn = embed_fn or embed
    methodology = methodology or FALLBACK_METHODOLOGY

    question = q["question"]
    qtype = q["qtype"]
    relation = q.get("relation")
    year = q.get("year")
    answer_type = q.get("answer_type", "entity")
    gold = q.get("answers", [])

    trace = TraceLog(
        question=question, qtype=qtype, relation=relation, year=year,
        answer_type=answer_type, methodology=methodology, gold=gold,
    )

    seeds = list(q.get("entities") or [])
    if not seeds:
        seeds = link_entities(kg, question, relation=relation, max_results=6)
    if not seeds:
        trace.steps.append(StepLog([], "(không link được seed)", "noop", "[]"))
        return trace

    prev: EntitySet = []
    # Paper §3.3 — head/tail entities are fixed at the seeds of the question;
    # only the relation pool moves. `last_relation` mirrors `LLM_rel_choose`
    # in ARI-QA: initially the question's relation, then locked to whichever
    # relation the LLM picks in an entity-op step.
    last_relation: str | None = relation
    for step_i in range(config.MAX_REASONING_STEPS):
        initial = enumerate_initial(kg, seeds, last_relation, year)
        followups = enumerate_followups(prev, year) if prev else []
        answers = enumerate_answers(prev, answer_type) if prev else []
        candidates = initial + followups + answers
        # dedupe by display and forbid actions already chosen in this trace
        # (paper §3.3 — prevents the LLM from looping on the same action).
        # `answer(...)` is exempt since the agent terminates on it anyway.
        used = {s.chosen for s in trace.steps}
        seen, uniq = set(), []
        for a in candidates:
            if a.display in seen:
                continue
            if a.op != "answer" and a.display in used:
                continue
            seen.add(a.display)
            uniq.append(a)
        # filter
        if len(uniq) > config.MAX_CANDIDATES_PER_RELATION:
            uniq = uniq[: config.MAX_CANDIDATES_PER_RELATION]
        if len(uniq) > config.TOP_K_ACTIONS:
            try:
                uniq = filter_actions(uniq, question, embed_fn)
            except Exception:
                uniq = uniq[: config.TOP_K_ACTIONS]

        if not uniq:
            trace.steps.append(StepLog([], "(no candidate)", "noop", "[]"))
            break

        actions_block = "\n".join(f"- {a.display}" for a in uniq)
        prompt = ACTION_SELECT_TEMPLATE.format(
            question=question,
            methodology=methodology,
            history=_format_history(trace.steps),
            actions=actions_block,
        )
        try:
            reply = chat_fn(prompt, system=ACTION_SELECT_SYSTEM)
        except Exception as e:
            trace.steps.append(StepLog([a.display for a in uniq],
                                       f"(LLM error: {e})", "noop", "[]"))
            break

        chosen = _pick_action(reply, uniq)
        if chosen is None:
            # default to first candidate
            chosen = uniq[0]

        # Bọc execute — bất kỳ lỗi nào (placeholder không bind được, op lạ,
        # arg sai kiểu, ...) cũng không được giết câu hỏi.
        try:
            result = execute(kg, chosen, prev)
        except Exception as e:
            trace.steps.append(StepLog(
                [a.display for a in uniq], chosen.display, chosen.op,
                f"(execute error: {type(e).__name__}: {e})",
                reply=reply, entities=[]))
            break

        if chosen.op == "answer":
            trace.steps.append(StepLog(
                [a.display for a in uniq], chosen.display, chosen.op,
                f"answer={result}", reply=reply, entities=[]))
            trace.final_answer = result
            trace.correct = _judge(kg, result, gold, answer_type)
            return trace

        prev = result if isinstance(result, list) else []
        # Paper: when an entity-op is picked, lock the relation for subsequent
        # steps (LLM_rel_choose). args layout: (qid, relation, year/_).
        if chosen.op in ("get_tail_entity", "get_head_entity", "get_time"):
            if len(chosen.args) >= 2 and isinstance(chosen.args[1], str):
                last_relation = chosen.args[1]
        trace.steps.append(StepLog(
            [a.display for a in uniq], chosen.display, chosen.op,
            format_entset(prev), reply=reply, entities=list(prev)))

    # max steps exhausted — pick best from prev
    if prev:
        first = prev[0]
        trace.final_answer = first[2] if answer_type == "time" else first[0]
        trace.correct = _judge(kg, trace.final_answer, gold, answer_type)
    return trace
