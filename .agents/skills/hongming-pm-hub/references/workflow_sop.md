# QUY TRÌNH TÁC NGHIỆP CHUẨN (SOP) QUẢN LÝ DỰ ÁN HONG MING GLOBAL

Tài liệu này hướng dẫn chi tiết quy trình 7 bước (Project Lifecycle SOP) mà nhân viên Quản lý Dự án (PM) tại Hong Ming Global phải tuân thủ để đảm bảo dự án vận hành trơn tru, không trễ hạn và không thất thoát công nợ.

---

## TỔNG QUAN VÒNG ĐỜI DỰ ÁN (PROJECT LIFECYCLE)

```
[BƯỚC 1] Khảo sát & Lập báo giá (Quotation)
   │
   ▼
[BƯỚC 2] Đàm phán & Ký kết Hợp đồng (Contract) ──► Thu tiền cọc đợt 1 (30%-50%)
   │
   ▼
[BƯỚC 3] Đặt hàng mua thiết bị (PO) & Thủ tục Hải quan (XNK)
   │
   ▼
[BƯỚC 4] Giám sát giao hàng & Điều phối thi công tại nhà xưởng
   │
   ▼
[BƯỚC 5] Chạy thử (Trial Run) & Ký Biên bản nghiệm thu giai đoạn (30%-40%)
   │
   ▼
[BƯỚC 6] Xuất hóa đơn VAT, Thu tiền đợt 2/3 & Nghiệm thu tổng thể (FAC)
   │
   ▼
[BƯỚC 7] Thu hồi nợ đợt cuối (尾款) & Chuyển giao Bảo hành (12 tháng)
```

---

## CHI TIẾT TỪNG BƯỚC THỰC HIỆN

### BƯỚC 1: KHẢO SÁT & LẬP BÁO GIÁ (QUOTATION / 報價單)
1. **Tiếp nhận nhu cầu:** Nhận yêu cầu từ Khách hàng hoặc qua Kinh doanh (Sales) / Giám đốc Tang.
2. **Khảo sát kỹ thuật:** Phối hợp cùng Kỹ sư trưởng (anh Jenson Chang) để bóc tách BOM (Bill of Materials):
   - Số lượng trạm máy cần gắn I/O Gateway, Relay, cảm biến nhiệt, biến dòng CT.
   - Khoảng cách kéo dây mạng cat6, cáp quang ODF, ống luồn PP bảo vệ.
   - Hạ tầng CNTT: Cần máy chủ Server Dell, máy trạm hay màn hình dashboard 65 inch.
