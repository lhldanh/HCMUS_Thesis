"""Prompts (Vietnamese) for ARI on cronqvn."""

ACTION_SELECT_SYSTEM = (
    "Bạn là một tác tử suy luận trên đồ thị tri thức theo thời gian (TKG). "
    "Bạn KHÔNG cần biết tri thức thực tế: bạn chỉ chọn hành động phù hợp "
    "trong danh sách cho sẵn để hệ thống truy vấn TKG giúp bạn."
)


ACTION_EXAMPLES = """Ví dụ 0 (tìm năm xảy ra sự kiện):
Câu hỏi: Năm nào Pháp ký hiệp định với Đức?
Action 0: $get_time("Pháp", "ký hiệp định", "Đức")$
Response 0: entities = [("Pháp", 1963)]
Action 1: $answer(1963)$
Response 1: Correct!

Ví dụ 1 (lọc theo năm):
Câu hỏi: Năm 2005, ai làm thủ tướng Đức?
Action 0: $get_head_entity("Đức", "thủ tướng", 2005)$
Response 0: entities = [("Gerhard Schröder", 2005), ("Angela Merkel", 2005)]
Action 1: $answer(Angela Merkel)$
Response 1: Correct!

Ví dụ 2 (first):
Câu hỏi: Ai là người đầu tiên giữ chức Tổng thống Pháp?
Action 0: $get_head_entity("Pháp", "tổng thống", no time)$
Response 0: entities = [("Charles de Gaulle", 1959), ("Georges Pompidou", 1969), ... ]
Action 1: $get_first({entities})$
Response 1: entities = [("Charles de Gaulle", 1959)]
Action 2: $answer(Charles de Gaulle)$
Response 2: Correct!

Ví dụ 3 (before + last — multi-hop):
Câu hỏi: Trước khi Angela Merkel làm thủ tướng Đức, ai là thủ tướng cuối cùng?
Action 0: $get_time("Angela Merkel", "thủ tướng", "Đức")$
Response 0: entities = [("Angela Merkel", 2005)]
Action 1: $get_head_entity("Đức", "thủ tướng", no time)$
Response 1: entities = [("Konrad Adenauer", 1949), ("Willy Brandt", 1969), ("Gerhard Schröder", 1998), ...]
Action 2: $get_before({entities}, 2005)$
Response 2: entities = [("Konrad Adenauer", 1949), ("Willy Brandt", 1969), ("Gerhard Schröder", 1998), ...]
Action 3: $get_last({entities})$
Response 3: entities = [("Gerhard Schröder", 1998)]
Action 4: $answer(Gerhard Schröder)$
Response 4: Correct!

Ví dụ 4 (after + first):
Câu hỏi: Sau năm 2010, nước nào đầu tiên ký hiệp ước với Nga?
Action 0: $get_head_entity("Nga", "ký hiệp ước", no time)$
Response 0: entities = [("Trung Quốc", 2005), ("Pháp", 2011), ("Ấn Độ", 2013), ...]
Action 1: $get_after({entities}, 2010)$
Response 1: entities = [("Pháp", 2011), ("Ấn Độ", 2013), ...]
Action 2: $get_first({entities})$
Response 2: entities = [("Pháp", 2011)]
Action 3: $answer(Pháp)$
Response 3: Correct!
"""


ACTION_SELECT_TEMPLATE = """Hãy chọn hành động kế tiếp để trả lời câu hỏi.

Các nhóm hàm khả dụng:
- Hàm thời gian: get_time(HEAD, REL, TAIL); get_before(LIST, T); get_after(LIST, T); get_between(LIST, T1, T2)
- Hàm thực thể: get_tail_entity(HEAD, REL, [T]); get_head_entity(TAIL, REL, [T])
- Hàm chọn lọc: get_first(LIST); get_last(LIST)
- Trả lời: answer(GIÁ_TRỊ)

Ví dụ tham khảo:
{examples}
(hết ví dụ)

Câu hỏi: {question}
Loại câu hỏi: {qtype}    Loại đáp án: {answer_type}

Phương pháp suy luận gợi ý (methodology):
{methodology}

Các bước đã thực hiện:
{history}

Các hành động khả dụng tại bước này (CHỈ được chọn một trong số này):
{actions}

Hãy chọn đúng MỘT hành động bằng cách lặp lại nguyên văn chuỗi nằm giữa hai dấu $.
Nếu hành động có chỗ trống {{your specified time}} thì THAY bằng một năm cụ thể (số nguyên 4 chữ số) suy ra từ các bước trước.
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
