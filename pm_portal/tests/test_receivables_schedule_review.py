import sqlite3
from copy import deepcopy

from app.services import receivables_service as ar


def comparison(monkeypatch, items):
    monkeypatch.setattr(ar,'list_receivables',lambda **kwargs:deepcopy(items))
    def connection():
        c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
        c.execute('CREATE TABLE receivables_weekly_snapshots (snapshot_date TEXT)')
        return c
    monkeypatch.setattr(ar,'get_db_connection',connection)
    return ar.get_weekly_comparison_data(prev_date='2026-10-25',curr_date='2026-11-01')['contracts_comparison']


def item(id, pct, received=0, **kwargs):
    return dict(id=id,contract_code='REVIEW-1',customer_name='A',project_name=f'{pct}% Project',
        total_contract_amount=1000,net_amount=pct*10,vat_rate=0,gross_amount=pct*10,
        received_amount=received,remaining_debt=pct*10-received,**kwargs)


def test_paid_by_bound_does_not_fabricate_a_receipt_date():
    row=item(1,35,350,paid_date=None,paid_by_date='2026-08-29',collection_status='PAID')
    assert ar._reconstruct_item_state_at_date(row,'2026-10-25')['collection_status']=='PAID'
    assert ar._reconstruct_item_state_at_date(row,'2026-08-28')['received_amount']==0
    assert row['paid_date'] is None


def test_partial_receipt_is_not_full_paid():
    row=item(1,55,100,paid_date='2026-08-29')
    state=ar._reconstruct_item_state_at_date(row,'2026-10-25')
    assert state['received_amount']==100 and not state['is_paid']


def test_unstarted_installment_alone_does_not_need_attention(monkeypatch):
    co=comparison(monkeypatch,[item(1,100,collection_status='PENDING')])[0]
    assert co['has_unstarted_next']
    assert not co['has_change']
    assert not co['is_active_attention']


def test_complete_schedule_keeps_35_55_10_and_payment_colors(monkeypatch):
    items=[item(2,55,550,paid_date='2026-08-29',installment_order=2),
           item(3,10,installment_order=3),
           item(1,35,350,paid_by_date='2026-08-29',installment_order=1)]
    co=comparison(monkeypatch,items)[0]
    assert [s['width_pct'] for s in co['segments']]==[35,55,10]
    assert [s['curr_status'] for s in co['segments'][:2]]==['PAID','PAID']
    assert co['curr_pct_collected']==90 and co['curr_debt']==100
    assert co['schedule_complete']


def test_incomplete_schedule_is_not_stretched_to_100(monkeypatch):
    co=comparison(monkeypatch,[item(2,55,550,paid_date='2026-08-29'),item(3,10)])[0]
    assert [s['width_pct'] for s in co['segments']]==[35,55,10]
    assert co['segments'][0]['is_missing_schedule']
    assert co['curr_pct_collected']==55 and co['curr_debt']==100
    assert not co['schedule_complete']


def test_distinct_projects_with_same_reference_stay_separate(monkeypatch):
    groups=comparison(monkeypatch,[item(1,10,project_group='Hardware'),item(2,10,project_group='Software')])
    assert len(groups)==2
    assert {g['project_title'] for g in groups}=={'Hardware','Software'}
    for g in groups:
        assert [s['width_pct'] for s in g['segments']]==[90,10]
        assert g['curr_received']==0 and g['curr_debt']==100


def test_sync_retains_reviewed_metadata(monkeypatch,tmp_path):
    path=tmp_path/'review.db';c=sqlite3.connect(path)
    c.executescript('''CREATE TABLE contracts (id INTEGER,contract_code TEXT,customer_name_vi TEXT,project_name_vi TEXT,total_amount REAL);
      CREATE TABLE payment_milestones (id INTEGER,contract_code TEXT,milestone_name TEXT,percentage REAL,amount REAL,trigger_condition TEXT,due_date TEXT,paid_date TEXT,invoice_no TEXT,status TEXT);
      CREATE TABLE project_receivables (id INTEGER,linked_milestone_id INTEGER,project_group TEXT,paid_by_date TEXT,installment_order INTEGER,notes TEXT);
      INSERT INTO contracts VALUES (1,'A','Customer','Project',1000);
      INSERT INTO payment_milestones VALUES (1,'A','Advance',35,350,'Condition',NULL,NULL,NULL,'PAID');
      INSERT INTO project_receivables VALUES (1,1,'Hardware','2026-08-29',1,'Reviewed');''')
    c.commit();c.close()
    def connection():
        c=sqlite3.connect(path);c.row_factory=sqlite3.Row;return c
    monkeypatch.setattr(ar,'get_db_connection',connection)
    assert ar.sync_from_existing_contracts(clear_first=True)==0
    c=connection();row=dict(c.execute('SELECT * FROM project_receivables').fetchone());c.close()
    assert row['paid_by_date']=='2026-08-29' and row['project_group']=='Hardware' and row['notes']=='Reviewed'
