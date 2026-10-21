"""Data models for ECO PRIME Quotation and AI Schematic Analysis."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EcoPrimeItem(BaseModel):
    """Một dòng sản phẩm / thiết bị trong báo giá ECO PRIME."""
    stt: int = Field(default=1, description="Số thứ tự")
    name: str = Field(default="", description="Tên thiết bị song ngữ Việt - Trung")
    category: str = Field(default="", description="Chủng loại song ngữ Việt - Trung")
    desc: str = Field(default="", description="Quy cách kỹ thuật song ngữ chi tiết")
    qty: float = Field(default=1.0, description="Số lượng")
    unit: str = Field(default="BỘ", description="Đơn vị tính (BỘ / SET)")
    unit_price_usd: Optional[float] = Field(default=None, description="Đơn giá bán USD (để trống cho Sếp điền)")
    total_price_usd: Optional[float] = Field(default=None, description="Thành tiền USD")
    unit_cost_usd: Optional[float] = Field(default=None, description="Giá vốn xuất xưởng USD")
    tax_rate: float = Field(default=0.08, description="Thuế suất VAT (0.0, 0.08, 0.20)")


class EcoPrimeQuotationData(BaseModel):
    """Toàn bộ dữ liệu của một bản Báo giá ECO PRIME hoàn chỉnh."""
    customer_name: Optional[str] = Field(default="", description="Tên công ty khách hàng mua")
    customer_dept: Optional[str] = Field(default="Ban Quản lý Dự án & Cơ điện 機電與專案部", description="Bộ phận")
    customer_contact: Optional[str] = Field(default="", description="Người liên hệ")
    customer_phone: Optional[str] = Field(default="", description="Số điện thoại")
    customer_address: Optional[str] = Field(default="", description="Địa chỉ nhà máy")
    customer_email: Optional[str] = Field(default="", description="Email liên hệ")
    
    quote_title: str = Field(
        default="Báo giá hệ thống đo đếm điện năng cao áp 高壓變電站電能計量系統硬體報價訂購確認單",
        description="Tiêu đề báo giá song ngữ"
    )
    quote_date: str = Field(default="", description="Ngày báo giá DD/MM/YYYY")
    project_solution: str = Field(
        default="1) Giải pháp nâng cấp hệ thống đo đếm điện năng và giám sát các trạm biến áp cao thế",
        description="Dòng tiêu đề giải pháp"
    )
    exchange_rate: float = Field(default=26130.0, description="Tỷ giá quy đổi VND/USD")
    items: List[EcoPrimeItem] = Field(default_factory=list, description="Danh sách thiết bị bóc tách")
    
    notes_validity: Optional[str] = Field(
        default="",
        description="Điều khoản hiệu lực và bảo hành 1 năm"
    )
    notes_payment: Optional[str] = Field(
        default="3. 付款方式 : 訂金 35%、 交貨 55%、驗收 10% TT3",
        description="Điều khoản thanh toán màu đỏ rực"
    )


class SchematicAnalysisRequest(BaseModel):
    """Payload gửi lên từ giao diện web để AI Vision phân tích sơ đồ."""
    image_base64: Optional[str] = Field(default=None, description="Dữ liệu ảnh base64 (Data URL hoặc raw)")
    file_name: Optional[str] = Field(default=None, description="Tên tệp gốc")
    mime_type: Optional[str] = Field(default="image/png", description="MIME type")
    customer_name_hint: Optional[str] = Field(default=None, description="Tên công ty gợi ý nếu người dùng nhập sẵn")
    preferred_model: Optional[str] = Field(default=None, description="Model Gemini lựa chọn")


class SchematicAnalysisResponse(BaseModel):
    """Kết quả phân tích từ AI trả về cho giao diện web."""
    success: bool = True
    data: Optional[EcoPrimeQuotationData] = None
    detected_substations: Optional[List[Dict[str, Any]]] = None
    ai_summary: Optional[str] = None
    error: Optional[str] = None
