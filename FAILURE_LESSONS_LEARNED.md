# SỔ TAY GHI NHẬN LỖI, GIẢI PHÁP & QUY TẮC CHỐNG TÁI PHẠM
*(FAILURE LOG & ANTI-REGRESSION REPOSITORY)*

> **NGUYÊN TẮC VÀNG:**  
> Mọi sai sót kỹ thuật đều phải được mổ xẻ nguyên nhân gốc rễ và ghi lại giải pháp vĩnh viễn tại đây.  
> **TUYỆT ĐỐI KHÔNG BAO GIỜ THỬ LẠI CÁCH ĐÃ TỪNG SAI.** Trước khi thực hiện bất kỳ tác vụ nào, trợ lý AI bắt buộc phải tra cứu sổ tay này để áp dụng ngay giải pháp đúng 100%.

---

## DANH MỤC CÁC BÀI HỌC KINH NGHIỆM ĐÃ ĐÚC KẾT (LESSONS LEARNED)

### 📌 ERR-001: LỖI KHÓA CUỘN TRANG WEB (PAGE SCROLL LOCK TRONG LAYOUT CSS)
* **Hiện tượng:** Người dùng truy cập một trang web mới tạo (như `/emails`) trên trình duyệt và hoàn toàn **không cuộn (scroll) chuột được**, trang bị cắt cụt ở phần dưới.
* **Nguyên nhân gốc rễ:**
  - Trong `pm_portal/app/static/css/layout.css`, thẻ cha `.app-main` được thiết lập `overflow: hidden; flex: 1;`.
  - Nếu container trang con chỉ dùng `display: flex; flex-direction: column;` mà **thiếu chiều cao tính toán `height: calc(100vh - var(--header-height));` và thiếu `overflow-y: auto;`**, thì vùng nội dung tràn sẽ bị trình duyệt giấu đi hoàn toàn mà không sinh thanh cuộn.
  - Ngoài ra, nếu các khối xem trước bên trong lại đặt `max-height: 600px; overflow-y: auto;` sẽ gây hiện tượng "cuộn lồng nhau" (nested scroll trap), khiến con trỏ chuột bị kẹt cục bộ.
* **Cách làm SAI trước đó (TUYỆT ĐỐI CẤM LẶP LẠI):**
  ```css
  /* SAI: Thiếu height và overflow-y */
  .email-center-container {
    display: flex;
    flex-direction: column;
    padding: 1.25rem;
  }
  ```
* **Giải pháp ĐÚNG TRIỆT ĐỂ (ÁP DỤNG VĨNH VIỄN):**
  Mọi trang làm việc đơn lập (workspace single) trong PM Portal bắt buộc phải tuân thủ đúng mẫu:
  ```css
  .email-center-container,
  .voucher-workspace {
    width: 100%;
    max-width: 1600px;
    margin: 0 auto;
    padding: 1.25rem 1.75rem 5rem;
    height: calc(100vh - var(--header-height)); /* Khóa chiều cao theo viewport trừ header */
    overflow-y: auto;                           /* BẬT THANH CUỘN DỌC TẠI CONTAINER CHÍNH */
    box-sizing: border-box;
    scroll-behavior: smooth;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }
  ```
  Và gỡ bỏ thuộc tính `max-height` cứng nhắc ở các khối con bên trong để toàn bộ trang cuộn tự nhiên theo 1 thanh cuộn duy nhất.

---

### 📌 ERR-002: LỖI THỨ TỰ ĐỐI SỐ JINJA2 TEMPLATERESPONSE TRONG STARLETTE / FASTAPI
* **Hiện tượng:** Gọi API render HTML báo lỗi: `TypeError: Jinja2Templates.TemplateResponse() missing 1 required positional argument: 'request'` hoặc `TypeError: unhashable type: 'dict'`.
* **Nguyên nhân gốc rễ:**
  - Trong phiên bản Starlette mới, chữ ký hàm của `TemplateResponse` bắt buộc phải nhận `request` làm đối số vị trí (positional argument) đầu tiên: `TemplateResponse(request, name, context)`.
* **Cách làm SAI trước đó (TUYỆT ĐỐI CẤM LẶP LẠI):**
  ```python
  # SAI: Truyền name trước request hoặc truyền dict vào name
  return templates.TemplateResponse("email_page.html", {"request": request, ...})
  return templates.TemplateResponse(name="email_page.html", context={...})
  ```
* **Giải pháp ĐÚNG TRIỆT ĐỂ (ÁP DỤNG VĨNH VIỄN):**
  Luôn luôn truyền đúng chuẩn 3 đối số:
  ```python
  return templates.TemplateResponse(
      request,
      "email_page.html",
      {
          "request": request,
          "active_tab": "email_center",
          "page_title": "Tiêu đề trang"
      }
  )
  ```

---

### 📌 ERR-003: LỖI THOÁT KÝ TỰ (ESCAPING) TRONG LỆNH POWERSHELL DÒNG LỆNH
* **Hiện tượng:** Chạy lệnh PowerShell inline với `\"` hoặc `$var` bị lỗi cú pháp: `Unexpected token`, `Missing closing ')'`, `The string is missing the terminator`.
* **Nguyên nhân gốc rễ:** PowerShell trên Windows diễn giải ký tự `$` thành biến môi trường và ký tự `\"` bị shell bao ngoài cắt xén.
* **Cách làm SAI trước đó (TUYỆT ĐỐI CẤM LẶP LẠI):**
  Cố nhồi nhét script Python dài hoặc logic phức tạp vào trong chuỗi `powershell -Command "..."` hoặc `python -c "..."`.
* **Giải pháp ĐÚNG TRIỆT ĐỂ (ÁP DỤNG VĨNH VIỄN):**
  Luôn tạo file scratch `.py` trong thư mục `scratch/` với encoding UTF-8 chuẩn xác, sau đó chạy file bằng `python script_path.py`. Cách này sạch sẽ 100%, không bao giờ bị lỗi escaping.

---

### 📌 ERR-004: LỖI POPUP CẢNH BÁO BẢO MẬT KHI ĐỌC OUTLOOK QUA MAPI COM
* **Hiện tượng:** Script đọc Outlook bị đơ / treo vô thời hạn (Task chạy ngầm không kết thúc) do Windows bật popup bảo mật: *"A program is trying to access email address information..."*.
* **Nguyên nhân gốc rễ:** Thuộc tính `item.SenderEmailAddress` và `item.To` thuộc nhóm nhạy cảm bị Outlook Security Guard chặn đối với các phần mềm bên ngoài truy cập MAPI.
* **Cách làm SAI trước đó (TUYỆT ĐỐI CẤM LẶP LẠI):**
  Truy cập trực tiếp `item.SenderEmailAddress` trong vòng lặp lặp email.
* **Giải pháp ĐÚNG TRIỆT ĐỂ (ÁP DỤNG VĨNH VIỄN):**
  Chỉ truy xuất các thuộc tính an toàn không bao giờ kích hoạt popup:
  - `item.Subject`
  - `item.SenderName`
  - `item.ReceivedTime`
  - `item.Attachments`
  - `item.Body`
  Tốc độ đọc đạt dưới 0.1 giây / email và an toàn tuyệt đối.

---

### 📌 ERR-005: LỖI ĐƯỜNG KẺ XANH ĐỨT ĐOẠN CHIA CẮT TRANG IN EXCEL
* **Hiện tượng:** File Excel tạo ra mở trên WPS/Excel bị các đường kẻ xanh đứt đoạn (blue dashed lines) chia bảng thành nhiều trang rời rạc (Page 1, 2, 3, 4).
* **Nguyên nhân gốc rễ:** Thiếu tỷ lệ co giãn in ấn `scale = 52` khi bảng dữ liệu rộng hơn khổ chuẩn A4.
* **Giải pháp ĐÚNG TRIỆT ĐỂ (ÁP DỤNG VĨNH VIỄN):**
  Luôn đặt:
  ```python
  ws.page_setup.scale = 52
  ws.page_setup.paperSize = 9  # A4
  ws.print_area = '$A$1:$H$28' # Khóa khít dữ liệu
  ```
  Và tuyệt đối không bật `showGridLines = True` trong `pageBreakPreview` để tránh loang viền xám.

---

### 📌 ERR-006: LỖI THIẾU CỘT CSDL KHI BẢNG SQLITE ĐÃ TỒN TẠI (ADDITIVE SCHEMA MIGRATION)
* **Hiện tượng:** Ứng dụng gọi INSERT hoặc SELECT báo lỗi: `sqlite3.OperationalError: table ... has no column named ...`.
* **Nguyên nhân gốc rễ:** Bảng đã được tạo từ trước bằng `CREATE TABLE IF NOT EXISTS`. Khi bổ sung code thêm trường mới vào câu lệnh CREATE TABLE, SQLite bỏ qua vì bảng đã tồn tại, dẫn tới các trường mới không được thêm vào cấu trúc bảng thực tế.
* **Cách làm SAI trước đó (TUYỆT ĐỐI CẤM LẶP LẠI):**
  Chỉ sửa câu lệnh `CREATE TABLE IF NOT EXISTS` mà không chạy lệnh migration thêm cột cho bảng đã có dữ liệu.
* **Giải pháp ĐÚNG TRIỆT ĐỂ (ÁP DỤNG VĨNH VIỄN):**
  Luôn thực hiện kiểm tra `PRAGMA table_info` và `ALTER TABLE ADD COLUMN` ngay sau khi tạo bảng:
---

### 📌 ERR-007: LỖI ĐIỀU KHOẢN BÁO GIÁ EXCEL BỊ XẸP DÒNG, MẤT MÀU VÀ LỆCH MẪU GỐC BAOGIAGOC.XLSX
* **Hiện tượng:** 
  - Khối Điều khoản đặc biệt (◆ 報價特別聲明) xuất ra Excel bị xẹp chiều cao dòng (Term 5 có 18 dòng text nhưng dòng chỉ cao 15pt khiến chữ bị chìm mất và đè vào viền dưới).
  - Điều 4 mất chữ màu đỏ (`FFFF0000`), Điều 5 mất chữ màu xanh dương (`FF0000FF`).
  - Toàn bộ font bị thu nhỏ về Arial 9.5pt thay vì `微軟正黑體` 12pt chuẩn mực doanh nghiệp Đài Loan.
  - Điều 5 bị rút ngắn thành 1 dòng tóm tắt, làm mất toàn bộ 2 phần pháp lý cố định (一、付款方式 quy định trên/dưới 30 triệu VND và 二、驗收條款 trong vòng 7 ngày).
* **Nguyên nhân gốc rễ:**
  - `quotation_excel_service.py` không thiết lập thuộc tính chiều cao dòng `ws.row_dimensions[tr].height`. Mẫu gốc quy định rõ: Header=34.8pt, T1..T4=58.2pt, T5=316.0pt.
  - Sử dụng chung 1 font `Arial 9.5pt` cho mọi điều khoản, không set màu font `FFFF0000` cho Điều 4 và `FF0000FF` cho Điều 5.
  - Biến `payment_terms` từ form web chỉ chứa 1 dòng tóm tắt đã ghi đè làm mất toàn bộ nội dung pháp lý 18 dòng chuẩn mẫu gốc.
