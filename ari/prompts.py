"""Prompts (Vietnamese) for ARI on cronqvn."""

# NOTE: phần static (vai trò + task spec + ví dụ few-shot) được gộp vào system
# prompt để Ollama có thể prefix-cache giữa các step → giảm prefill ~50%.
# Phần dynamic (câu hỏi / methodology / history / actions) giữ ở user template.


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

Ví dụ 5 (time_join — tìm đồng hành cùng thời điểm):
Câu hỏi: Ai cùng gia nhập Interpol với Ả Rập Xê Út?
Action 0: $get_time("Ả Rập Xê Út", "thành viên của", "Interpol")$
Reason: Cần xác định năm Ả Rập Xê Út gia nhập Interpol để tìm các nước cùng gia nhập năm đó.
Response 0: entities = [("Ả Rập Xê Út", 1956)]
Action 1: $get_head_entity("Interpol", "thành viên của", 1956)$
Reason: Tìm tất cả các nước gia nhập Interpol cùng năm 1956.
Response 1: entities = [("Sudan", 1956), ("Thổ Nhĩ Kỳ", 1956), ("Campuchia", 1956), ("Nhật Bản", 1956), ("Jordan", 1956)]
Action 2: $answer(Thổ Nhĩ Kỳ)$
Reason: Một trong các nước cùng gia nhập Interpol năm 1956.
Response 2: Correct!
"""


ACTION_SELECT_SYSTEM = (
    "Bạn là một tác tử suy luận trên đồ thị tri thức theo thời gian (TKG). "
    "Bạn KHÔNG cần biết tri thức thực tế: bạn chỉ chọn hành động phù hợp "
    "trong danh sách cho sẵn để hệ thống truy vấn TKG giúp bạn.\n\n"
    "Các nhóm hàm khả dụng:\n"
    "- Hàm thời gian: get_time(HEAD, REL, TAIL); get_before(LIST, T); "
    "get_after(LIST, T); get_between(LIST, T1, T2)\n"
    "- Hàm thực thể: get_tail_entity(HEAD, REL, [T]); get_head_entity(TAIL, REL, [T])\n"
    "- Hàm chọn lọc: get_first(LIST); get_last(LIST)\n"
    "- Trả lời: answer(GIÁ_TRỊ)\n\n"
    "Ví dụ tham khảo:\n"
    + ACTION_EXAMPLES
    + "(hết ví dụ)\n\n"
    "Quy tắc chọn hành động:\n"
    "- Chọn đúng MỘT hành động bằng cách lặp lại nguyên văn chuỗi nằm giữa hai dấu $.\n"
    "- Nếu hành động có chỗ trống {your specified time} thì THAY bằng một năm cụ thể "
    "(số nguyên 4 chữ số) suy ra từ các bước trước.\n"
    "- Nếu đã có đủ thông tin, hãy chọn hành động $answer(...)$.\n\n"
    "Định dạng đầu ra BẮT BUỘC:\n"
    "Action: <hành động bạn chọn, bao trong dấu $>\n"
    "Reason: <giải thích ngắn>"
)


ACTION_SELECT_TEMPLATE = """Câu hỏi: {question}

Phương pháp suy luận gợi ý (methodology):
{methodology}

Các bước đã thực hiện:
{history}

Các hành động khả dụng tại bước này (CHỈ được chọn một trong số này):
{actions}

Hãy chọn hành động kế tiếp theo đúng format Action: / Reason:.
"""


METHODOLOGY_SYSTEM = (
    "Bạn là chuyên gia đúc kết phương pháp suy luận trên KG thời gian. "
    "Hãy rút ra hướng dẫn TRỪU TƯỢNG, không gắn vào dữ kiện cụ thể."
)

METHODOLOGY_TEMPLATE = """Phân tích cẩn thận các ví dụ ĐÚNG và SAI dưới đây. Từ đó hãy rút ra các mẫu
chung và nguyên tắc tương ứng. Dựa vào các ví dụ đó, hãy đưa ra một phương pháp
toàn diện mô tả CÁCH tiếp cận đúng loại câu hỏi này, nêu bật các bước then chốt
và những cạm bẫy thường gặp cần tránh.

Định nghĩa nhiệm vụ:
Sử dụng các công cụ dưới đây để tương tác với đồ thị tri thức theo thời gian (TKG).
Bạn có một danh sách hành động được chia thành ba nhóm: truy vấn thời gian, truy
vấn thực thể, và truy vấn thời điểm cụ thể. Có thể có nhiều đáp án đúng cho câu
hỏi, nhưng chỉ cần trả về một đáp án hợp lệ.

