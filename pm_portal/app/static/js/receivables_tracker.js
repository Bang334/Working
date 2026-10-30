// ==============================================================================
// TÍNH TOÁN HẠN THANH TOÁN (KÍCH HOẠT KHI VỪA LẮP ĐẶT XONG / NGHIỆM THU)
// ==============================================================================
function addDaysToDate(dateStr, days) {
  if (!dateStr) return "";
  const parts = dateStr.split("-");
  if (parts.length !== 3) return "";
  const y = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10) - 1;
  const d = parseInt(parts[2], 10);
  const date = new Date(y, m, d);
  date.setDate(date.getDate() + parseInt(days, 10));

  const resY = date.getFullYear();
  const resM = String(date.getMonth() + 1).padStart(2, "0");
  const resD = String(date.getDate()).padStart(2, "0");
  return `${resY}-${resM}-${resD}`;
}

function setStartDateToday() {
  const startInput = document.getElementById("editStartDate");
  if (startInput) {
    startInput.value = new Date().toISOString().split("T")[0];
    autoCalculateDueDateFromStart();
  }
}

function setPaymentTermDays(days) {
  const daysInput = document.getElementById("editPaymentTermDays");
  if (daysInput) {
    daysInput.value = days;
    document.querySelectorAll(".btn-pill-day").forEach(btn => {
      btn.classList.toggle("active", btn.textContent.includes(`${days} ngày`));
    });
    autoCalculateDueDateFromStart();
  }
}

function extractPaymentTermDaysFromNotes(notes, projectName) {
  const combined = `${notes || ""} ${projectName || ""}`.toLowerCase();
  const m1 = combined.match(/t\/t\s*(\d+)/i);
  if (m1) return parseInt(m1[1], 10);
  const m2 = combined.match(/(\d+)\s*ng[àa]y/i);
  if (m2) return parseInt(m2[1], 10);
  return 60; // Mặc định 60 ngày
}

function autoCalculateDueDateFromStart() {
  const startInput = document.getElementById("editStartDate");
  const daysInput = document.getElementById("editPaymentTermDays");
  const dueInput = document.getElementById("editDueDate");
  const hint = document.getElementById("calcDueResultHint");

  if (startInput && startInput.value && daysInput && daysInput.value) {
    const days = parseInt(daysInput.value, 10);
    if (!isNaN(days) && days > 0) {
      const calcDue = addDaysToDate(startInput.value, days);
      if (dueInput) dueInput.value = calcDue;
      if (hint) {
        hint.innerHTML = `<span style="color: #34D399; font-weight: 700;">✓ Tính hạn:</span> ${formatDateVN(startInput.value)} + <strong>${days} ngày</strong> &rarr; Đến hạn: <strong style="color: #38BDF8;">${formatDateVN(calcDue)}</strong>`;
      }
    }
  }
}

function triggerStartDueDateCalculation() {
  const startInput = document.getElementById("editStartDate");
  const daysInput = document.getElementById("editPaymentTermDays");
  const dueInput = document.getElementById("editDueDate");
  const hint = document.getElementById("calcDueResultHint");
  const badge = document.getElementById("triggerStatusBadge");

  if (!startInput.value) {
    startInput.value = new Date().toISOString().split("T")[0];
  }

  let days = parseInt(daysInput.value, 10);
  if (!days || isNaN(days) || days <= 0) {
    days = 60;
    daysInput.value = 60;
  }

  const calculatedDueDate = addDaysToDate(startInput.value, days);
  if (calculatedDueDate) {
    dueInput.value = calculatedDueDate;
    if (hint) {
      hint.innerHTML = `<strong style="color: #34D399;">✓ Bắt đầu tính:</strong> ${formatDateVN(startInput.value)} + <strong>${days} ngày</strong> &rarr; Đến hạn: <strong style="color: #38BDF8;">${formatDateVN(calculatedDueDate)}</strong>`;
    }
    if (badge) {
      badge.textContent = `Đang tính hạn (${days} ngày)`;
      badge.className = "trigger-status-badge active";
    }

    // Tự động bổ sung thông tin vào ghi chú tiến độ
    const notesArea = document.getElementById("editNotes");
    if (notesArea) {
      const startFmt = formatDateVN(startInput.value);
      const dueFmt = formatDateVN(calculatedDueDate);
      const logLine = `[Lắp đặt/Nghiệm thu: ${startFmt} - Tính hạn TT ${days} ngày -> Đến hạn: ${dueFmt}]`;
      if (!notesArea.value.includes(startFmt)) {
        notesArea.value = notesArea.value ? `${notesArea.value.trim()}\n${logLine}` : logLine;
      }
    }

    showToast(`Đã bắt đầu tính hạn: Đến hạn ngày ${formatDateVN(calculatedDueDate)} (${days} ngày T/T)!`, "success");
  }
}

/**
 * RECEIVABLES TRACKER JAVASCRIPT (Sheet 3 · AR Debt Portfolio)
 * Hong Ming Global PM Portal
 */

let allReceivables = [];
let allStats = {};
let isOverdueOnly = false;
let searchDebounceTimer = null;
let aiDigestData = null;

document.addEventListener("DOMContentLoaded", function () {
  loadReceivablesData();
});

// Format VND Currency
function formatDateVN(value) {
  if (!value || value === '-') return '-';
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:$|T)/.exec(String(value));
  return match ? `${match[3]}/${match[2]}/${match[1]}` : String(value);
}

function formatVND(amount) {
  if (amount === null || amount === undefined || isNaN(amount)) return "0 ₫";
  return Math.round(amount).toLocaleString("vi-VN") + " ₫";
}

// Show Toast
function showToast(message, type = "success") {
  const toast = document.getElementById("toastNotification");
  if (!toast) return;
  toast.className = `toast-notification ${type}`;
  toast.textContent = message;
  toast.style.display = "flex";

  setTimeout(() => {
    toast.style.display = "none";
  }, 3500);
}

