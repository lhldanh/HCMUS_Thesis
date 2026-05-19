# ---------- Templates ----------
# Placeholders: {head} (s), {tail} (o), {time} (year)
#
# CẤU TRÚC:
# - simple_time: {"start": [...], "end": [...], "range": [...]}
#     → answer = fact.start | fact.end | (fact.start, fact.end)
# - simple_entity: [...] (flat list)
#     → answer = subject entity tại {time}
# - before_after: {"before": [...], "after": [...]}
#     → answer = subject entity (anchor có thể là {head}+{tail} hoặc {time})
# - first_last: {"first": [...], "last": [...]}
#     → answer = object entity (sớm/muộn nhất)
# - time_join: [...] (flat list, anchor là fact của {head})
#     → answer = subject entity khác overlap với (head, R, tail)
#
# LƯU Ý:
# - P166 (award) chỉ có "start" vì award là point-in-time (start == end)
# - Template before_after có thể anchor bằng {head}+{tail} HOẶC {time}
#   generate.py detect bằng placeholder trong template
TEMPLATES = {
    "P39": {  # position held - giữ chức
        "simple_time": {
            "start": [
                "{head} bắt đầu làm {tail} vào năm nào?",
                "{head} nhậm chức {tail} năm nào?",
                "Vào năm nào {head} đảm nhiệm chức {tail}?",
                "{head} giữ chức vụ {tail} từ năm nào?",
                "{head} giữ chức vụ {tail} vào năm nào?",
                "Khi nào {head} nắm giữ vị trí {tail}?",
            ],
            "end": [
                "{head} giữ chức vụ {tail} đến năm nào?",
                "{head} kết thúc chức vụ {tail} vào năm nào?",
                "{head} không còn làm {tail} từ năm nào?",
                "{head} từ chức {tail} vào năm nào?",
            ],
            "range": [
                "{head} giữ chức vụ {tail} từ khi nào đến khi nào?",
                "{head} giữ chức vụ {tail} từ năm nào đến năm nào?",
                "{head} làm {tail} trong khoảng thời gian nào?",
                "Khoảng thời gian nào {head} làm {tail}?",
                "{head} đảm nhiệm vai trò {tail} trong giai đoạn nào?",
            ],
        },
        "simple_entity": [
            "Ai giữ chức vụ {tail} vào năm {time}?",
            "Vào khoảng thời gian {time}, ai làm {tail}?",
            "Vào năm {time}, ai nắm giữ vị trí {tail}?",
            "Ai là người đảm nhận chức {tail} vào thời điểm {time}?",
            "Người giữ chức {tail} năm {time} là ai?",
            "Ai đảm trách vị trí {tail} trong năm {time}?",
        ],
        "before_after": {
            "before": [
                "Ai giữ chức vụ {tail} trước {head}?",
                "Ai là người đứng đầu {tail} trước khi {head} nhận chức?",
                "Người tiền nhiệm của {head} ở vị trí {tail} là ai?",
                "Trước khi {head} nắm giữ {tail}, ai từng giữ chức này?",
                "{tail} được ai lãnh đạo trước thời kỳ {head}?",
            ],
            "after": [
                "Ai làm {tail} sau {head}?",
                "Sau khi {head} rời chức {tail}, ai là người kế nhiệm?",
                "Người kế nhiệm {head} ở chức {tail} là ai?",
                "Ai thay {head} đảm nhiệm {tail}?",
                "{tail} được ai lãnh đạo sau thời kỳ {head}?",
            ],
        },
        "first_last": {
            "first": [
                "{head} giữ chức vụ nào đầu tiên?",
                "Vị trí đầu tiên mà {head} nắm giữ trong chính phủ là gì?",
                "{head} từng làm gì trước tiên trong sự nghiệp?",
                "Chức vụ nào là khởi đầu sự nghiệp của {head}?",
                "Chức vụ đầu đời của {head} là gì?",
            ],
            "last": [
                "Chức vụ cuối cùng của {head} trước khi nghỉ hưu là?",
                "{head} đảm nhiệm vị trí cuối cùng nào trong sự nghiệp?",
                "Vị trí cuối cùng {head} từng nắm giữ là gì?",
            ],
        },
        "time_join": [
            "Ai cùng {head} đảm nhiệm chức vụ {tail} vào thời điểm đó?",
            "Ai cùng làm {tail} với {head} trong cùng khoảng thời gian?",
            "Ai có cùng giữ chức {tail} với {head}?",
            "Cùng thời với {head} ở chức {tail} còn có ai?",
            "Ai cùng {head} đảm nhiệm {tail}?",
        ],
    },

    "P54": {  # member of sports team - chơi cho
        "simple_time": {
            "start": [
                "Khi nào {head} gia nhập {tail}?",
                "{head} là thành viên của {tail} vào năm nào?",
                "Năm nào {head} thi đấu cho {tail}?",
            ],
            "end": [
                "{head} rời {tail} năm nào?",
            ],
            "range": [
                "{head} thi đấu cho {tail} từ khi nào đến khi nào?",
                "Khoảng thời gian nào {head} chơi cho {tail}?",
                "{head} đầu quân cho {tail} trong khoảng thời gian nào?",
                "Hợp đồng của {head} với {tail} kéo dài từ năm nào đến năm nào?",
                "{head} khoác áo {tail} trong khoảng thời gian nào?",
            ],
        },
        "simple_entity": [
            "Ai thi đấu cho {tail} vào năm {time}?",
            "{tail} có thành viên nào vào lúc {time}?",
            "Vào năm {time}, ai là cầu thủ của {tail}?",
            "Ai chơi cho {tail} trong mùa giải {time}?",
            "Cầu thủ nào khoác áo {tail} vào năm {time}?",
            "Vào thời điểm {time}, đội hình {tail} có ai?",
            "Năm {time}, {tail} chiêu mộ ai?",
            "Ai là cầu thủ của {tail} năm {time}?",
        ],
        "before_after": {
            "before": [
                # Anchor là {head}+{tail}
                "{head} thi đấu cho đội nào trước khi gia nhập {tail}?",
                "Trước khi đến {tail}, {head} chơi cho đội nào?",
                "{head} chuyển từ đội nào sang {tail}?",
                # Anchor là {time}
                "Ai thi đấu cho {tail} trước năm {time}?",
            ],
            "after": [
                # Anchor là {head}+{tail}
                "Sau khi rời {tail}, {head} chơi cho đội nào?",
                "Đội bóng kế tiếp của {head} sau {tail} là gì?",
                "Sau {tail}, {head} đầu quân cho ai?",
                # Anchor là {time}
                "Ai là thành viên của {tail} sau năm {time}?",
            ],
        },
        "first_last": {
            "first": [
                "{head} thi đấu cho đội nào lần đầu tiên?",
                "Lần đầu tiên {head} chơi bóng là cho đội nào?",
                "Câu lạc bộ đầu tiên trong sự nghiệp của {head} là gì?",
                "Đội bóng đầu đời của {head} là gì?",
            ],
            "last": [
                "Đội cuối cùng của {head} trong sự nghiệp là?",
                "{head} kết thúc sự nghiệp ở đội nào?",
                "{head} giã từ sự nghiệp tại đội nào?",
                "{head} treo giày ở đội nào?",
            ],
        },
        "time_join": [
            "Ai chơi cùng {head} ở {tail}?",
            "Đồng đội của {head} tại {tail} là những ai?",
            "Ai cùng khoác áo {tail} với {head}?",
            "Ai cùng thi đấu cho {tail} với {head} trong cùng giai đoạn?",
        ],
    },

    "P166": {  # award received - nhận (point-in-time, chỉ có "start")
        "simple_time": {
            "start": [
                "{head} nhận giải {tail} khi nào?",
                "Năm nào {head} được trao giải {tail}?",
                "{head} đã từng nhận được {tail}? Vào thời gian nào?",
                "Khi nào {head} giành được {tail}?",
                "{head} được vinh danh giải {tail} vào năm nào?",
                "Vào thời điểm nào {head} nhận giải {tail}?",
                "{head} đoạt {tail} năm nào?",
                "Năm nào {head} được xướng tên cho giải {tail}?",
                "{head} ẵm giải {tail} vào năm nào?",
            ],
            # Không có "end" và "range" vì award là point-in-time
        },
        "simple_entity": [
            "{head} nhận giải nào vào năm {time}?",
            "Năm {time}, giải thưởng nào được trao cho {head}?",
            "Giải nào {head} nhận được năm {time}?",
            "Vào năm {time}, {head} được trao giải thưởng nào?",
            "Giải thưởng được trao cho {head} năm {time} là gì?",
            "{head} đoạt giải gì năm {time}?",
            "Năm {time}, {head} được vinh danh ở giải nào?",
        ],
        "before_after": {
            "before": [
                # Anchor là {head}+{tail}
                "Trước khi nhận {tail}, {head} từng nhận giải gì?",
                "Trước khi đoạt {tail}, {head} đã có giải thưởng nào?",
                "Giải nào {head} có trước {tail}?",
                "{head} nhận giải thưởng nào trước khi nhận {tail}?",
                # Anchor là {time}
                "Giải nào được trao cho {head} trước năm {time}?",
            ],
            "after": [
                # Anchor là {head}+{tail}
                "Sau khi đoạt {tail}, {head} nhận được giải nào?",
                "Sau giải {tail}, {head} còn nhận giải nào nữa?",
                "Giải kế tiếp của {head} sau {tail} là gì?",
                "{head} nhận giải thưởng nào sau khi nhận {tail}?",
                # Anchor là {time}
                "Giải nào được trao cho {head} sau năm {time}?",
            ],
        },
        "first_last": {
            "first": [
                "{head} nhận giải thưởng nào lần đầu?",
                "Giải thưởng đầu tiên trong sự nghiệp của {head} là gì?",
                "Giải đầu tiên đánh dấu sự nghiệp của {head} là gì?",
                "Giải thưởng đầu tay của {head} là gì?",
            ],
            "last": [
                "Giải thưởng cuối cùng {head} từng nhận là?",
                "{head} nhận giải cuối cùng vào dịp nào?",
                "Vinh dự cuối cùng {head} nhận được là gì?",
            ],
        },
        "time_join": [
            "Ai cùng {head} được trao giải {tail}?",
            "Ai và {head} nhận giải cùng năm?",
            "Cùng thời điểm với {head}, ai cũng đoạt {tail}?",
        ],
    },

    "P26": {  # spouse - kết hôn với
        "simple_time": {
            "start": [
                "{head} và {tail} kết hôn vào lúc nào?",
                "{head} kết hôn với {tail} từ năm bao nhiêu?",
                "Khi nào {head} lấy {tail}?",
                "{head} thành hôn với {tail} năm nào?",
                "Năm bao nhiêu {head} và {tail} về chung một nhà?",
                "{head} cưới {tail} vào năm nào?",
                "Cuộc hôn nhân của {head} và {tail} bắt đầu năm nào?",
            ],
            "end": [
                "{head} và {tail} ly hôn năm nào?",
                "Cuộc hôn nhân của {head} và {tail} kết thúc năm nào?",
            ],
            "range": [
                "Khoảng thời gian nào {head} là vợ/chồng của {tail}?",
                "Cuộc hôn nhân của {head} và {tail} kéo dài từ năm nào đến năm nào?",
                "{head} chung sống với {tail} trong khoảng thời gian nào?",
            ],
        },
        "simple_entity": [
            "{head} kết hôn với ai vào năm {time}?",
            "Vào khoảng thời gian {time}, vợ/chồng của {head} là ai?",
            "Năm {time}, ai là bạn đời của {head}?",
            "Ai là người vợ/chồng của {head} trong năm {time}?",
            "Vào năm {time}, ai là người bạn đời của {head}?",
            "Người phối ngẫu của {head} ở thời điểm {time} là ai?",
            "Năm {time}, {head} chung sống cùng ai?",
            "Ai là người đầu ấp tay gối với {head} vào năm {time}?",
        ],
        "before_after": {
            "before": [
                "{head} kết hôn với ai trước khi kết hôn với {tail}?",
                "Vợ/Chồng nào của {head} xuất hiện trước {tail}?",
                "Cuộc hôn nhân trước {tail} của {head} là với ai?",
                "{head} có cuộc hôn nhân nào trước {tail}?",
            ],
            "after": [
                "Sau khi ly hôn {tail}, {head} cưới ai?",
                "Sau {tail}, {head} tái hôn với ai?",
                "Người kế tiếp {tail} trong đời {head} là ai?",
                "Vợ/Chồng sau {tail} của {head} là ai?",
            ],
        },
        "first_last": {
            "first": [
                "{head} kết hôn với ai lần đầu tiên?",
                "Người vợ/chồng đầu tiên của {head} là ai?",
                "Cuộc hôn nhân đầu tiên của {head} là với ai?",
                "Người kết hôn đầu tiên với {head} là ai?",
            ],
            "last": [
                "Vợ/Chồng cuối cùng của {head} là ai?",
                "{head} lấy ai cuối cùng?",
                "Bạn đời cuối đời của {head} là ai?",
            ],
        },
        "time_join": [
            "Ai kết hôn cùng thời với {head}?",
            "Trong giai đoạn {head} kết hôn với {tail}, ai cũng có hôn nhân?",
            "Ai có hôn nhân trùng thời gian với {head} và {tail}?",
        ],
    },

    "P108": {  # employer - làm việc tại
        "simple_time": {
            "start": [
                "{head} bắt đầu công tác tại {tail} vào năm nào?",
                "Khi nào {head} gia nhập {tail}?",
                "Năm nào {head} bắt đầu làm việc tại {tail}?",
                "{head} đầu quân cho {tail} năm nào?",
            ],
            "end": [
                "{head} rời {tail} năm nào?",
                "{head} nghỉ việc tại {tail} năm nào?",
            ],
            "range": [
                "{head} làm việc cho {tail} từ khi nào đến khi nào?",
                "Khoảng thời gian nào {head} làm việc tại {tail}?",
                "{head} đầu quân cho {tail} vào khoảng thời gian nào?",
                "{head} công tác ở {tail} trong khoảng thời gian nào?",
            ],
        },
        "simple_entity": [
            "{head} làm việc cho công ty nào vào năm {time}?",
            "Vào lúc {time}, {head} công tác tại đâu?",
            "Năm {time}, ai là sếp của {head}?",
            "Vào thời gian {time}, {head} làm việc ở đâu?",
            "Vào năm {time}, {head} là nhân viên của công ty nào?",
            "Năm {time}, {head} đầu quân cho ai?",
            "Nơi làm việc của {head} vào năm {time} là ở đâu?",
        ],
        "before_after": {
            "before": [
                "Công ty nào thuê {head} trước khi chuyển sang {tail}?",
                "Trước khi gia nhập {tail}, {head} công tác tại đâu?",
                "Trước {tail}, {head} từng làm việc tại đâu?",
                "{head} làm việc cho tổ chức nào trước {tail}?",
            ],
            "after": [
                "Sau khi rời {tail}, {head} làm việc ở đâu?",
                "Công ty kế tiếp của {head} sau {tail} là gì?",
                "Nơi làm việc tiếp theo của {head} sau khi rời {tail} là gì?",
                "{head} làm việc cho tổ chức nào sau {tail}?",
            ],
        },
        "first_last": {
            "first": [
                "{head} làm việc cho công ty nào lần đầu?",
                "Nơi làm việc đầu tiên của {head} là?",
                "Công việc đầu đời của {head} là tại đâu?",
                "Tổ chức đầu tiên thuê {head} là?",
            ],
            "last": [
                "Công ty cuối cùng của {head} trong sự nghiệp là?",
                "Nơi cuối cùng {head} làm việc trước khi nghỉ hưu là?",
                "{head} kết thúc sự nghiệp tại công ty nào?",
            ],
        },
        "time_join": [
            "Ai là đồng nghiệp của {head} tại {tail}?",
            "Đồng nghiệp của {head} ở {tail} là ai?",
            "Ai cùng {head} làm việc tại {tail}?",
            "Ai có chung khoảng thời gian làm tại {tail} với {head}?",
        ],
    },

    # ============ Mở rộng ============
    "P69": {  # educated at - học tại
        "simple_time": {
            "start": [
                "{head} bắt đầu du học tại {tail} vào năm nào?",
                "Khi nào {head} nhập học {tail}?",
                "{head} theo học tại {tail} vào năm nào?",
            ],
            "end": [
                "{head} tốt nghiệp {tail} năm nào?",
            ],
            "range": [
                "{head} học tại {tail} từ khi nào đến khi nào?",
                "Khoảng thời gian nào {head} theo học ở {tail}?",
                "{head} là sinh viên {tail} trong khoảng thời gian nào?",
            ],
        },
        "simple_entity": [
            "Ai học tại {tail} vào năm {time}?",
            "Vào lúc {time}, ai là học sinh/sinh viên của {tail}?",
            "Năm {time}, học sinh nào của {tail}?",
            "Vào thời gian {time}, ai theo học ở {tail}?",
            "Năm {time}, {tail} có sinh viên nào?",
        ],
        "before_after": {
            "before": [
                "{head} học tại trường nào trước {tail}?",
                "Trước khi vào {tail}, {head} học ở đâu?",
            ],
            "after": [
                "Sau {tail}, {head} học ở đâu?",
                "Ngôi trường tiếp theo của {head} sau {tail} là gì?",
                "Sau khi rời {tail}, {head} chuyển đến trường nào?",
            ],
        },
        "first_last": {
            "first": [
                "{head} học tại trường nào lần đầu?",
                "Trường đầu tiên {head} theo học là gì?",
            ],
            "last": [
                "Trường cuối cùng của {head} là?",
                "Ngôi trường mà {head} tốt nghiệp lần cuối là gì?",
                "Bậc học cao nhất của {head} là ở trường nào?",
            ],
        },
        "time_join": [
            "Bạn học của {head} tại {tail} là ai?",
            "Ai cùng học tại {tail} với {head}?",
            "Ai có chung khoảng thời gian học tại {tail} với {head}?",
        ],
    },

    "P102": {  # member of political party
        "simple_time": {
            "start": [
                "{head} bắt đầu là thành viên {tail} vào năm nào?",
                "{head} gia nhập {tail} năm nào?",
                "{head} đứng trong hàng ngũ {tail} từ năm nào?",
            ],
            "end": [
                "{head} rời {tail} năm nào?",
            ],
            "range": [
                "{head} là thành viên {tail} từ khi nào đến khi nào?",
                "Khoảng thời gian nào {head} gia nhập {tail}?",
                "Khoảng thời gian nào {head} thuộc về {tail}?",
            ],
        },
        "simple_entity": [
            "Ai là thành viên {tail} vào năm {time}?",
            "Vào lúc {time}, ai thuộc {tail}?",
            "Năm {time}, đảng viên của {tail} có ai?",
            "Vào thời gian {time}, {tail} bao gồm những ai?",
            "Năm {time}, ai trong hàng ngũ {tail}?",
        ],
        "before_after": {
            "before": [
                "{head} là thành viên đảng nào trước {tail}?",
                "Trước {tail}, {head} thuộc đảng nào?",
                "{head} chuyển từ đảng nào sang {tail}?",
            ],
            "after": [
                "Sau khi rời {tail}, {head} gia nhập đảng nào?",
                "Đảng tiếp theo của {head} sau {tail} là gì?",
            ],
        },
        "first_last": {
            "first": [
                "{head} tham gia đảng nào lần đầu?",
                "Đảng phái đầu tiên trong sự nghiệp chính trị của {head} là gì?",
                "Đảng đầu tay của {head} là gì?",
            ],
            "last": [
                "Đảng cuối cùng của {head} là?",
                "{head} kết thúc sự nghiệp ở đảng nào?",
            ],
        },
        "time_join": [
            "Đồng chí của {head} tại {tail} là ai?",
            "Ai cùng sinh hoạt tại {tail} với {head}?",
            "Ai có chung khoảng thời gian sinh hoạt tại {tail} với {head}?",
        ],
    },

    "P463": {  # member of - là thành viên của (tổ chức chung)
        "simple_time": {
            "start": [
                "{head} tham gia {tail} năm nào?",
                "Khi nào {head} bắt đầu trở thành thành viên của {tail}?",
            ],
            "end": [
                "{head} rời {tail} năm nào?",
            ],
            "range": [
                "{head} là thành viên {tail} từ khi nào đến khi nào?",
                "Khoảng thời gian nào {head} gia nhập {tail}?",
                "{head} thuộc về {tail} trong khoảng thời gian nào?",
            ],
        },
        "simple_entity": [
            "Ai là thành viên {tail} vào năm {time}?",
            "Vào lúc {time}, {tail} có thành viên nào?",
            "Năm {time}, ai gia nhập {tail}?",
            "{tail} kết nạp ai vào năm {time}?",
            "Năm {time}, ai thuộc {tail}?",
        ],
        "before_after": {
            "before": [
                "{head} là thành viên tổ chức nào trước {tail}?",
                "Trước {tail}, {head} tham gia tổ chức nào?",
            ],
            "after": [
                "Sau khi rời {tail}, {head} gia nhập tổ chức nào?",
                "Sau khi rời {tail}, {head} đến với tổ chức nào?",
                "Tổ chức kế tiếp của {head} sau {tail} là gì?",
            ],
        },
        "first_last": {
            "first": [
                "{head} tham gia tổ chức nào lần đầu?",
                "Tổ chức đầu tiên {head} tham gia là gì?",
                "{head} được kết nạp vào tổ chức nào đầu tiên?",
            ],
            "last": [
                "Tổ chức cuối cùng mà {head} gia nhập là?",
                "Tổ chức cuối cùng mà {head} từng là thành viên là gì?",
            ],
        },
        "time_join": [
            "Bạn đồng hành của {head} tại {tail} là ai?",
            "Ai cùng là thành viên {tail} với {head}?",
            "Ai có chung giai đoạn ở {tail} với {head}?",
        ],
    },
}


