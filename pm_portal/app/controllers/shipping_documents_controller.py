import json
from zipfile import BadZipFile
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from app.models.shipping_documents import ShippingDocument
from app.services import shipping_documents_ai_service as ai
from app.services import shipping_documents_service as exporter

router=APIRouter(prefix='/api/shipping-documents',tags=['Invoice & Packing List'])


@router.post('/analyze')
async def analyze(files: list[UploadFile] = File(default=[]), roles: str = Form('[]'), texts: str = Form('[]')):
    try:
        file_roles=json.loads(roles);notes=json.loads(texts)
        if not isinstance(file_roles,list) or any(r not in ['order','reference'] for r in file_roles):
            raise ValueError('Loại nguồn tài liệu không hợp lệ.')
        if len(file_roles)!=len(files) or len(files)>20:
            raise ValueError('Tối đa 20 file; mỗi file phải có loại nguồn tương ứng.')
        if not isinstance(notes,list) or any(not isinstance(x,str) for x in notes):
            raise ValueError('Nội dung bổ sung phải là các đoạn văn bản.')
        sections=[];parts=[];size=0
        for file,role in zip(files,file_roles):
            content=await file.read(ai.MAX_FILE_BYTES+1);size+=len(content)
            if size>ai.MAX_TOTAL_BYTES:raise ValueError('Tổng dung lượng tối đa 25 MB.')
            section,inline=await run_in_threadpool(ai.extract_file,file.filename or '',content,role)
            sections.append(section)
            if inline:parts.extend([{'text':f'Nguồn {section["filename"]}, role={role}'}]+inline)
        result=await run_in_threadpool(ai.analyze,sections,parts,notes)
        return dict(status='success',**result,sources=[dict(filename=s['filename'],role=s['role']) for s in sections])
    except (ValueError,BadZipFile) as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        # Provider URLs/credentials must never appear in the browser.
        raise HTTPException(502,'AI chưa xử lý được tài liệu. Vui lòng thử lại hoặc kiểm tra cấu hình AI trong hệ thống.') from exc
    finally:
        for file in files:await file.close()


@router.post('/generate')
async def generate(payload: ShippingDocument):
    try:return dict(status='success',**await run_in_threadpool(exporter.generate,payload))
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    except RuntimeError as exc:raise HTTPException(503,str(exc)) from exc


@router.get('/download/{token}/{kind}')
async def download(token: str, kind: str):
    try:path=exporter.download_path(token,kind)
    except FileNotFoundError as exc:raise HTTPException(404,str(exc)) from exc
    return FileResponse(path,filename=path.name,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
