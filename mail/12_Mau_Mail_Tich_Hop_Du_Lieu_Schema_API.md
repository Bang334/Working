# MẪU MAIL BÀN GIAO CẤU TRÚC DỮ LIỆU & TÍCH HỢP HỆ THỐNG IT/ERP (DATABASE SCHEMA & API INTEGRATION)

## 1. DẠNG MAIL NÀY DÙNG ĐỂ LÀM GÌ?
- Dành cho bộ phận Kỹ thuật phần mềm & Quản trị Dự án (PM) khi làm việc trực tiếp với phòng Công nghệ Thông tin (IT Department) của các tập đoàn sản xuất lớn (như CX Technology, Darfon, Vonmax).
- Phản hồi yêu cầu cung cấp **Cấu trúc bảng Cơ sở dữ liệu (Database Table Schema)** hoặc **Đặc tả giao diện lập trình ứng dụng (API Endpoints)** của hệ thống RFID / IIoT / MES Lite do Hong Ming triển khai, phục vụ mục đích:
  1. Khách hàng kết nối dữ liệu máy móc vào hệ thống Quản trị nguồn lực doanh nghiệp nội bộ (ERP TIPTOP, SAP, Oracle).
  2. Khách hàng tích hợp dữ liệu vào hệ thống Phân tích Trí tuệ nhân tạo (AI Machine Learning / Vision Inspection).
  3. Bàn giao quyền truy cập và tài liệu bảo mật kết nối mạng nội bộ (Internal LAN / SQL Server).

---

## 2. FILE ĐÍNH KÈM BẮT BUỘC (ATTACHMENTS)
Khi gửi email bàn giao cấu trúc dữ liệu và tích hợp kỹ thuật, **BẮT BUỘC** phải đính kèm:
1. **Bảng đặc tả cấu trúc bảng CSDL (Database Table Schema) (Bắt buộc):**
   - File Excel chuẩn: `[TenHeThong]_Database_Table_Schema.xlsx`.
   - Liệt kê chi tiết: Tên bảng (Table Name), Tên trường (Field Name), Kiểu dữ liệu (Data Type: VARCHAR, INT, DATETIME), Khóa chính (PK), Cho phép null, và Mô tả ý nghĩa nghiệp vụ (Tiếng Việt & Tiếng Trung).
2. **Tài liệu hướng dẫn kết nối & Câu lệnh truy vấn mẫu (Bắt buộc):**
   - File PDF: `Tai_Lieu_Ket_Noi_Du_Lieu_API_[TenKhachHang].pdf`.
   - Bao gồm: Thông số kết nối Server IP, Cổng Port, View hoặc Stored Procedure được cấp phép truy xuất, và câu lệnh SQL mẫu (`SELECT TOP 100 ...`).
3. **Mẫu dữ liệu thực tế (Sample Data Export) (Khuyến nghị):**
   - File CSV hoặc Excel chứa dữ liệu mẫu để đội lập trình của đối tác test import.

---

## 3. MẪU NỘI DUNG EMAIL CHUẨN (SONG NGỮ VIỆT - TRUNG)

**Tiêu đề:** Cung cấp Cấu trúc CSDL hệ thống [Tên hệ thống: ví dụ RFID / IoT] để tích hợp ERP/AI - CÔNG TY TNHH TOÀN CẦU HONG MING / 提供 [系統名稱] 資料庫 Table Schema 暨系統介接文件 – 宏明環球有限公司

---

**Nội dung:**

Kính gửi: Ban Quản lý CNTT (IT Department) - Quý Công ty [Tên công ty khách hàng],  
CC: Ban Quản lý Dự án nội bộ,  
敬致：[貴公司名稱] 資訊部（IT Department）專案團隊：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng đến Quý Bộ phận CNTT.  
宏明環球有限公司謹向貴司資訊團隊致以誠摯的問候。

Căn cứ vào yêu cầu của Quý Công ty về việc kết nối và trích xuất dữ liệu từ hệ thống [Tên hệ thống: ví dụ Hệ thống quét trạm RFID / Hệ thống giám sát điện năng EMS] để phục vụ việc tích hợp vào hệ thống ERP / AI của nhà máy, Hong Ming đã tổng hợp và xin trân trọng bàn giao bộ tài liệu cấu trúc CSDL chi tiết như sau:  
針對貴司提出未來導入 AI 系統及內部 ERP 系統介接之需求，宏明工程團隊已依貴司指定格式完成資料庫欄位整理，特此提供完整資料庫 Table Schema 規格文件如下：

**1. Thông tin kiến trúc CSDL / 資料庫架構環境資訊：**
* Hệ quản trị CSDL / 資料庫類型: Microsoft SQL Server [Phiên bản: ví dụ 2019 / 2022] (hoặc MySQL)
* Tên Database / 資料庫名稱: `[Ten_Database: ví dụ HM_RFID_PROD_DB]`
* Chế độ cấp phép truy cập / 授權模式: Cấp quyền đọc an toàn (Read-Only User) hoặc kết nối qua CSDL Trung gian (Staging View) để đảm bảo không ảnh hưởng đến hiệu năng ghi dữ liệu tức thời của trạm quét.

**2. Danh mục các bảng dữ liệu cốt lõi / 核心資料表清單：**
* `tbl_TagMaster`: Bảng danh mục thông tin mã thẻ RFID, loại pallet, phân loại sản phẩm.
* `tbl_StationLogs`: Bảng nhật ký quét thời gian thực (Mã trạm, Thời điểm vào/ra, Mã công nhân, Trạng thái đạt/lỗi OK-NG).
* `tbl_MachineStatus`: Bảng trạng thái vận hành của máy móc (Chạy, Dừng, Báo động lỗi Sóng hài/Quá tải).

**Tài liệu đính kèm theo thư / 隨信檢附技術檔案：**
1. `RFID_Database_Table_Schema_[TenKhachHang].xlsx` (Bảng chi tiết tên trường, kiểu dữ liệu, khóa chính và giải thích ý nghĩa theo đúng biểu mẫu Quý bên yêu cầu)
2. `Huong_Dan_Ket_Noi_Du_Lieu_SQL.pdf` (Tài liệu hướng dẫn kết nối IP, phân quyền và câu lệnh truy vấn mẫu)

Nếu Quý Bộ phận CNTT cần tạo thêm các View tùy biến, tối ưu hóa câu lệnh truy vấn (Query Optimization) hoặc cần buổi họp kỹ thuật trực tuyến (Teams / Google Meet) để phối hợp test dữ liệu kết nối, xin vui lòng phản hồi qua email này để chúng tôi sắp xếp kỹ sư hỗ trợ ngay.  
若貴司資訊團隊在後續介接測試過程中需要自訂 View 檢視表、調整查詢效能，或需召開線上技術對接會議，請隨時回信告知，我司將立即安排軟體工程師全力配合。

Chúc dự án chuyển đổi số và ứng dụng AI của Quý Công ty triển khai thành công tốt đẹp!  
預祝貴公司 AI 智慧轉型專案順利推展！

Trân trọng / 敬上,

**Bộ phận Kỹ thuật Phần mềm & Tích hợp Hệ thống / 軟體研發暨系統整合部**  
**CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司**  
* Hotline: +84 966 687 109  
* Email: it-support@hongming-global.com / sales@hongming-global.com  
* Địa chỉ: Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh
