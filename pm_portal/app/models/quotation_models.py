"""Quotation data models using Pydantic."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QuotationItemModel(BaseModel):
    """Line item in quotation."""
    name: str = Field(..., description="Tên thiết bị, quy cách hoặc dịch vụ")
    unit: str = Field("Bộ", description="Đơn vị tính")
    qty: int = Field(1, description="Số lượng")
    price: float = Field(0.0, description="Đơn giá (VND)")


class QuotationAIParseRequest(BaseModel):
    """Request payload for Gemini AI quotation parsing."""
    model_config = {"protected_namespaces": ()}
    raw_text: Optional[str] = Field("", description="Văn bản hoặc ghi chú email/chat cần bóc tách")
    model_name: Optional[str] = Field(None, description="Tên model Gemini ưu tiên")
    file_base64: Optional[str] = Field(None, description="Dữ liệu tệp Base64 (ảnh hoặc Excel/Word)")
    file_name: Optional[str] = Field(None, description="Tên tệp gốc kèm phần mở rộng")
    file_mime: Optional[str] = Field(None, description="MIME type của tệp")


class QuotationSaveRequest(BaseModel):
    """Payload to save quotation with versioning and backup preservation."""
    customer_name_vi: str = Field(..., description="Tên pháp nhân khách hàng tiếng Việt")
    customer_name_zh: Optional[str] = Field("", description="Tên pháp nhân khách hàng tiếng Trung")
    tax_code: Optional[str] = Field("", description="Mã số thuế")
    quotation_no: str = Field(..., description="Số báo giá (HM-QT-...)")
    quotation_date: Optional[str] = Field("", description="Ngày phát hành báo giá")
    project_name: Optional[str] = Field("", description="Tên dự án triển khai")
    contact_person: Optional[str] = Field("", description="Người tiếp nhận / phòng ban")
    validity: Optional[str] = Field("30 ngày", description="Thời hạn hiệu lực")
    lead_time: Optional[str] = Field("60 - 80 ngày", description="Thời gian giao hàng")
    warranty: Optional[str] = Field("12 tháng", description="Thời hạn bảo hành")
    payment_terms: Optional[str] = Field("Tạm ứng 50%, Giao hàng 40%, Nghiệm thu 10%", description="Điều kiện thanh toán")
    notes: Optional[str] = Field("", description="Ghi chú kỹ thuật")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Danh sách các hạng mục thiết bị")
