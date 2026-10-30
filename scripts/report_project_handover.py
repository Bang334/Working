"""Produce a sourced PM handover review without changing source files or live data."""
import sys,json,hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path('D:/Working');AUDIT=ROOT/'.qa/project_handover_20261030';OUT=ROOT/'Bao Cao/Tiep Nhan Du An 20261030'
OUT.mkdir(parents=True,exist_ok=True)
inv=json.loads((AUDIT/'inventory.json').read_text(encoding='utf-8'))['files']
summary=json.loads((AUDIT/'summary.json').read_text(encoding='utf-8'))
db=json.loads((AUDIT/'database_snapshot.json').read_text(encoding='utf-8'))

def source(index,location=''):
    f=inv[index-1]
    return f"[{f['customer']} · {Path(f['path']).name}](<{f['path'].replace(chr(92),'/')}>)"+(f' — {location}' if location else '')

def write(name,text):
    p=OUT/name
    try:p.write_text(text,encoding='utf-8')
    except PermissionError:p=p.with_stem(p.stem+'_v2');p.write_text(text,encoding='utf-8')
    return p

customer_notes={
'AMPACS':('Chưa có hồ sơ / 尚無文件','Thư mục trống. Xin Sếp xác nhận dự án, đầu mối, giai đoạn và hồ sơ cần bàn giao.'),
'TTC':('Chưa có hồ sơ / 尚無文件','Thư mục trống. Chưa thể kết luận không có dự án.'),
'ASIAITALI':('Báo giá / 報價','AI kiểm tra bao bì; báo giá và báo giá nhà cung cấp. Chưa thấy hợp đồng trong bộ này; xác nhận đơn vị tiền vì PDF hiện ký hiệu $. Không ghi nhận công nợ chỉ từ báo giá.'),
'CHENG FENG':('Đang theo dõi; cần cập nhật / 追蹤中待更新','Hệ thống 1 tỷ, đã thu 300 triệu ngày30/10; lịch bàn giao còn ghi chưa ký nhưng đã tick ký/cọc. Mã bản Word khác mã hiện hành. HOP DONG A&B là hồ sơ với nhà thầu, không phải hợp đồng khách hàng 1 tỷ.'),
'CX':('Nhiều hợp đồng; tách phạm vi / 多份合約','Giữ riêng RFID phần mềm234 triệu, thẻ157 triệu,500 thẻ19,5 triệu,sửa chữa65 triệu,13,7 triệu và pin. Hồ sơ157 triệu có cả báo giá và hợp đồng; tên file có chữ合同 không đủ xác định loại tài liệu.'),
'DARFON':('Dự án đang theo dõi + lịch sử / 追蹤及歷史','Phase2 khớp203,22 triệu; báo giá ghi đợt cuối OA90Days sau nghiệm thu, hệ thống chưa có số ngày T/T cho đợt đó. Phase1 có nhiều phiên bản và báo giá nhà cung cấp, cần đánh dấu lưu trữ.'),
'FINEPRO':('Đơn hàng và báo giá / 訂單及報價','Có PO2025 và nhiều báo giá2025–2026. Chưa có hợp đồng/AR FINEPRO trong16 hợp đồng và47 khoản đang đối chiếu; xác nhận còn việc triển khai hay chỉ bảo hành/lưu trữ.'),
'FORESHOT':('Tư vấn MES và báo giá / MES輔導報價','Có nhiều phiên bản báo giá tư vấn MES. Chưa thấy hợp đồng trong bộ này; xác nhận phạm vi dịch vụ, thời lượng tư vấn, nghiệm thu và tình trạng chốt.'),
'JINGGUANG':('Dùng thử; cần xác minh khoản thu / 試用待核實','Thỏa thuận dùng thử, phụ lục sai mã tham chiếu, nhiều giá báo. AR681,9 triệu chưa có mã hợp đồng; không đủ hồ sơ để kết luận khoản này chính thức đến hạn.'),
'JINXUN':('Đang theo dõi; khớp giá ưu đãi / 優惠價相符','MES Lite781,53 triệu khớp giá ưu đãi G53, không lấy giá niêm yết807,583184 triệu. Có báo giáSMB/phần cứng khác phải tách; một điều khoản tiếngTrung45+55+10=110% cần đối chiếu.'),
'JIYANG':('Ưu tiên sửa cơ sở tiền / 優先核對稅額','Có hai hợp đồng ký và hai lịch: phần mềm495 triệu, phần cứng178,2 triệu đã gồmVAT. Phần cứng bị cộngVAT lần nữa trong hệ thống. Ngày thu14/05 cho hợp đồng tháng8 cần chứng từ xác nhận.'),
'MEN CHUEN':('Giải pháp và báo giá EMS / EMS提案報價','Báo giáHongMing và nhà cung cấpBasic/Pro. Chưa thấy hợp đồng trong bộ này. Quản lý phương án,phạm vi phần mềm và thiết bị loại trừ; xác nhận chưa/đã chốt.'),
'Midea':('Giải pháp; đăng ký NCC / 提案及供應商登錄','Có báo cáo giải phápA2 và hồ sơ đăng ký nhà cung cấp. Chưa thấy hợp đồng mua bán; quản lý như cơ hội/kỹ thuật tiền bán hàng đến khi có xác nhận.'),
'SEIYO':('Tách Phase1/2/3 / 分階段管理','Hai scanPhase2 có chữ ký và tiền khớp. Phase3 hợp đồngWord dùng mã mới, lịch vẫn mã cũ và nhiều ngày dự kiến. Ba file.doc cũ, trong đó tên file có1,736158 tỷ, cần chuyển đổi và xác minh phiên bản.'),
'Strong Way':('Hai gói dự kiến / 兩項規劃案','MES1,75 tỷ vàQMS500 triệu là hai gói; lịch dự kiến ký15/11/2026,FAC29/01/2027. Chưa thấy bản ký trong bộ này; không cộng2,25 tỷ vào AR. Tênfile lịch chỉ nóiMES nhưng workbook còn cósheetQMS.'),
'TECH LINK':('Dùng thử và báo giá / 試用及報價','Thỏa thuận dùng thửECO0005; báo giá440,7 triệu là ứng viên phương án. Cần ngày lắp đặt,baseline,kết quả và quyết định mua trước khi xác định khoản phải thu.'),
'VCAST':('RFID lịch sử + EMS / RFID歷史及EMS','PO/báo giáRFID2023–2025, ảnh giao hàng, báo giáEMS2026. Tách loại dự án và kiểm tra còn nghĩa vụ bảo hành/công nợ; không gộp đơn hàngNCC thành doanh thu.'),
'VONMAX':('Tách SMB,phần mềm,năng lượng / 分案管理','BaHĐSMB hiện có và thêm bảnWord năng lượng400,9 triệu chưa thấy trong16HĐ. MãSMBPhase2 trongWord có thêm0 so với mã bản ký đã lưu; giữ mã bản ký ưu tiên, lưualias.'),
}

