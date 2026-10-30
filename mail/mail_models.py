"""
HỆ THỐNG MÔ HÌNH DỮ LIỆU EMAIL CHUẨN HÓA (HONG MING PM HUB - MAIL MODELS)
Định nghĩa Pydantic models cho toàn bộ các dạng email giao dịch B2B thực tế tại Hong Ming Global.
Hỗ trợ sinh nội dung Rich Text song ngữ Việt - Trung và tự động kiểm tra file đính kèm bắt buộc.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field


class EmailType(str, Enum):
    QUOTATION = "QUOTATION"                              # Báo giá thiết bị / Giải pháp IoT
    CONTRACT_DRAFT = "CONTRACT_DRAFT"                    # Gửi dự thảo HĐ kinh tế / HĐ nguyên tắc
    PAYMENT_REQUEST = "PAYMENT_REQUEST"                  # Đề nghị thanh toán theo đợt (Cọc 30%, Giao hàng 40%, Nghiệm thu 20%)
    INVOICE_DELIVERY = "INVOICE_DELIVERY"                # Gửi hóa đơn GTGT điện tử (PDF + XML)
    DEBT_REMINDER = "DEBT_REMINDER"                      # Đôn đốc công nợ / Nhắc 10% quyết toán cuối
    ACCEPTANCE_HANDOVER = "ACCEPTANCE_HANDOVER"          # Nghiệm thu hoàn tất & Gửi video/ảnh hiện trường
    RMA_DEFECT_REPORT = "RMA_DEFECT_REPORT"              # Xử lý sự cố, bảo hành & khiếu nại RMA
    TECHNICAL_CLARIFICATION = "TECHNICAL_CLARIFICATION"  # Giải trình kỹ thuật & Kế hoạch thi công
    CUSTOMS_CLEARANCE = "CUSTOMS_CLEARANCE"              # Gửi bộ chứng từ hải quan xuất nhập khẩu tại chỗ (KCX EPE)
    PURCHASE_ORDER = "PURCHASE_ORDER"                    # Tiếp nhận & Xác nhận Đơn đặt hàng (PO)


class AttachmentItem(BaseModel):
    file_name: str
    file_type: str = Field(..., description="PDF, EXCEL, XML, IMAGE, VIDEO")
    file_path: Optional[str] = None
    is_required: bool = True
    description: Optional[str] = None


class BaseEmailPayload(BaseModel):
    email_type: EmailType
    customer_company_name: str
    department_or_recipient: str = "Ban Giám đốc & Phòng Ban Liên quan"
    recipient_email: str
    cc_emails: List[str] = []
    project_name: str
    contract_number: Optional[str] = None
    attachments: List[AttachmentItem] = []


# =====================================================================
# 1. MẪU DỮ LIỆU BÁO GIÁ (QUOTATION PAYLOAD)
# =====================================================================
class QuotationPayload(BaseEmailPayload):
    email_type: EmailType = EmailType.QUOTATION
    summary_items: str = Field(..., description="Tóm tắt danh mục cung cấp chính")
    lead_time_days: str = "15 - 20 ngày kể từ ngày nhận đủ tiền cọc"
    warranty_months: int = 12
    validity_days: int = 30
    total_amount_estimate: Optional[float] = None
    currency: str = "VND"

    def render_body(self) -> str:
        return f"""Kính gửi Quý Công ty {self.customer_company_name} / {self.department_or_recipient},
敬致 {self.customer_company_name} / {self.department_or_recipient}：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng đến Quý Công ty.
宏明環球有限公司謹向貴公司致以誠摯的問候。

Căn cứ vào nhu cầu thực tế và buổi trao đổi kỹ thuật về dự án {self.project_name}, Hong Ming xin trân trọng gửi đến Quý Công ty bảng báo giá chi tiết và hồ sơ kỹ thuật kèm theo.
根據貴公司實際需求及雙方就 {self.project_name} 之技術討論，宏明環球特此檢附詳細報價單及相關技術資料供貴公司審閱。

Thông tin báo giá tóm tắt / 報價項目摘要：
* Hạng mục cung cấp / 供應項目: {self.summary_items}
* Thời gian giao hàng dự kiến / 預計交期: {self.lead_time_days}
* Thời hạn bảo hành / 保固期限: {self.warranty_months} tháng kể từ ngày nghiệm thu bàn giao / 驗收移交日起保固 {self.warranty_months} 個月
* Hiệu lực báo giá / 報價有效期限: {self.validity_days} ngày kể từ ngày phát hành / 自發行日起 {self.validity_days} 天內有效

