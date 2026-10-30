> **Đã thay phạm vi:** Kết luận9 khoản thiếu ngày dưới đây dựa trên lịch kế hoạch, không phải9 khoản đã phát sinh nghĩa vụ thu. Xem RA_SOAT_MOC_DA_THUC_HIEN_20261030.md để biết kết quả hiện hành và ngày cọc đã được người dùng xác nhận.

# Đối chiếu lịch triển khai và công nợ — 30/10/2026

Phạm vi: 8 workbook lịch/tiến độ (Strong Way có 2 lịch MES/QMS), kiểm tra nội dung, dấu hoàn thành, màu theo tháng/tuần và dữ liệu hiện tại của web. Quét thêm nội dung toàn bộ workbook trong bộ hồ sơ để tìm lịch nhúng; workbook báo giá JIYANG số 166 có nhắc bảng tiến độ nhưng không phải một lịch độc lập. Chỉ đọc; không thay đổi tiền, ngày hay trạng thái trên web.

## 1. Các mốc đang thiếu trên web

| Dự án | Nguồn Excel | Mốc trong lịch | Hiện tại trên web | Kết luận |
|---|---|---|---|---|
| JIYANG phần cứng 178,2 triệu | File 169, JI YANG 專案, B14/U14 | Đợt 2: 55% = 98.010.000đ; ô lịch U thuộc tháng 12/2026, W1 | AR52: start_date/due_date/term đều trống; chưa thu | Thiếu lịch dự kiến tháng 12 tuần 1. Không có ngày 28 cụ thể ở mốc này. |
| JIYANG phần cứng | File 169, B19–B20/U19–U20 | UAT, đợt 3: 15% = 26.730.000đ; tháng 12 W1 | AR53: các trường ngày và kỳ hạn trống | Thiếu kế hoạch nghiệm thu/thu đợt cuối; tuần không xác định được ngày chính xác. |
| JIYANG phần mềm 495 triệu | File 170, B22/Y22 | Triển khai/cài đặt và đợt 2: 55% = 272.250.000đ; tháng 12/2026 W5 | AR55: các trường ngày và kỳ hạn trống | Thiếu lịch dự kiến cuối tháng 12. |
| JIYANG phần mềm | File 170, B25/Z25 | UAT và đợt 3: 15% = 74.250.000đ; tháng 1/2027 W1 | AR56: các trường ngày và kỳ hạn trống | Thiếu lịch dự kiến đầu tháng 1/2027. |
| Cheng Feng 1 tỷ | File 13, B10/K10 | Nghiệm thu kéo cáp và đợt 2: 30% = 300 triệu; tháng 10 W5; L10:Q10 có màu nhạt nối sang các tuần sau | AR66: các trường ngày/kỳ hạn trống; chưa thu | Thiếu kế hoạch thu; màu nhạt chưa đủ để kết luận gia hạn chính thức. |
| Cheng Feng | File 13, B17/L17:M17 | Nghiệm thu lắp thiết bị và đợt 3: 30% = 300 triệu; tháng 11 W1–W2 | AR67: các trường ngày/kỳ hạn trống | Thiếu kế hoạch. |
| Cheng Feng | File 13, B21–B22/M21:M22 | FAC, bàn giao và đợt 4: 10% = 100 triệu; tháng 11 W2 | AR68: các trường ngày/kỳ hạn trống | Thiếu kế hoạch; cần giải quyết nhãn tháng FAC lệch trước khi nhập. |
| SEIYO phase 3 | File 231, B16–B17/K16:K17 | Biên bản lắp đặt và đợt 2 60% = 427.212.000đ; tháng 11 W3; T/T15 ngày sau ký biên bản | AR32: ngày bắt đầu/hạn trống, đã có term15; milestone chưa kích hoạt | Thiếu lịch dự kiến; hạn thực tế chưa thể tính nếu chưa có ngày biên bản. Lịch vẽ biên bản và thu cùng tuần không phù hợp một hạn đủ15 ngày. |
| SEIYO phase 3 | File 231, B20–B21/K20:L21 | FAC khoảng15/11/2026; đợt 3 10% = 71.202.000đ, T/T30 ngày sau FAC; thanh màu ở tháng11 W3–W4 | AR33: ngày bắt đầu/hạn trống, đã có term30; milestone chưa kích hoạt | Lịch màu sớm hơn hạn suy ra. Nếu FAC thực tế15/11 thì hạn dự kiến15/12/2026; hiện chỉ là giả định kế hoạch. |