// Fetch receivables from server
async function loadReceivablesData() {
  const customer = document.getElementById("filterCustomer")?.value || "all";
  const status = document.getElementById("filterStatus")?.value || "all";
  const contract = document.getElementById("filterContract")?.value || "all";
  const search = document.getElementById("filterSearch")?.value || "";

  const params = new URLSearchParams();
  if (customer && customer !== "all") params.append("customer", customer);
  if (status && status !== "all") params.append("status", status);
  if (search && search.trim()) params.append("search", search.trim());
  if (contract && contract !== "all") {
    // Nếu có chọn hợp đồng thì thêm từ khóa tìm kiếm hoặc lọc
    if (!params.has("search")) params.append("search", contract);
  }

  const tbody = document.getElementById("receivablesTableBody");
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="18" class="text-center py-5">
          <div class="loading-state">
            <div class="spinner"></div>
            <p style="margin-top: 0.5rem; color: #64748B;">Đang tải danh sách công nợ dự án...</p>
          </div>
        </td>
      </tr>
    `;
  }

  try {
    const res = await fetch(`/api/v1/receivables?${params.toString()}`);
    const data = await res.json();

    if (data.status === "success") {
      let items = data.receivables || [];
      allStats = data.stats || {};

      // Filter client-side by contract if selected
      if (contract && contract !== "all") {
        items = items.filter(it => it.contract_code === contract);
      }

      allReceivables = items;
      updateKpis(allStats);
      populateFilters(allStats.customers || [], allStats.contracts || []);
      populateHeaderFilterDropdownsAr(allReceivables);
      renderTable(allReceivables);
    } else {
      showToast(data.message || "Không thể tải dữ liệu công nợ", "error");
    }
  } catch (err) {
    console.error("Error loading receivables:", err);
    showToast("Lỗi kết nối máy chủ khi tải công nợ.", "error");
  }
}

// Update KPI Header Cards & Legend Chips
function updateKpis(stats) {
  const totalReceivable = document.getElementById("kpiTotalReceivable");
  const totalCount = document.getElementById("kpiTotalCount");
  const totalReceived = document.getElementById("kpiTotalReceived");
  const completionRate = document.getElementById("kpiCompletionRate");
  const totalDebt = document.getElementById("kpiTotalDebt");
  const pendingCount = document.getElementById("kpiPendingCount");
  const overdueCount = document.getElementById("kpiOverdueCount");
  const urgentSub = document.getElementById("kpiUrgentSub");

  if (totalReceivable) totalReceivable.textContent = stats.total_receivable_formatted || "0 ₫";
  if (totalCount) totalCount.textContent = `${stats.total_milestones || 0} đợt thanh toán`;
  if (totalReceived) totalReceived.textContent = stats.total_received_formatted || "0 ₫";
  if (completionRate) completionRate.textContent = `Tỷ lệ thu: ${stats.completion_rate || 0}% (${stats.paid_count || 0} đợt xong)`;
  if (totalDebt) totalDebt.textContent = stats.total_debt_formatted || "0 ₫";
  if (pendingCount) pendingCount.textContent = `Chờ thu: ${stats.pending_count || 0} đợt`;
  if (overdueCount) overdueCount.textContent = stats.overdue_count || 0;
  if (urgentSub) urgentSub.textContent = `${stats.urgent_count || 0} mốc sắp đến hạn (<=7 ngày)`;

  // Update counts on quick legend chips
  const chipCountAll = document.getElementById("chipCountAll");
  const chipCountOverdue = document.getElementById("chipCountOverdue");
  const chipCountUrgent = document.getElementById("chipCountUrgent");
  const chipCountPending = document.getElementById("chipCountPending");
  const chipCountPaid = document.getElementById("chipCountPaid");

  if (chipCountAll) chipCountAll.textContent = stats.total_milestones || 0;
  if (chipCountOverdue) chipCountOverdue.textContent = stats.overdue_count || 0;
  if (chipCountUrgent) chipCountUrgent.textContent = stats.urgent_count || 0;
  if (chipCountPending) chipCountPending.textContent = stats.pending_count || 0;
  if (chipCountPaid) chipCountPaid.textContent = stats.paid_count || 0;
}

// Populate Customer and Contract Filter Dropdowns
function populateFilters(customers, contracts) {
  const selCust = document.getElementById("filterCustomer");
  if (selCust) {
    const curCust = selCust.value;
    selCust.innerHTML = '<option value="all">Tất cả khách hàng</option>';
    customers.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      if (c === curCust) opt.selected = true;
      selCust.appendChild(opt);
    });
  }

  const selContract = document.getElementById("filterContract");
  if (selContract) {
    const curContract = selContract.value;
    selContract.innerHTML = '<option value="all">Tất cả hợp đồng</option>';
    contracts.forEach(cnt => {
      const opt = document.createElement("option");
      opt.value = cnt;
      opt.textContent = cnt;
      if (cnt === curContract) opt.selected = true;
      selContract.appendChild(opt);
    });
  }
}

// Populate Header Filter Dropdowns for AR Tracker
function populateHeaderFilterDropdownsAr(items) {
  const custSelect = document.getElementById("thArFilterCustomer");
  if (custSelect) {
    const curCust = custSelect.value;
    const custs = new Set();
    items.forEach(it => {
      if (it.customer_name && it.customer_name.trim() && it.customer_name.trim() !== "-") {
        custs.add(it.customer_name.trim());
      }
    });
    custSelect.innerHTML = '<option value="all">Tất cả KH</option>';
    Array.from(custs).sort().forEach(c => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      if (c === curCust) opt.selected = true;
      custSelect.appendChild(opt);
    });
  }

  const cntSelect = document.getElementById("thArFilterContract");
  if (cntSelect) {
    const curCnt = cntSelect.value;
    const cnts = new Set();
    items.forEach(it => {
      if (it.contract_code && it.contract_code.trim() && it.contract_code.trim() !== "-" && it.contract_code.trim() !== "None") {
        cnts.add(it.contract_code.trim());
      }
    });
    cntSelect.innerHTML = '<option value="all">Tất cả HĐ</option><option value="__no_contract__">(Không có HĐ)</option>';
    Array.from(cnts).sort().forEach(cnt => {
      const opt = document.createElement("option");
      opt.value = cnt;
      opt.textContent = cnt;
      if (cnt === curCnt) opt.selected = true;
      cntSelect.appendChild(opt);
    });
    if (curCnt === "__no_contract__") cntSelect.value = "__no_contract__";
  }
}

// Apply Header Column Filters for AR Tracker
function applyHeaderFiltersAr() {
  const projectVal = (document.getElementById("thArFilterProject")?.value || "").trim().toLowerCase();
  const custVal = document.getElementById("thArFilterCustomer")?.value || "all";
  const cntVal = document.getElementById("thArFilterContract")?.value || "all";
  const vatVal = document.getElementById("thArFilterVatRate")?.value || "all";
  const docVal = document.getElementById("thArFilterDoc")?.value || "all";
  const statusVal = document.getElementById("thArFilterStatus")?.value || "all";
  const notesVal = (document.getElementById("thArFilterNotes")?.value || "").trim().toLowerCase();

  const isAnyFilterActive = Boolean(
    projectVal ||
    (custVal !== "all") ||
    (cntVal !== "all") ||
    (vatVal !== "all") ||
    (docVal !== "all") ||
    (statusVal !== "all") ||
    notesVal
  );

  const filtered = allReceivables.filter(it => {
    if (projectVal) {
      const pName = (it.project_name || "").toLowerCase();
      if (!pName.includes(projectVal)) return false;
    }
    if (custVal && custVal !== "all") {
      if ((it.customer_name || "").trim() !== custVal) return false;
    }
    if (cntVal && cntVal !== "all") {
      if (cntVal === "__no_contract__") {
        if (it.contract_code && it.contract_code !== "-" && it.contract_code !== "None") return false;
      } else {
        if ((it.contract_code || "").trim() !== cntVal) return false;
      }
    }
    if (vatVal && vatVal !== "all") {
      const vr = it.vat_rate !== null && it.vat_rate !== undefined ? Number(it.vat_rate) : 0;
      if (Math.abs(vr - Number(vatVal)) > 0.001) return false;
    }
    if (docVal && docVal !== "all") {
      const cleanDoc = (it.doc_status || "").trim();
      const isInvoiced = cleanDoc && cleanDoc !== "Chưa xuất" && cleanDoc !== "-";
      if (docVal === "invoiced" && !isInvoiced) return false;
      if (docVal === "pending" && isInvoiced) return false;
    }
    if (statusVal && statusVal !== "all") {
      if (it.collection_status !== statusVal) return false;
    }
    if (notesVal) {
      const nText = (it.notes || "").toLowerCase();
      if (!nText.includes(notesVal)) return false;
    }
    return true;
  });

  renderTable(filtered, isAnyFilterActive);
}

// Reset Header Column Filters for AR Tracker
function resetHeaderFiltersAr() {
  const elProj = document.getElementById("thArFilterProject");
  const elCust = document.getElementById("thArFilterCustomer");
  const elCnt = document.getElementById("thArFilterContract");
  const elVat = document.getElementById("thArFilterVatRate");
  const elDoc = document.getElementById("thArFilterDoc");
  const elStat = document.getElementById("thArFilterStatus");
  const elNotes = document.getElementById("thArFilterNotes");

  if (elProj) elProj.value = "";
  if (elCust) elCust.value = "all";
  if (elCnt) elCnt.value = "all";
  if (elVat) elVat.value = "all";
  if (elDoc) elDoc.value = "all";
  if (elStat) elStat.value = "all";
  if (elNotes) elNotes.value = "";

  applyHeaderFiltersAr();
}

function receivableNotesKey(item) {
  const code = String(item.contract_code || '').trim();
  return code && code !== '-' && code !== 'None'
    ? JSON.stringify([String(item.customer_name || '').trim(), code])
    : `item:${item.id}`;
}

function contractNotesMap(items) {
  const groups = new Map();
  items.forEach(item => {
    const key = receivableNotesKey(item);
    if (!groups.has(key)) groups.set(key, []);
    const note = String(item.notes || '').trim();
    if (note && !groups.get(key).includes(note)) groups.get(key).push(note);
  });
  return new Map([...groups].map(([key, notes]) => [key, notes.join('\n\n')]));
}

function escapeNotesHtml(value) {
  return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function renderContractNote(itemId, note) {
  return `<div class="notes-text notes-preview" role="button" tabindex="0" aria-expanded="false"
    onclick="toggleContractNote(this)" onkeydown="if(event.key === 'Enter' || event.key === ' ') { event.preventDefault(); toggleContractNote(this); }"
    title="Nhấp để xem toàn bộ ghi chú">${escapeNotesHtml(note) || '<em style="color:#94a3b8">Chưa có ghi chú</em>'}</div>
    <div class="notes-actions">
      <button type="button" class="notes-toggle" onclick="toggleContractNote(this.parentElement.previousElementSibling)">Xem thêm</button>
      <button type="button" onclick="startEditingNotes(${itemId}, this.closest('.editable-notes-cell'))">Sửa ghi chú</button>
    </div>`;
}

function toggleContractNote(preview) {
  const expanded = preview.classList.toggle('notes-expanded');
  preview.setAttribute('aria-expanded', String(expanded));
  preview.title = expanded ? 'Nhấp để thu gọn' : 'Nhấp để xem toàn bộ ghi chú';
  preview.nextElementSibling.querySelector('.notes-toggle').textContent = expanded ? 'Thu gọn' : 'Xem thêm';
}

// Render Table Rows with Interactive In-Place Editing
function renderTable(items, isHeaderFiltered = false) {
  const tbody = document.getElementById("receivablesTableBody");
  const tfoot = document.getElementById("receivablesTableFoot");
  const counter = document.getElementById("tableItemCount");
  if (counter) {
    counter.textContent = isHeaderFiltered
      ? `${items.length} / ${allReceivables.length} đợt`
      : `${items.length} đợt`;
  }
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="18" class="text-center py-5" style="color: #64748B;">
          <p style="font-size: 1rem; margin-bottom: 0.4rem;">Không tìm thấy đợt thanh toán nào phù hợp với bộ lọc.</p>
          <button type="button" class="btn btn-outline btn-sm" onclick="resetHeaderFiltersAr()">Đặt lại đầu lọc</button>
        </td>
      </tr>
    `;
    if (tfoot) tfoot.innerHTML = "";
    return;
  }

  let sumContract = 0;
  let sumNet = 0;
  let sumVat = 0;
  let sumGross = 0;
  let sumRec = 0;
  let sumDebt = 0;

  // Keep each contract contiguous so rowspan never covers another contract.
  const grouped = new Map();
  items.forEach(item => {
    const key = receivableNotesKey(item);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(item);
  });
  const orderedItems = [...grouped.values()].flat();
  const sharedNotes = contractNotesMap([...allReceivables, ...items]);
  const rowsHtml = orderedItems.map((it, idx) => {
    const key = receivableNotesKey(it);
    const firstInContract = idx === 0 || receivableNotesKey(orderedItems[idx - 1]) !== key;
    const notesCell = firstInContract ? `
        <td class="col-notes" rowspan="${grouped.get(key).length}" style="vertical-align: top;">
          <div class="editable-notes-cell">
            ${renderContractNote(it.id, sharedNotes.get(key) || '')}
          </div>
        </td>` : '';
    sumContract += (it.total_contract_amount || 0);
    sumNet += (it.net_amount || 0);
    sumVat += (it.vat_amount || 0);
    sumGross += (it.gross_amount || 0);
    sumRec += (it.received_amount || 0);
    sumDebt += (it.remaining_debt || 0);

    const stt = it.order_no || (idx + 1);
    const projName = it.project_name || "-";
    const custName = it.customer_name || "-";
    const contractCode = (it.contract_code && it.contract_code !== "-" && it.contract_code !== "None")
      ? `<span class="badge-pill blue" style="font-size: 0.75rem; font-family: monospace;">${it.contract_code}</span>`
      : `<span style="color: #94A3B8; font-style: italic; font-size: 0.8rem;">(Không HĐ)</span>`;

    // Due Date and Left Days Badge
    let dueBadge = "";
    if (it.collection_status === "DELAYED" && it.days_left !== null) {
      dueBadge = `<span class="overdue-pill">Trễ ${Math.abs(it.days_left)} ngày</span>`;
    } else if (it.collection_status === "URGENT" && it.days_left !== null) {
      dueBadge = `<span class="urgent-pill">Còn ${it.days_left} ngày</span>`;
    }

    // Status Select Options
    const statusSelect = `
      <select class="status-select-inline" onchange="updateCollectionStatus(${it.id}, this.value)" title="Nhấp chọn trạng thái thu nợ">
        <option value="PAID" ${it.collection_status === 'PAID' ? 'selected' : ''}>Đã thu (已收款)</option>
        <option value="PENDING" ${it.collection_status === 'PENDING' ? 'selected' : ''}>Chờ thu (待收款)</option>
        <option value="URGENT" ${it.collection_status === 'URGENT' ? 'selected' : ''}>Sắp đến hạn (即將到期)</option>
        <option value="DELAYED" ${it.collection_status === 'DELAYED' ? 'selected' : ''}>Quá hạn (已逾期)</option>
      </select>
    `;

    // VAT Rate Dropdown
    const vatRate = it.vat_rate !== null && it.vat_rate !== undefined ? Number(it.vat_rate) : 0;
    const vatSelect = `
      <select class="inline-vat-select" onchange="updateReceivableInline(${it.id}, 'vat_rate', this.value)" title="Nhấp chọn thuế suất VAT để tự động tính tiền">
        <option value="0" ${vatRate === 0 ? 'selected' : ''}>0% (-)</option>
        <option value="0.08" ${Math.abs(vatRate - 0.08) < 0.001 ? 'selected' : ''}>8% (VAT)</option>
        <option value="0.10" ${Math.abs(vatRate - 0.10) < 0.001 ? 'selected' : ''}>10% (VAT)</option>
      </select>
    `;

    // Customer Promised Date Picker
    const promisedDatePicker = `
      <div class="inline-date-picker-wrap">
        <input type="date" class="inline-date-input" value="${it.customer_promised_date || ''}"
               onchange="updateReceivableInline(${it.id}, 'customer_promised_date', this.value)"
               title="Chọn ngày KH cam kết thanh toán">
        ${it.customer_promised_date ? `<button type="button" class="btn-clear-date" onclick="clearDateInline(${it.id}, 'customer_promised_date', event)" title="Xóa ngày">×</button>` : ''}
      </div>
    `;

    // Due Date Picker
    const dueDatePicker = `
      <div class="inline-date-picker-wrap">
        <input type="date" class="inline-date-input" value="${it.due_date || ''}"
               onchange="updateReceivableInline(${it.id}, 'due_date', this.value)"
               title="Chọn hạn thanh toán">
        ${it.due_date ? `<button type="button" class="btn-clear-date" onclick="clearDateInline(${it.id}, 'due_date', event)" title="Xóa hạn TT">×</button>` : ''}
      </div>
      ${dueBadge ? `<div style="margin-top: 0.25rem;">${dueBadge}</div>` : ''}
    `;

    // Paid Date Picker
    const paidDatePicker = `
      <div class="inline-date-picker-wrap">
        <input type="date" class="inline-date-input" value="${it.paid_date || ''}"
               onchange="updateReceivableInline(${it.id}, 'paid_date', this.value)"
               title="Chọn ngày KH đã chuyển tiền">
        ${it.paid_date ? `<button type="button" class="btn-clear-date" onclick="clearDateInline(${it.id}, 'paid_date', event)" title="Xóa ngày TT">×</button>` : ''}
      </div>
    `;

    // Editable Received Amount Cell
    const receivedAmountCell = `
      <div class="editable-amount-cell" onclick="startEditingAmount(${it.id}, ${it.received_amount || 0}, this)" title="Nhấp để sửa số tiền đã nhận">
        <span class="amount-val">${formatVND(it.received_amount)}</span>
        <span class="edit-hint-icon" aria-hidden="true">✏️</span>
      </div>
    `;

    // Editable Doc Status Cell
    const cleanDoc = (it.doc_status || '').replace(/"/g, '&quot;');
    const isInvoiced = cleanDoc && cleanDoc !== 'Chưa xuất' && cleanDoc !== '-';
    const docStatusCell = `
      <div class="editable-doc-cell" onclick="startEditingDocStatus(${it.id}, '${cleanDoc}', this)" title="Nhấp để sửa trạng thái hóa đơn / chứng từ">
        <span class="badge-doc ${isInvoiced ? 'invoiced' : ''}">${cleanDoc || 'Chưa xuất'}</span>
        <span class="edit-hint-icon" aria-hidden="true">✏️</span>
      </div>
    `;

    return `
      <tr data-id="${it.id}">
        <td class="text-center sticky-col col-1">${stt}</td>
        <td class="sticky-col col-2" style="font-weight: 500;" title="${projName}">
          <div class="table-proj-click" onclick="handleTableProjectClick(event, ${it.id})" title="Nhấp chuột xem chi tiết dự án & các đợt" style="cursor: pointer; color: #0284C7; font-weight: 600; display: inline-flex; align-items: center; gap: 0.35rem;">
            <span>${projName}</span>
            <span style="font-size: 0.72rem; opacity: 0.75;" aria-hidden="true">🔍</span>
          </div>
        </td>
        <td class="sticky-col col-3" style="font-weight: 600;" title="${custName}">${custName}</td>
        <td class="text-center" style="font-family: monospace;">${contractCode}</td>
        <td class="text-end">${formatVND(it.total_contract_amount)}</td>
        <td class="text-end" style="font-weight: 600;">${formatVND(it.net_amount)}</td>
        <td class="text-center">${vatSelect}</td>
        <td class="text-end" style="color: #64748B;">${(it.vat_amount && it.vat_amount > 0) ? formatVND(it.vat_amount) : '-'}</td>
        <td class="text-end" style="font-weight: 700; color: #1F4E79;">${formatVND(it.gross_amount)}</td>
        <td class="text-end" style="color: #059669; font-weight: 600;">${receivedAmountCell}</td>
        <td class="text-end highlight-debt">${formatVND(it.remaining_debt)}</td>
        <td class="text-center">${promisedDatePicker}</td>
        <td class="text-center">${dueDatePicker}</td>
        <td class="text-center">${paidDatePicker}</td>
        <td class="text-center">${docStatusCell}</td>
        <td class="text-center">${statusSelect}</td>
        ${notesCell}
        <td class="text-center">
          <div style="display: flex; gap: 0.25rem; justify-content: center; align-items: center;">
            <button type="button" class="btn-action-icon warning" onclick="openEditReceivableModal(${it.id})" title="Chỉnh sửa toàn bộ thông tin đợt này (Mở form)">
              <svg class="icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <a href="/emails?source=receivable&id=${it.id}" class="btn-action-icon" style="color: #0284c7; font-weight: 700;" title="✉️ Soạn Email Nhắc Nợ B2B song ngữ cho đợt này">
              ✉️
            </a>
            <a href="/reminders" class="btn-action-icon primary" title="Tạo Thư Nhắc Nợ / Lịch nhắc cho đợt này">
              <svg class="icon" viewBox="0 0 24 24" width="13" height="13"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
            </a>
            <a href="/payment-requests" class="btn-action-icon" title="Tạo Đơn Xin Thanh Toán chi phí">
              <svg class="icon" viewBox="0 0 24 24" width="13" height="13"><rect x="2" y="4" width="20" height="16" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
            </a>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  tbody.innerHTML = rowsHtml;

  // Render Table Foot Summary
  if (tfoot) {
    tfoot.innerHTML = `
      <tr>
        <td colspan="4" class="text-center sticky-col" style="font-weight: 700; left: 0; z-index: 26;">TỔNG CỘNG / 合計 (${items.length} đợt)</td>
        <td class="text-end">${formatVND(sumContract)}</td>
        <td class="text-end">${formatVND(sumNet)}</td>
        <td class="text-center">-</td>
        <td class="text-end">${sumVat > 0 ? formatVND(sumVat) : '-'}</td>
        <td class="text-end" style="color: #1F4E79; font-weight: 800;">${formatVND(sumGross)}</td>
        <td class="text-end" style="color: #059669; font-weight: 800;">${formatVND(sumRec)}</td>
        <td class="text-end highlight-debt" style="font-size: 0.92rem;">${formatVND(sumDebt)}</td>
        <td colspan="7" class="text-center" style="font-weight: 500; color: #475569;">Thu hồi: ${sumGross > 0 ? ((sumRec / sumGross) * 100).toFixed(1) : 0}%</td>
      </tr>
    `;
  }
}

// Universal Inline Field Update (vat_rate, due_date, customer_promised_date, paid_date, received_amount, doc_status)
async function updateReceivableInline(itemId, field, value) {
  try {
    const res = await fetch(`/api/v1/receivables/${itemId}/inline`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field, value })
    });
    const data = await res.json();
    if (data.status === "success") {
      let fieldLabel = field;
      if (field === "vat_rate") fieldLabel = "thuế suất VAT";
      else if (field === "due_date") fieldLabel = "ngày đến hạn";
      else if (field === "paid_date") fieldLabel = "ngày thanh toán";
      else if (field === "customer_promised_date") fieldLabel = "ngày hẹn thanh toán";
      else if (field === "received_amount") fieldLabel = "số tiền đã nhận";
      else if (field === "doc_status") fieldLabel = "trạng thái chứng từ";

      showToast(`Đã lưu ${fieldLabel} thành công!`, "success");
      loadReceivablesData();
    } else {
      showToast(data.message || "Lỗi cập nhật dữ liệu", "error");
    }
  } catch (err) {
    console.error("Error updating inline:", err);
    showToast("Lỗi kết nối khi cập nhật dữ liệu.", "error");
  }
}

// Clear date inline
function clearDateInline(itemId, field, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  updateReceivableInline(itemId, field, null);
}

// Inline Edit Received Amount
function startEditingAmount(itemId, currentVal, cellElement) {
  if (cellElement.querySelector("input")) return;
  const originalHtml = cellElement.innerHTML;

  cellElement.innerHTML = `
    <div class="inline-amount-edit-wrap">
      <input type="number" class="form-control form-control-xs inline-amount-input" value="${currentVal || 0}" step="1000" min="0">
      <div class="inline-btn-group">
        <button type="button" class="btn-check-save" title="Lưu">✓</button>
        <button type="button" class="btn-cancel-save" title="Hủy">✕</button>
      </div>
    </div>
  `;

  const input = cellElement.querySelector("input");
  const btnSave = cellElement.querySelector(".btn-check-save");
  const btnCancel = cellElement.querySelector(".btn-cancel-save");

  input.focus();
  input.select();

  const doSave = () => {
    const newVal = parseFloat(input.value) || 0;
    if (newVal !== currentVal) {
      updateReceivableInline(itemId, "received_amount", newVal);
    } else {
      cellElement.innerHTML = originalHtml;
    }
  };

  const doCancel = (e) => {
    if (e) e.stopPropagation();
    cellElement.innerHTML = originalHtml;
  };

  btnSave.addEventListener("click", (e) => {
    e.stopPropagation();
    doSave();
  });

  btnCancel.addEventListener("click", doCancel);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      doSave();
    } else if (e.key === "Escape") {
      e.preventDefault();
      doCancel();
    }
  });
}

// Inline Edit Doc Status
function startEditingDocStatus(itemId, currentVal, cellElement) {
  if (cellElement.querySelector("input")) return;
  const originalHtml = cellElement.innerHTML;
  const safeVal = (currentVal === "Chưa xuất" || currentVal === "-") ? "" : currentVal;

  cellElement.innerHTML = `
    <div class="inline-doc-edit-wrap">
      <input type="text" class="form-control form-control-xs inline-doc-input" value="${safeVal}" placeholder="HD-...">
      <div class="inline-btn-group">
        <button type="button" class="btn-check-save" title="Lưu">✓</button>
        <button type="button" class="btn-cancel-save" title="Hủy">✕</button>
      </div>
    </div>
  `;

  const input = cellElement.querySelector("input");
  const btnSave = cellElement.querySelector(".btn-check-save");
  const btnCancel = cellElement.querySelector(".btn-cancel-save");

  input.focus();
  input.select();

  const doSave = () => {
    const newVal = input.value.trim();
    if (newVal !== safeVal) {
      updateReceivableInline(itemId, "doc_status", newVal || "Chưa xuất");
    } else {
      cellElement.innerHTML = originalHtml;
    }
  };

  const doCancel = (e) => {
    if (e) e.stopPropagation();
    cellElement.innerHTML = originalHtml;
  };

  btnSave.addEventListener("click", (e) => {
    e.stopPropagation();
    doSave();
  });

  btnCancel.addEventListener("click", doCancel);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      doSave();
    } else if (e.key === "Escape") {
      e.preventDefault();
      doCancel();
    }
  });
}

// Inline Update Collection Status
async function updateCollectionStatus(itemId, newStatus) {
  try {
    const res = await fetch(`/api/v1/receivables/${itemId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collection_status: newStatus })
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast("Đã cập nhật trạng thái thu tiền!", "success");
      loadReceivablesData();
    } else {
      showToast(data.message || "Lỗi cập nhật trạng thái", "error");
    }
  } catch (err) {
    console.error("Error updating status:", err);
    showToast("Không thể cập nhật trạng thái thu tiền.", "error");
  }
}

