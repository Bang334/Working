"""Apply only the explicitly approved Jingguang/JIYANG AR corrections."""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path('D:/Working')
DB=ROOT/'database/pm_portal.db'
CODE='HM27082026JI002'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--deposit',type=int,choices=[53460000,57736800],default=57736800)
    args=parser.parse_args()
    conn=sqlite3.connect(DB);conn.row_factory=sqlite3.Row
    try:
        conn.execute('BEGIN IMMEDIATE')
        jing=conn.execute('SELECT * FROM project_receivables WHERE id=34').fetchone()
        rows=[dict(r) for r in conn.execute('SELECT * FROM project_receivables WHERE contract_code=? ORDER BY id',(CODE,))]
        assert len(rows)==3 and [r['id'] for r in rows]==[51,52,53]
        assert [r['gross_amount'] for r in rows]==[57736800,105850800,28868400], 'Data changed; inspect before applying.'
        assert rows[0]['received_amount']==57736800
        assert jing and jing['gross_amount']==681900000 and not jing['received_amount'] and not jing['linked_milestone_id']
        assert not conn.execute('SELECT 1 FROM receivables_weekly_snapshots WHERE receivable_id=34').fetchone()
        contract=dict(conn.execute('SELECT * FROM contracts WHERE contract_code=?',(CODE,)).fetchone())
        milestones=[dict(r) for r in conn.execute('SELECT * FROM payment_milestones WHERE contract_id=? ORDER BY id',(contract['id'],))]
        assert len(milestones)==3
        unrelated_ar=[tuple(r) for r in conn.execute("SELECT * FROM project_receivables WHERE id<>34 AND contract_code IS NOT ? ORDER BY id",(CODE,))]
        unrelated_contracts=[tuple(r) for r in conn.execute('SELECT * FROM contracts WHERE id<>? ORDER BY id',(contract['id'],))]
        unrelated_ms=[tuple(r) for r in conn.execute('SELECT * FROM payment_milestones WHERE contract_id<>? ORDER BY id',(contract['id'],))]
        proposed=[]
        for row,net,vat,gross in zip(rows,[49500000,90750000,24750000],[3960000,7260000,1980000],[53460000,98010000,26730000]):
            received=args.deposit if row['id']==51 else row['received_amount']
            proposed.append({'id':row['id'],'net_amount':net,'vat_amount':vat,'gross_amount':gross,
                             'received_amount':received,'remaining_debt':gross-received})
        print(json.dumps({'remove_jingguang_id':34,'contract_gross_before':contract['total_amount'],
                          'contract_gross_after':178200000,'contract_net_after':165000000,
                          'deposit':args.deposit,'installments':proposed,'apply':args.apply},ensure_ascii=False,indent=2))
        if not args.apply:
            conn.rollback();return
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        backup=ROOT/'database/backups'/f'before_user_handover_corrections_{stamp}.db'
        backup.parent.mkdir(exist_ok=True)
        with sqlite3.connect(DB) as source,sqlite3.connect(backup) as target:source.backup(target)
        audit={'backup':str(backup),'before':{'jingguang':dict(jing),'contract':contract,'receivables':rows,'milestones':milestones},'proposed':proposed}
        note=('\n\n[30/10/2026 — Theo chỉ thị người dùng / 依使用者指示]\n'
              'Đã sửa tổng HĐ phần cứng về178.200.000đ gồmVAT:chưaVAT165.000.000đ,VAT13.200.000đ;giữ30%–55%–15%. '
              'Nguồn:bảnscan kýHM27082026JI002 ngày27/08/2026,trang1–2. '
              '含稅合約總額更正為178,200,000越盾，未稅165,000,000，稅額13,200,000。\n')
        note+=('Người dùng xác nhận thực nhận cọc53.460.000đ;chỉ sửa số cọc,ngày thực nhận14/05/2026 cũ vẫn chờ xác minh. '
               '使用者確認實收訂金53,460,000越盾，原收款日期仍待核實。'
               if args.deposit==53460000 else
               'Giữ số thực nhận đang ghi57.736.800đ;chênh4.276.800đ so với cọc hợp đồng được thể hiện là số dư có/chờ đối soát,không tự chuyển sang đợt khác. '
               '保留已登錄實收57,736,800越盾，訂金差額4,276,800列為待核對溢收，不自動移轉至其他期款。')
        conn.execute('DELETE FROM project_receivables WHERE id=34')
        for old,new in zip(rows,proposed):
            conn.execute('''UPDATE project_receivables SET total_contract_amount=165000000,
                net_amount=?,vat_rate=0.08,vat_amount=?,gross_amount=?,received_amount=?,remaining_debt=?,
                notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?''',
                (new['net_amount'],new['vat_amount'],new['gross_amount'],new['received_amount'],new['remaining_debt'],(old['notes'] or '')+note,new['id']))
            conn.execute('UPDATE payment_milestones SET amount=?,action_required=? WHERE id=? AND contract_id=?',
                (new['gross_amount'],'Đã sửa cơ sở VAT theo bản ký / 已依簽約版本更正稅額',old['linked_milestone_id'],contract['id']))
        conn.execute('UPDATE contracts SET total_amount=178200000,paid_amount=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
                     (args.deposit,(contract['notes'] or '')+note,contract['id']))
        assert unrelated_ar==[tuple(r) for r in conn.execute("SELECT * FROM project_receivables WHERE id<>34 AND contract_code IS NOT ? ORDER BY id",(CODE,))]
        assert unrelated_contracts==[tuple(r) for r in conn.execute('SELECT * FROM contracts WHERE id<>? ORDER BY id',(contract['id'],))]
        assert unrelated_ms==[tuple(r) for r in conn.execute('SELECT * FROM payment_milestones WHERE contract_id<>? ORDER BY id',(contract['id'],))]
        after=[dict(r) for r in conn.execute('SELECT * FROM project_receivables WHERE contract_code=? ORDER BY id',(CODE,))]
        assert sum(r['gross_amount'] for r in after)==178200000
        assert sum(r['net_amount'] for r in after)==165000000
        assert sum(r['vat_amount'] for r in after)==13200000
        assert sum(r['received_amount'] for r in after)==args.deposit
        assert sum(r['remaining_debt'] for r in after)==178200000-args.deposit
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        for before,now in zip(rows,after):
            for field in ['paid_date','due_date','customer_promised_date','start_date','collection_status']:
                assert before[field]==now[field]
        conn.commit()
        audit['after']=after
        path=ROOT/'database'/f'USER_HANDOVER_CORRECTIONS_{stamp}.json'
        path.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
        print('APPLIED. Backup:',backup,'Audit:',path)
    except Exception:
        conn.rollback();raise
    finally:conn.close()


if __name__=='__main__':main()
