# ARI on cronqvn — Hướng dẫn chạy

Cài đặt **Abstract Reasoning Induction** (Chen et al., ACL 2024) cho dataset
TKGQA tiếng Việt **cronqvn**, dùng **Ollama** thay vì OpenAI.

---

## 1. Yêu cầu

| | |
|---|---|
| Python | ≥ 3.9 (đã test 3.9.6) |
| Ollama | <https://ollama.com> chạy local ở `http://localhost:11434` |
| Disk   | ~3 GB (model + KG) |
| RAM    | ~2 GB (KG load full vào RAM) |

Không cần `pip install` gì cả — code chỉ dùng stdlib (`urllib`, `json`,
`dataclasses`, `re`, …). K-means và cosine viết tay.

---

## 2. Chuẩn bị Ollama

```bash
# (1) Cài Ollama nếu chưa có
#   macOS:  brew install ollama
#   Linux:  curl -fsSL https://ollama.com/install.sh | sh

# (2) Khởi động server (chạy nền)
ollama serve &

# (3) Pull model
ollama pull qwen2.5:7b          # LLM chính
ollama pull nomic-embed-text    # embedding cho K-means + semantic filter

# (4) Kiểm tra
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```

Đổi model? Sửa `LLM_MODEL` / `EMBED_MODEL` trong [config.py](config.py).

---

## 3. Kiểm tra dataset

Code đọc:
- `cronqvn/facts/P*.jsonl`           — TKG (≈238K facts)
- `cronqvn/facts/qid_labels.json`, `qid_labels.vi.json` — label entity
- `cronqvn/facts/pid_labels.json`, `pid_labels.vi.json` — label relation
- `cronqvn/out/questions.json`       — câu hỏi (đã kèm `entities: [qid,...]`)

```bash
python3 -c "from ari.kg import get_kg; kg=get_kg(); \
print('facts',len(kg.facts),'qids',len(kg.qid2label),'pids',len(kg.pid2label))"
# kỳ vọng: facts 237907 qids 37584 pids 271
```

---

## 4. Chạy pipeline

```bash
cd /Users/danhlhl/HCMUS_Thesis           # repo root
```

### Phase 1 — Học methodology (~15–30 phút với qwen2.5:7b)

```bash
python3 -m ari.learn --n 200 --k 10
```

Cờ:
- `--n` số sample stratified để xây bộ nhớ lịch sử (paper dùng 200)
- `--k` số cluster K-means (paper dùng 10)
- `--questions PATH` đổi file câu hỏi
- `--out PATH` nơi ghi `memory_bank.json`

Ghi ra:
- `ari/artifacts/history_records.json` — toàn bộ trace của 200 câu mẫu
- `ari/artifacts/memory_bank.json`     — `clusters[*]: {centroid, methodology, ...}`

### Phase 2 — Inference + đánh giá

```bash
python3 -m ari.evaluate --n 200
```

Cờ:
- `--n` số câu lấy stratified từ test set
- `--bank PATH` đường dẫn `memory_bank.json`
- `--no-methodology` ablation: bỏ guidance trừu tượng (paper: w/o Abstract Guidance)
- `--out PATH` nơi ghi trace

In ra accuracy tổng và theo `qtype` / `answer_type` / `qlabel`, ví dụ:

```
Overall:  76/200 = 0.380
By qtype:
  before_after      28/40   = 0.700
  first_last        20/40   = 0.500
  simple_entity     12/40   = 0.300
  simple_time        9/40   = 0.225
  time_join          7/40   = 0.175
By answer_type:
  entity     54/160 = 0.337
  time       22/40  = 0.550
```

Trace lưu ở `ari/artifacts/eval_traces.json`.

---

## 5. Smoke test nhanh (không gọi Ollama)

```bash
python3 -c "
from ari.agent import run_question
from ari.kg import get_kg
import json
kg = get_kg()

def fake_chat(prompt, system=None):
    import re
    m = re.search(r'Các hành động khả dụng tại bước này.*?\n(.+?)Hãy chọn', prompt, re.S)
    if not m: return 'Action: \$answer(unknown)\$'
    lines = [l.strip().lstrip('- ').strip() for l in m.group(1).strip().split('\n') if l.strip()]
    for l in lines:
        if l.startswith('\$answer('): return f'Action: {l}\nReason: stub'
    return f'Action: {lines[0]}\nReason: stub'

def fake_embed(texts): return [[1.0, 0.0] for _ in texts]

q = json.load(open('cronqvn/out/questions.json'))[0]
tr = run_question(kg, q, methodology='(stub)', embed_fn=fake_embed, chat_fn=fake_chat)
print(tr.final_answer, tr.correct)
"
```

---

## 6. Tinh chỉnh

Sửa `ari/config.py`:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `LLM_MODEL` | `qwen2.5:7b` | model trả lời |
| `EMBED_MODEL` | `nomic-embed-text` | model embedding |
| `LLM_TEMPERATURE` | `0.0` | reproducible |
| `N_CLUSTERS` | `10` | K trong K-means (paper Fig. 6: tối ưu ~10) |
| `N_MEMORY_SAMPLES` | `200` | size bộ nhớ lịch sử |
| `MAX_REASONING_STEPS` | `5` | trần độ dài chain (paper §4.1) |
| `TOP_K_ACTIONS` | `12` | sau semantic filter (Eq. 3) |
| `MAX_CANDIDATES_PER_RELATION` | `80` | hard cap trước filter |
| `TEST_SAMPLE_SIZE` | `200` | size eval set |

