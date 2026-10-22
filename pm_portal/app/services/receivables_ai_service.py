# -*- coding: utf-8 -*-
"""AI Service for Project Receivables (AR) risk analysis, overdue debt detection, and executive digest."""

import json
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from app.config import CANDIDATE_MODELS, DEFAULT_GEMINI_KEY, DEFAULT_GEMINI_KEYS, DEFAULT_MODEL
from app.services.receivables_service import list_receivables, get_receivables_stats

logger = logging.getLogger(__name__)

RECEIVABLES_ANALYST_SYSTEM_PROMPT = """Bạn là Chuyên gia Quản lý Tài chính Dự án & Thu hồi Công nợ (Credit Control & AR Specialist) cho CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司).
Hong Ming là doanh nghiệp cung cấp giải pháp IoT nhà máy (SMB IoT), tiết kiệm năng lượng (EMS), hệ thống RFID và máy chủ công nghiệp cho các nhà máy FDI (Đài Loan, Trung Quốc) tại Việt Nam như CX Technology, Vonmax, Darfon, Seiyo, Cheng Feng Le Hua.

NHIỆM VỤ:
Dựa trên dữ liệu tổng hợp công nợ dự án hiện tại, hãy lập Bản tin Phân tích & Cảnh báo Thu hồi Công nợ (AR Executive Digest) cho Ban Giám đốc (CEO Đường Vĩ Lực) và Trưởng bộ phận PM (Jenson Chang).

YÊU CẦU NỘI DUNG PHẢI ĐẠT ĐƯỢC:
1. Đánh giá sức khỏe dòng tiền thu hồi (% đã thu, tổng số tiền còn đọng).
2. Phân loại rủi ro công nợ:
   - Các khoản nợ đỏ (Báo động đỏ): Quá hạn lâu ngày, chưa có phản hồi hoặc khách hàng chây ì.
   - Các khoản nợ vàng: Sắp đến hạn trong 7-14 ngày tới cần chủ động đốc thúc chứng từ / VAT.
   - Các khoản nợ an toàn / đã thu tốt.
3. Top 3-5 khách hàng có dư nợ lớn nhất cần tập trung xử lý.
4. Đề xuất hành động tức thì cho PM (Actionable Advice): Cần gửi Thư nhắc nợ (催款函) cho ai, cần hoàn tất biên bản nghiệm thu (FAC) cho hợp đồng nào, cần xuất hóa đơn nào.

ĐỊNH DẠNG JSON TRẢ VỀ (BẮT BUỘC):
{
  "health_score": 75,
  "health_status": "Khá / Tốt / Cảnh báo / Nguy cơ cao",
  "summary_headline": "Dòng tiền thu hồi đạt 36%, cần ưu tiên thu hồi 1.48 tỷ VND quá hạn từ đối tác...",
  "aging_analysis": {
    "overdue_critical": "Số tiền và danh sách nợ quá hạn nghiêm trọng",
    "overdue_moderate": "Số tiền nợ quá hạn từ 1-30 ngày",
    "upcoming_soon": "Số tiền sắp đến hạn trong tuần này"
  },
  "top_risks": [
    {
      "customer": "Tên khách hàng",
      "project": "Tên dự án / Hợp đồng",
      "debt_amount": "Số tiền còn nợ",
      "overdue_days": "Số ngày trễ",
      "risk_level": "CAO / TRUNG BÌNH",
      "recommended_action": "Hành động cụ thể nên làm ngay"
    }
  ],
  "action_items": [
    "Hành động 1: Gửi thư nhắc nợ đợt 2...",
    "Hành động 2: Đối soát chứng từ nghiệm thu...",
    "Hành động 3: Đặt lịch họp trực tiếp..."
  ],
  "bilingual_executive_note": "Tóm tắt ngắn gọn 2-3 câu song ngữ Việt - Trung để PM dán vào báo cáo giao ban."
}
"""


def _clean_json_response(raw_text: str) -> str:
    """Clean markdown code block wrapping from LLM output."""
    cleaned = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    return cleaned


