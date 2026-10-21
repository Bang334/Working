/**
 * Acceptance Editor Module for Hong Ming Global PM Portal.
 * Handles interactive table editing, calculations, AI parsing, live preview, and document generation.
 */

// Top-level declared loading helpers to ensure availability in all contexts
function showLoading(text = "Đang xử lý dữ liệu...") {
  const overlay = document.getElementById("globalLoadingOverlay");
  const loadingText = document.getElementById("loadingOverlayText");
  if (loadingText && text) loadingText.textContent = text;
  if (overlay) {
    overlay.setAttribute("aria-hidden", "false");
    overlay.style.display = "flex";
  }
}

function hideLoading() {
  const overlay = document.getElementById("globalLoadingOverlay");
  if (overlay) {
    overlay.setAttribute("aria-hidden", "true");
    overlay.style.display = "none";
  }
}

const AcceptanceEditor = {
  data: {
    tieu_de_viet: "BIÊN BẢN KIỂM TRA & NGHIỆM THU THIẾT BỊ SAU SỬA CHỮA",
    tieu_de_trung: "維修設備檢查及驗收記錄",
    so_hop_dong: "",
    so_bien_ban: "",
    ngay_nghiem_thu: "",
    ben_a: {
      ten_cong_ty: "",
      ten_tieng_trung: "",
      dia_chi: "",
      mst: "",
      nguoi_dai_dien: "",
      chuc_vu: ""
    },
    ben_b: {
      ten_cong_ty: "CÔNG TY TNHH TOÀN CẦU HONG MING",
      ten_tieng_trung: "宏明環球有限公司",
      dia_chi: "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh",
      mst: "0318280158",
      nguoi_dai_dien: "TANG WEI LI",
      chuc_vu: "Tổng Giám Đốc"
    },
    hang_muc: [],
    tong_so_luong: "0 Thiết bị",
    tong_tien_so: "",
    ghi_chu_1: "",
    ghi_chu_2: "",
    ghi_chu_3: "",
    tao_cac_sheet_anh: false
  },

  initTabs() {
    document.querySelectorAll(".tab-btn[data-tab]").forEach(btn => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-tab");
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
        btn.classList.add("active");
        const target = document.getElementById(targetId);
        if (target) target.classList.add("active");
      });
    });
  },

  populateForm(data) {
    if (!data) return;
    this.data = JSON.parse(JSON.stringify(data));

    // Headers & Meta
    const elTieuDeViet = document.getElementById("tieuDeViet");
    if (elTieuDeViet) elTieuDeViet.value = data.tieu_de_viet || "";

    const elTieuDeTrung = document.getElementById("tieuDeTrung");
    if (elTieuDeTrung) elTieuDeTrung.value = data.tieu_de_trung || "";

    const elSoHD = document.getElementById("soHopDong");
    if (elSoHD) elSoHD.value = data.so_hop_dong || "";

    const elSoBB = document.getElementById("soBienBan");
    if (elSoBB) elSoBB.value = data.so_bien_ban || "";

    const elNgayNT = document.getElementById("ngayNghiemThu");
    if (elNgayNT) elNgayNT.value = data.ngay_nghiem_thu || "";

    // Party A
    const benA = data.ben_a || {};
    const elBenAViet = document.getElementById("benATenViet");
    if (elBenAViet) elBenAViet.value = benA.ten_cong_ty || "";

    const elBenATrung = document.getElementById("benATenTrung");
    if (elBenATrung) elBenATrung.value = benA.ten_tieng_trung || "";

    const elBenADiaChi = document.getElementById("benADiaChi");
    if (elBenADiaChi) elBenADiaChi.value = benA.dia_chi || "";

    // Party B
    const benB = data.ben_b || {};
    const elBenBViet = document.getElementById("benBTenViet");
    if (elBenBViet) elBenBViet.value = benB.ten_cong_ty || "CÔNG TY TNHH TOÀN CẦU HONG MING";

    const elBenBDaiDien = document.getElementById("benBDaiDien");
    if (elBenBDaiDien) elBenBDaiDien.value = benB.nguoi_dai_dien || "TANG WEI LI";

    // Notes
    const elGhiChu = document.getElementById("ghiChuNoiDung");
    if (elGhiChu) elGhiChu.value = data.ghi_chu || data.ghi_chu_1 || "";

    const elTongTien = document.getElementById("tongTienSo");
    if (elTongTien) elTongTien.value = data.tong_tien_so || "";

    const elTaoSheetAnh = document.getElementById("taoSheetAnhCheck");
    if (elTaoSheetAnh) elTaoSheetAnh.checked = !!data.tao_cac_sheet_anh;

    // Items table
    this.renderTable(data.hang_muc || []);
    this.recalculate();
  },

  renderTable(items) {
    const tbody = document.getElementById("acceptanceTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    items.forEach((item, index) => {
      const stt = item.stt || (index + 1);
      const row = document.createElement("tr");
      row.className = "table-row-item";
      row.innerHTML = `
        <td style="text-align: center; vertical-align: top; padding-top: 10px;">
          <input type="number" class="form-control form-control-sm item-stt" value="${stt}" style="width: 45px; text-align: center;" onchange="AcceptanceEditor.recalculate()">
        </td>
        <td>
          <input type="text" class="form-control form-control-sm item-sn" value="${this.escapeHtml(item.serial_number || '')}" placeholder="Serial / Mã máy" style="font-weight: 600; font-family: monospace;" oninput="AcceptanceEditor.recalculate()">
        </td>
        <td>
          <textarea class="form-control form-control-sm item-loi" rows="2" placeholder="Lỗi ban đầu (song ngữ)" oninput="AcceptanceEditor.recalculate()">${this.escapeHtml(item.loi_ban_dau || '')}</textarea>
        </td>
        <td style="width: 100px;">
          <input type="text" class="form-control form-control-sm item-bp" value="${this.escapeHtml(item.bo_phan || 'CNC')}" placeholder="Bộ phận" oninput="AcceptanceEditor.recalculate()">
        </td>
        <td>
          <textarea class="form-control form-control-sm item-hm" rows="2" placeholder="Hạng mục kiểm tra & xử lý" oninput="AcceptanceEditor.recalculate()">${this.escapeHtml(item.hang_muc_kiem_tra || '')}</textarea>
        </td>
        <td style="width: 120px;">
          <input type="text" class="form-control form-control-sm item-kq" value="${this.escapeHtml(item.ket_qua || 'Đạt / 合格')}" style="color: #047857; font-weight: 600;" oninput="AcceptanceEditor.recalculate()">
        </td>
        <td style="width: 120px;">
          <input type="text" class="form-control form-control-sm item-gia" value="${this.escapeHtml(item.tong_gia || item.don_gia || '')}" placeholder="Thành tiền" oninput="AcceptanceEditor.recalculate()">
        </td>
        <td style="text-align: center; vertical-align: top; padding-top: 10px;">
          <button type="button" class="btn-icon-danger" onclick="AcceptanceEditor.removeRow(this)" title="Xóa dòng" aria-label="Xóa dòng">×</button>
        </td>
      `;
      tbody.appendChild(row);
    });
  },

  addRow(itemData = null) {
    const tbody = document.getElementById("acceptanceTableBody");
    if (!tbody) return;
    const currentCount = tbody.querySelectorAll("tr").length;
    const newItem = itemData || {
      stt: currentCount + 1,
      serial_number: "",
      loi_ban_dau: "",
      bo_phan: "CNC",
      hang_muc_kiem_tra: "Đã kiểm tra nhưng không có lỗi\n已檢查，未發現異常",
      ket_qua: "Đạt / 合格",
      tong_gia: ""
    };
    const row = document.createElement("tr");
    row.className = "table-row-item";
    row.innerHTML = `
      <td style="text-align: center; vertical-align: top; padding-top: 10px;">
        <input type="number" class="form-control form-control-sm item-stt" value="${newItem.stt}" style="width: 45px; text-align: center;" onchange="AcceptanceEditor.recalculate()">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm item-sn" value="${this.escapeHtml(newItem.serial_number)}" placeholder="Serial / Mã máy" style="font-weight: 600; font-family: monospace;" oninput="AcceptanceEditor.recalculate()">
      </td>
      <td>
        <textarea class="form-control form-control-sm item-loi" rows="2" placeholder="Lỗi ban đầu (song ngữ)" oninput="AcceptanceEditor.recalculate()">${this.escapeHtml(newItem.loi_ban_dau)}</textarea>
      </td>
      <td style="width: 100px;">
        <input type="text" class="form-control form-control-sm item-bp" value="${this.escapeHtml(newItem.bo_phan)}" placeholder="Bộ phận" oninput="AcceptanceEditor.recalculate()">
      </td>
      <td>
        <textarea class="form-control form-control-sm item-hm" rows="2" placeholder="Hạng mục kiểm tra & xử lý" oninput="AcceptanceEditor.recalculate()">${this.escapeHtml(newItem.hang_muc_kiem_tra)}</textarea>
      </td>
      <td style="width: 120px;">
        <input type="text" class="form-control form-control-sm item-kq" value="${this.escapeHtml(newItem.ket_qua)}" style="color: #047857; font-weight: 600;" oninput="AcceptanceEditor.recalculate()">
      </td>
      <td style="width: 120px;">
        <input type="text" class="form-control form-control-sm item-gia" value="${this.escapeHtml(newItem.tong_gia)}" placeholder="Thành tiền" oninput="AcceptanceEditor.recalculate()">
      </td>
      <td style="text-align: center; vertical-align: top; padding-top: 10px;">
        <button type="button" class="btn-icon-danger" onclick="AcceptanceEditor.removeRow(this)" title="Xóa dòng" aria-label="Xóa dòng">×</button>
      </td>
    `;
    tbody.appendChild(row);
    this.recalculate();
  },

  removeRow(btn) {
    const row = btn.closest("tr");
    if (row) {
      row.remove();
      this.reindexRows();
      this.recalculate();
    }
  },

  reindexRows() {
    const tbody = document.getElementById("acceptanceTableBody");
    if (!tbody) return;
    const rows = tbody.querySelectorAll("tr");
    rows.forEach((r, idx) => {
      const sttInput = r.querySelector(".item-stt");
      if (sttInput) sttInput.value = idx + 1;
    });
  },

  readFormData() {
    const rows = document.querySelectorAll("#acceptanceTableBody tr");
    const items = [];
    let calculatedTotal = 0;

    rows.forEach((r, idx) => {
      const stt = parseInt(r.querySelector(".item-stt")?.value) || (idx + 1);
      const sn = r.querySelector(".item-sn")?.value.trim() || "";
      const loi = r.querySelector(".item-loi")?.value.trim() || "";
      const bp = r.querySelector(".item-bp")?.value.trim() || "CNC";
      const hm = r.querySelector(".item-hm")?.value.trim() || "";
      const kq = r.querySelector(".item-kq")?.value.trim() || "Đạt / 合格";
      const gia = r.querySelector(".item-gia")?.value.trim() || "";

      const rawNum = gia.replace(/[^\d]/g, "");
      if (rawNum) calculatedTotal += parseInt(rawNum);

      items.push({
        stt,
        serial_number: sn,
        loi_ban_dau: loi,
        bo_phan: bp,
        hang_muc_kiem_tra: hm,
        ket_qua: kq,
        don_gia: gia,
        tong_gia: gia,
        can_anh: true
      });
    });

    const userTotalVal = document.getElementById("tongTienSo")?.value.trim() || "";
    const finalTotal = userTotalVal || (calculatedTotal > 0 ? calculatedTotal.toLocaleString("vi-VN") : "0");

    return {
      tieu_de_viet: document.getElementById("tieuDeViet")?.value.trim() || "BIÊN BẢN KIỂM TRA & NGHIỆM THU THIẾT BỊ SAU SỬA CHỮA",
      tieu_de_trung: document.getElementById("tieuDeTrung")?.value.trim() || "維修設備檢查及驗收記錄",
      so_hop_dong: document.getElementById("soHopDong")?.value.trim() || "",
      so_bien_ban: document.getElementById("soBienBan")?.value.trim() || "",
      ngay_nghiem_thu: document.getElementById("ngayNghiemThu")?.value.trim() || "",
      ben_a: {
        ten_cong_ty: document.getElementById("benATenViet")?.value.trim() || "",
        ten_tieng_trung: document.getElementById("benATenTrung")?.value.trim() || "",
        dia_chi: document.getElementById("benADiaChi")?.value.trim() || ""
      },
      ben_b: {
        ten_cong_ty: document.getElementById("benBTenViet")?.value.trim() || "CÔNG TY TNHH TOÀN CẦU HONG MING",
        ten_tieng_trung: "宏明環球有限公司",
        dia_chi: "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh",
        mst: "0318280158",
        nguoi_dai_dien: document.getElementById("benBDaiDien")?.value.trim() || "TANG WEI LI",
        chuc_vu: "Tổng Giám Đốc"
      },
      hang_muc: items,
      tong_so_luong: `${items.length} Thiết bị`,
      tong_tien_so: finalTotal,
      ghi_chu: document.getElementById("ghiChuNoiDung")?.value.trim() || "",
      tao_cac_sheet_anh: document.getElementById("taoSheetAnhCheck")?.checked || false
    };
  },

  recalculate() {
    const rows = document.querySelectorAll("#acceptanceTableBody tr");
    const countDisplay = document.getElementById("summaryDeviceCount");
    const totalDisplay = document.getElementById("summaryAmountDisplay");
    let total = 0;

    rows.forEach(r => {
      const giaStr = r.querySelector(".item-gia")?.value || "";
      const rawDigits = giaStr.replace(/[^\d]/g, "");
      if (rawDigits) total += parseInt(rawDigits);
    });

    if (countDisplay) countDisplay.textContent = `${rows.length} Thiết bị`;
    if (totalDisplay) {
      if (total > 0) {
        totalDisplay.textContent = total.toLocaleString("vi-VN").replace(/,/g, ".") + " VND";
      } else {
        const inputVal = document.getElementById("tongTienSo")?.value || "0";
        totalDisplay.textContent = inputVal + " VND";
      }
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
  }
};

