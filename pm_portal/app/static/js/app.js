/**
 * Main Application Controller for Hong Ming Global PM Portal
 */

// Toast notification helper
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.setAttribute("role", type === "error" ? "alert" : "status");

  const iconMap = {
    success: "✓",
    error: "!",
    info: "i"
  };

  toast.innerHTML = `
    <span style="font-weight: 800; font-size: 1rem;" aria-hidden="true">${iconMap[type] || "i"}</span>
    <div style="flex: 1;">${message}</div>
    <button type="button" class="toast-close" aria-label="Đóng thông báo" onclick="this.parentElement.remove()">×</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

// Show/Hide Loading Overlay
function setLoading(isLoading, text = "Đang xử lý dữ liệu...") {
  const overlay = document.getElementById("globalLoadingOverlay");
  const loadingText = document.getElementById("loadingOverlayText");
  if (!overlay) return;

  if (isLoading) {
    if (loadingText) loadingText.textContent = text;
    overlay.setAttribute("aria-hidden", "false");
    overlay.style.display = "flex";
  } else {
    overlay.setAttribute("aria-hidden", "true");
    overlay.style.display = "none";
  }
}

// Helpers for showLoading and hideLoading
function showLoading(text = "Đang xử lý dữ liệu...") {
  setLoading(true, text);
}

function hideLoading() {
  setLoading(false);
}

// Switch Tabs
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-content").forEach(content => {
    content.classList.toggle("active", content.id === tabId);
  });
}

// ==========================================
// MULTIMODAL ATTACHMENT HANDLERS (Excel, Image, Docx)
// ==========================================
let currentAttachedAiFile = null;

function handleAiFileSelected(input) {
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];
  attachFileObject(file);
}

function attachFileObject(file) {
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    currentAttachedAiFile = {
      name: file.name,
      mime: file.type || "application/octet-stream",
      size: file.size,
      base64: e.target.result,
      previewUrl: file.type && file.type.startsWith("image/") ? e.target.result : null
    };
    renderAttachedAiFile();
    showToast(`Đã đính kèm "${file.name}"! Nhấn 'Gọi Gemini AI' để bắt đầu phân tích.`, "success");
  };
  reader.readAsDataURL(file);
}

function clearAttachedAiFile() {
  currentAttachedAiFile = null;
  const input = document.getElementById("aiFileInput");
  if (input) input.value = "";
  const container = document.getElementById("attachedFileContainer");
  if (container) container.style.display = "none";
  showToast("Đã hủy tệp đính kèm.", "info");
}

function renderAttachedAiFile() {
  const container = document.getElementById("attachedFileContainer");
  const nameEl = document.getElementById("attachedFileName");
  const badgeEl = document.getElementById("attachedFileTypeBadge");
  const sizeEl = document.getElementById("attachedFileSize");
  const thumbEl = document.getElementById("attachedFilePreviewThumb");

  if (!container || !currentAttachedAiFile) return;

  const f = currentAttachedAiFile;
  if (nameEl) nameEl.textContent = f.name;

  const sizeKb = f.size ? Math.round(f.size / 1024) + " KB" : "";
  if (sizeEl) sizeEl.textContent = sizeKb;

  const isImage = (f.mime && f.mime.startsWith("image/")) || /\.(png|jpg|jpeg|webp|bmp)$/i.test(f.name);
  const isExcel = /\.(xlsx|xls|xlsm)$/i.test(f.name);
  const isDocx = /\.docx$/i.test(f.name);

  if (badgeEl) {
    badgeEl.textContent = isImage ? "Ảnh Báo Giá" : isExcel ? "Bảng Tính Excel" : isDocx ? "Tài Liệu Word" : "Tệp Đính Kèm";
  }

  if (thumbEl) {
    if (isImage && f.previewUrl) {
      thumbEl.innerHTML = `<img src="${f.previewUrl}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px;" alt="preview">`;
    } else if (isExcel) {
      thumbEl.innerHTML = `<svg style="width: 24px; height: 24px; color: #16a34a;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`;
    } else {
      thumbEl.innerHTML = `<svg style="width: 24px; height: 24px; color: #2563eb;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
    }
  }

  container.style.display = "flex";
}

function loadSampleJinxunText() {
  const promptInput = document.getElementById("aiPromptInput");
  if (!promptInput) return;
  promptInput.value = `Tên công ty: CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM
Địa chỉ: Thôn Trụ, Phường Việt Hòa, Thành phố Hải Phòng, Việt Nam
Mã số thuế: 0801382054
Người đại diện: HUANG YU
Chức vụ: Tổng giám đốc
Thông tin tiếng Trung:
甲方（买方）： 越南金迅科技有限公司
地址： 越南海防市越和坊柱村
税号： 0801382054
代表人： HUANG YU
职务： 总经理 
STT	Tên Sản Phẩm 產品名稱	Đơn giá 單價	Số lượng 數量	Tổng Giá 總價
1	MES Lite 系統 - PM 作業 Hệ thống MES Lite - Nghiệp vụ PM	VND 110,000,000	1 SET	VND 110,000,000
2	MES Lite 系統 - Web 介面「25 機台授權版」 Hệ thống MES Lite - Giao diện Web "Phiên bản cấp phép cho 25 máy"	VND 588,000,000	1 SET	VND 588,000,000
3	MES Lite 系統 - 客製上料 API 接口 Hệ thống MES Lite - Giao diện API cấp liệu tùy chỉnh (Option)	VND 109,583,184	1 SET	VND 109,583,184
	總共 Tổng Cộng	807,583,184 VND	Sau Giảm Giá 優惠價	VND 781,530,000`;
  showToast("Đã nạp mẫu báo giá Jinxun vào ô nhập!", "info");
}

// Handle AI Analysis (Text + Multimodal File)
async function handleAIParse() {
  const promptInput = document.getElementById("aiPromptInput");
  const rawText = promptInput?.value.trim() || "";

  if (!rawText && !currentAttachedAiFile) {
    showToast("Vui lòng dán văn bản, nhập ghi chú hoặc tải lên tệp (ảnh / Excel) cần bóc tách.", "error");
    return;
  }

  const loadingMsg = currentAttachedAiFile
    ? `Gemini AI đang phân tích tệp "${currentAttachedAiFile.name}" & trích xuất bảng sản phẩm...`
    : "Gemini AI đang phân tích dữ liệu hợp đồng & chuẩn hóa song ngữ...";

  try {
    setLoading(true, loadingMsg);
    const result = await ApiClient.parseWithAI(rawText, null, currentAttachedAiFile);

    if (result.status === "success" && result.data) {
      ContractEditor.populateForm(result.data);
      if (result.preview_html) {
        const previewContainer = document.getElementById("contractPreviewWrapper");
        if (previewContainer) previewContainer.innerHTML = result.preview_html;
      }
      showToast(result.message || "Gemini AI đã phân tích thành công và điền vào biểu mẫu!", "success");
      // Switch to products tab for user to verify
      switchTab("tabProducts");

      // Tùy chọn tự động xuất file Word sau khi AI phân tích
      const autoExportChk = document.getElementById("chkAutoExportWord");
      if (autoExportChk && autoExportChk.checked) {
        try {
          const exportDirInput = document.getElementById("txtExportDirectory");
          const customExportDir = (exportDirInput ? exportDirInput.value.trim() : "") || "E:\\Working\\Ho So Du An\\Hop Dong\\";
          localStorage.setItem("pm_portal_contract_export_dir", customExportDir);

          const contractData = ContractEditor.collectFormData();
          contractData.custom_output_dir = customExportDir;

          setLoading(true, `AI đã bóc tách xong! Đang tự động xuất file Word vào "${customExportDir}"...`);
          const docxResult = await ApiClient.generateDocx(contractData);

          if (docxResult && docxResult.status === "success") {
            showAutoExportSuccess(docxResult);
            showToast(`Đã tự động xuất file Word vào: ${customExportDir}`, "success");
          }
        } catch (exportErr) {
          console.warn("Auto export docx error:", exportErr);
          showToast(`Đã điền dữ liệu xong, nhưng lỗi tự động xuất Word: ${exportErr.message}`, "warning");
        }
      }
    } else {
      showToast(result.message || "Phân tích thất bại.", "error");
    }
  } catch (err) {
    console.error("AI Parse Error:", err);
    showToast(`Lỗi: ${err.message}`, "error");
  } finally {
    setLoading(false);
  }
}

function showAutoExportSuccess(docxResult) {
  const banner = document.getElementById("aiAutoExportBanner");
  if (!banner) return;

  const exportDirInput = document.getElementById("txtExportDirectory");
  const fallbackDir = (exportDirInput ? exportDirInput.value.trim() : "") || "E:\\Working\\Ho So Du An\\Hop Dong\\";

  // Compute final path: file_path > folder_path + file_name > fallbackDir + file_name
  const targetPath = docxResult.file_path || (docxResult.folder_path && docxResult.file_name ? `${docxResult.folder_path.replace(/[\\\/]+$/, '')}\\${docxResult.file_name}` : (docxResult.file_name ? `${fallbackDir.replace(/[\\\/]+$/, '')}\\${docxResult.file_name}` : fallbackDir));

  const fileNameEl = document.getElementById("autoExportFileName");
  const filePathEl = document.getElementById("autoExportFilePath");
  const btnOpen = document.getElementById("btnAutoExportOpenFolder");
  const btnDown = document.getElementById("btnAutoExportDownload");

  if (fileNameEl) fileNameEl.textContent = docxResult.file_name || "";
  if (filePathEl) filePathEl.textContent = targetPath;

  if (btnOpen) {
    btnOpen.onclick = () => handleOpenSystemPath(targetPath);
  }

  if (btnDown) {
    btnDown.href = docxResult.download_url || (docxResult.file_name ? `/api/v1/contracts/download/${docxResult.file_name}` : "#");
  }

  banner.style.display = "block";
}

// Handle Live Preview Update
async function handleRefreshPreview() {
  const contractData = ContractEditor.collectFormData();
  try {
    setLoading(true, "Đang tính toán lại số tiền và cập nhật bản xem mẫu...");
    const res = await ApiClient.getLivePreview(contractData);
    if (res.status === "success" && res.preview_html) {
      const previewContainer = document.getElementById("contractPreviewWrapper");
      if (previewContainer) previewContainer.innerHTML = res.preview_html;
      showToast("Đã cập nhật bản xem trước hợp đồng!", "success");
    }
  } catch (err) {
    showToast(`Lỗi cập nhật xem trước: ${err.message}`, "error");
  } finally {
    setLoading(false);
  }
}

// Handle Generate and Download DOCX
async function handleGenerateDocx() {
  const contractData = ContractEditor.collectFormData();

  if (!contractData.ben_a.ten_cong_ty) {
    showToast("Vui lòng nhập Tên công ty Bên A.", "error");
    switchTab("tabParties");
    return;
  }

  try {
    setLoading(true, "Đang điền dữ liệu vào mẫu Word chuẩn bảo toàn 100% bố cục...");
    const res = await ApiClient.generateDocx(contractData);

    if (res.status === "success" && res.download_url) {
      if (res.preview_html) {
        const previewContainer = document.getElementById("contractPreviewWrapper");
        if (previewContainer) previewContainer.innerHTML = res.preview_html;
      }

      showToast(`Tạo thành công hợp đồng: ${res.file_name}`, "success");

      // Auto trigger download
      const downloadLink = document.createElement("a");
      downloadLink.href = res.download_url;
      downloadLink.download = res.file_name;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      downloadLink.remove();

      // Refresh contracts list if available
      if (window.ContractEditor && typeof ContractEditor.loadContractsList === "function") {
        ContractEditor.loadContractsList();
      }
    } else {
      showToast(res.message || "Không thể tạo tài liệu DOCX.", "error");
    }
  } catch (err) {
    showToast(`Lỗi tạo tệp Word: ${err.message}`, "error");
  } finally {
    setLoading(false);
  }
}

// Handle Save Contract into SQLite Dossier
async function handleSaveContract() {
  const contractData = ContractEditor.collectFormData();

  if (!contractData.ben_a.ten_cong_ty) {
    showToast("Vui lòng nhập Tên công ty Bên A.", "error");
    switchTab("tabParties");
    return;
  }

  if (!contractData.so_hop_dong) {
    showToast("Vui lòng nhập Số hợp đồng.", "error");
    switchTab("tabGeneral");
    return;
  }

  try {
    setLoading(true, "Đang tạo file DOCX và lưu hợp đồng vào cơ sở dữ liệu hồ sơ...");
    const res = await fetch("/api/v1/contracts/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(contractData)
    });

    const data = await res.json();
    if (data.status === "success") {
      showSaveSuccessModal(data);
      if (window.ContractEditor && typeof ContractEditor.loadContractsList === "function") {
        ContractEditor.loadContractsList();
      }
    } else {
      showToast(data.message || "Lỗi lưu hợp đồng vào hệ thống", "error");
    }
  } catch (err) {
    showToast(`Lỗi lưu hợp đồng: ${err.message}`, "error");
  } finally {
    setLoading(false);
  }
}

function showSaveSuccessModal(data) {
  const modal = document.getElementById("saveContractSuccessModal");
  if (!modal) {
    showToast(data.message || "Đã lưu hợp đồng thành công!", "success");
    return;
  }

  const setEl = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setEl("modalSavedContractCode", data.contract_code || "");
  setEl("modalSavedCustomer", data.customer_name || "");
  setEl("modalSavedTotal", (data.total_amount ? Number(data.total_amount).toLocaleString("vi-VN") + " VND" : ""));
  setEl("modalSavedFile", data.file_name || "");
  setEl("modalSavedPath", data.file_path || data.folder_path || "");

  const btnOpen = document.getElementById("btnModalOpenFolder");
  if (btnOpen) {
    const pathToOpen = data.file_path || data.folder_path || "";
    btnOpen.onclick = () => handleOpenSystemPath(pathToOpen);
  }

  const btnDownload = document.getElementById("btnModalDownloadDocx");
  if (btnDownload) {
    btnDownload.href = data.download_url || (data.file_name ? `/api/v1/contracts/download/${data.file_name}` : "#");
  }

  modal.style.display = "flex";
}

let isOpeningAppPath = false;
async function handleOpenSystemPath(targetPath) {
  if (!targetPath) {
    const exportDirInput = document.getElementById("txtExportDirectory");
    targetPath = exportDirInput ? exportDirInput.value.trim() : "";
  }
  if (!targetPath) {
    showToast("Không tìm thấy đường dẫn tệp để mở.", "warning");
    return;
  }
  if (isOpeningAppPath) return;
  isOpeningAppPath = true;

  try {
    const res = await fetch("/api/v1/system/open-path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: targetPath })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.status === "success") {
      showToast(data.message, "success");
    } else {
      showToast(data.message || data.detail || "Không thể mở đường dẫn.", "warning");
    }
  } catch (err) {
    showToast(`Lỗi mở tệp: ${err.message}`, "error");
  } finally {
    setTimeout(() => { isOpeningAppPath = false; }, 600);
  }
}

function closeSaveContractModal() {
  const modal = document.getElementById("saveContractSuccessModal");
  if (modal) modal.style.display = "none";
}

// Copy Rendered Contract as Rich Text for Word / Email
async function handleCopyRichText() {
  const previewElement = document.getElementById("contractPaperPreview");
  if (!previewElement) {
    showToast("Không tìm thấy bản xem trước để sao chép.", "error");
    return;
  }

  try {
    const htmlContent = previewElement.outerHTML;
    const textContent = previewElement.innerText;

    if (navigator.clipboard && window.ClipboardItem) {
      const blobHtml = new Blob([htmlContent], { type: "text/html" });
      const blobText = new Blob([textContent], { type: "text/plain" });
      const data = [new ClipboardItem({
        "text/html": blobHtml,
        "text/plain": blobText
      })];
      await navigator.clipboard.write(data);
    } else {
      await navigator.clipboard.writeText(textContent);
    }
    showToast("Đã sao chép Rich Text! Bạn có thể dán (Ctrl+V) thẳng vào Word, Outlook, Gmail hoặc WeChat.", "success");
  } catch (err) {
    showToast(`Không thể sao chép tự động: ${err.message}`, "error");
  }
}

// Trigger Print / PDF
function handlePrint() {
  window.print();
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  const currentWorkDate = document.getElementById("currentWorkDate");
  if (currentWorkDate) {
    currentWorkDate.textContent = new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric"
    }).format(new Date());
  }

  const navToggle = document.querySelector(".mobile-nav-toggle");
  const sidebar = document.getElementById("primarySidebar");
  if (navToggle && sidebar) {
    navToggle.addEventListener("click", () => {
      const isOpen = sidebar.classList.toggle("mobile-open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
      navToggle.setAttribute("aria-label", isOpen ? "Đóng điều hướng" : "Mở điều hướng");
    });
  }

  document.querySelectorAll(".form-group").forEach((group) => {
    const label = group.querySelector(".form-label");
    const control = group.querySelector("input[id], textarea[id], select[id]");
    if (label && control && !label.htmlFor) label.htmlFor = control.id;
  });

  // Setup tab switching
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  // Start with one clean row instead of demo data.
  const tbody = document.getElementById("itemsTableBody");
  if (tbody && tbody.children.length === 0) {
    ContractEditor.addRow();
  }

  const today = new Date();
  const dateParts = {
    fieldDay: String(today.getDate()).padStart(2, "0"),
    fieldMonth: String(today.getMonth() + 1).padStart(2, "0"),
    fieldYear: String(today.getFullYear())
  };
  Object.entries(dateParts).forEach(([id, value]) => {
    const field = document.getElementById(id);
    if (field && !field.value) field.value = value;
  });

  const acceptanceDate = document.getElementById("ngayNghiemThu");
  if (acceptanceDate && !acceptanceDate.value) {
    acceptanceDate.value = `${dateParts.fieldDay}/${dateParts.fieldMonth}/${dateParts.fieldYear}`;
  }

  // Setup Drag & Drop on AI Box
  const dropZone = document.getElementById("aiDropZone");
  const dragOverlay = document.getElementById("aiDragOverlay");
  if (dropZone && dragOverlay) {
    ["dragenter", "dragover"].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragOverlay.style.display = "flex";
      });
    });

    ["dragleave", "drop"].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragOverlay.style.display = "none";
      });
    });

    dropZone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length > 0) {
        attachFileObject(dt.files[0]);
      }
    });
  }

  // Setup Clipboard Paste for images (Ctrl+V)
  const promptInput = document.getElementById("aiPromptInput");
  if (promptInput) {
    promptInput.addEventListener("paste", (e) => {
      const items = (e.clipboardData || e.originalEvent.clipboardData)?.items;
      if (!items) return;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf("image") === 0) {
          const blob = items[i].getAsFile();
          if (blob) {
            e.preventDefault();
            const now = new Date();
            const timeStr = `${now.getHours()}${now.getMinutes()}${now.getSeconds()}`;
            attachFileObject(new File([blob], `anh_clipboard_${timeStr}.png`, { type: blob.type }));
            showToast("Đã dán ảnh thành công từ bộ nhớ tạm (Clipboard)!", "success");
            break;
          }
        }
      }
    });
  }

  // Load saved export directory from localStorage if available
  const savedExportDir = localStorage.getItem("pm_portal_contract_export_dir");
  const exportDirInput = document.getElementById("txtExportDirectory");
  if (exportDirInput) {
    if (savedExportDir && !savedExportDir.includes("outputs\\hop_dong") && !savedExportDir.includes("outputs/hop_dong")) {
      exportDirInput.value = savedExportDir;
    } else {
      exportDirInput.value = "E:\\Working\\Ho So Du An\\Hop Dong\\";
      localStorage.setItem("pm_portal_contract_export_dir", "E:\\Working\\Ho So Du An\\Hop Dong\\");
    }
  }
});
