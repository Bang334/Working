"""Controller handling ECO PRIME Quotation API endpoints."""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional
import urllib.parse

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.models.eco_prime_models import (
    EcoPrimeQuotationData,
    SchematicAnalysisRequest,
    SchematicAnalysisResponse,
)
from app.services.eco_prime.eco_prime_ai_service import analyze_schematic_image
from app.services.eco_prime.eco_prime_excel_service import generate_eco_prime_excel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/eco-prime", tags=["ECO PRIME Quotation"])


@router.post("/analyze-schematic", response_model=SchematicAnalysisResponse)
async def analyze_schematic_endpoint(req: SchematicAnalysisRequest):
    """API phân tích ảnh sơ đồ đơn tuyến / bản vẽ kỹ thuật bằng Gemini Vision."""
    try:
        res = analyze_schematic_image(req)
        return res
    except Exception as e:
        logger.exception("Error in analyze_schematic_endpoint: %s", e)
        return SchematicAnalysisResponse(
            success=False,
            error=str(e)
        )


@router.post("/upload-and-analyze", response_model=SchematicAnalysisResponse)
async def upload_and_analyze_endpoint(
    file: UploadFile = File(...),
    customer_name: Optional[str] = Form(None),
    preferred_model: Optional[str] = Form(None),
):
    """API tải lên trực tiếp file ảnh (PNG/JPG/WEBP) hoặc PDF và phân tích."""
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File tải lên rỗng.")

        mime = file.content_type or "image/png"
        b64_str = base64.b64encode(content).decode("utf-8")

        req = SchematicAnalysisRequest(
            image_base64=b64_str,
            file_name=file.filename,
            mime_type=mime,
            customer_name_hint=customer_name,
            preferred_model=preferred_model
        )

        return analyze_schematic_image(req)
    except Exception as e:
        logger.exception("Error in upload_and_analyze_endpoint: %s", e)
        return SchematicAnalysisResponse(
            success=False,
            error=str(e)
        )