Chi tiết danh mục thiết bị, đơn giá và điều khoản thương mại, kính mời Quý Công ty xem file đính kèm.

Trân trọng / 敬上,
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
Hotline: +84 966 687 109 | Email: sales@hongming-global.com
"""


# =====================================================================
# 2. MẪU DỮ LIỆU ĐỀ NGHỊ THANH TOÁN (PAYMENT REQUEST PAYLOAD)
# =====================================================================
class PaymentRequestPayload(BaseEmailPayload):
    email_type: EmailType = EmailType.PAYMENT_REQUEST
    installment_title: str = Field(..., description="VD: Đợt 1 - Tạm ứng đặt cọc 30% / Giai đoạn 3 - Nghiệm thu 20%")
    installment_percentage: str = "30%"
    requested_amount_num: float
    requested_amount_words_vn: str
    requested_amount_words_cn: str
    due_date: str = Field(..., description="DD/MM/YYYY")
    bank_account_no: str = "0011004123456"
    bank_name: str = "Ngân hàng TNHH MTV Cathay United Bank - Chi nhánh TP.HCM"

    def render_body(self) -> str:
        amount_formatted = f"{self.requested_amount_num:,.0f} VNĐ"
        return f"""Kính gửi Quý Công ty {self.customer_company_name} / {self.department_or_recipient},
敬致 {self.customer_company_name} / {self.department_or_recipient}：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng đến Quý Công ty.
宏明環球有限公司謹向貴公司致以誠摯的問候。

Hong Ming xin trân trọng gửi đến Quý Công ty hồ sơ đề nghị thanh toán {self.installment_title} theo Hợp đồng số {self.contract_number}, liên quan đến dự án {self.project_name}.
宏明環球茲檢附合約編號 {self.contract_number} 之 {self.installment_title} 付款申請文件，相關項目為 {self.project_name}。

Thông tin thanh toán / 付款資訊：
* Số hợp đồng / 合約編號: {self.contract_number}
* Nội dung thanh toán / 付款項目: {self.installment_title}
* Tỷ lệ thanh toán / 付款比例: {self.installment_percentage}
* Số tiền thanh toán / 付款金額: {amount_formatted}
  (Bằng chữ: {self.requested_amount_words_vn} / 大寫: {self.requested_amount_words_cn})
* Hạn thanh toán / 付款截止日期: {self.due_date}

Tài khoản thụ hưởng của Hong Ming / 宏明環球收款帳號資訊：
* Tên tài khoản / 戶名: CÔNG TY TNHH TOÀN CẦU HONG MING
* Số tài khoản / 帳號: {self.bank_account_no}
* Ngân hàng thụ hưởng / 開戶行: {self.bank_name}

Hồ sơ chứng từ đính kèm / 檢附請款文件: Đơn yêu cầu thanh toán & Biên bản nghiệm thu đã được đại diện hai bên ký xác nhận.
Kính nhờ Quý Công ty sắp xếp chuyển khoản đúng hạn và phản hồi ủy nhiệm chi vào email này.

Trân trọng / 敬上,
Bộ phận Quản lý Dự án & Kế toán / 專案部暨財務會計部
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
"""


# =====================================================================
# 3. MẪU DỮ LIỆU GỬI HÓA ĐƠN GTGT (INVOICE PAYLOAD)
# =====================================================================
class InvoiceDeliveryPayload(BaseEmailPayload):
    email_type: EmailType = EmailType.INVOICE_DELIVERY
    buyer_tax_code: str
    invoice_symbol: str = "1C26THM"
    invoice_number: str
    issue_date: str
    total_amount_with_vat: float
    total_amount_words_vn: str
    total_amount_words_cn: str
    lookup_portal: str = "https://tracuu.minvoice.vn"
    lookup_code: str

    def render_body(self) -> str:
        amount_formatted = f"{self.total_amount_with_vat:,.0f} VNĐ"
        return f"""Kính gửi: Quý Công ty {self.customer_company_name} / {self.department_or_recipient},
