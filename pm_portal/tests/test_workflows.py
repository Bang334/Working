"""Workflow invariants: no invented signatures, mail delivery or cash receipts."""
from pathlib import Path
from contextlib import contextmanager
import pytest
from app import database
from app.services import workflow_service as work
from app.services import workflow_outlook_service as outlook


@pytest.fixture
def case(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'test.db')
    monkeypatch.setattr(database,'WORKING_DIR',tmp_path)
    monkeypatch.setattr(work,'FILES_DIR',tmp_path/'files')
    database.init_db()
    work.init_schema()
    with database.get_db_connection() as c:
        c.execute('INSERT INTO contracts(contract_code,customer_name_vi,total_amount,currency) VALUES (?,?,?,?)',('QA-1','Khách kiểm thử',1000,'VND'))
        cid=c.execute("SELECT id FROM contracts WHERE contract_code='QA-1'").fetchone()[0]
        c.execute("INSERT INTO payment_milestones(contract_id,contract_code,milestone_name,amount,percentage,status,triggered) VALUES (?,?,?,?,?,'PENDING',0)",(cid,'QA-1','Đợt kiểm thử',1000,100))
    return work.list_cases()[0]


def file(case,role,verified='Kế toán QA'):
    return work.add_file(case['id'],role+'.pdf',b'%PDF-1.4\nworkflow QA',role,verified)


def ready(case):
    cid=case['id']
    file(case,'condition')
    work.confirm_condition(cid,{'actor':'PM QA','trigger_date':work.today().isoformat(),'term_days':0})
    work.advance(cid,0,'PM QA','Đã soát điều kiện')
    file(case,'draft')
    work.advance(cid,1,'PM QA','Đã kiểm tra bản in')
    work.advance(cid,2,'PM QA','Sếp đã ký, nhận lại hồ sơ')
    file(case,'signed_request')
    work.advance(cid,3,'PM QA','Đã kiểm tra scan')
    text=work.email_text(cid)
    work.update_case(cid,dict(text,recipient='qa@example.com'))
    return work.get_case(cid)


def collection(case):
    c=ready(case);cid=c['id']
    work.advance(cid,4,'PM QA','Tạo nháp và kiểm tra')
    work.record_mail(cid,'sent-evidence','sent','QA',actor='PM QA')
    work.advance(cid,5,'PM QA','Đã đối chiếu thư gửi')
    work.record_mail(cid,'reply-evidence','inbox','Khách xác nhận hồ sơ',actor='PM QA')
    work.advance(cid,6,'PM QA','Khách xác nhận đủ hồ sơ')
    return work.get_case(cid)


def test_schema_idempotent_and_sync_does_not_invent_progress(case):
    work.init_schema();work.sync_milestones()
    rows=work.list_cases()
    assert len(rows)==1
    assert rows[0]['stage']==0 and rows[0]['due_date']==''
    assert rows[0]['files']==[] and rows[0]['mail']==[]


def test_condition_requires_evidence_and_respects_zero_day_term(case):
    payload={'actor':'QA','trigger_date':work.today().isoformat(),'term_days':0}
    with pytest.raises(ValueError):work.confirm_condition(case['id'],payload)
    file(case,'condition');result=work.confirm_condition(case['id'],payload)
    assert result['due_date']==work.today().isoformat()
    assert result['milestone']['payment_term_days']==0


def test_cannot_advance_without_document_or_actor(case):
    with pytest.raises(ValueError):work.advance(case['id'],0,'QA','Đã xem')
    with pytest.raises(ValueError):work.advance(case['id'],0,'','')


def test_signed_scan_requires_human_verification(case):
    with pytest.raises(ValueError):file(case,'signed_request','')
    with pytest.raises(ValueError):work.add_file(case['id'],'signed.docx',b'PKdoc','signed_request','QA')


def test_stale_page_cannot_skip_stage(case):
    ready(case)
    with pytest.raises(ValueError):work.advance(case['id'],0,'QA','stale')


