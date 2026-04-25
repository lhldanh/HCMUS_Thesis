"""Template generic + override theo từng relation đặc biệt.

GENERIC dùng `{verb}` và `{noun}` từ config.RELATIONS để format. Generator sẽ
substitute trước khi fill {s}/{o}/{year}.

Slots:
  {verb}  - động từ relation (vd "giữ chức")
  {noun}  - danh từ object kind (vd "chức vụ")
  {s}     - subject label
  {o}     - object label
  {s2}    - subject thứ 2 (time_join)
  {o2}    - object thứ 2 (time_join)
  {year}  - năm
"""

# Template generic: dùng cho mọi relation chưa có override
GENERIC = {
    "simple_entity": [
        "Ai {verb} {o} năm {year}?",
        "Năm {year}, ai {verb} {o}?",
    ],
    "simple_time": [
        "{s} {verb} {o} vào năm nào?",
        "Khi nào {s} {verb} {o}?",
        "Năm nào {s} {verb} {o}?",
    ],
    "before_after": [
        "Ai {verb} {o} trước {s}?",
        "Ai {verb} {o} ngay sau {s}?",
    ],
    # first_last có 2 nhóm:
    #  - về subject ({s} là người, {noun} là object kind):
    #    "Trường đầu tiên mà X học là gì?" — answer là object
    #  - về object ({o} là target, hỏi ai làm với o sớm/muộn nhất):
    #    "Ai chơi cho X đầu tiên?" — answer là subject
    "first_last_s": [
        "{noun} đầu tiên mà {s} {verb} là gì?",
        "{noun} gần đây nhất mà {s} {verb} là gì?",
    ],
    "first_last_o": [
        "Ai {verb} {o} đầu tiên?",
        "Ai {verb} {o} gần đây nhất?",
    ],
    "time_join": [
        "Ai {verb} {o} khi {s2} {verb2} {o2}?",
    ],
}

# Override cho relation có cú pháp đặc thù.
# Nếu một qtype không override, dùng GENERIC.
OVERRIDES: dict[str, dict[str, list[str]]] = {
    # P26 spouse — đối xứng, "kết hôn với" trong cả 2 chiều.
    # Generic vẫn ổn nhưng thêm biến thể tự nhiên hơn.
    "P26": {
        "simple_entity": [
            "Vợ/chồng của {s} năm {year} là ai?",
            "Năm {year}, {s} kết hôn với ai?",
        ],
        "first_last_s": [
            "Vợ/chồng đầu tiên của {s} là ai?",
            "Vợ/chồng gần đây nhất của {s} là ai?",
        ],
    },

    # P39 — "tiền nhiệm" tự nhiên hơn "trước"
    "P39": {
        "before_after": [
            "Ai giữ chức {o} trước {s}?",
            "Ai làm {o} ngay sau {s}?",
            "Người tiền nhiệm của {s} ở vị trí {o} là ai?",
        ],
    },
}


def build_templates() -> dict[str, dict[str, list[str]]]:
    """Render template cho tất cả relation, áp dụng override + GENERIC."""
    from config import RELATIONS

    out: dict[str, dict[str, list[str]]] = {}
    for pid, info in RELATIONS.items():
        verb = info["verb"]
        noun = info["noun"]
        rel_tmpls = {}
        ovr = OVERRIDES.get(pid, {})
        for qtype, generic_list in GENERIC.items():
            if qtype in ovr:
                rel_tmpls[qtype] = list(ovr[qtype])
            else:
                # Substitute {verb} và {noun}
                rel_tmpls[qtype] = [
                    t.replace("{verb}", verb).replace("{noun}", noun)
                    for t in generic_list
                ]
        out[pid] = rel_tmpls
    return out


# Compile sẵn để generate.py import trực tiếp
TEMPLATES = build_templates()
