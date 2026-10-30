from pathlib import Path
import re,os,zipfile
import xml.etree.ElementTree as E
import openpyxl
P=Path('D:/Working/outputs/seiyo_20261030')
N='http://schemas.openxmlformats.org/spreadsheetml/2006/main';q=lambda t:'{'+N+'}'+t
def shift(s):return re.sub(r'(\$?[A-Z]+\$?)(\d+)',lambda m:m[1]+str(max(1,int(m[2])-15)),s)
for kind,outname,area in [('invoice','INVOICE_HONG_MING_SEIYO_20261030.xlsx',"'INV'!$A$1:$L$40"),('packing','PKL_HONG_MING_SEIYO_20261030.xlsx',"'Packing List'!$A$1:$H$37")]:
 target=P/outname;temp=target.with_suffix('.tmp')
 with zipfile.ZipFile(P/(kind+'_header_corrected.xlsx')) as src,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as dst:
  for item in src.infolist():
   data=src.read(item.filename)
   if item.filename=='xl/worksheets/sheet1.xml' and kind=='invoice':
    root=E.fromstring(data);sd=root.find(q('sheetData'))
    for row in list(sd):
     old=int(row.get('r'))
     if old<16:sd.remove(row);continue
     row.set('r',str(old-15))
     for c in row:
      c.set('r',shift(c.get('r')))
      f=c.find(q('f'))
      if f is not None and f.text:f.text=shift(f.text)
    for tag,att in [('mergeCell','ref'),('dimension','ref'),('autoFilter','ref'),('sheetView','topLeftCell'),('selection','activeCell'),('selection','sqref')]:
     for el in root.iter(q(tag)):
      if el.get(att):el.set(att,shift(el.get(att)))
    data=E.tostring(root,encoding='utf-8',xml_declaration=True)
   if item.filename=='xl/workbook.xml':
    root=E.fromstring(data);dn=root.find(q('definedNames'))
    if dn is None:dn=E.SubElement(root,q('definedNames'))
    for el in dn:
     if kind=='invoice' and el.text:el.text=shift(el.text)
    pa=next((el for el in dn if el.get('name')=='_xlnm.Print_Area'),None)
    if pa is None:pa=E.SubElement(dn,q('definedName'),{'name':'_xlnm.Print_Area','localSheetId':'0'})
    pa.text=area;data=E.tostring(root,encoding='utf-8',xml_declaration=True)
   dst.writestr(item,data)
 try:os.replace(temp,target)
 except PermissionError:
  target=target.with_stem(target.stem+'_v2');os.replace(temp,target)
 w=openpyxl.load_workbook(target);s=w.active;v=openpyxl.load_workbook(target,data_only=True).active
 if kind=='invoice':
  assert s['C5'].value=='INVOICE'
  assert v['L40'].value==712020000
  assert s['J6'].value=='DATE: 30/10/2026'
  assert sum(c.value=='INVOICE' for row in s for c in row)==1
  assert [s[f'A{r}'].value for r in list(range(18,28))+list(range(29,40))]==list(range(1,22))
 else:
  assert s['B4'].value=='PHIẾU ĐÓNG GÓI CHI TIẾT / PACKING LIST'
  assert [s[f'A{r}'].value for r in range(13,33)]==list(range(1,21))
  assert all(v[f'E{r}'].value is None for r in range(13,33))
 assert not any('DỰ THẢO' in str(c.value) for row in s for c in row)
 assert not any(c.data_type=='e' for row in v for c in row)
 print('Verified',target,s.print_area)
