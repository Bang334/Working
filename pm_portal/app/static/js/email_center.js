/**
 * HONG MING PM PORTAL - EMAIL AUTOMATION CENTER (JS)
 * Quản lý soạn thảo, xem trước và mô phỏng gửi email an toàn.
 * Kết nối sâu với toàn bộ module trong project:
 * - Hợp đồng (Contracts)
 * - Công nợ (Receivables AR)
 * - Mua hàng (PO / Procurement)
 * - Đơn xin thanh toán (Payment Vouchers)
 * - Báo giá (Quotations)
 * - Nghiệm thu (Acceptance)
 * - Quản lý File (File Manager)
 */

window.EmailApp = (function() {
  let presetsData = [];
  let currentPreset = null;
  let dbSources = {
    contracts: [],
    receivables: [],
    milestones: [],
    procurements: [],
    payment_vouchers: [],
    quotations: []
  };
  let currentActiveTab = 'presets';

  async function init(presets) {
    presetsData = presets || [];
    
    // Tải danh mục đối tượng thực tế từ CSDL
    await loadQuickSources();

    // Phân tích tham số URL (Deep Linking từ các module khác sang)
    const urlParams = new URLSearchParams(window.location.search);
    const sourceParam = urlParams.get('source');
    const idParam = urlParams.get('id');
    const codeParam = urlParams.get('code');
    const fileNameParam = urlParams.get('file_name');
    const categoryParam = urlParams.get('category');
    const presetParam = urlParams.get('preset');

    if (sourceParam) {
      // Map tên tab tương ứng
      let targetTab = 'presets';
      if (['receivable', 'debt'].includes(sourceParam)) targetTab = 'receivables';
      else if (sourceParam === 'contract') targetTab = 'contracts';
      else if (['po', 'procurement'].includes(sourceParam)) targetTab = 'procurements';
      else if (['voucher', 'payment_voucher'].includes(sourceParam)) targetTab = 'payment_vouchers';
      else if (sourceParam === 'quotation') targetTab = 'quotations';
      else if (sourceParam === 'acceptance') targetTab = 'acceptance';
      else if (sourceParam === 'file') targetTab = 'contracts'; // default view

      switchSourceTab(targetTab, false);
      await loadFromContext(sourceParam, idParam, codeParam, fileNameParam, categoryParam);
    } else if (presetParam) {
      switchSourceTab('presets', false);
      applyPreset(presetParam);
    } else if (presetsData.length > 0) {
      switchSourceTab('presets', false);
      applyPreset(presetsData[0].id);
    }
  }

  async function loadQuickSources() {
    try {
      const res = await fetch('/api/emails/quick-sources');
      if (!res.ok) return;
      const json = await res.json();
      if (json.status === 'success' && json.data) {
        dbSources = json.data;
      }
    } catch (e) {
      console.warn('Could not load quick sources from DB:', e);
    }
  }

  function switchSourceTab(tabName, autoSelectFirst = true) {
    currentActiveTab = tabName;

    // Cập nhật giao diện tab buttons
    document.querySelectorAll('.source-pill-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-source') === tabName);
    });

    const selectEl = document.getElementById('sourceEntitySelect');
    if (!selectEl) return;
    selectEl.innerHTML = '';

    if (tabName === 'presets') {
      presetsData.forEach(p => {
        const opt = document.createElement('option');
        opt.value = `preset:${p.id}`;
        opt.textContent = `${p.name} (${p.customer})`;
        selectEl.appendChild(opt);
      });
      if (autoSelectFirst && presetsData.length > 0) {
        applyPreset(presetsData[0].id);
      }
    } else if (tabName === 'receivables') {
      const list = dbSources.receivables || [];
      if (list.length === 0) {
        selectEl.innerHTML = '<option value="">(Không có dữ liệu công nợ trong CSDL)</option>';
      } else {
        list.forEach(r => {
          const opt = document.createElement('option');
          opt.value = `receivable:${r.id}`;
          const amt = r.remaining_debt || r.gross_amount || 0;
          const statusText = r.collection_status === 'DELAYED' ? '🚨 Quá hạn' : (r.collection_status === 'URGENT' ? '⚡ Sắp đến hạn' : '⏳ Chờ thu');
          opt.textContent = `[${statusText}] ${r.customer_name || 'KH'} - HĐ: ${r.contract_code || '-'} - ${amt.toLocaleString('vi-VN')} đ`;
          selectEl.appendChild(opt);
        });
        if (autoSelectFirst && list.length > 0) {
          loadFromContext('receivable', list[0].id);
        }
      }
    } else if (tabName === 'contracts') {
      const list = dbSources.contracts || [];
      if (list.length === 0) {
        selectEl.innerHTML = '<option value="">(Không có dữ liệu hợp đồng trong CSDL)</option>';
      } else {
        list.forEach(c => {
          const opt = document.createElement('option');
          opt.value = `contract:${c.id}`;
          const amt = c.total_amount || 0;
          opt.textContent = `[HĐ ${c.contract_code}] ${c.customer_name_vi || 'KH'} - ${c.project_name_vi || 'Dự án'} - ${amt.toLocaleString('vi-VN')} đ`;
          selectEl.appendChild(opt);
        });
        if (autoSelectFirst && list.length > 0) {
          loadFromContext('contract', list[0].id);
        }
      }
    } else if (tabName === 'procurements') {
      const list = dbSources.procurements || [];
      if (list.length === 0) {
        selectEl.innerHTML = '<option value="">(Không có dữ liệu đơn mua hàng PO)</option>';
      } else {
        list.forEach(p => {
          const opt = document.createElement('option');
          opt.value = `po:${p.id}`;
          opt.textContent = `[PO #${p.id}] NCC: ${p.supplier_name || '-'} - ${p.item_name || 'Vật tư'} (ETA: ${p.eta_date || 'Chưa rõ'})`;
          selectEl.appendChild(opt);
        });
        if (autoSelectFirst && list.length > 0) {
          loadFromContext('po', list[0].id);
        }
      }
    } else if (tabName === 'payment_vouchers') {
      const list = dbSources.payment_vouchers || [];
      if (list.length === 0) {
        selectEl.innerHTML = '<option value="">(Không có phiếu xin thanh toán nào)</option>';
      } else {
        list.forEach(v => {
          const opt = document.createElement('option');
          opt.value = `voucher:${v.id}`;
          const amt = v.amount || 0;
          opt.textContent = `[Phiếu ${v.report_code || 'PV'}] Thụ hưởng: ${v.beneficiary_name} - ${amt.toLocaleString('vi-VN')} đ`;
          selectEl.appendChild(opt);
        });
        if (autoSelectFirst && list.length > 0) {
          loadFromContext('voucher', list[0].id);
        }
      }
    } else if (tabName === 'quotations') {
      const list = dbSources.quotations || [];
      if (list.length === 0) {
        selectEl.innerHTML = '<option value="">(Không có báo giá trong CSDL)</option>';
      } else {
        list.forEach(q => {
          const opt = document.createElement('option');
          opt.value = `quotation:${q.id}`;
          const amt = q.total_amount || 0;
          opt.textContent = `[Báo giá ${q.quotation_no}] ${q.customer_name_vi || 'KH'} - ${q.project_name || 'Gói TB'} - ${amt.toLocaleString('vi-VN')} đ`;
          selectEl.appendChild(opt);
        });
        if (autoSelectFirst && list.length > 0) {
          loadFromContext('quotation', list[0].id);
        }
      }
    } else if (tabName === 'acceptance') {
      const list = dbSources.contracts || [];
      if (list.length === 0) {
        selectEl.innerHTML = '<option value="acceptance:seiyo">Biên bản nghiệm thu tiêu chuẩn (Seiyo IIoT)</option>';
      } else {
        list.forEach(c => {
          const opt = document.createElement('option');
          opt.value = `acceptance:${c.id}`;
          opt.textContent = `[Nghiệm thu HĐ ${c.contract_code}] ${c.customer_name_vi || 'KH'} - ${c.project_name_vi || 'Dự án'}`;
          selectEl.appendChild(opt);
        });
        if (autoSelectFirst && list.length > 0) {
          loadFromContext('acceptance', list[0].id);
        }
      }
    }
  }

  function onEntitySelectChange(selectedValue) {
    if (!selectedValue) return;
    const parts = selectedValue.split(':');
    const type = parts[0];
    const val = parts[1];

    if (type === 'preset') {
      applyPreset(val);
    } else {
      loadFromContext(type, val);
    }
  }

  async function loadFromContext(source, id, code, fileName, category) {
    try {
      showLoading(true, 'Đang đồng bộ dữ liệu vào email...');
      let url = `/api/emails/load-context?source=${encodeURIComponent(source)}`;
      if (id) url += `&id=${encodeURIComponent(id)}`;
      if (code) url += `&code=${encodeURIComponent(code)}`;
      if (fileName) url += `&file_name=${encodeURIComponent(fileName)}`;
      if (category) url += `&category=${encodeURIComponent(category)}`;

      const res = await fetch(url);
      const data = await res.json();
      showLoading(false);

      if (data.status === 'success' && data.data) {
        const item = data.data;

        // Điền dữ liệu vào form
        document.getElementById('emailCustomer').value = item.customer_name || '';
        document.getElementById('emailRecipient').value = item.recipient_email || '';
        document.getElementById('emailCc').value = item.cc_emails || '';
        document.getElementById('emailSubject').value = item.subject || '';
        document.getElementById('emailContract').value = item.contract_number || '';
        document.getElementById('emailAmount').value = item.amount ? Number(item.amount).toLocaleString('vi-VN') : '0';
        document.getElementById('emailDueDate').value = item.due_date || '';
        document.getElementById('emailBody').value = item.body || '';
        const workflowLink = document.getElementById('emailWorkflowLink');
        if (workflowLink) workflowLink.href = item.workflow_url || '/workflows';

        // Lưu ngữ cảnh
        const modInput = document.getElementById('emailSourceModule');
        const idInput = document.getElementById('emailSourceId');
        if (modInput) modInput.value = source;
        if (idInput) idInput.value = id || '';

        // Tệp đính kèm
        renderAttachments(item.attachments || [], item.required_attachments || []);
        updateLivePreview();

        // Hiển thị indicator kết nối
        const indicator = document.getElementById('activeLinkIndicator');
        const linkText = document.getElementById('activeLinkText');
        const badge = document.getElementById('connectionStatusBadge');
        if (indicator && linkText) {
          indicator.style.display = 'inline-flex';
          linkText.textContent = `🔗 Đang liên kết: [${source.toUpperCase()}] ${item.customer_name || item.contract_number || ''}`;
        }
        if (badge) {
          badge.textContent = `Đồng Bộ CSDL: ${source.toUpperCase()}`;
          badge.className = 'badge-pill green';
        }

        // Đồng bộ giá trị vào dropdown nếu có
        const selectEl = document.getElementById('sourceEntitySelect');
        if (selectEl && id) {
          const expectedVal = `${source}:${id}`;
          for (let i = 0; i < selectEl.options.length; i++) {
            if (selectEl.options[i].value === expectedVal) {
              selectEl.selectedIndex = i;
              break;
            }
          }
        }

        showToast(`✅ Đã kết nối dữ liệu thành công từ [${source.toUpperCase()}]!`, 'success');
      } else {
        showToast('Không tìm thấy dữ liệu đối tượng được chọn', 'warning');
      }
    } catch (e) {
      showLoading(false);
      showToast('Lỗi khi nạp dữ liệu: ' + e.message, 'error');
    }
  }

  function resetConnection() {
    const modInput = document.getElementById('emailSourceModule');
    const idInput = document.getElementById('emailSourceId');
    if (modInput) modInput.value = 'CUSTOM';
    if (idInput) idInput.value = '';

    const indicator = document.getElementById('activeLinkIndicator');
    const badge = document.getElementById('connectionStatusBadge');
    if (indicator) indicator.style.display = 'none';
    if (badge) {
      badge.textContent = 'Soạn Tự Do';
      badge.className = 'badge-pill blue';
    }
    showToast('Đã chuyển sang chế độ soạn thảo tự do (không khóa ngữ cảnh).', 'info');
  }

  function applyPreset(presetId) {
    const found = presetsData.find(p => p.id === presetId);
    if (!found) return;

    currentPreset = found;
    document.getElementById('emailCustomer').value = found.customer || '';
    document.getElementById('emailRecipient').value = found.recipient || '';
    document.getElementById('emailCc').value = found.cc || '';
    document.getElementById('emailSubject').value = found.subject || '';
    document.getElementById('emailContract').value = found.contract_number || '';
    document.getElementById('emailAmount').value = found.amount ? found.amount.toLocaleString('vi-VN') : '0';
    document.getElementById('emailDueDate').value = found.due_date || '';
    document.getElementById('emailBody').value = found.body || '';

    const modInput = document.getElementById('emailSourceModule');
    const idInput = document.getElementById('emailSourceId');
    if (modInput) modInput.value = 'preset';
    if (idInput) idInput.value = found.id;

    // Cập nhật danh sách tệp đính kèm
    renderAttachments(found.attachments || [], found.required_attachments || []);
    updateLivePreview();

    const indicator = document.getElementById('activeLinkIndicator');
    const linkText = document.getElementById('activeLinkText');
    const badge = document.getElementById('connectionStatusBadge');
    if (indicator && linkText) {
      indicator.style.display = 'inline-flex';
      linkText.textContent = `🌟 Mẫu chuẩn: ${found.name}`;
    }
    if (badge) {
      badge.textContent = 'Mẫu Chuẩn Preset';
      badge.className = 'badge-pill blue';
    }
  }

  function renderAttachments(attachments, requiredRules) {
    const container = document.getElementById('attachmentsContainer');
    const warningBox = document.getElementById('attachmentsWarningBox');

    container.innerHTML = '';
    if (attachments && attachments.length > 0) {
      attachments.forEach(file => {
        const badge = document.createElement('span');
        badge.className = 'attachment-badge';
        badge.innerHTML = `📎 ${file}`;
        container.appendChild(badge);
      });
    } else {
      container.innerHTML = '<span style="color: #9ca3af; font-size: 0.82rem;">(Chưa có tệp đính kèm nào)</span>';
    }

    if (requiredRules && requiredRules.length > 0) {
      warningBox.style.display = 'flex';
      document.getElementById('warningRulesText').innerText = requiredRules.join(' | ');
    } else {
      warningBox.style.display = 'none';
    }
  }

  function updateLivePreview() {
    const to = document.getElementById('emailRecipient').value;
    const cc = document.getElementById('emailCc').value;
    const subject = document.getElementById('emailSubject').value;
    const body = document.getElementById('emailBody').value;

    document.getElementById('previewTo').innerText = to || '(Chưa nhập người nhận)';
    document.getElementById('previewCc').innerText = cc || '(Không CC)';
    document.getElementById('previewSubject').innerText = subject || '(Chưa có tiêu đề)';
    document.getElementById('previewBody').innerText = body || '';
  }

  async function copyRichText() {
    const body = document.getElementById('emailBody').value;
    const subject = document.getElementById('emailSubject').value;

    if (!body) {
      showToast('Nội dung thư đang trống!', 'warning');
      return;
    }

    try {
      // Chuẩn bị nội dung HTML với font chữ chuẩn để dán vào Outlook
      const formattedHtml = `
        <div style="font-family: 'Microsoft JhengHei', '微軟正黑體', 'Segoe UI', Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #1e293b;">
          ${body.replace(/\n/g, '<br>')}
        </div>
      `;

      if (navigator.clipboard && window.ClipboardItem) {
        const textBlob = new Blob([body], { type: 'text/plain' });
        const htmlBlob = new Blob([formattedHtml], { type: 'text/html' });
        const item = new ClipboardItem({
          'text/plain': textBlob,
          'text/html': htmlBlob
        });
        await navigator.clipboard.write([item]);
      } else {
        await navigator.clipboard.writeText(body);
      }

      showToast('✅ Đã sao chép nội dung thư (Rich Text)! Bạn có thể dán trực tiếp (Ctrl+V) vào Outlook hoặc Gmail.', 'success');
    } catch (err) {
      console.warn('Clipboard write error, falling back:', err);
      navigator.clipboard.writeText(body).then(() => {
        showToast('✅ Đã sao chép văn bản vào Clipboard!', 'success');
      });
    }
  }

  async function handleSaveDraft() {
    const payload = gatherPayload();
    try {
      showLoading(true, 'Đang lưu bản nháp email...');
      const res = await fetch('/api/emails/save-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      showLoading(false);

      if (data.status === 'success') {
        showToast(`✅ Đã lưu bản nháp (${data.email_code}) vào hệ thống!`, 'success');
      } else {
        showToast(data.message || 'Lỗi lưu bản nháp', 'error');
      }
    } catch (e) {
      showLoading(false);
      showToast('Lỗi kết nối máy chủ: ' + e.message, 'error');
    }
  }

  async function handleSimulateSend() {
    const payload = gatherPayload();

    const confirmed = confirm(
      `🛡️ XÁC NHẬN MÔ PHỎNG GỬI AN TOÀN:\n\n` +
      `- Module nguồn: ${payload.source_module || 'CUSTOM'}\n` +
      `- Khách hàng: ${payload.customer_name}\n` +
      `- Người nhận: ${payload.recipient_email}\n` +
      `- Tiêu đề: ${payload.subject}\n\n` +
      `CAM KẾT AN TOÀN: Hệ thống đang ở chế độ xem trước an toàn. Email sẽ KHÔNG gửi thật đến khách hàng.\n\n` +
      `Bạn có muốn thực hiện mô phỏng gửi không?`
    );

    if (!confirmed) return;

    try {
      showLoading(true, 'Đang thực hiện mô phỏng gửi an toàn...');
      const res = await fetch('/api/emails/simulate-send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      showLoading(false);

      if (data.status === 'success') {
        showToast(`🎉 ${data.message} (Mã: ${data.tracking_code})`, 'success');
      } else {
        showToast(data.message || 'Lỗi mô phỏng gửi', 'error');
      }
    } catch (e) {
      showLoading(false);
      showToast('Lỗi máy chủ: ' + e.message, 'error');
    }
  }

  async function openHistoryModal() {
    try {
      showLoading(true, 'Đang tải lịch sử email...');
      const res = await fetch('/api/emails/history');
      const data = await res.json();
      showLoading(false);

      const tbody = document.getElementById('historyTableBody');
      tbody.innerHTML = '';

      if (data.data && data.data.length > 0) {
        data.data.forEach(item => {
          const tr = document.createElement('tr');
          const statusBadge = item.status === 'SIMULATED_SENT' 
            ? '<span class="badge-pill green">Mô Phỏng Gửi</span>' 
            : '<span class="badge-pill blue">Bản Nháp</span>';

          const modText = item.source_module ? `<span class="badge-pill indigo" style="font-size: 0.72rem; margin-right: 4px;">${item.source_module.toUpperCase()}</span>` : '';

          tr.innerHTML = `
            <td style="font-size: 0.8rem; font-family: monospace;">${item.email_code}</td>
            <td style="font-size: 0.82rem; font-weight: 600;">${item.customer_name}</td>
            <td style="font-size: 0.82rem;">${modText}${item.subject}</td>
            <td style="font-size: 0.8rem; text-align: right;">${item.amount ? item.amount.toLocaleString('vi-VN') + ' đ' : '-'}</td>
            <td>${statusBadge}</td>
            <td style="font-size: 0.78rem; color: #64748b;">${item.created_at}</td>
          `;
          tbody.appendChild(tr);
        });
      } else {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #94a3b8; padding: 2rem;">Chưa có email nào trong lịch sử</td></tr>';
      }

      document.getElementById('emailHistoryModal').style.display = 'flex';
    } catch (e) {
      showLoading(false);
      showToast('Lỗi tải lịch sử: ' + e.message, 'error');
    }
  }

  function closeHistoryModal() {
    document.getElementById('emailHistoryModal').style.display = 'none';
  }

  function gatherPayload() {
    const rawAmt = document.getElementById('emailAmount').value.replace(/[^0-9]/g, '');
    const modInput = document.getElementById('emailSourceModule');
    const idInput = document.getElementById('emailSourceId');

    // Lấy danh sách attachment hiện tại
    const attachmentEls = document.querySelectorAll('#attachmentsContainer .attachment-badge');
    const attachments = [];
    attachmentEls.forEach(el => {
      attachments.push(el.textContent.replace('📎', '').trim());
    });

    return {
      email_type: currentPreset ? currentPreset.id : 'CUSTOM',
      customer_name: document.getElementById('emailCustomer').value,
      recipient_email: document.getElementById('emailRecipient').value,
      cc_emails: document.getElementById('emailCc').value,
      subject: document.getElementById('emailSubject').value,
      body_text: document.getElementById('emailBody').value,
      amount: parseFloat(rawAmt) || 0,
      due_date: document.getElementById('emailDueDate').value,
      attachments: attachments.length > 0 ? attachments : (currentPreset ? currentPreset.attachments : []),
      is_safe_mode: true,
      source_module: modInput ? modInput.value : '',
      source_id: idInput && idInput.value ? parseInt(idInput.value, 10) : null
    };
  }

  function showToast(msg, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) {
      alert(msg);
      return;
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
      background: ${type === 'success' ? '#10b981' : type === 'warning' ? '#f59e0b' : type === 'error' ? '#ef4444' : '#3b82f6'};
      color: #fff; padding: 0.75rem 1.25rem; border-radius: 6px; margin-bottom: 0.5rem;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-size: 0.9rem; font-weight: 500;
    `;
    toast.innerText = msg;
    container.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 4000);
  }

  function showLoading(show, text = 'Đang xử lý...') {
    const overlay = document.getElementById('globalLoadingOverlay');
    const loadingText = document.getElementById('loadingOverlayText');
    if (overlay) {
      overlay.style.display = show ? 'flex' : 'none';
      if (loadingText) loadingText.innerText = text;
    }
  }

  return {
    init,
    switchSourceTab,
    onEntitySelectChange,
    loadFromContext,
    resetConnection,
    applyPreset,
    updateLivePreview,
    copyRichText,
    handleSaveDraft,
    handleSimulateSend,
    openHistoryModal,
    closeHistoryModal
  };
})();