* **Cách làm SAI trước đó (TUYỆT ĐỐI CẤM LẶP LẠI):**
  ```python
  # SAI: Ghi đè tóm tắt, không set height, font Arial 9.5pt đen
  t5 = f"5. 付款方式及驗收條件 / Điều kiện thanh toán & nghiệm thu:\n• {payment_terms}"
  ws[f"E{tr}"].font = Font(name="Arial", size=9.5)
  # Quên set ws.row_dimensions[tr].height = 316.0
  ```
* **Giải pháp ĐÚNG TRIỆT ĐỂ (ÁP DỤNG VĨNH VIỄN):**
  1. Luôn khóa chiều cao dòng khớp 1:1 theo mẫu gốc `BaoGiaGoc.xlsx`:
     - Row Header (`A_hdr, E_hdr`): `height = 34.8` pt.
     - Row Term 1 đến Term 4 (`E_t1:I_t4`): `height = 58.2` pt.
     - Row Term 5 (`E_t5:I_t5`): `height = 316.0` pt.
  2. Font chữ & Màu sắc 1:1:
     - Header: `A_hdr` dùng `Arial 14pt color=FF9C6500` (Nâu vàng), `E_hdr` dùng `微軟正黑體 12pt bold`.
     - Chữ ký khách: `A_t1` dùng `Arial 12pt color=FF9C6500` (Nâu vàng, căn trên top).
     - Điều 1, 2, 3: `微軟正黑體 12pt bold`.
     - Điều 4 (VAT): `微軟正黑體 12pt bold=False color=FFFF0000` (CHỮ ĐỎ).
     - Điều 5 (Thanh toán & Nghiệm thu): `微軟正黑體 12pt bold=False color=FF0000FF` (CHỮ XANH DƯƠNG).
  3. Bảo toàn 100% nội dung pháp lý 2 phần của Điều 5 từ mẫu gốc Hong Ming:
     - `一、付款方式`: Đơn hàng trên 30.000.000 VNĐ đặt cọc 50%, còn lại thanh toán 10 ngày sau nhận hàng; đơn hàng dưới 30.000.000 VNĐ thanh toán 100% sau 10 ngày.
     - `二、驗收條款`: Nghiệm thu trong vòng 7 ngày, quá hạn xem như nghiệm thu thành công, không được lấy cớ chưa ký biên bản riêng để hoãn thanh toán.
  4. Đóng khung viền `medium`: Cột A (trái), Cột I (phải), Hàng đáy Term 5 (dưới).
* **Quy tắc kiểm thử phòng ngừa (Verification Checklist):**
  - Chạy script kiểm tra `ws.row_dimensions[r].height` đảm bảo `r_t5` đạt `316.0`.
  - Kiểm tra `ws[f"E{r_t4}"].font.color.rgb == "FFFF0000"` và `ws[f"E{r_t5}"].font.color.rgb == "FF0000FF"`.
  - Mở file trên WPS Office / Excel để mắt thường kiểm tra không bị cắt cụt.

---

