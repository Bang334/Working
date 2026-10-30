# Đối soát lịch thanh toán và công nợ — 29/10/2026

Nguồn: QLDA_TRANG_PM_2026.xlsx (Sheet 3), ảnh ngày thu người dùng cung cấp và quy tắc người dùng xác nhận: đợt sau đã thanh toán thì các đợt trước đã thanh toán. File Excel gốc được giữ nguyên để đối chiếu.

## Các sửa đổi đã áp dụng

- MES Lite Jinxun HMV100120260001: bổ sung 35% = 273.535.500đ đã thu theo thứ tự; khoản55% = 429.841.500đ thu ngày29/08/2026 theo ảnh. Tổng đã thu90% =703.377.000đ; còn10% =78.153.000đ.

- Vonmax giai đoạn2 HMV07032026001: bổ sung35% =451.700.970đ theo thứ tự; tổng35/55/10 và đã thu100%.

- CX RFID HMV151020250001: bổ sung đợt đầu40% =93.600.000đ theo thứ tự; đủ40/40/20, đã thu80%, còn46.800.000đ.

- Khoản sửa chữa13.700.000đ có trạng thái đã thanh toán và ngày23/10/2026 trong nguồn nhưng ô tiền thu trống: đã đối soát về13.700.000đ đã thu.

- Chỉ lưu thời điểm chậm nhất đã thu cho các đợt suy ra; không điền ngày thực nhận. Ngày thu thật chưa biết vẫn để trống.

- Biểu đồ dùng giá trị toàn hợp đồng làm mẫu số; không kéo phần55+10 thành100%. Đợt còn thiếu nhưng chưa đủ căn cứ hiển thị phần kẻ sọc, không tự ghi thành tiền đã thu hoặc còn nợ.

- Sửa thứ tự CHENGFENG thành30/30/30/10. Bảo toàn metadata đối soát khi đồng bộ từ hợp đồng.

## Đối chiếu toàn bộ mã và dự án

| Mã | Tỷ lệ các đợt | Đã thu |

|---|---|---|

| HMV021020260001 | 30% + 30% + 30% + 10% = 100% | 0% |

| HMV22092026SY0001 | 30% + 60% + 10% = 100% | 0% |

| HMV100120260001 | 35% + 55% + 10% = 100% | 90% |

| HMV060620250001 | 90% + 10% (90% là tổng lịch sử, chưa tách từng đợt) = 100% | 90% |

| HMV060620250002 | 90% + 10% (90% là tổng lịch sử, chưa tách từng đợt) = 100% | 90% |

| Tiết kiệm năng lượng nhà máy 工廠節能 | 100% = 100% | 0% |

| HMV151020250001 | 40% + 40% + 20% = 100% | 80% |

| DFV20260505 | 30% + 60% + 10% = 100% | 90% |

| HM27082026JI002 | 30% + 55% + 15% = 100% | 30% |

| HM25082026JI001 | 30% + 55% + 15% = 100% | 30% |

| HMV27082026-001 | 50% + 50% = 100% | 50% |

| HMV220920260001 | 50% + 50% = 100% | 50% |

| - | 100% = 100% | 0% |

| HMSY200720260001 | 30% + 60% + 10% = 100% | 100% |

| HMSY200720260002 | 30% + 60% + 10% = 100% | 100% |

| HMV07032026001 | 35% + 55% + 10% = 100% | 100% |

| SC-2026-005 | 50% + 50% = 100% | 100% |

| - | 100% = 100% | 100% |

| HMV050520260001 | 100% = 100% | 100% |

| - | 100% = 100% | 100% |

| - | 100% = 100% | 100% |

| BÁO GIÁ PIN BAT-RFR900 → BAT-RFR900 電池報價單 | 100% = 100% | 100% |

## Kết quả kiểm tra email và hợp đồng Vonmax

Email16/10/2026 trích thư19/09/2026 xác nhận phần cứng HMV060620250002/545.454.545đ và phần mềm HMV060620250001/1.100.000.000đ, đều chỉ còn10% chưa thu. Đã sửa mã phần cứng, loại dòng110triệu ghi nhãn phần cứng trùng khoản phần mềm.

Đã bổ sung lịch sử đã thu90% theo xác nhận dư nợ trong email: phần cứng490.909.091đ, phần mềm990.000.000đ; không tự chia lịch sử thành35/55 hoặc30/60 vì chưa có hợp đồng gốc hai mã này. Chỉ lưu chậm nhất đã thu16/10, không ghi ngày thực nhận giả.

Bản hợp đồng scan ký đóng dấu HMV07032026001, trang1–2: tổng1.290.574.200đ, điều khoản35%=451.700.970đ,55%=709.815.810đ,10%=129.057.420đ. Email16/10 gõ HMV070320260012 không khớp bản ký; giữ mã theo bản ký HMV07032026001.

Khoản cuối phần cứng: thư gốc19/09 đề nghị54.545.454đ, email nhắc tổng16/10 làm tròn54.545.455đ. Giữ số phiếu yêu cầu chi tiết54.545.454đ; chênh1đ đã ghi chú.

Nguồn email đã đọc: D:\Working\.qa\vonmax_contract_mail\Vonmax_Email_Doi_Chieu_20261016.md

Nguồn hợp đồng ký: D:\Working\.qa\vonmax_contract_mail\mail_003\VONMAX HMV07032026001.pdf

## Các lỗi của file nguồn

- Dòng8/9 Darfon trùng27/28; đã xử lý từ lần nhập trước.

- Dòng44: ngày thu và ngày hẹn chứa serial6686371 vượt giới hạn Excel; ảnh người dùng xác nhận29/08/2026.

- J17/J19/J31 dùng công thức cộng tỷ lệVAT vào tiền đã thu, gây dư0,08đ; đã sửa từ lần nhập trước.

- Tổng I55/J55/K55 chỉ cộng đến dòng45, bỏCHENGFENG46–49; E55 cộng các đợt lặp HĐ và bỏ phần lớn bảng. Không dùng các ô tổng này để xác nhận tổng công nợ.

- JIYANG có ngày thu14/05/2026 trong khi nội dung/mã tham chiếu xuất hiện tháng8–9; giữ nguyên ngày nguồn và yêu cầu đối chiếu chứng từ, không tự sửa ngày.

- Tỷ lệ hoặc số đã thu của các khoản độc lập không có mãHĐ chỉ kiểm tra theo giá trị dòng, không gộp cùng khách.

## Bảo toàn

Các tệp hồ sơ nghiệm thu không đổi; không xóa workflow hoặc chứng từ trong lần đối soát. Bản sao lưu riêng có trong database/backups/schedule_review_*.