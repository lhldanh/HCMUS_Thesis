import json

from ari import config, ce_data as D


def _q(qtype):
    return next(x for x in json.load(open(config.QUESTIONS_FILE, encoding="utf-8"))
               if x["qtype"] == qtype)


def test_examples_have_pos_and_neg(kg):
    exs = D.examples_for_question(kg, _q("simple_entity"))
    assert any(e["label"] == 1 for e in exs)
    assert any(e["label"] == 0 for e in exs)
    for e in exs:
        assert e["context_text"] and e["action_text"]


def test_before_after_positive_is_filter_op(kg):
    # before_after có bước filter; positive ở bước đó phải là op get_before/get_after
    exs = D.examples_for_question(kg, _q("before_after"))
    pos_filter = [e for e in exs if e["label"] == 1
                  and ("trước" in e["action_text"].lower()
                       or "sau" in e["action_text"].lower())]
    assert pos_filter, "không có positive cho bước filter"


def test_dataset_build_small(kg):
    qs = json.load(open(config.QUESTIONS_FILE, encoding="utf-8"))[:20]
    data = D.build_dataset(kg, qs, history_path=None)
    assert len(data) > 0
    assert all({"context_text", "action_text", "label", "source"} <= set(d) for d in data)
