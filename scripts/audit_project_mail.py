"""Read-only review of project emails and their document attachments."""
import json
import re
import sqlite3
import sys
from pathlib import Path

import pythoncom
import win32com.client

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.qa'/'project_mail_audit_20261029'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(ROOT/'database/pm_portal.db');c.row_factory=sqlite3.Row
    contracts=[dict(r) for r in c.execute('SELECT * FROM contracts')]
    ar=[dict(r) for r in c.execute('SELECT * FROM project_receivables')];c.close()
    (OUT/'database_before.json').write_text(json.dumps({'contracts':contracts,'receivables':ar},ensure_ascii=False,indent=2),encoding='utf-8')
    pattern=re.compile(r'seiyo|正揚|正扬|darfon|達方|达方|jinxun|金迅|ji\s*yang|佶陽|吉陽|jing\s*guang|景光|cheng\s*feng|chengfeng|承豐|承丰|錩新|CX\s*(?:TECH|錩新|客戶)|HMV\d|HMSY\d|DFV2026|RFID|BAT-RFR900|F601-0700|vonmax|弘聲',re.I)
    pythoncom.CoInitialize();report={'folders':[],'matches':[]}
    try:
        ns=win32com.client.Dispatch('Outlook.Application').GetNamespace('MAPI');seen=set()
        for kind in [5,6]:
            stack=[ns.GetDefaultFolder(kind)]
            while stack:
                folder=stack.pop()
                stack.extend(folder.Folders.Item(j) for j in range(1,folder.Folders.Count+1))
                items=folder.Items;items.Sort('[SentOn]' if kind==5 else '[ReceivedTime]',True)
                report['folders'].append({'name':str(folder.Name),'count':int(items.Count),'direction':'sent' if kind==5 else 'inbox'})
                for i in range(1,int(items.Count)+1):
                    mail=items.Item(i)
                    if mail.Class!=43:continue
                    entry=str(mail.EntryID)
                    if entry in seen:continue
                    seen.add(entry)
                    subject=str(mail.Subject or '');body=str(mail.Body or '')
                    names=[str(mail.Attachments.Item(j).FileName) for j in range(1,mail.Attachments.Count+1)]
                    if not pattern.search(subject+'\n'+body+'\n'+'\n'.join(names)):continue
                    idx=len(report['matches'])+1
                    record={'id':idx,'direction':'sent' if kind==5 else 'inbox','date':str(mail.SentOn if kind==5 else mail.ReceivedTime),
                            'subject':subject,'sender_name':str(mail.SenderName or ''),'body':body,'attachments':[]}
                    for j,name in enumerate(names,1):
                        att=mail.Attachments.Item(j);a={'name':name,'size':int(att.Size)}
                        if Path(name).suffix.lower() in {'.pdf','.docx','.xlsx','.doc','.xls','.zip'} and int(att.Size)<35*1024*1024:
                            dest=OUT/f'mail_{idx:03d}'/Path(name).name;dest.parent.mkdir(exist_ok=True)
                            if not dest.exists():att.SaveAsFile(str(dest))
                            a['saved']=str(dest)
                        record['attachments'].append(a)
                    report['matches'].append(record)
        (OUT/'emails.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        for m in report['matches']:
            (OUT/f'mail_{m["id"]:03d}.md').write_text(f'# {m["subject"]}\n\nNgày: {m["date"]}\n\n{m["body"]}',encoding='utf-8')
        print(json.dumps({'folders':report['folders'],'matches':[{'id':m['id'],'date':m['date'],'direction':m['direction'],'subject':m['subject'],'attachments':[a['name'] for a in m['attachments'] if 'saved' in a]} for m in report['matches']]},ensure_ascii=False,indent=2))
    finally:pythoncom.CoUninitialize()


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
