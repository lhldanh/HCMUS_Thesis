# Phác thảo 5 hình TikZ cho khóa luận

Bản nháp bằng sơ đồ ASCII cho **5 chỗ trong report có ghi `\todo{vẽ lại bằng TikZ}`**, đã đối chiếu
với code thực tế trong `ari/` và `cronqvn/`. Mỗi hình gồm: vị trí trong report, bản phác, đối chiếu
code, và ghi chú khi chuyển sang TikZ. Cuối tài liệu là **các quyết định đã chốt với Danh**
(02/07/2026) về 2 chỗ report và code lệch nhau, và một hình bonus.

| # | Nhãn hình | Vị trí | Nội dung |
|---|-----------|--------|----------|
| 1 | `fig:three-levels` | `Chapter1/chapter1.tex:87–98` | Ba mức tích hợp thông tin với LLM |
| 2 | `fig:bi-cross` | `Chapter2/chapter2.tex:367–380` | Bi-encoder vs Cross-encoder |
| 3 | `fig:architecture` | `Chapter4/chapter4.tex:35–50` | Kiến trúc tổng thể ARI (2 pha, luồng học/suy luận) |
| 4 | `fig:entity-linking` | `Chapter4/chapter4.tex:394–405` | Liên kết thực thể cho câu hỏi mở |
| 5 | `fig:crossencoder` | `Chapter4/chapter4.tex:456–467` | Bộ lọc hành động hai tầng cosine → cross-encoder |

---

## Hình 1 — `fig:three-levels`: Ba mức tích hợp thông tin với LLM

**Caption trong report:** *"Ba mức tích hợp thông tin với mô hình ngôn ngữ lớn. Tri thức càng trừu
tượng và tinh lọc thì phạm vi áp dụng càng rộng (phỏng theo chen2024ari)."*

Dạng kim tự tháp 3 tầng, hai trục mũi tên hai bên: càng lên cao càng trừu tượng/tinh lọc, và phạm
vi áp dụng càng rộng.

```
 Mức trừu tượng,                                                        Phạm vi
 độ tinh lọc                                                            áp dụng
      ▲                      ┌─────────────────┐                           ▲
      │                      │   TRỪU TƯỢNG    │  hướng dẫn phương pháp    │
      │  cao                 │   (Abstract)    │  luận  →  ARI             │  rộng
      │                      └─────────────────┘                           │
      │                 ┌───────────────────────────┐                      │
      │  vừa            │        VÍ DỤ MẪU          │  học trong ngữ cảnh  │  vừa
      │                 │        (Exemplar)         │  (few-shot, CoT)     │
      │                 └───────────────────────────┘                      │
      │            ┌─────────────────────────────────────┐                 │
      │  thấp      │          TRI THỨC CỤ THỂ            │  truy hồi sự    │  hẹp
      │            │            (Specific)               │  kiện (RAG,     │
      │            └─────────────────────────────────────┘  KAPING)        │
```

**Ghi chú TikZ:**
- 3 node `trapezium` (hoặc 3 hình chữ nhật bo góc xếp chồng thu hẹp dần) + 2 mũi tên dọc hai bên
  bằng `\draw[->]` kèm nhãn xoay `rotate=90`.
- Tô màu đậm dần từ dưới lên (ví dụ 3 sắc độ của một màu) để nhấn "tinh lọc dần".
- Có thể đánh dấu tầng trên cùng bằng viền đậm/nhãn "ARI (khóa luận này)" vì đây là luận điểm
  của Chương 1.

---

## Hình 2 — `fig:bi-cross`: Bi-encoder vs Cross-encoder

**Caption trong report:** *"So sánh bi-encoder (mã hóa độc lập hai đầu vào rồi đo cosine) và
cross-encoder (mã hóa đồng thời cặp đầu vào để nắm bắt tương tác ngữ cảnh)."*

Hai cột song song:

```
          BI-ENCODER                                 CROSS-ENCODER
   (mã hóa ĐỘC LẬP từng vế)                   (mã hóa ĐỒNG THỜI cả cặp)

    văn bản a      văn bản b               [CLS] a [SEP] b [SEP]
        │              │                   (nối thành MỘT chuỗi)
        ▼              ▼                              │
   ┌─────────┐    ┌─────────┐                         ▼
   │  BERT   │    │  BERT   │                   ┌───────────┐
   └─────────┘    └─────────┘                   │   BERT    │ ← self-attention
        │              │                        └───────────┘   xuyên cặp a–b
        ▼              ▼                              │
       e_a            e_b                             ▼
        └──── cos ─────┘                       vector tại [CLS]
              │                                       │
              ▼                                       ▼
     score = cos(e_a, e_b)                     Linear  +  σ (sigmoid)
                                                      │
                                                      ▼
                                               score ∈ (0, 1)

 ✓ nhanh: e_a, e_b tính trước, lưu được      ✓ chính xác: nắm tương tác a–b
 ✗ bỏ lỡ tương tác trực tiếp giữa a và b     ✗ chậm: mỗi cặp một lượt BERT
```

