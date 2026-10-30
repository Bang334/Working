# Hướng dẫn sử dụng Việc cần làm

Mở http://127.0.0.1:8032/workflows hoặc chọn **Việc Cần Làm** trong thanh bên.

## Bắt đầu ngày làm việc

1. Chọn **Cần xử lý / gần hạn**. Xem công việc, người phụ trách và bước hiện tại.
2. Chọn việc để đọc phần **Việc tiếp theo** và các hồ sơ còn thiếu.
3. Ghi người phụ trách, người đang chờ và ngày theo dõi rồi lưu.
4. Sau khi thực hiện thật, ghi tên người xác nhận và căn cứ/kết quả, rồi xác nhận hoàn tất bước.

Ngày của trang việc được tính theo giờ Việt Nam. Hạn thu chỉ được tính khi điều kiện mốc đã được xác nhận. Ngày theo dõi là lịch nhắc nội bộ, không thay ngày đến hạn của hợp đồng. Trang cập nhật khi mở hoặc nhấn Làm mới; không có thông báo tự chạy khi ứng dụng đã tắt.

## Thu tiền khách hàng

Các đợt thu lấy từ hợp đồng và mốc đã nhập. Không tạo tỷ lệ thanh toán hoặc khách hàng mẫu.

1. **Điều kiện thu:** đối chiếu hợp đồng và chứng từ. Tải căn cứ; xác nhận ngày thực tế và số ngày T/T. T/T 0 là đến hạn ngay, không tự cộng 10 ngày.
2. **Hồ sơ:** chọn Lập phiếu thanh toán Word + Excel hoặc mở công cụ Đề nghị thanh toán. Đọc lại số tiền số/chữ, mã, hạn và thông tin thụ hưởng. Tệp mới tạo là bản để kiểm tra, chưa phải bản ký.
3. **Trình ký:** mở/tải hồ sơ, in từ Word hoặc Excel và trình người có thẩm quyền. Ghi người đang giữ hồ sơ, ngày hẹn và kết quả. Ứng dụng không tự ký hoặc đóng dấu.
4. **Scan:** nhận bản ký, scan đủ trang. Chọn đúng loại hồ sơ, nhập người kiểm tra và đánh dấu đã kiểm tra trước khi tải bản ký. Nếu đợt yêu cầu BBNT, bật mục cần nghiệm thu và lưu thêm bản xác nhận tương ứng.
5. **Email:** lưu To/CC thật; gợi ý nội dung, kiểm tra và lưu. Tạo nháp Outlook có tệp thật; chỉ lấy bản mới nhất của từng loại hồ sơ gửi khách. Mở nháp, kiểm tra tài khoản người gửi, chữ ký, nội dung và mọi tệp rồi tự bấm Gửi trong Outlook.
6. **Thư gửi:** nhấn Đọc Outlook, xem đúng thư Sent Items và gắn thư. Kết quả cùng mã hợp đồng có thể thuộc đợt khác hoặc là lịch sử trích dẫn, cần đọc trước khi chọn. Nếu dùng kênh khác, tải bằng chứng và ghi tham chiếu gửi. Thư nháp không tính là đã gửi.
7. **Khách:** đọc và gắn phản hồi hoặc tải bằng chứng khách xác nhận; ghi lịch hẹn và hồ sơ cần bổ sung. Có thể tạo tiếp nháp theo dõi từ cùng công việc. Ghi ngày hẹn trong ghi chú, dùng ngày theo dõi để nhắc xử lý; không thay hạn hợp đồng bằng lời hẹn chưa xác nhận.
8. **Tiền về:** kế toán đối chiếu tiền thực nhận. Tải chứng từ, xác nhận đã kiểm tra; ghi số tiền, ngày, mã ngân hàng và người xác nhận. Khoản thu một phần còn mở. Không ghi trùng tham chiếu; không ghi vượt nghĩa vụ của đợt thu. Chứng từ ngân hàng không tự đưa vào email gửi khách.

Nếu chưa có đủ xác nhận của khách nhưng tiền đã thực nhận, cần lưu bằng chứng tương ứng và xác nhận rõ kết quả từng bước. Không tạo thư gửi giả hoặc bỏ qua bước để đóng việc; có thể ghi căn cứ gửi qua kênh khác khi giao dịch thực sự dùng kênh đó.

## Các việc khác

Nút **Tạo công việc** có hướng dẫn cho Báo giá, Ký hợp đồng, Mua hàng, Giao hàng và thi công, Nghiệm thu, Bảo hành/sửa chữa. Có thể lấy từ hợp đồng, báo giá, PO hoặc hồ sơ nghiệm thu đang có; bản nguồn được liên kết theo ID, không chọn đại hồ sơ gần nhất.

