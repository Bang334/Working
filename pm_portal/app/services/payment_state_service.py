"""Reconcile explicit AR/milestone links; never match by customer or percentage."""
import math
from datetime import datetime, timezone, timedelta


def past_date(value):
    for fmt in ('%Y-%m-%d','%d/%m/%Y'):
        try:
            day=datetime.strptime(str(value),fmt).date()
            return day.isoformat() if day<=datetime.now(timezone(timedelta(hours=7))).date() else ''
        except ValueError:
            pass
    return ''


def linked_ar(conn,milestone):
    rows=conn.execute('''SELECT a.* FROM project_receivables a JOIN contracts co ON co.id=?
        WHERE a.linked_milestone_id=? AND a.contract_code=? AND co.currency='VND'
        AND ABS(a.gross_amount-?)<0.01''',
        (milestone['contract_id'],milestone['id'],milestone['contract_code'],milestone['amount'])).fetchall()
    # Duplicate or mismatched rows require reconciliation, not automatic summation.
    if len(rows)!=1:
        return None
    row=dict(rows[0]);received=float(row['received_amount'] or 0)
    if not math.isfinite(received) or received<0 or received>float(milestone['amount'])+0.01:
        return None
    if received>0 and not past_date(row['paid_date']):
        return None
    return row


def ledger_total(conn,milestone_id):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='workflow_receipts'").fetchone():
        return 0
    return float(conn.execute('''SELECT COALESCE(SUM(r.amount),0) FROM workflow_receipts r
        JOIN workflow_cases w ON w.id=r.case_id WHERE w.milestone_id=?''',(milestone_id,)).fetchone()[0])


def received_for(conn,milestone):
    if milestone['status']=='PAID':
        return float(milestone['amount'])
    ar=linked_ar(conn,milestone)
    return max(ledger_total(conn,milestone['id']),float(ar['received_amount'] or 0) if ar else 0)


def contract_total(conn,contract_id):
    return sum(received_for(conn,dict(m)) for m in conn.execute('SELECT * FROM payment_milestones WHERE contract_id=?',(contract_id,)))


def apply_ar(conn,receivable_id,allow_unpay=False):
    row=conn.execute('''SELECT m.* FROM payment_milestones m JOIN project_receivables a
            ON a.linked_milestone_id=m.id WHERE a.id=?''',(receivable_id,)).fetchone()
    if not row:
        return False
    m=dict(row);ar=linked_ar(conn,m)
    if not ar or ar['id']!=receivable_id:
        return False
    full=ar['collection_status']=='PAID' and float(ar['received_amount'] or 0)>=float(m['amount']) and float(m['amount'])>0
    if full and m['status']=='PAID' and past_date(m['paid_date'])==past_date(ar['paid_date']):
        return False
    if full and past_date(ar['paid_date']):
        conn.execute("UPDATE payment_milestones SET status='PAID',status_label='Đã thu đủ',paid_date=?,action_required='Đã thu theo dữ liệu công nợ đã nhập' WHERE id=?",
                     (past_date(ar['paid_date']),m['id']))
    elif allow_unpay and not ledger_total(conn,m['id']):
        status='WAITING' if m['triggered'] else 'PENDING_TRIGGER'
        conn.execute("UPDATE payment_milestones SET status=?,status_label='Chờ thu / còn phải thu',paid_date=NULL WHERE id=?",(status,m['id']))
    else:
        return False
    total=contract_total(conn,m['contract_id'])
    conn.execute('UPDATE contracts SET paid_amount=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(total,m['contract_id']))
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name='workflow_cases'").fetchone():
        # Stage 8 is the end of the collection workflow. Other workflows are not changed.
        if full:
            conn.execute("UPDATE workflow_cases SET stage=8,updated_at=CURRENT_TIMESTAMP WHERE milestone_id=? AND kind='payment'",(m['id'],))
        elif allow_unpay and not ledger_total(conn,m['id']):
            conn.execute("UPDATE workflow_cases SET stage=0,updated_at=CURRENT_TIMESTAMP WHERE milestone_id=? AND kind='payment' AND stage>=8",(m['id'],))
    return m['status']!='PAID' and full


def reconcile_existing(conn):
    ids=[r[0] for r in conn.execute("SELECT id FROM project_receivables WHERE linked_milestone_id IS NOT NULL AND collection_status='PAID'")]
    return [i for i in ids if apply_ar(conn,i)]


def write_received_to_ar(conn,milestone_id,received,paid_date):
    m=dict(conn.execute('SELECT * FROM payment_milestones WHERE id=?',(milestone_id,)).fetchone())
    ar=linked_ar(conn,m)
    if not ar:
        return
    full=received>=float(m['amount'])-0.001
    conn.execute('''UPDATE project_receivables SET received_amount=?,remaining_debt=?,paid_date=?,
        collection_status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?''',
        (received,max(0,float(m['amount'])-received),paid_date,'PAID' if full else 'PENDING',ar['id']))
