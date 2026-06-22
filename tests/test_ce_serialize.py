from ari.actions import Action
from ari import ce_serialize as S


def test_action_to_vi_head():
    a = Action("get_head_entity", ("Q1", "P102", 1992),
               '$get_head_entity("Đảng Xã hội", "đảng viên", 1992)$')
    txt = S.action_to_vi(a)
    assert "Đảng Xã hội" in txt and "đảng viên" in txt and "1992" in txt


def test_action_to_vi_answer():
    a = Action("answer", ("Manuel Valls",), "$answer(Manuel Valls)$")
    assert S.action_to_vi(a) == "Trả lời: Manuel Valls"


def test_action_to_vi_first():
    a = Action("get_first", (), "$get_first({entities})$")
    assert "sớm nhất" in S.action_to_vi(a)


def test_make_pair_includes_history():
    q = "Vào lúc 1992, ai thuộc Đảng Xã hội?"

    class Step:  # duck-typed StepLog
        chosen = '$get_head_entity("Đảng Xã hội", "đảng viên", 1992)$'
        op = "get_head_entity"
        entities = [("Manuel Valls", "Q1", 1980)]

    ctx, act = S.make_pair(q, [Step()],
                           Action("answer", ("Manuel Valls",), "$answer(Manuel Valls)$"))
    assert q in ctx and "Bước 0" in ctx
    assert act == "Trả lời: Manuel Valls"


def test_segment_runs():
    # pyvi đã cài trong môi trường test
    out = S.segment("Đại học Quốc gia Hà Nội")
    assert "_" in out
