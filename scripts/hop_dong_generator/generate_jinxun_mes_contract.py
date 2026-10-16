# -*- coding: utf-8 -*-
"""Sinh hợp đồng JINXUN MES Lite từ dữ liệu đã được người dùng xác nhận.

Script chuyên biệt này không đọc JSON và không gọi AI, nhờ đó mỗi lần chạy đều
dùng đúng bộ dữ liệu pháp nhân/tiến độ đã khóa bên dưới.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dien_hop_dong_tu_dong import fill_contract


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_TEMPLATE = WORKSPACE_ROOT / "Bieu Mau" / "Hợp đồng.docx"
DEFAULT_OUTPUT = SCRIPT_DIR / "outputs" / "final" / "Hop_Dong_JINXUN_MES_Lite_DA_SUA_V2.docx"


JINXUN_CONTRACT_DATA = {
    "so_hop_dong": "HMV131020260001",
    "ngay_ky": "13",
    "thang_ky": "10",
    "nam_ky": "2026",
    "ben_a": {
        "ten_cong_ty": "CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM",
        "dia_chi": "Thôn Trụ, Phường Việt Hòa, Thành phố Hải Phòng, Việt Nam",
        "mst": "0801382054",
        "nguoi_dai_dien": "HUANG YU",
        "chuc_vu": "Tổng giám đốc",
    },
    "ben_b": {
        "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
        "ten_tieng_trung": "宏明環球有限公司",
        "dia_chi": "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
        "mst": "0318280158",
        "nguoi_dai_dien": "TANG WEI LI",
        "chuc_vu": "TỔNG GIÁM ĐỐC",
        "chuc_vu_trung": "總經理",
    },
    "du_an": {
        "ten_du_an_viet": "Báo giá triển khai hệ thống MES Lite cho nhà máy JINXUN",
        "ten_du_an_trung": "JINXUN 金迅廠區 MES Lite 系統建置報價單",
    },
    "hang_muc": [
        {
            "stt": "1",
            "ten_san_pham": "MES Lite 系統 - PM 作業\nHệ thống MES Lite - Nghiệp vụ PM",
            "don_gia": "110.000.000 VND",
            "so_luong": "1 SET",
            "tong_gia": "110.000.000 VND",
        },
        {
            "stt": "2",
            "ten_san_pham": "MES Lite 系統 - Web 介面「25 機台授權版」\nHệ thống MES Lite - Giao diện Web \"Phiên bản cấp phép cho 25 máy\"",
            "don_gia": "588.000.000 VND",
            "so_luong": "1 SET",
            "tong_gia": "588.000.000 VND",
        },
        {
            "stt": "3",
            "ten_san_pham": "MES Lite 系統 - 客製上料 API 接口\nHệ thống MES Lite - Giao diện API cấp liệu tùy chỉnh (Option)",
            "don_gia": "109.583.184 VND",
            "so_luong": "1 SET",
            "tong_gia": "109.583.184 VND",
        },
    ],
    "tong_tien_truoc_giam": "807.583.184 VND",
    "tong_tien_sau_giam": "781.530.000 VND",
    "tong_tien_hop_dong_so": "781.530.000",
    "phan_bo_thanh_toan": [
        {
            "dot": 1,
            "phan_tram": 30,
            "tieu_de": "Đợt 1 (Tạm ứng 30%)",
            "tieu_de_trung": "簽約定金",
            "dieu_kien_viet": "thanh toán trước ngay sau khi hai bên ký kết hợp đồng bằng hình thức chuyển khoản T/T",
            "dieu_kien_trung": "雙方簽約後即期以電匯（T/T）方式支付",
        },
        {
            "dot": 2,
            "phan_tram": 55,
            "tieu_de": "Đợt 2 (55% Hoàn thành lắp đặt và cấu hình hệ thống)",
            "tieu_de_trung": "設備安裝款",
            "dieu_kien_viet": "sau khi hoàn thành lắp đặt và cấu hình hệ thống",
            "dieu_kien_trung": "於系統安裝及建置完成後支付",
        },
        {
            "dot": 3,
            "phan_tram": 15,
            "tieu_de": "Đợt 3 (15% Nghiệm thu cuối cùng - FAC)",
            "tieu_de_trung": "驗收尾款",
            "dieu_kien_viet": "sau khi khách hàng nghiệm thu hoàn tất và ký biên bản bàn giao chính thức (FAC)",
            "dieu_kien_trung": "於最終驗收（FAC）完成並簽署驗收交付文件後支付",
        },
    ],
    "thoi_gian_giao_hang_ngay": 80,
    "thoi_gian_bao_hanh_thang": 12,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sinh hợp đồng JINXUN MES Lite không phụ thuộc JSON/AI."
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = fill_contract(str(args.template), str(args.output), JINXUN_CONTRACT_DATA)
    print(f"Đã tạo: {result['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
