> **Cập nhật xác nhận30/10/2026:** SEIYO phase3 đã được yêu cầu thanh toán cọc30%; khách hẹn lại trả hôm nay30/10. Đã cập nhật mô tả và lịch hẹn trên web; chưa xác nhận nhận tiền.

# Rà soát mốc đã thực hiện đến30/10/2026

Báo cáo này thay thế kết luận “9 khoản thiếu ngày” trong báo cáo lịch trước. Mốc tương lai không được coi là thiếu cập nhật; mốc kế hoạch đã qua cũng không tự chứng minh thực hiện. Đối chiếu dấu hoàn thành trong các lịch và hồ sơ đã kiểm tra, kèm xác nhận mới của người dùng.

| Dự án | Sự kiện đã có căn cứ | Đối chiếu web / xử lý |
|---|---|---|
| Cheng Feng | Người dùng xác nhận thực thu cọc300triệu ngày30/10/2026 | Đã đúng tiền/ngày; đã sửa mô tả “chờ trả05/11” thành đã nhận cọc; đồng bộ hạn đang lưu25/10 ở milestone liên kết, không suy ra ngày kích hoạt mới. |
| Cheng Feng | File13 D6,D7,D9,D12,D13,D14 tick hoàn thành: khảo sát, đặt hàng, kéo cáp, nhận thiết bị, lắp mạng và bảng65inch | B10/D10 nghiệm thu kéo cáp/đợt2 chưa tick; B17/D17 nghiệm thu thiết bị/đợt3 chưa tick. Cần kiểm tra biên bản nghiệm thu hoặc việc gửi yêu cầu nghiệm thu để xác định đã đủ điều kiện thu chưa. Chưa đủ căn cứ đặt ngày phát sinh/hạn trả cho đợt2–3. |
| JIYANG phần cứng | File169 D5–D7 tick: cọc, đặt hàng, sản xuất/chuẩn bị hàng | Web đã thu53.460.000đ; người dùng xác nhận ngày14/09/2026. Đã sửa ngày thực thu AR51 và milestone105 từ14/05 sang14/09. Chuẩn bị hàng không đồng nghĩa giao/lắp/nghiệm thu xong, nên không tự kích hoạt đợt2. |
| JIYANG phần mềm | File170 D6,D7 tick: khảo sát yêu cầu và họp chốt chức năng; web đã thu148,5triệu | Người dùng xác nhận ngày cọc14/09/2026; đã sửa AR54 và milestone108. D5 trong file vẫn chưa tick cọc, là cập nhật thiếu ở file; nguồn gốc được giữ nguyên. Không có dấu hoàn thành triển khai/UAT để kích hoạt đợt2–3. |
| SEIYO phase2 | File224 các mốc ký/cọc, kiểm tra lắp đặt60%, nghiệm thu/UAT và thanh toán10% đều tick hoàn thành | Web hai hợp đồng277,33triệu và350,26triệu đã thu đủ. Không phát hiện khoản phải thu còn thiếu do các mốc này. Không ghi đè ngày nhận thực tế bằng tuần kế hoạch. |
| SEIYO phase3 | Hồ sơ ký đã đối chiếu: ký13/10/2026; file231 chưa tick các công việc | Web đã ghi hợp đồng ký và cọc chưa thu. Ngày bắt đầu tính hạn cọc còn trống dù milestone có trạng thái đã kích hoạt, kỳ hạn0; đây là trường thiếu cần thống nhất với hồ sơ ký. Hạn25/10 là ngày đề nghị đang lưu, không mặc định thay bằng một ngày dự kiến khác. Chưa có bằng chứng nghiệm thu lắp đặt/FAC để kích hoạt đợt2–3. |
| Strong Way / Vonmax lịch cũ | Không có căn cứ mới xác nhận phát sinh khoản thu cần cập nhật từ các lịch đã rà | Không thêm công nợ và không sửa hạn theo lịch tương lai/lịch cũ. |

## Kết quả ưu tiên

1. Đã giải quyết ngày cọc JIYANG và mô tả cọc Cheng Feng theo xác nhận người dùng; giữ nguyên mọi số tiền.
2. Cần kiểm tra thực tế biên bản kéo cáp/lắp thiết bị Cheng Feng: công việc đã tick nhưng nghiệm thu chưa tick. Không kết luận đã đến hạn từ dấu hoàn thành thi công riêng lẻ.
3. SEIYO phase3: đã ký hợp đồng là sự kiện thực tế; trường ngày kích hoạt cọc chưa điền dù đã có dữ liệu hồ sơ ký. Cần phân biệt ngày bắt đầu nghĩa vụ cọc và ngày đề nghị trả25/10 khi hoàn thiện cách lưu/hiển thị.
4. JIYANG phần mềm cần cập nhật dấu hoàn thành cọc ở bản lịch đang sử dụng; không thay đổi file nguồn trong lần rà soát này.

Sao lưu trước sửa: database/backups/before_completed_deposits_20261030_095251.db. Nhật ký đầy đủ before/after được lưu trong database/COMPLETED_DEPOSITS_CONFIRMED_*.json. Đã kiểm tra toàn bộ số tiền không đổi, các khoản ngoài AR51/54/65 không đổi, hợp đồng chính không đổi và kiểm tra tính toàn vẹn dữ liệu đạt.