敬致：{self.customer_company_name} / {self.department_or_recipient}：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng đến Quý Công ty.
宏明環球有限公司謹向貴公司致以誠摯的問候。

Căn cứ vào Hợp đồng số {self.contract_number} và biên bản nghiệm thu đã hoàn tất, Hong Ming xin trân trọng gửi đến Quý Công ty hóa đơn giá trị gia tăng điện tử với chi tiết như sau:
依據雙方簽署之合約編號 {self.contract_number} 及已完成之驗收確認書，宏明環球特此檢附電子增值稅發票，明細如下：

Thông tin hóa đơn chi tiết / 發票詳細明細：
* Tên bên mua / 買方公司抬頭: {self.customer_company_name}
* Mã số thuế / 稅號: {self.buyer_tax_code}
* Ký hiệu hóa đơn / 發票符號: {self.invoice_symbol}
* Số hóa đơn / 發票號碼: {self.invoice_number}
* Ngày lập hóa đơn / 開票日期: {self.issue_date}
* Tổng tiền thanh toán / 總含稅金額: {amount_formatted}
  (Bằng chữ: {self.total_amount_words_vn} / 大寫: {self.total_amount_words_cn})

Tra cứu hóa đơn trực tuyến / 線上發票查驗資訊：
* Trang tra cứu / 查驗網址: {self.lookup_portal}
* Mã số tra cứu bí mật / 查驗碼: {self.lookup_code}

Tài liệu đính kèm gồm: File PDF bản thể hiện và File XML dữ liệu gốc hóa đơn điện tử.

Trân trọng / 敬上,
Bộ phận Kế toán & Hóa đơn / 財務會計暨發票小組
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
"""


# =====================================================================
# 4. MẪU DỮ LIỆU BỘ CHỨNG TỪ HẢI QUAN EPE (CUSTOMS CLEARANCE PAYLOAD)
# =====================================================================
class CustomsClearancePayload(BaseEmailPayload):
    email_type: EmailType = EmailType.CUSTOMS_CLEARANCE
    items_description: str = Field(..., description="VD: 300 PCS thẻ RFID chịu nhiệt")
    customs_declaration_no: str = Field(..., description="Số tờ khai hải quan")
    clearance_status: str = "Đã thông quan xuất khẩu tại chỗ"
    delivery_readiness_question: str = "Xác nhận thời gian giao hàng vào kho"

    def render_body(self) -> str:
        return f"""Kính gửi: Quý Công ty {self.customer_company_name} / Bộ phận Xuất Nhập Khẩu & Thủ Kho,
敬致 {self.customer_company_name} / 進出口物流部暨倉庫管理組：

Hong Ming xin thông báo lô hàng {self.items_description} theo Hợp đồng số {self.contract_number} đã được Chi cục Hải quan hoàn tất thủ tục {self.clearance_status} (Số tờ khai: {self.customs_declaration_no}).
宏明謹通知合約編號 {self.contract_number} 項下 {self.items_description} 之廠內出口報關手續已全數通關完成（報關單號：{self.customs_declaration_no}）。

Hong Ming xin gửi kèm trọn bộ chứng từ hải quan (Hóa đơn thương mại, Packing List, Hóa đơn GTGT, Tờ khai xuất khẩu) để Quý Công ty tiến hành mở tờ khai nhập khẩu đối ứng.
宏明特此檢附完整海關通關憑證，以利貴司辦理對應之進口報關單申報手續。

Kính nhờ Quý Công ty phản hồi xác nhận kế hoạch nhận hàng tại nhà máy (ngày giờ cụ thể) để chúng tôi kịp thời bố trí nhân sự và phương tiện vận chuyển bàn giao hàng hóa thuận lợi.

Trân trọng / 敬上,
Bộ phận Xuất Nhập Khẩu & Kế toán / 進出口暨財務會計組
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
"""


# =====================================================================
# 5. MẪU DỮ LIỆU ĐƠN HÀNG PO (PURCHASE ORDER PAYLOAD)
# =====================================================================
class PurchaseOrderPayload(BaseEmailPayload):
    email_type: EmailType = EmailType.PURCHASE_ORDER
    po_number: str = Field(..., description="Số PO của khách hàng")
    po_date: str = Field(..., description="Ngày phát hành PO")
    items_summary: str = Field(..., description="Danh mục sản phẩm/dịch vụ trong PO")
    quantity: int
    total_po_amount: float
    estimated_lead_time: str = "05 - 07 ngày làm việc"

    def render_body(self) -> str:
        amount_formatted = f"{self.total_po_amount:,.0f} VNĐ"
        return f"""Kính gửi: Quý Công ty {self.customer_company_name} / {self.department_or_recipient},
