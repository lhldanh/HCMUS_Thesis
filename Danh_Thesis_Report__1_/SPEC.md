# SPEC — Báo cáo Khóa luận Tốt nghiệp của Liêu Hải Lưu Danh

> **Đề tài:** Nghiên cứu phương pháp trả lời câu hỏi có ràng buộc về thời gian sử dụng
> suy luận trừu tượng (*Abstract Reasoning for Temporal Question Answering*).
> **SV:** Liêu Hải Lưu Danh — MSSV 22120459. **GVHD:** TS. Nguyễn Hồng Bửu Long, TS. Lương An Vinh.
> **Loại:** Nghiên cứu. **Thời gian:** 2/2026 – 7/2026.

Tài liệu này là *bản đặc tả viết* (writing spec) cho toàn bộ phần thân báo cáo. Mỗi chương
ghi rõ: mục tiêu, dàn ý mục con, **ngân sách trang**, nguồn dữ liệu để viết, hình/bảng cần có,
và các chỗ **[PLACEHOLDER]** sẽ điền số liệu sau.

---

## 0. Quy ước chung

- **Ngôn ngữ:** Tiếng Việt học thuật. Thuật ngữ chuyên ngành giữ tiếng Anh trong ngoặc khi xuất hiện lần đầu, ví dụ: "đồ thị tri thức thời gian (*Temporal Knowledge Graph* — TKG)".
- **Template:** theo `Thesis Final Report/` (KLTN HCMUS): `extreport` 14pt, giãn dòng 1.5, lề T30/B25/L30/R20 mm, font T5 tiếng Việt, bib **IEEE** (`biblatex`).
- **Tổng trang thân (Ch1–Ch6):** mục tiêu **≥ 70 trang**.
- **Trích dẫn:** dùng `\cite{key}` với `References/references.bib`. Tất cả tài liệu tiếng Anh → in một danh mục thống nhất (như `main.tex` của CONGA).
- **Đánh dấu chưa hoàn tất:** mọi số liệu thực nghiệm chưa chạy ghi `[PLACEHOLDER: ...]` và tô bằng macro `\todo{}` (định nghĩa sẵn) để dễ tìm.
- **Quy ước tên:** ARI (Abstract Reasoning Induction), TKGQA (Temporal KG Question Answering), CronQ-VN (bộ dữ liệu tiếng Việt do Danh xây), KG/TKG, LLM.

## 0.1 Nguồn tư liệu (ánh xạ để viết)

| Nguồn | Vị trí | Dùng cho chương |
|---|---|---|
| Paper ARI gốc (Chen et al., ACL 2024) | `References/2024.acl-long.267.pdf`, `ari-paper-md (1).md` | Ch2, Ch3, Ch4 |
| Code ARI tái hiện (tiếng Việt, Ollama) | `HCMUS_Thesis/.../ari/*.py` + `ari/README.md` | Ch4, Ch5 |
| Pipeline dataset CronQ-VN | `HCMUS_Thesis/.../cronqvn/*.py` + `cronqvn/README.md` | Ch4, Ch5 |
| Code paper gốc (đối chiếu) | `HCMUS_Thesis/.../ARI-QA/` | Ch3, Ch5 |
| Slide weekly "Vietnamese TQA Datasets / NER" | `References/Vietnamese_NER.pdf` | Ch4 (dataset, NER) |
| Slide weekly "Pipeline hiện tại / Giải pháp Cross-encoder" | `References/Cross_En_ChuaLam.pdf` | Ch4 (cải tiến), Ch6 |
| Đề cương | `References/Đề Cương - Liêu Hải Lưu Danh.pdf` | Ch1 (mục tiêu, phạm vi) |

## 0.2 Ba đóng góp xuyên suốt (kim chỉ nam)

1. **CronQ-VN** — bộ dữ liệu TKGQA tiếng Việt đầu tiên xây từ Wikidata (238K facts, 37.5K thực thể, 271 quan hệ; 8 quan hệ × 5 loại câu hỏi để sinh QA; dịch nhãn thiếu bằng LLM).
2. **Thích nghi ARI cho tiếng Việt** chạy hoàn toàn bằng **LLM cục bộ** (Ollama + Qwen2.5) thay cho API thương mại; **liên kết thực thể (entity linking)** cho câu hỏi mở bằng NER tiếng Việt (`NlpHUST/ner-vietnamese-electra-base`) + VectorDB cosine.
3. **Cải tiến bộ lọc hành động bằng Cross-Encoder** thay cho lọc cosine Top-K "mù ngữ cảnh" → bộ lọc *nhận biết ngữ cảnh* `[CLS]action[SEP]history[SEP]` → BERT → sigmoid. *(Đề xuất; kết quả = [PLACEHOLDER].)*

