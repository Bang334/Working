/**
 * Repair Contract Editor - Logic quản trị & tương tác giao diện Hợp Đồng Sửa Chữa
 * Hong Ming Global PM Portal
 */

const RepairContractEditor = {
  items: [],
  installments: [],
  currentAttachedAiFile: null,

  parseNumber(str) {
    if (typeof str === "number") return Math.round(str);
    if (!str) return 0;
    const digits = String(str).replace(/[^\d]/g, "");
    return digits ? parseInt(digits, 10) : 0;
  },

  formatCurrency(num) {
    return this.parseNumber(num).toLocaleString("vi-VN") + " VND";
  },

  init() {
    this.bindDropzoneEvents();
    this.bindPasteEvents();

    // Default installments if empty
    if (!this.installments || this.installments.length === 0) {
      this.renderInstallments([
        {
          dot: 1,
          phan_tram: 50,
          tieu_de: "Tạm ứng ký hợp đồng",
          tieu_de_trung: "簽約預付款",
          dieu_kien_viet: "Thanh toán tạm ứng 50% ngay sau khi hai bên ký kết hợp đồng sửa chữa",
          dieu_kien_trung: "雙方簽署維修合約後即期以電匯方式支付 50%",
          thoi_han_tt_ngay: 0,
        },
        {
          dot: 2,
          phan_tram: 50,
          tieu_de: "Nghiệm thu hoàn tất",
          tieu_de_trung: "驗收交付款",
          dieu_kien_viet: "Thanh toán 50% còn lại sau khi hoàn thành sửa chữa, chạy thử đạt và ký biên bản nghiệm thu",
          dieu_kien_trung: "設備維修完成、測試正常並簽署驗收確認書後支付剩餘 50%",
          thoi_han_tt_ngay: 30,
        },
      ]);
    }

    if (this.items.length === 0) {
      this.addRow();
    }

    this.loadRepairContractsList();
  },

  // ==========================================
  // TABLE MANAGEMENT: ITEMS
  // ==========================================
  addRow(itemData = null) {
    const defaultItem = {
      stt: this.items.length + 1,
      ten_thiet_bi: "",
      model_serial: "",
      noi_dung_sua_chua: "",
      don_gia: "0 VND",
      so_luong: "1",
      tong_gia: "0 VND",
    };
    const item = itemData ? { ...defaultItem, ...itemData } : defaultItem;
    this.items.push(item);
    this.renderItemsTable();
    this.recalculateAllTotals();
  },

  removeRow(index) {
    if (this.items.length <= 1) {
      showToast("Hợp đồng cần có ít nhất một hạng mục thiết bị sửa chữa.", "warning");
      return;
    }
    this.items.splice(index, 1);
    this.renderItemsTable();
    this.recalculateAllTotals();
  },

  renderItemsTable() {
    const tbody = document.getElementById("repairItemsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    this.items.forEach((item, idx) => {
      const tr = document.createElement("tr");
      tr.className = "repair-item-row";
      tr.innerHTML = `
        <td style="text-align: center; font-weight: 700; color: #475569;">${idx + 1}</td>
        <td>
          <input type="text" class="form-control form-control-sm item-name font-bold" 
                 value="${this.escapeHtml(item.ten_thiet_bi || "")}" 
                 placeholder="Ví dụ: Máy tính công nghiệp IPC Advantech / 研華工控機"
                 oninput="RepairContractEditor.updateItemField(${idx}, 'ten_thiet_bi', this.value)">
        </td>
        <td>
          <input type="text" class="form-control form-control-sm item-serial" 
                 value="${this.escapeHtml(item.model_serial || "")}" 
                 placeholder="Model / Serial: IPC-610H / CX-SN2024"
                 oninput="RepairContractEditor.updateItemField(${idx}, 'model_serial', this.value)">
        </td>
        <td>
          <input type="text" class="form-control form-control-sm item-desc" 
                 value="${this.escapeHtml(item.noi_dung_sua_chua || "")}" 
                 placeholder="Lỗi: Hỏng nguồn, chập IC - Thay nguồn ATX & IC điều khiển"
                 oninput="RepairContractEditor.updateItemField(${idx}, 'noi_dung_sua_chua', this.value)">
        </td>
        <td>
          <input type="text" class="form-control form-control-sm item-price text-right font-mono" 
                 value="${this.formatCurrency(item.don_gia || 0).replace(' VND', '')}" 
                 placeholder="0"
                 oninput="RepairContractEditor.onPriceInput(${idx}, this)">
        </td>
        <td>
          <input type="text" class="form-control form-control-sm item-qty text-center" 
                 value="${this.escapeHtml(item.so_luong || '1')}" 
                 placeholder="1 Cái"
                 oninput="RepairContractEditor.onQtyInput(${idx}, this)">
        </td>
        <td>
          <input type="text" class="form-control form-control-sm item-total text-right font-bold font-mono" 
                 value="${this.formatCurrency(item.tong_gia || 0)}" 
                 readonly style="background: #f8fafc; color: #1d4ed8;">
        </td>
        <td style="text-align: center;">
          <button type="button" class="btn btn-outline btn-xs" onclick="RepairContractEditor.removeRow(${idx})" title="Xóa dòng này" style="color: #dc2626; border-color: #fca5a5; padding: 2px 7px;">
            ×
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  },

  updateItemField(index, field, value) {
    if (this.items[index]) {
      this.items[index][field] = value;
    }
  },

  onPriceInput(index, inputElem) {
    const rawVal = this.parseNumber(inputElem.value);
    inputElem.value = rawVal.toLocaleString("vi-VN");
    if (this.items[index]) {
      this.items[index].don_gia = this.formatCurrency(rawVal);
      const qtyNum = this.parseNumber(this.items[index].so_luong) || 1;
      const rowTotal = rawVal * qtyNum;
      this.items[index].tong_gia = this.formatCurrency(rowTotal);

      // Update row total cell without re-rendering whole table
      const row = inputElem.closest("tr");
      const totalInput = row?.querySelector(".item-total");
      if (totalInput) totalInput.value = this.formatCurrency(rowTotal);
    }
    this.recalculateAllTotals();
  },

  onQtyInput(index, inputElem) {
    const qtyStr = inputElem.value;
    if (this.items[index]) {
      this.items[index].so_luong = qtyStr;
      const qtyNum = this.parseNumber(qtyStr) || 1;
      const priceNum = this.parseNumber(this.items[index].don_gia) || 0;
      const rowTotal = priceNum * qtyNum;
      this.items[index].tong_gia = this.formatCurrency(rowTotal);

      const row = inputElem.closest("tr");
      const totalInput = row?.querySelector(".item-total");
      if (totalInput) totalInput.value = this.formatCurrency(rowTotal);
    }
    this.recalculateAllTotals();
  },

  recalculateAllTotals() {
    let grandTotal = 0;
    let totalQty = 0;

    this.items.forEach((item) => {
      const p = this.parseNumber(item.don_gia);
      const q = this.parseNumber(item.so_luong) || 1;
      grandTotal += p * q;
      totalQty += q;
    });

    // Update KPI Displays
    const totalDisplay = document.getElementById("summaryRepairTotalDisplay");
    if (totalDisplay) totalDisplay.textContent = this.formatCurrency(grandTotal);

    const qtyDisplay = document.getElementById("summaryRepairQtyDisplay");
    if (qtyDisplay) qtyDisplay.textContent = `${totalQty} MÁY/BỘ`;

    const grandTotalInput = document.getElementById("fieldRepairTotalAmount");
    if (grandTotalInput) grandTotalInput.value = this.formatCurrency(grandTotal).replace(" VND", "");

    // Update Installments amounts
    this.updateInstallmentsWithTotal(grandTotal);
  },

  // ==========================================
  // INSTALLMENTS (TIẾN ĐỘ THANH TOÁN)
  // ==========================================
  renderInstallments(installmentsList) {
    this.installments = installmentsList || [];
    const container = document.getElementById("repairInstallmentsEditor");
    if (!container) return;
    container.innerHTML = "";

    this.installments.forEach((inst, idx) => {
      const row = document.createElement("div");
      row.className = "repair-installment-row";
      row.style.cssText = "display: flex; gap: 0.65rem; align-items: center; margin-bottom: 0.65rem; background: #ffffff; padding: 0.65rem 0.85rem; border: 1px solid #e2e8f0; border-radius: 6px; flex-wrap: wrap;";
      row.innerHTML = `
        <div style="font-weight: 750; font-size: 0.82rem; color: #1e40af; width: 65px;">Đợt ${idx + 1}:</div>
        <div style="width: 85px;">
          <input type="number" class="form-control form-control-sm inst-percent text-center font-bold" 
                 value="${inst.phan_tram || 0}" min="0" max="100" step="5"
                 oninput="RepairContractEditor.onInstallmentPercentChange(${idx}, this.value)" title="Tỷ lệ %">
        </div>
        <div style="width: 140px;">
          <input type="text" class="form-control form-control-sm inst-amount text-right font-mono" 
                 value="${inst.so_tien || '0 VND'}" readonly style="background: #f8fafc; font-weight: 600;">
        </div>
        <div style="flex: 2; min-width: 200px;">
          <input type="text" class="form-control form-control-sm inst-cond-vi" 
                 value="${this.escapeHtml(inst.dieu_kien_viet || '')}" 
                 placeholder="Điều kiện tiếng Việt"
                 oninput="RepairContractEditor.installments[${idx}].dieu_kien_viet = this.value">
        </div>
        <div style="flex: 2; min-width: 200px;">
          <input type="text" class="form-control form-control-sm inst-cond-zh" 
                 value="${this.escapeHtml(inst.dieu_kien_trung || '')}" 
                 placeholder="Điều kiện tiếng Trung"
                 oninput="RepairContractEditor.installments[${idx}].dieu_kien_trung = this.value">
        </div>
        <div style="width: 80px;">
          <input type="number" class="form-control form-control-sm text-center" 
                 value="${inst.thoi_han_tt_ngay !== undefined && inst.thoi_han_tt_ngay !== null ? inst.thoi_han_tt_ngay : (idx === 0 ? 0 : 30)}" 
                 placeholder="T/T ngày" title="Thời hạn thanh toán T/T tính bằng ngày"
                 oninput="RepairContractEditor.installments[${idx}].thoi_han_tt_ngay = parseInt(this.value, 10) || 0">
        </div>
        <button type="button" class="btn btn-outline btn-xs" onclick="RepairContractEditor.removeInstallment(${idx})" style="color: #dc2626; border-color: #fca5a5;">×</button>
      `;
      container.appendChild(row);
    });

    this.updateInstallmentsSummary();
  },

  addInstallment() {
    this.installments.push({
      dot: this.installments.length + 1,
      phan_tram: 0,
      so_tien: "0 VND",
      tieu_de: `Đợt ${this.installments.length + 1}`,
      tieu_de_trung: `第 ${this.installments.length + 1} 期`,
      dieu_kien_viet: "Thanh toán theo tiến độ nghiệm thu thực tế",
      dieu_kien_trung: "依實際驗收進度以電匯方式支付",
      thoi_han_tt_ngay: 30,
    });
    this.renderInstallments(this.installments);
    this.recalculateAllTotals();
  },

  removeInstallment(index) {
    if (this.installments.length <= 1) {
      showToast("Cần có ít nhất 1 đợt thanh toán.", "warning");
      return;
    }
    this.installments.splice(index, 1);
    this.renderInstallments(this.installments);
    this.recalculateAllTotals();
  },

  onInstallmentPercentChange(index, value) {
    const pct = parseFloat(value) || 0;
    if (this.installments[index]) {
      this.installments[index].phan_tram = pct;
      const totalAmount = this.parseNumber(document.getElementById("fieldRepairTotalAmount")?.value || 0);
      const instAmount = Math.round((totalAmount * pct) / 100);
      this.installments[index].so_tien = this.formatCurrency(instAmount);

      const rows = document.querySelectorAll(".repair-installment-row");
      if (rows[index]) {
        const amountInput = rows[index].querySelector(".inst-amount");
        if (amountInput) amountInput.value = this.formatCurrency(instAmount);
      }
    }
    this.updateInstallmentsSummary();
  },

  updateInstallmentsWithTotal(grandTotal) {
    this.installments.forEach((inst, idx) => {
      const pct = parseFloat(inst.phan_tram) || 0;
      const amount = Math.round((grandTotal * pct) / 100);
      inst.so_tien = this.formatCurrency(amount);

      const rows = document.querySelectorAll(".repair-installment-row");
      if (rows[idx]) {
        const amountInput = rows[idx].querySelector(".inst-amount");
        if (amountInput) amountInput.value = this.formatCurrency(amount);
      }
    });

    // Update KPI Phase 1 and Phase Last
    const phase1Card = document.getElementById("summaryRepairPhase1Display");
    const phaseLastCard = document.getElementById("summaryRepairPhaseLastDisplay");
    if (this.installments.length > 0 && phase1Card) {
      phase1Card.textContent = this.installments[0].so_tien || "0 VND";
    }
    if (this.installments.length > 1 && phaseLastCard) {
      phaseLastCard.textContent = this.installments[this.installments.length - 1].so_tien || "0 VND";
    }
    this.updateInstallmentsSummary();
  },

  updateInstallmentsSummary() {
    let sumPct = 0;
    this.installments.forEach((inst) => {
      sumPct += parseFloat(inst.phan_tram) || 0;
    });
    const lbl = document.getElementById("repairPaymentPercentTotal");
    if (lbl) {
      lbl.textContent = `總計 / Tổng: ${sumPct}%`;
      lbl.style.color = sumPct === 100 ? "#16a34a" : "#dc2626";
    }
  },

  // ==========================================
  // FORM DATA POPULATION & COLLECTION
  // ==========================================
  populateForm(data) {
    if (!data) return;

    if (data.so_hop_dong) document.getElementById("fieldRepairContractNo").value = data.so_hop_dong;
    if (data.ngay_ky) document.getElementById("fieldRepairDay").value = data.ngay_ky;
    if (data.thang_ky) document.getElementById("fieldRepairMonth").value = data.thang_ky;
    if (data.nam_ky) document.getElementById("fieldRepairYear").value = data.nam_ky;

    // Bên A
    const benA = data.ben_a || {};
    if (benA.ten_cong_ty) document.getElementById("fieldRepairCompanyA").value = benA.ten_cong_ty;
    if (benA.ten_tieng_trung) document.getElementById("fieldRepairCompanyACn").value = benA.ten_tieng_trung;
    if (benA.dia_chi) document.getElementById("fieldRepairAddressA").value = benA.dia_chi;
    if (benA.dia_chi_trung) document.getElementById("fieldRepairAddressACn").value = benA.dia_chi_trung;
    if (benA.mst) document.getElementById("fieldRepairTaxA").value = benA.mst;
    if (benA.nguoi_dai_dien) document.getElementById("fieldRepairRepA").value = benA.nguoi_dai_dien;
    if (benA.chuc_vu) document.getElementById("fieldRepairRoleA").value = benA.chuc_vu;

    // Sửa chữa details
    if (data.ten_goi_sua_chua_viet) document.getElementById("fieldRepairProjectVn").value = data.ten_goi_sua_chua_viet;
    if (data.ten_goi_sua_chua_trung) document.getElementById("fieldRepairProjectCn").value = data.ten_goi_sua_chua_trung;
    if (data.dia_diem_sua_chua) document.getElementById("fieldRepairLocation").value = data.dia_diem_sua_chua;
    if (data.thoi_gian_hoan_thanh_ngay) document.getElementById("fieldRepairDeliveryDays").value = data.thoi_gian_hoan_thanh_ngay;
    if (data.thoi_gian_bao_hanh_thang) document.getElementById("fieldRepairWarrantyMonths").value = data.thoi_gian_bao_hanh_thang;

    // Items
    if (Array.isArray(data.hang_muc) && data.hang_muc.length > 0) {
      this.items = data.hang_muc.map((it, idx) => ({
        stt: idx + 1,
        ten_thiet_bi: it.ten_thiet_bi || it.ten_san_pham || "",
        model_serial: it.model_serial || "",
        noi_dung_sua_chua: it.noi_dung_sua_chua || "",
        don_gia: it.don_gia || "0 VND",
        so_luong: it.so_luong || "1",
        tong_gia: it.tong_gia || "0 VND",
      }));
      this.renderItemsTable();
    }

    // Installments
    if (Array.isArray(data.phan_bo_thanh_toan) && data.phan_bo_thanh_toan.length > 0) {
      this.renderInstallments(data.phan_bo_thanh_toan);
    }

    this.recalculateAllTotals();
  },

  collectFormData() {
    const exportDirInput = document.getElementById("txtRepairExportDirectory");
    const customExportDir = (exportDirInput ? exportDirInput.value.trim() : "") || "E:\\Working\\Ho So Du An\\Hop Dong\\";

    return {
      so_hop_dong: document.getElementById("fieldRepairContractNo")?.value.trim() || "HDSC-20261019-001",
      ngay_ky: document.getElementById("fieldRepairDay")?.value.trim() || new Date().getDate().toString(),
      thang_ky: document.getElementById("fieldRepairMonth")?.value.trim() || (new Date().getMonth() + 1).toString(),
      nam_ky: document.getElementById("fieldRepairYear")?.value.trim() || new Date().getFullYear().toString(),
      ben_a: {
        ten_cong_ty: document.getElementById("fieldRepairCompanyA")?.value.trim() || "",
        ten_tieng_trung: document.getElementById("fieldRepairCompanyACn")?.value.trim() || "",
        dia_chi: document.getElementById("fieldRepairAddressA")?.value.trim() || "",
        dia_chi_trung: document.getElementById("fieldRepairAddressACn")?.value.trim() || "",
        mst: document.getElementById("fieldRepairTaxA")?.value.trim() || "",
        nguoi_dai_dien: document.getElementById("fieldRepairRepA")?.value.trim() || "",
        chuc_vu: document.getElementById("fieldRepairRoleA")?.value.trim() || "TỔNG GIÁM ĐỐC / 總經理",
      },
      ten_goi_sua_chua_viet: document.getElementById("fieldRepairProjectVn")?.value.trim() || "Dịch vụ sửa chữa và bảo dưỡng thiết bị",
      ten_goi_sua_chua_trung: document.getElementById("fieldRepairProjectCn")?.value.trim() || "設備維修與保養服務",
      dia_diem_sua_chua: document.getElementById("fieldRepairLocation")?.value.trim() || "Tại nhà xưởng sản xuất Bên A",
      thoi_gian_hoan_thanh_ngay: parseInt(document.getElementById("fieldRepairDeliveryDays")?.value || "15", 10),
      thoi_gian_bao_hanh_thang: parseInt(document.getElementById("fieldRepairWarrantyMonths")?.value || "6", 10),
      hang_muc: this.items,
      tong_tien_hop_dong_so: document.getElementById("fieldRepairTotalAmount")?.value.trim() || "0",
      phan_bo_thanh_toan: this.installments,
      custom_output_dir: customExportDir,
    };
  },

  // ==========================================
  // DRAG & DROP AND FILE ATTACHMENTS
  // ==========================================
  bindDropzoneEvents() {
    const dropZone = document.getElementById("aiRepairDropZone");
    const overlay = document.getElementById("aiRepairDragOverlay");
    if (!dropZone) return;

    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (overlay) overlay.style.display = "flex";
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (overlay) overlay.style.display = "none";
      });
    });

    dropZone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      const files = dt?.files;
      if (files && files.length > 0) {
        this.processSelectedFile(files[0]);
      }
    });
  },

  bindPasteEvents() {
    document.addEventListener("paste", (e) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf("image") !== -1) {
          const blob = items[i].getAsFile();
          if (blob) {
            this.processSelectedFile(blob, `anh_dan_${new Date().getTime()}.png`);
            showToast("Đã dán ảnh từ bộ nhớ tạm (Clipboard) vào ô phân tích!", "info");
            break;
          }
        }
      }
    });
  },

  processSelectedFile(file, customName = null) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64Data = e.target.result.split(",")[1];
      this.currentAttachedAiFile = {
        name: customName || file.name,
        size: file.size,
        mime: file.type || "application/octet-stream",
        base64: base64Data,
      };
      this.renderAttachedFilePreview();
    };
    reader.readAsDataURL(file);
  },

  renderAttachedFilePreview() {
    const container = document.getElementById("attachedRepairFileContainer");
    const nameElem = document.getElementById("attachedRepairFileName");
    const sizeElem = document.getElementById("attachedRepairFileSize");
    const thumbElem = document.getElementById("attachedRepairFilePreviewThumb");
    const badgeElem = document.getElementById("attachedRepairFileTypeBadge");

    if (!this.currentAttachedAiFile || !container) return;

    nameElem.textContent = this.currentAttachedAiFile.name;
    sizeElem.textContent = `${(this.currentAttachedAiFile.size / 1024).toFixed(1)} KB`;

    if (this.currentAttachedAiFile.mime.startsWith("image/")) {
      thumbElem.innerHTML = `<img src="data:${this.currentAttachedAiFile.mime};base64,${this.currentAttachedAiFile.base64}" style="width: 100%; height: 100%; object-fit: cover;">`;
      badgeElem.textContent = "Ảnh Báo Giá / Lỗi";
    } else {
      thumbElem.innerHTML = `<span style="font-size: 1.5rem;">📄</span>`;
      badgeElem.textContent = "Bảng Excel / Tài Liệu";
    }
    container.style.display = "flex";
  },

  clearAttachedFile() {
    this.currentAttachedAiFile = null;
    const container = document.getElementById("attachedRepairFileContainer");
    if (container) container.style.display = "none";
    const input = document.getElementById("aiRepairFileInput");
    if (input) input.value = "";
  },

  // ==========================================
  // LIST OF REPAIR CONTRACTS
  // ==========================================
  async loadRepairContractsList() {
    try {
      const result = await ApiClient.getRepairContractsList();
      const tbody = document.getElementById("repairContractsListTableBody");
      const emptyState = document.getElementById("repairContractListEmptyState");
      const badge = document.getElementById("repairContractListCountBadge");
      const headerBadge = document.getElementById("headerRepairContractCount");

      if (!result || result.status !== "success" || !Array.isArray(result.data) || result.data.length === 0) {
        if (tbody) tbody.innerHTML = "";
        if (emptyState) emptyState.style.display = "block";
        if (badge) badge.textContent = "0 hợp đồng";
        if (headerBadge) headerBadge.textContent = "0";
        return;
      }

      if (emptyState) emptyState.style.display = "none";
      if (badge) badge.textContent = `${result.data.length} hợp đồng`;
      if (headerBadge) headerBadge.textContent = `${result.data.length}`;

      if (tbody) {
        tbody.innerHTML = "";
        result.data.forEach((c, idx) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td style="text-align: center; color: #64748b;">${idx + 1}</td>
            <td>
              <strong style="color: #1d4ed8; font-family: monospace;">${c.contract_code}</strong>
              <div style="font-size: 0.74rem; color: #64748b;">${c.signed_date || "Chưa ghi ngày"}</div>
            </td>
            <td>
              <div style="font-weight: 700; color: #1e293b;">${c.customer_name_vi || "---"}</div>
              <div style="font-size: 0.76rem; color: #64748b;">${c.customer_name_zh || ""}</div>
            </td>
            <td>
              <div style="font-weight: 600; color: #334155;">${c.project_name_vi || "Dịch vụ sửa chữa"}</div>
              <div style="font-size: 0.75rem; color: #64748b;">${c.project_name_zh || ""}</div>
            </td>
            <td style="text-align: right; font-weight: 800; color: #047857; font-family: monospace;">
              ${c.total_amount_formatted}
            </td>
            <td style="text-align: center;">
              <span class="badge-pill blue" style="font-size: 0.75rem;">${c.status || "Đang thực hiện"}</span>
            </td>
            <td style="text-align: center;">
              <div style="display: inline-flex; gap: 0.35rem;">
                <button type="button" class="btn btn-outline btn-xs" onclick="RepairContractEditor.loadDetailIntoForm('${c.contract_code}')" title="Nạp vào form để xem & sửa">
                  ✏️ Xem
                </button>
                <button type="button" class="btn btn-outline btn-xs" onclick="RepairContractEditor.deleteContract('${c.contract_code}')" title="Xóa hợp đồng này" style="color: #dc2626; border-color: #fca5a5;">
                  🗑️
                </button>
              </div>
            </td>
          `;
          tbody.appendChild(tr);
        });
      }
    } catch (e) {
      console.warn("Could not load repair contracts list:", e);
    }
  },

  async loadDetailIntoForm(contractCode) {
    try {
      setLoading(true, `Đang nạp dữ liệu hợp đồng ${contractCode}...`);
      const res = await fetch(`/api/v1/repair-contracts/detail/${encodeURIComponent(contractCode)}`);
      const json = await res.json();
      if (json.status === "success" && json.data) {
        this.populateForm(json.data);
        switchTab("tabRepairProducts");
        showToast(`Đã nạp dữ liệu hợp đồng ${contractCode}!`, "success");
      }
    } catch (e) {
      showToast(`Lỗi: ${e.message}`, "error");
    } finally {
      setLoading(false);
    }
  },

  async deleteContract(contractCode) {
    if (!confirm(`Bạn có chắc muốn xóa hợp đồng sửa chữa "${contractCode}" khỏi hệ thống?`)) return;
    try {
      setLoading(true, "Đang xóa hợp đồng...");
      const res = await ApiClient.deleteRepairContract(contractCode);
      showToast(res.message || "Đã xóa hợp đồng thành công!", "success");
      this.loadRepairContractsList();
    } catch (e) {
      showToast(`Lỗi xóa: ${e.message}`, "error");
    } finally {
      setLoading(false);
    }
  },

  escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },
};

