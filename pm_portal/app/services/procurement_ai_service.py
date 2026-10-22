# -*- coding: utf-8 -*-
"""AI Service for parsing supplier quotations and procurement orders via Gemini API."""

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.config import CANDIDATE_MODELS, DEFAULT_GEMINI_KEY, DEFAULT_GEMINI_KEYS, DEFAULT_MODEL
from app.utils.ai_file_helper import process_uploaded_file_for_ai

logger = logging.getLogger(__name__)


PROCUREMENT_SYSTEM_PROMPT = """Bạn là chuyên gia Quản lý Mua hàng & Cung ứng thiết bị (Procurement / PO Specialist) cho CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司).
Hong Ming là nhà tích hợp hệ thống IoT công nghiệp (SMB IoT), tiết kiệm năng lượng (EMS), hệ thống RFID và máy chủ CNTT.

NHIỆM VỤ:
Phân tích văn bản đầu vào (Báo giá NCC, Đơn chào hàng, Email xác nhận đặt hàng, Tin nhắn WeChat/Zalo hoặc Hóa đơn tạm tính) và trích xuất thành danh sách các đơn mua hàng (procurement orders) chuẩn xác 100% để lưu vào hệ thống theo dõi.

QUY TẮC BÓC TÁCH:
1. Dự án & Khách hàng:
   - project_name: Tên dự án (Ví dụ: Cheng Feng Le Hua, Seiyo, Darfon Phase 2, Ji Yang, CX Technology, Hong Ming nội bộ...). Nếu không rõ, ghi 'Dự án chung'.
   - customer_company: Khách hàng cuối (Ví dụ: CHENG FENG LE HUA, SEIYO, DARFON, CX, JI YANG...).
2. Nhà cung cấp (supplier_name):
   - Tên nhà cung cấp / đối tác bán hàng (Ví dụ: TBL, Advantech, A&B, Viet A Tech, BDA, Hằng Thanh...).
3. Danh mục vật tư / thiết bị (items):
   - item_name: Tên đầy đủ kèm mã hiệu, Part Number và cấu hình chi tiết (VD: 'DELL POWEREDGE R760xs Server Intel Xeon Silver 4509Y, 64GB DDR5, SSD 480GB + 4x2TB HDD', 'Bộ chuyển mạch TL-SG3210 8 port Gigabit + 2 SFP', 'Máy tính để bàn Asus D701MER i7-14700 64GB SSD 1TB').
   - category: Phân loại chuẩn ('MÁY CHỦ SERVER', 'MAY TINH IPC', 'MANG', 'Thiết bị PDA', 'DIAN SHI', 'Hệ thống', 'Vật tư', 'Thiết bị').
   - quantity: Số lượng (float/int).
   - unit: Đơn vị tính ('Bộ', 'Cái', 'Chiếc', 'Mét'...).
   - unit_price: Đơn giá (số nguyên/thực).
   - total_amount: Thành tiền (số nguyên/thực).
   - currency: Loại tiền tệ ('VND', 'USD', 'TWD').
4. Thời gian:
   - order_date: Ngày đặt hàng (Định dạng chuẩn YYYY-MM-DD, nếu không có để null).
   - eta_date: Ngày giao dự kiến ETA (Định dạng chuẩn YYYY-MM-DD, nếu không có để null).
   - actual_delivery_date: Ngày giao thực tế nếu đã nhận hàng (YYYY-MM-DD, nếu chưa có để null).
5. Thanh toán & Vận chuyển:
   - supplier_payment_status: Điều khoản thanh toán NCC (VD: 'Cọc 50%, nhận hàng thanh toán 50%', 'Chờ thanh toán', 'Đã thanh toán', 'Net 30 ngày'...).
   - delivery_status: 'PENDING' (chờ xử lý), 'IN_TRANSIT' (đang giao/chờ ETA), 'DELIVERED' (đã giao), 'DELAYED' (trễ hạn).
   - shipping_notes: Ghi chú vận chuyển, tình trạng hàng hóa, rủi ro, bảo hành.

ĐỊNH DẠNG JSON ĐẦU RA BẮT BUỘC:
{
  "project_name": "CHENG FENG LE HUA VIỆT NAM",
  "customer_company": "CHENG FENG LE HUA VIỆT NAM",
  "supplier_name": "TBL",
  "order_date": "2026-10-01",
  "eta_date": "2026-10-06",
  "supplier_payment_status": "Chờ thanh toán",
  "items": [
    {
      "item_name": "Bảng thông tin năng suất Smart Google TV TCL 65 inch + giá đỡ di động",
      "category": "DIAN SHI",
      "quantity": 1,
      "unit": "Bộ",
      "unit_price": 12500000,
      "total_amount": 12500000,
      "currency": "VND",
      "order_date": "2026-10-01",
      "eta_date": "2026-10-06",
      "actual_delivery_date": null,
      "supplier_payment_status": "Chờ thanh toán",
      "shipping_notes": "Giao tận nhà máy KCN Quế Võ"
    }
  ],
  "summary_notes": "Báo giá thiết bị TV và máy tính cho dự án Cheng Feng"
}
"""