---

## Chương 1 — Giới thiệu  ·  ngân sách: **8 trang**

**Mục tiêu:** đặt vấn đề, nêu động lực (đặc biệt bối cảnh tiếng Việt), chốt mục tiêu/câu hỏi nghiên cứu, liệt kê đóng góp, vẽ cấu trúc khóa luận.

- **1.1 Bối cảnh & động lực** (~2.5 tr): LLM bùng nổ trong hỏi–đáp; nhưng yếu ở suy luận thời gian. Ví dụ kinh điển: *"Tổng thống Hoa Kỳ khi Chiến tranh Việt Nam kết thúc là ai?"* (lấy từ đề cương). Tri thức tiến hóa theo thời gian.
- **1.2 Hai hạn chế cốt lõi của LLM** (~1 tr): (i) *thiếu tri thức thời gian* (tham số đóng băng sau train), (ii) *thiếu suy luận thời gian phức tạp nhiều bước*. (Dựa §1 paper.)
- **1.3 Khoảng trống cho tiếng Việt** (~1 tr): chưa có bộ dữ liệu TKGQA tiếng Việt; các phương pháp/LLM API tốn phí, khó triển khai cục bộ; NER tiếng Việt cho liên kết thực thể chưa được khai thác cho TKGQA.
- **1.4 Mục tiêu & câu hỏi nghiên cứu** (~1 tr): RQ1 ARI có cải thiện so với LLM suy luận trực tiếp trên TKGQA tiếng Việt? RQ2 đóng góp của từng thành phần (ablation)? RQ3 bộ lọc cross-encoder nhận biết ngữ cảnh có tốt hơn cosine?
- **1.5 Đóng góp của khóa luận** (~1.5 tr): liệt kê 3 đóng góp ở §0.2 + phạm vi (TKGQA, đồ thị con, dữ liệu MultiTQ/CronQuestions tham chiếu + CronQ-VN tự xây).
- **1.6 Cấu trúc khóa luận** (~1 tr): tóm tắt 6 chương.

**Hình/bảng:** Hình 1.1 — ba mức tích hợp thông tin với LLM (Specific/Exemplar/Abstract — phỏng Figure 1 paper). Hình 1.2 — ví dụ câu hỏi đa bước minh họa.
**Placeholder:** không.

---

## Chương 2 — Cơ sở lý thuyết  ·  ngân sách: **15 trang**

**Mục tiêu:** trang bị nền tảng để hiểu phương pháp ở Ch4. Viết theo kiểu "kiến thức nền", không phải khảo sát công trình (để dành Ch3).

- **2.1 Đồ thị tri thức và đồ thị tri thức thời gian** (~2 tr): định nghĩa KG (E, R, F); TKG K=(E,R,T,F), quan hệ kèm mốc/khoảng thời gian; Wikidata làm nguồn; qualifier thời gian P580/P582/P585.
- **2.2 Bài toán TKGQA — định nghĩa hình thức** (~1.5 tr): cho TKG K + câu hỏi q → trả về thực thể hoặc mốc thời gian. Phân loại câu hỏi simple/complex, entity/time. (Dựa §3.1 paper.)
- **2.3 Mô hình ngôn ngữ lớn & học trong ngữ cảnh** (~2 tr): kiến trúc Transformer (tóm tắt), sinh tự hồi quy, in-context learning, prompt; hiện tượng ảo giác (hallucination).
- **2.4 Tăng cường tri thức cho LLM** (~2 tr): RAG; tiêm tri thức tường minh (prompt) vs ngầm; KG-augmented prompting. Nền cho baseline KG-RAG.
- **2.5 Suy luận có cấu trúc với LLM** (~1.5 tr): Chain-of-Thought; ReAct (reason+act); agent tương tác môi trường. Nền cho baseline CoT-KB/ReAct-KB.
- **2.6 Bộ nhớ và học từ kinh nghiệm** (~1.5 tr): bộ nhớ ngoài cho LLM; thuyết kiến tạo (constructivism) — nền triết học của ARI (Piaget; Savery & Duffy; Kirschner).
- **2.7 Phân cụm K-means & biểu diễn ngữ nghĩa** (~1.5 tr): embedding câu, độ tương đồng cosine, thuật toán K-means (dùng phân loại lịch sử suy luận trong ARI).
- **2.8 Cross-encoder vs bi-encoder** (~1.5 tr): bi-encoder (cosine, nhanh, mã hóa độc lập) vs cross-encoder (mã hóa cặp `[CLS]a[SEP]b[SEP]`, chính xác hơn, có ngữ cảnh). Nền cho đóng góp #3.
- **2.9 Nhận dạng thực thể có tên (NER) tiếng Việt** (~1 tr): bài toán NER; mô hình `electra`/PhoBERT; vai trò trong liên kết thực thể.

