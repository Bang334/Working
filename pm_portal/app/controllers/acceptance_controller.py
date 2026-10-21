"""Acceptance controller handling document generation, preview, AI parsing, and download."""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from fastapi import UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.models.acceptance_models import AcceptanceAIParseRequest, InstallationAIParseRequest
from app.services.acceptance_ai_service import (
    parse_acceptance_text,
    parse_installation_acceptance_text,
)
from app.services.acceptance_excel_service import (
    generate_acceptance_excel,
    prepare_acceptance_data,
)
from app.services.acceptance_preview_service import generate_acceptance_preview_html
from app.services.acceptance_repair_upload_service import (
    MAX_REPAIR_UPLOAD_BYTES,
    process_uploaded_repair_file,
)
from app.services.acceptance_word_service import generate_acceptance_word
from app.services.installation_acceptance_preview_service import (
    generate_installation_acceptance_preview_html,
)
from app.services.installation_acceptance_word_service import (
    generate_installation_acceptance_word,
    prepare_installation_acceptance_data,
)

logger = logging.getLogger(__name__)


async def process_repair_workbook_upload_controller(
    file: UploadFile,
    contract_code: Any = None
) -> Dict[str, Any]:
    """Validate and process one uploaded repair workbook without blocking the event loop."""
    try:
        content = await file.read(MAX_REPAIR_UPLOAD_BYTES + 1)
        result = await run_in_threadpool(
            process_uploaded_repair_file,
            file.filename or "bien_ban_sua_chua.xlsx",
            content,
            contract_code=str(contract_code).strip() if contract_code else None,
        )
        msg = (
            "Đã phân tích file sửa chữa và tạo biên bản nghiệm thu thành công. "
            f"Đã nhập đủ {result.get('record_count', 0)} bản ghi và gán đúng "
            f"{result['assigned_count']} ghi chú theo sản phẩm."
        )
        if result.get("is_linked_contract") and result.get("contract_code"):
            msg += f" (Đã liên kết với HĐ {result['contract_code']})"
        else:
            msg += " (Biên bản nghiệm thu độc lập)"

        return {
            "status": "success",
            "message": msg,
            **result,
        }
    except Exception as exc:
        logger.exception("Repair workbook upload failed: %s", exc)
        return {
            "status": "error",
            "message": f"Không thể xử lý file biên bản sửa chữa: {str(exc)}",
        }
    finally:
        await file.close()


def generate_acceptance_excel_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to create Acceptance Excel (.xlsx) file matching CX Technology sample 1:1."""
    try:
        result = generate_acceptance_excel(data)
        preview_html = generate_acceptance_preview_html(result["acceptance_data"])
        return {
            "status": "success",
            "message": "Đã tạo Biên bản nghiệm thu Excel (.xlsx) chuẩn 1:1 thành công!",
            "file_name": result["file_name"],
            "download_url": result["download_url"],
            "total_amount": result["total_amount"],
            "preview_html": preview_html,
            "acceptance_data": result["acceptance_data"]
        }
    except Exception as exc:
        logger.exception("Error generating acceptance excel: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo tệp Excel nghiệm thu: {str(exc)}",
            "file_name": "",
            "download_url": ""
        }


def generate_acceptance_word_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to create Acceptance Word (.docx) document."""
    try:
        result = generate_acceptance_word(data)
        return {
            "status": "success",
            "message": "Đã tạo Biên bản nghiệm thu Word (.docx) chuẩn hành chính thành công!",
            "file_name": result["file_name"],
            "download_url": result["download_url"],
            "total_amount": result["total_amount"],
            "acceptance_data": result["acceptance_data"]
        }
    except Exception as exc:
        logger.exception("Error generating acceptance docx: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo tài liệu Word nghiệm thu: {str(exc)}",
            "file_name": "",
            "download_url": ""
        }