def _generate_rule_based_digest(stats: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate professional heuristic risk digest when AI API is unavailable."""
    total_gross = stats.get("total_receivable", 0.0)
    total_rec = stats.get("total_received", 0.0)
    total_debt = stats.get("total_debt", 0.0)
    completion_rate = stats.get("completion_rate", 0.0)
    overdue_count = stats.get("overdue_count", 0)
    urgent_count = stats.get("urgent_count", 0)

    # Find top overdue items
    overdue_items = [i for i in items if i.get("collection_status") == "DELAYED" and i.get("remaining_debt", 0) > 0]
    urgent_items = [i for i in items if i.get("collection_status") == "URGENT" and i.get("remaining_debt", 0) > 0]

    # Sort overdue by remaining debt descending
    overdue_items.sort(key=lambda x: x.get("remaining_debt", 0), reverse=True)
    urgent_items.sort(key=lambda x: x.get("remaining_debt", 0), reverse=True)

    top_risks = []
    for item in overdue_items[:5]:
        top_risks.append({
            "customer": item.get("customer_name") or "Khách hàng",
            "project": item.get("project_name") or item.get("contract_code") or "Dự án",
            "debt_amount": f"{int(round(item.get('remaining_debt', 0))):,} ₫".replace(",", "."),
            "overdue_days": f"Trễ {abs(item.get('days_left') or 0)} ngày",
            "risk_level": "CAO",
            "recommended_action": "Lập tức phát hành Thư nhắc nợ (催款函) và liên hệ phòng Kế toán đối tác"
        })

    for item in urgent_items[:3]:
        top_risks.append({
            "customer": item.get("customer_name") or "Khách hàng",
            "project": item.get("project_name") or item.get("contract_code") or "Dự án",
            "debt_amount": f"{int(round(item.get('remaining_debt', 0))):,} ₫".replace(",", "."),
            "overdue_days": f"Còn {item.get('days_left') or 0} ngày",
            "risk_level": "TRUNG BÌNH",
            "recommended_action": "Kiểm tra biên bản bàn giao, chuẩn bị xuất hóa đơn VAT và Phiếu đề nghị thanh toán"
        })

    health_status = "Tốt"
    health_score = 85
    if overdue_count >= 5 or total_debt > 3000000000:
        health_status = "Cảnh báo nợ đọng"
        health_score = 65
    if overdue_count >= 10:
        health_status = "Nguy cơ cao"
        health_score = 45

    action_items = [
        f"Thu hồi gấp {overdue_count} mốc nợ đã quá hạn, đặc biệt các hợp đồng với dư nợ lớn.",
        f"Đôn đốc chứng từ cho {urgent_count} mốc sắp đến hạn trong vòng 7 ngày tới.",
        "Rà soát việc xuất hóa đơn VAT và ký Biên bản bàn giao/nghiệm thu (FAC) để khách hàng có đủ hồ sơ thanh toán."
    ]

    return {
        "health_score": health_score,
        "health_status": health_status,
        "summary_headline": f"Tỷ lệ thu hồi hiện tại đạt {completion_rate:.1f}%. Còn {len(overdue_items)} mốc nợ quá hạn và {len(urgent_items)} mốc cần thu trong 7 ngày tới.",
        "aging_analysis": {
            "overdue_critical": f"{overdue_count} khoản nợ quá hạn với tổng nợ cần thu hồi gấp.",
            "overdue_moderate": "Cần theo sát các mốc nợ đã trễ hạn từ 15-30 ngày.",
            "upcoming_soon": f"{urgent_count} khoản nợ sắp đến hạn, cần chuẩn bị hồ sơ chứng từ thanh toán."
        },
        "top_risks": top_risks,
        "action_items": action_items,
        "bilingual_executive_note": f"目前專案應收款回收率為 {completion_rate:.1f}%，尚有 {overdue_count} 筆款項逾期未收，建議儘速發函催收並備妥驗收發票憑證。\nTỷ lệ thu hồi công nợ đạt {completion_rate:.1f}%, còn {overdue_count} mốc quá hạn, đề nghị PM khẩn trương gửi Thư nhắc nợ và hoàn tất chứng từ nghiệm thu/hóa đơn."
    }


def get_ai_receivables_digest(preferred_model: Optional[str] = None) -> Dict[str, Any]:
    """Analyze all receivables via Gemini AI or fallback to rule-based engine."""
    stats = get_receivables_stats()
    items = list_receivables()

    # If no data exists
    if not items:
        return {
            "health_score": 100,
            "health_status": "Chưa có dữ liệu",
            "summary_headline": "Chưa có mốc công nợ nào trong hệ thống.",
            "aging_analysis": {},
            "top_risks": [],
            "action_items": ["Nhập dữ liệu công nợ hoặc đồng bộ từ Hợp đồng."],
            "bilingual_executive_note": "尚無應收帳款資料 / Chưa có dữ liệu công nợ."
        }

    # Prepare compact context for Gemini
    compact_items = []
    for it in items[:40]:  # Top 40 items to avoid token limits
        compact_items.append({
            "stt": it.get("order_no"),
            "customer": it.get("customer_name"),
            "project": it.get("project_name"),
            "contract": it.get("contract_code"),
            "gross": it.get("gross_amount"),
            "debt": it.get("remaining_debt"),
            "status": it.get("collection_status"),
            "days_left": it.get("days_left"),
            "due_date": it.get("due_date"),
            "notes": it.get("notes")
        })

    user_prompt = f"""Dưới đây là số liệu công nợ tổng thể và danh sách các mốc công nợ của Hong Ming:
THỐNG KÊ TỔNG THỂ:
- Tổng số tiền phải thu: {stats.get('total_receivable_formatted')} ({stats.get('total_receivable')} VND)
- Đã thu: {stats.get('total_received_formatted')} ({stats.get('total_received')} VND)
- Còn nợ: {stats.get('total_debt_formatted')} ({stats.get('total_debt')} VND)
- Tỷ lệ thu hồi: {stats.get('completion_rate')}%
- Số mốc đã thu: {stats.get('paid_count')}
- Số mốc chờ thu trong hạn: {stats.get('pending_count')}
- Số mốc sắp đến hạn (<= 7 ngày): {stats.get('urgent_count')}
- Số mốc quá hạn: {stats.get('overdue_count')}

DANH SÁCH CHI TIẾT CÁC MỐC CÔNG NỢ (Tối đa 40 mốc):
{json.dumps(compact_items, ensure_ascii=False, indent=2)}

Hãy phân tích và trả về đúng định dạng JSON như đã hướng dẫn."""

    keys = DEFAULT_GEMINI_KEYS if DEFAULT_GEMINI_KEYS else [DEFAULT_GEMINI_KEY]
    models = [preferred_model] if preferred_model else CANDIDATE_MODELS
    models = [m for m in models if m]

    for key in keys:
        if not key or key == "your_gemini_api_key_here":
            continue
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"{RECEIVABLES_ANALYST_SYSTEM_PROMPT}\n\n{user_prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 2048,
                    "responseMimeType": "application/json"
                }
            }

            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    candidates = resp_data.get("candidates", [])
                    if candidates:
                        raw_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        cleaned = _clean_json_response(raw_content)
                        parsed = json.loads(cleaned)
                        logger.info(f"Successfully generated AI Receivables Digest with model {model}")
                        return parsed
            except Exception as e:
                logger.warning(f"Gemini API call failed with model {model}: {e}")
                continue

    # Fallback to rule-based engine
    logger.info("Falling back to rule-based AI Receivables digest.")
    return _generate_rule_based_digest(stats, items)


RECEIVABLES_INTAKE_SYSTEM_PROMPT = """Bạn là chuyên gia Quản lý Tài chính Dự án & Thu hồi Công nợ (Credit Control & AR Specialist) cho CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司).
Hong Ming là doanh nghiệp cung cấp giải pháp IoT nhà máy (SMB IoT), tiết kiệm năng lượng (EMS), hệ thống RFID và máy chủ CNTT.