Mỗi loại có bộ bước và yêu cầu bằng chứng riêng. Việc lập form vẫn mở công cụ chuyên biệt. Sau khi tạo, tải đúng tệp vào công việc để lưu cả lịch sử và phiên bản. Tệp ghi trong công việc cũng được lập chỉ mục vào Quản lý hồ sơ. Phiếu xin khách trả tiền khác đơn xin công ty duyệt chi cho nhà cung cấp.

## Outlook

- Dùng Outlook classic đã đăng nhập trên máy chạy portal, cần pywin32 trên Windows.
- Tạo nháp, mở nháp và đọc/gắn thư là các thao tác riêng. Ứng dụng không có thao tác tự gửi.
- Tìm trong tối đa 300 thư gần nhất mỗi thư mục Inbox và Sent Items. Mã công việc gắn trên nháp giúp nhận đúng thư; thư cũ được tìm theo mã tham chiếu chính xác trong tiêu đề hoặc nội dung.
- Chọn tệp trong kết quả Outlook để lưu vào công việc; trước đó chọn loại hồ sơ ở mục Hồ sơ và xác nhận đã kiểm tra nếu là bản ký.
- Không tự suy diễn đồng ý, nghiệm thu hoặc tiền về từ nội dung email. Người phụ trách xác nhận kết quả sau khi đọc.

## Kiểm tra và sửa sai

Nhật ký lưu tên người thao tác, thời gian và căn cứ. Hồ sơ tải lên tạo bản mới, không ghi đè tệp cũ. Có thể quay lại bước trước kèm lý do khi chưa có khoản thu; hồ sơ và nhật ký vẫn giữ. Khoản tiền đã đối chiếu không được xóa bằng nút hủy trạng thái cũ; kế toán cần xử lý điều chỉnh riêng theo chứng từ.

Các trạng thái đã thu từ hồ sơ cũ được kế thừa, không tạo chứng từ thu giả. Mốc thanh toán không liên kết được hợp đồng sẽ không tự tạo công việc. Những dự án chỉ mới xuất hiện trong email phải được nhập và đối chiếu hồ sơ trước.

## Kiểm thử

Chạy từ thư mục dự án:

    python -m pytest pm_portal/tests/test_workflows.py pm_portal/tests/test_file_integrity.py pm_portal/tests/test_payment_schedule.py -q

Các kiểm thử dùng cơ sở dữ liệu/tệp tạm và Outlook giả lập để kiểm tra chốt nghiệp vụ; không gửi email và không ghi khoản thu kiểm thử vào dữ liệu thật.

## Kết quả xác minh ngày 29/10/2026

Các lần kiểm tra trước: tạo Word/Excel bằng mẫu thật vào thư mục tạm; đọc Outlook thật tìm được thư liên quan SEIYO; kiểm tra giao diện bản trước trên máy tính và điện thoại. CUA hiện không khả dụng; không dùng ảnh bản trước để xác nhận giao diện mới.

## Đồng bộ nghiệp vụ ngoài thu tiền (29/10/2026)

Trong mỗi việc có mục **Liên kết các bước trong dự án**. Chọn đúng hợp đồng, tải chứng từ đúng loại, nhập người kiểm tra/ngày thực tế và xác nhận nghiệp vụ. Không ghép dự án chỉ vì trùng tên khách.

| Căn cứ được xác nhận | Kết quả |
| --- | --- |
| Khách chấp thuận báo giá | Mở việc đối chiếu hợp đồng; chưa ký, chưa tự đặt PO. Báo giá có thể được chấp thuận trước khi có hồ sơ hợp đồng. |
| Hợp đồng ký hai bên | Mở việc kiểm tra BOM, cọc và điều kiện mua; cần lập/liên kết dòng PO thật trước khi nhận hàng. |
| Nhận hàng NCC | Cộng từng lần thực nhận, chặn vượt số lượng PO, cập nhật PARTIAL/DELIVERED, mở việc chuẩn bị giao khách. Không kích hoạt tiền thu khách. |
| Giao khách có ký nhận | Mở việc nghiệm thu; chưa tính đã nghiệm thu hoặc đã thu tiền. |
| Ký / giao / nghiệm thu đạt đúng điều kiện thanh toán | Người dùng chọn chính xác đợt thu và T/T, tính hạn, đưa chứng từ vào việc thu tiền; không đánh dấu đã gửi thư hoặc tiền về. |
| Đăng ký model/SN | Lưu ngày giao và số tháng bảo hành theo điều khoản, tính ngày cuối tháng đúng lịch; không mặc định 12 tháng. |
| Xác nhận sửa có phí | Mở báo giá sửa chữa; cần chấp thuận trước khi xác nhận giao trả. Không tự lập hóa đơn hoặc khoản thu. |
| Giao trả bảo hành | Lưu căn cứ hoàn tất xử lý; giữ nguyên thời hạn bảo hành ban đầu. |

