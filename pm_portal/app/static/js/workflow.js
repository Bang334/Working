(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  let rows = [], roles = {}, sources = [], selected = null;
  const groupLabels={active:'Cần thực hiện',waiting:'Chờ điều kiện thu',review:'Hồ sơ cần đối chiếu',closed:'Đã hoàn tất',all:'Tất cả hồ sơ'};
  const money = c => `${Number(c.amount).toLocaleString('vi-VN')} ${esc(c.currency)}`;
  const actor = () => $('wf-actor')?.value.trim() || '';
  function notice(text, error = false) { $('wf-alert').innerHTML = `<div class="wf-message ${error ? 'error' : ''}">${esc(text)}</div>`; }
  async function api(path, method = 'GET', data) {
    const opts = {method};
    if (data instanceof FormData) opts.body = data;
    else if (data !== undefined) {opts.body = JSON.stringify(data); opts.headers = {'Content-Type':'application/json'};}
    const response = await fetch(`/api/workflows${path}`, opts);
    const body = await response.json();
    if (!response.ok) throw new Error(body.message || 'Không thực hiện được yêu cầu.');
    return body;
  }
  async function act(fn) {
    const buttons = [...document.querySelectorAll('.wf-page button')];
    buttons.forEach(b => b.disabled = true);
    try {await fn();} catch (err) {notice(err.message, true);}
    finally {buttons.forEach(b => b.disabled = false);}
  }
  function list() {
    const search = normalize($('wf-search').value), filter = $('wf-filter').value;
    const shown = rows.filter(c => normalize(`${c.title} ${c.customer} ${c.contract_code} ${c.project_label} ${c.owner}`).includes(search)
      && (filter === 'all' || c.queue_group===filter || (filter === 'attention' && c.attention && c.queue_group==='active'))
      && (!$('wf-type').value || c.kind===$('wf-type').value)
      && (!$('wf-project').value || c.project_label===$('wf-project').value)
      && (!$('wf-owner').value || ($('wf-owner').value==='__unassigned' ? !c.owner : c.owner===$('wf-owner').value)));
    const order=$('wf-sort').value;
    const priority={active:0,waiting:1,review:2,closed:3};
    shown.sort((a,b)=>order==='newest' ? b.id-a.id : order==='name' ? a.title.localeCompare(b.title,'vi') :
      priority[a.queue_group]-priority[b.queue_group] || Number(Boolean(b.attention))-Number(Boolean(a.attention)) || (a.followup_date||a.due_date||'9999').localeCompare(b.followup_date||b.due_date||'9999') || b.id-a.id);
    $('wf-results').textContent=`${shown.length} / ${rows.length} hồ sơ · ${groupLabels[filter] || 'Gần hạn / cần chú ý'}`;
    const extra=[$('wf-type').value?$('wf-type').selectedOptions[0].text:'',$('wf-project').value,$('wf-owner').value?$('wf-owner').selectedOptions[0].text:''].filter(Boolean);
    if(extra.length)$('wf-results').textContent+=' · '+extra.join(' · ');
    $('wf-summary').querySelectorAll('[data-queue]').forEach(b=>{b.classList.toggle('selected',b.dataset.queue===filter);b.setAttribute('aria-pressed',String(b.dataset.queue===filter));});
    const buckets=new Map();
    for(const c of shown){const key=$('wf-group').value==='project' ? c.project_label : $('wf-group').value==='kind' ? c.kind_label : 'Danh sách';if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(c);}
    $('wf-list').innerHTML=[...buckets].map(([name,items])=>`<section class="wf-list-group"><h3>${esc(name)} <span>${items.length}</span></h3>${items.map(c=>`<button type="button" class="wf-case ${selected?.id===c.id?'active':''}" data-case="${c.id}" aria-pressed="${selected?.id===c.id}"><div class="wf-case-top"><span class="wf-tag">${esc(c.kind_label)}</span><span class="wf-status ${esc(c.queue_group)}">${esc(c.queue_label)}</span></div><strong title="${esc(c.title)}">${esc(c.title)}</strong><p class="wf-case-ref">${esc(c.contract_code || c.customer || 'Chưa gắn hợp đồng')}${c.kind==='payment'?' · '+money(c):''}</p><p class="wf-case-state">${esc(c.source_status==='DELIVERED' ? 'Nguồn mua hàng: đã ghi giao đủ' : c.queue_reason)}</p><div class="wf-case-meta"><span>${esc(c.owner || 'Chưa phân công')}</span>${c.followup_date?`<span>Hẹn ${esc(c.followup_date)}</span>`:''}${c.attention&&c.queue_group==='active'?'<span class="wf-urgent">Gần hạn / cần chú ý</span>':''}</div></button>`).join('')}</section>`).join('') || `<div class="wf-empty"><span aria-hidden="true">✓</span><h3>${filter==='active'?'Chưa có việc được xác nhận cần thực hiện':'Không có hồ sơ phù hợp'}</h3><p>${filter==='active'?'Các hồ sơ kế thừa đang ở nhóm đối chiếu. Chưa có dữ liệu không đồng nghĩa chưa giao hàng.':'Thử đổi nhóm hoặc xóa bớt bộ lọc.'}</p>${filter==='active'?'<button type="button" id="wf-view-review">Xem hồ sơ cần đối chiếu</button>':''}</div>`;
    $('wf-list').querySelectorAll('[data-case]').forEach(b => b.onclick = () => act(async()=>{await choose(Number(b.dataset.case));if(window.matchMedia('(max-width:1100px)').matches)$('wf-detail').scrollIntoView({behavior:'smooth',block:'start'});}));
    if($('wf-view-review'))$('wf-view-review').onclick=()=>{$('wf-filter').value='review';list();};
    if(selected&&!shown.some(c=>c.id===selected.id)){
      selected=null;$('wf-detail').innerHTML='<div class="wf-empty"><span aria-hidden="true">◎</span><h3>Chọn hồ sơ trong kết quả lọc</h3><p>Chi tiết công việc sẽ hiện tại đây.</p></div>';
      const url=new URL(location.href);url.searchParams.delete('case');url.searchParams.delete('milestone');history.replaceState(null,'',url);
    }
  }
  const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/gi,'d').toLowerCase();
  function options(id,items,label){const value=$(id).value;$(id).innerHTML=`<option value="">${label}</option>`+items.map(([k,v])=>`<option value="${esc(k)}">${esc(v)}</option>`).join('');if([...$(id).options].some(o=>o.value===value))$(id).value=value;}
  async function load() {
    const data = await api(''); rows = data.cases; roles = data.roles; sources = data.sources || [];
    $('wf-kind').innerHTML = Object.entries(data.templates).filter(([k]) => k !== 'payment').map(([k,v]) => `<option value="${k}">${esc(v)}</option>`).join('');
    options('wf-type',Object.entries(data.templates),'Tất cả loại');
    options('wf-project',[...new Set(rows.map(c=>c.project_label))].sort((a,b)=>a.localeCompare(b,'vi')).map(x=>[x,x]),'Tất cả dự án');
    options('wf-owner',[['__unassigned','Chưa phân công'],...[...new Set(rows.map(c=>c.owner).filter(Boolean))].sort().map(x=>[x,x])],'Tất cả người phụ trách');
    $('wf-summary').innerHTML=Object.entries(groupLabels).map(([key,label])=>`<button type="button" class="wf-stat ${key}" data-queue="${key}" aria-pressed="false"><strong>${key==='all'?rows.length:rows.filter(c=>c.queue_group===key).length}</strong><span>${label}</span>${key==='review'?'<small>Không đồng nghĩa chưa giao</small>':key==='active'?'<small>Đã xác định bước cần làm</small>':''}</button>`).join('');
    $('wf-summary').querySelectorAll('[data-queue]').forEach(b=>b.onclick=()=>{$('wf-filter').value=b.dataset.queue;list();});
    sourceOptions(); list();
  }
  async function choose(id) {selected = await api(`/${id}`); if($('wf-filter').value!=='all'&&$('wf-filter').value!==selected.queue_group&& !($('wf-filter').value==='attention'&&selected.attention&&selected.queue_group==='active'))$('wf-filter').value=selected.queue_group; render(); await projectPanel(selected); list(); if(selected)history.replaceState(null,'',`?case=${id}`);}
  async function refresh() {const id = selected?.id; await load(); if(id) await choose(id);}
  function files(c) {return c.files.map(f => `<li><a target="_blank" rel="noopener" href="/api/workflows/files/${f.id}/download">${esc(f.name)}</a><br><small>${esc(roles[f.role])} · ${esc(f.verified_by ? 'Người kiểm tra: '+f.verified_by : 'Chưa có người xác nhận')}${f.exists ? '' : ' · Tệp không còn tại vị trí lưu'}</small></li>`).join('') || '<li>Chưa có hồ sơ. Tải đúng bản cho bước hiện tại.</li>';}
  function render() {
    const c = selected, step = c.current;
    $('wf-detail').innerHTML = `<div class="wf-head"><div><span class="wf-tag">${esc(c.kind_label)}</span><h3 style="margin-top:10px">${esc(c.title)}</h3><p class="wf-subtitle">${esc(c.customer)} · ${esc(c.contract_code)}<br>${c.kind === 'payment' ? `Đợt thu ${money(c)} · Đã ghi nhận ${Number(c.received).toLocaleString('vi-VN')} · Còn ${Number(c.remaining).toLocaleString('vi-VN')} ${esc(c.currency)}<br>Hạn theo điều kiện: ${esc(c.due_date || 'Chưa xác nhận điều kiện thu')}<br>Nguồn trạng thái: ${esc(c.payment_source)}${c.recorded_paid_date ? ' · Ngày thu đã ghi: '+esc(c.recorded_paid_date) : ''}` : ''}</p></div><a href="/tracker">Hồ sơ hợp đồng ↗</a></div>
      <div class="wf-progress">${c.steps.map((s,i) => `<span class="wf-step ${c.events.some(e=>e.action==='completed'&&e.note.startsWith(s.title+':')) ? 'done' : i === c.stage ? 'now' : ''}">${i+1}. ${esc(s.title)}</span>`).join('')}</div>
      <div class="wf-next ${esc(c.queue_group)}"><span class="wf-status ${esc(c.queue_group)}">${esc(c.queue_label)}</span><br><strong>${c.queue_group==='review'?'Đối chiếu hồ sơ đã có':c.queue_group==='waiting'?'Chờ xác nhận điều kiện của đợt thu':step ? 'Việc tiếp theo: '+esc(step.title) : c.inherited_paid ? 'Đã thu đủ theo dữ liệu đã nhập' : 'Công việc đã hoàn tất'}</strong><p>${esc(['review','waiting'].includes(c.queue_group)?c.queue_reason:step?.instruction || (c.inherited_paid ? 'Không nhắc thu lại khoản này. Chứng từ ký, thư gửi và sao kê cũ cần đối chiếu riêng khi bổ sung hồ sơ.' : 'Xem lại nhật ký và bộ hồ sơ bên dưới.'))}</p>${c.source_status?`<p class="wf-source-state">Trạng thái nguồn mua hàng: <strong>${esc(c.source_status==='DELIVERED'?'Đã ghi nhận giao đủ':c.source_status==='PARTIAL'?'Đã ghi nhận giao một phần':'Chưa xác nhận giao đủ')}</strong>${c.source_date?' · '+esc(c.source_date):''}</p>`:''}${step?.link&&c.queue_group!=='review' ? `<a href="${esc(step.link)}" target="_blank" rel="noopener">Mở công cụ lập hồ sơ ↗</a>` : ''}</div>
      ${c.blockers.length ? `<details class="wf-missing"><summary>${c.queue_group==='review'?'Hồ sơ ứng dụng chưa có · cần đối chiếu':'Cần bổ sung trước khi hoàn tất bước'}</summary><ul>${c.blockers.map(b => `<li>${esc(b)}</li>`).join('')}</ul></details>` : ''}
      <form id="wf-info"><div class="wf-fields"><label>Người phụ trách<input name="owner" value="${esc(c.owner)}"></label><label>Ngày theo dõi / nhắc lại<input name="followup_date" type="date" value="${esc(c.followup_date)}"></label><label>Người nhận To<input name="recipient" value="${esc(c.recipient)}" placeholder="Địa chỉ đã kiểm tra"></label><label>CC<input name="cc" value="${esc(c.cc)}"></label></div>${c.kind === 'payment' ? `<label class="wf-check"><input name="needs_acceptance" type="checkbox" ${c.needs_acceptance ? 'checked' : ''}>Đợt này cần bản nghiệm thu đã xác nhận đi kèm phiếu thanh toán</label>` : ''}<label>Ghi chú / đang chờ ai<textarea name="notes">${esc(c.notes)}</textarea></label><div class="wf-actions"><button>Lưu người phụ trách và lịch</button></div></form>
      <div class="wf-fields"><label>Người xác nhận thao tác<input id="wf-actor" value="${esc(c.owner)}" placeholder="Họ tên người đang xử lý"></label><label>Kết quả / căn cứ vừa thực hiện<input id="wf-note" placeholder="Đã trình ai, khách xác nhận gì…"></label></div>
      <div class="wf-actions">${step && step.key !== 'receipt' ? '<button id="wf-next" class="wf-primary" type="button">Xác nhận hoàn tất bước này</button>' : ''}${c.stage > 0 && !c.receipts.length ? '<button id="wf-back" type="button">Quay lại bước trước để bổ sung</button>' : ''}${c.kind === 'payment' && c.stage === 1 ? '<button id="wf-generate" type="button">Lập phiếu thanh toán Word + Excel</button>' : ''}</div>
      ${c.kind === 'payment' && c.stage === 0 ? `<form id="wf-condition" class="wf-box"><h4>Xác nhận điều kiện thu đã đạt</h4><p class="wf-note">Tải căn cứ đạt điều kiện ở mục hồ sơ trước. Thời hạn lấy đúng thỏa thuận; không tự cộng ngày ân hạn.</p><div class="wf-fields"><label>Ngày thực sự đạt điều kiện<input type="date" name="trigger_date" required></label><label>Số ngày T/T (0 = đến hạn ngay)<input type="number" name="term_days" min="0" step="1" required></label></div><div class="wf-actions"><button>Xác nhận điều kiện và tính ngày đến hạn</button></div></form>` : ''}
      <hr class="wf-divider"><h4>Hồ sơ của công việc</h4><ul class="wf-files">${files(c)}</ul>
      <form id="wf-upload"><div class="wf-fields"><label>Loại hồ sơ<select name="role">${Object.entries(roles).map(([k,v]) => `<option value="${k}" ${k === step?.role ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select></label><label>Tệp PDF, Word, Excel hoặc ảnh · tối đa 25 MB<input type="file" name="file" accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg" required></label></div><label class="wf-check"><input id="wf-verified" type="checkbox">Tôi đã mở và kiểm tra đúng nội dung, chữ ký/xác nhận của bản này</label><button>Tải hồ sơ vào đúng công việc</button></form>
      <details ${['email','sent','customer'].includes(step?.key) ? 'open' : ''}><summary>Soạn email và liên kết Outlook</summary><p class="wf-note">Địa chỉ nhận phải được kiểm tra. Chỉ đính kèm bản mới nhất của từng loại hồ sơ phù hợp; không gửi chứng từ ngân hàng cho khách. Bạn tự xem và bấm Gửi trong Outlook.</p><form id="wf-email"><label>Tiêu đề<input name="subject" value="${esc(c.subject)}"></label><label>Nội dung song ngữ<textarea name="body" style="min-height:210px">${esc(c.body)}</textarea></label><div class="wf-actions"><button>Lưu nội dung thư</button><button id="wf-suggest" type="button">Gợi ý nội dung theo việc</button><button id="wf-draft" type="button" class="wf-primary">Tạo nháp Outlook có tệp thật</button><button id="wf-outlook" type="button">Đọc Outlook / tìm thư liên quan</button></div></form><div id="wf-candidates"></div>
      <h4>Thư đã gắn với công việc</h4>${c.mail.map(m => `<div class="wf-mail"><span class="wf-tag">${esc({draft:'Nháp, chưa gửi',sent:'Thư gửi đã kiểm tra',inbox:'Phản hồi đã kiểm tra'}[m.direction])}</span><strong> ${esc(m.subject)}</strong><p class="wf-note">${esc(m.received_at)} · ${esc(m.confirmed_by)}</p>${m.direction === 'draft' ? `<button type="button" data-draft="${esc(m.entry_id)}">Mở nháp trong Outlook</button>` : ''}<details><summary>Xem nội dung</summary><pre>${esc(m.body)}</pre></details></div>`).join('') || '<p>Chưa có thư được gắn. Lưu nháp trong project không phải gửi thật.</p>'}
      <details><summary>Ghi nhận gửi qua kênh khác / Outlook chưa đồng bộ</summary><p class="wf-note">Tải ảnh/PDF chứng minh thư đã gửi với loại “Bằng chứng công việc”, rồi ghi mã thư và người kiểm tra.</p><form id="wf-manual"><label>Mã thư / tham chiếu gửi<input name="reference" required></label><label>Căn cứ đã gửi<input name="note" required></label><button>Ghi nhận bằng chứng gửi</button></form></details></details>
      ${step?.key === 'receipt' ? `<form id="wf-receipt" class="wf-box"><h4>Kế toán xác nhận tiền thực nhận</h4><p class="wf-note">Tải chứng từ nhận tiền và xác nhận đã kiểm tra trước. Mỗi tham chiếu chỉ ghi một lần; thu một phần không đóng đợt.</p><div class="wf-fields"><label>Số tiền nhận lần này (${esc(c.currency)})<input name="amount" type="number" min="0.01" step="0.01" required></label><label>Ngày nhận tiền<input name="paid_date" type="date" required></label><label>Tham chiếu ngân hàng<input name="reference" required></label><label>Chứng từ đã kiểm tra<select name="evidence_id" required><option value="">Chọn chứng từ</option>${c.files.filter(f => f.role === 'payment_evidence' && f.verified_by && f.exists).map(f => `<option value="${f.id}">${esc(f.name)}</option>`).join('')}</select></label></div><button class="wf-primary">Xác nhận khoản tiền này đã về</button></form>` : ''}
      ${c.receipts.length ? `<h4>Các khoản đã đối chiếu</h4><ul class="wf-events">${c.receipts.map(r => `<li>${Number(r.amount).toLocaleString('vi-VN')} ${esc(c.currency)} · ${esc(r.paid_date)} · ${esc(r.reference)} · ${esc(r.confirmed_by)}</li>`).join('')}</ul>` : ''}
      <details><summary>Nhật ký ai đã làm gì</summary><ul class="wf-events">${c.events.map(e => `<li>${esc(e.note)}<small>${esc(e.created_at)} · ${esc(e.actor)}</small></li>`).join('') || '<li>Chưa có thao tác mới.</li>'}</ul></details>`;
    function section(element,title,open=false){const wrapper=document.createElement('details');wrapper.className='wf-detail-section';wrapper.open=open;const summary=document.createElement('summary');summary.textContent=title;element.before(wrapper);wrapper.append(summary,element);return wrapper;}
    section($('wf-info'),'Người phụ trách, lịch theo dõi & thông tin nhận thư');
    const progress=$('wf-detail').querySelector('.wf-progress');section(progress,`Xem ${c.steps.length} bước của quy trình`);
    const upload=$('wf-upload'),fileList=upload.previousElementSibling,heading=fileList.previousElementSibling;
    const docSection=section(fileList,`Hồ sơ & chứng từ · ${c.files.length} tệp`,Boolean(step?.role));
    docSection.append(upload);if(heading?.tagName==='H4')heading.remove();
    const sendForm = (id, fn) => {if ($(id)) $(id).onsubmit = e => {e.preventDefault(); act(() => fn(Object.fromEntries(new FormData(e.target))));};};
    const click = (id, fn) => {if ($(id)) $(id).onclick = () => act(fn);};
    sendForm('wf-info', async payload => {payload.needs_acceptance = Boolean($('wf-info').elements.needs_acceptance?.checked); payload.actor=actor(); await api(`/${c.id}`,'PATCH',payload); await refresh(); notice('Đã lưu thông tin theo dõi.');});
    click('wf-next', async () => {await api(`/${c.id}/advance`,'POST',{stage:c.stage,actor:actor(),note:$('wf-note').value}); await refresh(); notice('Đã lưu bước hoàn tất và chuyển sang việc tiếp theo.');});
    click('wf-back', async () => {const reason=$('wf-note').value.trim(); if(!reason) throw new Error('Nhập lý do cần quay lại trong ô kết quả/căn cứ.'); await api(`/${c.id}/reopen`,'POST',{actor:actor(),reason}); await refresh(); notice('Đã quay lại bước trước, giữ nguyên hồ sơ và nhật ký.');});
    sendForm('wf-condition', async payload => {await api(`/${c.id}/condition`,'POST',{...payload,actor:actor()}); await refresh(); notice('Đã tính hạn từ ngày và T/T bạn xác nhận.');});
    click('wf-generate', async () => {await api(`/${c.id}/generate-request`,'POST',{actor:actor()}); await refresh(); notice('Đã lập Word và Excel để bạn kiểm tra, in và trình ký. Chưa phải bản đã ký.');});
    sendForm('wf-upload', async () => {const form = new FormData($('wf-upload')); form.set('verified_by',$('wf-verified').checked ? actor() : ''); await api(`/${c.id}/files`,'POST',form); await refresh(); notice('Đã lưu hồ sơ và liên kết đúng công việc.');});
    const saveEmail = async () => {const payload=Object.fromEntries(new FormData($('wf-email'))); await api(`/${c.id}`,'PATCH',{...payload,actor:actor()});};
    sendForm('wf-email', async () => {await saveEmail(); notice('Đã lưu nội dung thư. Chưa tạo hoặc gửi thư Outlook.');});
    click('wf-suggest', async () => {if($('wf-email').elements.body.value.trim() && !window.confirm('Thay nội dung đang soạn bằng gợi ý mới?')) return; const text=await api(`/${c.id}/email-suggestion`); $('wf-email').elements.subject.value=text.subject; $('wf-email').elements.body.value=text.body; notice('Đây là gợi ý. Kiểm tra nội dung rồi lưu trước khi tạo nháp.');});
    click('wf-draft', async () => {await saveEmail(); const result=await api(`/${c.id}/outlook-draft`,'POST',{actor:actor()}); await refresh(); notice(result.message);});
    click('wf-outlook', async () => {const result=await api(`/${c.id}/outlook`); showCandidates(result.candidates); notice(`Tìm thấy ${result.candidates.length} thư phù hợp. Kiểm tra nội dung và chọn đúng thư; chưa tự đổi giai đoạn.`);});
    document.querySelectorAll('[data-draft]').forEach(b => b.onclick=() => act(async () => {const r=await api(`/${c.id}/open-draft`,'POST',{entry_id:b.dataset.draft}); notice(r.message);}));
    sendForm('wf-manual', async payload => {await api(`/${c.id}/manual-mail`,'POST',{...payload,actor:actor()}); await refresh(); notice('Đã lưu bằng chứng gửi do bạn xác nhận.');});
    sendForm('wf-receipt', async payload => {await api(`/${c.id}/receipts`,'POST',{...payload,amount:Number(payload.amount),evidence_id:Number(payload.evidence_id),actor:actor()}); await refresh(); notice('Đã ghi nhận tiền thực nhận và cập nhật hồ sơ hợp đồng.');});
  }
  function showCandidates(items) {
    $('wf-candidates').innerHTML=items.map((m,i) => `<div class="wf-mail"><span class="wf-tag">${m.direction==='sent' ? 'Outlook · Sent Items' : 'Outlook · Inbox'}</span><strong> ${esc(m.subject)}</strong><p class="wf-note">${esc(m.received_at)} · ${esc(m.sender)} · ${m.match==='case_tag' ? 'Đúng mã công việc' : m.match==='contract_subject' ? 'Cùng mã hợp đồng, cần chọn đúng đợt' : 'Mã có trong nội dung hoặc lịch sử trích dẫn, cần kiểm tra đúng đợt'}</p><details><summary>Đọc nội dung và danh sách đính kèm (chọn loại hồ sơ ở mục bên trên trước khi lưu tệp)</summary><pre>${esc(m.body)}</pre><p>${m.attachments.map(a => `${esc(a.name)} <button data-import-mail="${i}" data-import-att="${a.index}" type="button">Lưu tệp vào công việc</button>`).join('<br>')}</p></details><button data-link="${i}" type="button">Tôi đã kiểm tra, gắn thư này</button></div>`).join('') || '<p>Chưa tìm thấy thư trong 300 thư gần nhất mỗi thư mục. Có thể ghi nhận bằng chứng gửi ở mục bên dưới.</p>';
    $('wf-candidates').querySelectorAll('[data-import-mail]').forEach(b => b.onclick=() => act(async () => {
      const m=items[Number(b.dataset.importMail)];
      const role=$('wf-upload').elements.role.value;
      await api(`/${selected.id}/outlook-attachment`,'POST',{entry_id:m.entry_id,direction:m.direction,index:Number(b.dataset.importAtt),role,verified_by:$('wf-verified').checked ? actor() : ''});
      await refresh();notice('Đã lưu tệp Outlook vào loại hồ sơ bạn chọn ở mục Hồ sơ của công việc.');
    }));
    $('wf-candidates').querySelectorAll('[data-link]').forEach(b => b.onclick=() => act(async () => {const m=items[Number(b.dataset.link)]; await api(`/${selected.id}/link-mail`,'POST',{entry_id:m.entry_id,direction:m.direction,actor:actor()}); await refresh(); notice('Đã gắn thư và giữ nguyên bước cho đến khi bạn xác nhận hoàn tất.');}));
  }
  async function projectPanel(c) {
    const p=await api(`/${c.id}/project`);
    if(selected?.id!==c.id) return;
    const panel=document.createElement('details');panel.className='wf-box wf-project-panel';
    panel.innerHTML=`<summary>Liên kết dự án & xác nhận nghiệp vụ</summary><p class="wf-note">Xác nhận theo chứng từ thực tế. Hoàn tất checklist bên trên chưa tự xác nhận nghiệp vụ. Bước tiếp theo chỉ được mở khi ghi nhận tại đây.</p>
      ${p.source_status ? `<p class="wf-missing">${esc(p.source_status)}</p>` : ''}
      <form id="project-link"><label>Hợp đồng liên quan<select name="contract_id" required><option value="">Chọn đúng hợp đồng</option>${p.contracts.map(x=>`<option value="${x.id}" ${x.id===p.contract_id?'selected':''}>${esc(x.contract_code)} · ${esc(x.customer_name_vi)}</option>`).join('')}</select></label><button>Xác nhận liên kết hợp đồng</button></form>
      ${Object.keys(p.actions).length ? `<form id="project-fact"><div class="wf-fields"><label>Nghiệp vụ đã thực hiện<select name="action" id="project-action">${Object.entries(p.actions).map(([k,v])=>`<option value="${k}">${esc(v)}</option>`).join('')}</select></label><label>Ngày thực tế<input name="actual_date" type="date" required></label><label>Chứng từ đã mở kiểm tra<select name="evidence_id" required><option value="">Chọn đúng loại chứng từ</option>${c.files.filter(f=>f.exists&&f.verified_by).map(f=>`<option value="${f.id}">${esc(roles[f.role])} · ${esc(f.name)}</option>`).join('')}</select></label><label>Nội dung xác nhận<input name="note" required placeholder="Phạm vi, số lượng, người ký, điều khoản…"></label></div>
      <div data-project-fields="supplier_received"><label>Số lượng thực nhận lần này theo đúng đơn vị PO<input name="quantity" type="number" min="0.0001" step="any"></label></div>
      <div data-project-fields="acceptance_confirmed,delivery_payment_condition,contract_payment_condition"><label>Đợt thu được kích hoạt<select name="milestone_id"><option value="">Chọn đúng đợt</option>${p.milestones.map(m=>`<option value="${m.id}">${esc(m.milestone_name)} · ${Number(m.amount).toLocaleString('vi-VN')} · ${esc(m.status)}</option>`).join('')}</select></label><label>Số ngày T/T đã thỏa thuận (0 = ngay)<input name="term_days" type="number" min="0" step="1"></label></div>
      <div data-project-fields="asset_registered"><div class="wf-fields"><label>Model<input name="model"></label><label>Số máy / SN duy nhất<input name="serial"></label><label>Số tháng bảo hành đúng điều khoản<input name="warranty_months" type="number" min="0" max="120"></label></div><p class="wf-note">Ngày thực tế ở trên là ngày giao của thiết bị. Không mặc định 12 tháng.</p></div>
      <div data-project-fields="warranty_scope"><label>Thiết bị<select name="asset_id"><option value="">Chọn model / SN</option>${p.assets.map(a=>`<option value="${a.id}">${esc(a.model)} / ${esc(a.serial)} · hết BH ${esc(a.warranty_until)}</option>`).join('')}</select></label><label>Kết luận đã được xác nhận<select name="scope"><option value="">Chọn theo bằng chứng</option><option value="FREE">Miễn phí</option><option value="CHARGEABLE">Có phí, cần báo giá duyệt trước khi sửa</option></select></label></div>
      <button class="wf-primary">Ghi nhận và đồng bộ bước liên quan</button></form>` : ''}
      ${p.assets.length?`<h4>Thiết bị của hợp đồng</h4><ul>${p.assets.map(a=>`<li>${esc(a.model)} / ${esc(a.serial)} · giao ${esc(a.delivery_date)} · BH ${a.warranty_months} tháng, đến ${esc(a.warranty_until)}</li>`).join('')}</ul>`:''}
      <h4>Nghiệp vụ đã xác nhận</h4>${p.facts.map(f=>`<p>${esc(p.actions[f.action]||f.action)} · ${esc(f.actual_date)} · ${esc(f.actor)}<br>${esc(JSON.parse(f.payload).note)}</p>`).join('')||'<p>Chưa có xác nhận nghiệp vụ; dữ liệu nguồn không thay thế bằng chứng ký.</p>'}
      ${p.related.length?`<h4>Các việc cùng hợp đồng</h4><ul>${p.related.map(w=>`<li><a href="/workflows?case=${w.id}">${esc(w.title)}</a></li>`).join('')}</ul>`:''}
      ${p.documents.length?`<details><summary>Lấy biểu mẫu / hồ sơ đã lưu đúng mã</summary><form id="project-document"><label>Tệp nguồn<select name="document_id">${p.documents.map(d=>`<option value="${d.id}">${esc(d.doc_type)} · ${esc(d.file_name)}</option>`).join('')}</select></label><p>Loại hồ sơ và ô đã kiểm tra lấy theo mục tải hồ sơ bên trên. Bản sao được giữ nguyên định dạng.</p><button>Đưa bản sao vào công việc</button></form></details>`:''}`;
    $('wf-detail').append(panel);
    const fields=()=>panel.querySelectorAll('[data-project-fields]').forEach(el=>{const active=el.dataset.projectFields.split(',').includes(document.getElementById('project-action')?.value);el.hidden=!active;el.querySelectorAll('input,select').forEach(x=>x.disabled=!active);});
    if($('project-action')){$('project-action').onchange=fields;fields();}
    const bind=(id,suffix,extra={})=>{if($(id))$(id).onsubmit=e=>{e.preventDefault();act(async()=>{const payload={...Object.fromEntries(new FormData(e.target)),actor:actor(),...extra};if(suffix==='project-document'){payload.role=$('wf-upload').elements.role.value;payload.verified_by=$('wf-verified').checked?actor():'';}await api(`/${c.id}/${suffix}`,'POST',payload);await refresh();notice('Đã lưu căn cứ và đồng bộ đúng hồ sơ liên quan.');});};};
    bind('project-link','project-link');bind('project-fact','project-confirm');bind('project-document','project-document');
  }
  function sourceOptions() {
    $('wf-source').innerHTML='<option value="">Tạo việc riêng</option>'+sources.map((s,i) => ({...s,index:i})).filter(s => s.kind===$('wf-kind').value).map(s => `<option value="${s.index}">${esc(s.title)} · ${esc(s.customer)}</option>`).join('');
  }
  $('wf-kind').onchange=sourceOptions;
  $('wf-source').onchange=() => {
    if($('wf-source').value==='') return;
    const source=sources[Number($('wf-source').value)];
    const form=$('wf-create').elements;
    form.title.value=source.title;form.customer.value=source.customer;form.contract_code.value=source.contract_code;
  };
  $('wf-new').onclick=() => {$('wf-create').hidden=!$('wf-create').hidden;};
  $('wf-create').onsubmit=e => {e.preventDefault();act(async () => {const payload=Object.fromEntries(new FormData(e.target)); if($('wf-source').value!==''){const source=sources[Number($('wf-source').value)];payload.source_type=source.source_type;payload.source_id=source.source_id;} const result=await api('','POST',payload); $('wf-create').hidden=true; await load(); await choose(result.id); notice('Đã tạo công việc với hướng dẫn từng bước.');});};
  $('wf-search').oninput=list;
  ['wf-filter','wf-type','wf-project','wf-owner','wf-group','wf-sort'].forEach(id=>$(id).onchange=list);
  $('wf-reset').onclick=()=>{$('wf-search').value='';$('wf-filter').value='all';['wf-type','wf-project','wf-owner'].forEach(id=>$(id).value='');$('wf-group').value='project';$('wf-sort').value='priority';list();};
  $('wf-refresh').onclick=() => act(refresh);
  act(async () => {await load(); const params=new URLSearchParams(location.search); const id=Number(params.get('case')); const milestone=Number(params.get('milestone')); const found=rows.find(c => id ? c.id===id : milestone ? c.milestone_id===milestone : false); if(found) await choose(found.id);});
})();