### 📌 ERR-008: LỖI SỐ TIỀN HIỂN THỊ "VND 13.70 (VND 0.000)" TRÊN WPS OFFICE
* **Hiện tượng:** Ô Tổng thành tiền `I{sum_r}` có giá trị 13,700,000 VND nhưng mở trên WPS Office bị hiển thị biến dạng thành `VND 13.70 (VND 0.000)`.
* **Nguyên nhân gốc rễ:**
  - Chuỗi định dạng `"[$VND] #,##0_;([$VND] #,##0)"` thiếu dấu gạch chéo ngược `\` để thoát ký tự dấu cách và dấu ngoặc đơn. WPS Office diễn giải nhầm dấu ngoặc và gạch dưới thành hệ số chia phần triệu kèm phân số.
* **Cách làm SAI trước đó (TUYỆT ĐỐI CẤM LẶP LẠI):**
  ```python
  # SAI: Thiếu dấu thoát ký tự \
  ws[f"I{sum_r}"].number_format = "[$VND] #,##0_;([$VND] #,##0)"
  ```
* **Giải pháp ĐÚNG TRIỆT ĐỂ (ÁP DỤNG VĨNH VIỄN):**
  Sử dụng định dạng chuẩn phổ quát hiển thị hoàn hảo trên cả WPS Office, Microsoft Excel và Google Sheets:
  ```python
  ws[f"I{sum_r}"].number_format = "$#,##0.00" if currency == "USD" else '#,##0 "VND"'
  ```
  Hoặc nếu muốn chữ VND đứng trước thì dùng chuỗi thoát đầy đủ từ mẫu gốc:
  ```python
  ws[f"I{sum_r}"].number_format = r'[$VND]\ #,##0_);\([$VND]\ #,##0\)'
  ```
* **Quy tắc kiểm thử phòng ngừa:**
  - Kiểm tra kết quả hiển thị trên WPS Office: `13,700,000 VND` thay vì `13.70 (0.000)`.



### ERR-009: Outlook connector khai báo công cụ nhưng backend báo Unknown tool (29/10/2026)
- Hiện tượng: search_messages trả MCP -32001 Unknown tool.
- Nguyên nhân gốc rễ: Công cụ có trong danh sách phiên nhưng backend không nhận microsoft_outlook_email.search_messages; chưa xác định nguyên nhân cấu hình.
- Anti-Pattern: Đồng nhất việc công cụ xuất hiện với tài khoản đã kết nối thành công; lặp lại cùng lời gọi lỗi.
- Permanent Solution: Kiểm tra kết quả thực tế; khi lỗi này xuất hiện, chuyển sang Computer Use để đọc Outlook cục bộ theo yêu cầu người dùng.
- Verification Checklist: Chỉ xác nhận truy cập thành công sau khi đã đọc được thư; phân biệt trạng thái connector và ứng dụng cục bộ.

### ERR-010: Computer Use Outlook không lấy được hình cửa sổ (29/10/2026)
- Hiện tượng: click báo coordinate input geometry is unavailable; khôi phục cửa sổ và chụp hình báo FrameArrived timed out.
- Nguyên nhân gốc rễ: Capture không cung cấp geometry/frame; chưa xác định nguyên nhân runtime.
- Anti-Pattern: Click lặp lại bằng chỉ số cũ sau khi capture thất bại.
- Permanent Solution: Lấy lại danh sách và window hiện hành, thử capture một lần; nếu vẫn lỗi thì dừng thao tác và chỉ báo nội dung accessibility thực sự đọc được.
- Verification Checklist: Không tuyên bố đọc toàn văn khi chỉ có preview; không sử dụng lại chỉ số/geometry cũ.

### ERR-011: Antigravity IDE cập nhật để tệp chạy trong thư mục _ (29/10/2026)
- Hiện tượng: Hộp thoại mang tiêu đề Visual Studio Code báo cập nhật thất bại; log vscode-inno-updater-1793236275.log báo thiếu Antigravity IDE.exe ở thư mục cài đặt.
- Nguyên nhân gốc rễ: Thư mục cài đặt chỉ còn _, tools và uninstaller; toàn bộ payload chương trình còn trong thư mục _.
- Anti-Pattern: Kết luận antivirus gây lỗi chỉ từ thông báo chung; xóa cấu hình hoặc cài lại khi chưa kiểm tra payload.
- Permanent Solution: Giữ nguyên bản trong _, sao chép payload về thư mục cài đặt đã đăng ký; kiểm tra phiên bản và mở ứng dụng để xác nhận.
- Verification Checklist: Tệp chạy và resources tồn tại ở root; tiến trình mở từ root và cửa sổ xuất hiện; không xóa dữ liệu người dùng.

### ERR-012: Hợp nhất Git có thay đổi cục bộ và SQLite (29/10/2026)
- Hiện tượng: stash apply sau fast-forward xung đột config.py, quotation_excel_service.py, pm_portal.db; môi trường thiếu pytest.
- Nguyên nhân gốc rễ: Hai bên cùng sửa cấu hình và vị trí đặt tên tệp; SQLite không hỗ trợ merge văn bản; pytest chưa được cài trong Python đang dùng.
- Anti-Pattern: Ghi đè cả database hoặc chọn nguyên một phía mã nguồn; chạy test trên hồ sơ thật; in giá trị cấu hình nhạy cảm khi xem diff.
- Permanent Solution: Giữ stash và ba bản SQLite base/local/remote trong .tmp/merge_20261029; giữ nghiệp vụ local kết hợp tên file upstream; chuyển khóa cấu hình sang file riêng được Git exclude; giữ database local cộng thay đổi custom_reminders upstream; kiểm tra integrity và dùng DB tạm khi test. Cài pytest để chạy kiểm thử đã có.
- Verification Checklist: Không còn unmerged paths hoặc conflict markers; import và compile đạt; kiểm tra test quản lý file và smoke test dùng dữ liệu tạm; không push bí mật.

### ERR-013: Đường dẫn máy E cố định trong script DFV (29/10/2026)
- Hiện tượng: test_organized_files_and_signature_mapping thất bại trên D vì script trỏ E:\Working.
- Nguyên nhân gốc rễ: Các script scripts/thiet_bi_dfv dùng chuỗi đường dẫn máy tác giả và Downloads của BANG.
- Anti-Pattern: Hardcode ổ đĩa hoặc tên người dùng; test chỉ đọc hằng chuỗi nên không hỗ trợ đường dẫn động.
- Permanent Solution: WORKING_DIR = Path(__file__).resolve().parents[2], Downloads = Path.home()/Downloads; test chỉ đánh giá khai báo đường dẫn bằng AST, không chạy script tạo tài liệu.
- Verification Checklist: 13 test_file_integrity đạt; 5 trang chính HTTP 200; xuất báo giá vào thư mục QA có công thức và timestamp mới; SQLite integrity OK, giữ 26 payment_milestones và 5 emails; compile Python và kiểm tra cú pháp 5 JavaScript đạt.

### ERR-014: Desktop launcher pythonw làm Uvicorn thoát ngay (29/10/2026)
- Hiện tượng: Nhấp Hong Ming PM Portal mở trình duyệt nhưng 127.0.0.1:8032 báo ERR_CONNECTION_REFUSED.
- Nguyên nhân gốc rễ: launcher.py dùng sys.executable (pythonw.exe) chạy run.py, không gắn stdout/stderr. Uvicorn logging.py gọi sys.stdout.isatty() khi stdout=None, gây ValueError Unable to configure formatter default. Launcher vẫn mở trình duyệt sau thời gian chờ.
- Anti-Pattern: Kiểm tra cổng đơn thuần rồi mở trình duyệt bất kể tiến trình sống/chết; chạy pythonw con không có luồng nhật ký; bật reload cho launcher Desktop.
- Permanent Solution: Launcher chọn python.exe cùng môi trường, chạy CREATE_NO_WINDOW, gắn stdin DEVNULL và stdout/stderr vào pm_portal/.tmp/portal_startup.log; đặt PM_PORTAL_RELOAD=0; đợi HTTP 200 và kiểm tra child exit; báo lỗi khi khởi động thất bại thay vì mở trang lỗi.
- Verification Checklist: Khởi động từ shortcut thật, HTTP /quotations trả 200; tiến trình nền sống; nhấp lần hai không sinh máy chủ thứ hai; log không có traceback khởi động.
- Kết quả xác minh ERR-014: shortcut Desktop đã khởi động server thành công; /quotations HTTP 200; startup complete; gọi launcher lần hai dùng cùng tiến trình, không chạy trùng.

### ERR-015: Đọc email Việt Trung bằng Python bị lỗi mã hóa console (29/10/2026)
- Hiện tượng: UnicodeEncodeError cp1252 khi in tên thư mục Outlook bằng tiếng Trung.
- Nguyên nhân gốc rễ: Python mặc định stdout cp1252 trong tiến trình shell.
- Anti-Pattern: In chuỗi Việt Trung khi chưa thiết lập encoding đầu ra.
- Permanent Solution: sys.stdout.reconfigure(encoding="utf-8") trước khi xuất; dữ liệu JSON ghi UTF-8 và đọc utf-8-sig khi PowerShell tạo BOM.
- Verification Checklist: Hiển thị được cả dấu tiếng Việt và ký tự CJK; không ghi lại token/mật khẩu từ email.

### ERR-016: Hồ sơ thanh toán scan không khớp email và số tiền bằng chữ (29/10/2026)
- Hiện tượng: Tệp DYCTT - BBNT 46.800.000.pdf trong thư CX 24/10/2026 có hạn trên phiếu là 31/10/2026, email là 05/11/2026. Trang 3 ghi số 46.800.000 nhưng bằng chữ tiếng Việt là Chín mươi sáu triệu sáu trăm nghìn đồng. Ô ký khách hàng còn trống trong bản scan.
- Nguyên nhân gốc rễ: Chưa đối chiếu đồng bộ trường dữ liệu và trạng thái ký khi tổng hợp hồ sơ; chưa xác định người tạo bản gốc.
- Anti-Pattern: Xem tài liệu đã gửi trước đây là mẫu đúng tuyệt đối; đánh dấu đã nghiệm thu/đã thanh toán chỉ từ tiêu đề thư; dùng OCR trống để kết luận PDF không có nội dung.
- Permanent Solution: Đọc trực quan bản scan; đối chiếu email, phiếu và biên bản; ghi rõ cần xác nhận hạn, sửa số tiền bằng chữ và bổ sung bằng chứng ký. Không tự sửa bản scan đã ký hoặc khẳng định tình trạng tiền về.
- Verification Checklist: Cùng mã HĐ, cùng hạn đã được xác nhận, số bằng chữ tương ứng số bằng số, đủ bằng chứng khách xác nhận và kế toán xác nhận tiền về.

### ERR-017: Liên kết nguồn email trong hướng dẫn thiếu bản trích (29/10/2026)
- Hiện tượng: Kiểm tra liên kết cẩm nang phát hiện thiếu nguon/Email_017.md, thư gốc vẫn có trong bản đọc Outlook.
- Nguyên nhân gốc rễ: Danh sách xuất thư chưa bao gồm một email đã dẫn trong phần DARFON.
- Anti-Pattern: Viết liên kết nguồn trước khi đối chiếu manifest xuất thư.
- Permanent Solution: Xuất bổ sung đúng thư gốc, cập nhật mục lục và số lượng 21 thư, kiểm tra tồn tại mọi link trước bàn giao.
- Verification Checklist: Tất cả liên kết local trong cẩm nang và mục lục trỏ đến tệp tồn tại; đúng số lượng nguồn.

### ERR-018: Email mẫu khẳng định đã ký và đính kèm khi chưa có bằng chứng (29/10/2026)
- Hiện tượng: email_controller.py nhánh milestone điền tên PDF giả định và câu đã ký duyệt/đóng dấu; nhánh acceptance ghi bản scan đầy đủ, nhưng bảng documents/emails chưa có cơ chế xác minh trạng thái ký và gửi Outlook thật.
- Nguyên nhân gốc rễ: Logic sinh nội dung theo nguồn hồ sơ, không có cổng xác nhận signed artifact, attachment vật lý và trạng thái workflow. Tích hợp Gmail riêng còn đường dẫn tài khoản BANG/ổ E.
- Anti-Pattern: Đồng nhất DRAFT hoặc SIMULATED_SENT với thư Outlook đã gửi; coi tên file trong attachments_json là tệp có thật; dùng dữ liệu ngân hàng/địa chỉ nhận mẫu chưa xác minh.
- Permanent Solution: Khi đánh giá phải ghi rõ mức hỗ trợ hiện tại. Thiết kế tiếp theo cần trạng thái hồ sơ, bản ký và xác nhận người dùng; chỉ soạn nội dung theo bằng chứng, kiểm tra file vật lý, người nhận và tài khoản; liên kết MessageID gửi thật; tiền về do kế toán xác nhận. Chưa sửa ứng dụng trong tác vụ đánh giá này.
- Verification Checklist: Tách đã tạo/chờ ký/đã scan/chờ gửi/đã gửi/khách xác nhận/đã thu; thử tình huống chưa có bản ký thì không hiện đã ký; không suy diễn SIMULATED_SENT là gửi thật.

### ERR-019: Kiểm thử workflow bắt lỗi timezone Windows và SQL nhật ký (29/10/2026)
- Hiện tượng: Test không tìm được tzdata và INSERT workflow_events báo 5 values for 4 columns.
- Nguyên nhân gốc rễ: Windows Python không có cơ sở IANA timezone; SQL có 5 placeholder cho 4 trường.
- Anti-Pattern: Giả định zoneinfo có dữ liệu trên Windows; viết INSERT mà không đối chiếu số cột với tham số.
- Permanent Solution: Dùng timezone UTC+7 chuẩn Việt Nam không phụ thuộc gói ngoài; sửa INSERT thành 4 placeholder; kiểm thử chuỗi workflow với SQLite tạm.
- Verification Checklist: T/T=0 giữ đúng ngày; tải file, nhật ký và tạo công việc hoạt động; toàn bộ test_workflows đạt.

### ERR-020: Kiểm tra hồi quy thấy test cũ gộp sai hai đơn CX (29/10/2026)
- Hiện tượng: test_payment_schedule kỳ vọng sheet CX là 100%, nhưng file mẫu hiện tại CX là hợp đồng phần mềm 40/40/20; CX (2) mới là đơn pin 100%.
- Nguyên nhân gốc rễ: Kỳ vọng test theo tên khách thay vì đúng sheet/giao dịch đang dùng.
- Anti-Pattern: Sửa form thật để ép khớp test; áp tỷ lệ chung cho mọi đơn cùng khách.
- Permanent Solution: Đối chiếu B15/B23 từng sheet, sửa test phân biệt CX 40/40/20 và CX (2) 100%; giữ nguyên form thật.
- Verification Checklist: Bộ 39 test workflow, file integrity và payment schedule đạt; không chỉnh dữ liệu mẫu để qua test.

### ERR-021: Tìm Outlook chỉ theo tiêu đề bỏ sót hợp đồng trong thân thư (29/10/2026)
- Hiện tượng: Nút đọc Outlook trả 0 thư cho SEIYO dù mã HĐ có trong nội dung.
- Nguyên nhân gốc rễ: workflow_outlook_service.candidates chỉ so khớp subject, thư thực tế đặt tiêu đề theo tên dự án.
- Anti-Pattern: Đoán giai đoạn theo khách hoặc chỉ dựa tiêu đề; tự động gắn mọi thư cùng hợp đồng vào một đợt.
- Permanent Solution: Tìm mã tham chiếu chính xác trong cả subject/body, phân biệt mã công việc, tiêu đề và lịch sử trích dẫn; yêu cầu người đọc chọn đúng thư/đợt trước khi gắn. Không tự chuyển giai đoạn khi chỉ đọc.
- Verification Checklist: Outlook thật trả 2 thư SEIYO; test QA-1 không khớp QA-10; chỉ đọc không tạo mail record hoặc khoản thu.

### ERR-022: Kiểm thử sinh hồ sơ không được đếm mất căn cứ có sẵn (29/10/2026)
- Hiện tượng: Test sinh phiếu kỳ vọng tổng 2 tệp nhưng phản hồi có 3 vì giữ cả căn cứ điều kiện.
- Nguyên nhân gốc rễ: Kỳ vọng test đếm tổng thay vì lọc loại draft.
- Anti-Pattern: Xóa căn cứ trước để khớp số tệp của test.
- Permanent Solution: Xác nhận có 2 bản draft mới và vẫn giữ căn cứ condition; kiểm tra nội dung khách trên Excel.
- Verification Checklist: 43 test đạt; Word/Excel sinh vào thư mục tạm, dữ liệu thật không có sự kiện hoặc khoản thu giả.

### ERR-023: Việc cần làm không kế thừa khoản đã thu trong Công nợ (29/10/2026)
- Hiện tượng: Công nợ SEIYO HMV22092026SY0001 ghi đợt 1 thu đủ ngày 24/10 và đợt 2 thu đủ ngày 26/10 (tổng 90%), nhưng workflow vẫn nhắc thu đợt 1; contracts.paid_amount chỉ 60%.
- Nguyên nhân gốc rễ: workflow chỉ đọc payment_milestones.status, trong khi AR id22 đã PAID nhưng milestone55 vẫn URGENT. Hàm AR cũ đồng bộ theo ngày trả đơn thuần và không cập nhật tổng hợp đồng; thiếu đối soát dữ liệu kế thừa.
- Anti-Pattern: Khẳng định liên kết tài chính đầy đủ chỉ vì có source_id; khởi tạo mọi đợt cũ như chưa thu; coi dự kiến ngày tương lai là thực nhận; cộng cả AR và ledger gây trùng.
- Permanent Solution: Đối soát theo linked_milestone_id + cùng mã HĐ + đúng giá trị đợt/VND + ngày thực nhận không ở tương lai; kế thừa nguồn đã nhập, không tạo chứng từ giả. Dùng chung phép tính tiền đã thu, cập nhật trạng thái mốc/tổng hợp đồng/workflow; khi thu qua workflow cập nhật ngược AR. Không tạo đề nghị thu lại cho đợt đã đủ.
- Verification Checklist: Đợt 1 SEIYO đóng khỏi danh sách cần xử lý, nhận 213.606.000 ngày24/10; tổng640.818.000 (90%), còn71.202.000 (10%). Test sai mã/sai giá trị/ngày tương lai không tự đóng; thu phần còn lại không cộng trùng tiền cũ.

### ERR-024: Cập nhật AR lỗi schema có thể ghi nhầm dữ liệu mẫu trùng ID (29/10/2026)
- Hiện tượng: Test dùng DB tạm gọi update_receivable trả thành công nhưng không cập nhật DB; rơi xuống JSON mẫu có cùng ID. Đã khôi phục đúng tệp dữ liệu mẫu sạch ngay sau khi phát hiện.
- Nguyên nhân gốc rễ: init_db thiếu migration start_date/payment_term_days của AR; update_receivable nuốt lỗi SQL rồi thử dataset khác.
- Anti-Pattern: Sau lỗi cập nhật dữ liệu thật, tìm record ID tương tự ở dữ liệu mẫu rồi ghi; coi không ném exception là cập nhật thành công.
- Permanent Solution: Bổ sung migration AR trong init_db; gắn nguồn database khi đọc record thật và không fallback sang dataset khác nếu cập nhật record đó lỗi.
- Verification Checklist: Test cập nhật AR đọc lại đúng DB tạm; JSON mẫu không có thay đổi; 49 kiểm thử workflow/file/payment schedule đạt; SEIYO đợt1 đã thu và tổng90% khớp giữa các trang.

### ERR-025: CUA không tải lại được tab browser.user (29/10/2026)
- Hiện tượng: Reload tab cũ và getTab đều báo browser.user is unavailable.
- Nguyên nhân gốc rễ: Runtime trình duyệt không cung cấp browser.user; chưa xác định cấu hình bên ngoài.
- Anti-Pattern: Lặp thao tác trên binding lỗi hoặc tuyên bố đã kiểm tra giao diện bằng hình mới.
- Permanent Solution: Dừng thử UI sau lần khôi phục thất bại; xác minh bằng API đang chạy và mở URL qua open_in_codex. Không dùng hình cũ làm bằng chứng bản mới.
- Verification Checklist: API case4 trả received213606000, remaining0, currentnull; danh sách có3 mở,0 cần xử lý,3 đóng; thông báo người dùng tải lại trang nếu còn cache.

### ERR-026: Cú pháp glob kiểu Bash trong PowerShell (29/10/2026)
- Hiện tượng: Lệnh tra cứu templates/{po,tracker,quotation} báo Missing argument in parameter list.
- Nguyên nhân gốc rễ: PowerShell không mở rộng brace glob như Bash.
- Anti-Pattern: Dùng cú pháp mở rộng đường dẫn của shell khác trong PowerShell.
- Permanent Solution: Dùng rg thư mục templates với các tham số -g riêng, hoặc truyền mảng đường dẫn PowerShell hợp lệ. Với Python nhiều dòng/có dấu nháy, truyền here-string vào python -; không dùng backslash để escape nháy kép theo kiểu Bash (đã gây SyntaxError khi kiểm tra integrity, không tác động dữ liệu).
- Verification Checklist: Tra cứu chạy thành công; không có thao tác sửa dữ liệu nào trong lệnh lỗi.

### ERR-027: Checklist nghiệp vụ chưa tạo thay đổi ở hồ sơ liên quan (29/10/2026)
- Hiện tượng: Ngoài thu tiền, hoàn tất checklist chưa cập nhật PO hay kích hoạt mốc thu; hồ sơ cũ có thể bị yêu cầu làm lại các bước đã thực hiện.
- Nguyên nhân gốc rễ: workflow_service.advance chỉ tăng stage; thiếu bản ghi nghiệp vụ có căn cứ và liên kết hợp đồng tường minh.
- Anti-Pattern: Gọi liên kết URL là đồng bộ đầy đủ; coi nhận từ NCC là giao khách; tô xanh mọi bước lịch sử chỉ vì tiền đã thu hoặc PO đã giao.
- Permanent Solution: project_sync_service lưu facts/links/assets và áp dụng nghiệp vụ trong cùng transaction, kiểm tra chứng từ/hash/ngày/người xác nhận, chống ghi trùng; PO từng phần cập nhật ngược nguồn, các mốc thu chỉ kích hoạt khi người dùng chọn đúng đợt và T/T. Chỉ tô xanh bước có nhật ký completed; dữ liệu cũ hiện nguồn và yêu cầu bổ sung căn cứ.
- Verification Checklist: DB tạm thử nhận thiếu/đủ/vượt; lặp chứng từ không cộng trùng; giao NCC không kích hoạt tiền khách; nghiệm thu/ký/giao chọn đúng mốc, không ghi đè PAID; bảo hành 6 tháng đúng lịch, sửa có phí có báo giá duyệt; không gửi email thật khi kiểm thử.

### ERR-028: Đếm hồ sơ kế thừa thành việc chưa thực hiện (29/10/2026)
- Hiện tượng: Trang Việc cần làm hiển thị 24 việc đang thực hiện, gồm 17 dòng mua hàng mặc dù 16 dòng nguồn ghi DELIVERED; người dùng hiểu thành 17 đơn chưa giao.
- Nguyên nhân gốc rễ: workflow.js đếm current != null; project_sync_service đưa hồ sơ cũ thiếu bằng chứng vào cùng hàng đợi nghiệp vụ mới. Trạng thái checklist bị dùng thay cho trạng thái giao hàng.
- Anti-Pattern: Coi chưa tải bản ký là chưa giao; gọi mọi dòng PO là việc chưa xong; tự đóng nghiệp vụ hoặc sửa ngày giao để giảm bộ đếm.
- Permanent Solution: queue_state tách active/waiting/review/closed, trả lý do và trạng thái nguồn độc lập. PO DELIVERED chưa có xác nhận mới thuộc review; các nguồn cũ chưa xác định bước cũng thuộc review; mốc thu chưa triggered thuộc waiting. Trang hiển thị các bộ đếm riêng, lọc dự án/loại/người phụ trách, nhóm danh sách và không sửa trạng thái nghiệp vụ gốc.
- Verification Checklist: DELIVERED không tăng số cần thực hiện; không mặc định PENDING là thực tế chưa giao; nhóm không chồng lặp và tổng bằng toàn bộ hồ sơ; thanh toán đã đủ vẫn closed; kiểm tra tìm kiếm không dấu, lọc kết hợp và chi tiết đúng hồ sơ.

---

### ERR-029: Bể layout banner Hero trên Trang Chủ do hàng nút cố định flex: 0 0 auto không bọc wrap (29/10/2026)
- **Hiện tượng:** Tiêu đề "Tổng quan danh mục dự án" bị ép co cụm xuống 5 dòng, nhãn trạng thái "DỮ LIỆU VẬN HÀNH THỰC TẾ" bị bẻ dọc từng chữ một thành 6 hàng dọc, các nút thao tác phía bên phải bị tràn và nút "+ Thêm hợp đồng" bị cắt cụt rìa phải (`+ Th...`).
- **Nguyên nhân gốc rễ:** `.dashboard-hero` dùng `display: flex; align-items: center; justify-content: space-between;` nhưng thiếu `flex-wrap: wrap;`. Khối nút `.dashboard-actions` chứa 6 nút dài với `flex: 0 0 auto` chiếm hơn 850px. Trên màn hình máy tính thông thường (1280px-1366px với sidebar), khối văn bản `.dashboard-hero-copy` không có `min-width` bị bóp nghẹt chỉ còn 150-180px. Badge `.live-indicator` thiếu `white-space: nowrap`.
- **Cách làm SAI trước đó (Anti-Pattern - TUYỆT ĐỐI CẤM LẶP LẠI):** Đặt `flex: 0 0 auto` cho cụm nhiều nút thao tác cạnh tiêu đề mà không cho phép `flex-wrap: wrap`; không đặt `min-width` cho cột nội dung văn bản chính; quên `white-space: nowrap` cho các pill badge trạng thái.
- **Giải pháp ĐÚNG TRIỆT ĐỂ (Permanent Solution):**
  1. `.dashboard-hero`: thêm `flex-wrap: wrap; gap: 1.25rem 2rem;`.
  2. `.dashboard-hero-copy`: đặt `flex: 1 1 420px; min-width: 300px; max-width: 760px;`.
  3. `.live-indicator` và `.dashboard-date-range`: đặt `white-space: nowrap; flex-shrink: 0;`.
  4. `.dashboard-actions`: đặt `flex-wrap: wrap; flex: 1 1 380px; justify-content: flex-end; max-width: 100%;`.
  5. Thêm breakpoint `@media (max-width: 1250px)` để hero tự động chuyển hàng nút xuống dưới gọn gàng, nút không bao giờ bị cắt cụt.
- **Quy tắc kiểm thử phòng ngừa (Verification Checklist):** Kiểm tra giao diện ở các độ phân giải laptop 1280px, 1366px, 1440px và 1920px; badge dữ liệu vận hành giữ nguyên 1 dòng; tiêu đề hiển thị thoáng đãng; toàn bộ 6 nút thao tác hiển thị đầy đủ và không bị tràn.

### ERR-029: Locator label select không khớp dù combobox hiện đúng (29/10/2026)
- Hiện tượng: CUA Playwright getByLabel('Loại công việc', exact=True).selectOption không tìm thấy bộ lọc, không có dữ liệu nào bị sửa.
- Nguyên nhân gốc rễ: Bộ chọn label không khớp trong runtime hiện tại; DOM snapshot vẫn cung cấp combobox có accessible name đúng.
- Anti-Pattern: Lặp locator timeout hoặc click tọa độ đoán khi chưa xem lại DOM.
- Permanent Solution: Đọc DOM snapshot mới; dùng getByRole('combobox', name='Loại công việc', exact=True), đã chọn thành công procurement và xác minh kết quả 3/27 cho tìm SEIYO.
- Verification Checklist: Kiểm tra kết quả lọc và tiêu đề chi tiết sau thao tác; chỉ thao tác bộ lọc, không bấm xác nhận nghiệp vụ trong DB thật.

### ERR-030: Đọc file Google Sheets xuất Excel gặp ngày lỗi và tổng thiếu dòng (29/10/2026)
- Hiện tượng: openpyxl cảnh báo date serial vượt giới hạn; ô ngày thành #VALUE!; tổng cuối bảng bỏ sót dòng mới, khoản thu lệch 0,08 VND.
- Nguyên nhân gốc rễ: định dạng ngày áp vào số 6686367/6686371; công thức tổng cố định đến dòng45; công thức đã thu cộng thêm tỷ lệ VAT.
- Anti-Pattern: Ép ô lỗi thành ngày, tin tổng cuối bảng, nhập dòng trùng, suy diễn trạng thái chữ thành tiền thực nhận.
- Permanent Solution: Đọc giá trị và kiểm tra công thức nguồn; giữ lỗi ở ghi chú; chỉ nhận ngày hợp lệ; đối soát theo từng dòng, tính nợ bằng phải thu trừ đã thu, ghi nhận mọi điều chỉnh; chỉ loại trùng có căn cứ sau chỉ thị người dùng. Script scripts/import_qlda_trang_2026.py sao lưu và dùng transaction, kiểm tra nguyên vẹn nghiệm thu.
- Verification Checklist: Chạy trên DB bản sao trước; Darfon loại2 dòng trùng; kiểm tra row count, tổng từng khoản, foreign_key_check, integrity_check; hash toàn bộ file nghiệm thu trước/sau bằng nhau.

### ERR-031: UnicodeEncodeError khi in dữ liệu Việt–Trung trên Python Windows (29/10/2026)
- Hiện tượng: stdout cp1252 không in được tên sheet tiếng Việt/Trung; lệnh đọc dừng trước khi sửa dữ liệu.
- Nguyên nhân gốc rễ: Python runtime Windows chọn cp1252 cho stdout dạng pipe.
- Anti-Pattern: In trực tiếp chuỗi Unicode mà chưa khai báo encoding trong môi trường pipe Windows.
- Permanent Solution: sys.stdout.reconfigure(encoding='utf-8') trước khi in. Không thay nội dung nguồn để tránh lỗi hiển thị.
- Verification Checklist: Đọc đủ tên sheet và các dòng song ngữ, exit0; file nguồn không thay đổi.

### ERR-032: Tệp nhắc nhở còn trên D nhưng liên kết lưu ổ E (29/10/2026)
- Hiện tượng: Mở/tải PDF trong nhắc nhở báo tệp không còn tồn tại dù file vẫn còn.
- Nguyên nhân gốc rễ: custom_reminders.attachment_path, folder_path và attachments JSON còn giữ root E:\Working sau chuyển workspace sang D:\Working.
- Anti-Pattern: Kết luận mất file chỉ từ đường dẫn cũ; chỉ sửa attachment_path mà bỏ qua attachments JSON.
- Permanent Solution: Kiểm tra đúng tệp ở workspace hiện tại, sao lưu SQLite, cập nhật đồng bộ đường dẫn chính, thư mục và từng đính kèm theo file đã xác minh. Không tìm đại file cùng tên để thay thế.
- Verification Checklist: Cả endpoint tải chính, tải theo index và preview trả HTTP200, application/pdf và byte giống file gốc; integrity_check=ok. Không sửa nội dung PDF hay dữ liệu nghiệm thu.

### ERR-033: Chuyển máy còn đường dẫn cố định trong DB, JSON và cấu hình xuất (29/10/2026)
- Hiện tượng: Nhiều hồ sơ/ảnh đính kèm không tải được, form xuất file vẫn trỏ ổ E hoặc user BANG.
- Nguyên nhân gốc rễ: Đường dẫn tuyệt đối tồn tại trong documents, custom_reminders JSON, payment_voucher_requests và mặc định form/Google/scripts; localStorage giữ thư mục máy cũ. Server khởi động PM_PORTAL_RELOAD=0 nên đổi Python phải khởi động lại.
- Anti-Pattern: Chỉ thay đường dẫn chính, tìm đại file cùng tên hoặc thay toàn bộ chữ trong DB; dùng runtime bundled để chạy pytest khi runtime đó không có pytest. Lặp glob path* theo Bash trên PowerShell; dùng rg thư mục với -g, hoặc đường dẫn tệp cụ thể. Mọi script kiểm tra Unicode phải cấu hình stdout UTF-8.
- Permanent Solution: workspace_path_service chỉ sửa cột path/JSON và chỉ khi tồn tại đúng đích dưới workspace/profile; không đổi tiền/ghi chú; backup SQLite, transaction, chặn thoát thư mục, idempotent; chạy khi khởi động. Form dùng root từ config, script tự nhận root, tài khoản theo Path.home. Dùng Python312 đang có pytest; restart riêng tiến trình run.py đã xác minh, chạy ẩn rồi kiểm tra HTTP.
- Verification Checklist: 15 test đạt; 36 script parse thành công, helper trả đúng workspace; 115 tệp hồ sơ giữ nguyên hash; dữ liệu hợp đồng/AR/mốc không thay đổi; 10 path sửa, 2 tệp thiếu để nguyên có báo cáo; kiểm tra form, tải hồ sơ và preview nhắc nhở trên server thật; chạy lại migration không phát sinh thay đổi.

### ERR-034: Nhấp tên dự án trên biểu đồ không có chi tiết (29/10/2026)
- Hiện tượng: Tooltip mời nhấp xem dự án nhưng không mở nội dung.
- Nguyên nhân gốc rễ: showProjectDetailCard truy cập projectDetailHoverCard/projCard* không có trong HTML; sau khi bổ sung khung, phát hiện formatCurrencyVN không tồn tại (hàm đúng formatVND). Bộ chọn selected-active dùng class cũ coord-y-label-box.
- Anti-Pattern: Chỉ kiểm tra handler onclick tồn tại mà chưa nhấp thực tế; thiếu DOM đích, dùng tên hàm không có, card không có vị trí cố định hoặc bị khuất dưới fullscreen. Locator getByText có thể khớp cả tiêu đề card ẩn; dùng .coord-y-label.filter(hasText) cho nhãn biểu đồ.
- Permanent Solution: Thêm khung chi tiết đầy đủ ID, màu chữ dễ đọc, vị trí giữa màn hình có giới hạn chiều cao/cuộn; chuyển khung ra body tránh stacking/overflow; dùng formatVND; đồng bộ selected class; Esc đóng card trước fullscreen.
- Verification Checklist: Trình duyệt thật nhấp cả biểu đồ trái/phải hiện đúng mã và tiền/đợt; đóng bằng nút, Esc và nhấp lại; Esc giữ biểu đồ mở; Node syntax check đạt; ảnh xác minh .qa/project_detail_verified.png. Không sửa dữ liệu tài chính trong tác vụ này.

### ERR-035: Hai biểu đồ không cuộn đồng bộ (29/10/2026)
- Hiện tượng: Cuộn biểu đồ trái/phải không kéo biểu đồ đối diện theo.
- Nguyên nhân gốc rễ: setupSynchronizedScrollAndHover tìm prevChartScroll/currChartScroll đã bị đổi tên; HTML thực tế dùng leftBarsScrollArea/rightBarsScrollArea nên hàm thoát trước khi gắn sự kiện.
- Anti-Pattern: Giữ selector cũ sau đổi layout; dùng cờ bật/tắt đồng bộ tức thì cho sự kiện scroll phát bất đồng bộ.
- Permanent Solution: Gắn onscroll đúng hai vùng cuộn, cập nhật scrollTop đối diện chỉ khi chênh hơn0,5px để tránh vòng lặp; gắn lại sau render bằng thuộc tính onscroll nên không nhân listener, căn lại vị trí khi tải dữ liệu.
- Verification Checklist: Node syntax check đạt; UI thật cuộn trái xuống cả hai54,4px; cuộn phải lên cả hai0px; cuộn phải xuống cả hai187,2px; ảnh .qa/chart_scroll_synced.png. Không thay dữ liệu nghiệp vụ.

### ERR-036: Lịch thiếu đợt bị kéo thành100%, tiền đã thu bị tô đỏ do ngày lỗi (29/10/2026)
- Hiện tượng: MES Lite chỉ có55/10 nhưng thanh100%, khoản55đã thu429.841.500đ hiệnđỏ. Vonmax phần cứng/phần mềm bị gộp mã0001 và lặp110triệu.
- Nguyên nhân gốc rễ: width_pct chia tổng các dòng hiện có thay vì tổngHĐ; reconstruct chỉ nhận ngày thu, bỏ tiềnđãthu nếu ngày serial bịlỗi; source dùng sai mãHĐ; base_info làm mất metadata; firstrow sau sắpxếp là cọc mới nên mất tên dựán; formatDateVN từngđượcgọi nhưng không cóhàm.
- Anti-Pattern: Ép các khoản đãliệt kê thành100%, tựđổi tỷlệ hoặc suyngày ngân hàng; dùng mã trùng trong Excel làm căn cứ gộp; tin email mã0012 khi bảnký mã001; xóa AR rồi sync mất paid_by_date/project_group; thử pytest từ cwd khác mà dùng đườngdẫn tests tươngđối.
- Permanent Solution: Đối chiếu file, ảnh người dùng, quy tắc người dùng và mail/hợpđồng. Giữ exact paid_date chỉ khi cócăn cứ; paid_by_date biểu diễn thờiđiểm chậmnhất đãthu. Bổsung cọc35Jinxun/35Vonmax2/40CX; Jinxun55paid29/08 theoảnh. Email16/10 + chuỗi19/09 xácnhận phầncứng0002/545.454.545 và phầnmềm0001/1.100.000.000, chỉcòn10%; lịch sử90gộp ghi rõ khôngphải mộtđợt90, chưa biết tỷlệ từngđợt. Bảnký phase2 xácnhận35/55/10 và mãHMV07032026001. Biểuđồ lấy toànHĐ làm mẫu số, dữliệuthiếu hiệngraygap/cảnhbáo; thứtựđợt tườngminh, khôngsorttheosốtiền. Sync khôngxóa metadata đốisoát. Dùng formatDateVN helper ISO khôngtimezone.
- Verification Checklist: 8test đạt; tấtcảprojectbar100%; Jinxun90,Vonmax2100,CX80,Vonmax0001/0002đều90; khôngcộngtrùng110triệu; gross-received=debt; DB integrity/fk đạt; 115tệp hồsơ giữnguyênhash; xem UIcả3đợt và2đợt xanh đúng; lưu báo cáo và bảnsao DBtrướcghi. Lịch sử90 chưa có ngày thựcnhận vẫn đểpaid_dateNULL.

---

### ERR-037: Đảo ngược sự kiện chuột trái/phải và hover tự động bật card chi tiết đè biểu đồ (29/10/2026)
- **Hiện tượng:** Người dùng lướt chuột qua các thanh công nợ trên biểu đồ thì một chiếc card màu trắng to (~420px) tự động bật lên đè kín màn hình như modal; nhấp chuột trái thì lại ghim xem chi tiết, muốn sửa đợt lại phải nhấp chuột phải, ngược hoàn toàn với thói quen thiết kế ban đầu.
- **Nguyên nhân gốc rễ:** 
  1. Trong commit `4ab6d02`, hàm `onSegmentHoverEnter` được gán thêm logic render và hiển thị `chartSegmentTooltip` khi rê chuột qua bất kỳ thanh khoản nào.
  2. Sự kiện `onclick` bị gán nhầm vào `handleSegmentClick` (mở card chi tiết), trong khi `oncontextmenu` lại gán vào `handleSegmentContextMenu` (mở modal sửa đợt).
  3. Header hint và tooltip title cũng bị ghi ngược: "Chuột trái: Chi tiết | Chuột phải: Sửa đợt".
- **Cách làm SAI trước đó (Anti-Pattern - TUYỆT ĐỐI CẤM LẶP LẠI):** Tự ý gán card chi tiết to lớn vào sự kiện `hover` gây cản trở tầm nhìn của người dùng; hoán đổi phím tắt/sự kiện chuột trái và chuột phải mà không kiểm tra thói quen thao tác UX gốc (Chuột trái thao tác chính: Sửa đợt; Chuột phải tra cứu phụ: Xem chi tiết).
- **Giải pháp ĐÚNG TRIỆT ĐỂ (Permanent Solution):**
  1. `onclick`: Gán `handleSegmentLeftClick` mở ngay Modal Sửa Đợt (`openEditReceivableModal(segId)`).
  2. `oncontextmenu`: Gán `handleSegmentRightClick` mở/ghim Card Chi Tiết (`showSegmentDetailCard(event, segId, side)`), chặn menu ngữ cảnh trình duyệt bằng `event.preventDefault()`.
  3. `onSegmentHoverEnter`: Loại bỏ hoàn toàn việc mở `chartSegmentTooltip` khi hover; chỉ kích hoạt highlight đồng bộ 2 bên (`seg-hover-synced`) và highlight hàng (`onRowHoverEnter`).
  4. Cập nhật đồng bộ các dòng chỉ dẫn ở tiêu đề biểu đồ và thuộc tính `title`: `Chuột trái: Sửa đợt | Chuột phải: Xem chi tiết`.
- **Quy tắc kiểm thử phòng ngừa (Verification Checklist):** 
  1. Rê chuột (hover) qua các thanh: Chỉ sáng màu thanh và hàng, tuyệt đối không xuất hiện card hay modal che khuất biểu đồ.
  2. Nhấp chuột trái: Mở ngay modal Sửa Đợt Công Nợ.
  3. Nhấp chuột phải: Mở Card Chi Tiết Song Ngữ hoặc đóng nếu nhấp lại chính đợt đó; không hiện menu chuột phải của trình duyệt.
  4. Test suite `pytest pm_portal/tests/test_receivables_tracker.py` chạy đạt 100%.


### ERR-038: Nhầm mã nháp, trạng thái hồ sơ và bằng chứng thu tiền khi đối chiếu mail (29/10/2026)
- Hiện tượng: SEIYO có mã Excel/YCTT khác bản ký; MES Lite ghi chưa mở hóa đơn dù thư mới đã gửi hóa đơn; biên bản CX có footer sót mã mẫu Jinxun.
- Nguyên nhân gốc rễ: Nhập ghi chú từ Excel nhưng chưa kiểm tra bản ký và thứ tự thời gian email; chủ đề mail được dùng lại cho khoản khác; tài liệu scan có thể có trang trắng xen kẽ.
- Anti-Pattern: Đổi trạng thái PAID từ thư gửi hóa đơn/YCTT/biên bản hoặc lời hẹn trả; lấy chủ đề mail làm bằng chứng duy nhất; coi thư cũ được trích là trạng thái hiện tại; suy ngày ký từ mã hợp đồng.
- Permanent Solution: Kiểm tra nội dung và tệp đúng dự án, giá trị, mốc; ưu tiên mã bản ký, giữ mã cũ trong ghi chú và tài liệu gốc. SEIYO bản ký HMV04102026SY0001 ngày13/10 thay mã nháp HMV22092026SY0001 trong liên kết hiện hành. Phân biệt số thu từ Excel, suy luận được người dùng duyệt và chứng từ thu độc lập; ghi rõ chưa xác minh khi thiếu bằng chứng.
- Verification Checklist: Sao lưu SQLite; chạy DB bản sao và kiểm tra lặp không nhân ghi chú/tệp; 48 khoản giữ nguyên tiền/ngày thực thu; hồ sơ gốc có hash nguyên vẹn; bản ký liên kết tải được; API trả mã và trạng thái hồ sơ mới.

### ERR-039: Lỗi tiện ích khi kiểm tra tệp/mail trên PowerShell (29/10/2026)
- Hiện tượng: rg nhận đường dẫn chứa wildcard báo123; Python hệ thống thiếu requests; đường API đoán thiếu /v1 trả404.
- Nguyên nhân gốc rễ: Wildcard kiểu Bash không được rg mở rộng; nhầm thư viện giữa runtime Python; không đọc router prefix.
- Anti-Pattern: Dùng đường dẫn file* làm đối số rg; giả định mọi runtime có requests; đoán endpoint.
- Permanent Solution: rg trên thư mục với -g; dùng urllib chuẩn cho HTTP; đọc prefix và route trước khi kiểm tra. Khi web reader không mở được Drive, urllib có thể tải PDF từ URL tải của cùng tệp đã được người dùng cho phép đọc; kiểm tra magic PDF và xem trang thực tế.
- Verification Checklist: Không lộ thông tin đăng nhập; tải đúng PDF; rg exit0; API /api/v1/receivables trả200.

### ERR-040: Ghi chú hợp đồng dài làm bảng công nợ cao quá mức (30/10/2026)
- **Hiện tượng:** Ghi chú dài hiển thị toàn bộ trong ô gộp, gây khó quan sát các khoản thu khác.
- **Nguyên nhân gốc rễ:** receivables_tracker.js render toàn văn với white-space pre-wrap nhưng chưa giới hạn số dòng; CSS chưa có chế độ thu gọn.
- **Anti-Pattern:** Hiển thị toàn bộ ghi chú mặc định và dùng cùng thao tác click cho việc đọc lẫn chỉnh sửa.
- **Permanent Solution:** Mặc định giới hạn hai dòng bằng line clamp và max-height; nhấp để mở rộng/thu gọn, tách nút sửa riêng; sau lưu hoặc lỗi cũng dựng lại chế độ thu gọn. Tăng phiên bản tài nguyên để tải CSS/JS mới.
- **Verification Checklist:** Node kiểm tra cú pháp; kiểm tra mở rộng/thu gọn hai chiều, aria-expanded và escape nội dung đều đạt. Khi kiểm tra giao diện, xác nhận ghi chú dài không tăng chiều cao mặc định, nội dung vẫn xem đầy đủ và ghi chú vẫn gộp theo hợp đồng.

### ERR-041: Thứ tự vùng sửa trong apply_patch (30/10/2026)
- **Hiện tượng:** Bản vá nhiều vùng báo không tìm thấy dòng dù dòng vẫn tồn tại.
- **Nguyên nhân gốc rễ:** Hai vùng sửa trong cùng file được liệt kê ngược thứ tự dòng (2260 trước 1924).
- **Anti-Pattern:** Ghép các hunk theo thứ tự ý tưởng thay vì thứ tự trong file.
- **Permanent Solution:** Sắp vùng sửa theo dòng tăng dần, kiểm tra lại file sau khi công cụ từ chối; không giả định bản vá đã áp dụng một phần.
- **Verification Checklist:** Đọc lại đúng vùng, áp dụng bản vá đã sắp thứ tự, kiểm tra cú pháp JavaScript.

### ERR-042: Đổi số đợt chưa cập nhật theo thao tác nhập (30/10/2026)
- **Hiện tượng:** Ô số đợt hiển thị 4 nhưng bản nháp vẫn có 3 đợt trong kiểm thử trình duyệt.
- **Nguyên nhân gốc rễ:** contract_schedule_editor.js chỉ gắn onchange; thao tác nhập của trình duyệt kiểm thử phát input nhưng chưa phát change như dự kiến.
- **Anti-Pattern:** Chỉ dựa vào onchange và cho rằng đổi giá trị đã cập nhật mô hình dữ liệu.
- **Permanent Solution:** Gắn thêm input có debounce 400ms, xử lý change ngay; trước khi lưu đồng bộ số đợt, khi đóng hủy bộ đếm. Giữ bản nháp tách dữ liệu đã lưu.
- **Verification Checklist:** Nhập số đợt, kiểm tra số hàng/thanh chia và tổng 100%; Hủy rồi mở lại phải giữ dữ liệu gốc; không lưu thử lên dữ liệu thật.

### Cập nhật quy tắc thao tác biểu đồ theo yêu cầu ngày 30/10/2026
- Yêu cầu mới thay thế thao tác của ERR-037: bấm tên mở duy nhất cửa sổ hợp đồng; các thanh đợt bỏ onclick/oncontextmenu, chỉ hiện thông tin nhỏ khi hover.
- Cửa sổ chung có bản nháp, số đợt, thanh phân bổ nhiều điểm chia, giá trị hợp đồng và trạng thái/tiền/ngày thu; chỉ ghi sau Lưu.
- Lưu trong một transaction, kiểm tra tổng 100%, làm tròn tiền có bù đợt cuối, giữ tiền thực thu, bảo vệ lịch sử và hồ sơ liên kết, kiểm tra phiên bản chống ghi đè dữ liệu mới.
- Xác minh: 18 kiểm thử đạt trên DB tạm; trình duyệt thật kiểm tra mở một lần, phân bổ 1 tỷ, kéo tỷ lệ, thu một phần, đổi 3 thành 4 đợt, Hủy mở lại giữ nguyên dữ liệu; thanh biểu đồ không còn handler trái/phải. Ảnh: .qa/contract_schedule_editor_verified.png. Không lưu bản nháp thử vào công nợ thật.

### ERR-043: Cửa sổ hợp đồng dính góc trên trái (30/10/2026)
- **Hiện tượng:** Dialog mở lệch sát góc trên trái, không có khoảng thở đều quanh màn hình.
- **Nguyên nhân gốc rễ:** contract_schedule_editor.css dòng 1 chưa đặt rõ margin auto, position fixed và inset; phụ thuộc định dạng mặc định của dialog trong trang.
- **Anti-Pattern:** Chỉ đặt width/max-height rồi coi dialog đã được căn giữa; ảnh kiểm tra cũ cũng dính góc nhưng chưa phát hiện.
- **Permanent Solution:** Khai báo fixed/inset 0/margin auto, box-sizing border-box, giới hạn chiều rộng và chiều cao theo viewport trừ 48px; giữ header/footer, chỉ cuộn vùng nội dung; tăng phiên bản CSS 6.1.
- **Verification Checklist:** Trình duyệt thật đo trái/phải/trên/dưới đều 24px ở viewport 1280x720; nội dung cuộn bên trong và nút Lưu vẫn thấy. Ảnh .qa/contract_schedule_centered.png. Không sửa số liệu hợp đồng.

### ERR-044: Đồng bộ cuộn biểu đồ phản hồi chậm ở hai đầu (30/10/2026)
- **Hiện tượng:** Người dùng thấy cuộn đầu/cuối danh sách hai biểu đồ chậm hơn giữa danh sách.
- **Nguyên nhân gốc rễ:** setupSynchronizedScrollAndHover dùng hai onscroll ghi scrollTop qua lại; cuộn mượt mặc định có thể bị vị trí phản hồi bên kia ngắt. Hover dựng tooltip trong lúc cuộn còn gây thêm công việc.
- **Anti-Pattern:** Cho hai animation cuộn tự chạy rồi dùng các sự kiện cuộn bất đồng bộ để kéo lẫn nhau, chỉ dựa vào ngưỡng chênh0,5px.
- **Permanent Solution:** Một wheel handler tính vị trí cho cả hai bên với cùng delta, chặn animation mặc định; chuẩn hóa deltaMode, giới hạn vùng cuộn, bỏ qua sự kiện phản hồi do đồng bộ. Giữ đồng bộ kéo scrollbar; không nhân listener khi tải lại; tạm ẩn tooltip khi cuộn. CSS scroll-behavior auto và overscroll contain.
- **Verification Checklist:** Node kiểm tra cú pháp; kiểm tra cùng delta120px ở đầu/giữa/cuối, đảo chiều từ đáy, cuộn từ hai bên, delta theo dòng, đồng bộ kéo scrollbar và gọi setup nhiều lần đều đạt.
- **Lưu ý công cụ:** apply_patch không nhận hai thao tác Update File cho cùng một file trong một bản vá; gộp các hunk theo thứ tự dòng tăng dần trước khi áp dụng.

### ERR-045: Trích xuất bộ hồ sơ nhiều định dạng trên Windows (30/10/2026)
- **Hiện tượng:** In tên tiếng Việt/Trung từ Python stdin gặp UnicodeEncodeError; truy vấn max_row của workbook read_only gặp None và gây TypeError.
- **Môi trường:** PowerShell, Python312; workbook xuất từ phần mềm văn phòng không luôn có dimension trong XML.
- **Nguyên nhân gốc rễ:** stdout mặc định cp1252; giả định ws.max_row luôn là số trong chế độ read_only.
- **Anti-Pattern:** In Unicode khi chưa cấu hình UTF-8; làm phép tính với max_row mà không kiểm tra; xuất toàn bộ danh sách tệp dài ra console gây mất nội dung do cắt output.
- **Permanent Solution:** sys.stdout.reconfigure(encoding='utf-8'); trích read_only bằng iter_rows, khi cần vị trí cuối dùng workbook thường cho file chọn lọc hoặc xử lý dimension thiếu; lưu inventory và text riêng, chỉ in tóm tắt có giới hạn. Dùng runtime do loader trả về.
- **Verification Checklist:** Toàn bộ inventory hoàn tất, không lỗi trích xuất với định dạng hỗ trợ; hash nguồn không thay đổi; scan được đánh dấu chưa đọc chữ, không kết luận nội dung hay chữ ký từ tênfile.

### ERR-046: Nhập nhầm số đã gồm VAT làm cơ sở chưa thuế (30/10/2026)
- **Hiện tượng:** Tổng khoản thu trên hệ thống vượt tổng đã ký dù tỷ lệ các đợt cộng đúng100%.
- **Nguyên nhân gốc rễ:** Nguồn tổng đã gồmVAT được gán vào total_contract_amount/net_amount rồi tínhVAT lần nữa trong quá trình nhập.
- **Anti-Pattern:** Tin nhãn cột hoặc tênfile mà không kiểm tra bảng tiền và câu xác nhận gồm/chưa thuế trong bản ký; tự giảm tiền thực nhận để khớp cơ sở mới.
- **Permanent Solution:** Đối chiếu bảnký: net + VAT = gross; ghi rõ tax basis khi nhập; tách sửa phải thu khỏi đối chiếu thực nhận. Chỉ đề xuất thay đổi có nguồn trang/ô, không sửa dữ liệu sống trong tác vụ rà soát.
- **Verification Checklist:** Đối chiếu tổngHĐ và từng đợt, số tiền bằng chữ, thuế đãgồm/chưa; kiểm chứng cọc/ngày thực nhận riêng; không đổi tiền ngân hàng theo công thức suy ra.


### ERR-047 — Thuộc tính viền ô gộp Excel có thể rỗng (2026-10-30)
- **Môi trường:** Windows, Python, openpyxl; đọc workbook có ô gộp.
- **Hiện tượng:** AttributeError khi đọc border.left.style.
- **Nguyên nhân gốc rễ:** Cạnh viền của một số ô/ô gộp là None.
- **Anti-Pattern:** Giả định mọi cạnh viền luôn có đối tượng Side.
- **Giải pháp:** Dùng getattr(side, 'style', None); chỉ đọc thuộc tính cần thiết khi kiểm tra màu lịch.
- **Kiểm thử phòng ngừa:** Đọc cả ô thường và ô gộp; kiểm tra lịch màu hoàn tất không lỗi. Lần kiểm tra lại đã đọc thành công các hàng công việc và chú giải màu.


### ERR-048 — Bộ lọc cần chú ý lấy cả khoản chưa kích hoạt (30/10/2026)
- **Hiện tượng:** Dự án chưa đến mốc thanh toán và không biến động vẫn xuất hiện ở Cần chú ý.
- **Nguyên nhân:** receivables_service.py và receivables_tracker.js cộng has_unstarted_next vào is_active_attention/isActive.
- **Anti-Pattern:** Đồng nhất thiếu ngày bắt đầu với quá hạn hoặc biến động.
- **Giải pháp:** Chỉ lấy biến động, đến hạn và quá hạn; giữ bộ lọc chưa bắt đầu riêng; tăng phiên bản JS6.4.
- **Kiểm thử:** 7 kiểm thử lịch đạt, bao gồm trường hợp PENDING thiếu ngày phải bị loại khỏi Cần chú ý; kiểm tra cú pháp JS và dữ liệu thực tế. Khi dùng rg trên Windows, truyền thư mục và -g thay vì wildcard trong đoạn đường dẫn.

### ERR-049: Kiểm tra font và bảng native khi thiết kế lại PPTX (30/10/2026)
- Môi trường: Windows, Artifact Tool JavaScript, PowerPoint16.
- Hiện tượng: Finalizer từ chối bảng thiếu policy theo từng slide; font thực tế vẫn Aptos khi đặt fontFamily; bước import con thiếu RUNTIME_NODE_MODULES.
- Nguyên nhân gốc rễ: Table owner phải khai báo cả requiredNativeTableOwnerSlides và layoutArgs; text.style dùng typeface; runtime con không kế thừa junction node_modules như biến môi trường.
- Anti-Pattern: Đoán tên tệp tài liệu API; dùng fontFamily trong text.style; chỉ kiểm tra ảnh xem trước mà bỏ font thực trong PPTX.
- Giải pháp: Dò tài liệu bằng rg --files, dùng tables.spec.md/rich-text.spec.md; đặt typeface rõ cho Latin và CJK; truyền --require-native-table-slide cho từng bảng; khai báo RUNTIME_NODE_MODULES theo loader. Không đổi skill hoặc thư viện bundled.
- Kiểm thử: Finalizer không finding/warning, import thành công11slide, hai bảng chỉnh sửa được; mở và xuất11PNG trong PowerPoint, đọc từng slide; đối chiếu toàn bộ mô tả công việc nguồn; bản gốc giữ nguyên, bản mới lưu riêng cạnh nguồn.


### ERR-050 — Thanh Header Biểu Đồ So Sánh Công Nợ Tuần Bị Chiếm Nhiều Dòng & Bị Ghi Đè Màu Đen (30/10/2026)
- **Hiện tượng:** Phần đầu modal `#modalWeeklyComparisonFullscreen` (`/receivables`) bị phình to thành 4 dòng (~180px chiều cao), ô tìm kiếm `#compSearch` tràn hết 1 dòng riêng, và nền màu đen tối (`#091124`, `#16223B`, `#0B132B`) gây nặng nề.
- **Nguyên nhân gốc rễ:**
  1. Ô tìm kiếm `#compSearch` và các select/input gắn class `.form-control` và `.btn` của `components.css` (vốn áp `width: 100%` và `height: 40px`), khiến `#compSearch` tự đẩy xuống chiếm trọn một hàng ngang.
  2. File `receivables_tracker.css` có các khối CSS trùng lặp ở cuối file (dòng ~2908 và ~3403) dùng `!important` với mã màu tối (`#091124`, `rgba(15, 23, 42, 0.75) !important`, `#16223B !important`) ghi đè lên các khai báo giao diện sáng ở đầu file.
