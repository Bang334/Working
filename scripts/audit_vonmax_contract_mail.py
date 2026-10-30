"""Read-only Outlook audit for Vonmax contracts, using non-guarded properties."""
import json
import re
import sys
from pathlib import Path

import pythoncom
import win32com.client

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.qa'/'vonmax_contract_mail'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pythoncom.CoInitialize()
    report={'folders':[],'matches':[]}
    try:
        app=win32com.client.Dispatch('Outlook.Application');ns=app.GetNamespace('MAPI')
        seen=set()
        for kind in [5,6]:
            base=ns.GetDefaultFolder(kind)
            folders=[base]
            while folders:
                folder=folders.pop()
                for i in range(1,int(folder.Folders.Count)+1):folders.append(folder.Folders.Item(i))
                items=folder.Items;items.Sort('[SentOn]' if kind==5 else '[ReceivedTime]',True)
                count=min(int(items.Count),1200)
                report['folders'].append({'folder':str(folder.Name),'available':int(items.Count),'scanned':count,'direction':'sent' if kind==5 else 'inbox'})
                for i in range(1,count+1):
                    mail=items.Item(i)
                    if mail.Class!=43:continue
                    entry=str(mail.EntryID)
                    if entry in seen:continue
                    seen.add(entry)
                    subject=str(mail.Subject or '');body=str(mail.Body or '')
                    if not re.search(r'von\s*max|弘聲|弘声|HMV060620250001|HMV07032026001',subject+'\n'+body,re.I):continue
                    index=len(report['matches'])+1
                    result={'direction':'sent' if kind==5 else 'inbox','date':str(mail.SentOn if kind==5 else mail.ReceivedTime),
                            'subject':subject,'sender_name':str(mail.SenderName or ''),'body':body[:60000],'attachments':[]}
                    for j in range(1,int(mail.Attachments.Count)+1):
                        att=mail.Attachments.Item(j);name=str(att.FileName)
                        record={'name':name,'size':int(att.Size)}
                        if Path(name).suffix.lower() in {'.pdf','.docx','.xlsx','.doc','.xls','.zip'} and int(att.Size)<35*1024*1024:
                            dest=OUT/f'mail_{index:03d}'/Path(name).name;dest.parent.mkdir(exist_ok=True)
                            if not dest.exists():att.SaveAsFile(str(dest))
                            record['saved']=str(dest)
                        result['attachments'].append(record)
                    report['matches'].append(result)
        (OUT/'mail_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'folders':report['folders'],'matches':[{'i':i+1,'direction':m['direction'],'date':m['date'],'subject':m['subject'],'attachments':m['attachments']} for i,m in enumerate(report['matches'])]},ensure_ascii=False,indent=2))
    finally:pythoncom.CoUninitialize()


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
