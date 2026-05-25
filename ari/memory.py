"""Historical memory + K-means clustering + abstract methodology induction.

Implements §3.4: store H_q, cluster by question embedding, derive M_C for each
cluster from correct & incorrect samples.
"""
from __future__ import annotations
import json
import math
import random
import re
from dataclasses import asdict
from pathlib import Path

from . import config
from .agent import TraceLog
from .kg import get_kg
from .ollama_client import chat, embed
from .prompts import METHODOLOGY_SYSTEM, METHODOLOGY_TEMPLATE, FALLBACK_METHODOLOGY


# ---------- question templating (paper §3.4 — cluster by structure, not topic) ----------

_YEAR_TOK = re.compile(r"\b\d{4}(?:-\d{1,2}(?:-\d{1,2})?)?\b")


def clean_question(text: str, entity_labels: list[str] | None = None,
                   year: int | None = None) -> str:
    """Replace concrete entity labels and dates with placeholders so that
    K-means clusters by question STRUCTURE (e.g. before-last, after-first),
    not by topic. Mirrors ARI-QA `get_clean_question`."""
    out = text
    for lbl in sorted(entity_labels or [], key=len, reverse=True):
        if lbl and len(lbl) > 1:
            out = out.replace(lbl, "{entity}")
    out = _YEAR_TOK.sub("{time}", out)
    if year is not None:
        out = out.replace(str(year), "{time}")
    return out


def _resolve_entity_labels(qids: list[str]) -> list[str]:
    try:
        kg = get_kg()
    except Exception:
        return []
    return [kg.label(q) for q in qids if q]


# ---------- K-means ----------

def _norm(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _cos(a, b) -> float:
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return s / (na * nb)


def _mean(vs: list[list[float]]) -> list[float]:
    n = len(vs)
    d = len(vs[0])
    out = [0.0] * d
    for v in vs:
        for i, x in enumerate(v):
            out[i] += x
    return [x / n for x in out]


def kmeans(vecs: list[list[float]], k: int, n_iter: int = 25, seed: int = 0
           ) -> tuple[list[list[float]], list[int]]:
    """Cosine K-means. Vectors and centroids are L2-normalised so that the
    centroid stays comparable to data points under cosine similarity."""
    random.seed(seed)
    nvecs = [_norm(v) for v in vecs]
    idx = random.sample(range(len(nvecs)), min(k, len(nvecs)))
    centroids = [nvecs[i][:] for i in idx]
    labels = [0] * len(nvecs)
    for _ in range(n_iter):
        new_labels = []
        for v in nvecs:
            sims = [_cos(v, c) for c in centroids]
            new_labels.append(int(max(range(len(centroids)), key=sims.__getitem__)))
        if new_labels == labels:
            break
        labels = new_labels
        # recompute centroids and re-normalise
        for c in range(len(centroids)):
            members = [nvecs[i] for i, l in enumerate(labels) if l == c]
            if members:
                centroids[c] = _norm(_mean(members))
    return centroids, labels


# ---------- memory persistence ----------

def trace_to_record(t: TraceLog, entity_qids: list[str] | None = None) -> dict:
    ent_labels = _resolve_entity_labels(entity_qids or [])
    return {
        "question": t.question, "qtype": t.qtype, "relation": t.relation,
        "year": t.year, "answer_type": t.answer_type, "gold": t.gold,
        "entities": list(entity_qids or []),
        "entity_labels": ent_labels,
        "clean_question": clean_question(t.question, ent_labels, t.year),
        "final_answer": str(t.final_answer) if t.final_answer is not None else None,
        "correct": t.correct,
        "steps": [
            {"chosen": s.chosen, "op": s.op, "result": s.result_summary}
            for s in t.steps
        ],
    }


def trace_to_text(rec: dict) -> str:
    lines = [f"Q: {rec['question']}", f"Gold: {rec['gold']}",
             f"Final: {rec['final_answer']}  (correct={rec['correct']})"]
    for i, s in enumerate(rec["steps"]):
        lines.append(f"  step {i}: {s['chosen']} -> {s['result']}")
    return "\n".join(lines)


# ---------- methodology induction ----------

def induce_methodology(correct: list[dict], incorrect: list[dict],
                        max_each: int = 4) -> str:
    if not correct and not incorrect:
        return FALLBACK_METHODOLOGY
    c_blk = "\n\n".join(trace_to_text(r) for r in correct[:max_each]) or "(không có)"
    i_blk = "\n\n".join(trace_to_text(r) for r in incorrect[:max_each]) or "(không có)"
    prompt = METHODOLOGY_TEMPLATE.format(correct_examples=c_blk, incorrect_examples=i_blk)
    try:
        return chat(prompt, system=METHODOLOGY_SYSTEM).strip()
    except Exception:
        return FALLBACK_METHODOLOGY


# ---------- learning phase ----------

def build_memory_bank(records: list[dict], k: int = config.N_CLUSTERS,
                       out_path: Path | None = None) -> dict:
    """Cluster records, generate one methodology per cluster. Returns memory dict.

    Clustering is performed on the TEMPLATED question (entity/date replaced
    with placeholders) so that clusters group by reasoning structure, not
    topic — matching ARI-QA `History_Memory.fit_history_memory`.
    """
    questions = [r.get("clean_question") or r["question"] for r in records]
    vecs = embed(questions)
    centroids, labels = kmeans(vecs, k=min(k, len(records)))

    clusters: list[dict] = []
    for ci in range(len(centroids)):
        idxs = [i for i, l in enumerate(labels) if l == ci]
        if not idxs:
            continue
        cluster_records = [records[i] for i in idxs]
        correct = [r for r in cluster_records if r["correct"]]
        incorrect = [r for r in cluster_records if not r["correct"]]
        method = induce_methodology(correct, incorrect)
        clusters.append({
            "id": ci,
            "centroid": centroids[ci],
            "size": len(idxs),
            "qtypes": {qt: sum(1 for r in cluster_records if r["qtype"] == qt)
                       for qt in {r["qtype"] for r in cluster_records}},
            "methodology": method,
        })

    bank = {"clusters": clusters, "records": records}
    if out_path:
        out_path.write_text(json.dumps(bank, ensure_ascii=False, indent=2))
    return bank


def select_methodology(bank: dict, question, entity_qids: list[str] | None = None,
                        year: int | None = None) -> str:
    """`question` may be a raw string OR a question-dict (with `entities`/`year`).
    The query is templated the same way as during bank-building so cluster
    assignment is consistent."""
    if not bank.get("clusters"):
        return FALLBACK_METHODOLOGY
    if isinstance(question, dict):
        entity_qids = entity_qids or question.get("entities") or []
        year = year if year is not None else question.get("year")
        q_text = question.get("question", "")
    else:
        q_text = question
    ent_labels = _resolve_entity_labels(entity_qids or [])
    clean = clean_question(q_text, ent_labels, year)
    qv = _norm(embed([clean])[0])
    best = max(bank["clusters"], key=lambda c: _cos(qv, c["centroid"]))
    return best["methodology"]


def load_bank(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