- **Cách làm SAI trước đó (Anti-Pattern - TUYỆT ĐỐI CẤM LẶP LẠI):** Dùng chung `.form-control` (`width: 100%`) cho thanh công cụ ngang (inline toolbar) và chỉ sửa CSS ở khối đầu file mà không kiểm tra các khối override `!important` ở cuối file.
- **Giải pháp ĐÚNG TRIỆT ĐỂ (Permanent Solution):**
  1. Tách class riêng `.comp-input-compact`, `.comp-select-compact`, `.comp-chart-search`, `.btn-comp-snapshot`, `.btn-comp-close` với chiều cao đồng nhất `28px`, đặt `.comp-chart-search { flex: 1 1 180px !important; max-width: 280px !important; }` để toàn bộ bộ lọc + tìm kiếm + nút nguồn dữ liệu nằm gọn trên 1 hàng ngang duy nhất.
  2. Đồng bộ toàn bộ các khối `.weekly-comp-header*`, `.comp-control-group`, `.comp-source-switch-group` ở cả đầu và cuối file `receivables_tracker.css` sang tông sáng thanh lịch (`#FFFFFF` / `#F8FAFC` / `#F1F5F9`, viền `#CBD5E1` / `#E2E8F0`, chữ `#0F172A` / `#334155`), tăng version cache-busting lên `v=7.0`.