Tổng cộng 9 khoản chưa thu thuộc 4 hợp đồng đã có lịch/mốc kế hoạch trong Excel nhưng chưa có ngày bắt đầu và hạn trên bảng công nợ. Toàn bộ46 khoản hiện có start_date trống; điều này cho thấy trường này chưa được điền từ nguồn cũ, không có nghĩa46 khoản đều đã có ngày nguồn đủ rõ.

## 2. Mâu thuẫn cần xử lý trước khi nhập

- **JIYANG ngày thực thu cọc:** AR51 và AR54 đều ghi14/05/2026, trước ngày ký27/08 và25/08/2026. Chưa có chứng từ chứng minh đây là trả trước hay lỗi ngày. Hạn đang ghi14/09/2026 không phải ngày thực thu. Giữ số tiền cọc đã xác nhận; không tự đổi14/05 thành14/09.
- **JIYANG phần mềm dấu hoàn thành cọc:** File170 D5 chưa tick trong khi web đã thu148,5 triệu. Đây là trạng thái cập nhật lệch giữa hai nguồn, không tự xóa khoản thu trên web. F5 đặt mốc ký tháng8, P5 còn có màu tại tháng10 W5, cần xác định ý nghĩa lần đánh dấu sau.
- **Cheng Feng:** A1/B5 còn ghi chưa ký và mã báo giá HMV220920260001, D5 lại tick hoàn thành; web dùng mã HMV021020260001 và đã thu300 triệu ngày30/10. Nguồn Excel chưa đồng bộ. B9 nêu thi công bắt đầu28/09/2026 nhưng ô màu J9 lại tháng10 W4: ngày28 này là ngày bắt đầu thi công, không phải ngày thanh toán đợt2. U2 gắn nhãn FAC tháng1/2027 nhưng M21/M22 đặt FAC và thu cuối tháng11 W2: nội bộ file lệch.
- **SEIYO phase3:** A1 dùng mã cũ HMV22092026SY0001, dự kiến ký19/10; B5 dự kiến14/10; hồ sơ ký đã đối chiếu và web dùng HMV04102026SY0001, ký13/10. A1 nói xong cuối tháng11; B20 FAC15/11; R2 gắn nhãn FAC tháng1/2027, còn K20 đặt tháng11 W3. Lịch phải được cập nhật thống nhất. Hạn cọc trên web25/10 là ngày đề nghị cũ theo ghi chú, không phải xác nhận ngày trả từ khách.
- **SEIYO phase2:** File224 B22/Q22 đánh dấu đã hoàn thành và lịch đặt thu10% tháng10 W1, web hai hợp đồng ghi thu30/09. Không xung đột số tiền/trạng thái hiện tại, nhưng kế hoạch và ngày thực nhận khác nhau; không ghi đè ngày thực thu bằng tuần kế hoạch. Ngày ký ở tiêu đề20/07 khác hồ sơ ký22/07 đã đối chiếu trước đó.
- **Strong Way:** Chưa có công nợ trên web, vẫn giữ theo chỉ đạo không tự thêm. File238 MES: B17 ghi thu15/01/2027 nhưng O17 thuộc tháng12/2026 W5; B22 ghi26/02/2027 nhưng T22 thuộc tháng1 W5. SheetQMS: B17/P17 phù hợp tháng1 W1 (chưa định ngày15), B22/T22 cũng đặt sớm một tháng so với nội dung26/02. Nội dung ghi kỳ hạn17/01 và28/02 tương ứng18/12+30 và29/01+30; đây là kế hoạch, chưa phải mốc thực tế.
- **Vonmax:** File346 là lịch cũ2025–đầu2026, không có ngày thu/tỷ lệ từng khoản để đối chiếu hạn công nợ cụ thể; không dùng thay hạn hiện tại. Không thêm dự án400,9 triệu đã hoàn thành theo chỉ đạo.
- **SEIYO file209:** Chỉ mô tả tuần tương đốiW1–W6, không có ngày bắt đầu lịch tuyệt đối; không đủ để điền một hạn ngày cụ thể.

## 3. Dữ liệu trên web tự lệch nhau

Cheng Feng đợt1: bảng công nợ AR65 ghi due_date2026-10-25, đã thu2026-10-30, start_date trống; milestone liên kết vẫn ghi trigger_date26/10/2026, due_date05/11/2026 và term10 từ đề nghị gộp cũ. Hai nơi chưa đồng bộ. Không dùng milestone cũ để ghi đè khoản đã thu. Các ghi chú nguồn của milestone JIYANG vẫn nhắc số tiền trước sửa VAT; số tiền chính đã sửa đúng, nhưng diễn giải lịch sử cần hiển thị rõ là dữ liệu cũ.

## 4. Cách cập nhật hợp lý

