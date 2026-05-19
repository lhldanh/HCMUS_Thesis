"""Lightweight entity linker for cronqvn questions.

Finds qids whose label appears as a substring of the question. Resolves
ambiguity by preferring labels that match the question's `relation` context
(i.e. the qid actually participates in a fact with that relation).
"""
from __future__ import annotations
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
