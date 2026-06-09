"""Historical memory + K-means clustering + abstract methodology induction.

Implements §3.4: store H_q, cluster by question embedding, derive M_C for each
cluster from correct & incorrect samples.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

from . import config
from .agent import TraceLog
from .kg import get_kg
from .ollama_client import chat, embed
from .prompts import METHODOLOGY_SYSTEM, METHODOLOGY_TEMPLATE, FALLBACK_METHODOLOGY


# ---------- question templating (paper §3.4 — cluster by structure, not topic) ----------

_YEAR_TOK = re.compile(r"\b\d{4}(?:-\d{1,2}(?:-\d{1,2})?)?\b")


def clean_question(text: str, entity_labels: list[str] | None = None,
                   year: int | None = None,
                   relation_labels: list[str] | None = None) -> str:
    """Replace concrete entity labels, relation labels, and dates with
    placeholders so that K-means clusters by question STRUCTURE (e.g.
    before-last, after-first), not by topic.

    Extends paper's `get_clean_question` — paper chỉ thay head/tail entities
    và date. Trên cronqvn (tiếng Việt), relation label cũng dễ trùng với
    noun trong câu (vd "thủ tướng", "đảng phái") → cần thay luôn để cluster
    không bị gom theo topic.
    """
    out = text
    # Thay relation label TRƯỚC entity (relation thường ngắn hơn, ưu tiên dài
    # trước để tránh substring match nhầm)
    for lbl in sorted(relation_labels or [], key=len, reverse=True):
        if lbl and len(lbl) > 1:
            out = out.replace(lbl, "{relation}")
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


def _resolve_relation_label(pid: str | None) -> str | None:
    if not pid:
        return None
    try:
        kg = get_kg()
    except Exception:
        return None
    return kg.rlabel(pid)


# ---------- K-means (paper-faithful: sklearn Euclidean, k-means++, n_init=10) ----------

try:
    from sklearn.cluster import KMeans as _SKKMeans  # type: ignore
    import numpy as _np  # type: ignore
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


def _euclidean_sq(a, b) -> float:
    return sum((x - y) * (x - y) for x, y in zip(a, b))


def kmeans(vecs: list[list[float]], k: int, n_iter: int = 300, seed: int = 0
           ) -> tuple[list[list[float]], list[int]]:
    """KMeans khớp paper: Euclidean, k-means++ init, n_init=10.

    Paper code: `KMeans(n_clusters=10, n_init=10)` ([multitq.py:76](ARI-QA/MultiTQ/multitq.py#L76)).
    """
    if not _HAS_SKLEARN:
        raise RuntimeError(
            "scikit-learn không có sẵn. Cài: `pip install scikit-learn numpy`. "
            "Paper dùng sklearn KMeans để cluster, không thay thế bằng cosine viết tay."
        )
    arr = _np.asarray(vecs, dtype=_np.float64)
    km = _SKKMeans(n_clusters=min(k, len(arr)), n_init=10,
                    random_state=seed, max_iter=n_iter)
    labels = km.fit_predict(arr)
    return km.cluster_centers_.tolist(), labels.tolist()


# ---------- memory persistence ----------

def trace_to_record(t: TraceLog, entity_qids: list[str] | None = None) -> dict:
    ent_labels = _resolve_entity_labels(entity_qids or [])
    rel_label = _resolve_relation_label(t.relation)
    rel_labels = [rel_label] if rel_label else []
    return {
        "question": t.question, "qtype": t.qtype, "relation": t.relation,
        "year": t.year, "answer_type": t.answer_type, "gold": t.gold,
        "entities": list(entity_qids or []),
        "entity_labels": ent_labels,
        "relation_label": rel_label,
        "clean_question": clean_question(t.question, ent_labels, t.year, rel_labels),
        "final_answer": str(t.final_answer) if t.final_answer is not None else None,
        "correct": t.correct,
        "steps": [
            {
                "chosen": s.chosen,
                "op": s.op,
                "result": s.result_summary,
                "reply": s.reply,
                "step_entities": [list(e) for e in s.entities],
            }
            for s in t.steps
        ],
    }


def _process_entities(ents: list) -> str:
    """Paper-style entity-list formatter: sort by time, keep first 2 + last 1
    with an ellipsis when length > 3. Mirrors ARI-QA `process_entities`."""
    if not ents:
        return "entities = []"
    # Each entry: (label, qid, year). Treat year=None as -inf for sorting stability.
    sorted_by_t = sorted(ents, key=lambda e: (e[2] is None, e[2] if e[2] is not None else 0))
    if len(sorted_by_t) > 3:
        head = sorted_by_t[:2]
        tail = sorted_by_t[-1:]
        items = [(e[0], e[2]) for e in head] + ["..."] + [(e[0], e[2]) for e in tail]
    else:
        items = [(e[0], e[2]) for e in sorted_by_t]
    return "entities = " + str(items)


def trace_to_text(rec: dict) -> str:
    """Paper-style history text passed to GPT-4o for methodology induction
    (mirrors ARI-QA `History_Memory.get_history_text`)."""
    lines = [f"Question: {rec['question']}"]
    for i, s in enumerate(rec["steps"]):
        reply = s.get("reply") or s["chosen"]
        lines.append(f"LLM Action {i}: {reply}")
        ents = s.get("step_entities") or []
        if ents:
            lines.append(f"Retrieval {i}: {_process_entities(ents)}")
        else:
            # answer step or noop — fall back to raw result string
            lines.append(f"Retrieval {i}: {s.get('result', '')}")
    if rec.get("correct"):
        lines.append("Correct!")
    else:
        lines.append(f"Wrong! The answer is {rec['gold']}")
    return "\n".join(lines)


# ---------- methodology induction ----------

def induce_methodology(correct: list[dict], incorrect: list[dict],
                        max_each: int = 3, chat_fn=None) -> str:
    """Induce a cluster-level methodology. `chat_fn(prompt, system=...)` defaults
    to local Ollama; pass `openai_chat` to match the paper's GPT-4o."""
    if not correct and not incorrect:
        return FALLBACK_METHODOLOGY
    c_blk = "\n\n".join(trace_to_text(r) for r in correct[:max_each]) or "(không có)"
    i_blk = "\n\n".join(trace_to_text(r) for r in incorrect[:max_each]) or "(không có)"
    prompt = METHODOLOGY_TEMPLATE.format(correct_examples=c_blk, incorrect_examples=i_blk)
    fn = chat_fn or chat
    try:
        return fn(prompt, system=METHODOLOGY_SYSTEM).strip()
    except Exception:
        return FALLBACK_METHODOLOGY


# ---------- learning phase ----------

def build_memory_bank(records: list[dict], k: int = config.N_CLUSTERS,
                       out_path: Path | None = None, chat_fn=None,
                       embed_fn=None) -> dict:
    """Cluster records, generate one methodology per cluster. Returns memory dict.

    Clustering is performed on the TEMPLATED question (entity/date replaced
    with placeholders) so that clusters group by reasoning structure, not
    topic — matching ARI-QA `History_Memory.fit_history_memory`.
    """
    # Recompute clean_question on-the-fly để dùng logic mới (thay relation
    # label) mà không cần re-run 200 câu inference.
    def _recompute_clean(r):
        ent_labels = r.get("entity_labels") or _resolve_entity_labels(r.get("entities") or [])
        rel_label = r.get("relation_label") or _resolve_relation_label(r.get("relation"))
        rel_labels = [rel_label] if rel_label else []
        return clean_question(r["question"], ent_labels, r.get("year"), rel_labels)

    questions = [_recompute_clean(r) for r in records]
    # Cache lại clean_question mới vào record (để debug)
    for r, cq in zip(records, questions):
        r["clean_question"] = cq
    emb = embed_fn or embed
    vecs = emb(questions)
    centroids, labels = kmeans(vecs, k=min(k, len(records)))

    clusters: list[dict] = []
    for ci in range(len(centroids)):
        idxs = [i for i, l in enumerate(labels) if l == ci]
        if not idxs:
            continue
        cluster_records = [records[i] for i in idxs]
        correct = [r for r in cluster_records if r["correct"]]
        incorrect = [r for r in cluster_records if not r["correct"]]
        method = induce_methodology(correct, incorrect, chat_fn=chat_fn)
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
        out_path.write_text(json.dumps(bank, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return bank


def select_methodology(bank: dict, question, entity_qids: list[str] | None = None,
                        year: int | None = None,
                        relation: str | None = None,
                        embed_fn=None) -> str:
    """`question` may be a raw string OR a question-dict (with `entities`/`year`/`relation`).
    The query is templated the same way as during bank-building so cluster
    assignment is consistent."""
    if not bank.get("clusters"):
        return FALLBACK_METHODOLOGY
    if isinstance(question, dict):
        entity_qids = entity_qids or question.get("entities") or []
        year = year if year is not None else question.get("year")
        relation = relation or question.get("relation")
        q_text = question.get("question", "")
    else:
        q_text = question
    ent_labels = _resolve_entity_labels(entity_qids or [])
    rel_label = _resolve_relation_label(relation)
    rel_labels = [rel_label] if rel_label else []
    clean = clean_question(q_text, ent_labels, year, rel_labels)
    embed_fn_local = embed_fn or embed
    qv = embed_fn_local([clean])[0]
    # Paper dùng `kmeans.predict([vec])` = Euclidean nearest centroid.
    best = min(bank["clusters"],
                key=lambda c: _euclidean_sq(qv, c["centroid"]))
    return best["methodology"]


def load_bank(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
