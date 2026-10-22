/**
 * Centralized File & Document Manager for Hong Ming Global PM Portal.
 * Handles instant search, category filtering, file actions, explorer integration, and uploading.
 */

const FileManagerApp = {
  state: {
    files: [],
    totalFiles: 0,
    totalFiltered: 0,
    categoryCounts: {},
    extensionCounts: {},
    totalSizeHuman: "0 B",
    activeCategory: "all",
    activeExtension: "all",
    searchQuery: "",
    sortBy: "updated_at_desc",
    viewMode: "table", // 'table' or 'grid'
    selectedFileForRename: null,
    searchDebounceTimer: null,
  },

  init() {
    this.bindEvents();
    this.loadFiles();
  },

  bindEvents() {
    const searchInput = document.getElementById("filemgrSearchInput");
    const clearBtn = document.getElementById("filemgrSearchClear");

    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        const val = e.target.value;
        if (clearBtn) clearBtn.style.display = val ? "block" : "none";

        clearTimeout(this.state.searchDebounceTimer);
        this.state.searchDebounceTimer = setTimeout(() => {
          this.state.searchQuery = val;
          this.loadFiles();
        }, 220);
      });

      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          this.clearSearch();
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", () => this.clearSearch());
    }

    // Drag and drop for upload modal
    const dropzone = document.getElementById("filemgrDropzone");
    const fileInput = document.getElementById("filemgrUploadInput");
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
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          fileInput.files = e.dataTransfer.files;
          this.updateSelectedFileLabel();
        }
      });
      fileInput.addEventListener("change", () => this.updateSelectedFileLabel());
    }
  },

  clearSearch() {
    const searchInput = document.getElementById("filemgrSearchInput");
    const clearBtn = document.getElementById("filemgrSearchClear");
    if (searchInput) searchInput.value = "";
    if (clearBtn) clearBtn.style.display = "none";
    this.state.searchQuery = "";
    this.loadFiles();
  },

  async loadFiles() {
    const tbody = document.getElementById("filemgrTableBody");
    const grid = document.getElementById("filemgrGridContainer");
    const empty = document.getElementById("filemgrEmpty");

    const params = new URLSearchParams({
      category: this.state.activeCategory,
      extension: this.state.activeExtension,
      search: this.state.searchQuery,
      sort_by: this.state.sortBy,
    });

    try {
      const res = await fetch(`/api/v1/files?${params.toString()}`);
      if (!res.ok) throw new Error("Không thể tải danh sách file từ máy chủ");
      const data = await res.json();

      this.state.files = data.files || [];
      this.state.totalFiles = data.total_files || 0;
      this.state.totalFiltered = data.total_filtered || 0;
      this.state.categoryCounts = data.category_counts || {};
      this.state.extensionCounts = data.extension_counts || {};
      this.state.totalSizeHuman = data.total_size_human || "0 B";

      this.renderStats();
      this.renderCategoryBadges();
      this.renderFiles();
    } catch (err) {
      console.error("Lỗi nạp file:", err);
      this.showToast("Không thể tải danh sách tài liệu: " + err.message, "error");
    }
  },

  renderStats() {
    const elTotal = document.getElementById("statTotalFiles");
    const elContracts = document.getElementById("statContracts");
    const elQuotes = document.getElementById("statQuotes");
    const elStorage = document.getElementById("statStorageUsed");

    if (elTotal) elTotal.textContent = this.state.totalFiles;
    if (elContracts) {
      const cCount = (this.state.categoryCounts["hop_dong"] || 0) + (this.state.categoryCounts["nghiem_thu"] || 0);
      elContracts.textContent = cCount;
    }
    if (elQuotes) {
      const qCount = (this.state.categoryCounts["bao_gia"] || 0) + (this.state.categoryCounts["don_xin_thanh_toan"] || 0);
      elQuotes.textContent = qCount;
    }
    if (elStorage) elStorage.textContent = this.state.totalSizeHuman;
  },

  renderCategoryBadges() {
    document.querySelectorAll(".filemgr-cat-pill").forEach((pill) => {
      const cat = pill.getAttribute("data-cat");
      const badge = pill.querySelector(".cat-count");
      if (badge) {
        if (cat === "all") {
          badge.textContent = this.state.totalFiles;
        } else {
          badge.textContent = this.state.categoryCounts[cat] || 0;
        }
      }
      if (cat === this.state.activeCategory) {
        pill.classList.add("active");
      } else {
        pill.classList.remove("active");
      }
    });

    const filteredCountEl = document.getElementById("filemgrFilteredCount");
    if (filteredCountEl) {
      filteredCountEl.textContent = `Hiển thị ${this.state.totalFiltered} / ${this.state.totalFiles} tệp tin`;
    }
  },

  setCategory(category) {
    this.state.activeCategory = category;
    this.loadFiles();
  },

  setExtension(ext) {
    this.state.activeExtension = ext;
    this.loadFiles();
  },

  setSort(sortVal) {
    this.state.sortBy = sortVal;
    this.loadFiles();
  },

  setViewMode(mode) {
    this.state.viewMode = mode;
    const btnTable = document.getElementById("btnViewTable");
    const btnGrid = document.getElementById("btnViewGrid");
    const tblCard = document.getElementById("filemgrTableCard");
    const gridContainer = document.getElementById("filemgrGridContainer");

    if (btnTable && btnGrid) {
      if (mode === "table") {
        btnTable.classList.add("active");
        btnGrid.classList.remove("active");
        if (tblCard) tblCard.style.display = "block";
        if (gridContainer) gridContainer.style.display = "none";
      } else {
        btnTable.classList.remove("active");
        btnGrid.classList.add("active");
        if (tblCard) tblCard.style.display = "none";
        if (gridContainer) gridContainer.style.display = "grid";
      }
    }
    this.renderFiles();
  },

  renderFiles() {
    const tbody = document.getElementById("filemgrTableBody");
    const grid = document.getElementById("filemgrGridContainer");
    const empty = document.getElementById("filemgrEmpty");
    const files = this.state.files;

    if (!files || files.length === 0) {
      if (empty) empty.style.display = "block";
      if (tbody) tbody.innerHTML = "";
      if (grid) grid.innerHTML = "";
      return;
    }

    if (empty) empty.style.display = "none";

    // 1. Render Table View
    if (tbody) {
      tbody.innerHTML = files.map((f) => this.renderTableRow(f)).join("");
    }

    // 2. Render Grid View
    if (grid) {
      grid.innerHTML = files.map((f) => this.renderGridCard(f)).join("");
    }
  },

  renderTableRow(f) {
    const previewBtn = f.can_preview
      ? `<button type="button" class="filemgr-btn-icon preview" onclick="FileManagerApp.previewFile('${f.id}', '${f.file_name}', '${f.file_ext}')" title="Xem trước tài liệu/hình ảnh">
          <svg class="icon" viewBox="0 0 24 24" width="15" height="15"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </button>`
      : "";

    const renameBtn = f.can_rename
      ? `<button type="button" class="filemgr-btn-icon rename" onclick="FileManagerApp.openRenameModal('${f.id}', '${f.file_name}')" title="Đổi tên file">
          <svg class="icon" viewBox="0 0 24 24" width="15" height="15"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
        </button>`
      : "";

    const deleteBtn = f.can_delete
      ? `<button type="button" class="filemgr-btn-icon delete" onclick="FileManagerApp.confirmDelete('${f.id}', '${f.file_name}')" title="Xóa file">
          <svg class="icon" viewBox="0 0 24 24" width="15" height="15"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>`
      : "";

    const tabLinkBtn = f.tab_url && f.tab_url !== "/files"
      ? `<a href="${f.tab_url}" class="filemgr-btn-icon tab-link" title="Đến tab nghiệp vụ liên quan">
          <svg class="icon" viewBox="0 0 24 24" width="15" height="15"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        </a>`
      : "";

    return `
      <tr>
        <td>
          <div class="filemgr-file-cell">
            <div class="filemgr-ext-icon ${f.icon_type}">${f.file_ext}</div>
            <div class="filemgr-file-meta">
              <a href="javascript:void(0)" onclick="FileManagerApp.openFile('${f.id}', '${f.file_name}')" class="filemgr-file-name" title="Bấm để mở trực tiếp trên máy tính bằng Word/Excel (${f.file_name})">
                ${f.file_name}
              </a>
              <span class="filemgr-folder-tag" title="Thư mục: ${f.folder_relative}">
                📁 ${f.folder_name}
              </span>
            </div>
          </div>
        </td>
        <td>
          <span class="badge-cat ${f.category_badge_class}">
            ${f.category_label}
          </span>
        </td>
        <td style="white-space: nowrap; font-weight: 600; color: var(--text-muted);">
          ${f.file_size_human}
        </td>
        <td style="white-space: nowrap; color: var(--text-muted); font-size: 0.8rem;">
          ${f.updated_at_formatted}
        </td>
        <td>
          <div class="filemgr-actions">
            <button type="button" class="filemgr-btn-icon download" onclick="FileManagerApp.downloadFile('${f.id}')" title="Tải file về máy">
              <svg class="icon" viewBox="0 0 24 24" width="15" height="15"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </button>
            <button type="button" class="filemgr-btn-icon explorer" onclick="FileManagerApp.openInExplorer('${f.id}')" title="Mở thư mục chứa file trên máy tính (Windows Explorer)">
              <svg class="icon" viewBox="0 0 24 24" width="15" height="15"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            </button>
            ${previewBtn}
            ${tabLinkBtn}
            ${renameBtn}
            ${deleteBtn}
          </div>
        </td>
      </tr>
    `;
  },

  renderGridCard(f) {
    const previewBtn = f.can_preview
      ? `<button type="button" class="filemgr-btn-icon preview" onclick="FileManagerApp.previewFile('${f.id}', '${f.file_name}', '${f.file_ext}')" title="Xem trước">
          <svg class="icon" viewBox="0 0 24 24" width="14" height="14"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </button>`
      : "";

    const renameBtn = f.can_rename
      ? `<button type="button" class="filemgr-btn-icon rename" onclick="FileManagerApp.openRenameModal('${f.id}', '${f.file_name}')" title="Đổi tên">
          <svg class="icon" viewBox="0 0 24 24" width="14" height="14"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
        </button>`
      : "";

    const deleteBtn = f.can_delete
      ? `<button type="button" class="filemgr-btn-icon delete" onclick="FileManagerApp.confirmDelete('${f.id}', '${f.file_name}')" title="Xóa file">
          <svg class="icon" viewBox="0 0 24 24" width="14" height="14"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>`
      : "";

    return `
      <div class="filemgr-grid-card">
        <div class="filemgr-grid-top">
          <div class="filemgr-ext-icon ${f.icon_type}">${f.file_ext}</div>
          <div class="filemgr-grid-meta">
            <span class="badge-cat ${f.category_badge_class}" style="width: fit-content;">
              ${f.category_label}
            </span>
            <a href="javascript:void(0)" onclick="FileManagerApp.openFile('${f.id}', '${f.file_name}')" class="filemgr-file-name" title="Bấm để mở trực tiếp trên máy tính bằng Word/Excel (${f.file_name})">
              ${f.file_name}
            </a>
            <span class="filemgr-folder-tag">📁 ${f.folder_name} · ${f.file_size_human}</span>
          </div>
        </div>

        <div class="filemgr-grid-actions">
          <span style="font-size: 0.73rem; color: var(--text-dim);">${f.updated_at_formatted}</span>
          <div class="filemgr-actions">
            <button type="button" class="filemgr-btn-icon download" onclick="FileManagerApp.downloadFile('${f.id}')" title="Tải về">
              <svg class="icon" viewBox="0 0 24 24" width="14" height="14"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </button>
            <button type="button" class="filemgr-btn-icon explorer" onclick="FileManagerApp.openInExplorer('${f.id}')" title="Mở trong máy">
              <svg class="icon" viewBox="0 0 24 24" width="14" height="14"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            </button>
            ${previewBtn}
            ${renameBtn}
            ${deleteBtn}
          </div>
        </div>
      </div>
    `;
  },

  async openFile(fileId, fileName) {
    if (!fileId) return;
    try {
      this.showToast(`Đang mở "${fileName}" trên máy tính...`, "info");
      const res = await fetch("/api/v1/files/open-file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_id: fileId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Không thể mở file trên máy tính");
      this.showToast(`Đã mở "${fileName}"!`, "success");
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  downloadFile(fileId) {
    if (!fileId) return;
    window.location.href = `/api/v1/files/download/${fileId}`;
    this.showToast("Đang tải file xuống máy tính...", "info");
  },

  async openInExplorer(fileId) {
    if (!fileId) return;
    try {
      this.showToast("Đang mở File Explorer...", "info");
      const res = await fetch("/api/v1/files/open-explorer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_id: fileId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Không thể mở file explorer");
      this.showToast("Đã mở thư mục chứa file trên máy tính!", "success");
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  async openActiveFolder() {
    try {
      const cat = this.state.activeCategory;
      this.showToast("Đang mở thư mục hồ sơ trên máy...", "info");
      const res = await fetch("/api/v1/files/open-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: cat }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Không thể mở thư mục");
      this.showToast("Đã mở thư mục trên máy tính!", "success");
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  previewFile(fileId, fileName, ext) {
    const modal = document.getElementById("filemgrPreviewModal");
    const title = document.getElementById("filemgrPreviewTitle");
    const container = document.getElementById("filemgrPreviewContainer");

    if (!modal || !container) return;

    if (title) title.textContent = `Xem trước: ${fileName}`;
    container.innerHTML = '<div style="color: #94a3b8; padding: 2rem;">Đang tải xem trước...</div>';
    modal.classList.add("active");

    const url = `/api/v1/files/preview/${fileId}`;
    if (ext === "pdf") {
      container.innerHTML = `<iframe src="${url}"></iframe>`;
    } else {
      container.innerHTML = `<img src="${url}" alt="${fileName}">`;
    }
  },

  closePreviewModal() {
    const modal = document.getElementById("filemgrPreviewModal");
    if (modal) modal.classList.remove("active");
  },

  openRenameModal(fileId, currentName) {
    this.state.selectedFileForRename = { fileId, currentName };
    const modal = document.getElementById("filemgrRenameModal");
    const input = document.getElementById("filemgrRenameInput");
    if (input) input.value = currentName;
    if (modal) modal.classList.add("active");
  },

  closeRenameModal() {
    const modal = document.getElementById("filemgrRenameModal");
    if (modal) modal.classList.remove("active");
    this.state.selectedFileForRename = null;
  },

  async handleRenameSubmit() {
    if (!this.state.selectedFileForRename) return;
    const input = document.getElementById("filemgrRenameInput");
    const newName = input ? input.value.trim() : "";
    if (!newName) {
      this.showToast("Vui lòng nhập tên file mới!", "warning");
      return;
    }

    try {
      const res = await fetch("/api/v1/files/rename", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_id: this.state.selectedFileForRename.fileId,
          new_name: newName,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Không thể đổi tên file");

      this.showToast(`Đã đổi tên thành công: ${data.new_name}`, "success");
      this.closeRenameModal();
      this.loadFiles();
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  confirmDelete(fileId, fileName) {
    if (confirm(`Bạn có chắc chắn muốn xóa file "${fileName}" không?\nHành động này sẽ xóa file khỏi máy tính.`)) {
      this.executeDelete(fileId);
    }
  },

  async executeDelete(fileId) {
    try {
      const res = await fetch(`/api/v1/files/${fileId}`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Không thể xóa file");

      this.showToast(data.message || "Đã xóa file thành công!", "success");
      this.loadFiles();
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  openUploadModal() {
    const modal = document.getElementById("filemgrUploadModal");
    const select = document.getElementById("filemgrUploadCategory");
    if (select && this.state.activeCategory !== "all") {
      select.value = this.state.activeCategory;
    }
    if (modal) modal.classList.add("active");
  },

  closeUploadModal() {
    const modal = document.getElementById("filemgrUploadModal");
    if (modal) modal.classList.remove("active");
    const input = document.getElementById("filemgrUploadInput");
    if (input) input.value = "";
    this.updateSelectedFileLabel();
  },

  updateSelectedFileLabel() {
    const input = document.getElementById("filemgrUploadInput");
    const label = document.getElementById("filemgrSelectedFileLabel");
    if (label) {
      if (input && input.files && input.files.length > 0) {
        label.textContent = `Đã chọn: ${input.files[0].name} (${(input.files[0].size / 1024).toFixed(1)} KB)`;
        label.style.color = "var(--primary)";
      } else {
        label.textContent = "Chưa chọn file nào";
        label.style.color = "var(--text-muted)";
      }
    }
  },

  async handleUploadSubmit() {
    const input = document.getElementById("filemgrUploadInput");
    const select = document.getElementById("filemgrUploadCategory");
    if (!input || !input.files || input.files.length === 0) {
      this.showToast("Vui lòng chọn hoặc kéo thả 1 file để tải lên!", "warning");
      return;
    }

    const file = input.files[0];
    const category = select ? select.value : "hop_dong";

    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);

    try {
      this.showToast("Đang tải file lên kho tài liệu...", "info");
      const res = await fetch("/api/v1/files/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Không thể tải file lên");

      this.showToast(`Tải file thành công: ${file.name}`, "success");
      this.closeUploadModal();
      this.loadFiles();
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) {
      alert(message);
      return;
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-body">
        <span>${message}</span>
      </div>
    `;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add("fade-out");
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  },
};

document.addEventListener("DOMContentLoaded", () => {
  FileManagerApp.init();
});
