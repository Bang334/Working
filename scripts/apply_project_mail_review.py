"""Apply evidence-scoped mailbox review; never infer receipts from invoices."""
import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / '.qa/project_mail_audit_20261029'
MARK = '[ĐỐI CHIẾU MAIL 29/10/2026]'


def stamp(old, message):
    return (old or '').split(MARK)[0].rstrip() + '\n\n' + MARK + '\n' + message


def review(row):
    code = row['contract_code'] or ''
    ident = row['id']
    evidence = []
    if code in ('HMSY200720260001', 'HMSY200720260002'):
        evidence = [38]
        text = ('Khách xác nhận đã ký hợp đồng ngày 22/07; bản scan khớp mã, tổng tiền và 30%–60%–10%. '
                'Trạng thái đã thu đủ giữ theo Excel; thư ký hợp đồng không xác nhận ngày thực nhận tiền. '
                'Thư 25/08 được trích trong mail 26/10 nói tiền cọc chưa về tại thời điểm 25/08, không phải trạng thái hiện tại.')
    elif code in ('HMV22092026SY0001', 'HMV04102026SY0001'):
        evidence = [3, 18, 23]
        text = ('SEIYO giai đoạn 3: tổng 712.020.000đ, đặt cọc 30%=213.606.000đ theo yêu cầu 15–16/10. '
                '25/10 là ngày Hong Ming đề nghị, chưa có xác nhận lịch trả từ khách. '
                'Khách gửi link scan hợp đồng 26/10 và đề nghị triển khai: dây mạng ngoài PC AI, khôi phục MES máy cũ, kết nối máy mới. '
                'Đã kiểm tra bản scan 11 trang từ link: mã chính thức HMV04102026SY0001, hai bên ký đóng dấu ngày 13/10/2026; '
                'mã HMV22092026SY0001 trong Excel, bản nháp và thư YCTT là mã cũ. '
                'Bản ký khớp tổng 712.020.000đ và 30%–60%–10%: cọc ngay sau ký, đợt 60% T/T15 ngày sau biên bản lắp đặt/chạy thử, '
                'đợt 10% T/T30 ngày sau FAC; chưa có bằng chứng các mốc sau đã kích hoạt. '
                'Ngày 30/10 trong cột hẹn của Excel chưa được chứng minh bởi các thư tìm thấy. Chưa có bằng chứng tiền về; giữ chưa thu. '
                'Không áp dụng thông tin tiền cọc tháng 8 của các hợp đồng cũ cho giai đoạn này.')
    elif code == 'HMV151020250001':
        evidence = [1, 5, 16, 33]
        text = ('Hợp đồng scan và email khớp tổng 234.000.000đ, lịch 40%–40%–20%. '
                'Đợt cuối 46.800.000đ đã gửi phiếu YCTT và biên bản nghiệm thu ngày 24/10, nhắc lại 27/10; '
                '05/11 là ngày đề nghị, chưa phải khách cam kết. Bản nghiệm thu đính kèm chỉ có chữ ký bên Hong Ming, ô ký bên CX còn trống; '
                'footer bị sót mã HMV100120260001 của mẫu, phần nội dung chính ghi HMV151020250001. '
                'Giữ nguyên hồ sơ nghiệm thu gốc, ghi cảnh báo để kiểm tra khi hoàn thiện. '
                'Số thu 80% theo Excel/quy tắc đợt trước đã đối soát; chưa thấy chứng từ ngân hàng trong thư đã đọc. Đợt cuối vẫn chưa thu.')
    elif code == 'HMV021020260001':
        evidence = [6, 8, 10, 19, 24]
        text = ('Email và phiếu YCTT xác nhận tổng HĐ 1.000.000.000đ, đặt cọc 30%=300.000.000đ, ngày đề nghị ban đầu 25/10. '
                'Khách Ngọc Thắng trả lời 20/10: dự kiến sắp xếp đợt đầu ngày 05/11, có thể sớm hơn nếu tiền về. '
                'Hong Ming đề xuất gộp đợt 1+2 thành 60%=600.000.000đ ngày 05/11; thư nhắc 22/10 vẫn chờ xác nhận. '
                'Chỉ đợt đầu có lịch dự kiến từ khách, không gán ngày hẹn cho đợt 2 và không ghi đã thanh toán. '
                'Các mốc 30%–30%–30%–10% đang theo Excel, chưa tìm thấy bản hợp đồng ký trong hộp thư để kiểm tra điều kiện từng mốc.')
    elif code == 'HMV100120260001':
        evidence = [14, 15]
        text = ('Đã phát hành và gửi hóa đơn số 23 ngày 16/10/2026, tổng 781.530.000đ cho MES Lite. '
                'Ghi chú cũ “chưa mở hóa đơn” hết hiệu lực về tình trạng hóa đơn. '
                'Hóa đơn toàn bộ HĐ không xác nhận đã nhận khoản cuối 10%=78.153.000đ. '
                'Giữ đã thu 90% theo Excel, ảnh người dùng và quy tắc suy ra đợt trước; chưa có chứng từ ngân hàng xác nhận lại các ngày thu. '
                'Thông tin hẹn cuối tháng 10 vẫn là thông tin Excel, chưa được kiểm chứng bằng mail đã tìm thấy.')
    elif code in ('HMV060620250001', 'HMV060620250002'):
        evidence = [13]
        text = ('Email kế toán 16/10 và thư 19/09 được trích dẫn phân biệt phần mềm HMV060620250001 tổng 1,1 tỷ '
                'với phần cứng HMV060620250002 tổng 545.454.545đ; chỉ còn 10% chưa trả. '
                'Lịch sử 90% là tổng các đợt trước suy ra từ thư nhắc nợ theo quy tắc người dùng, không có ngày nhận thực tế. '
                'Hồ sơ nghiệm thu đã gửi xin khách ký trả; thư gửi hồ sơ không chứng minh khách đã ký hoặc trả nốt. '
                'Khoản cứng 10% chênh làm tròn 1đ giữa thư tổng và phiếu chi tiết đã được lưu ở đối soát trước.')
    elif code == 'HMV07032026001':
        evidence = [13, 50, 51]
        text = ('Bản hợp đồng ký khớp tổng 1.290.574.200đ, 35%–55%–10%, mã HMV07032026001. '
                'Thư nhắc 16/10 gõ HMV070320260012 và gọi công trình tiết kiệm điện, trong khi bản ký là phần cứng SMB giai đoạn 2; ưu tiên mã và tên bản ký. '
                'Mail 16/10 còn nhắc nợ 10%, nhưng Excel ghi đã thu 10% ngày 21/10 (sau email), nên không khôi phục nợ theo thư cũ. '
                'Giữ đã thu đủ theo nguồn mới hơn; chưa thấy chứng từ ngân hàng kèm mail để kiểm chứng ngày 21/10.')
    elif code == 'DFV20260505':
        evidence = [9, 11, 48]
        text = ('Thư Darfon 07/07 nhắc đã nhận tiền trả trước và yêu cầu lịch lắp đặt; không nêu số tiền/ngày nhận cụ thể. '
                'Các thư 20/10 trao đổi kỹ thuật và bảo hành, không xác nhận thanh toán. '
                'Giữ tổng 203.220.000đ và 30%–60%–10%, số đã thu 90% theo Excel; chưa có chứng từ độc lập xác nhận đợt 60% hoặc 10% trong thư đã đọc.')
    elif code == 'HMV050520260001':
        evidence = [31, 32, 34, 35, 39, 40, 41]
        text = ('Hóa đơn số 9 và bộ thông quan 300 thẻ RFID khớp 11.100.000đ, tham chiếu HMV050520260001. '
                'Chứng từ thông quan ghi ngày HĐ 20/07/2026; không suy ngày ký chỉ từ chuỗi số trong mã. '
                'Giữ đã thu theo Excel; gửi hóa đơn/giao hàng không chứng minh tiền về, chưa thấy xác nhận ngân hàng.')
    elif code == 'SC-2026-005':
        evidence = [21, 22, 30]
        text = ('Excel dùng mã SC-2026-005, tổng 65.000.000đ và hai đợt 50%, đã thu theo nguồn. '
                'Chuỗi thư có tham chiếu HDSC/HMV04082026001 nhưng chủ đề đó được dùng lại cho sửa chữa 13.700.000đ. '
                'Chưa đủ căn cứ đổi mã hoặc gộp hai dự án; giữ riêng, cần đối chiếu đúng bản hợp đồng/biên nhận 65 triệu. '
                'Chưa có mail/chứng từ ngân hàng kiểm chứng hai ngày thu.')
    elif code in ('HM27082026JI002', 'HM25082026JI001'):
        text = ('Chưa tìm thấy thư hoặc hợp đồng đính kèm khớp mã JIYANG trong các thư Outlook hiện có. '
                'Giữ lịch 30%–55%–15% và tiền cọc theo Excel, chưa xác minh độc lập trạng thái/ngày thu. '
                'Ngày thu 14/05/2026 trong nguồn cần kiểm tra với chứng từ và ngày ký hợp đồng; không tự sửa theo tháng của mã.')
    elif code == 'HMV27082026-001':
        text = ('Chưa tìm thấy thư/hợp đồng khớp mã và tổng 157.000.000đ để đối chiếu độc lập. '
                'Giữ 50% đã thu và 50% còn lại theo Excel; không gộp với các lô thẻ CX 11,1 triệu hoặc 19,5 triệu.')
    elif code == 'HMV220920260001':
        text = ('Chưa tìm thấy thư xác nhận thu tiền khớp riêng PO F601-0700, 500 thẻ, tổng 19.500.000đ. '
                'Giữ 50% đã thu và 50% còn lại theo Excel; chưa xác minh độc lập bằng mail/chứng từ ngân hàng.')
    elif ident == 42:
        evidence = [12, 16, 17, 20, 21, 22, 30]
        text = ('Email 12/10 gửi hồ sơ hoàn tất sửa chữa, 15–16/10 gửi hóa đơn 24 cho 13.700.000đ; khách duyệt hình thức hóa đơn và yêu cầu gửi bản giấy. '
                'Đây là xác nhận hồ sơ, chưa phải xác nhận tiền về. Giữ đã thu ngày 23/10 theo Excel. '
                'Chủ đề mail chứa mã hợp đồng sửa chữa khác, không tự gán mã HDSC/HMV04082026001 cho khoản này.')
    elif ident == 45:
        evidence = [2]
        text = ('Khoản 3 pin BAT-RFR900 tổng 5.508.000đ giữ đã thu theo Excel. '
                'Email báo giá mới 27/10 có giá trị khác, chưa có căn cứ thay khoản đã thu cũ bằng báo giá mới; chưa thấy xác nhận ngân hàng cho khoản cũ.')
    elif ident in (38, 40):
        text = ('Khoản pin độc lập: giữ số đã thu theo Excel; chưa tìm thấy thư/chứng từ ngân hàng khớp chính xác số lượng và giá trị. Không gộp với báo giá pin mới.')
    elif ident in (34, 57):
        text = ('Chưa tìm thấy hợp đồng/mail khớp chính xác khoản tiết kiệm năng lượng này. '
                'Giữ chưa thu theo Excel; thiếu mã HĐ và chưa xác minh tổng giá trị, mốc thanh toán. '
                'Không coi dòng 100% hoặc một dòng tổng hợp nguồn là lịch hợp đồng đã kiểm chứng, không gộp với hợp đồng SMB khác.')
    else:
        raise ValueError(f'Unreviewed receivable {ident}')
    suffix = ('\nNguồn thư: ' + ', '.join(f'mail_{i:03d}.md' for i in evidence)) if evidence else '\nNguồn: Excel; chưa có thư đối chiếu khớp.'
    return text + suffix, evidence


