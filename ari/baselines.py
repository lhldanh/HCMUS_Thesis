"""Baselines for comparison against ARI (báo cáo Ch5 §5.3).

Bốn baseline:
- ``llm-only`` : hỏi thẳng LLM, KHÔNG truy cập KG (đo tri thức tham số thuần).
- ``kg-rag``   : truy hồi 1-hop fact quanh thực thể seed của câu hỏi, nhồi vào
                 prompt, yêu cầu trả lời trực tiếp (KG-augmented RAG, một lượt).
- ``cot-kb``   : cùng ngữ cảnh KG nhưng prompt suy luận từng bước (Chain-of-Thought).
- ``react-kb`` : tác tử nhiều bước reason+act trên KB, KHÔNG có methodology trừu
                 tượng. Cài trong ``agent.run_question(react=True)`` (không ở đây)
                 vì dùng chung vòng lặp hành động với ARI.

Đáp án được chấm bằng cùng hàm ``agent._judge`` như ARI nên metric đồng nhất
giữa mọi phương pháp.
"""
from __future__ import annotations
import re

from .kg import KG, Fact
from .ollama_client import chat
from .ner import link_entities
from .agent import _judge
from .prompts import (
    LLM_ONLY_SYSTEM, LLM_ONLY_TEMPLATE,
    KG_RAG_SYSTEM, KG_RAG_TEMPLATE,
    COT_KB_SYSTEM, COT_KB_TEMPLATE,
)


SINGLE_SHOT_METHODS = ("llm-only", "kg-rag", "cot-kb")

_ANSWER_RE = re.compile(r"(?:đáp\s*án|answer)\s*[:：]\s*(.+)", re.IGNORECASE)


def parse_answer(reply: str) -> str:
    """Trích đáp án sau 'Đáp án:' / 'Answer:' (ưu tiên dòng cuối khớp). Nếu không
    có, lấy dòng không rỗng cuối cùng làm fallback."""
    if not reply:
        return ""
    for line in reversed(reply.strip().splitlines()):
        m = _ANSWER_RE.search(line)
        if m:
            return m.group(1).strip().strip('".*` ')
    lines = [l.strip() for l in reply.strip().splitlines() if l.strip()]
    return lines[-1].strip('".*` ') if lines else ""


def _fmt_time(f: Fact) -> str:
    if f.start is not None and f.end is not None and f.start != f.end:
        return f" ({f.start}–{f.end})"
    y = f.start if f.start is not None else f.end
    return f" ({y})" if y is not None else ""


def serialize_context(kg: KG, seeds: list[str], relation: str | None = None,
                      max_facts: int = 60) -> str:
    """Tuần tự hóa 1-hop subgraph của các seed thành text cho KG-RAG / CoT-KB.

    Ưu tiên fact có cùng quan hệ với câu hỏi (nếu biết), rồi sắp theo thời gian.
    Cắt còn ``max_facts`` để không vượt ngữ cảnh LLM.
    """
    facts: list[Fact] = []
    for qid in seeds:
        facts.extend(kg.one_hop(qid))

    def keyf(f: Fact):
        same_rel = 0 if (relation and f.relation == relation) else 1
        yr = f.start if f.start is not None else (f.end if f.end is not None else 9999)
        return (same_rel, yr)

    lines: list[str] = []
    seen: set = set()
    for f in sorted(facts, key=keyf):
        key = (f.s_qid, f.relation, f.o_qid, f.start, f.end)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {f.s_label} — {f.r_label} — {f.o_label}{_fmt_time(f)}")
        if len(lines) >= max_facts:
            break
    return "\n".join(lines) if lines else "(không có dữ kiện liên quan)"


def run_baseline(kg: KG, q: dict, method: str, chat_fn=None) -> dict:
    """Chạy một baseline single-shot trên một câu hỏi, trả về record thống nhất."""
    chat_fn = chat_fn or (lambda p, system=None: chat(p, system=system))
    question = q["question"]
    answer_type = q.get("answer_type", "entity")
    gold = q.get("answers", [])
    relation = q.get("relation")

    seeds = list(q.get("entities") or [])
    if not seeds and method != "llm-only":
        seeds = link_entities(kg, question, relation=relation, max_results=6)

    rec = {
        "question": question, "qtype": q.get("qtype"),
        "answer_type": answer_type, "qlabel": q.get("qlabel"),
        "relation": relation, "gold": gold,
        "method": method, "final_answer": None, "correct": False, "reply": "",
    }
    try:
        if method == "llm-only":
            prompt = LLM_ONLY_TEMPLATE.format(question=question)
            reply = chat_fn(prompt, system=LLM_ONLY_SYSTEM)
        elif method == "kg-rag":
            ctx = serialize_context(kg, seeds, relation)
            prompt = KG_RAG_TEMPLATE.format(context=ctx, question=question)
            reply = chat_fn(prompt, system=KG_RAG_SYSTEM)
        elif method == "cot-kb":
            ctx = serialize_context(kg, seeds, relation)
            prompt = COT_KB_TEMPLATE.format(context=ctx, question=question)
            reply = chat_fn(prompt, system=COT_KB_SYSTEM)
        else:
            raise ValueError(f"baseline không hỗ trợ: {method}")
    except Exception as e:  # một câu lỗi LLM không được giết cả run
        rec["final_answer"] = f"(LLM error: {type(e).__name__}: {e})"
        return rec

    pred = parse_answer(reply)
    rec["reply"] = reply
    rec["final_answer"] = pred
    rec["correct"] = _judge(kg, pred, gold, answer_type)
    return rec
