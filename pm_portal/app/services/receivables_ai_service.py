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