def test_sample_email_has_no_invented_signature_bank_or_due_date(case):
    text=work.email_text(case['id'])
    assert 'đã ký' not in text['body']
    assert '0011004123456' not in text['body']
    assert 'Chưa xác nhận' in text['body']


def test_send_requires_real_verified_documents_and_recipient(case):
    with pytest.raises(ValueError):work.validate_email(work.get_case(case['id']))
    c=ready(case)
    assert len(work.validate_email(c))==1
    work.update_case(c['id'],{'needs_acceptance':True})
    with pytest.raises(ValueError):work.validate_email(work.get_case(c['id']))
    file(case,'acceptance')
    assert len(work.validate_email(work.get_case(c['id'])))==2


def test_modified_attachment_is_rejected(case):
    c=ready(case)
    f=next(f for f in c['files'] if f['role']=='signed_request')
    Path(f['path']).write_bytes(b'%PDF changed after review')
    with pytest.raises(ValueError,match='thay đổi'):work.validate_email(work.get_case(c['id']))


def test_draft_is_not_sent_evidence(case):
    c=ready(case);cid=c['id']
    work.advance(cid,4,'QA','đã soạn')
    work.record_mail(cid,'draft-id','draft','QA',actor='QA')
    with pytest.raises(ValueError,match='gửi thật'):work.advance(cid,5,'QA','chưa gửi')


def test_partial_receipts_preserve_obligation_and_prevent_duplicate(case):
    c=collection(case);fid=file(case,'payment_evidence')
    payload={'actor':'Kế toán QA','amount':400,'reference':'BANK-1','evidence_id':fid,'paid_date':work.today().isoformat()}
    result=work.add_receipt(c['id'],payload)
    assert result['remaining']==600 and result['current']['key']=='receipt'
    assert result['milestone']['amount']==1000 and result['milestone']['status']!='PAID'
    with pytest.raises(ValueError,match='ghi nhận'):work.add_receipt(c['id'],payload)
    with pytest.raises(ValueError,match='Vượt'):work.add_receipt(c['id'],dict(payload,reference='BANK-2',amount=601))
    result=work.add_receipt(c['id'],dict(payload,reference='BANK-2',amount=600))
    assert result['remaining']==0 and result['current'] is None
    assert result['milestone']['status']=='PAID' and result['milestone']['amount']==1000
    with database.get_db_connection() as db:
        assert db.execute("SELECT paid_amount FROM contracts WHERE contract_code='QA-1'").fetchone()[0]==1000
    with pytest.raises(ValueError):database.unmark_milestone_paid(result['milestone_id'])


def test_receipt_requires_evidence_from_same_case(case):
    c=collection(case)
    other=work.create_case({'kind':'warranty','title':'Other'})
    wrong=file(other,'payment_evidence')
    with pytest.raises(ValueError):work.add_receipt(c['id'],{'actor':'QA','amount':1,'reference':'X','evidence_id':wrong,'paid_date':work.today().isoformat()})


def test_receipt_cannot_be_recorded_before_workflow_checks(case):
    with pytest.raises(ValueError):work.add_receipt(case['id'],{})


def test_upload_containment_and_actual_format(case):
    with pytest.raises(ValueError):work.safe_path('../outside.pdf')
    with pytest.raises(ValueError):work.add_file(case['id'],'bad.pdf',b'not a pdf','evidence')
    with pytest.raises(ValueError):work.add_file(case['id'],'bad.exe',b'%PDF','evidence')
    fid=work.add_file(case['id'],'../../valid.pdf',b'%PDF-1.4','evidence')
    saved=next(f for f in work.get_case(case['id'])['files'] if f['id']==fid)
    assert saved['name']=='valid.pdf' and work.safe_path(saved['path']).is_file()


def test_all_operational_templates_and_reopen_keep_audit(case):
    for kind in work.TEMPLATES:
        if kind=='payment':continue
        row=work.create_case({'kind':kind,'title':'QA '+kind})
        assert row['current']['instruction'] and len(row['steps'])>=5
    c=ready(case)
    result=work.reopen(c['id'],'QA','Khách yêu cầu bổ sung scan')
    assert result['stage']==3 and result['events'][0]['action']=='reopened'
    assert result['files']


