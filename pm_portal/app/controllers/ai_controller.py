"""AI Controller for handling natural language input and Gemini parsing."""

import logging
from typing import Any, Dict

from app.models.contract_models import AIParseRequest
from app.services.ai_service import parse_contract_text
from app.services.contract_service import prepare_contract_data
from app.services.preview_service import generate_contract_preview_html

logger = logging.getLogger(__name__)


def parse_raw_contract_text_controller(request: AIParseRequest) -> Dict[str, Any]:
    """Parse unstructured user text or attached files (image, Excel, docx) using Gemini AI."""
    try:
        import base64
        raw_text = (request.raw_text or "").strip()
        file_bytes = None
        if request.file_base64:
            b64_str = request.file_base64
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            file_bytes = base64.b64decode(b64_str)

        if not raw_text and not file_bytes:
            raise ValueError("Vui lòng nhập văn bản hoặc chọn tệp (Ảnh / Excel) để AI bóc tách.")

        parsed_data = parse_contract_text(
            raw_input_text=raw_text,
            file_bytes=file_bytes,
            file_mime_type=request.file_mime,
            file_name=request.file_name,
            preferred_model=request.model_name
        )

        executed_model = parsed_data.pop("_executed_model", request.model_name or "Gemini")
        # Prepare and calculate
        sanitized_data = prepare_contract_data(parsed_data)
        preview_html = generate_contract_preview_html(sanitized_data)

        return {
            "status": "success",
            "message": f"AI ({executed_model}) đã bóc tách dữ liệu và sinh bản xem trước thành công!",
            "executed_model": executed_model,
            "data": sanitized_data,
            "preview_html": preview_html
        }
    except Exception as exc:
        logger.exception("AI parse failed: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi phân tích AI: {str(exc)}",
            "data": None,
            "preview_html": ""
        }