// ==========================================
// REPAIR WORKBOOK UPLOAD
// ==========================================

const RepairWorkbookUpload = {
  file: null,
  maxBytes: 20 * 1024 * 1024
};

function initRepairWorkbookUpload() {
  const input = document.getElementById("repairFileInput");
  const dropzone = document.getElementById("repairDropzone");
  const clearButton = document.getElementById("repairClearFileButton");
  if (!input || !dropzone) return;

  input.addEventListener("change", () => {
    selectRepairWorkbook(input.files && input.files[0] ? input.files[0] : null);
  });

  ["dragenter", "dragover"].forEach(eventName => {
    dropzone.addEventListener(eventName, event => {
      event.preventDefault();
      event.stopPropagation();
      dropzone.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropzone.addEventListener(eventName, event => {
      event.preventDefault();
      event.stopPropagation();
      dropzone.classList.remove("is-dragover");
    });
  });

  dropzone.addEventListener("drop", event => {
    const file = event.dataTransfer && event.dataTransfer.files
      ? event.dataTransfer.files[0]
      : null;
    selectRepairWorkbook(file);
  });

  dropzone.addEventListener("keydown", event => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });

  if (clearButton) {
    clearButton.addEventListener("click", clearRepairWorkbookSelection);
  }
}

function formatUploadFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 KB";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setRepairUploadStatus(message, isError = false) {
  const status = document.getElementById("repairUploadStatus");
  if (!status) return;
  status.textContent = message;
  status.classList.toggle("is-error", isError);
}

function resetRepairUploadResult() {
  const resultPanel = document.getElementById("repairResultPanel");
  if (resultPanel) resultPanel.hidden = true;
}

function selectRepairWorkbook(file) {
  const input = document.getElementById("repairFileInput");
  const dropzone = document.getElementById("repairDropzone");
  const selected = document.getElementById("repairSelectedFile");
  const processButton = document.getElementById("repairProcessButton");
  const fileName = document.getElementById("repairSelectedFileName");
  const fileSize = document.getElementById("repairSelectedFileSize");

  resetRepairUploadResult();
  if (!file) {
    clearRepairWorkbookSelection();
    return;
  }

  const validExtension = file.name.toLowerCase().endsWith(".xlsx");
  if (!validExtension) {
    if (input) input.value = "";
    RepairWorkbookUpload.file = null;
    if (selected) selected.hidden = true;
    if (processButton) processButton.disabled = true;
    if (dropzone) dropzone.classList.remove("has-file");
    setRepairUploadStatus("File không hợp lệ. Vui lòng chọn đúng định dạng .xlsx.", true);
    showToast("Chỉ chấp nhận file Excel .xlsx.", "warning");
    return;
  }

  if (!file.size || file.size > RepairWorkbookUpload.maxBytes) {
    if (input) input.value = "";
    RepairWorkbookUpload.file = null;
    if (selected) selected.hidden = true;
    if (processButton) processButton.disabled = true;
    if (dropzone) dropzone.classList.remove("has-file");
    setRepairUploadStatus("File phải có dữ liệu và không vượt quá 20 MB.", true);
    showToast("Dung lượng file không hợp lệ.", "warning");
    return;
  }

  RepairWorkbookUpload.file = file;
  if (fileName) fileName.textContent = file.name;
  if (fileSize) fileSize.textContent = `${formatUploadFileSize(file.size)} · Sẵn sàng xử lý`;
  if (selected) selected.hidden = false;
  if (processButton) processButton.disabled = false;
  if (dropzone) dropzone.classList.add("has-file");
  setRepairUploadStatus("File hợp lệ. Bấm nút bên dưới để Gemini phân tích ghi chú.");
}

function clearRepairWorkbookSelection() {
  const input = document.getElementById("repairFileInput");
  const dropzone = document.getElementById("repairDropzone");
  const selected = document.getElementById("repairSelectedFile");
  const processButton = document.getElementById("repairProcessButton");
  RepairWorkbookUpload.file = null;
  if (input) input.value = "";
  if (selected) selected.hidden = true;
  if (processButton) processButton.disabled = true;
  if (dropzone) dropzone.classList.remove("has-file", "is-dragover");
  resetRepairUploadResult();
  setRepairUploadStatus("Chưa chọn file biên bản sửa chữa.");
}

