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


@dataclass
class StepLog:
    candidates: list[str]              # display strings
    chosen: str                        # display string
    op: str                            # op name
    result_summary: str                # short string


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


def _pick_action(reply: str, actions: list[Action]) -> Action | None:
    # extract action between $...$ if present
    candidates = _ACTION_RE.findall(reply)
    if candidates:
        for c in candidates:
            ctxt = f"${c.strip()}$"
            for a in actions:
                if ctxt == a.display:
                    return a
        # loose: prefix match on op name
        for c in candidates:
            head = c.strip().split("(", 1)[0].strip()
            for a in actions:
                if a.op == head:
                    return a
    # very loose fallback
    for a in actions:
        if a.display in reply:
            return a
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


def _judge(pred, gold: list, answer_type: str) -> bool:
    if pred is None:
        return False
    p = _normalize_answer(pred)
    return any(p == _normalize_answer(g) for g in gold)


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
    for step_i in range(config.MAX_REASONING_STEPS):
        # Enumerate
        initial = enumerate_initial(kg, seeds, relation, year) if step_i == 0 else []
        followups = enumerate_followups(prev, year) if prev else []
        answers = enumerate_answers(prev, answer_type) if prev else []
        candidates = initial + followups + answers
        # dedupe by display
        seen, uniq = set(), []
        for a in candidates:
            if a.display in seen:
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
            question=question, qtype=qtype, answer_type=answer_type,
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

        result = execute(kg, chosen, prev)

        if chosen.op == "answer":
            trace.steps.append(StepLog(
                [a.display for a in uniq], chosen.display, chosen.op, f"answer={result}"))
            trace.final_answer = result
            trace.correct = _judge(result, gold, answer_type)
            return trace

        prev = result if isinstance(result, list) else []
        trace.steps.append(StepLog(
            [a.display for a in uniq], chosen.display, chosen.op, format_entset(prev)))

    # max steps exhausted — pick best from prev
    if prev:
        first = prev[0]
        trace.final_answer = first[2] if answer_type == "time" else first[0]
        trace.correct = _judge(trace.final_answer, gold, answer_type)
    return trace
