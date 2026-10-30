---
name: hongming-pm-hub
description: >-
  Comprehensive operational skill for Project Management (PM) at Hong Ming Global (CÔNG TY TNHH TOÀN CẦU HONG MING).
  Use this skill whenever the user needs assistance with:
  1) Preparing or reviewing bilingual Vietnamese-Chinese Quotations (報價單) and Contracts (買賣合約).
  2) Drafting Acceptance & Handover Minutes (驗收暨移交使用確認書) across project milestones (30%, 40%, 100% FAC).
  3) Tracking project milestones, lead times (60-80 days delivery), and on-site implementation schedules.
  4) Managing Procurement & Purchase Orders (PO / 採購單) for hardware (Gateways, Servers, Sensors, Cables) and import/export paperwork.
  5) Tracking payment milestones, issuing Payment Requests (付款申請書), calculating aging receivables, and writing professional bilingual payment reminders (催款函).
  6) Generating weekly/monthly PM status reports for company executives (CEO Tang Wei Li and PM Leads).
---

# Hong Ming Project Management Hub (PM Hub)

Kỹ năng này trang bị đầy đủ quy trình tác nghiệp, biểu mẫu chuẩn song ngữ (Việt - Trung), cẩm nang kiểm soát rủi ro và các kịch bản tự động hóa hỗ trợ Quản lý Dự án (PM) tại **Công ty TNHH Toàn Cầu Hong Ming**.

---

## 1. CÁC NĂNG LỰC TÁC NGHIỆP CỐT LÕI (WORKFLOWS)

Khi người dùng yêu cầu thực hiện một nhiệm vụ, hãy kích hoạt quy trình tương ứng dưới đây:

