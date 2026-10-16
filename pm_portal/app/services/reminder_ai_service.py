"""AI Service for parsing unstructured payment reminder and request data via Gemini API."""

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict

from app.config import CANDIDATE_MODELS, DEFAULT_GEMINI_KEY, DEFAULT_MODEL, DEFAULT_GEMINI_KEYS
from app.utils.currency_helper import parse_positive_integer

logger = logging.getLogger(__name__)

REMINDER_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích dữ liệu công nợ, đề nghị thanh toán và thư nhắc nợ song ngữ (Việt - Trung) cho CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司).

NHIỆM VỤ:
Phân tích văn bản đầu vào (email cũ, tin nhắn trao đổi thanh toán, biên bản nghiệm thu hoặc ghi chú hợp đồng) và trích xuất thành JSON chuẩn 100% để phục vụ việc tạo email và giấy đề nghị thanh toán (DXYCTT).

QUY TẮC CỐT LÕI:
1. Trích xuất danh sách các khoản thanh toán / hợp đồng (khoan_thanh_toan):
   - stt: 1, 2, 3...
   - so_hop_dong: Mã hợp đồng (VD: HMV15092026-001, HMV15092026-002)
   - hang_muc: Tên sản phẩm, dịch vụ hoặc gói thi công (VD: BAT-RFR900 電池 3 SET, Cung cấp dịch vụ bảo dưỡng sửa chữa...)
   - noi_dung_thanh_toan: Nội dung đợt thanh toán (VD: 合約款 50%, Tạm ứng 30%, Nghiệm thu 10% FAC...)
   - so_tien: Số tiền thanh toán bằng số nguyên (VD: 5508000, 32500000)
   - vat_info: Thông tin VAT nếu có (VD: 含 VAT 8%, Đã gồm VAT 8%, Chưa VAT)
   - han_thanh_toan: Hạn chót thanh toán (VD: 2026/09/30, 2026/10/15)
2. Trích xuất thông tin khách hàng (khach_hang):
   - ten_khach_hang: Tên tiếng Việt (VD: CX Technology (VN), CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN))
   - ten_tieng_trung: Tên tiếng Trung (VD: CX Technology (VN) 股份有限公司)
   - email_to: Danh sách email người nhận nếu tìm thấy (VD: ["pur04_vn@mail.cxtechnology.com"])
   - email_cc: Danh sách email CC nếu tìm thấy (VD: ["jenson@youngming-mes.com", "sales@hongming-global.com"])
3. Xác định cấp độ nhắc nợ (cap_do):
   - 1: Đề nghị thanh toán hoặc nhắc nhở trước hạn (mặc định)
   - 2: Nhắc nợ quá hạn 1-7 ngày
   - 3: Thư cảnh báo công nợ khẩn cấp (>14 ngày)
4. Tiêu đề email gợi ý (tieu_de_email): Song ngữ Việt - Trung chuẩn mực doanh nghiệp Đài Loan.

ĐỊNH DẠNG JSON ĐẦU RA BẮT BUỘC:
{
  "cap_do": 1,
  "so_cong_van": "HM-PR-20261013-001",
  "ngay_phat_hanh": "13/10/2026",
  "khach_hang": {
    "ten_khach_hang": "CX Technology (VN)",
    "ten_tieng_trung": "CX Technology (VN)",
    "email_to": ["pur04_vn@mail.cxtechnology.com"],
    "email_cc": ["jenson@youngming-mes.com", "jessica@youngming-mes.com", "lisa@youngming-mes.com", "sales@hongming-global.com"]
  },
  "khoan_thanh_toan": [
    {
      "stt": 1,
      "so_hop_dong": "HMV15092026-002",
      "hang_muc": "BAT-RFR900 電池 3 SET",
      "noi_dung_thanh_toan": "",
      "so_tien": "5508000",
      "vat_info": "含 VAT 8%",
      "han_thanh_toan": "2026/09/30",
      "ghi_chu": ""
    },
    {
      "stt": 2,
      "so_hop_dong": "HMV15092026-001",
      "hang_muc": "提供 CX 胡志明市工廠設備維修與保養服務",
      "noi_dung_thanh_toan": "合約款 50%",
      "so_tien": "32500000",
      "vat_info": "",
      "han_thanh_toan": "2026/10/15",
      "ghi_chu": ""
    }
  ],
  "tong_tien_so": "38008000",
  "danh_sach_dinh_kem": [
    "DXYCTT 32.500.000 & 5.508.000.pdf",
    "Bản scan Biên bản nghiệm thu và bàn giao (驗收暨移交使用確認書)",
    "Hóa đơn giá trị gia tăng điện tử (VAT)"
  ]
}

LƯU Ý: Chỉ trả về mã JSON thuần túy, không bao bọc bởi markdown block, không thêm lời chào hay giải thích.
"""


def _clean_json_response(raw_text: str) -> str:
    """Strip markdown backticks and extract pure JSON."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    return match.group(1).strip() if match else cleaned.strip()


