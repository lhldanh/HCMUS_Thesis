"""Sinh Appendix/appendix1.tex (code-derived) cho báo cáo.
Chạy từ repo root: PYTHONPATH=. python3 scratchpad/gen_appendix.py
"""
import json, importlib.util, sys
from ari import prompts

OUT = "Danh_Thesis_Report__1_/Appendix/appendix1.tex"


def tex_escape(s: str) -> str:
    rep = {'&': r'\&', '%': r'\%', '#': r'\#', '_': r'\_',
           '$': r'\$', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}',
           '^': r'\textasciicircum{}'}
    out = []
    for ch in s:
        out.append(rep.get(ch, ch))
    return ''.join(out)


def lst(title, code):
    return (f"\\subsection*{{{title}}}\n"
            "\\begin{lstlisting}\n" + code.rstrip() + "\n\\end{lstlisting}\n\n")


# ---- Section A: prompts ----
secA = "\\section{Toàn bộ prompt tiếng Việt}\n"
secA += ("Các prompt dưới đây được trích nguyên văn từ \\texttt{ari/prompts.py} "
         "(không chỉnh sửa). Phần tĩnh đặt ở \\emph{system prompt} để Ollama "
         "prefix-cache giữa các bước; phần động (câu hỏi/methodology/lịch sử/"
         "hành động) ở \\emph{user template}.\n\n")
secA += "\\subsubsection*{A.1 Prompt chọn hành động (decision)}\n\n"
secA += lst("System prompt", prompts.ACTION_SELECT_SYSTEM)
secA += lst("User template", prompts.ACTION_SELECT_TEMPLATE)
secA += "\\subsubsection*{A.2 Prompt chắt lọc phương pháp (methodology induction)}\n\n"
secA += lst("System prompt", prompts.METHODOLOGY_SYSTEM)
secA += lst("User template", prompts.METHODOLOGY_TEMPLATE)
secA += "\\subsubsection*{A.3 Methodology mặc định (fallback)}\n\n"
secA += lst("FALLBACK\\_METHODOLOGY", prompts.FALLBACK_METHODOLOGY)
secA += "\\subsubsection*{A.4 Prompt các baseline}\n\n"
secA += lst("LLM-only (system / template)",
            prompts.LLM_ONLY_SYSTEM + "\n---\n" + prompts.LLM_ONLY_TEMPLATE)
secA += lst("KG-RAG (system / template)",
            prompts.KG_RAG_SYSTEM + "\n---\n" + prompts.KG_RAG_TEMPLATE)
secA += lst("CoT-KB (system / template)",
            prompts.COT_KB_SYSTEM + "\n---\n" + prompts.COT_KB_TEMPLATE)
secA += lst("ReAct-KB (system / template)",
            prompts.REACT_SYSTEM + "\n---\n" + prompts.REACT_TEMPLATE)


# ---- Section B: relations ----
spec = importlib.util.spec_from_file_location("cfg", "cronqvn/config.py")
cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
R = cfg.RELATIONS

secB = "\\section{Danh sách quan hệ}\n"
secB += (f"CronQ-VN giữ \\textbf{{271}} quan hệ sau bước lọc của \\texttt{{build\\_kg.py}}. "
         f"Trong số đó, \\textbf{{{len(R)}}} quan hệ giàu dữ kiện thuộc nhiều lĩnh "
         "vực được tuyển chọn để sinh câu hỏi (Bảng~\\ref{tab:gen-relations}). "
         "Danh sách đầy đủ 271 quan hệ kèm nhãn xem Bảng~\\ref{tab:all-relations}.\n\n")

# B.1 — 21 generation relations
secB += "\\begin{table}[htbp]\n\\centering\n\\caption{Các quan hệ dùng để sinh câu hỏi CronQ-VN.}\n"
secB += "\\label{tab:gen-relations}\n\\begin{tabular}{llll}\n\\toprule\n"
secB += "PID & Nhãn (EN) & Động từ (VI) & Danh từ (VI) \\\\\n\\midrule\n"
for pid, m in R.items():
    secB += (f"{pid} & {tex_escape(m['en'])} & {tex_escape(m['verb'])} & "
             f"{tex_escape(m['noun'])} \\\\\n")
secB += "\\bottomrule\n\\end{tabular}\n\\end{table}\n\n"

# B.2 — full 271 relations longtable
pid_labels = json.load(open("cronqvn/facts/pid_labels.json", encoding="utf-8"))
items = sorted(pid_labels.items(), key=lambda kv: int(kv[0][1:]))
secB += "\\begin{center}\n\\begin{longtable}{p{1.6cm} p{5.2cm} p{5.2cm}}\n"
secB += "\\caption{Toàn bộ 271 quan hệ trong CronQ-VN.}\\label{tab:all-relations}\\\\\n"
secB += "\\toprule PID & Nhãn gốc (EN) & Nhãn tiếng Việt \\\\ \\midrule\n\\endfirsthead\n"
secB += ("\\multicolumn{3}{c}{\\tablename\\ \\thetable\\ -- tiếp theo}\\\\\n"
         "\\toprule PID & Nhãn gốc (EN) & Nhãn tiếng Việt \\\\ \\midrule\n\\endhead\n")
secB += "\\midrule \\multicolumn{3}{r}{\\emph{tiếp trang sau}}\\\\\n\\endfoot\n\\bottomrule\n\\endlastfoot\n"
for pid, meta in items:
    src = meta.get("src_label") or ""
    vi = meta.get("label") or ""
    lang = meta.get("lang", "")
    vi_cell = tex_escape(vi) if lang == "vi" else "\\textit{(=EN)}"
    secB += f"{pid} & {tex_escape(src)} & {vi_cell} \\\\\n"
secB += "\\end{longtable}\n\\end{center}\n\n"


# ---- Section C: traces (still needs eval run) ----
secC = ("\\section{Ví dụ trace suy luận đầy đủ}\n"
        "\\todo{Vài ví dụ trace ARI hoàn chỉnh cho mỗi loại câu hỏi (lấy từ "
        "\\texttt{ari/artifacts/eval\\_ari.json} sau khi chạy \\texttt{ari.evaluate}).}\n")

content = ("\\chapter{Phụ lục}\n\\label{ch:appendix}\n\n" + secA + secB + secC)
open(OUT, "w", encoding="utf-8").write(content)
print("wrote", OUT, "chars:", len(content))
print("gen relations:", len(R), "| total relations:", len(items))