customer_table=[]
for entry in summary['customers']:
    key=next((key for key in customer_notes if entry['customer'].startswith(key)),None)
    stage,note=customer_notes[key]
    customer_table.append(f"| {entry['customer']} | {entry['files']} | {stage} | {note} |")

gross=sum(r['gross_amount'] or 0 for r in db['project_receivables'])
received=sum(r['received_amount'] or 0 for r in db['project_receivables'])
fmt=lambda x:f'{x:,.0f}'.replace(',','.')
report=(ROOT/'scripts/templates/handover_review_20261030.md').read_text(encoding='utf-8')
for entry in inv:
    report=report.replace(f"[[S{entry['id']:03d}]]",source(entry['id']))
# Accept three-digit and unpadded references in the template.
for entry in inv:
    report=report.replace(f"[[S{entry['id']}]]",source(entry['id']))
path=write('BAO_CAO_DOI_CHIEU_DU_AN_20261030.md',report)
inventory=['# Danh mục hồ sơ bàn giao / 交接文件清單','','Nguồn: Thư mục drive-download-20261030T014758Z-1-001 do người dùng chỉ định. Giữ nguyên mọi tệp gốc.','', '| ID | Khách hàng | Tài liệu gốc | Kiểm tra |','|---:|---|---|---|']
for f in inv:
    status=f"Trùng hoàn toàn ID {f['duplicate_of']}" if 'duplicate_of' in f else 'Đã trích chữ/ô dữ liệu'
    if f.get('scan_pages'):status+='; có trang scan/ít chữ: '+','.join(map(str,f['scan_pages']))
    if f.get('unread_reason'):status=f['unread_reason']
    if f['id'] in [8,167,168,221,222]:status+='; đã kiểm tra trực quan bản scan'
    inventory.append(f"| {f['id']:03d} | {f['customer']} | [{f['relative']}](<{f['path'].replace(chr(92),'/')}>) | {status} |")
write('DANH_MUC_HO_SO_20261030.md','\n'.join(inventory)+'\n')
print(path)
