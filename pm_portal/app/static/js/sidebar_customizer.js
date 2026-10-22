/**
 * Sidebar Navigation Tab Customizer for Hong Ming Global PM Portal.
 * Allows user to temporarily hide/restore specific sidebar menu tabs based on individual responsibilities.
 */

const SidebarTabManager = {
  STORAGE_KEY: "hm_hidden_sidebar_tabs",

  TABS: [
    {
      id: "dashboard",
      section: "admin",
      name: "Trang Chủ · Tổng Quan Dự Án",
      icon: "📊",
      url: "/",
      desc: "Tiến độ hồ sơ, cảnh báo công việc và tổng quan tài chính dự án",
    },
    {
      id: "files",
      section: "admin",
      name: "Quản Lý Hồ Sơ & File",
      icon: "📁",
      url: "/files",
      desc: "Trung tâm quản lý toàn bộ hồ sơ, báo giá, hợp đồng & biên bản tập trung",
    },
    {
      id: "quotations",
      section: "project_flow",
      name: "Bảng Báo Giá Song Ngữ",
      icon: "📄",
      url: "/quotations",
      desc: "Báo giá thiết bị, vật tư (ẩn tạm khi Sếp trực tiếp đàm phán thương lượng)",
    },
    {
      id: "contracts",
      section: "project_flow",
      name: "Tạo Hợp Đồng Mua Bán",
      icon: "📑",
      url: "/contracts",
      desc: "Soạn thảo và xuất file hợp đồng mẫu song ngữ Việt - Trung",
    },
    {
      id: "repair_contracts",
      section: "project_flow",
      name: "Hợp Đồng Sửa Chữa",
      icon: "🛠️",
      url: "/repair-contracts",
      desc: "Soạn thảo và bóc tách hợp đồng dịch vụ sửa chữa thiết bị, linh kiện",
    },
    {
      id: "po",
      section: "project_flow",
      name: "Đơn Đặt Mua Hàng (PO)",
      icon: "🛒",
      url: "/purchase-orders",
      desc: "Tạo đơn đặt hàng PO thiết bị nhà xưởng, linh kiện máy móc",
    },
    {
      id: "delivery",
      section: "project_flow",
      name: "Phiếu Xuất Kho & Bàn Giao",
      icon: "🚚",
      url: "/delivery",
      desc: "Phiếu xuất kho, biên bản bàn giao vật tư máy móc cho khách hàng",
    },
    {
      id: "acceptance",
      section: "project_flow",
      name: "Biên Bản Nghiệm Thu",
      icon: "✅",
      url: "/acceptance",
      desc: "Nghiệm thu từng giai đoạn (30%, 40%, 100% FAC)",
    },
    {
      id: "reminders",
      section: "project_flow",
      name: "Đề Nghị TT & Nhắc Nợ",
      icon: "⏰",
      url: "/reminders",
      desc: "Đề nghị thanh toán, thư nhắc nợ khách hàng & lịch hẹn cá nhân",
    },
    {
      id: "payment_requests",
      section: "project_flow",
      name: "Đơn Xin Thanh Toán",
      icon: "💳",
      url: "/payment-requests",
      desc: "Lập đơn xin thanh toán chi phí nội bộ & nhà cung cấp (浤詺付款申请单)",
    },
    {
      id: "liquidation",
      section: "project_flow",
      name: "Thanh Lý Hợp Đồng",
      icon: "🤝",
      url: "/liquidation",
      desc: "Biên bản thanh lý và quyết toán hợp đồng kết thúc dự án",
    },
    {
      id: "fonts",
      section: "styling",
      name: "Kho 100 Kiểu Chữ (Fonts)",
      icon: "🔤",
      url: "/fonts",
      desc: "Thư viện kiểu chữ doanh nghiệp, xem trước và đổi font toàn trang",
    },
  ],

  SECTIONS: {
    admin: "Quản trị & Giám sát",
    project_flow: "Chuỗi hồ sơ dự án",
    styling: "Giao diện & Kiểu chữ",
  },

  // Staged hidden set while modal is open
  stagedHiddenIds: new Set(),

  init() {
    this.applyVisibility();
    this.checkCurrentPageHiddenBanner();
    this.bindGlobalEvents();
  },

  getHiddenIds() {
    try {
      const raw = localStorage.getItem(this.STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  },

  setHiddenIds(ids) {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(ids));
    } catch (e) {
      console.warn("Không thể lưu cài đặt ẩn tab:", e);
    }
  },

  applyVisibility() {
    const hiddenIds = this.getHiddenIds();
    const hiddenSet = new Set(hiddenIds);

    // 1. Update dynamic style in head for instant zero-flicker
    let style = document.getElementById("hm-sidebar-hidden-css");
    if (!style) {
      style = document.createElement("style");
      style.id = "hm-sidebar-hidden-css";
      document.head.appendChild(style);
    }

    if (hiddenIds.length > 0) {
      style.textContent = hiddenIds
        .map((id) => `.nav-item[data-nav-id="${id}"] { display: none !important; }`)
        .join("\n");
    } else {
      style.textContent = "";
    }

    // 2. Smart auto-hide for section headers if all its child items are hidden
    const sectionCounts = {};
    for (const tab of this.TABS) {
      if (!sectionCounts[tab.section]) {
        sectionCounts[tab.section] = { total: 0, visible: 0 };
      }
      sectionCounts[tab.section].total++;
      if (!hiddenSet.has(tab.id)) {
        sectionCounts[tab.section].visible++;
      }
    }

    for (const [secId, counts] of Object.entries(sectionCounts)) {
      const titleElem = document.querySelector(`.nav-section-title[data-section-id="${secId}"]`);
      if (titleElem) {
        if (counts.visible === 0) {
          titleElem.style.display = "none";
        } else {
          titleElem.style.display = "";
        }
      }
    }

    // 3. Update counter badge on sidebar customize button
    const badge = document.getElementById("sidebarHiddenBadge");
    if (badge) {
      if (hiddenIds.length > 0) {
        badge.textContent = `Ẩn: ${hiddenIds.length}`;
        badge.style.display = "inline-flex";
        badge.title = `Đang ẩn ${hiddenIds.length} tab trên thanh menu. Bấm để xem hoặc hiện lại.`;
      } else {
        badge.style.display = "none";
      }
    }
  },

  checkCurrentPageHiddenBanner() {
    const hiddenIds = this.getHiddenIds();
    if (!hiddenIds.length) return;

    const currentPath = window.location.pathname;
    const currentTab = this.TABS.find(
      (t) => (t.url === "/" && currentPath === "/") || (t.url !== "/" && currentPath.startsWith(t.url))
    );

    if (currentTab && hiddenIds.includes(currentTab.id)) {
      // User is currently viewing a hidden tab! Show friendly notice banner
      const mainContent = document.getElementById("main-content");
      if (mainContent && !document.getElementById("scHiddenNoticeBanner")) {
        const banner = document.createElement("div");
        banner.id = "scHiddenNoticeBanner";
        banner.className = "sc-hidden-page-banner";
        banner.innerHTML = `
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">👁️</span>
            <div>
              <strong>Tab "${currentTab.name}" đang được ẩn trên thanh menu</strong> theo cài đặt cá nhân của bạn.
            </div>
          </div>
          <button type="button" class="sc-hidden-banner-btn" onclick="SidebarTabManager.unhideSingleTab('${currentTab.id}')">
            ✓ Hiện lại tab này trên menu
          </button>
        `;

        const header = mainContent.querySelector(".app-header");
        if (header && header.nextSibling) {
          mainContent.insertBefore(banner, header.nextSibling);
        } else {
          mainContent.prepend(banner);
        }
      }
    }
  },

  unhideSingleTab(tabId) {
    let hiddenIds = this.getHiddenIds();
    hiddenIds = hiddenIds.filter((id) => id !== tabId);
    this.setHiddenIds(hiddenIds);
    this.applyVisibility();

    const banner = document.getElementById("scHiddenNoticeBanner");
    if (banner) banner.remove();

    if (typeof showToast === "function") {
      const tab = this.TABS.find((t) => t.id === tabId);
      showToast(`Đã bật hiển thị tab "${tab ? tab.name : tabId}" trên menu!`, "success");
    }
  },

  openModal() {
    const hiddenIds = this.getHiddenIds();
    this.stagedHiddenIds = new Set(hiddenIds);
    this.renderModalBody();
    this.updateModalFooter();

    const overlay = document.getElementById("scModalOverlay");
    if (overlay) {
      overlay.classList.add("active");
      document.body.style.overflow = "hidden";
    }
  },

  closeModal() {
    const overlay = document.getElementById("scModalOverlay");
    if (overlay) {
      overlay.classList.remove("active");
      document.body.style.overflow = "";
    }
  },

  renderModalBody() {
    const container = document.getElementById("scModalBody");
    if (!container) return;

    let html = "";
    const grouped = {};

    for (const tab of this.TABS) {
      if (!grouped[tab.section]) grouped[tab.section] = [];
      grouped[tab.section].push(tab);
    }

    for (const [secId, tabList] of Object.entries(grouped)) {
      const secName = this.SECTIONS[secId] || "Chức năng";
      html += `
        <div class="sc-group">
          <div class="sc-group-title">📂 ${secName}</div>
      `;

      for (const tab of tabList) {
        const isHidden = this.stagedHiddenIds.has(tab.id);
        const isShown = !isHidden;

        html += `
          <div class="sc-tab-row ${isHidden ? "is-hidden" : ""}" id="scRow_${tab.id}">
            <div class="sc-tab-info">
              <div class="sc-tab-icon">${tab.icon}</div>
              <div class="sc-tab-text">
                <div class="sc-tab-name-wrap">
                  <span class="sc-tab-name">${this.escapeHtml(tab.name)}</span>
                  <span class="sc-tab-badge">${tab.url}</span>
                </div>
                <div class="sc-tab-desc">${this.escapeHtml(tab.desc)}</div>
              </div>
            </div>

            <label class="sc-toggle-label" title="${isShown ? "Bấm để ẩn tạm tab này" : "Bấm để hiện lại tab này"}">
              <span class="sc-toggle-status ${isShown ? "status-shown" : "status-hidden"}" id="scStatus_${tab.id}">
                ${isShown ? "✓ Hiện" : "Ẩn"}
              </span>
              <div class="sc-switch">
                <input type="checkbox" id="scCheck_${tab.id}" ${isShown ? "checked" : ""} onchange="SidebarTabManager.handleToggle('${tab.id}', this.checked)">
                <span class="sc-slider"></span>
              </div>
            </label>
          </div>
        `;
      }

      html += `</div>`;
    }

    container.innerHTML = html;
  },

  handleToggle(tabId, isChecked) {
    if (isChecked) {
      this.stagedHiddenIds.delete(tabId);
    } else {
      this.stagedHiddenIds.add(tabId);
    }

    // Update row visual
    const row = document.getElementById(`scRow_${tabId}`);
    const statusText = document.getElementById(`scStatus_${tabId}`);
    if (row && statusText) {
      if (isChecked) {
        row.classList.remove("is-hidden");
        statusText.textContent = "✓ Hiện";
        statusText.className = "sc-toggle-status status-shown";
      } else {
        row.classList.add("is-hidden");
        statusText.textContent = "Ẩn";
        statusText.className = "sc-toggle-status status-hidden";
      }
    }

    this.updateModalFooter();
  },

  showAll() {
    this.stagedHiddenIds.clear();
    for (const tab of this.TABS) {
      const chk = document.getElementById(`scCheck_${tab.id}`);
      if (chk) chk.checked = true;
      const row = document.getElementById(`scRow_${tab.id}`);
      if (row) row.classList.remove("is-hidden");
      const statusText = document.getElementById(`scStatus_${tab.id}`);
      if (statusText) {
        statusText.textContent = "✓ Hiện";
        statusText.className = "sc-toggle-status status-shown";
      }
    }
    this.updateModalFooter();
  },

  resetDefault() {
    this.showAll();
  },

  updateModalFooter() {
    const total = this.TABS.length;
    const hiddenCount = this.stagedHiddenIds.size;
    const visibleCount = total - hiddenCount;

    const statsElem = document.getElementById("scFooterStats");
    if (statsElem) {
      if (hiddenCount > 0) {
        statsElem.innerHTML = `Đang hiển thị <strong>${visibleCount}/${total}</strong> tab · Đang tạm ẩn <strong style="color: #b45309;">${hiddenCount} tab</strong>`;
      } else {
        statsElem.innerHTML = `Đang hiển thị đủ <strong>${total}/${total}</strong> tab (Chưa ẩn tab nào)`;
      }
    }
  },

  saveChanges() {
    const hiddenList = Array.from(this.stagedHiddenIds);
    this.setHiddenIds(hiddenList);
    this.applyVisibility();
    this.closeModal();

    // Check banner on current page
    const banner = document.getElementById("scHiddenNoticeBanner");
    if (banner) banner.remove();
    this.checkCurrentPageHiddenBanner();

    if (typeof showToast === "function") {
      if (hiddenList.length > 0) {
        showToast(`Đã lưu tùy chỉnh! Đang tạm ẩn ${hiddenList.length} tab trên thanh menu.`, "info");
      } else {
        showToast("Đã bật hiển thị đầy đủ tất cả các tab trên menu!", "success");
      }
    }
  },

  bindGlobalEvents() {
    // Close modal on Escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.closeModal();
      }
    });

    // Close on clicking backdrop
    const overlay = document.getElementById("scModalOverlay");
    if (overlay) {
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) {
          this.closeModal();
        }
      });
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

// Global trigger function
function openSidebarTabCustomizer() {
  SidebarTabManager.openModal();
}

// Auto init on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  SidebarTabManager.init();
});
