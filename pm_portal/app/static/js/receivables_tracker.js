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

  const rowsHtml = items.map((it, idx) => {
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
        <td class="sticky-col col-2" style="font-weight: 500;" title="${projName}">${projName}</td>
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
        <td class="col-notes">
          <div class="editable-notes-cell" onclick="startEditingNotes(${it.id}, this)" title="Nhấp để cập nhật ghi chú tiến độ">
            <span class="notes-text">${it.notes || '<em style="color:#94a3b8">Chưa có ghi chú</em>'}</span>
          </div>
        </td>
        <td class="text-center">
          <div style="display: flex; gap: 0.25rem; justify-content: center; align-items: center;">
            <button type="button" class="btn-action-icon warning" onclick="openEditReceivableModal(${it.id})" title="Chỉnh sửa toàn bộ thông tin đợt này (Mở form)">
              <svg class="icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
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
  const currentTextSpan = cellElement.querySelector(".notes-text");
  const rawText = currentTextSpan.textContent.includes("Chưa có ghi chú") ? "" : currentTextSpan.textContent;

  // Replace with textarea
  cellElement.innerHTML = `
    <textarea class="notes-editor-textarea" placeholder="Nhập ghi chú tiến độ...">${rawText}</textarea>
  `;
  const textarea = cellElement.querySelector("textarea");
  textarea.focus();

  // Save on blur or Ctrl/Shift+Enter
  const saveAction = async () => {
    const newNotes = textarea.value.trim();
    cellElement.innerHTML = `<span class="notes-text">${newNotes || '<em style="color:#94a3b8">Chưa có ghi chú</em>'}</span>`;

    if (newNotes !== rawText) {
      try {
        const res = await fetch(`/api/v1/receivables/${itemId}/notes`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ notes: newNotes })
        });
        const data = await res.json();
        if (data.status === "success") {
          showToast("Đã lưu ghi chú thành công!", "success");
        } else {
          showToast(data.message || "Lỗi lưu ghi chú", "error");
        }
      } catch (e) {
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
let isSyncingScroll = false;
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
      brand.innerHTML = `KẾ HOẠCH THU HỒI CÔNG NỢ TUẦN TỚI <span style="font-size: 0.8rem; font-weight: 500; color: #94A3B8;">· 下週應收帳款回收預估計劃</span>`;
    } else {
      brand.innerHTML = `SO SÁNH THU HỒI CÔNG NỢ TUẦN <span style="font-size: 0.8rem; font-weight: 500; color: #94A3B8;">· 每週應收帳款回收對比</span>`;
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
                   style="width: ${s.width_pct}%; cursor: pointer;"
                   data-seg-id="${s.id}"
                   data-contract-key="${cKey}"
                   onclick="openSegmentBilingualModal(${s.id})"
                   oncontextmenu="handleSegmentContextMenu(event, ${s.id}, '${side}')"
                   onmouseenter="onSegmentHoverEnter(event, ${s.id}, '${side}')"
                   onmouseleave="onSegmentHoverLeave()"
                   title="Nhấp chuột trái: Chi tiết | Nhấp chuột phải: Sửa đợt">
              </div>`;
    }).join("");

    // CẢ 2 BIỂU ĐỒ ĐỀU CÓ coord-y-label ĐỂ TRỤC ĐỨNG 0% VÀ CÁC THANH HOÀN TOÀN THẲNG HÀNG
    const yLabelHtml = isCurr ? `
      <div class="coord-y-label"
           onclick="handleProjectLabelClick(event, '${cKey}')"
           onmouseenter="onProjectNameHoverEnter(event, '${cKey}')"
           onmouseleave="onProjectNameHoverLeave()"
           style="cursor: pointer;"
           title="Nhấp chuột xem chi tiết dự án">
        <div class="coord-proj-title">${c.project_title_vi || c.project_title}</div>
        <div class="coord-contract-sub" style="color: #0284C7;">${codeLabel ? codeLabel + ' · ' : ''}Thu: ${c.curr_pct_collected || 0}%</div>
        ${c.has_change ? '<div style="font-size: 0.68rem; color: #EAB308; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">⚡ Có biến động tuần</div>' : ''}
      </div>
    ` : `
      <div class="coord-y-label"
           onclick="handleProjectLabelClick(event, '${cKey}')"
           onmouseenter="onProjectNameHoverEnter(event, '${cKey}')"
           onmouseleave="onProjectNameHoverLeave()"
           style="cursor: pointer;"
           title="Nhấp chuột xem chi tiết dự án">
        <div class="coord-proj-title">${c.project_title_vi || c.project_title}</div>
        ${c.project_title_zh && c.project_title_zh !== (c.project_title_vi || c.project_title) ? `<div class="coord-proj-title-zh" style="font-size: 0.72rem; color: #64748B; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${c.project_title_zh}</div>` : ''}
        <div class="coord-contract-sub">${codeLabel ? codeLabel + ' · ' : ''}${c.segment_count} 期款 (khoản)</div>
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
    const isActive = !!c.is_active_attention || hasChange || hasOverdue || hasUrgent || hasUnstarted;
    const custClean = (c.customer_name || "").trim().toLowerCase();

    return `
      <div class="coord-bar-row"
           data-contract-key="${cKey}"
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

// Chuột phải vào khoản trên biểu đồ -> Mở Modal Sửa Đợt Công Nợ
function handleSegmentContextMenu(event, segId, side) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  hideSegmentTooltip();
  hideProjectHoverCard();
  openEditReceivableModal(segId);
}

// Click vào tên dự án ở Biểu đồ -> Hiển thị Modal/Card tổng quan dự án (Toggle)
function handleProjectLabelClick(event, cKey) {
  if (event && event.stopPropagation) {
    event.stopPropagation();
  }
  if (activeClickedContractKey === cKey) {
    hideProjectHoverCard();
    return;
  }
  hideSegmentTooltip();
  activeClickedContractKey = cKey;
  showProjectDetailCard(event, cKey);
}

function showProjectDetailCard(event, cKey) {
  const c = contractLookupMap[cKey];
  if (!c) return;

  const card = document.getElementById("projectDetailHoverCard");
  if (!card) return;

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
  
  const debtVal = Math.max(0, (c.total_gross || 0) - (c.curr_received || 0));
  if (debtEl) debtEl.textContent = formatCurrencyVN(debtVal);
  if (rateEl) rateEl.textContent = `${c.curr_pct_collected || 0}%`;

  if (listEl) {
    const segs = c.segments || [];
    listEl.innerHTML = segs.map((s, idx) => {
      const stColor = getStatusColorClass(s.curr_status);
      const stText = s.curr_status_label_vi || s.curr_status;
      const rec = parseFloat(s.curr_received) || 0;
      const debt = parseFloat(s.curr_debt) || Math.max(0, (s.gross_amount || 0) - rec);
      
      return `
        <div class="proj-card-ms-row" style="padding: 0.35rem 0.5rem; border-bottom: 1px solid #1E293B; display: flex; justify-content: space-between; align-items: center; font-size: 0.74rem;">
          <div style="flex: 1 1 auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 0.5rem;">
            <strong style="color: #F8FAFC;">Đợt ${idx + 1}: ${s.milestone_name_vi || s.milestone_name}</strong>
            <span style="font-size: 0.7rem; color: #94A3B8; margin-left: 0.35rem;">(${s.width_pct}%)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0;">
            <span style="font-family: monospace; font-weight: 700; color: #38BDF8;">${s.gross_formatted || "0 ₫"}</span>
            <span class="coord-seg ${stColor}" style="width: 10px; height: 10px; border-radius: 2px; display: inline-block;"></span>
            <span style="font-size: 0.7rem; color: #CBD5E1;">${stText}</span>
          </div>
        </div>
      `;
    }).join("");
  }

  card.style.display = "block";
  document.querySelectorAll(".coord-y-label-box").forEach(el => el.classList.remove("selected-active"));
  const activeYLabel = document.querySelector(`.coord-y-label-box[data-contract-key="${cKey}"]`);
  if (activeYLabel) activeYLabel.classList.add("selected-active");
}

function hideProjectHoverCard() {
  const card = document.getElementById("projectDetailHoverCard");
  if (card) card.style.display = "none";
  activeClickedContractKey = null;
  document.querySelectorAll(".coord-y-label-box").forEach(el => el.classList.remove("selected-active"));
}

function onProjectNameHoverEnter(event, cKey) {
  onRowHoverEnter(cKey);
}

function onProjectNameHoverLeave() {
  onRowHoverLeave();
}

// Click vào khoản -> Hiển thị Modal chi tiết song ngữ (Toggle)
function openSegmentBilingualModal(segId) {
  if (activeClickedSegmentId === segId) {
    hideSegmentTooltip();
    return;
  }
  hideProjectHoverCard();
  activeClickedSegmentId = segId;
  showSegmentDetailCard(segId);
}

function showSegmentDetailCard(segId) {
  const info = segmentLookupMap[segId];
  if (!info) return;

  const s = info.segment;
  const c = info.contract;
  const card = document.getElementById("segmentDetailFloatingModal");
  if (!card) return;

  const mNameVi = document.getElementById("floatModalMilestoneVi");
  const mNameZh = document.getElementById("floatModalMilestoneZh");
  const pTitle = document.getElementById("floatModalProjectTitle");
  const cCode = document.getElementById("floatModalContractCode");
  const gross = document.getElementById("floatModalGross");
  const widthPct = document.getElementById("floatModalWidthPct");
  const due = document.getElementById("floatModalDueDate");
  const rec = document.getElementById("floatModalReceived");
  const debt = document.getElementById("floatModalDebt");
  const statusBadge = document.getElementById("floatModalStatusBadge");
  const changeBanner = document.getElementById("floatModalChangeBanner");
  const changeText = document.getElementById("floatModalChangeText");

  if (mNameVi) mNameVi.textContent = s.milestone_name_vi || s.milestone_name;
  if (mNameZh) mNameZh.textContent = s.milestone_name_zh || "";
  if (pTitle) pTitle.textContent = `${c.project_title_vi || c.project_title} (${c.customer_name_vi || c.customer_name || ""})`;
  if (cCode) cCode.textContent = (c.contract_code && c.contract_code !== "-") ? c.contract_code : "Chưa có số HĐ";
  if (gross) gross.textContent = s.gross_formatted || "0 ₫";
  if (widthPct) widthPct.textContent = `${s.width_pct}%`;
  
  const dueFmt = (s.due_date && s.due_date !== "-") ? formatDateVN(s.due_date) : "Chưa chốt hạn";
  if (due) due.textContent = dueFmt;
  
  if (rec) rec.textContent = s.curr_received_formatted || "0 ₫";
  if (debt) debt.textContent = s.curr_debt_formatted || "0 ₫";

  if (statusBadge) {
    const colorClass = getStatusColorClass(s.curr_status);
    const labelVi = s.curr_status_label_vi || s.curr_status;
    const labelZh = s.curr_status_label_zh || "";
    statusBadge.innerHTML = `<span class="badge-bullet"></span> ${labelVi} · ${labelZh}`;
    statusBadge.className = `float-status-pill ${colorClass}`;
  }

  if (changeBanner && changeText) {
    if (s.change_type && s.change_type !== "UNCHANGED") {
      changeText.textContent = s.change_badge_text || s.change_badge_text_vi || "Có biến động tuần này";
      changeBanner.style.display = "flex";
    } else {
      changeBanner.style.display = "none";
    }
  }

  // Cập nhật nút sửa trực tiếp
  const editBtn = document.getElementById("btnEditFromFloatModal");
  if (editBtn) {
    editBtn.onclick = function() {
      hideSegmentTooltip();
      openEditReceivableModal(s.id);
    };
  }

  card.style.display = "block";
  document.querySelectorAll(".coord-seg").forEach(el => el.classList.remove("selected-active"));
  const activeSegs = document.querySelectorAll(`.coord-seg[data-seg-id="${segId}"]`);
  activeSegs.forEach(el => el.classList.add("selected-active"));
}

function hideSegmentTooltip() {
  const card = document.getElementById("segmentDetailFloatingModal");
  if (card) card.style.display = "none";
  activeClickedSegmentId = null;
  document.querySelectorAll(".coord-seg").forEach(el => el.classList.remove("selected-active"));
}

function onSegmentHoverEnter(event, segId, side) {
  const info = segmentLookupMap[segId];
  if (info) {
    onRowHoverEnter(info.contract.contract_key);
  }
}

function onSegmentHoverLeave() {
  onRowHoverLeave();
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

function setupSynchronizedScrollAndHover() {
  const pScroll = document.getElementById("prevChartScroll");
  const cScroll = document.getElementById("currChartScroll");

  if (!pScroll || !cScroll) return;

  pScroll.onscroll = function () {
    if (!isSyncingScroll) {
      isSyncingScroll = true;
      cScroll.scrollTop = pScroll.scrollTop;
      isSyncingScroll = false;
    }
  };

  cScroll.onscroll = function () {
    if (!isSyncingScroll) {
      isSyncingScroll = true;
      pScroll.scrollTop = cScroll.scrollTop;
      isSyncingScroll = false;
    }
  };
}

// ==============================================================================
// BỘ LỌC THEO DÕI CÔNG NỢ TUẦN (TIÊU ĐIỂM, TIẾN ĐỘ, TÍNH HẠN, HẠN THANH TOÁN)
// ==============================================================================

function onFilterChangesDropdownChange() {
  filterComparisonItems();
}

function filterComparisonItems() {
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

    const isVisible = matchCust && matchFilter;
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
