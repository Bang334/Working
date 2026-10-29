# HỆ THỐNG ĐIỀN HỢP ĐỒNG TỰ ĐỘNG THEO MẪU

Thư mục: `scripts/hop_dong_generator/`  
Công ty: **CÔNG TY TNHH TOÀN CẦU HONG MING**

---

## 1. NGUYÊN TẮC CỐT LÕI (ZERO-LAYOUT-DISTORTION)
- **CHỈ THAY THẾ DỮ LIỆU / THÔNG TIN, TUYỆT ĐỐI KHÔNG LÀM VỠ BỐ CỤC:**
  - Giữ nguyên 100% lề trang A4, ngắt trang, font chữ (`Times New Roman`, `微軟正黑體`), cỡ chữ, in đậm/in nghiêng.
  - Bảng sản phẩm tự động cập nhật số dòng theo thực tế, giữ nguyên độ rộng cột, viền bảng và định dạng số.
  - Tự động chuyển đổi số tiền thành chữ song ngữ chuẩn kế toán:
    - Tiếng Việt: `Bảy trăm tám mươi mốt triệu năm trăm ba mươi nghìn đồng chẵn.`
    - Tiếng Trung (Đại tả 大寫): `越南盾柒億捌仟壹佰伍拾參萬整`
  - Tự động tính toán các đợt thanh toán theo % (ví dụ: 35% cọc, 55% lắp đặt, 10% nghiệm thu FAC).
  - Giữ nguyên tiêu đề tiếng Trung của từng đợt trong mẫu (`簽約定金`, `設備安裝款`, `驗收尾款`), không tự đổi sang `第…期`.
  - Nếu hợp đồng chỉ có ba đợt, xóa hẳn paragraph đợt dư để Word không còn hiển thị số thứ tự `4.` rỗng.
  - Không tự dịch hoặc suy đoán tên pháp nhân, địa chỉ, MST, đại diện và chức vụ. Trường không có trong dữ liệu đầu vào sẽ được yêu cầu bổ sung hoặc để trống theo loại trường.
  - Tên công ty, địa chỉ và chức vụ chỉ điền đúng nội dung đã cung cấp vào placeholder; không tự nối bản dịch tiếng Trung.
  - Xử lý được placeholder `{{...}}` kể cả khi Word chia placeholder qua nhiều run; file đầu ra không được còn dấu ngoặc placeholder.
  - Bộ kiểm tra đọc toàn bộ OOXML, bao gồm chữ nằm trong textbox/shape.

---

## 2. CẤU TRÚC THƯ MỤC
```
scripts/hop_dong_generator/
├── dien_hop_dong_tu_dong.py       # Script chính điều khiển điền hợp đồng
├── generate_jinxun_mes_contract.py # Script JINXUN chuyên biệt, không dùng JSON/AI
├── ai_contract_parser.py          # Module AI gọi Google Gemini API để bóc tách text thô
├── chay_thu_nghiem.bat            # File chạy thử nghiệm nhanh 1-click trên Windows
├── tests/
│   ├── kiem_tra_hop_dong.py       # Kiểm tra dữ liệu cả trong textbox/shape
│   └── test_placeholders.py        # Kiểm tra placeholder bị chia qua nhiều run
└── outputs/
    ├── final/                      # File đã vượt qua kiểm tra
    └── archive/                    # Bản cũ/chưa đạt, chỉ để đối chiếu
```

---

## 3. CÁCH SỬ DỤNG

### Cách 1: Sử dụng AI để tự động đọc văn bản tự do (Khuyên dùng khi dữ liệu đầu vào chưa có cấu trúc)
Khi nhận tin nhắn Zalo, WeChat, email hoặc ghi chú lộn xộn, chỉ cần truyền vào tham số `--ai-text`:
```bash
python scripts/hop_dong_generator/dien_hop_dong_tu_dong.py \
  --template "Bieu Mau/Mau_Goc_Hop_Dong_Mua_Ban.docx" \
  --ai-text "Tên công ty: CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM, MST 0801382054, đại diện HUANG YU, thanh toán 35% cọc, 55% lắp đặt, 10% nghiệm thu, tổng tiền 781.530.000 VND" \
  --output "Hop_Dong_JINXUN.docx"
```

### Cách 2: Sinh hợp đồng JINXUN từ script chuyên biệt, không dùng JSON
```bash
python scripts/hop_dong_generator/generate_jinxun_mes_contract.py \
  --template "Bieu Mau/Mau_Goc_Hop_Dong_Mua_Ban.docx" \
  --output "scripts/hop_dong_generator/outputs/final/Hop_Dong_JINXUN_MES_Lite_DA_SUA_V2.docx"
```

---

## 4. KẾT QUẢ HỢP ĐỒNG JINXUN ĐÃ XUẤT THÀNH CÔNG
- **File Word hoàn chỉnh:** `outputs/final/Hop_Dong_JINXUN_MES_Lite_DA_SUA_V2.docx`
- **Bên A:** CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM
- **Tổng giá trị:** 781.530.000 VND
- **Phân bổ:**
  - Đợt 1 (35%): 273.535.500 VND
  - Đợt 2 (55%): 429.841.500 VND
  - Đợt 3 (10%): 78.153.000 VND
