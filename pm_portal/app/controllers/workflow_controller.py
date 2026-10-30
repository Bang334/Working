"""Guided operational workflows. All mutations require explicit user actions."""
import functools
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from app.services import workflow_service as work
from app.services import workflow_outlook_service as outlook
from app import database

router=APIRouter(tags=['Việc cần làm'])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent/'templates'))


def guarded(fn):
    @functools.wraps(fn)
    async def wrapped(*args,**kwargs):
        try:
            return await fn(*args,**kwargs)
        except (ValueError,TypeError,KeyError) as exc:
            return JSONResponse(status_code=400,content={'status':'error','message':str(exc)})
    return wrapped


@router.get('/workflows')
async def page(request:Request):
    return templates.TemplateResponse(request,'workflow_page.html',{'request':request,
        'active_tab':'workflows','page_title':'Công việc & hồ sơ dự án'})


@router.get('/api/workflows')
@guarded
async def listing():
    work.init_schema()
    from app.services import project_sync_service as projects
    projects.init_schema()
    projects.sync_sources()
    return {'cases':work.list_cases(),'templates':{k:v[0] for k,v in work.TEMPLATES.items()},'roles':work.ROLES,'sources':work.sources()}


@router.post('/api/workflows')
@guarded
async def create(payload:dict):
    return work.create_case(payload)


@router.get('/api/workflows/{case_id}')
@guarded
async def detail(case_id:int):
    return work.get_case(case_id)


@router.patch('/api/workflows/{case_id}')
@guarded
async def update(case_id:int,payload:dict):
    return work.update_case(case_id,payload)


@router.post('/api/workflows/{case_id}/advance')
@guarded
async def advance(case_id:int,payload:dict):
    return work.advance(case_id,int(payload['stage']),str(payload.get('actor','')),str(payload.get('note','')))


@router.post('/api/workflows/{case_id}/condition')
@guarded
async def condition(case_id:int,payload:dict):
    return work.confirm_condition(case_id,payload)


@router.post('/api/workflows/{case_id}/reopen')
@guarded
async def reopen(case_id:int,payload:dict):
    return work.reopen(case_id,str(payload.get('actor','')),str(payload.get('reason','')))


@router.post('/api/workflows/{case_id}/files')
@guarded
async def upload(case_id:int,file:UploadFile=File(...),role:str=Form(...),verified_by:str=Form('')):
    content=await file.read(25*1024*1024+1)
    work.add_file(case_id,file.filename or 'file',content,role,verified_by)
    return work.get_case(case_id)


@router.get('/api/workflows/files/{file_id}/download')
@guarded
async def download(file_id:int):
    with work.connection() as c:
        f=c.execute('SELECT * FROM workflow_files WHERE id=?',(file_id,)).fetchone()
    if not f:
        raise ValueError('Không tìm thấy tệp.')
    path=work.safe_path(f['path'])
    if not path.is_file():
        raise ValueError('Tệp đã bị di chuyển; cần tải lại hồ sơ.')
    return FileResponse(path,filename=f['name'],content_disposition_type='inline' if path.suffix=='.pdf' else 'attachment')


@router.post('/api/workflows/{case_id}/generate-request')
@guarded
async def generate_request(case_id:int,payload:dict):
    data=work.get_case(case_id)
    if data['kind']!='payment' or data['stage']!=1 or not data['milestone']['triggered']:
        raise ValueError('Kiểm tra và hoàn tất điều kiện thu trước khi lập phiếu.')
    if data['currency']!='VND':
        raise ValueError('Mẫu phiếu hiện dùng VND. Với ngoại tệ, lập đúng mẫu riêng rồi tải vào công việc để kiểm tra.')
    actor=str(payload.get('actor','')).strip()
    if not actor:
        raise ValueError('Nhập tên người lập hồ sơ.')
    # Existing template engines preserve the company forms. Draft files are never signed scans.
    from app.services.payment_request_excel_service import generate_payment_request_excel
    result=await run_in_threadpool(generate_payment_request_excel,contract_code=data['contract_code'],
        milestone_name=data['title'],amount=data['amount'],due_date=data['due_date'],
        percentage=data['milestone']['percentage'],customer_name_vi=data['customer'])
    path=Path(result['word_file_path'])
    work.add_file(case_id,path.name,path.read_bytes(),'draft',actor)
    excel=Path(result['file_path'])
    work.add_file(case_id,excel.name,excel.read_bytes(),'draft',actor)
    return work.get_case(case_id)


@router.get('/api/workflows/{case_id}/email-suggestion')
@guarded
async def suggest(case_id:int):
    return work.email_text(case_id)


@router.post('/api/workflows/{case_id}/outlook-draft')
@guarded
async def draft(case_id:int,payload:dict):
    return await run_in_threadpool(outlook.create_draft,case_id,str(payload.get('actor','')))


@router.post('/api/workflows/{case_id}/open-draft')
@guarded
async def open_draft(case_id:int,payload:dict):
    return await run_in_threadpool(outlook.open_draft,case_id,str(payload.get('entry_id','')))


@router.get('/api/workflows/{case_id}/outlook')
@guarded
async def sync(case_id:int):
    return {'candidates':await run_in_threadpool(outlook.candidates,case_id)}


@router.post('/api/workflows/{case_id}/link-mail')
@guarded
async def link(case_id:int,payload:dict):
    return await run_in_threadpool(outlook.link_mail,case_id,str(payload.get('entry_id','')),
                                  str(payload.get('direction','')),str(payload.get('actor','')))


@router.post('/api/workflows/{case_id}/manual-mail')
@guarded
async def manual(case_id:int,payload:dict):
    data=work.get_case(case_id)
    if not work.has_file(data,'evidence') or not str(payload.get('note','')).strip():
        raise ValueError('Tải bằng chứng gửi thư và ghi căn cứ xác nhận trước.')
    work.record_mail(case_id,str(payload.get('reference','')),'sent',str(payload.get('note','')),
                     actor=str(payload.get('actor','')))
    return work.get_case(case_id)


@router.post('/api/workflows/{case_id}/outlook-attachment')
@guarded
async def import_attachment(case_id:int,payload:dict):
    return await run_in_threadpool(outlook.import_attachment,case_id,str(payload.get('entry_id','')),
        str(payload.get('direction','')),int(payload.get('index',0)),str(payload.get('role','')),
        str(payload.get('verified_by','')))


@router.post('/api/workflows/{case_id}/receipts')
@guarded
async def receipt(case_id:int,payload:dict):
    return work.add_receipt(case_id,payload)


@router.get('/api/workflows/{case_id}/project')
@guarded
async def project_context(case_id:int):
    from app.services import project_sync_service as projects
    projects.init_schema()
    result=projects.context(case_id)
    kind=work.get_case(case_id)['kind']
    result['actions']={k:v[2] for k,v in projects.ACTIONS.items() if v[0]==kind}
    result['documents']=projects.documents(case_id)
    return result


@router.post('/api/workflows/{case_id}/project-link')
@guarded
async def project_link(case_id:int,payload:dict):
    from app.services import project_sync_service as projects
    return projects.link(case_id,payload)


@router.post('/api/workflows/{case_id}/project-confirm')
@guarded
async def project_confirm(case_id:int,payload:dict):
    from app.services import project_sync_service as projects
    return projects.confirm(case_id,payload)


@router.post('/api/workflows/{case_id}/project-document')
@guarded
async def project_document(case_id:int,payload:dict):
    from app.services import project_sync_service as projects
    return projects.import_document(case_id,payload)
