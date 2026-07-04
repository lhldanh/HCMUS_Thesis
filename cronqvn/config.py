"""Cấu hình chung cho 3 phase của cronqvn."""

# ---------- Paths ----------
DATA_DIR = "data"
CACHE_DIR = "facts"
FACTS_DIR = "facts"
OUT_DIR = "out"
DUMP_FILE = "data/latest-all.json.bz2"

# ---------- KG filtering ----------
# Lấy mọi năm, không giới hạn (giống tkbc)
YEAR_MIN = 1
YEAR_MAX = 2100

# ---------- Wikidata dump ----------
# build_kg.py duyệt full dump để extract fact tự lọc (giống tkbc).
WIKIDATA_DUMP_URL = "https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.bz2"

# ---------- Relations ----------
# Mỗi relation cần:
#   - "verb"  : động từ tiếng Việt (vd "giữ chức", "chơi cho")
#   - "noun"  : danh từ chỉ object kind (cho first_last template)
#   - "en"    : tên EN (chỉ để tham khảo)
#   - "tmpl_override" (optional): nếu cú pháp đặc biệt, dùng template riêng
#                                  thay vì generic. Phải có cùng 5 qtype keys.
# Chỉ giữ các PID có template trong templates.py (8 relation active thực sự).
RELATIONS = {
    # CronQ gốc (5)
    "P39":  {"verb": "giữ chức",      "noun": "chức vụ",       "en": "position held"},
    "P54":  {"verb": "chơi cho",      "noun": "câu lạc bộ",    "en": "member of sports team"},
    "P166": {"verb": "nhận",          "noun": "giải thưởng",   "en": "award received"},
    "P26":  {"verb": "kết hôn với",   "noun": "vợ/chồng",      "en": "spouse"},
    "P108": {"verb": "làm việc tại",  "noun": "nơi làm việc",  "en": "employer"},

    # Mở rộng — Education / Career
    "P69":  {"verb": "học tại",       "noun": "trường",         "en": "educated at"},

    # Politics
    "P102": {"verb": "là thành viên của",      "noun": "đảng",      "en": "member of political party"},

    # Membership
    "P463": {"verb": "là thành viên của", "noun": "tổ chức",    "en": "member of"},
}

# ---------- Question generation ----------
TARGET_QUESTIONS = 30000
QTYPE_DISTRIBUTION = {
    "simple_entity": 0.20,
    "simple_time":   0.20,
    "before_after":  0.20,
    "first_last":    0.20,
    "time_join":     0.20,
}

# ---------- KG-build filters (tkbc-style, áp ở build_kg.py) ----------
# Step 2: lọc relation hiếm — relation có < N statement bị bỏ
BUILD_MIN_RELATION_FACTS = 100
# Step 3: lọc entity hiếm — entity xuất hiện < M fact bị bỏ
BUILD_MIN_ENTITY_FACTS = 20

# ---------- Question-gen filters (áp ở generate.py) ----------
MAX_ANSWERS = 20
MIN_LABEL_LEN = 3
MIN_BEFORE_AFTER_GAP = 1

# Bỏ fact có o_label là class chung — làm câu hỏi vô nghĩa.
# Vd "chính trị gia độc lập" không phải một đảng cụ thể; "extraordinary professor"
# là chức danh chung dùng làm value của P39.
BAD_O_LABELS = {
    "P102": {
        "chính trị gia độc lập", "không đảng phái", "phi đảng phái",
        "independent politician", "independent",
    },
    "P39": {
        "extraordinary professor", "Privatdozent", "privatdozent",
        "giáo sư danh dự", "giáo sư thỉnh giảng",
    },
}

# Với các relation kéo dài (membership/employment), simple_entity yêu cầu fact
# có closed interval (end != None) để tránh các claim ongoing thiếu chính xác.
SIMPLE_ENTITY_REQUIRE_CLOSED = {"P102", "P54", "P108", "P463", "P39", "P69"}

# time_join: overlap tối thiểu (năm) giữa hai fact để được coi là "cùng giai đoạn"
TIME_JOIN_MIN_OVERLAP = 1

