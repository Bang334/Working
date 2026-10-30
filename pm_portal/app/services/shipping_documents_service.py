"""Isolated export jobs, never write to contracts or receivables."""
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import zipfile
import xml.etree.ElementTree as ET
from app.config import WORKING_DIR
from app.models.shipping_documents import ShippingDocument, review_document

logger=logging.getLogger(__name__)
RESOURCES=Path(__file__).resolve().parent.parent/'resources'/'shipping_documents'
EXPORT_ROOT=WORKING_DIR/'Ho So Du An'/'Ho So Hai Quan'


def artifact_runtime():
    base=Path.home()/'.cache'/'codex-runtimes'/'codex-primary-runtime'/'dependencies'/'node'
    node=os.environ.get('SHIPPING_NODE_EXECUTABLE') or (str(base/'bin'/'node.exe') if (base/'bin'/'node.exe').exists() else shutil.which('node'))
    modules=os.environ.get('SHIPPING_NODE_MODULES') or str(base/'node_modules')
    if not node or not Path(modules,'@oai','artifact-tool').exists():
        raise RuntimeError('Chưa có bộ xuất Excel. Cần cấu hình SHIPPING_NODE_EXECUTABLE và SHIPPING_NODE_MODULES trên máy chủ.')
    return node,modules


def _print_areas(path: Path, area: str):
    """Metadata-only patch; Artifact Tool owns values, formulas and styles."""
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    q=lambda name:'{'+ns+'}'+name
    temp=path.with_suffix('.tmp')
    with zipfile.ZipFile(path) as src,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as dst:
        for entry in src.infolist():
            content=src.read(entry.filename)
            if entry.filename=='xl/workbook.xml':
                root=ET.fromstring(content);names=root.find(q('definedNames'))
                if names is None:names=ET.SubElement(root,q('definedNames'))
                pa=next((x for x in names if x.get('name')=='_xlnm.Print_Area'),None)
                if pa is None:pa=ET.SubElement(names,q('definedName'),{'name':'_xlnm.Print_Area','localSheetId':'0'})
                pa.text=area;content=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            dst.writestr(entry,content)
    try:os.replace(temp,path)
    except PermissionError:
        alternative=path.with_stem(path.stem+'_v2');os.replace(temp,alternative);return alternative
    return path


def generate(data: ShippingDocument) -> dict:
    if not data.buyer_name:
        raise ValueError('Điền tên người mua trước khi xuất file.')
    if not data.items:
        raise ValueError('Thêm ít nhất một hạng mục.')
    for index,item in enumerate(data.items,1):
        if not item.name_vi or item.quantity is None or not item.unit:
            raise ValueError(f'Dòng {index}: cần tên hàng, số lượng và đơn vị.')
    node,modules=artifact_runtime()
    token=uuid.uuid4().hex
    folder=EXPORT_ROOT/token;folder.mkdir(parents=True,exist_ok=False)
    payload=folder/'reviewed_data.json'
    payload.write_text(data.model_dump_json(indent=2),encoding='utf-8')
    env=os.environ.copy();env['NODE_PATH']=modules
    try:
        result=subprocess.run([node,str(RESOURCES/'generate.mjs'),str(payload),str(folder)],
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180,env=env,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:
            logger.error('Shipping export failed (%s): %s',token,result.stderr[-2500:])
            raise RuntimeError('Chưa xuất được file Excel. Dữ liệu trên màn hình vẫn giữ nguyên; vui lòng thử lại.')
        meta=json.loads((folder/'layout.json').read_text(encoding='utf-8'))
        for kind,name in [('invoice','Invoice.xlsx'),('packing','Packing_List.xlsx')]:
            file=folder/name
            if not file.exists():file=folder/(Path(name).stem+'_v2.xlsx')
            final=_print_areas(file,meta[kind]['printArea'])
            meta[kind]['filename']=final.name
        (folder/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
    except Exception as exc:
        # Never return download URLs for an incomplete pair.
        if isinstance(exc,subprocess.TimeoutExpired):raise RuntimeError('Xuất Excel quá thời gian. Vui lòng thử lại hoặc chia nhỏ đơn hàng.') from exc
        raise
    return dict(job_id=token,review=review_document(data),downloads={k:f'/api/shipping-documents/download/{token}/{k}' for k in ['invoice','packing']})


def download_path(token: str, kind: str) -> Path:
    if not re.fullmatch(r'[a-f0-9]{32}',token) or kind not in {'invoice','packing'}:
        raise FileNotFoundError('Không tìm thấy bộ hồ sơ.')
    folder=EXPORT_ROOT/token
    manifest=folder/'manifest.json'
    if not manifest.exists():raise FileNotFoundError('Bộ hồ sơ chưa hoàn tất hoặc không tồn tại.')
    filename=json.loads(manifest.read_text(encoding='utf-8'))[kind]['filename']
    target=folder/filename
    if target.parent.resolve()!=folder.resolve() or not target.is_file():raise FileNotFoundError('Không tìm thấy file.')
    return target
