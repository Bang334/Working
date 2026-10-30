(() => {
 'use strict';
 const $=id=>document.getElementById(id);
 let attachments=[],data=null,busy=false,revision=0;
 const numericFields=new Set(['quantity','unit_price','unit_weight_kg','total_weight_kg']);
 const mainFields=[['buyer_name','Tên người mua'],['buyer_address','Địa chỉ người mua'],['issue_date','Ngày phát hành','date'],['invoice_no','Số Invoice'],['packing_no','Số Packing List'],['contract_no','Số hợp đồng'],['buyer_phone','Điện thoại người mua'],['buyer_email','Email người mua'],['currency','Tiền tệ'],['payment_term','Điều khoản thanh toán'],['shipment_term','Phương thức vận chuyển'],['incoterm','Điều kiện giao hàng']];
 const sellerFields=[['seller_name','Tên bên bán'],['seller_address','Địa chỉ bên bán'],['seller_phone','Điện thoại bên bán'],['seller_email','Email bên bán'],['seller_representative','Đại diện bên bán'],['departure','Nơi đi'],['destination','Nơi đến'],['on_board_date','Ngày giao hàng'],['package_count','Số kiện'],['lc_no','Số L/C'],['notes','Ghi chú']];
 function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
 function error(message=''){$('shipError').textContent=message;$('shipError').hidden=!message;}
 function dirty(){revision++;$('shipDownloads').hidden=true;summary();}
 function setBusy(value){busy=value;for(const id of ['shipAnalyze','shipGenerate','shipAddItem','shipAddNote','shipFiles'])$(id).disabled=value;document.querySelectorAll('#shipFileList select,#shipNotes textarea,#shipNotes button').forEach(e=>e.disabled=value);}
 function addNote(value=''){
  const box=el('div','ship-note'),label=el('label','',`Nội dung bổ sung ${$('shipNotes').children.length+1}`),row=el('div');
  const text=el('textarea');text.value=value;text.placeholder='Dán nội dung đơn hàng, email, ghi chú giao hàng hoặc yêu cầu bổ sung…';text.setAttribute('aria-label',label.textContent);text.maxLength=100000;
  const remove=el('button','ship-btn secondary','Xóa');remove.type='button';remove.onclick=()=>{if(!busy)box.remove();};
  row.append(text,remove);box.append(label,row);$('shipNotes').append(box);
 }
 function renderFiles(){
  const list=$('shipFileList');list.replaceChildren();
  attachments.forEach((entry,index)=>{
   const row=el('div','ship-file'),name=el('span','',entry.file.name+' · '+(entry.file.size/1024/1024).toFixed(2)+' MB');
   const role=el('select');role.setAttribute('aria-label','Loại nguồn '+entry.file.name);
   [['order','Đơn hàng / dữ liệu mới'],['reference','Mẫu / tham khảo']].forEach(([v,t])=>{const o=el('option','',t);o.value=v;role.append(o);});role.value=entry.role;
   role.onchange=()=>entry.role=role.value;
   const remove=el('button','ship-btn secondary','Xóa');remove.type='button';remove.onclick=()=>{if(!busy){attachments.splice(index,1);renderFiles();}};
   row.append(name,role,remove);list.append(row);
  });
 }
 function addFiles(files){
  if(busy)return;
  const combined=[...attachments];
  for(const file of files){
   if(!/\.(xlsx|docx|pdf|png|jpe?g|webp|txt|csv|tsv)$/i.test(file.name)){error('Định dạng chưa hỗ trợ: '+file.name);continue;}
   if(file.size>10*1024*1024){error(file.name+': tối đa 10 MB/file.');continue;}
   if(!combined.some(x=>x.file.name===file.name&&x.file.size===file.size&&x.file.lastModified===file.lastModified))combined.push({file,role:'order'});
  }
  if(combined.length>20||combined.reduce((n,x)=>n+x.file.size,0)>25*1024*1024){error('Tối đa 20 file, tổng dung lượng 25 MB.');return;}
  attachments=combined;renderFiles();
 }
 async function api(url,options){
  const response=await fetch(url,options);let result;try{result=await response.json();}catch{throw new Error('Máy chủ chưa phản hồi hợp lệ. Vui lòng thử lại.');}
  if(!response.ok){let detail=result.detail||result.message||'Không xử lý được yêu cầu.';if(Array.isArray(detail))detail=detail.map(x=>`${x.loc.slice(1).join('.')}: ${x.msg}`).join('\n');throw new Error(detail);}
  return result;
 }
 function fields(list,id){
  $(id).replaceChildren();
  list.forEach(([key,label,type])=>{
   const wrapper=el('label','ship-field',label),input=el(key.includes('address')||key==='notes'?'textarea':'input');
   if(input.tagName==='INPUT')input.type=type||'text';input.value=data[key]??'';input.dataset.field=key;
   input.oninput=()=>{data[key]=input.value;dirty();};wrapper.append(input);$(id).append(wrapper);
  });
 }
 function itemInput(item,key,label,type='text'){
  const box=el('div'),caption=el('label','',label),input=el(type==='textarea'?'textarea':'input');
  if(input.tagName==='INPUT')input.type=type;input.value=item[key]??'';input.dataset.itemField=key;input.setAttribute('aria-label',label);
  if(type==='number'){input.min=key==='quantity'?'0.000001':'0';input.step='any';}
  input.oninput=()=>{item[key]=numericFields.has(key)?(input.value===''?null:Number(input.value)):input.value;dirty();};box.append(caption,input);return box;
 }
 function renderItems(){
  $('shipItems').replaceChildren();
  data.items.forEach((item,index)=>{
   const row=el('tr');row.append(el('td','',index+1));
   const desc=el('td');desc.append(itemInput(item,'name_vi','Tên tiếng Việt'),itemInput(item,'name_zh','Tên tiếng Trung Phồn thể'),itemInput(item,'description','Mô tả / quy cách','textarea'),itemInput(item,'model','Model'));
   const group=el('td');group.append(itemInput(item,'group','Nhóm theo đơn hàng'));
   const kind=el('select');kind.setAttribute('aria-label','Loại hạng mục');[['goods','Hàng hóa / vật tư'],['service','Dịch vụ / thi công']].forEach(([v,t])=>{const o=el('option','',t);o.value=v;kind.append(o);});kind.value=item.kind;group.append(kind);
   const qty=el('td');qty.append(itemInput(item,'quantity','Số lượng','number'),itemInput(item,'unit','Đơn vị'));
   const price=el('td');price.append(itemInput(item,'unit_price','Đơn giá bán','number'));
   const weights=el('td');weights.append(itemInput(item,'unit_weight_kg','Kg / đơn vị','number'),itemInput(item,'total_weight_kg','Tổng kg (nếu không có kg/đv)','number'));
   const source=el('td');source.append(itemInput(item,'origin','Xuất xứ'),itemInput(item,'source','Nguồn đối chiếu','textarea'));
   const pack=el('td'),check=el('input');check.type='checkbox';check.checked=item.include_in_packing&&item.kind!=='service';check.disabled=item.kind==='service';check.setAttribute('aria-label','Đưa vào Packing List');check.onchange=()=>{item.include_in_packing=check.checked;dirty();};pack.append(check);
   kind.onchange=()=>{item.kind=kind.value;item.include_in_packing=kind.value==='goods';check.checked=item.include_in_packing;check.disabled=item.kind==='service';dirty();};
   const action=el('td'),remove=el('button','ship-remove','✕');remove.type='button';remove.setAttribute('aria-label','Xóa dòng '+(index+1));remove.onclick=()=>{if(!busy){data.items.splice(index,1);renderItems();dirty();}};action.append(remove);
   row.append(desc,group,qty,price,weights,source,pack,action);$('shipItems').append(row);
  });summary();
 }
 function summary(){
  if(!data)return;const packed=data.items.filter(i=>i.kind==='goods'&&i.include_in_packing),complete=data.items.length&&data.items.every(i=>i.quantity!==null&&i.unit_price!==null);
  const total=complete?data.items.reduce((s,i)=>s+Number(i.quantity)*Number(i.unit_price),0):null;
  $('shipSummary').replaceChildren(el('span','',`${data.items.length} dòng Invoice · ${packed.length} dòng Packing List`),el('span','',total===null?'Tổng tiền: chưa đủ dữ liệu':`Tổng tiền: ${total.toLocaleString('vi-VN',{maximumFractionDigits:2})} ${data.currency}`));
 }
 function warnings(values){const box=$('shipWarnings');box.replaceChildren();if(!values?.length)return;box.append(el('strong','','Cần kiểm tra'));const ul=el('ul');values.forEach(v=>ul.append(el('li','',v)));box.append(ul);}
 $('shipFiles').onchange=e=>{addFiles(e.target.files);e.target.value='';};
 for(const event of ['dragover','drop'])$('shipDrop').addEventListener(event,e=>{e.preventDefault();if(event==='drop'){addFiles(e.dataTransfer.files);$('shipDrop').classList.remove('dragover');}else $('shipDrop').classList.add('dragover');});
 $('shipDrop').addEventListener('dragleave',()=>$('shipDrop').classList.remove('dragover'));
 $('shipAddNote').onclick=()=>{if($('shipNotes').children.length<20)addNote();};
 $('shipAddItem').onclick=()=>{data.items.push({name_vi:'',name_zh:'',description:'',model:'',group:'',origin:'',quantity:null,unit:'',unit_price:null,unit_weight_kg:null,total_weight_kg:null,kind:'goods',include_in_packing:true,source:''});renderItems();dirty();};
 $('shipAnalyze').onclick=async()=>{
  if(busy)return;error();const notes=[...$('shipNotes').querySelectorAll('textarea')].map(e=>e.value).filter(v=>v.trim());
  if(!attachments.length&&!notes.length){error('Thêm file hoặc nội dung đơn hàng trước khi phân tích.');return;}
  const fd=new FormData();attachments.forEach(x=>fd.append('files',x.file));fd.append('roles',JSON.stringify(attachments.map(x=>x.role)));fd.append('texts',JSON.stringify(notes));
  setBusy(true);$('shipProgress').textContent='Đang đọc và đối chiếu tài liệu…';
  try{const result=await api('/api/shipping-documents/analyze',{method:'POST',body:fd});data=result.data;fields(mainFields,'shipFields');fields(sellerFields,'shipSellerFields');renderItems();warnings(result.review.warnings);$('shipReview').hidden=false;$('shipDownloads').hidden=true;$('shipProgress').textContent='Đã trích xuất. Anh kiểm tra dữ liệu bên dưới trước khi xuất.';}
  catch(e){error(e.message);$('shipProgress').textContent='Chưa phân tích được. Các file đã chọn vẫn được giữ.';}finally{setBusy(false);}
 };
 $('shipGenerate').onclick=async()=>{
  if(busy||!data)return;error();setBusy(true);const current=revision;$('shipExportProgress').textContent='Đang tạo hai file Excel…';
  try{const result=await api('/api/shipping-documents/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});warnings(result.review.warnings);if(revision!==current){$('shipExportProgress').textContent='Dữ liệu vừa thay đổi. Bấm tạo lại để xuất bản mới nhất.';return;}$('shipInvoiceLink').href=result.downloads.invoice;$('shipPackingLink').href=result.downloads.packing;$('shipDownloads').hidden=false;$('shipExportProgress').textContent='Đã tạo xong.';}
  catch(e){error(e.message);$('shipExportProgress').textContent='Chưa xuất được. Nội dung chỉnh sửa vẫn được giữ.';}finally{setBusy(false);}
 };
 addNote();
})();
