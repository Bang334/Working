"""Explicit, evidence-backed transitions between project modules.

Reading an email never executes these transitions. Source records remain distinct
from verified business facts; old delivery statuses are displayed as inherited.
"""
import calendar
import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path
from app.services import workflow_service as work


def init_schema():
    with work.connection() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS project_case_links(
          case_id INTEGER PRIMARY KEY,contract_id INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS project_facts(
          id INTEGER PRIMARY KEY,case_id INTEGER NOT NULL,contract_id INTEGER NOT NULL,
          action TEXT NOT NULL,actual_date TEXT NOT NULL,evidence_id INTEGER NOT NULL,
          actor TEXT NOT NULL,payload TEXT NOT NULL,request_key TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS project_assets(
          id INTEGER PRIMARY KEY,contract_id INTEGER NOT NULL,case_id INTEGER NOT NULL,
          model TEXT NOT NULL,serial TEXT NOT NULL UNIQUE,delivery_date TEXT NOT NULL,
          warranty_months INTEGER NOT NULL,warranty_until TEXT NOT NULL,evidence_id INTEGER NOT NULL);
        ''')


def sync_sources():
    """Refresh explicit source identities, never infer acceptance or signatures."""
    for source in work.sources():
        case=work.create_case(dict(source, owner=''))
        with work.connection() as c:
            c.execute('UPDATE workflow_cases SET title=?,customer=? WHERE id=?',(source['title'],source['customer'],case['id']))
            if source['source_type']=='po':
                po=c.execute('SELECT delivery_status FROM procurement_orders WHERE id=?',(source['source_id'],)).fetchone()
                if po and po[0]=='DELIVERED':
                    # Historical receipt does not prove earlier paperwork, nor customer delivery.
                    c.execute('UPDATE workflow_cases SET stage=5 WHERE id=? AND stage=0',(case['id'],))
    with work.connection() as c:
        c.execute('''INSERT OR IGNORE INTO project_case_links(case_id,contract_id)
          SELECT w.id,co.id FROM workflow_cases w JOIN contracts co
          ON w.contract_code=co.contract_code WHERE w.source_type='contract' OR w.kind='payment' ''')


def context(case_id):
    with work.connection() as c:
        link=c.execute('SELECT contract_id FROM project_case_links WHERE case_id=?',(case_id,)).fetchone()
        contract_id=link[0] if link else None
        facts=[dict(r) for r in c.execute('SELECT * FROM project_facts WHERE case_id=? ORDER BY id DESC',(case_id,))]
        contracts=[dict(r) for r in c.execute('SELECT id,contract_code,customer_name_vi FROM contracts ORDER BY id DESC')]
        milestones=[dict(r) for r in c.execute('SELECT * FROM payment_milestones WHERE contract_id=?',(contract_id,))] if contract_id else []
        assets=[dict(r) for r in c.execute('SELECT * FROM project_assets WHERE contract_id=?',(contract_id,))] if contract_id else []
        row=c.execute('SELECT * FROM workflow_cases WHERE id=?',(case_id,)).fetchone()
        source_status=''
        if row and row['source_type']=='po':
            po=c.execute('SELECT * FROM procurement_orders WHERE id=?',(row['source_id'],)).fetchone()
            if po:
                source_status=f"Mua hàng: {po['delivery_status'] or 'PENDING'}; ngày nhận đã nhập: {po['actual_delivery_date'] or 'chưa có'}. Đây là hàng từ NCC, chưa xác nhận giao khách."
        related=[dict(r) for r in c.execute('''SELECT w.id,w.kind,w.title,w.stage FROM workflow_cases w
          JOIN project_case_links l ON l.case_id=w.id WHERE l.contract_id=? AND w.id<>?''',(contract_id,case_id))] if contract_id else []
        return dict(contract_id=contract_id,facts=facts,contracts=contracts,milestones=milestones,assets=assets,source_status=source_status,related=related)


def link(case_id,payload):
    work.get_case(case_id)
    actor=str(payload.get('actor','')).strip()
    target=int(payload.get('contract_id') or 0)
    if not actor:
        raise ValueError('Nhập người xác nhận liên kết hợp đồng.')
    with work.connection() as c:
        co=c.execute('SELECT * FROM contracts WHERE id=?',(target,)).fetchone()
        row=c.execute('SELECT * FROM workflow_cases WHERE id=?',(case_id,)).fetchone()
        if not co:
            raise ValueError('Hợp đồng không tồn tại.')
        old=c.execute('SELECT contract_id FROM project_case_links WHERE case_id=?',(case_id,)).fetchone()
        if old and old[0]!=target or (row['source_type']=='contract' and row['source_id']!=target):
            raise ValueError('Đã liên kết hợp đồng khác; cần đối chiếu riêng trước khi đổi.')
        if row['milestone_id'] and row['contract_code']!=co['contract_code']:
            raise ValueError('Không được đổi hợp đồng của đợt thu.')
        c.execute('INSERT OR IGNORE INTO project_case_links VALUES (?,?)',(case_id,target))
        # A quotation reference remains its own identity; do not overwrite it.
        if row['kind'] not in ('quotation','payment','contract'):
            c.execute('UPDATE workflow_cases SET contract_code=? WHERE id=?',(co['contract_code'],case_id))
        work.event(c,case_id,'linked',actor,'Liên kết đúng hợp đồng '+co['contract_code'])
    return context(case_id)


def _next(c,kind,title,co,source_id):
    c.execute('''INSERT OR IGNORE INTO workflow_cases(kind,title,contract_code,customer,source_type,source_id)
      VALUES (?,?,?,?,'project_fact',?)''',(kind,title,co['contract_code'],co['customer_name_vi'],source_id))
    row=c.execute("SELECT id FROM workflow_cases WHERE kind=? AND source_type='project_fact' AND source_id=?",(kind,source_id)).fetchone()
    if co['id']:
        c.execute('INSERT OR IGNORE INTO project_case_links VALUES (?,?)',(row[0],co['id']))
    return row[0]


ACTIONS={
 'quotation_approved':('quotation','customer_confirmation','Khách chấp thuận báo giá'),
 'contract_signed':('contract','signed_contract','Nhận hợp đồng ký hai bên'),
 'supplier_received':('procurement','delivery','Nhận hàng từ nhà cung cấp'),
 'customer_delivered':('delivery','delivery','Giao hàng cho khách'),
 'acceptance_recorded':('acceptance','acceptance','Lưu nghiệm thu khách xác nhận, chưa kích hoạt thu'),
 'acceptance_confirmed':('acceptance','acceptance','Nghiệm thu đạt điều kiện của đợt thu đã chọn'),
 'delivery_payment_condition':('delivery','delivery','Giao hàng đạt điều kiện thu theo hợp đồng'),
 'contract_payment_condition':('contract','signed_contract','Ký hợp đồng đạt điều kiện thu theo hợp đồng'),
 'warranty_scope':('warranty','customer_confirmation','Chốt bảo hành miễn phí / có phí'),
 'warranty_returned':('warranty','delivery','Giao trả thiết bị sau xử lý'),
 'asset_registered':('delivery','delivery','Ghi thiết bị và thời hạn bảo hành'),
}


def confirm(case_id,payload):
    data=work.get_case(case_id)
    action=str(payload.get('action',''))
    if action not in ACTIONS or ACTIONS[action][0]!=data['kind']:
        raise ValueError('Nghiệp vụ không phù hợp loại công việc.')
    actor=str(payload.get('actor','')).strip()
    actual=work.iso(payload.get('actual_date'))
    note=str(payload.get('note','')).strip()
    ev=next((f for f in data['files'] if f['id']==int(payload.get('evidence_id') or 0)),None)
    if not actor or not note or not actual or actual>work.today().isoformat() or not ev or not ev['verified_by'] or not ev['exists'] or ev['role']!=ACTIONS[action][1]:
        raise ValueError('Cần ngày thực tế, người xác nhận, nội dung và đúng loại chứng từ đã kiểm tra.')
    if hashlib.sha256(work.safe_path(ev['path']).read_bytes()).hexdigest()!=ev['sha256']:
        raise ValueError('Chứng từ đã thay đổi; tải lại bản đúng để kiểm tra.')
    ctx=context(case_id)
    if not ctx['contract_id'] and action!='quotation_approved':
        raise ValueError('Chọn chính xác hợp đồng liên quan trước khi đồng bộ nghiệp vụ.')
    # Stable semantic identity makes retries harmless; distinct deliveries need distinct evidence.
    identity={k:payload.get(k) for k in ('milestone_id','serial')}
    key=hashlib.sha256(json.dumps([case_id,action,ev['id'],identity],sort_keys=True).encode()).hexdigest()
    with work.connection() as c:
        old=c.execute('SELECT * FROM project_facts WHERE request_key=?',(key,)).fetchone()
        if old:
            if old['payload']!=json.dumps(payload,ensure_ascii=False,sort_keys=True):
                raise ValueError('Chứng từ đã ghi với nội dung khác. Đối chiếu lịch sử trước khi sửa.')
            return context(case_id)
        co=c.execute('SELECT * FROM contracts WHERE id=?',(ctx['contract_id'],)).fetchone()
        if co is None:
            # A quote can be accepted before a contract exists. Create a review
            # task, never fabricate a signed contract or payment schedule.
            co=dict(id=0,contract_code='',customer_name_vi=data['customer'])
        if action in ('quotation_approved','contract_signed','acceptance_confirmed','warranty_scope','warranty_returned') and c.execute('SELECT 1 FROM project_facts WHERE case_id=? AND action=?',(case_id,action)).fetchone():
            raise ValueError('Nghiệp vụ đã được xác nhận. Không ghi lại bằng chứng khác để tạo trùng bước sau.')
        cur=c.execute('''INSERT INTO project_facts(case_id,contract_id,action,actual_date,evidence_id,actor,payload,request_key)
          VALUES (?,?,?,?,?,?,?,?)''',(case_id,co['id'],action,actual,ev['id'],actor,json.dumps(payload,ensure_ascii=False,sort_keys=True),key))
        fid=cur.lastrowid
        if action=='quotation_approved':
            # Approval starts review, never marks a contract signed or places a PO.
            origin=c.execute("SELECT action FROM project_facts WHERE id=?",(data['source_id'],)).fetchone() if data['source_type']=='project_fact' else None
            if not origin or origin[0]!='warranty_scope':
                _next(c,'contract','Đối chiếu hợp đồng từ '+data['title'],co,fid)
        elif action=='contract_signed':
            _next(c,'procurement','Kiểm tra BOM, cọc và điều kiện mua '+co['contract_code'],co,fid)
        elif action=='supplier_received':
            if data['source_type']!='po':
                raise ValueError('Liên kết đúng dòng mua hàng trước khi ghi nhận hàng NCC.')
            po=c.execute('SELECT * FROM procurement_orders WHERE id=?',(data['source_id'],)).fetchone()
            qty=float(payload.get('quantity') or 0)
            previous=c.execute("SELECT payload FROM project_facts WHERE case_id=? AND action='supplier_received' AND id<>?",(case_id,fid)).fetchall()
            total=qty+sum(float(json.loads(r[0])['quantity']) for r in previous)
            if not math.isfinite(qty) or qty<=0 or not po or total>float(po['quantity'] or 0):
                raise ValueError('Số lượng thực nhận phải dương và tổng nhận không vượt dòng PO.')
            full=total>=float(po['quantity'])
            if po['delivery_status']=='DELIVERED' and not full:
                raise ValueError('PO cũ đã ghi nhận đủ; cần đối chiếu lại, không tự chuyển thành nhận thiếu.')
            c.execute('UPDATE procurement_orders SET delivery_status=?,actual_delivery_date=?,delivery_status_label=? WHERE id=?',('DELIVERED' if full else 'PARTIAL',actual if full else po['actual_delivery_date'],'Đã nhận đủ' if full else 'Nhận một phần',po['id']))
            _next(c,'delivery','Chuẩn bị giao khách: '+data['title'],co,fid)
        elif action=='customer_delivered':
            _next(c,'acceptance','Nghiệm thu: '+data['title'],co,fid)
        elif action in ('acceptance_confirmed','delivery_payment_condition','contract_payment_condition'):
            mid=int(payload.get('milestone_id') or 0)
            m=c.execute('SELECT * FROM payment_milestones WHERE id=? AND contract_id=?',(mid,co['id'])).fetchone()
            raw=payload.get('term_days')
            if not m or raw is None or isinstance(raw,bool) or int(raw)!=float(raw) or int(raw)<0:
                raise ValueError('Chọn đúng đợt thu và nhập T/T đã thỏa thuận, kể cả 0 ngày.')
            due=(date.fromisoformat(actual)+timedelta(days=int(raw))).isoformat()
            if m['status']=='PAID' or m['triggered'] and (work.iso(m['trigger_date'])!=actual or m['payment_term_days']!=int(raw)):
                raise ValueError('Đợt thu đã thu đủ hoặc có điều kiện khác; cần đối chiếu, không ghi đè.')
            c.execute('UPDATE payment_milestones SET triggered=1,trigger_date=?,payment_term_days=?,due_date=? WHERE id=?',(actual,int(raw),due,mid))
            pay=c.execute('SELECT id FROM workflow_cases WHERE milestone_id=?',(mid,)).fetchone()
            if not pay:
                raise ValueError('Làm mới danh sách để tạo việc thu tiền trước.')
            c.execute('''INSERT INTO workflow_files(case_id,role,name,path,sha256,verified_by)
              VALUES (?,'condition',?,?,?,?)''',(pay[0],ev['name'],ev['path'],ev['sha256'],actor))
            if action=='acceptance_confirmed':
                c.execute('''INSERT INTO workflow_files(case_id,role,name,path,sha256,verified_by)
                  VALUES (?,'acceptance',?,?,?,?)''',(pay[0],ev['name'],ev['path'],ev['sha256'],actor))
                c.execute('UPDATE workflow_cases SET needs_acceptance=1 WHERE id=?',(pay[0],))
            work.event(c,pay[0],'condition',actor,f'{ACTIONS[action][2]} #{case_id}: {actual}; T/T {raw}; hạn {due}. Cần tiếp tục lập và ký phiếu.')
        elif action=='asset_registered':
            serial=str(payload.get('serial','')).strip();model=str(payload.get('model','')).strip()
            raw=payload.get('warranty_months')
            if not serial or not model or raw is None or isinstance(raw,bool) or int(raw)!=float(raw) or not 0<=int(raw)<=120:
                raise ValueError('Cần model, SN duy nhất và số tháng bảo hành đúng điều khoản (0 nếu không bảo hành).')
            d=date.fromisoformat(actual);month=d.month-1+int(raw);year=d.year+month//12;month=month%12+1
            expiry=date(year,month,min(d.day,calendar.monthrange(year,month)[1])).isoformat()
            if c.execute('SELECT 1 FROM project_assets WHERE serial=?',(serial,)).fetchone():
                raise ValueError('SN đã tồn tại, không tạo trùng thiết bị.')
            c.execute('INSERT INTO project_assets(contract_id,case_id,model,serial,delivery_date,warranty_months,warranty_until,evidence_id) VALUES (?,?,?,?,?,?,?,?)',(co['id'],case_id,model,serial,actual,int(raw),expiry,ev['id']))
        elif action=='warranty_scope':
            asset=c.execute('SELECT * FROM project_assets WHERE id=? AND contract_id=?',(int(payload.get('asset_id') or 0),co['id'])).fetchone()
            if not asset or payload.get('scope') not in ('FREE','CHARGEABLE','PENDING'):
                raise ValueError('Chọn thiết bị đúng hợp đồng và kết luận miễn phí/có phí/chờ xác nhận theo bằng chứng.')
            if payload['scope']=='CHARGEABLE':
                _next(c,'quotation','Báo giá sửa chữa '+asset['model']+' / '+asset['serial'],co,fid)
        elif action=='warranty_returned':
            scope=c.execute("SELECT payload FROM project_facts WHERE case_id=? AND action='warranty_scope'",(case_id,)).fetchone()
            if not scope or json.loads(scope[0])['scope']=='PENDING':
                raise ValueError('Chưa có phương án bảo hành được xác nhận.')
            if json.loads(scope[0])['scope']=='CHARGEABLE':
                approved=c.execute('''SELECT 1 FROM project_facts approval JOIN workflow_cases q ON q.id=approval.case_id
                  JOIN project_facts scope ON scope.id=q.source_id
                  WHERE approval.action='quotation_approved' AND q.source_type='project_fact'
                  AND scope.case_id=? AND scope.action='warranty_scope' ''',(case_id,)).fetchone()
                if not approved:
                    raise ValueError('Sửa có phí cần báo giá được khách chấp thuận trước khi xác nhận giao trả.')
            # No sales invoice, cash receipt or extension of warranty is inferred.
        next_stage={'quotation_approved':5,'contract_signed':4,'customer_delivered':3,'acceptance_recorded':4,
                    'acceptance_confirmed':4,'warranty_scope':2,'warranty_returned':6}.get(action)
        if action=='supplier_received':
            next_stage=6 if full else 5
        if next_stage is not None:
            c.execute('UPDATE workflow_cases SET stage=MAX(stage,?),updated_at=CURRENT_TIMESTAMP WHERE id=?',(next_stage,case_id))
        work.event(c,case_id,'business_confirmed',actor,ACTIONS[action][2]+f' ngày {actual}: '+note)
    return context(case_id)


def documents(case_id):
    data=work.get_case(case_id)
    with work.connection() as c:
        return [dict(r) for r in c.execute("SELECT id,doc_name,file_name,doc_type FROM documents WHERE contract_code=? AND doc_type<>'WORKFLOW' ORDER BY id DESC",(data['contract_code'],))] if data['contract_code'] else []


def import_document(case_id,payload):
    choices={r['id'] for r in documents(case_id)}
    docid=int(payload.get('document_id') or 0)
    if docid not in choices:
        raise ValueError('Tệp không thuộc đúng mã tham chiếu của công việc.')
    with work.connection() as c:
        doc=c.execute('SELECT * FROM documents WHERE id=?',(docid,)).fetchone()
    path=Path(doc['file_path']).resolve()
    from app import database
    if not path.is_relative_to(Path(database.WORKING_DIR).resolve()) or not path.is_file() or path.stat().st_size>25*1024*1024:
        raise ValueError('Tệp nguồn không còn trong kho hợp lệ hoặc quá 25 MB.')
    work.add_file(case_id,path.name,path.read_bytes(),str(payload.get('role','draft')),str(payload.get('verified_by','')))
    return work.get_case(case_id)
