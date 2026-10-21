"""AI Service for parsing unstructured text and files into repair contract schema via Google Gemini API."""

import base64
import io
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.config import CANDIDATE_MODELS, DEFAULT_GEMINI_KEY, DEFAULT_MODEL, DEFAULT_GEMINI_KEYS
from app.utils.currency_helper import (
    format_currency_vnd,
    number_to_chinese_words,
    number_to_vietnamese_words,
    parse_positive_integer,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_REPAIR = """Bạn là trợ lý AI chuyên nghiệp về bóc tách và chuẩn hóa dữ liệu HỢP ĐỒNG DỊCH VỤ SỬA CHỮA & BẢO TRÌ THIẾT BỊ song ngữ Việt - Trung cho CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司).

NHIỆM VỤ CỦA BẠN:
Phân tích văn bản mô tả kỹ thuật, bảng báo giá sửa chữa thiết bị, danh sách máy móc hư hỏng, biên bản kiểm tra lỗi hoặc ảnh chụp do người dùng cung cấp và trích xuất thành định dạng JSON chuẩn xác 100%.

QUY TẮC CỐT LÕI:
1. Bóc tách danh mục thiết bị sửa chữa & linh kiện thay thế:
   - STT: Thứ tự (1, 2, 3...)
   - ten_thiet_bi: Tên thiết bị hoặc linh kiện cần sửa chữa (song ngữ Việt - Trung nếu có, ví dụ: "Máy tính công nghiệp IPC / 工控機", "Màn hình cảm ứng HMI Proface 10 inch / 人機介面觸控螢幕", "Bo mạch I/O Gateway / I/O 網關主板")
   - model_serial: Model, Mã hiệu thiết bị, Số Serial hoặc Vị trí máy (Ví dụ: "D701MER-S2024", "SN: CX-IPC-0988", "Máy dập #03")
   - noi_dung_sua_chua: Hiện tượng lỗi và phương án sửa chữa (Ví dụ: "Hỏng nguồn cấp, chập IC nguồn - Thay thế bộ nguồn 24VDC và IC điều khiển / 電源損壞、更換 24VDC 電源模組及控制晶片")
   - don_vi_tinh: Đơn vị tính (Bộ, Cái, Máy, Chiếc, Lần...)
   - don_gia: Đơn giá sửa chữa/thay thế bằng số kèm VND (VD: "5.500.000 VND")
   - so_luong: Số lượng kèm đơn vị (VD: "2 Cái")
   - tong_gia: Thành tiền (VD: "11.000.000 VND")

2. Trích xuất thông tin Bên A (Khách hàng / Bên giao thiết bị sửa chữa / 買方 / 委託方):
   - Tên công ty (Việt & Trung), Địa chỉ (Việt & Trung), Mã số thuế, Người đại diện, Chức vụ.
   - Nếu không có tiếng Trung thì để chuỗi rỗng. Tuyệt đối không tự bịa đặt MST hay địa chỉ nếu đề bài không có.

3. Thông tin dịch vụ sửa chữa:
   - ten_goi_sua_chua_viet: Tóm tắt tên gói dịch vụ (Ví dụ: "Dịch vụ sửa chữa hệ thống máy trạm và bo mạch I/O Gateway tại nhà máy CX")
   - ten_goi_sua_chua_trung: Tên gói tiếng Trung (Ví dụ: "CX 廠區工控機與 I/O 網關控制板維修保養服務")
   - dia_diem_sua_chua: Nơi thực hiện sửa chữa (Ví dụ: "Tại xưởng sản xuất Bên A" hoặc "Tại trung tâm kỹ thuật Hong Ming Global")
   - thoi_gian_hoan_thanh_ngay: Thời hạn hoàn thành sửa chữa tính theo ngày (Mặc định 10-15 ngày nếu không nêu)
   - thoi_gian_bao_hanh_thang: Thời gian bảo hành dịch vụ và linh kiện sau sửa chữa (Mặc định 3, 6 hoặc 12 tháng tùy giá trị)

4. Tiến độ thanh toán (phan_bo_thanh_toan):
   - HỖ TRỢ ĐẶC BIỆT CÚ PHÁP VIẾT TẮT SỐ NGÀY:
     + Số `0`: ngay lập tức (ngay sau khi ký hợp đồng / 雙方簽約後即期以電匯方式支付, "thoi_han_tt_ngay": 0).
     + Số N (ví dụ `30`, `60`): thời hạn thanh toán T/T N ngày sau khi nghiệm thu đạt yêu cầu.
   - Nếu đề bài ghi "Đặt cọc 50%, sửa xong nghiệm thu trả 50%" hoặc "50% 0, 50% 30" -> Bóc tách thành 2 đợt:
     + Đợt 1 (50%): Tạm ứng ký hợp đồng (簽約預付款)
     + Đợt 2 (50%): Nghiệm thu hoàn thành sửa chữa (維修驗收完成款)
   - Nếu chỉ ghi thanh toán 100% sau khi sửa xong và nghiệm thu đạt -> 1 đợt 100%.

5. Tự động tính toán tổng số tiền bằng số và làm tròn chuẩn.

ĐỊNH DẠNG JSON ĐẦU RA BẮT BUỘC:
{
  "so_hop_dong": "HDSC-20261019-001",
  "ngay_ky": "19",
  "thang_ky": "10",
  "nam_ky": "2026",
  "ben_a": {
    "ten_cong_ty": "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
    "ten_tieng_trung": "越南CX科技股份有限公司",
    "dia_chi": "Lô K1, Khu chế xuất Tân Thuận, P. Tân Thuận Đông, Q. 7, TP. HCM",
    "dia_chi_trung": "胡志明市第七郡新順加工出口區K1地塊",
    "mst": "0301789999",
    "nguoi_dai_dien": "CHEN CHEN-YEN",
    "chuc_vu": "TỔNG GIÁM ĐỐC",
    "chuc_vu_trung": "總經理"
  },
  "ben_b": {
    "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
    "ten_tieng_trung": "宏明環球有限公司",
    "dia_chi": "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
    "dia_chi_trung": "越南胡志明市西貢坊阮惠路68號2樓",
    "mst": "0318280158",
    "nguoi_dai_dien": "TANG WEI LI",
    "chuc_vu": "TỔNG GIÁM ĐỐC",
    "chuc_vu_trung": "總經理"
  },
  "ten_goi_sua_chua_viet": "Dịch vụ kiểm tra, sửa chữa và thay thế linh kiện hệ thống máy tính công nghiệp",
  "ten_goi_sua_chua_trung": "工控機設備檢修、更換零件及維修服務",
  "dia_diem_sua_chua": "Tại xưởng sản xuất Bên A (KCX Tân Thuận, Quận 7, TP.HCM)",
  "hang_muc": [
    {
      "stt": 1,
      "ten_thiet_bi": "Máy tính công nghiệp IPC Advantech / 研華工控機",
      "model_serial": "IPC-610H / SN: CX20250912",
      "noi_dung_sua_chua": "Không lên nguồn, chập tụ nguồn chính - Thay nguồn ATX 400W chuyên dụng và vệ sinh tản nhiệt",
      "don_vi_tinh": "Bộ",
      "don_gia": "6.800.000 VND",
      "so_luong": "2 Bộ",
      "tong_gia": "13.600.000 VND"
    }
  ],
  "tong_so_luong": "2 Bộ",
  "tong_tien_truoc_giam": "13.600.000 VND",
  "tong_tien_sau_giam": "13.600.000 VND",
  "tong_tien_hop_dong_so": "13.600.000",
  "thoi_gian_hoan_thanh_ngay": 10,
  "thoi_gian_bao_hanh_thang": 6,
  "phan_bo_thanh_toan": [
    {
      "dot": 1,
      "phan_tram": 50,
      "so_tien": "6.800.000 VND",
      "tieu_de": "Tạm ứng ký hợp đồng",
      "tieu_de_trung": "簽約預付款",
      "dieu_kien_viet": "Thanh toán tạm ứng 50% ngay sau khi ký hợp đồng và tiếp nhận thiết bị",
      "dieu_kien_trung": "雙方簽約並交付待修設備後即期支付 50%",
      "thoi_han_tt_ngay": 0
    },
    {
      "dot": 2,
      "phan_tram": 50,
      "so_tien": "6.800.000 VND",
      "tieu_de": "Nghiệm thu hoàn tất",
      "tieu_de_trung": "驗收交付款",
      "dieu_kien_viet": "Thanh toán 50% còn lại sau khi hoàn thành sửa chữa, chạy thử đạt và ký biên bản nghiệm thu",
      "dieu_kien_trung": "設備維修完成、測試正常並簽署驗收確認書後支付剩餘 50%",
      "thoi_han_tt_ngay": 30
    }
  ]
}

CHỈ TRẢ VỀ DUY NHẤT KHỐI JSON HỢP LỆ (BẮT ĐẦU BẰNG { VÀ KẾT THÚC BẰNG }), KHÔNG VIẾT BẤT KỲ LỜI MỞ ĐẦU HAY GIẢI THÍCH NÀO NGOÀI JSON.
"""


def extract_text_from_excel(file_bytes: bytes) -> str:
    """Extract rows and tables from Excel file bytes (.xlsx, .xlsm, .xltx)."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        text_lines = []
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            text_lines.append(f"\n--- SHEET: {sheet} ---")
            for row in ws.iter_rows(values_only=True):
                non_empty = [str(cell).strip() for cell in row if cell is not None and str(cell).strip() != ""]
                if non_empty:
                    text_lines.append("\t".join(non_empty))
        return "\n".join(text_lines)
    except Exception as exc:
        logger.warning(f"Failed to read Excel workbook: {exc}")
        return ""


def call_gemini_api(
    prompt: str,
    system_instruction: str = SYSTEM_PROMPT_REPAIR,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_mime_type: Optional[str] = None,
) -> str:
    """Call Google Gemini API with fallback key & candidate model chain."""
    keys_to_try = [api_key] if api_key else DEFAULT_GEMINI_KEYS
    target_models = [model_name] if model_name else CANDIDATE_MODELS

    last_error = None
    for current_key in keys_to_try:
        if not current_key:
            continue
        for current_model in target_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={current_key}"

            contents_parts = []
            if image_base64:
                mime = image_mime_type or "image/png"
                contents_parts.append({
                    "inline_data": {
                        "mime_type": mime,
                        "data": image_base64
                    }
                })

            contents_parts.append({"text": prompt})

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": contents_parts
                    }
                ],
                "systemInstruction": {
                    "role": "user",
                    "parts": [{"text": system_instruction}]
                },
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.95,
                    "maxOutputTokens": 8192
                }
            }

            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=35) as response:
                    body = response.read().decode("utf-8")
                    resp_json = json.loads(body)
                    candidates = resp_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
            except urllib.error.HTTPError as http_err:
                last_error = http_err
                err_body = ""
                try:
                    err_body = http_err.read().decode("utf-8")
                except Exception:
                    pass
                logger.warning(
                    f"Gemini API error (model: {current_model}): {http_err.code} {http_err.reason} - {err_body}"
                )
                continue
            except Exception as exc:
                last_error = exc
                logger.warning(f"Gemini API connection error (model: {current_model}): {exc}")
                continue

    raise RuntimeError(f"All Gemini models/keys exhausted for repair parsing. Last error: {last_error}")


def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Strip markdown code fence backticks and clean JSON output."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace : last_brace + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error(f"Failed to parse cleaned JSON: {cleaned[:300]}...")
        raise ValueError(f"Gemini AI returned invalid JSON: {exc}")


def parse_repair_contract_with_ai(
    raw_text: str = "",
    model_name: Optional[str] = None,
    file_base64: Optional[str] = None,
    file_name: Optional[str] = None,
    file_mime: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse text and/or file for Repair Contract."""
    extracted_text = ""
    image_base64 = None
    image_mime = None

    if file_base64:
        mime = (file_mime or "").lower()
        fname = (file_name or "").lower()

        is_excel = (
            "spreadsheet" in mime
            or "excel" in mime
            or fname.endswith((".xlsx", ".xls", ".xlsm"))
        )
        is_image = (
            mime.startswith("image/")
            or fname.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"))
        )

        try:
            file_bytes = base64.b64decode(file_base64)
            if is_excel:
                extracted_text = extract_text_from_excel(file_bytes)
            elif is_image:
                image_base64 = file_base64
                image_mime = mime or "image/png"
            elif fname.endswith(".txt"):
                extracted_text = file_bytes.decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning(f"Error decoding attached file: {exc}")

    prompt_parts = []
    if raw_text and raw_text.strip():
        prompt_parts.append(f"GHI CHÚ / YÊU CẦU CỦA NGƯỜI DÙNG:\n{raw_text.strip()}")
    if extracted_text:
        prompt_parts.append(f"\nDỮ LIỆU ĐƯỢC TRÍCH XUẤT TỪ FILE EXCEL / TÀI LIỆU:\n{extracted_text}")
    if image_base64 and not prompt_parts:
        prompt_parts.append("Hãy đọc ảnh bảng báo giá sửa chữa / biên bản kiểm tra thiết bị hư hỏng đính kèm và trích xuất bảng sản phẩm sửa chữa, số tiền, khách hàng.")

    full_prompt = "\n\n".join(prompt_parts)
    if not full_prompt and not image_base64:
        raise ValueError("Vui lòng cung cấp nội dung văn bản, bảng báo giá sửa chữa hoặc tải lên tệp đính kèm.")

    raw_ai_out = call_gemini_api(
        prompt=full_prompt,
        system_instruction=SYSTEM_PROMPT_REPAIR,
        model_name=model_name,
        image_base64=image_base64,
        image_mime_type=image_mime,
    )

    data = clean_json_response(raw_ai_out)

    # Post-process currency and words
    raw_amount = data.get("tong_tien_hop_dong_so", "")
    numeric_val = parse_positive_integer(raw_amount)

    # If 0, compute from items
    if numeric_val == 0 and data.get("hang_muc"):
        total_calc = 0
        for item in data["hang_muc"]:
            val = parse_positive_integer(item.get("tong_gia", ""))
            if val == 0:
                p = parse_positive_integer(item.get("don_gia", ""))
                q = parse_positive_integer(item.get("so_luong", "1")) or 1
                val = p * q
                item["tong_gia"] = format_currency_vnd(val)
            total_calc += val
        numeric_val = total_calc

    if numeric_val > 0:
        data["tong_tien_hop_dong_so"] = format_currency_vnd(numeric_val).replace(" VND", "")
        data["tong_tien_sau_giam"] = format_currency_vnd(numeric_val)
        data["tong_tien_chu_viet"] = number_to_vietnamese_words(numeric_val)
        data["tong_tien_chu_trung"] = number_to_chinese_words(numeric_val)

        # Update installment amounts if percent is provided but amount is missing
        if data.get("phan_bo_thanh_toan"):
            for inst in data["phan_bo_thanh_toan"]:
                pct = float(inst.get("phan_tram", 0) or 0)
                if pct > 0:
                    inst_amount = round(numeric_val * pct / 100)
                    inst["so_tien"] = format_currency_vnd(inst_amount)

    return data