**Đối chiếu:** khớp Công thức (2.x) `eq:crossencoder` trong `Chapter2/chapter2.tex:392–396`;
ở mức background nên giữ "BERT" tổng quát (bản cài đặt cụ thể dùng PhoBERT — thể hiện ở Hình 5).

**Ghi chú TikZ:**
- Hai `scope` đặt cạnh nhau, mỗi bên một cột; node BERT dùng cùng style để thấy "cùng một mô hình,
  khác cách ghép đầu vào".
- Dòng ✓/✗ chuyển thành hai dòng chú thích nhỏ dưới mỗi cột (`\node[font=\scriptsize]`).

---

## Hình 3 — `fig:architecture`: Kiến trúc tổng thể hệ thống

**Caption trong report:** *"Kiến trúc tổng thể: pha tương tác dựa trên tri thức và pha suy luận
trừu tượng"* — yêu cầu vẽ theo Figure 3 của paper ARI, **luồng học nét liền `──▶`, luồng suy luận
nét đứt `┄┄▶`**.

Bố cục 3 khối: (a) quá trình học, (b) quá trình suy luận, (c) vòng lặp suy luận dùng chung —
tương tác hai pha ở mỗi bước.

### (a) Quá trình học — nét liền `──▶`

```
 Tập câu hỏi mẫu  (N = 200, lấy mẫu phân tầng theo loại câu hỏi)
      │
      ▼
 ┌───────────────────────────────┐   chạy với phương pháp luận mặc định
 │ VÒNG LẶP SUY LUẬN — xem (c)   │   (fallback), ghi lại từng bước
 └───────────────────────────────┘
      │
      ▼
 Trace lịch sử H_q — gồm cả lời giải ĐÚNG lẫn SAI          (history_records.json)
      │
      │  khuôn mẫu hóa câu hỏi: thay {entity}, {relation}, {time}
      │  (để phân cụm theo CẤU TRÚC suy luận, không theo chủ đề)
      ▼
 Nhúng vector  ──▶  K-means (k = 4 cụm)
      │
      ▼
 Mỗi cụm C:  ví dụ ĐÚNG (≤3)  +  ví dụ SAI (≤3)  ──▶  LLM chắt lọc  ──▶  M_C
      │
      ▼
 ┌───────────────────────────────────────────────────────┐
 │ BỘ NHỚ PHƯƠNG PHÁP LUẬN            (memory_bank.json)  │
 │   cụm 1: (tâm cụm μ₁, M_C₁)  …  cụm k: (μ_k, M_Ck)     │
 └───────────────────────────────────────────────────────┘
```

### (b) Quá trình suy luận — nét đứt `┄┄▶`

```
 Câu hỏi mới ┄┄▶ khuôn mẫu hóa + nhúng ┄┄▶ tìm tâm cụm GẦN NHẤT ┄┄▶ lấy M_C của cụm
                                            (Euclid, trên bộ nhớ ở (a))    ┆
      ┌────────────────────────────────────────────────────────────────────┘
      ▼
 ┌───────────────────────────────┐
 │ VÒNG LẶP SUY LUẬN — xem (c)   │ ┄┄▶  Đáp án
 └───────────────────────────────┘
```

### (c) Vòng lặp suy luận — tương tác hai pha ở MỖI bước (tối đa 5 bước)

