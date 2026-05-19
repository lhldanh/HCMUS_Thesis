"""Temporal KG loader for cronqvn facts.

Each fact is a dataclass with (s_qid, s_label, o_qid, o_label, start, end, relation, r_label).
Indexes by subject, object, and relation. Labels are Vietnamese where available.
"""
from __future__ import annotations
import json
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from . import config


@dataclass(frozen=True)
class Fact:
    s_qid: str
    s_label: str
    o_qid: str
    o_label: str
    start: int | None
    end: int | None
    relation: str
    r_label: str

    def years(self) -> list[int]:
        if self.start is None and self.end is None:
            return []
        a = self.start if self.start is not None else self.end
        b = self.end if self.end is not None else self.start
        if a is None or b is None:
            return []
        return list(range(min(a, b), max(a, b) + 1))


class KG:
    def __init__(self) -> None:
        self.facts: list[Fact] = []
        self.by_s: dict[str, list[Fact]] = defaultdict(list)
        self.by_o: dict[str, list[Fact]] = defaultdict(list)
        self.by_r: dict[str, list[Fact]] = defaultdict(list)
        self.qid2label: dict[str, str] = {}
        self.label2qids: dict[str, list[str]] = defaultdict(list)
        self.pid2label: dict[str, str] = {}

    def load(self) -> "KG":
        # Relation labels: prefer .vi, then base
        for fname in ("pid_labels.json", "pid_labels.vi.json"):
            fp = config.FACTS_DIR / fname
            if not fp.exists():
                continue
            with open(fp, encoding="utf-8") as f:
                for pid, meta in json.load(f).items():
                    lbl = meta.get("label") or meta.get("src_label") or pid
                    self.pid2label[pid] = lbl  # later loader (.vi) overrides
        # Entity labels: base first (broader), vi overrides
        for fname in ("qid_labels.json", "qid_labels.vi.json"):
            fp = config.FACTS_DIR / fname
            if not fp.exists():
                continue
            with open(fp, encoding="utf-8") as f:
                for qid, meta in json.load(f).items():
                    lbl = meta.get("label") or meta.get("src_label") or qid
                    self.qid2label[qid] = lbl
        # Facts
        for fp in sorted(config.FACTS_DIR.glob("P*.jsonl")):
            with open(fp, encoding="utf-8") as f:
                for line in f:
                    d = json.loads(line)
                    fact = Fact(
                        s_qid=d["s_qid"], s_label=d["s_label"],
                        o_qid=d["o_qid"], o_label=d["o_label"],
                        start=d.get("start"), end=d.get("end"),
                        relation=d["relation"],
                        r_label=d.get("r_label") or self.pid2label.get(d["relation"], d["relation"]),
                    )
                    self.facts.append(fact)
                    self.by_s[fact.s_qid].append(fact)
                    self.by_o[fact.o_qid].append(fact)
                    self.by_r[fact.relation].append(fact)
                    # remember labels seen on facts
                    self.qid2label.setdefault(fact.s_qid, fact.s_label)
                    self.qid2label.setdefault(fact.o_qid, fact.o_label)
                    self.pid2label.setdefault(fact.relation, fact.r_label)
        for qid, lbl in self.qid2label.items():
            self.label2qids[lbl.lower()].append(qid)
        return self

    def label(self, qid: str) -> str:
        return self.qid2label.get(qid, qid)

    def rlabel(self, pid: str) -> str:
        return self.pid2label.get(pid, pid)

    @lru_cache(maxsize=4096)
    def one_hop(self, qid: str) -> tuple[Fact, ...]:
        """1-hop subgraph (subject or object side)."""
        return tuple(self.by_s.get(qid, []) + self.by_o.get(qid, []))


_singleton: KG | None = None


def get_kg() -> KG:
    global _singleton
    if _singleton is None:
        _singleton = KG().load()
    return _singleton
