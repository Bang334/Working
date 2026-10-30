# MẪU MAIL TIẾP NHẬN ĐƠN HÀNG (PO) & QUY ĐỊNH PHÁT HÀNH PO (PURCHASE ORDER WORKFLOW)

## 1. DẠNG MAIL NÀY DÙNG ĐỂ LÀM GÌ?
- **Trường hợp 1 (Xác nhận tiếp nhận đơn đặt hàng PO):** Khi khách hàng gửi Đơn đặt hàng (Purchase Order - PO) chính thức cho gói mua thiết bị hoặc gói dịch vụ sửa chữa/bảo trì. Hong Ming gửi email xác nhận đã nhận PO, xác nhận giá cả, số lượng và thông báo lịch bắt đầu triển khai/giao hàng.
- **Trường hợp 2 (Thống nhất quy định phát hành PO trọn gói):** Nhắc nhở khách hàng không tách nhỏ PO thành nhiều đợt lẻ tẻ đối với cùng một lô máy móc gửi sửa chữa (ví dụ gửi 6 máy thì mở 1 PO duy nhất cho cả 6 máy), tránh gây rối rắm quy trình đối soát kế toán và thủ tục xuất kho.
- **Trường hợp 3 (Đề xuất ký Hợp đồng nguyên tắc dài hạn):** Khi khách hàng phát sinh sửa chữa nhiều lô định kỳ, hai bên thống nhất ký 01 Hợp đồng nguyên tắc duy nhất để các lô sau chỉ cần gửi PO là tiến hành ngay.

---

## 2. FILE ĐÍNH KÈM BẮT BUỘC (ATTACHMENTS)
Khi gửi email liên quan đến PO, **BẮT BUỘC** phải đính kèm:
1. **Đơn đặt hàng (Purchase Order - PO) đã được hai bên xác nhận (Bắt buộc):**
   - File PDF PO có chữ ký của Trưởng phòng mua hàng và dấu mộc đối tác (Ví dụ: `PO_[SoPO]_[TenKhachHang].pdf`).
2. **Báo giá dịch vụ / Bảng kê chi phí sửa chữa tham chiếu (Bắt buộc):**
   - File Excel hoặc PDF bảng báo giá các hạng mục linh kiện thay thế đã được duyệt trước đó.
3. **Phiếu tiếp nhận thiết bị / Biên bản bàn giao hiện trạng (Nếu là dịch vụ sửa chữa):**
   - File PDF ghi nhận số lượng máy, số Serial Number và hiện trạng máy khi tiếp nhận vào phòng kỹ thuật.

---

## 3. MẪU NỘI DUNG EMAIL CHUẨN (SONG NGỮ VIỆT - TRUNG)

### MẪU A: XÁC NHẬN TIẾP NHẬN PO & THÔNG BÁO TIẾN ĐỘ THỰC HIỆN

**Tiêu đề:** Xác nhận tiếp nhận Đơn đặt hàng PO số [Số PO] - CÔNG TY TNHH TOÀN CẦU HONG MING / 採購訂單（PO）接收確認通知 – 宏明環球有限公司

---

**Nội dung:**

Kính gửi: Quý Công ty [Tên công ty khách hàng] / Bộ phận Mua hàng & Quản lý Dự án,  
敬致 [貴公司名稱] / 採購部暨專案管理組：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng đến Quý Công ty.  
宏明環球有限公司謹向貴公司致以誠摯的問候。

Chúng tôi xin xác nhận đã nhận được Đơn đặt hàng (Purchase Order) số **[Số PO]** phát hành ngày [Ngày phát hành], áp dụng cho lô hàng [Tên hạng mục: ví dụ Dịch vụ sửa chữa 06 máy kiểm kho Bluebird RFR-900 Lot 2 / Cung cấp 10 bộ Cảm biến nhiệt độ IoT].  
我司確認已收到貴公司於 [開立日期] 開出之採購訂單編號 **[PO 編號]**，相關項目為 [項目品名：如 Bluebird RFR-900 手持式掃描器第2批維修案 / 10組工廠溫濕度感測器採購案]。

**Chi tiết đơn hàng đã xác nhận / 訂單確認詳細資訊：**
* Số PO khách hàng / 客戶 PO 編號: [Số PO]
* Hạng mục thực hiện / 執行項目: [Tên hạng mục]
* Số lượng thiết bị / 數量: [Số lượng] máy
* Tổng giá trị đơn hàng / 訂單總含稅金額: [Số tiền] VNĐ
* Thời gian hoàn thành dự kiến / 預計完工或交貨交期: Trong vòng [Số ngày: ví dụ 05 - 07 ngày làm việc kể từ ngày tiếp nhận PO / 收到 PO 後 5-7 個工作天內]。

