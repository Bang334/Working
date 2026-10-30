# CẤU TRÚC THÀNH PHẦN EMAIL & MÔ HÌNH DỮ LIỆU ĐỂ TÍCH HỢP HỆ THỐNG (MAIL SYSTEM INTEGRATION GUIDE)

Tài liệu này chuẩn hóa toàn bộ các **thành phần (fields/components)** của từng loại email giao dịch thực tế tại Hong Ming Global. Mục tiêu giúp lập trình viên và AI dễ dàng tích hợp module gửi/nhận/xử lý mail tự động vào hệ thống Backend (FastAPI, Flask, Node.js, ERP/CRM).

---

## 1. MÔ HÌNH THÀNH PHẦN TỔNG QUÁT CỦA MỘT EMAIL (UNIVERSAL EMAIL SCHEMA)

Mọi email nghiệp vụ trong hệ thống B2B của Hong Ming đều tuân thủ cấu trúc 7 khối thành phần chuẩn:

```
+--------------------------------------------------------------------------------------------------+
| 1. HEADER / ENVELOPE (Phong bì & Siêu dữ liệu)                                                  |
|    - To, CC, BCC, Subject (Song ngữ), Sender, Mail Type, Thread ID                               |
+--------------------------------------------------------------------------------------------------+
| 2. GREETING & SALUTATION (Lời chào trang trọng)                                                 |
|    - Tên công ty khách hàng, Bộ phận tiếp nhận (Kế toán, Kỹ thuật, Mua hàng), Tên đại diện      |
+--------------------------------------------------------------------------------------------------+
| 3. CONTEXT & REFERENCE (Căn cứ & Dẫn chiếu)                                                     |
|    - Số Hợp Đồng, Mã Báo Giá, Tên Dự Án, Ngày ký kết, Lịch sử cuộc họp/trao đổi                 |
+--------------------------------------------------------------------------------------------------+
| 4. CORE DATA PAYLOAD (Bảng dữ liệu hạt nhân - Key/Value)                                        |
|    - Tùy loại mail: Số tiền, Tỷ lệ %, Thuế VAT, Hạn chót, Model thiết bị, Serial Number, STK ngân hàng|
+--------------------------------------------------------------------------------------------------+
| 5. CALL TO ACTION (CTA) & NEXT STEPS (Hành động yêu cầu)                                        |
|    - Ký xác nhận HĐ, Chuyển khoản giải ngân, Gửi điện chuyển tiền (UNC), Thu hồi pin lỗi        |
+--------------------------------------------------------------------------------------------------+
| 6. ATTACHMENT MANIFEST (Danh mục tệp đính kèm)                                                  |
|    - Tên file, loại file, kích thước, cờ bắt buộc (required: true), mục đích file               |
+--------------------------------------------------------------------------------------------------+
| 7. SIGN-OFF & ENTERPRISE SIGNATURE (Chữ ký doanh nghiệp)                                        |
|    - Thông tin PM đại diện, Phòng ban, Hotline, Email công ty, MST, Địa chỉ pháp nhân           |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. BẢNG PHÂN TÍCH THÀNH PHẦN CHI TIẾT THEO TỪNG LOẠI MAIL

Dưới đây là đặc tả các trường dữ liệu bắt buộc (Required Fields) và tệp đính kèm tương ứng cho 7 nghiệp vụ cốt lõi:

### 1. Mail Báo Giá Dự Án / Thiết Bị (Quotation Mail)
* **Mã loại nghiệp vụ (Type):** `QUOTATION`
* **Dữ liệu hạt nhân cần truyền vào hệ thống:**
  - `customer_name`: Tên pháp nhân khách hàng (VD: CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN))
  - `project_name`: Tên dự án (VD: Hệ thống giám sát điện năng EMS Nhà máy 2)
  - `validity_days`: Thời hạn hiệu lực báo giá (VD: 30 ngày)
  - `lead_time`: Thời gian giao hàng cam kết (VD: 15-20 ngày sau khi nhận cọc)
  - `warranty_months`: Thời hạn bảo hành (VD: 12 tháng)
  - `total_estimated_amount`: Tổng giá trị dự kiến (VNĐ hoặc USD)
* **File đính kèm bắt buộc (Attachments):**
  - File bảng tính Excel báo giá chi tiết (`.xlsx`) - Tạo theo chuẩn 1:1.
  - File tài liệu thông số kỹ thuật Catalog/Datasheet thiết bị (`.pdf`).

---

### 2. Mail Gửi Dự Thảo Hợp Đồng (Contract Draft Mail)
* **Mã loại nghiệp vụ (Type):** `CONTRACT_DRAFT`
* **Dữ liệu hạt nhân cần truyền vào hệ thống:**
  - `contract_number`: Số hợp đồng (VD: `HMV22092026SY0001`)
  - `contract_type`: Loại HĐ (`Mua bán thiết bị`, `Sửa chữa`, `Hợp đồng nguyên tắc`)
  - `contract_value`: Giá trị hợp đồng trước thuế (VNĐ)
  - `vat_rate`: Thuế suất VAT (8% hoặc 10%)
  - `total_with_vat`: Tổng giá trị thanh toán đã gồm thuế
  - `payment_schedule`: Danh sách các đợt thanh toán (`[{"installment": 1, "pct": 30}, {"installment": 2, "pct": 40}, {"installment": 3, "pct": 30}]`)
  - `feedback_deadline`: Hạn chót phản hồi xác nhận dự thảo
* **File đính kèm bắt buộc (Attachments):**
  - File bản thảo Hợp đồng kinh tế song ngữ (`.pdf` hoặc `.docx`).
  - File Hợp đồng nguyên tắc (`.pdf` - nếu áp dụng hợp tác dài hạn).
  - Phụ lục kỹ thuật / Danh mục BOM thiết bị.

---

### 3. Mail Đề Nghị Thanh Toán Theo Đợt (Payment Request Mail)
* **Mã loại nghiệp vụ (Type):** `PAYMENT_REQUEST`
* **Dữ liệu hạt nhân cần truyền vào hệ thống:**
  - `contract_number`: Số hợp đồng tham chiếu
  - `project_name`: Tên dự án / Gói thầu
  - `installment_name`: Tên đợt (VD: `Đợt 1 - Tạm ứng đặt cọc 30%`, `Giai đoạn 3 - Nghiệm thu đạt 20%`)
  - `installment_percentage`: Tỷ lệ % thanh toán (VD: `30%`, `20%`)
  - `contract_total_amount`: Tổng giá trị hợp đồng (VNĐ)
  - `requested_amount`: Số tiền đề nghị thanh toán bằng số (VNĐ)
  - `requested_amount_words_vn`: Số tiền bằng chữ tiếng Việt
  - `requested_amount_words_cn`: Số tiền bằng chữ tiếng Trung (Phồn thể)
  - `due_date`: Hạn thanh toán (Ngày/Tháng/Năm)
  - `bank_name`, `bank_account_number`, `bank_account_holder`: Thông tin tài khoản thụ hưởng của Hong Ming
* **File đính kèm bắt buộc (Attachments):**
  - File PDF ghép gộp **Đơn yêu cầu thanh toán (DYCTT) + Biên bản nghiệm thu (BBNT)** có đủ chữ ký 2 bên (`DYCTT_BBNT_[SoTien]_[MaHD].pdf`).

---

### 4. Mail Gửi Hóa Đơn Điện Tử GTGT (E-Invoice Mail)
* **Mã loại nghiệp vụ (Type):** `INVOICE_DELIVERY`
* **Dữ liệu hạt nhân cần truyền vào hệ thống:**
  - `buyer_tax_code`: Mã số thuế bên mua
  - `buyer_company_name`: Tên công ty bên mua
  - `invoice_symbol`: Ký hiệu hóa đơn (VD: `1C26THM`)
  - `invoice_number`: Số hóa đơn điện tử (VD: `00000023`)
  - `issue_date`: Ngày lập hóa đơn
  - `subtotal_amount`: Tiền hàng trước thuế
  - `vat_rate`, `vat_amount`: Thuế suất và tiền thuế GTGT
  - `total_invoice_amount`: Tổng tiền thanh toán đã gồm thuế
  - `lookup_url`: Đường link portal tra cứu hóa đơn trực tuyến
  - `lookup_code`: Mã bảo mật tra cứu hóa đơn
* **File đính kèm bắt buộc (Attachments):**
  - Bản thể hiện Hóa đơn điện tử PDF (`.pdf`).
  - File dữ liệu gốc hóa đơn XML (`.xml`) hợp chuẩn Cục Thuế.

---

### 5. Mail Đôn Đốc Công Nợ & Quyết Toán Cuối Kỳ (Debt Collection Mail)
* **Mã loại nghiệp vụ (Type):** `DEBT_REMINDER`
* **Dữ liệu hạt nhân cần truyền vào hệ thống:**
  - `reminder_level`: Cấp độ nhắc nợ (`LEVEL_1_GENTLE`, `LEVEL_2_URGENT_10PCT_RETAINAGE`, `LEVEL_3_FORMAL_NOTICE`)
  - `unpaid_contracts`: Mảng danh sách các Hợp đồng còn nợ:
    * `contract_no`: Số hợp đồng
    * `contract_title`: Tên hạng mục
    * `retainage_pct`: Tỷ lệ nợ còn lại (thường là 10% 尾款)
    * `debt_amount`: Số tiền nợ (VNĐ)
  - `total_debt_amount`: Tổng số tiền nợ cộng dồn
  - `overdue_days`: Số ngày quá hạn thanh toán
  - `payment_deadline`: Hạn chót yêu cầu chuyển khoản
  - `banking_info`: Thông tin tài khoản nhận tiền
* **File đính kèm bắt buộc (Attachments):**
  - Bảng kê đối chiếu công nợ chi tiết (Statement of Account - SOA).
  - Bản sao các hóa đơn GTGT / BBNT chưa quyết toán.
  - Thư nhắc nợ có dấu đỏ (nếu ở cấp độ 3).

---

### 6. Mail Nghiệm Thu Hoàn Tất & Video Hiện Trường (Acceptance & Handover Mail)
* **Mã loại nghiệp vụ (Type):** `ACCEPTANCE_HANDOVER`
* **Dữ liệu hạt nhân cần truyền vào hệ thống:**
  - `contract_number`: Số hợp đồng tham chiếu
  - `repair_ticket_id`: Mã phiếu sửa chữa / Mã dự án (VD: `HM-FINEPRO-20261009.001`)
  - `completion_date`: Ngày hoàn thành thi công/sửa chữa
  - `device_list`: Danh sách thiết bị (Tên máy, Model, Serial Number)
  - `test_result`: Trạng thái kiểm tra (Đạt 100% / Chạy thử nghiệm thu thành công)
  - `payment_request_included`: Cờ boolean có gửi kèm Phiếu yêu cầu thanh toán hay không
* **File đính kèm bắt buộc (Attachments):**
  - File bảng tính Excel / PDF Biên bản nghiệm thu kiểm tra thiết bị (`.xlsx` / `.pdf`).
  - File video / hình ảnh bằng chứng thiết bị chạy bình thường sau sửa chữa (`.mp4`, `.jpg`).
  - File Phiếu yêu cầu thanh toán chi phí sửa chữa / hoàn thành giai đoạn.

---

### 7. Mail Xử Lý Sự Cố & Khiếu Nại Bảo Hành RMA (RMA Defect Report Mail)
* **Mã loại nghiệp vụ (Type):** `RMA_DEFECT_REPORT`
* **Dữ liệu hạt nhân cần truyền vào hệ thống:**
  - `defect_description`: Mô tả chi tiết hiện tượng lỗi (VD: `8 viên pin máy tính bảng bị phồng rộp khi sạc dock`)
  - `incident_date`: Thời điểm phát hiện lỗi
  - `affected_quantity`: Số lượng linh kiện bị lỗi
  - `device_models`: Model và Serial Numbers của các thiết bị lỗi
  - `root_cause_analysis`: Nguyên nhân kỹ thuật từ Hãng (RCA)
  - `resolution_action`: Phương án xử lý (Đổi mới trong 3-5 ngày, hỗ trợ tận nơi)
  - `prevention_guide`: Khuyến nghị vận hành để tránh tái diễn
* **File đính kèm bắt buộc (Attachments):**
  - Ảnh chụp lỗi thực tế hiện trường kèm tem nhãn S/N và tem bảo hành.
  - Biên bản kiểm tra sự cố hiện trường có chữ ký xác nhận của quản đốc phân xưởng.
  - Datasheet thiết bị công nghiệp thay thế được Hãng khuyến nghị.

---

## 3. THIẾT KẾ CSDL (DATABASE ENTITY) ĐỂ QUẢN LÝ EMAIL TRONG HỆ THỐNG

Khi thiết kế cơ sở dữ liệu (PostgreSQL / SQLite / MySQL), có thể dùng bảng `emails` và `email_attachments` như sau:

```sql
-- Bảng quản lý Email giao dịch
CREATE TABLE project_emails (
    id VARCHAR(36) PRIMARY KEY,                   -- UUID
    project_id VARCHAR(50) NOT NULL,              -- Mã dự án liên quan
    contract_number VARCHAR(50),                  -- Số hợp đồng tham chiếu
    email_type VARCHAR(30) NOT NULL,              -- QUOTATION, CONTRACT_DRAFT, PAYMENT_REQUEST, INVOICE, DEBT_REMINDER, ACCEPTANCE, RMA
    direction VARCHAR(10) NOT NULL,               -- OUTBOUND (Gửi đi) hoặc INBOUND (Nhận về)
    sender VARCHAR(255) NOT NULL,                 -- Email người gửi
    recipients_to TEXT NOT NULL,                  -- Danh sách email người nhận (JSON array)
    recipients_cc TEXT,                           -- Danh sách CC (JSON array)
    subject VARCHAR(500) NOT NULL,                -- Tiêu đề song ngữ
    body_html TEXT NOT NULL,                      -- Nội dung định dạng Rich Text / HTML
    body_plain TEXT,                              -- Nội dung văn bản thuần
    currency VARCHAR(10) DEFAULT 'VND',           -- VND hoặc USD
    amount NUMERIC(15, 2),                        -- Số tiền liên quan đến email (nếu có)
    due_date DATE,                                -- Hạn thanh toán / Hạn phản hồi
    status VARCHAR(20) DEFAULT 'DRAFT',           -- DRAFT, QUEUED, SENT, DELIVERED, OPENED, REPLIED, FAILED
    error_message TEXT,                           -- Ghi nhận lỗi gửi nếu có
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

-- Bảng quản lý tệp đính kèm theo Email
CREATE TABLE email_attachments (
    id VARCHAR(36) PRIMARY KEY,                   -- UUID
    email_id VARCHAR(36) REFERENCES project_emails(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,              -- Tên file (VD: DYCTT_BBNT_46.800.000.pdf)
    file_path VARCHAR(500) NOT NULL,              -- Đường dẫn vật lý trên server / S3
    file_type VARCHAR(50) NOT NULL,               -- PDF, EXCEL, XML, IMAGE, VIDEO
    file_size_bytes BIGINT,                       -- Dung lượng file
    is_required BOOLEAN DEFAULT TRUE              -- Có phải file nghiệp vụ bắt buộc hay không
);
```