- **Quy tắc kiểm thử phòng ngừa (Verification Checklist):** Kiểm tra toàn bộ file CSS xem còn sót selector trùng lặp có `!important` ở cuối file không; xác nhận header của `#modalWeeklyComparisonFullscreen` chỉ gói gọn trong 2 hàng mảnh (~72px) và hiển thị nền sáng đồng bộ.

- ERR-045 tái kiểm ngày 30/10/2026: Python bundled vẫn dùng cp1252 khi gọi -c; đọc Excel tiếng Việt gặp UnicodeEncodeError. Bắt buộc đặt -X utf8 ngay khi gọi Python. Đã đọc lại bằng -X utf8 thành công.

### ERR-SEIYO-20261030 — Chữ hai dòng vượt chiều cao mẫu Invoice
- Môi trường: Windows, Artifact Tool; mẫu Invoice Seiyo có các dòng cao 18,6–21pt.
- Hiện tượng: Mô tả Việt–Trung bị cắt khi chèn dấu xuống dòng.
- Nguyên nhân gốc rễ: Nội dung mới cần hai dòng trong khi chiều cao gốc chỉ đủ một dòng.
- Anti-Pattern: Ghi mô tả hai dòng vào mọi hàng và bỏ qua ảnh kiểm tra.
- Giải pháp: Giữ nguyên chiều cao/bố cục; dùng một dòng Việt / Trung ở các hàng thấp, rút gọn tên nhóm nhưng giữ model, quy cách và mô tả chi tiết nguồn trong trường chi tiết sẵn có.
- Verification Checklist: Đã render lại vùng thân, tổng tiền và đầu trang; không còn chữ cắt ở các dòng sửa. Đã đối chiếu tổng tiền, số hạng mục, ô gộp, chiều rộng cột và chiều cao dòng với mẫu; cân nặng chưa có được để trống.

