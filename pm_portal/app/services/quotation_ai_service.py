"""AI Service for parsing unstructured text or files into quotation data via Google Gemini API."""

import base64
import json
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import openpyxl
from docx import Document

from app.config import CANDIDATE_MODELS, DEFAULT_GEMINI_KEY, DEFAULT_GEMINI_KEYS, DEFAULT_MODEL
from app.utils.currency_helper import parse_positive_integer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên gia bóc tách dữ liệu báo giá thiết bị IoT nhà máy và hệ thống tiết kiệm điện EMS cho CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司).

NHIỆM VỤ CỦA BẠN:
Phân tích văn bản yêu cầu báo giá, danh sách thiết bị từ email, chat WeChat hoặc bảng tính khảo sát và trích xuất thành định dạng JSON chuẩn xác 100%.

QUY TẮC CỐT LÕI:
1. Bóc tách toàn bộ danh mục sản phẩm / thiết bị / dịch vụ: Tên thiết bị kèm quy cách kỹ thuật (song ngữ Việt - Trung nếu có), Đơn vị tính (Bộ, Cái, Hệ, Cuộn, Gói...), Số lượng, Đơn giá dự kiến (nếu không có thì để 0).
2. Trích xuất thông tin khách hàng nếu có: Tên tiếng Việt, Tên tiếng Trung, Mã số thuế, Người liên hệ, Tên dự án.
3. Nếu không có số báo giá cụ thể, hãy đề xuất số báo giá theo định dạng: HM-QT-YYYYMM-001 (dựa theo tháng năm hiện tại).
4. Các điều khoản thương mại: Nếu trong văn bản có nêu thời hạn hiệu lực, lead time, bảo hành, điều kiện thanh toán thì trích xuất; nếu không nêu thì dùng mặc định tiêu chuẩn:
   - validity: "30 ngày kể từ ngày phát hành"
   - lead_time: "60 - 80 ngày sau khi nhận đủ tiền đặt cọc"
   - warranty: "12 tháng chính hãng kể từ ngày nghiệm thu"
   - payment_terms: "Tạm ứng 50%, Giao hàng 40%, Nghiệm thu 10%". HỖ TRỢ CÚ PHÁP VIẾT TẮT: số 0 là "ngay lập tức", số N (như 30, 60) là "N ngày". Ví dụ: "35% 0, 55% 60, 10% 60" -> "Tạm ứng 35% ngay lập tức, Giao hàng 55% (60 ngày), Nghiệm thu 10% (60 ngày)".
5. Trả về đúng định dạng JSON thuần túy, không bọc giải thích rườm rà.

ĐỊNH DẠNG JSON ĐẦU RA BẮT BUỘC:
{
  "customer_name_vi": "Tên công ty tiếng Việt nếu có",
  "customer_name_zh": "Tên công ty tiếng Trung nếu có",
  "tax_code": "Mã số thuế nếu có",
  "quotation_no": "HM-QT-202610-001",
  "quotation_date": "16/10/2026",
  "project_name": "Tên dự án phù hợp với thiết bị",
  "contact_person": "Phòng ban hoặc người liên hệ nếu có",
  "validity": "30 ngày kể từ ngày phát hành",
  "lead_time": "60 - 80 ngày sau khi nhận đủ tiền đặt cọc",
  "warranty": "12 tháng chính hãng kể từ ngày nghiệm thu",
  "payment_terms": "Tạm ứng 50%, Giao hàng 40%, Nghiệm thu 10%",
  "notes": "Ghi chú kỹ thuật hoặc phạm vi công việc",
  "items": [
    {
      "name": "Tên thiết bị / dịch vụ kèm quy cách",
      "unit": "Bộ",
      "qty": 1,
      "price": 18500000
    }
  ]
}
"""


def extract_text_from_excel(file_bytes: bytes) -> str:
    """Read cell values from uploaded Excel workbook for quotation parsing."""
    try:
        wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
        lines = []
        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            lines.append(f"--- SHEET: {sheetname} ---")
            for row in ws.iter_rows(values_only=True):
                non_empty = [str(c).strip() for c in row if c is not None and str(c).strip() != ""]
                if non_empty:
                    lines.append(" | ".join(non_empty))
        return "\n".join(lines[:250])
    except Exception as exc:
        logger.warning("Failed to extract Excel content: %s", exc)
        return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Read paragraphs and tables from uploaded DOCX file."""
    try:
        doc = Document(BytesIO(file_bytes))
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_vals = [c.text.strip() for c in row.cells if c.text.strip()]
                if row_vals:
                    lines.append(" | ".join(row_vals))
        return "\n".join(lines[:300])
    except Exception as exc:
        logger.warning("Failed to extract DOCX content: %s", exc)
        return ""


