# Quản lý thư mục và hồ sơ Hong Ming

## Các khu vực chính

- `pm_portal/`: mã ứng dụng, giao diện, API và kiểm thử. Chạy ứng dụng bằng `pm_portal/start_app.bat`.
- `scripts/`: các công cụ chuyên dụng; `scripts/thiet_bi_dfv/` chứa script xử lý thiết bị DFV.
- `Bieu Mau/`: chỉ chứa biểu mẫu và mục lục; giữ nguyên nội dung mẫu, tạo bản mới khi sử dụng.
- `Ho So Du An/Cong Ty/<Ten_Cong_Ty>/<Loai_Ho_So>/`: hồ sơ theo công ty, rồi theo loại như `Hop Dong`, `Bao Gia`, `Nghiem Thu`, `Thiet Bi`. Các thư mục theo loại cũ vẫn tồn tại để tương thích với những phân hệ chưa chuyển.
- `database/pm_portal.db`: cơ sở dữ liệu đang sử dụng; sao lưu cùng các thư mục hồ sơ và biểu mẫu.
- `database/thung_rac/`: bản file chuyển vào thùng rác từ trang quản lý file. Có thể khôi phục thủ công vào thư mục ban đầu; nếu cần liên kết lại hợp đồng, phải kiểm tra và liên kết lại trong ứng dụng.
- `.agents/`: tài nguyên kỹ năng PM. Các thư mục tạm và cache được ẩn trong Explorer của VS Code, không bị xóa.
- `ChuaHieu/` và các tệp ở thư mục gốc: dữ liệu cũ chưa được phân loại; chưa tự động di chuyển để tránh đứt đường dẫn hoặc nhầm bản chính thức.

## Quy tắc đặt tên

Ưu tiên `LoaiTaiLieu_KhachHang_MaHopDongHoacBaoGia_NgayGio_PhienBan.ext`, ví dụ `Bao_Gia_CX_HM-QT-001_20261028_153000_v1.xlsx`. Tên phải thể hiện đúng khách hàng và mã thực tế; không tự đặt mã hợp đồng khi chưa biết. Cùng một lần lưu báo giá trên portal, bản Word và Excel dùng chung phần tên và thời điểm. Các loại biểu mẫu và script cũ vẫn có quy tắc riêng, cần chuyển dần và kiểm thử từng loại.

Trên trang quản lý hồ sơ, các file cùng tên ở các thư mục khác nhau đều được hiển thị. Tải lên qua trang file sẽ lưu vào thư mục theo loại và ghi danh mục; việc gắn với hợp đồng cần thực hiện qua chức năng nghiệp vụ. Đổi tên qua trang file cập nhật các đường dẫn cơ sở dữ liệu được hỗ trợ; file đính kèm nhắc nhở cần xử lý tại chức năng nhắc nhở. Xóa qua trang file chuyển file vào thùng rác; các file đang gắn với dữ liệu báo giá hoặc phiếu thanh toán phải xử lý ở phân hệ tương ứng trước.

Không tự ý di chuyển hay đổi tên hồ sơ bằng Explorer khi ứng dụng đang sử dụng. Việc quét chỉ bổ sung tài liệu chưa có và chỉ tự liên kết khi tên chứa chính xác một mã hợp đồng; liên kết quan trọng cần được người dùng kiểm tra. Các liên kết sai đã tồn tại từ trước không tự động được sửa.

## Cấu hình AI

Đặt biến môi trường `GEMINI_API_KEY` trước khi chạy ứng dụng để dùng Gemini. Khóa cũ đã từng có trong mã nguồn phải được thu hồi hoặc thay tại Google; xóa khỏi mã không tự thu hồi khóa đã lộ.

## Xuất và tìm tài liệu trên PM Portal

