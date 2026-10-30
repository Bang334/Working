import json
import sqlite3

from app.services.workspace_path_service import relocated_path, repair_workspace_paths


def test_exact_relocation_and_no_guessing(tmp_path):
    folder=tmp_path/'Ho So Du An'/'Nhac Nho'/'reminder_15'
    folder.mkdir(parents=True)
    pdf=folder/'a.pdf';pdf.write_bytes(b'%PDF-1.7')
    old=r'Z:\Working\Ho So Du An\Nhac Nho\reminder_15\a.pdf'
    assert relocated_path(old,tmp_path)==str(pdf)
    assert relocated_path(r'Z:\Working\elsewhere\a.pdf',tmp_path)==r'Z:\Working\elsewhere\a.pdf'
    assert relocated_path(r'Z:\Working\..\outside.pdf',tmp_path)==r'Z:\Working\..\outside.pdf'
    assert relocated_path(str(pdf),tmp_path)==str(pdf)


def test_migration_json_money_preservation_backup_and_repeat(tmp_path):
    pdf=tmp_path/'file.pdf';pdf.write_bytes(b'%PDF-1.7')
    db=tmp_path/'test.db';c=sqlite3.connect(db)
    c.execute('CREATE TABLE records (id INTEGER PRIMARY KEY, file_path TEXT, attachments_json TEXT, amount REAL, notes TEXT)')
    old=r'Z:\Working\file.pdf'
    c.execute('INSERT INTO records VALUES (1,?,?,1234,?)',(old,json.dumps([{'path':old}]),old))
    c.commit();c.close()
    report=repair_workspace_paths(db,tmp_path)
    assert len(report['changed'])==2 and report['backup']
    c=sqlite3.connect(db);r=c.execute('SELECT * FROM records').fetchone();c.close()
    assert r[1]==str(pdf) and json.loads(r[2])[0]['path']==str(pdf)
    assert r[3:]==(1234,old)
    backup=sqlite3.connect(report['backup'])
    assert backup.execute('SELECT file_path FROM records').fetchone()[0]==old
    backup.close()
    repeated=repair_workspace_paths(db,tmp_path)
    assert repeated['changed']==[] and repeated['backup'] is None
