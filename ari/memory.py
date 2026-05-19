"""Historical memory + K-means clustering + abstract methodology induction.

Implements §3.4: store H_q, cluster by question embedding, derive M_C for each
cluster from correct & incorrect samples.
"""
from __future__ import annotations
import json
import math
import random
from dataclasses import asdict
from pathlib import Path

from . import config
from .agent import TraceLog
from .ollama_client import chat, embed
from .prompts import METHODOLOGY_SYSTEM, METHODOLOGY_TEMPLATE, FALLBACK_METHODOLOGY


# ---------- K-means ----------

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
    random.seed(seed)
    idx = random.sample(range(len(vecs)), min(k, len(vecs)))
    centroids = [vecs[i][:] for i in idx]
    labels = [0] * len(vecs)
    for _ in range(n_iter):
        new_labels = []
        for v in vecs:
            sims = [_cos(v, c) for c in centroids]
            new_labels.append(int(max(range(len(centroids)), key=sims.__getitem__)))
        if new_labels == labels:
            break
        labels = new_labels
        # recompute centroids
        for c in range(len(centroids)):
            members = [vecs[i] for i, l in enumerate(labels) if l == c]
            if members:
                centroids[c] = _mean(members)
    return centroids, labels


# ---------- memory persistence ----------

def trace_to_record(t: TraceLog) -> dict:
    return {
        "question": t.question, "qtype": t.qtype, "relation": t.relation,
        "year": t.year, "answer_type": t.answer_type, "gold": t.gold,
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
    """Cluster records, generate one methodology per cluster. Returns memory dict."""
    questions = [r["question"] for r in records]
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


def select_methodology(bank: dict, question: str) -> str:
    if not bank.get("clusters"):
        return FALLBACK_METHODOLOGY
    qv = embed([question])[0]
    best = max(bank["clusters"], key=lambda c: _cos(qv, c["centroid"]))
    return best["methodology"]


def load_bank(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