1. Lưu riêng lịch dự kiến theo tuần/tháng và ngày chính xác được ghi trong văn bản; luôn có đường dẫn nguồn, sheet/ô.
2. Ngày bắt đầu tính hạn chỉ đặt khi mốc kích hoạt xảy ra thực tế (ký biên bản, nghiệm thu…), hoặc ghi rõ là dự kiến. Số ngày dự kiến công việc ở cộtE không tự động là kỳ hạn thanh toán.
3. Hạn thanh toán = ngày kích hoạt thực tế + kỳ hạn hợp đồng. Không biến ngày thi công hay ô lịch tuần thành hạn phải thu chính thức.
4. Trường hợp đang thiếu lịch phải hiện “Chưa có lịch thanh toán xác nhận”; nhãn “Chưa đến hạn” riêng lẻ dễ khiến người xem tưởng đã có ngày hạn.
5. Ưu tiên xử lý JIYANG AR52–56, ChengFeng AR66–68 và SEIYO AR32–33; giải quyết xung đột nêu trên trước khi cập nhật ngày chính xác. Không cần danh mục dự án độc lập.

## 5. Hồ sơ đã kiểm tra

- File 13: [CHENG FENG 晟峰\專案導入進度表-BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN_\BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN (Schedule)  專案導入期程表Giá trị合約金額 1.000.000.000 VND.xlsx](C:/Users/HM-Sales01/Downloads/drive-download-20261030T014758Z-1-001/CHENG FENG 晟峰/專案導入進度表-BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN_/BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN (Schedule)  專案導入期程表Giá trị合約金額 1.000.000.000 VND.xlsx)
- File 169: [JIYANG 吉洋電子\專案進度_TIẾN ĐỘ DỰ ÁN_\BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN Schedule  專案導入期程表 Giá trị.合約金額-178.200.000 VND.xlsx](C:/Users/HM-Sales01/Downloads/drive-download-20261030T014758Z-1-001/JIYANG 吉洋電子/專案進度_TIẾN ĐỘ DỰ ÁN_/BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN Schedule  專案導入期程表 Giá trị.合約金額-178.200.000 VND.xlsx)
- File 170: [JIYANG 吉洋電子\專案進度_TIẾN ĐỘ DỰ ÁN_\BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN Schedule  專案導入期程表 Giá trị.合約金額-495.000.000 VND.xlsx](C:/Users/HM-Sales01/Downloads/drive-download-20261030T014758Z-1-001/JIYANG 吉洋電子/專案進度_TIẾN ĐỘ DỰ ÁN_/BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN Schedule  專案導入期程表 Giá trị.合約金額-495.000.000 VND.xlsx)
- File 209: [SEIYO 正揚\Phase 2\HM浤詺 - 正揚SEIYO北寧廠 Phase2 機聯網佈建Schedule.xlsx](C:/Users/HM-Sales01/Downloads/drive-download-20261030T014758Z-1-001/SEIYO 正揚/Phase 2/HM浤詺 - 正揚SEIYO北寧廠 Phase2 機聯網佈建Schedule.xlsx)
- File 224: [SEIYO 正揚\Phase 2\專案導入期程表-BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN\BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN (Schedule)-專案導入期程表.xlsx](C:/Users/HM-Sales01/Downloads/drive-download-20261030T014758Z-1-001/SEIYO 正揚/Phase 2/專案導入期程表-BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN/BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN (Schedule)-專案導入期程表.xlsx)
- File 231: [SEIYO 正揚\Phase 3\專案導入期程表-BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN\專案導入期程表  BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN.xlsx](C:/Users/HM-Sales01/Downloads/drive-download-20261030T014758Z-1-001/SEIYO 正揚/Phase 3/專案導入期程表-BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN/專案導入期程表  BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN.xlsx)
- File 238: [Strong Way 崇瑋\專案導入期程表-BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN\專案導入期程表BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN 1.750.000.000 VND.xlsx](C:/Users/HM-Sales01/Downloads/drive-download-20261030T014758Z-1-001/Strong Way 崇瑋/專案導入期程表-BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN/專案導入期程表BẢNG TIẾN ĐỘ TRIỂN KHAI DỰ ÁN 1.750.000.000 VND.xlsx)
- File 346: [VONMAX 弘聲\Phase2\Vonmax_SMB專案 第二階段 schedule期程_202512_V1.0.xlsx](C:/Users/HM-Sales01/Downloads/drive-download-20261030T014758Z-1-001/VONMAX 弘聲/Phase2/Vonmax_SMB專案 第二階段 schedule期程_202512_V1.0.xlsx)
