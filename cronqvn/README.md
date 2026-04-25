# CronQ-VN

Sinh dataset QA tiếng Việt có yếu tố thời gian từ Wikidata KG, lấy cảm hứng từ CronQuestions (Saxena et al., ACL 2021) + lọc kiểu tkbc (Lacroix et al., NeurIPS 2020).

## Cấu trúc

```
cronqvn/
├── build_kg.py       # Phase 1: download dump + extract KG (100% VN label)
├── generate.py       # Phase 2: sinh 30K câu hỏi từ KG
├── config.py         # cấu hình relations, filter, target
├── templates.py      # template VN generic + override
├── requirements.txt
├── data/             # (auto) Wikidata dump bz2
├── cache/            # (auto) KG: P*.jsonl + labels.json
└── out/              # (auto) questions.json
```

## Cài đặt

```bash
pip install -r requirements.txt
```

Không cần Ollama, không cần dịch — vì build_kg lọc strict 100% VN.

## Chạy

```bash
# Test trước với 1M entity (~5-10 phút):
python build_kg.py --limit 1000000

# Full (~10-15 giờ, dump ~100GB):
python build_kg.py

# Sinh câu hỏi (~5 phút):
python generate.py
```

## Trên Colab

```python
# Cell 1: clone + setup
!git clone https://github.com/USERNAME/cronqvn.git
%cd cronqvn
!pip install -q -r requirements.txt

# Cell 2: pipeline
!python build_kg.py 2>&1 | tee build_kg.log
!python generate.py 2>&1 | tee generate.log

# Cell 3: backup ra Drive
from google.colab import drive
drive.mount('/content/drive')
!cp out/questions.json /content/drive/MyDrive/cronqvn_questions.json
!cp -r cache /content/drive/MyDrive/cronqvn_cache
```

**Khuyến nghị Colab Pro** (225 GB disk + 24h session).
Free tier (78 GB) thiếu chỗ → dùng `--limit 5000000` để test.

## Pipeline build_kg.py (4 step kiểu tkbc + VN strict)

```
Step 0. Download dump latest-all.json.bz2 (resume support)

Step 1. Pass 1 → collect {qid: vi_label, en_label}
        cho mọi entity có VN label
        (~5M entity, RAM ~1 GB)

Step 2. Pass 2 → extract fact temporal mà:
        - subject ∈ entity-có-VN
        - object  ∈ entity-có-VN  ← STRICT
        - claim có time qualifier P580/P582/P585
        - discretize timestamp về năm

Step 3. Lọc relation hiếm (< 200 fact/relation)

Step 4. Lọc entity hiếm (< 2 fact/entity)

Output: cache/{P39,P54,...}.jsonl + cache/labels.json
        100% VN label, không cần dịch sau.
```

## Output schema

`out/questions.json`:
```json
{
  "quid": 1,
  "question": "Ai giữ chức Tổng thống Hoa Kỳ vào năm 2010?",
  "answers": ["Barack Obama"],
  "answer_type": "entity",
  "qtype": "simple_entity",
  "time_level": "year",
  "relation": "P39",
  "year": 2010,
  "qlabel": "Single"
}
```

## 5 qtype (như CronQuestions)

- `simple_entity` — Ai làm X năm Y?
- `simple_time` — X làm Y năm nào?
- `before_after` — Ai là X trước/sau Y?
- `first_last` — X đầu tiên / gần nhất là gì?
- `time_join` — Ai là X khi Y đang là Z?

## ~22 Wikidata relation (mở rộng từ 5 của CronQ)

| Group | Relations |
|---|---|
| CronQ gốc | P39, P54, P166, P26, P108 |
| Education / Career | P69, P512, P937 |
| Politics | P6, P102, P488, P1308 |
| Awards | P1411, P1346 |
| Membership | P463, P551 |
| Sports | P286 |
| Military | P410, P241 |
| Misc | P127, P185 |

Mỗi relation có `verb` + `noun` trong `config.py`. Template generic dùng chung,
override riêng nếu cần (vd P26 spouse có "vợ/chồng"). Mở rộng = thêm dòng vào
`RELATIONS` dict.

## Filter

**`build_kg.py`** (giống tkbc + VN strict):
- VN label cho cả s và o
- Time qualifier (P580/P582/P585)
- `BUILD_MIN_RELATION_FACTS=200`
- `BUILD_MIN_ENTITY_FACTS=2`

**`generate.py`** (chất lượng câu hỏi):
- `MAX_ANSWERS=20`: bỏ câu bùng nổ (parliament)
- `MIN_LABEL_LEN=3`: bỏ label quá ngắn
- `MIN_BEFORE_AFTER_GAP=1`: before_after cần cách ≥ 1 năm
- Không self-ref (s_qid ≠ o_qid)
- Không leak đáp án vào câu
- Dedup câu trùng

## Tuỳ chỉnh

Sửa `config.py`:
- `TARGET_QUESTIONS`, `QTYPE_DISTRIBUTION`
- `MAX_ANSWERS`, `MIN_LABEL_LEN`, `MIN_BEFORE_AFTER_GAP`
- `BUILD_MIN_RELATION_FACTS`, `BUILD_MIN_ENTITY_FACTS`
- `RELATIONS` (thêm/bớt; nhớ cập nhật template nếu cần override)
