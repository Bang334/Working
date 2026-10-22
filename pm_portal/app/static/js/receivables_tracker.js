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

// Render Table Rows
// Render Table Rows with Interactive In-Place Editing
function renderTable(items) {
  const tbody = document.getElementById("receivablesTableBody");
  const tfoot = document.getElementById("receivablesTableFoot");
  const counter = document.getElementById("tableItemCount");
  if (counter) counter.textContent = `${items.length} đợt`;
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="18" class="text-center py-5" style="color: #64748B;">
          <p style="font-size: 1rem; margin-bottom: 0.4rem;">Không tìm thấy đợt thanh toán nào phù hợp với bộ lọc.</p>
          <button type="button" class="btn btn-outline btn-sm" onclick="resetFilters()">Đặt lại bộ lọc</button>
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
    const contractCode = it.contract_code || "-";

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
      loadReceivablesData();
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
      loadReceivablesData();
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