```
 ┌── PHA DỰA TRÊN TRI THỨC (knowledge-based) ──────┐   ┌── PHA SUY LUẬN TRỪU TƯỢNG ─────────┐
 │                                                 │   │      (knowledge-agnostic)          │
 │  Câu hỏi ──▶ liên kết thực thể ──▶ seed (QID)   │   │                                    │
 │                     │                           │   │   Phương pháp luận M_C             │
 │                     ▼                           │   │   (từ bộ nhớ; học thì dùng         │
 │   ĐỒ THỊ TRI THỨC THỜI GIAN (s, r, o, [tb,te])  │   │    phương pháp luận mặc định)      │
 │                     │                           │   │              │                     │
 │                     ▼                           │   │              ▼                     │
 │   Liệt kê hành động khả thi                     │   │      ┌───────────────┐             │
 │   (9 thao tác nguyên tử; khử trùng lặp,         │   │      │      LLM      │             │
 │    cấm lặp lại hành động cũ; cap 80)            │   │      │ chọn hành động│             │
 │                     │                           │   │      └───────────────┘             │
 │                     ▼                           │   │         ▲         │                │
 │   LỌC HÀNH ĐỘNG top-K  ── danh sách ứng viên ───┼───┼─────────┘         │                │
 │   (cosine top-12, hoặc cosine top-30            │   │                   │                │
 │    + cross-encoder top-12 — xem Hình 5)         │   │          "Action: … / Reason: …"   │
 │                     ┌───────────────────────────┼───┼───────────────────┘                │
 │                     ▼                           │   └────────────────────────────────────┘
 │   THỰC THI hành động trên đồ thị                │
 │        │                                        │        Học:      LLM = GPT-4o
 │        ├── cập nhật tập thực thể + lịch sử ──▶ (quay     Suy luận: LLM = Qwen3-14B (Ollama)
 │        │   lại đầu bước, tối đa 5 bước)         │        Nhúng:    nomic-embed-text
 │        │                                        │
 │        └── nếu chọn answer(…) ──▶ DỪNG ──▶ Đáp án
 └─────────────────────────────────────────────────┘
```

**Đối chiếu code:**

| Thành phần trong hình | Code |
|---|---|
| Lấy mẫu phân tầng N=200 | `ari/learn.py:16` (`stratified_sample`), `config.N_MEMORY_SAMPLES` |
| Vòng lặp suy luận ≤ 5 bước | `ari/agent.py:165` (`run_question`), `config.MAX_REASONING_STEPS = 5` |
| Liệt kê hành động (initial + followup + answer) | `ari/enumerate_actions.py:37,93,125` |
| 9 thao tác nguyên tử | `ari/actions.py:49–107` (`get_tail/head_entity, get_time, get_before/after/between, get_first/last, answer`) |
| Khử trùng lặp + cấm chọn lại + cap 80 | `ari/agent.py:216–227`, `config.MAX_CANDIDATES_PER_RELATION = 80` |
| Lọc cosine top-K / top-N | `ari/agent.py:228–247`, `enumerate_actions.filter_actions` |
| Khuôn mẫu hóa câu hỏi `{entity}/{relation}/{time}` | `ari/memory.py:23` (`clean_question`), ưu tiên trường `template` |
| K-means k=4 (sklearn, k-means++, n_init=10) | `ari/memory.py:82`, `config.N_CLUSTERS = 4` |
| Chắt lọc M_C từ ví dụ đúng + sai (≤3 mỗi loại) | `ari/memory.py:171` (`induce_methodology`) |
| Chọn cụm gần nhất (Euclid) lúc suy luận | `ari/memory.py:253` (`select_methodology`) |
| LLM học = GPT-4o, suy luận = qwen3:14b | `ari/learn.py:38–41`, `ari/config.py:12,20` |

**Ghi chú TikZ:**
- Hai node `fit` lớn cho hai pha, đặt cạnh nhau; bộ nhớ phương pháp luận là một node hình trụ
  (`cylinder`) nằm trong pha trừu tượng; TKG là node trụ nằm trong pha tri thức.
- Style: `learn/.style={->, thick}` (nét liền) và `infer/.style={->, thick, dashed}` — khớp yêu cầu
  caption. Thêm legend nhỏ góc hình.
- ✅ **Đã chốt (02/07/2026): gộp cả (a)(b)(c) vào MỘT hình** như Figure 3 của paper: khối (c)
  đặt giữa, luồng học (a) đi vòng phía trên bằng nét liền, luồng suy luận (b) đi phía dưới bằng
  nét đứt, cả hai cùng trỏ vào (c). Ba panel ở trên chỉ là cách trình bày nháp cho dễ đọc.

---

## Hình 4 — `fig:entity-linking`: Liên kết thực thể cho câu hỏi mở

**Caption trong report:** *"NER tiếng Việt trích cụm thực thể, sau đó khớp về mã định danh qua tìm
kiếm tương đồng trong cơ sở dữ liệu vector."*

> ✅ **Đã chốt (02/07/2026):** thực nghiệm cuối dùng **bộ so khớp chuỗi con**
> (`ari/ner.py::link_entities`) — hình vẽ theo code, và **mô tả trong report sẽ sửa lại cho khớp**
> (giải quyết luôn todo ở `chapter4.tex:410`; repo không có code NER electra hay vector DB).