def render_acceptance_preview_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to recalculate and refresh live acceptance preview HTML without writing files."""
    try:
        sanitized = prepare_acceptance_data(data)
        preview_html = generate_acceptance_preview_html(sanitized)
        return {
            "status": "success",
            "preview_html": preview_html,
            "data": sanitized
        }
    except Exception as exc:
        logger.exception("Error rendering acceptance preview: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
            "preview_html": f"<div class='alert alert-danger'>Lỗi cập nhật xem trước: {str(exc)}</div>"
        }


def parse_raw_acceptance_text_controller(request: AcceptanceAIParseRequest) -> Dict[str, Any]:
    """Analyze delivery sheet or repair notes with Gemini AI to extract acceptance items."""
    try:
        raw_text = request.raw_text.strip()
        if not raw_text:
            raise ValueError("Văn bản đầu vào không được để trống.")

        parsed_data = parse_acceptance_text(
            raw_input_text=raw_text,
            preferred_model=request.model_name
        )

        executed_model = parsed_data.pop("_executed_model", request.model_name or "Gemini")
        sanitized_data = prepare_acceptance_data(parsed_data)
        preview_html = generate_acceptance_preview_html(sanitized_data)

        return {
            "status": "success",
            "message": f"AI ({executed_model}) đã bóc tách dữ liệu nghiệm thu & tạo bản xem trước thành công!",
            "executed_model": executed_model,
            "data": sanitized_data,
            "preview_html": preview_html
        }
    except Exception as exc:
        logger.exception("Acceptance AI parse failed: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi phân tích AI: {str(exc)}",
            "data": None,
            "preview_html": ""
        }


def download_acceptance_file_controller(file_name: str) -> FileResponse:
    """Stream generated Excel or Word file for browser download."""
    clean_name = os.path.basename(file_name)
    
    # Ưu tiên tìm trong thư mục chính thức Ho So Du An/Nghiem Thu
    nghiem_thu_dir = WORKING_DIR / "Ho So Du An" / "Nghiem Thu"
    candidate_path = nghiem_thu_dir / clean_name
    
    if candidate_path.is_file():
        file_path = candidate_path
    else:
        file_path = OUTPUTS_DIR / clean_name

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp nghiệm thu đã tạo.")

    if clean_name.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif clean_name.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        filename=clean_name,
        media_type=media_type
    )


def generate_installation_acceptance_word_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to generate Installation Acceptance Word (.docx) document matching template 1:1."""
    try:
        result = generate_installation_acceptance_word(data)
        preview_html = generate_installation_acceptance_preview_html(result["acceptance_data"])
        return {
            "status": "success",
            "message": "Đã tạo Biên bản nghiệm thu lắp đặt Word (.docx) chuẩn 100% mẫu thành công!",
            "file_name": result["file_name"],
            "download_url": result["download_url"],
            "file_path": result.get("file_path", ""),
            "total_amount": result["total_amount"],
            "preview_html": preview_html,
            "acceptance_data": result["acceptance_data"]
        }
    except Exception as exc:
        logger.exception("Error generating installation acceptance docx: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo tài liệu Word nghiệm thu lắp đặt: {str(exc)}",
            "file_name": "",
            "download_url": ""
        }


