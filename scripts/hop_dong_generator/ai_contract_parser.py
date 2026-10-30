# -*- coding: utf-8 -*-
"""
MODULE AI PHÂN TÍCH VÀ BÓC TÁCH THÔNG TIN HỢP ĐỒNG (GEMINI API)
Tệp: ai_contract_parser.py
Thư mục: e:\\Working\\scripts\\hop_dong_generator\\

Chức năng:
- Nhận văn bản đầu vào ở bất kỳ định dạng nào (tin nhắn, ghi chú, form thô, tiếng Việt, tiếng Trung, bảng giá...).
- Sử dụng Google Gemini 2.5 Flash / 1.5 Flash để bóc tách thông tin thành JSON chuẩn cho hệ thống điền hợp đồng.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any
from pathlib import Path

PORTAL_DIR = Path(__file__).resolve().parents[2] / "pm_portal"
if str(PORTAL_DIR) not in sys.path:
    sys.path.insert(0, str(PORTAL_DIR))

from app.services.payment_schedule_service import resolve_payment_schedule

try:
    from app.config import DEFAULT_GEMINI_KEYS, DEFAULT_GEMINI_KEY, CANDIDATE_MODELS, DEFAULT_MODEL
except Exception:
    DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
    DEFAULT_GEMINI_KEYS = [DEFAULT_GEMINI_KEY] if DEFAULT_GEMINI_KEY else []
    CANDIDATE_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
    ]
    DEFAULT_MODEL = CANDIDATE_MODELS[0]



SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên nghiệp về bóc tách và chuẩn hóa dữ liệu hợp đồng mua bán thiết bị / phần mềm song ngữ Việt - Trung cho CÔNG TY TNHH TOÀN CẦU HONG MING.

Nhiệm vụ của bạn:
Phân tích văn bản hoặc dữ liệu người dùng cung cấp và trích xuất thành định dạng JSON chuẩn xác 100%, tuân thủ cấu trúc sau:

QUY TẮC CHỐNG SUY DIỄN / BỊA DỮ LIỆU:
1. Chỉ ghi lại thông tin xuất hiện rõ ràng trong đầu vào; không tự dịch, không tự suy đoán và không tự bổ sung tên pháp nhân, địa chỉ, MST, người đại diện, chức vụ hoặc điều kiện thanh toán.
2. Nếu đầu vào không có tiếng Trung cho một trường thì trả về chuỗi rỗng cho trường tiếng Trung tương ứng. Tuyệt đối không tự tạo bản dịch tiếng Trung.
3. Bảo toàn nguyên văn tên công ty, địa chỉ, MST, tên người đại diện và chức vụ do người dùng cung cấp.
4. Nếu không có số hợp đồng hoặc ngày ký thì trả về chuỗi rỗng; chương trình chính sẽ yêu cầu người dùng bổ sung thay vì tự sinh.

{
  "so_hop_dong": "Số hợp đồng; để trống nếu đầu vào không có",
  "ngay_ky": "13",
  "thang_ky": "10",
  "nam_ky": "2026",
  "ben_a": {
    "ten_cong_ty": "Tên công ty tiếng Việt",
    "ten_tieng_trung": "Tên công ty tiếng Trung (nếu có)",
    "dia_chi": "Địa chỉ tiếng Việt",
    "dia_chi_trung": "Địa chỉ tiếng Trung (nếu có)",
    "mst": "Mã số thuế",
    "nguoi_dai_dien": "Họ và tên người đại diện",
    "chuc_vu": "Chức vụ",
    "chuc_vu_trung": "Chức vụ tiếng Trung; để trống nếu đầu vào không có"
  },
  "ben_b": {
    "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
    "ten_tieng_trung": "宏明環球有限公司",
    "dia_chi": "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
    "mst": "0318280158",
    "nguoi_dai_dien": "TANG WEI LI",
    "chuc_vu": "TỔNG GIÁM ĐỐC"
  },
  "du_an": {
    "ten_du_an_viet": "Tên dự án hoặc tên gói triển khai tiếng Việt",
    "ten_du_an_trung": "Tên dự án tiếng Trung; để trống nếu đầu vào không có"
  },
  "hang_muc": [
    {
      "stt": 1,
      "ten_san_pham": "Tên sản phẩm song ngữ",
      "don_gia": "110.000.000 VND",
      "so_luong": "1 SET",
      "tong_gia": "110.000.000 VND"
    }
  ],
  "tong_tien_truoc_giam": "807.583.184 VND",
  "tong_tien_sau_giam": "781.530.000 VND",
  "tong_tien_hop_dong_so": "781.530.000",
  "phan_bo_thanh_toan": [],
  "thoi_gian_giao_hang_ngay": 80,
  "thoi_gian_bao_hanh_thang": 12
}

CHỈ TRẢ VỀ DUY NHẤT KHỐI JSON HỢP LỆ (BẮT ĐẦU BẰNG { VÀ KẾT THÚC BẰNG }), KHÔNG VIẾT THÊM LỜI GIẢI THÍCH NÀO NGOÀI JSON.
"""


def parse_contract_info_with_ai(
    raw_input_text: str,
    api_key: str = None,
    model_name: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Sử dụng Gemini API để phân tích văn bản thô thành cấu trúc dữ liệu hợp đồng chuẩn.
    """
    key = api_key or DEFAULT_GEMINI_KEY
    if not key:
        raise ValueError("Chưa cấu hình GEMINI_API_KEY!")

    models_to_try = [model_name] if model_name != DEFAULT_MODEL else CANDIDATE_MODELS
    last_error = None

    prompt = f"{SYSTEM_PROMPT}\n\nDƯỚI ĐÂY LÀ DỮ LIỆU ĐẦU VÀO CẦN PHÂN TÍCH:\n\"\"\"\n{raw_input_text}\n\"\"\""
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
        print(f"[*] Đang phân tích bằng Model: {m}...")
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                response_data = json.loads(res.read().decode("utf-8"))
                candidate = response_data.get("candidates", [])[0]
                text_out = candidate["content"]["parts"][0]["text"].strip()

                # Loại bỏ markdown fences nếu có
                if text_out.startswith("```json"):
                    text_out = text_out[7:]
                elif text_out.startswith("```"):
                    text_out = text_out[3:]
                if text_out.endswith("```"):
                    text_out = text_out[:-3]
                text_out = text_out.strip()

                parsed_json = json.loads(text_out)
                parsed_json["phan_bo_thanh_toan"] = resolve_payment_schedule(
                    raw_input_text, parsed_json
                )
                print(f"[OK] Phân tích thành công bằng Model {m}!")
                return parsed_json
        except Exception as e:
            print(f"[CẢNH BÁO] Model {m} gặp lỗi ({e}), chuyển sang model tiếp theo...")
            last_error = e

    raise RuntimeError(f"Tất cả các Model AI đều thất bại: {last_error}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    test_input = """
    Tên công ty: CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM
    Địa chỉ: Thôn Trụ, Phường Việt Hòa, Thành phố Hải Phòng, Việt Nam
    Mã số thuế: 0801382054
    Người đại diện: HUANG YU
    Chức vụ: Tổng giám đốc
    hợp đồng phân bổ là 10% trong 30 ngày, 30% trong 60 ngày, 30%, và 30%
    Tổng tiền sau giảm giá: 781.530.000 VND
    """
    print("[*] Đang gửi yêu cầu phân tích tới Gemini AI...")
    res = parse_contract_info_with_ai(test_input)
    print(json.dumps(res, ensure_ascii=False, indent=2))
