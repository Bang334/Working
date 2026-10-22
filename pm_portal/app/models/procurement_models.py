# -*- coding: utf-8 -*-
"""Pydantic models for Procurement Orders & Supplier PO Tracking."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProcurementOrderItem(BaseModel):
    """Model representing a single procurement order row."""
    id: Optional[int] = None
    order_no: Optional[int] = None
    project_name: str = Field(..., description="Tên dự án")
    category: Optional[str] = Field(None, description="Hạng mục (Hệ thống, Server, IPC, Mạng...)")
    item_name: str = Field(..., description="Tên vật tư / thiết bị")
    quantity: float = Field(1.0, description="Số lượng")
    unit: Optional[str] = Field("Bộ", description="Đơn vị tính")
    customer_company: Optional[str] = Field(None, description="Công ty khách hàng / Dự án")
    supplier_name: str = Field(..., description="Nhà cung cấp")
    order_date: Optional[str] = Field(None, description="Ngày đặt hàng (YYYY-MM-DD)")
    eta_date: Optional[str] = Field(None, description="Ngày giao dự kiến ETA (YYYY-MM-DD)")
    actual_delivery_date: Optional[str] = Field(None, description="Ngày giao thực tế (YYYY-MM-DD)")
    material_desc: Optional[str] = Field(None, description="Quy cách ngắn / vật liệu")
    supplier_payment_status: Optional[str] = Field(None, description="Tình trạng thanh toán NCC")
    delivery_status: str = Field("PENDING", description="PENDING / IN_TRANSIT / DELIVERED / DELAYED")
    delivery_status_label: Optional[str] = Field(None, description="Nhãn hiển thị (Đã giao, Đang giao...)")
    shipping_notes: Optional[str] = Field(None, description="Ghi chú vận chuyển / Rủi ro")
    unit_price: float = Field(0.0, description="Đơn giá")
    total_amount: float = Field(0.0, description="Tổng tiền")
    currency: str = Field("VND", description="VND / USD")


class ProcurementCreateRequest(BaseModel):
    """Request payload to create a new procurement order."""
    order_no: Optional[int] = None
    project_name: str
    category: Optional[str] = None
    item_name: str
    quantity: float = 1.0
    unit: Optional[str] = "Bộ"
    customer_company: Optional[str] = None
    supplier_name: str
    order_date: Optional[str] = None
    eta_date: Optional[str] = None
    actual_delivery_date: Optional[str] = None
    material_desc: Optional[str] = None
    supplier_payment_status: Optional[str] = None
    delivery_status: Optional[str] = "PENDING"
    shipping_notes: Optional[str] = None
    unit_price: Optional[float] = 0.0
    total_amount: Optional[float] = 0.0
    currency: Optional[str] = "VND"


class ProcurementUpdateRequest(BaseModel):
    """Request payload to update an existing procurement order."""
    order_no: Optional[int] = None
    project_name: Optional[str] = None
    category: Optional[str] = None
    item_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    customer_company: Optional[str] = None
    supplier_name: Optional[str] = None
    order_date: Optional[str] = None
    eta_date: Optional[str] = None
    actual_delivery_date: Optional[str] = None
    material_desc: Optional[str] = None
    supplier_payment_status: Optional[str] = None
    delivery_status: Optional[str] = None
    shipping_notes: Optional[str] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None


class ProcurementAIParseRequest(BaseModel):
    """Request to parse unstructured supplier quotation / order text with AI."""
    raw_text: str = Field(..., description="Văn bản báo giá / email / PO của NCC")
    model_name: Optional[str] = Field(None, description="Model Gemini ưu tiên")


class ProcurementStats(BaseModel):
    """Summary statistics for procurement tracker dashboard."""
    total_orders: int = 0
    in_transit_count: int = 0
    delivered_count: int = 0
    delayed_count: int = 0
    pending_payment_count: int = 0
    suppliers: List[str] = []
    projects: List[str] = []


class QuickFieldUpdateRequest(BaseModel):
    """Payload to fast inline update a single order field (order_date, eta_date, actual_delivery_date, etc.)."""
    field: str
    value: Any