### Workflow 1: Lập & Kiểm Tra Báo Giá (Quotation / 報價單)
- **Mục tiêu:** Tạo hoặc rà soát báo giá thiết bị IoT, hệ thống tiết kiệm năng lượng (EMS), bản quyền phần mềm, hoặc gói nhân công thi công.
- **Tài liệu tham khảo:**
  - Báo giá EMS/IoT Hong Ming: [quotation_sample.md](./resources/quotation_sample.md) & Bảng giá gốc [`HM浤詺資訊_Vonmax弘聲 機聯網暨工廠節能 第二階段 硬體報價單_202603_V1.5.xlsx`](file:///e:/Working/HM浤詺資訊_Vonmax弘聲%20機聯網暨工廠節能%20第二階段%20硬體報價單_202603_V1.5.xlsx).
  - Báo giá chuẩn ECO PRIME (Đồng hồ điện, Gateway CC2051, biến dòng Rogowski): Mẫu phôi chuẩn bất biến `E:\Working\Bieu Mau\Mau_Goc_Bao_Gia_ECO_PRIME_Dong_Ho_Dien.xlsx` và script tạo tự động 1:1 `scripts/generate_eco_prime_quotation.py`.
- **Quy tắc bắt buộc:**
  1. Thể hiện song ngữ: Tiếng Việt và Tiếng Trung Phồn thể.
  2. Bóc tách rõ danh mục thiết bị từ sơ đồ thiết kế. Bám sát 100% bản vẽ sơ đồ nguyên lý (Zero Deviation from Schematic Drawing), tuyệt đối không tự suy diễn hoặc tùy tiện tăng giảm số lượng Gateway hay thiết bị (trên bản vẽ vẽ 1 Gateway thì bóc tách đúng 1 Gateway). TUYỆT ĐỐI KHÔNG tự ý bịa thêm chi phí thi công nếu đề bài không yêu cầu.
  3. Tuân thủ 100% màu sắc chuẩn: Chữ thiết bị màu đen; Hàng bảo hành (Điều khoản 2) có đoạn chữ xanh dương; Hàng thanh toán (Điều khoản 3) toàn bộ chữ màu đỏ rực; Khối chữ ký (A24:A25) chữ màu nâu vàng `#9C6500`; Số tiền Tạm tính, VAT, Tổng cộng chữ màu xanh dương `#0000FF` bold; Nền theme chuẩn 6 tint 0.8.
  4. Cột đơn giá bán (cột F) và giá vốn (cột J) để trống cho Sếp tự điền. Vùng in `$A$1:$H$28` khít chặt trên 1 trang A4 đứng, scale 38%, không loang viền ngoài.
- **Tính năng Web Portal ECO PRIME (AI Vision Sơ Đồ Điện -> Báo Giá Excel Chuẩn 1:1):**
  - **Đường dẫn truy cập:** `/eco-prime-quotations` (hoặc `/eco-prime`).
  - **Cấu trúc thư mục module tách biệt (Folder Separation - Dễ bảo trì & tìm kiếm):**
    * *Data Models:* `pm_portal/app/models/eco_prime_models.py` (Pydantic models cho thiết bị, báo giá và payload).
    * *AI Vision Service:* `pm_portal/app/services/eco_prime/eco_prime_ai_service.py` (Gemini Multimodal Vision phân tích sơ đồ đơn tuyến, đếm trạm biến áp, cáp XLPE, chọn CT-1000RV/CT-2000RV, bám sát 100% bản vẽ không tăng giảm Gateway).
    * *Excel Generator Service:* `pm_portal/app/services/eco_prime/eco_prime_excel_service.py` (Tạo file `.xlsx` chuẩn 1:1 từ phôi mẫu gốc, công thức sống, Rich Text bảo hành, màu đỏ thanh toán).
    * *Controller API:* `pm_portal/app/controllers/eco_prime_controller.py` (`/api/eco-prime/analyze-schematic`, `/api/eco-prime/upload-and-analyze`, `/api/eco-prime/export-excel`, `/api/eco-prime/sample-data`).
    * *Giao diện HTML:* `pm_portal/app/templates/eco_prime_quotation_page.html` (Kéo thả ảnh sơ đồ, tag nhận diện trạm biến áp, form thông tin linh hoạt có hoặc để trống, bảng BOM tương tác).
    * *Client Script & CSS:* `pm_portal/app/static/js/eco_prime_quotation.js` & `pm_portal/app/static/css/eco_prime_quotation.css`.
    * *Kiểm thử tự động:* `pm_portal/tests/test_eco_prime.py`.


### Workflow 2: Soạn Thảo & Rà Soát Hợp Đồng Mua Bán (Contract / 買賣合約)
- **Mục tiêu:** Soạn thảo hợp đồng bán hàng thiết bị hoặc hợp đồng trọn gói triển khai dự án cho khách hàng FDI Đài Loan/Trung Quốc.
- **Tài liệu tham khảo:** [contract_bilingual_sample.md](./resources/contract_bilingual_sample.md).
- **Checklist 6 điểm kiểm soát vàng:**
  1. Thông tin pháp nhân 2 bên (Tên cty, MST, Người đại diện, Địa chỉ).
  2. Bảng kê danh mục sản phẩm (Đơn giá, số lượng, thành tiền, tổng tiền bằng số và bằng chữ).
  3. Cơ cấu đợt thanh toán (Tạm ứng 30%-50%, thanh toán theo tiến độ thi công, nghiệm thu cuối FAC 10%-20%).
  4. Hạn giao hàng (Quy định rõ "trong vòng X ngày kể từ ngày nhận đủ tiền đặt cọc").
  5. Điều khoản nghiệm thu ngầm định (Sau 7 ngày thông báo nếu khách không phản hồi thì tự động xem như nghiệm thu đạt).
  6. Điều khoản giải thích ngôn ngữ: "Nếu có mâu thuẫn giữa tiếng Trung và tiếng Việt thì bản tiếng Việt sẽ được ưu tiên áp dụng".

### Workflow 3: Lập Biên Bản Nghiệm Thu & Bàn Giao (Acceptance / 驗收確認書)
- **Mục tiêu:** Xác nhận hoàn thành mốc chạy thử (Trial run), đưa vào sử dụng, hoặc nghiệm thu tổng thể để mở đợt thanh toán.
- **Tài liệu tham khảo:** [acceptance_minute_sample.md](./resources/acceptance_minute_sample.md) & file mẫu [`001_BIEN_BAN_NGHIEM_THU_BAN_GIAO_CX_.docx`](file:///e:/Working/001_BIEN_BAN_NGHIEM_THU_BAN_GIAO_CX_.docx).
- **Quy tắc bắt buộc:**
  1. Dẫn chiếu chính xác Số Hợp Đồng, Ngày Ký, Phụ Lục Kỹ Thuật đính kèm.
  2. Liệt kê rõ các hạng mục kỹ thuật đã kiểm tra đạt yêu cầu.
  3. Ghi rõ: "Biên bản này là căn cứ xác nhận giai đoạn thanh toán X% giá trị hợp đồng = ... VNĐ".

### Workflow 4: Đặt Hàng & Quản Lý Nhà Cung Cấp (PO & Procurement)
- **Mục tiêu:** Lập Đơn đặt hàng (Purchase Order - PO) mua thiết bị nội địa hoặc linh kiện nhập khẩu (Đài Loan/Trung Quốc).
- **Tài liệu tham khảo:** [purchase_order_sample.md](./resources/purchase_order_sample.md).
- **Quy tắc:** Chỉ phát hành PO mua thiết bị giá trị lớn sau khi Kế toán xác nhận khách hàng đã chuyển tiền tạm ứng (cọc). Theo dõi chặt chẽ chứng từ xuất nhập khẩu (Invoice, Packing List, CO/CQ, Tờ khai hải quan).

### Workflow 5: Đề Nghị Thanh Toán & Đôn Đốc Công Nợ (Payment Request & AR Reminder)
- **Mục tiêu:** Nhắc khách hàng thanh toán đúng hạn hợp đồng (T/T 14 days, T/T 30 days, T/T 60 days).
- **Tài liệu tham khảo:** [payment_request_and_reminder_sample.md](./resources/payment_request_and_reminder_sample.md).
- **Mẫu Word chuẩn bắt buộc cho Phiếu yêu cầu NCC thanh toán:** `E:\Working\Bieu Mau\Mau_Goc_De_Nghi_Thanh_Toan_NCC.docx`.
- **Quy tắc mẫu gốc bất biến:** Luôn nhân bản trực tiếp từ file trên và chỉ thay dữ liệu. Giữ nguyên 100% cấu trúc, thứ tự khối, lề A4, độ rộng cột, chiều cao hàng, ô gộp, font, cỡ chữ, màu, viền, padding, khoảng cách, vùng ký và ngắt trang. Không dựng lại mẫu bằng code và không tự động làm đẹp lại.
- **Công cụ bắt buộc:** Dùng `scripts/fill_supplier_payment_request_docx.py` để thay chuỗi ở cấp run và xác minh dấu vân tay layout/style. Dùng `scripts/create_payment_request_word_template.py` chỉ để tạo bản sao 1:1 chưa điền dữ liệu.
- **Dữ liệu thay thế:** Truyền file JSON dạng `{"replacements":[{"find":"giá trị cũ","replace":"giá trị mới","expected":1}]}`; tách riêng từng dòng nếu nội dung song ngữ có xuống dòng.
- **Bảo vệ mẫu:** Không bao giờ ghi đè file `-Gốc.docx`. Lưu kết quả sang tên file khác; nếu file đích đang mở thì lưu bản `_v2`.
- **Kiểm tra bàn giao:** Render file đã điền và xác nhận vẫn đúng 1 trang, không tràn/cắt/ẩn chữ. Nếu dữ liệu mới dài làm tràn trang, không tự ý đổi layout; báo người dùng để chọn cách rút gọn nội dung.
- **3 Cấp độ đôn đốc công nợ:**
  - *Cấp độ 1 (Nhắc nhở nhẹ nhàng / Trước hạn 3-5 ngày):* Gửi kèm đề nghị thanh toán + Biên bản nghiệm thu + Hóa đơn điện tử.
  - *Cấp độ 2 (Đến hạn / Quá hạn 1-7 ngày):* Email/Tin nhắn song ngữ lịch sự nhưng nhấn mạnh điều khoản hợp đồng.
  - *Cấp độ 3 (Quá hạn >14 ngày):* Thư nhắc công nợ chính thức (催款函) có đóng dấu công ty Hong Ming, nêu rõ quyền tạm dừng hỗ trợ kỹ thuật và bảo hành theo HĐ.

### Workflow 6: Quản Lý Tiến Độ Dự Án (Project Tracker)
- **Mục tiêu:** Theo dõi toàn diện dòng đời dự án từ mốc ký kết, giao hàng, thi công đến thu nợ.
- **Công cụ hỗ trợ:**
  - Chạy script tính toán mốc thời hạn: `python .agents/skills/hongming-pm-hub/scripts/project_timeline_calc.py`
  - Chạy script sinh file Excel theo dõi dự án: `python .agents/skills/hongming-pm-hub/scripts/create_project_tracker_excel.py`

### Workflow 7: Lập Phiếu Xuất Kho & Biên Bản Bàn Giao Thiết Bị (Stock-out & Delivery Note / 出庫單暨設備交貨移交作業)
- **Mục tiêu:** Xuất kho giao thiết bị, máy chủ, Gateway, cảm biến, vật tư tới nhà máy đối tác hoặc cấp phát cho đội kỹ thuật thi công hiện trường.
- **Tài liệu tham khảo:** [stock_out_delivery_note_sample.md](./resources/stock_out_delivery_note_sample.md).
- **Công cụ hỗ trợ:**
  - **File Word (.docx) chính thức ký đóng dấu:** `python .agents/skills/hongming-pm-hub/scripts/generate_stock_out_word.py` (chuẩn hành chính pháp lý gửi đối tác).
  - **File Excel (.xlsx) bảng kê chi tiết:** `python .agents/skills/hongming-pm-hub/scripts/generate_stock_out_note.py` (chuẩn in ấn A4 ngang, quản lý xuất nhập tồn).
- **Quy tắc bắt buộc:**
  1. Ghi rõ số Serial Number (S/N), Part Number, quy cách kỹ thuật và tình trạng ngoại quan (mới 100%, nguyên seal).
  2. Dẫn chiếu căn cứ hợp đồng để làm cơ sở kích hoạt mốc thanh toán đợt giao hàng.
  3. Bắt buộc có đủ chữ ký 4 bên: Người lập phiếu (PM), Thủ kho xuất hàng, Người vận chuyển/giao hàng, và Đại diện khách hàng nhận hàng.

---

### Báo cáo tuần PowerPoint PM Hong Ming / BANG
- Khi tạo hoặc sửa báo cáo tuần dạng trình chiếu, mặc định dùng mẫu người dùng duyệt ngày 30/10/2026. Đọc [hướng dẫn mẫu báo cáo tuần](./references/weekly_report_presentation.md) trước khi làm; dùng PPTX mẫu làm tham chiếu thực tế, không quay lại mẫu nền đen cũ. Yêu cầu mới của người dùng được ưu tiên.

## 2. THƯ MỤC TÀI NGUYÊN (RESOURCES & REFERENCES)

- [Bảng từ vựng chuyên ngành Việt - Trung](./references/bilingual_glossary.md): Tra cứu nhanh thuật ngữ IoT, Phần cứng, Kế toán, Hợp đồng.
- [Quy trình tác nghiệp chuẩn SOP 7 bước](./references/workflow_sop.md): Hướng dẫn chi tiết từng bước từ Pre-sales đến Hậu mãi.
- [Cẩm nang kiểm soát rủi ro hợp đồng & công nợ](./references/risk_control_guide.md): Các "bẫy" thường gặp trong dự án kỹ thuật và cách phòng tránh.
- [Biểu mẫu báo giá song ngữ](./resources/quotation_sample.md)
- [Biểu mẫu hợp đồng song ngữ](./resources/contract_bilingual_sample.md)
- [Biểu mẫu biên bản nghiệm thu song ngữ](./resources/acceptance_minute_sample.md)
- [Biểu mẫu phiếu xuất kho & bàn giao thiết bị song ngữ](./resources/stock_out_delivery_note_sample.md)
- [Biểu mẫu đơn đặt mua hàng (PO)](./resources/purchase_order_sample.md)
- [Biểu mẫu đề nghị thanh toán & thư nhắc nợ](./resources/payment_request_and_reminder_sample.md)

---

## 3. QUY TẮC ĐỊNH DẠNG XUẤT VĂN BẢN (OUTPUT FORMATTING RULES - BẮT BUỘC)

Khi hỗ trợ người dùng soạn thảo các nội dung gửi cho đối tác (Email, Tin nhắn WeChat/Zalo, Hợp đồng, Biên bản nghiệm thu, Đề nghị thanh toán, Thư nhắc nợ, Đơn hàng PO):
1. **TUYỆT ĐỐI KHÔNG sử dụng khối mã code block (triple backticks ```) để bao quanh văn bản.**
   - Lý do: Khối mã sẽ hiển thị văn bản thô, khi người dùng sao chép dán vào Gmail, Outlook, Word sẽ bị dính các ký tự `**`, `*`, `---`, `###` khiến văn bản xấu và mất công xóa tay.
2. **BẮT BUỘC hiển thị trực tiếp ở dạng Rich Text (văn bản được render chuẩn):**
   - Tiêu đề, số tiền quan trọng, tên công ty được in đậm trực tiếp bằng markdown thông thường ngoài code block.
   - Người dùng chỉ cần bôi đen chuột toàn bộ đoạn văn bản, nhấn `Ctrl + C` và dán `Ctrl + V` vào Gmail/Outlook/Word là sẽ tự động có chữ in đậm xịn, danh sách đẹp mắt.
3. **KHÔNG để placeholder dạng `**[...**`:**
   - Điền sẵn thông tin thực tế tối đa (Ngày tháng hiện tại, số tiền thực tế, mã hợp đồng, tên đại diện).
   - Nếu có thông tin người dùng cần điền bổ sung (như STK công ty), hãy ghi chú bằng dấu ngoặc đơn đơn giản `(Điền số tài khoản...)` để không bị lỗi ký tự khi copy.

---

## 4. QUY TRÌNH BẮT CHƯỚC & TẠO FILE THEO MẪU CHUẨN XÁC 1:1 (TEMPLATE FIDELITY PROTOCOL)

Khi người dùng yêu cầu tạo file tài liệu/bảng tính (Excel, Word) dựa trên một biểu mẫu có sẵn:

### Bước 1: Khảo sát mẫu gốc toàn diện (Deep Inspection Checklist - BẮT BUỘC KHÔNG BỎ SÓT)
Tuyệt đối không đoán mò cấu trúc hoặc tự ý vẽ thêm thuộc tính. Agent phải chạy script bóc tách trực tiếp toàn bộ 10 thuộc tính cốt lõi từ file mẫu:
1. **Cố định hàng & cột (Freeze Panes):**
   - Kiểm tra `ws.freeze_panes` và cấu trúc `<pane>` trong XML (`ySplit`, `xSplit`, `topLeftCell`, `state="frozen"`).
   - Nếu mẫu gốc ghim hàng tiêu đề (ví dụ 5 hàng đầu: `ws.freeze_panes = 'A6'`), file mới BẮT BUỘC phải ghim y hệt để khi người dùng cuộn chuột xem dữ liệu, tiêu đề không bị trôi đi.
2. **Chế độ xem, tỷ lệ co giãn in ấn & Không để loang rìa ngoài (Sheet View & Scale 52%):**
   - Kiểm tra `ws.views.sheetView[0].view`, `zoomScale`, `zoomScaleSheetLayoutView` (chuẩn 85%).
   - **Tỷ lệ co giãn in ấn (`scale = 52`):** Bắt buộc thiết lập `ws.page_setup.scale = 52`. Khi bảng rộng hơn khổ A4, nếu thiếu `scale = 52`, Excel/WPS sẽ tự động sinh các **đường kẻ ngắt trang màu xanh đứt đoạn (blue dashed lines)** chia cắt ngang dọc bảng thành nhiều trang (Page 1, 2, 3, 4). Đặt đúng `scale = 52` giúp toàn bộ bảng nằm trọn vẹn trên 1 trang duy nhất, loại bỏ hoàn toàn đường xanh chia cắt!
   - Thiết lập vùng in `ws.print_area` khít chặt chẽ với bảng dữ liệu (ví dụ `$A$1:$G$15`).
   - **TUYỆT ĐỐI KHÔNG bật `showGridLines = True`** trong `pageBreakPreview` nếu mẫu gốc không bật! Khi bật `showGridLines = True`, Excel sẽ vẽ lưới trắng loang lổ ra toàn bộ vùng lề/rìa ngoài bảng thay vì nền xám thuần chuẩn.
3. **Kích thước khung ảnh lớn & Tính đồng đều chuẩn mẫu gốc (Large Uniform Image Frames):**
   - Không được tự ý thu nhỏ độ rộng cột ảnh. Độ rộng cột ảnh chuẩn của Hong Ming rất rộng rãi:
     - **Dòng EF (Máy kiểm kho EF550):** Cả 5 cột ảnh A, B, C, D, E đều có độ rộng lớn **`37.11`** (khoảng 265 pixel mỗi ô), cột Ghi chú F là `14.0`, chiều cao dòng 6 là **`284.25pt`**.
     - **Dòng RF (Súng quét RFR900):** Cả 3 cột ảnh A, B, C đều có độ rộng lớn **`34.44`** (khoảng 245 pixel mỗi ô), cột Ghi chú D là `25.33`, chiều cao dòng 6 là **`284.25pt`**.
   - Tất cả các khung ảnh màu vàng `#FFFFF2CC` trong cùng sheet phải có kích thước lớn đồng nhất, viền thin đen chuẩn mẫu gốc.
4. **Kiểm tra ranh giới viền từng dòng (Per-Row Border Precision - Bỏ rìa ngoài thừa):**
   - Phải soi rõ dòng nào có viền bảng, dòng nào KHÔNG có viền:
     - Khối tiêu đề trên (Tên biên bản, Số hợp đồng, Ngày tháng, Bên A, Bên B): để `border=None`.
     - Khối bảng dữ liệu (Header & Data rows): có viền mảnh (`thin`).
     - Khối ghi chú, điều khoản, khối chữ ký đại diện: để `border=None`.
     - Nút bấm quay về (Back button): nếu mẫu gốc không kẻ viền thì để `border=None`.
   - Không được tự ý kẻ viền bao quanh toàn trang hay thêm viền ngoài (outer border) vào những dòng vốn dĩ không có viền.
5. **Logo & Media:** Kiểm tra sự hiện diện của logo (ảnh PNG trong `xl/media/`), vị trí neo (Anchor cell, ví dụ: `A4:B7`), kích thước pixel (`cx`, `cy`). Phải giữ nguyên vẹn logo công ty Hong Ming.
6. **Font chữ & Cỡ chữ:** Font chuẩn của Hong Ming là `微軟正黑體` (Microsoft JhengHei) hoặc `Times New Roman` tùy theo mẫu gốc quy định. Giữ chuẩn 1:1 từng phân đoạn (tiêu đề 13-14pt bold, header cột 12pt bold, nội dung 11-12pt regular, kết quả đạt 12pt bold màu xanh lá `#375623`).
7. **Màu sắc & Theme:** Tái tạo chính xác mã màu hex (Dark blue `#1F4E79`, Header blue `#2E75B6`, Light blue `#D6E4F0`, Zebra gray `#F2F2F2`, Green pass `#E2EFDA`, Yellow image placeholder `#FFFFF2CC`).
8. **Công thức tính toán & Liên kết Hyperlink:**
   - Tự động chèn công thức nhân thành tiền sống `=F*E` và công thức tổng `=SUM(...)`.
   - Liên kết Hyperlink 2 chiều: Từ sheet tổng hợp nhấp chuột nhảy đến sheet chi tiết (`#'Sheet'!A1`), và từ sheet chi tiết có nút quay về (`#'Nghiệm Thu'!A1`).
9. **Cấu hình trang in (Page Setup):** Hướng trang in (`orientation`: portrait/landscape), khổ giấy (`paperSize = 9` cho A4), tỷ lệ co giãn (`scale = 52` cho bảng dọc), lề in (`pageMargins`).
10. **Tự động mở rộng sheet chi tiết:** Khi dữ liệu có N thiết bị, phải tạo đủ N sheet chi tiết tương ứng, không bỏ dở giữa chừng.

### Bước 2: Thuật toán chống ẩn/cắt chữ (Anti-Clipping Height Algorithm)
- Văn bản trong bảng tính công nghiệp có cả tiếng Trung (ký tự 2-byte CJK), tiếng Việt có dấu và tiếng Anh kỹ thuật.
- Khi chữ dài hơn độ rộng cột, tính năng `wrap_text` sẽ tự động bẻ dòng (soft wrap). Nếu chỉ đếm dấu `\n` thì Excel sẽ cắt cụt các dòng còn lại!
- **Công thức tính chiều cao dòng bắt buộc:**
  - Đo tổng trọng số ký tự: Ký tự CJK tính trọng số 1.95, ký tự Latin hoa tính 1.2, chữ thường tính 0.95.
  - Tính số dòng thực tế = `ceil(tổng trọng số / độ rộng hữu dụng của cột)`.
  - Chiều cao dòng = `số dòng tối đa * 19.5pt + 16pt (padding an toàn)`.
  - Luôn đảm bảo 100% từng dòng chữ đều hiển thị trọn vẹn, không bị che mất đuôi.

### Bước 3: Kiểm tra chéo tự động trước khi bàn giao (Automated Cross-Check Checklist)
Trước khi bàn giao file cho người dùng, Agent BẮT BUỘC phải chạy script kiểm tra chéo tự động (Verification Script):
1. `freeze_panes`: Đã ghim đúng hàng/cột chưa?
2. `column_dimensions`: Các cột ảnh đã bằng nhau 100% chưa?
3. `views.sheetView`: Chế độ xem, zoomScale và gridlines đã khớp hoàn toàn mẫu gốc chưa?
4. `print_area`: Đã bao khít vùng dữ liệu, không tạo rìa trắng thừa chưa?
5. `borders`: Các dòng ngoài bảng có bị dính viền thừa không?
Nếu phát hiện bất kỳ điểm nào chưa khớp, phải chỉnh sửa ngay trước khi trả lời người dùng.

### Bước 4: Xử lý an toàn khi khóa file (File Lock & Permission Protection)
Khi lưu file vào thư mục người dùng (ví dụ Downloads):
- Luôn bọc trong khối `try-except PermissionError`.
- Nếu file đang mở trong Excel/WPS Office, tự động lưu bản dự phòng an toàn (ví dụ `_v2.xlsx`) và lưu một bản đồng bộ vào Workspace, thông báo rõ cho người dùng để không làm gián đoạn công việc.

### Bước 5: Quản lý thư viện script (`scripts/`) để tái sử dụng
1. **Không dùng 1 script chung duy nhất:** Vì công ty có nhiều mẫu biểu khác nhau (Mẫu Tiết kiệm năng lượng EMS, Mẫu Kết nối máy móc SMB IoT Phase 2, Mẫu Hợp đồng Cheng Feng, Mẫu Nghiệm thu sửa chữa thiết bị, v.v.), mỗi mẫu có layout riêng biệt.
2. **Quy chuẩn đặt tên script:**
   - `generate_energy_quotation.py`: Cho các báo giá theo mẫu Tiết kiệm năng lượng (EMS / Lá chắn điện xanh / PM2100).
   - `generate_iot_phase2_quotation.py`: Cho các báo giá kết nối máy móc SMB IoT (Dây chuyền dập đầu, ủ mềm, phốt phát hóa, phun cát).
   - `generate_smart_factory_quotation.py`: Cho các dự án nhà máy thông minh tích hợp ERP/Server.
   - `generate_cx_repair_acceptance.py`: Cho các biên bản nghiệm thu thiết bị sửa chữa CX Technology.
3. **Nguyên tắc lưu kho:** Mọi script sau khi tạo phải được lưu trữ vĩnh viễn trong thư mục `.agents/skills/hongming-pm-hub/scripts/` và đồng bộ sang thư mục Global (`C:\Users\BANG\.gemini\config\skills\hongming-pm-hub\scripts\`). Khi người dùng đưa dữ liệu mới cho một mẫu tương tự, Agent chỉ cần tái sử dụng script đã có hoặc nhân bản ra để điều chỉnh, không được xóa đi.

## 6. QUY CHUẨN BIỂU MẪU BÁO GIÁ ECO PRIME (ECO PRIME 報價單)

1. **File phôi mẫu gốc bất biến:** `E:\Working\Bieu Mau\Mau_Goc_Bao_Gia_ECO_PRIME_Dong_Ho_Dien.xlsx` (nhân bản từ `ECO PRIME_BHT Báo Giá Đồng Hồ Điện_24-07-2026.xlsx`).
2. **Script tạo tự động 1:1 cố định:** `E:\Working\scripts\generate_eco_prime_quotation.py` (đồng bộ tại `hongming-pm-hub/scripts/generate_eco_prime_quotation.py`).
3. **Quy tắc bắt buộc khi tạo báo giá ECO PRIME:**
   - **Bám sát 100% bản vẽ sơ đồ nguyên lý (Zero Deviation from Schematic Drawing):** Phân tích chính xác số lượng thiết bị từ sơ đồ đơn tuyến, TUYỆT ĐỐI KHÔNG tự suy diễn hoặc tùy tiện tăng giảm số lượng (ví dụ: trên bản vẽ vẽ 1 Gateway kết nối 4 trạm biến áp qua vòng RS485 thì bóc tách đúng 1 Gateway, không tự ý sửa thành 2). Mọi prompt AI và code bóc tách phải trung thành tuyệt đối với bản vẽ.
   - **Gộp bộ nguồn PW vào Gateway CC2051 (Bundle Rule):** Bộ nguồn 24VDC (電源供應器) chỉ cần 1 cái và **BẮT BUỘC ĐƯỢC GỘP CHUNG VÀO DÒNG GATEWAY CC2051** vì nhà cung cấp bán kèm trọn gói với nhau (`Gateway thu thập dữ liệu CC2051 (kèm bộ nguồn 24VDC) / CC2051 工業級資料收集閘道器 (含24VDC電源供應器)`).
   - **Cấu trúc 7 hạng mục hoàn hảo 1:1:** Nhờ gộp PW vào CC2051, toàn bộ danh mục gồm đồng hồ, biến dòng, CC2051 kèm PW, LAN switch, vật tư phụ và chi phí thi công có đúng **7 hạng mục**, trùng khớp 1:1 với 7 dòng (`Row 13:19`) của file phôi mẫu gốc, không cần chèn thêm dòng, giữ nguyên bảng tổng tiền tại `Row 21:23`, vùng in `$A$1:$H$27`.
   - **Quy chuẩn màu sắc 100% mẫu gốc:**
     - 7 hạng mục thiết bị: Font chữ màu đen chuẩn mực, không dùng màu xanh.
     - Khối chữ ký (A24:A25): Chữ màu nâu vàng `#9C6500` bold.
     - Số tiền Tạm tính, VAT 8%, Tổng cộng (G21:H23): Chữ màu xanh dương `#0000FF` bold.
     - Điều khoản 2 (Bảo hành): Đoạn `交貨後保固一年` và `Bảo hành 1 năm kể từ ngày giao hàng.` có màu xanh dương `#0000FF` bold.
     - Điều khoản 3 (Thanh toán): Toàn bộ chữ màu đỏ rực `#FF0000` bold.
     - Màu nền theme: Giữ nguyên màu theme 6 tint 0.8 gốc của workbook, không dùng mã màu cam đậm nhân tạo.
   - **Cột đơn giá:** Cột F (Giá bán USD) và Cột J (Giá vốn xuất xưởng USD) để trống (`None`) để Sếp tự điền.
   - **Khổ in & Sheet View:** Khóa chặt vùng in `$A$1:$H$27`, PageBreakPreview, Zoom 60%, Scale 38%, freeze_panes A13, không loang viền ngoài.