def apply(db):
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    backup = ROOT / 'database/backups' / ('mail_review_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True)
    with sqlite3.connect(backup / 'before.db') as target:
        c.backup(target)
    rows = [dict(r) for r in c.execute('SELECT * FROM project_receivables ORDER BY id')]
    immutable = [(r['id'], r['gross_amount'], r['received_amount'], r['remaining_debt'], r['paid_date'], r['paid_by_date']) for r in rows]
    docs = sorted({p for p in (ROOT/'Ho So Du An').rglob('*') if p.is_file()} |
                  {Path(r[0]) for r in c.execute('SELECT file_path FROM documents') if r[0] and Path(r[0]).is_file()})
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in docs}
    summaries = []
    with c:
        for row in rows:
            message, evidence = review(row)
            changes = {'notes': stamp(row['notes'], message)}
            if row['id'] == 36:
                changes['doc_status'] = 'Đã gửi YCTT + BBNT 24/10; chờ CX ký/xác nhận / 已寄請款及驗收資料，待客戶確認'
                changes['due_date'] = '2026-11-05'
            if row['id'] == 64:
                changes['doc_status'] = 'Đã phát hành hóa đơn 23 ngày 16/10; 10% chưa thu / 已開立23號發票，尾款未收'
            if row['id'] == 65:
                changes['customer_promised_date'] = '2026-11-05'
                changes['doc_status'] = 'Đã gửi YCTT 30%; khách dự kiến trả 05/11 / 已寄訂金請款，客戶預計11/05付款'
            if row['id'] == 66:
                changes['doc_status'] = 'Đề xuất gộp cùng đợt 1 ngày 05/11; khách chưa xác nhận / 合併付款方案待確認'
            if row['id'] == 31:
                changes['doc_status'] = 'HĐ đã ký hai bên 13/10; YCTT còn mã cũ; chưa có xác nhận thu / 合約已簽，請款編號待更正'
            if row['contract_code'] in ('HMV22092026SY0001', 'HMV04102026SY0001'):
                changes['contract_code'] = 'HMV04102026SY0001'
                changes['payment_term_days'] = {31:0,32:15,33:30}[row['id']]
            assignments = ', '.join(f'{k}=?' for k in changes)
            c.execute(f'UPDATE project_receivables SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?', [*changes.values(), row['id']])
            summaries.append({'id': row['id'], 'code': changes.get('contract_code',row['contract_code']), 'project': row['project_name'], 'gross': row['gross_amount'], 'received': row['received_amount'], 'debt': row['remaining_debt'], 'review': message, 'mail_ids': evidence})
        old, new = 'HMV22092026SY0001', 'HMV04102026SY0001'
        for table in ('contracts','payment_milestones','documents','workflow_cases'):
            c.execute(f'UPDATE {table} SET contract_code=? WHERE contract_code=?', (new,old))
        c.execute('UPDATE contracts SET signed_date=? WHERE contract_code=?', ('2026-10-13',new))
        for mid, term in [(90,0),(91,15),(92,30)]:
            c.execute('UPDATE payment_milestones SET payment_term_days=? WHERE id=? AND contract_code=?',(term,mid,new))
        c.execute('UPDATE workflow_cases SET title=? WHERE contract_code=? AND title=?',(new,new,old))
        source = AUDIT/'mail_003/20261026HOP DONG MUA BAN.pdf'
        if not source.is_file(): raise FileNotFoundError('Signed SEIYO PDF must be available before applying code correction')
        target = ROOT/'Ho So Du An/Hop Dong/SEIYO_HMV04102026SY0001_Da_Ky_20261013.pdf'
        if not target.exists(): shutil.copy2(source,target)
        assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
        contract_id = c.execute('SELECT id FROM contracts WHERE contract_code=?',(new,)).fetchone()[0]
        if not c.execute('SELECT 1 FROM documents WHERE file_path=?',(str(target),)).fetchone():
            c.execute('''INSERT INTO documents(contract_id,contract_code,doc_type,doc_name,file_name,file_path,file_size,file_format,description)
                         VALUES(?,?,?,?,?,?,?,?,?)''',(contract_id,new,'HOP_DONG','Hợp đồng SEIYO đã ký hai bên 13/10/2026',target.name,str(target),target.stat().st_size,'pdf','Bản scan khách gửi qua link trong email 26/10; 11 trang; mã chính thức HMV04102026SY0001, mã nháp cũ HMV22092026SY0001.'))
        titles = {
            'HMSY200720260001': 'Nâng cấp trực quan hóa SMB dây chuyền E, F',
            'HMSY200720260002': 'Xây dựng mạng SMB khu vực IT, nhà máy, E–F',
            'HMV04102026SY0001': 'Quy hoạch mạng IIoT SEIYO giai đoạn 3',
            'HMV151020250001': 'Phần mềm tùy chỉnh chức năng hệ thống RFID',
            'HMV060620250001': 'Hệ thống phần mềm IoT Visual SMB tại nhà máy Vonmax',
            'HMV060620250002': 'Phần cứng kết nối máy SMB tại nhà máy Vonmax',
            'HMV07032026001': 'Phần cứng kết nối máy SMB giai đoạn 2 tại Vonmax',
            'HMV100120260001': 'Hệ thống MES Lite tại Jinxun',
        }
        for contract in c.execute('SELECT id,contract_code,notes FROM contracts').fetchall():
            related = next((s for s in summaries if s['code'] == contract['contract_code']), None)
            if not related: continue
            c.execute('UPDATE contracts SET notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?', (stamp(contract['notes'], related['review']), contract['id']))
            if contract['contract_code'] in titles:
                c.execute('UPDATE contracts SET project_name_vi=? WHERE id=?', (titles[contract['contract_code']], contract['id']))
        after = [tuple(r) for r in c.execute('SELECT id,gross_amount,received_amount,remaining_debt,paid_date,paid_by_date FROM project_receivables ORDER BY id')]
        assert after == immutable, 'Money or actual payment dates changed unexpectedly'
        assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        assert all(Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in hashes.items())
    c.close()
    (backup / 'review.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Đối chiếu dự án với email và hồ sơ – 29/10/2026', '',
             'Phạm vi: 272 thư Outlook hiện có (46 thư đã gửi, 226 thư nhận); lọc và đọc 54 thư liên quan cùng chuỗi trích dẫn, kiểm tra tệp đính kèm phù hợp. Đây không phải xác nhận đã kiểm tra toàn bộ thư trên máy chủ hay toàn bộ tài khoản kế toán.', '',
             'Đã ghi kết quả đối chiếu vào ghi chú từng khoản và từng hợp đồng trên hệ thống. Giữ nguyên các khoản đã thu theo Excel nếu không có bằng chứng mới mâu thuẫn; ghi rõ khoản nào còn thiếu xác nhận ngân hàng. Không ghi nhận thu tiền chỉ vì đã gửi hóa đơn, YCTT, nghiệm thu hoặc khách dự kiến trả.', '',
             '## Những thông tin đã cập nhật', '',
             '- CX RFID 234 triệu: hồ sơ đợt cuối 46,8 triệu đã gửi 24/10 và nhắc 27/10; 05/11 là ngày đề nghị. Biên bản gửi đi chưa có chữ ký CX; footer sót mã mẫu Jinxun, giữ nguyên tệp và đánh dấu cần rà trước khi hoàn thiện.',
             '- Jinxun MES Lite: hóa đơn 23 đã phát hành 16/10, xóa trạng thái hiển thị cũ “chưa mở hóa đơn”; khoản cuối 78,153 triệu vẫn chưa thu.',
             '- Cheng Feng: ghi lịch khách dự kiến trả đợt đầu 300 triệu ngày 05/11; đề xuất gộp 600 triệu chưa được khách xác nhận.',
             '- SEIYO: kiểm tra hai bản scan tháng 7, khớp mã/tổng và 30–60–10. Giai đoạn 3 đã kiểm tra bản scan từ link 26/10: mã đúng HMV04102026SY0001, ký hai bên 13/10. Đổi mã cũ HMV22092026SY0001 trong liên kết dữ liệu hiện hành, giữ bản nháp và hồ sơ gốc; đã thêm bản PDF ký vào hồ sơ hợp đồng. Chưa thấy bằng chứng thu cọc.',
             '- Sửa tên hợp đồng tổng thể đang bị lấy tên một đợt thanh toán; riêng Vonmax phần mềm 1,1 tỷ trước đó còn mang nhầm tên phần cứng.', '',
             '## Kết quả từng dự án/khoản', '']
    groups = {}
    for item in summaries:
        key = item['code'] or f"Khoản độc lập #{item['id']}"
        groups.setdefault(key, []).append(item)
    fmt = lambda x: f'{x:,.0f}'.replace(',', '.')
    for key, items in groups.items():
        lines += [f'### {key.replace(chr(10), " / ")}', '',
                  f"Phải thu theo lịch: {fmt(sum(x['gross'] for x in items))}đ; đã thu theo dữ liệu hiện có: {fmt(sum(x['received'] for x in items))}đ; còn lại: {fmt(sum(x['debt'] for x in items))}đ.", '', items[0]['review'], '']
        for mail_id in items[0]['mail_ids']:
            path = AUDIT / f'mail_{mail_id:03d}.md'
            lines.append(f'- [Thư {mail_id:03d}]({path.as_posix()})')
        lines.append('')
    lines += ['## Hồ sơ chưa được gộp vào công nợ', '',
              'Hóa đơn CX 96.410.000đ, tham chiếu HDSC/HMV06032026001, xuất hiện trong thư 30/06 nhưng không khớp khoản hiện có trong Excel. Chưa thêm công nợ để tránh ghi trùng hoặc ghi lại khoản đã tất toán; cần hợp đồng và sổ thu trước khi kết luận.', '',
              'Báo giá pin mới ngày 27/10 không thay thế khoản pin đã thanh toán trong Excel. Thư nhà cung cấp hoặc báo giá kỹ thuật không được dùng làm bằng chứng khách thanh toán.', '',
              '## Kiểm tra bảo toàn', '',
              f'Đã sao lưu tại {backup.as_posix()}. Đối chiếu trước/sau: nguyên 48 khoản, số tiền, ngày thực nhận và ngày chậm nhất đã thu không đổi; {len(hashes)} tệp hồ sơ có hash nguyên vẹn. SQLite integrity_check=ok, không lỗi khóa ngoại.', '',
              'Các mục JIYANG, Jing Guang, Vonmax tiết kiệm điện 400,9 triệu và một số lô RFID/pin chưa có thư/chứng từ khớp trong hộp thư hiện có. Trạng thái của chúng vẫn căn cứ Excel và được đánh dấu chưa xác minh độc lập.']
    report = ROOT / 'database/BAO_CAO_DOI_CHIEU_MAIL_DU_AN_20261029.md'
    report.write_text('\n'.join(lines), encoding='utf-8')
    return {'reviewed_receivables': len(rows), 'groups': len(groups), 'files_preserved': len(hashes), 'backup': str(backup), 'report': str(report)}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(); parser.add_argument('--db', type=Path, default=ROOT/'database/pm_portal.db')
    print(json.dumps(apply(parser.parse_args().db), ensure_ascii=False, indent=2))