def test_outlook_draft_attaches_real_files_and_never_calls_send(case,monkeypatch):
    c=ready(case)
    class Mail:
        EntryID='OUTLOOK-DRAFT-QA'
        def __init__(self):self.UserProperties=self;self.Attachments=self;self.files=[];self.saved=False
        def Add(self,*args,**kwargs):
            if args[0]=='HongMingWorkflowCase':return type('Prop',(),{})()
            assert Path(args[0]).is_file();self.files.append(args[0])
        def Save(self):self.saved=True
        def Send(self):raise AssertionError('Must never send email')
    mail=Mail()
    @contextmanager
    def fake():yield type('App',(),{'CreateItem':lambda self,n:mail})()
    monkeypatch.setattr(outlook,'outlook',fake)
    outlook.create_draft(c['id'],'QA')
    assert mail.saved and len(mail.files)==1
    assert work.get_case(c['id'])['mail'][0]['direction']=='draft'


def test_legacy_amount_override_rejected(case):
    with pytest.raises(ValueError):database.mark_milestone_paid(case['milestone_id'],actual_amount=1)


def test_source_link_is_real_idempotent_and_cannot_cross_types(case):
    source=next(s for s in work.sources() if s['source_type']=='contract')
    payload=dict(source,title='ignored input')
    first=work.create_case(payload);second=work.create_case(payload)
    assert first['id']==second['id']
    assert first['contract_code']=='QA-1' and first['source_id']==source['source_id']
    with pytest.raises(ValueError):work.create_case(dict(payload,source_id=99999))


def test_outlook_matches_exact_contract_in_body_but_not_similar_code(case,monkeypatch):
    class Items:
        Count=2
        def Sort(self,*args):pass
        def Item(self,i):
            return type('Mail',(),dict(Class=43,Subject='Thu khong co ma',Body='Can cu QA-1' if i==1 else 'Can cu QA-10',
                UserProperties=type('Props',(),{'Find':lambda self,n:None})(),EntryID=str(i),
                SenderEmailAddress='qa@example.com',SentOn='2026-10-29',ReceivedTime='2026-10-29',
                Attachments=type('Attachments',(),{'Count':0})()))()
    class App:
        def GetNamespace(self,name):return self
        def GetDefaultFolder(self,id):return type('Folder',(),{'Items':Items()})()
    @contextmanager
    def fake():yield App()
    monkeypatch.setattr(outlook,'outlook',fake)
    found=outlook.candidates(case['id'])
    assert len(found)==2 and all(m['entry_id']=='1' and m['match']=='contract_body' for m in found)
    assert work.get_case(case['id'])['mail']==[]  # Reading does not assert receipt/sending.


def test_followup_draft_does_not_require_bank_evidence(case):
    c=collection(case)
    assert not work.has_file(c,'payment_evidence')
    assert work.validate_email(c)


@pytest.mark.anyio
async def test_workflow_api_validation_and_page(case):
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        assert (await client.get('/workflows')).status_code==200
        response=await client.post('/api/workflows',json={'kind':'bad','title':'bad'})
        assert response.status_code==400
        response=await client.post(f'/api/workflows/{case["id"]}/advance',json={'stage':0,'actor':'QA','note':'No evidence'})
        assert response.status_code==400
        response=await client.get('/api/emails/load-context',params={'source':'milestone','id':999999})
        assert response.status_code==404
        response=await client.post(f'/api/v1/dossier/milestones/{case["milestone_id"]}/mark-paid',json={})
        assert response.status_code==409
        response=await client.get('/api/emails/load-context',params={'source':'milestone','id':case['milestone_id']})
        assert response.status_code==200
        assert response.json()['data']['attachments']==[]
        assert 'đã ký' not in response.json()['data']['body']


@pytest.fixture
def anyio_backend():return 'asyncio'


