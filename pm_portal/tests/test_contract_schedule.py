"""Contract schedule changes use isolated SQLite data, never the live ledger."""
import sqlite3
import pytest
from app.services import contract_schedule_service as service


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / 'test.db'
    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    monkeypatch.setattr(service, 'get_db_connection', connect)
    conn = connect()
    conn.executescript('''
        CREATE TABLE project_receivables (
          id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, project_group TEXT,
          customer_name TEXT, contract_code TEXT, total_contract_amount REAL,
          net_amount REAL, vat_rate REAL, vat_amount REAL, gross_amount REAL,
          received_amount REAL, remaining_debt REAL, collection_status TEXT,
          paid_date TEXT, due_date TEXT, customer_promised_date TEXT,
          doc_status TEXT, notes TEXT, installment_order INTEGER,
          linked_milestone_id INTEGER, paid_by_date TEXT, payment_basis TEXT,
          updated_at TEXT);
        CREATE TABLE receivables_weekly_snapshots(receivable_id INTEGER);
        CREATE TABLE payment_milestones(id INTEGER PRIMARY KEY, contract_id INTEGER,
          contract_code TEXT, milestone_name TEXT, percentage REAL, amount REAL,
          due_date TEXT, paid_date TEXT, status TEXT, status_label TEXT);
        CREATE TABLE contracts(id INTEGER PRIMARY KEY,total_amount REAL,paid_amount REAL,updated_at TEXT);
        INSERT INTO project_receivables VALUES
          (1,'Cọc','MES','KH','HD1',1000,300,0.08,24,324,324,0,'PAID',NULL,NULL,NULL,'INV','ghi chú',1,NULL,'2026-10-01','history',NULL),
          (2,'Còn lại','MES','KH','HD1',1000,700,0.08,56,756,0,756,'PENDING',NULL,NULL,NULL,'','ghi chú',2,NULL,NULL,NULL,NULL),
          (3,'Dự án khác','IT','KH','HD1',999,999,0,0,999,0,999,'PENDING',NULL,NULL,NULL,'','riêng',1,NULL,NULL,NULL,NULL);
    ''')
    conn.commit();conn.close()
    return connect


def draft(item_id=1):
    data=service.get_contract_schedule(item_id)
    return dict(revision=data['revision'],total_amount=1000,project_name='MES',notes='Chung',
        installments=[dict(id=1,name='Cọc',percentage=30,vat_rate=.08,received_amount=324,collection_status='PAID'),
                      dict(id=2,name='Còn lại',percentage=70,vat_rate=.08,received_amount=0,collection_status='PENDING')])


def test_atomic_allocation_preserves_cash_and_other_project(ledger):
    payload=draft();payload['total_amount']=2000
    payload['installments'][0]['collection_status']='PARTIAL'
    result=service.save_contract_schedule(1,payload)
    assert [r['net_amount'] for r in result['rows']]==[600,1400]
    assert result['rows'][0]['received_amount']==324
    assert result['rows'][0]['paid_by_date']=='2026-10-01'
    assert service.get_contract_schedule(3)['rows'][0]['net_amount']==999


def test_add_remove_and_rounding(ledger):
    payload=draft();payload['total_amount']=1001
    payload['installments'][0].update(percentage=40,collection_status='PARTIAL')
    payload['installments'][1]['percentage']=30
    payload['installments'].append(dict(id=None,percentage=30,received_amount=0,vat_rate=.08))
    saved=service.save_contract_schedule(1,payload)
    assert sum(r['net_amount'] for r in saved['rows'])==1001
    assert len(saved['rows'])==3
    payload['revision']=saved['revision']
    payload['installments']=payload['installments'][:2]
    payload['installments'][1]['percentage']=60
    assert len(service.save_contract_schedule(1,payload)['rows'])==2


@pytest.mark.parametrize('change', ['percent','received','stale','foreign','duplicate','remove_paid'])
def test_invalid_edits_rollback(ledger,change):
    payload=draft()
    if change=='percent':payload['installments'][1]['percentage']=60
    if change=='received':payload['installments'][0]['received_amount']=9999
    if change=='stale':payload['revision']='stale'
    if change=='foreign':payload['installments'][1]['id']=3
    if change=='duplicate':payload['installments'][1]['id']=1
    if change=='remove_paid':payload['installments']=[dict(id=2,percentage=100)]
    before=service.get_contract_schedule(1)
    with pytest.raises(ValueError):service.save_contract_schedule(1,payload)
    assert service.get_contract_schedule(1)==before


def test_status_partial_and_shared_note(ledger):
    payload=draft();payload['installments'][1].update(received_amount=100,collection_status='PARTIAL')
    result=service.save_contract_schedule(1,payload)
    assert result['rows'][1]['remaining_debt']==656
    assert {r['notes'] for r in result['rows']}=={'Chung'}


def test_snapshot_protects_removal(ledger):
    conn=ledger();conn.execute('INSERT INTO receivables_weekly_snapshots VALUES (2)');conn.commit();conn.close()
    payload=draft();payload['installments']=payload['installments'][:1]
    payload['installments'][0].update(percentage=100,collection_status='PARTIAL')
    with pytest.raises(ValueError, match='chốt tuần'):service.save_contract_schedule(1,payload)


def test_linked_milestones_follow_new_allocations(ledger):
    conn=ledger()
    conn.executescript('''INSERT INTO contracts VALUES(10,1000,324,NULL);
      INSERT INTO payment_milestones(id,contract_id,contract_code,amount) VALUES(20,10,'HD1',324);
      UPDATE project_receivables SET linked_milestone_id=20 WHERE id=1;''')
    conn.commit();conn.close()
    payload=draft();payload['installments'][0].update(percentage=40,collection_status='PARTIAL')
    payload['installments'][1]['percentage']=30
    payload['installments'].append(dict(id=None,percentage=30,received_amount=0,vat_rate=.08))
    result=service.save_contract_schedule(1,payload)
    conn=ledger()
    assert conn.execute('SELECT amount FROM payment_milestones WHERE id=20').fetchone()[0]==432
    assert result['rows'][2]['linked_milestone_id'] is not None
    conn.close()


def test_api_save_round_trip(ledger):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.controllers.receivables_controller import router
    app=FastAPI();app.include_router(router)
    with TestClient(app) as client:
        response=client.get('/api/v1/receivables/contract-schedule/1')
        assert response.status_code==200
        payload=draft();payload['notes']='Ghi chú từ cửa sổ hợp đồng'
        response=client.put('/api/v1/receivables/contract-schedule/1',json=payload)
        assert response.status_code==200
        assert response.json()['rows'][0]['notes']==payload['notes']
        assert client.put('/api/v1/receivables/contract-schedule/1',json=payload).status_code==400


def test_contract_vat_overrides_all_installment_rates(ledger):
    payload=draft();payload['vat_rate']=0.1
    payload['installments'][0]['collection_status']='PARTIAL'
    payload['installments'][1]['vat_rate']=0
    saved=service.save_contract_schedule(1,payload)
    assert [r['vat_rate'] for r in saved['rows']]==[0.1,0.1]
    assert sum(r['gross_amount'] for r in saved['rows'])==1100
    assert saved['rows'][0]['received_amount']==324


def test_mixed_installment_vat_without_contract_rate_is_rejected(ledger):
    payload=draft();payload['installments'][1]['vat_rate']=0.1
    with pytest.raises(ValueError,match='VAT'):
        service.save_contract_schedule(1,payload)
