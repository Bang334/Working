"""Controller handling repair contract endpoints and AI parsing."""

import os
from pathlib import Path
from typing import Any, Dict
from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.models.repair_contract_models import (
    GenerateRepairDocxResponse,
    RepairAIParseRequest,
    RepairContractData,
)
from app.services.repair_contract_ai_service import parse_repair_contract_with_ai
from app.services.repair_contract_service import (
    delete_repair_contract,
    get_all_repair_contracts_list,
    get_repair_contract_detail,
    prepare_repair_contract_data,
    save_repair_contract_to_db,
)
from app.services.repair_contract_word_service import generate_repair_contract_docx


def parse_raw_repair_contract_text_controller(request: RepairAIParseRequest) -> Dict[str, Any]:
    """Parse raw text, tables, or uploaded files into repair contract data schema."""
    try:
        parsed_data = parse_repair_contract_with_ai(
            raw_text=request.raw_text or "",
            model_name=request.model_name,
            file_base64=request.file_base64,
            file_name=request.file_name,
            file_mime=request.file_mime,
        )
        return {
            "status": "success",
            "message": "Gemini AI đã bóc tách thông tin sửa chữa và linh kiện thành công!",
            "data": parsed_data,
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Lỗi bóc tách AI hợp đồng sửa chữa: {str(exc)}",
            "data": None,
        }


def generate_repair_contract_controller(contract_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate official DOCX file for repair contract."""
    try:
        prepared = prepare_repair_contract_data(contract_data)
        result = generate_repair_contract_docx(prepared, contract_data.get("custom_output_dir"))
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xuất file Word hợp đồng sửa chữa: {str(exc)}"
        )


def save_repair_contract_controller(contract_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save repair contract to SQLite database and generate file."""
    try:
        result = save_repair_contract_to_db(contract_data)
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi lưu hợp đồng sửa chữa: {str(exc)}"
        )


def list_repair_contracts_controller() -> Dict[str, Any]:
    """List all repair contracts."""
    try:
        contracts = get_all_repair_contracts_list()
        return {
            "status": "success",
            "count": len(contracts),
            "data": contracts
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "data": []
        }


def get_repair_contract_detail_controller(contract_code: str) -> Dict[str, Any]:
    """Get detail of a specific repair contract."""
    detail = get_repair_contract_detail(contract_code)
    if not detail:
        raise HTTPException(status_code=404, detail="Không tìm thấy hợp đồng sửa chữa.")
    return {
        "status": "success",
        "data": detail
    }


def delete_repair_contract_controller(contract_code: str) -> Dict[str, Any]:
    """Delete a repair contract."""
    success = delete_repair_contract(contract_code)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy hợp đồng sửa chữa để xóa.")
    return {
        "status": "success",
        "message": f"Đã xóa hợp đồng sửa chữa {contract_code} khỏi hệ thống."
    }


def download_repair_contract_file_controller(filename: str):
    """Download a generated repair contract file."""
    # Look in OUTPUTS_DIR or Ho So Du An/Hop Dong
    clean_filename = os.path.basename(filename)
    candidates = [
        OUTPUTS_DIR / clean_filename,
        WORKING_DIR / "Ho So Du An" / "Hop Dong" / clean_filename,
    ]
    for path in candidates:
        if path.exists():
            return FileResponse(
                path=str(path),
                filename=clean_filename,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    raise HTTPException(status_code=404, detail=f"Không tìm thấy file: {clean_filename}")