敬致 {self.customer_company_name} / {self.department_or_recipient}：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng đến Quý Công ty.
宏明環球有限公司謹向貴公司致以誠摯的問候。

Chúng tôi xin xác nhận đã nhận được Đơn đặt hàng (Purchase Order) số {self.po_number} phát hành ngày {self.po_date}, áp dụng cho {self.items_summary}.
我司確認已收到貴公司於 {self.po_date} 開立之採購訂單編號 {self.po_number}，相關項目為 {self.items_summary}。

Chi tiết đơn hàng đã xác nhận / 訂單確認詳細資訊：
* Số PO khách hàng / 客戶 PO 編號: {self.po_number}
* Hạng mục thực hiện / 執行項目: {self.items_summary}
* Số lượng thiết bị / 數量: {self.quantity}
* Tổng giá trị đơn hàng / 訂單總含稅金額: {amount_formatted}
* Thời gian hoàn thành dự kiến / 預計完工或交貨交期: Trong vòng {self.estimated_lead_time}

Đội ngũ kỹ thuật của Hong Ming đã chính thức đưa lô thiết bị vào quy trình triển khai theo đúng tiêu chuẩn cam kết.

Trân trọng / 敬上,
Bộ phận Dịch vụ Khách hàng & Quản lý Đơn hàng / 客戶服務暨訂單管理組
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
"""


# =====================================================================
# 6. HÀM KIỂM TRA FILE ĐÍNH KÈM BẮT BUỘC (VALIDATOR)
# =====================================================================
def validate_email_attachments(payload: BaseEmailPayload) -> List[str]:
    """Kiểm tra xem email đã có đủ các loại file đính kèm bắt buộc theo quy định chưa."""
    missing_warnings = []
    filenames = [att.file_name.lower() for att in payload.attachments]
    
    if payload.email_type == EmailType.QUOTATION:
        if not any(f.endswith(('.xlsx', '.xls', '.pdf')) for f in filenames):
            missing_warnings.append("Cảnh báo: Email Báo giá bắt buộc phải có file bảng tính (.xlsx) hoặc PDF báo giá!")
            
    elif payload.email_type == EmailType.PAYMENT_REQUEST:
        if not any(f.endswith('.pdf') for f in filenames):
            missing_warnings.append("Cảnh báo: Email Đề nghị thanh toán bắt buộc phải đính kèm file PDF Đơn yêu cầu thanh toán (DYCTT) và BBNT!")
            
    elif payload.email_type == EmailType.INVOICE_DELIVERY:
        has_pdf = any(f.endswith('.pdf') for f in filenames)
        has_xml = any(f.endswith('.xml') for f in filenames)
        if not has_pdf:
            missing_warnings.append("Cảnh báo: Email gửi hóa đơn thiếu file PDF bản thể hiện hóa đơn!")
        if not has_xml:
            missing_warnings.append("Cảnh báo: Email gửi hóa đơn thiếu file XML dữ liệu gốc theo quy định Tổng cục Thuế!")

    elif payload.email_type == EmailType.ACCEPTANCE_HANDOVER:
        if not any(f.endswith(('.xlsx', '.pdf')) for f in filenames):
            missing_warnings.append("Cảnh báo: Email Nghiệm thu hoàn tất thiếu Biên bản kiểm tra / nghiệm thu (.xlsx/.pdf)!")

    elif payload.email_type == EmailType.CUSTOMS_CLEARANCE:
        has_pdf = any(f.endswith('.pdf') for f in filenames)
        if not has_pdf:
            missing_warnings.append("Cảnh báo: Email Bộ chứng từ hải quan thiếu file PDF Tờ khai hải quan / Commercial Invoice!")

    elif payload.email_type == EmailType.PURCHASE_ORDER:
        if not any(f.endswith(('.pdf', '.xlsx', '.xls')) for f in filenames):
            missing_warnings.append("Cảnh báo: Email Đơn hàng PO thiếu file đính kèm PO của khách hàng!")

    return missing_warnings
