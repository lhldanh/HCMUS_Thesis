from ari.actions import Action
from ari import ce_rerank as R


def test_rerank_orders_by_score(monkeypatch):
    acts = [Action("answer", (x,), f"$answer({x})$") for x in ["A", "B", "C"]]
    monkeypatch.setattr(R, "_model_predict", lambda pairs: [0.1, 0.9, 0.2])
    out = R.rerank("q?", [], acts, top=2)
    assert [a.args[0] for a in out] == ["B", "C"]


def test_rerank_empty():
    assert R.rerank("q?", [], [], top=5) == []


def test_score_builds_pairs(monkeypatch):
    captured = {}

    def fake_predict(pairs):
        captured["n"] = len(pairs)
        return [0.5] * len(pairs)

    monkeypatch.setattr(R, "_model_predict", fake_predict)
    acts = [Action("get_first", (), "$get_first({entities})$"),
            Action("answer", ("X",), "$answer(X)$")]
    R.score("câu hỏi?", [], acts)
    assert captured["n"] == 2