3. **Lập bảng báo giá:**
   - Dùng file mẫu Excel [`HM浤詺資訊_Vonmax弘聲 機聯網暨工廠節能 第二階段 硬體報價單_202603_V1.5.xlsx`](file:///e:/Working/HM浤詺資訊_Vonmax弘聲%20機聯網暨工廠節能%20第二階段%20硬體報價單_202603_V1.5.xlsx).
   - Kiểm tra công thức, tỷ giá, chiết khấu và thuế suất VAT.
   - Xuất PDF song ngữ (Việt - Trung), gửi Sếp duyệt trước khi gửi khách.

---

### BƯỚC 2: SOẠN THẢO & KÝ KẾT HỢP ĐỒNG (CONTRACT / 買賣合約)
1. **Soạn thảo hợp đồng:**
   - Sử dụng form mẫu song ngữ chuẩn của Hong Ming (xem `contract_bilingual_sample.md`).
   - Đảm bảo thông tin pháp nhân (Tên cty, MST, Người đại diện) trùng khớp 100% với giấy ĐKKD của khách.
   - Quy định rõ điều khoản thanh toán (chia làm 3 hoặc 4 đợt).
   - Quy định thời gian giao hàng: **"Trong vòng 60 đến 80 ngày kể từ ngày nhận đủ tiền đặt cọc"**.
2. **Ký kết & Thu cọc:**
   - Trình Tổng Giám Đốc Tang Wei Li ký và đóng dấu.
   - Gửi 02 bản cứng cho khách hàng ký đóng dấu, nhận lại 01 bản lưu trữ.
   - **Mốc quan trọng:** Theo dõi sát sao tài khoản công ty. Chỉ khi Kế toán báo đã nhận đủ tiền cọc đợt 1 (30% - 50%), PM mới được phép phát hành PO đặt hàng thiết bị.

---

### BƯỚC 3: MUA HÀNG (PO) & THỦ TỤC XUẤT NHẬP KHẨU (LOGISTICS)
1. **Lập Đơn đặt hàng (PO - Purchase Order):**
   - Thiết bị trong nước (Màn hình TV TCL, vật tư điện Cadivi, ống PP, Switch mạng): Đặt nhà phân phối tại Việt Nam.
   - Thiết bị chuyên dụng nhập khẩu (Gateway IoT, Bộ chuyển đổi RS485, Thẻ RFID Silicon chịu nhiệt, Đồng hồ đo điện đa mạch PM2100): Đặt đối tác sản xuất tại Đài Loan/Trung Quốc.
2. **Thủ tục xuất nhập khẩu:**
   - Nhận Proforma Invoice (PI), Commercial Invoice (CI), Packing List (PL) từ NCC.
   - Gửi cho bên dịch vụ Forwarder/Hải quan để làm thủ tục mở tờ khai nhập khẩu.
   - Lưu trữ chứng nhận nguồn gốc xuất xứ (CO) và chứng nhận chất lượng (CQ) phục vụ nghiệm thu sau này.

---

### BƯỚC 4: GIÁM SÁT GIAO HÀNG & THI CÔNG LẮP ĐẶT
1. **Giao nhận thiết bị:**
   - Kiểm tra số lượng, ngoại quan, số serial trước khi xuất kho đi công trình.
   - Lập Phiếu giao hàng / Biên bản bàn giao thiết bị tại nhà xưởng khách hàng.
2. **Điều phối thi công:**
   - Làm việc với quản đốc/kỹ thuật nhà máy của khách (đăng ký giấy phép an toàn, lịch cúp điện nếu cần đấu nối tủ điện).
   - Theo dõi đội thi công kéo cáp quang, hàn ODF, đi ống luồn dây PP, lắp đặt tủ điện, lắp đặt màn hình TV.
   - Báo cáo cập nhật tiến độ hàng ngày/hàng tuần cho Sếp và Chị PM Lead.

---

### BƯỚC 5: CHẠY THỬ (TRIAL RUN) & NGHIỆM THU GIAI ĐOẠN
1. **Cấu hình & Vận hành thử:**
   - Kỹ sư phần mềm kết nối dữ liệu từ Gateway lên hệ thống máy chủ / Dashboard.
   - Kiểm tra việc truyền tín hiệu: Quét RFID vào trạm/ra trạm, báo công, đo đếm dòng điện thực tế.
   - Cho hệ thống chạy thử nghiệm (Trial Run) từ 1 đến 2 tuần để theo dõi độ ổn định.
2. **Ký Biên bản nghiệm thu giai đoạn:**
   - Soạn thảo *Biên bản nghiệm thu và bàn giao đưa vào sử dụng* (xem mẫu `001_BIEN_BAN_NGHIEM_THU_BAN_GIAO_CX_.docx`).
   - Mời đại diện kỹ thuật và quản lý của khách hàng cùng ký xác nhận.
   - Biên bản này là điều kiện tiên quyết để kích hoạt đợt thanh toán tiếp theo (thường là 30% - 40%).

---

### BƯỚC 6: XUẤT HÓA ĐƠN, THU TIỀN ĐỢT 2/3 & NGHIỆM THU CUỐI (FAC)
1. **Phát hành hồ sơ yêu cầu thanh toán:**
   - Bàn giao Biên bản nghiệm thu có đủ dấu đỏ cho Kế toán Hong Ming.
   - Kế toán xuất hóa đơn VAT điện tử.
   - PM gửi bộ hồ sơ: Giấy đề nghị thanh toán + Hóa đơn VAT + Biên bản nghiệm thu cho phòng Mua hàng / Kế toán của khách.
2. **Theo dõi thanh toán:**
   - Căn cứ vào hạn hợp đồng (T/T 14 ngày hoặc 30 ngày hoặc 60 ngày).
   - Nhắc nợ trước hạn 3 ngày để khách chuẩn bị lệnh chuyển tiền.
3. **Nghiệm thu cuối cùng (Final Acceptance Certificate - FAC):**
   - Bàn giao toàn bộ tài liệu: Bản vẽ hoàn công (竣工圖), Hướng dẫn sử dụng hệ thống, Phiếu bảo hành.
   - Ký Biên bản nghiệm thu tổng thể dự án (FAC).

---

### BƯỚC 7: THU HỒI NỢ ĐỢT CUỐI (尾款) & DỊCH VỤ BẢO HÀNH
1. **Quyết toán nợ đợt cuối:**
   - Nhắc khách thanh toán khoản 10% - 20% còn lại theo đúng hạn sau ngày ký FAC.
   - Sau khi nhận đủ 100% tiền, ký Biên bản thanh lý hợp đồng.
2. **Quản lý bảo hành (12 tháng):**
   - Lưu trữ ngày bắt đầu và kết thúc bảo hành vào file quản trị.
   - Phối hợp xử lý sự cố trong vòng 24 - 48 giờ nếu khách hàng thông báo lỗi phần cứng hoặc phần mềm.