NHIỆM VỤ:
Phân tích văn bản hoặc tập tin đính kèm (Biên bản nghiệm thu, Hóa đơn VAT, Email/Zalo nhắc nợ, Đơn đặt hàng PO của khách, Bảng kê thanh toán đợt) và trích xuất thành danh sách các đợt/mốc công nợ phải thu (Receivables Milestones).

LƯU Ý CỰC KỲ QUAN TRỌNG VỀ HỢP ĐỒNG:
- Nhiều khoản công nợ phát sinh thực tế KHÔNG LIÊN QUAN ĐẾN HỢP ĐỒNG NÀO (ví dụ: mua lẻ thiết bị phụ tùng, chi phí sửa chữa thay thế linh kiện, dịch vụ bảo trì đột xuất, tạm ứng dịch vụ).
- Nếu văn bản/tập tin KHÔNG đề cập đến số hợp đồng, hãy để contract_code = null. TUYỆT ĐỐI KHÔNG TỰ BỊA RA SỐ HỢP ĐỒNG.
- Ô contract_code hoàn toàn có thể trống.

QUY TẮC BÓC TÁCH CÁC TRƯỜNG:
1. project_name: Tên dự án và tên đợt thanh toán (Ví dụ: 'Đợt 1 (30%) - Mạng IIoT Seiyo', 'Sửa chữa máy dập CX Tech', 'Cung cấp linh kiện lẻ máy in RFID Vonmax'...).
2. customer_name: Tên đầy đủ của công ty khách hàng.
3. contract_code: Số hợp đồng nếu có (Ví dụ: HD-20261013-001, HMV...). Nếu không có thì để null.
4. total_contract_amount: Tổng giá trị hợp đồng nếu có, nếu không có thì để bằng 0 hoặc bằng net_amount.
5. net_amount: Số tiền đợt thanh toán chưa VAT (VNĐ).
6. vat_rate: Tỷ lệ thuế VAT (ví dụ: 0.0 nếu không VAT, 0.08 nếu 8%, 0.10 nếu 10%). Mặc định 0.0 nếu không nêu rõ.
7. vat_amount: Tiền thuế VAT (VNĐ). Nếu vat_rate > 0 và không có số tiền thuế cụ thể thì tính net_amount * vat_rate.
8. gross_amount: Tổng tiền thanh toán gồm VAT (net_amount + vat_amount).
9. received_amount: Số tiền khách đã thanh toán trước (nếu có, không có thì 0).
10. customer_promised_date: Ngày khách hàng cam kết / hẹn thanh toán (YYYY-MM-DD, nếu không có để null).
11. due_date: Hạn thanh toán theo thỏa thuận hoặc hợp đồng (YYYY-MM-DD, nếu không có để null).
12. paid_date: Ngày khách đã chuyển tiền thực tế nếu có (YYYY-MM-DD, nếu chưa trả để null).
13. doc_status: Trạng thái hóa đơn / chứng từ (Ví dụ: 'HD-202610-01', 'Đã xuất HĐ', 'Chờ nghiệm thu', 'Chưa xuất'...).
14. collection_status: 'PAID' (đã thu), 'PENDING' (chờ thu), 'URGENT' (sắp đến hạn <= 7 ngày), 'DELAYED' (quá hạn).
15. notes: Ghi chú điều khoản thanh toán, tiến độ trao đổi hoặc lý do phát sinh.

