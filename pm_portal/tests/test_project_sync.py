"""Cross-module transitions use isolated data; never Outlook.Send or real forms."""
import pytest
from app import database
from app.services import workflow_service as w, project_sync_service as p


@pytest.fixture
def env(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DB_PATH',tmp_path/'qa.db')
    monkeypatch.setattr(database,'WORKING_DIR',tmp_path)
    monkeypatch.setattr(w,'FILES_DIR',tmp_path/'files')
    database.init_db();w.init_schema();p.init_schema()
    with w.connection() as c:
        cid=c.execute("INSERT INTO contracts(contract_code,customer_name_vi,total_amount,currency) VALUES ('QA-SYNC','QA',1000,'VND')").lastrowid
        mid=c.execute("INSERT INTO payment_milestones(contract_id,contract_code,milestone_name,amount,percentage,status,triggered) VALUES (?,'QA-SYNC','FAC',1000,100,'PENDING',0)",(cid,)).lastrowid
    w.sync_milestones()
    return cid,mid


def case(env,kind):
    d=w.create_case(dict(kind=kind,title='QA '+kind))
    p.link(d['id'],dict(contract_id=env[0],actor='QA'))
    return d


def payload(d,action,role,**kw):
    fid=w.add_file(d['id'],'proof.pdf',b'%PDF-1.4\nQA',role,'QA')
    return dict(action=action,actual_date='2026-10-20',evidence_id=fid,actor='QA',note='Đã đối chiếu bản ký và phạm vi',**kw)


def test_acceptance_activates_only_selected_milestone_and_attaches_proof(env):
    d=case(env,'acceptance');x=payload(d,'acceptance_confirmed','acceptance',milestone_id=env[1],term_days=10)
    p.confirm(d['id'],x);p.confirm(d['id'],x)
    pay=next(r for r in w.list_cases() if r['milestone_id']==env[1])
    assert pay['due_date']=='2026-10-30' and pay['stage']==0
    assert {f['role'] for f in pay['files']}=={'acceptance','condition'}
    assert len(p.context(d['id'])['facts'])==1
    with w.connection() as c: assert c.execute('SELECT paid_amount FROM contracts WHERE id=?',(env[0],)).fetchone()[0]==0


def test_wrong_milestone_rolls_back_fact(env):
    d=case(env,'acceptance');x=payload(d,'acceptance_confirmed','acceptance',milestone_id=9999,term_days=0)
    with pytest.raises(ValueError):p.confirm(d['id'],x)
    assert p.context(d['id'])['facts']==[]


def test_acceptance_does_not_overwrite_prior_condition(env):
    with w.connection() as c:c.execute("UPDATE payment_milestones SET triggered=1,trigger_date='2026-10-01',payment_term_days=0 WHERE id=?",(env[1],))
    d=case(env,'acceptance')
    with pytest.raises(ValueError):p.confirm(d['id'],payload(d,'acceptance_confirmed','acceptance',milestone_id=env[1],term_days=10))


def test_quote_approval_does_not_sign_contract_or_order(env):
    d=case(env,'quotation');x=payload(d,'quotation_approved','customer_confirmation')
    p.confirm(d['id'],x);p.confirm(d['id'],x)
    with w.connection() as c:
        children=c.execute("SELECT * FROM workflow_cases WHERE source_type='project_fact'").fetchall()
        assert len(children)==1 and children[0]['kind']=='contract' and children[0]['stage']==0
        assert c.execute('SELECT count(*) FROM procurement_orders').fetchone()[0]==0


def test_receipt_partial_and_full_updates_po_not_customer_payment(env):
    with w.connection() as c:
        oid=c.execute("INSERT INTO procurement_orders(project_name,item_name,supplier_name,quantity,delivery_status) VALUES ('QA','Pin','NCC',4,'PENDING')").lastrowid
    p.sync_sources()
    with w.connection() as c: row=dict(c.execute("SELECT * FROM workflow_cases WHERE source_type='po' AND source_id=?",(oid,)).fetchone())
    p.link(row['id'],dict(contract_id=env[0],actor='QA'))
    x=payload(row,'supplier_received','delivery',quantity=1);p.confirm(row['id'],x);p.confirm(row['id'],x)
    with w.connection() as c: assert c.execute('SELECT delivery_status FROM procurement_orders WHERE id=?',(oid,)).fetchone()[0]=='PARTIAL'
    with pytest.raises(ValueError):p.confirm(row['id'],dict(x,quantity=2))
    p.confirm(row['id'],payload(row,'supplier_received','delivery',quantity=3))
    with w.connection() as c:
        assert c.execute('SELECT delivery_status FROM procurement_orders WHERE id=?',(oid,)).fetchone()[0]=='DELIVERED'
        assert c.execute('SELECT triggered FROM payment_milestones WHERE id=?',(env[1],)).fetchone()[0]==0
    with pytest.raises(ValueError):p.confirm(row['id'],payload(row,'supplier_received','delivery',quantity=1))


def test_asset_uses_explicit_six_month_warranty_and_unique_sn(env):
    d=case(env,'delivery');x=payload(d,'asset_registered','delivery',model='BAT-RFR900',serial='QA-SN',warranty_months=6)
    x['actual_date']='2026-08-31';p.confirm(d['id'],x)
    asset=p.context(d['id'])['assets'][0]
    assert asset['warranty_until']=='2027-02-28'
    with pytest.raises(ValueError):p.confirm(d['id'],payload(d,'asset_registered','delivery',model='BAT-RFR900',serial='QA-SN',warranty_months=6))


def test_warranty_charged_creates_quote_and_requires_approval_before_return(env):
    delivery=case(env,'delivery');p.confirm(delivery['id'],payload(delivery,'asset_registered','delivery',model='BAT',serial='QA-SN2',warranty_months=6))
    asset=p.context(delivery['id'])['assets'][0]
    d=case(env,'warranty');p.confirm(d['id'],payload(d,'warranty_scope','customer_confirmation',asset_id=asset['id'],scope='CHARGEABLE'))
    ret=payload(d,'warranty_returned','delivery')
    with pytest.raises(ValueError):p.confirm(d['id'],ret)
    with w.connection() as c:q=dict(c.execute("SELECT * FROM workflow_cases WHERE kind='quotation' AND source_type='project_fact'").fetchone())
    p.confirm(q['id'],payload(q,'quotation_approved','customer_confirmation'))
    p.confirm(d['id'],ret)
    assert p.context(d['id'])['assets'][0]['warranty_until']==asset['warranty_until']


def test_confirm_rejects_missing_link_wrong_role_and_modified_evidence(env):
    d=w.create_case(dict(kind='contract',title='QA'));x=payload(d,'contract_signed','signed_contract')
    with pytest.raises(ValueError):p.confirm(d['id'],x)
    p.link(d['id'],dict(contract_id=env[0],actor='QA'))
    with w.connection() as c:path=c.execute('SELECT path FROM workflow_files WHERE id=?',(x['evidence_id'],)).fetchone()[0]
    w.safe_path(path).write_bytes(b'%PDF-1.4 changed')
    with pytest.raises(ValueError):p.confirm(d['id'],x)


def test_source_refresh_idempotent_and_inherited_po_does_not_reorder(env):
    with w.connection() as c:oid=c.execute("INSERT INTO procurement_orders(project_name,item_name,supplier_name,quantity,delivery_status,actual_delivery_date) VALUES ('QA','Pin','NCC',4,'DELIVERED','2026-10-20')").lastrowid
    p.sync_sources();p.sync_sources()
    with w.connection() as c: rows=c.execute("SELECT * FROM workflow_cases WHERE source_type='po' AND source_id=?",(oid,)).fetchall()
    assert len(rows)==1 and rows[0]['stage']==5
    assert p.context(rows[0]['id'])['facts']==[]


def test_different_email_contents_per_kind(env):
    texts=[w.email_text(case(env,k)['id'])['body'] for k in ('quotation','contract','procurement','delivery','acceptance','warranty')]
    assert len(set(texts))==6
    assert 'SN' in texts[-1] and 'ký xác nhận' in texts[0]


def test_quote_can_be_approved_before_contract_exists(env):
    d=w.create_case(dict(kind='quotation',title='Báo giá mới',customer='Khách mới'))
    p.confirm(d['id'],payload(d,'quotation_approved','customer_confirmation'))
    with w.connection() as c:
        child=c.execute("SELECT * FROM workflow_cases WHERE kind='contract' AND source_type='project_fact'").fetchone()
        assert child and child['contract_code']==''
        assert c.execute('SELECT count(*) FROM contracts').fetchone()[0]==1


def test_delivery_based_term_uses_own_proof_without_inventing_acceptance(env):
    d=case(env,'delivery')
    p.confirm(d['id'],payload(d,'delivery_payment_condition','delivery',milestone_id=env[1],term_days=10))
    pay=next(r for r in w.list_cases() if r['milestone_id']==env[1])
    assert pay['due_date']=='2026-10-30'
    assert {f['role'] for f in pay['files']}=={'condition'}
    assert not pay['needs_acceptance'] and pay['received']==0


def test_acceptance_record_without_payment_trigger(env):
    d=case(env,'acceptance');p.confirm(d['id'],payload(d,'acceptance_recorded','acceptance'))
    with w.connection() as c:assert c.execute('SELECT triggered FROM payment_milestones WHERE id=?',(env[1],)).fetchone()[0]==0
    assert w.get_case(d['id'])['stage']==4
