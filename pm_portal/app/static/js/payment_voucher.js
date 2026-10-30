/**
 * Payment Voucher Manager (Đơn Xin Thanh Toán - 浤詺付款申请单)
 * Hong Ming Global PM Portal.
 */

const PaymentVoucherApp = {
  state: {
    beneficiary_name: "CONG TY TNHH TO CHUC SU KIEN OMG",
    account_number: "0071000764939",
    bank_name: "Vietcombank CN HCM",
    amount: 42346800,
    currency: "VND",
    exchange_rate: 26000,
    amount_usd: 1628.72,
    amount_in_words_vi: "Bốn mươi hai triệu ba trăm bốn mươi sáu nghìn tám trăm đồng chẵn",
    amount_in_words_zh: "肆仟貳佰參拾肆萬陸仟捌佰元整",
    reason_vi: "Thanh toán đợt 2 (50%) theo hợp đồng số VIMF BD26_HONG MING cho chi phí tham gia Triển lãm Công nghiệp và Sản xuất Việt Nam – Bình Dương 2026 (17–19/06/2026).",
    reason_zh: "依據合約編號 VIMF BD26_HONG MING，支付第2期款項（50%），用於參加「2026年越南工業製造展（平陽）」（2026年06月17日至19日）之相關費用。",
    full_reason: "Thanh toán đợt 2 (50%) theo hợp đồng số VIMF BD26_HONG MING cho chi phí tham gia Triển lãm Công nghiệp và Sản xuất Việt Nam – Bình Dương 2026 (17–19/06/2026).\n依據合約編號 VIMF BD26_HONG MING，支付第2期款項（50%），用於參加「2026年越南工業製造展（平陽）」（2026年06月17日至19日）之相關費用。",
    employee_code: "HVM007",
    report_code: "报单号：HVM007-20261020-1",
    request_date: new Date().toISOString().split("T")[0],
    prepared_by: "NGUYỄN SỸ KIM BẰNG",
    supervisor: "",
    checker: "",
    accountant: "",
    director: "",
    attachment_note: "",
    attachedFile: null,
    beneficiaries: [],
    history: [],
    breakdown_items: []
  },

  init() {
    const savedEmp = localStorage.getItem("pm_employee_code");
    if (savedEmp) {
      this.state.employee_code = savedEmp.toUpperCase();
      const empInput = document.getElementById("inputEmployeeCode");
      if (empInput) empInput.value = this.state.employee_code;
    }
    this.bindEvents();
    this.loadBeneficiaries();
    this.loadHistory();
    this.fetchNextReportCode();
    this.renderBreakdownRows();
    this.updateLivePreview();
  },

  bindEvents() {
    const self = this;

    // Beneficiary Select change
    const benSelect = document.getElementById("selectBeneficiary");
    if (benSelect) {
      benSelect.addEventListener("change", function(e) {
        self.handleBeneficiarySelected(e.target.value);
      });
    }

    // Drag and Drop Zone
    const dropZone = document.getElementById("voucherDropZone");
    const dragOverlay = document.getElementById("voucherDragOverlay");
    if (dropZone && dragOverlay) {
      ["dragenter", "dragover"].forEach(evt => {
        dropZone.addEventListener(evt, e => {
          e.preventDefault();
          e.stopPropagation();
          dragOverlay.style.display = "flex";
        });
      });
      ["dragleave", "drop"].forEach(evt => {
        dropZone.addEventListener(evt, e => {
          e.preventDefault();
          e.stopPropagation();
          dragOverlay.style.display = "none";
        });
      });
      dropZone.addEventListener("drop", e => {
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          self.attachFileObject(e.dataTransfer.files[0]);
        }
      });
    }

    // Clipboard Paste (Ctrl+V) Image
    const promptInputEl = document.getElementById("aiVoucherPromptInput");
    if (promptInputEl) {
      promptInputEl.addEventListener("paste", e => {
        const items = (e.clipboardData || (e.originalEvent && e.originalEvent.clipboardData))?.items;
        if (!items) return;
        for (let i = 0; i < items.length; i++) {
          if (items[i].type && items[i].type.indexOf("image") !== -1) {
            const blob = items[i].getAsFile();
            if (blob) {
              const file = new File([blob], `screenshot_${new Date().getTime()}.png`, { type: blob.type });
              self.attachFileObject(file);
              self.showToast("Đã dán ảnh hóa đơn từ clipboard!", "success");
              break;
            }
          }
        }
      });
    }

    // Amount input formatting & calculations
    const amountInput = document.getElementById("inputAmount");
    if (amountInput) {
      amountInput.addEventListener("input", function(e) {
        let clean = e.target.value.replace(/\D/g, "");
        let num = parseInt(clean, 10) || 0;
        self.state.amount = num;
        e.target.value = num > 0 ? num.toLocaleString("vi-VN") : "";
        self.calculateDerivedAmounts();
        self.updateLivePreview();
      });
    }

    // Exchange rate change
    const exInput = document.getElementById("inputExchangeRate");
    if (exInput) {
      exInput.addEventListener("input", function(e) {
        let val = parseFloat(e.target.value) || 26000;
        self.state.exchange_rate = val;
        self.calculateDerivedAmounts();
        self.updateLivePreview();
      });
    }

    // Reason VI input
    const reasonViInput = document.getElementById("inputReasonVi");
    if (reasonViInput) {
      reasonViInput.addEventListener("input", function(e) {
        self.state.reason_vi = e.target.value;
        self.syncFullReason();
        self.updateLivePreview();
      });
    }

    // Reason ZH input
    const reasonZhInput = document.getElementById("inputReasonZh");
    if (reasonZhInput) {
      reasonZhInput.addEventListener("input", function(e) {
        self.state.reason_zh = e.target.value;
        self.syncFullReason();
        self.updateLivePreview();
      });
    }

    // Form field bindings
    const fieldBindings = [
      { id: "inputBeneficiaryName", key: "beneficiary_name" },
      { id: "inputAccountNumber", key: "account_number" },
      { id: "inputBankName", key: "bank_name" },
      { id: "inputReportCode", key: "report_code" },
      { id: "inputRequestDate", key: "request_date" },
      { id: "inputPreparedBy", key: "prepared_by" },
      { id: "inputSupervisor", key: "supervisor" },
      { id: "inputChecker", key: "checker" },
      { id: "inputAccountant", key: "accountant" },
      { id: "inputDirector", key: "director" },
      { id: "inputAttachmentNote", key: "attachment_note" }
    ];

    fieldBindings.forEach(binding => {
      const el = document.getElementById(binding.id);
      if (el) {
        el.addEventListener("input", function(e) {
          self.state[binding.key] = e.target.value;
          self.updateLivePreview();
        });
      }
    });

    // Employee Code listener
    const empInput = document.getElementById("inputEmployeeCode");
    if (empInput) {
      empInput.addEventListener("input", function(e) {
        const val = e.target.value.trim().toUpperCase();
        self.state.employee_code = val || "HVM007";
        localStorage.setItem("pm_employee_code", self.state.employee_code);
        self.fetchNextReportCode();
      });
    }

    // Refresh next report code button
    const btnRefresh = document.getElementById("btnRefreshReportCode");
    if (btnRefresh) {
      btnRefresh.addEventListener("click", function() {
        self.fetchNextReportCode(true);
      });
    }

    // Request date change recalculates sequence for that day
    const reqDateEl = document.getElementById("inputRequestDate");
    if (reqDateEl) {
      reqDateEl.addEventListener("change", function(e) {
        self.state.request_date = e.target.value;
        self.fetchNextReportCode();
        self.updateLivePreview();
      });
    }

    // Add Breakdown Row button
    const btnAddBreakdown = document.getElementById("btnAddBreakdownRow");
    if (btnAddBreakdown) {
      btnAddBreakdown.addEventListener("click", function() {
        self.addBreakdownRow();
      });
    }
  },

  addBreakdownRow(desc = "", amount = "") {
    if (this.state.breakdown_items.length >= 4) {
      this.showToast("Mẫu chuẩn hỗ trợ tối đa 4 dòng chi tiết (từ hàng 8 đến hàng 11).", "warning");
      return;
    }
    this.state.breakdown_items.push({ desc: desc, amount: amount });
    this.renderBreakdownRows();
    this.syncBreakdownTotal();
  },

  removeBreakdownRow(idx) {
    this.state.breakdown_items.splice(idx, 1);
    this.renderBreakdownRows();
    this.syncBreakdownTotal();
  },

  renderBreakdownRows() {
    const container = document.getElementById("breakdownRowsContainer");
    const notice = document.getElementById("breakdownEmptyNotice");
    if (!container) return;

    container.innerHTML = "";
    if (this.state.breakdown_items.length === 0) {
      if (notice) notice.style.display = "block";
      return;
    }
    if (notice) notice.style.display = "none";

    const self = this;
    this.state.breakdown_items.forEach((item, idx) => {
      const row = document.createElement("div");
      row.style.cssText = "display: flex; gap: 0.45rem; align-items: center;";
      row.innerHTML = `
        <span style="font-size: 0.78rem; font-weight: 700; color: #1e40af; width: 22px;">#${idx + 1}</span>
        <input type="text" class="form-control form-control-sm" placeholder="Số HĐ / Nội dung (F${8 + idx})" value="${self.escapeHtml(item.desc || "")}" style="flex: 1.4; font-size: 0.8rem; font-weight: 600;" data-idx="${idx}" data-field="desc">
        <input type="text" class="form-control form-control-sm" placeholder="Số tiền (G${8 + idx})" value="${item.amount ? Number(item.amount).toLocaleString("vi-VN") : ""}" style="flex: 1; font-size: 0.82rem; font-weight: 700; color: #16a34a; text-align: right;" data-idx="${idx}" data-field="amount">
        <span style="font-size: 0.76rem; color: var(--text-muted);">VND</span>
        <button type="button" class="btn btn-outline btn-sm" style="padding: 2px 7px; color: #dc2626; border-color: #fca5a5; font-size: 0.75rem;" title="Xóa dòng này" data-remove="${idx}">✕</button>
      `;

      const descIn = row.querySelector('[data-field="desc"]');
      const amtIn = row.querySelector('[data-field="amount"]');
      const rmBtn = row.querySelector('[data-remove]');

      descIn.addEventListener("input", function(e) {
        self.state.breakdown_items[idx].desc = e.target.value;
        self.updateLivePreview();
      });

      amtIn.addEventListener("input", function(e) {
        const raw = e.target.value.replace(/[^0-9]/g, "");
        const num = raw ? parseInt(raw, 10) : 0;
        self.state.breakdown_items[idx].amount = num;
        e.target.value = num ? num.toLocaleString("vi-VN") : "";
        self.syncBreakdownTotal();
      });

      rmBtn.addEventListener("click", function() {
        self.removeBreakdownRow(idx);
      });

      container.appendChild(row);
    });
  },

  syncBreakdownTotal() {
    if (this.state.breakdown_items.length > 0) {
      let sum = 0;
      this.state.breakdown_items.forEach(it => {
        sum += (parseInt(it.amount, 10) || 0);
      });
      if (sum > 0) {
        this.state.amount = sum;
        const amtInput = document.getElementById("inputAmount");
        if (amtInput) amtInput.value = sum.toLocaleString("vi-VN");
        this.calculateDerivedAmounts();
      }
    }
    this.updateLivePreview();
  },

  async fetchNextReportCode(showToastNotice = false) {
    const emp = (this.state.employee_code || "HVM007").trim().toUpperCase();
    const date = this.state.request_date || new Date().toISOString().split("T")[0];
    try {
      const res = await fetch(`/api/v1/payment-requests/next-code?employee_code=${encodeURIComponent(emp)}&date=${encodeURIComponent(date)}`);
      const data = await res.json();
      if (data.status === "success" && data.data && data.data.full_code) {
        this.state.report_code = data.data.full_code;
        const codeInput = document.getElementById("inputReportCode");
        if (codeInput) codeInput.value = data.data.full_code;
        const badge = document.getElementById("seqBadge");
        if (badge) badge.textContent = `Bản thứ ${data.data.seq} trong ngày`;
        this.updateLivePreview();
        if (showToastNotice) {
          this.showToast(`Đã lấy mã báo đơn tiếp theo: ${data.data.full_code} (Bản thứ ${data.data.seq})`, "info");
        }
      }
    } catch (err) {
      console.warn("Could not fetch next report code:", err);
    }
  },

  syncFullReason() {
    const vi = (this.state.reason_vi || "").trim();
    const zh = (this.state.reason_zh || "").trim();
    if (vi && zh) {
      this.state.full_reason = `${vi}\n${zh}`;
    } else {
      this.state.full_reason = vi || zh || "";
    }
  },

  calculateDerivedAmounts() {
    const amt = this.state.amount || 0;
    const rate = this.state.exchange_rate || 26000;
    this.state.amount_usd = amt > 0 ? (amt / rate).toFixed(2) : "0.00";

    // Client-side text conversion
    this.state.amount_in_words_vi = this.numberToVietnamese(amt);
    this.state.amount_in_words_zh = this.numberToChinese(amt);

    const txtViEl = document.getElementById("textAmountWordsVi");
    if (txtViEl) txtViEl.textContent = this.state.amount_in_words_vi;

    const txtZhEl = document.getElementById("textAmountWordsZh");
    if (txtZhEl) txtZhEl.textContent = this.state.amount_in_words_zh;

    const usdEl = document.getElementById("textAmountUsd");
    if (usdEl) usdEl.textContent = Number(this.state.amount_usd).toLocaleString("en-US", { minimumFractionDigits: 2 });
  },

  handleBeneficiarySelected(benId) {
    if (!benId) return;
    const found = this.state.beneficiaries.find(b => String(b.id) === String(benId));
    if (found) {
      this.state.beneficiary_name = found.unit_name;
      this.state.account_number = found.account_number;
      this.state.bank_name = found.bank_name;

      document.getElementById("inputBeneficiaryName").value = found.unit_name;
      document.getElementById("inputAccountNumber").value = found.account_number;
      document.getElementById("inputBankName").value = found.bank_name;

      if (found.default_reason && !this.state.reason_vi) {
        this.state.reason_vi = found.default_reason;
        const rVi = document.getElementById("inputReasonVi");
        if (rVi) rVi.value = found.default_reason;
        this.syncFullReason();
      }

      this.updateLivePreview();
      this.showToast(`Đã tự động chọn tài khoản: ${found.short_name || found.unit_name}`, "info");
    }
  },

  async loadBeneficiaries() {
    try {
      const res = await fetch("/api/v1/payment-requests/beneficiaries");
      const data = await res.json();
      if (data.status === "success" && Array.isArray(data.data)) {
        this.state.beneficiaries = data.data;
        this.renderBeneficiariesDropdown(data.data);
        this.renderBeneficiariesTable(data.data);
      }
    } catch (err) {
      console.warn("Could not load beneficiaries:", err);
    }
  },

  renderBeneficiariesDropdown(list) {
    const sel = document.getElementById("selectBeneficiary");
    if (!sel) return;
    sel.innerHTML = '<option value="">-- Chọn đơn vị thụ hưởng thường dùng --</option>';
    list.forEach(b => {
      const opt = document.createElement("option");
      opt.value = b.id;
      const tag = b.short_name ? `[${b.short_name}] ` : "";
      opt.textContent = `${tag}${b.unit_name} · ${b.account_number} (${b.bank_name})`;
      if (b.unit_name === this.state.beneficiary_name) {
        opt.selected = true;
      }
      sel.appendChild(opt);
    });
  },

  renderBeneficiariesTable(list) {
    const tbody = document.getElementById("beneficiariesTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Chưa có tài khoản nào trong sổ tay.</td></tr>';
      return;
    }
    list.forEach((b, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="text-align: center; font-weight: 600;">${idx + 1}</td>
        <td>
          <div style="font-weight: 700; color: var(--primary);">${this.escapeHtml(b.unit_name)}</div>
          <div style="font-size: 0.78rem; color: var(--text-muted);">${b.short_name ? 'Tên gợi nhớ: ' + this.escapeHtml(b.short_name) : ''}</div>
        </td>
        <td style="font-family: monospace; font-weight: 700;">${this.escapeHtml(b.account_number)}</td>
        <td>${this.escapeHtml(b.bank_name)}</td>
        <td style="text-align: center;"><span class="badge-pill blue" style="font-size: 0.75rem;">${b.usage_count || 0} lần</span></td>
        <td style="text-align: center; white-space: nowrap;">
          <button type="button" class="btn btn-primary btn-sm" onclick="PaymentVoucherApp.selectAndCloseModal(${b.id})" title="Chọn tài khoản này để tạo phiếu" style="padding: 3px 8px; font-size: 0.75rem;">
            Chọn
          </button>
          <button type="button" class="btn btn-outline btn-sm" onclick="PaymentVoucherApp.deleteBeneficiary(${b.id})" title="Xóa tài khoản này" style="padding: 3px 6px; font-size: 0.75rem; color: #ef4444; border-color: #fca5a5;">
            ✕
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  },

  selectAndCloseModal(benId) {
    this.handleBeneficiarySelected(benId);
    const sel = document.getElementById("selectBeneficiary");
    if (sel) sel.value = benId;
    this.closeModal("beneficiariesModal");
  },

  async saveNewBeneficiary() {
    const name = document.getElementById("modalUnitName").value.trim();
    const acc = document.getElementById("modalAccountNumber").value.trim();
    const bank = document.getElementById("modalBankName").value.trim();
    const shortName = document.getElementById("modalShortName").value.trim();
    const defReason = document.getElementById("modalDefaultReason").value.trim();

    if (!name || !acc || !bank) {
      alert("Vui lòng nhập đầy đủ Tên đơn vị, Số tài khoản và Tên ngân hàng.");
      return;
    }

    try {
      const res = await fetch("/api/v1/payment-requests/beneficiaries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          unit_name: name,
          account_number: acc,
          bank_name: bank,
          short_name: shortName,
          default_reason: defReason
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        this.showToast("Đã lưu tài khoản thụ hưởng vào sổ tay thành công!", "success");
        document.getElementById("modalUnitName").value = "";
        document.getElementById("modalAccountNumber").value = "";
        document.getElementById("modalBankName").value = "";
        document.getElementById("modalShortName").value = "";
        document.getElementById("modalDefaultReason").value = "";
        await this.loadBeneficiaries();
      } else {
        alert(data.detail || "Không thể lưu tài khoản.");
      }
    } catch (err) {
      alert("Lỗi khi lưu tài khoản: " + err.message);
    }
  },

  async deleteBeneficiary(id) {
    if (!confirm("Bạn có chắc chắn muốn xóa tài khoản này khỏi danh bạ?")) return;
    try {
      const res = await fetch(`/api/v1/payment-requests/beneficiaries/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (data.status === "success") {
        this.showToast("Đã xóa tài khoản khỏi danh bạ.", "info");
        await this.loadBeneficiaries();
      }
    } catch (err) {
      alert("Lỗi khi xóa: " + err.message);
    }
  },

  handleFileSelected(input) {
    if (!input.files || input.files.length === 0) return;
    this.attachFileObject(input.files[0]);
  },

  attachFileObject(file) {
    if (!file) return;
    const self = this;
    const reader = new FileReader();
    reader.onload = function(e) {
      self.state.attachedFile = {
        name: file.name,
        mime: file.type || "application/octet-stream",
        size: file.size,
        base64: e.target.result,
        previewUrl: file.type && file.type.startsWith("image/") ? e.target.result : null
      };
      self.renderAttachedFilePreview();
      self.showToast(`Đã đính kèm tệp "${file.name}"! Nhấn 'AI Trích Xuất' để bắt đầu.`, "success");
    };
    reader.readAsDataURL(file);
  },

  clearAttachedFile() {
    this.state.attachedFile = null;
    const input = document.getElementById("aiVoucherFileInput");
    if (input) input.value = "";
    const container = document.getElementById("voucherAttachedFileContainer");
    if (container) container.style.display = "none";
    this.showToast("Đã hủy tệp đính kèm.", "info");
  },

  renderAttachedFilePreview() {
    const container = document.getElementById("voucherAttachedFileContainer");
    const nameEl = document.getElementById("voucherFileName");
    const badgeEl = document.getElementById("voucherFileTypeBadge");
    const sizeEl = document.getElementById("voucherFileSize");
    const thumbEl = document.getElementById("voucherFileThumb");

    if (!container || !this.state.attachedFile) return;
    const f = this.state.attachedFile;

    if (nameEl) nameEl.textContent = f.name;
    const sizeKb = f.size ? Math.round(f.size / 1024) + " KB" : "";
    if (sizeEl) sizeEl.textContent = sizeKb;

    const isPdf = (f.mime && f.mime.includes("pdf")) || /\.pdf$/i.test(f.name);
    const isImage = (f.mime && f.mime.startsWith("image/")) || /\.(png|jpg|jpeg|webp|bmp)$/i.test(f.name);
    const isExcel = /\.(xlsx|xls|xlsm)$/i.test(f.name);
    const isDoc = /\.(docx|doc)$/i.test(f.name) || (f.mime && (f.mime.includes("word") || f.mime.includes("officedocument.wordprocessingml")));

    if (badgeEl) {
      badgeEl.textContent = isDoc ? "Biên Bản/Hợp Đồng Word" : isPdf ? "Hóa Đơn PDF" : isImage ? "Ảnh Hóa Đơn" : isExcel ? "Bảng Tính Excel" : "Tài Liệu Đính Kèm";
      badgeEl.style.background = isDoc ? "#eff6ff" : isPdf ? "#fee2e2" : isImage ? "#dbeafe" : "#dcfce7";
      badgeEl.style.color = isDoc ? "#1d4ed8" : isPdf ? "#dc2626" : isImage ? "#1d4ed8" : "#15803d";
      badgeEl.style.borderColor = isDoc ? "#93c5fd" : isPdf ? "#fca5a5" : isImage ? "#93c5fd" : "#86efac";
    }

    if (thumbEl) {
      if (isImage && f.previewUrl) {
        thumbEl.innerHTML = `<img src="${f.previewUrl}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px;" alt="preview">`;
      } else if (isDoc) {
        thumbEl.innerHTML = `<svg style="width: 22px; height: 22px; color: #1d4ed8;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`;
      } else if (isPdf) {
        thumbEl.innerHTML = `<svg style="width: 22px; height: 22px; color: #dc2626;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 15h6M9 11h6M9 7h2"/></svg>`;
      } else if (isExcel) {
        thumbEl.innerHTML = `<svg style="width: 22px; height: 22px; color: #16a34a;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></svg>`;
      } else {
        thumbEl.innerHTML = `<svg style="width: 22px; height: 22px; color: #2563eb;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
      }
    }

    container.style.display = "flex";
  },

  async handleAiExtract() {
    const promptInput = document.getElementById("aiVoucherPromptInput");
    const rawText = promptInput ? promptInput.value.trim() : "";
    const attached = this.state.attachedFile;

    if (!rawText && !attached) {
      this.showToast("Vui lòng nhập văn bản hoặc đính kèm tệp hóa đơn/chứng từ (PDF, Ảnh, Excel).", "warning");
      if (promptInput) promptInput.focus();
      return;
    }

    const modelSelect = document.getElementById("aiModelSelect");
    const modelName = modelSelect ? modelSelect.value : undefined;

    const loadingMsg = attached
      ? `AI Gemini đang phân tích tệp "${attached.name}" & trích xuất dữ liệu biểu mẫu thanh toán...`
      : "AI Gemini đang phân tích, nhận diện tài khoản thụ hưởng & tính số tiền...";
    this.showLoading(true, loadingMsg);

    try {
      const res = await fetch("/api/v1/payment-requests/ai-extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          raw_text: rawText,
          model_name: modelName,
          file_base64: attached ? attached.base64 : null,
          file_mime: attached ? attached.mime : null,
          file_name: attached ? attached.name : null
        })
      });
      const result = await res.json();

      if (result.status === "success" && result.data) {
        const d = result.data;
        this.state.beneficiary_name = d.beneficiary_name || "";
        this.state.account_number = d.account_number || "";
        this.state.bank_name = d.bank_name || "";
        this.state.amount = d.amount || 0;
        this.state.currency = d.currency || "VND";
        this.state.reason_vi = d.reason_vi || "";
        this.state.reason_zh = d.reason_zh || "";
        this.state.full_reason = d.full_reason || "";
        this.state.report_code = d.report_code || this.state.report_code;
        this.state.request_date = d.request_date || this.state.request_date;
        this.state.prepared_by = d.prepared_by || this.state.prepared_by;

        // Fill Form Inputs
        document.getElementById("inputBeneficiaryName").value = this.state.beneficiary_name;
        document.getElementById("inputAccountNumber").value = this.state.account_number;
        document.getElementById("inputBankName").value = this.state.bank_name;
        document.getElementById("inputAmount").value = this.state.amount ? this.state.amount.toLocaleString("vi-VN") : "";
        document.getElementById("inputReasonVi").value = this.state.reason_vi;
        document.getElementById("inputReasonZh").value = this.state.reason_zh;
        document.getElementById("inputReportCode").value = this.state.report_code;
        document.getElementById("inputRequestDate").value = this.state.request_date;
        document.getElementById("inputPreparedBy").value = this.state.prepared_by;

        if (Array.isArray(d.breakdown_items) && d.breakdown_items.length > 0) {
          this.state.breakdown_items = d.breakdown_items.slice(0, 4);
          this.renderBreakdownRows();
        } else {
          this.state.breakdown_items = [];
          this.renderBreakdownRows();
        }

        this.calculateDerivedAmounts();
        this.updateLivePreview();

        // Match dropdown if available
        if (d.beneficiary_id) {
          const sel = document.getElementById("selectBeneficiary");
          if (sel) sel.value = d.beneficiary_id;
        }

        const matchMsg = d._matched_from_directory
          ? `Đã nhận diện đơn vị thụ hưởng "${d.beneficiary_name}" từ Sổ tay!`
          : `Đã trích xuất xong thông tin cho "${d.beneficiary_name}".`;
        this.showToast(matchMsg, "success");
      } else {
        alert(result.detail || "Không thể phân tích dữ liệu.");
      }
    } catch (err) {
      alert("Lỗi kết nối AI: " + err.message);
    } finally {
      this.showLoading(false);
    }
  },

  async handleTranslateReason() {
    const vi = (this.state.reason_vi || document.getElementById("inputReasonVi").value || "").trim();
    if (!vi) {
      this.showToast("Vui lòng nhập nội dung lý do thanh toán bằng tiếng Việt trước.", "warning");
      return;
    }

    const modelSelect = document.getElementById("aiModelSelect");
    const modelName = modelSelect ? modelSelect.value : undefined;

    this.showLoading(true, "AI đang dịch lý do thanh toán sang tiếng Trung song ngữ...");
    try {
      const res = await fetch("/api/v1/payment-requests/ai-translate-reason", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason_vi: vi, model_name: modelName })
      });
      const result = await res.json();
      if (result.status === "success" && result.data) {
        this.state.reason_zh = result.data.reason_zh || "";
        document.getElementById("inputReasonZh").value = this.state.reason_zh;
        this.syncFullReason();
        this.updateLivePreview();
        this.showToast("Đã dịch sang tiếng Trung song ngữ thành công!", "success");
      }
    } catch (err) {
      alert("Lỗi dịch AI: " + err.message);
    } finally {
      this.showLoading(false);
    }
  },

  async handleGenerateExcel() {
    const payload = { ...this.state };
    if (!payload.beneficiary_name) {
      this.showToast("Vui lòng nhập tên đơn vị thụ hưởng.", "warning");
      return;
    }

    this.showLoading(true, "Đang khởi tạo file Excel Đơn Xin Thanh Toán chuẩn 1:1...");
    try {
      const res = await fetch("/api/v1/payment-requests/generate-excel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await res.json();

      if (result.status === "success" && result.download_url) {
        this.showToast("Xuất file Excel thành công! Đang mở trực tiếp trên máy tính...", "success");

        // Tự động mở file trực tiếp trên Windows nếu có đường dẫn
        if (result.file_path) {
          this.openFileOnSystem(result.file_path);
        } else {
          // Fallback tải về qua trình duyệt
          const a = document.createElement("a");
          a.href = result.download_url;
          a.download = result.file_name;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }

        await this.loadHistory();

        if (result.next_report_code) {
          this.state.report_code = result.next_report_code;
          const codeInput = document.getElementById("inputReportCode");
          if (codeInput) codeInput.value = result.next_report_code;
          this.updateLivePreview();
        } else {
          await this.fetchNextReportCode();
        }
      } else {
        alert(result.detail || "Không thể tạo file Excel.");
      }
    } catch (err) {
      alert("Lỗi tạo file Excel: " + err.message);
    } finally {
      this.showLoading(false);
    }
  },

  async openFileOnSystem(targetPath) {
    if (!targetPath) {
      this.showToast("Không tìm thấy đường dẫn tệp trên máy.", "warning");
      return;
    }
    try {
      this.showToast("Đang mở file trực tiếp trên máy tính...", "info");
      const res = await fetch("/api/v1/system/open-path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: targetPath })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.status === "success") {
        this.showToast(data.message || "Đã mở file thành công trên máy tính!", "success");
      } else {
        this.showToast(data.message || data.detail || "Không thể mở file trên máy.", "warning");
      }
    } catch (err) {
      this.showToast(`Lỗi mở tệp: ${err.message}`, "error");
    }
  },

  openHistoryFile(voucherId) {
    const item = this.state.history.find(h => h.id === voucherId);
    if (!item) {
      this.showToast("Không tìm thấy thông tin đơn thanh toán.", "warning");
      return;
    }
    const path = item.file_path || (item.file_name ? `Ho So Du An/Don Xin Thanh Toan/${item.file_name}` : "");
    if (!path) {
      this.showToast("Không tìm thấy đường dẫn file trên máy cho đơn này.", "warning");
      return;
    }
    this.openFileOnSystem(path);
  },

  openStorageFolder() {
    this.openFileOnSystem("Ho So Du An/Don Xin Thanh Toan");
  },

  async loadHistory(search = "") {
    try {
      const q = search ? `&search=${encodeURIComponent(search.trim())}` : "";
      const res = await fetch(`/api/v1/payment-requests/history?limit=100${q}`);
      const data = await res.json();
      if (data.status === "success" && Array.isArray(data.data)) {
        this.state.history = data.data;
        this.renderHistoryTable(data.data);
      }
    } catch (err) {
      console.warn("Could not load history:", err);
    }
  },

  handleHistorySearch(keyword) {
    if (this._historySearchTimeout) clearTimeout(this._historySearchTimeout);
    this._historySearchTimeout = setTimeout(() => {
      this.loadHistory(keyword);
    }, 250);
  },

  clearHistorySearch() {
    const input = document.getElementById("historySearchInput");
    if (input) input.value = "";
    this.loadHistory("");
  },

  async deleteHistoryItem(voucherId) {
    const found = this.state.history.find(h => h.id === voucherId);
    const code = found ? found.report_code : `ID #${voucherId}`;
    if (!confirm(`Bạn có chắc chắn muốn xóa đơn "${code}" và file Excel tương ứng khỏi ổ đĩa không?`)) {
      return;
    }
    try {
      const res = await fetch(`/api/v1/payment-requests/history/${voucherId}`, {
        method: "DELETE"
      });
      const data = await res.json();
      if (data.status === "success") {
        this.showToast("Đã xóa đơn thanh toán và file Excel tương ứng khỏi hệ thống.", "success");
        const kw = document.getElementById("historySearchInput")?.value || "";
        await this.loadHistory(kw);
      } else {
        this.showToast(data.detail || "Không thể xóa đơn.", "error");
      }
    } catch (err) {
      this.showToast("Lỗi khi xóa đơn thanh toán.", "error");
    }
  },

  renderHistoryTable(list) {
    const tbody = document.getElementById("historyTableBody");
    const badge = document.getElementById("historySummaryBadge");
    if (badge) {
      const totalAmt = list.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
      badge.textContent = `Tổng: ${list.length} đơn · ${totalAmt.toLocaleString("vi-VN")} đ`;
    }
    if (!tbody) return;
    tbody.innerHTML = "";
    if (list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Không tìm thấy phiếu thanh toán nào phù hợp.</td></tr>';
      return;
    }
    list.forEach((h, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="text-align: center; font-weight: 600;">${idx + 1}</td>
        <td style="font-family: monospace; font-weight: 700; color: var(--primary);">${this.escapeHtml(h.report_code)}</td>
        <td>${this.escapeHtml(h.request_date)}</td>
        <td style="font-weight: 600;">${this.escapeHtml(h.beneficiary_name)}</td>
        <td style="text-align: right; font-weight: 700; color: #16a34a;">${h.amount_formatted} đ</td>
        <td style="font-size: 0.8rem; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${this.escapeHtml(h.full_reason)}">${this.escapeHtml(h.full_reason)}</td>
        <td style="text-align: center; white-space: nowrap;">
          <button type="button" class="btn btn-primary btn-sm" onclick="PaymentVoucherApp.openHistoryFile(${h.id})" style="padding: 2px 7px; font-size: 0.74rem; background: #2563eb; color: #ffffff; border-color: #2563eb; font-weight: 600;" title="Mở trực tiếp file Excel trên máy tính bằng Excel/WPS">
            📂 Mở
          </button>
          <a href="${h.download_url}" class="btn btn-outline btn-sm" style="padding: 2px 7px; font-size: 0.74rem;" title="Tải file Excel về máy (Downloads)">
            📥 Tải
          </a>
          <button type="button" class="btn btn-secondary btn-sm" onclick="PaymentVoucherApp.reloadVoucherToForm(${h.id})" style="padding: 2px 7px; font-size: 0.74rem;" title="Nạp lại dữ liệu phiếu này lên form">
            📝 Nạp
          </button>
          <a href="/emails?source=voucher&id=${h.id}" class="btn btn-outline btn-sm" style="padding: 2px 7px; font-size: 0.74rem; color: #0284c7; border-color: #bae6fd; font-weight: 600;" title="✉️ Soạn Email Trình Ký Sếp Tang Wei Li">
            ✉️ Email
          </a>
          <button type="button" class="btn btn-outline btn-sm" onclick="PaymentVoucherApp.deleteHistoryItem(${h.id})" style="padding: 2px 6px; font-size: 0.74rem; color: #dc2626; border-color: #fca5a5;" title="Xóa đơn này">
            🗑️
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  },

  reloadVoucherToForm(voucherId) {
    const found = this.state.history.find(h => h.id === voucherId);
    if (!found) return;

    this.state.beneficiary_name = found.beneficiary_name;
    this.state.account_number = found.account_number;
    this.state.bank_name = found.bank_name;
    this.state.amount = parseInt(found.amount, 10) || 0;
    this.state.currency = found.currency || "VND";
    this.state.exchange_rate = found.exchange_rate || 26000;
    this.state.reason_vi = found.reason_vi || "";
    this.state.reason_zh = found.reason_zh || "";
    this.state.full_reason = found.full_reason || "";
    this.state.report_code = found.report_code;
    this.state.request_date = found.request_date;
    this.state.prepared_by = found.prepared_by || "NGUYỄN SỸ KIM BẰNG";

    const empMatch = (found.report_code || "").match(/(?:报单号[：:])?\s*([A-Za-z0-9]+)-\d{8}-\d+/);
    if (empMatch && empMatch[1]) {
      this.state.employee_code = empMatch[1].toUpperCase();
      const empIn = document.getElementById("inputEmployeeCode");
      if (empIn) empIn.value = this.state.employee_code;
    }

    document.getElementById("inputBeneficiaryName").value = this.state.beneficiary_name;
    document.getElementById("inputAccountNumber").value = this.state.account_number;
    document.getElementById("inputBankName").value = this.state.bank_name;
    document.getElementById("inputAmount").value = this.state.amount.toLocaleString("vi-VN");
    document.getElementById("inputReasonVi").value = this.state.reason_vi;
    document.getElementById("inputReasonZh").value = this.state.reason_zh;
    document.getElementById("inputReportCode").value = this.state.report_code;
    document.getElementById("inputRequestDate").value = this.state.request_date;
    document.getElementById("inputPreparedBy").value = this.state.prepared_by;

    this.calculateDerivedAmounts();
    this.updateLivePreview();
    this.closeModal("historyModal");
    this.showToast(`Đã nạp lại phiếu ${found.report_code} lên form!`, "success");
  },

  fillSamplePrompt(type) {
    const input = document.getElementById("aiVoucherPromptInput");
    if (!input) return;

    if (type === "thaison") {
      input.value = "Thanh toán cho CONG TY TNHH PHAT TRIEN CONG NGHE THAI SON STK 0491001474862 Ngân Hàng TMCP Ngoại Thương VN - CN Thăng Long HN, chi phí TT CKS+EBH(bhxh) và Gia hạn CKS+PM Hải Quan gồm 4 hóa đơn: INV 66024 số tiền 1.792.800 đ, INV 65684 số tiền 500.000 đ, INV 66854 số tiền 1.252.800 đ, INV 66855 số tiền 1.580.000 đ";
    } else if (type === "omg") {
      input.value = "Thanh toán đợt 2 (50%) theo hợp đồng số VIMF BD26_HONG MING cho bên CÔNG TY TNHH TO CHUC SU KIEN OMG, số tiền 42.346.800 đ chi phí tham gia Triển lãm Công nghiệp và Sản xuất Việt Nam – Bình Dương 2026";
    } else if (type === "finepro") {
      input.value = "Thanh toán cho CONG TY TNHH FINEPRO AUTOMATION chi phí Thu Thập dữ liệu máy dập Hóa Đơn: 055 số tiền 10.800.000 vnđ";
    } else if (type === "vietnhat") {
      input.value = "Chuyển tiền mua laptop cho CÔNG TY TNHH VIET NHAT SOLUTIONS số tiền 24.800.000 đ theo hóa đơn 170";
    } else if (type === "dtt") {
      input.value = "Thanh toán cước vận chuyển hàng không Air Freight cho CÔNG TY TNHH GIAO NHẬN HÀNG HẢI ĐỨC TRƯỜNG THỊNH theo Debit Note DTTDAE-080526 số tiền 7.061.240 VND";
    }
    input.focus();
    this.handleAiExtract();
  },

  resetForm() {
    this.state.beneficiary_name = "";
    this.state.account_number = "";
    this.state.bank_name = "";
    this.state.amount = 0;
    this.state.reason_vi = "";
    this.state.reason_zh = "";
    this.state.full_reason = "";
    this.state.request_date = new Date().toISOString().split("T")[0];
    this.state.prepared_by = "NGUYỄN SỸ KIM BẰNG";

    document.getElementById("inputBeneficiaryName").value = "";
    document.getElementById("inputAccountNumber").value = "";
    document.getElementById("inputBankName").value = "";
    document.getElementById("inputAmount").value = "";
    document.getElementById("inputReasonVi").value = "";
    document.getElementById("inputReasonZh").value = "";
    document.getElementById("inputRequestDate").value = this.state.request_date;
    document.getElementById("inputPreparedBy").value = "NGUYỄN SỸ KIM BẰNG";
    const empInput = document.getElementById("inputEmployeeCode");
    if (empInput) empInput.value = this.state.employee_code || "HVM007";
    const sel = document.getElementById("selectBeneficiary");
    if (sel) sel.value = "";

    this.clearAttachedFile();
    this.state.breakdown_items = [];
    this.renderBreakdownRows();
    this.calculateDerivedAmounts();
    this.fetchNextReportCode();
    this.updateLivePreview();
    this.showToast("Đã làm mới form tạo phiếu.", "info");
  },

  togglePreview(forceState = null) {
    const layout = document.getElementById("voucherGridLayout");
    const btnText = document.getElementById("togglePreviewText");
    if (!layout) return;

    const isCurrentlyHidden = layout.classList.contains("preview-hidden");
    let willShow;

    if (forceState !== null) {
      willShow = !!forceState;
    } else {
      willShow = isCurrentlyHidden; // Nếu đang ẩn thì bấm nút sẽ hiện
    }

    if (willShow) {
      layout.classList.remove("preview-hidden");
      if (btnText) btnText.textContent = "✕ Ẩn Xem Trước";
      this.updateLivePreview();
    } else {
      layout.classList.add("preview-hidden");
      if (btnText) btnText.textContent = "👁️ Xem Trước Excel";
    }
  },

  updateLivePreview() {
    const s = this.state;

    // Header dates
    const dateEl = document.getElementById("prevDate");
    if (dateEl) dateEl.textContent = s.request_date || new Date().toISOString().split("T")[0];

    const codeEl = document.getElementById("prevReportCode");
    if (codeEl) codeEl.textContent = s.report_code.startsWith("报单号：") ? s.report_code : `报单号：${s.report_code}`;

    // Table cells
    const unitEl = document.getElementById("prevUnit");
    if (unitEl) unitEl.textContent = s.beneficiary_name || "(Chưa nhập đơn vị thụ hưởng)";

    const accEl = document.getElementById("prevAccount");
    if (accEl) accEl.textContent = s.account_number || "-";

    const bankEl = document.getElementById("prevBank");
    if (bankEl) bankEl.textContent = s.bank_name || "-";

    const reasonEl = document.getElementById("prevReason");
    if (reasonEl) {
      reasonEl.innerHTML = this.escapeHtml(s.full_reason || "(Chưa nhập lý do thanh toán)").replace(/\n/g, "<br>");
    }

    const amtEl = document.getElementById("prevAmount");
    if (amtEl) amtEl.textContent = (s.amount || 0).toLocaleString("vi-VN");

    const currEl = document.getElementById("prevCurrency");
    if (currEl) currEl.textContent = s.currency || "VND";

    // G7 formula & Rows 8-11 breakdown display
    const formulaG7El = document.getElementById("prevFormulaG7");
    const hasItems = Array.isArray(s.breakdown_items) && s.breakdown_items.length > 0;

    if (hasItems) {
      if (formulaG7El) formulaG7El.textContent = `=SUM(G8:G${7 + s.breakdown_items.length})`;
      for (let i = 0; i < 4; i++) {
        const descEl = document.getElementById(`prevSubDesc${i}`);
        const amtElSub = document.getElementById(`prevSubAmt${i}`);
        const currElSub = document.getElementById(`prevSubCurr${i}`);
        if (i < s.breakdown_items.length) {
          const item = s.breakdown_items[i];
          if (descEl) descEl.textContent = item.desc || "";
          if (amtElSub) amtElSub.textContent = item.amount ? Number(item.amount).toLocaleString("vi-VN") : "";
          if (currElSub) currElSub.textContent = s.currency || "VND";
        } else {
          if (descEl) descEl.textContent = "";
          if (amtElSub) amtElSub.textContent = "";
          if (currElSub) currElSub.textContent = "";
        }
      }
    } else {
      if (formulaG7El) formulaG7El.textContent = "";
      for (let i = 0; i < 4; i++) {
        const descEl = document.getElementById(`prevSubDesc${i}`);
        const amtElSub = document.getElementById(`prevSubAmt${i}`);
        const currElSub = document.getElementById(`prevSubCurr${i}`);
        if (descEl) descEl.textContent = "";
        if (amtElSub) amtElSub.textContent = "";
        if (currElSub) currElSub.textContent = "";
      }
    }

    const wordsZhEl = document.getElementById("prevWordsZh");
    if (wordsZhEl) wordsZhEl.textContent = s.amount_in_words_zh || "-";

    const d12El = document.getElementById("prevD12");
    if (d12El) d12El.textContent = (s.amount || 0).toLocaleString("vi-VN");

    const usdEl = document.getElementById("prevD13Usd");
    if (usdEl) usdEl.textContent = Number(s.amount_usd || 0).toLocaleString("en-US", { minimumFractionDigits: 2 });

    const signPrep = document.getElementById("prevSignPrepared");
    const prepName = s.prepared_by || "NGUYỄN SỸ KIM BẰNG";
    if (signPrep) signPrep.textContent = prepName;

    const signImgContainer = document.getElementById("prevSignImgContainer");
    if (signImgContainer) {
      const isBang = prepName.toUpperCase().includes("BẰNG") || prepName.toUpperCase().includes("BANG");
      signImgContainer.style.display = isBang ? "flex" : "none";
    }
  },

  openModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.style.display = "flex";
  },

  closeModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.style.display = "none";
  },

  numberToVietnamese(num) {
    if (!num || num === 0) return "Không đồng";
    const units = ["", " nghìn", " triệu", " tỷ", " nghìn tỷ", " triệu tỷ"];
    const digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"];

    function readGroup(n) {
      let h = Math.floor(n / 100);
      let t = Math.floor((n % 100) / 10);
      let u = n % 10;
      let res = "";
      if (h > 0) res += digits[h] + " trăm ";
      if (t > 1) {
        res += digits[t] + " mươi ";
        if (u === 1) res += "mốt ";
        else if (u === 5) res += "lăm ";
        else if (u > 0) res += digits[u] + " ";
      } else if (t === 1) {
        res += "mười ";
        if (u === 5) res += "lăm ";
        else if (u > 0) res += digits[u] + " ";
      } else if (t === 0 && h > 0 && u > 0) {
        res += "lẻ " + digits[u] + " ";
      } else if (t === 0 && u > 0) {
        res += digits[u] + " ";
      }
      return res.trim();
    }

    let n = Math.abs(num);
    let groups = [];
    while (n > 0) {
      groups.push(n % 1000);
      n = Math.floor(n / 1000);
    }

    let parts = [];
    for (let i = 0; i < groups.length; i++) {
      let g = groups[i];
      if (g > 0) {
        let gStr = readGroup(g);
        parts.unshift(gStr + units[i]);
      }
    }

    let result = parts.join(" ").trim() + " đồng chẵn";
    return result.charAt(0).toUpperCase() + result.slice(1);
  },

  numberToChinese(num) {
    if (!num || num === 0) return "零元整";
    const digits = ["零", "壹", "貳", "參", "肆", "伍", "陸", "柒", "捌", "玖"];
    const units = ["", "拾", "佰", "仟"];
    const bigUnits = ["", "萬", "億", "兆"];

    function readSection(sec) {
      let str = "";
      let zero = true;
      for (let i = 0; i < 4; i++) {
        let digit = Math.floor(sec / Math.pow(10, 3 - i)) % 10;
        if (digit !== 0) {
          if (zero && str !== "") str += "零";
          str += digits[digit] + units[3 - i];
          zero = false;
        } else {
          zero = true;
        }
      }
      return str;
    }

    let n = Math.abs(num);
    let str = "";
    let unitIdx = 0;
    while (n > 0) {
      let sec = n % 10000;
      if (sec !== 0) {
        let secStr = readSection(sec);
        str = secStr + bigUnits[unitIdx] + str;
      }
      unitIdx++;
      n = Math.floor(n / 10000);
    }
    return (str || "零") + "元整";
  },

  escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },

  showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast-item toast-${type}`;
    toast.style.cssText = `
      padding: 0.75rem 1.15rem;
      border-radius: 8px;
      margin-bottom: 0.5rem;
      font-size: 0.88rem;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      background: ${type === "success" ? "#10b981" : type === "warning" ? "#f59e0b" : "#3b82f6"};
      color: #ffffff;
      animation: fadeIn 0.25s ease;
    `;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  showLoading(show, message = "Đang xử lý...") {
    const overlay = document.getElementById("globalLoadingOverlay");
    const txt = document.getElementById("loadingOverlayText");
    if (!overlay) return;
    if (txt) txt.textContent = message;
    overlay.style.display = show ? "flex" : "none";
  }
};

document.addEventListener("DOMContentLoaded", function() {
  PaymentVoucherApp.init();
});