// Inline Edit Notes
function startEditingNotes(itemId, cellElement) {
  if (cellElement.querySelector('textarea')) return;
  const currentTextSpan = cellElement.querySelector(".notes-text");
  const rawText = currentTextSpan.querySelector('em') ? "" : currentTextSpan.textContent;

  // Replace with textarea
  cellElement.innerHTML = `
    <textarea class="notes-editor-textarea" placeholder="Nhập ghi chú tiến độ chung của hợp đồng...">${escapeNotesHtml(rawText)}</textarea>
  `;
  const textarea = cellElement.querySelector("textarea");
  textarea.focus();

  // Save on blur or Ctrl/Shift+Enter
  const saveAction = async () => {
    const newNotes = textarea.value.trim();
    cellElement.innerHTML = renderContractNote(itemId, newNotes);

    if (newNotes !== rawText) {
      try {
        const res = await fetch(`/api/v1/receivables/${itemId}/notes`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ notes: newNotes })
        });
        const data = await res.json();
        if (data.status === "success") {
          const item = allReceivables.find(row => row.id === itemId);
          if (item) allReceivables.forEach(row => {
            if (receivableNotesKey(row) === receivableNotesKey(item)) row.notes = newNotes;
          });
          showToast("Đã lưu ghi chú thành công!", "success");
        } else {
          cellElement.innerHTML = renderContractNote(itemId, rawText);
          showToast(data.message || "Lỗi lưu ghi chú", "error");
        }
      } catch (e) {
        cellElement.innerHTML = renderContractNote(itemId, rawText);
        showToast("Không thể lưu ghi chú.", "error");
      }
    }
  };

  textarea.addEventListener("blur", saveAction);
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      textarea.blur();
    }
  });
}

// Filter triggers
function onFilterChange() {
  // Sync chips with selected status
  const curStatus = document.getElementById("filterStatus")?.value || "all";
  syncChipsWithStatus(curStatus);
  loadReceivablesData();
}

function debounceSearch() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    loadReceivablesData();
  }, 350);
}

// Filter by clicking on quick chips
function filterByChip(statusVal, element) {
  document.querySelectorAll(".legend-chip").forEach(chip => chip.classList.remove("active"));
  if (element) element.classList.add("active");

  const selStat = document.getElementById("filterStatus");
  if (selStat) selStat.value = statusVal;

  loadReceivablesData();
}

function syncChipsWithStatus(statusVal) {
  document.querySelectorAll(".legend-chip").forEach(chip => chip.classList.remove("active"));
  if (statusVal === "all") {
    document.getElementById("chipAll")?.classList.add("active");
  } else if (statusVal === "DELAYED") {
    document.getElementById("chipOverdue")?.classList.add("active");
  } else if (statusVal === "URGENT") {
    document.getElementById("chipUrgent")?.classList.add("active");
  } else if (statusVal === "PENDING") {
    document.getElementById("chipPending")?.classList.add("active");
  } else if (statusVal === "PAID") {
    document.getElementById("chipPaid")?.classList.add("active");
  }
}

function resetFilters() {
  const selCust = document.getElementById("filterCustomer");
  const selStat = document.getElementById("filterStatus");
  const selContract = document.getElementById("filterContract");
  const inputSearch = document.getElementById("filterSearch");

  if (selCust) selCust.value = "all";
  if (selStat) selStat.value = "all";
  if (selContract) selContract.value = "all";
  if (inputSearch) inputSearch.value = "";

  document.querySelectorAll(".legend-chip").forEach(chip => chip.classList.remove("active"));
  document.getElementById("chipAll")?.classList.add("active");

  // Reset Header Column Filters
  const elProj = document.getElementById("thArFilterProject");
  const elCustH = document.getElementById("thArFilterCustomer");
  const elCntH = document.getElementById("thArFilterContract");
  const elVatH = document.getElementById("thArFilterVatRate");
  const elDocH = document.getElementById("thArFilterDoc");
  const elStatH = document.getElementById("thArFilterStatus");
  const elNotesH = document.getElementById("thArFilterNotes");

  if (elProj) elProj.value = "";
  if (elCustH) elCustH.value = "all";
  if (elCntH) elCntH.value = "all";
  if (elVatH) elVatH.value = "all";
  if (elDocH) elDocH.value = "all";
  if (elStatH) elStatH.value = "all";
  if (elNotesH) elNotesH.value = "";

  loadReceivablesData();
}

// Sync from Web Contracts (DB)
async function syncFromContracts() {
  try {
    showToast("Đang đồng bộ các mốc thanh toán từ Hợp đồng trong Database...", "success");
    const res = await fetch("/api/v1/receivables/sync", { method: "POST" });
    const data = await res.json();
    if (data.status === "success") {
      showToast(data.message, "success");
      loadReceivablesData();
    } else {
      showToast(data.message || "Đồng bộ thất bại", "error");
    }
  } catch (err) {
    showToast("Lỗi máy chủ khi đồng bộ hợp đồng.", "error");
  }
}

// Toggle Table Fullscreen View
function toggleTableFullscreen() {
  const card = document.getElementById("receivablesCard");
  const text = document.getElementById("btnToggleFullscreenText");
  const btn = document.getElementById("btnToggleTableFullscreen");
  if (!card) return;
  const isFull = card.classList.toggle("fullscreen");
  document.body.classList.toggle("table-modal-fullscreen-open", isFull);
  if (isFull) {
    if (text) text.textContent = "Thu Nhỏ (Esc)";
    if (btn) btn.className = "btn btn-danger btn-xs";
    showToast("Đã mở Full màn hình. Nhấn phím Esc để thu nhỏ.", "success");
  } else {
    if (text) text.textContent = "Full Màn Hình";
    if (btn) btn.className = "btn btn-outline btn-xs";
  }
}

// Quick Horizontal Scroll buttons
function scrollTableHorizontally(direction) {
  const wrapper = document.getElementById("tableContainer");
  if (!wrapper) return;
  const distance = direction === "right" ? 500 : -500;
  wrapper.scrollBy({ left: distance, behavior: "smooth" });
}

// Global Escape listener to exit fullscreen
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    const card = document.getElementById("receivablesCard");
    if (card && card.classList.contains("fullscreen")) {
      toggleTableFullscreen();
    }
  }
});

// Export Excel Matching Sheet 3
function exportReceivablesExcel() {
  const customer = document.getElementById("filterCustomer")?.value || "all";
  const status = document.getElementById("filterStatus")?.value || "all";
  const search = document.getElementById("filterSearch")?.value || "";

  const params = new URLSearchParams();
  if (customer && customer !== "all") params.append("customer", customer);
  if (status && status !== "all") params.append("status", status);
  if (search && search.trim()) params.append("search", search.trim());
  if (isOverdueOnly) params.append("overdue_only", "true");

  window.location.href = `/api/v1/receivables/export-excel?${params.toString()}`;
}

// AI Executive Risk Digest
async function toggleAiDigest() {
  const panel = document.getElementById("aiDigestPanel");
  if (!panel) return;

  if (panel.style.display === "none" || !panel.style.display) {
    panel.style.display = "block";
    if (!aiDigestData) {
      await fetchAiDigest();
    }
  } else {
    panel.style.display = "none";
  }
}

async function fetchAiDigest() {
  const headline = document.getElementById("aiHeadline");
  const healthBadge = document.getElementById("aiHealthText");
  const risksList = document.getElementById("aiRisksList");
  const actionsList = document.getElementById("aiActionsList");
  const execNote = document.getElementById("aiExecutiveNote");

  if (headline) headline.textContent = "AI Gemini đang phân tích danh mục công nợ & phát hiện rủi ro thu hồi...";

  try {
    const res = await fetch("/api/v1/receivables/ai-digest");
    const data = await res.json();

    if (data.status === "success" && data.digest) {
      aiDigestData = data.digest;
      const d = data.digest;

      if (healthBadge) healthBadge.textContent = `${d.health_status || 'Bình thường'} (${d.health_score || 0}/100)`;
      if (headline) headline.textContent = d.summary_headline || "Đã hoàn tất phân tích.";

      // Render Top Risks
      if (risksList) {
        if (d.top_risks && d.top_risks.length > 0) {
          risksList.innerHTML = d.top_risks.map(r => `
            <div class="ai-risk-card">
              <div class="risk-info">
                <span class="risk-cust">${r.customer}</span>
                <span class="risk-proj">${r.project} · ${r.recommended_action || ''}</span>
              </div>
              <div style="text-align: right;">
                <span class="risk-badge">${r.overdue_days || 'Quá hạn'}</span>
                <div style="font-weight: 700; color: #DC2626; font-size: 0.8rem; margin-top: 0.15rem;">${r.debt_amount}</div>
              </div>
            </div>
          `).join("");
        } else {
          risksList.innerHTML = '<p style="color: #059669; font-size: 0.85rem;">Không có khoản nợ nào ở mức rủi ro cao.</p>';
        }
      }

      // Render Action Items
      if (actionsList) {
        if (d.action_items && d.action_items.length > 0) {
          actionsList.innerHTML = d.action_items.map(a => `
            <div class="ai-action-item">${a}</div>
          `).join("");
        }
      }

      // Render Bilingual Executive Note
      if (execNote && d.bilingual_executive_note) {
        execNote.textContent = d.bilingual_executive_note;
        execNote.style.display = "block";
      }
    }
  } catch (err) {
    console.error("AI Digest error:", err);
    if (headline) headline.textContent = "Không thể tải phân tích AI.";
  }
}