async function handleProcessRepairWorkbook() {
  const file = RepairWorkbookUpload.file;
  const processButton = document.getElementById("repairProcessButton");
  if (!file) {
    setRepairUploadStatus("Vui lòng chọn file .xlsx trước khi xử lý.", true);
    showToast("Vui lòng chọn file biên bản sửa chữa.", "warning");
    return;
  }

  const formData = new FormData();
  formData.append("file", file, file.name);

  // Thêm mã hợp đồng liên kết (nếu người dùng chọn)
  const contractSelect = document.getElementById("acceptanceContractSelect");
  const selectedContract = contractSelect ? contractSelect.value.trim() : "";
  if (selectedContract) {
    formData.append("contract_code", selectedContract);
  }

  if (processButton) {
    processButton.disabled = true;
    processButton.setAttribute("aria-busy", "true");
  }
  setRepairUploadStatus("Đang tải file lên và phân tích ghi chú bằng Gemini...");
  showLoading("Đang đọc biên bản sửa chữa, đối chiếu serial và tạo file nghiệm thu...");

  try {
    const response = await fetch("/api/v1/acceptance/process-repair-file", {
      method: "POST",
      body: formData
    });
    const result = await response.json();
    if (!response.ok || result.status !== "success") {
      throw new Error(result.message || "Máy chủ không thể xử lý file tải lên.");
    }

    const panel = document.getElementById("repairResultPanel");
    const summary = document.getElementById("repairResultSummary");
    const recordCount = document.getElementById("repairRecordCount");
    const assigned = document.getElementById("repairAssignedCount");
    const ignored = document.getElementById("repairIgnoredCount");
    const model = document.getElementById("repairGeminiModel");
    const download = document.getElementById("repairDownloadButton");
    const contractBadge = document.getElementById("repairResultContractBadge");

    if (summary) summary.textContent = `${result.source_file_name} đã được xử lý và giữ nguyên bố cục mẫu nghiệm thu.`;
    if (recordCount) recordCount.textContent = String(result.record_count || 0);
    if (assigned) assigned.textContent = String(result.assigned_count || 0);
    if (ignored) ignored.textContent = String(result.ignored_note_count || 0);
    if (model) model.textContent = result.gemini_model || "Gemini";
    if (download) {
      download.href = result.download_url;
      download.download = result.file_name || "Bien_Ban_Nghiem_Thu.xlsx";
    }

    // Hiển thị trạng thái liên kết hợp đồng
    if (contractBadge) {
      if (result.is_linked_contract && result.contract_code) {
        contractBadge.style.display = "block";
        contractBadge.innerHTML = `
          <span style="color: #1d4ed8; background: #dbeafe; padding: 4px 10px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px;">
            <span>📋 Đã liên kết với Hợp đồng:</span>
            <strong style="font-family: monospace;">${escapeHtml(result.contract_code)}</strong>
            ${result.customer_name ? `<span>(${escapeHtml(result.customer_name)})</span>` : ""}
          </span>
        `;
      } else {
        contractBadge.style.display = "block";
        contractBadge.innerHTML = `
          <span style="color: #475569; background: #f1f5f9; padding: 4px 10px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px;">
            <span>ℹ️ Biên bản nghiệm thu độc lập (Không liên kết hợp đồng)</span>
          </span>
        `;
      }
    }

    if (panel) panel.hidden = false;

    setRepairUploadStatus("Xử lý hoàn tất. File nghiệm thu đã sẵn sàng để tải xuống.");
    showToast(result.message || "Đã tạo file nghiệm thu thành công.", "success");
    if (typeof loadAcceptanceFilesList === "function") {
      loadAcceptanceFilesList();
    }
  } catch (error) {
    resetRepairUploadResult();
    setRepairUploadStatus(error.message || "Không thể xử lý file tải lên.", true);
    showToast(error.message || "Lỗi xử lý file biên bản sửa chữa.", "error");
  } finally {
    hideLoading();
    if (processButton) {
      processButton.disabled = !RepairWorkbookUpload.file;
      processButton.removeAttribute("aria-busy");
    }
  }
}

// ==========================================
// CONTRACT LINKING DROPDOWN
// ==========================================