### Bản chính — so khớp chuỗi con (`ari/ner.py:21`)

```
  "Ai là tổng thống đầu tiên của Hoa Kỳ?"
        │
        ▼
 ┌──────────────────────────────────────┐
 │ ① Chuẩn hóa câu hỏi                  │   NFC + lowercase + gộp khoảng trắng
 └──────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────┐        ┌─────────────────────────────┐
 │ ② Giới hạn không gian tìm kiếm       │  ◀──   │  ĐỒ THỊ TRI THỨC            │
 │   chỉ các QID tham gia QUAN HỆ       │        │  chỉ mục kg.by_r[relation]  │
 │   của câu hỏi                        │        └─────────────────────────────┘
 └──────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────┐
 │ ③ So khớp nhãn thực thể với câu      │   (1) nhãn là CHUỖI CON của câu
 │                                      │       → ưu tiên nhãn DÀI nhất
 │                                      │   (2) fallback: mọi token của nhãn
 │                                      │       đều có mặt trong câu
 └──────────────────────────────────────┘
        │   "Hoa Kỳ" ⊂ câu hỏi
        ▼
 ④ Danh sách QID ứng viên (tối đa 6–8), xếp theo độ dài nhãn giảm dần
    ⇒  { Q30 (Hoa Kỳ), … }
```

Lưu ý cho phần chữ đi kèm: câu hỏi CronQ-VN đã có sẵn trường `entities`, nên bộ liên kết này chỉ
được gọi với **câu hỏi mở** do người dùng nhập (`ari/agent.py:195–197`).

**Ghi chú TikZ:** pipeline dọc 4 node đánh số ①–④, KG vẽ node `cylinder` bên phải trỏ vào bước ②;
ví dụ minh họa chạy bằng chữ nghiêng nhỏ dọc theo các mũi tên. Pipeline NER + VectorDB trong report
cũ sẽ bỏ (hoặc chuyển thành một câu "hướng phát triển" không kèm hình).

---

## Hình 5 — `fig:crossencoder`: Bộ lọc hành động hai tầng

**Caption trong report:** *"Bộ lọc hành động hai tầng đề xuất: cosine chọn rộng, cross-encoder
xếp hạng lại theo ngữ cảnh lịch sử."*

```
 Toàn bộ hành động ứng viên tại bước t   (sau liệt kê + khử trùng lặp, ≤ 80)
        │
        ▼
 ┌───────────────────────────────────────────────┐
 │ TẦNG 1 — COSINE, chọn RỘNG                    │   so với CÂU HỎI GỐC,
 │ cos( nhúng(hành động), nhúng(câu hỏi) )       │   KHÔNG nhìn lịch sử
 └───────────────────────────────────────────────┘
        │   giữ top-N = 30 ứng viên
        ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │ TẦNG 2 — CROSS-ENCODER, xếp hạng lại theo NGỮ CẢNH                │
 │                                                                   │
 │   h  =  câu hỏi [SEP] Bước 0: hành động → kết quả [SEP] Bước 1: … │
 │        (lịch sử suy luận, thực thể nén "2 đầu + 1 cuối")          │
 │   a  =  mô tả hành động ứng viên (đã Việt hóa, tách từ pyvi)      │
 │                                                                   │
 │   [CLS] h [SEP] a [SEP] ──▶ PhoBERT ──▶ Linear + σ ──▶ score(a,h) │
 │                             (vinai/phobert-base, max_len 256)     │
 └───────────────────────────────────────────────────────────────────┘
        │   sắp giảm dần theo score, giữ top-K = 12
        ▼
 Danh sách hành động cuối cùng đưa cho LLM chọn  (pha suy luận trừu tượng)
```

Kèm theo (nếu cần cho §4.6.3) — **nguồn dữ liệu huấn luyện** của bộ chấm điểm:

```
  positive:  hành động trên GOLD-PATH (tái dựng từ đồ thị tri thức, ce_goldpath)
  negative:  các hành động khác trong pool cùng bước
  hard neg:  hành động LLM đã chọn trong các trace SAI (history_records.json)
                    │
                    ▼   split theo CÂU HỎI (tránh leak), val 15%
       fine-tune PhoBERT cross-encoder — BCE loss
       (mặc định ce_train.py: 4 epoch, batch 16, lr 2e-5)
```

**Đối chiếu code:**