def _clean_json_response(raw_text: str) -> str:
    """Clean markdown code block wrapping from LLM output."""
    cleaned = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    return cleaned


def parse_procurement_ai(
    raw_text: Optional[str] = None,
    preferred_model: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Gemini API with model fallback to extract procurement details from text and/or attached file."""
    extracted_file_text, inline_part = None, None
    if file_bytes and filename:
        extracted_file_text, inline_part = process_uploaded_file_for_ai(file_bytes, filename, content_type)

    has_text = bool(raw_text and raw_text.strip())
    has_file = bool(extracted_file_text or inline_part)

    if not has_text and not has_file:
        return {
            "status": "error",
            "message": "Vui lòng nhập văn bản hoặc đính kèm tập tin báo giá / đơn hàng.",
            "data": None
        }

    parts = [{"text": PROCUREMENT_SYSTEM_PROMPT}]
    if has_text:
        parts.append({"text": f"DƯỚI ĐÂY LÀ VĂN BẢN / GHI CHÚ:\n\n{raw_text.strip()}"})
    if extracted_file_text:
        parts.append({"text": f"DƯỚI ĐÂY LÀ NỘI DUNG TỪ TẬP TIN ({filename}):\n\n{extracted_file_text}"})
    if inline_part:
        parts.append(inline_part)

    keys = DEFAULT_GEMINI_KEYS if DEFAULT_GEMINI_KEYS else [DEFAULT_GEMINI_KEY]
    models = [preferred_model] if preferred_model else CANDIDATE_MODELS
    # Ensure preferred model is first
    models = [m for m in models if m]

    last_error = ""

    payload = {
        "contents": [
            {
                "parts": parts
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    for key in keys:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            try:
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data_bytes,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))

                candidates = resp_data.get("candidates", [])
                if not candidates:
                    continue

                content_parts = candidates[0].get("content", {}).get("parts", [])
                if not content_parts:
                    continue

                raw_json = content_parts[0].get("text", "")
                cleaned_json = _clean_json_response(raw_json)
                parsed_data = json.loads(cleaned_json)

                # Post-process items to ensure standard fields
                items = parsed_data.get("items", [])
                if not items and "item_name" in parsed_data:
                    items = [parsed_data]

                processed_items = []
                for it in items:
                    processed_items.append({
                        "project_name": it.get("project_name") or parsed_data.get("project_name") or "Dự án chung",
                        "customer_company": it.get("customer_company") or parsed_data.get("customer_company"),
                        "supplier_name": it.get("supplier_name") or parsed_data.get("supplier_name") or "NCC",
                        "category": it.get("category"),
                        "item_name": it.get("item_name") or "Vật tư thiết bị",
                        "quantity": float(it.get("quantity") or 1.0),
                        "unit": it.get("unit") or "Bộ",
                        "unit_price": float(it.get("unit_price") or 0.0),
                        "total_amount": float(it.get("total_amount") or 0.0),
                        "currency": it.get("currency") or "VND",
                        "order_date": it.get("order_date") or parsed_data.get("order_date"),
                        "eta_date": it.get("eta_date") or parsed_data.get("eta_date"),
                        "actual_delivery_date": it.get("actual_delivery_date"),
                        "supplier_payment_status": it.get("supplier_payment_status") or parsed_data.get("supplier_payment_status"),
                        "shipping_notes": it.get("shipping_notes") or parsed_data.get("summary_notes"),
                    })

                return {
                    "status": "success",
                    "model_used": model,
                    "project_name": parsed_data.get("project_name"),
                    "customer_company": parsed_data.get("customer_company"),
                    "supplier_name": parsed_data.get("supplier_name"),
                    "items": processed_items,
                    "summary_notes": parsed_data.get("summary_notes")
                }

            except Exception as e:
                last_error = str(e)
                logger.warning("Gemini model %s failed: %s", model, e)
                continue

    return {
        "status": "error",
        "message": f"Không thể trích xuất qua Gemini AI: {last_error}",
        "data": None
    }
