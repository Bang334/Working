/**
 * Custom Personal Reminders & Task Appointments Manager for Hong Ming PM Portal.
 * Handles:
 * - Independent personal reminders & task scheduling (separate from project contracts)
 * - Due date & time with Vietnamese weekday calculation (Thứ Hai, Thứ Ba...)
 * - File attachments: direct file upload or 1-click link to project files in Ho So Du An/
 * - Search, filtering by status (Today, Upcoming, Overdue, Completed) and priority
 * - Quick date buttons (Hôm nay, Ngày mai, Thứ Hai tới, +3 ngày, +1 tuần)
 * - Full CRUD & status toggles
 */

const CustomReminderManager = {
  reminders: [],
  stats: {
    total: 0,
    pending: 0,
    today: 0,
    overdue: 0,
    upcoming: 0,
    completed: 0,
  },
  currentFilter: "all",
  currentPriority: "ALL",
  searchQuery: "",
  availableProjectFiles: [],
  activeEditingId: null,
  attachmentMode: "upload", // 'upload' or 'project'

  init() {
    this.bindEvents();
    this.loadProjectFiles();
    this.loadReminders();
    this.checkInitialTab();
  },

  checkInitialTab() {
    const hash = window.location.hash;
    const savedTab = localStorage.getItem("activeReminderMasterTab");
    if (hash === "#custom-reminders" || savedTab === "custom") {
      this.switchMasterTab("custom");
    } else {
      this.switchMasterTab("project");
    }
  },

  switchMasterTab(tabName) {
    const btnProject = document.getElementById("tabBtnProjectReminders");
    const btnCustom = document.getElementById("tabBtnCustomReminders");
    const panelProject = document.getElementById("projectRemindersPanel");
    const panelCustom = document.getElementById("customRemindersPanel");

    if (!panelProject || !panelCustom) return;

    if (tabName === "custom") {
      if (btnProject) btnProject.classList.remove("active");
      if (btnCustom) btnCustom.classList.add("active");
      panelProject.style.display = "none";
      panelCustom.style.display = "block";
      localStorage.setItem("activeReminderMasterTab", "custom");
      history.replaceState(null, null, "#custom-reminders");
      this.loadReminders();
    } else {
      if (btnProject) btnProject.classList.add("active");
      if (btnCustom) btnCustom.classList.remove("active");
      panelProject.style.display = "block";
      panelCustom.style.display = "none";
      localStorage.setItem("activeReminderMasterTab", "project");
      if (window.location.hash === "#custom-reminders") {
        history.replaceState(null, null, window.location.pathname);
      }
    }
  },

  bindEvents() {
    const searchInput = document.getElementById("crSearchInput");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        this.renderReminders();
      });
    }

    const prioritySelect = document.getElementById("crPriorityFilter");
    if (prioritySelect) {
      prioritySelect.addEventListener("change", (e) => {
        this.currentPriority = e.target.value;
        this.renderReminders();
      });
    }

    // Modal attachment tabs
    const tabUpload = document.getElementById("crAttachTabUpload");
    const tabProject = document.getElementById("crAttachTabProject");
    if (tabUpload && tabProject) {
      tabUpload.addEventListener("click", () => this.switchAttachmentTab("upload"));
      tabProject.addEventListener("click", () => this.switchAttachmentTab("project"));
    }
  },

  async loadReminders() {
    try {
      const res = await fetch("/api/v1/custom-reminders");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.status === "success") {
        this.reminders = data.reminders || [];
        this.stats = data.stats || { total: 0, pending: 0, today: 0, overdue: 0, upcoming: 0, completed: 0 };
        this.renderStats();
        this.renderReminders();
        this.updateMasterBadge();
      }
    } catch (err) {
      console.error("Lỗi khi tải danh sách nhắc nhở:", err);
    }
  },

  async loadProjectFiles() {
    try {
      const res = await fetch("/api/v1/custom-reminders/project-files");
      if (!res.ok) return;
      const data = await res.json();
      if (data.status === "success") {
        this.availableProjectFiles = data.files || [];
        this.populateProjectFilesDropdown();
      }
    } catch (err) {
      console.warn("Không thể tải danh sách file hồ sơ:", err);
    }
  },

  populateProjectFilesDropdown() {
    const select = document.getElementById("crProjectFileSelect");
    if (!select) return;

    if (!this.availableProjectFiles.length) {
      select.innerHTML = '<option value="">(Chưa có file trong Hồ Sơ Dự Án)</option>';
      return;
    }

    let html = '<option value="">-- Chọn một file từ Hồ Sơ Dự Án để đính kèm --</option>';
    const grouped = {};
    for (const f of this.availableProjectFiles) {
      const cat = f.category_label || "Hồ Sơ Khác";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(f);
    }

    for (const [catName, fileList] of Object.entries(grouped)) {
      html += `<optgroup label="📂 ${catName}">`;
      for (const f of fileList) {
        html += `<option value="${this.escapeHtml(f.path)}">${this.escapeHtml(f.name)} (${this.escapeHtml(f.size_human)})</option>`;
      }
      html += `</optgroup>`;
    }
    select.innerHTML = html;
  },

  updateMasterBadge() {
    const badge = document.getElementById("badgeCustomCount");
    if (badge) {
      const pendingCount = (this.stats.today || 0) + (this.stats.overdue || 0);
      badge.textContent = this.stats.pending || 0;
      if (this.stats.overdue > 0) {
        badge.style.background = "#dc2626";
        badge.title = `${this.stats.overdue} việc quá hạn, ${this.stats.today} việc hôm nay!`;
      } else if (this.stats.today > 0) {
        badge.style.background = "#f59e0b";
        badge.title = `${this.stats.today} việc cần làm hôm nay!`;
      } else {
        badge.style.background = "#3b82f6";
        badge.title = `${this.stats.pending} việc chưa hoàn tất`;
      }
    }
  },

  renderStats() {
    const elTotal = document.getElementById("crStatTotal");
    const elToday = document.getElementById("crStatToday");
    const elUpcoming = document.getElementById("crStatUpcoming");
    const elOverdue = document.getElementById("crStatOverdue");
    const elCompleted = document.getElementById("crStatCompleted");

    if (elTotal) elTotal.textContent = this.stats.total || 0;
    if (elToday) elToday.textContent = this.stats.today || 0;
    if (elUpcoming) elUpcoming.textContent = this.stats.upcoming || 0;
    if (elOverdue) elOverdue.textContent = this.stats.overdue || 0;
    if (elCompleted) elCompleted.textContent = this.stats.completed || 0;

    // Filter pill counts
    const pillAll = document.getElementById("crPillCountAll");
    const pillToday = document.getElementById("crPillCountToday");
    const pillUpcoming = document.getElementById("crPillCountUpcoming");
    const pillOverdue = document.getElementById("crPillCountOverdue");
    const pillPending = document.getElementById("crPillCountPending");
    const pillCompleted = document.getElementById("crPillCountCompleted");

    if (pillAll) pillAll.textContent = this.stats.total || 0;
    if (pillToday) pillToday.textContent = this.stats.today || 0;
    if (pillUpcoming) pillUpcoming.textContent = this.stats.upcoming || 0;
    if (pillOverdue) pillOverdue.textContent = this.stats.overdue || 0;
    if (pillPending) pillPending.textContent = this.stats.pending || 0;
    if (pillCompleted) pillCompleted.textContent = this.stats.completed || 0;
  },

  setFilter(filterType, btnElem) {
    this.currentFilter = filterType;
    document.querySelectorAll(".cr-filter-btn").forEach((b) => b.classList.remove("active"));
    if (btnElem) btnElem.classList.add("active");
    this.renderReminders();
  },

  renderReminders() {
    const container = document.getElementById("crCardsContainer");
    if (!container) return;

    // Filter list
    let filtered = this.reminders.filter((r) => {
      // Status filter
      if (this.currentFilter === "today" && (!r.is_today || r.status === "COMPLETED")) return false;
      if (this.currentFilter === "upcoming" && (!r.is_upcoming || r.status === "COMPLETED")) return false;
      if (this.currentFilter === "overdue" && (!r.is_overdue || r.status === "COMPLETED")) return false;
      if (this.currentFilter === "pending" && r.status !== "PENDING") return false;
      if (this.currentFilter === "completed" && r.status !== "COMPLETED") return false;

      // Priority filter
      if (this.currentPriority !== "ALL" && r.priority !== this.currentPriority) return false;

      // Search query
      if (this.searchQuery) {
        const text = `${r.title} ${r.description || ""} ${r.attachment_name || ""}`.toLowerCase();
        if (!text.includes(this.searchQuery)) return false;
      }

      return true;
    });

    if (!filtered.length) {
      container.innerHTML = `
        <div class="cr-empty-state">
          <div style="font-size: 3rem; margin-bottom: 0.75rem;">📋</div>
          <h4 style="font-size: 1.1rem; color: #1e3a8a; margin: 0 0 0.5rem 0;">Không có lời nhắc nào phù hợp</h4>
          <p style="font-size: 0.85rem; color: #64748b; margin: 0 0 1.25rem 0; max-width: 420px; line-height: 1.5;">
            ${this.searchQuery || this.currentFilter !== "all" 
              ? "Hãy thử chọn bộ lọc khác hoặc tìm kiếm từ khóa khác." 
              : "Bạn chưa có lời nhắc hoặc lịch hẹn riêng nào. Hãy thêm ngay việc cần nhớ kèm file đính kèm!"}
          </p>
          <button type="button" class="btn btn-primary" onclick="CustomReminderManager.openCreateModal()" style="font-weight: 700;">
            ➕ Tạo Nhắc Nhở Đầu Tiên
          </button>
        </div>
      `;
      return;
    }

    let cardsHtml = "";
    for (const r of filtered) {
      const isDone = r.status === "COMPLETED";

      // Priority Pill
      let priorityBadge = "";
      if (r.priority === "URGENT") {
        priorityBadge = `<span class="cr-badge cr-badge-urgent">🔥 Khẩn Cấp</span>`;
      } else if (r.priority === "HIGH") {
        priorityBadge = `<span class="cr-badge cr-badge-high">⚡ Quan Trọng</span>`;
      } else {
        priorityBadge = `<span class="cr-badge cr-badge-normal">Bình Thường</span>`;
      }

      // Timing Badge
      let timingBadge = "";
      if (isDone) {
        timingBadge = `<span class="cr-timing cr-timing-done">✓ Đã Hoàn Thành</span>`;
      } else if (r.is_today) {
        timingBadge = `<span class="cr-timing cr-timing-today">🔥 Hôm Nay (${r.due_time})</span>`;
      } else if (r.is_overdue) {
        const days = Math.abs(r.days_remaining || 0);
        timingBadge = `<span class="cr-timing cr-timing-overdue">⚠️ Quá hạn ${days} ngày</span>`;
      } else if (r.days_remaining !== null) {
        timingBadge = `<span class="cr-timing cr-timing-upcoming">⏳ Còn ${r.days_remaining} ngày</span>`;
      }

      // Category Pill
      const catLabel = this.getCategoryLabel(r.category);

      // Attachment Block
      let attachHtml = "";
      if (r.attachment_name) {
        const fileIcon = this.getFileIcon(r.attachment_name);
        const sizeHuman = r.attachment_size_human || "";
        attachHtml = `
          <div class="cr-attachment-box">
            <div style="display: flex; align-items: center; gap: 0.5rem; overflow: hidden; min-width: 0;">
              <span style="font-size: 1.3rem;">${fileIcon}</span>
              <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                <div style="font-size: 0.85rem; font-weight: 600; color: #1e3a8a; overflow: hidden; text-overflow: ellipsis;" title="${this.escapeHtml(r.attachment_name)}">
                  ${this.escapeHtml(r.attachment_name)}
                </div>
                <div style="font-size: 0.72rem; color: #64748b;">
                  ${sizeHuman ? sizeHuman : ""} ${r.is_linked_from_project ? "• 📂 Hồ sơ dự án" : "• 📁 Tệp tải lên"}
                </div>
              </div>
            </div>
            <a href="/api/v1/custom-reminders/${r.id}/download" target="_blank" class="btn btn-outline btn-sm cr-download-btn" title="Tải về tệp đính kèm">
              <svg class="icon" viewBox="0 0 24 24" style="width: 14px; height: 14px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              <span>Tải Tệp</span>
            </a>
          </div>
        `;
      }

      // Card Container
      cardsHtml += `
        <div class="cr-card ${isDone ? "is-completed" : ""} ${r.is_overdue && !isDone ? "is-overdue" : ""} ${r.is_today && !isDone ? "is-today" : ""}">
          <div class="cr-card-header">
            <div class="cr-checkbox-wrapper" onclick="CustomReminderManager.toggleStatus(${r.id})" title="${isDone ? 'Đánh dấu chưa hoàn thành' : 'Đánh dấu đã hoàn thành'}">
              <div class="cr-checkbox ${isDone ? "checked" : ""}">
                ${isDone ? "✓" : ""}
              </div>
            </div>

            <div style="flex: 1; min-width: 0;">
              <div style="display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; margin-bottom: 0.35rem;">
                ${priorityBadge}
                <span class="cr-category-tag">${catLabel}</span>
                ${timingBadge}
              </div>
              <h4 class="cr-card-title ${isDone ? "strike" : ""}">${this.escapeHtml(r.title)}</h4>
            </div>

            <div class="cr-card-actions">
              <button type="button" class="cr-action-icon-btn" onclick="CustomReminderManager.openEditModal(${r.id})" title="Chỉnh sửa nhắc nhở">
                <svg class="icon" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button type="button" class="cr-action-icon-btn delete" onclick="CustomReminderManager.deleteReminder(${r.id})" title="Xóa nhắc nhở">
                <svg class="icon" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
              </button>
            </div>
          </div>

          ${r.description ? `<div class="cr-card-desc">${this.escapeHtml(r.description)}</div>` : ""}

          ${attachHtml}

          <div class="cr-card-footer">
            <div class="cr-schedule-time">
              📅 <strong>${this.escapeHtml(r.due_date_formatted || r.due_date)}</strong>
              ${r.due_time ? `<span style="color: #64748b; margin-left: 0.3rem;">(${r.due_time})</span>` : ""}
            </div>
            
            <div style="display: flex; gap: 0.4rem; align-items: center;">
              <button type="button" class="btn btn-outline btn-sm" onclick="CustomReminderManager.toggleStatus(${r.id})" style="font-size: 0.76rem; padding: 2px 8px;">
                ${isDone ? "↺ Đặt Lại" : "✓ Hoàn Thành"}
              </button>
            </div>
          </div>
        </div>
      `;
    }

    container.innerHTML = cardsHtml;
  },

  getCategoryLabel(cat) {
    switch (cat) {
      case "CUSTOMER_FILE":
        return "📤 Gửi File Khách";
      case "MEETING":
        return "🤝 Cuộc Hẹn / Họp";
      case "PAYMENT":
        return "💰 Thanh Toán";
      case "TECHNICAL":
        return "⚙️ Kỹ Thuật";
      default:
        return "📌 Nhắc Nhở";
    }
  },

  getFileIcon(filename) {
    if (!filename) return "📎";
    const lower = filename.toLowerCase();
    if (lower.endsWith(".xlsx") || lower.endsWith(".xls")) return "📊";
    if (lower.endsWith(".docx") || lower.endsWith(".doc")) return "📄";
    if (lower.endsWith(".pdf")) return "📑";
    if (lower.endsWith(".png") || lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "🖼️";
    if (lower.endsWith(".zip") || lower.endsWith(".rar") || lower.endsWith(".7z")) return "📦";
    return "📎";
  },

  openCreateModal() {
    this.activeEditingId = null;
    document.getElementById("crModalTitle").innerHTML = "➕ Thêm Nhắc Nhở Riêng & Lịch Hẹn";
    document.getElementById("crTitleInput").value = "";
    document.getElementById("crDescInput").value = "";
    
    // Default date: today or tomorrow
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    document.getElementById("crDueDateInput").value = `${yyyy}-${mm}-${dd}`;
    document.getElementById("crDueTimeInput").value = "09:00";

    document.getElementById("crPrioritySelect").value = "NORMAL";
    document.getElementById("crCategorySelect").value = "CUSTOMER_FILE";

    // Reset attachments
    document.getElementById("crFileInput").value = "";
    document.getElementById("crProjectFileSelect").value = "";
    document.getElementById("crCurrentAttachmentWrapper").style.display = "none";
    document.getElementById("crRemoveAttachmentCheck").checked = false;

    this.switchAttachmentTab("upload");
    this.showModal();
  },

  openEditModal(id) {
    const item = this.reminders.find((r) => r.id === id);
    if (!item) return;

    this.activeEditingId = id;
    document.getElementById("crModalTitle").innerHTML = "✏️ Chỉnh Sửa Nhắc Nhở Riêng";
    document.getElementById("crTitleInput").value = item.title || "";
    document.getElementById("crDescInput").value = item.description || "";
    document.getElementById("crDueDateInput").value = item.due_date || "";
    document.getElementById("crDueTimeInput").value = item.due_time || "09:00";
    document.getElementById("crPrioritySelect").value = item.priority || "NORMAL";
    document.getElementById("crCategorySelect").value = item.category || "GENERAL";

    // Attachment
    document.getElementById("crFileInput").value = "";
    document.getElementById("crProjectFileSelect").value = "";
    document.getElementById("crRemoveAttachmentCheck").checked = false;

    const currentAttachWrapper = document.getElementById("crCurrentAttachmentWrapper");
    if (item.attachment_name) {
      currentAttachWrapper.style.display = "block";
      document.getElementById("crCurrentAttachmentName").textContent = `${item.attachment_name} (${item.attachment_size_human || ""})`;
    } else {
      currentAttachWrapper.style.display = "none";
    }

    this.switchAttachmentTab("upload");
    this.showModal();
  },

  showModal() {
    const modal = document.getElementById("customReminderModal");
    if (modal) modal.style.display = "flex";
  },

  closeModal() {
    const modal = document.getElementById("customReminderModal");
    if (modal) modal.style.display = "none";
  },

  switchAttachmentTab(mode) {
    this.attachmentMode = mode;
    const tabUpload = document.getElementById("crAttachTabUpload");
    const tabProject = document.getElementById("crAttachTabProject");
    const contentUpload = document.getElementById("crAttachContentUpload");
    const contentProject = document.getElementById("crAttachContentProject");

    if (mode === "upload") {
      if (tabUpload) tabUpload.classList.add("active");
      if (tabProject) tabProject.classList.remove("active");
      if (contentUpload) contentUpload.style.display = "block";
      if (contentProject) contentProject.style.display = "none";
    } else {
      if (tabUpload) tabUpload.classList.remove("active");
      if (tabProject) tabProject.classList.add("active");
      if (contentUpload) contentUpload.style.display = "none";
      if (contentProject) contentProject.style.display = "block";
    }
  },

  setQuickDate(offsetDays, toMonday = false) {
    const date = new Date();
    if (toMonday) {
      // Find upcoming Monday
      const dayOfWeek = date.getDay(); // 0 is Sunday, 1 is Monday
      let daysUntilMonday = 1 - dayOfWeek;
      if (daysUntilMonday <= 0) {
        daysUntilMonday += 7;
      }
      date.setDate(date.getDate() + daysUntilMonday);
    } else {
      date.setDate(date.getDate() + offsetDays);
    }

    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, "0");
    const dd = String(date.getDate()).padStart(2, "0");
    document.getElementById("crDueDateInput").value = `${yyyy}-${mm}-${dd}`;
  },

  async submitReminder() {
    const title = document.getElementById("crTitleInput").value.trim();
    const dueDate = document.getElementById("crDueDateInput").value.trim();
    const dueTime = document.getElementById("crDueTimeInput").value.trim() || "09:00";
    const desc = document.getElementById("crDescInput").value.trim();
    const priority = document.getElementById("crPrioritySelect").value;
    const category = document.getElementById("crCategorySelect").value;

    if (!title) {
      alert("Vui lòng nhập tiêu đề nhắc nhở!");
      document.getElementById("crTitleInput").focus();
      return;
    }

    if (!dueDate) {
      alert("Vui lòng chọn ngày đến hạn!");
      document.getElementById("crDueDateInput").focus();
      return;
    }

    const formData = new FormData();
    formData.append("title", title);
    formData.append("due_date", dueDate);
    formData.append("due_time", dueTime);
    formData.append("description", desc);
    formData.append("priority", priority);
    formData.append("category", category);

    // Attachment logic
    const fileInput = document.getElementById("crFileInput");
    const projectFileSelect = document.getElementById("crProjectFileSelect");
    const removeCheck = document.getElementById("crRemoveAttachmentCheck");

    if (this.activeEditingId && removeCheck && removeCheck.checked) {
      formData.append("remove_attachment", "true");
    } else if (this.attachmentMode === "upload" && fileInput && fileInput.files.length > 0) {
      formData.append("file", fileInput.files[0]);
    } else if (this.attachmentMode === "project" && projectFileSelect && projectFileSelect.value) {
      formData.append("existing_file_path", projectFileSelect.value);
    }

    const btnSubmit = document.getElementById("btnSubmitCustomReminder");
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.textContent = "Đang lưu...";
    }

    try {
      let url = "/api/v1/custom-reminders";
      let method = "POST";
      if (this.activeEditingId) {
        url = `/api/v1/custom-reminders/${this.activeEditingId}`;
        method = "PUT";
      }

      const res = await fetch(url, {
        method: method,
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Lỗi máy chủ (${res.status})`);
      }

      this.closeModal();
      await this.loadReminders();
    } catch (err) {
      alert(`Không thể lưu nhắc nhở: ${err.message}`);
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.textContent = "💾 Lưu Lời Nhắc";
      }
    }
  },

  async toggleStatus(id) {
    try {
      const res = await fetch(`/api/v1/custom-reminders/${id}/toggle`, {
        method: "PATCH",
      });
      if (!res.ok) throw new Error("Không thể cập nhật trạng thái");
      await this.loadReminders();
    } catch (err) {
      alert(err.message);
    }
  },

  async deleteReminder(id) {
    const item = this.reminders.find((r) => r.id === id);
    const title = item ? item.title : `lời nhắc #${id}`;
    if (!confirm(`Bạn có chắc muốn xóa "${title}" không?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/custom-reminders/${id}?delete_file=false`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Không thể xóa lời nhắc");
      await this.loadReminders();
    } catch (err) {
      alert(err.message);
    }
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
};

// Global hooks for direct inline onclick handlers
function switchMasterReminderTab(tabName) {
  CustomReminderManager.switchMasterTab(tabName);
}
