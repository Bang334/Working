# CẨM NANG BẢO TOÀN BỐ CỤC 100% KHI ĐIỀN HỢP ĐỒNG (ZERO-LAYOUT-DISTORTION PROTOCOL)

Tài liệu này quy định tiêu chuẩn kỹ thuật bắt buộc khi trợ lý AI tiếp nhận, xử lý và điền thông tin vào các file Hợp đồng mua bán & triển khai dự án mẫu của **Công ty TNHH Toàn Cầu Hong Ming**.

---

## 1. NGUYÊN TẮC CỐT LÕI: "CHỈ SỬA NỘI DUNG — TUYỆT ĐỐI KHÔNG SỬA BỐ CỤC"

Mọi hợp đồng kinh tế và mua bán thiết bị với các đối tác FDI (như CX Technology, Vonmax, Cheng Feng...) đều là văn bản có tính pháp lý cao. Mọi hành vi làm lệch dòng, nhảy trang, đổi font hay vỡ viền bảng đều gây mất tính chuyên nghiệp và vi phạm quy chuẩn hành chính.

### 5 Không (Bắt buộc tuân thủ):
1. **KHÔNG** làm thay đổi lề trang (Margins), hướng giấy (Orientation), hoặc vị trí ngắt trang (Page breaks).
2. **KHÔNG** làm thay đổi kiểu font (Times New Roman / Microsoft JhengHei `微軟正黑體`), cỡ chữ (11-13pt), màu chữ hoặc các thuộc tính in đậm/in nghiêng của mẫu gốc.
3. **KHÔNG** thay đổi độ rộng cột (`col.width`), chiều cao dòng (`row.height`), đường viền ô (`borders`) hay khoảng đệm lề trong ô bảng (`cell margins`).
4. **KHÔNG** tự ý viết lại, xóa bỏ hoặc xáo trộn các điều khoản pháp lý cố định nếu người dùng không yêu cầu.
5. **KHÔNG** làm dịch chuyển khối Logo công ty, khối Tiêu ngữ Quốc hiệu và các khung chữ ký đóng dấu 2 bên.

---

## 2. QUY ƯỚC ĐỊNH DẠNG ĐÁNH DẤU CHỖ CẦN SỬA (PLACEHOLDER STANDARDS)

Để AI và script tự động nhận diện chính xác 100%, hệ thống hỗ trợ 3 cách định dạng từ phía người dùng:

| Định dạng | Cú pháp ví dụ | Mức độ khuyến nghị | Ưu điểm |
| :--- | :--- | :---: | :--- |
| **Thẻ ngoặc nhọn đôi** | `{{TEN_BEN_A}}`, `{{SO_HD}}` | ⭐⭐⭐⭐⭐ (Khuyên dùng số 1) | Chuẩn quốc tế, không bao giờ bị lẫn với dấu ngoặc đơn chú thích trong luật. Script nhận diện tuyệt đối. |
| **Thẻ ngoặc vuông** | `[TEN_BEN_A]`, `[SO_HD]` | ⭐⭐⭐⭐ (Tiện gõ nhanh) | Dễ gõ trên điện thoại, nhận diện tốt. |
| **Tô màu Highlight / Chữ đỏ** | Chữ đỏ hoặc bôi vàng ô | ⭐⭐⭐ (Thao tác trực quan trên Word) | Người dùng nhìn bằng mắt rất dễ thấy, AI quét theo style run. |

---

## 3. DANH MỤC CÁC TRƯỜNG BIẾN ĐỘNG CHUẨN (PLACEHOLDER REGISTRY)

Khi người dùng cung cấp bảng dữ liệu hoặc form, các khóa (keys) chuẩn hóa bao gồm:

### A. Thông tin chung về Hợp đồng
- `SO_HOP_DONG` / `SO_HD`: Số hợp đồng (ví dụ: `HM-2026/CX-01`)
- `NGAY_KY`, `THANG_KY`, `NAM_KY`: Ngày tháng năm ký kết
- `DIA_DIEM_KY`: Địa điểm ký (ví dụ: `TP. Hồ Chí Minh` / `胡志明市`)