ĐỊNH DẠNG JSON TRẢ VỀ BẮT BUỘC:
{
  "summary": "Tóm tắt ngắn gọn danh sách công nợ trích xuất được",
  "items": [
    {
      "project_name": "Đợt 1 (30%) - Mạng IIoT Seiyo",
      "customer_name": "CÔNG TY TNHH SEIYO VIỆT NAM",
      "contract_code": null,
      "total_contract_amount": 0,
      "net_amount": 213606000,
      "vat_rate": 0.0,
      "vat_amount": 0,
      "gross_amount": 213606000,
      "received_amount": 0,
      "customer_promised_date": "2026-11-05",
      "due_date": "2026-10-27",
      "paid_date": null,
      "doc_status": "Chưa xuất",
      "collection_status": "PENDING",
      "notes": "Khách hẹn chuyển khoản vào đầu tháng sau"
    }
  ]
}
"""


def parse_receivables_ai(
    raw_text: Optional[str] = None,
    preferred_model: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract receivable milestones from text and/or uploaded file via Gemini AI."""
    from app.utils.ai_file_helper import process_uploaded_file_for_ai

    extracted_file_text, inline_part = None, None
    if file_bytes and filename:
        extracted_file_text, inline_part = process_uploaded_file_for_ai(file_bytes, filename, content_type)

    has_text = bool(raw_text and raw_text.strip())
    has_file = bool(extracted_file_text or inline_part)

    if not has_text and not has_file:
        return {
            "status": "error",
            "message": "Vui lòng nhập văn bản hoặc đính kèm tập tin hóa đơn / biên bản nghiệm thu.",
            "data": None
        }

    parts = [{"text": RECEIVABLES_INTAKE_SYSTEM_PROMPT}]
    if has_text:
        parts.append({"text": f"DƯỚI ĐÂY LÀ VĂN BẢN / GHI CHÚ:\n\n{raw_text.strip()}"})
    if extracted_file_text:
        parts.append({"text": f"DƯỚI ĐÂY LÀ NỘI DUNG TỪ TẬP TIN ({filename}):\n\n{extracted_file_text}"})
    if inline_part:
        parts.append(inline_part)

    keys = DEFAULT_GEMINI_KEYS if DEFAULT_GEMINI_KEYS else [DEFAULT_GEMINI_KEY]
    models = [preferred_model] if preferred_model else CANDIDATE_MODELS
    models = [m for m in models if m]

    last_error = ""
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    for key in keys:
        if not key or key == "your_gemini_api_key_here":
            continue
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

                items = parsed_data.get("items", [])
                if not items and "project_name" in parsed_data:
                    items = [parsed_data]

                processed_items = []
                for it in items:
                    net = float(it.get("net_amount") or 0.0)
                    vat_r = float(it.get("vat_rate") or 0.0)
                    vat_a = float(it.get("vat_amount") or round(net * vat_r, 2))
                    gross = float(it.get("gross_amount") or round(net + vat_a, 2))
                    rec = float(it.get("received_amount") or 0.0)
                    processed_items.append({
                        "project_name": it.get("project_name") or "Đợt thanh toán",
                        "customer_name": it.get("customer_name") or "Khách hàng",
                        "contract_code": it.get("contract_code") or None,  # Cho phép NULL nếu không có HĐ
                        "total_contract_amount": float(it.get("total_contract_amount") or 0.0),
                        "net_amount": net,
                        "vat_rate": vat_r,
                        "vat_amount": vat_a,
                        "gross_amount": gross,
                        "received_amount": rec,
                        "remaining_debt": max(0.0, gross - rec),
                        "customer_promised_date": it.get("customer_promised_date") or None,
                        "due_date": it.get("due_date") or None,
                        "paid_date": it.get("paid_date") or None,
                        "doc_status": it.get("doc_status") or "Chưa xuất",
                        "collection_status": it.get("collection_status") or "PENDING",
                        "notes": it.get("notes") or "",
                    })

                return {
                    "status": "success",
                    "model_used": model,
                    "summary": parsed_data.get("summary") or "Đã trích xuất danh sách công nợ",
                    "items": processed_items
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Gemini API parse_receivables_ai failed with model {model}: {e}")
                continue

    return {
        "status": "error",
        "message": f"Không thể trích xuất công nợ qua Gemini AI: {last_error}",
        "data": None
    }

