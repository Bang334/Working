"""Move the old six-item divider after item ten, retaining row and cell styles."""
from pathlib import Path
import zipfile,re,copy,json,sys
import xml.etree.ElementTree as ET
import openpyxl
ROOT=Path('D:/Working/outputs/seiyo_20261030')
N='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
def q(t):return '{'+N+'}'+t
source=ROOT/'INVOICE_HONG_MING_SEIYO_20261030_DU_THAO.xlsx'
stage=ROOT/'invoice_group_layout.xlsx'
mapping={39:43,40:39,41:40,42:41,43:42}
def addr(s):
 return re.sub(r'(\$?[A-Z]+\$?)(\d+)',lambda m:m[1]+str(mapping.get(int(m[2]),int(m[2]))),s)
with zipfile.ZipFile(source) as z:
 root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
 sd=root.find(q('sheetData'))
 for row in sd:
  rn=int(row.attrib['r'])
  if rn in mapping:
   row.attrib['r']=str(mapping[rn])
   for cell in row:
    cell.attrib['r']=addr(cell.attrib['r'])
    f=cell.find(q('f'))
    if f is not None and f.text:f.text=addr(f.text)
 sd[:]=sorted(sd,key=lambda r:int(r.attrib['r']))
 for merge in root.find(q('mergeCells')):merge.attrib['ref']=addr(merge.attrib['ref'])
 for c in root.iter(q('c')):
  if c.attrib['r']=='L63':c.find(q('f')).text='SUM(L33:L42,L44:L62)'
 with zipfile.ZipFile(stage,'w',zipfile.ZIP_DEFLATED) as out:
  for e in z.infolist():out.writestr(e,ET.tostring(root,encoding='utf-8',xml_declaration=True) if e.filename=='xl/worksheets/sheet1.xml' else z.read(e.filename))
print(stage)
if len(sys.argv)>1:
 with zipfile.ZipFile(ROOT/'invoice_groups_authored.xlsx') as a:
  ar=ET.fromstring(a.read('xl/worksheets/sheet1.xml'))
  cells={c.attrib['r']:c for c in ar.iter(q('c'))}
  strings=[''.join(s.itertext()) for s in ET.fromstring(a.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in a.namelist() else []
 with zipfile.ZipFile(stage) as z:
  root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
  for cell in root.iter(q('c')):
   if cell.attrib['r'] not in ['A32','A43','L63']:continue
   ac=cells[cell.attrib['r']]
   for child in list(cell):cell.remove(child)
   cell.attrib.pop('t',None)
   if ac.attrib.get('t')=='s':
    cell.attrib['t']='inlineStr';ET.SubElement(ET.SubElement(cell,q('is')),q('t')).text=strings[int(ac.find(q('v')).text)]
   else:
    if ac.attrib.get('t'):cell.attrib['t']=ac.attrib['t']
    for child in ac:cell.append(copy.deepcopy(child))
  target=ROOT/'INVOICE_HONG_MING_SEIYO_20261030_DU_THAO_v2.xlsx'
  try:
   out=zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED)
  except PermissionError:
   target=target.with_stem(target.stem+'_v2');out=zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED)
  with out:
   for e in z.infolist():out.writestr(e,ET.tostring(root,encoding='utf-8',xml_declaration=True) if e.filename=='xl/worksheets/sheet1.xml' else z.read(e.filename))
 v=openpyxl.load_workbook(target,data_only=True).active
 f=openpyxl.load_workbook(target,data_only=False).active
 assert v['L63'].value==712020000
 assert [v[f'A{r}'].value for r in range(33,43)]==list(range(1,11))
 assert [v[f'A{r}'].value for r in range(44,55)]==list(range(11,22))
 for r in list(range(33,43))+list(range(44,55)):
  assert f[f'L{r}'].value.startswith(f'=K{r}*')
 assert 'A43:L43' in str(f.merged_cells) and 'A39:L39' not in str(f.merged_cells)
 print('Verified 10 hardware + 11 materials/services, total 712020000:',target)