### ERR-SEIYO-GROUPS-20261030 — Chia mục theo số dòng mẫu thay vì danh mục mới
- Môi trường: Invoice Excel Seiyo, mẫu cũ có 6 hạng mục phần cứng; nguồn mới có 10.
- Hiện tượng: Tiêu đề danh mục lặp sau hạng mục 6, chia sai nhóm; lần thử di chuyển dòng chưa dịch công thức khiến tổng tạm bị lệch.
- Nguyên nhân gốc rễ: Giữ cứng vị trí tiêu đề mẫu, sau đó thay địa chỉ ô nhưng chưa đổi tham chiếu công thức cùng dòng.
- Anti-Pattern: Dùng số dòng hoặc số sản phẩm mẫu để quyết định nhóm; di chuyển ô công thức mà không dịch tham chiếu.
- Giải pháp: Chia nhóm theo nguồn khách mua: 10 phần cứng, 11 vật tư/thi công; di chuyển tiêu đề cùng style và cập nhật tham chiếu công thức cùng tổng cộng.
- Verification Checklist: Kiểm tra STT1–10 trước tiêu đề2; STT11–21 sau tiêu đề2; từng thành tiền tham chiếu đúng đơn giá cùng dòng; tổng độc lập và công thức đều là712.020.000đ. Bản v2 đã kiểm chứng.