/* ==========================================================================
   MODAL EDIT & CREATE RECEIVABLE HANDLERS
   ========================================================================== */

// Open Edit Receivable Modal
async function openEditReceivableModal(itemId) {
  // Ẩn các tooltip/hover card đang mở
  hideSegmentTooltip();
  hideProjectHoverCard();

  let item = allReceivables.find(x => x.id === itemId);
  if (!item) {
    try {
      const res = await fetch(`/api/v1/receivables/${itemId}`);
      const data = await res.json();
      if (data.status === "success") item = data.receivable;
    } catch (e) {
      console.error("Error fetching receivable detail:", e);
    }
  }

  // Fallback từ segmentLookupMap nếu xem dữ liệu mẫu hoặc file riêng
  if (!item && segmentLookupMap && segmentLookupMap[itemId]) {
    const info = segmentLookupMap[itemId];
    const s = info.segment;
    const c = info.contract;
    const gross = parseFloat(s.gross_amount) || 0;
    const rec = parseFloat(s.curr_received !== undefined ? s.curr_received : (s.received_amount || 0)) || 0;
    item = {
      id: s.id,
      project_name: s.milestone_name || c.project_title_vi || c.project_title,
      contract_code: (c.contract_code && c.contract_code !== '-') ? c.contract_code : '',
      customer_name: c.customer_name || '',
      net_amount: gross,
      vat_rate: 0,
      received_amount: rec,
      customer_promised_date: (s.customer_promised_date && s.customer_promised_date !== '-') ? s.customer_promised_date : '',
      due_date: (s.due_date && s.due_date !== '-') ? s.due_date : '',
      paid_date: (s.paid_date && s.paid_date !== '-') ? s.paid_date : '',
      doc_status: (s.doc_status && s.doc_status !== '-') ? s.doc_status : '',
      collection_status: s.curr_status || 'PENDING',
      notes: (s.notes && s.notes !== '-') ? s.notes : ''
    };
  }

  if (!item) {
    showToast("Không tìm thấy thông tin đợt thanh toán.", "error");
    return;
  }

  document.getElementById("editRecId").value = item.id;
  document.getElementById("editProjectName").value = item.project_name || "";
  document.getElementById("editContractCode").value = item.contract_code || "";
  document.getElementById("editCustomerName").value = item.customer_name || "";
  document.getElementById("editNetAmount").value = item.net_amount || 0;

  const vatRateSelect = document.getElementById("editVatRate");
  const rawVat = Number(item.vat_rate || 0);
  if (Math.abs(rawVat - 0.08) < 0.001) vatRateSelect.value = "0.08";
  else if (Math.abs(rawVat - 0.10) < 0.001) vatRateSelect.value = "0.10";
  else vatRateSelect.value = "0";

  document.getElementById("editReceivedAmount").value = item.received_amount || 0;
  document.getElementById("editCustomerPromisedDate").value = item.customer_promised_date || "";
  document.getElementById("editDueDate").value = item.due_date || "";
  document.getElementById("editPaidDate").value = item.paid_date || "";
  document.getElementById("editDocStatus").value = item.doc_status || "";
  document.getElementById("editCollectionStatus").value = item.collection_status || "PENDING";
  document.getElementById("editNotes").value = item.notes || "";

  recalcEditModalAmounts();

  const modal = document.getElementById("modalEditReceivable");
  if (modal) {
    modal.style.display = "block";
    modal.classList.add("show");
  }
}

// Close Edit Modal
function closeEditReceivableModal() {
  const modal = document.getElementById("modalEditReceivable");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("show");
  }
  removeSegmentActiveHighlight();
}

// Recalculate Live Amounts on Edit Modal
function recalcEditModalAmounts() {
  const net = parseFloat(document.getElementById("editNetAmount")?.value) || 0;
  const vatRate = parseFloat(document.getElementById("editVatRate")?.value) || 0;
  const received = parseFloat(document.getElementById("editReceivedAmount")?.value) || 0;

  const vatAmount = Math.round(net * vatRate);
  const gross = net + vatAmount;
  const remaining = Math.max(0, gross - received);

  const prevNet = document.getElementById("previewNetAmount");
  const prevVat = document.getElementById("previewVatAmount");
  const prevGross = document.getElementById("previewGrossAmount");
  const prevRec = document.getElementById("previewReceivedAmount");
  const prevDebt = document.getElementById("previewRemainingDebt");

  if (prevNet) prevNet.textContent = formatVND(net);
  if (prevVat) prevVat.textContent = `VAT: ${formatVND(vatAmount)}`;
  if (prevGross) prevGross.value = formatVND(gross);
  if (prevRec) prevRec.textContent = formatVND(received);
  if (prevDebt) prevDebt.value = formatVND(remaining);
}

// Auto change collection status to PAID if paid date is entered
function onEditPaidDateChange(val) {
  if (val && val.trim()) {
    const statusSel = document.getElementById("editCollectionStatus");
    if (statusSel) statusSel.value = "PAID";
  }
}

