"""Reconcile the reviewed 2026 source without re-importing or deleting workflow history."""
import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def reconcile(db_path, drop_vonmax_duplicate=False):
    c=sqlite3.connect(db_path);c.row_factory=sqlite3.Row
    out=ROOT/'database'/'backups'/('schedule_review_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    out.mkdir(parents=True)
    b=sqlite3.connect(out/'before.db');c.backup(b);b.close()
    report={'changes':[],'backup':str(out/'before.db'),'original_workbook_unchanged':True}
    protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Ho So Du An').rglob('*') if p.is_file()}
    try:
        c.execute('BEGIN IMMEDIATE')
        cols={r[1] for r in c.execute('PRAGMA table_info(project_receivables)')}
        for name,typ in [('paid_by_date','TEXT'),('payment_basis','TEXT'),('installment_order','INTEGER'),('project_group','TEXT')]:
            if name not in cols:c.execute(f'ALTER TABLE project_receivables ADD COLUMN {name} {typ}')

        def group(code):
            return [dict(r) for r in c.execute('SELECT * FROM project_receivables WHERE contract_code=? ORDER BY id',(code,))]

        def patch(row, **values):
            changes={k:v for k,v in values.items() if row.get(k)!=v}
            if not changes:return
            c.execute('UPDATE project_receivables SET '+','.join(k+'=?' for k in changes)+',updated_at=CURRENT_TIMESTAMP WHERE id=?',list(changes.values())+[row['id']])
            report['changes'].append({'id':row['id'],'contract':row['contract_code'],'fields':changes})
            row.update(changes)

        # User-provided screenshot explicitly supplies the lost Excel date.
        jinxun=group('HMV100120260001')
        second=next(r for r in jinxun if abs(r['net_amount']-429841500)<1)
        if second.get('payment_basis')!='user_screenshot_20261029':
            patch(second,paid_date='2026-08-29',customer_promised_date='2026-08-29',
                  payment_basis='user_screenshot_20261029',notes=(second['notes'] or '')+'\nĐỐI SOÁT 29/10/2026: ngày thu 29/08/2026 theo ảnh người dùng; file xuất bị lỗi serial ngày, không phải khoản chưa thu.')

        schedules=[('HMV100120260001',35,55,10),('HMV07032026001',35,55,10),('HMV151020250001',40,40,20)]
        for code,advance_pct,second_pct,last_pct in schedules:
            rr=group(code);total=rr[0]['total_contract_amount']
            adv=round(total*advance_pct/100,2)
            inferred=next((r for r in rr if r.get('payment_basis')=='inferred_preceding_paid'),None)
            if not inferred:
                # All three reviewed schedules lack their first installment in the source.
                assert len(rr)==2,(code,len(rr))
                second=next(r for r in rr if abs(r['net_amount']-total*second_pct/100)<1)
                final=next(r for r in rr if r['id']!=second['id'])
                assert second['received_amount']>=second['gross_amount']>0
                bound=second.get('paid_date') or second.get('paid_by_date')
                assert bound,code
                title=f'Đợt 1 – Tạm ứng {advance_pct}% / 第一期 {advance_pct}% 訂金'
                note=f'ĐỐI SOÁT 29/10/2026: bổ sung đợt {advance_pct}% còn thiếu. Theo quy tắc người dùng xác nhận: đợt sau đã thu thì đợt trước đã thu. Chậm nhất đã thu ngày {bound}; chưa có ngày thực nhận chính xác, không tạo chứng từ ngân hàng.'
                cur=c.execute('''INSERT INTO project_receivables (order_no,project_name,customer_name,contract_code,total_contract_amount,
                    net_amount,vat_rate,vat_amount,gross_amount,received_amount,remaining_debt,collection_status,notes,
                    paid_by_date,payment_basis,installment_order) VALUES (?,?,?,?,?,?,?,?,?,?,0,'PAID',?,?,?,1)''',
                    (second['order_no'],title,second['customer_name'],code,total,adv,0,0,adv,adv,note,bound,'inferred_preceding_paid'))
                inferred=dict(c.execute('SELECT * FROM project_receivables WHERE id=?',(cur.lastrowid,)).fetchone())
                report['changes'].append({'contract':code,'added_advance_pct':advance_pct,'received':adv,'paid_by':bound,'exact_paid_date':None})
            else:
                remaining=[r for r in rr if r['id']!=inferred['id']]
                second=next(r for r in remaining if abs(r['net_amount']-total*second_pct/100)<1)
                final=next(r for r in remaining if r['id']!=second['id'])
            patch(inferred,installment_order=1)
            patch(second,installment_order=2)
            patch(final,installment_order=3)

        # The workbook explicitly marks this repair invoice paid and supplies a receipt date.
        for raw in c.execute("SELECT * FROM project_receivables WHERE contract_code IS NULL AND gross_amount=13700000 AND paid_date='2026-10-23'").fetchall():
            row=dict(raw)
            patch(row,received_amount=13700000,remaining_debt=0,collection_status='PAID',payment_basis='source_paid_status_and_date',
                  notes=(row['notes'] or '')+ ('\nĐỐI SOÁT: nguồn ghi đã thanh toán và ngày thu 23/10/2026; bổ sung số đã thu bị để trống.' if row['received_amount']==0 else ''))

        # Source sequence, never money size or urgency order, controls installment order.
        for code in [r[0] for r in c.execute('SELECT DISTINCT contract_code FROM project_receivables WHERE contract_code IS NOT NULL')]:
            rr=group(code)
            if code in {s[0] for s in schedules} | {'HMV060620250001','HMV060620250002'}:continue
            for n,row in enumerate(rr,1):patch(row,installment_order=n)

        audit_path=ROOT/'.qa/vonmax_contract_mail/mail_audit.json'
        audit=json.loads(audit_path.read_text(encoding='utf-8'))
        evidence=next(m for m in audit['matches'] if '2026-10-16' in m['date'] and 'HMV060620250002' in m['body'])
        assert all(s in evidence['body'] for s in ['HMV060620250001','545,454,545','1,100,000,000','54.545.454'])
        report['vonmax_evidence']={'subject':evidence['subject'],'date':evidence['date'],'source':str(audit_path)}
        vm=group('HMV060620250001')+group('HMV060620250002')
        for row in vm:
            if row['net_amount']==54545454 and row['total_contract_amount']==545454545:
                patch(row,contract_code='HMV060620250002',project_group='Vonmax – Phần cứng / 硬體',installment_order=2,
                      notes=(row['notes'] or '')+ ('\nĐỐI SOÁT EMAIL 16/10/2026 và thư19/09 được trích dẫn: HĐ phần cứng đúng HMV060620250002, đợt cuối54.545.454đ; email nhắc tổng làm tròn54.545.455đ, giữ số yêu cầu chi tiết.' if row['contract_code']!='HMV060620250002' else ''))
            elif row['net_amount']==110000000 and 'phần mềm' in row['project_name'].lower():
                patch(row,project_group='Vonmax – Phần mềm / 軟體',installment_order=2)
            elif row['net_amount']==110000000 and 'phần cứng' in row['project_name'].lower():
                assert row['received_amount']==0
                if row['linked_milestone_id']:
                    assert not c.execute('SELECT 1 FROM workflow_cases WHERE milestone_id=?',(row['linked_milestone_id'],)).fetchone(), 'Dòng đã có workflow: cần đối chiếu bằng chứng trước khi loại.'
                    c.execute('DELETE FROM payment_milestones WHERE id=?',(row['linked_milestone_id'],))
                c.execute('DELETE FROM project_receivables WHERE id=?',(row['id'],))
                report['changes'].append({'removed_id':row['id'],'reason':'Đối chiếu email16/10: phần cứng là HMV060620250002/54.545.454đ; dòng110triệu ghi nhãn phần cứng và mã0001 là trùng khoản phần mềm.'})
        for code,label,total in [('HMV060620250002','Vonmax – Phần cứng / 硬體',545454545),('HMV060620250001','Vonmax – Phần mềm / 軟體',1100000000)]:
            rr=group(code);final=next(r for r in rr if r['payment_basis']!='email_remaining_balance')
            if not c.execute('SELECT 1 FROM contracts WHERE contract_code=?',(code,)).fetchone():
                c.execute('INSERT INTO contracts (contract_code,customer_name_vi,project_name_vi,total_amount,currency,notes) VALUES (?,?,?,?,?,?)',
                    (code,final['customer_name'],label,total,'VND','Mã, giá trị và khoản cuối đối chiếu email16/10/2026, chuỗi19/09/2026; chưa có bản hợp đồng ký của hợp đồng này trên máy hiện tại.'))
            if not any(r['payment_basis']=='email_remaining_balance' for r in rr):
                history=total-final['gross_amount']
                note='ĐỐI SOÁT EMAIL16/10/2026: chỉ còn10% chưa thanh toán; suy ra90% các đợt trước đã thu theo quy tắc người dùng. Tổng hợp lịch sử, chưa tách tỷ lệ từng đợt, chưa biết ngày thực nhận. Đây không phải một đợt90% trong hợp đồng.'
                c.execute('''INSERT INTO project_receivables (order_no,project_name,customer_name,contract_code,total_contract_amount,net_amount,vat_rate,vat_amount,
                    gross_amount,received_amount,remaining_debt,collection_status,notes,paid_by_date,payment_basis,installment_order,project_group)
                    VALUES (?,?,?,?,?,?,0,0,?,?,0,'PAID',?,'2026-10-16','email_remaining_balance',1,?)''',
                    (final['order_no'],'Tổng các đợt trước90% / 前期期款合計90%',final['customer_name'],code,total,history,history,history,note,label))
                report['changes'].append({'contract':code,'prior_paid_total':history,'paid_by':'2026-10-16','basis':'Email xác nhận chỉ còn khoản cuối10%; tổng hợp lịch sử, không tự tách tỷ lệ từng đợt.'})

        # Rebuild only missing links; preserve every existing workflow and evidence.
        for raw in c.execute('SELECT * FROM project_receivables WHERE contract_code IS NOT NULL').fetchall():
            row=dict(raw)
            co=c.execute('SELECT * FROM contracts WHERE contract_code=?',(row['contract_code'],)).fetchone()
            if not co:continue
            peers=[r for r in group(row['contract_code']) if r['project_group']==row['project_group']]
            if len({r['total_contract_amount'] for r in peers})>1:
                continue  # Keep unresolved mixed-value rows out of collection workflows.
            pct=round(row['net_amount']/row['total_contract_amount']*100,5) if row['total_contract_amount'] else None
            ms=row['linked_milestone_id']
            ms_status='PAID' if row['collection_status']=='PAID' else ('WAITING' if row['due_date'] else 'PENDING_TRIGGER')
            if not ms:
                cur=c.execute('''INSERT INTO payment_milestones (contract_id,contract_code,milestone_name,percentage,amount,trigger_condition,status,status_label,paid_date,triggered,due_date)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?)''',(co['id'],row['contract_code'],row['project_name'],pct,row['gross_amount'],row['notes'],ms_status,
                    'Đã thu / theo căn cứ đối soát' if ms_status=='PAID' else 'Theo dõi công nợ',row['paid_date'],int(bool(row['due_date'])),row['due_date']))
                ms=cur.lastrowid;c.execute('UPDATE project_receivables SET linked_milestone_id=? WHERE id=?',(ms,row['id']))
            else:
                c.execute('UPDATE payment_milestones SET percentage=?,status=?,paid_date=?,status_label=? WHERE id=?',
                    (pct,ms_status,row['paid_date'],'Đã thu / theo căn cứ đối soát' if ms_status=='PAID' else 'Theo dõi công nợ',ms))

        for code in [r[0] for r in c.execute('SELECT contract_code FROM contracts')]:
            rr=group(code);groups={}
            for r in rr:groups.setdefault(r['project_group'] or '',[]).append(r)
            vals=[]
            for sub in groups.values():
                totals={r['total_contract_amount'] for r in sub};rates={r['vat_rate'] for r in sub}
                if len(totals)==1 and len(rates)==1:vals.append(next(iter(totals))*(1+next(iter(rates))))
            known_total=sum(vals) if len(vals)==len(groups) else 0
            paid=sum(r['received_amount'] for r in rr)
            c.execute('UPDATE contracts SET total_amount=?,paid_amount=?,status=?,updated_at=CURRENT_TIMESTAMP WHERE contract_code=?',
                (known_total,paid,'Đã thu đủ theo dữ liệu đối soát' if known_total and paid>=known_total-1 else 'Đã đối soát lịch thanh toán / theo dõi các khoản còn lại',code))

        assert not c.execute('SELECT id FROM project_receivables WHERE abs(gross_amount-received_amount-remaining_debt)>.01').fetchall()
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert protected=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Ho So Du An').rglob('*') if p.is_file()}
        c.commit()
    except Exception:
        c.rollback();raise
    report['contracts']=[]
    for (code,) in c.execute('SELECT DISTINCT contract_code FROM project_receivables WHERE contract_code IS NOT NULL'):
        rr=group(code)
        for label in {r['project_group'] or '' for r in rr}:
            sub=[r for r in rr if (r['project_group'] or '')==label]
            totals={r['total_contract_amount'] for r in sub};total=next(iter(totals)) if len(totals)==1 else None
            percent=round(sum(r['net_amount'] for r in sub)/total*100,4) if total else None
            report['contracts'].append({'code':code,'project':label,'listed_schedule_pct':percent,'received':sum(r['received_amount'] for r in sub),'rows':[r['id'] for r in sub]})
    report['unchanged_document_files']=len(protected)
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    c.close();return report


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,default=ROOT/'database/pm_portal.db');p.add_argument('--drop-vonmax-duplicate',action='store_true');args=p.parse_args()
    print(json.dumps(reconcile(args.db,args.drop_vonmax_duplicate),ensure_ascii=False,indent=2))