def fallback_heuristic_parse(raw_text: str) -> Dict[str, Any]:
    """Fallback parser using regex when Gemini API is offline or unavailable."""
    today_str = datetime.now().strftime("%d/%m/%Y")
    now_ym = datetime.now().strftime("%Y%m")

    cust_vi = "KHÁCH HÀNG DOANH NGHIỆP"
    cust_zh = ""
    proj = "Dự Án Cung Cấp Thiết Bị & Dịch Vụ IoT"
    quote_no = f"HM-QT-{now_ym}-001"

    # Search for customer
    cust_match = re.search(r"(?:công ty|khách hàng|kính gửi|to|customer)\s*[:：\-]?\s*([^\n\r,]+)", raw_text, re.IGNORECASE)
    if cust_match:
        cust_vi = cust_match.group(1).strip()

    tax_match = re.search(r"(?:mst|tax|mã số thuế)\s*[:：\-]?\s*([0-9\-]+)", raw_text, re.IGNORECASE)
    tax_code = tax_match.group(1).strip() if tax_match else ""

    items = []
    lines = raw_text.splitlines()
    for line in lines:
        cleaned = line.strip("-* \t•")
        if not cleaned or len(cleaned) < 3:
            continue
        # Check if line looks like item
        # e.g. "Đồng hồ đo điện PM2100: 4 bộ x 18.500.000"
        qty_price_match = re.search(r"(?:số lượng|sl|qty)?\s*[:：]?\s*(\d+)\s*(bộ|cái|hệ|cuộn|gói|bộ|set|ea)?(?:\s*[x*]\s*([0-9.,]+))?", cleaned, re.IGNORECASE)
        if qty_price_match:
            qty = int(qty_price_match.group(1)) if qty_price_match.group(1) else 1
            unit = qty_price_match.group(2) or "Bộ"
            price = parse_positive_integer(qty_price_match.group(3)) if qty_price_match.group(3) else 0
            name = cleaned.split(":")[0].strip() if ":" in cleaned else cleaned
            items.append({
                "name": name,
                "unit": unit,
                "qty": qty,
                "price": price
            })
        elif len(items) < 8 and ("thiết bị" in cleaned.lower() or "cáp" in cleaned.lower() or "tủ" in cleaned.lower() or "gateway" in cleaned.lower() or "cổng" in cleaned.lower()):
            items.append({
                "name": cleaned,
                "unit": "Bộ",
                "qty": 1,
                "price": 0
            })

    if not items:
        items = [
            {"name": "Thiết Bị Theo Bảng Khảo Sát Kỹ Thuật", "unit": "Bộ", "qty": 1, "price": 0}
        ]

    return {
        "customer_name_vi": cust_vi,
        "customer_name_zh": cust_zh,
        "tax_code": tax_code,
        "quotation_no": quote_no,
        "quotation_date": today_str,
        "project_name": proj,
        "contact_person": "Phòng Kỹ Thuật / Mua Hàng",
        "validity": "30 ngày kể từ ngày phát hành",
        "lead_time": "60 - 80 ngày sau khi nhận đủ tiền đặt cọc",
        "warranty": "12 tháng chính hãng kể từ ngày nghiệm thu",
        "payment_terms": "Tạm ứng 50%, Giao hàng 40%, Nghiệm thu 10%",
        "notes": "Báo giá trích xuất sơ bộ từ nội dung yêu cầu.",
        "items": items,
        "_executed_model": "Heuristic Parser"
    }


