# -*- coding: utf-8 -*-
"""Pydantic models for Project Receivables & AR Tracker."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReceivableItem(BaseModel):
    """Model representing a single receivable milestone row."""
    id: Optional[int] = None
    order_no: Optional[int] = None
    project_name: str = Field(..., description="Tên dự án và đợt thanh toán")
    customer_name: str = Field(..., description="Tên công ty khách hàng")
    contract_code: Optional[str] = Field(None, description="Số hợp đồng / PO")
    total_contract_amount: float = Field(0.0, description="Tổng giá trị HĐ (VNĐ)")
    net_amount: float = Field(0.0, description="Khoản thanh toán chưa thuế (VNĐ)")
    vat_rate: float = Field(0.0, description="Tỷ lệ thuế VAT (ví dụ: 0.0, 0.08)")
    vat_amount: float = Field(0.0, description="Tiền thuế (VNĐ)")
    gross_amount: float = Field(0.0, description="Các khoản phải thu bao gồm thuế (VNĐ)")
    received_amount: float = Field(0.0, description="Số tiền đã nhận được (VNĐ)")
    remaining_debt: float = Field(0.0, description="Số tiền còn nợ (VNĐ)")
    customer_promised_date: Optional[str] = Field(None, description="Khách hàng phản hồi ngày thanh toán")
    due_date: Optional[str] = Field(None, description="Hạn thanh toán (YYYY-MM-DD)")
    paid_date: Optional[str] = Field(None, description="Ngày đã thu tiền (YYYY-MM-DD)")
    doc_status: Optional[str] = Field(None, description="Trạng thái chứng từ (PKL / INV / BB Nghiệm thu)")
    collection_status: Optional[str] = Field("PENDING", description="Trạng thái thu nợ (PAID, PENDING, DELAYED, URGENT)")
    notes: Optional[str] = Field(None, description="Hành động giục nợ / Ghi chú")
    linked_milestone_id: Optional[int] = None
    days_left: Optional[int] = None
    is_overdue: bool = False


class ReceivableCreateRequest(BaseModel):
    order_no: Optional[int] = None
    project_name: str
    customer_name: str
    contract_code: Optional[str] = None
    total_contract_amount: float = 0.0
    net_amount: float = 0.0
    vat_rate: float = 0.0
    received_amount: float = 0.0
    customer_promised_date: Optional[str] = None
    due_date: Optional[str] = None
    paid_date: Optional[str] = None
    doc_status: Optional[str] = None
    collection_status: Optional[str] = "PENDING"
    notes: Optional[str] = None


class ReceivableUpdateRequest(BaseModel):
    order_no: Optional[int] = None
    project_name: Optional[str] = None
    customer_name: Optional[str] = None
    contract_code: Optional[str] = None
    total_contract_amount: Optional[float] = None
    net_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    gross_amount: Optional[float] = None
    received_amount: Optional[float] = None
    customer_promised_date: Optional[str] = None
    due_date: Optional[str] = None
    paid_date: Optional[str] = None
    doc_status: Optional[str] = None
    collection_status: Optional[str] = None
    notes: Optional[str] = None


class QuickReceivableStatusRequest(BaseModel):
    collection_status: str
    paid_date: Optional[str] = None


class QuickReceivableNotesRequest(BaseModel):
    notes: Optional[str] = ""


# Aliases for controller compatibility
ReceivableQuickStatusUpdate = QuickReceivableStatusRequest
ReceivableQuickNotesUpdate = QuickReceivableNotesRequest


class ReceivableStats(BaseModel):
    total_receivable: float = 0.0
    total_received: float = 0.0
    total_debt: float = 0.0
    total_milestones: int = 0
    paid_count: int = 0
    pending_count: int = 0
    overdue_count: int = 0
    urgent_count: int = 0
    completion_rate: float = 0.0
    customers: List[str] = []
    contracts: List[str] = []
