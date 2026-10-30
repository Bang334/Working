// One contract editor; changes remain a draft until Save.
let contractEditor = null;
let contractEditorOpening = false;
let scheduleCountTimer = null;
const scheduleColors = ['#2563eb', '#0891b2', '#7c3aed', '#d97706', '#db2777', '#059669'];
const scheduleEsc = value => escapeNotesHtml(value ?? '');

function handleTableProjectClick(event, itemId) {
  event?.stopPropagation();
  const existing = Object.values(contractLookupMap).find(c=>c.segments?.some(s=>Number(s.id)===itemId));
  if (existing) return openContractEditor(existing.contract_key);
  const item = allReceivables.find(row=>row.id===itemId);
  if (!item) return;
  const key = `AR_ITEM_${itemId}`;
  contractLookupMap[key] = {contract_key:key,contract_code:item.contract_code,
    project_title:item.project_group || item.project_name,customer_name:item.customer_name,segments:[{id:itemId}]};
  return openContractEditor(key);
}

async function openContractEditor(cKey) {
  if (contractEditorOpening) return;
  const contract = contractLookupMap[cKey];
  const anchor = contract?.segments?.find(s => !s.is_missing_schedule && Number.isInteger(Number(s.id)));
  if (!anchor) return;
  if (currentDataSource !== 'db') {
    showToast('Chuyển về Dữ Liệu Gốc để chỉnh sửa hợp đồng. / 請切換至原始資料以編輯合約。', 'info');
    return;
  }
  contractEditorOpening = true;
  hideSegmentTooltip();
  hideProjectHoverCard();
  try {
    const response = await fetch(`/api/v1/receivables/contract-schedule/${anchor.id}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Không tải được hợp đồng. / 無法載入合約。');
    const total = data.total_amount || data.rows.reduce((sum, row) => sum + Number(row.net_amount || 0), 0);
    const rows = data.rows.map(row => ({...row, name: row.project_name,
      percentage: total > 0 ? Math.round(Number(row.net_amount || 0) / total * 1000) / 10 : 100 / data.rows.length}));
    let sum = rows.reduce((n, row) => n + row.percentage, 0);
    let warning = data.warning || '';
    if (sum < 99.9) {
      rows.push({id: null, name: 'Đợt chưa phân bổ / 尚未分配期款', percentage: Math.round((100-sum)*10)/10,
        received_amount: 0, collection_status: 'PENDING', vat_rate: rows[0]?.vat_rate || 0});
      warning += ' Lịch hiện có chưa đủ 100%. Phần thiếu được đặt thành đợt chưa phân bổ trong bản nháp; hãy đối chiếu trước khi lưu. / 現有付款計畫未達100%，差額已列入草稿的未分配期款，儲存前請核對。';
    } else if (sum > 100.1) {
      rows.forEach(row => row.percentage = Math.round(row.percentage / sum * 1000) / 10);
      warning += ' Tổng đợt cũ vượt giá trị hợp đồng; tỷ lệ bản nháp được phân bổ theo số tiền hiện có. Hãy kiểm tra trước khi lưu. / 原期款總額超過合約金額，草稿比例已按現有金額重新分配，儲存前請核對。';
    }
    rows[rows.length-1].percentage = Math.round((100-rows.slice(0,-1).reduce((n,r)=>n+r.percentage,0))*10)/10;
    contractEditor = {anchor: anchor.id, revision: data.revision, total,
      vat_rate: Number(rows[0]?.vat_rate || 0),
      project_name: contract.project_title_vi || contract.project_title, rows,
      notes: [...new Set(data.rows.map(r => (r.notes || '').trim()).filter(Boolean))].join('\n\n'), warning};
    let dialog = document.getElementById('contractScheduleDialog');
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.id = 'contractScheduleDialog';
      dialog.className = 'contract-schedule-dialog';
      document.body.appendChild(dialog);
      dialog.addEventListener('cancel', event => {
        event.stopPropagation();
        if (contractEditor?.saving) event.preventDefault();
      });
    }
    renderContractEditor(contract);
    dialog.showModal();
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    contractEditorOpening = false;
  }
}

function renderContractEditor(contract) {
  const state = contractEditor;
  document.getElementById('contractScheduleDialog').innerHTML = `
    <form onsubmit="event.preventDefault(); saveContractEditor()" oninput="editContractField(event)">
      <header class="schedule-header"><div><h2>Hợp đồng & lịch thanh toán / 合約及付款計畫</h2>
        <p>${scheduleEsc(contract.customer_name_vi || contract.customer_name)} · ${scheduleEsc(contract.contract_code)}</p></div>
        <button type="button" class="btn btn-outline" onclick="closeContractEditor()" aria-label="Đóng / 關閉">✕</button></header>
      <section class="schedule-content">
        ${state.warning ? `<p class="schedule-warning-box">${scheduleEsc(state.warning)}</p>` : ''}
        <div class="schedule-fields">
          <label><span>Tên dự án</span><small lang="zh-Hant">專案名稱</small><input class="form-control" data-field="project_name" value="${scheduleEsc(state.project_name)}" required></label>
          <label><span>Giá trị chưa VAT (VNĐ)</span><small lang="zh-Hant">合約未稅金額（越盾）</small><input class="form-control" data-field="total" type="number" min="1" step="1" value="${state.total}" required></label>
          <label><span>VAT hợp đồng</span><small lang="zh-Hant">合約營業稅</small><select class="form-control" data-field="vat_rate">${[0,0.08,0.1].map(rate=>`<option value="${rate}" ${state.vat_rate===rate?'selected':''}>${Math.round(rate*100)}%</option>`).join('')}</select></label>
          <label><span>Số đợt</span><small lang="zh-Hant">付款期數</small><input class="form-control" id="scheduleCount" type="number" min="1" max="20" value="${state.rows.length}" oninput="queueScheduleCount(this)" onchange="clearTimeout(scheduleCountTimer); changeScheduleCount(this)"></label>
        </div>
        <div class="schedule-section-heading"><strong>Phân bổ các đợt · Tổng 100% / 各期比例分配 · 合計100%</strong><button type="button" class="btn btn-outline" onclick="addScheduleInstallment()">+ Thêm đợt / 新增期款</button></div>
        <div id="scheduleSharedSlider"></div>
        <p class="schedule-help">Kéo điểm chia để chỉnh tỷ lệ. Đã thu đủ = 100% tiền đợt. Rê chuột xem nội dung đầy đủ; bấm ô để sửa. / 拖曳分界調整比例；全額收款＝該期100%。滑鼠停留可查看全文，點選欄位編輯。</p>
        <div class="schedule-table-scroll"><table class="schedule-table"><colgroup><col class="schedule-col-name"><col class="schedule-col-pct"><col class="schedule-col-money"><col class="schedule-col-status"><col span="3" class="schedule-col-date"><col class="schedule-col-doc"></colgroup><thead><tr>
          <th>Đợt / nội dung<br><small lang="zh-Hant">期別／內容</small></th><th>Tỷ lệ<br><small lang="zh-Hant">比例</small></th><th>Phải thu (có VAT)<br><small lang="zh-Hant">應收金額（含稅）</small></th><th>Trạng thái thu<br><small lang="zh-Hant">收款狀態</small></th><th>Hạn thanh toán<br><small lang="zh-Hant">付款期限</small></th><th>Ngày thực thu<br><small lang="zh-Hant">實際收款日</small></th><th>KH hẹn trả<br><small lang="zh-Hant">客戶承諾付款日</small></th><th>Chứng từ<br><small lang="zh-Hant">單據狀態</small></th>
        </tr></thead><tbody id="scheduleEditorRows"></tbody></table></div>
        <div id="scheduleTotals" class="schedule-totals"></div>
        <label class="schedule-note-label">Ghi chú tiến độ chung / 合約進度備註<textarea class="form-control" data-field="notes" rows="3">${scheduleEsc(state.notes)}</textarea></label>
        <p id="scheduleEditorError" class="schedule-error" role="alert"></p>
      </section>
      <footer class="schedule-footer"><span>Chỉ cập nhật sau khi bấm Lưu thay đổi. / 按「儲存變更」後才會更新資料。</span><div>
        <button type="button" class="btn btn-outline" onclick="closeContractEditor()">Hủy / 取消</button>
        <button type="submit" id="saveContractScheduleButton" class="btn btn-primary">Lưu thay đổi / 儲存變更</button>
      </div></footer>
    </form>`;
  renderScheduleRows();
}

function scheduleAmounts() {
  let allocated = 0;
  return contractEditor.rows.map((row, index) => {
    const net = index === contractEditor.rows.length-1 ? contractEditor.total-allocated : Math.round(contractEditor.total*row.percentage/100);
    allocated += net;
    return {net, gross: net+Math.round(net*Number(contractEditor.vat_rate || 0))};
  });
}

function renderScheduleRows() {
  const state = contractEditor;
  document.getElementById('scheduleEditorRows').innerHTML = state.rows.map((row, i) => {
    return `<tr data-index="${i}">
      <td><label class="schedule-row-label" style="--schedule-color:${scheduleColors[i%scheduleColors.length]}">Đợt ${i+1} / 第${i+1}期</label><textarea rows="1" class="schedule-cell-text" data-field="name" title="${scheduleEsc(row.name)}" aria-label="Nội dung đợt ${i+1}">${scheduleEsc(row.name)}</textarea></td>
      <td><strong id="schedulePct${i}"></strong></td>
      <td id="scheduleGross${i}" class="schedule-money"></td>
      <td><select data-field="collection_status" id="scheduleStatus${i}" aria-label="Trạng thái đợt ${i+1}">
        ${[['PENDING','Chờ thu / 待收款'],['PAID','Đã thu đủ / 已全額收款'],['URGENT','Sắp đến hạn / 即將到期'],['DELAYED','Quá hạn / 已逾期']].map(([v,t])=>`<option value="${v}" ${row.collection_status===v?'selected':''}>${t}</option>`).join('')}</select></td>
      ${[['due_date','Hạn thanh toán'],['paid_date','Ngày thực thu'],['customer_promised_date','KH hẹn trả']].map(([field,label])=>`<td><input type="date" data-field="${field}" value="${scheduleEsc(row[field]||'')}" aria-label="${label} đợt ${i+1}" title="${scheduleEsc(row[field]||'Chưa xác định / 尚未確認')}">${field==='paid_date' && row.paid_by_date ? `<small class="schedule-history-note" title="Chưa xác định ngày thực nhận / 實際收款日尚待確認">Chậm nhất: ${scheduleEsc(row.paid_by_date)}</small>` : ''}</td>`).join('')}
      <td><textarea rows="1" class="schedule-cell-text" data-field="doc_status" title="${scheduleEsc(row.doc_status||'')}" aria-label="Chứng từ đợt ${i+1}">${scheduleEsc(row.doc_status||'')}</textarea></td>
    </tr>`;
  }).join('');
  renderSharedScheduleSlider();
  updateScheduleAmounts();
}

function renderSharedScheduleSlider() {
  let boundary = 0;
  const rows = contractEditor.rows;
  document.getElementById('scheduleSharedSlider').innerHTML = `<div class="schedule-slider-track">
    <div class="schedule-slider-segments">${rows.map((row,i)=>`<div data-slider-segment="${i}" style="width:${row.percentage}%;background:${scheduleColors[i%scheduleColors.length]}"><span>${i+1}</span></div>`).join('')}</div>
    ${rows.slice(0,-1).map((row,i)=>{
      boundary += row.percentage;
      return `<input type="range" class="schedule-boundary" data-boundary="${i}" min="0" max="100" step="0.1" value="${boundary}" aria-label="Điểm chia giữa đợt ${i+1} và ${i+2}" oninput="moveScheduleBoundary(${i}, this)">`;
    }).join('')}</div><div class="schedule-slider-legend">${rows.map((row,i)=>`<span style="color:${scheduleColors[i%scheduleColors.length]}">Đợt ${i+1} / 第${i+1}期: <b id="scheduleLegend${i}">${row.percentage}%</b></span>`).join('')}</div>`;
}

function moveScheduleBoundary(index, input) {
  const rows = contractEditor.rows;
  const before = rows.slice(0,index).reduce((n,r)=>n+r.percentage,0);
  const after = before+rows[index].percentage+rows[index+1].percentage;
  const boundary = Math.min(after-0.1,Math.max(before+0.1,Number(input.value)));
  input.value = boundary;
  rows[index].percentage = Math.round((boundary-before)*10)/10;
  rows[index+1].percentage = Math.round((after-boundary)*10)/10;
  updateScheduleAmounts();
}

function updateScheduleAmounts() {
  const amounts = scheduleAmounts();
  let received = 0, gross = 0;
  contractEditor.rows.forEach((row,i)=>{
    row.received_amount = row.collection_status === 'PAID' ? amounts[i].gross : 0;
    const paid = row.received_amount;
    received += paid; gross += amounts[i].gross;
    document.getElementById(`schedulePct${i}`).textContent = `${row.percentage.toFixed(1).replace('.0','')}%`;
    document.getElementById(`scheduleLegend${i}`).textContent = `${row.percentage.toFixed(1).replace('.0','')}%`;
    document.querySelector(`[data-slider-segment="${i}"]`).style.width = `${row.percentage}%`;
    document.getElementById(`scheduleGross${i}`).textContent = formatVND(amounts[i].gross);
    document.getElementById(`scheduleGross${i}`).classList.toggle('schedule-invalid',paid>amounts[i].gross);

  });
  document.getElementById('scheduleTotals').textContent = `Tổng phải thu / 應收總額: ${formatVND(gross)} · Đã thu / 已收金額: ${formatVND(received)} · Còn phải thu / 未收餘額: ${formatVND(gross-received)}`;
}

function editContractField(event) {
  const input = event.target, field = input.dataset.field;
  if (!field) return;
  if (input.classList.contains('schedule-cell-text')) input.title=input.value;
  const tr = input.closest('tr[data-index]');
  if (!tr) {
    contractEditor[field] = field==='total'?Math.round(Number(input.value)):field==='vat_rate'?Number(input.value):input.value;
  } else {
    const index = Number(tr.dataset.index), row = contractEditor.rows[index];
    row[field] = input.value;
    if (field==='collection_status' && input.value!=='PAID') {
      row.received_amount=0;
      row.paid_date=null;
      document.querySelector(`tr[data-index="${index}"] input[data-field="paid_date"]`).value='';
    }
  }
  updateScheduleAmounts();
}

function addScheduleInstallment() {
  clearTimeout(scheduleCountTimer);
  const input = document.getElementById('scheduleCount');
  input.value = Math.min(20,contractEditor.rows.length+1);
  changeScheduleCount(input);
}

function queueScheduleCount(input) {
  clearTimeout(scheduleCountTimer);
  scheduleCountTimer = setTimeout(()=>changeScheduleCount(input),400);
}

function changeScheduleCount(input) {
  const count = Number(input.value), rows = contractEditor.rows;
  if (!Number.isInteger(count) || count<1 || count>20) {input.value=rows.length;return;}
  if (count<rows.length && rows.slice(count).some(r=>r.received_amount>0 || r.paid_date || r.paid_by_date || r.linked_milestone_id)) {
    document.getElementById('scheduleEditorError').textContent='Không thể bỏ đợt đã thu tiền hoặc có hồ sơ liên kết. / 已收款或已關聯單據的期款無法刪除。';
    input.value=rows.length;return;
  }
  if (count===rows.length) return;
  while(rows.length<count) rows.push({id:null,name:`Đợt ${rows.length+1} / 第${rows.length+1}期`,percentage:0,vat_rate:rows[0]?.vat_rate||0,received_amount:0,collection_status:'PENDING'});
  rows.splice(count);
  rows.forEach(row=>row.percentage=Math.floor(1000/count)/10);
  rows[rows.length-1].percentage=Math.round((100-rows[0].percentage*(count-1))*10)/10;
  document.getElementById('scheduleEditorError').textContent='Đã chia đều tỷ lệ bản nháp theo số đợt mới. Kéo thanh để điều chỉnh theo hợp đồng. / 已依新期數平均分配草稿比例，請拖曳滑桿調整為合約約定比例。';
  renderScheduleRows();
}

function closeContractEditor() {
  if (contractEditor?.saving) return;
  clearTimeout(scheduleCountTimer);
  document.getElementById('contractScheduleDialog')?.close();
}

async function saveContractEditor() {
  const state = contractEditor;
  if (state.saving) return;
  clearTimeout(scheduleCountTimer);
  changeScheduleCount(document.getElementById('scheduleCount'));
  const error = document.getElementById('scheduleEditorError');
  const button = document.getElementById('saveContractScheduleButton');
  state.saving = true; button.disabled=true; button.textContent='Đang lưu… / 儲存中…';
  document.getElementById('contractScheduleDialog').querySelectorAll('input,select,textarea').forEach(el=>el.disabled=true);
  error.textContent='';
  try {
    const response = await fetch(`/api/v1/receivables/contract-schedule/${state.anchor}`, {
      method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({revision:state.revision,total_amount:state.total,vat_rate:state.vat_rate,project_name:state.project_name,notes:state.notes,
        installments:state.rows.map(row=>({...row,vat_rate:state.vat_rate,percentage:Number(row.percentage.toFixed(1))}))})});
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail==='string'?result.detail:'Không thể lưu. Kiểm tra lại các trường dữ liệu. / 無法儲存，請檢查各欄位資料。');
    state.saving=false;
    closeContractEditor();
    showToast('Đã cập nhật hợp đồng và toàn bộ các đợt thanh toán. / 合約及所有期款已更新。', 'success');
    await Promise.all([loadReceivablesData(),loadWeeklyComparisonData()]);
  } catch (e) {
    error.textContent=e.message;
  } finally {
    state.saving=false;button.disabled=false;button.textContent='Lưu thay đổi / 儲存變更';
    document.getElementById('contractScheduleDialog').querySelectorAll('input,select,textarea').forEach(el=>el.disabled=false);
  }
}