---

## 7. Cấu trúc thư mục

```
ari/
├── config.py            # paths, model, hyper-params
├── ollama_client.py     # HTTP client chat + embeddings
├── kg.py                # nạp TKG cronqvn vào RAM, build index
├── actions.py           # 9 atomic op (Table 6)
├── enumerate_actions.py # enumerate (Eq. 2) + semantic top-K (Eq. 3)
├── ner.py               # entity linker (fallback nếu câu thiếu `entities`)
├── prompts.py           # prompt tiếng Việt
├── agent.py             # vòng lặp ARI (Algorithm 1)
├── memory.py            # H_q + K-means + induce M_C (§3.4)
├── learn.py             # phase 1 — induce methodology bank
├── evaluate.py          # phase 2 — inference + report
└── artifacts/           # output ghi vào đây
```

---

## 8. Ánh xạ paper ↔ code

| Paper | Code |
|---|---|
| 1-hop subgraph G_{e_h} (Eq. 1) | `kg.KG.one_hop` |
| Enumerate P_t (Eq. 2) | `enumerate_actions.enumerate_initial` |
| Semantic top-K P'_t (Eq. 3) | `enumerate_actions.filter_actions` |
| History H_q (Eq. 4) | `memory.trace_to_record` |
| Cluster + chọn C* (Eq. 5) | `memory.kmeans` + `memory.select_methodology` |
| LLM(M_C*, q, P'_t) (Eq. 6) | `agent.run_question` |
| Methodology induction (App. prompt) | `memory.induce_methodology` |
| Atomic templates (Table 6) | `actions.py` |
| Algorithm 1 | `agent.run_question` (vòng `for step_i in range(MAX_REASONING_STEPS)`) |

---

## 9. Troubleshooting

| Lỗi | Khắc phục |
|---|---|
| `ConnectionRefusedError` khi gọi Ollama | `ollama serve` chưa chạy, hoặc đổi `OLLAMA_URL` |
| `model 'qwen2.5:7b' not found` | `ollama pull qwen2.5:7b` |
| `seeds=[]` xuất hiện trên nhiều câu | Dùng `cronqvn/out/questions.json` (có sẵn `entities`), không phải `test.json` |
| Quá chậm | Giảm `N_MEMORY_SAMPLES`, `TEST_SAMPLE_SIZE`, hoặc đổi sang model nhỏ hơn (`qwen2.5:3b`) |
| Embedding hết RAM | Đổi `EMBED_MODEL` sang model nhẹ hơn |
| LLM trả lời sai format | Tăng `LLM_NUM_CTX`, hoặc sửa prompt trong `prompts.py` |

---

## 10. Cross-encoder reranker (tuỳ chọn)

Mặc định bước chọn action lọc candidate bằng **cosine** (bi-encoder). Có thể bật
thêm một **cross-encoder PhoBERT** chấm điểm bộ ba `(câu hỏi, lịch sử suy luận,
action)` và rerank — cascade *sau* cosine: cosine lấy `CE_COSINE_TOPN` rộng →
cross-encoder cắt còn `TOP_K_ACTIONS`.

### 10.1 Cài deps (chỉ khi train / bật)

```bash
pip install -r ari/requirements-ce.txt   # torch, transformers, sentence-transformers, pyvi
```

Core ARI vẫn stdlib-only khi `USE_CROSS_ENCODER=False` (lazy import).

### 10.2 Sinh dataset (gold-path + hard negatives)

```bash
python3 -m ari.ce_data        # -> ari/artifacts/ce_dataset.jsonl
```

Mỗi qtype có một chuỗi op gold dựng tự động từ KG + annotation, **verify bằng
cách thực thi** (giữ câu nào chạy ra đúng `answers`). In thống kê giữ/rớt theo
qtype (vd `time_join`/`simple_time` rớt do ngữ nghĩa vượt bộ op atomic). Negative
= các candidate còn lại trong pool + hard negatives từ `history_records.json`
(trace LLM sai). Nhãn không gán tay.

### 10.3 Train

```bash
python3 -m ari.ce_train --epochs 4   # -> ari/artifacts/ce_model/
```

Split theo **câu hỏi** (tránh leak giữa các step cùng câu). Sau train in
`Hit@12` / `MRR` của reranker trên val.

### 10.4 Bật khi đánh giá + ablation

Đặt `USE_CROSS_ENCODER = True` trong [config.py](config.py) rồi:

```bash
python3 -m ari.evaluate --n 200       # cosine -> cross-encoder
```

So với baseline `USE_CROSS_ENCODER = False` (cosine-only) để đo tác động.

| Biến (config.py) | Mặc định | Ý nghĩa |
|---|---|---|
| `USE_CROSS_ENCODER` | `False` | bật/tắt tầng cross-encoder |
| `CE_COSINE_TOPN` | `30` | cosine giữ N trước khi rerank |
| `CE_BASE_MODEL` | `vinai/phobert-base` | base để fine-tune |
| `CE_MAX_LEN` | `256` | trần token PhoBERT |
| `CE_MODEL_DIR` | `artifacts/ce_model` | nơi lưu/đọc model |
