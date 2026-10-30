"""Evidence-based work queue shared by project dossiers, files and Outlook."""
import hashlib
import json
import math
import re
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from contextlib import contextmanager

from app import database
from app.config import WORKING_DIR

FILES_DIR = WORKING_DIR / "Ho So Du An" / "Quy Trinh"


@contextmanager
def connection():
    conn=database.get_db_connection()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def today():
    return datetime.now(timezone(timedelta(hours=7))).date()


def iso(value):
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError("Ngày phải có dạng YYYY-MM-DD hoặc DD/MM/YYYY.")


def step(key, title, instruction, role="", link=""):
    return dict(key=key, title=title, instruction=instruction, role=role, link=link)


TEMPLATES = {
    "payment": ("Thu tiền khách hàng", [
        step("condition", "Kiểm tra điều kiện thu", "Đối chiếu đúng hợp đồng, đợt thu, chứng từ và thời hạn T/T. Chỉ xác nhận ngày kích hoạt khi điều kiện thực sự đạt.", "condition", "/tracker"),
        step("prepare", "Lập và kiểm tra hồ sơ", "Lập phiếu yêu cầu thanh toán. Soát số/chữ, mã hợp đồng, tỷ lệ, ngày và tài khoản; bổ sung BBNT/giao nhận nếu mốc yêu cầu.", "draft", "/reminders"),
        step("sign", "In và trình ký", "In bản đã kiểm tra, trình người có thẩm quyền ký và đóng dấu theo quy trình. Ghi người đang giữ hồ sơ và ngày cần lấy lại."),
        step("scan", "Nhận và lưu bản scan", "Scan đủ trang, mở kiểm tra rõ chữ và đúng đợt. Tải phiếu đã ký; BBNT/giao nhận kèm theo nếu cần. Người kiểm tra phải xác nhận bản ký.", "signed_request"),
        step("email", "Kiểm tra bộ gửi và tạo thư nháp", "Kiểm tra To/CC, ngày và toàn bộ tệp đã xác minh. Tạo nháp Outlook; mở xem lại rồi tự bấm Gửi trong Outlook."),
        step("sent", "Xác nhận thư đã gửi thật", "Đồng bộ Outlook và chọn đúng thư trong Sent Items; hoặc ghi mã thư/bằng chứng gửi với người xác nhận. Nháp và mô phỏng không được tính là đã gửi."),
        step("customer", "Theo dõi khách và lịch thanh toán", "Ghi phản hồi, hồ sơ cần bổ sung và ngày khách hẹn. Chỉ xác nhận khách đã nhận đủ hồ sơ khi có bằng chứng; có thể tiếp tục nhắc bằng nháp Outlook.", "customer_confirmation"),
        step("receipt", "Kế toán xác nhận tiền về", "Đối chiếu chứng từ ngân hàng và khoản thực nhận. Ghi từng lần thu; nhận một phần vẫn còn công việc theo dõi.", "payment_evidence"),
    ]),
    "quotation": ("Báo giá", [
        step("need", "Xác nhận nhu cầu", "Chốt model, số lượng, phạm vi và người phụ trách. Bám bản vẽ; không tự thêm chi phí.", "evidence"),
        step("prepare", "Lập và duyệt báo giá", "Chọn đúng pháp nhân/mẫu. Soát giá, VAT, thời hạn và bảo hành; lấy xác nhận người duyệt.", "draft", "/quotations"),
        step("email", "Soạn và kiểm tra thư gửi", "Chọn bản báo giá đã duyệt, To/CC thật; tạo nháp Outlook và kiểm tra trước khi gửi."),
        step("sent", "Lưu thư gửi thật", "Gắn thư Sent Items hoặc bằng chứng gửi đã kiểm tra."),
        step("customer", "Nhận xác nhận hoặc điều chỉnh", "Lưu báo giá ký/PO hoặc email đồng ý rõ phạm vi. Sau đó mở việc hợp đồng/đặt hàng phù hợp.", "customer_confirmation"),
    ]),
    "contract": ("Ký hợp đồng", [
        step("prepare", "Soạn hợp đồng và phụ lục", "Đối chiếu báo giá được duyệt, pháp nhân, người ký và các mốc thu riêng của hợp đồng.", "draft", "/contracts"),
        step("review", "Khách duyệt nội dung", "Lưu phản hồi duyệt; đồng ý nội dung chưa phải hợp đồng ký hai bên.", "customer_confirmation"),
        step("sign", "Trình ký và gửi bản ký", "Trình ký đúng thẩm quyền, theo dõi bản gốc chuyển khách; ghi người giữ và ngày hẹn."),
        step("scan", "Nhận hợp đồng ký hai bên", "Kiểm tra chữ ký, dấu, đủ trang/phụ lục và lưu bản ký hai bên.", "signed_contract"),
        step("register", "Cập nhật hồ sơ và mốc thu", "Vào Hồ sơ hợp đồng nhập/đối chiếu từng mốc, điều kiện và T/T; không suy diễn tỷ lệ mẫu.", "", "/tracker"),
    ]),
    "procurement": ("Mua hàng nhà cung cấp", [
        step("need", "Kiểm tra nhu cầu và điều kiện mua", "Đối chiếu BOM, tồn kho và cọc khách. Nếu mua trước cọc cần lưu phê duyệt ngoại lệ.", "evidence"),
        step("prepare", "Lập và duyệt PO", "Soát NCC, model, số lượng, giá, ngày giao và điều kiện. Chuyển đơn xin duyệt chi khi cần.", "draft", "/po"),
        step("email", "Tạo thư nháp đặt hàng", "Đính kèm PO được duyệt; kiểm tra đầu mối NCC và điều khoản."),
        step("sent", "Xác nhận gửi PO", "Gắn thư gửi thật hoặc bằng chứng gửi."),
        step("customer", "NCC xác nhận và hẹn giao", "Lưu xác nhận PO/PI, lịch giao; phối hợp kế toán thanh toán và XNK nếu có.", "customer_confirmation"),
        step("receive", "Nhận và kiểm tra hàng", "Đếm hàng, SN, ngoại quan; lưu giao nhận và cập nhật mua hàng. Sai lệch phải có phương án.", "delivery", "/po"),
    ]),
    "delivery": ("Giao hàng và thi công", [
        step("prepare", "Chuẩn bị giao hàng", "Soát danh mục/SN, điều kiện nhận hàng, chứng từ XNK nếu giao dịch yêu cầu.", "draft", "/delivery"),
        step("confirm", "Chốt lịch và đầu mối", "Xác nhận kho/người nhận, lịch vào xưởng và yêu cầu an toàn. Lưu bằng chứng xác nhận.", "customer_confirmation"),
        step("handover", "Giao và ký nhận", "Kiểm tra thực tế cùng người nhận, lấy chứng từ giao nhận rõ số lượng/SN.", "delivery"),
        step("implement", "Thi công và kiểm tra", "Theo dõi phạm vi, phát sinh, kết quả kiểm tra và ảnh hiện trường.", "evidence"),
        step("acceptance", "Chuyển nghiệm thu", "Mở việc nghiệm thu đúng phạm vi, cập nhật điều kiện mốc thu sau khi có căn cứ.", "", "/acceptance"),
    ]),
    "acceptance": ("Nghiệm thu", [
        step("condition", "Kiểm tra phạm vi hoàn thành", "Đối chiếu phạm vi hợp đồng, checklist thử và các lỗi còn tồn.", "condition"),
        step("prepare", "Lập biên bản", "Chọn nghiệm thu lắp đặt hoặc sửa chữa, điền đúng từng hạng mục/SN và tiền mốc tương ứng.", "draft", "/acceptance"),
        step("sign", "Tổ chức kiểm tra và ký", "Trình ký bên Hong Ming, hẹn khách kiểm tra; theo dõi các điểm cần bổ sung."),
        step("scan", "Lưu bản xác nhận khách", "Kiểm tra bản ký hai bên/bằng chứng xác nhận phù hợp; không coi bản bên bán ký là hoàn chỉnh.", "acceptance"),
        step("email", "Soạn thư bàn giao hồ sơ", "Chọn đúng bộ nghiệm thu đã xác minh, tạo nháp và kiểm tra trước gửi."),
        step("sent", "Gắn thư gửi và chuyển mốc thu", "Gắn thư gửi thật, sau đó xác nhận điều kiện đợt thu đúng hợp đồng."),
    ]),
    "warranty": ("Bảo hành và sửa chữa", [
        step("need", "Tiếp nhận sự cố", "Ghi model/SN, ngày giao, lỗi và ảnh/video; tách lỗi phát sinh khác thời điểm.", "evidence"),
        step("scope", "Xác nhận phạm vi bảo hành", "Đối chiếu ngày giao/điều khoản và xác nhận NCC: đổi miễn phí hay sửa có phí.", "customer_confirmation"),
        step("prepare", "Chốt phương án xử lý", "Lưu phương án và lịch hàng. Nếu phát sinh phí phải báo giá và được chấp thuận trước.", "draft"),
        step("email", "Soạn thư xác nhận phương án", "Tạo nháp đúng phương án đã duyệt; ghi lịch dự kiến và người phụ trách."),
        step("sent", "Gắn thư gửi thật", "Lưu bằng chứng đã thông báo, theo dõi thực hiện."),
        step("return", "Giao trả và kiểm tra", "Lưu kết quả thử/SN và xác nhận nhận lại thiết bị. Cập nhật việc còn tồn.", "delivery"),
    ]),
}