- Quy tắc mới áp dụng cho báo giá Word/Excel, nghiệm thu, nghiệm thu lắp đặt, đề nghị thanh toán và đơn xin thanh toán: `Loai_KhachHang_MaTaiLieu_NgayGio.ext` khi có đủ dữ liệu. Dấu thời gian kèm phần phân biệt giúp hạn chế ghi đè; cặp đề nghị thanh toán và báo giá dùng cùng tên gốc cho Word và Excel. Một số phân hệ và script cũ vẫn giữ tên riêng.
- Excel dùng cho bảng số liệu và công thức; Word dùng cho tài liệu văn bản và ký kết. Định dạng cụ thể phụ thuộc chức năng và biểu mẫu gốc; PDF và hình ảnh tải lên được lưu nguyên định dạng.
- Tìm kiếm hỗ trợ tiếng Việt không dấu, nhiều từ không cần đúng thứ tự, đường dẫn, loại file, ngày cập nhật và thông tin hợp đồng đã liên kết. Ví dụ `cx nghiem thu`, `hmv 999` hoặc `mau bao gia eco prime`. Chỉ các file thuộc hồ sơ dự án, biểu mẫu và outputs được quét; công cụ này không tìm nội dung bên trong Word/Excel/PDF.
- Xem [Mục lục biểu mẫu](Bieu%20Mau/MUC_LUC_BIEU_MAU.md) để biết mẫu đang dùng. Mục lục dùng tên file hiện hành sau khi chuẩn hóa.

## Đổi tên mẫu ngày 28/10/2026

Biểu mẫu trong `Bieu Mau/` đã đổi tên theo tiền tố `Mau_Goc_`, `Du_Phong_`, `Mau_` hoặc `Tham_Khao_`. Đường dẫn đang dùng trong PM Portal, script và kỹ năng PM đã được cập nhật. Tra tên cũ, tên mới và SHA-256 tại `scripts/doi_ten_bieu_mau_20261028.json`. Tên trong mục lục biểu mẫu là tên hiện hành.

## Sắp xếp hồ sơ và tài nguyên

- `Ho So Du An/Cong Ty/DFV_Darfon/Thiet Bi/`: hồ sơ thiết bị DFV và `Anh_Pin/` chứa ảnh pin. Script tương ứng đặt tại `scripts/thiet_bi_dfv/`.
- `Ho So Du An/Bao Cao/Tuan/`: báo cáo tuần; `Ho So Du An/Tham Khao/`: tài liệu dự án đã điền dữ liệu, dùng tham khảo.
- `database/du_phong_bieu_mau/`: các bản dự phòng, chia `Ban_Phu/` và `Ban_Luu_Tru/`. Bản dự phòng đơn xin thanh toán vẫn được ứng dụng dùng khi thiếu mẫu chính.
- `pm_portal/app/static/img/signatures/`: chữ ký đang dùng và bản dự phòng.
- `scripts/sap_xep_bieu_mau_20261028.json`: vị trí trước và sau khi chuyển cùng mã băm tại thời điểm chuyển. Bảng đổi tên trước đó là lịch sử và một số đường dẫn trong đó đã thay đổi theo bảng sắp xếp này.

Một số script DFV cũ còn cần ảnh gốc hoặc mẫu nguồn trong Downloads; các nguồn này hiện chưa được tìm thấy. Ảnh pin và hai bảng Excel đã di chuyển đầy đủ, nhưng cần cung cấp lại nguồn còn thiếu trước khi chạy các script phụ thuộc chúng.

## Quản lý theo công ty

Quy ước: `Ho So Du An/Cong Ty/<Ten_Cong_Ty>/<Loai_Ho_So>/`. Ví dụ hồ sơ thiết bị DFV nằm tại `Ho So Du An/Cong Ty/DFV_Darfon/Thiet Bi/`; ảnh pin nằm trong `Anh_Pin/`. Khi tải file qua Quản lý hồ sơ, nhập đúng tên công ty đã có để file vào cùng thư mục; tên mới sẽ tạo thư mục công ty mới. Có thể tìm theo tên công ty kết hợp loại hồ sơ.

Các hồ sơ cũ chưa xác định chắc công ty và các chức năng tạo file chưa chuyển vẫn lưu theo thư mục loại tài liệu cũ; cần đối chiếu và chuyển lần lượt, không tự gán tên công ty. Bảng đối chiếu vị trí chuyển DFV và mã băm nằm tại `scripts/sap_xep_theo_cong_ty_20261028.json`.