// Save Edit Receivable
async function saveReceivableModal() {
  const id = document.getElementById("editRecId")?.value;
  if (!id) return;

  const projName = document.getElementById("editProjectName")?.value.trim();
  const custName = document.getElementById("editCustomerName")?.value.trim();
  if (!projName || !custName) {
    showToast("Vui lòng điền tên dự án và khách hàng.", "error");
    return;
  }

  const net = parseFloat(document.getElementById("editNetAmount")?.value) || 0;
  const vatRate = parseFloat(document.getElementById("editVatRate")?.value) || 0;
  const received = parseFloat(document.getElementById("editReceivedAmount")?.value) || 0;
  const promised = document.getElementById("editCustomerPromisedDate")?.value || null;
  const due = document.getElementById("editDueDate")?.value || null;
  const paid = document.getElementById("editPaidDate")?.value || null;
  const doc = document.getElementById("editDocStatus")?.value.trim() || null;
  const status = document.getElementById("editCollectionStatus")?.value || "PENDING";
  const notes = document.getElementById("editNotes")?.value.trim() || null;
  const contract = document.getElementById("editContractCode")?.value.trim() || null;

  const payload = {
    project_name: projName,
    customer_name: custName,
    contract_code: contract,
    net_amount: net,
    vat_rate: vatRate,
    received_amount: received,
    customer_promised_date: promised,
    due_date: due,
    paid_date: paid,
    doc_status: doc,
    collection_status: status,
    notes: notes
  };

  try {
    const res = await fetch(`/api/v1/receivables/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast("Đã lưu chi tiết đợt công nợ thành công!", "success");
      closeEditReceivableModal();
      loadReceivablesData(true);

      // Tự động làm mới biểu đồ so sánh tuần nếu đang mở fullscreen modal
      const compModal = document.getElementById("modalWeeklyComparisonFullscreen");
      if (compModal && (compModal.style.display === "flex" || compModal.classList.contains("active"))) {
        loadWeeklyComparisonData();
      }
    } else {
      showToast(data.message || "Lỗi lưu dữ liệu", "error");
    }
  } catch (err) {
    console.error("Save error:", err);
    showToast("Lỗi máy chủ khi lưu đợt công nợ.", "error");
  }
}

// Confirm Delete Receivable
async function confirmDeleteCurrentReceivable() {
  const id = document.getElementById("editRecId")?.value;
  if (!id) return;
  if (!confirm("Bạn có chắc chắn muốn xóa đợt thanh toán này khỏi danh mục theo dõi?")) {
    return;
  }

  try {
    const res = await fetch(`/api/v1/receivables/${id}`, { method: "DELETE" });
    const data = await res.json();
    if (data.status === "success") {
      showToast("Đã xóa đợt công nợ thành công!", "success");
      closeEditReceivableModal();
      loadReceivablesData(true);

      const compModal = document.getElementById("modalWeeklyComparisonFullscreen");
      if (compModal && (compModal.style.display === "flex" || compModal.classList.contains("active"))) {
        loadWeeklyComparisonData();
      }
    } else {
      showToast(data.message || "Lỗi xóa mốc công nợ", "error");
    }
  } catch (e) {
    showToast("Lỗi kết nối khi xóa mốc công nợ.", "error");
  }
}

// Open Create Receivable Modal
function openCreateReceivableModal() {
  document.getElementById("createProjectName").value = "";
  document.getElementById("createContractCode").value = "";
  document.getElementById("createCustomerName").value = "";
  document.getElementById("createNetAmount").value = "";
  document.getElementById("createVatRate").value = "0";
  document.getElementById("createReceivedAmount").value = "0";
  document.getElementById("createCustomerPromisedDate").value = "";
  document.getElementById("createDueDate").value = "";
  document.getElementById("createPaidDate").value = "";
  document.getElementById("createDocStatus").value = "Chưa xuất";
  document.getElementById("createCollectionStatus").value = "PENDING";
  document.getElementById("createNotes").value = "";

  recalcCreateModalAmounts();

  const modal = document.getElementById("modalCreateReceivable");
  if (modal) {
    modal.style.display = "block";
    modal.classList.add("show");
  }
}

// Close Create Modal
function closeCreateReceivableModal() {
  const modal = document.getElementById("modalCreateReceivable");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("show");
  }
}

// Recalculate Live Amounts on Create Modal
function recalcCreateModalAmounts() {
  const net = parseFloat(document.getElementById("createNetAmount")?.value) || 0;
  const vatRate = parseFloat(document.getElementById("createVatRate")?.value) || 0;
  const received = parseFloat(document.getElementById("createReceivedAmount")?.value) || 0;

  const vatAmount = Math.round(net * vatRate);
  const gross = net + vatAmount;
  const remaining = Math.max(0, gross - received);

  const prevNet = document.getElementById("previewCreateNetAmount");
  const prevVat = document.getElementById("previewCreateVatAmount");
  const prevGross = document.getElementById("previewCreateGrossAmount");
  const prevRec = document.getElementById("previewCreateReceivedAmount");
  const prevDebt = document.getElementById("previewCreateRemainingDebt");

  if (prevNet) prevNet.textContent = formatVND(net);
  if (prevVat) prevVat.textContent = `VAT: ${formatVND(vatAmount)}`;
  if (prevGross) prevGross.value = formatVND(gross);
  if (prevRec) prevRec.textContent = formatVND(received);
  if (prevDebt) prevDebt.value = formatVND(remaining);
}

// Save Create Receivable
async function saveCreateReceivableModal() {
  const projName = document.getElementById("createProjectName")?.value.trim();
  const custName = document.getElementById("createCustomerName")?.value.trim();
  const net = parseFloat(document.getElementById("createNetAmount")?.value) || 0;

  if (!projName || !custName) {
    showToast("Vui lòng điền tên dự án và khách hàng.", "error");
    return;
  }
  if (net <= 0) {
    showToast("Vui lòng nhập số tiền đợt thanh toán hợp lệ.", "error");
    return;
  }

  const vatRate = parseFloat(document.getElementById("createVatRate")?.value) || 0;
  const received = parseFloat(document.getElementById("createReceivedAmount")?.value) || 0;
  const promised = document.getElementById("createCustomerPromisedDate")?.value || null;
  const due = document.getElementById("createDueDate")?.value || null;
  const paid = document.getElementById("createPaidDate")?.value || null;
  const doc = document.getElementById("createDocStatus")?.value.trim() || "Chưa xuất";
  const status = document.getElementById("createCollectionStatus")?.value || "PENDING";
  const notes = document.getElementById("createNotes")?.value.trim() || null;
  const contract = document.getElementById("createContractCode")?.value.trim() || null;

  const payload = {
    project_name: projName,
    customer_name: custName,
    contract_code: contract,
    net_amount: net,
    vat_rate: vatRate,
    received_amount: received,
    customer_promised_date: promised,
    due_date: due,
    paid_date: paid,
    doc_status: doc,
    collection_status: status,
    notes: notes
  };

  try {
    const res = await fetch("/api/v1/receivables", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast("Đã thêm mới đợt thanh toán thành công!", "success");
      closeCreateReceivableModal();
      loadReceivablesData();
    } else {
      showToast(data.message || "Lỗi tạo mới", "error");
    }
  } catch (err) {
    console.error("Create error:", err);
    showToast("Lỗi máy chủ khi tạo mới đợt công nợ.", "error");
  }
}

/* ========================================================
 * AI BÓC TÁCH CÔNG NỢ ĐA PHƯƠNG THỨC (TEXT & TẬP TIN)
 * ======================================================== */
let aiReceivableSelectedFile = null;
let currentExtractedReceivables = [];

// Mở modal AI Bóc Tách Công Nợ
function openAiExtractReceivableModal() {
  const modal = document.getElementById("modalAiExtractReceivable");
  if (!modal) return;
  modal.style.display = "block";
  modal.classList.add("show");
  document.body.classList.add("modal-open");

  // Reset form nếu chưa có kết quả
  if (currentExtractedReceivables.length === 0) {
    const input = document.getElementById("aiReceivableInput");
    if (input) input.value = "";
    clearAiReceivableFile();
    const resultsDiv = document.getElementById("aiReceivableResults");
    if (resultsDiv) resultsDiv.style.display = "none";
  }
}

// Đóng modal AI Bóc Tách Công Nợ
function closeAiExtractReceivableModal() {
  const modal = document.getElementById("modalAiExtractReceivable");
  if (!modal) return;
  modal.style.display = "none";
  modal.classList.remove("show");
  document.body.classList.remove("modal-open");
}

// Xử lý khi người dùng chọn file đính kèm
function handleAiReceivableFileSelect(input) {
  if (input && input.files && input.files[0]) {
    aiReceivableSelectedFile = input.files[0];
    const nameEl = document.getElementById("aiReceivableSelectedFileName");
    const infoEl = document.getElementById("aiReceivableSelectedFileInfo");
    if (nameEl) {
      const sizeKB = Math.round(aiReceivableSelectedFile.size / 1024);
      nameEl.textContent = `${aiReceivableSelectedFile.name} (${sizeKB} KB)`;
    }
    if (infoEl) infoEl.style.display = "flex";
  }
}

// Hủy file đính kèm
function clearAiReceivableFile() {
  aiReceivableSelectedFile = null;
  const fileInput = document.getElementById("aiReceivableFileInput");
  if (fileInput) fileInput.value = "";
  const infoEl = document.getElementById("aiReceivableSelectedFileInfo");
  if (infoEl) infoEl.style.display = "none";
}

// Thực hiện gọi API AI phân tích và bóc tách
async function executeAiReceivableExtract() {
  const textInput = document.getElementById("aiReceivableInput");
  const rawText = textInput ? textInput.value.trim() : "";
  const modelSelect = document.getElementById("aiReceivableModelSelect");
  const modelName = modelSelect ? modelSelect.value : "";

  if (!rawText && !aiReceivableSelectedFile) {
    showToast("Vui lòng dán văn bản hoặc đính kèm tập tin (ảnh/PDF/Excel/Word).", "error");
    return;
  }

  const btn = document.getElementById("btnExecuteAiReceivableExtract");
  const btnText = document.getElementById("btnExecuteAiReceivableExtractText");
  const originalText = btnText ? btnText.textContent : "Tiến Hành Phân Tích & Bóc Tách Công Nợ";

  if (btn) btn.disabled = true;
  if (btnText) btnText.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang phân tích bằng Gemini AI...`;

  try {
    const formData = new FormData();
    formData.append("raw_text", rawText);
    formData.append("model_name", modelName);
    if (aiReceivableSelectedFile) {
      formData.append("file", aiReceivableSelectedFile);
    }

    const res = await fetch("/api/v1/receivables/ai-extract", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (data.status === "success") {
      const items = data.items || [];
      if (items.length === 0) {
        showToast("AI không tìm thấy mốc công nợ nào trong dữ liệu cung cấp.", "error");
      } else {
        currentExtractedReceivables = items;
        renderAiReceivablePreview(items);
        const resultsDiv = document.getElementById("aiReceivableResults");
        if (resultsDiv) resultsDiv.style.display = "block";
        showToast(`AI đã trích xuất thành công ${items.length} mốc công nợ!`, "success");
      }
    } else {
      showToast(data.message || "Lỗi khi trích xuất dữ liệu bằng AI.", "error");
    }
  } catch (err) {
    console.error("AI Receivable Extract Error:", err);
    showToast("Lỗi kết nối tới máy chủ AI.", "error");
  } finally {
    if (btn) btn.disabled = false;
    if (btnText) btnText.textContent = originalText;
  }
}

// Render bảng xem trước các mốc công nợ AI trích xuất
function renderAiReceivablePreview(items) {
  const tbody = document.getElementById("aiReceivablePreviewTableBody");
  const summaryEl = document.getElementById("aiReceivableSummaryText");
  const btnSave = document.getElementById("btnSaveAiReceivables");

  if (summaryEl) {
    summaryEl.textContent = `Đã nhận diện ${items.length} mốc thanh toán. Quý khách vui lòng kiểm tra lại trước khi lưu vào hệ thống.`;
  }
  if (btnSave) {
    btnSave.innerHTML = `
      <svg class="icon" viewBox="0 0 24 24" width="14" height="14"><polyline points="20 6 9 17 4 12"/></svg>
      <span>Lưu Tất Cả Vào Hệ Thống (${items.length} đợt)</span>
    `;
    btnSave.disabled = items.length === 0;
  }

  if (!tbody) return;
  tbody.innerHTML = "";

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="12" class="text-center py-4 text-muted">Không còn mốc công nợ nào để lưu.</td></tr>`;
    return;
  }

  items.forEach((it, idx) => {
    const net = it.net_amount || 0;
    const vatRate = it.vat_rate !== null && it.vat_rate !== undefined ? Number(it.vat_rate) : 0;
    const vatPct = vatRate > 0 ? `${Math.round(vatRate * 100)}%` : "0%";
    const vatAmount = it.vat_amount || Math.round(net * vatRate);
    const gross = it.gross_amount || (net + vatAmount);
    const received = it.received_amount || 0;
    const remaining = it.remaining_debt || Math.max(0, gross - received);

    // Xử lý hiển thị Hợp đồng: có thể trống
    const contractHtml = (it.contract_code && it.contract_code !== "-" && it.contract_code !== "None")
      ? `<span class="badge-pill blue" style="font-size: 0.75rem; font-family: monospace;">${it.contract_code}</span>`
      : `<span style="color: #94A3B8; font-style: italic; font-size: 0.75rem;">(Không HĐ)</span>`;

    let statusBadge = `<span class="badge-pill blue" style="font-size:0.75rem;">Chờ thu</span>`;
    if (it.collection_status === "PAID") {
      statusBadge = `<span class="badge-pill green" style="font-size:0.75rem;">Đã thu</span>`;
    } else if (it.collection_status === "URGENT") {
      statusBadge = `<span class="badge-pill amber" style="font-size:0.75rem;">Sắp đến hạn</span>`;
    } else if (it.collection_status === "DELAYED") {
      statusBadge = `<span class="badge-pill red" style="font-size:0.75rem;">Quá hạn</span>`;
    }

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="text-center">${idx + 1}</td>
      <td style="font-weight: 600; color: #1E293B;">
        ${it.project_name || "-"}
        ${it.notes ? `<div style="font-size: 0.72rem; color: #64748B; font-weight: normal; margin-top: 2px;">${it.notes}</div>` : ""}
      </td>
      <td style="font-weight: 500;">${it.customer_name || "-"}</td>
      <td class="text-center">${contractHtml}</td>
      <td class="text-end" style="font-weight: 600;">${formatVND(net)}</td>
      <td class="text-center" style="color: #64748B;">${vatPct}</td>
      <td class="text-end" style="font-weight: 700; color: #1F4E79;">${formatVND(gross)}</td>
      <td class="text-end" style="color: #059669; font-weight: 600;">${formatVND(received)}</td>
      <td class="text-end" style="color: #DC2626; font-weight: 700;">${formatVND(remaining)}</td>
      <td class="text-center" style="font-size: 0.75rem; color: #475569;">${it.due_date || it.customer_promised_date || "-"}</td>
      <td class="text-center">${statusBadge}</td>
      <td class="text-center">
        <button type="button" class="btn btn-outline-danger btn-xs" onclick="removeAiReceivablePreviewItem(${idx})" title="Xóa mốc này" style="padding: 1px 5px; font-size: 0.75rem;">✕</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Xóa 1 mốc công nợ khỏi bảng preview
function removeAiReceivablePreviewItem(index) {
  if (index >= 0 && index < currentExtractedReceivables.length) {
    currentExtractedReceivables.splice(index, 1);
    renderAiReceivablePreview(currentExtractedReceivables);
  }
}

// Lưu tất cả mốc công nợ AI trích xuất vào hệ thống
async function saveAiExtractedReceivables() {
  if (!currentExtractedReceivables || currentExtractedReceivables.length === 0) {
    showToast("Không có mốc công nợ nào để lưu.", "error");
    return;
  }

  const btnSave = document.getElementById("btnSaveAiReceivables");
  const originalHtml = btnSave ? btnSave.innerHTML : "";
  if (btnSave) {
    btnSave.disabled = true;
    btnSave.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu vào cơ sở dữ liệu...`;
  }

  try {
    const res = await fetch("/api/v1/receivables/bulk-save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: currentExtractedReceivables })
    });

    const data = await res.json();
    if (data.status === "success") {
      showToast(`Đã lưu thành công ${data.count || currentExtractedReceivables.length} mốc công nợ vào hệ thống!`, "success");
      currentExtractedReceivables = [];
      closeAiExtractReceivableModal();
      loadReceivablesData();
    } else {
      showToast(data.message || "Lỗi lưu dữ liệu công nợ.", "error");
    }
  } catch (err) {
    console.error("Save AI Receivables Error:", err);
    showToast("Lỗi máy chủ khi lưu mốc công nợ.", "error");
  } finally {
    if (btnSave) {
      btnSave.disabled = false;
      btnSave.innerHTML = originalHtml;
    }
  }
}

// ==============================================================================
// WEEKLY COMPARISON FULLSCREEN DASHBOARD (2 Biểu Đồ Trục Tọa Độ: Tên Dự Án vs %)
// ==============================================================================

let currentWeeklyData = null;
let segmentLookupMap = {};
let contractLookupMap = {};
let currentCompMode = "past_to_curr"; // 'past_to_curr' | 'curr_to_next'
let currentDataSource = "db"; // 'db' (Gốc), 'sample' (Mẫu), 'upload' (File Riêng)
let currentUploadId = null;
let currentUploadedFilename = "";
let activeClickedSegmentId = null;
let activeClickedContractKey = null;

// Mở modal toàn màn hình
function openWeeklyComparisonFullscreen() {
  const modal = document.getElementById("modalWeeklyComparisonFullscreen");
  if (!modal) return;
  modal.classList.add("active");
  modal.style.display = "flex";
  document.body.classList.add("table-modal-fullscreen-open");

  loadWeeklyComparisonData();
}

// Đóng modal toàn màn hình
function closeWeeklyComparisonFullscreen() {
  const modal = document.getElementById("modalWeeklyComparisonFullscreen");
  if (!modal) return;
  hideSegmentTooltip();
  hideProjectHoverCard();
  modal.classList.remove("active");
  modal.style.display = "none";
  document.body.classList.remove("table-modal-fullscreen-open");
}

// Chuyển chế độ: So sánh Tuần Trước vs Tuần Này  HOẶC  Kế Hoạch Tuần Tới vs Tuần Này
function switchWeeklyCompMode(mode) {
  currentCompMode = mode;
  document.getElementById("btnModePastToCurr")?.classList.toggle("active", mode === "past_to_curr");
  document.getElementById("btnModeCurrToNext")?.classList.toggle("active", mode === "curr_to_next");

  const brand = document.getElementById("compHeaderBrandTitle");
  if (brand) {
    if (mode === "curr_to_next") {
      brand.innerHTML = `KẾ HOẠCH THU HỒI CÔNG NỢ TUẦN TỚI <span style="font-size: 0.76rem; font-weight: 600; color: #64748B;">· 下週應收帳款回收預估計劃</span>`;
    } else {
      brand.innerHTML = `SO SÁNH THU HỒI CÔNG NỢ TUẦN <span style="font-size: 0.76rem; font-weight: 600; color: #64748B;">· 每週應收帳款回收對比</span>`;
    }
  }

  const lblPrev = document.getElementById("lblDatePrev");
  const lblCurr = document.getElementById("lblDateCurr");
  if (lblPrev && lblCurr) {
    if (mode === "curr_to_next") {
      lblPrev.textContent = "Tuần này (本週):";
      lblCurr.textContent = "Tuần tới (下週):";
    } else {
      lblPrev.textContent = "Tuần trước (上週):";
      lblCurr.textContent = "Tuần này (本週):";
    }
  }

  loadWeeklyComparisonData();
}

function onWeeklyCompDateChange() {
  loadWeeklyComparisonData();
}

function onWeeklyCompFilterChange() {
  loadWeeklyComparisonData();
}

// Cập nhật dropdown Khách hàng từ dữ liệu so sánh tuần
function populateWeeklyCompCustomerFilter(contracts) {
  const select = document.getElementById("compFilterCustomer");
  if (!select) return;

  const currentVal = select.value;
  select.innerHTML = '<option value="all">Tất cả khách hàng (全部客戶)</option>';

  const custSet = new Set();
  (contracts || []).forEach(c => {
    if (c.customer_name && c.customer_name.trim()) {
      custSet.add(c.customer_name.trim());
    }
  });

  if (custSet.size === 0 && allStats && allStats.customers) {
    allStats.customers.forEach(c => custSet.add(c));
  }

  Array.from(custSet).sort().forEach(cust => {
    const opt = document.createElement("option");
    opt.value = cust;
    opt.textContent = cust;
    if (cust === currentVal) opt.selected = true;
    select.appendChild(opt);
  });
}

// Nạp dữ liệu so sánh từ backend API
async function loadWeeklyComparisonData() {
  const prevDateInput = document.getElementById("compDatePrev");
  const currDateInput = document.getElementById("compDateCurr");
  const customerSelect = document.getElementById("compFilterCustomer");

  const prevDate = prevDateInput?.value || "";
  const currDate = currDateInput?.value || "";
  const customer = (customerSelect?.value && customerSelect?.value !== "all") ? customerSelect.value : "";

  const params = new URLSearchParams();
  if (prevDate) params.append("prev_date", prevDate);
  if (currDate) params.append("curr_date", currDate);
  if (customer) params.append("customer", customer);
  params.append("data_source", currentDataSource);
  if (currentDataSource === "upload" && currentUploadId) {
    params.append("upload_id", currentUploadId);
  }

  const prevContainer = document.getElementById("prevBarsContainer");
  const currContainer = document.getElementById("currBarsContainer");

  if (prevContainer) {
    prevContainer.innerHTML = '<div style="padding: 2rem; text-align: center; color: #64748B;">Đang tải biểu đồ...</div>';
  }
  if (currContainer) {
    currContainer.innerHTML = '<div style="padding: 2rem; text-align: center; color: #64748B;">Đang tải biểu đồ...</div>';
  }

  try {
    const res = await fetch(`/api/v1/receivables/weekly-comparison?${params.toString()}`);
    const data = await res.json();

    if (data.status === "success") {
      currentWeeklyData = data;

      if (prevDateInput && !prevDateInput.value && data.dates?.prev_date) {
        prevDateInput.value = data.dates.prev_date;
      }
      if (currDateInput && !currDateInput.value && data.dates?.curr_date) {
        currDateInput.value = data.dates.curr_date;
      }

      // Build lookup maps for instant hover tooltip
      segmentLookupMap = {};
      contractLookupMap = {};
      const contracts = data.contracts_comparison || [];
      contracts.forEach(c => {
        contractLookupMap[c.contract_key] = c;
        (c.segments || []).forEach(s => {
          segmentLookupMap[s.id] = { segment: s, contract: c };
        });
      });

      // Populate dynamic customer filter dropdown
      populateWeeklyCompCustomerFilter(contracts);

      // Update Column Headers & Next Week Plan stats
      updateChartColumnHeaders(data);

      // Render Side-by-Side Coordinate Stacked % Charts
      renderCoordinateChartSide("prev", contracts);
      renderCoordinateChartSide("curr", contracts);

      setupSynchronizedScrollAndHover();
      filterComparisonItems();
      updateDataSourceUI(data);
    } else {
      showToast(data.message || "Lỗi tải dữ liệu so sánh tuần", "error");
    }
  } catch (err) {
    console.error("Lỗi loadWeeklyComparisonData:", err);
    showToast("Không thể kết nối máy chủ để tải biểu đồ so sánh tuần.", "error");
  }
}

function updateChartColumnHeaders(data) {
  const isPlanMode = currentCompMode === "curr_to_next";
  const prevWeek = data.prev_week || {};
  const currWeek = data.curr_week || {};
  const deltas = data.deltas || {};
  const plan = data.plan_next_week || {};

  const prevTag = document.getElementById("prevBadgeWeekTag");
  const prevRec = document.getElementById("prevColReceived");
  const prevDebt = document.getElementById("prevColDebt");
  const prevRate = document.getElementById("prevColRate");

  const currTag = document.getElementById("currBadgeWeekTag");
  const currRec = document.getElementById("currColReceived");
  const currDebt = document.getElementById("currColDebt");
  const currRate = document.getElementById("currColRate");
  const deltaBadge = document.getElementById("currColDeltaBadge");

  const formatDmy = (dStr) => {
    if (!dStr || dStr === "-") return "";
    try {
      const parts = dStr.split("-");
      if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    } catch (e) {}
    return dStr;
  };

  const prevDateInput = document.getElementById("compDatePrev");
  const currDateInput = document.getElementById("compDateCurr");
  const prevDateFmt = formatDmy(prevWeek.date || (prevDateInput ? prevDateInput.value : ""));
  const currDateFmt = formatDmy(currWeek.date || (currDateInput ? currDateInput.value : ""));

  if (prevTag) {
    const prevVi = isPlanMode ? "BIỂU ĐỒ 1 · CUỐI TUẦN NÀY" : "BIỂU ĐỒ 1 · CUỐI TUẦN TRƯỚC";
    const prevZh = isPlanMode ? "本週末" : "上週末";
    const dateStr = prevDateFmt ? ` (${prevDateFmt})` : "";
    prevTag.innerHTML = `${prevVi} <span class="badge-zh-sub">· ${prevZh}</span>${dateStr}`;
  }
  if (prevRec) prevRec.textContent = prevWeek.total_received_formatted || "0 ₫";
  if (prevDebt) prevDebt.textContent = prevWeek.total_debt_formatted || "0 ₫";
  if (prevRate) prevRate.textContent = `${prevWeek.collection_rate || 0}%`;

  if (currTag) {
    const currVi = isPlanMode ? "BIỂU ĐỒ 2 · KẾ HOẠCH TUẦN TỚI" : "BIỂU ĐỒ 2 · CUỐI TUẦN NÀY";
    const currZh = isPlanMode ? "下週預估計劃" : "本週末";
    const dateStr = currDateFmt ? ` (${currDateFmt})` : "";
    currTag.innerHTML = `${currVi} <span class="badge-zh-sub">· ${currZh}</span>${dateStr}`;
  }
  if (currRec) currRec.textContent = currWeek.total_received_formatted || "0 ₫";
  if (currDebt) currDebt.textContent = currWeek.total_debt_formatted || "0 ₫";
  if (currRate) currRate.textContent = `${currWeek.collection_rate || 0}%`;

  if (deltaBadge) {
    const recDelta = deltas.received_delta || 0;
    if (recDelta > 0) {
      deltaBadge.innerHTML = `Thu thêm (新增): +${deltas.received_delta_formatted}`;
      deltaBadge.className = "comp-col-delta-badge positive";
      deltaBadge.style.display = "inline-block";
    } else {
      deltaBadge.style.display = "none";
    }
  }
}

// Render Side-by-Side Coordinate Stacked % Charts
function renderCoordinateChartSide(side, contracts) {
  const isCurr = side === "curr";
  const isPlanMode = currentCompMode === "curr_to_next";
  const container = document.getElementById(`${side}BarsContainer`);
  if (!container) return;

  if (!contracts || contracts.length === 0) {
    container.innerHTML = '<div style="padding: 2rem; text-align: center; color: #64748B;">Không có hợp đồng / dự án phù hợp.</div>';
    return;
  }

  const rowsHtml = contracts.map(c => {
    const cKey = c.contract_key;
    const codeLabel = c.contract_code && c.contract_code !== "-" ? c.contract_code : "";
    const segments = c.segments || [];

    // Xây dựng các khoản chia theo % trong thanh ngang 100% của hợp đồng
    const segsHtml = segments.map(s => {
      if (s.is_missing_schedule) {
        return `<div class="coord-seg schedule-data-gap" style="width: ${s.width_pct}%;" title="${s.width_pct}% HĐ: chưa có dữ liệu lịch sử, chưa xác định đã thu hay còn nợ"></div>`;
      }
      const status = isCurr ? s.curr_status : s.prev_status;
      const colorClass = getStatusColorClass(status);

      let extraClass = "";
      if (isCurr && !isPlanMode && s.change_type && s.change_type !== "UNCHANGED") {
        extraClass = "seg-changed-this-week";
      } else if (isCurr && isPlanMode) {
        if (s.is_newly_overdue || status === "URGENT" || status === "OVERDUE") {
          extraClass = "seg-plan-target";
        }
      }

      return `<div class="coord-seg ${colorClass} ${extraClass}"
                   style="width: ${s.width_pct}%; cursor: default;"
                   data-seg-id="${s.id}"
                   data-contract-key="${cKey}"
                   onmouseenter="onSegmentHoverEnter(event, '${s.id}', '${side}')"
                   onmousemove="onSegmentHoverMove(event)"
                   onmouseleave="onSegmentHoverLeave('${s.id}')"
                   aria-label="Rê chuột để xem thông tin đợt">
              </div>`;
    }).join("");

    // CẢ 2 BIỂU ĐỒ ĐỀU CÓ coord-y-label ĐỂ TRỤC ĐỨNG 0% VÀ CÁC THANH HOÀN TOÀN THẲNG HÀNG
    const projectLabel = escapeNotesHtml(c.project_title_vi || c.project_title || '-');
    const customerLabel = escapeNotesHtml(c.customer_name_vi || c.customer_name || '-');
    const yLabelHtml = `
      <div class="coord-y-label" role="button" tabindex="0" onclick="handleProjectLabelClick(event, '${cKey}')"
           onkeydown="if(event.key === 'Enter' || event.key === ' ') { event.preventDefault(); handleProjectLabelClick(event, '${cKey}'); }"
           title="${projectLabel} · ${customerLabel} · ${escapeNotesHtml(codeLabel)}">
        <div class="coord-proj-title">${projectLabel}</div>
        <div class="coord-customer-title">${customerLabel}</div>
      </div>
    `;

    // Thuộc tính dữ liệu phục vụ lọc
    const isFullyPaid = (parseFloat(c.curr_pct_collected) || 0) >= 99.9;
    const hasDebt = (parseFloat(c.curr_pct_collected) || 0) < 99.9;
    const hasUnstarted = c.has_unstarted_next !== undefined ? c.has_unstarted_next : (c.segments || []).some(s => s.curr_status !== "PAID" && (!s.start_date || s.start_date === "-"));
    const hasCalculating = c.has_calculating_next !== undefined ? c.has_calculating_next : (c.segments || []).some(s => s.curr_status !== "PAID" && s.start_date && s.start_date !== "-");
    const hasPaid = (c.segments || []).some(s => s.curr_status === "PAID" || (parseFloat(s.curr_received) || 0) > 0);
    const hasPending = (c.segments || []).some(s => s.curr_status === "PENDING");
    const hasOverdue = !!c.has_overdue_curr || (c.segments || []).some(s => s.curr_status === "DELAYED");
    const hasUrgent = !!c.has_urgent_curr || (c.segments || []).some(s => s.curr_status === "URGENT");
    const hasChange = !!c.has_change;
    const isActive = hasChange || hasOverdue || hasUrgent;
    const custClean = (c.customer_name || "").trim().toLowerCase();

    return `
      <div class="coord-bar-row"
           data-contract-key="${cKey}"
           data-search="${encodeURIComponent(normalizeChartSearch([c.project_title_vi, c.project_title, c.project_title_zh, c.customer_name_vi, c.customer_name, c.contract_code].join(' ')))}"
           data-customer="${encodeURIComponent(custClean)}"
           data-is-active="${isActive ? '1' : '0'}"
           data-has-change="${hasChange ? '1' : '0'}"
           data-has-overdue="${hasOverdue ? '1' : '0'}"
           data-has-urgent="${hasUrgent ? '1' : '0'}"
           data-has-pending="${hasPending ? '1' : '0'}"
           data-is-fully-paid="${isFullyPaid ? '1' : '0'}"
           data-has-paid="${hasPaid ? '1' : '0'}"
           data-has-debt="${hasDebt ? '1' : '0'}"
           data-has-unstarted="${hasUnstarted ? '1' : '0'}"
           data-has-calculating="${hasCalculating ? '1' : '0'}"
           data-seg-count="${c.segment_count || (c.segments || []).length}"
           onmouseenter="onRowHoverEnter('${cKey}')"
           onmouseleave="onRowHoverLeave('${cKey}')">
        ${yLabelHtml}
        <div class="coord-plot-cell">
          <div class="coord-stacked-bar">
            ${segsHtml}
          </div>
        </div>
      </div>
    `;
  }).join("");

  container.innerHTML = rowsHtml;
}

// Click vào tên dự án ở Biểu đồ -> Hiển thị Modal/Card tổng quan dự án (Toggle)
function handleProjectLabelClick(event, cKey) {
  if (event && event.stopPropagation) {
    event.stopPropagation();
  }
  openContractEditor(cKey);
}

function showProjectDetailCard(event, cKey) {
  const c = contractLookupMap[cKey];
  if (!c) return;

  const card = document.getElementById("projectDetailHoverCard");
  if (!card) return;
  // Keep the detail above the fullscreen chart and outside scrolling containers.
  if (card.parentElement !== document.body) document.body.appendChild(card);

  const titleEl = document.getElementById("projCardTitle");
  const custEl = document.getElementById("projCardCustomer");
  const codeEl = document.getElementById("projCardContract");
  const grossEl = document.getElementById("projCardGross");
  const recEl = document.getElementById("projCardReceived");
  const debtEl = document.getElementById("projCardDebt");
  const rateEl = document.getElementById("projCardRate");
  const listEl = document.getElementById("projCardMilestonesList");

  if (titleEl) {
    const zh = c.project_title_zh && c.project_title_zh !== (c.project_title_vi || c.project_title) ? `<div style="font-size: 0.76rem; color: #64748B; font-weight: 500;">${c.project_title_zh}</div>` : "";
    titleEl.innerHTML = `<div>${c.project_title_vi || c.project_title}</div>${zh}`;
  }
  if (custEl) custEl.textContent = c.customer_name_vi || c.customer_name || "-";
  if (codeEl) codeEl.textContent = (c.contract_code && c.contract_code !== "-") ? c.contract_code : "Chưa có số HĐ";
  if (grossEl) grossEl.textContent = c.total_gross_formatted || "0 ₫";
  if (recEl) recEl.textContent = c.curr_received_formatted || "0 ₫";

  const debtVal = Math.max(0, c.curr_debt ?? ((c.total_gross || 0) - (c.curr_received || 0)));
  if (debtEl) debtEl.textContent = formatVND(debtVal);
  if (rateEl) rateEl.textContent = `${c.curr_pct_collected || 0}%`;

  if (listEl) {
    const segs = c.segments || [];
    listEl.innerHTML = segs.map((s, idx) => {
      const stColor = getStatusColorClass(s.curr_status);
      const stText = s.curr_status_label_vi || s.curr_status;
      const rec = parseFloat(s.curr_received) || 0;
      const debt = parseFloat(s.curr_debt) || Math.max(0, (s.gross_amount || 0) - rec);

      return `
        <div class="proj-card-ms-row">
          <div class="proj-card-ms-name">
            <strong>${s.is_missing_schedule || s.is_aggregate_history ? '' : `Đợt ${s.seg_index || idx + 1}: `}${s.milestone_name_vi || s.milestone_name}</strong>
            <span style="font-size: 0.7rem; color: #94A3B8; margin-left: 0.35rem;">(${s.width_pct}%)</span>
            ${s.payment_basis === 'inferred_preceding_paid' ? `<div class="schedule-warning">Đã thu theo thứ tự đợt; chậm nhất ${formatDateVN(s.paid_by_date)}. Chưa rõ ngày thực nhận.</div>` : ''}
            ${s.is_aggregate_history ? '<div class="schedule-warning">Tổng lịch sử theo email xác nhận chỉ còn 10%; chưa tách các đợt, chưa rõ ngày thực nhận.</div>' : ''}
          </div>
          <div class="proj-card-ms-summary">
            <span style="font-family: monospace; font-weight: 700; color: #38BDF8;">${s.gross_formatted || "0 ₫"}</span>
            <span class="coord-seg ${stColor}" style="width: 10px; height: 10px; border-radius: 2px; display: inline-block;"></span>
            <span style="font-size: 0.7rem;">${stText}</span>
          </div>
        </div>
      `;
    }).join("") + (c.schedule_warning ? `<p class="schedule-warning">${c.schedule_warning}</p>` : '');
  }

  card.style.display = "block";
  card.focus({ preventScroll: true });
  document.querySelectorAll(".coord-y-label").forEach(el => {
    el.classList.toggle("selected-active", el.closest(".coord-bar-row")?.dataset.contractKey === cKey);
  });
}

function hideProjectHoverCard() {
  const card = document.getElementById("projectDetailHoverCard");
  if (card) card.style.display = "none";
  activeClickedContractKey = null;
  document.querySelectorAll(".coord-y-label").forEach(el => el.classList.remove("selected-active"));
}

function onProjectNameHoverEnter(event, cKey) {
  onRowHoverEnter(cKey);
}

function onProjectNameHoverLeave() {
  onRowHoverLeave();
}

// ==============================================================================
// FLOATING CHI TIẾT ĐỢT CÔNG NỢ & HOVER PREVIEW (Sleek White Bilingual Floating Card)
// ==============================================================================

let activeClickedSegId = null;

function getStatusPillClass(status) {
  switch (status) {
    case "PAID": return "paid";
    case "OVERDUE":
    case "DELAYED": return "overdue";
    case "URGENT": return "urgent";
    case "PENDING":
    default: return "pending";
  }
}

function getStatusLabelZH(status) {
  switch (status) {
    case "PAID": return "已全額收款";
    case "OVERDUE":
    case "DELAYED": return "已逾期未收";
    case "URGENT": return "即將到期(<=7天)";
    case "PENDING":
    default: return "尚未到期";
  }
}

function getStatusLabelVN(status) {
  switch (status) {
    case "PAID": return "Đã thu xong";
    case "OVERDUE":
    case "DELAYED": return "Quá hạn thanh toán";
    case "URGENT": return "Sắp đến hạn (<=7 ngày)";
    case "PENDING":
    default: return "Chưa đến hạn";
  }
}

// ==============================================================================
// FLOATING CHI TIẾT ĐỢT CÔNG NỢ & TƯƠNG TÁC CHUỘT
// (Chuột trái: Sửa đợt · Chuột phải: Xem chi tiết · Hover: Chỉ highlight dòng & thanh, không bật modal/card)
// ==============================================================================

// Chuột trái vào khoản trên biểu đồ -> Mở Modal Sửa Đợt Công Nợ (Chuẩn thiết kế gốc)
function handleSegmentLeftClick(event, segId, side) {
  if (event) {
    if (event.stopPropagation) event.stopPropagation();
  }
  hideSegmentTooltip();
  hideProjectHoverCard();
  openEditReceivableModal(segId);
}

// Chuột phải vào khoản trên biểu đồ -> Mở / Ghim xem Card Chi Tiết Đợt (Chuẩn thiết kế gốc)
function handleSegmentRightClick(event, segId, side) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  hideProjectHoverCard();

  const sIdStr = String(segId);
  // Nếu nhấp chuột phải lại chính khoản đang mở -> Toggle đóng
  if (activeClickedSegId === sIdStr) {
    hideSegmentTooltip();
    return;
  }

  // Bỏ phát sáng active của khoản cũ
  removeSegmentActiveHighlight();

  // Đặt khoản active mới và thêm viền phát sáng xanh
  activeClickedSegId = sIdStr;
  document.querySelectorAll(`.coord-seg[data-seg-id="${segId}"]`).forEach(el => {
    el.classList.add("seg-active-selected");
  });

  showSegmentDetailCard(event, segId, side);
}