def render_installation_acceptance_preview_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to recalculate and refresh live installation acceptance preview HTML."""
    try:
        sanitized = prepare_installation_acceptance_data(data)
        preview_html = generate_installation_acceptance_preview_html(sanitized)
        return {
            "status": "success",
            "preview_html": preview_html,
            "data": sanitized
        }
    except Exception as exc:
        logger.exception("Error rendering installation acceptance preview: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
            "preview_html": f"<div class='alert alert-danger'>Lỗi cập nhật xem trước nghiệm thu lắp đặt: {str(exc)}</div>"
        }


def parse_installation_acceptance_text_controller(request: InstallationAIParseRequest) -> Dict[str, Any]:
    """Analyze raw contract or installation handover text with Gemini AI to extract acceptance items."""
    try:
        raw_text = request.raw_text.strip()
        if not raw_text:
            raise ValueError("Văn bản đầu vào không được để trống.")

        parsed_data = parse_installation_acceptance_text(
            raw_input_text=raw_text,
            preferred_model=request.model_name
        )

        executed_model = parsed_data.pop("_executed_model", request.model_name or "Gemini")
        sanitized_data = prepare_installation_acceptance_data(parsed_data)
        preview_html = generate_installation_acceptance_preview_html(sanitized_data)

        return {
            "status": "success",
            "message": f"AI ({executed_model}) đã bóc tách dữ liệu nghiệm thu lắp đặt thành công!",
            "executed_model": executed_model,
            "data": sanitized_data,
            "preview_html": preview_html
        }
    except Exception as exc:
        logger.exception("Installation Acceptance AI parse failed: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi phân tích AI: {str(exc)}",
            "data": None,
            "preview_html": ""
        }


async def upload_and_parse_installation_file_controller(file: UploadFile, model_name: Optional[str] = None) -> Dict[str, Any]:
    """Upload contract or draft document (.docx, .xlsx, .txt), extract text and parse with AI."""
    from app.services.acceptance_ai_service import parse_installation_acceptance_file
    from app.services.installation_acceptance_preview_service import generate_installation_acceptance_preview_html

    try:
        content = await file.read()
        filename = file.filename or "uploaded_document.docx"
        data = parse_installation_acceptance_file(content, filename, preferred_model=model_name)
        preview_html = generate_installation_acceptance_preview_html(data)
        return {
            "status": "success",
            "message": f"AI đã trích xuất dữ liệu thành công từ tệp '{filename}'!",
            "data": data,
            "preview_html": preview_html
        }
    except Exception as exc:
        logger.exception("Upload and parse installation file failed: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi đọc và trích xuất tệp: {str(exc)}",
            "data": None,
            "preview_html": ""
        }


def get_installation_sample_data_controller() -> Dict[str, Any]:
    """Return default CX Technology RFID sample data for installation acceptance."""
    sample = {
        "so_hop_dong": "HMV151020250001",
        "so_bien_ban": "002_BIEN_BAN_NGHIEM_THU_BAN_GIAO_CX_",
        "ngay_ky_hop_dong": "09/12/2025",
        "ngay_nghiem_thu": "09/10/2026",
        "gia_tri_hop_dong": "234.000.000 VNĐ",
        "ten_he_thong": "RFID 硬體 (RFID Hardware) – Phần mềm tùy chỉnh chức năng hệ thống RFID",
        "ten_he_thong_trung": "RFID 硬體（RFID Hardware）－ RFID 系統客製化軟體",
        "ben_a": {
            "ten_cong_ty": "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
            "ten_tieng_trung": "CX TECHNOLOGY (VN) 股份有限公司",
            "dia_chi": "Số Lô CT 10b-12-14-16-18-20-22-24a, Khu C, KCX Tân Thuận, Phường Tân Thuận, Tp. Hồ Chí Minh",
            "mst": "0300737556"
        },
        "ben_b": {
            "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
            "ten_tieng_trung": "宏明環球有限公司",
            "dia_chi": "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
            "mst": "0318280158",
            "nguoi_dai_dien": "Ông TANG WEI LI",
            "chuc_vu": "Tổng giám đốc"
        },
        "can_cu_phu_luc": "Phụ lục 1 – Báo giá khai phá chức năng ưu hóa tùy chỉnh (V1.2.3_VND) kèm theo hợp đồng",
        "can_cu_phu_luc_trung": "附件一「RFID系統客製化功能開發報價單（V1.2.3_VND）」",
        "can_cu_ky_thuat": "Biên bản kiểm tra kỹ thuật ngày 04/03/2026 xác nhận hoàn thành lắp đặt và kết quả chạy thử, điều chỉnh, theo dõi vận hành sau đó.",
        "can_cu_ky_thuat_trung": "依據 2026/03/04《技術檢驗單》所確認之安裝完成情況，以及其後之試運行、調整及運行觀察結果。",
        "giai_doan_thanh_toan": "Giai đoạn 2 (Sau khi triển khai lắp đặt đưa vào sử dụng - 40%)",
        "so_tien_thanh_toan": "93.600.000 VND",
        "so_tien_chu_vn": "Chín mươi ba triệu sáu trăm nghìn đồng chẵn.",
        "so_tien_chu_tw": "玖仟參佰陸拾萬越盾整",
        "hang_muc": [
            {
                "stt": 1,
                "ten_san_pham": "Concept Development",
                "hang_muc": "1. Xác nhận mở vụ án / 立案確認, Yêu cầu xác nhận / 需求確認",
                "noi_dung": "",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu.\\n驗收合格，確認符合需求"
            },
            {
                "stt": 2,
                "ten_san_pham": "加工組 GIA CÔNG 「進站/出站 與 報工」",
                "hang_muc": "2. Mỗi máy có thể quét các nhân viên vận hành máy khác nhau khi vào và ra khỏi trạm.\\n進出站時每個機台都可以掃不同的機台操作者Máy quét mã vạch được tối ưu hóa để lựa chọn máy bằng cách nhấp chuột。掃描機台條碼優化為點選機台方式。",
                "noi_dung": "",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu.\\n驗收合格，確認符合需求"
            },
            {
                "stt": 3,
                "ten_san_pham": "包裝組 ĐÓNG GÓI 「進站/出站」",
                "hang_muc": "3. Quét nhiều ID nhân viên để vào và ra khỏi trạm.\\n進出站可刷複數人員工號。",
                "noi_dung": "",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu.\\n驗收合格，確認符合需求"
            },
            {
                "stt": 4,
                "ten_san_pham": "通箱資訊查詢 Truy vấn thông tin thùng",
                "hang_muc": "4. QR條碼掃描\\nQuét mã vạch QR",
                "noi_dung": "",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu.\\n驗收合格，確認符合需求"
            },
            {
                "stt": 5,
                "ten_san_pham": "報工APP－通箱解除綁定 APP Báo Công",
                "hang_muc": "5. 特定人員解除綁定權限控管\\nHủy ràng buộc quyền cho nhân viên cụ thể",
                "noi_dung": "",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu.\\n驗收合格，確認符合需求"
            },
            {
                "stt": 6,
                "ten_san_pham": "RFID離線資料暫存優化 Tối ưu hóa lưu trữ ngoại tuyến",
                "hang_muc": "6. RFID離線模式可以自動切換\\nChế độ ngoại tuyến RFID có thể chuyển đổi tự động",
                "noi_dung": "",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\\n確認已投入 sử dụng",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu.\\n驗收合格，確認符合需求"
            },
            {
                "stt": 7,
                "ten_san_pham": "WEB RFID報表查詢 Truy vấn báo cáo RFID WEB",
                "hang_muc": "7. 增加Run Card查詢條件\\nThêm điều kiện truy vấn Run Card",
                "noi_dung": "",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\\n確認已投入 sử dụng",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu.\\n驗收合格，確認符合需求"
            }
        ],
        "payment_stages": [
            {
                "stage_id": "1",
                "stage": "GIAI ĐOẠN 1\n第一期",
                "condition": "Sau khi ký kết hợp đồng\n簽約完成時",
                "rate": "40%",
                "amount": "93.600.000 VND",
                "selected": False
            },
            {
                "stage_id": "2",
                "stage": "GIAI ĐOẠN 2\n第二期",
                "condition": "Sau khi triển khai sản phẩm đưa vào sử dụng\n產品安裝後",
                "rate": "40%",
                "amount": "93.600.000 VND",
                "selected": True
            },
            {
                "stage_id": "3",
                "stage": "GIAI ĐOẠN 3\n第三期",
                "condition": "Khi nghiệm thu đạt tiêu chuẩn\n驗收合格時",
                "rate": "20%",
                "amount": "46.800.000 VND",
                "selected": True
            }
        ]
    }
    return {"status": "success", "data": sample}


def list_acceptance_files_controller() -> Dict[str, Any]:
    """List all created acceptance files (.xlsx and .docx) in Ho So Du An/Nghiem Thu."""
    from datetime import datetime
    from app.database import get_db_connection

    nghiem_thu_dir = WORKING_DIR / "Ho So Du An" / "Nghiem Thu"
    if not nghiem_thu_dir.exists():
        return {"status": "success", "files": []}

    doc_map = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.file_name, d.contract_code, d.contract_id, 
                   c.customer_name_vi, c.project_name_vi
            FROM documents d
            LEFT JOIN contracts c ON (c.id = d.contract_id OR c.contract_code = d.contract_code)
            WHERE d.doc_type = 'NGHIEM_THU'
        """)
        for row in cursor.fetchall():
            doc_map[row["file_name"]] = dict(row)
        conn.close()
    except Exception:
        pass

    files = []
    # Quét cả file .xlsx và .docx trong thư mục
    scanned_files = list(nghiem_thu_dir.glob("*.xlsx")) + list(nghiem_thu_dir.glob("*.docx"))
    
    for f in scanned_files:
        if f.is_file() and not f.name.startswith("~$"):
            stat = f.stat()
            mtime_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            doc_info = doc_map.get(f.name) or {}
            c_code = (doc_info.get("contract_code") or "").strip()
            
            is_docx = f.suffix.lower() == ".docx"
            format_label = "Word (.docx) - Lắp đặt" if is_docx else "Excel (.xlsx) - Sửa chữa"
            badge_color = "blue" if is_docx else "green"

            files.append({
                "file_name": f.name,
                "file_path": str(f.resolve()),
                "file_size": stat.st_size,
                "file_size_formatted": f"{stat.st_size / 1024:.1f} KB",
                "modified_time": mtime_str,
                "mtime_ts": stat.st_mtime,
                "download_url": f"/api/v1/acceptance/download/{f.name}",
                "contract_code": c_code,
                "contract_id": doc_info.get("contract_id"),
                "customer_name": doc_info.get("customer_name_vi") or "",
                "project_name": doc_info.get("project_name_vi") or "",
                "is_linked_contract": bool(c_code),
                "is_docx": is_docx,
                "format_label": format_label,
                "badge_color": badge_color
            })

    files.sort(key=lambda x: x["mtime_ts"], reverse=True)
    return {"status": "success", "files": files}


