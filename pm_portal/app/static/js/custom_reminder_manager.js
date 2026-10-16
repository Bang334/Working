/**
 * Custom Personal Reminders & Task Appointments Manager for Hong Ming PM Portal.
 * Supports:
 * - Dedicated folders per reminder on disk
 * - Multiple file & image attachments with thumbnail galleries & full lightbox preview
 * - Linking files from anywhere on PC or Ho So Du An
 * - Deletion options: delete files in dedicated folder vs keep files intact
 * - Direct folder opening in Windows Explorer
 * - Glowing red notification alert on sidebar when due today or overdue
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
  attachmentMode: "upload",

  // Staged state for modal
  stagedFiles: [],       // Array of File objects selected from computer
  stagedLinkedPaths: [], // Array of string paths linked from project or custom disk path
  existingAttachments: [], // Current attachments when editing
  removedIndices: [],    // Indices of existing attachments to remove

  // Pending delete target
  targetDeleteId: null,

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

        // Refresh global sidebar alert as well
        if (typeof refreshSidebarRemindersAlert === "function") {
          refreshSidebarRemindersAlert();
        }
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

    let html = '<option value="">-- Chọn file từ Hồ Sơ Dự Án để gắn vào lịch hẹn --</option>';
    const grouped = {};
    for (const f of this.availableProjectFiles) {
      const cat = f.category_label || "Hồ Sơ Khác";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(f);
    }

    for (const [catName, fileList] of Object.entries(grouped)) {
      html += `<optgroup label="📂 ${catName}">`;
      for (const f of fileList) {
        html += `<option value="${this.escapeHtml(f.file_path)}">${this.escapeHtml(f.file_name)} (${this.escapeHtml(f.file_size_formatted)})</option>`;
      }
      html += `</optgroup>`;
    }
    select.innerHTML = html;
  },

  updateMasterBadge() {
    const badge = document.getElementById("badgeCustomCount");
    if (badge) {
      const dueCount = (this.stats.today || 0) + (this.stats.overdue || 0);
      badge.textContent = dueCount > 0 ? dueCount : (this.stats.pending || 0);
      if (this.stats.overdue > 0) {
        badge.style.background = "#dc2626";
        badge.title = `${this.stats.overdue} việc quá hạn, ${this.stats.today} việc hôm nay!`;
      } else if (this.stats.today > 0) {
        badge.style.background = "#ea580c";
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

    let filtered = this.reminders.filter((r) => {
      if (this.currentFilter === "today" && (!r.is_today || r.status === "COMPLETED")) return false;
      if (this.currentFilter === "upcoming" && (!r.is_upcoming || r.status === "COMPLETED")) return false;
      if (this.currentFilter === "overdue" && (!r.is_overdue || r.status === "COMPLETED")) return false;
      if (this.currentFilter === "pending" && r.status !== "PENDING") return false;
      if (this.currentFilter === "completed" && r.status !== "COMPLETED") return false;

      if (this.currentPriority !== "ALL" && r.priority !== this.currentPriority) return false;

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
              : "Bạn chưa có lời nhắc hoặc lịch hẹn riêng nào. Hãy thêm ngay việc cần nhớ kèm nhiều file hoặc ảnh đính kèm!"}
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

      const catLabel = this.getCategoryLabel(r.category);

      // Dedicated Folder Box
      const folderBoxHtml = `
        <div class="cr-folder-box" title="Thư mục lưu trữ: ${this.escapeHtml(r.folder_path || '')}">
          <div style="display: flex; align-items: center; gap: 0.35rem; min-width: 0; overflow: hidden;">
            <span>📁</span>
            <span class="cr-folder-path">reminder_${r.id}</span>
          </div>
          <button type="button" class="cr-open-folder-btn" onclick="CustomReminderManager.openFolder(${r.id})" title="Mở thư mục này trên máy tính trong File Explorer">
            <svg class="icon" viewBox="0 0 24 24" style="width: 12px; height: 12px;"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            <span>Mở Folder</span>
          </button>
        </div>
      `;

      // Attachments & Images rendering
      const attachList = r.attachments_list || [];
      const imageItems = [];
      const docItems = [];

      for (let i = 0; i < attachList.length; i++) {
        const att = attachList[i];
        if (att.is_image) {
          imageItems.push({ ...att, index: i });
        } else {
          docItems.push({ ...att, index: i });
        }
      }

      // Render image thumbnails gallery
      let galleryHtml = "";
      if (imageItems.length > 0) {
        galleryHtml += `<div class="cr-images-gallery">`;
        for (const img of imageItems) {
          galleryHtml += `
            <div class="cr-image-thumb-box" onclick="CustomReminderManager.openLightbox('${img.preview_url}')" title="${this.escapeHtml(img.name)} (${img.size_human})">
              <img src="${img.preview_url}" class="cr-image-thumb-img" alt="${this.escapeHtml(img.name)}" loading="lazy">
              <div class="cr-image-thumb-overlay">🔍</div>
            </div>
          `;
        }
        galleryHtml += `</div>`;
      }

      // Render documents stack
      let docsHtml = "";
      if (docItems.length > 0) {
        docsHtml += `<div class="cr-attachments-stack">`;
        for (const doc of docItems) {
          const fileIcon = this.getFileIcon(doc.name);
          docsHtml += `
            <div class="cr-attachment-row">
              <div style="display: flex; align-items: center; gap: 0.45rem; overflow: hidden; min-width: 0;">
                <span style="font-size: 1.15rem;">${fileIcon}</span>
                <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  <span style="font-size: 0.82rem; font-weight: 600; color: #1e3a8a;" title="${this.escapeHtml(doc.path)}">
                    ${this.escapeHtml(doc.name)}
                  </span>
                  <span style="font-size: 0.72rem; color: #64748b; margin-left: 0.35rem;">
                    (${doc.size_human}) ${doc.is_uploaded ? "• 📁 Thư mục" : "• 📂 Liên kết"}
                  </span>
                </div>
              </div>
              <a href="${doc.download_url}" target="_blank" class="btn btn-outline btn-sm cr-download-btn" title="Tải về tệp này">
                <svg class="icon" viewBox="0 0 24 24" style="width: 12px; height: 12px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                <span>Tải</span>
              </a>
            </div>
          `;
        }
        docsHtml += `</div>`;
      }

      // Card assembly
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
              <button type="button" class="cr-action-icon-btn" onclick="CustomReminderManager.openEditModal(${r.id})" title="Chỉnh sửa nhắc nhở & tệp đính kèm">
                <svg class="icon" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button type="button" class="cr-action-icon-btn delete" onclick="CustomReminderManager.openDeleteModal(${r.id})" title="Xóa nhắc nhở (Chọn xóa tệp hoặc giữ tệp)">
                <svg class="icon" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
              </button>
            </div>
          </div>

          ${r.description ? `<div class="cr-card-desc">${this.escapeHtml(r.description)}</div>` : ""}

          ${folderBoxHtml}

          ${galleryHtml}

          ${docsHtml}

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
    if (lower.endsWith(".png") || lower.endsWith(".jpg") || lower.endsWith(".jpeg") || lower.endsWith(".webp")) return "🖼️";
    if (lower.endsWith(".zip") || lower.endsWith(".rar") || lower.endsWith(".7z")) return "📦";
    return "📎";
  },

  openCreateModal() {
    this.activeEditingId = null;
    this.stagedFiles = [];
    this.stagedLinkedPaths = [];
    this.existingAttachments = [];
    this.removedIndices = [];

    document.getElementById("crModalTitle").innerHTML = "➕ Thêm Nhắc Nhở Riêng & Đính Kèm Tệp";
    document.getElementById("crTitleInput").value = "";
    document.getElementById("crDescInput").value = "";
    
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
    document.getElementById("crCustomFilePathInput").value = "";

    this.renderStagedAttachments();
    this.switchAttachmentTab("upload");
    this.showModal();
  },

  openEditModal(id) {
    const item = this.reminders.find((r) => r.id === id);
    if (!item) return;

    this.activeEditingId = id;
    this.stagedFiles = [];
    this.stagedLinkedPaths = [];
    this.existingAttachments = [...(item.attachments_list || [])];
    this.removedIndices = [];

    document.getElementById("crModalTitle").innerHTML = `✏️ Sửa Nhắc Nhở (#${id} - folder: reminder_${id})`;
    document.getElementById("crTitleInput").value = item.title || "";
    document.getElementById("crDescInput").value = item.description || "";
    document.getElementById("crDueDateInput").value = item.due_date || "";
    document.getElementById("crDueTimeInput").value = item.due_time || "09:00";
    document.getElementById("crPrioritySelect").value = item.priority || "NORMAL";
    document.getElementById("crCategorySelect").value = item.category || "GENERAL";

    document.getElementById("crFileInput").value = "";
    document.getElementById("crProjectFileSelect").value = "";
    document.getElementById("crCustomFilePathInput").value = "";

    this.renderStagedAttachments();
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

  onFilesSelected(event) {
    const files = event.target.files;
    if (!files || !files.length) return;
    for (let i = 0; i < files.length; i++) {
      this.stagedFiles.push(files[i]);
    }
    // Clear input so selecting same file again triggers change
    event.target.value = "";
    this.renderStagedAttachments();
  },

  onProjectFileSelected(filePath) {
    if (!filePath) return;
    if (!this.stagedLinkedPaths.includes(filePath)) {
      this.stagedLinkedPaths.push(filePath);
      this.renderStagedAttachments();
    }
    document.getElementById("crProjectFileSelect").value = "";
  },

  addCustomFilePath() {
    const input = document.getElementById("crCustomFilePathInput");
    if (!input) return;
    const pathVal = input.value.trim();
    if (!pathVal) {
      alert("Vui lòng nhập hoặc dán đường dẫn tệp tin!");
      return;
    }
    if (!this.stagedLinkedPaths.includes(pathVal)) {
      this.stagedLinkedPaths.push(pathVal);
      this.renderStagedAttachments();
    }
    input.value = "";
  },

  removeStagedFile(index) {
    this.stagedFiles.splice(index, 1);
    this.renderStagedAttachments();
  },

  removeStagedLinkedPath(index) {
    this.stagedLinkedPaths.splice(index, 1);
    this.renderStagedAttachments();
  },

  markExistingAttachmentRemove(index) {
    if (!this.removedIndices.includes(index)) {
      this.removedIndices.push(index);
    }
    this.renderStagedAttachments();
  },

  unmarkExistingAttachmentRemove(index) {
    this.removedIndices = this.removedIndices.filter((i) => i !== index);
    this.renderStagedAttachments();
  },

  renderStagedAttachments() {
    const container = document.getElementById("crStagedAttachmentsContainer");
    const list = document.getElementById("crStagedList");
    const countEl = document.getElementById("crStagedCount");
    if (!container || !list) return;

    let itemsHtml = "";
    let activeExistingCount = 0;

    // Existing attachments when editing
    for (let i = 0; i < this.existingAttachments.length; i++) {
      const att = this.existingAttachments[i];
      const isRemoved = this.removedIndices.includes(i);
      if (!isRemoved) activeExistingCount++;

      itemsHtml += `
        <div class="cr-staged-item" style="${isRemoved ? 'opacity: 0.5; text-decoration: line-through; background: #fee2e2;' : ''}">
          <div style="display: flex; align-items: center; gap: 0.35rem; min-width: 0; overflow: hidden;">
            <span>${this.getFileIcon(att.name)}</span>
            <span style="font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${this.escapeHtml(att.name)}
            </span>
            <span style="color: #64748b; font-size: 0.72rem;">(${att.size_human || ""}) • Hiện có</span>
          </div>
          <div>
            ${isRemoved 
              ? `<button type="button" class="btn btn-outline btn-sm" onclick="CustomReminderManager.unmarkExistingAttachmentRemove(${i})" style="font-size: 0.7rem; padding: 1px 6px;">↺ Khôi phục</button>`
              : `<button type="button" class="cr-staged-remove" onclick="CustomReminderManager.markExistingAttachmentRemove(${i})" title="Gỡ tệp này">✕ Gỡ</button>`}
          </div>
        </div>
      `;
    }

    // Newly staged upload files
    for (let i = 0; i < this.stagedFiles.length; i++) {
      const f = this.stagedFiles[i];
      const szHuman = (f.size < 1048576) ? `${round1(f.size / 1024)} KB` : `${round2(f.size / 1048576)} MB`;
      const isImg = f.type.startsWith("image/");
      itemsHtml += `
        <div class="cr-staged-item" style="border-left: 3px solid #2563eb;">
          <div style="display: flex; align-items: center; gap: 0.35rem; min-width: 0; overflow: hidden;">
            <span>${isImg ? "🖼️" : this.getFileIcon(f.name)}</span>
            <span style="font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${this.escapeHtml(f.name)}
            </span>
            <span style="color: #2563eb; font-size: 0.72rem;">(${szHuman}) • Sẽ tải lên</span>
          </div>
          <button type="button" class="cr-staged-remove" onclick="CustomReminderManager.removeStagedFile(${i})" title="Bỏ chọn">✕</button>
        </div>
      `;
    }

    // Newly staged linked paths
    for (let i = 0; i < this.stagedLinkedPaths.length; i++) {
      const p = this.stagedLinkedPaths[i];
      const fname = p.split(/[\\/]/).pop();
      itemsHtml += `
        <div class="cr-staged-item" style="border-left: 3px solid #059669;">
          <div style="display: flex; align-items: center; gap: 0.35rem; min-width: 0; overflow: hidden;">
            <span>📂</span>
            <span style="font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this.escapeHtml(p)}">
              ${this.escapeHtml(fname)}
            </span>
            <span style="color: #059669; font-size: 0.72rem;">• Đường dẫn ngoài</span>
          </div>
          <button type="button" class="cr-staged-remove" onclick="CustomReminderManager.removeStagedLinkedPath(${i})" title="Bỏ chọn">✕</button>
        </div>
      `;
    }

    const totalCount = activeExistingCount + this.stagedFiles.length + this.stagedLinkedPaths.length;
    if (countEl) countEl.textContent = totalCount;

    if (totalCount > 0 || this.removedIndices.length > 0) {
      container.style.display = "block";
      list.innerHTML = itemsHtml;
    } else {
      container.style.display = "none";
      list.innerHTML = "";
    }

    function round1(v) { return Math.round(v * 10) / 10; }
    function round2(v) { return Math.round(v * 100) / 100; }
  },

  setQuickDate(offsetDays, toMonday = false) {
    const date = new Date();
    if (toMonday) {
      const dayOfWeek = date.getDay();
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

    // Staged uploaded files
    for (const f of this.stagedFiles) {
      formData.append("files", f);
    }

    // Staged linked paths
    if (this.stagedLinkedPaths.length > 0) {
      formData.append("existing_file_paths", JSON.stringify(this.stagedLinkedPaths));
    }

    // Removed indices when editing
    if (this.activeEditingId && this.removedIndices.length > 0) {
      formData.append("removed_indices", JSON.stringify(this.removedIndices));
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

  openDeleteModal(id) {
    this.targetDeleteId = id;
    const item = this.reminders.find((r) => r.id === id);
    const titleEl = document.getElementById("crDeleteReminderTitle");
    if (titleEl && item) {
      titleEl.innerHTML = `Đang xóa: <strong>${this.escapeHtml(item.title)}</strong> (Thư mục: <code>reminder_${id}</code> có ${item.attachments_count || 0} tệp)`;
    }
    const modal = document.getElementById("customReminderDeleteModal");
    if (modal) modal.style.display = "flex";
  },

  closeDeleteModal() {
    this.targetDeleteId = null;
    const modal = document.getElementById("customReminderDeleteModal");
    if (modal) modal.style.display = "none";
  },

  async confirmDeleteExecute(deleteFiles) {
    const id = this.targetDeleteId;
    if (!id) return;

    try {
      const res = await fetch(`/api/v1/custom-reminders/${id}?delete_files=${deleteFiles}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Không thể xóa lời nhắc");
      this.closeDeleteModal();
      await this.loadReminders();
    } catch (err) {
      alert(err.message);
    }
  },

  async openFolder(id) {
    try {
      const res = await fetch(`/api/v1/custom-reminders/${id}/open-folder`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.status === "success") {
        console.log(data.message);
      } else {
        alert(data.message || "Không thể mở thư mục trên máy tính.");
      }
    } catch (err) {
      alert(`Lỗi khi mở thư mục: ${err.message}`);
    }
  },

  openLightbox(imageUrl) {
    const modal = document.getElementById("crImageLightboxModal");
    const img = document.getElementById("crLightboxImg");
    const dlLink = document.getElementById("crLightboxDownloadLink");
    if (!modal || !img) return;

    img.src = imageUrl;
    if (dlLink) dlLink.href = imageUrl;
    modal.style.display = "flex";
  },

  closeLightbox() {
    const modal = document.getElementById("crImageLightboxModal");
    if (modal) modal.style.display = "none";
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

function switchMasterReminderTab(tabName) {
  CustomReminderManager.switchMasterTab(tabName);
}