### ERR-SEIYO-BLANK-ROWS-20261030 — Giữ thừa dòng bảng trống của mẫu
- Môi trường: Invoice/Packing List Seiyo Excel.
- Hiện tượng: Hết sản phẩm còn8dòng có viền trống trước tổng cộng ở cả hai file.
- Nguyên nhân gốc rễ: Hiểu sai “dựa trên mẫu” thành giữ nguyên số dòng mẫu, mặc dù dữ liệu mới ít hơn.
- Anti-Pattern: Giữ dòng dự phòng và vị trí tổng cố định theo mẫu; chỉ xóa giá trị mà không bỏ khung bảng dư.
- Giải pháp: Số dòng bảng phải khớp số hạng mục thực tế. Tổng ngay sau hạng mục cuối; thu gọn ô gộp, công thức, phần ký và vùng in theo dữ liệu. Chỉ giữ nguyên hình thức có ích; yêu cầu người dùng mới được ưu tiên hơn quy tắc giữ bố cục mẫu.
- Verification Checklist: Invoice21hạng mục, tổng ở dòng55 ngay sau hạng mục21 tại54; PKL20hạng mục, tổng33 ngay sau hạng mục20 tại32; chữ ký35–37; không còn viền bảng trống bên dưới; tổng712.020.000đ, trọng lượng trống; đã kiểm tra ảnh cả hai và vùng in.