ROLES = {"condition": "Căn cứ đạt điều kiện", "draft": "Hồ sơ đã kiểm tra để trình ký",
         "signed_request": "Phiếu yêu cầu thanh toán đã ký", "acceptance": "Nghiệm thu đã xác nhận",
         "signed_contract": "Hợp đồng ký hai bên", "customer_confirmation": "Xác nhận của khách/NCC",
         "delivery": "Giao nhận đã xác nhận", "evidence": "Bằng chứng công việc",
         "payment_evidence": "Chứng từ nhận tiền"}
SIGNED_ROLES = {"signed_request", "acceptance", "signed_contract", "customer_confirmation", "delivery"}


def init_schema():
    with connection() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS workflow_cases (
          id INTEGER PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
          contract_code TEXT NOT NULL DEFAULT '', customer TEXT NOT NULL DEFAULT '',
          milestone_id INTEGER UNIQUE, amount REAL NOT NULL DEFAULT 0, currency TEXT NOT NULL DEFAULT 'VND',
          stage INTEGER NOT NULL DEFAULT 0, owner TEXT NOT NULL DEFAULT '',
          followup_date TEXT NOT NULL DEFAULT '', recipient TEXT NOT NULL DEFAULT '', cc TEXT NOT NULL DEFAULT '',
          notes TEXT NOT NULL DEFAULT '', needs_acceptance INTEGER NOT NULL DEFAULT 0,
          subject TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '',
          source_type TEXT NOT NULL DEFAULT '', source_id INTEGER,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS workflow_files (
          id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL, role TEXT NOT NULL,
          name TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL, verified_by TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS workflow_events (
          id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL, action TEXT NOT NULL,
          actor TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS workflow_mail (
          id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL, entry_id TEXT NOT NULL,
          direction TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL DEFAULT '',
          sender TEXT NOT NULL DEFAULT '', received_at TEXT NOT NULL DEFAULT '',
          confirmed_by TEXT NOT NULL DEFAULT '', UNIQUE(case_id,entry_id,direction));
        CREATE TABLE IF NOT EXISTS workflow_receipts (
          id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL, amount REAL NOT NULL,
          paid_date TEXT NOT NULL, reference TEXT NOT NULL, confirmed_by TEXT NOT NULL,
          evidence_id INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(case_id,reference));
        """)
        columns={r[1] for r in c.execute('PRAGMA table_info(workflow_cases)')}
        for name,definition in [('source_type',"TEXT NOT NULL DEFAULT ''"),('source_id','INTEGER')]:
            if name not in columns:
                c.execute(f'ALTER TABLE workflow_cases ADD COLUMN {name} {definition}')
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS workflow_source_unique ON workflow_cases(kind,source_type,source_id) WHERE source_id IS NOT NULL")


def event(c, case_id, action, actor, note):
    c.execute("INSERT INTO workflow_events(case_id,action,actor,note) VALUES (?,?,?,?)",
              (case_id, action, actor, note))


def sync_milestones():
    """Import explicit milestones only. Never invent dates or infer signed documents."""
    with connection() as c:
        from app.services.payment_state_service import reconcile_existing
        reconcile_existing(c)
        rows = c.execute("""SELECT m.*,co.customer_name_vi,co.contact_email,co.contact_cc,co.currency
               FROM payment_milestones m JOIN contracts co ON co.id=m.contract_id""").fetchall()
        for row in rows:
            m = dict(row)
            stage = len(TEMPLATES['payment'][1]) if m['status'] == 'PAID' else 0
            c.execute("""INSERT OR IGNORE INTO workflow_cases
              (kind,title,contract_code,customer,milestone_id,amount,currency,stage,recipient,cc)
              VALUES ('payment',?,?,?,?,?,?,?,?,?)""",
              (m['milestone_name'], m['contract_code'], m['customer_name_vi'], m['id'],
               m['amount'], m['currency'] or 'VND', stage, m['contact_email'] or '', m['contact_cc'] or ''))
            c.execute("""UPDATE workflow_cases SET amount=?,customer=?,currency=?
                         WHERE milestone_id=?""", (m['amount'], m['customer_name_vi'], m['currency'] or 'VND', m['id']))
            if m['status']=='PAID':
                c.execute('UPDATE workflow_cases SET stage=? WHERE milestone_id=?',(len(TEMPLATES['payment'][1]),m['id']))


def get_case(case_id):
    with connection() as c:
        row = c.execute("SELECT * FROM workflow_cases WHERE id=?", (case_id,)).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy công việc.")
        data = dict(row)
        data['source_status']=''
        data['source_date']=''
        data['project_label']=data['contract_code'] or data['customer'] or 'Chưa gắn dự án'
        if data['source_type']=='po':
            source=c.execute('SELECT project_name,customer_company,delivery_status,actual_delivery_date FROM procurement_orders WHERE id=?',(data['source_id'],)).fetchone()
            if source:
                data['source_status']=source['delivery_status'] or ''
                data['source_date']=source['actual_delivery_date'] or ''
                data['project_label']=source['project_name'] or source['customer_company'] or data['project_label']
        data['files'] = [dict(r) for r in c.execute("SELECT * FROM workflow_files WHERE case_id=? ORDER BY id DESC", (case_id,))]
        data['events'] = [dict(r) for r in c.execute("SELECT * FROM workflow_events WHERE case_id=? ORDER BY id DESC", (case_id,))]
        data['mail'] = [dict(r) for r in c.execute("SELECT * FROM workflow_mail WHERE case_id=? ORDER BY id DESC", (case_id,))]
        data['receipts'] = [dict(r) for r in c.execute("SELECT * FROM workflow_receipts WHERE case_id=?", (case_id,))]
        has_facts=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='project_facts'").fetchone()
        data['business_confirmations']=[dict(r) for r in c.execute('SELECT action,actual_date,actor FROM project_facts WHERE case_id=? ORDER BY id DESC',(case_id,))] if has_facts else []
        milestone = c.execute("SELECT * FROM payment_milestones WHERE id=?", (data['milestone_id'],)).fetchone()
        from app.services.payment_state_service import received_for, linked_ar
        inherited_ar=linked_ar(c,dict(milestone)) if milestone else None
        received=received_for(c,dict(milestone)) if milestone else 0
    data['milestone'] = dict(milestone) if milestone else None
    data['steps'] = TEMPLATES[data['kind']][1]
    data['kind_label'] = TEMPLATES[data['kind']][0]
    data['current'] = data['steps'][data['stage']] if data['stage'] < len(data['steps']) else None
    data['received'] = received if milestone else 0
    data['payment_source'] = ('Công nợ đã nhập' if inherited_ar and float(inherited_ar['received_amount'] or 0)>0 else
                              'Chứng từ thu đã ghi nhận' if data['receipts'] else 'Hồ sơ hợp đồng')
    data['recorded_paid_date'] = iso(inherited_ar['paid_date']) if inherited_ar and inherited_ar['paid_date'] else (iso(milestone['paid_date']) if milestone and milestone['paid_date'] else '')
    if milestone and milestone['status']=='PAID' and not data['receipts']:
        data['received']=float(data['amount'])
        data['inherited_paid']=True
    data['remaining'] = max(0, float(data['amount']) - data['received'])
    data['due_date'] = iso(data['milestone']['due_date']) if milestone and data['milestone']['triggered'] else ''
    data['days_left'] = (date.fromisoformat(data['due_date']) - today()).days if data['due_date'] else None
    follow = iso(data['followup_date'])
    data['attention'] = bool(data['current'] and (
        (follow and follow <= today().isoformat()) or (data['days_left'] is not None and data['days_left'] <= 7)))
    data['blockers'] = blockers(data) if data['current'] else []
    data.update(queue_state(data))
    # File paths stay server-side; downloads use an id and a containment check.
    for f in data['files']:
        f['exists'] = safe_path(f['path']).is_file()
    return data


def queue_state(data):
    """A missing historical file is not an outstanding delivery or a new task."""
    if not data['current']:
        return dict(queue_group='closed',queue_label='Đã hoàn tất',queue_reason='Đã thu đủ theo dữ liệu đã nhập' if data.get('inherited_paid') else 'Quy trình đã hoàn tất')
    worked=bool(data.get('business_confirmations') or any(e['action']=='completed' for e in data.get('events',[])))
    scheduled=bool(data.get('owner') or data.get('followup_date'))
    if data.get('source_type')=='po' and data.get('source_status')=='DELIVERED' and not worked:
        return dict(queue_group='review',queue_label='Hồ sơ cần đối chiếu',queue_reason='Nguồn mua hàng ghi đã giao đủ'+(' · '+data['source_date'] if data.get('source_date') else '')+'. Chưa xác minh bộ chứng từ; không yêu cầu mua/giao lại.')
    if data.get('source_type') in ('po','contract','document','quotation') and not worked and not scheduled:
        return dict(queue_group='review',queue_label='Hồ sơ cần đối chiếu',queue_reason='Hồ sơ kế thừa chưa được xác nhận bước hiện tại. Thiếu dữ liệu không có nghĩa nghiệp vụ chưa làm.')
    if data['kind']=='payment' and not (data.get('milestone') or {}).get('triggered'):
        return dict(queue_group='waiting',queue_label='Chờ điều kiện thu',queue_reason='Đợt thu chưa xác nhận điều kiện kích hoạt. Chưa kết luận đến hạn hoặc cần đòi thanh toán.')
    return dict(queue_group='active',queue_label='Cần thực hiện',queue_reason=data['current']['title'])


def list_cases():
    sync_milestones()
    with connection() as c:
        ids = [r[0] for r in c.execute("SELECT id FROM workflow_cases ORDER BY id DESC")]
    rows = [get_case(i) for i in ids]
    rows.sort(key=lambda r: (r['current'] is None, not r['attention'], r['followup_date'] or r['due_date'] or '9999'))
    return rows


def sources():
    result=[]
    with connection() as c:
        for r in c.execute('SELECT id,contract_code,customer_name_vi,contact_email,contact_cc FROM contracts'):
            result.append(dict(source_type='contract',source_id=r['id'],kind='contract',title=r['contract_code'],
                contract_code=r['contract_code'],customer=r['customer_name_vi'],recipient=r['contact_email'] or '',cc=r['contact_cc'] or ''))
        for r in c.execute('SELECT id,quotation_no,customer_name_vi FROM quotations WHERE is_current=1'):
            result.append(dict(source_type='quotation',source_id=r['id'],kind='quotation',title=r['quotation_no'],contract_code=r['quotation_no'],customer=r['customer_name_vi']))
        for r in c.execute('SELECT id,project_name,item_name,supplier_name FROM procurement_orders'):
            result.append(dict(source_type='po',source_id=r['id'],kind='procurement',title=f"{r['project_name']} · {r['item_name']}",contract_code='',customer=r['supplier_name']))
        for r in c.execute("SELECT id,contract_code,doc_name FROM documents WHERE doc_type IN ('NGHIEM_THU','ACCEPTANCE','NGHIEM_THU_LAP_DAT','NGHIEM_THU_SUA_CHUA')"):
            result.append(dict(source_type='document',source_id=r['id'],kind='acceptance',title=r['doc_name'],contract_code=r['contract_code'] or '',customer=''))
    return result


def create_case(payload):
    kind = payload.get('kind', '')
    title = str(payload.get('title', '')).strip()
    if kind not in TEMPLATES or not title:
        raise ValueError("Chọn loại việc và nhập tên công việc.")
    if kind == 'payment':
        raise ValueError("Đợt thu được tạo từ Hồ sơ hợp đồng; hãy nhập mốc thu vào hợp đồng trước.")
    payload=dict(payload)
    linked=None
    if payload.get('source_id'):
        linked=next((s for s in sources() if s['source_type']==payload.get('source_type') and s['source_id']==int(payload['source_id']) and s['kind']==kind),None)
        if not linked:
            raise ValueError('Hồ sơ nguồn không tồn tại hoặc khác loại công việc.')
        payload.update(linked)
        title=linked['title']
    with connection() as c:
        if linked:
            existing=c.execute('SELECT id FROM workflow_cases WHERE kind=? AND source_type=? AND source_id=?',
                (kind,linked['source_type'],linked['source_id'])).fetchone()
            if existing:
                return get_case(existing['id'])
        cur = c.execute("""INSERT INTO workflow_cases(kind,title,contract_code,customer,owner,followup_date,source_type,source_id,recipient,cc)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (kind, title, str(payload.get('contract_code', '')).strip(),
            str(payload.get('customer', '')).strip(), str(payload.get('owner', '')).strip(), iso(payload.get('followup_date')),
            linked['source_type'] if linked else '',linked['source_id'] if linked else None,
            payload.get('recipient',''),payload.get('cc','')))
        event(c, cur.lastrowid, 'created', str(payload.get('owner') or 'Người lập'), title)
        case_id = cur.lastrowid
    return get_case(case_id)


def update_case(case_id, payload):
    get_case(case_id)
    allowed = {'owner','followup_date','recipient','cc','notes','needs_acceptance','subject','body'}
    values = {k: v for k, v in payload.items() if k in allowed}
    if 'followup_date' in values:
        values['followup_date'] = iso(values['followup_date'])
    if 'needs_acceptance' in values:
        values['needs_acceptance'] = int(bool(values['needs_acceptance']))
    if values:
        with connection() as c:
            c.execute("UPDATE workflow_cases SET " + ','.join(k+'=?' for k in values) +
                      ",updated_at=CURRENT_TIMESTAMP WHERE id=?", (*values.values(), case_id))
            event(c, case_id, 'updated', str(payload.get('actor') or 'Người cập nhật'), 'Cập nhật thông tin theo dõi và nội dung thư')
    return get_case(case_id)


def safe_path(path):
    p = Path(path).resolve()
    if not p.is_relative_to(FILES_DIR.resolve()):
        raise ValueError("Tệp không thuộc kho hồ sơ công việc.")
    return p


def add_file(case_id, name, content, role, verified_by=''):
    case = get_case(case_id)
    if role not in ROLES:
        raise ValueError("Chọn đúng loại hồ sơ.")
    suffix = Path(name).suffix.lower()
    if suffix not in {'.pdf','.docx','.xlsx','.png','.jpg','.jpeg'} or not content or len(content) > 25*1024*1024:
        raise ValueError("Chỉ nhận PDF, DOCX, XLSX hoặc ảnh, tối đa 25 MB.")
    if (suffix == '.pdf' and not content.startswith(b'%PDF')) or (suffix in {'.docx','.xlsx'} and not content.startswith(b'PK')):
        raise ValueError("Nội dung tệp không khớp định dạng.")
    if suffix == '.png' and not content.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError("Tệp PNG không hợp lệ.")
    if suffix in {'.jpg','.jpeg'} and not content.startswith(b'\xff\xd8'):
        raise ValueError("Tệp JPEG không hợp lệ.")
    if role in SIGNED_ROLES and (not str(verified_by).strip() or suffix not in {'.pdf','.png','.jpg','.jpeg'}):
        raise ValueError("Bản ký/xác nhận cần PDF hoặc ảnh và tên người đã kiểm tra.")
    path = FILES_DIR / str(case_id) / (uuid.uuid4().hex + suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    display_name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', Path(name.replace('\\','/')).name)[:180]
    with connection() as c:
        cur = c.execute("""INSERT INTO workflow_files(case_id,role,name,path,sha256,verified_by)
                  VALUES (?,?,?,?,?,?)""", (case_id,role,display_name,str(path),hashlib.sha256(content).hexdigest(),verified_by.strip()))
        file_id = cur.lastrowid
        c.execute("""INSERT INTO documents(contract_code,doc_type,doc_name,file_name,file_path,file_size,file_format,description)
            VALUES (?,?,?,?,?,?,?,?)""", (case['contract_code'],'WORKFLOW',display_name,display_name,str(path),len(content),suffix[1:],f"Công việc #{case_id}: {ROLES[role]}"))
        event(c,case_id,'file',verified_by or case['owner'] or 'Người tải',ROLES[role]+': '+display_name)
    return file_id


def has_file(data, role):
    return any(f['role']==role and safe_path(f['path']).is_file() and
               (role not in SIGNED_ROLES or f['verified_by']) for f in data['files'])


def blockers(data):
    current = data['current']
    if not current:
        return []
    missing = []
    key, role = current['key'], current['role']
    confirmed_reply = role == 'customer_confirmation' and any(m['direction']=='inbox' and m['confirmed_by'] for m in data['mail'])
    if role and not has_file(data, role) and not confirmed_reply:
        missing.append('Thiếu '+ROLES[role])
    if data['kind']=='payment' and (not math.isfinite(float(data['amount'])) or float(data['amount'])<=0):
        missing.append('Số tiền đợt thu chưa hợp lệ; kiểm tra Hồ sơ hợp đồng')
    if key == 'condition' and data['kind']=='payment' and not data['milestone']['triggered']:
        missing.append('Chưa xác nhận ngày đạt điều kiện và thời hạn T/T')
    if key in {'email','sent'}:
        if not data['recipient'].strip():
            missing.append('Chưa có người nhận được xác nhận')
        required = ['signed_request'] if data['kind']=='payment' else (['acceptance'] if data['kind']=='acceptance' else ['draft'])
        if data['kind']=='payment' and data['needs_acceptance']:
            required.append('acceptance')
        for r in required:
            if not has_file(data,r):
                missing.append('Thiếu '+ROLES[r])
        if not data['subject'].strip() or not data['body'].strip():
            missing.append('Chưa lưu tiêu đề và nội dung thư đã kiểm tra')
    if key=='sent' and not any(m['direction']=='sent' and m['confirmed_by'] for m in data['mail']):
        missing.append('Chưa có bằng chứng thư gửi thật')
    if key=='receipt':
        missing.append('Cần ghi nhận tiền thực nhận với xác nhận kế toán')
    return missing


def advance(case_id, stage, actor, note):
    data = get_case(case_id)
    if not actor.strip() or not note.strip():
        raise ValueError("Nhập người xác nhận và căn cứ/kết quả thực hiện.")
    if data['stage']!=stage or not data['current']:
        raise ValueError("Công việc đã đổi bước; tải lại trang trước khi xác nhận.")
    if data['blockers']:
        raise ValueError('; '.join(data['blockers']))
    with connection() as c:
        cur=c.execute("UPDATE workflow_cases SET stage=stage+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND stage=?",(case_id,stage))
        if not cur.rowcount:
            raise ValueError("Bước đã được người khác cập nhật.")
        event(c,case_id,'completed',actor,data['current']['title']+': '+note)
    return get_case(case_id)


def reopen(case_id, actor, reason):
    data=get_case(case_id)
    if data['business_confirmations']:
        raise ValueError('Nghiệp vụ đã đồng bộ sang hồ sơ liên quan. Không lùi checklist để hủy sự thật đã ghi; cần đối chiếu và ghi hồ sơ điều chỉnh riêng.')
    if not actor.strip() or not reason.strip() or not data['stage'] or data['receipts']:
        raise ValueError('Cần người xác nhận, lý do và công việc chưa có khoản thu. Khoản thu đã đối chiếu cần kế toán xử lý riêng.')
    with connection() as c:
        c.execute('UPDATE workflow_cases SET stage=stage-1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND stage=?',(case_id,data['stage']))
        event(c,case_id,'reopened',actor,'Quay lại bước trước: '+reason)
    return get_case(case_id)


def confirm_condition(case_id, payload):
    data=get_case(case_id)
    actor=str(payload.get('actor','')).strip()
    if data['kind']!='payment' or data['stage']!=0 or not actor or not has_file(data,'condition'):
        raise ValueError("Cần căn cứ đạt điều kiện, người xác nhận và công việc ở bước kiểm tra điều kiện thu.")
    raw=payload.get('term_days')
    if raw is None or isinstance(raw,bool) or int(raw)!=float(raw) or int(raw)<0:
        raise ValueError("Nhập số ngày T/T đã xác nhận, 0 nghĩa là đến hạn ngay.")
    trigger=iso(payload.get('trigger_date'))
    if not trigger or trigger>today().isoformat():
        raise ValueError("Ngày đạt điều kiện không được trống hoặc ở tương lai.")
    # Do not use the legacy implicit ten-day grace period.
    due=(date.fromisoformat(trigger)+timedelta(days=int(raw))).isoformat()
    with connection() as c:
        c.execute("UPDATE payment_milestones SET triggered=1,trigger_date=?,payment_term_days=?,due_date=? WHERE id=?",
                  (trigger,int(raw),due,data['milestone_id']))
        event(c,case_id,'condition',actor,f'Đạt điều kiện {trigger}; T/T {raw} ngày; đến hạn {due}')
    return get_case(case_id)


def email_text(case_id):
    data=get_case(case_id)
    from app.utils.currency_helper import number_to_vietnamese_words, number_to_chinese_words
    amount=float(data['remaining'])
    if data['kind']=='payment':
        due=data['due_date'] or 'Chưa xác nhận / 待確認'
        amount_text=f'{amount:,.0f}' if data['currency']=='VND' else f'{amount:,.2f}'
        words=(f"Bằng chữ：{number_to_vietnamese_words(int(amount))}\n大寫：{number_to_chinese_words(int(amount))}\n"
               if data['currency']=='VND' else '')
        subject=f"Đề nghị thanh toán {data['title']} – {data['contract_code']} / 付款申請"
        body=(f"Kính gửi Quý Công ty {data['customer']},\n敬致 {data['customer']} 貴公司：\n\n"
              f"Hong Ming kính đề nghị thanh toán theo thông tin sau / 敬請協助安排以下款項：\n"
              f"Hợp đồng / 合約：{data['contract_code']}\nGiai đoạn / 付款期次：{data['title']}\n"
              f"Số tiền còn đề nghị / 本次申請金額：{amount_text} {data['currency']}\n"
              f"{words}"
              f"Ngày đến hạn đã xác nhận / 已確認付款期限：{due}\n\n"
              "Thông tin chuyển khoản theo phiếu yêu cầu thanh toán đã kiểm tra.\n匯款資訊請依已核對之請款單。\n\n"
              "Kính nhờ Quý Công ty kiểm tra hồ sơ và xác nhận lịch thanh toán.\n敬請貴司核對資料並確認付款安排。\n\n"
              "Trân trọng / 此致 敬禮\nCÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司")
    else:
        subject=f"{data['kind_label']} – {data['title']} – {data['contract_code']}"
        body=(f"Kính gửi Quý Công ty {data['customer']},\n敬致 {data['customer']} 貴公司：\n\n"
              f"Hong Ming gửi hồ sơ liên quan đến {data['title']}, tham chiếu {data['contract_code']}.\n"
              f"我司提供「{data['title']}」相關資料，參考編號：{data['contract_code']}。\n\n"
              "Kính nhờ Quý Công ty kiểm tra và phản hồi nội dung cần xác nhận.\n敬請貴司查閱並回覆需確認事項。\n\n"
              "Trân trọng / 此致 敬禮\nCÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司")
        messages={
          'quotation':('Kính gửi báo giá để Quý Công ty kiểm tra model, số lượng, giá và điều kiện. Kính nhờ ký xác nhận hoặc phản hồi nội dung cần điều chỉnh để chúng tôi sắp xếp bước tiếp theo.',
                       '敬請核對報價之型號、數量、價格及條件，並簽回確認或告知需調整事項，以便安排後續作業。'),
          'contract':('Kính gửi hồ sơ hợp đồng để đối chiếu pháp nhân, phạm vi, lịch giao và các mốc thanh toán. Kính nhờ phản hồi nội dung và phối hợp ký đúng thẩm quyền. Việc duyệt nội dung cần được phân biệt với việc hoàn tất ký hai bên.',
                      '敬請核對合約之法人資料、範圍、交期及付款條件，並回覆意見及協助辦理授權簽署。內容同意與雙方完成簽署須分別確認。'),
          'procurement':('Kính gửi hồ sơ đặt hàng để Quý Công ty xác nhận model, số lượng, đơn giá và lịch giao. Kính nhờ phản hồi xác nhận PO và thời gian dự kiến; thay đổi cần được hai bên thống nhất trước khi thực hiện.',
                         '敬請確認採購單之型號、數量、單價及交期，並回覆訂單確認與預計出貨日；如有變更請先取得雙方同意。'),
          'delivery':('Kính nhờ xác nhận lịch giao, địa điểm, người nhận và yêu cầu vào xưởng. Khi nhận hàng, kính nhờ kiểm đếm số lượng, số máy và ký chứng từ giao nhận; nội dung còn thiếu xin phản hồi để đối chiếu.',
                      '敬請確認交貨時間、地點、收貨窗口及入廠要求。收貨時請核對數量、序號並簽收交貨文件；如有缺漏敬請回覆核對。'),
          'acceptance':('Kính gửi hồ sơ nghiệm thu để Quý Công ty đối chiếu phạm vi, kết quả kiểm tra và các điểm còn tồn. Kính nhờ phối hợp kiểm tra, ký xác nhận hoặc phản hồi nội dung cần bổ sung. Điều kiện thu tiền sẽ được đối chiếu riêng theo đúng mốc hợp đồng.',
                        '敬請核對驗收範圍、測試結果及待處理事項，並協助查驗簽認或回覆需補充內容。請款條件將依合約對應期次另行核對。'),
          'warranty':('Kính nhờ xác nhận model/SN, ngày giao, thời điểm phát sinh lỗi và ảnh/video hiện tượng. Phạm vi miễn phí hay có phí cần được đối chiếu điều khoản và xác nhận phương án trước khi xử lý; lịch giao trả sẽ được thông báo sau khi thống nhất.',
                      '敬請提供型號、序號、交貨日、故障發生時間及照片／影片。免費保固或付費維修須依條款核對並確認處理方案後辦理；返還時程於確認後通知。'),
        }
        vi,zh=messages[data['kind']]
        body=body.replace('Kính nhờ Quý Công ty kiểm tra và phản hồi nội dung cần xác nhận.\n敬請貴司查閱並回覆需確認事項。',vi+'\n'+zh)
    return {'subject':subject,'body':body}


def verified_attachments(data):
    allowed={'payment':{'signed_request','acceptance'},'quotation':{'draft'},
             'contract':{'signed_contract'} if has_file(data,'signed_contract') else {'draft'},
             'procurement':{'draft'},'delivery':{'delivery'} if has_file(data,'delivery') else {'draft'},
             'acceptance':{'acceptance'} if has_file(data,'acceptance') else {'draft'},
             'warranty':{'draft'}}[data['kind']]
    # Latest version of each role only; other cases and payment evidence are never added.
    selected={}
    for f in data['files']:
        if f['role'] in allowed and f['role'] not in selected and (f['verified_by'] or f['role']=='draft'):
            p=safe_path(f['path'])
            if p.is_file():
                if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:
                    raise ValueError('Tệp đã thay đổi sau kiểm tra; tải lại bản đúng trước khi gửi.')
                selected[f['role']]=f
    return list(selected.values())


def validate_email(data):
    # Apply the same attachment rules even when drafting a follow-up at a later stage.
    copy=dict(data,current={'key':'email','role':''})
    errors=blockers(copy)
    if data['kind']=='payment' and float(data['remaining'])<=0:
        errors.append('Đợt này đã thu đủ theo dữ liệu đã nhập; không tạo đề nghị thu lại.')
    if data['kind']=='payment' and (not data['milestone']['triggered'] or not data['due_date']):
        errors.append('Chưa xác nhận điều kiện thu và ngày đến hạn')
    for raw in (data['recipient'],data['cc']):
        for address in filter(None,re.split(r'[;,\s]+',raw)):
            if not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+',address) or address.endswith('@khachhang.com'):
                errors.append('Địa chỉ email chưa hợp lệ hoặc còn dữ liệu mẫu')
    if errors:
        raise ValueError('; '.join(errors))
    files=verified_attachments(data)
    if not files:
        raise ValueError('Chưa có tệp thật đã kiểm tra để gửi.')
    return files


def record_mail(case_id, entry_id, direction, subject, body='', sender='', received_at='', actor=''):
    get_case(case_id)
    if direction not in {'draft','sent','inbox'} or not entry_id or not actor.strip():
        raise ValueError('Cần mã thư, loại thư và người kiểm tra.')
    with connection() as c:
        c.execute("""INSERT INTO workflow_mail(case_id,entry_id,direction,subject,body,sender,received_at,confirmed_by)
          VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(case_id,entry_id,direction) DO UPDATE SET confirmed_by=excluded.confirmed_by""",
          (case_id,entry_id,direction,subject,body,sender,received_at,actor))
        event(c,case_id,'mail',actor,f'{direction}: {subject} [{entry_id}]')


def add_receipt(case_id,payload):
    data=get_case(case_id)
    if data['kind']!='payment' or not data['current'] or data['current']['key']!='receipt':
        raise ValueError('Chỉ xác nhận tiền về khi đang ở bước kế toán đối chiếu.')
    amount=float(payload.get('amount') or 0)
    actor=str(payload.get('actor') or '').strip()
    reference=str(payload.get('reference') or '').strip()
    paid=iso(payload.get('paid_date'))
    evidence=next((f for f in data['files'] if f['id']==payload.get('evidence_id') and f['role']=='payment_evidence' and f['verified_by'] and f['exists']),None)
    if not math.isfinite(amount) or amount<=0 or not actor or not reference or not evidence or not paid or paid>today().isoformat():
        raise ValueError('Cần số tiền dương, ngày thực nhận, tham chiếu, người kế toán xác nhận và chứng từ đã kiểm tra.')
    if data['currency']=='VND' and not amount.is_integer():
        raise ValueError('Số tiền VND phải là số nguyên đồng.')
    with connection() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT 1 FROM workflow_receipts WHERE case_id=? AND reference=?',(case_id,reference)).fetchone():
            raise ValueError('Tham chiếu thu tiền đã được ghi nhận; không ghi trùng.')
        from app.services.payment_state_service import received_for, write_received_to_ar
        current_ms=dict(c.execute('SELECT * FROM payment_milestones WHERE id=?',(data['milestone_id'],)).fetchone())
        total=received_for(c,current_ms)
        if total+amount>float(data['amount'])+0.001:
            raise ValueError('Vượt số tiền của đợt thu; cần đối chiếu riêng khoản trả thừa.')
        c.execute('INSERT INTO workflow_receipts(case_id,amount,paid_date,reference,confirmed_by,evidence_id) VALUES (?,?,?,?,?,?)',
                  (case_id,amount,paid,reference,actor,evidence['id']))
        full=total+amount>=float(data['amount'])-0.001
        if full:
            c.execute("UPDATE payment_milestones SET status='PAID',status_label='Đã thu đủ',paid_date=?,action_required='Đã hoàn thành thu tiền' WHERE id=?",(paid,data['milestone_id']))
            c.execute('UPDATE workflow_cases SET stage=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(len(data['steps']),case_id))
        write_received_to_ar(c,data['milestone_id'],total+amount,paid)
        # Preserve the agreed milestone amount and include partial receipts in contract totals.
        row=c.execute('SELECT contract_id FROM payment_milestones WHERE id=?',(data['milestone_id'],)).fetchone()
        new_paid=database.contract_received_total(c,row['contract_id'])
        c.execute('UPDATE contracts SET paid_amount=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(new_paid,row['contract_id']))
        event(c,case_id,'receipt',actor,f'Nhận {amount:,.0f} {data["currency"]} ngày {paid}; tham chiếu {reference}')
    return get_case(case_id)