// ==========================================
// ACTION HANDLERS
// ==========================================

async function handleAIRepairParse() {
  const promptInput = document.getElementById("aiRepairPromptInput");
  const rawText = promptInput?.value.trim() || "";

  if (!rawText && !RepairContractEditor.currentAttachedAiFile) {
    showToast("Vui lòng dán văn bản báo giá sửa chữa hoặc tải lên tệp (ảnh / Excel) cần bóc tách.", "error");
    return;
  }

  const loadingMsg = RepairContractEditor.currentAttachedAiFile
    ? `Gemini AI đang phân tích tệp "${RepairContractEditor.currentAttachedAiFile.name}" & trích xuất thiết bị sửa chữa...`
    : "Gemini AI đang phân tích dữ liệu hợp đồng sửa chữa & thiết bị hư hỏng...";

  try {
    setLoading(true, loadingMsg);
    const result = await ApiClient.parseRepairWithAI(rawText, null, RepairContractEditor.currentAttachedAiFile);

    if (result.status === "success" && result.data) {
      RepairContractEditor.populateForm(result.data);
      showToast(result.message || "Gemini AI đã phân tích thành công và điền vào biểu mẫu sửa chữa!", "success");
      switchTab("tabRepairProducts");

      // Auto export if checked
      const autoExportChk = document.getElementById("chkRepairAutoExportWord");
      if (autoExportChk && autoExportChk.checked) {
        try {
          const exportDirInput = document.getElementById("txtRepairExportDirectory");
          const customExportDir = (exportDirInput ? exportDirInput.value.trim() : "") || "E:\\Working\\Ho So Du An\\Hop Dong\\";
          const contractData = RepairContractEditor.collectFormData();
          contractData.custom_output_dir = customExportDir;

          setLoading(true, `AI đã bóc tách xong! Đang tự động xuất file Word vào "${customExportDir}"...`);
          const docxResult = await ApiClient.generateRepairDocx(contractData);
          if (docxResult && docxResult.status === "success") {
            showRepairAutoExportSuccess(docxResult);
            showToast(`Đã tự động xuất file Word hợp đồng sửa chữa: ${docxResult.file_name}`, "success");
          }
        } catch (exportErr) {
          console.warn("Auto export docx error:", exportErr);
        }
      }
    } else {
      showToast(result.message || "Phân tích thất bại.", "error");
    }
  } catch (err) {
    console.error("AI Repair Parse Error:", err);
    showToast(`Lỗi: ${err.message}`, "error");
  } finally {
    setLoading(false);
  }
}