// Tương thích ngược nếu các nơi khác gọi handleSegmentClick / handleSegmentContextMenu
function handleSegmentClick(event, segId, side) {
  handleSegmentLeftClick(event, segId, side);
}

function handleSegmentContextMenu(event, segId, side) {
  handleSegmentRightClick(event, segId, side);
}

// Hiển thị Card chi tiết đợt thanh toán khi BẤM CHUỘT PHẢI (Nền trắng, viền xanh thanh lịch, tương phản cao)
function showSegmentDetailCard(event, segId, side) {
  const info = segmentLookupMap[segId] || segmentLookupMap[String(segId)];
  if (!info) {
    console.warn("Segment not found in lookup map:", segId);
    return;
  }

  const s = info.segment;
  const c = info.contract;
  const tooltip = document.getElementById("chartSegmentTooltip");
  if (!tooltip) return;

  const isPlanMode = currentCompMode === "curr_to_next";
  const prevLabelText = isPlanMode ? "Tuần này (本週):" : "Tuần trước (上週):";
  const currLabelText = isPlanMode ? "Tuần tới (下週):" : "Tuần này (本週):";

  const prevPill = `<span class="badge-status-pill ${getStatusPillClass(s.prev_status)}">
    <span>${getStatusLabelVN(s.prev_status)}</span>
    <span style="font-size: 0.68rem; opacity: 0.85;"> · ${s.prev_status_label_zh || getStatusLabelZH(s.prev_status)}</span>
  </span>`;

  const currPill = `<span class="badge-status-pill ${getStatusPillClass(s.curr_status)}">
    <span>${getStatusLabelVN(s.curr_status)}</span>
    <span style="font-size: 0.68rem; opacity: 0.85;"> · ${s.curr_status_label_zh || getStatusLabelZH(s.curr_status)}</span>
  </span>`;

  const cleanMilestone = (s.milestone_name_vi || s.milestone_name || "").split("\n")[0];
  const dueDisplay = (s.due_date && s.due_date !== '-') ? formatDateVN(s.due_date) : 'Theo tiến độ (chờ lắp đặt)';
  const paidDisplay = (s.paid_date && s.paid_date !== '-') ? formatDateVN(s.paid_date) : null;
  const promisedDisplay = (s.customer_promised_date && s.customer_promised_date !== '-') ? formatDateVN(s.customer_promised_date) : null;
  const notesContent = (s.notes && s.notes !== '-') ? s.notes : null;

  let changeBanner = "";
  if (s.change_type === "NEWLY_PAID") {
    changeBanner = `<div class="tt-change-banner newly-paid">${s.change_badge_text || '🎉 Vừa thu xong trong tuần này'}</div>`;
  } else if (s.change_type === "NEWLY_OVERDUE") {
    changeBanner = `<div class="tt-change-banner newly-overdue">${s.change_badge_text || '🚨 Chạm hạn trong tuần nhưng chưa thu được'}</div>`;
  } else if (s.change_type === "BECOMING_URGENT") {
    changeBanner = `<div class="tt-change-banner urgent">${s.change_badge_text || '⚡ Sắp đến hạn trong vòng 7 ngày'}</div>`;
  }

  tooltip.innerHTML = `
    <div class="tt-seg-head">
      <div style="display: flex; align-items: center; gap: 0.45rem; min-width: 0;">
        <span class="tt-seg-title" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">📌 ${cleanMilestone}</span>
        <span class="tt-seg-pct">${s.width_pct}% HĐ (合約)</span>
      </div>
      <button type="button" class="btn-close-card" onclick="hideSegmentTooltip(event)" title="Đóng / 關閉">✕</button>
    </div>

    <div style="font-size: 0.76rem; color: #64748B; margin-bottom: 0.4rem;">
      🏢 <strong>${c.project_title_vi || c.project_title}</strong> (${c.customer_name_vi || c.customer_name || 'Khách hàng'})
      ${(c.contract_code && c.contract_code !== '-') ? `<span style="font-family: monospace; color: #475569;"> · HĐ: ${c.contract_code}</span>` : ''}
    </div>

    <div class="tt-row" style="margin-bottom: 0.35rem;">
      <span class="tt-k">Số tiền khoản / 款項金額:</span>
      <span class="tt-v" style="color: #0284C7; font-size: 0.94rem; font-weight: 800;">${s.gross_formatted || formatVND(s.gross_amount)}</span>
    </div>

    <div class="tt-row" style="margin-top: 0.25rem;">
      <span class="tt-k">${prevLabelText}</span>
      <span class="tt-v">${prevPill}</span>
    </div>

    <div class="tt-row">
      <span class="tt-k">${currLabelText}</span>
      <span class="tt-v">${currPill}</span>
    </div>

    ${changeBanner}

    <div style="border-top: 1px dashed #CBD5E1; margin-top: 0.45rem; padding-top: 0.4rem;">
      ${paidDisplay ? `<div class="tt-row"><span class="tt-k">✅ Đã thu / 收款日:</span><span class="tt-v" style="color: #16A34A; font-weight: 700;">${paidDisplay}</span></div>` : ''}
      <div class="tt-row"><span class="tt-k">📅 Hạn TT / 到期日:</span><span class="tt-v" style="color: ${s.curr_status === 'OVERDUE' ? '#DC2626' : (s.curr_status === 'URGENT' ? '#D97706' : '#1E293B')}; font-weight: 700;">${dueDisplay}</span></div>
      ${promisedDisplay ? `
        <div class="tt-row" style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 4px 7px; margin: 4px 0;">
          <span class="tt-k" style="color: #92400E; font-weight: 700;">🤝 Khách hẹn / 客戶預計:</span>
          <span class="tt-v" style="color: #B45309; font-weight: 800;">${promisedDisplay}</span>
        </div>
      ` : ''}
      ${s.doc_status && s.doc_status !== '-' ? `<div class="tt-row"><span class="tt-k">🧾 Chứng từ / 單據:</span><span class="tt-v" style="color: #334155; font-weight: 600;">${(s.doc_status || '').split("\n")[0]}</span></div>` : ''}
    </div>

    ${notesContent ? `
      <div style="margin-top: 0.5rem; background: #F0F9FF; border: 1px solid #BAE6FD; border-left: 3.5px solid #0284C7; border-radius: 0 6px 6px 0; padding: 0.45rem 0.65rem;">
        <div style="font-size: 0.72rem; font-weight: 700; color: #0369A1; margin-bottom: 2px;">📝 GHI CHÚ THEO DÕI NỢ / 追帳備註:</div>
        <div style="font-size: 0.78rem; color: #1E293B; line-height: 1.45; font-weight: 500;">${notesContent}</div>
      </div>
    ` : ''}

    <div style="margin-top: 0.65rem; padding-top: 0.45rem; border-top: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center;">
      <span style="font-size: 0.68rem; color: #94A3B8;">👆 Chuột phải: Đóng · Chuột trái: Sửa</span>
      <button type="button" class="btn btn-outline-primary btn-sm" onclick="hideSegmentTooltip(event); openEditReceivableModal('${s.id}')" style="font-size: 0.74rem; font-weight: 700; padding: 0.25rem 0.65rem; border-radius: 6px;">
        ✏️ Mở form sửa đợt (Chuột trái)
      </button>
    </div>
  `;

  tooltip.style.pointerEvents = "auto";
  tooltip.style.display = "block";
  positionSegmentTooltip(event);
}

