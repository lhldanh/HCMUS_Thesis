"""Lightweight entity + relation linker for cronqvn questions.

Entity: finds qids whose label appears as a substring of the question.
Resolves ambiguity by preferring labels that match the question's `relation`
context (i.e. the qid actually participates in a fact with that relation).

Relation (câu hỏi mở, không có trường `relation`): xếp hạng mọi pid có mặt
trong KG theo cosine(nhúng(câu hỏi), nhúng(nhãn pid)), giữ top-K để giới hạn
không gian liệt kê hành động. Embedding nhãn pid là tĩnh nên cache theo process.
"""
from __future__ import annotations
import math
import re
import unicodedata
from .kg import KG


_WORD_RE = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def link_entities(kg: KG, question: str, relation: str | None = None,
                  max_results: int = 8) -> list[str]:
    """Return candidate qids ranked by label length (longest first), bounded."""
    qn = _norm(question)
    qtok = set(_WORD_RE.findall(qn))

    hits: list[tuple[int, str]] = []
    # Restrict search space: only qids that appear with the given relation, if known
    if relation and relation in kg.by_r:
        cand_qids = set()
        for f in kg.by_r[relation]:
            cand_qids.add(f.s_qid)
            cand_qids.add(f.o_qid)
    else:
        cand_qids = set(kg.qid2label.keys())

    for qid in cand_qids:
        lbl = kg.qid2label.get(qid)
        if not lbl or len(lbl) < 3:
            continue
        ln = _norm(lbl)
        if ln in qn:
            hits.append((len(ln), qid))
            continue
        # fallback: all label tokens present in question
        ltok = set(_WORD_RE.findall(ln))
        if len(ltok) >= 2 and ltok.issubset(qtok):
            hits.append((len(ln) - 1, qid))

    hits.sort(reverse=True)
    # dedupe preserving order
    seen, out = set(), []
    for _, qid in hits:
        if qid in seen:
            continue
        seen.add(qid)
        out.append(qid)
        if len(out) >= max_results:
            break
    return out


# ---------- relation linking (câu hỏi mở) ----------

def _cos(a: list[float], b: list[float]) -> float:
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return s / (na * nb)


# key = tên embed_fn → (pids đã sort, vectors). Nhãn pid tĩnh trong một
# process nên chỉ nhúng một lần; rebuild nếu tập pid của KG thay đổi.
_REL_EMB: dict[str, tuple[list[str], list[list[float]]]] = {}


def _relation_embeddings(kg: KG, embed_fn) -> tuple[list[str], list[list[float]]]:
    key = getattr(embed_fn, "__name__", repr(embed_fn))
    # chỉ xét pid thực sự có fact (kg.by_r) — pid chỉ có nhãn thì không tạo
    # được hành động nào nên bỏ qua
    pids = sorted(kg.by_r.keys())
    cached = _REL_EMB.get(key)
    if cached and cached[0] == pids:
        return cached
    vecs = embed_fn([kg.rlabel(p) for p in pids])
    _REL_EMB[key] = (pids, vecs)
    return _REL_EMB[key]


def link_relations(kg: KG, question: str, embed_fn,
                   top_k: int = 5) -> list[str]:
    """Return top-`top_k` relation pids ranked by cosine similarity between
    the question and each relation's (Vietnamese) label."""
    pids, vecs = _relation_embeddings(kg, embed_fn)
    if not pids:
        return []
    qv = embed_fn([question])[0]
    order = sorted(zip(pids, vecs), key=lambda pv: _cos(qv, pv[1]),
                   reverse=True)
    return [p for p, _ in order[:top_k]]