def _build_contract_context_for_prompt(contract_code: str, milestone_name: str = None) -> str:
    """Pull contract & milestone info from SQLite database to provide context for Gemini."""
    if not contract_code:
        return ""
    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM contracts WHERE contract_code = ?", (contract_code,))
        c_row = c.fetchone()
        if not c_row:
            conn.close()
            return ""

        c.execute("SELECT * FROM payment_milestones WHERE contract_code = ? ORDER BY id ASC", (contract_code,))
        ms_rows = c.fetchall()
        conn.close()

        lines = [
            "BỐI CẢNH DỮ LIỆU HỢP ĐỒNG ĐÃ BIẾT TRONG HỆ THỐNG ĐỂ ĐỐI CHIẾU:",
            f"- Mã hợp đồng: {c_row['contract_code']}",
            f"- Tên khách hàng (VI): {c_row['customer_name_vi']}",
            f"- Tên khách hàng (ZH): {c_row['customer_name_zh'] or c_row['customer_name_vi']}",
            f"- Tên dự án (VI): {c_row['project_name_vi']}",
            f"- Tên dự án (ZH): {c_row['project_name_zh'] or ''}",
            f"- Tổng giá trị hợp đồng: {int(c_row['total_amount'] or 0):,} VND".replace(",", "."),
            f"- Kỹ sư phụ trách: {c_row['lead_engineer'] or 'Jenson Chang'}",
        ]
        if milestone_name:
            lines.append(f"- Đợt thanh toán mục tiêu đang chọn: {milestone_name}")

        lines.append("- Danh sách tiến độ các đợt thanh toán theo thỏa thuận hợp đồng:")
        for idx, m in enumerate(ms_rows, 1):
            amt_str = f"{int(m['amount'] or 0):,} VND".replace(",", ".")
            due_str = m['due_date'] or "Chờ kích hoạt"
            cond = m['trigger_condition'] or "Theo HĐ"
            lines.append(f"  * {m['milestone_name']} ({m['percentage']}% - {amt_str}): Hạn {due_str} · Điều kiện: {cond}")

        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Error fetching contract context for AI reminder: %s", exc)
        return ""


def parse_reminder_text(
    raw_input_text: str,
    preferred_model: str = None,
    contract_code: str = None,
    milestone_name: str = None,
    match_contract: bool = True
) -> Dict[str, Any]:
    """Call Gemini API with model & key rotation to extract payment request schema and correlate contract context."""
    models_to_try = [preferred_model] if preferred_model else []
    for m in CANDIDATE_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    keys_to_try = list(DEFAULT_GEMINI_KEYS)
    if DEFAULT_GEMINI_KEY and DEFAULT_GEMINI_KEY not in keys_to_try:
        keys_to_try.insert(0, DEFAULT_GEMINI_KEY)

    contract_context_str = ""
    if match_contract and contract_code:
        contract_context_str = _build_contract_context_for_prompt(contract_code, milestone_name)

    user_prompt_parts = []
    if contract_context_str:
        user_prompt_parts.append(contract_context_str)
        user_prompt_parts.append(
            "QUY TẮC ĐỐI CHIẾU:\n"
            "1. Tách mọi địa chỉ email người nhận thành email_to (người nhận chính) và email_cc (người được gửi kèm).\n"
            "2. Nếu người dùng đưa vào văn bản tự do (ví dụ: 'Gửi cho chị Lan lan.kt@... cc sếp Chen chen@...'), "
            "hãy bóc tách chính xác các email này và kết hợp chuẩn với dữ liệu Hợp đồng ở trên.\n"
            "3. Nếu có đợt thanh toán cụ thể, đối chiếu số tiền và hạn chót theo đúng hợp đồng (trừ khi người dùng chỉ định số tiền/ngày khác).\n"
            "4. Sinh tiêu đề email song ngữ chuẩn mực: 【宏明環球】合約編號 {so_hop_dong} {noi_dung_thanh_toan}款項到期提醒 / Yêu cầu hỗ trợ thanh toán {noi_dung_thanh_toan} HĐ {so_hop_dong} ({ten_khach_hang})."
        )
    
    user_prompt_parts.append(f"VĂN BẢN / CHỈ THỊ CẦN PHÂN TÍCH:\n{raw_input_text}")
    combined_user_text = "\n\n".join(user_prompt_parts)

    last_error = None

    for model_name in models_to_try:
        for api_key in keys_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "systemInstruction": {"parts": [{"text": REMINDER_SYSTEM_PROMPT}]},
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": combined_user_text}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json"
                }
            }

            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    candidates = resp_data.get("candidates", [])
                    if candidates:
                        raw_content = candidates[0]["content"]["parts"][0]["text"]
                        cleaned_json = _clean_json_response(raw_content)
                        parsed = json.loads(cleaned_json)
                        parsed["_executed_model"] = model_name
                        return parsed

            except urllib.error.HTTPError as http_err:
                status_code = http_err.code
                err_body = http_err.read().decode("utf-8", errors="ignore")
                logger.warning(
                    "Model %s failed with key ...%s (HTTP %s): %s",
                    model_name, api_key[-6:], status_code, err_body[:120]
                )
                last_error = http_err
                if status_code in (429, 403, 400):
                    continue
            except Exception as exc:
                logger.warning("Error with model %s: %s", model_name, exc)
                last_error = exc
                continue

    raise RuntimeError(f"Tất cả mô hình Gemini đều không thể xử lý yêu cầu. Lỗi cuối: {last_error}")
