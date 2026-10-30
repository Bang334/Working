// Public Artifact Tool API. Header/style masters are local immutable resources.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {FileBlob,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const resources=path.dirname(fileURLToPath(import.meta.url));
const input=JSON.parse(await fs.readFile(process.argv[2],'utf8'));
const out=process.argv[3];
const layout=JSON.parse(await fs.readFile(path.join(resources,'layout.json'),'utf8'));
const text=v=>{const s=String(v??'');return /^[=+@]/.test(s)?"'"+s:s;};
const join=(...parts)=>parts.filter(Boolean).join('\n');
const n=v=>v==null||v===''?null:Number(v);
function height(value,width,size=11){
 let lines=0;
 for(const line of String(value??'').split('\n')){
  const units=[...line].reduce((a,c)=>a+(/[\u2e80-\uffef]/.test(c)?2:1),0);
  lines+=Math.max(1,Math.ceil(units/width));
 }
 const result=Math.max(24,lines*(size+3)+8);
 if(result>409)throw new Error('Nội dung một ô quá dài; vui lòng rút gọn tên hoặc mô tả trước khi xuất.');
 return result;
}
function write(sh,addr,value){sh.getRange(addr).values=[[typeof value==='string'?text(value):value]];}
function numeric(sh,addr,value){write(sh,addr,n(value));sh.getRange(addr).setNumberFormat(Number.isInteger(n(value))?'#,##0':'#,##0.00###');}
const stats={};
for(const kind of ['invoice','packing']){
 const master=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(resources,kind+'.xlsx')));
 const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(resources,kind+'.xlsx')));
 const sh=wb.worksheets.getItemAt(0),src=master.worksheets.getItemAt(0);
 const start=kind==='invoice'?17:13;
 for(const m of layout[kind].merges){
  const row=Number(m.match(/\d+/)[0]);
  if(row>=start)sh.unmergeCells(m);
 }
 sh.getRange(kind==='invoice'?'A17:T60':'A13:I65').clear({applyTo:'all'});
 sh.freezePanes.unfreeze();sh.showGridLines=false;
 const date=input.issue_date.split('-').reverse().join('/');
 if(kind==='invoice'){
  write(sh,'C1',input.seller_name);write(sh,'C2',input.seller_address);
  write(sh,'C3',join(input.seller_phone&&'TEL: '+input.seller_phone,input.seller_email));
  write(sh,'C5','INVOICE');write(sh,'D6',input.invoice_no);write(sh,'J6','DATE: '+date);
  write(sh,'E7','PAYMENT TERM: '+input.payment_term);
  sh.unmergeCells('C8:D8');sh.mergeCells('C8:E8');sh.mergeCells('F8:K8');
  write(sh,'C8',input.buyer_name);write(sh,'F8','SHIPMENT TERM: '+input.shipment_term);
  write(sh,'C9',input.buyer_address);write(sh,'C11','TEL: '+input.buyer_phone);write(sh,'C12','MAIL: '+input.buyer_email);
  write(sh,'C13','FROM: '+input.departure+'    TO: '+input.destination);
  write(sh,'C14','CONTRACT NO.: '+input.contract_no);write(sh,'J10','C/NO.: '+input.package_count);
  write(sh,'J12','INCOTERM : '+input.incoterm);write(sh,'J13','ON BOARD DAY: '+input.on_board_date);write(sh,'J14','L/C NO.: '+input.lc_no);
  write(sh,'K15','Unit Price '+input.currency);write(sh,'L15','Total Price '+input.currency);
  sh.getRange('C8:E8').format.wrapText=true;sh.getRange('F8:K8').format.wrapText=true;
  sh.getRange('A8:L8').format.rowHeight=Math.max(height(input.buyer_name,65),height(input.shipment_term,65));
  sh.getRange('A7:L7').format.rowHeight=height(input.payment_term,100);
  sh.getRange('A9:L10').format.rowHeight=Math.max(18,height(input.buyer_address,65)/2);
  let row=17,previous=null;const detailRows=[];
  for(let i=0;i<input.items.length;i++){
   const it=input.items[i];
   if(it.group&&it.group!==previous){
    sh.getRange(`A${row}:L${row}`).copyFrom(src.getRange('A17:L17'),'all');
    sh.mergeCells(`A${row}:L${row}`);write(sh,`A${row}`,it.group);
    sh.getRange(`A${row}:L${row}`).format.rowHeight=height(it.group,160);row++;
   }
   previous=it.group;
   sh.getRange(`A${row}:L${row}`).copyFrom(src.getRange('A18:L18'),'all');
   sh.mergeCells(`C${row}:E${row}`);
   write(sh,`A${row}`,i+1);write(sh,`B${row}`,join(it.name_vi,it.name_zh));
   sh.getRange(`B${row}`).format.horizontalAlignment='center';
   sh.getRange(`B${row}`).format.verticalAlignment='center';
   const desc=join(it.description,it.model&&!it.description.includes(it.model)?it.model:'');
   write(sh,`C${row}`,desc);write(sh,`F${row}`,it.origin);write(sh,`H${row}`,it.source);
   numeric(sh,`J${row}`,it.quantity);
   sh.getRange(`J${row}`).setNumberFormat((Number.isInteger(n(it.quantity))?'#,##0':'#,##0.00###')+(it.unit?' "'+it.unit.replaceAll('"','""')+'"':''));
   numeric(sh,`K${row}`,it.unit_price);
   sh.getRange(`L${row}`).formulas=[['=IF(OR(J'+row+'="",K'+row+'=""),"",J'+row+'*K'+row+')']];
   sh.getRange(`L${row}`).setNumberFormat(Number.isInteger(n(it.quantity)*n(it.unit_price))?'#,##0':'#,##0.00');
   sh.getRange(`A${row}:L${row}`).format.wrapText=true;
   sh.getRange(`A${row}:L${row}`).format.rowHeight=Math.max(height(join(it.name_vi,it.name_zh),19),height(desc,90),height(it.origin,14),height(it.unit,18));
   detailRows.push(row);row++;
  }
  sh.getRange(`A${row}:L${row}`).copyFrom(src.getRange('A40:L40'),'all');
  sh.mergeCells(`A${row}:J${row}`);write(sh,`K${row}`,'TỔNG / 總價');
  sh.getRange(`L${row}`).formulas=[['=IF(COUNT(L17:L'+(row-1)+')='+input.items.length+',SUM(L17:L'+(row-1)+'),"")']];
  sh.getRange(`A${row}:L${row}`).format.rowHeight=34;
  stats[kind]={lastRow:row,printArea:`'INV'!$A$1:$L$${row}`,detailRows,total:`L${row}`};
 }else{
  write(sh,'A1',join(input.seller_name,'HONG MING GLOBAL COMPANY LIMITED','Địa chỉ: '+input.seller_address,'Tel: '+input.seller_phone+' Email: '+input.seller_email));
  write(sh,'B4','PHIẾU ĐÓNG GÓI CHI TIẾT / PACKING LIST');
  write(sh,'A7',input.buyer_name);write(sh,'A8',input.buyer_address);
  write(sh,'G7',input.packing_no);write(sh,'G8',date);write(sh,'G9',input.contract_no);write(sh,'G10',input.shipment_term);
  sh.mergeCells('G10:H11');sh.getRange('G10:H11').format.wrapText=true;
  sh.getRange('A10:H11').format.rowHeight=Math.max(18,height(input.shipment_term,23,9)/2);
  sh.getRange('A7:H7').format.rowHeight=height(input.buyer_name,72,9);
  sh.getRange('A8:H8').format.rowHeight=height(input.buyer_address,72,9);
  const items=input.items.filter(i=>i.include_in_packing&&i.kind==='goods');
  const detailRows=[];let row=13;
  for(let i=0;i<items.length;i++,row++){
   const it=items[i];
   sh.getRange(`A${row}:H${row}`).copyFrom(src.getRange('A13:H13'),'all');
   for(const pair of [['B','C'],['E','F'],['G','H']])sh.mergeCells(`${pair[0]}${row}:${pair[1]}${row}`);
   write(sh,`A${row}`,i+1);const desc=join(it.description||join(it.name_vi,it.name_zh),it.model&&!it.description.includes(it.model)?it.model:'');
   write(sh,`B${row}`,desc);numeric(sh,`D${row}`,it.quantity);
   sh.getRange(`B${row}:C${row}`).format.horizontalAlignment='center';
   sh.getRange(`B${row}:C${row}`).format.verticalAlignment='center';
   sh.getRange(`D${row}`).setNumberFormat((Number.isInteger(n(it.quantity))?'#,##0':'#,##0.00###')+(it.unit?' "'+it.unit.replaceAll('"','""')+'"':''));
   numeric(sh,`E${row}`,it.unit_weight_kg);
   const fallback=it.total_weight_kg==null?'""':Number(it.total_weight_kg);
   sh.getRange(`G${row}`).formulas=[['=IF(E'+row+'="",'+fallback+',E'+row+'*D'+row+')']];
   sh.getRange(`G${row}`).setNumberFormat('#,##0.000');
   sh.getRange(`A${row}:H${row}`).format.wrapText=true;
   sh.getRange(`A${row}:H${row}`).format.rowHeight=Math.max(height(desc,43,9),height(it.unit,12,9));detailRows.push(row);
  }
  sh.getRange(`A${row}:H${row}`).copyFrom(src.getRange('A33:H33'),'all');
  for(const pair of [['B','C'],['E','F'],['G','H']])sh.mergeCells(`${pair[0]}${row}:${pair[1]}${row}`);
  write(sh,`A${row}`,'TOTAL :');
  sh.getRange(`G${row}`).formulas=[[items.length?'=IF(COUNT(G13:G'+(row-1)+')='+items.length+',SUM(G13:G'+(row-1)+'),"")':'=""']];
  sh.getRange(`A${row}:H${row}`).format.rowHeight=24;
  sh.getRange(`F${row+2}:H${row+4}`).copyFrom(src.getRange('F35:H37'),'all');
  write(sh,`F${row+4}`,input.seller_representative);
  sh.getRange(`A${row+2}:H${row+4}`).format.rowHeight=38;
  stats[kind]={lastRow:row+4,printArea:`'Packing List'!$A$1:$H$${row+4}`,detailRows,total:`G${row}`};
 }
 wb.recalculate();
 const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!',options:{useRegex:true,maxResults:10},maxChars:1000});
 if(errors.ndjson.includes('"kind":"match"'))throw new Error('Công thức Excel chưa hợp lệ.');
 const filename=kind==='invoice'?'Invoice.xlsx':'Packing_List.xlsx';
 try{await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,filename));}
 catch(error){if(error.code==='EACCES'||error.code==='EPERM')await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,filename.replace('.xlsx','_v2.xlsx')));else throw error;}
 if(process.env.SHIPPING_QA_RENDER==='1'){
  const pic=await wb.render({sheetName:layout[kind].sheet,range:kind==='invoice'?`A1:L${Math.min(stats[kind].lastRow,25)}`:`A1:H${Math.min(stats[kind].lastRow,20)}`,scale:1,format:'png'});
  await fs.writeFile(path.join(out,kind+'_preview.png'),new Uint8Array(await pic.arrayBuffer()));
 }
}
await fs.writeFile(path.join(out,'layout.json'),JSON.stringify(stats));
