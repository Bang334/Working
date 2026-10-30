"""Record the user's explicit confirmation of the actual JIYANG deposit."""
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
root=Path('D:/Working');db=root/'database/pm_portal.db'
stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
conn=sqlite3.connect(db);conn.row_factory=sqlite3.Row
try:
    conn.execute('BEGIN IMMEDIATE')
    before=dict(conn.execute('SELECT * FROM project_receivables WHERE id=51').fetchone())
    assert before['contract_code']=='HM27082026JI002' and before['gross_amount']==53460000
    assert before['received_amount']==57736800 and before['linked_milestone_id']==105
    other=[tuple(r) for r in conn.execute('SELECT * FROM project_receivables WHERE id<>51 ORDER BY id')]
    backup=root/'database/backups'/f'before_jiyang_deposit_confirmation_{stamp}.db'
    with sqlite3.connect(db) as src,sqlite3.connect(backup) as dest:src.backup(dest)
    note=('\n\n[30/10/2026 — Người dùng xác nhận thực nhận / 使用者確認實收]\n'
          'Cọc JIYANG đã thực nhận53.460.000đ,đúng30% của178.200.000đ gồmVAT. '
          'Cập nhật thay số57.736.800đ và kết thúc chênh4.276.800đ chờ đối soát nêu trước đó. '
          'Ngày thực nhận chưa được xác nhận lại,giữ nguyên ngày đang lưu. '
          'JIYANG實收訂金確認為53,460,000越盾，原待核對差額4,276,800已結清；未重新確認收款日期，保留原登錄日期。')
    conn.execute('''UPDATE project_receivables SET received_amount=53460000,
        remaining_debt=0,notes=COALESCE(notes,'')||?,updated_at=CURRENT_TIMESTAMP WHERE id=51''',(note,))
    conn.execute('''UPDATE contracts SET paid_amount=53460000,
        notes=COALESCE(notes,'')||?,updated_at=CURRENT_TIMESTAMP WHERE id=40 AND contract_code='HM27082026JI002' ''',(note,))
    conn.execute('''UPDATE payment_milestones SET status='PAID',status_label='Đã thu đủ / 已全額收款',
        action_required='Người dùng xác nhận cọc thực nhận53.460.000đ / 使用者確認實收訂金53,460,000越盾' WHERE id=105''')
    assert other==[tuple(r) for r in conn.execute('SELECT * FROM project_receivables WHERE id<>51 ORDER BY id')]
    rows=[dict(r) for r in conn.execute("SELECT * FROM project_receivables WHERE contract_code='HM27082026JI002' ORDER BY id")]
    assert sum(r['gross_amount'] for r in rows)==178200000
    assert sum(r['received_amount'] for r in rows)==53460000
    assert sum(r['remaining_debt'] for r in rows)==124740000
    assert rows[0]['paid_date']==before['paid_date']
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    conn.commit()
    (root/'database'/f'JIYANG_DEPOSIT_CONFIRMED_{stamp}.json').write_text(json.dumps(
        {'backup':str(backup),'before':before,'after':rows[0],'confirmation':'Người dùng xác nhận đã nhận53.460.000đ'},ensure_ascii=False,indent=2),encoding='utf-8')
    report=root/'Bao Cao/Tiep Nhan Du An 20261030/BAO_CAO_DOI_CHIEU_DU_AN_20261030.md'
    text=report.read_text(encoding='utf-8')
    report.write_text('> **Xác nhận bổ sung ngày30/10/2026:** Người dùng xác nhận cọc JIYANG thực nhận53.460.000đ;đã cập nhật hệ thống,dư nợ124.740.000đ.Chênh4.276.800đ nêu trong ghi chú lịch sử dưới đây đã được giải quyết. / 使用者確認實收訂金53,460,000越盾，系統未收餘額124,740,000越盾，原差額已結清。\n\n'+text,encoding='utf-8')
    print('CONFIRMED: contract178200000; received53460000; remaining124740000; unrelatedARunchanged;backup',backup)
except Exception:
    conn.rollback();raise
finally:
    conn.close()