| Thành phần | Code |
|---|---|
| Hai tầng cosine 30 → CE 12 | `ari/agent.py:228–247`; `config.CE_COSINE_TOPN = 30`, `TOP_K_ACTIONS = 12` |
| Ghép chuỗi h, a + tách từ | `ari/ce_serialize.py:111` (`build_context_text`), `:31` (`action_to_vi`), `:126` (`segment`) |
| Chấm điểm + rerank | `ari/ce_rerank.py:28,37` |
| Sinh dữ liệu huấn luyện | `ari/ce_data.py:59` (gold-path), `:108` (hard negatives) |
| Huấn luyện | `ari/ce_train.py` (PhoBERT, split theo câu hỏi, Hit@K/MRR trên val) |

> ✅ **Đã chốt (02/07/2026):** report (công thức `eq:ce-score` và hình) đang viết
> `[CLS] a [SEP] h [SEP]`, nhưng code `ce_rerank.score` đưa cặp `(context, action)` → mô hình nhận
> `[CLS] h [SEP] a [SEP]` (lịch sử trước, hành động sau). Hình vẽ **theo code**, và sẽ **sửa công
> thức `eq:ce-score` (chapter4.tex:446–450) cùng đoạn mô tả ở `chapter2.tex`/`chapter4.tex` cho
> khớp** — model đã huấn luyện theo thứ tự h–a nên không đổi code.

**Ghi chú TikZ:** hai tầng vẽ thành hai khối lớn xếp dọc, mũi tên giữa các tầng ghi rõ "top-30" /
"top-12"; bên trong tầng 2 vẽ chuỗi token `[CLS] h [SEP] a [SEP]` như một hàng ô vuông nhỏ đi vào
node PhoBERT — nhất quán về style với Hình 2 (cross-encoder là trường hợp cụ thể hóa của hình đó).

---

## Bonus — minh họa TKG có nút và cạnh

Không nằm trong 5 todo TikZ, nhưng hai todo khác cũng là hình vẽ và nhiều khả năng vẽ TikZ luôn:
`chapter1.tex:46` (*"thay bằng hình minh họa TKG đẹp hơn"*) và `chapter2.tex:67` (*"thay bằng hình
đồ thị trực quan có nút và cạnh"*). Một phác thảo dùng được cho cả hai, lấy đúng ví dụ Gerald Ford
của Chương 1:

```
 ┌───────────────┐  chức vụ, [1969–1974]   ┌─────────────────────┐
 │ Richard Nixon │ ───────────────────────▶│ Tổng thống Hoa Kỳ   │
 └───────────────┘                         └─────────────────────┘
                                                      ▲
 ┌───────────────┐  chức vụ, [1974–1977]              │
 │  Gerald Ford  │ ────────────────────────────────────┘
 └───────────────┘

 ┌──────────────────────┐  thời điểm kết thúc: 1975   ┌────────┐
 │ Chiến tranh Việt Nam │ ───────────────────────────▶│  1975  │
 └──────────────────────┘                             └────────┘

 Suy luận: kết thúc chiến tranh (1975) ∈ [1974–1977] ⇒ đáp án: Gerald Ford
```

Mỗi cạnh là một bộ bốn (s, r, o, τ) đúng như định dạng KG trong `cronqvn` (τ = [t_b, t_e], cho
phép t_e rỗng). Khi vẽ TikZ có thể tô đậm (highlight) đường suy luận 2 bước để khớp ví dụ 3 bước
trong `fig:temporal-example`.

---

## Các quyết định đã chốt (Danh xác nhận 02/07/2026)

1. **Hình 4 — liên kết thực thể:** vẽ theo **bộ so khớp chuỗi con** (code `ari/ner.py` hiện tại);
   sửa lại mô tả NER + VectorDB trong report cho khớp code (đóng luôn todo `chapter4.tex:410`).
2. **Hình 5 — thứ tự ghép cặp:** vẽ theo code `[CLS] h [SEP] a [SEP]`; sửa công thức
   `eq:ce-score` và đoạn mô tả trong report theo code (model đã huấn luyện theo thứ tự h–a).
3. **Hình 3 — bố cục:** gộp luồng học + luồng suy luận + vòng lặp hai pha vào **một hình duy
   nhất** theo đúng Figure 3 của paper ARI.

**Việc còn lại khi chuyển sang TikZ:** ngoài vẽ 5 hình, cần sửa 2 chỗ chữ trong report cho khớp
quyết định 1 và 2 (mục §4.5.2 liên kết thực thể, và công thức/mô tả cross-encoder §4.6.2).
