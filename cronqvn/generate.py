"""Phase 3: Sinh câu hỏi tiếng Việt + đáp án từ cache KG.

Cache đã được build_kg.py lọc theo tkbc (rare relation/entity).
Phase này chỉ filter ở mức câu hỏi:
  - MIN_LABEL_LEN:      label quá ngắn ("PM", "CEO")
  - NUMERIC_RE:         label toàn số/ID
  - NO_SELF_REF:        s_qid != o_qid
  - MAX_ANSWERS:        bỏ câu có >N đáp án
  - MIN_BEFORE_AFTER_GAP: before_after cần cách ≥ N năm
  - NO_ANSWER_LEAK:     đáp án không xuất hiện trong câu
  - DEDUP:              câu trùng

CẤU TRÚC TEMPLATES (v2):
  - simple_time:  {"start": [...], "end": [...], "range": [...]}
  - simple_entity: [...]
  - before_after: {"before": [...], "after": [...]}  (anchor = (R,o) nếu chứa
                  {time} hoặc {head} đóng vai trò mốc; ngược lại anchor = (s,R))
  - first_last:   {"first": [...], "last": [...]}   (answer = o_label)
  - time_join:    [...]                              (anchor = fact của {head})
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from config import (BAD_O_LABELS, CACHE_DIR, FACTS_DIR, MAX_ANSWERS,
                    MIN_BEFORE_AFTER_GAP, MIN_LABEL_LEN, OUT_DIR,
                    QTYPE_DISTRIBUTION, RELATIONS,
                    SIMPLE_ENTITY_REQUIRE_CLOSED, TARGET_QUESTIONS,
                    TIME_JOIN_MIN_OVERLAP)
from templates import TEMPLATES


NUMERIC_RE = re.compile(r"^[\d\s\-\.:/]+$")


def load_qid_labels() -> dict[str, str]:
    """qid -> label tiếng Việt từ qid_labels.json (đã được translate)."""
    path = Path(FACTS_DIR) / "qid_labels.json"
    raw = json.loads(path.read_text())
    return {qid: info["label"] for qid, info in raw.items()
            if info.get("label")}


def _bad_label(lab: str) -> bool:
    if not lab or len(lab) < MIN_LABEL_LEN:
        return True
    if NUMERIC_RE.match(lab):
        return True
    return False


def load_kg() -> list[dict]:
    """Load fact đã được build_kg.py lọc sẵn (tkbc-style).

    Label được override từ qid_labels.json (đã translate sang tiếng Việt)
    thay vì dùng s_label/o_label gốc trong .jsonl (có thể còn tiếng Anh).
    """
    qid_labels = load_qid_labels()
    facts: list[dict] = []
    for pid in RELATIONS:
        path = Path(CACHE_DIR) / f"{pid}.jsonl"
        if not path.exists():
            continue
        with path.open() as f:
            for line in f:
                fact = json.loads(line)
                if fact["s_qid"] == fact["o_qid"]:
                    continue
                if fact.get("start") is None:
                    continue
                s_lab = qid_labels.get(fact["s_qid"])
                o_lab = qid_labels.get(fact["o_qid"])
                if not s_lab or not o_lab:
                    continue
                fact["s_label"] = s_lab
                fact["o_label"] = o_lab
                if _bad_label(s_lab) or _bad_label(o_lab):
                    continue
                bad = BAD_O_LABELS.get(pid)
                if bad and o_lab in bad:
                    continue
                facts.append(fact)
    return facts


class KG:
    def __init__(self, facts: list[dict]):
        self.facts = facts
        self.by_ro: dict[tuple, list[dict]] = defaultdict(list)
        self.by_rs: dict[tuple, list[dict]] = defaultdict(list)
        self.by_ry: dict[tuple, list[dict]] = defaultdict(list)
        self.by_rel: dict[str, list[dict]] = defaultdict(list)
        for f in facts:
            self.by_ro[(f["relation"], f["o_qid"])].append(f)
            self.by_rs[(f["relation"], f["s_qid"])].append(f)
            self.by_rel[f["relation"]].append(f)
            for y in range(f["start"], (f["end"] or f["start"]) + 1):
                self.by_ry[(f["relation"], y)].append(f)
        self.relations = sorted(self.by_rel.keys())

    def active_at(self, rel: str, o_qid: str, year: int) -> list[dict]:
        return [f for f in self.by_ro[(rel, o_qid)]
                if f["start"] <= year <= (f["end"] or f["start"])]


# ====================================================================
# Helpers
# ====================================================================

def _fmt(tmpl: str, *, head="", tail="", time="") -> str:
    """Format an chỉ với các key chuẩn."""
    return tmpl.format(head=head, tail=tail, time=time)


# Cụm cho biết {head} đang đóng vai trò mốc tham chiếu (không phải subject).
# Nếu xuất hiện → o-anchor (cùng o, khác s, answer = s_label).
_O_ANCHOR_PHRASES = (
    "trước {head}", "sau {head}",
    "trước khi {head}", "sau khi {head}",
    "thời kỳ {head}",
    "tiền nhiệm của {head}", "kế nhiệm {head}", "kế nhiệm của {head}",
    "{head} nắm giữ", "{head} nhận chức",
    "thay {head}",
)


def _is_o_anchor(tmpl: str) -> bool:
    """True nếu template anchor theo (R, o) — cùng object, khác subject."""
    if "{time}" in tmpl:
        return True
    return any(p in tmpl for p in _O_ANCHOR_PHRASES)


# ====================================================================
# Generators
# ====================================================================

def gen_simple_time(kg: KG, pid: str, rng: random.Random):
    cfg = TEMPLATES[pid]["simple_time"]  # dict
    pool = kg.by_rel.get(pid, [])
    if not pool: return None
    f = rng.choice(pool)
    available = list(cfg.keys())
    # Open-ended fact (end=None) chỉ trả được "start"
    if f["end"] is None:
        available = [s for s in available if s == "start"]
    if not available: return None
    subtype = rng.choice(available)
    tmpl = rng.choice(cfg[subtype])
    q = _fmt(tmpl, head=f["s_label"], tail=f["o_label"])
    if subtype == "start":
        answers = [str(f["start"])]
    elif subtype == "end":
        answers = [str(f["end"])]
    else:  # range
        answers = [str(f["start"]), str(f["end"])]
    return {"question": q, "template": tmpl, "answers": answers, "answer_type": "time",
            "qtype": "simple_time", "subtype": subtype,
            "time_level": "year", "relation": pid,
            "entities": [f["s_qid"], f["o_qid"]]}


def gen_simple_entity(kg: KG, pid: str, rng: random.Random):
    cfg = TEMPLATES[pid]["simple_entity"]  # list
    require_closed = pid in SIMPLE_ENTITY_REQUIRE_CLOSED
    keys = [k for k in kg.by_ry if k[0] == pid]
    if not keys: return None
    _, year = rng.choice(keys)
    fs = kg.by_ry[(pid, year)]
    if require_closed:
        fs = [x for x in fs if x["end"] is not None]
    if not fs: return None
    f = rng.choice(fs)
    tmpl = rng.choice(cfg)
    q = _fmt(tmpl, head=f["s_label"], tail=f["o_label"], time=year)
    cohort = kg.active_at(pid, f["o_qid"], year)
    if require_closed:
        cohort = [x for x in cohort if x["end"] is not None]
    answers = sorted({x["s_label"] for x in cohort})
    if not answers: return None
    return {"question": q, "template": tmpl, "answers": answers, "answer_type": "entity",
            "qtype": "simple_entity", "time_level": "year",
            "relation": pid, "year": year,
            "entities": [f["o_qid"]]}


def gen_before_after(kg: KG, pid: str, rng: random.Random):
    cfg = TEMPLATES[pid]["before_after"]  # dict {before, after}
    subtype = rng.choice(list(cfg.keys()))
    tmpl = rng.choice(cfg[subtype])
    o_anchor = _is_o_anchor(tmpl)

    if o_anchor:
        # Cùng o, khác s → answer = s_label
        candidates = [(p, o) for (p, o), fs in kg.by_ro.items()
                      if p == pid and len({f["s_qid"] for f in fs}) >= 2]
        if not candidates: return None
        _, o_qid = rng.choice(candidates)
        fs_sorted = sorted(kg.by_ro[(pid, o_qid)], key=lambda x: x["start"])
        seen = set(); picks = []
        for f in fs_sorted:
            if f["s_qid"] not in seen:
                seen.add(f["s_qid"]); picks.append(f)
        if len(picks) < 2: return None
        idx = rng.randint(1, len(picks) - 1)
        curr, prev = picks[idx], picks[idx - 1]
        if curr["start"] - prev["start"] < MIN_BEFORE_AFTER_GAP:
            return None
        if subtype == "before":
            head_l, tail_l = curr["s_label"], curr["o_label"]
            time_v = curr["start"]
            answers = [prev["s_label"]]
        else:
            head_l, tail_l = prev["s_label"], prev["o_label"]
            time_v = prev["end"] or prev["start"]
            answers = [curr["s_label"]]
    else:
        # Cùng s, khác o → answer = o_label (career path)
        candidates = [(p, s) for (p, s), fs in kg.by_rs.items()
                      if p == pid and len({f["o_qid"] for f in fs}) >= 2]
        if not candidates: return None
        _, s_qid = rng.choice(candidates)
        fs_sorted = sorted(kg.by_rs[(pid, s_qid)], key=lambda x: x["start"])
        seen = set(); picks = []
        for f in fs_sorted:
            if f["o_qid"] not in seen:
                seen.add(f["o_qid"]); picks.append(f)
        if len(picks) < 2: return None
        idx = rng.randint(1, len(picks) - 1)
        curr, prev = picks[idx], picks[idx - 1]
        if curr["start"] - prev["start"] < MIN_BEFORE_AFTER_GAP:
            return None
        if prev["o_label"] == curr["o_label"]:
            return None
        if subtype == "before":
            head_l, tail_l = curr["s_label"], curr["o_label"]
            time_v = curr["start"]
            answers = [prev["o_label"]]
        else:
            head_l, tail_l = prev["s_label"], prev["o_label"]
            time_v = prev["end"] or prev["start"]
            answers = [curr["o_label"]]

    q = _fmt(tmpl, head=head_l, tail=tail_l, time=time_v)
    # Resolve qid của head/tail từ fact gốc (prev hoặc curr tuỳ subtype)
    anchor_fact = curr if subtype == "before" else prev
    return {"question": q, "template": tmpl, "answers": answers, "answer_type": "entity",
            "qtype": "before_after", "subtype": subtype,
            "anchor": "o" if o_anchor else "s",
            "time_level": "year", "relation": pid,
            "entities": [anchor_fact["s_qid"], anchor_fact["o_qid"]]}


def gen_first_last(kg: KG, pid: str, rng: random.Random):
    cfg = TEMPLATES[pid]["first_last"]  # dict {first, last}
    pool = [(p, s) for (p, s), fs in kg.by_rs.items()
            if p == pid and len({f["o_qid"] for f in fs}) >= 2]
    if not pool: return None
    subtype = rng.choice(list(cfg.keys()))
    tmpl = rng.choice(cfg[subtype])
    _, s_qid = rng.choice(pool)
    fs_sorted = sorted(kg.by_rs[(pid, s_qid)], key=lambda x: x["start"])
    target = fs_sorted[0] if subtype == "first" else fs_sorted[-1]
    q = _fmt(tmpl, head=target["s_label"], tail=target["o_label"])
    answers = [target["o_label"]]
    return {"question": q, "template": tmpl, "answers": answers, "answer_type": "entity",
            "qtype": "first_last", "subtype": subtype,
            "time_level": "year", "relation": pid,
            "entities": [target["s_qid"]]}


# Mặc định time_join yêu cầu cùng o (cùng đội/đảng/trường…).
# P26 (spouse) chỉ yêu cầu trùng thời gian, không cần cùng vợ/chồng.
TIME_JOIN_SAME_O = {"P26": False}


def gen_time_join(kg: KG, pid: str, rng: random.Random):
    cfg = TEMPLATES[pid]["time_join"]  # list
    pool = kg.by_rel.get(pid, [])
    if len(pool) < 2: return None
    same_o = TIME_JOIN_SAME_O.get(pid, True)
    for _ in range(30):
        f1 = rng.choice(pool)
        s1, e1 = f1["start"], f1["end"] or f1["start"]
        if same_o:
            cohort_src = kg.by_ro[(pid, f1["o_qid"])]
        else:
            cohort_src = pool
        # Lọc theo overlap toàn period với f1 (không chỉ 1 năm)
        cohort = [x for x in cohort_src
                  if x["s_qid"] != f1["s_qid"]
                  and min(x["end"] or x["start"], e1) - max(x["start"], s1) + 1
                      >= TIME_JOIN_MIN_OVERLAP]
        if not cohort: continue
        tmpl = rng.choice(cfg)
        q = _fmt(tmpl, head=f1["s_label"], tail=f1["o_label"], time=s1)
        answers = sorted({x["s_label"] for x in cohort})
        return {"question": q, "template": tmpl, "answers": answers, "answer_type": "entity",
                "qtype": "time_join", "time_level": "year",
                "relation": pid, "year": s1,
                "entities": [f1["s_qid"], f1["o_qid"]]}
    return None


GENERATORS = {
    "simple_entity": gen_simple_entity,
    "simple_time":   gen_simple_time,
    "before_after":  gen_before_after,
    "first_last":    gen_first_last,
    "time_join":     gen_time_join,
}


def _valid_question(item: dict) -> bool:
    if len(item["answers"]) > MAX_ANSWERS:
        return False
    q_lower = item["question"].lower()
    for ans in item["answers"]:
        if ans.lower() in q_lower:
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", "-n", type=int, default=TARGET_QUESTIONS,
                    help=f"Tổng số câu cần sinh (mặc định {TARGET_QUESTIONS})")
    ap.add_argument("--out", type=str, default=None,
                    help="Đường dẫn file output (mặc định OUT_DIR/questions.json)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    target = args.limit

    rng = random.Random(args.seed)
    print(f"[load] KG từ cache + filter (target={target:,}):")
    facts = load_kg()
    if not facts:
        print("Không có fact. Chạy build_kg.py trước.")
        return
    kg = KG(facts)
    # Chỉ dùng relation có template
    active = [r for r in kg.relations if r in TEMPLATES]
    if not active:
        print("Không có relation nào có template.")
        return
    print(f"\nRelations active: {len(active)}: {active}")

    questions: list[dict] = []
    seen_q: set[str] = set()
    quid = 0

    for qtype, ratio in QTYPE_DISTRIBUTION.items():
        n_target = int(target * ratio)
        pbar = tqdm(total=n_target, desc=f"  {qtype:14s}")
        attempts = 0
        made = 0
        while made < n_target and attempts < n_target * 30:
            attempts += 1
            pid = rng.choice(active)
            # Skip nếu pid không hỗ trợ qtype này (vd P166 không có "end")
            if qtype not in TEMPLATES[pid]:
                continue
            item = GENERATORS[qtype](kg, pid, rng)
            if item is None or not _valid_question(item):
                continue
            if item["question"] in seen_q:
                continue
            seen_q.add(item["question"])
            quid += 1
            item["quid"] = quid
            item["qlabel"] = "Single" if len(item["answers"]) == 1 else "Multiple"
            questions.append(item)
            made += 1
            pbar.update(1)
        pbar.close()
        if made < n_target:
            print(f"    [warn] {qtype}: {made:,}/{n_target:,}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path(OUT_DIR); out_dir.mkdir(exist_ok=True)
        out_path = out_dir / "questions.json"
    out_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2))
    print(f"\n[done] {len(questions):,} câu -> {out_path}")


if __name__ == "__main__":
    main()
