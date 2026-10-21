"""AI Vision Service to analyze electrical single-line schematic drawings into ECO PRIME Quotations."""

from __future__ import annotations

import base64
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.config import (
    CANDIDATE_MODELS,
    DEFAULT_GEMINI_KEY,
    DEFAULT_GEMINI_KEYS,
    DEFAULT_MODEL,
)
from app.models.eco_prime_models import (
    EcoPrimeItem,
    EcoPrimeQuotationData,
    SchematicAnalysisRequest,
    SchematicAnalysisResponse,
)

logger = logging.getLogger(__name__)

ECO_PRIME_VISION_SYSTEM_PROMPT = """Bạn là Chuyên gia Kỹ thuật Hệ thống Đo đếm Điện năng & IoT Năng lượng (EMS) của CÔNG TY TNHH TOÀN CẦU HONG MING & ECO PRIME.

NHIỆM VỤ CỦA BẠN:
Phân tích bản vẽ sơ đồ nguyên lý điện (Single-line diagram / 電氣單線圖 / 系統規劃圖), sơ đồ trạm biến áp hoặc ảnh chụp thiết bị, bóc tách chính xác 100% cấu trúc hệ thống và chuyển đổi thành Danh mục thiết bị Báo giá ECO PRIME chuẩn mực.

NGUYÊN TẮC BẮT BUỘC SỐ 1: BÁM SÁT 100% BẢN VẼ SƠ ĐỒ NGUYÊN LÝ (ZERO DEVIATION FROM SCHEMATIC DRAWING)
- TUYỆT ĐỐI KHÔNG tự suy diễn hoặc tùy tiện tăng/giảm số lượng thiết bị so với những gì thể hiện trên sơ đồ.
- ĐẶC BIỆT VỚI GATEWAY CC2051: Hãy nhìn kỹ đường dây truyền thông (RS-485 / Cáp màu nâu) và đếm chính xác số lượng hộp chữ nhật ghi "Gateway" trên bản vẽ. Nếu 4 đồng hồ nối tiếp (daisy-chain) về 1 Gateway thì số lượng Gateway CC2051 BẮT BUỘC PHẢI LÀ 1, TUYỆT ĐỐI KHÔNG TỰ Ý ĐỔI THÀNH 2!

QUY TẮC BÓC TÁCH KỸ THUẬT:
1. Thông tin khách hàng & Dự án:
   - Nếu trên bản vẽ có chữ tiếng Trung (ví dụ: 普惠醫工 越南廠), hãy trích xuất và gợi ý tên pháp nhân tiếng Việt tương ứng (ví dụ: CÔNG TY TNHH VIỆT NAM PHỔ HUỆ Y TẾ CÔNG NGHỆ (POU HUI)).
   - Nếu bản vẽ KHÔNG có tên khách hàng, để trống "" (không tự bịa đặt).
   - Địa chỉ, số điện thoại: Nếu không có trên bản vẽ thì để trống "".

2. Phân tích từng Trạm Biến Áp (Substation / 變電站):
   - Đếm số lượng trạm (ví dụ: 1號, 2號, 3號, 4號... = 4 trạm).
   - Đọc công suất từng máy biến áp (ví dụ: 630KVA, 750KVA, 1000KVA...).
   - Đọc tỷ số biến dòng sơ cấp (ví dụ: CT1000/5A, CT1200/5A...).
   - Đọc tiết diện dây cáp hạ thế (ví dụ: XLPE 325mm² x 2 sợi/pha, XLPE 250mm² x 3 sợi/pha...).

3. Ghép danh mục thiết bị theo chuẩn ECO PRIME (BOM Catalog):
   - Hạng mục 1: Đồng hồ đa năng PM210-4-V (PM210-4-V 三相單迴路多功能需量總表)
     + Số lượng = Số trạm biến áp (hoặc số lộ đo trên bản vẽ).
   - Hạng mục 2: Biến dòng mềm Rogowski CT-1000RV (1000A) (三相羅氏比流器 CT-1000RV (1000A))
     + Dùng cho các trạm có dòng sơ cấp <= 1000A (ví dụ trạm 630KVA, cáp 2 sợi/pha).
     + Số lượng = Số trạm thỏa mãn điều kiện này. Thuế suất: 0.20 (hoặc theo catalog).
   - Hạng mục 3: Biến dòng mềm Rogowski CT-2000RV (2000A) (三相羅氏比流器 CT-2000RV (2000A))
     + Dùng cho các trạm có dòng sơ cấp > 1000A (ví dụ trạm 750KVA/CT1200A, cáp 3 sợi/pha).
     + Số lượng = Số trạm thỏa mãn điều kiện này. Thuế suất: 0.20.
   - Hạng mục 4: Gateway thu thập dữ liệu CC2051 (kèm bộ nguồn 24VDC) (CC2051 工業級資料收集閘道器 (含24VDC電源供應器))
     + QUY TẮC BẮT BUỘC: Bộ nguồn công nghiệp (電源供應器 PW) chỉ cần 1 cái và ĐƯỢC GỘP CHUNG VÀO CÙNG MỤC VỚI CC2051 vì bán kèm trọn gói với nhau (電源供應器1個就可以，且跟CC2051合併，一起賣).
     + Số lượng = Số Gateway trên bản vẽ (thường là 1 BỘ). Thuế suất: 0.08.
   - Hạng mục 5: Bộ chia mạng công nghiệp 5-Port (LAN SWITCH) (工業級5埠乙太網交換機)
     + Số lượng = Đếm theo ký hiệu LAN Switch trên bản vẽ (thường 1 BỘ). Thuế suất: 0.08.
   - Hạng mục 6: Cáp mạng Cat6, cáp RS485 & Vật tư phụ (網絡線 Cat.6、RS485通訊線及安裝輔材)
     + Số lượng = 1 SET. Thuế suất: 0.08.
     + Mô tả bao gồm: Cáp mạng Cat6 UTP 4-Pair, Cáp chống nhiễu RS485 UL2464 24AWG 2P, ống bảo vệ chống cháy, đầu cosse, nhãn đánh số cáp.
   - Hạng mục 7: Chi phí thi công (施工費)
     + Số lượng = 1 SET. Thuế suất: 0.08.
     + Mô tả bao gồm: Cài đặt hệ thống, Lắp đặt phần cứng N trạm, Hiệu chỉnh Modbus CC2051, Quản lý vận chuyển, Thiết kế bản vẽ hoàn công, Chi phí đi lại giàn giáo an toàn.

4. Cột Đơn giá (USD):
   - Để trống (null) cho toàn bộ các mục để Sếp tự điền giá.

ĐỊNH DẠNG JSON ĐẦU RA BẮT BUỘC:
{
  "customer_name": "CÔNG TY TNHH VIỆT NAM PHỔ HUỆ Y TẾ CÔNG NGHỆ (POU HUI)",
  "customer_dept": "Ban Quản lý Dự án & Cơ điện 機電與專案部",
  "customer_contact": "",
  "customer_phone": "",
  "customer_address": "Lô D7/I, Đường số 1B, KCN Vĩnh Lộc, Q. Bình Tân, TP. Hồ Chí Minh",
  "customer_email": "",
  "quote_title": "Báo giá hệ thống đo đếm điện năng 4 trạm biến áp 高壓變電站電能計量系統硬體報價訂購確認單",
  "quote_date": "21/10/2026",
  "project_solution": "1) Giải pháp nâng cấp hệ thống đo đếm điện năng và giám sát 4 trạm biến áp cao thế 普惠醫工4座高壓變電站電能計量與能耗監控系統方案",
  "exchange_rate": 26130.0,
  "detected_substations": [
    {"name": "1號 高壓變電站", "capacity": "630KVA", "ct": "CT1000/5A", "cable": "XLPE 325mm² x 2", "recommended_ct": "CT-1000RV"},
    {"name": "2號 高壓變電站", "capacity": "630KVA", "ct": "CT1000/5A", "cable": "XLPE 325mm² x 2", "recommended_ct": "CT-1000RV"},
    {"name": "3號 高壓變電站", "capacity": "630KVA", "ct": "CT1000/5A", "cable": "XLPE 325mm² x 2", "recommended_ct": "CT-1000RV"},
    {"name": "4號 高壓變電站", "capacity": "750KVA", "ct": "CT1200/5A", "cable": "XLPE 250mm² x 3", "recommended_ct": "CT-2000RV"}
  ],
  "items": [
    {
      "stt": 1,
      "name": "Đồng hồ đa năng PM210-4-V\\nPM210-4-V 三相單迴路多功能需量總表",
      "category": "Đồng hồ đa năng\\n多功能電表",
      "desc": "Đồng hồ đo đếm điện năng 3 pha đa chức năng PM210-4-V...\\nPM210-4-V三相單迴路多功能需量總表...",
      "qty": 4,
      "unit": "BỘ",
      "unit_price_usd": null,
      "tax_rate": 0.0
    },
    {
      "stt": 2,
      "name": "Biến dòng mềm Rogowski CT-1000RV (1000A)\\n三相羅氏比流器 CT-1000RV (1000A)",
      "category": "Biến dòng Rogowski\\n羅氏比流器",
      "desc": "Biến dòng kiểu vòng mềm Rogowski coil CT-1000RV, dòng định mức 1000A... Dùng cho Trạm 1, Trạm 2, Trạm 3...\\nCT-1000RV三相羅氏比流器 (1000A)...",
      "qty": 3,
      "unit": "BỘ",
      "unit_price_usd": null,
      "tax_rate": 0.20
    },
    {
      "stt": 3,
      "name": "Biến dòng mềm Rogowski CT-2000RV (2000A)\\n三相羅氏比流器 CT-2000RV (2000A)",
      "category": "Biến dòng Rogowski\\n羅氏比流器",
      "desc": "Biến dòng kiểu vòng mềm Rogowski coil CT-2000RV, dòng định mức 2000A... Dùng cho Trạm 4...\\nCT-2000RV三相羅氏比流器 (2000A)...",
      "qty": 1,
      "unit": "BỘ",
      "unit_price_usd": null,
      "tax_rate": 0.20
    },
    {
      "stt": 4,
      "name": "Gateway thu thập dữ liệu CC2051 (kèm bộ nguồn 24VDC)\\nCC2051 工業級資料收集閘道器 (含24VDC電源供應器)",
      "category": "Gateway & Nguồn\\n數據閘道器及電源",
      "desc": "Bộ điều khiển/thu thập dữ liệu biên công nghiệp CC2051 (Edge Gateway) kèm bộ nguồn công nghiệp Din-rail 24VDC chuyên dụng...\\nCC2051工業級邊緣計算與資料收集閘道器 (含專用導軌式24VDC開關電源供應器)...",
      "qty": 1,
      "unit": "BỘ",
      "unit_price_usd": null,
      "tax_rate": 0.08
    },
    {
      "stt": 5,
      "name": "Bộ chia mạng công nghiệp 5-Port\\n工業級5埠乙太網交換機 (LAN SWITCH)",
      "category": "Thiết bị mạng\\n網絡設備",
      "desc": "Switch mạng công nghiệp 5 cổng RJ45 10/100Mbps...\\n工業級5埠 10/100Mbps 導軌式交換機...",
      "qty": 1,
      "unit": "BỘ",
      "unit_price_usd": null,
      "tax_rate": 0.08
    },
    {
      "stt": 6,
      "name": "Cáp mạng Cat6, cáp RS485 & Vật tư phụ\\n網絡線 Cat.6、RS485通訊線及安裝輔材",
      "category": "Vật tư phụ\\n輔助材料",
      "desc": "Bao gồm nội dung 內容包含:\\n- Cáp mạng Cat6: 網絡線 Category 6 UTP Cable, 4-Pair\\n- Cáp truyền thông chống nhiễu chuyên dụng RS485 (UL2464 24AWG 2P)\\n- Ống luồn bảo vệ chống cháy, dây tiếp địa, cầu chì bảo vệ\\n- Đầu cosse bọc cách điện, nhãn đánh dấu dây cáp và phụ kiện đấu nối.",
      "qty": 1,
      "unit": "SET",
      "unit_price_usd": null,
      "tax_rate": 0.08
    },
    {
      "stt": 7,
      "name": "Chi phí thi công\\n施工費",
      "category": "Chi phí thi công\\n施工費",
      "desc": "Bao gồm nội dung 內容包含:\\n- Cài đặt hệ thống 系統設定\\n- Lắp đặt phần cứng các trạm biến áp\\n- Hiệu chỉnh chức năng & liên động Modbus CC2051\\n- Phí quản lý, vận chuyển 管理、運費\\n- Thiết kế bản vẽ hoàn công 設計、竣工圖費用\\n- Chi phí đi lại, giàn giáo, dụng cụ an toàn 交通費、鷹架、工安器具...",
      "qty": 1,
      "unit": "SET",
      "unit_price_usd": null,
      "tax_rate": 0.08
    }
  ],
  "ai_summary": "Phát hiện 4 trạm biến áp (Trạm 1, 2, 3: 630KVA dùng CT-1000RV; Trạm 4: 750KVA dùng CT-2000RV). Cả 4 trạm liên kết qua 1 đường RS485 duy nhất vào 1 Gateway CC2051 (kèm bộ nguồn 24VDC) kết nối LAN Switch. Đã bóc tách đủ 7 hạng mục thiết bị, vật tư phụ và chi phí thi công chuẩn mực."
}
}
CHỈ TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON HỢP LỆ, TUYỆT ĐỐI KHÔNG BỌC TRONG CODE BLOCK HOẶC KÈM VĂN BẢN NGOÀI JSON.
"""


