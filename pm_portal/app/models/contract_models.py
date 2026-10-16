"""Contract data models using Pydantic."""

from typing import List, Optional
from pydantic import BaseModel, Field


class PartyInfo(BaseModel):
    """Company legal party information."""
    ten_cong_ty: str = Field(..., description="Tên công ty tiếng Việt")
    ten_tieng_trung: Optional[str] = Field("", description="Tên công ty tiếng Trung (Phồn thể)")
    dia_chi: str = Field(..., description="Địa chỉ tiếng Việt")
    dia_chi_trung: Optional[str] = Field("", description="Địa chỉ tiếng Trung (Phồn thể)")
    mst: str = Field(..., description="Mã số thuế")
    nguoi_dai_dien: str = Field(..., description="Họ và tên người đại diện pháp luật")
    chuc_vu: str = Field(..., description="Chức vụ tiếng Việt")
    chuc_vu_trung: Optional[str] = Field("", description="Chức vụ tiếng Trung")


class ContractItem(BaseModel):
    """Line item in contract equipment/software list."""
    stt: int = Field(..., description="Số thứ tự")
    ten_san_pham: str = Field(..., description="Tên sản phẩm song ngữ hoặc đơn ngữ")
    don_gia: str = Field(..., description="Đơn giá (VD: 185.000.000 VND)")
    so_luong: str = Field(..., description="Số lượng kèm đơn vị tính (VD: 1 SET)")
    tong_gia: str = Field(..., description="Tổng giá (VD: 185.000.000 VND)")


class PaymentInstallment(BaseModel):
    """Payment phase installment."""
    dot: int = Field(..., description="Đợt thanh toán")
    phan_tram: float = Field(..., description="Tỷ lệ phần trăm (VD: 35.0)")
    so_tien: Optional[str] = Field("", description="Số tiền đợt (VND)")
    dieu_kien_viet: str = Field(..., description="Điều kiện thanh toán tiếng Việt")
    dieu_kien_trung: Optional[str] = Field("", description="Điều kiện thanh toán tiếng Trung")
    thoi_han_tt_ngay: Optional[int] = Field(None, description="Thời hạn T/T của đợt, tính bằng ngày")
    nguon_mau_sheet: Optional[str] = Field("", description="Sheet 備註 được dùng làm mẫu")
    tieu_de: Optional[str] = Field("", description="Tên ngắn của đợt bằng tiếng Việt")
    tieu_de_trung: Optional[str] = Field("", description="Tên ngắn của đợt bằng tiếng Trung")
    mo_ta_nguoi_dung: Optional[str] = Field("", description="Mục đích hoặc điều kiện riêng do người dùng ghi rõ")


class ProjectInfo(BaseModel):
    """Project or quotation overview information."""
    ten_du_an_viet: str = Field(..., description="Tên dự án tiếng Việt")
    ten_du_an_trung: Optional[str] = Field("", description="Tên dự án tiếng Trung")


class ContractData(BaseModel):
    """Full contract schema matching Hong Ming Global standards."""
    so_hop_dong: str = Field("HD-20261013-001", description="Số hợp đồng")
    ngay_ky: str = Field("13", description="Ngày ký")
    thang_ky: str = Field("10", description="Tháng ký")
    nam_ky: str = Field("2026", description="Năm ký")
    ben_a: PartyInfo
    ben_b: Optional[PartyInfo] = None
    du_an: ProjectInfo
    hang_muc: List[ContractItem] = Field(default_factory=list)
    tong_so_luong: Optional[str] = Field("", description="Tổng số lượng (VD: 36 SET)")
    tong_tien_truoc_giam: Optional[str] = Field("", description="Tổng tiền trước giảm")
    tong_tien_sau_giam: Optional[str] = Field("", description="Tổng tiền sau giảm")
    tong_tien_hop_dong_so: str = Field(..., description="Tổng tiền hợp đồng bằng số")
    tong_tien_chu_viet: Optional[str] = Field("", description="Tổng tiền bằng chữ tiếng Việt")
    tong_tien_chu_trung: Optional[str] = Field("", description="Tổng tiền bằng chữ tiếng Trung đại tả")
    phan_bo_thanh_toan: Optional[List[PaymentInstallment]] = Field(default_factory=list)
    thoi_gian_giao_hang_ngay: int = Field(80, description="Thời gian giao hàng (ngày)")
    thoi_gian_bao_hanh_thang: int = Field(12, description="Thời gian bảo hành (tháng)")


class AIParseRequest(BaseModel):
    """Request payload for Gemini AI text or multimodal file parsing."""
    model_config = {"protected_namespaces": ()}
    raw_text: Optional[str] = Field("", description="Văn bản hoặc ghi chú kèm theo")
    model_name: Optional[str] = Field(None, description="Tên model Gemini ưu tiên")
    file_base64: Optional[str] = Field(None, description="Dữ liệu tệp Base64 (ảnh hoặc Excel/Word)")
    file_name: Optional[str] = Field(None, description="Tên tệp gốc kèm phần mở rộng")
    file_mime: Optional[str] = Field(None, description="MIME type của tệp")


class GenerateDocxResponse(BaseModel):
    """Response returned after generating DOCX file."""
    status: str
    message: str
    file_name: str
    download_url: str
    total_amount: str
    company_name: str
