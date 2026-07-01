# RUN_GUIDE — Chạy để điền số liệu cho báo cáo

Hướng dẫn chuỗi lệnh để sinh **mọi số liệu [CẦN ĐIỀN]** trong Chương 5 và Phụ lục C.
Mỗi mục ánh xạ thẳng tới bảng/hình trong báo cáo.

> Chạy mọi lệnh `ari.*` từ **repo root** (`/Users/danhlhl/HCMUS_Thesis`).
> Các lệnh `cronqvn` chạy trong thư mục `cronqvn/`.

---

## 0. Tiền đề

```bash
ollama serve &                       # nền
ollama pull qwen3:14b                # LLM suy luận (pha đánh giá)
ollama pull nomic-embed-text         # embedding
export OPENAI_API_KEY=sk-...         # pha học induce methodology = gpt-4o (theo bản gốc)
```

Cross-encoder (chỉ khi làm đóng góp #3):
```bash
pip install -r ari/requirements-ce.txt
```

---

## 1. Sinh bộ dữ liệu TOÀN BỘ — đóng góp #1, **Bảng 5.1** + **Ch3 dòng CronQ-VN**

`generate.py` giờ **liệt kê toàn bộ** câu hỏi hợp lệ (không lấy mẫu):
```bash
cd cronqvn
python3 generate.py                  # mặc định = TOÀN BỘ -> out/questions.json (~539.584 câu, ~244MB)
# python3 generate.py -n 30000       # (tuỳ chọn) quay lại chế độ lấy mẫu ngẫu nhiên ≤N câu
```
Số liệu hiện tại (khớp Bảng 5.1): simple_time 200.924 · before_after 170.561 ·
simple_entity 99.121 · time_join 44.278 · first_last 24.700 · **tổng 539.584**.

> ⚠️ `out/questions.json` (~244MB) **vượt giới hạn 100MB của GitHub** → đã gitignore
> + gỡ khỏi git. Tái sinh 100% (tất định) bằng lệnh trên.
> ⚠️ Sau khi đổi `questions.json`, **phải chạy lại pha học (mục 2)** vì memory bank
> hiện tại học từ bộ câu hỏi cũ.
> ⚠️ 539K câu rất lớn cho pha học/CE — `learn`/`evaluate` tự lấy mẫu phân tầng qua
> `--n`; hoặc trỏ `--questions` tới một tập con.

---

## 2. Pha học — methodology bank (nền cho ARI)

```bash
python3 -m ari.learn --n 200 --k 10        # gpt-4o induce -> ari/artifacts/memory_bank.json
                                           #               + history_records.json
```
Biến thể cho ablation (tái dùng `history_records.json` qua `--resume`, **không tốn LLM lại**):
```bash
python3 -m ari.learn --k 1 --resume --out ari/artifacts/memory_bank_k1.json      # w/o History Cluster
python3 -m ari.learn --no-incorrect --resume --out ari/artifacts/memory_bank_noinc.json  # w/o Incorrect Examples
```

---

## 3. **Bảng 5.3** — Kết quả tổng (baselines + ARI)

```bash
python3 -m ari.evaluate --method llm-only  --n 200    # -> eval_llm-only.json
python3 -m ari.evaluate --method kg-rag    --n 200    # -> eval_kg-rag.json
python3 -m ari.evaluate --method cot-kb    --n 200    # -> eval_cot-kb.json
python3 -m ari.evaluate --method react-kb  --n 200    # -> eval_react-kb.json
python3 -m ari.evaluate                    --n 200    # ARI đầy đủ -> eval_ari.json
```
Mỗi lệnh in: `Overall`, theo `qtype`, `answer_type`, `qlabel`. Cột **Đơn giản** =
gộp `simple_entity`+`simple_time`; **Phức tạp** = `before_after`+`first_last`+`time_join`.

---

## 4. **Bảng 5.4** — Ablation

```bash
python3 -m ari.evaluate --no-methodology     --n 200   # w/o Abstract Guidance
python3 -m ari.evaluate --no-action-filter   --n 200   # w/o Action Filter
python3 -m ari.evaluate --bank ari/artifacts/memory_bank_k1.json   --n 200   # w/o History Cluster
python3 -m ari.evaluate --bank ari/artifacts/memory_bank_noinc.json --n 200  # w/o Incorrect Examples
```
(Dòng "ARI đầy đủ" lấy lại từ `eval_ari.json` ở mục 3.)

---

## 5. **Bảng 5.5** + **Hình 5.x** — Phân tích cross-encoder (đóng góp #3, CHNC3)

```bash
python3 -m ari.ce_data                       # -> ari/artifacts/ce_dataset.jsonl (đã có; chạy lại nếu đổi dataset)
python3 -m ari.ce_train --epochs 4           # -> ari/artifacts/ce_model/  (in Hit@12 / MRR trên val)
```
So sánh hai cấu hình lọc (cùng bank, cùng model):
```bash
# Cosine Top-K (gốc): giữ USE_CROSS_ENCODER=False -> chính là eval_ari.json (mục 3)
# Cosine + Cross-encoder: đặt USE_CROSS_ENCODER=True trong ari/config.py rồi:
python3 -m ari.evaluate --n 200              # -> eval_ari_cross-encoder.json
```

---

## 6. **Hình 5.1** (accuracy theo số cụm k) — tùy chọn

Quét k:
```bash
for k in 1 4 7 10 14 20; do
  python3 -m ari.learn --k $k --resume --out ari/artifacts/bank_k$k.json
  python3 -m ari.evaluate --bank ari/artifacts/bank_k$k.json --n 200
done
```

---

## 7. Phụ lục

- **A (prompts) + B (bảng quan hệ):** sinh tự động, không cần LLM:
  ```bash
  PYTHONPATH=. python3 Danh_Thesis_Report__1_/scripts/gen_appendix.py
  ```
- **C (trace ví dụ):** trích vài record mỗi `qtype` từ `ari/artifacts/eval_ari.json`.

---

## 8. Còn cần điền thủ công (không tự sinh được)

- §5.2: **phần cứng** (CPU/GPU, RAM) + **thời gian chạy trung bình mỗi câu** — đo khi chạy mục 3.
- §5.7: số bước suy luận trung bình (có/không hướng dẫn) — đọc từ trace; nhóm lỗi điển hình.

---

## Ánh xạ output → báo cáo

| File `ari/artifacts/` | Mục báo cáo |
|---|---|
| `eval_ari.json` | Bảng 5.3 (ARI), 5.4 (đầy đủ), 5.5 (cosine), Phụ lục C |
| `eval_{llm-only,kg-rag,cot-kb,react-kb}.json` | Bảng 5.3 |
| `eval_ari_no-methodology.json` | Bảng 5.4 |
| `eval_ari_no-action-filter.json` | Bảng 5.4 |
| `eval_ari_memory_bank_k1.json` | Bảng 5.4 (w/o History Cluster) |
| `eval_ari_memory_bank_noinc.json` | Bảng 5.4 (w/o Incorrect Examples) |
| `eval_ari_cross-encoder.json` | Bảng 5.5 (CE) |