**Hình/bảng:** Hình 2.1 — minh họa một TKG nhỏ (đa quan hệ thời gian). Hình 2.2 — sơ đồ bi-encoder vs cross-encoder. Bảng 2.1 — ký hiệu toán học dùng xuyên suốt.
**Placeholder:** không.

---

## Chương 3 — Các công trình liên quan  ·  ngân sách: **9 trang**

**Mục tiêu:** khảo sát có hệ thống, kết thúc bằng việc *định vị* đề tài (khoảng trống).

- **3.1 Các mô hình TKGQA truyền thống** (~2.5 tr): TEQUILA (phân rã câu hỏi + ràng buộc thời gian); CronKGQA & EmbedKGQA (nhúng TKG); TempoQR (EaE, temporal scope); MultiQA/subgraph reasoning (Chen et al.). Hạn chế: phụ thuộc luật tay/biểu diễn học, yếu với suy luận phức tạp.
- **3.2 LLM suy luận với tri thức ngoài** (~2 tr): KAPING, CoK, ChatKBQA, Symbol-LLM, ToG. Hai nhánh tiêm tri thức tường minh/ngầm; hạn chế (nhiễu, giới hạn ngữ cảnh, tốn fine-tune).
- **3.3 LLM suy luận với bộ nhớ** (~1.5 tr): MemoChat, Reflexion, MemPrompt, RLEM, Thought Propagation. Hạn chế: tiếp nhận lịch sử thụ động, chưa *kiến tạo* tri thức trừu tượng → ARI khắc phục.
- **3.4 Bộ dữ liệu TKGQA** (~1.5 tr): CronQuestions (Wikidata, Saxena 2021), MultiTQ (ICEWS, đa hạt thời gian, Chen 2023). **Khoảng trống: chưa có dữ liệu tiếng Việt** → CronQ-VN.
- **3.5 Định vị đề tài** (~1.5 tr): bảng so sánh; chốt 3 khoảng trống mà khóa luận lấp (ngôn ngữ, LLM cục bộ, lọc hành động nhận biết ngữ cảnh).