function showRepairAutoExportSuccess(docxResult) {
  const banner = document.getElementById("aiRepairAutoExportBanner");
  if (!banner) return;
  const fileNameElem = document.getElementById("autoRepairExportFileName");
  const filePathElem = document.getElementById("autoRepairExportFilePath");
  const downloadBtn = document.getElementById("btnRepairAutoExportDownload");

  if (fileNameElem) fileNameElem.textContent = docxResult.file_name;
  if (filePathElem) filePathElem.textContent = docxResult.file_path || docxResult.file_name;
  if (downloadBtn && docxResult.download_url) downloadBtn.href = docxResult.download_url;

  banner.style.display = "block";
}

async function handleGenerateRepairDocx() {
  const data = RepairContractEditor.collectFormData();
  try {
    setLoading(true, "Đang xuất file Word (.docx) Hợp đồng sửa chữa song ngữ...");
    const res = await ApiClient.generateRepairDocx(data);
    if (res && res.status === "success") {
      showToast("Đã xuất file Word Hợp đồng sửa chữa thành công!", "success");
      showRepairAutoExportSuccess(res);
      // Trigger instant download
      if (res.download_url) {
        const link = document.createElement("a");
        link.href = res.download_url;
        link.download = res.file_name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    }
  } catch (e) {
    showToast(`Lỗi xuất file Word: ${e.message}`, "error");
  } finally {
    setLoading(false);
  }
}

async function handleSaveRepairContract() {
  const data = RepairContractEditor.collectFormData();
  try {
    setLoading(true, "Đang lưu hợp đồng sửa chữa vào hồ sơ hệ thống...");
    const res = await ApiClient.saveRepairContract(data);
    if (res && res.status === "success") {
      showToast(res.message || "Đã lưu hợp đồng sửa chữa thành công!", "success");
      RepairContractEditor.loadRepairContractsList();
      if (res.docx_info) {
        showRepairAutoExportSuccess(res.docx_info);
      }
    }
  } catch (e) {
    showToast(`Lỗi lưu hợp đồng: ${e.message}`, "error");
  } finally {
    setLoading(false);
  }
}

function handleCopyRichTextRepair() {
  const data = RepairContractEditor.collectFormData();
  let text = `HỢP ĐỒNG DỊCH VỤ SỬA CHỮA VÀ BẢO TRÌ THIẾT BỊ / 設備維修保養服務合約\nSố / 合約編號: ${data.so_hop_dong}\n`;
  text += `BÊN A: ${data.ben_a.ten_cong_ty} (${data.ben_a.ten_tieng_trung}) - MST: ${data.ben_a.mst}\n`;
  text += `TỔNG CHI PHÍ: ${data.tong_tien_hop_dong_so} VND\n\nDANH MỤC THIẾT BỊ SỬA CHỮA:\n`;

  data.hang_muc.forEach((it, idx) => {
    text += `${idx + 1}. ${it.ten_thiet_bi} | Model/SN: ${it.model_serial || '-'} | Lỗi: ${it.noi_dung_sua_chua || '-'} | SL: ${it.so_luong} | Thành tiền: ${it.tong_gia}\n`;
  });

  navigator.clipboard.writeText(text).then(() => {
    showToast("Đã sao chép nội dung Hợp đồng sửa chữa vào Clipboard!", "success");
  }).catch(() => {
    showToast("Không thể sao chép văn bản.", "error");
  });
}

function handlePrintRepair() {
  window.print();
}

function loadSampleRepairText() {
  const promptInput = document.getElementById("aiRepairPromptInput");
  if (!promptInput) return;
  promptInput.value = `Khách hàng Bên A: CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN) - 越南CX科技股份有限公司
Địa chỉ: Lô K1, Khu chế xuất Tân Thuận, Phường Tân Thuận Đông, Quận 7, TP.HCM
Mã số thuế: 0301789999, Đại diện: CHEN CHEN-YEN (TỔNG GIÁM ĐỐC)
Số hợp đồng: HDSC-20261019-001, ngày 19/10/2026

Danh sách thiết bị giao sửa chữa:
1. Máy tính công nghiệp IPC Advantech IPC-610H (SN: CX-IPC-202401)
Hiện tượng: Không kích nguồn, chập nguồn tổ ong chính
Nội dung sửa chữa: Thay thế bộ nguồn ATX 400W công nghiệp và vệ sinh quạt tản nhiệt
Số lượng: 2 Bộ, Đơn giá: 6.800.000 VND, Thành tiền: 13.600.000 VND

2. Bo mạch điều khiển máy dập I/O Gateway RS-485 (Vị trí: Máy dập #03 & #05)
Hiện tượng: Bị cháy IC giao tiếp RS-485 và tụ lọc đầu vào
Nội dung sửa chữa: Thay chip IC MAX485, thay dàn tụ lọc 24VDC và nạp lại firmware
Số lượng: 3 Cái, Đơn giá: 4.500.000 VND, Thành tiền: 13.500.000 VND

Tổng chi phí sửa chữa: 27.100.000 VND
Thời gian hoàn thành: 10 ngày làm việc. Bảo hành sau sửa chữa: 6 tháng.
Tiến độ thanh toán: Tạm ứng 50% ngay sau khi ký hợp đồng, 50% còn lại sau khi sửa xong và ký biên bản nghiệm thu (T/T 30 ngày).`;
  showToast("Đã nạp mẫu báo giá sửa chữa CX Technology vào ô nhập!", "info");
}

document.addEventListener("DOMContentLoaded", () => {
  RepairContractEditor.init();
});
