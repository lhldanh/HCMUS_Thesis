"""Prompts (Vietnamese) for ARI on cronqvn."""

ACTION_SELECT_SYSTEM = (
    "Bạn là một tác tử suy luận trên đồ thị tri thức theo thời gian (TKG). "
    "Bạn KHÔNG cần biết tri thức thực tế: bạn chỉ chọn hành động phù hợp "
    "trong danh sách cho sẵn để hệ thống truy vấn TKG giúp bạn."
)

ACTION_SELECT_TEMPLATE = """Hãy chọn hành động kế tiếp để trả lời câu hỏi.

Các nhóm hàm khả dụng:
- Hàm thời gian: get_time(HEAD, REL, TAIL); get_before(LIST, T); get_after(LIST, T); get_between(LIST, T1, T2)
- Hàm thực thể: get_tail_entity(HEAD, REL, [T]); get_head_entity(TAIL, REL, [T])
- Hàm chọn lọc: get_first(LIST); get_last(LIST)
- Trả lời: answer(GIÁ_TRỊ)

Câu hỏi: {question}
Loại câu hỏi: {qtype}    Loại đáp án: {answer_type}

Phương pháp suy luận gợi ý (methodology):
{methodology}

Các bước đã thực hiện:
{history}

Các hành động khả dụng tại bước này (CHỈ được chọn một trong số này):
{actions}

Hãy chọn đúng MỘT hành động bằng cách lặp lại nguyên văn chuỗi nằm giữa hai dấu $.
Nếu đã có đủ thông tin, hãy chọn hành động $answer(...)$.

Định dạng đầu ra BẮT BUỘC:
Action: <hành động bạn chọn, bao trong dấu $>
Reason: <giải thích ngắn>
"""


METHODOLOGY_SYSTEM = (
    "Bạn là chuyên gia đúc kết phương pháp suy luận trên KG thời gian. "
    "Hãy rút ra hướng dẫn TRỪU TƯỢNG, không gắn vào dữ kiện cụ thể."
)

METHODOLOGY_TEMPLATE = """Phân tích các ví dụ ĐÚNG và SAI dưới đây để rút ra phương pháp tổng quát
giải các câu hỏi cùng loại. Hướng dẫn phải ở mức phương pháp luận, không kể tên
thực thể cụ thể.

Định nghĩa nhiệm vụ: Trả lời câu hỏi thời gian trên TKG bằng chuỗi hành động
nguyên tử (get_time, get_head_entity, get_tail_entity, get_before, get_after,
get_between, get_first, get_last, answer).

Ví dụ ĐÚNG:
{correct_examples}

Ví dụ SAI:
{incorrect_examples}

Hãy xuất theo đúng định dạng:

Overall Instruction:
<Mô tả phương pháp ở mức trừu tượng cho loại câu hỏi này.>

Step-by-step Guide:
1. <bước 1: chọn loại action nào, mục đích là gì>
2. <bước 2 ...>
3. <...>
"""


FALLBACK_METHODOLOGY = (
    "Overall Instruction: Trước tiên xác định thực thể chủ đề và quan hệ "
    "trong câu hỏi. Dùng get_head_entity hoặc get_tail_entity với ràng buộc "
    "thời gian (nếu có) để lấy danh sách ứng viên. Áp dụng get_first/get_last/"
    "get_before/get_after để lọc khi cần, rồi gọi answer.\n\n"
    "Step-by-step Guide:\n"
    "1. Xác định seed và relation từ câu hỏi.\n"
    "2. Truy vấn get_head_entity / get_tail_entity (kèm time nếu có).\n"
    "3. Nếu cần so sánh thời gian: get_before / get_after / get_first / get_last.\n"
    "4. Gọi answer với ứng viên còn lại."
)