### B. Bên A — Bên Mua (Khách hàng)
- `TEN_BEN_A`: Tên công ty tiếng Việt
- `TEN_TRUNG_BEN_A`: Tên công ty tiếng Trung (nếu có)
- `MST_A` / `MST_BEN_A`: Mã số thuế
- `DIA_CHI_A`: Địa chỉ trụ sở/nhà máy
- `DAI_DIEN_A`: Họ tên người đại diện pháp luật
- `CHUC_VU_A`: Chức vụ (Tổng Giám Đốc, Giám Đốc Nhà Máy...)
- `SDT_A`: Số điện thoại liên hệ

### C. Bên B — Bên Bán (Hong Ming Global - Mặc định cố định)
- Tên công ty: `CÔNG TY TNHH TOÀN CẦU HONG MING` (宏明環球有限公司)
- MST: `0318280158`
- Địa chỉ: Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP.HCM
- Đại diện: `TANG WEI LI` (Đường Vĩ Lực) - Chức vụ: Tổng Giám Đốc

### D. Giá trị hợp đồng & Thanh toán
- `TONG_TIEN_SO`: Giá trị hợp đồng bằng số (ví dụ: `385.000.000`)
- `TONG_TIEN_CHU_VIET`: Số tiền bằng chữ tiếng Việt (Script tự động sinh nếu để trống)
- `TONG_TIEN_CHU_TRUNG`: Số tiền bằng chữ tiếng Trung Phồn thể (Script tự động sinh nếu để trống)
- `TIEN_COC_PHAN_TRAM`: Tỷ lệ tạm ứng đợt 1 (ví dụ: `30%` hoặc `50%`)
- `TIEN_COC_SO`: Số tiền cọc đợt 1
- `TIEN_DOT_2_PHAN_TRAM`: Tỷ lệ đợt 2 (ví dụ: `40%`)
- `TIEN_DOT_2_SO`: Số tiền đợt 2
- `TIEN_FAC_PHAN_TRAM`: Tỷ lệ đợt cuối nghiệm thu (ví dụ: `10%` hoặc `20%`)
- `TIEN_FAC_SO`: Số tiền đợt cuối
- `THOI_HAN_GIAO_HANG`: Thời gian giao hàng (ví dụ: `60 - 80 ngày kể từ ngày nhận đủ cọc`)
- `THOI_HAN_BAO_HANH`: Thời gian bảo hành (ví dụ: `12 tháng`)

---

## 4. CÔNG CỤ THỰC THI TỰ ĐỘNG (`scripts/fill_contract_docx.py`)

Kỹ năng này trang bị script tự động điền hợp đồng bằng Python, sử dụng thuật toán **Cross-Run Placeholder Replacement**:
- Xử lý triệt để lỗi Word chia nhỏ chuỗi `{{TÊN_TRƯỜNG}}` thành nhiều XML runs.
- Duyệt đệ quy: Body paragraphs, All tables (kể cả bảng lồng nhau), All Headers & Footers.
- Tự động bảo vệ chống lỗi file đang mở (`PermissionError` -> sinh `_v2.docx`).

### Cách sử dụng dòng lệnh:
```bash
python .agents/skills/hongming-pm-hub/scripts/fill_contract_docx.py \
  --template "HOP_DONG_MAU.docx" \
  --data "du_lieu_hop_dong.json" \
  --output "HOP_DONG_HOAN_TAT.docx"
```

### Sử dụng trực tiếp trong code Python:
```python
from fill_contract_docx import fill_contract_document

data = {
    "SO_HOP_DONG": "HM-2026/VONMAX-02",
    "TEN_BEN_A": "CÔNG TY TNHH VONMAX (VIỆT NAM)",
    "MST_A": "2300998877",
    "DAI_DIEN_A": "Ông CHEN WEI HUNG",
    "CHUC_VU_A": "TỔNG GIÁM ĐỐC",
    "TONG_TIEN_SO": "1.250.000.000",
}
result = fill_contract_document("HOP_DONG_MAU.docx", "HOP_DONG_VONMAX.docx", data)
print(result)
```
