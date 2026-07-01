import json

from ari import config, ce_goldpath as G


def _by_qtype():
    qs = json.load(open(config.QUESTIONS_FILE, encoding="utf-8"))
    out = {}
    for q in qs:
        out.setdefault(q["qtype"], q)
    return out


def test_reconstruct_each_qtype_verifies(kg):
    samples = _by_qtype()
    failed = []
    for qt, q in samples.items():
        path = G.reconstruct_gold_path(kg, q)
        if path is None or not G.verify_path(kg, q, path):
            failed.append(qt)
    # Ít nhất 4/5 qtype dựng được path verify (một số có thể rớt do KG thiếu thời gian)
    assert len(failed) <= 1, f"qtype rớt verify: {failed}"


def test_simple_time_is_time_answer(kg):
    q = next(x for x in json.load(open(config.QUESTIONS_FILE, encoding="utf-8"))
             if x["qtype"] == "simple_time")
    path = G.reconstruct_gold_path(kg, q)
    assert path is not None
    assert path[0].op == "get_time"
