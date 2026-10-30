# MẪU MAIL GỬI HÓA ĐƠN ĐIỆN TỬ GTGT (E-INVOICE EMAIL)

## 1. DẠNG MAIL NÀY DÙNG ĐỂ LÀM GÌ?
- Gửi hóa đơn giá trị gia tăng (VAT E-Invoice) hợp lệ có mã của Cơ quan Thuế cho bộ phận Kế toán khách hàng sau khi nhận thanh toán hoặc hoàn thành nghiệm thu theo quy định của pháp luật Việt Nam.
- Cung cấp đầy đủ thông tin: Ký hiệu mẫu số, ký hiệu hóa đơn, số hóa đơn, ngày phát hành, tổng tiền thanh toán, thuế suất VAT.
- Cung cấp đường link tra cứu trực tuyến và mã tra cứu bí mật để kế toán khách hàng có thể kiểm tra và lưu trữ vào phần mềm kế toán ERP.

---

## 2. FILE ĐÍNH KÈM BẮT BUỘC (ATTACHMENTS)
Khi gửi email hóa đơn GTGT, **BẮT BUỘC** phải đính kèm:
1. **Bản thể hiện Hóa đơn điện tử dạng PDF (Bắt buộc):**
   - File PDF có đầy đủ chữ ký số điện tử của Công ty TNHH Toàn Cầu Hong Ming và mã xác thực của Cục Thuế.
   - Tên file đặt theo chuẩn kế toán: `[KyHieu]_[SoHoaDon]_[TenKhachHang]_[SoTien].pdf` (Ví dụ: `C26THM_00000023_CONG_TY_JINXUN_781.530.000.pdf`).
2. **File dữ liệu gốc Hóa đơn điện tử dạng XML (Bắt buộc theo Luật Thuế):**
   - File XML chứa chữ ký số để khách hàng lưu trữ hợp lệ phục vụ quyết toán thuế theo Thông tư 78/2021/TT-BTC.
3. **Biên bản nghiệm thu / Đối chiếu thanh toán đi kèm (Nếu có):**
   - Dùng để kế toán hai bên kẹp chung thành 1 bộ hồ sơ chứng từ thanh toán đầy đủ.

---

## 3. MẪU NỘI DUNG EMAIL CHUẨN (SONG NGỮ VIỆT - TRUNG)

**Tiêu đề:** Gửi hóa đơn GTGT [Tên dịch vụ / Hạng mục] - CÔNG TY TNHH TOÀN CẦU HONG MING / 寄送 [項目名稱] 增值稅發票 – 宏明環球有限公司

---

**Nội dung:**

Kính gửi: Quý Công ty [Tên công ty khách hàng] / Bộ phận Kế toán tài chính,  
CC: [Tên người phụ trách mua hàng / PM đối tác],  
敬致：[貴公司名稱] / 財務會計部，  
抄送：[專案主管 / 採購窗口]：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng đến Quý Công ty.  
宏明環球有限公司謹向貴公司致以誠摯的問候。

Căn cứ vào Hợp đồng số [Số Hợp Đồng] và biên bản nghiệm thu đã hoàn thành, Hong Ming xin trân trọng gửi đến Quý Công ty hóa đơn giá trị gia tăng điện tử với các chi tiết cụ thể như sau:  
依據雙方簽署之合約編號 [合約編號] 及已完成之驗收確認書，宏明環球特此檢附電子增值稅發票，明細如下：

**Thông tin chi tiết hóa đơn / 發票詳細明細：**
* Tên người mua / 買方公司抬頭: [Tên pháp nhân đầy đủ của khách hàng]
* Mã số thuế / 稅號: [Mã số thuế khách hàng]
* Tên dịch vụ, hàng hóa / 貨品或服務名稱: [Ví dụ: Hệ thống MES Lite - Giao diện Web cấp phép 25 máy trạm / Dịch vụ sửa chữa và thay thế linh kiện máy kiểm kho]
* Mẫu số & Ký hiệu / 發票符號: [Ví dụ: 1C26THM]
* Số hóa đơn / 發票號碼: [Ví dụ: 00000023]
* Ngày lập hóa đơn / 開票日期: [Ngày/Tháng/Năm: ví dụ 16/10/2026]
* Tiền hàng trước thuế / 未稅金額: [Số tiền trước thuế] VNĐ
* Thuế suất & Tiền thuế GTGT / 稅率及稅額: [Ví dụ: 8% hoặc 10%] = [Số tiền thuế] VNĐ
* Tổng tiền thanh toán / 總含稅金額: [Tổng số tiền] VNĐ  
  *(Bằng chữ / 大寫: [Số tiền bằng chữ tiếng Việt] / [Số tiền bằng chữ tiếng Trung])*

**Tra cứu hóa đơn trực tuyến / 線上發票查驗資訊：**
* Trang tra cứu / 查驗網址: [Ví dụ: https://tracuu.minvoice.vn hoặc portal phát hành]
* Mã số tra cứu bí mật / 查驗碼: [Điền mã tra cứu bảo mật]

**Tài liệu đính kèm theo thư / 隨信附件檔案：**
1. `[KyHieu]_[SoHD]_[TenKhachHang].pdf` (Bản thể hiện hóa đơn điện tử)
2. `[KyHieu]_[SoHD]_[TenKhachHang].xml` (File dữ liệu gốc lưu trữ thuế)

Kính nhờ Quý Bộ phận Kế toán hỗ trợ tải file, kiểm tra thông tin và tiến hành lưu trữ hạch toán sổ sách theo quy định hiện hành.  
煩請貴司財務部協助下載檔案、核對開票資訊，並依越南稅務法規進行會計入帳作業。

Nếu cần thêm thông tin hoặc xuất lại hóa đơn do có sai sót, xin vui lòng phản hồi ngay cho chúng tôi qua email này.  
若對發票內容有任何疑問或需進一步協助，請隨時回信告知。

Rất cảm ơn sự hợp tác của Quý Công ty!  
非常感謝貴公司的密切配合！

Trân trọng / 敬上,

**Bộ phận Kế toán & Hóa đơn / 財務會計暨發票小組**  
**CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司**  
* Hotline: +84 966 687 109  
* Email: invoice@hongming-global.com / sales@hongming-global.com  
* Địa chỉ: Lầu 2, số 68 Nguyễn Huệ, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh
