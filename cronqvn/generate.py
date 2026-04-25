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
"""
from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from config import (CACHE_DIR, MAX_ANSWERS, MIN_BEFORE_AFTER_GAP,
                    MIN_LABEL_LEN, OUT_DIR, QTYPE_DISTRIBUTION, RELATIONS,
                    TARGET_QUESTIONS)
from templates import TEMPLATES


NUMERIC_RE = re.compile(r"^[\d\s\-\.:/]+$")


def _bad_label(lab: str) -> bool:
    if not lab or len(lab) < MIN_LABEL_LEN:
        return True
    if NUMERIC_RE.match(lab):
        return True
    return False


def load_kg() -> list[dict]:
    """Load fact đã được build_kg.py lọc sẵn (tkbc-style).
    Phase này chỉ skip self-ref và label xấu."""
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
                if _bad_label(fact["s_label"]) or _bad_label(fact["o_label"]):
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
# Generators (dùng TEMPLATES[pid][qtype] đã render từ templates.py)
# ====================================================================

def _verb(pid: str) -> str:
    return RELATIONS[pid]["verb"]


def gen_simple_entity(kg: KG, pid: str, rng: random.Random):
    keys = [k for k in kg.by_ry if k[0] == pid]
    if not keys: return None
    _, year = rng.choice(keys)
    fs = kg.by_ry[(pid, year)]
    if not fs: return None
    f = rng.choice(fs)
    tmpl = rng.choice(TEMPLATES[pid]["simple_entity"])
    q = tmpl.format(s=f["s_label"], o=f["o_label"], year=year)
    answers = sorted({x["s_label"] for x in kg.active_at(pid, f["o_qid"], year)})
    if not answers: return None
    return {"question": q, "answers": answers, "answer_type": "entity",
            "qtype": "simple_entity", "time_level": "year",
            "relation": pid, "year": year}


def gen_simple_time(kg: KG, pid: str, rng: random.Random):
    pool = kg.by_rel.get(pid, [])
    if not pool: return None
    f = rng.choice(pool)
    tmpl = rng.choice(TEMPLATES[pid]["simple_time"])
    q = tmpl.format(s=f["s_label"], o=f["o_label"], year=f["start"])
    answers = sorted({str(x["start"])
                      for x in kg.by_rs[(pid, f["s_qid"])]
                      if x["o_qid"] == f["o_qid"]})
    return {"question": q, "answers": answers, "answer_type": "time",
            "qtype": "simple_time", "time_level": "year",
            "relation": pid}


def gen_before_after(kg: KG, pid: str, rng: random.Random):
    candidates = [(p, o) for (p, o), fs in kg.by_ro.items()
                  if p == pid and len({f["s_qid"] for f in fs}) >= 2]
    if not candidates: return None
    _, o_qid = rng.choice(candidates)
    fs = sorted(kg.by_ro[(pid, o_qid)], key=lambda x: x["start"])
    seen = set(); subjects = []
    for f in fs:
        if f["s_qid"] not in seen:
            seen.add(f["s_qid"]); subjects.append(f)
    if len(subjects) < 2: return None
    idx = rng.randint(1, len(subjects) - 1)
    curr, prev = subjects[idx], subjects[idx - 1]
    if curr["start"] - prev["start"] < MIN_BEFORE_AFTER_GAP:
        return None
    tmpl = rng.choice(TEMPLATES[pid]["before_after"])
    if "trước" in tmpl or "tiền nhiệm" in tmpl:
        q = tmpl.format(s=curr["s_label"], o=curr["o_label"])
        answers = [prev["s_label"]]
    else:
        q = tmpl.format(s=prev["s_label"], o=prev["o_label"])
        answers = [curr["s_label"]]
    return {"question": q, "answers": answers, "answer_type": "entity",
            "qtype": "before_after", "time_level": "year", "relation": pid}


def gen_first_last(kg: KG, pid: str, rng: random.Random):
    """2 biến thể: hỏi về subject (câu first_last_s) hoặc object (first_last_o)."""
    pool_s = [(p, s) for (p, s), fs in kg.by_rs.items()
              if p == pid and len(fs) >= 2]
    pool_o = [(p, o) for (p, o), fs in kg.by_ro.items()
              if p == pid and len({f["s_qid"] for f in fs}) >= 2]
    use_s = pool_s and (not pool_o or rng.random() < 0.5)
    if use_s:
        _, s_qid = rng.choice(pool_s)
        fs = sorted(kg.by_rs[(pid, s_qid)], key=lambda f: f["start"])
        target = rng.choice([fs[0], fs[-1]])
        tmpl = rng.choice(TEMPLATES[pid]["first_last_s"])
        q = tmpl.format(s=target["s_label"])
        answers = [target["o_label"]]
    elif pool_o:
        _, o_qid = rng.choice(pool_o)
        fs = sorted(kg.by_ro[(pid, o_qid)], key=lambda f: f["start"])
        target = rng.choice([fs[0], fs[-1]])
        tmpl = rng.choice(TEMPLATES[pid]["first_last_o"])
        q = tmpl.format(o=target["o_label"])
        answers = [target["s_label"]]
    else:
        return None
    return {"question": q, "answers": answers, "answer_type": "entity",
            "qtype": "first_last", "time_level": "year", "relation": pid}


def gen_time_join(kg: KG, pid: str, rng: random.Random):
    pool = kg.by_rel.get(pid, [])
    if len(pool) < 2: return None
    for _ in range(30):
        f1, f2 = rng.sample(pool, 2)
        if f1["s_qid"] == f2["s_qid"]: continue
        s1, e1 = f1["start"], f1["end"] or f1["start"]
        s2, e2 = f2["start"], f2["end"] or f2["start"]
        if max(s1, s2) > min(e1, e2): continue
        overlap = max(s1, s2)
        # time_join template có {verb}/{verb2} đã render trong TEMPLATES.
        # Vì template generic không phân biệt 2 verb → cùng pid nên cùng verb.
        tmpl = rng.choice(TEMPLATES[pid]["time_join"])
        # Render verb2 ở đây nếu template còn placeholder
        tmpl_filled = tmpl.replace("{verb2}", _verb(pid))
        q = tmpl_filled.format(s=f1["s_label"], o=f1["o_label"],
                               s2=f2["s_label"], o2=f2["o_label"])
        answers = sorted({x["s_label"]
                          for x in kg.active_at(pid, f1["o_qid"], overlap)})
        if not answers: continue
        return {"question": q, "answers": answers, "answer_type": "entity",
                "qtype": "time_join", "time_level": "year",
                "relation": pid, "year": overlap}
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
    rng = random.Random(42)
    print("[load] KG từ cache + filter:")
    facts = load_kg()
    if not facts:
        print("Không có fact. Chạy build_kg.py trước.")
        return
    kg = KG(facts)
    print(f"\nRelations active: {len(kg.relations)}: {kg.relations}")

    questions: list[dict] = []
    seen_q: set[str] = set()
    quid = 0

    for qtype, ratio in QTYPE_DISTRIBUTION.items():
        n_target = int(TARGET_QUESTIONS * ratio)
        pbar = tqdm(total=n_target, desc=f"  {qtype:14s}")
        attempts = 0
        made = 0
        while made < n_target and attempts < n_target * 30:
            attempts += 1
            pid = rng.choice(kg.relations)
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

    out_dir = Path(OUT_DIR); out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "questions.json"
    out_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2))
    print(f"\n[done] {len(questions):,} câu -> {out_path}")


if __name__ == "__main__":
    main()
