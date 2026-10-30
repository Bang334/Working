"""Outlook classic integration. This module never sends mail."""
from contextlib import contextmanager
from app.services import workflow_service as work


@contextmanager
def outlook():
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise ValueError('Cần Outlook classic và thư viện pywin32 trên máy chạy ứng dụng.') from exc
    pythoncom.CoInitialize()
    try:
        app=win32com.client.Dispatch('Outlook.Application')
        yield app
    except Exception as exc:
        if isinstance(exc,ValueError):
            raise
        raise ValueError('Không truy cập được Outlook classic. Hãy mở Outlook và kiểm tra tài khoản đã đăng nhập.') from exc
    finally:
        pythoncom.CoUninitialize()


def create_draft(case_id,actor):
    if not actor.strip():
        raise ValueError('Nhập tên người kiểm tra bộ thư.')
    data=work.get_case(case_id)
    files=work.validate_email(data)
    with outlook() as app:
        mail=app.CreateItem(0)
        mail.To=data['recipient']
        mail.CC=data['cc']
        mail.Subject=data['subject']
        mail.Body=data['body']+'\n\nHồ sơ đính kèm / 附件：\n'+'\n'.join(f['name'] for f in files)
        prop=mail.UserProperties.Add('HongMingWorkflowCase',1)
        prop.Value=str(case_id)
        for f in files:
            mail.Attachments.Add(str(work.safe_path(f['path'])),1,1,f['name'])
        mail.Save()
        entry_id=str(mail.EntryID)
        work.record_mail(case_id,entry_id,'draft',data['subject'],data['body'],actor=actor)
    return {'entry_id':entry_id,'message':'Đã tạo nháp trong Outlook. Chưa gửi cho khách. Mở Drafts để xem và gửi.'}


def open_draft(case_id,entry_id):
    data=work.get_case(case_id)
    if not any(m['entry_id']==entry_id and m['direction']=='draft' for m in data['mail']):
        raise ValueError('Thư nháp không thuộc công việc này.')
    with outlook() as app:
        app.GetNamespace('MAPI').GetItemFromID(entry_id).Display()
    return {'message':'Đã mở thư trong Outlook để bạn kiểm tra.'}


def candidates(case_id):
    data=work.get_case(case_id)
    found=[]
    # Require an exact case tag or an exact contract token, never customer-name guessing.
    import re
    code=data['contract_code'].strip()
    with outlook() as app:
        namespace=app.GetNamespace('MAPI')
        for folder_id,direction in [(5,'sent'),(6,'inbox')]:
            items=namespace.GetDefaultFolder(folder_id).Items
            items.Sort('[SentOn]' if direction=='sent' else '[ReceivedTime]',True)
            for i in range(1,min(int(items.Count),300)+1):
                item=items.Item(i)
                if item.Class!=43:
                    continue
                subject=str(item.Subject or '')
                prop=item.UserProperties.Find('HongMingWorkflowCase')
                tagged=prop is not None and str(prop.Value)==str(case_id)
                pattern=r'(?<![\w])'+re.escape(code)+r'(?![\w])' if code else ''
                match=bool(pattern and re.search(pattern,subject,re.I))
                body=str(item.Body or '')
                body_match=bool(pattern and re.search(pattern,body,re.I))
                if not tagged and not match and not body_match:
                    continue
                found.append(dict(entry_id=str(item.EntryID),direction=direction,subject=subject,
                                  body=body[:20000],sender=str(item.SenderEmailAddress or ''),
                                  received_at=str(item.SentOn if direction=='sent' else item.ReceivedTime),
                                  match='case_tag' if tagged else 'contract_subject' if match else 'contract_body',
                                  attachments=[{'index':j,'name':str(item.Attachments.Item(j).FileName)}
                                               for j in range(1,min(int(item.Attachments.Count),50)+1)]))
    return found


def link_mail(case_id,entry_id,direction,actor):
    if not actor.strip() or direction not in {'sent','inbox'}:
        raise ValueError('Cần người kiểm tra và loại thư gửi/nhận.')
    selected=next((m for m in candidates(case_id) if m['entry_id']==entry_id and m['direction']==direction),None)
    if not selected:
        raise ValueError('Thư không nằm trong kết quả Outlook phù hợp; không tự gắn thư khác đơn.')
    work.record_mail(case_id,selected['entry_id'],selected['direction'],selected['subject'],
                     selected['body'],selected['sender'],selected['received_at'],actor)
    return work.get_case(case_id)


def import_attachment(case_id, entry_id, direction, index, role, verified_by):
    """Materialize one explicitly selected attachment without executing it."""
    selected=next((m for m in candidates(case_id) if m['entry_id']==entry_id and m['direction']==direction),None)
    if not selected or not any(a['index']==index for a in selected['attachments']):
        raise ValueError('Không tìm thấy tệp đã chọn trong thư phù hợp với công việc.')
    from pathlib import Path
    import tempfile
    with outlook() as app:
        item=app.GetNamespace('MAPI').GetItemFromID(entry_id)
        attachment=item.Attachments.Item(index)
        name=str(attachment.FileName)
        if int(attachment.Size)>25*1024*1024:
            raise ValueError('Tệp vượt giới hạn 25 MB.')
        with tempfile.TemporaryDirectory(prefix='hm_outlook_') as tmp:
            destination=Path(tmp)/('attachment'+Path(name).suffix.lower())
            attachment.SaveAsFile(str(destination))
            work.add_file(case_id,name,destination.read_bytes(),role,verified_by)
    return work.get_case(case_id)