### ERR-SEIYO-HEADER-20261030 — Tự sửa tiêu đề và để lặp khối thông tin đầu
- Môi trường: Excel Invoice/Packing List Seiyo trên Windows.
- Hiện tượng: Tiêu đề khác mẫu do thêm DỰ THẢO/草稿; Invoice hiển thị hai khối công ty/khách hàng.
- Nguyên nhân gốc rễ: Mẫu có khối đầu dư ngoài vùng in; đã chỉ kiểm tra khối in và tự thêm nhãn.
- Anti-Pattern: Đổi tiêu đề không được yêu cầu; bỏ qua phần đầu hiển thị khi mở Excel; giữ nhiều bản sửa sai.
- Giải pháp: Khôi phục tiêu đề/style đúng mẫu; bỏ15dòng đầu dư và dịch công thức, ô gộp, vùng in; giữ ngày30/10 và bảng khớp số hàng. Theo yêu cầu xóa bản sai, chỉ đóng workbook sai trong thư mục kết quả rồi xóa, không đụng file nguồn.
- Verification Checklist: INVOICE đúng một lần; Packing List đúng tiêu đề mẫu; không có DỰ THẢO; số hạng mục21/20, tổng712.020.000đ; ảnh đầu/cuối đã kiểm tra; thư mục chỉ còn2file Excel cuối.
- Lưu ý khóa file: Remove-Item thất bại khi bản cũ đang mở. Windows PowerShell5.1 GetActiveObject Excel cho phép đóng đúng workbook đích và xóa thành công; không kết thúc toàn bộ tiến trình Excel hoặc đóng workbook khác.

### ERR-SHIPPING-AI-20261030 — Kiểu ghi chú AI và nhận diện nhóm hàng
- Môi trường: PM Portal Python3.12, Gemini đa phương thức, mẫu Excel nhiều cột.
- Hiện tượng: AI trả notes dưới dạng list thay vì string; dùng cột loại từng sản phẩm làm nhóm, dẫn tới tiêu đề nhóm lặp mỗi sản phẩm.
- Nguyên nhân gốc rễ: Ngữ cảnh notes là mảng và hướng dẫn group chưa phân biệt tiêu đề khối gộp với cột Hạng Mục.
- Anti-Pattern: Chỉ dựa schema mô tả mà không kiểm tra AI thực tế; coi đủ số dòng/đúng tổng là đã đúng cấu trúc.
- Giải pháp: Chuẩn hóa danh sách ghi chú string thành text; prompt group chỉ lấy tiêu đề khối lớn, không lấy cột loại sản phẩm. Tên Việt phải dịch từ nguồn Trung nếu cần. Bổ sung cảnh báo giá/khối lượng thiếu hoặc mâu thuẫn. Ưu tiên model lite từ cấu hình chung, vẫn dự phòng model/key hiện hành.
- Verification Checklist: Lượt gọi Gemini thật với3file xác minh21/20dòng,2nhóm lớn, tổng712.020.000đ, không lấy cân nặng mẫu. Unit test notes-list và multi-source; kiểm tra trực quan kết quả thực tế.

### ERR-SHIPPING-EXPORT-20261030 — Vùng in mất và số nguyên có dấu thập phân thừa
- Môi trường: Artifact Tool XLSX export trên Windows.
- Hiện tượng: Export lại file căn giữa không giữ print area; định dạng0.### hiển thị7. và đơn giá có dấu chấm thừa; phương thức vận chuyển dài có thể tràn cột PKL.
- Nguyên nhân gốc rễ: Defined names không được giữ qua export này; optional-decimal format có hành vi hiển thị dấu chấm; ô Shipment G10 chưa wrap/gộp theo chiều rộng.
- Anti-Pattern: Tin rằng export giữ toàn bộ metadata; dùng một numberFormat cho cả số nguyên và số lẻ; không kiểm tra file thực tế của AI.
- Giải pháp: Sau export chỉ vá metadata print area khớp dòng cuối; chọn format nguyên hoặc thập phân theo dữ liệu; wrap/gộp Shipment G10:H11; tính chiều cao theo text CJK/VN và chặn ô quá dài vượt chiều cao Excel.
- Verification Checklist: Test print_area không rỗng và khớp lastRow; kiểm tra ảnh cả2file từ AI thật; tổng và công thức/trọng lượng đúng, không dòng thừa. DESCRIPTION căn giữa ngang/dọc cả bản hiện tại và mọi lần xuất mới.

### ERR-WPS-LOCK-20261030 — Nhận nhầm WPS là Microsoft Excel khi xóa bản cũ
- Môi trường: Windows, WPS Office et.exe/wps.exe; file XLSX đang mở.
- Hiện tượng: File bị khóa, GetActiveObject Excel không đóng được; ROT trả đối tượng WPS và COM có thể bị Call was rejected by callee.
- Nguyên nhân gốc rễ: Ứng dụng mặc định mở XLSX là WPS, không phải Excel; window có thể minimized hoặc bị đóng trong lúc kiểm tra.
- Anti-Pattern: Giả định tất cả XLSX đang mở thuộc Excel; nuốt lỗi COM và coi file đã đóng; dùng window ID sau khi cửa sổ thay đổi.
- Giải pháp: Xác định ứng dụng từ inventory; chỉ thao tác đúng cửa sổ quan sát được; không đóng tiến trình hàng loạt. Khi cửa sổ biến mất, thử xóa đúng file cũ đã được người dùng chỉ định và xác minh danh sách còn lại. Không đụng ba file nguồn.
- Verification Checklist: Hai bản cũ đã xóa thành công; thư mục kết quả chỉ còn Invoice/PKL căn giữa, có vùng in và tổng tiền đúng. Khi ghi kiểm thử app.routes ở FastAPI mới, dùng TestClient kiểm tra HTTP thay vì giả định mọi phần tử đều có thuộc tính path.

### ERR-011: GITHUB PUSH PROTECTION CHẶN SECRET TRONG CODE
- **Môi trường:** Git push lên GitHub repository công khai (`https://github.com/Bang334/Working.git`).
- **Hiện tượng:** `git push` thất bại với thông báo `remote: error: GH013: Repository rule violations found for refs/heads/main ... Push cannot contain secrets` do có chuỗi API key GCP/Gemini (`AQ.Ab8...`) trong file Python.
- **Nguyên nhân gốc rễ:** Script `ai_contract_parser.py` và `test_gemini_keys.py` khai báo trực tiếp danh sách chuỗi API key dự phòng thay vì đọc từ `database/local_gemini_keys.json` (file đã được `.gitignore` bảo vệ).
- **Cách làm SAI trước đó (TUYỆT ĐỐI CẤM LẶP LẠI):** Gán trực tiếp chuỗi khóa bí mật vào mảng `DEFAULT_GEMINI_KEYS = ["AQ.Ab8..."]` trong code được Git theo dõi.
- **Giải pháp ĐÚNG TRIỆT ĐỂ:** Luôn import cấu hình từ `app.config` hoặc đọc an toàn từ file ignore `database/local_gemini_keys.json` / biến môi trường `GEMINI_API_KEY`. Tuyệt đối không hardcode bí mật vào bất kỳ file nào đẩy lên GitHub.
- **Verification Checklist:** Quét `grep_search` kiểm tra từ khóa `AQ.Ab8` và `AIzaSy` trước khi commit/push; chạy `git push --dry-run` để đảm bảo không bị chặn bởi GitHub Secret Scanning.

### ERR-012: LỖI WINDOW STATION SHUTDOWN KHI CHẠY SUB-SHELL
- **Môi trường:** Windows 10/11, PowerShell qua agent task runner.
- **Hiện tượng:** Công cụ `run_command` báo lỗi: `CreateDesktop: {DLL Initialization Failed} The application failed to initialize because the window station is shutting down.`
- **Nguyên nhân gốc rễ:** Phiên làm việc Windows của máy tính người dùng đang trong trạng thái đăng xuất (logoff), khóa màn hình (lock) hoặc hệ thống đang chuẩn bị khởi động lại/tắt máy, làm giải phóng trạm làm việc (Win32 window station).
- **Giải pháp ĐÚNG TRIỆT ĐỂ:** Lưu lại toàn bộ mã nguồn an toàn trên đĩa; cung cấp ngay các câu lệnh ngắn gọn để người dùng hoặc agent thực thi tiếp ngay khi phiên Windows hoạt động trở lại.