def _clean_json_text(text: str) -> str:
    """Loại bỏ markdown code blocks hoặc ký tự thừa ngoài JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _call_gemini_vision(
    system_prompt: str,
    parts: List[Dict[str, Any]],
    preferred_model: Optional[str] = None
) -> Dict[str, Any]:
    """Gọi Gemini API hỗ trợ đa mô hình và xoay vòng API Keys."""
    models_to_try = []
    if preferred_model and preferred_model in CANDIDATE_MODELS:
        models_to_try.append(preferred_model)
    for m in CANDIDATE_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    keys_to_try = [DEFAULT_GEMINI_KEY] + [k for k in DEFAULT_GEMINI_KEYS if k != DEFAULT_GEMINI_KEY]

    last_error = None
    for key in keys_to_try:
        if not key:
            continue
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
                payload = {
                    "contents": [{"parts": parts}],
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    cand = resp_data.get("candidates", [])[0]
                    content_parts = cand.get("content", {}).get("parts", [])
                    raw_text = "".join(p.get("text", "") for p in content_parts)
                    clean_text = _clean_json_text(raw_text)
                    parsed = json.loads(clean_text)
                    parsed["_model_used"] = model_name
                    return parsed
            except urllib.error.HTTPError as exc:
                if exc.code == 403:
                    logger.warning("Key %s... returned 403. Rotating to next key.", key[:8])
                    break
                elif exc.code in (404, 429, 503):
                    logger.warning("Model %s returned HTTP %d on key %s...", model_name, exc.code, key[:8])
                    last_error = exc
                    continue
                else:
                    last_error = exc
            except Exception as e:
                logger.error("Error calling Gemini Vision with %s: %s", model_name, e)
                last_error = e
                continue

    raise RuntimeError(f"Không thể phân tích bản vẽ bằng Gemini AI: {last_error}")


def analyze_schematic_image(req: SchematicAnalysisRequest) -> SchematicAnalysisResponse:
    """Phân tích ảnh sơ đồ điện / PDF sang Báo giá ECO PRIME."""
    if not req.image_base64:
        return SchematicAnalysisResponse(
            success=False,
            error="Vui lòng tải lên ảnh sơ đồ nguyên lý hoặc bản vẽ kỹ thuật."
        )

    clean_b64 = req.image_base64
    if "," in clean_b64:
        clean_b64 = clean_b64.split(",", 1)[1]

    parts: List[Dict[str, Any]] = [
        {
            "inlineData": {
                "mimeType": req.mime_type or "image/png",
                "data": clean_b64
            }
        }
    ]

    instruction = (
        "Hãy phân tích kỹ sơ đồ nguyên lý điện và hệ thống thu thập dữ liệu trong hình ảnh đính kèm. "
        "Bám sát 100% sơ đồ nguyên lý (Zero Deviation from Schematic Drawing). "
        "Trích xuất số lượng trạm biến áp, công suất, cáp điện, đồng hồ PM210, Rogowski coil, Gateway CC2051, bộ nguồn, LAN switch, vật tư phụ và chi phí thi công."
    )
    if req.customer_name_hint:
        instruction += f"\nGợi ý tên khách hàng từ người dùng: {req.customer_name_hint}"

    parts.append({"text": instruction})

    try:
        raw_result = _call_gemini_vision(
            system_prompt=ECO_PRIME_VISION_SYSTEM_PROMPT,
            parts=parts,
            preferred_model=req.preferred_model
        )

        # Chuyển đổi sang Pydantic Model
        items: List[EcoPrimeItem] = []
        for it in raw_result.get("items", []):
            items.append(
                EcoPrimeItem(
                    stt=it.get("stt", len(items) + 1),
                    name=it.get("name", ""),
                    category=it.get("category", ""),
                    desc=it.get("desc", ""),
                    qty=float(it.get("qty", 1)),
                    unit=it.get("unit", "BỘ"),
                    unit_price_usd=it.get("unit_price_usd"),
                    tax_rate=float(it.get("tax_rate", 0.08)),
                )
            )

        quote_data = EcoPrimeQuotationData(
            customer_name=req.customer_name_hint or raw_result.get("customer_name", ""),
            customer_dept=raw_result.get("customer_dept", "Ban Quản lý Dự án & Cơ điện 機電與專案部"),
            customer_contact=raw_result.get("customer_contact", ""),
            customer_phone=raw_result.get("customer_phone", ""),
            customer_address=raw_result.get("customer_address", ""),
            customer_email=raw_result.get("customer_email", ""),
            quote_title=raw_result.get("quote_title", "Báo giá hệ thống đo đếm điện năng cao áp 高壓變電站電能計量系統硬體報價訂購確認單"),
            quote_date=raw_result.get("quote_date", ""),
            project_solution=raw_result.get("project_solution", "1) Giải pháp nâng cấp hệ thống đo đếm điện năng và giám sát các trạm biến áp cao thế"),
            exchange_rate=float(raw_result.get("exchange_rate", 26130.0)),
            items=items,
            notes_payment=raw_result.get("notes_payment", "3. 付款方式 : 訂金 35%、 交貨 55%、驗收 10% TT3"),
        )

        return SchematicAnalysisResponse(
            success=True,
            data=quote_data,
            detected_substations=raw_result.get("detected_substations", []),
            ai_summary=raw_result.get("ai_summary", ""),
        )
    except Exception as e:
        logger.exception("Error in analyze_schematic_image: %s", e)
        return SchematicAnalysisResponse(
            success=False,
            error=str(e)
        )