def parse_quotation_text(
    raw_input_text: str,
    file_bytes: Optional[bytes] = None,
    file_mime_type: Optional[str] = None,
    file_name: Optional[str] = None,
    preferred_model: Optional[str] = None
) -> Dict[str, Any]:
    """Parse quotation raw input text or attachments using Gemini API with model rotation."""
    keys_to_try = [k for k in DEFAULT_GEMINI_KEYS if k]
    if DEFAULT_GEMINI_KEY and DEFAULT_GEMINI_KEY not in keys_to_try:
        keys_to_try.insert(0, DEFAULT_GEMINI_KEY)

    models_to_try = []
    if preferred_model and preferred_model in CANDIDATE_MODELS:
        models_to_try.append(preferred_model)
    for m in CANDIDATE_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    fname_lower = (file_name or "").lower()
    fmime_lower = (file_mime_type or "").lower()
    is_image = any(ext in fname_lower or ext in fmime_lower for ext in ("jpg", "jpeg", "png", "webp"))
    is_excel = any(ext in fname_lower or ext in fmime_lower for ext in ("xls", "xlsx", "spreadsheet"))
    is_docx = any(ext in fname_lower or ext in fmime_lower for ext in ("doc", "docx", "word"))

    parts = []
    if file_bytes and is_image:
        mime_to_send = "image/jpeg"
        if "png" in fname_lower or "png" in fmime_lower:
            mime_to_send = "image/png"
        elif "webp" in fname_lower or "webp" in fmime_lower:
            mime_to_send = "image/webp"

        prompt_text = f"{SYSTEM_PROMPT}\n\nHÃY BÓC TÁCH BẢNG BÁO GIÁ / DANH MỤC THIẾT BỊ TỪ ẢNH ĐÍNH KÈM:"
        if raw_input_text and raw_input_text.strip():
            prompt_text += f"\n\nGhi chú bổ sung:\n{raw_input_text.strip()}"

        parts = [
            {"text": prompt_text},
            {
                "inlineData": {
                    "mimeType": mime_to_send,
                    "data": base64.b64encode(file_bytes).decode("ascii")
                }
            }
        ]
    elif file_bytes and is_excel:
        excel_text = extract_text_from_excel(file_bytes)
        prompt_text = (
            f"{SYSTEM_PROMPT}\n\nDỮ LIỆU ĐỌC TỪ BẢNG TÍNH EXCEL ĐÍNH KÈM ({file_name or 'Bao_Gia.xlsx'}):\n\"\"\"\n{excel_text}\n\"\"\""
        )
        if raw_input_text and raw_input_text.strip():
            prompt_text += f"\n\nCHÚ THÍCH CỦA NGƯỜI DÙNG:\n\"\"\"\n{raw_input_text.strip()}\n\"\"\""
        parts = [{"text": prompt_text}]
    elif file_bytes and is_docx:
        docx_text = extract_text_from_docx(file_bytes)
        prompt_text = (
            f"{SYSTEM_PROMPT}\n\nDỮ LIỆU ĐỌC TỪ TỆP WORD ĐÍNH KÈM ({file_name or 'Bao_Gia.docx'}):\n\"\"\"\n{docx_text}\n\"\"\""
        )
        if raw_input_text and raw_input_text.strip():
            prompt_text += f"\n\nCHÚ THÍCH CỦA NGƯỜI DÙNG:\n\"\"\"\n{raw_input_text.strip()}\n\"\"\""
        parts = [{"text": prompt_text}]
    else:
        prompt = f"{SYSTEM_PROMPT}\n\nDỮ LIỆU ĐẦU VÀO CẦN BÓC TÁCH BÁO GIÁ:\n\"\"\"\n{raw_input_text}\n\"\"\""
        parts = [{"text": prompt}]

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    parsed = None
    executed_model = None

    if keys_to_try:
        for key in keys_to_try:
            for model in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                logger.info("Quotation AI: attempting model %s", model)
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                try:
                    with urllib.request.urlopen(req, timeout=25) as response:
                        result = json.loads(response.read().decode("utf-8"))
                        candidate = result.get("candidates", [])[0]
                        text_out = candidate["content"]["parts"][0]["text"].strip()
                        if text_out.startswith("```json"):
                            text_out = text_out[7:]
                        elif text_out.startswith("```"):
                            text_out = text_out[3:]
                        if text_out.endswith("```"):
                            text_out = text_out[:-3]
                        parsed = json.loads(text_out.strip())
                        executed_model = model
                        break
                except Exception as exc:
                    logger.warning("Quotation AI failed with model %s: %s", model, exc)
                    continue
            if parsed:
                break

    if not parsed:
        logger.info("Falling back to heuristic quotation parser.")
        parsed = fallback_heuristic_parse(raw_input_text)
        executed_model = parsed.get("_executed_model", "Heuristic Parser")

    parsed["_executed_model"] = executed_model
    return parsed