// Compact read-only information on hover; editing lives in the contract dialog.
function onSegmentHoverEnter(event, segId, side) {
  if (performance.now() < chartScrollQuietUntil) return;
  // Highlight đồng bộ cả 2 bên biểu đồ
  document.querySelectorAll(`.coord-seg[data-seg-id="${segId}"]`).forEach(el => {
    el.classList.add("seg-hover-synced");
  });

  const info = segmentLookupMap[segId] || segmentLookupMap[String(segId)];
  if (info) {
    onRowHoverEnter(info.contract.contract_key);
    const s = info.segment;
    const curr = side === 'curr';
    const tooltip = document.getElementById('chartSegmentTooltip');
    if (tooltip) {
      if (tooltip.parentElement !== document.body) document.body.appendChild(tooltip);
      tooltip.innerHTML = `<div class="chart-segment-compact">
        <strong>Đợt ${s.seg_index || ''} / 第${s.seg_index || ''}期: ${escapeNotesHtml(s.milestone_name_vi || s.milestone_name || '')}</strong>
        ${s.milestone_name_zh && s.milestone_name_zh !== (s.milestone_name_vi || s.milestone_name) ? `<div lang="zh-Hant">${escapeNotesHtml(s.milestone_name_zh)}</div>` : ''}
        <div>Tỷ lệ / 比例: ${s.width_pct}%</div>
        <div>Phải thu / 應收金額: ${formatVND(s.gross_amount)}</div>
        <div>Trạng thái / 收款狀態: ${escapeNotesHtml(curr ? s.curr_status_label_vi : s.prev_status_label_vi)} / ${escapeNotesHtml(curr ? s.curr_status_label_zh : s.prev_status_label_zh)}</div>
        <div>Đã thu / 已收金額: ${formatVND(curr ? s.curr_received : s.prev_received)}</div>
        <div>Còn phải thu / 未收餘額: ${formatVND(curr ? s.curr_debt : s.prev_debt)}</div>
        <div>Hạn thanh toán / 付款期限: ${escapeNotesHtml(s.due_date || '-')}</div>
        <div>Ngày thu / 收款日: ${escapeNotesHtml(s.paid_date || '-')}</div>
        <div>Chứng từ / 單據狀態: ${escapeNotesHtml(s.doc_status_vi || s.doc_status || '-')}</div>
        ${s.doc_status_zh && s.doc_status_zh !== (s.doc_status_vi || s.doc_status) ? `<div lang="zh-Hant">${escapeNotesHtml(s.doc_status_zh)}</div>` : ''}
      </div>`;
      tooltip.classList.add('compact-hover');
      tooltip.style.display = 'block';
      tooltip.style.pointerEvents = 'none';
      positionSegmentTooltip(event);
    }
  }
}

function onSegmentHoverMove(event) {
  positionSegmentTooltip(event);
}

function onSegmentHoverLeave(segId) {
  hideSegmentTooltip();
  document.querySelectorAll(`.coord-seg[data-seg-id="${segId}"]`).forEach(el => {
    el.classList.remove("seg-hover-synced");
  });

  const info = segmentLookupMap[segId] || segmentLookupMap[String(segId)];
  if (info) {
    onRowHoverLeave(info.contract.contract_key);
  }
}

function hideSegmentTooltip(event) {
  if (event && event.stopPropagation) {
    event.stopPropagation();
  }
  const tooltip = document.getElementById("chartSegmentTooltip");
  if (tooltip) {
    tooltip.style.display = "none";
    tooltip.style.pointerEvents = "none";
  }
  activeClickedSegId = null;
  removeSegmentActiveHighlight();
}

function removeSegmentActiveHighlight() {
  document.querySelectorAll(".coord-seg.seg-active-selected").forEach(el => {
    el.classList.remove("seg-active-selected");
  });
}