Truy vấn theo thời gian:
- $get_time(HEAD, RELATION, TAIL)$: lấy thời điểm của một sự kiện cụ thể.
- $get_before(ENTITY_LIST, SPECIFIED_TIME)$: lọc các thực thể/sự kiện trước thời điểm cho trước.
- $get_after(ENTITY_LIST, SPECIFIED_TIME)$: lọc các thực thể/sự kiện sau thời điểm cho trước.
- $get_between(ENTITY_LIST, START_TIME, END_TIME)$: lọc các thực thể/sự kiện giữa hai thời điểm.

Truy vấn thực thể:
- $get_tail_entity(CURRENT_HEAD, RELATION, OPTIONAL_TIME)$: lấy thực thể đuôi.
- $get_head_entity(CURRENT_TAIL, RELATION, OPTIONAL_TIME)$: lấy thực thể đầu.

Truy vấn thời điểm cụ thể:
- $get_first(ENTITY_LIST)$: thực thể xuất hiện sớm nhất.
- $get_last(ENTITY_LIST)$: thực thể xuất hiện muộn nhất.
- $answer(YOUR_ANSWER)$: trả lời cuối cùng.
(hết định nghĩa nhiệm vụ)

Ví dụ output mẫu:
Ví dụ 1:
Overall Instruction:
Loại câu hỏi này yêu cầu xác định tuần tự các sự kiện, vd. "Ai <Quan hệ R>
<thực thể C> trước <thực thể B>". Để tìm đáp án <thực thể A> cần ba bước suy
luận: đầu tiên xác định thời điểm cụ thể t mà (<thực thể B>, <Quan hệ R>,
<thực thể C>) xảy ra; tiếp theo tìm các head entity đã có quan hệ R với
<thực thể C>; cuối cùng lọc theo điều kiện thời gian trước t.

Step-by-step Guide:
1. Dùng get_time để tìm thời điểm: $get_time(<thực thể B>, <Quan hệ R>, <thực thể C>)$,
   thu được bộ 4 (B, R, C, t).
2. Dùng get_head_entity để lấy danh sách entity có quan hệ R với C:
   $get_head_entity(<thực thể C>, <Quan hệ R>, no time)$.
3. Dùng get_before để lọc theo thời gian: $get_before(<entities>, t)$.
4. Kết thúc bằng $answer(<thực thể A>)$.
(hết ví dụ output)

Ví dụ ĐÚNG và SAI cho loại câu hỏi hiện tại:

Ví dụ ĐÚNG:
{correct_examples}

Ví dụ SAI:
{incorrect_examples}
(hết ví dụ)

Bây giờ bắt đầu viết. Hãy thiết kế phương pháp ở mức PHƯƠNG PHÁP LUẬN — KHÔNG
nêu tên thực thể cụ thể của ví dụ, NHƯNG vẫn phải CỤ THỂ ACTIONABLE.

YÊU CẦU BẮT BUỘC (cấm vi phạm):
1. **Phải có TEMPLATE câu hỏi**: mở đầu Overall bằng "Câu hỏi dạng: ..." mô tả
   pattern bằng biến (vd: "Trước/Sau <thực thể B> làm <Quan hệ R>, ai <Quan hệ
   R'> với <thực thể C>?").
2. **Phải đặt tên biến** cho thực thể (A, B, C), quan hệ (R, R'), thời gian (t).
3. **Mỗi bước trong Step-by-step PHẢI có gọi hàm cụ thể** dạng
   `$get_xxx(arg, arg, arg)$` với arg là biến đã đặt, KHÔNG được viết "dùng
   get_xxx" suông.
4. **CẤM** các cụm sau (quá trừu tượng):
   - "tùy trường hợp", "phụ thuộc vào câu hỏi", "chọn hàm phù hợp"
   - "xác định yếu tố chính", "nếu cần thì..."
   - "đảm bảo chính xác", "tránh nhầm lẫn"
5. **CẤM** kết bằng general advice ("tránh các cạm bẫy", "kiểm tra đầy đủ").
6. Chuỗi action phải có thứ tự cố định cho pattern câu hỏi đó (vd: bước 1 luôn
   là `$get_time$`, bước 2 luôn là `$get_head_entity$`, ...).

Định dạng output BẮT BUỘC:

Overall Instruction:
Câu hỏi dạng: <template với biến>. Cần <số> bước:
<mô tả ngắn gọn logic tổng>.

Step-by-step Guide:
1. <ý đồ bước 1>: `$get_xxx(<biến>, <biến>, <biến>)$` — kết quả: <ý nghĩa>.
2. <ý đồ bước 2>: `$get_xxx(<biến>, ...)$` — kết quả: ...
3. ...
N. `$answer(<biến trả lời>)$`.
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