@pytest.mark.anyio
async def test_generate_payment_request_uses_real_forms_in_temporary_output(case,tmp_path,monkeypatch):
    import httpx
    import openpyxl
    from app.main import app
    from app.services import payment_request_excel_service as generator
    output=tmp_path/'generated';output.mkdir()
    monkeypatch.setattr(generator,'OUTPUT_DIR',output)
    file(case,'condition')
    work.confirm_condition(case['id'],{'actor':'QA','trigger_date':work.today().isoformat(),'term_days':0})
    work.advance(case['id'],0,'QA','Căn cứ kiểm thử')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post(f'/api/workflows/{case["id"]}/generate-request',json={'actor':'QA'})
    assert response.status_code==200,response.text
    data=response.json()
    assert len([f for f in data['files'] if f['role']=='draft'])==2
    assert any(f['role']=='condition' for f in data['files'])
    generated=next(f for f in data['files'] if f['name'].endswith('.xlsx'))
    sheet=openpyxl.load_workbook(generated['path'],data_only=False).active
    assert sheet['C10'].value=='Khách kiểm thử'
    assert work.get_case(case['id'])['stage']==1


def insert_ar(case,received=1000,code='QA-1',gross=1000,paid_date=None,status='PAID'):
    day=paid_date or work.today().isoformat()
    with database.get_db_connection() as c:
        row=c.execute('''INSERT INTO project_receivables(project_name,customer_name,contract_code,
            total_contract_amount,net_amount,gross_amount,received_amount,remaining_debt,
            paid_date,collection_status,linked_milestone_id)
            VALUES ('QA AR','QA',?,1000,?,?,?, ?,?,?,?)''',
            (code,gross,gross,received,max(0,gross-received),day,status,case['milestone_id']))
        return row.lastrowid


def test_existing_ar_paid_closes_workflow_and_reconciles_contract_without_fake_receipts(case):
    insert_ar(case)
    result=work.list_cases()[0]
    assert result['current'] is None and result['remaining']==0
    assert result['received']==1000 and result['inherited_paid']
    assert result['payment_source']=='Công nợ đã nhập' and result['receipts']==[]
    with database.get_db_connection() as c:
        assert c.execute("SELECT paid_amount FROM contracts WHERE contract_code='QA-1'").fetchone()[0]==1000
    work.list_cases()
    assert work.get_case(case['id'])['received']==1000


@pytest.mark.parametrize('code,gross',[('OTHER-CONTRACT',1000),('QA-1',999)])
def test_ar_must_match_explicit_link_contract_and_amount(case,code,gross):
    insert_ar(case,received=gross,code=code,gross=gross)
    assert work.list_cases()[0]['current'] is not None


def test_future_paid_date_does_not_turn_forecast_into_actual_cash(case):
    from datetime import timedelta
    insert_ar(case,paid_date=(work.today()+timedelta(days=3)).isoformat())
    result=work.list_cases()[0]
    assert result['current'] is not None and result['received']==0


def test_partial_opening_ar_is_preserved_when_recording_balance_in_workflow(case):
    insert_ar(case,received=400,status='PENDING')
    assert work.list_cases()[0]['received']==400
    c=collection(case);evidence=file(case,'payment_evidence')
    result=work.add_receipt(c['id'],dict(actor='Kế toán QA',amount=600,reference='BALANCE',evidence_id=evidence,paid_date=work.today().isoformat()))
    assert result['current'] is None and result['received']==1000 and result['remaining']==0
    with database.get_db_connection() as db:
        ar=db.execute('SELECT received_amount,remaining_debt,collection_status FROM project_receivables').fetchone()
        assert tuple(ar)==(1000,0,'PAID')
        assert db.execute('SELECT paid_amount FROM contracts').fetchone()[0]==1000


def test_ar_manual_update_synchronizes_without_using_date_alone(case):
    from app.services.receivables_service import update_receivable
    ar_id=insert_ar(case,received=0,status='PENDING')
    assert update_receivable(ar_id,dict(paid_date=work.today().isoformat(),received_amount=1000,collection_status='PAID'))
    assert work.list_cases()[0]['current'] is None