# ============ ANSWER EXTRACTION LOGIC ============
"""
def get_answer(fact, qtype, subtype=None, head2_fact=None):
    s, r, o, start, end = fact
    
    if qtype == "simple_time":
        return {"start": start, "end": end, "range": (start, end)}[subtype]
    
    elif qtype == "simple_entity":
        # query (?, R, o, st, en) where st <= time <= en
        return query_entity_at_time(r, o, time)
    
    elif qtype == "before_after":
        if subtype == "before":
            # Nếu template có {time}: cutoff = time
            # Nếu template có {head}+{tail}: cutoff = start của (head, R, tail)
            return query_before(r, o, cutoff)
        else:  # after
            return query_after(r, o, cutoff)
    
    elif qtype == "first_last":
        if subtype == "first":
            # SELECT o FROM facts WHERE s=head AND r=R ORDER BY start ASC LIMIT 1
            return query_first(s, r)
        else:  # last
            return query_last(s, r)
    
    elif qtype == "time_join":
        # Anchor là (head, R, tail, s1, e1)
        # Tìm s2 khác sao cho (s2, R, tail, s2_start, s2_end) overlap với anchor
        return query_overlap(r, o, head, s1, e1)


# ============ EDGE CASES ============

1. Point-in-time (P166): chỉ generate "start" template
2. Open-ended fact (end == None): skip "end" và "range" subtypes
3. before_after có 2 dạng anchor:
   - {head}+{tail}: cutoff = start/end của fact (head, R, tail)
   - {time}: cutoff = {time} sample
   → generate.py detect bằng cách check "{time}" in template
4. time_join: chỉ generate nếu có ít nhất 2 fact (s1, R, tail, ...) và (s2, R, tail, ...) overlap
"""


# ============ HELPER ============
"""
import random

def sample_template(rel_id, qtype):
    config = TEMPLATES[rel_id][qtype]
    if isinstance(config, dict):
        subtype = random.choice(list(config.keys()))
        template = random.choice(config[subtype])
        return template, subtype
    else:
        return random.choice(config), None
"""
