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

    if (summary) summary.textContent = `${result.source_file_name} đã được xử lý và giữ nguyên bố cục mẫu nghiệm thu.`;
    if (recordCount) recordCount.textContent = String(result.record_count || 0);
    if (assigned) assigned.textContent = String(result.assigned_count || 0);
    if (ignored) ignored.textContent = String(result.ignored_note_count || 0);
    if (model) model.textContent = result.gemini_model || "Gemini";
    if (download) {
      download.href = result.download_url;
      download.download = result.file_name || "Bien_Ban_Nghiem_Thu.xlsx";
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
    tbody.innerHTML = files.map((file, idx) => `
      <tr>
        <td style="text-align: center; font-weight: 600; color: var(--text-muted);">${idx + 1}</td>
        <td>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <svg style="width: 18px; height: 18px; color: #16a34a; flex-shrink: 0;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
            <div>
              <div style="font-weight: 600; color: #0f172a; word-break: break-all;">${escapeHtml(file.file_name)}</div>
              <div style="font-size: 0.72rem; color: #64748b; font-family: monospace;">${escapeHtml(file.file_path)}</div>
            </div>
          </div>
        </td>
        <td style="text-align: center; font-size: 0.82rem; color: #475569;">
          <span class="badge-pill" style="background: #f1f5f9; color: #334155;">${file.file_size_formatted}</span>
        </td>
        <td style="text-align: center; font-size: 0.82rem; color: #64748b;">
          ${file.modified_time}
        </td>
        <td style="text-align: center;">
          <div style="display: flex; gap: 0.4rem; justify-content: center; align-items: center;">
            <a href="${file.download_url}" download="${file.file_name}" class="btn btn-sm btn-success" title="Tải file Excel về máy">
              <svg class="icon" viewBox="0 0 24 24" style="width: 14px; height: 14px;"><path d="M12 3v12M7 10l5 5 5-5M5 21h14"/></svg>
              <span>Tải Xuống</span>
            </a>
            <button type="button" class="btn btn-sm btn-outline" onclick="handleOpenAcceptanceFile('${escapeAttr(file.file_path)}')" title="Mở trực tiếp trên máy tính bằng Excel">
              <svg class="icon" viewBox="0 0 24 24" style="width: 14px; height: 14px;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              <span>Mở File</span>
            </button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Lỗi nạp danh sách file nghiệm thu:", err);
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #dc2626; padding: 1.5rem;">Lỗi tải danh sách: ${escapeHtml(err.message)}</td></tr>`;
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