Hồ sơ hợp đồng, PO, báo giá hiện hành và tài liệu nghiệm thu đã được lập chỉ mục tự xuất hiện trong danh sách. PO cũ ghi đã giao chuyển đến bước bổ sung/kiểm tra chứng từ nhận hàng, không yêu cầu đặt lại. Những bước cũ chưa có nhật ký xác nhận không được tô xanh như đã hoàn thành.

Các trang Báo giá, Hợp đồng, PO, Nghiệm thu, Hồ sơ hợp đồng và Công nợ có mục mở công việc liên quan dùng chung. Trong công việc có danh sách các việc cùng hợp đồng và thiết bị/SN. Tệp có thể lấy từ kho hồ sơ đúng mã hoặc từ Outlook; luôn giữ bản sao nguyên định dạng. Không đổi tên/xóa chứng từ đã được gắn để tránh làm đứt bằng chứng.

Email gợi ý đã tách theo sáu nghiệp vụ dựa trên thư thực tế CX, SEIYO, CHENG FENG và DARFON. Phải rà lại điều khoản, người nhận và tệp; ví dụ bảo hành pin CX là 6 tháng, email chấp thuận nội dung chưa chứng minh đã ký, đề nghị dời hạn chưa phải hai bên đã đồng ý. Chưa tự nhập mọi thư vào hồ sơ vì cần nhận diện chính xác từng giao dịch. Không gửi email tự động.

Kiểm thử bổ sung: `pm_portal/tests/test_project_sync.py`, dùng DB/tệp tạm. Kiểm tra số lượng từng phần, chống ghi trùng/ghi đè điều kiện, đúng đợt thu, nhận NCC khác giao khách, bảo hành 6 tháng, chấp thuận sửa có phí, không tự tạo hợp đồng/tiền về.

Kết quả bản này: **62 kiểm thử đạt**. Kiểm tra cú pháp JavaScript đạt; 7 địa chỉ trang/tài nguyên trả HTTP 200; SQLite integrity_check=ok. Danh sách thật có 27 việc từ 2 hợp đồng, 6 đợt thu, 17 dòng mua hàng và 2 tài liệu nghiệm thu. SEIYO đợt 1 giữ đã thu 213.606.000, còn 0; tổng hợp đồng giữ 640.818.000 (90%). Không có project_facts, project_assets hoặc workflow_receipts kiểm thử trong DB thật. Chưa xác minh trực quan giao diện mới do CUA không khả dụng.

## Bố cục quản lý và phân loại hồ sơ (cập nhật tiếp 29/10/2026)

Đã sửa bộ đếm 24 việc mở gây hiểu nhầm. `queue_state` phân biệt việc có bước thực hiện đã xác định, đợt thu chờ điều kiện, hồ sơ kế thừa cần đối chiếu và quy trình đã hoàn tất. Trạng thái nguồn PO và ngày giao được trình bày riêng; không đổi dữ liệu giao hàng hoặc đóng giả quy trình để giảm số lượng.

Trang mở đầu bằng toàn bộ hồ sơ, có thẻ chuyển nhóm; lọc kết hợp loại việc, dự án/khách, người phụ trách; tìm không dấu; nhóm theo dự án hoặc loại, sắp xếp ưu tiên/ngày/tên. Tổng của từng nhóm là số toàn hệ thống; dòng kết quả hiển thị số sau lọc / toàn bộ. Tên thiết bị dài được thu gọn, danh sách cuộn riêng; phần chi tiết chia thành các mục mở/đóng (hồ sơ, phụ trách, các bước, Outlook, liên kết nghiệp vụ).

**71 kiểm thử đạt** (gồm 9 kiểm thử phân nhóm mới). CUA đã kết nối lại trong phiên này: xác minh các thẻ nhóm trên trang, tìm SEIYO trả 4 hồ sơ đối chiếu; lọc thêm mua hàng trả 3 dòng; mở TV SEIYO hiển thị nguồn DELIVERED/ngày giao, không yêu cầu giao lại. Thử màn hình 1440×1000 và 390×844; chiều rộng nội dung không vượt khung điện thoại. Kiểm thử giao diện chỉ đọc, không cập nhật chứng từ/tiền/trạng thái nghiệp vụ thật.
