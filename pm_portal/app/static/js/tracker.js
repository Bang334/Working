/**
 * Hong Ming Global PM Portal - Live Dashboard & Project Tracker
 * Completely dynamically driven by SQLite database & real operational files.
 */

(function () {
  let cachedContracts = [];
  let activeFilter = "all";

  // Document Ready
  document.addEventListener("DOMContentLoaded", () => {
    initDashboard();
  });

  async function initDashboard() {
    initFilterEvents();
    initSearchEvents();
    await loadDashboardData();
  }

  // Load Overview Data from Backend
  window.loadDashboardData = async function () {
    try {
      const res = await fetch("/api/v1/dashboard/overview");
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();

      if (data.status === "success") {
        cachedContracts = data.contracts || [];
        renderSummary(data.summary || {});
        renderPortfolioBars(data.portfolio_bars || []);
        renderDonutChart(data.donut || {}, data.summary || {});
        renderActionItems(data.action_items || []);
        renderProjectsTable(cachedContracts);
        applyFilters();
      }
    } catch (err) {
      console.error("Lỗi nạp dữ liệu dashboard:", err);
      if (typeof showToast === "function") {
        showToast("Không thể nạp dữ liệu tổng quan: " + err.message, "error");
      }
    }
  };

  // Render KPI Summary Cards
  function renderSummary(summary) {
    // Period & Date
    const periodEl = document.getElementById("dashboardPeriod");
    if (periodEl) {
      periodEl.textContent = `Kỳ báo cáo · ${summary.report_period || "Tháng 10/2026"}`;
    }

    // Card 1: Total Projects
    const totalEl = document.getElementById("kpiTotalProjects");
    const activeBadgeEl = document.getElementById("kpiActiveBadge");
    const projectsDetailEl = document.getElementById("kpiProjectsDetail");
    const tot = summary.total_projects || 0;
    if (totalEl) totalEl.textContent = tot < 10 ? `0${tot}` : String(tot);
    if (activeBadgeEl) {
      const activeCount = (summary.running_count || 0) + (summary.waiting_count || 0);
      activeBadgeEl.textContent = `${activeCount} đang hoạt động`;
    }
    if (projectsDetailEl) {
      projectsDetailEl.textContent = `${summary.running_count || 0} đang triển khai · ${summary.waiting_count || 0} chờ thu · ${summary.done_count || 0} hoàn tất`;
    }

    // Card 2: Portfolio Value
    const portfolioEl = document.getElementById("kpiPortfolioValue");
    const portfolioDetailEl = document.getElementById("kpiPortfolioDetail");
    if (portfolioEl) {
      portfolioEl.innerHTML = `${summary.total_contract_value_millions || "0,0"} <small>triệu</small>`;
      portfolioEl.title = summary.total_contract_value_formatted || "";
    }
    if (portfolioDetailEl) {
      portfolioDetailEl.textContent = `Đã thu: ${summary.total_paid_value_formatted || "0 ₫"}`;
    }

    // Card 3: Urgent Actions
    const urgentEl = document.getElementById("kpiUrgentActions");
    const urgentBadgeEl = document.getElementById("kpiUrgentBadge");
    const urgentDetailEl = document.getElementById("kpiUrgentDetail");
    const uCount = summary.urgent_count || 0;
    if (urgentEl) urgentEl.textContent = uCount < 10 ? `0${uCount}` : String(uCount);
    if (urgentBadgeEl) {
      urgentBadgeEl.textContent = uCount > 0 ? `${uCount} ưu tiên` : "Ổn định";
      urgentBadgeEl.className = uCount > 0 ? "kpi-change warning" : "kpi-change positive";
    }
    if (urgentDetailEl) {
      urgentDetailEl.textContent = uCount > 0 ? "Mốc đến hạn hoặc quá hạn" : "Không có công nợ quá hạn";
    }

    // Card 4: Collection Rate
    const rateEl = document.getElementById("kpiCollectionRate");
    const rateBadgeEl = document.getElementById("kpiCollectionBadge");
    const rateProgressEl = document.getElementById("kpiCollectionProgressBar");
    const rateDetailEl = document.getElementById("kpiCollectionDetail");
    const rate = summary.collection_rate || 0;
    if (rateEl) rateEl.textContent = `${rate}%`;
    if (rateBadgeEl) {
      rateBadgeEl.textContent = `Còn ${summary.total_remaining_value_formatted || "0 ₫"}`;
    }
    if (rateProgressEl) {
      rateProgressEl.style.width = `${Math.min(100, Math.max(0, rate))}%`;
    }
    if (rateDetailEl) {
      rateDetailEl.textContent = `Đã thu: ${summary.total_paid_value_formatted || "0 ₫"} / ${summary.total_contract_value_formatted || "0 ₫"}`;
    }
  }

  // Render Bar Chart (Portfolio Value by Project)
  function renderPortfolioBars(bars) {
    const container = document.getElementById("barChartRows");
    if (!container) return;

    if (!bars || bars.length === 0) {
      container.innerHTML = `
        <div style="padding: 1.5rem; text-align: center; color: #94a3b8; font-size: 0.75rem;">
          Chưa có hợp đồng nào được lưu trong cơ sở dữ liệu.
        </div>
      `;
      return;
    }

    let html = "";
    bars.forEach((b) => {
      html += `
        <div class="bar-row" title="${escapeHtml(b.customer_full)} - ${b.formatted_amount} triệu VND">
          <div class="bar-label">
            <strong>${escapeHtml(b.customer_short)}</strong>
            <span>${escapeHtml(b.contract_code)}</span>
          </div>
          <div class="bar-track">
            <span class="bar-fill ${b.color_class}" style="--bar-size: ${Math.max(4, b.bar_percentage)}%"></span>
          </div>
          <strong class="bar-value">${b.formatted_amount}</strong>
        </div>
      `;
    });
    container.innerHTML = html;
  }

  // Render Donut Chart & Legend
  function renderDonutChart(donut, summary) {
    const chartEl = document.getElementById("statusDonutChart");
    const centerPctEl = document.getElementById("donutCenterPct");
    const totalEl = document.getElementById("statusTotalProjects");

    if (chartEl && donut.gradient) {
      chartEl.style.background = donut.gradient;
    }
    if (centerPctEl) {
      centerPctEl.textContent = `${donut.active_rate || 0}%`;
    }
    if (totalEl) {
      const tot = summary.total_projects || 0;
      totalEl.textContent = tot < 10 ? `0${tot} dự án` : `${tot} dự án`;
    }

    // Legend
    const rSub = document.getElementById("legendRunningSub");
    const rCount = document.getElementById("legendRunningCount");
    const wSub = document.getElementById("legendWaitingSub");
    const wCount = document.getElementById("legendWaitingCount");
    const dSub = document.getElementById("legendDoneSub");
    const dCount = document.getElementById("legendDoneCount");

    if (rSub) rSub.textContent = `${donut.count_running || 0} dự án · ${donut.pct_running || 0}%`;
    if (rCount) rCount.textContent = formatTwoDigits(donut.count_running);

    if (wSub) wSub.textContent = `${donut.count_waiting || 0} dự án · ${donut.pct_waiting || 0}%`;
    if (wCount) wCount.textContent = formatTwoDigits(donut.count_waiting);

    if (dSub) dSub.textContent = `${donut.count_done || 0} dự án · ${donut.pct_done || 0}%`;
    if (dCount) dCount.textContent = formatTwoDigits(donut.count_done);
  }

  // Render Priority Action Items
  function renderActionItems(actions) {
    const listEl = document.getElementById("dashboardActionList");
    const badgeEl = document.getElementById("actionCountBadge");
    if (!listEl) return;

    if (badgeEl) {
      badgeEl.textContent = `${actions.length} đầu việc`;
    }

    if (!actions || actions.length === 0) {
      listEl.innerHTML = `
        <li style="grid-column: 1 / -1; display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 1.25rem; color: #047857; background: #ecfdf5; border-color: #a7f3d0;">
          <svg class="icon" viewBox="0 0 24 24" style="width: 18px; height: 18px;" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <strong style="color: #065f46;">Tiến độ và công nợ tất cả các dự án đang trong tầm kiểm soát an toàn!</strong>
        </li>
      `;
      return;
    }

    let html = "";
    actions.forEach((a) => {
      const clickAction = a.action_url ? `style="cursor: pointer;" onclick="window.location.href='${a.action_url}'"` : "";
      html += `
        <li ${clickAction} title="Nhấn để xử lý đầu việc này">
          <span class="action-marker ${a.severity}" aria-hidden="true"></span>
          <div>
            <strong>${escapeHtml(a.title)}</strong>
            <span>${escapeHtml(a.detail)}</span>
          </div>
          <span class="action-tag ${a.severity}">${escapeHtml(a.badge_text)}</span>
        </li>
      `;
    });
    listEl.innerHTML = html;
  }

  // Render Projects Matrix Table
  function renderProjectsTable(contracts) {
    const tbody = document.getElementById("trackerTableBody");
    if (!tbody) return;

    // Update filter counts
    let cAll = contracts.length;
    let cRunning = 0;
    let cPayment = 0;
    let cDone = 0;

    contracts.forEach((c) => {
      if (c.filter_cat === "running") cRunning++;
      else if (c.filter_cat === "payment") cPayment++;
      else if (c.filter_cat === "done") cDone++;
    });

    setCount("filterAllCount", cAll);
    setCount("filterRunningCount", cRunning);
    setCount("filterPaymentCount", cPayment);
    setCount("filterDoneCount", cDone);

    if (contracts.length === 0) {
      tbody.innerHTML = "";
      showEmptyState(true, "Chưa có dự án nào trong hệ thống", "Hãy nhấn 'Thêm hợp đồng' hoặc 'Đồng bộ Excel' để bắt đầu quản lý.");
      return;
    }

    let html = "";
    contracts.forEach((c) => {
      const docsCount = (c.documents || []).length;
      const ms = c.current_milestone_info || { name: "--", text: "--", dot_color: "blue" };
      const pill = c.status_pill || { text: c.status || "--", class: "running" };

      // Searchable keywords
      const searchTerms = [
        c.contract_code,
        c.customer_name_vi,
        c.customer_name_zh,
        c.project_name_vi,
        c.project_name_zh,
        c.lead_engineer,
        c.status,
      ].filter(Boolean).join(" ");

      html += `
        <tr data-status="${c.filter_cat || "running"}" data-search="${escapeHtml(searchTerms)}">
          <td><span class="project-code">${escapeHtml(c.contract_code)}</span></td>
          <td>
            <div class="project-main">
              <strong>${escapeHtml(c.customer_name_vi)}</strong>
              <span>${escapeHtml(c.project_name_vi)}</span>
            </div>
            <small>${escapeHtml(c.customer_name_zh || "")} · Ký ngày: ${escapeHtml(c.signed_date || "--")}</small>
          </td>
          <td class="align-right">
            <strong>${c.formatted_total}</strong>
            <small style="color: #64748b; font-size: 0.62rem; display: block;">Đã thu: ${c.formatted_paid}</small>
          </td>
          <td>
            <div class="table-progress ${c.percent_paid >= 100 ? "complete" : ""}">
              <span><i style="width: ${c.percent_paid}%"></i></span>
              <b>${c.percent_paid}%</b>
            </div>
          </td>
          <td>
            <span class="milestone">
              <i class="milestone-dot ${ms.dot_color}"></i>
              ${escapeHtml(ms.name)} · ${escapeHtml(ms.text)}
            </span>
          </td>
          <td><span class="status-pill ${pill.class}">${escapeHtml(pill.text)}</span></td>
          <td>
            <div class="row-actions">
              <button type="button" class="row-action-btn primary" onclick="openDossierModal('${c.contract_code}')" title="Xem danh sách hồ sơ và tài liệu">
                Hồ sơ (${docsCount})
              </button>
              <a class="row-action-btn" href="/reminders?contract_code=${encodeURIComponent(c.contract_code)}" title="Soạn đề nghị thanh toán & nhắc nợ">
                ĐNTT
              </a>
            </div>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
    showEmptyState(false);
  }

  // Filter & Search Logic
  function initFilterEvents() {
    const filterButtons = document.querySelectorAll(".filter-btn");
    filterButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        activeFilter = btn.dataset.filter || "all";
        filterButtons.forEach((b) => {
          const isActive = b === btn;
          b.classList.toggle("active", isActive);
          b.setAttribute("aria-pressed", String(isActive));
        });
        applyFilters();
      });
    });
  }

  function initSearchEvents() {
    const searchInput = document.getElementById("projectSearch");
    if (searchInput) {
      searchInput.addEventListener("input", applyFilters);
    }
  }

  function normalize(value) {
    return (value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function applyFilters() {
    const table = document.getElementById("trackerTable");
    if (!table) return;

    const rows = Array.from(table.querySelectorAll("tbody tr"));
    const searchInput = document.getElementById("projectSearch");
    const countLabel = document.getElementById("projectCount");
    const query = normalize(searchInput ? searchInput.value : "");

    let visibleCount = 0;
    rows.forEach((row) => {
      const matchesStatus = activeFilter === "all" || row.dataset.status === activeFilter;
      const searchableText = normalize(`${row.dataset.search || ""} ${row.textContent}`);
      const matchesSearch = !query || searchableText.includes(query);
      const isVisible = matchesStatus && matchesSearch;
      row.hidden = !isVisible;
      if (isVisible) visibleCount++;
    });

    if (countLabel) {
      countLabel.textContent = `Hiển thị ${visibleCount} trên ${rows.length} dự án`;
    }

    const emptyState = document.getElementById("projectEmptyState");
    if (emptyState) {
      emptyState.hidden = visibleCount > 0;
      if (visibleCount === 0 && rows.length > 0) {
        document.getElementById("emptyStateTitle").textContent = "Không tìm thấy dự án phù hợp";
        document.getElementById("emptyStateDesc").textContent = "Thử thay đổi từ khóa tìm kiếm hoặc chọn bộ lọc 'Tất cả'.";
      }
    }
    table.hidden = visibleCount === 0 && rows.length === 0;
  }

  function showEmptyState(show, title, desc) {
    const emptyState = document.getElementById("projectEmptyState");
    const table = document.getElementById("trackerTable");
    if (emptyState) {
      emptyState.hidden = !show;
      if (title) document.getElementById("emptyStateTitle").textContent = title;
      if (desc) document.getElementById("emptyStateDesc").textContent = desc;
    }
    if (table) {
      table.hidden = show;
    }
  }

  function setCount(elementId, count) {
    const el = document.getElementById(elementId);
    if (el) el.textContent = String(count);
  }

  function formatTwoDigits(n) {
    const val = Number(n) || 0;
    return val < 10 ? `0${val}` : String(val);
  }

  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // ==========================================
  // ACTION BUTTONS: EXCEL EXPORT, SYNC & REFRESH
  // ==========================================

  window.refreshDashboard = async function () {
    if (typeof showToast === "function") {
      showToast("Đang làm mới dữ liệu dự án từ cơ sở dữ liệu...", "info");
    }
    await loadDashboardData();
    if (typeof showToast === "function") {
      showToast("Đã cập nhật số liệu mới nhất!", "success");
    }
  };

  window.exportDashboardExcel = function () {
    if (typeof showToast === "function") {
      showToast("Đang kết xuất báo cáo Excel tổng quan...", "info");
    }
    window.location.href = "/api/v1/dashboard/export-excel";
  };

  window.syncTrackerExcel = async function () {
    if (!confirm("Bạn có muốn đồng bộ các dự án từ file Excel theo dõi gốc (DANH_SACH_THEO_DOI_DU_AN_HONG_MING.xlsx) vào cơ sở dữ liệu?")) {
      return;
    }

    try {
      if (typeof showToast === "function") {
        showToast("Đang đọc file Excel theo dõi và đồng bộ...", "info");
      }
      const res = await fetch("/api/v1/dashboard/sync-excel", { method: "POST" });
      const data = await res.json();
      if (data.status === "success") {
        if (typeof showToast === "function") {
          showToast(data.message, "success");
        }
        await loadDashboardData();
      } else {
        if (typeof showToast === "function") {
          showToast(data.message || "Không thể đồng bộ.", "error");
        }
      }
    } catch (err) {
      if (typeof showToast === "function") {
        showToast("Lỗi đồng bộ: " + err.message, "error");
      }
    }
  };

  // ==========================================
  // DOSSIER MODAL (XEM HỒ SƠ & TÀI LIỆU)
  // ==========================================

  window.openDossierModal = function (contractCode) {
    const contract = cachedContracts.find((c) => c.contract_code === contractCode);
    if (!contract) return;

    const modal = document.getElementById("dossierModal");
    if (!modal) return;

    // Header info
    document.getElementById("modalContractCode").textContent = contract.contract_code;
    document.getElementById("modalCustomerName").textContent = `${contract.customer_name_vi} ${contract.customer_name_zh ? `(${contract.customer_name_zh})` : ""}`;

    // Summary box
    const summaryBox = document.getElementById("modalSummaryBox");
    summaryBox.innerHTML = `
      <div>
        <span>Tổng giá trị HĐ</span>
        <strong>${contract.formatted_total}</strong>
      </div>
      <div>
        <span>Đã thanh toán</span>
        <strong style="color: #059669;">${contract.formatted_paid} (${contract.percent_paid}%)</strong>
      </div>
      <div>
        <span>Còn lại cần thu</span>
        <strong style="color: #d97706;">${contract.formatted_remaining}</strong>
      </div>
      <div>
        <span>Kỹ thuật phụ trách</span>
        <strong>${escapeHtml(contract.lead_engineer || "Jenson Chang")}</strong>
      </div>
      <div>
        <span>Ngày ký hợp đồng</span>
        <strong>${escapeHtml(contract.signed_date || "--")}</strong>
      </div>
      <div>
        <span>Trạng thái hiện tại</span>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <strong style="color: #2563eb;">${escapeHtml(contract.status || "--")}</strong>
          <button type="button" class="row-action-btn" onclick="changeContractStatusFromTracker('${contract.contract_code}', '${escapeHtml(contract.status || '')}')" style="padding: 1px 6px; font-size: 0.64rem;">
            ✏️ Đổi
          </button>
        </div>
      </div>
    `;

    // Documents list
    const docs = contract.documents || [];
    document.getElementById("modalDocsCount").textContent = String(docs.length);
    const docsList = document.getElementById("modalDocsList");

    if (docs.length === 0) {
      docsList.innerHTML = `
        <div style="padding: 0.85rem; text-align: center; color: #94a3b8; font-size: 0.75rem; background: #f8fafc; border: 1px dashed #e2e8f0; border-radius: 8px;">
          Chưa có tài liệu nào được liên kết với mã hợp đồng này.
        </div>
      `;
    } else {
      let docsHtml = "";
      docs.forEach((d) => {
        const ext = (d.file_format || "docx").toLowerCase();
        docsHtml += `
          <div class="dossier-doc-item">
            <div class="dossier-doc-left">
              <span class="dossier-doc-ext ${ext}">${ext}</span>
              <div class="dossier-doc-info">
                <strong>${escapeHtml(d.doc_name || d.file_name)}</strong>
                <small>${escapeHtml(d.description || d.file_name)}</small>
              </div>
            </div>
            <div class="dossier-doc-actions">
              <button type="button" class="row-action-btn" onclick="openSystemPath('${escapeHtml(d.file_path || "")}')" title="Mở trực tiếp trên máy tính Windows">
                Mở tệp
              </button>
              <a href="/api/v1/dossier/documents/${d.id}/download" class="row-action-btn primary" download title="Tải tệp về máy">
                Tải về
              </a>
            </div>
          </div>
        `;
      });
      docsList.innerHTML = docsHtml;
    }

    // Milestones list
    const msList = document.getElementById("modalMilestonesList");
    const milestones = contract.milestones || [];
    if (milestones.length === 0) {
      msList.innerHTML = `<div style="padding: 0.6rem; color: #94a3b8; font-size: 0.72rem;">Chưa có mốc thanh toán nào.</div>`;
    } else {
      let msHtml = "";
      milestones.forEach((m) => {
        const amt = Number(m.amount) || 0;
        const days = m.days_left;
        const isPaid = m.status === "PAID";
        let badgeColor = "#2563eb";
        let badgeBg = "#eff6ff";
        if (isPaid) {
          badgeColor = "#059669";
          badgeBg = "#ecfdf5";
        } else if (m.status === "OVERDUE" || (days !== null && days < 0)) {
          badgeColor = "#dc2626";
          badgeBg = "#fef2f2";
        } else if (m.status === "URGENT" || (days !== null && days <= 10)) {
          badgeColor = "#d97706";
          badgeBg = "#fffbeb";
        }

        msHtml += `
          <div class="dossier-ms-item">
            <div>
              <strong>${escapeHtml(m.milestone_name)} (${m.percentage || 0}%)</strong>
              <div style="color: #64748b; font-size: 0.66rem; margin-top: 2px;">
                ${escapeHtml(m.trigger_condition || "")} · Hạn: ${escapeHtml(m.due_date || "Chưa tính")}
              </div>
            </div>
            <div style="text-align: right;">
              <strong style="color: #0f172a;">${amt.toLocaleString("vi-VN")} ₫</strong>
              <div style="margin-top: 2px; display: flex; align-items: center; justify-content: flex-end; gap: 0.35rem;">
                <span style="display: inline-block; padding: 2px 6px; border-radius: 999px; font-size: 0.6rem; font-weight: 750; color: ${badgeColor}; background: ${badgeBg};">
                  ${escapeHtml(m.status_label || (isPaid ? "Đã thu đủ" : "Chờ xử lý"))}
                </span>
                ${!isPaid ? `
                  <button type="button" class="row-action-btn primary" onclick="markMilestonePaidFromTracker(${m.id}, '${contract.contract_code}', '${escapeHtml(m.milestone_name)}', ${amt})" style="padding: 1px 6px; font-size: 0.64rem; font-weight: 750; background: #ecfdf5; color: #047857; border-color: #a7f3d0;" title="Mở quy trình để đối chiếu tiền thực nhận và chứng từ">
                    💰 Đã thu
                  </button>
                ` : `
                  <button type="button" class="row-action-btn" onclick="unmarkMilestonePaidFromTracker(${m.id}, '${contract.contract_code}')" style="padding: 1px 5px; font-size: 0.62rem; color: #b45309; border-color: #fde68a;" title="Hủy trạng thái đã thu để tính lại nợ">
                    ↩️ Hoàn tác
                  </button>
                `}
              </div>
            </div>
          </div>
        `;
      });
      msList.innerHTML = msHtml;
    }

    // Action button inside modal
    const btnDntt = document.getElementById("modalBtnDntt");
    if (btnDntt) {
      btnDntt.href = `/reminders?contract_code=${encodeURIComponent(contract.contract_code)}`;
    }

    modal.style.display = "flex";
  };

  window.closeDossierModal = function (e) {
    if (e && e.target && e.target.id !== "dossierModal" && !e.target.classList.contains("toast-close") && e.target.tagName !== "BUTTON") {
      return;
    }
    const modal = document.getElementById("dossierModal");
    if (modal) modal.style.display = "none";
  };

  window.openSystemPath = async function (pathStr) {
    if (!pathStr) return;
    try {
      const res = await fetch("/api/v1/system/open-path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: pathStr }),
      });
      const data = await res.json();
      if (typeof showToast === "function") {
        showToast(data.message || "Đã yêu cầu mở tệp.", data.status === "error" ? "error" : "success");
      }
    } catch (err) {
      if (typeof showToast === "function") {
        showToast("Lỗi mở tệp: " + err.message, "error");
      }
    }
  };

  window.markMilestonePaidFromTracker = function (milestoneId) {
    window.location.href = `/workflows?milestone=${encodeURIComponent(milestoneId)}`;
  };

  window.unmarkMilestonePaidFromTracker = async function (milestoneId, contractCode) {
    if (!confirm("Bạn có chắc chắn muốn hủy trạng thái đã thu tiền của đợt này để tính lại nợ?")) return;

    try {
      if (typeof showToast === "function") showToast("Đang hoàn tác thanh toán...", "info");
      const res = await fetch(`/api/v1/dossier/milestones/${milestoneId}/unmark-paid`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.status === "success") {
        if (typeof showToast === "function") showToast(data.message, "success");
        await loadDashboardData();
        openDossierModal(contractCode);
      } else {
        if (typeof showToast === "function") showToast(data.message || "Lỗi cập nhật", "error");
      }
    } catch (err) {
      if (typeof showToast === "function") showToast("Lỗi: " + err.message, "error");
    }
  };

  window.changeContractStatusFromTracker = async function (contractCode, currentStatus) {
    const newStatus = prompt(`Cập nhật trạng thái cho hợp đồng ${contractCode}:`, currentStatus);
    if (!newStatus || newStatus === currentStatus) return;

    try {
      const res = await fetch(`/api/v1/dossier/contracts/${contractCode}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      const data = await res.json();
      if (data.status === "success") {
        if (typeof showToast === "function") showToast(data.message, "success");
        await loadDashboardData();
        openDossierModal(contractCode);
      } else {
        if (typeof showToast === "function") showToast(data.message || "Lỗi cập nhật", "error");
      }
    } catch (err) {
      if (typeof showToast === "function") showToast("Lỗi: " + err.message, "error");
    }
  };
})();
