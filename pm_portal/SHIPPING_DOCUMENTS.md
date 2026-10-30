# Invoice & Packing List

Trang `/shipping-documents` trong menu chuỗi hồ sơ dự án.

1. Thêm một hoặc nhiều file nguồn (XLSX, DOCX, PDF, PNG/JPEG/WebP, TXT/CSV/TSV UTF-8) và nhiều đoạn ghi chú.
2. Gán `Đơn hàng / dữ liệu mới` cho nguồn chính, `Mẫu / tham khảo` cho chứng từ cũ. Nguồn tham khảo không được dùng để lấp số lượng, giá, cân nặng hoặc số chứng từ mới.
3. Phân tích AI, kiểm tra thông tin và sửa bảng hàng. Không tự ghi nhận công nợ hoặc giao hàng. Dịch vụ giữ trong Invoice, bỏ khỏi Packing List.
4. Xuất hai Excel độc lập; cân nặng chưa biết để trống. Thêm cân nặng sau và tạo lại. Nút tải ẩn khi dữ liệu đã thay đổi để tránh tải bản cũ.

Giới hạn: 20 file, 10 MB/file, tổng 25 MB; 20 đoạn ghi chú, tổng 100.000 ký tự; 300 dòng hàng. XLSX đọc mọi dòng có dữ liệu đến giới hạn an toàn, không âm thầm cắt ở dòng 60. File `.xls` cũ phải chuyển sang `.xlsx` trước.

Mẫu trình bày đã được chỉnh và duyệt trong chat Seiyo ngày30/10/2026 nằm tại `app/resources/shipping_documents/`. Header chỉ một lần; DESCRIPTION căn giữa ngang/dọc; nhóm lấy từ tiêu đề khối đơn hàng; tổng ngay sau dòng cuối; vùng in theo dữ liệu. Các bản xuất lưu thành từng bộ riêng trong `Ho So Du An/Ho So Hai Quan/<uuid>/`, gồm dữ liệu đã kiểm tra, hai Excel, manifest. Chỉ công bố URL tải khi cả hai file hoàn tất.

Backend gọi Gemini bằng cấu hình AI hiện hành; ưu tiên model lite có trong danh sách cấu hình và dùng cơ chế dự phòng chung. Đọc XLSX bằng openpyxl, DOCX bằng python-docx, PDF/ảnh gửi đa phương thức. Dữ liệu upload là tài liệu, không phải chỉ thị hệ thống.

Xuất workbook bằng Artifact Tool, không dựng lại bằng openpyxl. Runtime mặc định là bộ Node và node_modules do Codex desktop cài trong thư mục `.cache/codex-runtimes/codex-primary-runtime/dependencies/node` của tài khoản chạy ứng dụng. Máy khác có thể đặt `SHIPPING_NODE_EXECUTABLE` và `SHIPPING_NODE_MODULES`. Không tự sửa/cài thư viện trong dependency bundle. Khi thiếu runtime, giao diện báo lỗi và giữ dữ liệu để thử lại.

Kiểm thử: `python -m pytest tests/test_shipping_documents.py -q`. Bao gồm parser sau dòng60, nhiều nguồn và ghi chú, phân biệt mẫu cũ, giá0/thiếu giá, sai tổng nguồn, dịch vụ, số dòng1/10/21/35, công thức/trọng lượng chưa đủ và đủ, căn giữa, tải file và đường dẫn không hợp lệ. Browser QA và lượt gọi Gemini thực tế với bộ ba file Seiyo được ghi nhận trong `.qa/shipping_documents/`.
