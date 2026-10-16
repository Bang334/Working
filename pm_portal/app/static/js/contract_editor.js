/**
 * Contract Form & Table Editor
 */

const ContractEditor = {
  /**
   * Helper to parse string number to integer
   */
  parseNumber(str) {
    if (typeof str === "number") return str;
    const digits = String(str || "").replace(/[^\d]/g, "");
    return digits ? parseInt(digits, 10) : 0;
  },

  /**
   * Format number to VND string
   */
  formatVND(num) {
    return this.parseNumber(num).toLocaleString("vi-VN") + " VND";
  },

  escapeHTML(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  },

  /**
   * Add a new item row to the products table
   */
  addRow(item = null) {
    const tbody = document.getElementById("itemsTableBody");
    if (!tbody) return;

    const rowCount = tbody.querySelectorAll("tr").length + 1;
    const tr = document.createElement("tr");

    const stt = item?.stt || rowCount;
    const name = item?.ten_san_pham || "";
    const price = item?.don_gia || "";
    const qty = item?.so_luong || "1 SET";
    const total = item?.tong_gia || "";

    tr.innerHTML = `
      <td class="text-center" style="width: 45px;">
        <span class="row-stt font-bold">${stt}</span>
      </td>
      <td>
        <textarea class="table-input item-name-input" rows="2" placeholder="Tên sản phẩm song ngữ">${name}</textarea>
      </td>
      <td style="width: 140px;">
        <input type="text" class="table-input item-price-input" value="${price}" placeholder="Nhập đơn giá" oninput="ContractEditor.recalculateRow(this)">
      </td>
      <td style="width: 90px;">
        <input type="text" class="table-input item-qty-input" value="${qty}" placeholder="1 SET" oninput="ContractEditor.recalculateRow(this)">
      </td>
      <td style="width: 150px;">
        <input type="text" class="table-input item-total-input font-semibold" value="${total}" placeholder="Thành tiền" oninput="ContractEditor.recalculateAllTotals()">
      </td>
      <td style="width: 40px;" class="text-center">
        <button type="button" class="btn-icon-del" onclick="ContractEditor.removeRow(this)" title="Xóa dòng" aria-label="Xóa dòng">×</button>
      </td>
    `;

    tbody.appendChild(tr);
    this.recalculateAllTotals();
  },

  /**
   * Remove a row from the table
   */
  removeRow(btn) {
    const row = btn.closest("tr");
    const tbody = row.parentElement;
    row.remove();
    // Re-index STT
    tbody.querySelectorAll("tr").forEach((tr, idx) => {
      const sttSpan = tr.querySelector(".row-stt");
      if (sttSpan) sttSpan.textContent = idx + 1;
    });
    this.recalculateAllTotals();
  },

  /**
   * Recalculate row total when price or quantity changes
   */
  recalculateRow(input) {
    const tr = input.closest("tr");
    const priceInput = tr.querySelector(".item-price-input");
    const qtyInput = tr.querySelector(".item-qty-input");
    const totalInput = tr.querySelector(".item-total-input");

    const price = this.parseNumber(priceInput.value);
    const qty = this.parseNumber(qtyInput.value) || 1;

    if (price > 0) {
      const rowTotal = price * qty;
      totalInput.value = this.formatVND(rowTotal);
    }
    this.recalculateAllTotals();
  },

  /**
   * Recalculate total table amount & total quantity
   */
  recalculateAllTotals() {
    const tbody = document.getElementById("itemsTableBody");
    if (!tbody) return;

    let totalSum = 0;
    let totalQty = 0;

    tbody.querySelectorAll("tr").forEach(tr => {
      const totalInput = tr.querySelector(".item-total-input");
      const qtyInput = tr.querySelector(".item-qty-input");

      const rowTotal = this.parseNumber(totalInput?.value);
      const rowQty = this.parseNumber(qtyInput?.value) || 1;

      totalSum += rowTotal;
      totalQty += rowQty;
    });

    const displayTotal = totalSum.toLocaleString("vi-VN");
    const totalInput = document.getElementById("fieldTotalAmount");
    if (totalInput) totalInput.value = displayTotal;

    const totalQtySpan = document.getElementById("summaryQtyDisplay");
    if (totalQtySpan) totalQtySpan.textContent = `${totalQty} SET`;

    const totalSumSpan = document.getElementById("summaryTotalDisplay");
    if (totalSumSpan) totalSumSpan.textContent = `${displayTotal} VND`;

    this.updatePaymentSummary(totalSum);
  },

  addInstallment(item = null) {
    const container = document.getElementById("paymentInstallmentsEditor");
    if (!container) return;
    if (container.querySelectorAll(".payment-installment-row").length >= 4) return;

    const index = container.querySelectorAll(".payment-installment-row").length + 1;
    const row = document.createElement("div");
    row.className = "payment-installment-row";
    row.style.cssText = "padding: 1rem; margin-bottom: 0.75rem; background: #fff; border: 1px solid #dbe3ee; border-radius: 8px;";
    row.innerHTML = `
      <div style="display:grid;grid-template-columns:110px 130px 1fr 38px;gap:0.75rem;align-items:end;">
        <div class="form-group">
          <label class="form-label installment-title">第${index}期 / Đợt ${index}</label>
          <input type="number" min="0.01" max="100" step="0.01" class="form-control installment-percent" value="${this.escapeHTML(item?.phan_tram ?? "")}" oninput="ContractEditor.onInstallmentsChanged()">
        </div>
        <div class="form-group">
          <label class="form-label">T/T 天數 / Số ngày</label>
          <input type="number" min="0" step="1" class="form-control installment-days" value="${this.escapeHTML(item?.thoi_han_tt_ngay ?? "")}" placeholder="T/T (ngày)">
        </div>
        <div class="form-group">
          <label class="form-label">用途 / 付款條件（繁體中文 - Ưu tiên sếp đọc）</label>
          <textarea rows="2" class="form-control installment-condition-zh" placeholder="雙方簽約後即期以電匯（T/T）方式支付">${this.escapeHTML(item?.dieu_kien_trung ?? "")}</textarea>
        </div>
        <button type="button" class="btn-icon-del" style="margin-bottom:0.45rem" onclick="ContractEditor.removeInstallment(this)" title="Xóa đợt">×</button>
      </div>
      <div class="form-group" style="margin-top:0.65rem;">
        <label class="form-label">Mục đích / Điều kiện giải ngân (Tiếng Việt)</label>
        <textarea rows="2" class="form-control installment-condition-vi" placeholder="Thanh toán tạm ứng ngay sau khi hai bên ký kết hợp đồng">${this.escapeHTML(item?.dieu_kien_viet ?? "")}</textarea>
      </div>`;
    container.appendChild(row);
    this.onInstallmentsChanged();
  },

  removeInstallment(button) {
    const container = document.getElementById("paymentInstallmentsEditor");
    if (!container || container.querySelectorAll(".payment-installment-row").length <= 1) return;
    button.closest(".payment-installment-row")?.remove();
    this.reindexInstallments();
    this.onInstallmentsChanged();
  },

  reindexInstallments() {
    document.querySelectorAll("#paymentInstallmentsEditor .payment-installment-row").forEach((row, index) => {
      const label = row.querySelector(".installment-title");
      if (label) label.textContent = `第${index + 1}期 / Đợt ${index + 1}`;
    });
  },

  renderInstallments(items) {
    const container = document.getElementById("paymentInstallmentsEditor");
    if (!container) return;
    container.innerHTML = "";
    const rows = Array.isArray(items) && items.length ? items : [
      { phan_tram: 35, tieu_de_trung: "簽約定金", dieu_kien_trung: "雙方簽約後即期以電匯 (T/T) 方式支付", dieu_kien_viet: "Thanh toán tạm ứng 35% ngay sau khi hai bên ký kết hợp đồng" },
      { phan_tram: 55, tieu_de_trung: "設備安裝款", dieu_kien_trung: "於設備安裝及系統建置完成並經雙方簽署確認文件後", dieu_kien_viet: "Sau khi bàn giao thiết bị và hoàn thành cài đặt hệ thống" },
      { phan_tram: 10, tieu_de_trung: "驗收尾款", dieu_kien_trung: "於最終驗收 (FAC) 完成並簽署驗收交付文件後", dieu_kien_viet: "Sau khi khách hàng nghiệm thu hoàn tất và ký biên bản bàn giao (FAC)" }
    ];
    rows.slice(0, 4).forEach(item => this.addInstallment(item));
    this.onInstallmentsChanged();
  },

  collectInstallments() {
    const rows = Array.from(document.querySelectorAll("#paymentInstallmentsEditor .payment-installment-row"));
    const totalCount = rows.length;
    return rows.map((row, index) => {
      const daysRaw = row.querySelector(".installment-days")?.value.trim() || "";
      const dotNum = index + 1;
      const pct = parseFloat(row.querySelector(".installment-percent")?.value || "0");
      const zhCond = row.querySelector(".installment-condition-zh")?.value.trim() || "";
      const viCond = row.querySelector(".installment-condition-vi")?.value.trim() || "";

      let tieuDeCn = row.dataset.tieuDeTrung || "";
      let tieuDeVn = row.dataset.tieuDe || "";

      if (!tieuDeCn) {
        const combined = (zhCond + " " + viCond).toLowerCase();
        if (combined.includes("佈線") || combined.includes("kéo dây") || combined.includes("kéo cáp") || combined.includes("hạ tầng")) {
          tieuDeCn = "佈線工程款";
        } else if (combined.includes("安裝") || combined.includes("lắp đặt") || combined.includes("調測") || combined.includes("cài đặt")) {
          tieuDeCn = "設備安裝款";
        } else if (combined.includes("驗收") || combined.includes("nghiệm thu") || combined.includes("fac")) {
          tieuDeCn = "驗收尾款";
        } else if (combined.includes("簽約") || combined.includes("ký hợp đồng") || combined.includes("tạm ứng")) {
          tieuDeCn = "簽約定金";
        } else if (dotNum === 1) {
          tieuDeCn = "簽約定金";
        } else if (dotNum === totalCount) {
          tieuDeCn = "驗收尾款";
        } else if (totalCount === 4 && dotNum === 2) {
          tieuDeCn = "佈線工程款";
        } else if (totalCount === 4 && dotNum === 3) {
          tieuDeCn = "設備安裝款";
        } else if (totalCount === 3 && dotNum === 2) {
          tieuDeCn = "設備安裝款";
        } else {
          tieuDeCn = `第 ${dotNum} 期款`;
        }
      }

      if (!tieuDeVn) {
        if (tieuDeCn === "簽約定金") {
          tieuDeVn = `Đợt ${dotNum} (Tạm ứng ${pct}%)`;
        } else if (tieuDeCn === "佈線工程款") {
          tieuDeVn = `Đợt ${dotNum} (${pct}% Thi công kéo dây/hạ tầng)`;
        } else if (tieuDeCn === "設備安裝款") {
          tieuDeVn = `Đợt ${dotNum} (${pct}% Lắp đặt thiết bị)`;
        } else if (tieuDeCn === "驗收尾款") {
          tieuDeVn = `Đợt ${dotNum} (${pct}% Nghiệm thu cuối cùng)`;
        } else {
          tieuDeVn = `Đợt ${dotNum} (${pct}%)`;
        }
      }

      return {
        dot: dotNum,
        phan_tram: pct,
        thoi_han_tt_ngay: daysRaw === "" ? null : parseInt(daysRaw, 10),
        tieu_de_trung: tieuDeCn,
        tieu_de: tieuDeVn,
        dieu_kien_trung: zhCond,
        dieu_kien_viet: viCond
      };
    });
  },

  onInstallmentsChanged() {
    const installments = this.collectInstallments();
    const totalPercent = installments.reduce((sum, item) => sum + (Number(item.phan_tram) || 0), 0);
    const totalLabel = document.getElementById("paymentPercentTotal");
    if (totalLabel) {
      totalLabel.textContent = `Tổng: ${totalPercent.toLocaleString("vi-VN")}%`;
      totalLabel.style.color = Math.abs(totalPercent - 100) < 0.001 ? "#047857" : "#b91c1c";
    }
    const total = this.parseNumber(document.getElementById("summaryTotalDisplay")?.textContent || 0);
    this.updatePaymentSummary(total);
  },

  updatePaymentSummary(total) {
    const installments = this.collectInstallments();
    if (!installments.length) return;
    const first = installments[0];
    const last = installments[installments.length - 1];
    const firstLabel = document.getElementById("summaryPhase1Label");
    const lastLabel = document.getElementById("summaryPhaseLastLabel");
    const firstValue = document.getElementById("summaryPhase1Display");
    const lastValue = document.getElementById("summaryPhaseLastDisplay");
    if (firstLabel) firstLabel.textContent = `Thanh Toán Đợt 1 (${first.phan_tram || 0}%)`;
    if (lastLabel) lastLabel.textContent = `Thanh Toán Đợt Cuối (${last.phan_tram || 0}%)`;
    if (firstValue) firstValue.textContent = this.formatVND(Math.round(total * (first.phan_tram || 0) / 100));
    if (lastValue) lastValue.textContent = this.formatVND(Math.round(total * (last.phan_tram || 0) / 100));
  },

  /**
   * Populate form inputs with contract data object
   */
  populateForm(data) {
    if (!data) return;

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) {
        el.value = String(val);
      }
    };

    // Header fields
    setVal("fieldContractNo", data.so_hop_dong || "");
    setVal("fieldDay", data.ngay_ky || "");
    setVal("fieldMonth", data.thang_ky || "");
    setVal("fieldYear", data.nam_ky || "");

    // Party A
    const benA = data.ben_a || {};
    setVal("fieldCompanyA", benA.ten_cong_ty || "");
    setVal("fieldCompanyACn", benA.ten_tieng_trung || "");
    setVal("fieldAddressA", benA.dia_chi || "");
    setVal("fieldAddressACn", benA.dia_chi_trung || "");
    setVal("fieldTaxA", benA.mst || "");
    setVal("fieldRepA", benA.nguoi_dai_dien || "");

    let roleVi = (benA.chuc_vu || "TỔNG GIÁM ĐỐC").trim();
    // Loại bỏ chữ Hán và chuẩn hóa in hoa theo quy chuẩn hợp đồng
    roleVi = roleVi.replace(/\s*\/\s*[\u4e00-\u9fff\s]+.*$/g, "").replace(/[\u4e00-\u9fff]+/g, "").trim().toUpperCase();
    if (!roleVi) roleVi = "TỔNG GIÁM ĐỐC";
    const roleCn = benA.chuc_vu_trung || "總經理";
    setVal("fieldRoleA", roleVi);
    setVal("fieldRoleACn", roleCn);

    // Project
    const duAn = data.du_an || {};
    setVal("fieldProjectVn", duAn.ten_du_an_viet || "");
    setVal("fieldProjectCn", duAn.ten_du_an_trung || "");

    // Terms
    setVal("fieldDeliveryDays", data.thoi_gian_giao_hang_ngay || 80);
    setVal("fieldWarrantyMonths", data.thoi_gian_bao_hanh_thang || 12);
    this.renderInstallments(data.phan_bo_thanh_toan || []);

    // Line items
    const tbody = document.getElementById("itemsTableBody");
    if (tbody && Array.isArray(data.hang_muc) && data.hang_muc.length > 0) {
      tbody.innerHTML = "";
      data.hang_muc.forEach(item => this.addRow(item));
    }

    // Set Total Amount if present (prioritize stated/discounted total)
    if (data.tong_tien_hop_dong_so) {
      setVal("fieldTotalAmount", data.tong_tien_hop_dong_so);
    }

    this.recalculateAllTotals();
  },

  /**
   * Collect all form inputs into a structured ContractData object
   */
  collectFormData() {
    const tbody = document.getElementById("itemsTableBody");
    const items = [];

    if (tbody) {
      tbody.querySelectorAll("tr").forEach((tr, index) => {
        items.push({
          stt: index + 1,
          ten_san_pham: tr.querySelector(".item-name-input")?.value.trim() || "",
          don_gia: tr.querySelector(".item-price-input")?.value.trim() || "",
          so_luong: tr.querySelector(".item-qty-input")?.value.trim() || "1 SET",
          tong_gia: tr.querySelector(".item-total-input")?.value.trim() || ""
        });
      });
    }

    const totalRaw = document.getElementById("fieldTotalAmount")?.value || "";

    return {
      so_hop_dong: document.getElementById("fieldContractNo")?.value.trim() || "",
      ngay_ky: document.getElementById("fieldDay")?.value.trim() || "",
      thang_ky: document.getElementById("fieldMonth")?.value.trim() || "",
      nam_ky: document.getElementById("fieldYear")?.value.trim() || "",
      ben_a: {
        ten_cong_ty: document.getElementById("fieldCompanyA")?.value.trim() || "",
        ten_tieng_trung: document.getElementById("fieldCompanyACn")?.value.trim() || "",
        dia_chi: document.getElementById("fieldAddressA")?.value.trim() || "",
        dia_chi_trung: document.getElementById("fieldAddressACn")?.value.trim() || "",
        mst: document.getElementById("fieldTaxA")?.value.trim() || "",
        nguoi_dai_dien: document.getElementById("fieldRepA")?.value.trim() || "",
        chuc_vu: (document.getElementById("fieldRoleA")?.value.trim() || "TỔNG GIÁM ĐỐC").replace(/\s*\/\s*[\u4e00-\u9fff\s]+.*$/g, "").replace(/[\u4e00-\u9fff]+/g, "").trim().toUpperCase() || "TỔNG GIÁM ĐỐC",
        chuc_vu_trung: document.getElementById("fieldRoleACn")?.value.trim() || "總經理"
      },
      ben_b: {
        ten_cong_ty: "CÔNG TY TNHH TOÀN CẦU HONG MING",
        ten_tieng_trung: "宏明環球有限公司",
        dia_chi: "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
        dia_chi_trung: "越南胡志明市西貢坊阮惠路68號2樓",
        mst: "0318280158",
        nguoi_dai_dien: "TANG WEI LI",
        chuc_vu: "TỔNG GIÁM ĐỐC",
        chuc_vu_trung: "總經理"
      },
      du_an: {
        ten_du_an_viet: document.getElementById("fieldProjectVn")?.value.trim() || "",
        ten_du_an_trung: document.getElementById("fieldProjectCn")?.value.trim() || ""
      },
      hang_muc: items,
      tong_so_luong: document.getElementById("summaryQtyDisplay")?.textContent.trim() || "0 SET",
      tong_tien_truoc_giam: totalRaw ? `${totalRaw} VND` : "",
      tong_tien_sau_giam: totalRaw ? `${totalRaw} VND` : "",
      tong_tien_hop_dong_so: totalRaw,
      thoi_gian_giao_hang_ngay: parseInt(document.getElementById("fieldDeliveryDays")?.value, 10) || 80,
      thoi_gian_bao_hanh_thang: parseInt(document.getElementById("fieldWarrantyMonths")?.value, 10) || 12,
      phan_bo_thanh_toan: this.collectInstallments()
    };
  },

  /**
   * Cache for contract list loaded from API
   */
  contractsCache: [],

  /**
   * Load list of all created contracts from backend API
   */
  async loadContractsList() {
    const tbody = document.getElementById("contractsListTableBody");
    const emptyState = document.getElementById("contractListEmptyState");
    const headerCount = document.getElementById("headerContractCount");
    const tabBadge = document.getElementById("contractListBadge");
    const listCountBadge = document.getElementById("contractListCountBadge");
    const statContracts = document.getElementById("statTotalContracts");
    const statAmount = document.getElementById("statTotalAmount");
    const statWordFiles = document.getElementById("statTotalWordFiles");

    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:2rem;color:#64748b;">⏳ Đang tải danh sách hợp đồng...</td></tr>`;
    }

    try {
      const res = await fetch("/api/v1/contracts/list");
      const result = await res.json();

      if (result.status === "success" && Array.isArray(result.data)) {
        this.contractsCache = result.data;
        const total = result.data.length;

        // Update counts
        if (headerCount) headerCount.textContent = total;
        if (tabBadge) tabBadge.textContent = total;
        if (listCountBadge) listCountBadge.textContent = `${total} hợp đồng`;
        if (statContracts) statContracts.textContent = total;

        // Compute KPIs
        let sumAmount = 0;
        let wordFileCount = 0;
        result.data.forEach(item => {
          sumAmount += Number(item.total_amount || 0);
          if (item.file_name) wordFileCount++;
        });

        if (statAmount) statAmount.textContent = `${sumAmount.toLocaleString("vi-VN")} VND`;
        if (statWordFiles) statWordFiles.textContent = `${wordFileCount} tệp`;

        this.renderContractsTable(this.contractsCache);
      } else {
        if (tbody) {
          tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:1.5rem;color:#dc2626;">Lỗi tải dữ liệu: ${this.escapeHTML(result.message || "Không xác định")}</td></tr>`;
        }
      }
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:1.5rem;color:#dc2626;">Không thể kết nối đến máy chủ: ${this.escapeHTML(err.message)}</td></tr>`;
      }
    }
  },

  /**
   * Filter contracts in real-time by search query
   */
  filterContracts(query) {
    const q = (query || "").trim().toLowerCase();
    if (!q) {
      this.renderContractsTable(this.contractsCache);
      return;
    }

    const filtered = this.contractsCache.filter(item => {
      const code = (item.contract_code || "").toLowerCase();
      const custVi = (item.customer_name_vi || "").toLowerCase();
      const custZh = (item.customer_name_zh || "").toLowerCase();
      const projVi = (item.project_name_vi || "").toLowerCase();
      const fileName = (item.file_name || "").toLowerCase();
      const status = (item.status || "").toLowerCase();
      return code.includes(q) || custVi.includes(q) || custZh.includes(q) || projVi.includes(q) || fileName.includes(q) || status.includes(q);
    });

    this.renderContractsTable(filtered);
  },

  /**
   * Render table rows from contracts array
   */
  renderContractsTable(contracts) {
    const tbody = document.getElementById("contractsListTableBody");
    const emptyState = document.getElementById("contractListEmptyState");
    if (!tbody) return;

    if (!contracts || contracts.length === 0) {
      tbody.innerHTML = "";
      if (emptyState) emptyState.style.display = "block";
      return;
    }

    if (emptyState) emptyState.style.display = "none";

    tbody.innerHTML = contracts.map((c, index) => {
      const stt = index + 1;
      const code = this.escapeHTML(c.contract_code || "HỢP ĐỒNG");
      const signedDate = this.escapeHTML(c.signed_date || "");
      const custVi = this.escapeHTML(c.customer_name_vi || "Chưa đặt tên");
      const custZh = this.escapeHTML(c.customer_name_zh || "");
      const projVi = this.escapeHTML(c.project_name_vi || "Hợp đồng mua bán");
      const projZh = this.escapeHTML(c.project_name_zh || "");
      const amountNum = Number(c.total_amount || 0);
      const amountStr = amountNum > 0 ? `${amountNum.toLocaleString("vi-VN")} VND` : "<span style='color:#94a3b8;'>Chưa xác định</span>";
      
      const fileName = this.escapeHTML(c.file_name || "");
      const filePath = this.escapeHTML(c.file_path || "");
      const fileMtime = this.escapeHTML(c.file_mtime || "");
      const fileSizeKb = c.file_size ? `${Math.round(c.file_size / 1024)} KB` : "";

      const statusText = this.escapeHTML(c.status || "Đang thực hiện");
      let statusBadgeClass = "gray";
      if (statusText.includes("nghiệm thu") || statusText.includes("Đang")) {
        statusBadgeClass = "blue";
      } else if (statusText.includes("Chờ") || statusText.includes("hạn")) {
        statusBadgeClass = "yellow";
      } else if (statusText.includes("Xuất file") || statusText.includes("Hoàn tất")) {
        statusBadgeClass = "green";
      }

      // Action buttons
      const detailBtn = `
        <button type="button" class="btn btn-outline btn-xs" onclick="ContractEditor.openContractDossierModal('${this.escapeHTML(c.contract_code || c.id)}')" style="padding: 4px 10px; font-size: 0.78rem; font-weight: 700; color: #1d4ed8; border-color: #93c5fd; background: #eff6ff; display: inline-flex; align-items: center; gap: 4px;" title="Xem chi tiết toàn bộ hồ sơ (Hợp đồng, Đề nghị TT, Nghiệm thu...)">
          <span>👁️ Chi Tiết</span>
        </button>
      `;

      let openFolderBtn = "";
      if (filePath) {
        openFolderBtn = `
          <button type="button" class="btn btn-outline btn-xs" onclick="handleOpenSystemPath('${filePath.replace(/\\/g, "\\\\")}')" style="padding: 4px 8px; font-size: 0.75rem; color: #0369a1; border-color: #7dd3fc; background: #f0f9ff;" title="Mở thư mục chứa file trong Explorer">
            📂 Mở
          </button>
        `;
      }

      const deleteBtn = `
        <button type="button" class="btn btn-outline btn-xs" onclick="ContractEditor.deleteContract('${this.escapeHTML(c.id || '')}', '${this.escapeHTML(c.contract_code || fileName)}')" style="padding: 4px 8px; font-size: 0.75rem; color: #dc2626; border-color: #fca5a5; background: #fff;" title="Xóa hợp đồng">
          🗑️
        </button>
      `;

      return `
        <tr>
          <td style="text-align: center; font-weight: 700; color: #64748b; font-size: 0.85rem;">${stt}</td>
          <td>
            <div style="font-family: monospace; font-weight: 700; color: #1d4ed8; font-size: 0.88rem;">${code}</div>
            ${signedDate ? `<div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">📅 ${signedDate}</div>` : ""}
          </td>
          <td>
            <div style="font-weight: 700; color: #0f172a; font-size: 0.88rem; line-height: 1.3;">${custVi}</div>
            ${custZh ? `<div style="font-size: 0.78rem; color: #64748b; margin-top: 2px;">${custZh}</div>` : ""}
          </td>
          <td>
            <div style="font-size: 0.84rem; color: #1e293b; line-height: 1.3;">${projVi}</div>
            ${projZh ? `<div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">${projZh}</div>` : ""}
          </td>
          <td style="text-align: right;">
            <div style="font-weight: 800; color: #15803d; font-size: 0.9rem;">${amountStr}</div>
          </td>
          <td>
            ${fileName ? `
              <div style="font-size: 0.8rem; font-weight: 600; color: #0284c7; word-break: break-all; display: flex; align-items: center; gap: 4px;">
                <span style="color: #2563eb;">📄</span>
                <span title="${fileName}">${fileName.length > 32 ? fileName.substring(0, 30) + '...' : fileName}</span>
              </div>
              <div style="font-size: 0.72rem; color: #64748b; margin-top: 2px;">
                ${fileSizeKb ? `<span>${fileSizeKb}</span>` : ""}
                ${fileMtime ? ` · <span>${fileMtime}</span>` : ""}
              </div>
            ` : `<span style="font-size: 0.78rem; color: #94a3b8; font-style: italic;">Chưa xuất Word</span>`}
          </td>
          <td style="text-align: center;">
            <span class="badge-pill ${statusBadgeClass}" style="font-size: 0.72rem; padding: 2px 7px;">${statusText}</span>
          </td>
          <td style="text-align: center;">
            <div style="display: inline-flex; align-items: center; gap: 6px; justify-content: center; flex-wrap: nowrap;">
              ${detailBtn}
              ${openFolderBtn}
              ${deleteBtn}
            </div>
          </td>
        </tr>
      `;
    }).join("");
  },

  /**
   * Load a contract detail and populate into the editor form
   */
  async loadContractToForm(contractCodeOrId) {
    if (!contractCodeOrId) return;

    try {
      showLoading("Đang nạp dữ liệu hợp đồng vào bảng soạn thảo...");
      const res = await fetch(`/api/v1/contracts/detail/${encodeURIComponent(contractCodeOrId)}`);
      const result = await res.json();

      if (result.status === "success" && result.data) {
        this.populateForm(result.data);
        switchTab("tabProducts");
        showToast(`Đã nạp thông tin Hợp đồng ${result.data.so_hop_dong || ""} vào giao diện!`, "success");
      } else {
        showToast(result.message || "Không thể tải chi tiết hợp đồng.", "error");
      }
    } catch (err) {
      showToast(`Lỗi nạp hợp đồng: ${err.message}`, "error");
    } finally {
      hideLoading();
    }
  },

  /**
   * Delete a contract record after confirmation
   */
  async deleteContract(id, contractCode) {
    const target = id || contractCode;
    if (!target) return;

    const ok = confirm(`Bạn có chắc chắn muốn xóa hợp đồng "${contractCode || id}" khỏi hệ thống không?\n\nThao tác này sẽ xóa hồ sơ và các đợt thanh toán liên quan.`);
    if (!ok) return;

    try {
      showLoading("Đang xóa hợp đồng...");
      const res = await fetch(`/api/v1/contracts/${encodeURIComponent(target)}`, {
        method: "DELETE"
      });
      const result = await res.json();

      if (result.status === "success") {
        showToast(result.message || "Đã xóa hợp đồng thành công!", "success");
        await this.loadContractsList();
      } else {
        showToast(result.message || "Không thể xóa hợp đồng.", "error");
      }
    } catch (err) {
      showToast(`Lỗi xóa hợp đồng: ${err.message}`, "error");
    } finally {
      hideLoading();
    }
  },

  /**
   * Lọc toàn bộ tên sản phẩm từ bảng để đưa cho AI khái quát hóa tên dự án ngắn gọn (Hệ thống..., Hạ tầng...)
   */
  async autoSummarizeProjectFromItems() {
    const tbody = document.getElementById("itemsTableBody");
    if (!tbody) return;
    const names = Array.from(tbody.querySelectorAll(".item-name-input"))
      .map(el => el.value.trim())
      .filter(Boolean);

    if (!names.length) {
      if (window.showToast) {
        window.showToast("Vui lòng nhập ít nhất 1 sản phẩm trong bảng để AI đặt tên dự án!", "warning");
      } else {
        alert("Vui lòng nhập ít nhất 1 sản phẩm trong bảng để AI đặt tên dự án!");
      }
      return;
    }

    try {
      if (window.showLoading) window.showLoading("AI đang phân tích sản phẩm và khái quát hóa tên dự án...");
      const res = await fetch("/api/v1/contracts/ai-project-title", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_names: names })
      });
      const data = await res.json();
      if (res.ok && data.status === "success" && data.data) {
        if (data.data.ten_du_an_viet) {
          const vEl = document.getElementById("fieldProjectVn");
          if (vEl) vEl.value = data.data.ten_du_an_viet;
        }
        if (data.data.ten_du_an_trung) {
          const cEl = document.getElementById("fieldProjectCn");
          if (cEl) cEl.value = data.data.ten_du_an_trung;
        }
        if (window.showToast) {
          window.showToast(`AI đã tạo tên dự án: "${data.data.ten_du_an_viet}"!`, "success");
        }
      } else {
        if (window.showToast) {
          window.showToast("Không thể tạo tên dự án qua AI.", "error");
        }
      }
    } catch (err) {
      if (window.showToast) {
        window.showToast(`Lỗi AI: ${err.message}`, "error");
      }
    } finally {
      if (window.hideLoading) window.hideLoading();
    }
  },

  /**
   * Mở Modal Hồ Sơ Chi Tiết Hợp Đồng (Hợp đồng, Đề nghị thanh toán, Nghiệm thu...)
   */
  async openContractDossierModal(contractCodeOrId) {
    if (!contractCodeOrId) return;
    const modal = document.getElementById("contractDossierModal");
    if (!modal) return;

    modal.style.display = "flex";
    const bodyContainer = document.getElementById("contractDossierModalBody");
    if (bodyContainer) {
      bodyContainer.innerHTML = `
        <div style="text-align: center; padding: 3rem 1rem; color: #64748b;">
          <div class="spinner" style="margin: 0 auto 1rem; width: 36px; height: 36px; border-width: 3px;"></div>
          <div style="font-weight: 600;">Đang kết nối cơ sở dữ liệu và tải hồ sơ hợp đồng ${this.escapeHTML(contractCodeOrId)}...</div>
        </div>
      `;
    }

    try {
      const res = await fetch(`/api/v1/contracts/${encodeURIComponent(contractCodeOrId)}/dossier`);
      const data = await res.json();

      if (data.status === "success" && data.contract) {
        this.renderDossierModalContent(data);
      } else {
        if (bodyContainer) {
          bodyContainer.innerHTML = `
            <div style="text-align: center; padding: 2.5rem; color: #dc2626;">
              <div style="font-weight: 700; font-size: 1rem;">Không tìm thấy hồ sơ hợp đồng</div>
              <div style="font-size: 0.85rem; margin-top: 0.5rem; color: #64748b;">${this.escapeHTML(data.message || "Lỗi không xác định")}</div>
            </div>
          `;
        }
      }
    } catch (err) {
      if (bodyContainer) {
        bodyContainer.innerHTML = `
          <div style="text-align: center; padding: 2.5rem; color: #dc2626;">
            <div style="font-weight: 700;">Lỗi kết nối máy chủ</div>
            <div style="font-size: 0.85rem; margin-top: 0.5rem; color: #64748b;">${this.escapeHTML(err.message)}</div>
          </div>
        `;
      }
    }
  },

  closeContractDossierModal() {
    const modal = document.getElementById("contractDossierModal");
    if (modal) modal.style.display = "none";
  },

  renderDossierModalContent(data) {
    const bodyContainer = document.getElementById("contractDossierModalBody");
    if (!bodyContainer) return;

    const c = data.contract;
    const ms = data.milestones || [];
    const docs = data.documents || {};
    const contractDocs = docs.contract_docs || [];
    const paymentDocs = docs.payment_docs || [];
    const acceptanceDocs = docs.acceptance_docs || [];
    const otherDocs = docs.other_docs || [];

    const custName = `${this.escapeHTML(c.customer_name_vi)}${c.customer_name_zh ? ` · <span style="font-weight:400;color:#64748b;">${this.escapeHTML(c.customer_name_zh)}</span>` : ""}`;
    const projName = `${this.escapeHTML(c.project_name_vi)}${c.project_name_zh ? ` · <span style="color:#64748b;">${this.escapeHTML(c.project_name_zh)}</span>` : ""}`;

    // Render payment milestones rows
    let milestonesHtml = "";
    if (ms.length > 0) {
      milestonesHtml = `
        <table class="modern-table" style="min-width: 100%; font-size: 0.82rem; margin-top: 0.5rem;">
          <thead>
            <tr>
              <th style="width: 70px; text-align: center;">Đợt</th>
              <th style="width: 70px; text-align: center;">Tỷ Lệ</th>
              <th style="width: 140px; text-align: right;">Số Tiền (VND)</th>
              <th>Điều Kiện Thanh Toán (Trigger Condition)</th>
              <th style="width: 90px; text-align: center;">Hạn T/T</th>
              <th style="width: 110px; text-align: center;">Trạng Thái</th>
            </tr>
          </thead>
          <tbody>
            ${ms.map((m, idx) => `
              <tr>
                <td style="text-align: center; font-weight: 700; color: #1d4ed8;">${this.escapeHTML(m.milestone_name || `Đợt ${idx + 1}`)}</td>
                <td style="text-align: center; font-weight: 700;">${m.percentage}%</td>
                <td style="text-align: right; font-weight: 700; color: #15803d;">${Number(m.amount || 0).toLocaleString("vi-VN")} VND</td>
                <td style="font-size: 0.8rem; color: #334155;">${this.escapeHTML(m.trigger_condition || "Thanh toán theo hợp đồng")}</td>
                <td style="text-align: center; font-size: 0.78rem;">${m.payment_term_days ? `${m.payment_term_days} ngày` : "Tức thì"}</td>
                <td style="text-align: center;">
                  <span class="badge-pill ${m.status === 'PAID' ? 'green' : (m.triggered ? 'yellow' : 'gray')}" style="font-size: 0.7rem; padding: 2px 6px;">
                    ${this.escapeHTML(m.status_label || (m.status === 'PAID' ? 'Đã thu tiền' : (m.triggered ? 'Chờ thanh toán' : 'Chờ điều kiện')))}
                  </span>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    } else {
      milestonesHtml = `<div style="font-size: 0.82rem; color: #94a3b8; font-style: italic; padding: 0.5rem 0;">Chưa thiết lập tiến độ thanh toán chi tiết.</div>`;
    }

    // Helper to render file card
    const renderFileCard = (doc, icon = "📄", color = "#2563eb") => {
      const escapedPath = (doc.file_path || "").replace(/\\/g, "\\\\");
      return `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0.85rem; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 0.45rem; gap: 0.75rem; flex-wrap: wrap;">
          <div style="display: flex; align-items: center; gap: 0.65rem; min-width: 0; flex: 1;">
            <span style="font-size: 1.25rem;">${icon}</span>
            <div style="min-width: 0;">
              <div style="font-weight: 750; font-size: 0.85rem; color: #0f172a; word-break: break-all;" title="${this.escapeHTML(doc.file_name)}">
                ${this.escapeHTML(doc.file_name)}
              </div>
              <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;">
                ${doc.file_size_formatted ? `<span>${doc.file_size_formatted}</span> · ` : ""}${doc.created_at ? `<span>${doc.created_at}</span>` : ""}
                ${doc.exists ? `<span class="badge-pill green" style="font-size: 0.65rem; padding: 1px 5px; margin-left: 6px;">✓ Tệp sẵn sàng</span>` : `<span class="badge-pill gray" style="font-size: 0.65rem; padding: 1px 5px; margin-left: 6px;">Không tìm thấy tệp</span>`}
              </div>
            </div>
          </div>
          <div style="display: flex; gap: 0.4rem; align-items: center; flex-shrink: 0;">
            ${doc.download_url ? `
              <a href="${doc.download_url}" download="${this.escapeHTML(doc.file_name)}" class="btn btn-outline btn-xs" style="padding: 4px 10px; font-size: 0.75rem; font-weight: 600; text-decoration: none; color: #166534; border-color: #86efac; background: #f0fdf4;" title="Tải tệp về máy tính">
                ⬇️ Tải Về
              </a>
            ` : ""}
            ${doc.file_path ? `
              <button type="button" class="btn btn-outline btn-xs" onclick="handleOpenSystemPath('${escapedPath}')" style="padding: 4px 10px; font-size: 0.75rem; font-weight: 600; color: #0369a1; border-color: #7dd3fc; background: #f0f9ff;" title="Mở trực tiếp trên máy tính">
                📂 Mở
              </button>
            ` : ""}
          </div>
        </div>
      `;
    };

    bodyContainer.innerHTML = `
      <!-- Thẻ Thông Tin Tổng Quan Hợp Đồng -->
      <div style="background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%); border: 1px solid #bfdbfe; border-radius: 10px; padding: 1.1rem 1.25rem; margin-bottom: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.75rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.65rem; flex-wrap: wrap;">
              <span style="font-family: monospace; font-size: 1.15rem; font-weight: 800; color: #1d4ed8; background: #dbeafe; padding: 3px 12px; border-radius: 6px; letter-spacing: 0.03em;">
                ${this.escapeHTML(c.contract_code)}
              </span>
              <span class="badge-pill blue" style="font-size: 0.78rem;">${this.escapeHTML(c.status)}</span>
              ${c.signed_date ? `<span style="font-size: 0.8rem; color: #64748b;">📅 Ký ngày: <strong>${this.escapeHTML(c.signed_date)}</strong></span>` : ""}
            </div>
            <div style="margin-top: 0.55rem; font-size: 0.98rem; font-weight: 750; color: #0f172a;">
              🏢 Khách Hàng: ${custName}
            </div>
            <div style="margin-top: 0.25rem; font-size: 0.86rem; color: #334155;">
              📦 Dự Án: ${projName}
            </div>
          </div>

          <div style="text-align: right;">
            <div style="font-size: 0.76rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Tổng Giá Trị Hợp Đồng</div>
            <div style="font-size: 1.35rem; font-weight: 800; color: #15803d; margin-top: 0.15rem;">
              ${this.escapeHTML(c.total_amount_formatted)}
            </div>
            <div style="font-size: 0.76rem; color: #64748b; margin-top: 0.25rem;">
              Kỹ sư phụ trách: <strong>${this.escapeHTML(c.lead_engineer)}</strong>
            </div>
          </div>
        </div>

        <!-- Quick actions inside dossier -->
        <div style="display: flex; gap: 0.65rem; margin-top: 0.95rem; padding-top: 0.75rem; border-top: 1px dashed #cbd5e1; flex-wrap: wrap; align-items: center;">
          <button type="button" class="btn btn-primary btn-sm" onclick="ContractEditor.loadContractToForm('${this.escapeHTML(c.contract_code)}'); ContractEditor.closeContractDossierModal(); switchTab('tabProducts');" style="font-size: 0.8rem; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">
            <span>👁️ Nạp Lại Vào Form Soạn Thảo</span>
          </button>
          <a href="/reminders" class="btn btn-outline btn-sm" style="font-size: 0.8rem; font-weight: 600; text-decoration: none; color: #1e40af; border-color: #93c5fd; background: #ffffff; display: inline-flex; align-items: center; gap: 4px;">
            <span>👉 Sang Quản Lý Đề Nghị TT & Nhắc Nợ</span>
          </a>
        </div>
      </div>

      <!-- Section 1: Tệp Hợp Đồng Word (.docx) -->
      <div style="margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
          <h4 style="margin: 0; font-size: 0.92rem; font-weight: 750; color: #1e293b; display: flex; align-items: center; gap: 6px;">
            <span>📄</span> Hợp Đồng Mua Bán Chính Thức (Word .docx)
          </h4>
          <span style="font-size: 0.75rem; color: #64748b; font-weight: 600;">${contractDocs.length} tệp</span>
        </div>
        ${contractDocs.length > 0 ? contractDocs.map(d => renderFileCard(d, "📄", "#2563eb")).join("") : `
          <div style="font-size: 0.82rem; color: #94a3b8; font-style: italic; padding: 0.75rem; background: #f8fafc; border-radius: 6px; border: 1px dashed #cbd5e1;">
            Chưa có tệp Word hợp đồng nào được lưu.
          </div>
        `}
      </div>

      <!-- Section 2: Tiến Độ & Phiếu Đề Nghị Thanh Toán (Payment Requests) -->
      <div style="margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
          <h4 style="margin: 0; font-size: 0.92rem; font-weight: 750; color: #1e293b; display: flex; align-items: center; gap: 6px;">
            <span>💰</span> Tiến Độ Thanh Toán & Phiếu Đề Nghị TT
          </h4>
          <span style="font-size: 0.75rem; color: #166534; font-weight: 700;">${paymentDocs.length} chứng từ đã tạo</span>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.85rem; margin-bottom: 0.65rem;">
          <div style="font-weight: 700; font-size: 0.82rem; color: #334155;">Tiến Độ Các Đợt Theo Hợp Đồng:</div>
          ${milestonesHtml}
        </div>

        ${paymentDocs.length > 0 ? paymentDocs.map(d => renderFileCard(d, d.file_name.endsWith(".xlsx") ? "📊" : "📄", "#16a34a")).join("") : `
          <div style="font-size: 0.82rem; color: #94a3b8; font-style: italic; padding: 0.75rem; background: #f8fafc; border-radius: 6px; border: 1px dashed #cbd5e1;">
            Chưa có file Đề Nghị Thanh Toán cho hợp đồng này.
          </div>
        `}
      </div>

      <!-- Section 3: Hồ Sơ Biên Bản Nghiệm Thu (Acceptance Handover) -->
      <div style="margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
          <h4 style="margin: 0; font-size: 0.92rem; font-weight: 750; color: #1e293b; display: flex; align-items: center; gap: 6px;">
            <span>📝</span> Biên Bản Nghiệm Thu & Bàn Giao Thiết Bị (Acceptance)
          </h4>
          <span style="font-size: 0.75rem; color: #64748b; font-weight: 600;">${acceptanceDocs.length} biên bản</span>
        </div>
        ${acceptanceDocs.length > 0 ? acceptanceDocs.map(d => renderFileCard(d, "📝", "#0284c7")).join("") : `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; background: #f8fafc; border-radius: 8px; border: 1px dashed #cbd5e1; flex-wrap: wrap; gap: 0.5rem;">
            <div style="font-size: 0.82rem; color: #64748b;">
              Chưa có biên bản nghiệm thu nào khớp mã <strong>${this.escapeHTML(c.contract_code)}</strong>.
            </div>
            <a href="/acceptance" class="btn btn-outline btn-xs" style="text-decoration: none; font-size: 0.75rem; font-weight: 600; color: #0284c7; border-color: #7dd3fc; background: #ffffff;">
              ＋ Lập Biên Bản Nghiệm Thu
            </a>
          </div>
        `}
      </div>

      <!-- Section 4: Các Tài Liệu & Hồ Sơ Khác (nếu có) -->
      ${otherDocs.length > 0 ? `
        <div style="margin-bottom: 1.25rem;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
            <h4 style="margin: 0; font-size: 0.92rem; font-weight: 750; color: #1e293b; display: flex; align-items: center; gap: 6px;">
              <span>📁</span> Chứng Từ & Tài Liệu Liên Quan Khác
            </h4>
            <span style="font-size: 0.75rem; color: #64748b; font-weight: 600;">${otherDocs.length} tệp</span>
          </div>
          ${otherDocs.map(d => renderFileCard(d, "📎", "#64748b")).join("")}
        </div>
      ` : ""}
    `;
  }
};

