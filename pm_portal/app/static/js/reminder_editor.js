/**
 * Payment Requests & AR Reminders Editor for Hong Ming PM Portal.
 * Workflow:
 * 1. Select upcoming milestone from SQLite contracts dossier.
 * 2. Generate Phiếu yêu cầu thanh toán from the selected Excel/Word master template.
 * 3. Review and send the payment reminder with both generated formats attached via Gmail.
 */

const ReminderEditor = {
  currentView: "email", // 'email' or 'dxyctt'
  cachedEmailPreviewHtml: "",
  cachedDxycttPreviewHtml: "",
  currentGeneratedFile: "",

  cachedContracts: [],
  activeContractCode: "",
  activeMilestoneName: "",
  activeDossierFilter: "all",
  dossierSearchQuery: "",

  init() {
    this.initTabs();
    this.loadSavedContracts();
    this.renderVisualAttachmentsList();
  },

  loadDossierData() {
    return this.loadSavedContracts();
  },

  /**
   * Kiểm tra xem một đợt thanh toán có phải là Đợt 1 / Tạm ứng thanh toán ngay khi ký hợp đồng không.
   * Nghiệp vụ: Đợt thanh toán ngay theo hợp đồng không cần tạo "Phiếu Yêu Cầu Thanh Toán",
   * mà tiền đã được thanh toán hoặc chỉ cần bấm "Xác Nhận Đã Thu".
   */
  isImmediateFirstMilestone(ms, index = 0) {
    if (!ms) return false;
    const name = (ms.milestone_name || "").toLowerCase().trim();
    const cond = (ms.trigger_condition || "").toLowerCase().trim();

    // 1. Kiểm tra có phải là Đợt 1 / Đợt đầu tiên / Tạm ứng / Cọc
    const isFirst = (index === 0) ||
                    name.includes("đợt 1") ||
                    name.includes("đợt 01") ||
                    name.includes("đợt một") ||
                    name.includes("tạm ứng") ||
                    name.includes("đặt cọc") ||
                    name.includes("tiền cọc");
    if (!isFirst) return false;

    // 2. Nếu là đợt 1 thì kiểm tra tính chất thanh toán ngay:
    const immediateKeywords = ["ký", "kí", "ngay", "tạm ứng", "cọc", "đặt cọc", "đặt hàng", "ký kết"];
    const hasImmediateWord = immediateKeywords.some(kw => cond.includes(kw));

    // Nếu không có điều kiện hoặc điều kiện chứa từ khóa trên thì tính là thanh toán ngay
    return hasImmediateWord || !cond || name.includes("tạm ứng") || name.includes("cọc");
  },


  async loadSavedContracts() {
    try {
      const res = await fetch("/api/v1/dossier/contracts");
      const data = await res.json();
      if (data.status === "success" && Array.isArray(data.contracts)) {
        this.cachedContracts = data.contracts;
        this.updateDossierCounters();
        this.renderDossierCards();
      }
    } catch (err) {
      console.error("Error loading saved contracts:", err);
      const container = document.getElementById("dossierCardsList");
      if (container) {
        container.innerHTML = `<div style="padding: 1rem; color: #dc2626; font-size: 0.85rem;">Không thể nạp dữ liệu hợp đồng: ${err.message}</div>`;
      }
    }
  },

  currentTriggerMilestone: null,

  openTriggerModal(milestoneId, contractCode = "") {
    let targetContract = null;
    let targetMilestone = null;

    for (const c of this.cachedContracts) {
      if (contractCode && c.contract_code !== contractCode) continue;
      const ms = (c.milestones || []).find(m => m.id === milestoneId);
      if (ms) {
        targetContract = c;
        targetMilestone = ms;
        break;
      }
    }

    if (!targetMilestone) return;
    this.currentTriggerMilestone = targetMilestone;

    const modal = document.getElementById("milestoneTriggerModal");
    const nameEl = document.getElementById("tmMilestoneName");
    const codeEl = document.getElementById("tmContractCode");
    const condEl = document.getElementById("tmCondition");
    const amtEl = document.getElementById("tmAmountInfo");
    const termEl = document.getElementById("tmTermDays");
    const dateInput = document.getElementById("tmTriggerDateInput");
    const idInput = document.getElementById("tmActiveMilestoneId");
    const resetBtn = document.getElementById("tmBtnReset");

    if (nameEl) nameEl.textContent = targetMilestone.milestone_name;
    if (codeEl) codeEl.textContent = targetContract ? targetContract.contract_code : "";
    if (condEl) condEl.textContent = targetMilestone.trigger_condition || "Theo thỏa thuận HĐ";
    if (amtEl) {
      const amtStr = Number(targetMilestone.amount || 0).toLocaleString("vi-VN") + " VND";
      amtEl.textContent = `${targetMilestone.percentage}% (${amtStr})`;
    }
    const termDays = parseInt(targetMilestone.payment_term_days, 10) || 0;
    if (termEl) termEl.textContent = `${termDays} ngày`;

    if (idInput) idInput.value = targetMilestone.id;

    // Default trigger date: existing trigger_date, or today (15/10/2026 or current)
    const now = new Date();
    const todayStr = `${String(now.getDate()).padStart(2, "0")}/${String(now.getMonth() + 1).padStart(2, "0")}/${now.getFullYear()}`;
    if (dateInput) {
      dateInput.value = targetMilestone.trigger_date || todayStr;
    }

    if (resetBtn) {
      resetBtn.style.display = targetMilestone.triggered ? "inline-block" : "none";
    }

    this.onTriggerDateInputChanged();
    if (modal) modal.style.display = "flex";
  },

  closeTriggerModal() {
    const modal = document.getElementById("milestoneTriggerModal");
    if (modal) modal.style.display = "none";
    this.currentTriggerMilestone = null;
  },

  onTriggerDateInputChanged() {
    if (!this.currentTriggerMilestone) return;
    const dateInput = document.getElementById("tmTriggerDateInput");
    const dueEl = document.getElementById("tmCalculatedDueDate");
    const statusEl = document.getElementById("tmCalculatedStatusBadge");

    const dateStr = (dateInput?.value || "").trim();
    const termDays = parseInt(this.currentTriggerMilestone.payment_term_days, 10) || 0;

    const parts = dateStr.split(/[\/\-.]/);
    if (parts.length === 3) {
      const day = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const year = parseInt(parts[2], 10);

      const triggerDt = new Date(year, month, day);
      if (!isNaN(triggerDt.getTime())) {
        const dueDt = new Date(triggerDt.getTime());
        dueDt.setDate(dueDt.getDate() + termDays);

        const dueFormatted = `${String(dueDt.getDate()).padStart(2, "0")}/${String(dueDt.getMonth() + 1).padStart(2, "0")}/${dueDt.getFullYear()}`;
        if (dueEl) dueEl.textContent = dueFormatted;

        // Simulated today: October 15, 2026
        const simulatedToday = new Date(2026, 9, 15);
        const diffMs = dueDt.getTime() - simulatedToday.getTime();
        const daysLeft = Math.round(diffMs / (1000 * 60 * 60 * 24));

        if (statusEl) {
          if (daysLeft < 0) {
            statusEl.className = "badge-pill red";
            statusEl.textContent = `⚠️ ĐÃ TRỄ HẠN ${Math.abs(daysLeft)} NGÀY (Quá hạn thanh toán)`;
          } else if (daysLeft <= 10) {
            statusEl.className = "badge-pill amber";
            statusEl.textContent = `🔥 Sắp đến hạn (Còn ${daysLeft} ngày)`;
          } else {
            statusEl.className = "badge-pill green";
            statusEl.textContent = `✓ Trong hạn (Còn ${daysLeft} ngày)`;
          }
        }
        return;
      }
    }

    if (dueEl) dueEl.textContent = "Chưa hợp lệ";
    if (statusEl) {
      statusEl.className = "badge-pill";
      statusEl.textContent = "Nhập ngày DD/MM/YYYY";
    }
  },

  async submitTriggerMilestone() {
    const idInput = document.getElementById("tmActiveMilestoneId");
    const dateInput = document.getElementById("tmTriggerDateInput");
    const milestoneId = idInput?.value;
    const triggerDate = (dateInput?.value || "").trim();

    if (!milestoneId || !triggerDate) {
      alert("Vui lòng nhập ngày hoàn thành điều kiện.");
      return;
    }

    try {
      const response = await fetch(`/api/v1/dossier/milestones/${milestoneId}/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trigger_date: triggerDate })
      });
      const data = await response.json();
      if (!response.ok || data.status !== "success") {
        throw new Error(data.detail || data.message || "Không thể kích hoạt tính hạn.");
      }
      if (typeof showToast === "function") showToast(data.message, "success");
      this.closeTriggerModal();
      this.closeDossierModal();
      await this.loadSavedContracts();
    } catch (error) {
      if (typeof showToast === "function") showToast(error.message, "error");
      else alert(error.message);
    }
  },

  async submitResetMilestone() {
    const idInput = document.getElementById("tmActiveMilestoneId");
    const milestoneId = idInput?.value;
    if (!milestoneId) return;

    if (!confirm("Bạn có chắc chắn muốn hủy kích hoạt và đặt lại đợt thanh toán này về trạng thái chờ?")) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/dossier/milestones/${milestoneId}/reset`, {
        method: "POST"
      });
      const data = await response.json();
      if (!response.ok || data.status !== "success") {
        throw new Error(data.detail || data.message || "Không thể đặt lại đợt thanh toán.");
      }
      if (typeof showToast === "function") showToast(data.message, "success");
      this.closeTriggerModal();
      this.closeDossierModal();
      await this.loadSavedContracts();
    } catch (error) {
      if (typeof showToast === "function") showToast(error.message, "error");
      else alert(error.message);
    }
  },

  activateMilestone(milestoneId, contractCode = "") {
    this.openTriggerModal(milestoneId, contractCode);
  },

  openMarkPaidModal(milestoneId, contractCode, milestoneName, amount) {
    const modal = document.getElementById("markPaidModal");
    const nameEl = document.getElementById("mpMilestoneName");
    const codeEl = document.getElementById("mpContractCode");
    const expectedEl = document.getElementById("mpExpectedAmount");
    const dateInput = document.getElementById("mpPaidDateInput");
    const actualInput = document.getElementById("mpActualAmountInput");
    const invoiceInput = document.getElementById("mpInvoiceInput");
    const idInput = document.getElementById("mpActiveMilestoneId");

    if (nameEl) nameEl.textContent = milestoneName;
    if (codeEl) codeEl.textContent = contractCode;
    if (expectedEl) expectedEl.textContent = Number(amount || 0).toLocaleString("vi-VN") + " VND";
    if (actualInput) actualInput.value = amount || 0;
    if (idInput) idInput.value = milestoneId;
    if (invoiceInput) invoiceInput.value = "";

    const now = new Date();
    const todayStr = `${String(now.getDate()).padStart(2, "0")}/${String(now.getMonth() + 1).padStart(2, "0")}/${now.getFullYear()}`;
    if (dateInput) dateInput.value = todayStr;

    if (modal) modal.style.display = "flex";
  },

  closeMarkPaidModal() {
    const modal = document.getElementById("markPaidModal");
    if (modal) modal.style.display = "none";
  },

  async submitMarkPaid() {
    const idInput = document.getElementById("mpActiveMilestoneId");
    const dateInput = document.getElementById("mpPaidDateInput");
    const actualInput = document.getElementById("mpActualAmountInput");
    const invoiceInput = document.getElementById("mpInvoiceInput");

    const milestoneId = idInput?.value;
    if (!milestoneId) return;

    const paidDate = (dateInput?.value || "").trim();
    const amountVal = parseFloat(actualInput?.value || 0);
    const invoiceNo = (invoiceInput?.value || "").trim();

    try {
      const response = await fetch(`/api/v1/dossier/milestones/${milestoneId}/mark-paid`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          paid_date: paidDate,
          amount: amountVal,
          invoice_no: invoiceNo,
        }),
      });
      const data = await response.json();
      if (!response.ok || data.status !== "success") {
        throw new Error(data.detail || data.message || "Không thể xác nhận thanh toán.");
      }
      if (typeof showToast === "function") showToast(data.message, "success");
      this.closeMarkPaidModal();
      await this.loadSavedContracts();
    } catch (error) {
      if (typeof showToast === "function") showToast(error.message, "error");
      else alert(error.message);
    }
  },

  async revertPaidMilestone(milestoneId, contractCode, milestoneName) {
    if (!confirm(`Bạn có chắc chắn muốn hủy trạng thái đã thu tiền của "${milestoneName}" (HĐ: ${contractCode})?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/dossier/milestones/${milestoneId}/unmark-paid`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok || data.status !== "success") {
        throw new Error(data.detail || data.message || "Không thể hoàn tác thanh toán.");
      }
      if (typeof showToast === "function") showToast(data.message, "success");
      await this.loadSavedContracts();
    } catch (error) {
      if (typeof showToast === "function") showToast(error.message, "error");
      else alert(error.message);
    }
  },

  openChangeStatusModal(contractCode, currentStatus, currentNotes = "") {
    const modal = document.getElementById("changeContractStatusModal");
    const codeEl = document.getElementById("csContractCode");
    const codeInput = document.getElementById("csActiveContractCode");
    const selectEl = document.getElementById("csStatusSelect");
    const notesInput = document.getElementById("csNotesInput");

    if (codeEl) codeEl.textContent = contractCode;
    if (codeInput) codeInput.value = contractCode;
    if (selectEl) {
      let found = false;
      for (let i = 0; i < selectEl.options.length; i++) {
        if (selectEl.options[i].value === currentStatus) {
          selectEl.selectedIndex = i;
          found = true;
          break;
        }
      }
      if (!found && currentStatus) {
        const opt = new Option(currentStatus, currentStatus);
        selectEl.add(opt);
        selectEl.value = currentStatus;
      }
    }
    if (notesInput) notesInput.value = currentNotes || "";

    if (modal) modal.style.display = "flex";
  },

  closeChangeStatusModal() {
    const modal = document.getElementById("changeContractStatusModal");
    if (modal) modal.style.display = "none";
  },

  async submitChangeStatus() {
    const codeInput = document.getElementById("csActiveContractCode");
    const selectEl = document.getElementById("csStatusSelect");
    const notesInput = document.getElementById("csNotesInput");

    const contractCode = codeInput?.value;
    const newStatus = selectEl?.value;
    const notes = notesInput?.value;

    if (!contractCode || !newStatus) return;

    try {
      const response = await fetch(`/api/v1/dossier/contracts/${contractCode}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus, notes: notes }),
      });
      const data = await response.json();
      if (!response.ok || data.status !== "success") {
        throw new Error(data.detail || data.message || "Không thể cập nhật trạng thái.");
      }
      if (typeof showToast === "function") showToast(data.message, "success");
      this.closeChangeStatusModal();
      await this.loadSavedContracts();
    } catch (error) {
      if (typeof showToast === "function") showToast(error.message, "error");
      else alert(error.message);
    }
  },


  updateDossierCounters() {
    const total = this.cachedContracts.length;
    const urgent = this.cachedContracts.filter(c => c.has_urgent).length;
    const running = this.cachedContracts.filter(c => c.status && c.status.includes("Đang")).length;

    const elTotal = document.getElementById("countAllContracts");
    const elUrgent = document.getElementById("countUrgentContracts");
    const elRunning = document.getElementById("countRunningContracts");

    if (elTotal) elTotal.textContent = total;
    if (elUrgent) elUrgent.textContent = urgent;
    if (elRunning) elRunning.textContent = running;
  },

  onDossierFilter(filterType, btnEl) {
    this.activeDossierFilter = filterType;
    document.querySelectorAll(".contract-dossier-panel .filter-pill").forEach(b => b.classList.remove("active"));
    if (btnEl) btnEl.classList.add("active");
    this.renderDossierCards();
  },

  onDossierSearch(query) {
    this.dossierSearchQuery = (query || "").toLowerCase().trim();
    this.renderDossierCards();
  },

  renderDossierCards() {
    const container = document.getElementById("dossierCardsList");
    if (!container) return;

    let list = this.cachedContracts;

    // Apply Filter
    if (this.activeDossierFilter === "urgent") {
      list = list.filter(c => c.has_urgent);
    } else if (this.activeDossierFilter === "running") {
      list = list.filter(c => c.status && c.status.includes("Đang"));
    }

    // Apply Search
    if (this.dossierSearchQuery) {
      list = list.filter(c => {
        const text = `${c.contract_code} ${c.customer_name_vi} ${c.customer_name_zh || ""} ${c.project_name_vi}`.toLowerCase();
        return text.includes(this.dossierSearchQuery);
      });
    }

    if (list.length === 0) {
      if (this.cachedContracts.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; padding: 2.5rem 1.5rem; color: #475569; background: #ffffff; border-radius: 8px; border: 1.5px dashed #cbd5e1;">
            <svg class="icon" style="width: 40px; height: 40px; margin-bottom: 0.75rem; color: #94a3b8;" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <div style="font-weight: 700; font-size: 1rem; color: #1e293b; margin-bottom: 0.4rem;">Chưa Có Hợp Đồng Nào Trong Hồ Sơ</div>
            <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 1rem; max-width: 480px; margin-left: auto; margin-right: auto;">
              Danh sách hiện đang trống. Hãy tạo hợp đồng mua bán mới và bấm <strong>"💾 Lưu Hợp Đồng Vào Hồ Sơ"</strong> để tự động xuất hiện tại đây và theo dõi đợt thanh toán!
            </p>
            <a href="/contracts" class="btn btn-primary btn-sm" style="display: inline-flex; align-items: center; gap: 0.4rem;">
              <span>➕ Chuyển Sang Tạo Hợp Đồng Mới</span>
            </a>
          </div>
        `;
      } else {
        container.innerHTML = `
          <div style="text-align: center; padding: 2rem; color: #64748b; background: #ffffff; border-radius: 8px; border: 1px dashed #cbd5e1;">
            <svg class="icon" style="width: 32px; height: 32px; margin-bottom: 0.5rem; color: #94a3b8;" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <div>Không tìm thấy hợp đồng nào phù hợp với bộ lọc hiện tại.</div>
          </div>
        `;
      }
      return;
    }

    container.innerHTML = "";
    list.forEach(c => {
      const card = document.createElement("div");
      card.className = `dossier-card ${c.has_urgent ? "urgent" : ""}`;

      // Format currency
      const totalStr = (c.total_amount ? Number(c.total_amount).toLocaleString("vi-VN") : "0") + " VND";
      const paidStr = (c.paid_amount ? Number(c.paid_amount).toLocaleString("vi-VN") : "0") + " VND";
      const remainStr = (c.con_lai ? Number(c.con_lai).toLocaleString("vi-VN") : "0") + " VND";

      // Milestones HTML
      let milestonesHtml = "";
      if (Array.isArray(c.milestones) && c.milestones.length > 0) {
        c.milestones.forEach((ms, index) => {
          const isOverdue = ms.status === "OVERDUE";
          const isUrgent = ms.status === "URGENT";
          const isPaid = ms.status === "PAID";
          const isRunning = ms.status === "IN_PROGRESS";
          const badgeClass = isOverdue ? "overdue" : isUrgent ? "urgent" : isPaid ? "paid" : isRunning ? "running" : "";
          
          let countdownText = "";
          if (isPaid) {
            countdownText = "✓ Đã thu đủ";
          } else if (!ms.triggered) {
            countdownText = `Chưa bắt đầu tính hạn · T/T ${ms.payment_term_days || 0} ngày`;
          } else if (ms.days_left !== null && ms.days_left !== undefined) {
            if (ms.days_left < 0) {
              countdownText = `⚠️ Quá hạn ${Math.abs(ms.days_left)} ngày (Hạn: ${ms.due_date})`;
            } else if (ms.days_left <= 10) {
              countdownText = `🔥 Còn ${ms.days_left} ngày (Hạn: ${ms.due_date})`;
            } else {
              countdownText = `Hạn: ${ms.due_date} (Còn ${ms.days_left} ngày)`;
            }
          } else {
            countdownText = `Hạn: ${ms.due_date || "Chưa xác định"}`;
          }

          const msAmountStr = Number(ms.amount).toLocaleString("vi-VN") + "đ";
          const isImmediate = this.isImmediateFirstMilestone(ms, index);

          milestonesHtml += `
            <div class="milestone-badge-card ${badgeClass}">
              <span style="font-weight: 700;">${this.escapeHtml(ms.milestone_name)} (${ms.percentage}% - ${msAmountStr}):</span>
              <span>${this.escapeHtml(countdownText)}</span>
              ${!isPaid ? `
                ${!ms.triggered ? `
                  <button type="button" class="btn btn-outline btn-sm" onclick="ReminderEditor.openTriggerModal(${ms.id}, '${c.contract_code}')" style="padding: 2px 8px; font-size: 0.72rem; margin-left: 0.25rem; font-weight: 700; color: #1d4ed8; border-color: #93c5fd; background: #eff6ff;">
                    ✓ Đánh Dấu Điều Kiện
                  </button>
                ` : `
                  <button type="button" class="btn btn-outline btn-sm" onclick="ReminderEditor.openTriggerModal(${ms.id}, '${c.contract_code}')" style="padding: 2px 6px; font-size: 0.72rem; margin-left: 0.25rem;" title="Xem hoặc chỉnh sửa ngày kích hoạt">
                    ⚙️ Đổi Ngày
                  </button>
                `}
                ${!isImmediate ? `
                  <button type="button" class="btn btn-primary btn-sm" onclick="ReminderEditor.selectAndGenerateSheet('${c.contract_code}', '${this.escapeHtml(ms.milestone_name)}', true, this)" style="padding: 2px 8px; font-size: 0.72rem; margin-left: 0.25rem;">
                    👉 Tạo Phiếu Yêu Cầu TT
                  </button>
                ` : `
                  <span style="font-size: 0.7rem; color: #475569; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; margin-left: 0.25rem; font-weight: 600; border: 1px dashed #cbd5e1;" title="Đợt thanh toán ngay theo điều khoản ký hợp đồng (không cần tạo phiếu yêu cầu thanh toán)">
                    ⚡ TT ngay khi ký
                  </span>
                `}
                <button type="button" class="btn btn-sm" onclick="ReminderEditor.openMarkPaidModal(${ms.id}, '${c.contract_code}', '${this.escapeHtml(ms.milestone_name)}', ${ms.amount})" style="padding: 2px 8px; font-size: 0.72rem; margin-left: 0.25rem; font-weight: 750; color: #ffffff; background: #059669; border: 1px solid #047857;" title="Xác nhận khách hàng đã thanh toán đợt này">
                  💰 Xác Nhận Đã Thu
                </button>
              ` : `
                <span style="font-size: 0.75rem; color: #166534; font-weight: 700; margin-left: 0.25rem;">
                  (Đã thu: ${this.escapeHtml(ms.paid_date || 'Đủ')})
                </span>
                <button type="button" class="btn btn-outline btn-sm" onclick="ReminderEditor.revertPaidMilestone(${ms.id}, '${c.contract_code}', '${this.escapeHtml(ms.milestone_name)}')" style="padding: 1px 6px; font-size: 0.68rem; margin-left: 0.25rem; color: #b45309; border-color: #fde68a; background: #fffbeb;" title="Hủy xác nhận thanh toán">
                  ↩️ Hoàn tác
                </button>
              `}
            </div>
          `;
        });
      } else {
        milestonesHtml = "<span style='font-size: 0.8rem; color: #94a3b8;'>Chưa có đợt thanh toán được lập chỉ mục.</span>";
      }

      // Linked Files HTML
      let filesHtml = "";
      if (Array.isArray(c.documents) && c.documents.length > 0) {
        c.documents.forEach(doc => {
          const ext = (doc.file_format || "file").toLowerCase();
          const sizeKb = doc.file_size ? Math.round(doc.file_size / 1024) + " KB" : "";
          filesHtml += `
            <div class="file-chip ${ext}">
              <svg class="icon" style="width: 13px; height: 13px;" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <strong style="font-size: 0.72rem;">${this.escapeHtml(doc.doc_type)}:</strong>
              <span title="${this.escapeHtml(doc.file_name)}">${this.escapeHtml(doc.file_name)}</span>
              <small style="opacity: 0.75;">(${sizeKb})</small>
              <a href="/api/v1/dossier/documents/${doc.id}/download" download class="btn btn-outline btn-sm" style="padding: 1px 6px; font-size: 0.68rem; margin-left: 0.2rem; background: #ffffff;" title="Tải về máy tính">
                Tải về
              </a>
              <button type="button" class="btn btn-outline btn-sm" onclick="openSystemPath('${this.escapeHtml(doc.file_path || '').replace(/\\/g, '\\\\')}', this)" style="padding: 1px 6px; font-size: 0.68rem; background: #ffffff;" title="Mở trực tiếp file bằng Word / Excel">
                📂 Mở file
              </button>
              <button type="button" class="btn btn-outline btn-sm" onclick="addDriveFileToAttachments('${this.escapeHtml(doc.file_name)}')" style="padding: 1px 6px; font-size: 0.68rem; background: #ffffff;" title="Đính kèm file này vào email">
                + Đính kèm
              </button>
              <button type="button" class="btn btn-outline btn-sm" onclick="deleteDossierDocument(${doc.id}, '${this.escapeHtml(doc.file_name)}', event)" style="padding: 1px 6px; font-size: 0.68rem; color: #dc2626; border-color: #fca5a5; background: #fffafa;" title="Xóa file này khỏi hệ thống và máy tính">
                🗑️ Xóa
              </button>
            </div>
          `;
        });
      } else {
        filesHtml = "<span style='font-size: 0.75rem; color: #94a3b8;'>Chưa có file hồ sơ nào được liên kết với mã HĐ này.</span>";
      }

      card.innerHTML = `
        <div class="dossier-header-row">
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
              <span class="contract-code-tag">${this.escapeHtml(c.contract_code)}</span>
              <strong style="font-size: 0.98rem; color: #0f172a;">${this.escapeHtml(c.customer_name_vi)}</strong>
              ${c.customer_name_zh ? `<span style="font-size: 0.8rem; color: #475569;">(${this.escapeHtml(c.customer_name_zh)})</span>` : ""}
              ${c.has_urgent ? `<span class="badge-pill amber" style="font-size: 0.7rem; padding: 1px 6px;">🔥 Có đợt đến hạn</span>` : ""}
              <button type="button" class="btn btn-outline btn-sm" onclick="ReminderEditor.openChangeStatusModal('${c.contract_code}', '${this.escapeHtml(c.status || '')}', '${this.escapeHtml(c.notes || '')}')" style="padding: 1px 7px; font-size: 0.68rem; margin-left: 0.35rem; color: #4338ca; border-color: #c7d2fe; background: #eef2ff;" title="Cập nhật trạng thái tiến độ hợp đồng">
                ✏️ Đổi Trạng Thái
              </button>
            </div>
            <div style="font-size: 0.82rem; color: #334155; margin-top: 0.25rem;">
              <strong>Dự án:</strong> ${this.escapeHtml(c.project_name_vi)}
              ${c.lead_engineer ? ` · <strong>Kỹ thuật:</strong> ${this.escapeHtml(c.lead_engineer)}` : ""}
              ${c.signed_date ? ` · <strong>Ký ngày:</strong> ${this.escapeHtml(c.signed_date)}` : ""}
            </div>
          </div>

          <div style="text-align: right;">
            <div style="font-size: 0.8rem; color: #64748b;">Tổng giá trị HĐ: <strong style="font-size: 0.95rem; color: #1e3a8a;">${totalStr}</strong></div>
            <div style="font-size: 0.78rem; color: #166534; margin-top: 0.15rem;">Đã thu: <strong>${paidStr}</strong> (${c.ty_le_thu}) · Còn lại: <strong>${remainStr}</strong></div>
            <div style="width: 180px; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; margin-top: 0.35rem; display: inline-block;">
              <div style="width: ${c.ty_le_thu}; height: 100%; background: #2563eb; border-radius: 3px;"></div>
            </div>
          </div>
        </div>

        <div>
          <span style="font-size: 0.76rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.03em;">Mốc Thời Hạn Thanh Toán:</span>
          <div class="milestone-strip">
            ${milestonesHtml}
          </div>
        </div>

        <div class="files-badge-list">
          <span style="font-size: 0.74rem; font-weight: 700; color: #475569; display: flex; align-items: center; gap: 0.3rem;">
            <svg class="icon" style="width: 12px; height: 12px;" viewBox="0 0 24 24"><path d="M21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
            Hồ Sơ Liên Kết:
          </span>
          ${filesHtml}
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.65rem; border-top: 1px solid #f1f5f9; padding-top: 0.5rem;">
          <button type="button" class="btn btn-outline btn-sm" onclick="ReminderEditor.openContractDossierModal('${c.contract_code}')" style="font-size: 0.75rem;">
            <svg class="icon" style="width: 13px; height: 13px;" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="13" r="3"/></svg>
            <span>Xem Chi Tiết Hồ Sơ & Điều Khoản</span>
          </button>
          <button type="button" class="btn btn-outline btn-sm" onclick="ReminderEditor.onDeleteContract('${c.contract_code}', event)" style="font-size: 0.75rem; color: #dc2626; border-color: #fca5a5; background: #fffafa;" title="Xóa hợp đồng này khỏi hồ sơ theo dõi">
            <svg class="icon" style="width: 13px; height: 13px;" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
            <span>🗑️ Xóa HĐ</span>
          </button>
        </div>
      `;

      container.appendChild(card);
    });
  },

  /**
   * Primary action: User picks contract milestone -> Server creates Excel 712TR + Word and populates Email Draft.
   */
  async selectAndGenerateSheet(contractCode, milestoneName, shouldScroll = true, btnEl = null) {
    const templateSource = document.getElementById("paymentRequestTemplateSource")?.value || "excel";
    const templateLabel = templateSource === "word" ? "Word (.docx)" : "Excel (sheet 712TR)";

    // 1. Phản hồi trực quan tức thì trên nút bấm
    let originalBtnHtml = "";
    if (btnEl) {
      originalBtnHtml = btnEl.innerHTML;
      btnEl.innerHTML = `<span style="display: inline-flex; align-items: center; gap: 4px;"><span style="width: 10px; height: 10px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; display: inline-block; animation: spin 0.8s linear infinite;"></span> Đang tạo...</span>`;
      btnEl.disabled = true;
    }

    // Lưu lại HĐ và đợt active để AI đối chiếu
    this.activeContractCode = contractCode;
    this.activeMilestoneName = milestoneName;
    const aiBadge = document.getElementById("aiActiveContractBadge");
    if (aiBadge) {
      aiBadge.textContent = `${contractCode} (${milestoneName})`;
    }

    // 2. Cuộn ngay lập tức xuống Bước Soạn Thư Email
    const emailSection = document.getElementById("step3EmailSection");
    if (shouldScroll && emailSection) {
      emailSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    if (window.showToast) {
      window.showToast(`Đang tạo phiếu yêu cầu thanh toán (${templateLabel}) cho ${milestoneName}...`, "info");
    }

    try {
      const res = await fetch("/api/v1/reminders/generate-sheet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contract_code: contractCode,
          milestone_name: milestoneName,
          template_source: templateSource
        })
      });

      const data = await res.json();
      if (data.status === "success") {
        this.currentGeneratedFile = data.primary_file_name || data.file_name;
        this.currentGeneratedWordFile = data.word_file_name || "";

        // 1. Populate Step 2 (Email Form) values
        this.populateStep3FromSheetData(data.sheet_data, data.file_name, data.word_file_name, data.template_source);

        // 2. Tự động reload lại danh sách hồ sơ SQLite để hiện ngay tệp mới vừa tạo vào thẻ HĐ & modal
        await this.loadSavedContracts();

        // 3. Update Live Email Preview & Print Preview
        await handleRefreshReminderPreview();

        // 4. Thêm hiệu ứng highlight viền nổi bật cho Bước Soạn Thư Email
        if (emailSection) {
          emailSection.classList.remove("section-highlight");
          void emailSection.offsetWidth; // trigger reflow
          emailSection.classList.add("section-highlight");
        }

        if (window.showToast) {
          window.showToast(`✅ Đã tạo Phiếu Yêu Cầu TT (${milestoneName}) và đính kèm vào email!`, "success");
        }
      } else {
        if (window.showToast) {
          window.showToast(`Lỗi tạo phiếu: ${data.message}`, "error");
        }
      }
    } catch (err) {
      console.error("Error generating sheet:", err);
      if (window.showToast) {
        window.showToast(`Lỗi kết nối máy chủ: ${err.message}`, "error");
      }
    } finally {
      if (btnEl && originalBtnHtml) {
        btnEl.innerHTML = originalBtnHtml;
        btnEl.disabled = false;
      }
    }
  },

  populateStep3FromSheetData(sheetData, fileName, wordFileName = "", templateSource = "excel") {
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val;
    };

    setVal("custNameVi", sheetData.customer_name_vi || "");
    setVal("custNameZh", sheetData.customer_name_zh || "");
    setVal("emailToInput", "nguyensykimbang321@gmail.com");
    setVal("emailCcInput", "pm02@hongming-global.com, sales@hongming-global.com");
    setVal("docCodeInput", sheetData.form_no || "HM-PR-20261013-001");

    const dueDateEl = document.getElementById("summaryDueDate");
    if (dueDateEl) dueDateEl.textContent = sheetData.due_date || "25/10/2026";

    // Set Subject
    const subject = `【宏明環球】合約編號 ${sheetData.contract_code} ${sheetData.milestone_name}款項到期提醒 / Yêu cầu hỗ trợ thanh toán ${sheetData.milestone_name} HĐ ${sheetData.contract_code} (${sheetData.customer_name_vi})`;
    setVal("emailSubjectInput", subject);

    // Set Cathay Bank Details
    setVal("bankOwnerInput", "CÔNG TY TNHH TOÀN CẦU HONG MING");
    setVal("bankAccInput", "604080006546(VND)");
    setVal("bankNameInput", "CATHAY UNITED BANK – HO CHI MINH CITY BRANCH");

    // Tự động đính kèm cả Excel và Word mới tạo; giữ các tài liệu khác.
    const currentAttachRaw = document.getElementById("attachmentsInput")?.value || "";
    const otherAttachments = currentAttachRaw
      .replace(/;/g, ",")
      .split(/[,\n]/)
      .map(s => s.trim())
      .filter(s => s && !s.toLowerCase().includes("đơn yêu cầu") && !s.toLowerCase().includes("yeu cau thanh toan"));

    const generatedFiles = (templateSource === "word" ? [wordFileName, fileName] : [fileName, wordFileName]).filter(Boolean);
    const attachList = [...generatedFiles, ...otherAttachments];
    if (attachList.length === generatedFiles.length && (fileName.includes("CX") || (sheetData.customer_name_vi && sheetData.customer_name_vi.includes("CX")))) {
      attachList.push("001_BIEN_BAN_NGHIEM_THU_BAN_GIAO_CX_.docx");
    }
    setVal("attachmentsInput", attachList.join(", "));
    this.renderVisualAttachmentsList();

    // Update payment items table
    const tbody = document.getElementById("paymentTableBody");
    if (tbody) {
      tbody.innerHTML = "";
      this.addRow({
        so_hop_dong: sheetData.contract_code,
        hang_muc: `${sheetData.project_name_vi} (${sheetData.milestone_name} - ${sheetData.percentage}%)`,
        noi_dung: `產品上線移交使用款 : ${sheetData.percentage}%`,
        so_tien: sheetData.milestone_amount,
        vat_info: sheetData.invoice_no && sheetData.invoice_no !== "Chưa xuất" ? `HĐ ${sheetData.invoice_no}` : "Chưa gồm VAT",
        han_thanh_toan: sheetData.due_date
      });
    }

    this.recalculate();
  },

  scrollToEmailSection() {
    const el = document.getElementById("step3EmailSection");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  },

  loadSampleCXTech() {
    if (this.cachedContracts.some(c => c.contract_code === "HMV151020250001")) {
      this.selectAndGenerateSheet("HMV151020250001", "Đợt 2", true);
    } else if (this.cachedContracts.length > 0) {
      const c = this.cachedContracts[0];
      const nonImmediateMs = (c.milestones || []).find((m, i) => !this.isImmediateFirstMilestone(m, i));
      const targetMs = nonImmediateMs ? nonImmediateMs.milestone_name : (c.milestones && c.milestones[0] ? c.milestones[0].milestone_name : "Đợt 2");
      this.selectAndGenerateSheet(c.contract_code, targetMs, true);
    } else {
      if (window.showToast) {
        window.showToast("Chưa có hợp đồng nào. Hãy tạo hợp đồng mới và bấm Lưu!", "info");
      } else {
        alert("Chưa có hợp đồng nào. Hãy tạo hợp đồng mới và bấm Lưu!");
      }
    }
  },

  async onDeleteContract(contractCode, event) {
    if (event) event.stopPropagation();
    if (!confirm(`Bạn có chắc chắn muốn xóa hợp đồng "${contractCode}" và toàn bộ hồ sơ, đợt thanh toán liên quan khỏi hệ thống không?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/dossier/contracts/${encodeURIComponent(contractCode)}`, {
        method: "DELETE"
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        if (window.showToast) {
          window.showToast(`Đã xóa thành công hợp đồng ${contractCode}`, "success");
        } else {
          alert(`Đã xóa thành công hợp đồng ${contractCode}`);
        }
        await this.loadSavedContracts();
      } else {
        alert(data.message || "Không thể xóa hợp đồng.");
      }
    } catch (err) {
      alert("Lỗi khi xóa hợp đồng: " + err.message);
    }
  },

  async onClearAllDummyContracts() {
    const confirmed = confirm(
      "⚠️ CẢNH BÁO: Thao tác này sẽ XÓA TOÀN BỘ hợp đồng và đợt thanh toán hiện có trong cơ sở dữ liệu để bạn bắt đầu tạo các hợp đồng thực tế mới!\n\nBạn có chắc chắn muốn dọn dẹp dữ liệu rác không?"
    );
    if (!confirmed) return;

    try {
      const res = await fetch("/api/v1/dossier/contracts/clear-all", {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        if (window.showToast) {
          window.showToast(`Đã dọn dẹp thành công ${data.deleted_count} hợp đồng mẫu!`, "success");
        } else {
          alert(`Đã dọn dẹp thành công ${data.deleted_count} hợp đồng mẫu!`);
        }
        this.currentGeneratedFile = "";
        await this.loadSavedContracts();
      } else {
        alert(data.message || "Không thể dọn dẹp dữ liệu.");
      }
    } catch (err) {
      alert("Lỗi khi dọn dẹp dữ liệu: " + err.message);
    }
  },

  openContractDossierModal(contractCode) {
    const c = this.cachedContracts.find(item => item.contract_code === contractCode);
    if (!c) return;

    const modal = document.getElementById("contractDossierModal");
    const titleCode = document.getElementById("modalContractCode");
    const titleCust = document.getElementById("modalCustomerName");
    const projName = document.getElementById("modalProjectName");
    const bodyEl = document.getElementById("modalDossierBody");

    if (titleCode) titleCode.textContent = c.contract_code;
    if (titleCust) titleCust.textContent = c.customer_name_vi;
    if (projName) projName.textContent = `${c.project_name_vi} · Kỹ thuật phụ trách: ${c.lead_engineer || "Jenson Chang"}`;

    const totalStr = (c.total_amount ? Number(c.total_amount).toLocaleString("vi-VN") : "0") + " VND";
    const paidStr = (c.paid_amount ? Number(c.paid_amount).toLocaleString("vi-VN") : "0") + " VND";
    const remainStr = (c.con_lai ? Number(c.con_lai).toLocaleString("vi-VN") : "0") + " VND";

    let milestonesTableRows = "";
    if (Array.isArray(c.milestones)) {
      c.milestones.forEach((m, idx) => {
        const amtStr = Number(m.amount).toLocaleString("vi-VN") + " đ";
        const isPaid = m.status === "PAID";
        const isImmediate = this.isImmediateFirstMilestone(m, idx);
        const badgeColor = isPaid ? "color: #166534; background: #f0fdf4; border: 1px solid #bbf7d0;" : "color: #b45309; background: #fffbeb; border: 1px solid #fcd34d;";
        milestonesTableRows += `
          <tr>
            <td style="text-align: center; font-weight: 600;">${idx + 1}</td>
            <td><strong>${this.escapeHtml(m.milestone_name)}</strong></td>
            <td style="text-align: center;">${m.percentage}%</td>
            <td style="text-align: right; font-weight: 700; color: #1e3a8a;">${amtStr}</td>
            <td>${this.escapeHtml(m.trigger_condition || "Theo thỏa thuận HĐ")}</td>
            <td style="text-align: center; font-weight: 600;">${m.triggered ? this.escapeHtml(m.due_date || "-") : `Chờ kích hoạt<br><small>T/T ${m.payment_term_days || 0} ngày</small>`}</td>
            <td style="text-align: center;">${this.escapeHtml(m.invoice_no || "-")}</td>
            <td style="text-align: center;">
              <span style="font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; ${badgeColor}">${this.escapeHtml(m.status_label || m.status)}</span>
            </td>
            <td style="text-align: center;">
              ${!isPaid ? `
                ${!m.triggered ? `
                  <button type="button" class="btn btn-outline btn-sm" onclick="ReminderEditor.openTriggerModal(${m.id}, '${c.contract_code}')" style="padding: 2px 8px; font-size: 0.72rem; margin-bottom: 0.25rem; font-weight: 700; color: #1d4ed8; border-color: #93c5fd; background: #eff6ff;">
                    ✓ Hoàn Thành Điều Kiện
                  </button><br>
                ` : `
                  <button type="button" class="btn btn-outline btn-sm" onclick="ReminderEditor.openTriggerModal(${m.id}, '${c.contract_code}')" style="padding: 2px 6px; font-size: 0.72rem; margin-bottom: 0.25rem;">
                    ⚙️ Đổi Ngày
                  </button><br>
                `}
                ${!isImmediate ? `
                  <button type="button" class="btn btn-primary btn-sm" onclick="ReminderEditor.closeDossierModal(); ReminderEditor.selectAndGenerateSheet('${c.contract_code}', '${this.escapeHtml(m.milestone_name)}')" style="padding: 2px 8px; font-size: 0.72rem; margin-bottom: 0.25rem;">
                    Tạo Phiếu Đợt Này
                  </button><br>
                ` : `
                  <span style="display: inline-block; font-size: 0.7rem; color: #475569; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; margin-bottom: 0.25rem; font-weight: 600; border: 1px dashed #cbd5e1;">
                    ⚡ TT ngay khi ký
                  </span><br>
                `}
                <button type="button" class="btn btn-sm" onclick="ReminderEditor.closeDossierModal(); ReminderEditor.openMarkPaidModal(${m.id}, '${c.contract_code}', '${this.escapeHtml(m.milestone_name)}', ${m.amount})" style="padding: 2px 8px; font-size: 0.72rem; font-weight: 750; color: #ffffff; background: #059669; border: 1px solid #047857;" title="Xác nhận khách hàng đã thanh toán đợt này">
                  💰 Xác Nhận Đã Thu
                </button>
              ` : `
                <span style="font-size: 0.75rem; color: #166534; font-weight: 700;">Đã thu: ${this.escapeHtml(m.paid_date || 'Đủ')}</span>
                <br>
                <button type="button" class="btn btn-outline btn-sm" onclick="ReminderEditor.closeDossierModal(); ReminderEditor.revertPaidMilestone(${m.id}, '${c.contract_code}', '${this.escapeHtml(m.milestone_name)}')" style="padding: 1px 6px; font-size: 0.68rem; margin-top: 0.2rem; color: #b45309; border-color: #fde68a; background: #fffbeb;" title="Hủy xác nhận thanh toán">
                  ↩️ Hoàn tác
                </button>
              `}
            </td>
          </tr>
        `;
      });
    }

    let docsListHtml = "";
    if (Array.isArray(c.documents) && c.documents.length > 0) {
      c.documents.forEach(d => {
        const sizeKb = d.file_size ? Math.round(d.file_size / 1024) + " KB" : "";
        docsListHtml += `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0.75rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 0.4rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span class="badge-pill blue" style="font-size: 0.7rem;">${this.escapeHtml(d.doc_type)}</span>
              <strong style="font-size: 0.82rem; color: #0f172a;">${this.escapeHtml(d.file_name)}</strong>
              <small style="color: #64748b;">(${sizeKb})</small>
            </div>
            <div style="display: flex; gap: 0.35rem; align-items: center; flex-wrap: wrap;">
              <a href="/api/v1/dossier/documents/${d.id}/download" download class="btn btn-outline btn-sm" style="padding: 2px 8px; font-size: 0.72rem;">
                Tải Về
              </a>
              <button type="button" class="btn btn-outline btn-sm" onclick="openSystemPath('${this.escapeHtml(d.file_path || '').replace(/\\/g, '\\\\')}', this)" style="padding: 2px 8px; font-size: 0.72rem;" title="Mở trực tiếp file bằng Word / Excel">
                📂 Mở File
              </button>
              <button type="button" class="btn btn-outline btn-sm" onclick="addDriveFileToAttachments('${this.escapeHtml(d.file_name)}')" style="padding: 2px 8px; font-size: 0.72rem;">
                + Đính Kèm
              </button>
              <button type="button" class="btn btn-outline btn-sm" onclick="deleteDossierDocument(${d.id}, '${this.escapeHtml(d.file_name)}', event)" style="padding: 2px 8px; font-size: 0.72rem; color: #dc2626; border-color: #fca5a5; background: #fffafa;" title="Xóa file này khỏi hệ thống và xóa tệp trên máy tính">
                🗑️ Xóa File
              </button>
            </div>
          </div>
        `;
      });
    } else {
      docsListHtml = "<div style='color: #94a3b8; font-size: 0.82rem; padding: 0.5rem;'>Chưa có file nào liên kết với hợp đồng này.</div>";
    }

    if (bodyEl) {
      bodyEl.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1rem; background: #f1f5f9; padding: 0.85rem; border-radius: 8px;">
          <div><span style="font-size: 0.75rem; color: #64748b;">Tổng Giá Trị Hợp Đồng:</span><div style="font-weight: 700; color: #1e3a8a; font-size: 1.05rem;">${totalStr}</div></div>
          <div><span style="font-size: 0.75rem; color: #64748b;">Đã Thu:</span><div style="font-weight: 700; color: #166534; font-size: 1.05rem;">${paidStr} (${c.ty_le_thu})</div></div>
          <div><span style="font-size: 0.75rem; color: #64748b;">Công Nợ Còn Lại:</span><div style="font-weight: 700; color: #b45309; font-size: 1.05rem;">${remainStr}</div></div>
        </div>

        <h4 style="margin: 0.75rem 0 0.5rem 0; font-size: 0.92rem; color: #1e3a8a; display: flex; align-items: center; gap: 0.4rem;">
          <svg class="icon" style="width: 16px; height: 16px;" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Chi Tiết Tiến Độ Thanh Toán Các Đợt:
        </h4>
        <div style="overflow-x: auto; margin-bottom: 1.25rem;">
          <table class="modern-table" style="font-size: 0.82rem;">
            <thead>
              <tr>
                <th style="width: 40px; text-align: center;">STT</th>
                <th>Đợt TT</th>
                <th style="text-align: center;">Tỷ Lệ</th>
                <th style="text-align: right;">Số Tiền</th>
                <th>Điều Kiện Kích Hoạt</th>
                <th style="text-align: center;">Hạn TT</th>
                <th style="text-align: center;">Số HĐ VAT</th>
                <th style="text-align: center;">Trạng Thái</th>
                <th style="text-align: center;">Thao Tác</th>
              </tr>
            </thead>
            <tbody>
              ${milestonesTableRows}
            </tbody>
          </table>
        </div>

        <h4 style="margin: 0.75rem 0 0.5rem 0; font-size: 0.92rem; color: #1e3a8a; display: flex; align-items: center; gap: 0.4rem;">
          <svg class="icon" style="width: 16px; height: 16px;" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          Chuỗi Hồ Sơ & File Tài Liệu Đã Lưu Trong SQLite:
        </h4>
        <div>
          ${docsListHtml}
        </div>
      `;
    }

    if (modal) modal.style.display = "flex";
  },

  closeDossierModal() {
    const modal = document.getElementById("contractDossierModal");
    if (modal) modal.style.display = "none";
  },

  initTabs() {
    document.querySelectorAll(".tabs-nav .tab-btn[data-tab]").forEach(btn => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-tab");
        document.querySelectorAll(".tabs-nav .tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
        btn.classList.add("active");
        const targetEl = document.getElementById(targetId);
        if (targetEl) targetEl.classList.add("active");
      });
    });
  },

  searchGoogleDrive() {
    handleSearchDrive();
  },

  addRow(itemData = {}) {
    const tbody = document.getElementById("paymentTableBody");
    if (!tbody) return;

    const rowIdx = tbody.querySelectorAll("tr").length + 1;
    const tr = document.createElement("tr");

    const soHd = itemData.so_hop_dong || `HMV-2026-${String(rowIdx).padStart(3, "0")}`;
    const hangMuc = itemData.hang_muc || "";
    const noiDung = itemData.noi_dung || itemData.noi_dung_thanh_toan || "";
    const soTien = itemData.so_tien || "";
    const vatInfo = itemData.vat_info || "";
    const hanTt = itemData.han_thanh_toan || "";

    tr.innerHTML = `
      <td style="text-align: center; font-weight: 600; color: var(--text-muted);">${rowIdx}</td>
      <td>
        <input type="text" class="cell-input item-so-hd" value="${this.escapeHtml(soHd)}" placeholder="Mã HĐ" oninput="ReminderEditor.onItemChanged()">
      </td>
      <td>
        <input type="text" class="cell-input item-hang-muc" value="${this.escapeHtml(hangMuc)}" placeholder="Tên sản phẩm / dịch vụ" oninput="ReminderEditor.onItemChanged()">
      </td>
      <td>
        <input type="text" class="cell-input item-noi-dung" value="${this.escapeHtml(noiDung)}" placeholder="VD: Hợp đồng 50%" oninput="ReminderEditor.onItemChanged()">
      </td>
      <td>
        <input type="text" class="cell-input item-so-tien" value="${this.formatVndInput(soTien)}" placeholder="0" style="text-align: right; font-weight: 700; color: #047857;" oninput="ReminderEditor.onAmountInput(this)">
      </td>
      <td>
        <input type="text" class="cell-input item-vat" value="${this.escapeHtml(vatInfo)}" placeholder="含 VAT 8%" oninput="ReminderEditor.onItemChanged()">
      </td>
      <td>
        <input type="text" class="cell-input item-han-tt" value="${this.escapeHtml(hanTt)}" placeholder="YYYY/MM/DD" style="text-align: center; color: #b91c1c; font-weight: 600;" oninput="ReminderEditor.onItemChanged()">
      </td>
      <td style="text-align: center;">
        <button type="button" class="btn-icon text-danger" title="Xóa dòng" onclick="ReminderEditor.removeRow(this)">
          <svg class="icon" viewBox="0 0 24 24" style="width: 15px; height: 15px;"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </td>
    `;

    tbody.appendChild(tr);
    this.recalculate();
  },

  removeRow(btn) {
    const tr = btn.closest("tr");
    if (tr) {
      tr.remove();
      this.reindexRows();
      this.recalculate();
      handleRefreshReminderPreview();
    }
  },

  reindexRows() {
    const rows = document.querySelectorAll("#paymentTableBody tr");
    rows.forEach((r, idx) => {
      const tdFirst = r.querySelector("td");
      if (tdFirst) tdFirst.textContent = idx + 1;
    });
  },

  onAmountInput(inputEl) {
    const rawVal = inputEl.value.replace(/[^\d]/g, "");
    if (rawVal) {
      inputEl.value = Number(rawVal).toLocaleString("vi-VN");
    } else {
      inputEl.value = "";
    }
    this.recalculate();
    this.debounceRefresh();
  },

  onItemChanged() {
    this.debounceRefresh();
  },

  debounceTimer: null,
  debounceRefresh() {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      handleRefreshReminderPreview();
    }, 400);
  },

  onLevelChange() {
    const level = document.getElementById("reminderLevelSelect").value;
    const contracts = this.getContractNumbers();
    const hdStr = contracts.join("、") || "合約";
    const hdViStr = contracts.join(" và ") || "hợp đồng";

    let subject = "";
    let levelLabel = "Cấp 1: Lịch Sự";
    if (level === "1") {
      subject = `請協助安排付款 - ${hdStr} 合約款項 Yêu cầu hỗ trợ thanh toán - Hợp đồng ${hdViStr}`;
      levelLabel = "Cấp 1: Lịch Sự";
    } else if (level === "2") {
      subject = `【宏明環球】合約 ${hdStr} 款項到期提醒 - Đôn đốc thanh toán HĐ ${hdViStr}`;
      levelLabel = "Cấp 2: Đến Hạn";
    } else {
      subject = `【宏明環球】逾期應收帳款催收通知函 - CÔNG VĂN ĐÔN ĐỐC CÔNG NỢ QUÁ HẠN HĐ ${hdViStr}`;
      levelLabel = "Cấp 3: Công Văn Đòi Nợ";
    }

    const subEl = document.getElementById("emailSubjectInput");
    if (subEl) subEl.value = subject;

    const lblEl = document.getElementById("summaryLevelLabel");
    if (lblEl) lblEl.textContent = levelLabel;

    handleRefreshReminderPreview();
  },

  getContractNumbers() {
    const rows = document.querySelectorAll("#paymentTableBody tr");
    const list = [];
    rows.forEach(r => {
      const val = (r.querySelector(".item-so-hd")?.value || "").trim();
      if (val && !list.includes(val)) list.push(val);
    });
    return list;
  },

  recalculate() {
    const rows = document.querySelectorAll("#paymentTableBody tr");
    let sum = 0;
    const contracts = new Set();

    rows.forEach(r => {
      const soHd = (r.querySelector(".item-so-hd")?.value || "").trim();
      if (soHd) contracts.add(soHd);

      const amountStr = (r.querySelector(".item-so-tien")?.value || "").replace(/[^\d]/g, "");
      if (amountStr) sum += parseInt(amountStr, 10);
    });

    const sumContractsEl = document.getElementById("summaryContractCount");
    const sumTotalEl = document.getElementById("summaryTotalAmount");

    if (sumContractsEl) sumContractsEl.textContent = `${contracts.size} Hợp đồng`;
    if (sumTotalEl) sumTotalEl.textContent = `${sum.toLocaleString("vi-VN")} VND`;
  },

  switchView(viewMode) {
    this.currentView = viewMode;
    const btnEmail = document.getElementById("btnViewEmail");
    const btnDxyctt = document.getElementById("btnViewDxyctt");

    if (viewMode === "email") {
      if (btnEmail) btnEmail.className = "btn btn-sm btn-primary";
      if (btnDxyctt) btnDxyctt.className = "btn btn-sm btn-ghost";
    } else {
      if (btnEmail) btnEmail.className = "btn btn-sm btn-ghost";
      if (btnDxyctt) btnDxyctt.className = "btn btn-sm btn-primary";
    }

    this.renderCurrentView();
  },

  renderCurrentView() {
    const container = document.getElementById("reminderPreviewWrapper");
    if (!container) return;

    if (this.currentView === "email") {
      container.innerHTML = this.cachedEmailPreviewHtml || "<div class='preview-empty-state'>Chưa có bản xem trước email</div>";
    } else {
      container.innerHTML = this.cachedDxycttPreviewHtml || "<div class='preview-empty-state'>Chưa có bản xem trước văn bản</div>";
    }
  },

  getPayloadFromDom() {
    const rows = document.querySelectorAll("#paymentTableBody tr");
    const items = [];
    rows.forEach((r, idx) => {
      const soHd = (r.querySelector(".item-so-hd")?.value || "").trim();
      const hangMuc = (r.querySelector(".item-hang-muc")?.value || "").trim();
      const noiDung = (r.querySelector(".item-noi-dung")?.value || "").trim();
      const soTien = (r.querySelector(".item-so-tien")?.value || "").replace(/[^\d]/g, "");
      const vat = (r.querySelector(".item-vat")?.value || "").trim();
      const hanTt = (r.querySelector(".item-han-tt")?.value || "").trim();

      items.push({
        stt: idx + 1,
        so_hop_dong: soHd,
        hang_muc: hangMuc,
        noi_dung_thanh_toan: noiDung,
        so_tien: soTien,
        vat_info: vat,
        han_thanh_toan: hanTt
      });
    });

    const rawTo = document.getElementById("emailToInput")?.value || "";
    const rawCc = document.getElementById("emailCcInput")?.value || "";
    const rawAttach = document.getElementById("attachmentsInput")?.value || "";

    const emailToList = rawTo.replace(/;/g, ",").split(",").map(e => e.trim()).filter(Boolean);
    const emailCcList = rawCc.replace(/;/g, ",").split(",").map(e => e.trim()).filter(Boolean);
    const attachList = rawAttach.replace(/;/g, ",").split(/[,\n]/).map(a => a.trim()).filter(Boolean);

    return {
      cap_do: parseInt(document.getElementById("reminderLevelSelect")?.value || "1", 10),
      so_cong_van: document.getElementById("docCodeInput")?.value || "HM-PR-20261013-001",
      ngay_phat_hanh: "13/10/2026",
      khach_hang: {
        ten_khach_hang: document.getElementById("custNameVi")?.value || "CX Technology (VN)",
        ten_tieng_trung: document.getElementById("custNameZh")?.value || "CX Technology (VN)",
        email_to: emailToList,
        email_cc: emailCcList
      },
      khoan_thanh_toan: items,
      email_nguoi_gui: document.getElementById("emailSenderInput")?.value || "pm02@hongming-global.com",
      tieu_de_email: document.getElementById("emailSubjectInput")?.value || "",
      tai_khoan: {
        ten_tai_khoan: document.getElementById("bankOwnerInput")?.value || "CÔNG TY TNHH TOÀN CẦU HONG MING",
        so_tai_khoan: document.getElementById("bankAccInput")?.value || "604080006546(VND)",
        ngan_hang: document.getElementById("bankNameInput")?.value || "CATHAY UNITED BANK – HO CHI MINH CITY BRANCH"
      },
      danh_sach_dinh_kem: attachList,
      template_source: document.getElementById("paymentRequestTemplateSource")?.value || "excel"
    };
  },

  renderVisualAttachmentsList() {
    const container = document.getElementById("visualAttachmentsList");
    const input = document.getElementById("attachmentsInput");
    const badge = document.getElementById("attachmentsCountBadge");
    if (!container || !input) return;

    const raw = (input.value || "").trim();
    const files = raw ? raw.split(",").map(s => s.trim()).filter(Boolean) : [];

    if (badge) badge.textContent = `${files.length} tệp`;

    if (files.length === 0) {
      container.innerHTML = `
        <div style="padding: 1rem; text-align: center; background: #ffffff; border: 1.5px dashed #cbd5e1; border-radius: 8px; color: #94a3b8; font-size: 0.85rem;">
          Chưa có tệp đính kèm nào. Hãy bấm nút <strong>"⚡ Tạo / Làm Mới Phiếu Thanh Toán"</strong> hoặc <strong>"Thêm File Từ Máy Tính"</strong> ở trên!
        </div>
      `;
      return;
    }

    let html = "";
    files.forEach((file, index) => {
      const ext = file.split(".").pop().toLowerCase();
      let iconClass = "attach-icon-pdf";
      let badgeText = "PDF";
      let borderClr = "#fecaca";
      let bgClr = "#fff5f5";
      
      if (ext === "xlsx" || ext === "xls") {
        iconClass = "attach-icon-xlsx";
        badgeText = "XLSX";
        borderClr = "#bbf7d0";
        bgClr = "#f0fdf4";
      } else if (ext === "docx" || ext === "doc") {
        iconClass = "attach-icon-docx";
        badgeText = "DOCX";
        borderClr = "#bfdbfe";
        bgClr = "#eff6ff";
      } else if (ext !== "pdf") {
        iconClass = "attach-icon-file";
        badgeText = ext.toUpperCase().slice(0, 4);
        borderClr = "#e2e8f0";
        bgClr = "#f8fafc";
      }

      const isPaymentRequest = file.toLowerCase().includes("đơn yêu cầu") || file.toLowerCase().includes("yeu cau thanh toan");
      const tagHtml = isPaymentRequest
        ? `<span style="font-size: 0.7rem; background: #dcfce7; color: #166534; font-weight: 700; padding: 2px 7px; border-radius: 4px; border: 1px solid #86efac;">✓ Phiếu YCTT 1:1</span>`
        : `<span style="font-size: 0.7rem; background: #e0f2fe; color: #0369a1; font-weight: 600; padding: 2px 7px; border-radius: 4px; border: 1px solid #bae6fd;">Chứng từ nghiệm thu / hồ sơ</span>`;

      html += `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.65rem 0.95rem; background: ${bgClr}; border: 1px solid ${borderClr}; border-radius: 8px; gap: 0.75rem; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
          <div style="display: flex; align-items: center; gap: 0.75rem; min-width: 0; flex: 1;">
            <div class="${iconClass}" style="flex-shrink: 0;">${badgeText}</div>
            <div style="min-width: 0; flex: 1;">
              <div style="font-weight: 700; font-size: 0.85rem; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${this.escapeHtml(file)}">
                ${this.escapeHtml(file)}
              </div>
              <div style="margin-top: 3px; display: flex; align-items: center; gap: 0.4rem;">
                ${tagHtml}
                <span style="font-size: 0.72rem; color: #64748b;">${ext === "xlsx" ? "10.7 KB" : ext === "docx" ? "35.9 KB" : ""}</span>
              </div>
            </div>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" onclick="ReminderEditor.removeAttachment(${index})" style="color: #dc2626; padding: 3px 8px; font-size: 0.75rem; border: 1px solid #fca5a5; background: #ffffff; flex-shrink: 0;" title="Gỡ bỏ tệp này khỏi danh sách gửi">
            ✕ Xóa
          </button>
        </div>
      `;
    });

    container.innerHTML = html;
  },

  removeAttachment(index) {
    const input = document.getElementById("attachmentsInput");
    if (!input) return;
    const files = (input.value || "").split(",").map(s => s.trim()).filter(Boolean);
    if (index >= 0 && index < files.length) {
      const removed = files.splice(index, 1);
      input.value = files.join(", ");
      this.renderVisualAttachmentsList();
      handleRefreshReminderPreview();
      if (window.showToast) window.showToast(`Đã gỡ tệp "${removed[0]}"`, "info");
    }
  },

  onAttachmentsInputChanged() {
    this.renderVisualAttachmentsList();
    handleRefreshReminderPreview();
  },

  formatVndInput(val) {
    if (!val) return "";
    const num = parseInt(String(val).replace(/[^\d]/g, ""), 10);
    return isNaN(num) ? "" : num.toLocaleString("vi-VN");
  },

  escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  },

  toggleAiBox() {
    const box = document.getElementById("aiPromptBoxWrapper");
    const text = document.getElementById("aiToggleText");
    if (!box) return;
    if (box.style.display === "none") {
      box.style.display = "block";
      if (text) text.textContent = "Thu gọn ▲";
    } else {
      box.style.display = "none";
      if (text) text.textContent = "Mở rộng ▼";
    }
  },

  fillAiSample(sampleType) {
    const ta = document.getElementById("aiRawInputText");
    if (!ta) return;
    if (sampleType === "sampleCX") {
      ta.value = "Gửi chị Mai kế toán trưởng mai.nt@cxtechnology.com, cc ông Chen chen.gm@cxtechnology.com và sales@hongming-global.com. Nhắc thanh toán đợt 2 93.600.000đ trước 25/10/2026, đính kèm biên bản nghiệm thu và hóa đơn VAT.";
    } else if (sampleType === "sampleJinXun") {
      ta.value = "Kính gửi chị Lan phòng kế toán lan.kt@jinxun.com, cc anh Jenson Cát jenson@hongming-global.com. Yêu cầu thanh toán Đợt 2 (55%) hợp đồng JinXun HD-20261013-001 sau khi hoàn thành lắp đặt hệ thống.";
    } else if (sampleType === "sampleContactsOnly") {
      ta.value = "Email To: pur04_vn@mail.cxtechnology.com, accountant@cxtechnology.com\nEmail CC: gm@cxtechnology.com, sales@hongming-global.com\nNgười liên hệ: Chị Mai Kế toán trưởng";
    }
    ta.focus();
  },

  async executeAiParse() {
    const ta = document.getElementById("aiRawInputText");
    const rawText = (ta?.value || "").trim();
    if (!rawText) {
      if (window.showToast) {
        window.showToast("Vui lòng nhập hoặc dán nội dung văn bản/danh bạ email để Gemini phân tích!", "warning");
      } else {
        alert("Vui lòng nhập hoặc dán nội dung văn bản/danh bạ email để Gemini phân tích!");
      }
      ta?.focus();
      return;
    }

    const matchContractChecked = document.getElementById("aiMatchContractCheckbox")?.checked ?? true;
    const contractCode = this.activeContractCode || (this.cachedContracts[0] ? this.cachedContracts[0].contract_code : "");
    const milestoneName = this.activeMilestoneName || "";

    const btn = document.getElementById("btnExecuteAiParse");
    const origBtnHtml = btn ? btn.innerHTML : "";
    if (btn) {
      btn.innerHTML = `<span style="display: inline-flex; align-items: center; gap: 5px;"><span style="width: 12px; height: 12px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; display: inline-block; animation: spin 0.8s linear infinite;"></span> Đang phân tích...</span>`;
      btn.disabled = true;
    }

    try {
      const res = await fetch("/api/v1/ai/parse-reminder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          raw_text: rawText,
          contract_code: matchContractChecked ? contractCode : null,
          milestone_name: matchContractChecked ? milestoneName : null,
          match_contract: matchContractChecked
        })
      });

      const result = await res.json();
      if (res.ok && result.status === "success" && result.data) {
        const d = result.data;

        // 1. Điền Email To & CC
        if (d.khach_hang?.email_to && d.khach_hang.email_to.length > 0) {
          const emailToInput = document.getElementById("emailToInput");
          if (emailToInput) emailToInput.value = d.khach_hang.email_to.join(", ");
        }
        if (d.khach_hang?.email_cc && d.khach_hang.email_cc.length > 0) {
          const emailCcInput = document.getElementById("emailCcInput");
          if (emailCcInput) emailCcInput.value = d.khach_hang.email_cc.join(", ");
        }

        // 2. Điền tên khách hàng
        if (d.khach_hang?.ten_khach_hang) {
          const custVi = document.getElementById("custNameVi");
          if (custVi) custVi.value = d.khach_hang.ten_khach_hang;
        }
        if (d.khach_hang?.ten_tieng_trung) {
          const custZh = document.getElementById("custNameZh");
          if (custZh) custZh.value = d.khach_hang.ten_tieng_trung;
        }

        // 3. Điền tiêu đề email
        if (d.tieu_de_email) {
          const subjInput = document.getElementById("emailSubjectInput");
          if (subjInput) subjInput.value = d.tieu_de_email;
        }

        // 4. Điền cấp độ nhắc
        if (d.cap_do) {
          const levelRadios = document.getElementsByName("reminderLevel");
          for (const r of levelRadios) {
            if (Number(r.value) === Number(d.cap_do)) {
              r.checked = true;
              break;
            }
          }
        }

        // 5. Điền ngày hạn
        const firstItem = (d.khoan_thanh_toan && d.khoan_thanh_toan[0]) ? d.khoan_thanh_toan[0] : null;
        if (firstItem?.han_thanh_toan) {
          const dueDateEl = document.getElementById("summaryDueDate");
          if (dueDateEl) dueDateEl.textContent = firstItem.han_thanh_toan;
        }

        // 6. Cập nhật Live Preview
        await handleRefreshReminderPreview();

        if (window.showToast) {
          window.showToast("✨ Gemini AI đã bóc tách To/CC và đối chiếu dữ liệu thành công!", "success");
        }
      } else {
        const msg = result.message || "Không thể phân tích dữ liệu.";
        if (window.showToast) window.showToast(`Lỗi AI: ${msg}`, "error");
        else alert(msg);
      }
    } catch (err) {
      console.error("AI parse error:", err);
      if (window.showToast) window.showToast(`Lỗi kết nối AI: ${err.message}`, "error");
      else alert(`Lỗi kết nối AI: ${err.message}`);
    } finally {
      if (btn) {
        btn.innerHTML = origBtnHtml;
        btn.disabled = false;
      }
    }
  }
};

/* ================================================= */
/* GLOBAL ACTIONS & GMAIL/DRIVE HANDLERS             */
/* ================================================= */

async function handleRefreshReminderPreview() {
  const payload = ReminderEditor.getPayloadFromDom();

  try {
    const res = await fetch("/api/v1/reminders/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.status === "success") {
      ReminderEditor.cachedEmailPreviewHtml = data.email_preview_html;
      ReminderEditor.cachedDxycttPreviewHtml = data.dxyctt_preview_html;
      ReminderEditor.renderCurrentView();

      const footerToEl = document.getElementById("footerToDisplay");
      if (footerToEl && payload.khach_hang?.email_to?.length > 0) {
        footerToEl.textContent = payload.khach_hang.email_to.join(", ");
      }
    }
  } catch (err) {
    console.error("Preview refresh error:", err);
  }
}

async function handleCopyReminderRichText() {
  const payload = ReminderEditor.getPayloadFromDom();

  try {
    const res = await fetch("/api/v1/reminders/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    const htmlText = data.data?.email_html_body || "";
    const plainText = data.data?.email_plain_body || "";

    if (navigator.clipboard && window.ClipboardItem) {
      const item = new ClipboardItem({
        "text/html": new Blob([htmlText], { type: "text/html" }),
        "text/plain": new Blob([plainText], { type: "text/plain" })
      });
      await navigator.clipboard.write([item]);
      if (window.showToast) {
        window.showToast("Đã sao chép Rich Text thành công! Bạn có thể dán (Ctrl+V) ngay vào Outlook, Gmail, WeChat hoặc Zalo với đầy đủ in đậm và bảng biểu.", "success");
      }
    } else {
      await navigator.clipboard.writeText(plainText);
      if (window.showToast) window.showToast("Đã sao chép văn bản thành công!", "success");
    }
  } catch (err) {
    if (window.showToast) window.showToast(`Lỗi sao chép: ${err.message}`, "error");
  }
}

async function handleCreateGmailDraft() {
  const payload = ReminderEditor.getPayloadFromDom();

  showLoading("Đang chuẩn bị Phiếu YCTT 1:1 và tạo bản nháp trên Gmail...");
  try {
    const res = await fetch("/api/v1/reminders/gmail/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (result.status === "success") {
      if (result.attachments && result.attachments.length > 0) {
        const attachInput = document.getElementById("attachmentsInput");
        if (attachInput) attachInput.value = result.attachments.join(", ");
        ReminderEditor.renderVisualAttachmentsList();
      }
      const attachInfo = result.attachments ? ` Đính kèm: ${result.attachments.join(", ")}` : "";
      if (window.showToast) {
        window.showToast(
          `Đã tạo thư nháp thành công trên Gmail!${attachInfo}`,
          "success"
        );
      }
      window.open(result.gmail_url || "https://mail.google.com/mail/u/0/#drafts", "_blank");
    } else {
      if (window.showToast) window.showToast(result.message || "Lỗi tạo thư nháp trên Gmail", "error");
    }
  } catch (err) {
    if (window.showToast) window.showToast(`Lỗi kết nối Gmail: ${err.message}`, "error");
  } finally {
    hideLoading();
  }
}

function handleSendGmailConfirm() {
  const payload = ReminderEditor.getPayloadFromDom();
  const toList = payload.khach_hang?.email_to || [];

  if (toList.length === 0) {
    if (window.showToast) window.showToast("Vui lòng nhập email người nhận (To).", "warning");
    return;
  }

  document.getElementById("modalToAddress").textContent = toList.join(", ");
  document.getElementById("modalCcAddress").textContent = (payload.khach_hang?.email_cc || []).join(", ") || "(Không)";
  document.getElementById("modalSubject").textContent = payload.tieu_de_email || "(Chưa có tiêu đề)";
  document.getElementById("modalAttachments").textContent = payload.danh_sach_dinh_kem?.join(", ") || "(Không đính kèm)";

  document.getElementById("sendConfirmModal").style.display = "flex";
}

function closeSendModal() {
  document.getElementById("sendConfirmModal").style.display = "none";
}

async function executeSendGmail() {
  closeSendModal();
  const payload = ReminderEditor.getPayloadFromDom();

  showLoading("Đang chuẩn bị Phiếu YCTT và gửi email trực tiếp qua Gmail...");
  try {
    const res = await fetch("/api/v1/reminders/gmail/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (result.status === "success") {
      if (result.attachments && result.attachments.length > 0) {
        const attachInput = document.getElementById("attachmentsInput");
        if (attachInput) attachInput.value = result.attachments.join(", ");
        ReminderEditor.renderVisualAttachmentsList();
      }
      if (window.showToast) window.showToast("Đã gửi email đề nghị thanh toán thành công qua Gmail (Kèm theo Phiếu YCTT Excel chuẩn 1:1)!", "success");
    } else {
      if (window.showToast) window.showToast(result.message || "Lỗi gửi email", "error");
    }
  } catch (err) {
    if (window.showToast) window.showToast(`Lỗi gửi email: ${err.message}`, "error");
  } finally {
    hideLoading();
  }
}

async function handleGenerateCurrentSheet() {
  const payload = ReminderEditor.getPayloadFromDom();
  const items = payload.khoan_thanh_toan || [];
  const firstItem = items[0] || {};
  const contractCode = firstItem.so_hop_dong || "HMV151020250001";
  let milestoneName = firstItem.hang_muc || "Đợt 2";
  if (milestoneName.includes("(")) {
    const parts = milestoneName.split("(");
    if (parts.length > 1) {
      milestoneName = parts[1].split("-")[0].replace(")", "").trim();
    }
  }

  await ReminderEditor.selectAndGenerateSheet(contractCode, milestoneName, true);
}

async function handleSearchDrive() {
  const query = (document.getElementById("driveSearchQuery")?.value || "").trim();
  const container = document.getElementById("driveResultsContainer");
  const listEl = document.getElementById("driveResultsList");

  container.style.display = "block";
  listEl.innerHTML = "<div style='padding: 12px; color: var(--text-muted); font-size: 0.85rem;'>Đang tìm kiếm tệp trên Google Drive...</div>";

  try {
    const res = await fetch("/api/v1/reminders/drive/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });

    const data = await res.json();
    if (data.status === "success" && Array.isArray(data.files) && data.files.length > 0) {
      listEl.innerHTML = "";
      data.files.forEach(f => {
        const item = document.createElement("div");
        item.className = "drive-file-item";
        item.innerHTML = `
          <div class="drive-file-name">
            <svg class="icon" style="width: 16px; height: 16px; color: #2563eb;" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span>${ReminderEditor.escapeHtml(f.name)}</span>
            <span class="drive-file-badge">${ReminderEditor.escapeHtml(f.mime_type?.split("/")[1] || "file")}</span>
          </div>
          <button type="button" class="btn btn-outline btn-sm" onclick="addDriveFileToAttachments('${ReminderEditor.escapeHtml(f.name)}')" style="padding: 2px 8px; font-size: 0.75rem;">
            + Đính Kèm
          </button>
        `;
        listEl.appendChild(item);
      });
    } else {
      listEl.innerHTML = "<div style='padding: 12px; color: var(--text-muted); font-size: 0.85rem;'>Không tìm thấy tệp nào phù hợp trên Google Drive.</div>";
    }
  } catch (err) {
    listEl.innerHTML = `<div style='padding: 12px; color: #b91c1c; font-size: 0.85rem;'>Lỗi tìm kiếm: ${err.message}</div>`;
  }
}

function addDriveFileToAttachments(fileName) {
  const attachInput = document.getElementById("attachmentsInput");
  if (!attachInput) return;
  const current = (attachInput.value || "").trim();
  if (current) {
    const list = current.split(",").map(s => s.trim());
    if (!list.includes(fileName)) {
      attachInput.value = current + ", " + fileName;
    }
  } else {
    attachInput.value = fileName;
  }
  ReminderEditor.renderVisualAttachmentsList();
  handleRefreshReminderPreview();
  if (window.showToast) window.showToast(`Đã thêm tệp "${fileName}" vào danh sách đính kèm!`, "success");
}

function handleLocalFileUpload(event) {
  const files = event.target.files;
  if (!files || files.length === 0) return;
  const fileNames = Array.from(files).map(f => f.name);
  fileNames.forEach(fn => addDriveFileToAttachments(fn));
  if (window.showToast) {
    window.showToast(`Đã thêm thành công ${fileNames.length} tệp từ máy tính vào danh sách đính kèm!`, "success");
  }
  event.target.value = "";
}

function handlePrintDocument() {
  window.print();
}

let isOpeningSystemPath = false;
async function openSystemPath(filePath, btnEl) {
  if (!filePath) {
    if (window.showToast) window.showToast("Không tìm thấy đường dẫn tệp trên ổ đĩa.", "warning");
    return;
  }
  if (isOpeningSystemPath) return;
  isOpeningSystemPath = true;

  let originalHtml = "";
  if (btnEl && btnEl.innerHTML) {
    originalHtml = btnEl.innerHTML;
    btnEl.innerHTML = "⏳ Đang mở...";
    btnEl.disabled = true;
  }

  try {
    const res = await fetch("/api/v1/system/open-path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: filePath })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.status === "success") {
      if (window.showToast) window.showToast(data.message, "success");
    } else {
      if (window.showToast) window.showToast(data.message || data.detail || "Không thể mở tệp trên máy tính.", "warning");
    }
  } catch (err) {
    if (window.showToast) window.showToast(`Lỗi mở tệp: ${err.message}`, "error");
  } finally {
    if (btnEl && originalHtml) {
      btnEl.innerHTML = originalHtml;
      btnEl.disabled = false;
    }
    setTimeout(() => { isOpeningSystemPath = false; }, 600);
  }
}

async function deleteDossierDocument(docId, fileName, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  if (!confirm(`Bạn có chắc chắn muốn xóa tệp "${fileName}"?\nThao tác này sẽ xóa bản ghi khỏi hệ thống VÀ XÓA TỆP VẬT LÝ trên ổ đĩa máy tính.`)) {
    return;
  }
  try {
    const res = await fetch(`/api/v1/dossier/documents/${docId}`, { method: "DELETE" });
    const data = await res.json().catch(() => ({}));
    if (res.ok || data.status === "success" || res.status === 404) {
      const msg = data.message || (res.status === 404 ? `Tài liệu "${fileName}" đã được xóa trước đó hoặc không tồn tại.` : `Đã xóa tệp "${fileName}" và tệp trên máy tính!`);
      if (window.showToast) window.showToast(msg, res.status === 404 ? "info" : "success");
      if (typeof ReminderEditor !== "undefined" && typeof ReminderEditor.loadSavedContracts === "function") {
        await ReminderEditor.loadSavedContracts();
      }
      const modal = document.getElementById("contractDossierModal");
      if (modal && modal.style.display !== "none") {
        modal.style.display = "none";
      }
    } else {
      const errMsg = data.message || data.detail || "Không thể xóa tệp.";
      if (window.showToast) window.showToast(errMsg, "error");
    }
  } catch (err) {
    if (window.showToast) window.showToast(`Lỗi xóa tệp: ${err.message}`, "error");
  }
}


