"""Atomic editing of an AR contract and its payment schedule."""
import hashlib
import json
import sqlite3
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from app.database import get_db_connection


def _rows(conn, item_id):
    anchor = conn.execute('SELECT * FROM project_receivables WHERE id=?', (item_id,)).fetchone()
    if not anchor:
        raise ValueError('Không tìm thấy hợp đồng. / 找不到合約。')
    code = str(anchor['contract_code'] or '').strip()
    if code and code not in ('-', 'None'):
        rows = conn.execute("SELECT * FROM project_receivables WHERE TRIM(contract_code)=? AND TRIM(COALESCE(project_group,''))=? ORDER BY COALESCE(installment_order,999),id", (code,str(anchor['project_group'] or '').strip())).fetchall()
    else:
        rows = [anchor]
    if len({r['customer_name'] for r in rows}) > 1:
        raise ValueError('Mã hợp đồng đang thuộc nhiều khách hàng. Cần đối chiếu trước khi sửa chung. / 此合約編號涉及多個客戶，請核對後再統一編輯。')
    return [dict(r) for r in rows]


def _revision(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def get_contract_schedule(item_id):
    conn = get_db_connection()
    try:
        rows = _rows(conn, item_id)
        totals = {float(r['total_contract_amount'] or 0) for r in rows}
        return {'rows': rows, 'revision': _revision(rows),
                'total_amount': next(iter(totals)) if len(totals) == 1 else 0,
                'warning': '' if len(totals) == 1 else 'Các đợt đang khác giá trị hợp đồng. Hãy xác nhận giá trị đúng trước khi lưu. / 各期合約總額不一致，儲存前請確認正確金額。'}
    finally:
        conn.close()


def _money(value):
    amount = Decimal(str(value or 0))
    if not amount.is_finite() or amount < 0:
        raise ValueError('Số tiền và tỷ lệ phải là số không âm hợp lệ. / 金額及比例必須為有效的非負數。')
    return amount


def _day(value):
    if not value:
        return None
    return date.fromisoformat(str(value)).isoformat()


def save_contract_schedule(item_id, payload):
    conn = get_db_connection()
    try:
        conn.execute('BEGIN IMMEDIATE')
        rows = _rows(conn, item_id)
        if payload['revision'] != _revision(rows):
            raise ValueError('Dữ liệu đã thay đổi ở nơi khác. Đóng và mở lại hợp đồng để cập nhật. / 資料已在其他位置更新，請關閉並重新開啟合約。')
        total = _money(payload['total_amount']).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        if total <= 0:
            raise ValueError('Giá trị hợp đồng phải lớn hơn 0. / 合約金額必須大於0。')
        installments = payload['installments']
        contract_rate = payload.get('vat_rate')
        if contract_rate is None:
            rates = {_money(i.get('vat_rate', rows[0].get('vat_rate', 0))) for i in installments}
            if len(rates) != 1:
                raise ValueError('VAT phải dùng chung cho cả hợp đồng. / 全合約須使用同一稅率。')
            contract_rate = next(iter(rates))
        contract_rate = _money(contract_rate)
        if not 1 <= len(installments) <= 20:
            raise ValueError('Số đợt phải từ 1 đến 20. / 付款期數須為1至20期。')
        percentages = [_money(i['percentage']) for i in installments]
        if any(p <= 0 for p in percentages) or sum(percentages) != Decimal('100'):
            raise ValueError('Tỷ lệ từng đợt phải lớn hơn 0 và tổng đúng 100%. / 各期比例須大於0，且合計必須為100%。')
        existing = {r['id']: r for r in rows}
        ids = [i['id'] for i in installments if i.get('id') is not None]
        if len(ids) != len(set(ids)) or not set(ids).issubset(existing):
            raise ValueError('Danh sách đợt không thuộc hợp đồng hoặc bị trùng. / 期款不屬於本合約或有重複資料。')
        removed = [r for r in rows if r['id'] not in ids]
        for r in removed:
            if r['received_amount'] or r['paid_date'] or r.get('paid_by_date') or r.get('linked_milestone_id'):
                raise ValueError('Không thể bỏ đợt đã thu tiền hoặc đã liên kết hồ sơ. Hãy giữ đợt đó trong lịch. / 已收款或已關聯單據的期款無法刪除，請保留該期。')
            if conn.execute('SELECT 1 FROM receivables_weekly_snapshots WHERE receivable_id=? LIMIT 1', (r['id'],)).fetchone():
                raise ValueError('Đợt cần bỏ đã có lịch sử chốt tuần; cần giữ lại để bảo toàn lịch sử. / 該期已有每週結算歷史，須保留以維護歷史紀錄。')
        project = str(payload['project_name']).strip()
        if not project:
            raise ValueError('Vui lòng nhập tên dự án. / 請輸入專案名稱。')
        if project != str(rows[0].get('project_group') or '').strip():
            other = conn.execute("SELECT id FROM project_receivables WHERE contract_code=? AND TRIM(COALESCE(project_group,''))=?", (rows[0]['contract_code'],project)).fetchall()
            if any(r['id'] not in existing for r in other):
                raise ValueError('Tên dự án này đã thuộc một nhóm khác của cùng mã hợp đồng. Vui lòng dùng tên riêng để tránh gộp nhầm. / 同一合約編號已有其他群組使用此名稱，請使用不同名稱以免誤合併。')
        prepared = []
        allocated = Decimal(0)
        for index, (item, percentage) in enumerate(zip(installments, percentages)):
            old = existing.get(item.get('id'), {})
            net = total - allocated if index == len(installments)-1 else (total * percentage / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            allocated += net
            rate = contract_rate
            if rate not in (Decimal('0'), Decimal('0.08'), Decimal('0.1')):
                raise ValueError('Thuế VAT phải là 0%, 8% hoặc 10%. / 營業稅率須為0%、8%或10%。')
            vat = (net * rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            gross = net + vat
            received = _money(item.get('received_amount', old.get('received_amount', 0)))
            status = item.get('collection_status', 'PENDING')
            if status not in ('PAID', 'PARTIAL', 'PENDING', 'URGENT', 'DELAYED'):
                raise ValueError('Trạng thái thu không hợp lệ. / 收款狀態無效。')
            if received > gross:
                raise ValueError(f'Đợt {index+1}: tiền phải thu thấp hơn tiền đã nhận. Hãy điều chỉnh tỷ lệ hoặc tiền đã thu. / 應收金額低於已收金額，請調整比例或已收金額。')
            if status == 'PAID' and received != gross:
                raise ValueError(f'Đợt {index+1}: chọn đã thu đủ phải có số đã nhận bằng tiền phải thu. / 選擇已全額收款時，已收金額須等於應收金額。')
            if status != 'PAID' and received == gross and gross > 0:
                status = 'PAID'
            elif status in ('PARTIAL', 'PAID'):
                status = 'PENDING'
            paid = _day(item.get('paid_date'))
            if paid and received <= 0:
                raise ValueError(f'Đợt {index+1}: đã nhập ngày thực thu nhưng chưa có số tiền đã nhận. / 已填入實際收款日，但尚未填入已收金額。')
            if paid and date.fromisoformat(paid) > datetime.now(timezone(timedelta(hours=7))).date():
                raise ValueError('Ngày thực thu không được ở tương lai. / 實際收款日不得為未來日期。')
            due = _day(item.get('due_date'))
            promised = _day(item.get('customer_promised_date'))
            linked = old.get('linked_milestone_id')
            if linked:
                from app.services.payment_state_service import ledger_total
                if received < Decimal(str(ledger_total(conn, linked))):
                    raise ValueError('Tiền đã thu thấp hơn số đã ghi nhận bằng chứng từ thu tiền. / 已收金額不得低於收款憑證已登錄的金額。')
            prepared.append((item, old, percentage, net, vat, gross, received, status, paid, due, promised, rate))
        # SQLite backup before the one transaction is committed. No live data changed on open.
        dbfile = conn.execute('PRAGMA database_list').fetchone()[2]
        if dbfile:
            backup_dir = Path(dbfile).parent / 'backups'
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f'contract_schedule_{datetime.now():%Y%m%d_%H%M%S_%f}.db'
            with sqlite3.connect(dbfile) as source, sqlite3.connect(backup_path) as dest:
                source.backup(dest)
        linked_contract_id = None
        for row in rows:
            if row.get('linked_milestone_id'):
                linked = conn.execute('SELECT contract_id FROM payment_milestones WHERE id=?', (row['linked_milestone_id'],)).fetchone()
                if linked:
                    linked_contract_id = linked[0]
                    break
        first_saved_id = None
        for r in removed:
            conn.execute('DELETE FROM project_receivables WHERE id=?', (r['id'],))
        for index, values in enumerate(prepared, 1):
            item, old, percentage, net, vat, gross, received, status, paid, due, promised, rate = values
            fields = dict(project_name=str(item.get('name') or f'Đợt {index}').strip(),
                project_group=project, customer_name=rows[0]['customer_name'], contract_code=rows[0]['contract_code'],
                total_contract_amount=float(total), net_amount=float(net), vat_rate=float(rate), vat_amount=float(vat),
                gross_amount=float(gross), received_amount=float(received), remaining_debt=float(gross-received),
                collection_status=status, paid_date=paid, due_date=due, customer_promised_date=promised,
                doc_status=str(item.get('doc_status') or ''), notes=str(payload.get('notes') or ''), installment_order=index)
            if old:
                # An explicit receipt edit invalidates inferred timing; keep untouched historical evidence.
                if received != Decimal(str(old.get('received_amount') or 0)) or paid != old.get('paid_date'):
                    fields.update(paid_by_date=None, payment_basis='manual_schedule_edit')
                conn.execute('UPDATE project_receivables SET '+','.join(f'{k}=?' for k in fields)+',updated_at=CURRENT_TIMESTAMP WHERE id=?', (*fields.values(), old['id']))
                rid = old['id']
            else:
                rid = conn.execute('INSERT INTO project_receivables ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')', tuple(fields.values())).lastrowid
                if linked_contract_id:
                    mid = conn.execute('INSERT INTO payment_milestones (contract_id,contract_code,milestone_name,percentage,amount,status,status_label) VALUES (?,?,?,?,?,?,?)',
                        (linked_contract_id, rows[0]['contract_code'], fields['project_name'], float(percentage), float(gross), 'WAITING', 'Chờ thu')).lastrowid
                    conn.execute('UPDATE project_receivables SET linked_milestone_id=? WHERE id=?', (mid,rid))
                    old = {'linked_milestone_id': mid}
            if first_saved_id is None:
                first_saved_id = rid
            if old.get('linked_milestone_id'):
                mid = old['linked_milestone_id']
                conn.execute('UPDATE payment_milestones SET milestone_name=?,percentage=?,amount=?,due_date=?,paid_date=?,status=?,status_label=? WHERE id=?',
                    (fields['project_name'], float(percentage), float(gross), due, paid, 'PAID' if status=='PAID' else 'WAITING', 'Đã thu đủ' if status=='PAID' else 'Chờ thu / còn phải thu', mid))
        linked_contracts = [(linked_contract_id,)] if linked_contract_id else []
        for contract in linked_contracts:
            paid_total = sum(float(values[6]) for values in prepared)
            conn.execute('UPDATE contracts SET total_amount=?,paid_amount=?,updated_at=CURRENT_TIMESTAMP WHERE id=?', (float(total),paid_total,contract[0]))
        conn.commit()
        return get_contract_schedule(first_saved_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
