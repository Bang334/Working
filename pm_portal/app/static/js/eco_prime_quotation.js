/**
 * ECO PRIME Quotation & AI Vision Schematic Analyzer
 * Handles image upload, Gemini Vision analysis, interactive BOM table, and Excel export.
 */

const EcoPrimeApp = (() => {
  let selectedFile = null;
  let fileBase64 = null;
  let itemsList = [];
  let detectedSubstations = [];

  // Khởi tạo
  function init() {
    setupDragAndDrop();
    // Tự động điền ngày hôm nay
    const today = new Date();
    const dd = String(today.getDate()).padStart(2, '0');
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const yyyy = today.getFullYear();
    const dateInput = document.getElementById('quoteDate');
    if (dateInput && !dateInput.value) {
      dateInput.value = `${dd}/${mm}/${yyyy}`;
    }
  }

  // Cấu hình Kéo & Thả ảnh
  function setupDragAndDrop() {
    const dropzone = document.getElementById('ecoDropzone');
    const card = document.getElementById('visionDropCard');
    if (!dropzone || !card) return;

    ['dragenter', 'dragover'].forEach(eventName => {
      card.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        card.classList.add('drag-over');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      card.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        card.classList.remove('drag-over');
      }, false);
    });

    card.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        processSelectedFile(files[0]);
      }
    }, false);
  }

  // Xử lý chọn file từ input
  function handleFileSelect(e) {
    const files = e.target.files;
    if (files && files.length > 0) {
      processSelectedFile(files[0]);
    }
  }

  // Đọc file và hiển thị bản xem trước
  function processSelectedFile(file) {
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      fileBase64 = e.target.result;
      const imgElem = document.getElementById('schematicPreviewImg');
      const previewContainer = document.getElementById('previewContainer');
      const dropzone = document.getElementById('ecoDropzone');

      if (imgElem && previewContainer && dropzone) {
        imgElem.src = fileBase64;
        previewContainer.style.display = 'block';
        dropzone.style.display = 'none';
      }
    };
    reader.readAsDataURL(file);
  }

  // Xóa ảnh
  function clearImage(e) {
    if (e) e.stopPropagation();
    selectedFile = null;
    fileBase64 = null;
    const fileInput = document.getElementById('schematicFileInput');
    if (fileInput) fileInput.value = '';

    const previewContainer = document.getElementById('previewContainer');
    const dropzone = document.getElementById('ecoDropzone');
    if (previewContainer) previewContainer.style.display = 'none';
    if (dropzone) dropzone.style.display = 'flex';
  }

  // Gọi AI Vision phân tích sơ đồ
  async function analyzeSchematic() {
    if (!fileBase64 && !selectedFile) {
      alert('Vui lòng kéo thả hoặc tải lên ảnh sơ đồ nguyên lý trước khi bấm phân tích!');
      return;
    }

    const btn = document.getElementById('btnAnalyzeSchematic');
    const btnText = document.getElementById('analyzeBtnText');
    const modelSelect = document.getElementById('aiModelSelect');
    const customerHint = document.getElementById('customerHintInput');

    const origHtml = btnText.innerHTML;
    btn.disabled = true;
    btnText.innerHTML = '<span class="eco-loading-spinner"></span> Đang phân tích sơ đồ bằng Gemini Vision...';

    try {
      let resp;
      if (selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        if (customerHint && customerHint.value.trim()) {
          formData.append('customer_name', customerHint.value.trim());
        }
        if (modelSelect && modelSelect.value) {
          formData.append('preferred_model', modelSelect.value);
        }
        resp = await fetch('/api/eco-prime/upload-and-analyze', {
          method: 'POST',
          body: formData
        });
      } else {
        const payload = {
          image_base64: fileBase64,
          mime_type: 'image/png',
          customer_name_hint: customerHint ? customerHint.value.trim() : '',
          preferred_model: modelSelect ? modelSelect.value : null
        };
        resp = await fetch('/api/eco-prime/analyze-schematic', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      const resData = await resp.json();
      if (!resData.success) {
        throw new Error(resData.error || 'Lỗi khi phân tích sơ đồ.');
      }

      applyAnalyzedData(resData);
    } catch (err) {
      console.error('Error analyzing schematic:', err);
      alert('Phân tích thất bại: ' + err.message);
    } finally {
      btn.disabled = false;
      btnText.innerHTML = origHtml;
    }
  }

  // Áp dụng dữ liệu phân tích được vào form
  function applyAnalyzedData(resData) {
    const data = resData.data;
    if (!data) return;

    if (data.customer_name) {
      document.getElementById('customerName').value = data.customer_name;
    }
    if (data.customer_dept) {
      document.getElementById('customerDept').value = data.customer_dept;
    }
    if (data.customer_address) {
      document.getElementById('customerAddress').value = data.customer_address;
    }
    if (data.quote_title) {
      document.getElementById('quoteTitle').value = data.quote_title;
    }
    if (data.project_solution) {
      document.getElementById('projectSolution').value = data.project_solution;
    }
    if (data.quote_date) {
      document.getElementById('quoteDate').value = data.quote_date;
    }
    if (data.exchange_rate) {
      document.getElementById('exchangeRate').value = data.exchange_rate;
    }
    if (data.notes_payment) {
      document.getElementById('paymentTermsInput').value = data.notes_payment;
    }

    // Hiển thị tags trạm biến áp nhận diện được
    detectedSubstations = resData.detected_substations || [];
    renderSubstationTags(detectedSubstations, resData.ai_summary);

    // Cập nhật danh sách thiết bị
    itemsList = data.items || [];
    renderItemsTable();
  }

  // Hiển thị tags các trạm biến áp
  function renderSubstationTags(stations, summary) {
    const box = document.getElementById('detectionResultsBox');
    const container = document.getElementById('substationTags');
    const summaryElem = document.getElementById('aiSummaryText');
    if (!box || !container) return;

    if (!stations || stations.length === 0) {
      box.style.display = 'none';
      return;
    }

    box.style.display = 'block';
    container.innerHTML = '';

    stations.forEach(st => {
      const is2000 = st.recommended_ct && st.recommended_ct.includes('2000');
      const tag = document.createElement('div');
      tag.className = `substation-tag ${is2000 ? 'ct-2000' : ''}`;
      tag.innerHTML = `
        <span>⚡ ${st.name || 'Trạm'}: ${st.capacity || ''} | ${st.ct || ''} | Biến dòng: <strong>${st.recommended_ct || ''}</strong></span>
      `;
      container.appendChild(tag);
    });

    if (summaryElem) {
      summaryElem.textContent = summary || 'Đã phân tích xong các trạm biến áp và đường truyền RS-485 trên bản vẽ.';
    }
  }

  // Render bảng sản phẩm
  function renderItemsTable() {
    const tbody = document.getElementById('ecoItemsBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!itemsList || itemsList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #94a3b8; padding: 2rem;">Chưa có hạng mục nào. Hãy tải ảnh sơ đồ hoặc bấm "Điền Mẫu POU HUI" để nạp dữ liệu.</td></tr>`;
      return;
    }

    itemsList.forEach((it, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="text-align: center; font-weight: 600;">${idx + 1}</td>
        <td>
          <textarea class="item-input" rows="2" onchange="EcoPrimeApp.updateItem(${idx}, 'name', this.value)">${escapeHtml(it.name || '')}</textarea>
        </td>
        <td>
          <textarea class="item-input" rows="2" onchange="EcoPrimeApp.updateItem(${idx}, 'category', this.value)">${escapeHtml(it.category || '')}</textarea>
        </td>
        <td>
          <textarea class="item-input" rows="4" style="font-size: 0.78rem;" onchange="EcoPrimeApp.updateItem(${idx}, 'desc', this.value)">${escapeHtml(it.desc || '')}</textarea>
        </td>
        <td style="text-align: center;">
          <input type="number" step="1" min="1" class="item-num" value="${it.qty || 1}" onchange="EcoPrimeApp.updateItem(${idx}, 'qty', parseFloat(this.value) || 1)">
        </td>
        <td style="text-align: center;">
          <input type="text" style="width: 50px; text-align: center;" class="item-num" value="${escapeHtml(it.unit || 'BỘ')}" onchange="EcoPrimeApp.updateItem(${idx}, 'unit', this.value)">
        </td>
        <td style="text-align: center;">
          <select style="font-size: 0.78rem; padding: 2px;" onchange="EcoPrimeApp.updateItem(${idx}, 'tax_rate', parseFloat(this.value))">
            <option value="0.0" ${it.tax_rate === 0.0 ? 'selected' : ''}>0%</option>
            <option value="0.08" ${it.tax_rate === 0.08 ? 'selected' : ''}>8%</option>
            <option value="0.20" ${it.tax_rate === 0.20 ? 'selected' : ''}>20%</option>
          </select>
        </td>
        <td style="text-align: center;">
          <span class="price-blank-badge">Sếp điền</span>
        </td>
        <td style="text-align: center;">
          <button type="button" class="btn btn-outline btn-sm" style="padding: 2px 6px; color: #ef4444;" onclick="EcoPrimeApp.deleteItemRow(${idx})" title="Xóa dòng này">
            🗑️
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Cập nhật giá trị trường trong item
  function updateItem(idx, field, val) {
    if (itemsList[idx]) {
      itemsList[idx][field] = val;
    }
  }

  // Thêm dòng thiết bị mới
  function addItemRow() {
    const newItem = {
      stt: itemsList.length + 1,
      name: 'Tên thiết bị mới\n設備名稱',
      category: 'Chủng loại\n類別',
      desc: 'Mô tả quy cách kỹ thuật chi tiết...\n詳細規格描述...',
      qty: 1,
      unit: 'BỘ',
      tax_rate: 0.08,
      unit_price_usd: null
    };
    itemsList.push(newItem);
    renderItemsTable();
  }

  // Xóa dòng thiết bị
  function deleteItemRow(idx) {
    if (confirm(`Bạn có chắc muốn xóa hạng mục số ${idx + 1}?`)) {
      itemsList.splice(idx, 1);
      itemsList.forEach((it, i) => it.stt = i + 1);
      renderItemsTable();
    }
  }

  // Nạp nhanh mẫu Pou Hui
  async function loadSampleData() {
    try {
      const resp = await fetch('/api/eco-prime/sample-data');
      const resData = await resp.json();
      if (resData.success && resData.data) {
        applyAnalyzedData(resData);
        alert('Đã nạp thành công bộ dữ liệu mẫu dự án POU HUI 4 trạm biến áp!');
      }
    } catch (e) {
      console.error(e);
      alert('Không thể tải dữ liệu mẫu: ' + e.message);
    }
  }

  // Làm mới form
  function resetForm() {
    if (confirm('Làm mới form để nhập sơ đồ mới? Mọi nội dung chưa lưu sẽ bị xóa.')) {
      clearImage();
      document.getElementById('customerName').value = '';
      document.getElementById('customerContact').value = '';
      document.getElementById('customerPhone').value = '';
      document.getElementById('customerAddress').value = '';
      document.getElementById('customerHintInput').value = '';
      itemsList = [];
      detectedSubstations = [];
      renderItemsTable();
      const box = document.getElementById('detectionResultsBox');
      if (box) box.style.display = 'none';
    }
  }

  // Xuất file Excel
  async function exportExcel() {
    if (!itemsList || itemsList.length === 0) {
      alert('Bảng thiết bị đang trống! Vui lòng tải ảnh sơ đồ hoặc bấm "Điền Mẫu POU HUI" trước khi xuất Excel.');
      return;
    }

    const btn = document.getElementById('btnExportExcel');
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="eco-loading-spinner"></span> Đang tạo file Excel chuẩn 1:1...';

    try {
      const payload = {
        customer_name: document.getElementById('customerName').value.trim(),
        customer_dept: document.getElementById('customerDept').value.trim(),
        customer_contact: document.getElementById('customerContact').value.trim(),
        customer_phone: document.getElementById('customerPhone').value.trim(),
        customer_address: document.getElementById('customerAddress').value.trim(),
        quote_title: document.getElementById('quoteTitle').value.trim(),
        project_solution: document.getElementById('projectSolution').value.trim(),
        quote_date: document.getElementById('quoteDate').value.trim(),
        exchange_rate: parseFloat(document.getElementById('exchangeRate').value) || 26130.0,
        notes_payment: document.getElementById('paymentTermsInput').value.trim(),
        items: itemsList
      };

      const resp = await fetch('/api/eco-prime/export-excel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText || 'Lỗi khi xuất file Excel');
      }

      // Đọc filename từ Content-Disposition header nếu có
      let filename = 'ECO_PRIME_Bao_Gia.xlsx';
      const disposition = resp.headers.get('Content-Disposition');
      if (disposition && disposition.indexOf('filename*=UTF-8\'\'') !== -1) {
        filename = decodeURIComponent(disposition.split("filename*=UTF-8''")[1].split(';')[0]);
      } else if (disposition && disposition.indexOf('filename=') !== -1) {
        filename = disposition.split('filename=')[1].split(';')[0].replace(/"/g, '');
      }

      const blob = await resp.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

    } catch (err) {
      console.error('Export error:', err);
      alert('Xuất Excel thất bại: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  return {
    init,
    handleFileSelect,
    clearImage,
    analyzeSchematic,
    renderItemsTable,
    updateItem,
    addItemRow,
    deleteItemRow,
    loadSampleData,
    resetForm,
    exportExcel
  };
})();

document.addEventListener('DOMContentLoaded', () => {
  EcoPrimeApp.init();
});
