# -*- coding: utf-8 -*-
"""
Test generating installation acceptance and verify 1:1 match with user template.
"""
import sys
from pathlib import Path
import docx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.installation_acceptance_word_service import generate_installation_acceptance_word

def test_match():
    # Test data for CX Technology with Stage 3
    data_stage3 = {
        "so_hop_dong": "HMV151020250001",
        "so_bien_ban": "BB-NT-2026-___",
        "ngay_ky_hop_dong": "09/12/2025",
        "gia_tri_hop_dong": "234.000.000 VND",
        "ten_he_thong": "Phần mềm tùy chỉnh chức năng hệ thống RFID",
        "ten_he_thong_trung": "RFID 系統功能客製化軟體",
        "ben_a": {
            "ten_cong_ty": "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
            "ten_tieng_trung": "金迅科技（越南）有限公司"
        },
        "ben_b": {
            "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
            "ten_tieng_trung": "宏明環球有限公司"
        },
        "hang_muc": [
            {"stt": 1, "hang_muc": "1. Xác nhận mở vụ án / 立案確認, Yêu cầu xác nhận / 需求確認"},
            {"stt": 2, "hang_muc": "2. Mỗi máy có thể quét các nhân viên vận hành máy khác nhau khi vào và ra khỏi trạm.\n進出站時每個機台都可以掃不同的機台操作者Máy quét mã vạch được tối ưu hóa để lựa chọn máy bằng cách nhấp chuột.掃描機台條碼優化為點選機台方式。"},
            {"stt": 3, "hang_muc": "3. Quét nhiều ID nhân viên để vào và ra khỏi trạm.\n進出站可刷複數人員工號。"},
            {"stt": 4, "hang_muc": "4. QR條碼掃描\nQuét mã vạch QR"},
            {"stt": 5, "hang_muc": "5. 特定人員解除綁定權限控管\nHủy ràng buộc quyền cho nhân viên cụ thể"},
            {"stt": 6, "hang_muc": "6. RFID離線模式可以自動切換\nChế độ ngoại tuyến RFID có thể chuyển đổi tự động"},
            {"stt": 7, "hang_muc": "7. 增加Run Card查詢條件\nThêm điều kiện truy vấn Run Card"}
        ],
        "payment_stages": [
            {
                "stage_id": "1",
                "stage": "GIAI ĐOẠN 1\n第一期",
                "condition": "Sau khi ký kết hợp đồng\n簽約完成時",
                "rate": "40%",
                "amount": "93.600.000 VND",
                "selected": False
            },
            {
                "stage_id": "2",
                "stage": "GIAI ĐOẠN 2\n第二期",
                "condition": "Sau khi triển khai sản phẩm đưa vào sử dụng\n產品安裝後",
                "rate": "40%",
                "amount": "93.600.000 VND",
                "selected": False
            },
            {
                "stage_id": "3",
                "stage": "GIAI ĐOẠN 3\n第三期",
                "condition": "Nghiệm thu đạt tiêu chuẩn\n驗收合格時",
                "rate": "20%",
                "amount": "46.800.000 VND",
                "selected": True
            }
        ]
    }

    res = generate_installation_acceptance_word(data_stage3)
    print("Result file:", res["file_path"])

if __name__ == "__main__":
    test_match()
