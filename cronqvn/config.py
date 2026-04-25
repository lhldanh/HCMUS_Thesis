"""Cấu hình chung cho 3 phase của cronqvn."""

# ---------- Paths ----------
DATA_DIR = "data"
CACHE_DIR = "cache"
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
RELATIONS = {
    # CronQ gốc (5)
    "P39":  {"verb": "giữ chức",      "noun": "chức vụ",       "en": "position held"},
    "P54":  {"verb": "chơi cho",      "noun": "câu lạc bộ",    "en": "member of sports team"},
    "P166": {"verb": "nhận",          "noun": "giải thưởng",   "en": "award received"},
    "P26":  {"verb": "kết hôn với",   "noun": "vợ/chồng",      "en": "spouse"},
    "P108": {"verb": "làm việc tại",  "noun": "nơi làm việc",  "en": "employer"},

    # Mở rộng — Education / Career
    "P69":  {"verb": "học tại",       "noun": "trường",         "en": "educated at"},
    "P512": {"verb": "có học vị",     "noun": "học vị",         "en": "academic degree"},
    "P937": {"verb": "công tác tại",  "noun": "nơi công tác",   "en": "work location"},

    # Politics
    "P6":   {"verb": "đứng đầu chính phủ của", "noun": "chính phủ", "en": "head of government"},
    "P102": {"verb": "là thành viên của",      "noun": "đảng",      "en": "member of political party"},
    "P488": {"verb": "là chủ tịch của",        "noun": "tổ chức",   "en": "chairperson"},
    "P1308":{"verb": "giữ vị trí",             "noun": "vị trí",    "en": "officeholder"},

    # Awards adjacent
    "P1411":{"verb": "được đề cử",   "noun": "giải đề cử",     "en": "nominated for"},
    "P1346":{"verb": "thắng",        "noun": "cuộc thi",        "en": "winner"},

    # Membership
    "P463": {"verb": "là thành viên của", "noun": "tổ chức",    "en": "member of"},
    "P551": {"verb": "cư trú tại",        "noun": "nơi cư trú", "en": "residence"},

    # Sports
    "P286": {"verb": "huấn luyện",     "noun": "đội",            "en": "head coach"},

    # Military
    "P410": {"verb": "có quân hàm",    "noun": "quân hàm",       "en": "military rank"},
    "P241": {"verb": "phục vụ trong",  "noun": "quân chủng",     "en": "military branch"},

    # Misc
    "P127": {"verb": "thuộc sở hữu của", "noun": "chủ sở hữu",   "en": "owned by"},
    "P185": {"verb": "hướng dẫn",       "noun": "nghiên cứu sinh","en": "doctoral student"},
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
BUILD_MIN_RELATION_FACTS = 0
# Step 3: lọc entity hiếm — entity xuất hiện < M fact bị bỏ
BUILD_MIN_ENTITY_FACTS = 0

# ---------- Question-gen filters (áp ở generate.py) ----------
MAX_ANSWERS = 20
MIN_LABEL_LEN = 3
MIN_BEFORE_AFTER_GAP = 1

