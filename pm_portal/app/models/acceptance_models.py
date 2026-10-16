"""Acceptance minute data models using Pydantic."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AcceptanceParty(BaseModel):
    """Party info for acceptance document."""
    ten_cong_ty: str = Field(..., description="Tên công ty tiếng Việt")
    ten_tieng_trung: Optional[str] = Field("", description="Tên công ty tiếng Trung (Phồn thể)")
    dia_chi: Optional[str] = Field("", description="Địa chỉ tiếng Việt")
    dia_chi_trung: Optional[str] = Field("", description="Địa chỉ tiếng Trung")
    mst: Optional[str] = Field("", description="Mã số thuế")
    nguoi_dai_dien: Optional[str] = Field("", description="Họ và tên người đại diện")
    chuc_vu: Optional[str] = Field("", description="Chức vụ tiếng Việt")
    chuc_vu_trung: Optional[str] = Field("", description="Chức vụ tiếng Trung")


class AcceptanceItem(BaseModel):
    """Line item in equipment repair or acceptance list."""
    stt: int = Field(..., description="Số thứ tự")
    serial_number: str = Field(..., description="Serial Number / Mã định danh thiết bị")
    loi_ban_dau: str = Field(..., description="Lỗi ban đầu / 故障說明")
    bo_phan: str = Field("CNC", description="Bộ phận gửi sửa / 部門")
    hang_muc_kiem_tra: str = Field(..., description="Hạng mục kiểm tra & xử lý / 檢查項目")
    ket_qua: str = Field("Đạt / 合格", description="Kết quả kiểm tra / 結果")
    sheet_anh: Optional[str] = Field("", description="Tên sheet hình ảnh hoặc ghi chú")
    don_gia: Optional[str] = Field("", description="Đơn giá (nếu có)")
    tong_gia: Optional[str] = Field("", description="Tổng giá (nếu có)")
    can_anh: Optional[bool] = Field(False, description="Tạo sheet hình ảnh chi tiết cho thiết bị này")


class AcceptanceData(BaseModel):
    """Full acceptance minutes schema matching Hong Ming Global standard."""
    loai_nghiem_thu: str = Field("thiet_bi", description="thiet_bi (sửa chữa thiết bị) hoặc du_an (nghiệm thu mốc hợp đồng)")
    tieu_de_viet: str = Field(
        "BIÊN BẢN KIỂM TRA & NGHIỆM THU THIẾT BỊ SAU SỬA CHỮA",
        description="Tiêu đề tiếng Việt"
    )
    tieu_de_trung: str = Field(
        "維修設備檢查及驗收記錄",
        description="Tiêu đề tiếng Trung"
    )
    so_hop_dong: str = Field("HM-FINEPRO-20261009.001", description="Số HĐ hoặc Số PO")
    so_bien_ban: str = Field("001/2026/BBNT-SC", description="Số biên bản nghiệm thu")
    ngay_nghiem_thu: str = Field("09/10/2026", description="Ngày nghiệm thu (DD/MM/YYYY)")
    
    ben_a: AcceptanceParty
    ben_b: Optional[AcceptanceParty] = None
    
    hang_muc: List[AcceptanceItem] = Field(default_factory=list)
    tong_so_luong: Optional[str] = Field("6 Thiết bị", description="Tổng số lượng thiết bị")
    tong_tien_so: str = Field("13.700.000", description="Tổng giá trị bằng số")
    tong_tien_chu_viet: Optional[str] = Field("", description="Tổng tiền bằng chữ tiếng Việt")
    tong_tien_chu_trung: Optional[str] = Field("", description="Tổng tiền bằng chữ tiếng Trung")
    
    ghi_chu_1: Optional[str] = Field(
        "Thiết bị đã được kiểm tra chức năng, bảo trì/sửa chữa và chạy thử đạt tiêu chuẩn kỹ thuật trước khi bàn giao / 設備已完成功能檢查、維修更換零件並測試正常運作後交付。",
        description="Ghi chú mục 1"
    )
    ghi_chu_2: Optional[str] = Field("", description="Ghi chú mục 2 (tổng tiền)")
    ghi_chu_3: Optional[str] = Field(
        "Chi tiết kết quả kiểm tra & linh kiện thay thế / 檢驗結果與更換零件明細:\n   - STT 1, 4, 5, 6: Không phát hiện lỗi phát sinh thêm (No error founds) / 檢查未發現異常。\n   - STT 2 (EF550RA4LAWBHI677): Xử lý cụm Barcode / 檢修條碼掃描模組。\n   - STT 3 (RFR900NA55RSWLBA565): Thay thế Mounting Adapter / 更換轉接支架。",
        description="Ghi chú mục 3 (chi tiết linh kiện thay thế)"
    )
    tao_cac_sheet_anh: bool = Field(False, description="Tạo thêm các sheet placeholder ảnh cho từng thiết bị")


class AcceptanceAIParseRequest(BaseModel):
    """Request payload for Gemini AI to parse acceptance notes or delivery receipt."""
    model_config = {"protected_namespaces": ()}
    raw_text: str = Field(..., description="Văn bản thô, bảng giao nhận, ghi chú lỗi")
    model_name: Optional[str] = Field(None, description="Tên mô hình Gemini ưu tiên")
