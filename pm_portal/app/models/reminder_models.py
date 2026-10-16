"""Payment request and reminder data models using Pydantic."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PaymentItem(BaseModel):
    """Individual contract payment item or line item."""
    stt: int = Field(1, description="Số thứ tự")
    so_hop_dong: str = Field(..., description="Mã số Hợp đồng hoặc Đơn hàng (VD: HMV15092026-001)")
    hang_muc: str = Field(..., description="Tên hạng mục sản phẩm / dịch vụ (song ngữ hoặc Việt/Trung)")
    noi_dung_thanh_toan: Optional[str] = Field("", description="Nội dung thanh toán (VD: Hợp đồng 50%, Tạm ứng 30%, Toàn phần)")
    so_tien: str = Field(..., description="Số tiền thanh toán (VD: 32500000 hoặc 32.500.000)")
    vat_info: Optional[str] = Field("", description="Thông tin VAT (VD: 含 VAT 8%, Đã gồm VAT 8%, Chưa VAT)")
    han_thanh_toan: str = Field(..., description="Hạn chót thanh toán (VD: 2026/10/15 hoặc 15/10/2026)")
    ghi_chu: Optional[str] = Field("", description="Ghi chú thêm nếu có")


class CustomerInfo(BaseModel):
    """Customer recipient information."""
    ten_khach_hang: str = Field("CX Technology (VN)", description="Tên khách hàng tiếng Việt")
    ten_tieng_trung: Optional[str] = Field("CX Technology (VN)", description="Tên khách hàng tiếng Trung")
    email_to: List[str] = Field(default_factory=lambda: ["pur04_vn@mail.cxtechnology.com"], description="Danh sách email người nhận chính")
    email_cc: List[str] = Field(default_factory=lambda: [
        "jenson@youngming-mes.com",
        "jessica@youngming-mes.com",
        "lisa@youngming-mes.com",
        "sales@hongming-global.com"
    ], description="Danh sách email CC")
    dia_chi: Optional[str] = Field("", description="Địa chỉ nhà máy")
    nguoi_lien_he: Optional[str] = Field("", description="Người liên hệ phụ trách mua hàng hoặc kế toán")


class BankInfo(BaseModel):
    """Beneficiary bank account details for Hong Ming Global."""
    ten_tai_khoan: str = Field("CÔNG TY TNHH TOÀN CẦU HONG MING", description="Tên chủ tài khoản")
    so_tai_khoan: str = Field("0318280158", description="Số tài khoản ngân hàng")
    ngan_hang: str = Field("Ngân hàng TMCP Á Châu (ACB) - Chi nhánh TP.HCM", description="Ngân hàng & Chi nhánh")
    noi_dung_chuyen_khoan: Optional[str] = Field("", description="Cú pháp nội dung chuyển khoản")


class ReminderData(BaseModel):
    """Full payment reminder and request schema matching Hong Ming Global standard."""
    cap_do: int = Field(1, description="Cấp độ nhắc nợ: 1 (Đề nghị thanh toán / Trước hạn), 2 (Quá hạn 1-7 ngày), 3 (Cảnh báo khẩn cấp >14 ngày)")
    so_cong_van: str = Field("HM-PR-20261013-001", description="Số công văn / Mã phiếu đề nghị")
    ngay_phat_hanh: str = Field("13/10/2026", description="Ngày phát hành văn bản")
    
    khach_hang: CustomerInfo = Field(default_factory=CustomerInfo)
    khoan_thanh_toan: List[PaymentItem] = Field(default_factory=list)
    
    tong_tien_so: str = Field("0", description="Tổng tiền đề nghị thanh toán bằng số")
    tong_tien_chu_viet: Optional[str] = Field("", description="Tổng tiền bằng chữ tiếng Việt")
    tong_tien_chu_trung: Optional[str] = Field("", description="Tổng tiền bằng chữ tiếng Trung đại tả")
    
    tai_khoan: BankInfo = Field(default_factory=BankInfo)
    danh_sach_dinh_kem: List[str] = Field(default_factory=lambda: [
        "DXYCTT 32.500.000 & 5.508.000.pdf",
        "Bản scan Biên bản nghiệm thu và bàn giao (驗收暨移交使用確認書)",
        "Hóa đơn giá trị gia tăng điện tử (VAT)"
    ], description="Danh sách tệp đính kèm")
    
    email_nguoi_gui: str = Field("pm02@hongming-global.com", description="Email người gửi đại diện Hong Ming")
    tieu_de_email: Optional[str] = Field("", description="Tiêu đề email")
    loi_chao_trung: Optional[str] = Field("敬啟者 CX Technology (VN) 您好：", description="Lời chào tiếng Trung")
    loi_chao_viet: Optional[str] = Field("Kính gửi Quý Công ty CX Technology (VN),", description="Lời chào tiếng Việt")
    
    nguoi_lap_phieu: str = Field("PM Hong Ming Global", description="Người lập phiếu")
    tong_giam_doc: str = Field("TANG WEI LI", description="Tổng Giám Đốc đại diện")


class ReminderAIParseRequest(BaseModel):
    """Request payload for Gemini AI to parse payment/reminder notes."""
    model_config = {"protected_namespaces": ()}
    raw_text: str = Field(..., description="Văn bản cần phân tích bóc tách (Email, tin nhắn, danh bạ, chỉ thị)")
    model_name: Optional[str] = Field(None, description="Tên mô hình Gemini ưu tiên")
    contract_code: Optional[str] = Field(None, description="Mã hợp đồng cần đối chiếu nếu có")
    milestone_name: Optional[str] = Field(None, description="Tên đợt thanh toán cần đối chiếu nếu có")
    match_contract: Optional[bool] = Field(True, description="Có đối chiếu với dữ liệu hợp đồng trong SQLite không")



class GmailDraftRequest(BaseModel):
    """Request payload to create a Gmail draft."""
    to: List[str] = Field(..., description="Danh sách email nhận chính")
    cc: Optional[List[str]] = Field(default_factory=list, description="Danh sách email CC")
    bcc: Optional[List[str]] = Field(default_factory=list, description="Danh sách email BCC")
    subject: str = Field(..., description="Tiêu đề email")
    body: str = Field(..., description="Nội dung email dạng text/plain")
    html_body: Optional[str] = Field("", description="Nội dung email dạng HTML")
    attachments: Optional[List[str]] = Field(default_factory=list, description="Danh sách đường dẫn tệp đính kèm")


class GmailSendRequest(BaseModel):
    """Request payload to send an email via Gmail."""
    to: List[str] = Field(..., description="Danh sách email nhận chính")
    cc: Optional[List[str]] = Field(default_factory=list, description="Danh sách email CC")
    bcc: Optional[List[str]] = Field(default_factory=list, description="Danh sách email BCC")
    subject: str = Field(..., description="Tiêu đề email")
    body: str = Field(..., description="Nội dung email dạng text/plain")
    html_body: Optional[str] = Field("", description="Nội dung email dạng HTML")
    attachments: Optional[List[str]] = Field(default_factory=list, description="Danh sách đường dẫn tệp đính kèm")


class DriveSearchRequest(BaseModel):
    """Request payload to search Google Drive files."""
    query: str = Field(..., description="Tên tệp hoặc từ khóa cần tìm kiếm trên Google Drive")