async function loadAcceptanceContractsList() {
  const select = document.getElementById("acceptanceContractSelect");
  if (!select) return;

  try {
    const res = await fetch("/api/v1/contracts/list");
    const json = await res.json();
    if (!res.ok || json.status !== "success") return;

    const contracts = json.data || [];
    const urlParams = new URLSearchParams(window.location.search);
    const qCode = (urlParams.get("contract_code") || "").trim();

    select.innerHTML = '<option value="">-- Không liên kết (Tạo biên bản nghiệm thu độc lập) --</option>';

    contracts.forEach(c => {
      const code = c.contract_code || "";
      if (!code) return;
      const cust = c.customer_name_vi || c.project_name_vi || "";
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = `${code} — ${cust}`.trim();
      if (qCode && (code.toLowerCase() === qCode.toLowerCase())) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    onAcceptanceContractSelectChange(select.value);
  } catch (err) {
    console.warn("Could not load contracts list for acceptance:", err);
  }
}

function onAcceptanceContractSelectChange(val) {
  const hint = document.getElementById("acceptanceContractHint");
  if (!hint) return;
  if (val) {
    hint.innerHTML = `<span style="color: #1d4ed8; font-weight: 600;">✅ Sẽ liên kết biên bản nghiệm thu vào hồ sơ Hợp đồng <strong>${escapeHtml(val)}</strong>.</span>`;
  } else {
    hint.innerHTML = `💡 Nếu có hợp đồng tương ứng, hệ thống sẽ tự động gắn biên bản nghiệm thu vào hồ sơ hợp đồng. Nếu không chọn hoặc không có, biên bản sẽ được lưu độc lập.`;
  }
}

// ==========================================
// PRESET SAMPLE DATA
// ==========================================

function loadSampleCXTechnology() {
  const promptInput = document.getElementById("aiPromptInput");
  if (promptInput) {
    promptInput.value = `浤詺資訊責任有限公司
Hardware Delivery Receipt
硬體交貨簽收單 Đơn Ký Nhận Bàn Giao PhầnCứng
合約編號 Số Hợp Đồng ：HM-FINEPRO-20261009.001
甲方 (買方) Bên Mua：CÔNG TY CỔ PHẦN CX Technology (VN)
乙方 (賣方) Bên Bán：CÔNG TY TNHH TOÀN CẦU HONG MING
STT	Tên Sản Phẩm	Hạng mục yêu cầu kiểm tra	Bộ phận gửi sửa	Kết quả kiểm tra	Số lượng	Đơn Giá	Tổng Giá
1	RFR900NA55RSWLBA574	Cò bắn không nhả 扳机扣住不松	CNC	No error founds	1	550000	550000
2	EF550RA4LAWBHI677	Màn hình lỗi 螢幕故障	CNC	Barcode	1	8000000	8000000
3	RFR900NA55RSWLBA565	Cò bắn không nhả 扳机扣住不松	CNC	Mounting Adapter	1	3500000	3500000
4	EF550RA4LAWBHI641	Cò bắn → 扳机 Sạc không vô điện → 充电器无法充电	xi treo	No error founds	1	550000	550000
5	EF550RA4LAWBHI657	Cò bắn → 扳机 Sạc không vô điện → 充电器无法充电	xi treo	No error founds	1	550000	550000
6	EF550RA4LAWBHI650	Cò bắn → 扳机 Sạc không vô điện → 充电器无法充电	xi treo	No error founds	1	550000	550000
TỔNG THÀNH TIỀN: 13.700.000 VND`;
  }

  const cxData = {
    tieu_de_viet: "BIÊN BẢN KIỂM TRA & NGHIỆM THU THIẾT BỊ SAU SỬA CHỮA",
    tieu_de_trung: "維修設備檢查及驗收記錄",
    so_hop_dong: "HM-FINEPRO-20261009.001",
    so_bien_ban: "001/2026/BBNT-SC",
    ngay_nghiem_thu: "09/10/2026",
    ben_a: {
      ten_cong_ty: "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
      ten_tieng_trung: "CX Technology (VN) 股份有限公司",
      dia_chi: "KCX Tân Thuận, Phường Tân Thuận Đông, Quận 7, TP.HCM",
      mst: "0301445778"
    },
    ben_b: {
      ten_cong_ty: "CÔNG TY TNHH TOÀN CẦU HONG MING",
      ten_tieng_trung: "宏明環球有限公司",
      dia_chi: "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh",
      mst: "0318280158",
      nguoi_dai_dien: "TANG WEI LI",
      chuc_vu: "Tổng Giám Đốc"
    },
    hang_muc: [
      {
        stt: 1,
        serial_number: "RFR900NA55RSWLBA574",
        loi_ban_dau: "Cò bắn không nhả\n扳機扣住不鬆",
        bo_phan: "CNC",
        hang_muc_kiem_tra: "Kiểm tra cò bắn & chức năng quét trigger scan\n檢查扳機及掃描功能",
        ket_qua: "Đạt / 合格",
        tong_gia: "550.000 VND",
        xu_ly: "No error founds\n(Không phát hiện lỗi phát sinh)",
        can_anh: true
      },
      {
        stt: 2,
        serial_number: "EF550RA4LAWBHI677",
        loi_ban_dau: "Màn hình lỗi\n螢幕故障",
        bo_phan: "CNC",
        hang_muc_kiem_tra: "Kiểm tra hiển thị màn hình & đầu quét barcode\n檢查螢幕顯示及條碼掃描功能",
        ket_qua: "Đạt / 合格",
        tong_gia: "8.000.000 VND",
        xu_ly: "Barcode\n(Xử lý & thay cụm Barcode)",
        can_anh: true
      },
      {
        stt: 3,
        serial_number: "RFR900NA55RSWLBA565",
        loi_ban_dau: "Cò bắn không nhả\n扳機扣住不鬆",
        bo_phan: "CNC",
        hang_muc_kiem_tra: "Kiểm tra cò bắn & gá chuyển đổi Mounting Adapter\n檢查扳機及轉接支架功能",
        ket_qua: "Đạt / 合格",
        tong_gia: "3.500.000 VND",
        xu_ly: "Mounting Adapter\n(Thay thế Mounting Adapter)",
        can_anh: true
      },
      {
        stt: 4,
        serial_number: "EF550RA4LAWBHI641",
        loi_ban_dau: "Cò bắn & Sạc không vô điện\n扳機故障及無法充電",
        bo_phan: "Xi treo\n吊鍍",
        hang_muc_kiem_tra: "Kiểm tra cò bắn & chức năng sạc pin\n檢查扳機及電池充電功能",
        ket_qua: "Đạt / 合格",
        tong_gia: "550.000 VND",
        xu_ly: "No error founds\n(Không phát hiện lỗi phát sinh)",
        can_anh: true
      },
      {
        stt: 5,
        serial_number: "EF550RA4LAWBHI657",
        loi_ban_dau: "Cò bắn & Sạc không vô điện\n扳機故障及無法充電",
        bo_phan: "Xi treo\n吊鍍",
        hang_muc_kiem_tra: "Kiểm tra cò bắn & chức năng sạc pin\n檢查扳機及電池充電功能",
        ket_qua: "Đạt / 合格",
        tong_gia: "550.000 VND",
        xu_ly: "No error founds\n(Không phát hiện lỗi phát sinh)",
        can_anh: true
      },
      {
        stt: 6,
        serial_number: "EF550RA4LAWBHI650",
        loi_ban_dau: "Cò bắn & Sạc không vô điện\n扳機故障及無法充電",
        bo_phan: "Xi treo\n吊鍍",
        hang_muc_kiem_tra: "Kiểm tra cò bắn & chức năng sạc pin\n檢查扳機及電池充電功能",
        ket_qua: "Đạt / 合格",
        tong_gia: "550.000 VND",
        xu_ly: "No error founds\n(Không phát hiện lỗi phát sinh)",
        can_anh: true
      }
    ],
    tong_so_luong: "6 Thiết bị",
    tong_tien_so: "13.700.000",
    ghi_chu: "",
    tao_cac_sheet_anh: true
  };

  AcceptanceEditor.populateForm(cxData);
  handleRefreshAcceptancePreview();
  showToast("Đã nạp mẫu Nghiệm Thu CX Technology (6 Thiết Bị - 13.700.000 VND) thành công!", "success");
}

function loadSampleProjectFAC() {
  const facData = {
    tieu_de_viet: "BIÊN BẢN NGHIỆM THU VÀ BÀN GIAO ĐƯA VÀO SỬ DỤNG",
    tieu_de_trung: "驗收暨移交使用確認書",
    so_hop_dong: "HMV-20261013-001",
    so_bien_ban: "002/2026/BBNT-FAC",
    ngay_nghiem_thu: "13/10/2026",
    ben_a: {
      ten_cong_ty: "CÔNG TY TNHH VONMAX (VN)",
      ten_tieng_trung: "弘聲科技（越南）有限公司",
      dia_chi: "KCN Quế Võ, Tỉnh Bắc Ninh, Việt Nam",
      mst: "2300998877"
    },
    ben_b: {
      ten_cong_ty: "CÔNG TY TNHH TOÀN CẦU HONG MING",
      ten_tieng_trung: "宏明環球有限公司",
      dia_chi: "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh",
      mst: "0318280158",
      nguoi_dai_dien: "TANG WEI LI",
      chuc_vu: "Tổng Giám Đốc"
    },
    hang_muc: [
      {
        stt: 1,
        serial_number: "IOT-GW-VONMAX-01",
        loi_ban_dau: "Khảo sát và lắp đặt I/O Gateway kết nối 30 máy dập",
        bo_phan: "Xưởng Dập",
        hang_muc_kiem_tra: "Đo kiểm truyền thông Modbus/TCP, tín hiệu ổn định 100%",
        ket_qua: "Đạt yêu cầu / 驗收合格",
        tong_gia: "420.000.000 VND"
      },
      {
        stt: 2,
        serial_number: "EMS-PM2100-3B-PACK",
        loi_ban_dau: "Lắp đặt 12 bộ đồng hồ đo điện đa mạch PM2100 & biến dòng CT",
        bo_phan: "Trạm Điện",
        hang_muc_kiem_tra: "Kiểm tra đo đếm điện năng và tích hợp hệ thống phần mềm EMS",
        ket_qua: "Đạt yêu cầu / 驗收合格",
        tong_gia: "380.000.000 VND"
      },
      {
        stt: 3,
        serial_number: "SRV-DELL-R750-MES",
        loi_ban_dau: "Cài đặt máy chủ Dell PowerEdge R750 và cơ sở dữ liệu MS SQL Server",
        bo_phan: "Phòng IT",
        hang_muc_kiem_tra: "Chạy thử nghiệm liên tục 168 giờ không gián đoạn",
        ket_qua: "Đạt yêu cầu / 驗收合格",
        tong_gia: "450.000.000 VND"
      }
    ],
    tong_so_luong: "3 Hạng mục",
    tong_tien_so: "1.250.000.000",
    ghi_chu_1: "Hai bên thống nhất xác nhận toàn bộ hệ thống đã chạy thử đạt tiêu chuẩn và chính thức bàn giao đưa vào sử dụng / 雙方確認系統已試運行合格並正式移交投入使用。",
    ghi_chu_3: "Biên bản này là căn cứ pháp lý để thực hiện thanh toán đợt cuối (10% - 驗收尾款) theo đúng điều khoản hợp đồng / 本確認書作為支付最後階段款項（10%尾款）之依據。",
    tao_cac_sheet_anh: false
  };

  AcceptanceEditor.populateForm(facData);
  handleRefreshAcceptancePreview();
  showToast("Đã nạp mẫu Nghiệm Thu Bàn Giao Dự Án (FAC 1.250.000.000 VND) thành công!", "success");
}

// ==========================================
// ASYNC ACTION HANDLERS
// ==========================================

async function handleAIParseAcceptance() {
  const promptInput = document.getElementById("aiPromptInput");
  const rawText = promptInput ? promptInput.value.trim() : "";
  if (!rawText) {
    showToast("Vui lòng dán nội dung đơn giao nhận, bảng kiểm tra hoặc ghi chú lỗi.", "warning");
    return;
  }


  showLoading("Gemini AI đang phân tích danh mục thiết bị và bóc tách dữ liệu...");

  try {
    const res = await fetch("/api/v1/ai/parse-acceptance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText, model_name: null })
    });

    const result = await res.json();
    hideLoading();

    if (result.status === "success") {
      AcceptanceEditor.populateForm(result.data);
      if (result.preview_html) {
        const previewWrapper = document.getElementById("acceptancePreviewWrapper");
        if (previewWrapper) previewWrapper.innerHTML = result.preview_html;
      }
      showToast(result.message || "Bóc tách dữ liệu thành công!", "success");
    } else {
      showToast(result.message || "Lỗi bóc tách AI", "error");
    }
  } catch (err) {
    hideLoading();
    showToast("Lỗi kết nối tới máy chủ: " + err.message, "error");
  }
}

async function handleRefreshAcceptancePreview() {
  const payload = AcceptanceEditor.readFormData();
  try {
    const res = await fetch("/api/v1/acceptance/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (result.status === "success") {
      const previewWrapper = document.getElementById("acceptancePreviewWrapper");
      if (previewWrapper) previewWrapper.innerHTML = result.preview_html;
    }
  } catch (err) {
    console.error("Preview error:", err);
  }
}

async function handleGenerateAcceptanceExcel() {
  const payload = AcceptanceEditor.readFormData();
  showLoading("Đang tạo tệp Excel (.xlsx) nghiệm thu chuẩn 1:1 theo mẫu...");

  try {
    const res = await fetch("/api/v1/acceptance/generate-excel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    hideLoading();

    if (result.status === "success" && result.download_url) {
      showToast("Đã tạo tệp Excel nghiệm thu thành công! Đang tải xuống...", "success");
      // Trigger download
      const link = document.createElement("a");
      link.href = result.download_url;
      link.download = result.file_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      showToast(result.message || "Lỗi xuất file Excel", "error");
    }
  } catch (err) {
    hideLoading();
    showToast("Lỗi xuất file Excel: " + err.message, "error");
  }
}

async function handleGenerateAcceptanceWord() {
  const payload = AcceptanceEditor.readFormData();
  showLoading("Đang tạo tệp Word (.docx) nghiệm thu chuẩn hành chính...");

  try {
    const res = await fetch("/api/v1/acceptance/generate-word", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    hideLoading();

    if (result.status === "success" && result.download_url) {
      showToast("Đã tạo tệp Word nghiệm thu thành công! Đang tải xuống...", "success");
      const link = document.createElement("a");
      link.href = result.download_url;
      link.download = result.file_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      showToast(result.message || "Lỗi xuất file Word", "error");
    }
  } catch (err) {
    hideLoading();
    showToast("Lỗi xuất file Word: " + err.message, "error");
  }
}

function handleCopyAcceptanceRichText() {
  const previewWrapper = document.getElementById("acceptancePreviewWrapper");
  if (!previewWrapper) return;

  const htmlContent = previewWrapper.innerHTML;
  const plainText = previewWrapper.innerText;

  if (navigator.clipboard && window.ClipboardItem) {
    const blobHtml = new Blob([htmlContent], { type: "text/html" });
    const blobText = new Blob([plainText], { type: "text/plain" });
    const item = new ClipboardItem({
      "text/html": blobHtml,
      "text/plain": blobText
    });
    navigator.clipboard.write([item]).then(() => {
      showToast("Đã sao chép Rich Text vào Clipboard! Dán trực tiếp vào Word hoặc Email.", "success");
    }).catch(err => {
      copyFallback(plainText);
    });
  } else {
    copyFallback(plainText);
  }
}

function handlePrintAcceptance() {
  const previewWrapper = document.getElementById("acceptancePreviewWrapper");
  if (!previewWrapper) return;

  const printWindow = window.open("", "_blank");
  printWindow.document.write(`
    <html>
      <head>
        <title>In Biên Bản Nghiệm Thu - Hong Ming Global</title>
        <style>
          body { margin: 0; padding: 20px; font-family: 'Times New Roman', serif; }
          @page { size: A4 portrait; margin: 15mm; }
          .contract-paper { box-shadow: none !important; padding: 0 !important; max-width: 100% !important; }
        </style>
      </head>
      <body>
        ${previewWrapper.innerHTML}
      </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
    printWindow.close();
  }, 300);
}

function copyFallback(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
  showToast("Đã sao chép văn bản vào Clipboard!", "success");
}

// ==========================================
// ACCEPTANCE FILES LIST MANAGEMENT
// ==========================================

async function loadAcceptanceFilesList() {
  const tbody = document.getElementById("acceptanceFilesTableBody");
  const emptyState = document.getElementById("acceptanceFilesEmptyState");
  const badge = document.getElementById("acceptanceFilesCountBadge");
  if (!tbody) return;

  try {
    const res = await fetch("/api/v1/acceptance/files");
    const json = await res.json();
    if (!res.ok || json.status !== "success") {
      throw new Error(json.message || "Không thể tải danh sách tệp nghiệm thu.");
    }

    const files = json.files || [];
    if (badge) badge.textContent = `${files.length} tệp`;

    if (files.length === 0) {
      tbody.innerHTML = "";
      if (emptyState) emptyState.style.display = "block";
      return;
    }

    if (emptyState) emptyState.style.display = "none";
    tbody.innerHTML = files.map((file, idx) => {
      const isDocx = file.is_docx || file.file_name.endsWith(".docx");
      const typeBadge = isDocx
        ? `<span class="badge-pill blue" style="font-weight: 700; font-size: 0.72rem;">Word (.docx) - Lắp đặt</span>`
        : `<span class="badge-pill green" style="font-weight: 700; font-size: 0.72rem;">Excel (.xlsx) - Sửa chữa</span>`;

      const iconSvg = isDocx
        ? `<svg style="width: 18px; height: 18px; color: #2563eb; flex-shrink: 0;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`
        : `<svg style="width: 18px; height: 18px; color: #16a34a; flex-shrink: 0;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;

      return `
      <tr>
        <td style="text-align: center; font-weight: 600; color: var(--text-muted);">${idx + 1}</td>
        <td style="text-align: center;">${typeBadge}</td>
        <td>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            ${iconSvg}
            <div>
              <div style="font-weight: 600; color: #0f172a; word-break: break-all;">${escapeHtml(file.file_name)}</div>
              <div style="font-size: 0.72rem; color: #64748b; font-family: monospace;">${escapeHtml(file.file_path)}</div>
            </div>
          </div>
        </td>
        <td style="text-align: center;">
          ${file.contract_code ? `
            <a href="/contracts" title="Xem hợp đồng ${escapeHtml(file.contract_code)} ${escapeHtml(file.customer_name ? '— ' + file.customer_name : '')}" style="text-decoration: none;">
              <span class="badge-pill blue" style="font-family: monospace; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 3px;">
                📋 ${escapeHtml(file.contract_code)}
              </span>
            </a>
            ${file.customer_name ? `<div style="font-size: 0.72rem; color: #64748b; margin-top: 2px; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(file.customer_name)}</div>` : ""}
          ` : `
            <span class="badge-pill" style="background: #f1f5f9; color: #64748b; font-weight: 500;">Độc lập</span>
          `}
        </td>
        <td style="text-align: center; font-size: 0.82rem; color: #475569;">
          <span class="badge-pill" style="background: #f1f5f9; color: #334155;">${file.file_size_formatted}</span>
        </td>
        <td style="text-align: center; font-size: 0.82rem; color: #64748b;">
          ${file.modified_time}
        </td>
        <td style="text-align: center;">
          <div style="display: flex; gap: 0.4rem; justify-content: center; align-items: center;">
            <a href="${file.download_url}" download="${file.file_name}" class="btn btn-sm ${isDocx ? 'btn-primary' : 'btn-success'}" title="Tải file về máy">
              <svg class="icon" viewBox="0 0 24 24" style="width: 14px; height: 14px;"><path d="M12 3v12M7 10l5 5 5-5M5 21h14"/></svg>
              <span>Tải Xuống</span>
            </a>
            <button type="button" class="btn btn-sm btn-outline" onclick="handleOpenAcceptanceFile('${escapeAttr(file.file_path)}')" title="Mở trực tiếp trên máy tính">
              <svg class="icon" viewBox="0 0 24 24" style="width: 14px; height: 14px;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              <span>Mở File</span>
            </button>
          </div>
        </td>
      </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Lỗi nạp danh sách file nghiệm thu:", err);
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #dc2626; padding: 1.5rem;">Lỗi tải danh sách: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function handleOpenAcceptanceFolder() {
  try {
    const res = await fetch("/api/v1/system/open-path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: "Ho So Du An/Nghiem Thu" })
    });
    const json = await res.json();
    if (json.status === "success") {
      showToast("Đã mở thư mục Hồ Sơ Nghiệm Thu trên máy tính!", "success");
    } else {
      showToast(json.message || "Không thể mở thư mục.", "warning");
    }
  } catch (err) {
    showToast("Lỗi mở thư mục: " + err.message, "error");
  }
}

async function handleOpenAcceptanceFile(filePath) {
  if (!filePath) return;
  try {
    const res = await fetch("/api/v1/system/open-path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: filePath })
    });
    const json = await res.json();
    if (json.status === "success") {
      showToast("Đang mở tệp nghiệm thu trên máy tính...", "success");
    } else {
      showToast(json.message || "Không thể mở tệp.", "warning");
    }
  } catch (err) {
    showToast("Lỗi mở tệp: " + err.message, "error");
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

function escapeAttr(text) {
  if (!text) return "";
  return String(text).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}


// =========================================================================
// TAB SWITCHER (INSTALLATION ACCEPTANCE VS REPAIR ACCEPTANCE)
// =========================================================================

function switchAcceptanceTab(tab) {
  const btnInst = document.getElementById("tabBtnInstallation");
  const btnRepair = document.getElementById("tabBtnRepair");
  const contentInst = document.getElementById("tabContentInstallation");
  const contentRepair = document.getElementById("tabContentRepair");

  if (!btnInst || !btnRepair || !contentInst || !contentRepair) return;

  if (tab === "installation") {
    btnInst.style.background = "#1e40af";
    btnInst.style.color = "#ffffff";
    btnInst.style.borderColor = "#1d4ed8";
    btnInst.style.boxShadow = "0 2px 6px rgba(30, 64, 175, 0.25)";

    btnRepair.style.background = "#f8fafc";
    btnRepair.style.color = "#475569";
    btnRepair.style.borderColor = "#cbd5e1";
    btnRepair.style.boxShadow = "none";

    contentInst.style.display = "block";
    contentRepair.style.display = "none";
  } else {
    btnRepair.style.background = "#16a34a";
    btnRepair.style.color = "#ffffff";
    btnRepair.style.borderColor = "#15803d";
    btnRepair.style.boxShadow = "0 2px 6px rgba(22, 163, 74, 0.25)";

    btnInst.style.background = "#f8fafc";
    btnInst.style.color = "#475569";
    btnInst.style.borderColor = "#cbd5e1";
    btnInst.style.boxShadow = "none";

    contentInst.style.display = "none";
    contentRepair.style.display = "block";
  }
}


// =========================================================================
// INSTALLATION ACCEPTANCE MODULE (WORD .DOCX CHUẨN MẪU HONG MING)
// =========================================================================

window.currentInstallationData = null;
let instDebounceTimer = null;

async function initInstallationAcceptance() {
  await loadInstallationContractsDropdown();
  await handleLoadInstallationSampleData(false);
}

async function loadInstallationContractsDropdown() {
  const select = document.getElementById("instContractSelect");
  if (!select) return;

  try {
    const res = await fetch("/api/v1/contracts");
    const json = await res.json();
    if (res.ok && json.contracts) {
      const opts = ['<option value="">-- Tự nhập thông tin hợp đồng mới --</option>'];
      json.contracts.forEach(c => {
        const code = c.contract_code || "";
        const cust = c.customer_name_vi || "";
        const proj = c.project_name_vi || "";
        opts.push(`<option value="${escapeAttr(code)}">${escapeHtml(code)} — ${escapeHtml(cust)} (${escapeHtml(proj)})</option>`);
      });
      select.innerHTML = opts.join("");
    }
  } catch (err) {
    console.warn("Không thể tải danh sách hợp đồng:", err);
  }
}

async function onInstallationContractSelectChange(contractCode) {
  if (!contractCode) return;
  showLoading("Đang nạp dữ liệu hợp đồng " + contractCode + "...");
  try {
    const res = await fetch(`/api/v1/contracts/${encodeURIComponent(contractCode)}`);
    const json = await res.json();
    hideLoading();
    if (res.ok && json.data) {
      const c = json.data;
      if (c.contract_code) document.getElementById("instSoHopDong").value = c.contract_code;
      if (c.contract_date) document.getElementById("instNgayKyHopDong").value = c.contract_date;
      if (c.total_amount_formatted) document.getElementById("instGiaTriHopDong").value = c.total_amount_formatted + " VNĐ";
      if (c.project_name_vi) document.getElementById("instTenHeThong").value = c.project_name_vi;
      if (c.project_name_zh) document.getElementById("instTenHeThongTrung").value = c.project_name_zh;

      const benA = c.party_a || {};
      if (benA.name_vi) document.getElementById("instTenBenA").value = benA.name_vi;
      if (benA.name_zh) document.getElementById("instTenBenATrung").value = benA.name_zh;

      showToast(`Đã liên kết dữ liệu hợp đồng ${contractCode}!`, "success");
      handleInstallationFormChange();
    }
  } catch (err) {
    hideLoading();
    showToast("Lỗi nạp hợp đồng: " + err.message, "error");
  }
}

async function handleLoadInstallationSampleData(showNotification = true) {
  try {
    const res = await fetch("/api/v1/acceptance/installation/sample-data");
    const json = await res.json();
    if (res.ok && json.data) {
      populateInstallationForm(json.data);
      if (showNotification) {
        showToast("Đã nạp toàn bộ dữ liệu mẫu thực tế của CX Technology (HMV151020250001)!", "success");
      }
    }
  } catch (err) {
    console.error("Lỗi nạp dữ liệu mẫu:", err);
  }
}

function populateInstallationForm(data) {
  if (!data) return;
  window.currentInstallationData = JSON.parse(JSON.stringify(data));

  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val || "";
  };

  setVal("instSoHopDong", data.so_hop_dong);
  setVal("instSoBienBan", data.so_bien_ban);
  setVal("instNgayKyHopDong", data.ngay_ky_hop_dong);
  setVal("instNgayNghiemThu", data.ngay_nghiem_thu);
  setVal("instGiaTriHopDong", data.gia_tri_hop_dong);
  setVal("instTenHeThong", data.ten_he_thong);
  setVal("instTenHeThongTrung", data.ten_he_thong_trung);

  const benA = data.ben_a || {};
  setVal("instTenBenA", benA.ten_cong_ty);
  setVal("instTenBenATrung", benA.ten_tieng_trung);

  setVal("instCanCuPhuLuc", data.can_cu_phu_luc);
  setVal("instCanCuPhuLucTrung", data.can_cu_phu_luc_trung);
  setVal("instCanCuKyThuat", data.can_cu_ky_thuat);
  setVal("instCanCuKyThuatTrung", data.can_cu_ky_thuat_trung);

  // Initialize payment stages if empty
  if (!window.currentInstallationData.payment_stages || window.currentInstallationData.payment_stages.length === 0) {
    window.currentInstallationData.payment_stages = [
      {
        stage_id: "stage_1",
        stage_num: 1,
        stage: "GIAI ĐOẠN 1\n第一期",
        condition: "Sau khi ký kết hợp đồng\n簽約完成時",
        rate: "40%",
        amount: "93.600.000 VND",
        selected: false
      },
      {
        stage_id: "stage_2",
        stage_num: 2,
        stage: "GIAI ĐOẠN 2\n第二期",
        condition: "Sau khi triển khai sản phẩm đưa vào sử dụng\n產品安裝後",
        rate: "40%",
        amount: "93.600.000 VND",
        selected: true
      },
      {
        stage_id: "stage_3",
        stage_num: 3,
        stage: "GIAI ĐOẠN 3\n第三期",
        condition: "Khi nghiệm thu đạt tiêu chuẩn\n驗收合格時",
        rate: "20%",
        amount: "46.800.000 VND",
        selected: true
      }
    ];
  }

  renderInstallationItems();
  renderInstallationPaymentStages();
  recalculateInstallationPaymentSummary();
  handleRefreshInstallationPreview();
}

function renderInstallationItems() {
  const container = document.getElementById("instItemsContainer");
  const countBadge = document.getElementById("instItemCountBadge");
  if (!container || !window.currentInstallationData) return;

  const items = window.currentInstallationData.hang_muc || [];
  if (countBadge) countBadge.textContent = items.length;

  if (items.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 1.5rem; background: #f8fafc; border-radius: 6px; color: #94a3b8; font-size: 0.85rem;">
        Chưa có hạng mục nghiệm thu lắp đặt nào. Bấm "➕ Thêm Hạng Mục" ở trên.
      </div>
    `;
    return;
  }

  container.innerHTML = items.map((it, idx) => `
    <div style="background: #f8fafc; border: 1.5px solid #e2e8f0; border-radius: 8px; padding: 0.75rem 0.9rem; position: relative;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
        <span style="font-weight: 750; font-size: 0.82rem; color: #1e40af; display: flex; align-items: center; gap: 0.35rem;">
          <span style="background: #dbeafe; width: 20px; height: 20px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 0.75rem;">${idx + 1}</span>
          <span>Hạng mục #${idx + 1}</span>
        </span>
        <button type="button" class="btn btn-outline btn-sm" onclick="removeInstallationItem(${idx})" style="color: #dc2626; border-color: #fca5a5; padding: 0.15rem 0.45rem; font-size: 0.75rem;" title="Xóa hạng mục này">
          🗑️ Xóa
        </button>
      </div>

      <div style="margin-bottom: 0.45rem;">
        <label style="font-size: 0.74rem; font-weight: 600; color: #475569;">Tên Sản Phẩm / Module (Cột Tên sản phẩm):</label>
        <input type="text" class="form-control form-control-sm" value="${escapeAttr(it.ten_san_pham)}" oninput="handleItemFieldChange(${idx}, 'ten_san_pham', this.value)" style="font-weight: 600;">
      </div>

      <div style="margin-bottom: 0.45rem;">
        <label style="font-size: 0.74rem; font-weight: 600; color: #475569;">Nhóm Hạng Mục / Yêu Cầu Xác Nhận (項目類別):</label>
        <textarea class="form-control form-control-sm" rows="1" oninput="handleItemFieldChange(${idx}, 'hang_muc', this.value)">${escapeHtml(it.hang_muc || "")}</textarea>
      </div>

      <div>
        <label style="font-size: 0.74rem; font-weight: 600; color: #475569;">Nội Dung Sản Phẩm / Tính Năng Chi Tiết (產品內容):</label>
        <textarea class="form-control form-control-sm" rows="2" oninput="handleItemFieldChange(${idx}, 'noi_dung', this.value)">${escapeHtml(it.noi_dung || "")}</textarea>
      </div>
    </div>
  `).join("");
}

function addInstallationItem() {
  if (!window.currentInstallationData) {
    window.currentInstallationData = { hang_muc: [] };
  }
  const items = window.currentInstallationData.hang_muc || [];
  const nextStt = items.length + 1;
  items.push({
    stt: nextStt,
    ten_san_pham: `Hạng mục tính năng mới #${nextStt}`,
    hang_muc: "Xác nhận triển khai / 需求確認",
    noi_dung: "Đã hoàn thành lắp đặt, cấu hình và chạy thử đạt yêu cầu kỹ thuật.",
    xac_nhan_lap_dat: "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用",
    ket_qua_xac_nhan: "Đã nghiệm thu, xác nhận đạt yêu cầu và chính thức đưa vào sử dụng.\n驗收合格，確認正式投入使用。"
  });
  renderInstallationItems();
  handleInstallationFormChange();
}

function removeInstallationItem(idx) {
  if (!window.currentInstallationData || !window.currentInstallationData.hang_muc) return;
  window.currentInstallationData.hang_muc.splice(idx, 1);
  window.currentInstallationData.hang_muc.forEach((it, i) => it.stt = i + 1);
  renderInstallationItems();
  handleInstallationFormChange();
}

function handleItemFieldChange(idx, field, val) {
  if (!window.currentInstallationData || !window.currentInstallationData.hang_muc) return;
  if (window.currentInstallationData.hang_muc[idx]) {
    window.currentInstallationData.hang_muc[idx][field] = val;
    triggerDebouncedInstallationPreview();
  }
}

// -------------------------------------------------------------
// PAYMENT STAGES MANAGEMENT (BẢNG MỤC V & MỤC VI TỰ ĐỘNG CẬP NHẬT)
// -------------------------------------------------------------

function renderInstallationPaymentStages() {
  const container = document.getElementById("instStagesContainer");
  if (!container || !window.currentInstallationData) return;

  const stages = window.currentInstallationData.payment_stages || [];
  if (stages.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 1.25rem; background: #f8fafc; border-radius: 6px; color: #94a3b8; font-size: 0.85rem;">
        Chưa có giai đoạn thanh toán nào. Bấm "➕ Thêm Đợt" ở trên.
      </div>
    `;
    return;
  }

  container.innerHTML = stages.map((st, idx) => {
    const isSelected = !!st.selected;
    const borderStyle = isSelected ? "border: 1.5px solid #2563eb; background: #eff6ff;" : "border: 1.5px solid #e2e8f0; background: #ffffff;";
    const badgeColor = isSelected ? "background: #2563eb; color: #ffffff;" : "background: #f1f5f9; color: #64748b;";
    const stageTitle = st.stage || `GIAI ĐOẠN ${idx + 1}`;
    const condText = st.condition || "";
    const rateVal = st.rate || "0%";
    const amountVal = st.amount || "0 VND";

    return `
      <div style="${borderStyle} border-radius: 8px; padding: 0.75rem 0.9rem; transition: all 0.2s; position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; gap: 0.5rem;">
          <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; margin: 0; font-weight: 750; font-size: 0.88rem; color: ${isSelected ? '#1e40af' : '#334155'};">
            <input type="checkbox" style="width: 18px; height: 18px; accent-color: #2563eb; cursor: pointer;" ${isSelected ? 'checked' : ''} onchange="toggleInstallationStageSelection(${idx}, this.checked)">
            <span>${escapeHtml(stageTitle.replace('\n', ' / '))}</span>
          </label>
          <div style="display: flex; align-items: center; gap: 0.4rem;">
            <span style="${badgeColor} padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 0.76rem;">${escapeHtml(rateVal)}</span>
            <button type="button" class="btn btn-outline btn-sm" onclick="removeInstallationPaymentStage(${idx})" style="color: #dc2626; border-color: #fca5a5; padding: 0.1rem 0.4rem; font-size: 0.72rem;" title="Xóa đợt này">
              🗑️
            </button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 0.5rem; margin-bottom: 0.35rem;">
          <div>
            <label style="font-size: 0.72rem; font-weight: 600; color: #64748b;">Điều kiện thanh toán (Song ngữ Việt - Trung):</label>
            <input type="text" class="form-control form-control-sm" value="${escapeAttr(condText)}" oninput="handleStageFieldChange(${idx}, 'condition', this.value)" style="font-size: 0.82rem;">
          </div>
          <div>
            <label style="font-size: 0.72rem; font-weight: 600; color: #64748b;">Tỷ lệ (%):</label>
            <input type="text" class="form-control form-control-sm" value="${escapeAttr(rateVal)}" oninput="handleStageFieldChange(${idx}, 'rate', this.value)" style="font-weight: 700; text-align: center; font-size: 0.82rem;">
          </div>
          <div>
            <label style="font-size: 0.72rem; font-weight: 600; color: #64748b;">Số tiền (VND):</label>
            <input type="text" class="form-control form-control-sm" value="${escapeAttr(amountVal)}" oninput="handleStageFieldChange(${idx}, 'amount', this.value)" style="font-weight: 700; color: #047857; text-align: right; font-size: 0.82rem;">
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function toggleInstallationStageSelection(idx, isChecked) {
  if (!window.currentInstallationData?.payment_stages?.[idx]) return;
  window.currentInstallationData.payment_stages[idx].selected = isChecked;
  renderInstallationPaymentStages();
  recalculateInstallationPaymentSummary();
  handleInstallationFormChange();
}

function selectOnlyStage(stageNum) {
  if (!window.currentInstallationData?.payment_stages) return;
  window.currentInstallationData.payment_stages.forEach(st => {
    const sName = (st.stage || "").toLowerCase();
    const isMatch = st.stage_num === stageNum || String(st.stage_id) === String(stageNum) || sName.includes(`đoạn ${stageNum}`) || sName.includes(`đợt ${stageNum}`);
    st.selected = isMatch;
  });
  renderInstallationPaymentStages();
  recalculateInstallationPaymentSummary();
  handleInstallationFormChange();
  showToast(`Đã chọn riêng Giai đoạn ${stageNum}!`, "info");
}

function selectStagesCombined(stageNums) {
  if (!window.currentInstallationData?.payment_stages) return;
  window.currentInstallationData.payment_stages.forEach(st => {
    let isMatch = false;
    for (const num of stageNums) {
      const sName = (st.stage || "").toLowerCase();
      if (st.stage_num === num || String(st.stage_id) === String(num) || sName.includes(`đoạn ${num}`) || sName.includes(`đợt ${num}`)) {
        isMatch = true;
        break;
      }
    }
    st.selected = isMatch;
  });
  renderInstallationPaymentStages();
  recalculateInstallationPaymentSummary();
  handleInstallationFormChange();
  showToast(`Đã chọn kết hợp Giai đoạn ${stageNums.join(" & ")}!`, "info");
}

function addInstallationPaymentStage() {
  if (!window.currentInstallationData) {
    window.currentInstallationData = { payment_stages: [] };
  }
  const stages = window.currentInstallationData.payment_stages || [];
  const nextNum = stages.length + 1;
  const zhStages = ["第一期", "第二期", "第三期", "第四期", "第五期"];
  const zhLabel = zhStages[nextNum - 1] || `第${nextNum}期`;

  stages.push({
    stage_id: String(nextNum),
    stage_num: nextNum,
    stage: `GIAI ĐOẠN ${nextNum}\n${zhLabel}`,
    condition: "Nghiệm thu đạt tiêu chuẩn\n驗收合格時",
    rate: "20%",
    amount: "46.800.000 VND",
    selected: true
  });

  renderInstallationPaymentStages();
  recalculateInstallationPaymentSummary();
  handleInstallationFormChange();
}

function removeInstallationPaymentStage(idx) {
  if (!window.currentInstallationData?.payment_stages) return;
  window.currentInstallationData.payment_stages.splice(idx, 1);
  renderInstallationPaymentStages();
  recalculateInstallationPaymentSummary();
  handleInstallationFormChange();
}

function handleStageFieldChange(idx, field, val) {
  if (!window.currentInstallationData?.payment_stages?.[idx]) return;
  window.currentInstallationData.payment_stages[idx][field] = val;
  recalculateInstallationPaymentSummary();
  triggerDebouncedInstallationPreview();
}

function recalculateInstallationPaymentSummary() {
  if (!window.currentInstallationData?.payment_stages) return;

  const stages = window.currentInstallationData.payment_stages;
  const selectedStages = stages.filter(st => st.selected);

  const elStagesLabel = document.getElementById("instSummaryStagesLabel");
  const elTotalAmount = document.getElementById("instSummaryTotalAmount");
  const elWordsVN = document.getElementById("instSummaryWordsVN");
  const elWordsTW = document.getElementById("instSummaryWordsTW");

  if (selectedStages.length === 0) {
    if (elStagesLabel) elStagesLabel.textContent = "Chưa chọn đợt nào";
    if (elTotalAmount) elTotalAmount.textContent = "0 VND (0%)";
    if (elWordsVN) elWordsVN.textContent = "Chưa chọn đợt thanh toán.";
    if (elWordsTW) elWordsTW.textContent = "未選擇付款期別";
    return;
  }

  let totalRate = 0;
  let totalAmount = 0;
  const stageLabels = [];

  selectedStages.forEach(st => {
    totalRate += parsePositiveInteger(st.rate);
    totalAmount += parsePositiveInteger(st.amount);
    const m = (st.stage || "").match(/(?:GIAI\s*ĐOẠN|ĐỢT)\s*([0-9]+)/i);
    const num = m ? m[1] : (st.stage_num || "");
    stageLabels.push(num ? `Giai đoạn ${num}` : st.stage.split('\n')[0]);
  });

  const stagesSummaryText = stageLabels.join(" & ") + ` (${totalRate}%)`;
  const formattedAmount = formatCurrencyVnd(totalAmount);
  const wordsVN = numberToVietnameseWords(totalAmount);
  const wordsTW = numberToChineseWords(totalAmount);

  if (elStagesLabel) elStagesLabel.textContent = stagesSummaryText;
  if (elTotalAmount) elTotalAmount.textContent = `${formattedAmount} (${totalRate}%)`;
  if (elWordsVN) elWordsVN.textContent = wordsVN;
  if (elWordsTW) elWordsTW.textContent = wordsTW;

  // Sync with form fields
  const elGiaiDoanTT = document.getElementById("instGiaiDoanTT");
  if (elGiaiDoanTT) {
    if (selectedStages.length === 1) {
      const cond = selectedStages[0].condition ? selectedStages[0].condition.split('\n')[0] : "";
      elGiaiDoanTT.value = `${stageLabels[0]} (${cond ? cond + ' - ' : ''}${selectedStages[0].rate || totalRate + '%'})`;
    } else {
      elGiaiDoanTT.value = stagesSummaryText;
    }
  }

  const elSoTienTT = document.getElementById("instSoTienTT");
  if (elSoTienTT) elSoTienTT.value = formattedAmount;

  const elSoTienChuVN = document.getElementById("instSoTienChuVN");
  if (elSoTienChuVN) elSoTienChuVN.value = wordsVN;

  const elSoTienChuTW = document.getElementById("instSoTienChuTW");
  if (elSoTienChuTW) elSoTienChuTW.value = wordsTW;
}

// -------------------------------------------------------------
// NUMBER TO WORDS HELPERS (VIETNAMESE & TRADITIONAL CHINESE)
// -------------------------------------------------------------

function parsePositiveInteger(val) {
  if (typeof val === "number") return Math.floor(Math.abs(val));
  const digits = String(val || "").replace(/[^\d]/g, "");
  return digits ? parseInt(digits, 10) : 0;
}

function formatCurrencyVnd(amount) {
  const val = parsePositiveInteger(amount);
  return val.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " VND";
}

function numberToVietnameseWords(n) {
  const val = parsePositiveInteger(n);
  if (val === 0) return "Không đồng chẵn.";

  const digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"];
  const units = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"];

  function readThreeDigits(numStr, isFirst) {
    const num = parseInt(numStr, 10);
    const h = Math.floor(num / 100);
    const t = Math.floor((num % 100) / 10);
    const u = num % 10;
    const parts = [];

    if (h > 0 || !isFirst) {
      parts.push(digits[h] + " trăm");
    }

    if (t === 0 && u !== 0) {
      if (h > 0 || !isFirst) parts.push("lẻ");
      parts.push(digits[u]);
    } else if (t === 1) {
      parts.push("mười");
      if (u === 1) parts.push("một");
      else if (u === 5) parts.push("lăm");
      else if (u !== 0) parts.push(digits[u]);
    } else if (t > 1) {
      parts.push(digits[t] + " mươi");
      if (u === 1) parts.push("mốt");
      else if (u === 4) parts.push("tư");
      else if (u === 5) parts.push("lăm");
      else if (u !== 0) parts.push(digits[u]);
    }

    return parts.join(" ");
  }

  let s = val.toString();
  const groups = [];
  while (s.length > 3) {
    groups.unshift(s.slice(-3));
    s = s.slice(0, -3);
  }
  groups.unshift(s);

  const res = [];
  const totalGroups = groups.length;
  for (let i = 0; i < totalGroups; i++) {
    const g = groups[i];
    if (parseInt(g, 10) === 0) continue;
    const gWords = readThreeDigits(g, i === 0);
    const unitIdx = totalGroups - 1 - i;
    const unit = units[unitIdx] || "";
    if (gWords) res.push(gWords + (unit ? " " + unit : ""));
  }

  let result = res.join(" ").trim();
  if (!result) return "Không đồng chẵn.";
  result = result.charAt(0).toUpperCase() + result.slice(1) + " đồng chẵn.";
  return result;
}

function numberToChineseWords(n) {
  const val = parsePositiveInteger(n);
  if (val === 0) return "零越盾整";

  const digits = ["零", "壹", "貳", "參", "肆", "伍", "陸", "柒", "捌", "玖"];
  const units = ["", "拾", "佰", "仟"];
  const bigUnits = ["", "萬", "億", "兆"];

  let s = val.toString();
  const groups = [];
  while (s.length > 4) {
    groups.unshift(s.slice(-4));
    s = s.slice(0, -4);
  }
  groups.unshift(s);

  const resultParts = [];
  const totalGroups = groups.length;
  for (let i = 0; i < totalGroups; i++) {
    const gNum = parseInt(groups[i], 10);
    if (gNum === 0) continue;
    const gStr = i > 0 ? String(gNum).padStart(4, "0") : String(gNum);
    let groupWords = "";
    let zeroFlag = false;
    const l = gStr.length;
    for (let j = 0; j < l; j++) {
      const digitVal = parseInt(gStr[j], 10);
      const pos = l - 1 - j;
      if (digitVal === 0) {
        zeroFlag = true;
      } else {
        if (zeroFlag) {
          groupWords += digits[0];
          zeroFlag = false;
        }
        groupWords += digits[digitVal] + units[pos];
      }
    }
    const bigUnitIdx = totalGroups - 1 - i;
    groupWords += bigUnits[bigUnitIdx] || "";
    resultParts.push(groupWords);
  }

  return "越南盾" + resultParts.join("") + "整";
}

function collectInstallationFormData() {
  const getVal = (id) => (document.getElementById(id)?.value || "").trim();

  const data = window.currentInstallationData ? JSON.parse(JSON.stringify(window.currentInstallationData)) : {};

  data.so_hop_dong = getVal("instSoHopDong");
  data.so_bien_ban = getVal("instSoBienBan");
  data.ngay_ky_hop_dong = getVal("instNgayKyHopDong");
  data.ngay_nghiem_thu = getVal("instNgayNghiemThu");
  data.gia_tri_hop_dong = getVal("instGiaTriHopDong");
  data.ten_he_thong = getVal("instTenHeThong");
  data.ten_he_thong_trung = getVal("instTenHeThongTrung");

  data.ben_a = data.ben_a || {};
  data.ben_a.ten_cong_ty = getVal("instTenBenA");
  data.ben_a.ten_tieng_trung = getVal("instTenBenATrung");

  data.can_cu_phu_luc = getVal("instCanCuPhuLuc");
  data.can_cu_phu_luc_trung = getVal("instCanCuPhuLucTrung");
  data.can_cu_ky_thuat = getVal("instCanCuKyThuat");
  data.can_cu_ky_thuat_trung = getVal("instCanCuKyThuatTrung");

  data.giai_doan_thanh_toan = getVal("instGiaiDoanTT");
  data.so_tien_thanh_toan = getVal("instSoTienTT");
  data.so_tien_chu_vn = getVal("instSoTienChuVN");
  data.so_tien_chu_tw = getVal("instSoTienChuTW");

  // Include payment stages and selected indices
  data.payment_stages = window.currentInstallationData?.payment_stages || [];
  data.selected_stage_indices = [];
  data.payment_stages.forEach((st, idx) => {
    if (st.selected) data.selected_stage_indices.push(idx);
  });

  return data;
}

function handleInstallationFormChange() {
  triggerDebouncedInstallationPreview();
}

function triggerDebouncedInstallationPreview() {
  clearTimeout(instDebounceTimer);
  instDebounceTimer = setTimeout(() => {
    handleRefreshInstallationPreview();
  }, 350);
}

async function handleRefreshInstallationPreview() {
  const container = document.getElementById("instPreviewContainer");
  if (!container) return;

  const payload = collectInstallationFormData();
  window.currentInstallationData = payload;

  try {
    const res = await fetch("/api/v1/acceptance/installation/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (res.ok && json.preview_html) {
      container.innerHTML = json.preview_html;
    }
  } catch (err) {
    console.error("Lỗi cập nhật xem trước:", err);
  }
}

async function handleGenerateInstallationWord() {
  const btn = document.getElementById("btnGenerateInstallationWord");
  if (btn) btn.disabled = true;

  showLoading("Đang xuất Biên bản nghiệm thu lắp đặt Word (.docx) chuẩn mẫu 1:1...");
  const payload = collectInstallationFormData();

  try {
    const res = await fetch("/api/v1/acceptance/installation/generate-word", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    hideLoading();
    if (btn) btn.disabled = false;

    if (!res.ok || json.status !== "success") {
      throw new Error(json.message || "Không thể tạo tài liệu Word.");
    }

    // Tự động tải file về máy
    const downloadUrl = json.download_url;
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = json.file_name || "Bien_Ban_Nghiem_Thu_Lap_Dat.docx";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    showToast(`Đã tạo và tải file Word thành công: ${json.file_name}`, "success");
    // Làm mới danh sách tệp phía dưới
    loadAcceptanceFilesList();

  } catch (err) {
    hideLoading();
    if (btn) btn.disabled = false;
    showToast("Lỗi xuất file Word: " + err.message, "error");
  }
}

// -------------------------------------------------------------
// FILE UPLOAD & AI PARSING HANDLERS
// -------------------------------------------------------------

function triggerInstallationFileInput() {
  const input = document.getElementById("instAcceptanceFileInput");
  if (input) input.click();
}

async function handleInstallationFileUpload(input) {
  if (!input || !input.files || input.files.length === 0) return;
  const file = input.files[0];

  closeInstallationAIModal();
  showLoading(`Đang trích xuất dữ liệu từ file "${file.name}" (AI bóc tách các giai đoạn thanh toán)...`);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/v1/acceptance/installation/upload-and-parse", {
      method: "POST",
      body: formData
    });
    const json = await res.json();
    hideLoading();
    input.value = ""; // Reset file input

    if (!res.ok || json.status !== "success" || !json.data) {
      throw new Error(json.message || "Không thể trích xuất dữ liệu từ file.");
    }

    populateInstallationForm(json.data);
    showToast(json.message || `Đã trích xuất thành công dữ liệu từ file ${file.name}!`, "success");

  } catch (err) {
    hideLoading();
    if (input) input.value = "";
    showToast("Lỗi trích xuất file: " + err.message, "error");
  }
}

function openInstallationAIModal() {
  const modal = document.getElementById("installationAIModal");
  if (modal) modal.style.display = "flex";
}

function closeInstallationAIModal() {
  const modal = document.getElementById("installationAIModal");
  if (modal) modal.style.display = "none";
}

async function handleExecuteInstallationAI() {
  const rawText = document.getElementById("instAIRawText")?.value.trim();
  if (!rawText) {
    showToast("Vui lòng dán văn bản đầu vào để AI phân tích.", "warning");
    return;
  }

  closeInstallationAIModal();
  showLoading("Gemini AI đang phân tích và bóc tách dữ liệu nghiệm thu lắp đặt...");

  try {
    const res = await fetch("/api/v1/acceptance/installation/ai-parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText })
    });
    const json = await res.json();
    hideLoading();

    if (!res.ok || json.status !== "success" || !json.data) {
      throw new Error(json.message || "AI không thể phân tích văn bản.");
    }

    populateInstallationForm(json.data);
    showToast(json.message || "AI đã bóc tách dữ liệu thành công!", "success");

  } catch (err) {
    hideLoading();
    showToast("Lỗi phân tích AI: " + err.message, "error");
  }
}


