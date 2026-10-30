"""Apply explicit user confirmations; preserve all monetary amounts."""
import sqlite3,json
from pathlib import Path
from datetime import datetime
root=Path('D:/Working'); db=root/'database/pm_portal.db'
stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
backup=root/'database/backups'/f'before_completed_deposits_{stamp}.db'
with sqlite3.connect(db) as src,sqlite3.connect(backup) as dst: src.backup(dst)
c=sqlite3.connect(db);c.row_factory=sqlite3.Row
try:
 c.execute('BEGIN IMMEDIATE')
 before={t:[dict(r) for r in c.execute('select * from '+t)] for t in ['project_receivables','payment_milestones','contracts']}
 for rid,code,amt in [(51,'HM27082026JI002',53460000),(54,'HM25082026JI001',148500000)]:
  r=c.execute('select * from project_receivables where id=?',(rid,)).fetchone()
  assert r['contract_code']==code and r['received_amount']==amt
  note='\n\n[30/10/2026 — Xác nhận người dùng / 使用者確認] Ngày thực nhận cọc đúng là14/09/2026, thay ngày14/05/2026 nhập sai. Không đổi số tiền. / 實收訂金日確認為2026/09/14，修正原誤登日期，不變更金額。'
  c.execute("update project_receivables set paid_date='2026-09-14',notes=coalesce(notes,'')||?,updated_at=CURRENT_TIMESTAMP where id=?",(note,rid))
  c.execute("update payment_milestones set paid_date='2026-09-14' where id=?",(r['linked_milestone_id'],))
 r=c.execute('select * from project_receivables where id=65').fetchone()
 assert r['received_amount']==300000000 and r['paid_date']=='2026-10-30'
 note='\n\n[30/10/2026 — Xác nhận người dùng / 使用者確認] Cheng Feng đã thực nhận cọc30%=300.000.000đ ngày30/10/2026. Thông tin chờ cọc/gộp đợt ngày05/11 ở ghi chú nguồn là lịch cũ, không còn phản ánh trạng thái đợt1. Đợt2 vẫn chưa xác nhận thu. / 已於2026/10/30實收30%訂金300,000,000越盾；原11/05待付款為歷史計畫，第二期尚未確認收款。'
 c.execute("update project_receivables set doc_status='Đã thu cọc 30% ngày30/10/2026 / 已於2026/10/30收訂金30%',notes=coalesce(notes,'')||?,updated_at=CURRENT_TIMESTAMP where id=65",(note,))
 c.execute("update payment_milestones set due_date=?,action_required='Đã nhận cọc300.000.000đ ngày30/10/2026 theo xác nhận người dùng / 使用者確認已收訂金',trigger_condition=coalesce(trigger_condition,'')||? where id=?",(r['due_date'],note,r['linked_milestone_id']))
 after={t:[dict(r) for r in c.execute('select * from '+t)] for t in before}
 for a,b in zip(before['project_receivables'],after['project_receivables']):
  for k in ['gross_amount','net_amount','vat_amount','received_amount','remaining_debt']:assert a[k]==b[k]
  if a['id'] not in [51,54,65]: assert a==b
 assert before['contracts']==after['contracts']
 assert c.execute('pragma integrity_check').fetchone()[0]=='ok'
 c.commit()
 (root/'database'/f'COMPLETED_DEPOSITS_CONFIRMED_{stamp}.json').write_text(json.dumps({'backup':str(backup),'before':before,'after':after},ensure_ascii=False,indent=2),encoding='utf-8')
 print('Verified: JIYANG two deposits 2026-09-14; ChengFeng deposit 2026-10-30; all amounts unchanged; backup '+str(backup))
except Exception:
 c.rollback();raise
finally:c.close()