function positionSegmentTooltip(event) {
  const tooltip = document.getElementById("chartSegmentTooltip");
  if (!tooltip || tooltip.style.display === "none") return;

  const pad = 16;
  const rect = tooltip.getBoundingClientRect();
  let clientX = event ? event.clientX : window.innerWidth / 2;
  let clientY = event ? event.clientY : window.innerHeight / 2;

  let left = clientX + pad;
  let top = clientY + pad;

  if (left + rect.width > window.innerWidth - 12) {
    left = clientX - rect.width - pad;
  }
  if (top + rect.height > window.innerHeight - 12) {
    top = window.innerHeight - rect.height - 12;
  }

  tooltip.style.left = `${Math.max(12, left)}px`;
  tooltip.style.top = `${Math.max(12, top)}px`;
}

// Giữ lại hàm mở Modal song ngữ lớn nếu cần dùng
function openSegmentBilingualModal(segId) {
  handleSegmentClick(null, segId, 'curr');
}

function closeSegmentBilingualModal() {
  hideSegmentTooltip();
}

function onRowHoverEnter(cKey) {
  if (!cKey) return;
  document.querySelectorAll(`.coord-bar-row[data-contract-key="${cKey}"]`).forEach(row => {
    row.classList.add("row-hover-highlight");
  });
}

function onRowHoverLeave(cKey) {
  document.querySelectorAll(".coord-bar-row").forEach(row => {
    row.classList.remove("row-hover-highlight");
  });
}

let chartScrollQuietUntil = 0;

function setupSynchronizedScrollAndHover() {
  const pScroll = document.getElementById("leftBarsScrollArea");
  const cScroll = document.getElementById("rightBarsScrollArea");

  if (!pScroll || !cScroll) return;

  const mirroredPositions = new WeakMap();
  const quietHover = () => {
    chartScrollQuietUntil = performance.now() + 160;
    hideSegmentTooltip();
  };
  const syncFrom = (source, target) => {
    if (mirroredPositions.get(source) === source.scrollTop) {
      mirroredPositions.delete(source);
      return;
    }
    quietHover();
    if (Math.abs(target.scrollTop-source.scrollTop)>0.5) {
      target.scrollTop=source.scrollTop;
      mirroredPositions.set(target,target.scrollTop);
    }
  };
  pScroll.onscroll=()=>syncFrom(pScroll,cScroll);
  cScroll.onscroll=()=>syncFrom(cScroll,pScroll);

  // Drive both panes with one wheel step instead of competing scroll animations.
  const wheel = event => {
    if (event.ctrlKey || event.shiftKey || Math.abs(event.deltaX)>Math.abs(event.deltaY)) return;
    if (!event.deltaY) return;
    event.preventDefault();
    quietHover();
    const source=event.currentTarget;
    const unit=event.deltaMode===1?16:event.deltaMode===2?source.clientHeight:1;
    const max=Math.max(0,Math.min(pScroll.scrollHeight-pScroll.clientHeight,cScroll.scrollHeight-cScroll.clientHeight));
    const top=Math.max(0,Math.min(max,source.scrollTop+event.deltaY*unit));
    for (const pane of [pScroll,cScroll]) {
      pane.scrollTop=top;
      mirroredPositions.set(pane,pane.scrollTop);
    }
  };
  for (const pane of [pScroll,cScroll]) {
    if (pane._comparisonWheel) pane.removeEventListener('wheel',pane._comparisonWheel);
    pane._comparisonWheel=wheel;
    pane.addEventListener('wheel',wheel,{passive:false});
  }
  // Reconcile positions after a refresh/filter without adding duplicate listeners.
  cScroll.scrollTop = pScroll.scrollTop;
}

// ==============================================================================
// BỘ LỌC THEO DÕI CÔNG NỢ TUẦN (TIÊU ĐIỂM, TIẾN ĐỘ, TÍNH HẠN, HẠN THANH TOÁN)
// ==============================================================================

function onFilterChangesDropdownChange() {
  filterComparisonItems();
}

function normalizeChartSearch(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase().trim();
}

function filterComparisonItems() {
  const searchTerms = normalizeChartSearch(document.getElementById('compSearch')?.value).split(/\s+/).filter(Boolean);
  const filterVal = document.getElementById("compFilterChanges")?.value || "active_only";
  const customerVal = (document.getElementById("compFilterCustomer")?.value || "all").toLowerCase();
  const allRows = document.querySelectorAll(".coord-bar-row");

  let visibleCount = 0;
  const totalCount = allRows.length / 2; // Do mỗi dự án có 1 dòng bên Trái và 1 dòng bên Phải

  allRows.forEach(row => {
    const isActive = row.getAttribute("data-is-active") === "1";
    const hasChange = row.getAttribute("data-has-change") === "1";
    const hasOverdue = row.getAttribute("data-has-overdue") === "1";
    const hasUrgent = row.getAttribute("data-has-urgent") === "1";
    const hasPending = row.getAttribute("data-has-pending") === "1";
    const isFullyPaid = row.getAttribute("data-is-fully-paid") === "1";
    const hasDebt = row.getAttribute("data-has-debt") === "1";
    const hasUnstarted = row.getAttribute("data-has-unstarted") === "1";
    const hasCalculating = row.getAttribute("data-has-calculating") === "1";
    const segCount = parseInt(row.getAttribute("data-seg-count") || "1", 10);
    const rowCust = decodeURIComponent(row.getAttribute("data-customer") || "").toLowerCase();

    // 1. Kiểm tra khách hàng
    let matchCust = (customerVal === "all") || (rowCust === customerVal) || (rowCust.includes(customerVal));

    // 2. Kiểm tra bộ lọc trạng thái & tiến độ
    let matchFilter = true;
    if (filterVal === "active_only") {
      matchFilter = isActive;
    } else if (filterVal === "changed") {
      matchFilter = hasChange;
    } else if (filterVal === "unstarted_next") {
      // Yêu cầu: Các project chưa thanh toán xong VÀ khoản tiếp theo chưa có ngày tính hạn
      matchFilter = hasDebt && hasUnstarted;
    } else if (filterVal === "unpaid") {
      matchFilter = hasDebt;
    } else if (filterVal === "calculating") {
      matchFilter = hasCalculating;
    } else if (filterVal === "paid") {
      matchFilter = isFullyPaid;
    } else if (filterVal === "overdue") {
      matchFilter = hasOverdue;
    } else if (filterVal === "urgent") {
      matchFilter = hasUrgent;
    } else if (filterVal === "pending") {
      matchFilter = hasPending;
    } else if (filterVal === "multi") {
      matchFilter = segCount >= 2;
    }

    const searchText = decodeURIComponent(row.getAttribute('data-search') || '');
    const matchSearch = searchTerms.every(term => searchText.includes(term));
    const isVisible = matchCust && matchFilter && matchSearch;
    row.style.display = isVisible ? "flex" : "none";
    if (isVisible && row.closest("#prevBarsContainer")) {
      visibleCount++;
    }
  });

  const activeBadge = document.getElementById("cntActiveProjects");
  if (activeBadge) {
    activeBadge.textContent = `${visibleCount}/${totalCount}`;
  }
}

function getStatusColorClass(status) {
  switch (status) {
    case "PAID": return "bg-paid";
    case "OVERDUE":
    case "DELAYED": return "bg-overdue";
    case "URGENT": return "bg-urgent";
    case "PENDING":
    default: return "bg-pending";
  }
}

// Cập nhật giao diện thanh chuyển đổi nguồn dữ liệu & Banners
function updateDataSourceUI(data) {
  const src = data.data_source || currentDataSource || "db";
  currentDataSource = src;

  document.getElementById("btnSourceDb")?.classList.toggle("active", src === "db");
  document.getElementById("btnSourceSample")?.classList.toggle("active", src === "sample");
  document.getElementById("btnSourceUpload")?.classList.toggle("active", src === "upload");

  const customBanner = document.getElementById("weeklyCompCustomFileBanner");
  const sampleBanner = document.getElementById("weeklyCompSampleBanner");

  if (src === "upload") {
    if (customBanner) customBanner.style.display = "flex";
    if (sampleBanner) sampleBanner.style.display = "none";

    const nameEl = document.getElementById("customFileLoadedName");
    const countEl = document.getElementById("customFileLoadedItems");
    const meta = data.data_source_meta || {};
    if (nameEl) nameEl.textContent = currentUploadedFilename || meta.filename || "Tập tin độc lập";
    const totalSegs = (data.contracts_comparison || []).reduce((acc, c) => acc + (c.segments || []).length, 0);
    if (countEl) countEl.textContent = totalSegs;
  } else if (src === "sample") {
    if (customBanner) customBanner.style.display = "none";
    if (sampleBanner) sampleBanner.style.display = "flex";
  } else {
    if (customBanner) customBanner.style.display = "none";
    if (sampleBanner) sampleBanner.style.display = "none";
  }
}

// Chuyển đổi giữa Dữ Liệu Gốc (DB) và Dữ Liệu Mẫu (Sample)
function switchDataSource(sourceType) {
  if (sourceType === "upload" && !currentUploadId) {
    triggerCustomFileUpload();
    return;
  }
  currentDataSource = sourceType;

  document.getElementById("btnSourceDb")?.classList.toggle("active", sourceType === "db");
  document.getElementById("btnSourceSample")?.classList.toggle("active", sourceType === "sample");
  document.getElementById("btnSourceUpload")?.classList.toggle("active", sourceType === "upload");

  if (sourceType === "db") {
    showToast("Đã kết nối Dữ Liệu Gốc của hệ thống (切換至系統原始數據)", "info");
  } else if (sourceType === "sample") {
    showToast("Đang dùng Dữ Liệu Mẫu chuẩn hóa (切換至示範數據)", "info");
  }

  loadWeeklyComparisonData();
}

function triggerCustomFileUpload() {
  const input = document.getElementById("inputCustomChartFile");
  if (input) {
    input.value = "";
    input.click();
  }
}

async function handleCustomFileUpload(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  const prevDate = document.getElementById("compDatePrev")?.value || "";
  const currDate = document.getElementById("compDateCurr")?.value || "";
  if (prevDate) formData.append("prev_date", prevDate);
  if (currDate) formData.append("curr_date", currDate);

  showToast(`Đang phân tích tập tin '${file.name}' để tạo biểu đồ độc lập...`, "info");

  try {
    const res = await fetch("/api/v1/receivables/upload-custom-chart", {
      method: "POST",
      body: formData,
    });
    const result = await res.json();

    if (result.status === "success") {
      currentDataSource = "upload";
      currentUploadId = result.upload_id;
      currentUploadedFilename = result.filename;

      showToast(`Đã nạp file '${result.filename}' thành công (${result.total_items} mốc thanh toán)!`, "success");

      const modal = document.getElementById("modalWeeklyComparisonFullscreen");
      if (!modal || modal.style.display !== "flex") {
        openWeeklyComparisonFullscreen();
      } else {
        loadWeeklyComparisonData();
      }
    } else {
      showToast(result.message || "Không thể phân tích tập tin đã tải lên.", "error");
    }
  } catch (err) {
    console.error("Lỗi tải lên file tùy chỉnh:", err);
    showToast("Lỗi máy chủ khi xử lý file tùy chỉnh.", "error");
  }
}

// Chốt tuần (Snapshot)
function saveWeeklySnapshotPrompt() {
  const dInput = document.getElementById("compDateCurr");
  const defaultDate = dInput ? dInput.value : new Date().toISOString().split("T")[0];
  const snapDate = prompt("Nhập ngày chốt tuần (YYYY-MM-DD):", defaultDate);
  if (!snapDate) return;
  const notes = prompt("Ghi chú chốt tuần (tùy chọn):", "Chốt số liệu thu hồi công nợ tuần");
  saveWeeklySnapshot(snapDate, notes);
}

async function saveWeeklySnapshot(snapshotDate, notes) {
  try {
    const res = await fetch("/api/v1/receivables/weekly-snapshot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot_date: snapshotDate, notes: notes || "" })
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast(data.message || "Đã lưu chốt snapshot tuần thành công!", "success");
      loadWeeklyComparisonData();
    } else {
      showToast(data.message || "Lỗi lưu snapshot", "error");
    }
  } catch (err) {
    console.error("Save snapshot error:", err);
    showToast("Lỗi máy chủ khi lưu snapshot tuần.", "error");
  }
}

// Phím tắt Esc đóng biểu đồ toàn màn hình
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    if (document.getElementById('contractScheduleDialog')?.open) return;
    const projectCard = document.getElementById("projectDetailHoverCard");
    if (projectCard && projectCard.style.display === "block") {
      hideProjectHoverCard();
      return;
    }
    const editModal = document.getElementById("modalEditReceivable");
    if (editModal && editModal.style.display !== "none") {
      closeEditReceivableModal();
      return;
    }
    const compModal = document.getElementById("modalWeeklyComparisonFullscreen");
    if (compModal && (compModal.style.display === "flex" || compModal.classList.contains("active"))) {
      closeWeeklyComparisonFullscreen();
    }
  }
});

// Đóng popup card/tooltip khi nhấp chuột ra ngoài
document.addEventListener("click", function (e) {
  const tooltip = document.getElementById("chartSegmentTooltip");
  if (tooltip && tooltip.style.display === "block") {
    if (!tooltip.contains(e.target) && !e.target.closest(".coord-seg")) {
      hideSegmentTooltip();
    }
  }

  const projCard = document.getElementById("projectDetailHoverCard");
  if (projCard && projCard.style.display === "block") {
    if (!projCard.contains(e.target) && !e.target.closest(".coord-y-label")) {
      hideProjectHoverCard();
    }
  }
});

// Chuyển trực tiếp sang Trung Tâm Soạn Email Nhắc Nợ từ Modal Công Nợ
window.goToEmailFromSegmentDetail = function() {
  if (typeof activeClickedSegId !== "undefined" && activeClickedSegId) {
    window.location.href = `/emails?source=receivable&id=${activeClickedSegId}`;
  } else {
    window.location.href = `/emails?source=receivable`;
  }
};
