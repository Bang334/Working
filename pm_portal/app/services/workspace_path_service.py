"""Repair migrated file references using exact relative paths, never filenames."""
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import WORKING_DIR


def relocated_path(value, workspace=None, home=None):
    """Return an existing counterpart only; keep missing/unsafe paths unchanged."""
    root = Path(workspace or WORKING_DIR).resolve()
    profile = Path(home or Path.home()).resolve()
    if not isinstance(value, str) or not value or Path(value).exists():
        return value
    normalized = value.replace('\\', '/')
    match = re.fullmatch(r'[a-zA-Z]:/Working(?:/(.*))?', normalized, re.I)
    base, suffix = (root, match.group(1) or '') if match else (None, '')
    if base is None:
        match = re.fullmatch(r'C:/Users/[^/]+/(.*)', normalized, re.I)
        if match:
            base, suffix = profile, match.group(1)
    if base is None:
        return value
    candidate = (base / suffix).resolve()
    if not candidate.is_relative_to(base):
        return value
    return str(candidate) if candidate.exists() else value


def repair_workspace_paths(db_path=None, workspace=None, backup=True):
    """Update path columns and attachment JSON atomically; no financial writes."""
    if db_path is None:
        from app.database import DB_PATH
        db_path = DB_PATH
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    report = {'changed': [], 'missing': [], 'backup': None}
    changes = []

    def rewrite(value, where):
        if isinstance(value, dict):
            return {k:rewrite(v, where+'.'+k) for k,v in value.items()}
        if isinstance(value, list):
            return [rewrite(v, where+f'[{i}]') for i,v in enumerate(value)]
        if not isinstance(value, str) or not re.match(r'^[A-Za-z]:[\\/]', value):
            return value
        new = relocated_path(value, workspace=workspace)
        if new != value:
            report['changed'].append({'location':where, 'old':value, 'new':new})
        elif not Path(value).exists():
            report['missing'].append({'location':where,'path':value})
        return new

    try:
        c.execute('BEGIN IMMEDIATE')
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            qtable='"'+table.replace('"','""')+'"'
            cols=[r[1] for r in c.execute(f'PRAGMA table_info({qtable})')]
            # Intentionally exclude prose, bodies, notes, money and business states.
            selected=[x for x in cols if x in {'path','file_path','folder_path','attachment_path','docx_file_path','xlsx_file_path','attachments','attachments_json'}]
            for column in selected:
                for row in c.execute(f'SELECT rowid AS __rowid__, "{column}" AS value FROM {qtable} WHERE "{column}" IS NOT NULL').fetchall():
                    old=row['value'];where=f'{table}[{row["__rowid__"]}].{column}'
                    if column in {'attachments','attachments_json'}:
                        try:
                            parsed=json.loads(old)
                        except (ValueError,TypeError):
                            continue
                        new_obj=rewrite(parsed,where)
                        new=json.dumps(new_obj,ensure_ascii=False) if new_obj!=parsed else old
                    else:
                        new=rewrite(old,where)
                    if new!=old:
                        changes.append((qtable,column,row['__rowid__'],new))
        if changes and backup:
            folder=Path(workspace or WORKING_DIR)/'database'/'backups'
            folder.mkdir(parents=True,exist_ok=True)
            dest=folder/('workspace_paths_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.db')
            # Separate read connection avoids backing up a connection with an open transaction.
            source=sqlite3.connect(db_path);out=sqlite3.connect(dest)
            source.backup(out);out.close();source.close()
            report['backup']=str(dest)
        for table,column,rowid,new in changes:
            c.execute(f'UPDATE {table} SET "{column}"=? WHERE rowid=?',(new,rowid))
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()
    return report