Đội ngũ kỹ thuật của Hong Ming đã chính thức đưa lô thiết bị vào quy trình triển khai theo đúng tiêu chuẩn cam kết.  
宏明技術工程團隊已正式將該批設備排入作業流程，並嚴格遵循標準作業規範執行。

Rất cảm ơn sự tin tưởng và đồng hành của Quý Công ty!  
感謝貴公司一直以來的信任與支持！

---

### MẪU B: THÔNG BÁO QUY ĐỊNH PHÁT HÀNH PO TRỌN GÓI CHO LÔ THIẾT BỊ SỬA CHỮA

**Tiêu đề:** Thông báo về quy định phát hành PO cho đơn hàng sửa chữa thiết bị / 關於維修訂單採購單（PO）開立規範之說明通知

---

**Nội dung:**

Kính gửi: Quý Công ty [Tên công ty khách hàng] / Bộ phận Mua hàng & Quản lý Thiết bị,  
敬致 [貴公司名稱] / 採購部暨設備管理組：

Trước tiên, Công ty TNHH Toàn Cầu Hong Ming xin chân thành cảm ơn Quý Công ty đã luôn tin tưởng và sử dụng dịch vụ sửa chữa thiết bị công nghiệp của chúng tôi trong suốt thời gian qua.  
首先，誠摯感謝貴公司一直以來對宏明維修服務的信任與愛護。

Trong thời gian gần đây, bộ phận quản lý đơn hàng nhận thấy đối với một số lô thiết bị gửi đến sửa chữa, Quý Công ty phát hành PO thành nhiều đợt nhỏ lẻ. Ví dụ: Quý Công ty gửi cùng lúc 06 máy để kiểm tra và sửa chữa nhưng ban đầu chỉ phát hành PO cho 2–3 máy, sau đó vài ngày mới tiếp tục phát hành PO cho các máy còn lại trong cùng lô.  
近期，我司訂單管理部門發現部分送修設備之 PO 是採分批零散開立。例如：貴司一次送修 6 台設備，但初次僅開立其中 2～3 台之 PO，數日後方補開其餘設備之 PO。

Việc tách nhỏ PO đối với cùng một lô thiết bị gây khó khăn đáng kể cho quá trình tiếp nhận, theo dõi tiến độ sửa chữa, đồng thời làm chậm trễ thủ tục bàn giao, xuất kho và lập hồ sơ thanh toán đối soát giữa hai bên.  
同批設備分批開立 PO 將對進度追蹤、零件調度造成困擾，並導致後續設備移交出庫、發票開立及會計帳務核對作業嚴重延遲。

**Hong Ming trân trọng đề xuất quy chuẩn phối hợp như sau / 宏明謹建議後續配合規範如下：**
1. **Phát hành PO trọn gói 1 lần duy nhất:** Đối với mỗi lô thiết bị gửi đến sửa chữa, kính nhờ Quý Công ty phát hành 01 bản PO duy nhất bao gồm toàn bộ số lượng máy đã được hai bên thống nhất theo báo giá kiểm tra kỹ thuật.
2. **Ký Hợp đồng nguyên tắc dài hạn:** Để đơn giản hóa thủ tục hành chính, Hong Ming đề xuất hai bên ký 01 Hợp đồng nguyên tắc khung về dịch vụ sửa chữa thiết bị. Khi đó, mỗi lần phát sinh sửa chữa, Quý Công ty chỉ cần phát hành PO theo đơn giá đã thỏa thuận mà không cần lập hợp đồng kinh tế riêng cho từng đợt.

Kính mong nhận được sự thấu hiểu và phối hợp từ Quý Công ty để nâng cao hơn nữa chất lượng dịch vụ và rút ngắn thời gian bàn giao thiết bị.  
懇請貴公司理解並惠予配合，以利進一步提升維修服務品質並縮短設備交件週期。

Trân trọng / 敬上,

**Bộ phận Dịch vụ Khách hàng & Quản lý Đơn hàng / 客戶服務暨訂單管理組**  
**CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司**  
* Hotline: +84 966 687 109  
* Email: sales@hongming-global.com / pm02@hongming-global.com