**Hình/bảng:** Bảng 3.1 — so sánh phương pháp (loại, dùng LLM?, dùng bộ nhớ?, ngôn ngữ, dữ liệu). Bảng 3.2 — so sánh bộ dữ liệu (nguồn KG, #câu hỏi, hạt thời gian, ngôn ngữ).
**Placeholder:** không.

---

## Chương 4 — Phương pháp đề xuất  ·  ngân sách: **20 trang** (chương trọng tâm)

**Mục tiêu:** mô tả đầy đủ hệ thống Danh xây — kiến trúc 2 pha + 3 đóng góp.

- **4.1 Tổng quan kiến trúc** (~2 tr): sơ đồ tổng thể 2 pha (knowledge-based ↔ knowledge-agnostic); luồng học (solid) và luồng suy luận (dashed). (Phỏng Figure 3 paper, vẽ lại bằng TikZ.)
- **4.2 Xây dựng bộ dữ liệu CronQ-VN** (~5 tr) — *đóng góp #1*:
  - 4.2.1 Trích xuất TKG từ Wikidata (`build_kg.py`): tải dump → 2 lượt quét → lọc fact thời gian (qualifier P580/582/585), strict VN label cả s và o → lọc quan hệ <200 fact, thực thể <2 fact. Số liệu: 238K facts / 37.5K thực thể / 271 quan hệ.
  - 4.2.2 Phủ tiếng Việt & dịch nhãn thiếu: 34% thực thể có nhãn VI, 77% quan hệ có nhãn VI → dịch phần thiếu bằng Qwen (`facts_vi/`, `*.vi.json`).
  - 4.2.3 Sinh câu hỏi (`generate.py`, `templates.py`): chọn 8 quan hệ giàu fact/đa lĩnh vực → 5 loại câu hỏi (simple_entity, simple_time, before_after, first_last, time_join) → ghép template → truy vấn KG lấy ground truth → lọc chất lượng (MAX_ANSWERS, MIN_LABEL_LEN, không self-ref, không leak, dedup).
  - 4.2.4 Lược đồ & ví dụ (schema JSON + bảng ví dụ mỗi loại câu hỏi).
- **4.3 Pha tương tác dựa trên tri thức (Knowledge-based)** (~4 tr):
  - 4.3.1 Nạp TKG vào RAM, chỉ mục đồ thị (`kg.py`); đồ thị con 1-hop G_{e_h} (Eq.1).
  - 4.3.2 Chín thao tác nguyên tử (Bảng 6 paper): getTailEntity, getHeadEntity, getTime, getBetween, getBefore, getAfter, getFirst, getLast, answer (`actions.py`).
  - 4.3.3 Liệt kê hành động ứng viên (Eq.2) + lọc khả thi (execution filter) + lọc Top-K theo cosine (Eq.3) (`enumerate_actions.py`).
- **4.4 Pha suy luận trừu tượng (Knowledge-agnostic)** (~3.5 tr) — lõi ARI:
  - 4.4.1 Lưu lịch sử suy luận H_q (Eq.4) (`memory.py`).
  - 4.4.2 Phân cụm K-means lịch sử → cụm C_H; chắt lọc *methodology* trừu tượng từ ví dụ đúng & sai (App. prompt).
  - 4.4.3 Suy luận với hướng dẫn: chọn cụm C* gần nhất (Eq.5), LLM(M_{C*}, q, P'_t) chọn action (Eq.6); vòng lặp Algorithm 1 (`agent.py`), trần 5 bước.
- **4.5 Thích nghi tiếng Việt** (~2 tr) — *đóng góp #2*:
  - 4.5.1 LLM cục bộ qua Ollama (qwen2.5:7b) + embedding `nomic-embed-text`; prompt tiếng Việt (`prompts.py`, `ollama_client.py`).
  - 4.5.2 Liên kết thực thể cho câu hỏi mở: NER `NlpHUST/ner-vietnamese-electra-base` → embedding → tìm cosine trong VectorDB nhãn thực thể → khớp QID (`ner.py`). Sơ đồ 4 bước (Question → NER → VectorDB → Matched).
- **4.6 Cải tiến: bộ lọc hành động bằng Cross-Encoder** (~3.5 tr) — *đóng góp #3*:
  - 4.6.1 Vấn đề của lọc cosine: so action với câu hỏi *gốc*, không biết đang ở bước nào → ranking bước 1 ≡ bước 4, dễ loại nhầm action đúng cho bước hiện tại.
  - 4.6.2 Đề xuất: cosine lấy *rộng* candidate → cross-encoder chọn Top-K *cuối*. Đầu vào `[CLS]action[SEP]history[SEP]`; history = câu hỏi + chuỗi action đúng đã thực thi; BERT → Linear(→1) → sigmoid → score∈(0,1). Học liên kết action–ngữ cảnh.
  - 4.6.3 Sinh dữ liệu huấn luyện cho scorer (cặp action–history dương/âm từ trace lịch sử), hàm mất mát, tích hợp vào vòng lặp agent. **[PLACEHOLDER: chi tiết cấu hình huấn luyện khi chạy].**

**Hình/bảng:** Hình 4.1 kiến trúc tổng thể; Hình 4.2 pipeline CronQ-VN (2 nhánh, phỏng slide); Hình 4.3 đồ thị con + liệt kê action; Hình 4.4 vòng lặp ARI (Algorithm 1, pseudo-code); Hình 4.5 liên kết thực thể NER→VectorDB; Hình 4.6 sơ đồ cross-encoder. Bảng 4.1 — 9 thao tác nguyên tử; Bảng 4.2 — 8 quan hệ chọn sinh câu hỏi; Bảng 4.3 — 5 loại câu hỏi + template ví dụ.
**Placeholder:** cấu hình huấn luyện cross-encoder (§4.6.3).

---

## Chương 5 — Thực nghiệm & Kết quả  ·  ngân sách: **14 trang**

**Mục tiêu:** thiết lập, baseline, độ đo, và (khi có số) trả lời RQ1–RQ3. **Phần lớn số liệu = [PLACEHOLDER].**

- **5.1 Bộ dữ liệu & thống kê** (~2 tr): thống kê CronQ-VN (số fact/thực thể/quan hệ; phân bố theo loại câu hỏi; tỉ lệ entity/time). Bảng thống kê đầy đủ (một phần đã có từ KG; phần phân bố câu hỏi = [PLACEHOLDER nếu chưa sinh đủ 30K]).
- **5.2 Thiết lập thực nghiệm** (~1.5 tr): LLM qwen2.5:7b, embedding nomic-embed-text, T=0.0; N_MEMORY_SAMPLES=200, K=10 cụm, trần 5 bước, Top-K=12, lấy mẫu phân tầng 200 câu test. Phần cứng, thời gian chạy.
- **5.3 Baseline & độ đo** (~1.5 tr): LLM-only, KG-RAG, CoT-KB, ReAct-KB vs ARI (đối chiếu bảng 1 paper). Độ đo: accuracy tổng + theo qtype/answer_type/qlabel.
- **5.4 Kết quả tổng (RQ1)** (~2.5 tr): bảng accuracy ARI vs baseline trên CronQ-VN. **[PLACEHOLDER: toàn bộ số]** — khung bảng đã dựng sẵn, có chú thích cách điền.
- **5.5 Nghiên cứu cắt bỏ — ablation (RQ2)** (~2 tr): w/o Abstract Guidance, w/o History Cluster, w/o Action Filter, w/o Incorrect Examples. **[PLACEHOLDER]**.
- **5.6 Phân tích bộ lọc Cross-Encoder (RQ3)** (~2 tr): so cosine Top-K vs cross-encoder Top-K (accuracy, recall action đúng, số bước trung bình). **[PLACEHOLDER]**.
- **5.7 Hiệu quả suy luận & phân tích lỗi** (~1.5 tr): số bước trung bình w/ vs w/o hướng dẫn trừu tượng; 3 nhóm lỗi điển hình (thực thể sai, methodology kém chất lượng, LLM lệch định dạng). **[PLACEHOLDER số; mô tả định tính có thể viết trước]**.
- **5.8 Bàn luận & hạn chế** (~1 tr): phụ thuộc năng lực LLM nhỏ; chi phí suy luận nhiều bước; phạm vi suy luận thời gian.

**Hình/bảng:** Bảng 5.1 thống kê CronQ-VN; Bảng 5.2 cấu hình; Bảng 5.3 kết quả tổng; Bảng 5.4 ablation; Bảng 5.5 cross-encoder; Hình 5.1 accuracy vs số cụm (phỏng Fig.6); Hình 5.2 số bước trung bình.
**Placeholder:** 5.4, 5.5, 5.6 toàn bộ số; một phần 5.1, 5.7.

---

## Chương 6 — Kết luận & hướng phát triển  ·  ngân sách: **4 trang**

- **6.1 Tổng kết** (~1.5 tr): nhắc lại bài toán, 3 đóng góp, kết quả chính **[PLACEHOLDER số tóm tắt]**.
- **6.2 Ý nghĩa** (~0.5 tr): bộ dữ liệu + hệ thống TKGQA tiếng Việt chạy cục bộ; hướng kết hợp bộ nhớ kinh nghiệm + LLM.
- **6.3 Hạn chế** (~0.5 tr): nhắc lại từ §5.8 cô đọng.
- **6.4 Hướng phát triển** (~1.5 tr): hoàn thiện & huấn luyện cross-encoder; mở rộng quan hệ/đa hạt thời gian; suy luận đa bước sâu hơn; fine-tune LLM tiếng Việt; mở rộng sang dữ liệu không-thời gian.

**Placeholder:** số kết quả tóm tắt.

---

## Phụ lục (không tính vào 70 trang thân)

- A. Toàn bộ prompt tiếng Việt (induction + decision).
- B. Danh sách 271 quan hệ / 8 quan hệ sinh câu hỏi + nhãn.
- C. Ví dụ trace suy luận đầy đủ (vài câu mỗi loại).

## Tiến độ viết (checklist)

- [x] Skeleton LaTeX + main.tex + references.bib + SPEC
- [ ] Chương 1 — Giới thiệu
- [ ] Chương 2 — Cơ sở lý thuyết
- [ ] Chương 3 — Công trình liên quan
- [ ] Chương 4 — Phương pháp đề xuất
- [ ] Chương 5 — Thực nghiệm & Kết quả
- [ ] Chương 6 — Kết luận
- [ ] Đọc soát toàn bộ + điền số liệu thật (sau khi chạy eval)