@router.post("/export-excel")
async def export_excel_endpoint(data: EcoPrimeQuotationData):
    """API xuất và tải trực tiếp file Excel Báo Giá ECO PRIME chuẩn 1:1."""
    try:
        result = generate_eco_prime_excel(data, save_to_disk=True)
        content_bytes = result.get("content_bytes")
        if not content_bytes and "bytes_io" in result:
            content_bytes = result["bytes_io"].getvalue()
        file_name = result["file_name"]

        # Mã hóa filename theo RFC 5987 để trình duyệt tải đúng tiếng Việt / Trung
        # Fallback filename chỉ chứa ASCII an toàn để tránh UnicodeEncodeError latin-1 trong Starlette/HTTP header
        ascii_fallback = "".join(c for c in file_name if c.isascii() and c not in r'\"\\').strip() or "ECO_PRIME_Bao_Gia.xlsx"
        encoded_filename = urllib.parse.quote(file_name)
        headers = {
            "Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }

        return Response(
            content=content_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        logger.exception("Error in export_excel_endpoint: %s", e)
        raise HTTPException(status_code=500, detail=f"Không thể tạo file Excel: {str(e)}")


@router.get("/sample-data")
async def get_sample_data():
    """Lấy dữ liệu mẫu dự án POU HUI chuẩn để điền thử nghiệm."""
    from app.models.eco_prime_models import EcoPrimeItem
    
    sample_items = [
        EcoPrimeItem(
            stt=1,
            name="Đồng hồ đa năng PM210-4-V\nPM210-4-V 三相單迴路多功能需量總表",
            category="Đồng hồ đa năng\n多功能電表",
            desc="Đồng hồ đo đếm điện năng 3 pha đa chức năng PM210-4-V, đo công suất, điện áp, dòng điện, điện năng tiêu thụ (KWh/KVAh/KVARh), hỗ trợ kết nối trực tiếp biến dòng mềm Rogowski, giao tiếp Modbus RTU/RS485. 1 bộ / trạm biến áp (Trạm 1~Trạm 4).\nPM210-4-V三相單迴路多功能需量總表, 具備電力參數測量、電能計量功能, 直連羅氏線圈比流器, Modbus RTU/RS485通訊。每座變電站配置1台 (1號~4號高壓變電站)。",
            qty=4, unit="BỘ", tax_rate=0.0
        ),
        EcoPrimeItem(
            stt=2,
            name="Biến dòng mềm Rogowski CT-1000RV (1000A)\n三相羅氏比流器 CT-1000RV (1000A)",
            category="Biến dòng Rogowski\n羅氏比流器",
            desc="Biến dòng kiểu vòng mềm Rogowski coil CT-1000RV, dòng định mức 1000A, độ chính xác cao, lắp đặt kẹp mềm không cần cắt điện dừng máy nhà máy. Dùng cho Trạm 1, Trạm 2, Trạm 3 (máy biến áp 630KVA, cáp XLPE 325mm² x 2 sợi/pha).\nCT-1000RV三相羅氏比流器 (1000A), 柔性開口式線圈, 免停電快速施工安裝。適用於1號、2號、3號高壓變電站 (630KVA變壓器, XLPE 325mm²x2線徑)。",
            qty=3, unit="BỘ", tax_rate=0.20
        ),
        EcoPrimeItem(
            stt=3,
            name="Biến dòng mềm Rogowski CT-2000RV (2000A)\n三相羅氏比流器 CT-2000RV (2000A)",
            category="Biến dòng Rogowski\n羅氏比流器",
            desc="Biến dòng kiểu vòng mềm Rogowski coil CT-2000RV, dòng định mức 2000A (dải đo dòng sơ cấp 1200A), đường kính vòng lớn luồn qua bó 3 sợi cáp/pha, không cần cắt điện. Dùng cho Trạm 4 (máy biến áp 750KVA, cáp XLPE 250mm² x 3 sợi/pha).\nCT-2000RV三相羅氏比流器 (2000A), 大口徑柔性開口式線圈, 適用於單相3條電纜束線, 免停電快速安裝。適用於4號高壓變電站 (750KVA變壓器, XLPE 250mm²x3線徑)。",
            qty=1, unit="BỘ", tax_rate=0.20
        ),
        EcoPrimeItem(
            stt=4,
            name="Gateway thu thập dữ liệu CC2051 (kèm bộ nguồn 24VDC)\nCC2051 工業級資料收集閘道器 (含24VDC電源供應器)",
            category="Gateway & Nguồn\n數據閘道器及電源",
            desc="Bộ điều khiển/thu thập dữ liệu biên công nghiệp CC2051 (Edge Gateway) kèm bộ nguồn công nghiệp Din-rail 24VDC chuyên dụng, cổng RS-485 Modbus RTU thu thập tín hiệu từ 4 đồng hồ đo điện PM210-4-V của 4 trạm biến áp, chuyển đổi sang Modbus TCP / MQTT qua cổng mạng RJ45 Ethernet kết nối LAN Switch về EMS trung tâm.\nCC2051工業級邊緣計算與資料收集閘道器 (含專用導軌式24VDC開關電源供應器), 具備RS-485 Modbus RTU接口採集4座變電站PM210電表數據, 經由RJ45以太網轉換為Modbus TCP/MQTT協議, 經由LAN Switch即時上傳至中央能源管理系統 (EMS)。",
            qty=1, unit="BỘ", tax_rate=0.08
        ),
        EcoPrimeItem(
            stt=5,
            name="Bộ chia mạng công nghiệp 5-Port\n工業級5埠乙太網交換機 (LAN SWITCH)",
            category="Thiết bị mạng\n網絡設備",
            desc="Switch mạng công nghiệp 5 cổng RJ45 10/100Mbps gắn thanh ray, vỏ kim loại chuẩn công nghiệp chống nhiễu điện từ, kết nối truyền dữ liệu từ Gateway CC2051 về mạng nội bộ LAN nhà máy.\n工業級5埠 10/100Mbps 導軌式交換機, 金屬抗干擾外殼, 適用於工廠高壓變電站環境, 將 CC2051 網關連接至廠區局域網 (LAN)。",
            qty=1, unit="BỘ", tax_rate=0.08
        ),
        EcoPrimeItem(
            stt=6,
            name="Cáp mạng Cat6, cáp RS485 & Vật tư phụ\n網絡線 Cat.6、RS485通訊線及安裝輔材",
            category="Vật tư phụ\n輔助材料",
            desc="Bao gồm nội dung 內容包含:\n- Cáp mạng Cat6: 網絡線 Category 6 UTP Cable, 4-Pair\n- Cáp truyền thông chống nhiễu chuyên dụng RS485 (UL2464 24AWG 2P 隔離通訊線)\n- Ống luồn bảo vệ chống cháy, dây tiếp địa, cầu chì bảo vệ 阻燃保護套管、接地線、保險絲\n- Đầu cosse bọc cách điện, nhãn đánh dấu dây cáp và toàn bộ phụ kiện đấu nối 冷壓端子、電纜號碼管及全套配線輔材。",
            qty=1, unit="SET", tax_rate=0.08
        ),
        EcoPrimeItem(
            stt=7,
            name="Chi phí thi công\n施工費",
            category="Chi phí thi công\n施工費",
            desc="Bao gồm nội dung 內容包含:\n- Cài đặt hệ thống 系統設定\n- Lắp đặt phần cứng 4 trạm biến áp 4座高壓變電站硬體安裝\n- Hiệu chỉnh chức năng & liên động Modbus CC2051 功能調適與通訊聯調\n- Phí quản lý, vận chuyển 管理、運費\n- Thiết kế bản vẽ hoàn công 設計、竣工圖費用\n- Chi phí đi lại, giàn giáo, dụng cụ an toàn 交通費、鷹架、工安器具...",
            qty=1, unit="SET", tax_rate=0.08
        )
    ]

    return {
        "success": True,
        "data": EcoPrimeQuotationData(
            customer_name="CÔNG TY TNHH VIỆT NAM PHỔ HUỆ Y TẾ CÔNG NGHỆ (POU HUI)",
            customer_dept="Ban Quản lý Dự án & Cơ điện 機電與專案部",
            customer_contact="",
            customer_phone="",
            customer_address="Lô D7/I, Đường số 1B, KCN Vĩnh Lộc, Phường Bình Hưng Hòa B, Q. Bình Tân, TP. Hồ Chí Minh",
            customer_email="",
            quote_title="Báo giá hệ thống đo đếm điện năng 4 trạm biến áp 高壓變電站電能計量系統硬體報價訂購確認單",
            quote_date="21/10/2026",
            project_solution="1) Giải pháp nâng cấp hệ thống đo đếm điện năng và giám sát 4 trạm biến áp cao thế 普惠醫工4座高壓變電站電能計量與能耗監控系統方案",
            exchange_rate=26130.0,
            items=sample_items
        )
    }
