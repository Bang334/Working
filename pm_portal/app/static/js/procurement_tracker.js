/**
 * Hong Ming Global PM Portal - Procurement & Supplier PO Tracker
 * Handles live tracking, Excel upload/import, AI quotation extraction, and Excel export.
 */

(function () {
  let cachedOrders = [];
  let currentFilter = {
    status: "all",
    supplier: "all",
    project: "all",
    search: ""
  };
  let aiExtractedItems = [];

  document.addEventListener("DOMContentLoaded", () => {
    initProcurementTracker();
  });

  async function initProcurementTracker() {
    initEventListeners();
    await Promise.all([loadProcurementData(), loadProcurementChartData()]);
  }

  function initEventListeners() {
    // Search input
    const searchInput = document.getElementById("procurementSearch");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        currentFilter.search = e.target.value.trim();
        applyClientFilters();
      });
    }

    // Status filter
    const statusSelect = document.getElementById("filterStatus");
    if (statusSelect) {
      statusSelect.addEventListener("change", (e) => {
        currentFilter.status = e.target.value;
        loadProcurementData();
        loadProcurementChartData();
      });
    }

    // Supplier filter
    const supplierSelect = document.getElementById("filterSupplier");
    if (supplierSelect) {
      supplierSelect.addEventListener("change", (e) => {
        currentFilter.supplier = e.target.value;
        loadProcurementData();
        loadProcurementChartData();
      });
    }

    // Project filter
    const projectSelect = document.getElementById("filterProject");
    if (projectSelect) {
      projectSelect.addEventListener("change", (e) => {
        currentFilter.project = e.target.value;
        loadProcurementData();
        loadProcurementChartData();
      });
    }

    // File Drag & Drop in Upload Modal
    const dropzone = document.getElementById("excelDropzone");
    const fileInput = document.getElementById("excelFileInput");
    if (dropzone && fileInput) {
      dropzone.addEventListener("click", () => fileInput.click());
      dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });
      dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
      });
      dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
          fileInput.files = e.dataTransfer.files;
          handleSelectedExcelFile(e.dataTransfer.files[0]);
        }
      });
      fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
          handleSelectedExcelFile(fileInput.files[0]);
        }
      });
    }
  }

  // Load Data from Backend
  window.loadProcurementData = async function () {
    try {
      showLoading(true, "Đang nạp danh sách đơn mua hàng...");
      const params = new URLSearchParams();
      if (currentFilter.status && currentFilter.status !== "all") params.append("status", currentFilter.status);
      if (currentFilter.supplier && currentFilter.supplier !== "all") params.append("supplier", currentFilter.supplier);
      if (currentFilter.project && currentFilter.project !== "all") params.append("project", currentFilter.project);
      if (currentFilter.search) params.append("search", currentFilter.search);

      const res = await fetch(`/api/v1/procurement/orders?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();

      if (data.status === "success") {
        cachedOrders = data.orders || [];
        renderKpis(data.stats || {});
        populateFilterDropdowns(data.stats || {});
        populateHeaderFilterDropdowns(cachedOrders);
        renderOrdersTable(cachedOrders);
      }
    } catch (err) {
      console.error("Lỗi nạp dữ liệu mua hàng:", err);
      showToast("Không thể tải danh sách đơn mua hàng: " + err.message, "error");
    } finally {
      showLoading(false);
    }
  };

  // Render KPIs
  function renderKpis(stats) {
    const elTotal = document.getElementById("kpiTotalOrders");
    const elInTransit = document.getElementById("kpiInTransitOrders");
    const elDelivered = document.getElementById("kpiDeliveredOrders");
    const elPendingPayment = document.getElementById("kpiPendingPaymentOrders");

    if (elTotal) elTotal.textContent = stats.total_orders || 0;
    if (elInTransit) elInTransit.textContent = stats.in_transit_count || 0;
    if (elDelivered) elDelivered.textContent = stats.delivered_count || 0;
    if (elPendingPayment) elPendingPayment.textContent = stats.pending_payment_count || 0;

    // Calculate dynamic chip counts
    let attentionCount = 0;
    let paymentCount = 0;
    let shippingCount = 0;
    let deliveredCount = 0;

    cachedOrders.forEach(o => {
      const payRaw = (o.supplier_payment_status || "").toLowerCase();
      const isPay = payRaw.includes("chờ") || payRaw.includes("待") || payRaw.includes("50%");
      const isShip = o.delivery_status === "IN_TRANSIT" || (!o.actual_delivery_date && o.eta_date);
      const isDel = o.delivery_status === "DELIVERED";
      const isDelayed = o.delivery_status === "DELAYED";

      if (isPay) paymentCount++;
      if (isShip) shippingCount++;
      if (isDel) deliveredCount++;
      if (isPay || isShip || isDelayed) attentionCount++;
    });

    const cAll = document.getElementById("chipCountAll");
    const cAtt = document.getElementById("chipCountAttention");
    const cPay = document.getElementById("chipCountPayment");
    const cShip = document.getElementById("chipCountShipping");
    const cDel = document.getElementById("chipCountDelivered");

    if (cAll) cAll.textContent = cachedOrders.length;
    if (cAtt) cAtt.textContent = attentionCount;
    if (cPay) cPay.textContent = paymentCount;
    if (cShip) cShip.textContent = shippingCount;
    if (cDel) cDel.textContent = deliveredCount;
  }

  // Category Badge Formatter
  function getCategoryBadge(cat) {
    if (!cat || cat === "-") return '<span class="cat-badge default">-</span>';
    const raw = String(cat).trim();
    const c = raw.toUpperCase();
    if (c.includes("SERVER") || c.includes("MÁY CHỦ")) {
      return `<span class="cat-badge server">🖥️ ${escapeHtml(raw)}</span>`;
    } else if (c.includes("IPC") || c.includes("MÁY TÍNH") || c.includes("LAPTOP") || c.includes("DIAN NAO")) {
      return `<span class="cat-badge ipc">💻 ${escapeHtml(raw)}</span>`;
    } else if (c.includes("MANG") || c.includes("MẠNG") || c.includes("SWITCH")) {
      return `<span class="cat-badge network">🌐 ${escapeHtml(raw)}</span>`;
    } else if (c.includes("PDA")) {
      return `<span class="cat-badge pda">📱 ${escapeHtml(raw)}</span>`;
    } else if (c.includes("DIAN SHI") || c.includes("DIANSHI") || c.includes("TV") || c.includes("TIVI") || c.includes("KANBAN")) {
      return `<span class="cat-badge tv">📺 ${escapeHtml(raw)}</span>`;
    } else if (c.includes("HỆ THỐNG") || c.includes("SYSTEM")) {
      return `<span class="cat-badge system">⚙️ ${escapeHtml(raw)}</span>`;
    } else if (c.includes("VẬT TƯ") || c.includes("DÂY") || c.includes("CÁP")) {
      return `<span class="cat-badge material">📦 ${escapeHtml(raw)}</span>`;
    }
    return `<span class="cat-badge default">${escapeHtml(raw)}</span>`;
  }

  // Quick Filter by Attention Type
  window.filterByAttention = function(type, el) {
    document.querySelectorAll(".legend-chip").forEach(c => c.classList.remove("active"));
    if (el) el.classList.add("active");

    if (type === "all") {
      renderOrdersTable(cachedOrders);
      return;
    }

    const filtered = cachedOrders.filter(o => {
      const payRaw = (o.supplier_payment_status || "").toLowerCase();
      const isPay = payRaw.includes("chờ") || payRaw.includes("待") || payRaw.includes("50%");
      const isShip = o.delivery_status === "IN_TRANSIT" || (!o.actual_delivery_date && o.eta_date);
      const isDel = o.delivery_status === "DELIVERED";
      const isDelayed = o.delivery_status === "DELAYED";

      if (type === "attention") return isPay || isShip || isDelayed;
      if (type === "payment") return isPay;
      if (type === "shipping") return isShip;
      if (type === "delivered") return isDel;
      return true;
    });

    renderOrdersTable(filtered);
  };

  // Populate Filter Selects
  function populateFilterDropdowns(stats) {
    const supplierSelect = document.getElementById("filterSupplier");
    if (supplierSelect && stats.suppliers) {
      const currentVal = supplierSelect.value;
      supplierSelect.innerHTML = '<option value="all">Tất cả nhà cung cấp</option>';
      stats.suppliers.forEach(sup => {
        const opt = document.createElement("option");
        opt.value = sup;
        opt.textContent = sup;
        if (sup === currentVal) opt.selected = true;
        supplierSelect.appendChild(opt);
      });
    }

    const projectSelect = document.getElementById("filterProject");
    if (projectSelect && stats.projects) {
      const currentVal = projectSelect.value;
      projectSelect.innerHTML = '<option value="all">Tất cả dự án</option>';
      stats.projects.forEach(proj => {
        const opt = document.createElement("option");
        opt.value = proj;
        opt.textContent = proj;
        if (proj === currentVal) opt.selected = true;
        projectSelect.appendChild(opt);
      });
    }
  }

  // Populate Header Filter Dropdowns (Category, Supplier)
  function populateHeaderFilterDropdowns(orders) {
    const catSelect = document.getElementById("thPoFilterCategory");
    if (catSelect) {
      const curCat = catSelect.value;
      const cats = new Set();
      orders.forEach(o => {
        if (o.category && o.category.trim() && o.category.trim() !== "-") {
          cats.add(o.category.trim());
        }
      });
      catSelect.innerHTML = '<option value="all">Tất cả</option>';
      Array.from(cats).sort().forEach(cat => {
        const opt = document.createElement("option");
        opt.value = cat;
        opt.textContent = cat;
        if (cat === curCat) opt.selected = true;
        catSelect.appendChild(opt);
      });
    }

    const supSelect = document.getElementById("thPoFilterSupplier");
    if (supSelect) {
      const curSup = supSelect.value;
      const sups = new Set();
      orders.forEach(o => {
        if (o.supplier_name && o.supplier_name.trim() && o.supplier_name.trim() !== "-") {
          sups.add(o.supplier_name.trim());
        }
      });
      supSelect.innerHTML = '<option value="all">Tất cả</option>';
      Array.from(sups).sort().forEach(sup => {
        const opt = document.createElement("option");
        opt.value = sup;
        opt.textContent = sup;
        if (sup === curSup) opt.selected = true;
        supSelect.appendChild(opt);
      });
    }
  }

  // Apply Header Column Filters
  window.applyHeaderFiltersPo = function() {
    const projectVal = (document.getElementById("thPoFilterProject")?.value || "").trim().toLowerCase();
    const itemVal = (document.getElementById("thPoFilterItem")?.value || "").trim().toLowerCase();
    const catVal = document.getElementById("thPoFilterCategory")?.value || "all";
    const supVal = document.getElementById("thPoFilterSupplier")?.value || "all";
    const payVal = document.getElementById("thPoFilterPayment")?.value || "all";
    const statusVal = document.getElementById("thPoFilterDeliveryStatus")?.value || "all";
    const notesVal = (document.getElementById("thPoFilterNotes")?.value || "").trim().toLowerCase();

    const isAnyFilterActive = Boolean(projectVal || itemVal || (catVal !== "all") || (supVal !== "all") || (payVal !== "all") || (statusVal !== "all") || notesVal);

    const filtered = cachedOrders.filter(o => {
      if (projectVal) {
        const pName = (o.project_name || "").toLowerCase();
        const cComp = (o.customer_company || "").toLowerCase();
        if (!pName.includes(projectVal) && !cComp.includes(projectVal)) return false;
      }
      if (itemVal) {
        const iName = (o.item_name || "").toLowerCase();
        const mDesc = (o.material_desc || "").toLowerCase();
        if (!iName.includes(itemVal) && !mDesc.includes(itemVal)) return false;
      }
      if (catVal && catVal !== "all") {
        if ((o.category || "").trim() !== catVal) return false;
      }
      if (supVal && supVal !== "all") {
        if ((o.supplier_name || "").trim() !== supVal) return false;
      }
      if (payVal && payVal !== "all") {
        const payRaw = (o.supplier_payment_status || "").toLowerCase();
        if (payVal === "paid") {
          if (!payRaw.includes("đã") && !payRaw.includes("已") && !payRaw.includes("100%")) return false;
        } else if (payVal === "pending") {
          if (!payRaw.includes("chờ") && !payRaw.includes("待") && !payRaw.includes("50%")) return false;
        }
      }
      if (statusVal && statusVal !== "all") {
        if (o.delivery_status !== statusVal) return false;
      }
      if (notesVal) {
        const nText = (o.shipping_notes || "").toLowerCase();
        if (!nText.includes(notesVal)) return false;
      }
      return true;
    });

    renderOrdersTable(filtered, isAnyFilterActive);
  };

  // Reset Header Column Filters
  window.resetHeaderFiltersPo = function() {
    const elProj = document.getElementById("thPoFilterProject");
    const elItem = document.getElementById("thPoFilterItem");
    const elCat = document.getElementById("thPoFilterCategory");
    const elSup = document.getElementById("thPoFilterSupplier");
    const elPay = document.getElementById("thPoFilterPayment");
    const elStat = document.getElementById("thPoFilterDeliveryStatus");
    const elNotes = document.getElementById("thPoFilterNotes");

    if (elProj) elProj.value = "";
    if (elItem) elItem.value = "";
    if (elCat) elCat.value = "all";
    if (elSup) elSup.value = "all";
    if (elPay) elPay.value = "all";
    if (elStat) elStat.value = "all";
    if (elNotes) elNotes.value = "";

    applyHeaderFiltersPo();
  };

  // Render Orders Table
  function renderOrdersTable(orders, isHeaderFiltered = false) {
    const tbody = document.getElementById("procurementTableBody");
    const emptyState = document.getElementById("procurementEmptyState");
    const tableCard = document.getElementById("procurementTableCard");

    if (!tbody) return;
    tbody.innerHTML = "";

    if (!orders || orders.length === 0) {
      if (isHeaderFiltered) {
        if (tableCard) tableCard.style.display = "block";
        if (emptyState) emptyState.style.display = "none";
        const poCounter = document.getElementById("poTableItemCount");
        if (poCounter) poCounter.textContent = `0 / ${cachedOrders.length} đơn`;
        tbody.innerHTML = `
          <tr>
            <td colspan="13" class="text-center py-5" style="color: #64748B;">
              <p style="font-size: 0.95rem; margin-bottom: 0.5rem;">Không tìm thấy đơn hàng nào khớp với các đầu lọc ở tiêu đề.</p>
              <button type="button" class="btn btn-outline btn-xs" onclick="resetHeaderFiltersPo()">Đặt lại đầu lọc</button>
            </td>
          </tr>
        `;
        return;
      }
      if (emptyState) emptyState.style.display = "block";
      if (tableCard) tableCard.style.display = "none";
      return;
    }

    if (emptyState) emptyState.style.display = "none";
    if (tableCard) tableCard.style.display = "block";
    const poCounter = document.getElementById("poTableItemCount");
    if (poCounter) {
      poCounter.textContent = isHeaderFiltered
        ? `${orders.length} / ${cachedOrders.length} đơn`
        : `${orders.length} đơn`;
    }

    orders.forEach((o, index) => {
      const tr = document.createElement("tr");

      // Check attention flags
      const payRaw = (o.supplier_payment_status || "").toLowerCase();
      const isPaymentAttention = payRaw.includes("chờ") || payRaw.includes("待") || payRaw.includes("50%");
      const isDelayed = o.delivery_status === "DELAYED";
      const isShipping = o.delivery_status === "IN_TRANSIT" || (!o.actual_delivery_date && o.eta_date);
      const isDelivered = o.delivery_status === "DELIVERED";

      // Row styling priority
      if (isDelayed) {
        tr.className = "row-attention-delayed";
      } else if (isPaymentAttention) {
        tr.className = "row-attention-payment";
      } else if (isShipping) {
        tr.className = "row-attention-shipping";
      } else if (isDelivered) {
        tr.className = "row-delivered";
      }

      // Attention indicators
      let attentionBadgeHtml = "";
      if (isDelayed) {
        attentionBadgeHtml = `<span class="attention-pill delayed">⚠️ Quá hạn ETA</span>`;
      } else if (isPaymentAttention) {
        attentionBadgeHtml = `<span class="attention-pill payment">💳 Chờ chi tiền NCC</span>`;
      } else if (isShipping) {
        attentionBadgeHtml = `<span class="attention-pill shipping">🚚 Đang chờ giao</span>`;
      }

      // Status badge class
      let badgeClass = "pending";
      let statusText = o.delivery_status_label || "Chờ xử lý";
      if (o.delivery_status === "DELIVERED") {
        badgeClass = "delivered";
      } else if (o.delivery_status === "IN_TRANSIT") {
        badgeClass = "in_transit";
      } else if (o.delivery_status === "DELAYED") {
        badgeClass = "delayed";
      }

      // Format clean lines
      const itemName = escapeHtml(o.item_name || "").replace(/\n/g, "<br>");
      const projectName = escapeHtml(o.project_name || "").replace(/\n/g, "<br>");
      const customerCompany = escapeHtml(o.customer_company || "-").replace(/\n/g, "<br>");
      const categoryBadge = getCategoryBadge(o.category);
      const supplierName = escapeHtml(o.supplier_name || "").replace(/\n/g, "<br>");
      const shippingNotes = escapeHtml(o.shipping_notes || "-").replace(/\n/g, "<br>");
      const paymentStatus = escapeHtml(o.supplier_payment_status || "-").replace(/\n/g, "<br>");

      // REORDERED COLUMNS:
      // Col 1: STT (col-stt) [FIX CỨNG BÊN TRÁI]
      // Col 2: Dự án & Khách hàng (col-project) [FIX CỨNG BÊN TRÁI, ĐỨNG TRƯỚC TÊN THIẾT BỊ]
      // Col 3: Tên vật tư / Thiết bị & Quy cách (col-item) [FIX CỨNG BÊN TRÁI, CẮT CHỮ NẾU DÀI THÀNH ...]
      // Col 4: Hạng mục (col-cat) [CỘT CUỘN BÌNH THƯỜNG]
      // Col 5: Số lượng
      // Col 6: Nhà cung cấp
      // Col 7: Ngày đặt
      // Col 8: ETA dự kiến
      // Col 9: Giao thực tế
      // Col 10: Thanh toán NCC
      // Col 11: Trạng thái giao
      // Col 12: Ghi chú & Rủi ro ✏️ (Click sửa trực tiếp)
      // Col 13: Thao tác
      tr.innerHTML = `
        <td class="col-stt" style="font-weight: 700;">${o.order_no || (index + 1)}</td>
        <td class="col-project">
          <strong style="color: var(--text-main); font-size: 0.84rem; display: block; line-height: 1.3;">${projectName}</strong>
          <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 2px; line-height: 1.25;">${customerCompany}</div>
        </td>
        <td class="col-item" title="${escapeHtml(o.item_name || '')}${o.material_desc ? ' | Quy cách: ' + escapeHtml(o.material_desc) : ''}">
          <div class="item-name-ellipsis">${itemName}</div>
          ${o.material_desc ? `<div class="item-desc-ellipsis" title="Quy cách: ${escapeHtml(o.material_desc)}">Quy cách: ${escapeHtml(o.material_desc)}</div>` : ""}
          ${attentionBadgeHtml ? `<div style="margin-top: 4px;">${attentionBadgeHtml}</div>` : ""}
        </td>
        <td class="col-cat">
          ${categoryBadge}
        </td>
        <td style="text-align: center; font-weight: 700; white-space: nowrap;">
          <span style="font-size: 0.92rem; color: #1F4E79;">${o.quantity || 1}</span> 
          <small style="color: var(--text-muted); font-size: 0.75rem;">${o.unit || "Bộ"}</small>
        </td>
        <td>
          <span style="font-weight: 700; color: #1F4E79; font-size: 0.85rem;">${supplierName}</span>
        </td>
        <td style="text-align: center; white-space: nowrap;">
          <div class="inline-date-picker-wrap">
            <input type="date" class="inline-date-input" value="${o.order_date || ''}" 
                   onchange="updatePoInlineDate(${o.id}, 'order_date', this.value)" 
                   title="Chọn ngày đặt hàng">
            ${o.order_date ? `<button type="button" class="btn-clear-date" onclick="clearPoDateInline(${o.id}, 'order_date', event)" title="Xóa ngày đặt">×</button>` : ''}
          </div>
        </td>
        <td style="text-align: center; white-space: nowrap;">
          <div class="inline-date-picker-wrap eta-wrap">
            <input type="date" class="inline-date-input eta-input" value="${o.eta_date || ''}" 
                   onchange="updatePoInlineDate(${o.id}, 'eta_date', this.value)" 
                   title="Chọn ngày giao dự kiến ETA">
            ${o.eta_date ? `<button type="button" class="btn-clear-date" onclick="clearPoDateInline(${o.id}, 'eta_date', event)" title="Xóa ngày ETA">×</button>` : ''}
          </div>
        </td>
        <td style="text-align: center; white-space: nowrap;" id="actual-date-cell-${o.id}">
          <div class="inline-date-picker-wrap actual-wrap">
            <input type="date" class="inline-date-input actual-input" value="${o.actual_delivery_date || ''}" 
                   onchange="updatePoInlineDate(${o.id}, 'actual_delivery_date', this.value)" 
                   title="Chọn ngày giao hàng thực tế">
            ${o.actual_delivery_date ? `<button type="button" class="btn-clear-date" onclick="clearPoDateInline(${o.id}, 'actual_delivery_date', event)" title="Xóa ngày giao thực tế">×</button>` : ''}
          </div>
        <td style="max-width: 170px; font-size: 0.78rem; cursor: pointer;" onclick="startEditingPaymentStatus(${o.id}, '${escapeHtml(o.supplier_payment_status || '-')}', this)" title="Nhấp vào để sửa nhanh tình trạng thanh toán NCC">
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 4px;">
            <span style="${isPaymentAttention ? 'color: #7C3AED; font-weight: 700;' : ''}">${paymentStatus}</span>
            <span style="font-size: 0.72rem; opacity: 0.5;">✏️</span>
          </div>
        </td>
        <td style="text-align: center; white-space: nowrap;">
          <div class="status-dropdown-wrapper" onclick="event.stopPropagation()">
            <select class="status-select-badge ${badgeClass}" id="status-select-${o.id}" onchange="quickChangeDeliveryStatus(${o.id}, this.value, this)" title="Nhấp để thay đổi trạng thái nhanh không cần mở modal">
              <option value="DELIVERED" ${o.delivery_status === 'DELIVERED' ? 'selected' : ''}>✓ Đã giao / 已交貨</option>
              <option value="IN_TRANSIT" ${o.delivery_status === 'IN_TRANSIT' ? 'selected' : ''}>🚚 Đang vận chuyển / 運輸中</option>
              <option value="DELAYED" ${o.delivery_status === 'DELAYED' ? 'selected' : ''}>⚠️ Trễ hạn / 延遲</option>
              <option value="PENDING" ${o.delivery_status === 'PENDING' ? 'selected' : ''}>⏳ Chờ xử lý / 待處理</option>
            </select>
          </div>
        </td>
        <td class="col-notes-editable" id="notes-cell-${o.id}" data-order-id="${o.id}" onclick="startEditNotes(event, ${o.id})" title="Nhấp vào ô để sửa trực tiếp ghi chú & rủi ro">
          <div class="notes-display-box" id="notes-box-${o.id}">
            <div class="notes-text-content ${!o.shipping_notes || o.shipping_notes === '-' ? 'empty-placeholder' : ''}">
              ${o.shipping_notes && o.shipping_notes !== '-' ? shippingNotes : '<em>+ Nhấp để ghi chú/rủi ro...</em>'}
            </div>
            <span class="notes-pen-icon" title="Nhấp vào để sửa trực tiếp">✏️</span>
          </div>
        </td>
        <td style="text-align: center; white-space: nowrap;">
          <button type="button" class="btn btn-outline btn-sm" onclick="openEditOrderModal(${o.id})" title="Chỉnh sửa đơn hàng" style="padding: 4px 8px; margin-right: 4px;">
            <svg class="icon" viewBox="0 0 24 24" style="width: 14px; height: 14px;"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button type="button" class="btn btn-outline btn-sm" onclick="deleteOrder(${o.id})" title="Xóa đơn hàng" style="padding: 4px 8px; color: #DC2626; border-color: rgba(220,38,38,0.3);">
            <svg class="icon" viewBox="0 0 24 24" style="width: 14px; height: 14px;"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Client-side quick filter
  function applyClientFilters() {
    const q = (currentFilter.search || "").toLowerCase();
    if (!q) {
      renderOrdersTable(cachedOrders);
      return;
    }
    const filtered = cachedOrders.filter(o => {
      return (o.item_name || "").toLowerCase().includes(q) ||
             (o.project_name || "").toLowerCase().includes(q) ||
             (o.supplier_name || "").toLowerCase().includes(q) ||
             (o.customer_company || "").toLowerCase().includes(q) ||
             (o.category || "").toLowerCase().includes(q) ||
             (o.shipping_notes || "").toLowerCase().includes(q);
    });
    renderOrdersTable(filtered);
  }

  // ==========================================
  // QUICK CHANGE DELIVERY STATUS (INLINE DROPDOWN)
  // ==========================================
  window.quickChangeDeliveryStatus = async function (orderId, newStatus, selectEl) {
    const o = cachedOrders.find(item => item.id === orderId);
    if (!o) return;

    const oldStatus = o.delivery_status;
    if (oldStatus === newStatus) return;

    const badgeMap = {
      DELIVERED: "delivered",
      IN_TRANSIT: "in_transit",
      DELAYED: "delayed",
      PENDING: "pending",
    };

    // Update select badge styling immediately
    selectEl.className = `status-select-badge ${badgeMap[newStatus] || "pending"}`;

    // If delivered, update actual delivery date if currently empty
    if (newStatus === "DELIVERED" && (!o.actual_delivery_date || o.actual_delivery_date === "-")) {
      const todayStr = new Date().toISOString().split("T")[0];
      o.actual_delivery_date = todayStr;
      const dateCell = document.getElementById(`actual-date-cell-${orderId}`);
      if (dateCell) dateCell.textContent = todayStr;
    }

    // Update local cached order
    o.delivery_status = newStatus;

    // Update row attention classes immediately
    const tr = selectEl.closest("tr");
    if (tr) {
      tr.className = "";
      const payRaw = (o.supplier_payment_status || "").toLowerCase();
      const isPaymentAttention = payRaw.includes("chờ") || payRaw.includes("待") || payRaw.includes("50%");
      if (newStatus === "DELAYED") {
        tr.className = "row-attention-delayed";
      } else if (isPaymentAttention) {
        tr.className = "row-attention-payment";
      } else if (newStatus === "IN_TRANSIT" || (!o.actual_delivery_date && o.eta_date)) {
        tr.className = "row-attention-shipping";
      } else if (newStatus === "DELIVERED") {
        tr.className = "row-delivered";
      }
    }

    try {
      const res = await fetch(`/api/v1/procurement/orders/${orderId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ delivery_status: newStatus }),
      });
      const data = await res.json();
      if (!res.ok || data.status === "error") {
        throw new Error(data.message || "Không thể cập nhật trạng thái.");
      }

      if (data.order) {
        Object.assign(o, data.order);
        if (data.order.actual_delivery_date) {
          const dateCell = document.getElementById(`actual-date-cell-${orderId}`);
          if (dateCell) dateCell.textContent = data.order.actual_delivery_date;
        }
      }
      if (data.stats) {
        renderKpis(data.stats);
      }
      showToast("✓ Đã cập nhật trạng thái giao hàng!", "success");
    } catch (err) {
      console.error("Lỗi cập nhật trạng thái giao hàng:", err);
      showToast(err.message, "error");
      // Revert select on error
      selectEl.value = oldStatus;
      selectEl.className = `status-select-badge ${badgeMap[oldStatus] || "pending"}`;
      o.delivery_status = oldStatus;
    }
  };

  // ==========================================
  // INLINE DATE EDITING (NGÀY ĐẶT, ETA, GIAO THỰC TẾ)
  // ==========================================
  window.updatePoInlineDate = async function (orderId, field, value) {
    try {
      const res = await fetch(`/api/v1/procurement/orders/${orderId}/inline`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field, value })
      });
      const data = await res.json();
      if (data.status === "success") {
        let fieldName = field;
        if (field === "order_date") fieldName = "ngày đặt hàng";
        else if (field === "eta_date") fieldName = "ngày giao dự kiến (ETA)";
        else if (field === "actual_delivery_date") fieldName = "ngày giao hàng thực tế";

        showToast(`✓ Đã lưu ${fieldName} thành công!`, "success");
        // Update cached order
        const o = cachedOrders.find(item => item.id === orderId);
        if (o && data.order) {
          Object.assign(o, data.order);
        }
        if (data.stats) {
          renderKpis(data.stats);
        }
        applyHeaderFiltersPo();
      } else {
        showToast(data.message || "Không thể cập nhật ngày", "error");
      }
    } catch (err) {
      console.error("Lỗi cập nhật ngày PO:", err);
      showToast("Lỗi máy chủ khi cập nhật ngày.", "error");
    }
  };

  window.clearPoDateInline = function (orderId, field, event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    updatePoInlineDate(orderId, field, null);
  };

  // ==========================================
  // INLINE EDITING: THANH TOÁN NCC (CLICK ĐỂ SỬA TRỰC TIẾP)
  // ==========================================
  window.startEditingPaymentStatus = function (orderId, currentVal, cellEl) {
    if (cellEl.querySelector("input")) return;
    const originalHtml = cellEl.innerHTML;
    const rawVal = currentVal && currentVal !== "-" ? currentVal.replace(/&quot;/g, '"') : "";
    cellEl.innerHTML = `
      <div class="inline-edit-box" style="display: flex; gap: 4px; align-items: center;" onclick="event.stopPropagation()">
        <input type="text" class="th-filter-input" value="${rawVal}" style="font-size: 0.78rem; height: 26px; padding: 2px 6px; min-width: 120px;" placeholder="Đã TT, Chờ TT 50%...">
        <button type="button" class="btn-inline-save" style="background:#1F4E79; color:#FFF; border:none; border-radius:4px; padding:2px 6px; font-size:0.72rem; cursor:pointer;">Lưu</button>
        <button type="button" class="btn-inline-cancel" style="background:#E2E8F0; color:#475569; border:none; border-radius:4px; padding:2px 5px; font-size:0.72rem; cursor:pointer;">✕</button>
      </div>
    `;

    const input = cellEl.querySelector("input");
    const btnSave = cellEl.querySelector(".btn-inline-save");
    const btnCancel = cellEl.querySelector(".btn-inline-cancel");
    if (input) {
      input.focus();
      input.select();
    }

    const doSave = async () => {
      const newVal = input.value.trim();
      try {
        const res = await fetch(`/api/v1/procurement/orders/${orderId}/inline`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ field: "supplier_payment_status", value: newVal || "-" })
        });
        const data = await res.json();
        if (data.status === "success") {
          showToast("✓ Đã lưu trạng thái thanh toán NCC!", "success");
          const o = cachedOrders.find(item => item.id === orderId);
          if (o && data.order) Object.assign(o, data.order);
          applyHeaderFiltersPo();
        } else {
          showToast(data.message || "Lỗi lưu thanh toán", "error");
          cellEl.innerHTML = originalHtml;
        }
      } catch (err) {
        showToast("Lỗi kết nối máy chủ", "error");
        cellEl.innerHTML = originalHtml;
      }
    };

    btnSave.addEventListener("click", (e) => {
      e.stopPropagation();
      doSave();
    });

    btnCancel.addEventListener("click", (e) => {
      e.stopPropagation();
      cellEl.innerHTML = originalHtml;
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        doSave();
      } else if (e.key === "Escape") {
        e.preventDefault();
        cellEl.innerHTML = originalHtml;
      }
    });
  };

  // ==========================================
  // INLINE EDITING: GHI CHÚ & RỦI RO (CLICK ĐỂ SỬA TRỰC TIẾP)
  // ==========================================
  let activeEditingNotesOrderId = null;

  window.startEditNotes = function (event, orderId) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    // If clicked inside an existing inline-notes-editor, ignore
    if (event && event.target && event.target.closest(".inline-notes-editor")) {
      return;
    }

    // If another cell is being edited, save it first
    if (activeEditingNotesOrderId && activeEditingNotesOrderId !== orderId) {
      saveInlineNotes(activeEditingNotesOrderId);
    }

    const o = cachedOrders.find(item => item.id === orderId);
    if (!o) return;

    const cell = document.getElementById(`notes-cell-${orderId}`);
    if (!cell) return;

    activeEditingNotesOrderId = orderId;
    const currentText = o.shipping_notes && o.shipping_notes !== "-" ? o.shipping_notes : "";

    cell.innerHTML = `
      <div class="inline-notes-editor" onclick="event.stopPropagation()" onmousedown="event.stopPropagation()">
        <textarea class="inline-notes-textarea" id="notes-textarea-${orderId}" placeholder="Nhập ghi chú, cảnh báo rủi ro hoặc kế hoạch xử lý..." onclick="event.stopPropagation()" onkeydown="event.stopPropagation()">${escapeHtml(currentText)}</textarea>
        <div class="inline-notes-footer" onclick="event.stopPropagation()">
          <span class="inline-notes-hint">Enter: Lưu • Esc: Hủy • Shift+Enter: Xuống dòng</span>
          <div class="inline-notes-btns">
            <button type="button" class="btn-inline-cancel" onclick="cancelEditNotes(${orderId}, event)" title="Hủy bỏ">✕ Hủy</button>
            <button type="button" class="btn-inline-save" onclick="saveInlineNotes(${orderId}, event)" title="Lưu ghi chú">✓ Lưu</button>
          </div>
        </div>
      </div>
    `;

    // Focus with slight timeout to ensure DOM update is complete
    setTimeout(() => {
      const textarea = document.getElementById(`notes-textarea-${orderId}`);
      if (textarea) {
        textarea.focus();
        const len = textarea.value.length;
        textarea.setSelectionRange(len, len);

        textarea.addEventListener("keydown", function (e) {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            e.stopPropagation();
            saveInlineNotes(orderId, e);
          } else if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            cancelEditNotes(orderId, e);
          }
        });
      }
    }, 15);
  };

  window.cancelEditNotes = function (orderId, event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    activeEditingNotesOrderId = null;
    const o = cachedOrders.find(item => item.id === orderId);
    renderNotesCellDisplay(orderId, o ? o.shipping_notes : "");
  };

  window.saveInlineNotes = async function (orderId, event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    const textarea = document.getElementById(`notes-textarea-${orderId}`);
    if (!textarea) return;

    const newNotes = textarea.value.trim();
    activeEditingNotesOrderId = null;

    const o = cachedOrders.find(item => item.id === orderId);
    const originalNotes = o ? (o.shipping_notes && o.shipping_notes !== "-" ? o.shipping_notes : "") : "";

    // If nothing changed, just revert to display view without making API request or false toast
    if (newNotes === originalNotes.trim()) {
      renderNotesCellDisplay(orderId, o ? o.shipping_notes : "");
      return;
    }

    // Immediately update UI with new text
    renderNotesCellDisplay(orderId, newNotes || "-");

    try {
      const res = await fetch(`/api/v1/procurement/orders/${orderId}/notes`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ shipping_notes: newNotes }),
      });

      const data = await res.json();
      if (!res.ok || data.status === "error") {
        throw new Error(data.message || "Không thể lưu ghi chú.");
      }

      // Update cachedOrders
      if (o) {
        o.shipping_notes = newNotes;
      }

      // Re-render cell with saved text and success flash
      renderNotesCellDisplay(orderId, newNotes, true);
      showToast("✓ Đã lưu ghi chú rủi ro!", "success");
    } catch (err) {
      console.error("Lỗi lưu ghi chú inline:", err);
      showToast(err.message, "error");
      // Revert from cache
      renderNotesCellDisplay(orderId, o ? o.shipping_notes : "");
    }
  };

  function renderNotesCellDisplay(orderId, text, flash = false) {
    const cell = document.getElementById(`notes-cell-${orderId}`);
    if (!cell) return;

    const cleanText = (text || "").trim();
    const isEmpty = !cleanText || cleanText === "-";
    const formattedHtml = escapeHtml(cleanText).replace(/\n/g, "<br>");

    cell.innerHTML = `
      <div class="notes-display-box ${flash ? 'notes-flash-saved' : ''}" id="notes-box-${orderId}">
        <div class="notes-text-content ${isEmpty ? 'empty-placeholder' : ''}">
          ${isEmpty ? '<em>+ Nhấp để ghi chú/rủi ro...</em>' : formattedHtml}
        </div>
        <span class="notes-pen-icon" title="Nhấp vào để sửa nhanh">✏️</span>
      </div>
    `;

    if (flash) {
      setTimeout(() => {
        const box = document.getElementById(`notes-box-${orderId}`);
        if (box) box.classList.remove("notes-flash-saved");
      }, 1500);
    }
  }

  // Global click outside to auto-save any open inline editor
  document.addEventListener("click", function (e) {
    if (activeEditingNotesOrderId) {
      if (!e.target || !e.target.isConnected) return;
      const editor = document.querySelector(".inline-notes-editor");
      const currentCell = document.getElementById(`notes-cell-${activeEditingNotesOrderId}`);
      if (editor && !editor.contains(e.target) && (!currentCell || !currentCell.contains(e.target))) {
        saveInlineNotes(activeEditingNotesOrderId, e);
      }
    }
  });

  // ==========================================
  // EXCEL UPLOAD & IMPORT
  // ==========================================
  window.openUploadExcelModal = function () {
    const modal = document.getElementById("uploadExcelModal");
    if (modal) modal.classList.add("active");
  };

  window.closeUploadExcelModal = function () {
    const modal = document.getElementById("uploadExcelModal");
    if (modal) modal.classList.remove("active");
    const fileInput = document.getElementById("excelFileInput");
    if (fileInput) fileInput.value = "";
    const previewEl = document.getElementById("selectedFileInfo");
    if (previewEl) previewEl.style.display = "none";
  };

  function handleSelectedExcelFile(file) {
    if (!file) return;
    const previewEl = document.getElementById("selectedFileInfo");
    const nameEl = document.getElementById("selectedFileName");
    const sizeEl = document.getElementById("selectedFileSize");
    if (previewEl && nameEl && sizeEl) {
      nameEl.textContent = file.name;
      sizeEl.textContent = `${(file.size / 1024).toFixed(1)} KB`;
      previewEl.style.display = "block";
    }
  }

  window.submitUploadExcel = async function () {
    const fileInput = document.getElementById("excelFileInput");
    if (!fileInput || !fileInput.files.length) {
      showToast("Vui lòng chọn hoặc kéo thả file Excel cần tải lên.", "warning");
      return;
    }

    const file = fileInput.files[0];
    const overwrite = document.getElementById("overwriteCheckbox")?.checked || false;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("overwrite", overwrite ? "true" : "false");

    try {
      showLoading(true, "Đang đọc & phân tích Sheet Theo Dõi Mua Hàng...");
      const res = await fetch("/api/v1/procurement/upload-excel", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok || data.status === "error") {
        throw new Error(data.message || `Lỗi tải lên (${res.status})`);
      }

      showToast(data.message || "Tải lên file Excel thành công!", "success");
      closeUploadExcelModal();
      await loadProcurementData();
    } catch (err) {
      console.error("Lỗi import Excel:", err);
      showToast(err.message, "error");
    } finally {
      showLoading(false);
    }
  };

  // ==========================================
  // EXPORT EXCEL
  // ==========================================
  window.exportProcurementExcel = function () {
    const params = new URLSearchParams();
    if (currentFilter.status && currentFilter.status !== "all") params.append("status", currentFilter.status);
    if (currentFilter.supplier && currentFilter.supplier !== "all") params.append("supplier", currentFilter.supplier);
    if (currentFilter.project && currentFilter.project !== "all") params.append("project", currentFilter.project);
    if (currentFilter.search) params.append("search", currentFilter.search);

    const url = `/api/v1/procurement/export-excel?${params.toString()}`;
    window.location.href = url;
  };

  // ==========================================
  // AI QUOTATION EXTRACTION
  // ==========================================
  window.openAiExtractModal = function () {
    const modal = document.getElementById("aiExtractModal");
    if (modal) modal.classList.add("active");
  };

  window.closeAiExtractModal = function () {
    const modal = document.getElementById("aiExtractModal");
    if (modal) modal.classList.remove("active");
    const resultsContainer = document.getElementById("aiExtractResults");
    if (resultsContainer) resultsContainer.style.display = "none";
  };

  // File attachment handler for AI PO extraction
  window.handleAiPoFileSelect = function (input) {
    const info = document.getElementById("aiPoSelectedFileInfo");
    const nameEl = document.getElementById("aiPoSelectedFileName");
    if (input.files && input.files[0]) {
      const file = input.files[0];
      if (nameEl) nameEl.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
      if (info) info.style.display = "flex";
    }
  };

  window.clearAiPoFile = function () {
    const input = document.getElementById("aiPoFileInput");
    const info = document.getElementById("aiPoSelectedFileInfo");
    if (input) input.value = "";
    if (info) info.style.display = "none";
  };

  window.executeAiExtract = async function () {
    const textarea = document.getElementById("aiExtractInput");
    const rawText = textarea ? textarea.value.trim() : "";
    const fileInput = document.getElementById("aiPoFileInput");
    const hasFile = fileInput && fileInput.files && fileInput.files[0];

    if (!rawText && !hasFile) {
      showToast("Vui lòng dán văn bản hoặc đính kèm tập tin báo giá (Ảnh, Excel, Word, PDF).", "warning");
      return;
    }

    const modelSelect = document.getElementById("aiModelSelect");
    const modelName = modelSelect ? modelSelect.value : null;

    const formData = new FormData();
    if (rawText) formData.append("raw_text", rawText);
    if (modelName) formData.append("model_name", modelName);
    if (hasFile) formData.append("file", fileInput.files[0]);

    try {
      showLoading(true, "Gemini AI đang bóc tách thiết bị, số lượng và điều khoản từ văn bản / tập tin...");
      const res = await fetch("/api/v1/procurement/ai-extract", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok || data.status === "error") {
        throw new Error(data.message || "Không thể trích xuất dữ liệu bằng AI.");
      }

      aiExtractedItems = data.items || [];
      renderAiExtractedPreview(data);
      showToast(`AI đã trích xuất thành công ${aiExtractedItems.length} hạng mục!`, "success");
    } catch (err) {
      console.error("Lỗi AI trích xuất:", err);
      showToast(err.message, "error");
    } finally {
      showLoading(false);
    }
  };

  function renderAiExtractedPreview(data) {
    const container = document.getElementById("aiExtractResults");
    const tbody = document.getElementById("aiPreviewTableBody");
    const summaryEl = document.getElementById("aiExtractSummaryText");

    if (!container || !tbody) return;

    if (summaryEl) {
      summaryEl.textContent = `Dự án: ${data.project_name || "-"} · NCC: ${data.supplier_name || "-"} · Ghi chú: ${data.summary_notes || "-"}`;
    }

    tbody.innerHTML = "";
    aiExtractedItems.forEach((item, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="text-align: center;">${idx + 1}</td>
        <td><strong>${escapeHtml(item.item_name || "")}</strong></td>
        <td style="text-align: center;">${item.category || "-"}</td>
        <td style="text-align: center;">${item.quantity || 1} ${item.unit || "Bộ"}</td>
        <td>${escapeHtml(item.supplier_name || data.supplier_name || "-")}</td>
        <td style="text-align: center;">${item.eta_date || "-"}</td>
        <td style="font-size: 0.78rem;">${escapeHtml(item.supplier_payment_status || "-")}</td>
      `;
      tbody.appendChild(tr);
    });

    container.style.display = "block";
  }

  window.saveAiExtractedItems = async function () {
    if (!aiExtractedItems || !aiExtractedItems.length) {
      showToast("Không có hạng mục nào để lưu.", "warning");
      return;
    }

    try {
      showLoading(true, "Đang lưu các hạng mục vào hệ thống...");
      const res = await fetch("/api/v1/procurement/bulk-save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: aiExtractedItems }),
      });

      const data = await res.json();
      if (!res.ok || data.status === "error") {
        throw new Error(data.message || "Lỗi lưu danh mục.");
      }

      showToast(data.message || "Đã lưu thành công vào bảng theo dõi!", "success");
      closeAiExtractModal();
      await loadProcurementData();
    } catch (err) {
      console.error("Lỗi lưu đơn hàng AI:", err);
      showToast(err.message, "error");
    } finally {
      showLoading(false);
    }
  };

  // ==========================================
  // ADD / EDIT MODAL
  // ==========================================
  window.openAddOrderModal = function () {
    const modal = document.getElementById("orderFormModal");
    const form = document.getElementById("orderForm");
    const title = document.getElementById("orderFormModalTitle");
    if (form) form.reset();
    document.getElementById("orderFormId").value = "";
    if (title) title.textContent = "Thêm Đơn Mua Hàng Mới";
    if (modal) modal.classList.add("active");
  };

  window.closeOrderFormModal = function () {
    const modal = document.getElementById("orderFormModal");
    if (modal) modal.classList.remove("active");
  };

  window.openEditOrderModal = async function (id) {
    try {
      showLoading(true, "Đang tải thông tin đơn hàng...");
      const res = await fetch(`/api/v1/procurement/orders/${id}`);
      const data = await res.json();
      if (!res.ok || data.status !== "success") {
        throw new Error(data.message || "Không thể lấy thông tin đơn hàng.");
      }

      const o = data.order;
      document.getElementById("orderFormId").value = o.id;
      document.getElementById("formProjectName").value = o.project_name || "";
      document.getElementById("formCustomerCompany").value = o.customer_company || "";
      document.getElementById("formSupplierName").value = o.supplier_name || "";
      document.getElementById("formCategory").value = o.category || "";
      document.getElementById("formItemName").value = o.item_name || "";
      document.getElementById("formQuantity").value = o.quantity || 1;
      document.getElementById("formUnit").value = o.unit || "Bộ";
      document.getElementById("formOrderDate").value = o.order_date || "";
      document.getElementById("formEtaDate").value = o.eta_date || "";
      document.getElementById("formActualDate").value = o.actual_delivery_date || "";
      document.getElementById("formSupplierPayment").value = o.supplier_payment_status || "";
      document.getElementById("formDeliveryStatus").value = o.delivery_status || "PENDING";
      document.getElementById("formShippingNotes").value = o.shipping_notes || "";

      const title = document.getElementById("orderFormModalTitle");
      if (title) title.textContent = `Chỉnh Sửa Đơn Mua Hàng #${o.id}`;

      const modal = document.getElementById("orderFormModal");
      if (modal) modal.classList.add("active");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      showLoading(false);
    }
  };

  window.submitOrderForm = async function () {
    const id = document.getElementById("orderFormId").value;
    const projectName = document.getElementById("formProjectName").value.trim();
    const itemName = document.getElementById("formItemName").value.trim();
    const supplierName = document.getElementById("formSupplierName").value.trim();

    if (!projectName || !itemName || !supplierName) {
      showToast("Vui lòng điền đầy đủ Tên Dự Án, Tên Thiết Bị và Nhà Cung Cấp.", "warning");
      return;
    }

    const payload = {
      project_name: projectName,
      customer_company: document.getElementById("formCustomerCompany").value.trim() || null,
      supplier_name: supplierName,
      category: document.getElementById("formCategory").value.trim() || null,
      item_name: itemName,
      quantity: parseFloat(document.getElementById("formQuantity").value) || 1,
      unit: document.getElementById("formUnit").value.trim() || "Bộ",
      order_date: document.getElementById("formOrderDate").value || null,
      eta_date: document.getElementById("formEtaDate").value || null,
      actual_delivery_date: document.getElementById("formActualDate").value || null,
      supplier_payment_status: document.getElementById("formSupplierPayment").value.trim() || null,
      delivery_status: document.getElementById("formDeliveryStatus").value || "PENDING",
      shipping_notes: document.getElementById("formShippingNotes").value.trim() || null,
    };

    try {
      showLoading(true, "Đang lưu thông tin đơn hàng...");
      const url = id ? `/api/v1/procurement/orders/${id}` : "/api/v1/procurement/orders";
      const method = id ? "PUT" : "POST";

      const res = await fetch(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok || data.status === "error") {
        throw new Error(data.message || "Lỗi lưu dữ liệu.");
      }

      showToast(data.message || "Đã lưu đơn mua hàng thành công!", "success");
      closeOrderFormModal();
      await loadProcurementData();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      showLoading(false);
    }
  };

  window.deleteOrder = async function (id) {
    if (!confirm("Bạn có chắc chắn muốn xóa đơn mua hàng này không?")) return;

    try {
      showLoading(true, "Đang xóa đơn hàng...");
      const res = await fetch(`/api/v1/procurement/orders/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (!res.ok || data.status === "error") {
        throw new Error(data.message || "Lỗi xóa đơn.");
      }
      showToast("Đã xóa đơn mua hàng thành công.", "success");
      await loadProcurementData();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      showLoading(false);
    }
  };

  // Helper Utilities
  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function showLoading(show, message = "Đang xử lý...") {
    const overlay = document.getElementById("globalLoadingOverlay");
    const textEl = document.getElementById("loadingOverlayText");
    if (!overlay) return;
    if (textEl && message) textEl.textContent = message;
    overlay.style.display = show ? "flex" : "none";
    overlay.setAttribute("aria-hidden", show ? "false" : "true");
  }

  function showToast(message, type = "info") {
    if (typeof window.showNotification === "function") {
      window.showNotification(message, type);
      return;
    }
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4000);
  }

  // Toggle Fullscreen Table Mode
  window.toggleProcurementFullscreen = function () {
    const card = document.getElementById("procurementTableCard");
    const text = document.getElementById("btnTogglePoFullscreenText");
    const btn = document.getElementById("btnTogglePoFullscreen");
    if (!card) return;
    const isFull = card.classList.toggle("fullscreen");
    document.body.classList.toggle("table-modal-fullscreen-open", isFull);
    if (isFull) {
      if (text) text.textContent = "Thu Nhỏ (Esc)";
      if (btn) btn.className = "btn btn-danger btn-xs";
      showToast("Đã mở Full màn hình bảng Mua hàng. Nhấn phím Esc để thu nhỏ.", "success");
    } else {
      if (text) text.textContent = "Full Màn Hình";
      if (btn) btn.className = "btn btn-outline btn-xs";
    }
  };

  // Quick Horizontal Scroll buttons
  window.scrollPoTableHorizontally = function (direction) {
    const wrapper = document.getElementById("procurementTableResponsive");
    if (!wrapper) return;
    const distance = direction === "right" ? 500 : -500;
    wrapper.scrollBy({ left: distance, behavior: "smooth" });
  };

  // =========================================================================
  // PROCUREMENT HARDWARE READINESS & TIMELINE CHART ENGINE (INTERACTIVE)
  // =========================================================================
  let cachedChartData = null;
  let currentChartView = "readiness";

  window.loadProcurementChartData = async function () {
    try {
      const params = new URLSearchParams();
      if (currentFilter.status && currentFilter.status !== "all") params.append("status", currentFilter.status);
      if (currentFilter.supplier && currentFilter.supplier !== "all") params.append("supplier", currentFilter.supplier);
      if (currentFilter.project && currentFilter.project !== "all") params.append("project", currentFilter.project);
      if (currentFilter.search) params.append("search", currentFilter.search);

      const res = await fetch(`/api/v1/procurement/chart-data?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();

      if (data.status === "success") {
        cachedChartData = data;
        renderProcurementChart(data);
      }
    } catch (err) {
      console.error("Lỗi tải dữ liệu biểu đồ mua hàng:", err);
    }
  };

  function renderProcurementChart(data) {
    if (!data) return;
    const kpi = data.kpi || {};
    const overallEl = document.getElementById("chartOverallReadiness");
    if (overallEl) {
      overallEl.textContent = kpi.summary_text || `${kpi.delivered_count || 0}/${kpi.total_orders || 0} thiết bị đã về kho`;
    }

    const timelineBadge = document.getElementById("tabTimelineBadge");
    const timeline = data.timeline_analysis || {};
    const totalTimelineAttention = (timeline.delayed_count || 0) + (timeline.next_week_plan_count || 0);
    if (timelineBadge) {
      timelineBadge.textContent = totalTimelineAttention;
      timelineBadge.style.display = totalTimelineAttention > 0 ? "inline-block" : "none";
    }

    renderProjectReadinessBars(data.projects_readiness || []);
    renderTimelineColumns(timeline);
  }

  // Render Tab 1: Project Hardware Batch Board (Theo Dõi Hàng Theo Lô Dự Án)
  function renderProjectReadinessBars(projects) {
    const container = document.getElementById("projectsReadinessList");
    if (!container) return;

    if (!projects || projects.length === 0) {
      container.innerHTML = `
        <div style="padding: 2.5rem; text-align: center; color: #64748B;">
          <div>Không có dự án mua hàng phù hợp với bộ lọc hiện tại.</div>
        </div>
      `;
      return;
    }

    const html = projects.map(p => {
      const orderIdsJson = JSON.stringify(p.order_ids || []).replace(/"/g, '&quot;');
      const isArrived = p.all_arrived;

      // Danh sách các món hàng trong lô (chỉ là danh sách thông tin, KHÔNG có trạng thái riêng từng món)
      const itemsListHtml = (p.segments || []).map(s => {
        const itemFull = escapeHtml(s.item_name_full || s.item_name);
        const supplier = escapeHtml(s.supplier_name || "-");
        const eta = s.eta_date && s.eta_date !== "-" ? s.eta_date : "";
        const etaText = eta ? ` · ETA: ${eta}` : "";
        return `
          <div class="batch-item-tag" title="${itemFull} | NCC: ${supplier}${etaText}">
            <span class="batch-item-bullet">📦</span>
            <span class="batch-item-title">${escapeHtml(s.item_name)}</span>
            <span class="batch-item-qty">(${s.quantity} ${escapeHtml(s.unit)})</span>
            <span class="batch-item-ncc">· ${supplier}</span>
          </div>
        `;
      }).join("");

      return `
        <div class="project-batch-card ${isArrived ? 'batch-card-arrived' : 'batch-card-pending'}" data-project-key="${escapeHtml(p.project_key)}">
          <div class="batch-proj-col">
            <div class="batch-proj-title" title="${escapeHtml(p.project_name_vi)}">${escapeHtml(p.project_name_vi)}</div>
            ${p.project_name_zh && p.project_name_zh !== p.project_name_vi ? `<div class="batch-proj-zh" title="${escapeHtml(p.project_name_zh)}">${escapeHtml(p.project_name_zh)}</div>` : ''}
            <div class="batch-proj-meta">
              <span class="batch-count-pill">${p.total_items} hạng mục trong lô</span>
            </div>
          </div>

          <div class="batch-items-col">
            <div class="batch-items-tags-wrap">
              ${itemsListHtml}
            </div>
          </div>

          <div class="batch-action-col">
            ${isArrived ? `
              <button type="button" class="btn-batch-toggle btn-batch-status-arrived"
                      onclick="toggleBatchDelivery(${orderIdsJson}, 'PENDING', '${escapeHtml(p.project_name_vi)}')"
                      title="Lô hàng này đã đến. Nhấp chuột để chuyển thành Chưa Đến">
                <span class="batch-toggle-icon">🟢</span>
                <span class="batch-toggle-body">
                  <strong class="batch-toggle-state">ĐÃ ĐẾN (已到貨)</strong>
                  <small class="batch-toggle-hint">⇄ Nhấp để đổi Chưa Đến</small>
                </span>
              </button>
            ` : `
              <button type="button" class="btn-batch-toggle btn-batch-status-pending"
                      onclick="toggleBatchDelivery(${orderIdsJson}, 'DELIVERED', '${escapeHtml(p.project_name_vi)}')"
                      title="Lô hàng này chưa đến. Nhấp chuột để xác nhận Cả Lô Đã Đến">
                <span class="batch-toggle-icon">⚪</span>
                <span class="batch-toggle-body">
                  <strong class="batch-toggle-state">CHƯA ĐẾN (未到貨)</strong>
                  <small class="batch-toggle-hint">⇄ Nhấp để nhận Cả Lô</small>
                </span>
              </button>
            `}
          </div>
        </div>
      `;
    }).join("");

    container.innerHTML = html;
  }

  // 1-Click Toggle Delivery Status for Individual Item
  window.toggleItemDelivery = async function (orderId, event) {
    if (event) {
      if (event.target.classList.contains("seg-edit-btn") || event.target.closest(".seg-edit-btn")) {
        return;
      }
      event.stopPropagation();
    }

    try {
      const res = await fetch(`/api/v1/procurement/orders/${orderId}/toggle-delivery`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.status === "success") {
        showToast(data.message, "success");
        await Promise.all([
          loadProcurementChartData(),
          loadProcurementData()
        ]);
      } else {
        showToast(data.message || "Lỗi cập nhật", "error");
      }
    } catch (err) {
      console.error("Lỗi toggleItemDelivery:", err);
      showToast("Không thể cập nhật trạng thái: " + err.message, "error");
    }
  };

  // Batch Delivery Status Update for the Entire Project Batch (Đi Theo Lô)
  window.toggleBatchDelivery = async function (orderIds, newStatus, projectName) {
    if (!orderIds || !orderIds.length) {
      showToast("Không có thiết bị nào trong lô dự án này.", "error");
      return;
    }

    const actionText = newStatus === "DELIVERED" ? "CẢ LÔ ĐÃ ĐẾN (整批已到)" : "CHƯA ĐẾN (未到貨)";
    try {
      const payload = {
        order_ids: orderIds,
        delivery_status: newStatus,
        actual_delivery_date: newStatus === "DELIVERED" ? new Date().toISOString().split("T")[0] : null
      };

      const res = await fetch("/api/v1/procurement/orders/batch-delivery-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.status === "success") {
        showToast(`✓ Đã cập nhật ${actionText} cho lô ${projectName} (${data.updated_count} thiết bị)!`, "success");
        await Promise.all([
          loadProcurementChartData(),
          loadProcurementData()
        ]);
      } else {
        showToast(data.message || "Lỗi cập nhật lô", "error");
      }
    } catch (err) {
      console.error("Lỗi toggleBatchDelivery:", err);
      showToast("Không thể cập nhật cả lô: " + err.message, "error");
    }
  };

  // Render Tab 2: Weekly Timeline Columns (3 Phần theo chuẩn Sếp)
  function renderTimelineColumns(timeline) {
    const delCountEl = document.getElementById("timelineDeliveredCount");
    const delayCountEl = document.getElementById("timelineDelayedCount");
    const nextCountEl = document.getElementById("timelineNextWeekCount");

    const deliveredList = document.getElementById("timelineDeliveredList");
    const delayedList = document.getElementById("timelineDelayedList");
    const nextList = document.getElementById("timelineNextWeekList");

    const deliveredItems = timeline.delivered_this_week || [];
    const delayedItems = timeline.delayed_items || [];
    const nextItems = timeline.next_week_plan_items || [];

    if (delCountEl) delCountEl.textContent = `${deliveredItems.length} đơn`;
    if (delayCountEl) delayCountEl.textContent = `${delayedItems.length} đơn`;
    if (nextCountEl) nextCountEl.textContent = `${nextItems.length} đơn`;

    // 1. Delivered items
    if (deliveredList) {
      if (deliveredItems.length === 0) {
        deliveredList.innerHTML = `<div style="padding: 1.5rem; text-align: center; color: #94A3B8; font-size: 0.78rem;">Chưa có đơn giao trong tuần này.</div>`;
      } else {
        deliveredList.innerHTML = deliveredItems.map(item => `
          <div class="timeline-item-card" onclick="openChartQuickEditModal(${item.id}, event)" title="Nhấp để xem/sửa">
            <div class="timeline-item-title">${escapeHtml(item.item_name)}</div>
            <div class="timeline-item-meta">
              <span>🏢 ${escapeHtml(item.project_name)}</span>
              <strong style="color: #059669;">Đã giao: ${item.actual_delivery_date || 'Gần đây'}</strong>
            </div>
            <div style="font-size: 0.7rem; color: #64748B;">NCC: <strong>${escapeHtml(item.supplier_name)}</strong> · SL: ${item.quantity} ${item.unit || 'Bộ'}</div>
          </div>
        `).join("");
      }
    }

    // 2. Delayed items
    if (delayedList) {
      if (delayedItems.length === 0) {
        delayedList.innerHTML = `<div style="padding: 1.5rem; text-align: center; color: #059669; font-size: 0.78rem; font-weight: 700;">🎉 Tuyệt vời! Không có đơn nào bị trễ hạn.</div>`;
      } else {
        delayedList.innerHTML = delayedItems.map(item => `
          <div class="timeline-item-card" onclick="openChartQuickEditModal(${item.id}, event)" title="Nhấp để giải trình lý do">
            <div class="timeline-item-title" style="color: #DC2626;">🚨 ${escapeHtml(item.item_name)}</div>
            <div class="timeline-item-meta">
              <span>🏢 ${escapeHtml(item.project_name)}</span>
              <span style="color: #DC2626; font-weight: 700;">Hạn ETA: ${item.eta_date || 'Chưa rõ'}</span>
            </div>
            <div class="timeline-item-reason">
              ${item.shipping_notes && item.shipping_notes !== '-' ? escapeHtml(item.shipping_notes) : '<em>Chưa ghi chú lý do trễ - Nhấp vào để cập nhật giải trình với Sếp!</em>'}
            </div>
          </div>
        `).join("");
      }
    }

    // 3. Next week items
    if (nextList) {
      if (nextItems.length === 0) {
        nextList.innerHTML = `<div style="padding: 1.5rem; text-align: center; color: #94A3B8; font-size: 0.78rem;">Không có đơn nào dự kiến rơi vào tuần tới.</div>`;
      } else {
        nextList.innerHTML = nextItems.map(item => `
          <div class="timeline-item-card" onclick="openChartQuickEditModal(${item.id}, event)" title="Nhấp để xem/sửa">
            <div class="timeline-item-title">🎯 ${escapeHtml(item.item_name)}</div>
            <div class="timeline-item-meta">
              <span>🏢 ${escapeHtml(item.project_name)}</span>
              <strong style="color: #7C3AED;">Hẹn ETA: ${item.eta_date || '-'}</strong>
            </div>
            <div style="font-size: 0.7rem; color: #64748B;">NCC: <strong>${escapeHtml(item.supplier_name)}</strong> · ${item.supplier_payment_status || 'Chưa thanh toán'}</div>
          </div>
        `).join("");
      }
    }
  }

  // Switch between Tab 1 (Readiness) and Tab 2 (Timeline)
  window.switchProcurementChartView = function (mode) {
    currentChartView = mode;
    const btnReadiness = document.getElementById("tabBtnProjectReadiness");
    const btnTimeline = document.getElementById("tabBtnTimeline");
    const panelReadiness = document.getElementById("panelProjectReadiness");
    const panelTimeline = document.getElementById("panelTimeline");
    const legendRow = document.getElementById("chartLegendRow");

    if (mode === "readiness") {
      if (btnReadiness) btnReadiness.classList.add("active");
      if (btnTimeline) btnTimeline.classList.remove("active");
      if (panelReadiness) panelReadiness.style.display = "block";
      if (panelTimeline) panelTimeline.style.display = "none";
      if (legendRow) legendRow.style.display = "flex";
    } else {
      if (btnReadiness) btnReadiness.classList.remove("active");
      if (btnTimeline) btnTimeline.classList.add("active");
      if (panelReadiness) panelReadiness.style.display = "none";
      if (panelTimeline) panelTimeline.style.display = "block";
      if (legendRow) legendRow.style.display = "none";
    }
  };

  // Fullscreen Presentation Mode for Meetings with Boss
  window.toggleProcurementChartFullscreen = function () {
    const card = document.getElementById("procurementChartCard");
    const textEl = document.getElementById("btnChartFullscreenText");
    const btnEl = document.getElementById("btnChartFullscreen");
    if (!card) return;

    const isFull = card.classList.toggle("is-fullscreen");
    document.body.classList.toggle("chart-fullscreen-open", isFull);

    if (isFull) {
      if (textEl) textEl.textContent = "Thu Nhỏ (Esc)";
      if (btnEl) btnEl.className = "btn btn-danger btn-xs";
      showToast("Đã mở biểu đồ toàn màn hình để báo cáo. Nhấn phím Esc để thu nhỏ.", "success");
    } else {
      if (textEl) textEl.textContent = "Toàn Màn Hình";
      if (btnEl) btnEl.className = "btn btn-outline btn-xs";
    }
  };

  // Collapse / Expand Chart Section
  window.toggleChartSectionCollapse = function () {
    const card = document.getElementById("procurementChartCard");
    const icon = document.getElementById("btnChartCollapseIcon");
    const panelReadiness = document.getElementById("panelProjectReadiness");
    const panelTimeline = document.getElementById("panelTimeline");
    const legendRow = document.getElementById("chartLegendRow");

    const isCollapsed = card.classList.toggle("is-collapsed");
    if (isCollapsed) {
      if (panelReadiness) panelReadiness.style.display = "none";
      if (panelTimeline) panelTimeline.style.display = "none";
      if (legendRow) legendRow.style.display = "none";
      if (icon) icon.textContent = "▼";
    } else {
      window.switchProcurementChartView(currentChartView);
      if (icon) icon.textContent = "▲";
    }
  };

  // =========================================================================
  // INLINE QUICK EDIT POPOVER LOGIC (CLICK TRỰC TIẾP TRÊN SƠ ĐỒ ĐỂ SỬA)
  // =========================================================================
  let currentEditingOrder = null;

  window.openChartQuickEditModal = function (orderId, event) {
    if (event && event.stopPropagation) {
      event.stopPropagation();
    }

    // Find order data
    let ord = cachedOrders.find(o => o.id === orderId);
    if (!ord && cachedChartData) {
      for (const p of cachedChartData.projects_readiness || []) {
        const found = (p.segments || []).find(s => s.id === orderId);
        if (found) {
          ord = found;
          break;
        }
      }
    }

    if (!ord) {
      showToast("Không tìm thấy thông tin đơn hàng này.", "error");
      return;
    }

    currentEditingOrder = ord;

    // Populate Modal fields
    const modal = document.getElementById("chartQuickEditModal");
    const badgeEl = document.getElementById("chartEditProjectBadge");
    const titleEl = document.getElementById("chartEditItemName");
    const subEl = document.getElementById("chartEditSubInfo");

    const idInput = document.getElementById("chartEditOrderId");
    const statusSelect = document.getElementById("chartEditDeliveryStatus");
    const payInput = document.getElementById("chartEditSupplierPayment");
    const etaInput = document.getElementById("chartEditEtaDate");
    const actualInput = document.getElementById("chartEditActualDate");
    const qtyInput = document.getElementById("chartEditQuantity");
    const unitInput = document.getElementById("chartEditUnit");
    const supplierInput = document.getElementById("chartEditSupplierName");
    const notesTextarea = document.getElementById("chartEditShippingNotes");

    if (badgeEl) badgeEl.textContent = ord.project_name || ord.customer_company || "DỰ ÁN";
    if (titleEl) titleEl.textContent = ord.item_name_full || ord.item_name || "Thiết Bị";
    if (subEl) subEl.textContent = `Nhà cung cấp: ${ord.supplier_name || '-'} · SL: ${ord.quantity || 1} ${ord.unit || 'Bộ'}`;

    if (idInput) idInput.value = ord.id;
    if (statusSelect) statusSelect.value = ord.delivery_status || "PENDING";
    if (payInput) payInput.value = ord.supplier_payment_status && ord.supplier_payment_status !== '-' ? ord.supplier_payment_status : "";
    if (etaInput) etaInput.value = ord.eta_date && ord.eta_date !== '-' ? ord.eta_date : "";
    if (actualInput) actualInput.value = ord.actual_delivery_date && ord.actual_delivery_date !== '-' ? ord.actual_delivery_date : "";
    if (qtyInput) qtyInput.value = ord.quantity || 1;
    if (unitInput) unitInput.value = ord.unit || "Bộ";
    if (supplierInput) supplierInput.value = ord.supplier_name && ord.supplier_name !== '-' ? ord.supplier_name : "";
    if (notesTextarea) notesTextarea.value = ord.shipping_notes && ord.shipping_notes !== '-' ? ord.shipping_notes : "";

    if (modal) {
      modal.style.display = "flex";
      setTimeout(() => {
        if (notesTextarea) notesTextarea.focus();
      }, 100);
    }
  };

  window.onChartEditStatusChange = function (newStatus) {
    const actualInput = document.getElementById("chartEditActualDate");
    if (newStatus === "DELIVERED" && actualInput && !actualInput.value) {
      actualInput.value = new Date().toISOString().split("T")[0];
    }
  };

  window.closeChartQuickEditModal = function (event) {
    if (event && event.target && event.target.id !== "chartQuickEditModal" && !event.target.classList.contains("btn-close-chart-edit")) {
      return;
    }
    const modal = document.getElementById("chartQuickEditModal");
    if (modal) modal.style.display = "none";
    currentEditingOrder = null;
  };

  window.saveChartQuickEdit = async function () {
    const orderId = document.getElementById("chartEditOrderId").value;
    if (!orderId) return;

    const btnSave = document.getElementById("btnSaveChartQuickEdit");
    const originalText = btnSave ? btnSave.innerHTML : "";
    if (btnSave) {
      btnSave.disabled = true;
      btnSave.innerHTML = `<span>Đang lưu...</span>`;
    }

    try {
      const payload = {
        delivery_status: document.getElementById("chartEditDeliveryStatus").value,
        supplier_payment_status: document.getElementById("chartEditSupplierPayment").value.trim(),
        eta_date: document.getElementById("chartEditEtaDate").value || null,
        actual_delivery_date: document.getElementById("chartEditActualDate").value || null,
        quantity: parseFloat(document.getElementById("chartEditQuantity").value) || 1.0,
        unit: document.getElementById("chartEditUnit").value.trim() || "Bộ",
        supplier_name: document.getElementById("chartEditSupplierName").value.trim(),
        shipping_notes: document.getElementById("chartEditShippingNotes").value.trim(),
      };

      const res = await fetch(`/api/v1/procurement/orders/${orderId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const resData = await res.json();

      if (resData.status === "success") {
        showToast("Đã lưu cập nhật thiết bị thành công!", "success");
        closeChartQuickEditModal();

        // Reload data and redraw chart dynamically
        await Promise.all([
          loadProcurementData(),
          loadProcurementChartData()
        ]);
      } else {
        throw new Error(resData.message || "Lỗi lưu dữ liệu");
      }
    } catch (err) {
      console.error("Lỗi saveChartQuickEdit:", err);
      showToast("Không thể lưu: " + err.message, "error");
    } finally {
      if (btnSave) {
        btnSave.disabled = false;
        btnSave.innerHTML = originalText;
      }
    }
  };

  window.openFullModalFromChartEdit = function () {
    if (!currentEditingOrder) return;
    const orderId = currentEditingOrder.id;
    closeChartQuickEditModal();
    if (window.openEditOrderModal) {
      window.openEditOrderModal(orderId);
    }
  };

  // Global Escape listener to exit chart fullscreen or close quick edit modal
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      const editModal = document.getElementById("chartQuickEditModal");
      if (editModal && editModal.style.display === "flex") {
        closeChartQuickEditModal();
        return;
      }

      const chartCard = document.getElementById("procurementChartCard");
      if (chartCard && chartCard.classList.contains("is-fullscreen")) {
        window.toggleProcurementChartFullscreen();
        return;
      }

      const card = document.getElementById("procurementTableCard");
      if (card && card.classList.contains("fullscreen")) {
        window.toggleProcurementFullscreen();
      }
    }
  });
})();

