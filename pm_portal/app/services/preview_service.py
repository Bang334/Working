"""Preview service to render bilingual contract HTML preview and rich text."""

import re
from typing import Any, Dict
from app.utils.currency_helper import (
    format_currency_vnd,
    number_to_chinese_words,
    number_to_vietnamese_words,
    parse_positive_integer,
)


def generate_contract_preview_html(data: Dict[str, Any]) -> str:
    """Generate high-fidelity HTML representation of the contract matching official A4 style."""
    so_hd = data.get("so_hop_dong", "HD-20261013-001")
    ngay = data.get("ngay_ky", "13")
    thang = data.get("thang_ky", "10")
    nam = data.get("nam_ky", "2026")

    ben_a = dict(data.get("ben_a", {}))
    raw_role = str(ben_a.get("chuc_vu", "")).strip()
    if raw_role:
        role_cleaned = re.sub(r"\s*/\s*[\u4e00-\u9fff\s]+.*$", "", raw_role)
        role_cleaned = re.sub(r"[\u4e00-\u9fff]+", "", role_cleaned).strip().upper()
        ben_a["chuc_vu"] = role_cleaned or "TỔNG GIÁM ĐỐC"
    ben_b = data.get("ben_b", {
        "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
        "ten_tieng_trung": "宏明環球有限公司",
        "dia_chi": "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
        "dia_chi_trung": "越南胡志明市西貢坊阮惠路68號2樓",
        "mst": "0318280158",
        "nguoi_dai_dien": "TANG WEI LI",
        "chuc_vu": "TỔNG GIÁM ĐỐC",
        "chuc_vu_trung": "總經理"
    })

    du_an = data.get("du_an", {})
    ten_du_an_vn = du_an.get("ten_du_an_viet", "Hệ thống Quản lý Kho WMS & MES Pro")
    ten_du_an_cn = du_an.get("ten_du_an_trung", "")

    hang_muc = data.get("hang_muc", [])
    total_val = parse_positive_integer(data.get("tong_tien_hop_dong_so", 0))
    if total_val == 0:
        for item in hang_muc:
            total_val += parse_positive_integer(item.get("tong_gia", 0))

    total_formatted = f"{total_val:,}".replace(",", ".")
    words_vn = number_to_vietnamese_words(total_val)
    words_cn = number_to_chinese_words(total_val)

    # Line items HTML rows
    items_rows_html = ""
    for item in hang_muc:
        stt = item.get("stt", 1)
        name = str(item.get("ten_san_pham", "")).replace("\n", "<br>")
        price = item.get("don_gia", "")
        qty = item.get("so_luong", "")
        total = item.get("tong_gia", "")

        items_rows_html += f"""
        <tr>
            <td class="text-center">{stt}</td>
            <td class="item-name">{name}</td>
            <td class="text-right">{price}</td>
            <td class="text-center">{qty}</td>
            <td class="text-right font-semibold">{total}</td>
        </tr>
        """

    # Payment installments HTML
    installments = data.get("phan_bo_thanh_toan", [])
    installments_html = ""
    if installments:
        for idx, inst in enumerate(installments, start=1):
            dot = inst.get("dot", idx)
            pct = inst.get("phan_tram", 0)
            amount = int(total_val * float(pct) / 100.0)
            amount_str = f"{amount:,}".replace(",", ".")
            words_cn_inst = number_to_chinese_words(amount)
            words_vn_inst = number_to_vietnamese_words(amount)

            total_count = len(installments)
            dk_cn = inst.get("dieu_kien_trung", "").strip().lstrip("，,。").rstrip("。")
            dk_vn = inst.get("dieu_kien_viet", "").strip().lstrip(" ,.-").rstrip(".")

            tieu_de_cn = inst.get("tieu_de_trung", "").strip()
            if not tieu_de_cn:
                combined_dk = f"{dk_cn} {dk_vn}".lower()
                if any(k in combined_dk for k in ["佈線", "配線", "kéo dây", "kéo cáp", "hạ tầng"]):
                    tieu_de_cn = "佈線工程款"
                elif any(k in combined_dk for k in ["設備安裝", "調測", "lắp đặt", "cài đặt", "chạy thử"]):
                    tieu_de_cn = "設備安裝款"
                elif any(k in combined_dk for k in ["驗收", "fac", "nghiệm thu", "bàn giao"]):
                    tieu_de_cn = "驗收尾款"
                elif any(k in combined_dk for k in ["簽約", "tạm ứng", "ký hợp đồng"]):
                    tieu_de_cn = "簽約定金"
                elif dot == 1:
                    tieu_de_cn = "簽約定金"
                elif dot == total_count:
                    tieu_de_cn = "驗收尾款"
                elif total_count == 4 and dot == 2:
                    tieu_de_cn = "佈線工程款"
                elif total_count == 4 and dot == 3:
                    tieu_de_cn = "設備安裝款"
                elif total_count == 3 and dot == 2:
                    tieu_de_cn = "設備安裝款"
                else:
                    tieu_de_cn = f"第 {dot} 期款"

            tieu_de_vn = inst.get("tieu_de", "").strip()
            if not tieu_de_vn:
                if tieu_de_cn == "簽約定金":
                    tieu_de_vn = f"Đợt {dot} (Tạm ứng {pct}%)"
                elif tieu_de_cn == "佈線工程款":
                    tieu_de_vn = f"Đợt {dot} ({pct}% Thi công kéo dây/hạ tầng)"
                elif tieu_de_cn == "設備安裝款":
                    tieu_de_vn = f"Đợt {dot} ({pct}% Lắp đặt thiết bị)"
                elif tieu_de_cn == "驗收尾款":
                    tieu_de_vn = f"Đợt {dot} ({pct}% Nghiệm thu cuối cùng)"
                else:
                    tieu_de_vn = f"Đợt {dot} ({pct}%)"

            cn_cond_text = f"，{dk_cn}。" if dk_cn else "。"
            vn_cond_text = f" {dk_vn}." if dk_vn else "."

            words_vn_clean = words_vn_inst.rstrip(".")

            installments_html += f"""
            <div class="installment-block" style="margin-bottom: 1.15rem; line-height: 1.7;">
                <div class="cjk-text" style="font-weight: 600; color: #0f172a; font-size: 0.98rem;">
                    <strong>{dot}. {tieu_de_cn}:</strong> 支付合約總金額之 {pct}%, 即 <strong>{amount_str} VND</strong> ({words_cn_inst}){cn_cond_text}
                </div>
                <div style="padding-left: 1.5rem; color: #334155; font-size: 0.92rem; margin-top: 0.25rem;">
                    <strong>{tieu_de_vn}:</strong> Thanh toán {pct}% giá trị hợp đồng (<strong>{amount_str} VND</strong> – {words_vn_clean}.){vn_cond_text}
                </div>
            </div>
            """

    # Summary row HTML for product table: Có giảm giá (Hình 1) vs Không giảm giá (Hình 2)
    has_discount = data.get("has_discount")
    tt_truoc = parse_positive_integer(data.get("tong_tien_truoc_giam", 0))
    tt_sau = parse_positive_integer(data.get("tong_tien_sau_giam", 0))
    if has_discount is None:
        has_discount = (tt_truoc > 0 and total_val > 0 and total_val < tt_truoc)

    if has_discount:
        summary_row_html = f"""
                        {items_rows_html}
                        <tr class="summary-row">
                            <td colspan="2" class="text-center font-bold">總共 / Tổng Cộng</td>
                            <td class="text-right font-bold">{data.get('tong_tien_truoc_giam', f'{total_formatted} VND')}</td>
                            <td class="text-center font-bold">Sau Giảm Giá<br>優惠價</td>
                            <td class="text-right font-bold highlight-total">{total_formatted} VND</td>
                        </tr>
        """
    else:
        summary_row_html = f"""
                        {items_rows_html}
                        <tr class="summary-row">
                            <td colspan="2" class="text-center font-bold">總共 / Tổng Cộng</td>
                            <td class="text-right font-bold"></td>
                            <td class="text-center font-bold">{data.get('tong_so_luong', '')}</td>
                            <td class="text-right font-bold highlight-total">{total_formatted} VND</td>
                        </tr>
        """

    preview_html = f"""
    <div class="contract-paper" id="contractPaperPreview">
        <div class="contract-national-header">
            <div class="header-cn">
                <p class="title-bold">越南社會主義共和國</p>
                <p class="subtitle">獨立 – 自由 – 幸福</p>
                <div class="line-divider">───────</div>
            </div>
            <div class="header-vn">
                <p class="title-bold">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</p>
                <p class="subtitle">Độc lập – Tự do – Hạnh phúc</p>
                <div class="line-divider">───────</div>
            </div>
        </div>

        <div class="contract-title-section">
            <h1 class="main-title">經濟合約 / HỢP ĐỒNG KINH TẾ</h1>
            <p class="contract-no">合約編號 / Số HĐ: <strong>{so_hd}</strong></p>
        </div>

        <div class="contract-parties-section">
            <!-- Bên A -->
            <div class="party-box party-a">
                <div class="party-header">
                    <h3>買方 (BÊN A): <strong>{ben_a.get('ten_tieng_trung') or ben_a.get('ten_cong_ty', '')}</strong></h3>
                    {f"<p class='party-cn'>{ben_a.get('ten_cong_ty', '')}</p>" if ben_a.get('ten_tieng_trung') else ''}
                </div>
                <table class="party-details-table">
                    <tr>
                        <td class="label">地址 / Địa chỉ:</td>
                        <td><span class='cjk-text'>{ben_a.get('dia_chi_trung', '')}</span> {f"<br>{ben_a.get('dia_chi')}" if ben_a.get('dia_chi') else ''}</td>
                    </tr>
                    <tr>
                        <td class="label">稅號 / MST:</td>
                        <td><strong>{ben_a.get('mst', '')}</strong></td>
                    </tr>
                    <tr>
                        <td class="label">代表人 / Đại diện:</td>
                        <td><strong>{ben_a.get('nguoi_dai_dien', '')}</strong> — 職務 / Chức vụ: {ben_a.get('chuc_vu_trung', '')} {f"({ben_a.get('chuc_vu', '')})" if ben_a.get('chuc_vu') else ''}</td>
                    </tr>
                </table>
            </div>

            <!-- Bên B -->
            <div class="party-box party-b">
                <div class="party-header">
                    <h3>賣方 (BÊN B): <strong>{ben_b.get('ten_tieng_trung', '宏明環球有限公司')}</strong></h3>
                    <p class='party-cn'>{ben_b.get('ten_cong_ty', 'CÔNG TY TNHH TOÀN CẦU HONG MING')}</p>
                </div>
                <table class="party-details-table">
                    <tr>
                        <td class="label">地址 / Địa chỉ:</td>
                        <td><span class='cjk-text'>{ben_b.get('dia_chi_trung', '越南胡志明市西貢坊阮惠路68號2樓')}</span><br>{ben_b.get('dia_chi', '')}</td>
                    </tr>
                    <tr>
                        <td class="label">稅號 / MST:</td>
                        <td><strong>{ben_b.get('mst', '0318280158')}</strong></td>
                    </tr>
                    <tr>
                        <td class="label">代表人 / Đại diện:</td>
                        <td><strong>{ben_b.get('nguoi_dai_dien', 'TANG WEI LI')}</strong> — 職務 / Chức vụ: {ben_b.get('chuc_vu_trung', '總經理')} ({ben_b.get('chuc_vu', 'TỔNG GIÁM ĐỐC')})</td>
                    </tr>
                </table>
            </div>
        </div>

        <!-- Căn cứ hợp đồng -->
        <div class="contract-clause">
            <p class="clause-preamble-cn cjk-text">雙方就 {ten_du_an_cn or ten_du_an_vn} 報價內容達成共識，並同意簽訂本合約，共同遵守執行合約內容如下:</p>
            <p class="clause-preamble">
                Hai bên đã thống nhất thỏa thuận dựa trên nội dung <strong>Báo giá triển khai {ten_du_an_vn}</strong>{f' ({ten_du_an_cn})' if ten_du_an_cn else ''}, và ký kết hợp đồng này. Hai bên cùng cam kết tuân thủ và thực hiện các điều khoản nội dung hợp đồng như sau:
            </p>
        </div>

        <!-- Điều 1: Bảng sản phẩm -->
        <div class="contract-clause">
            <h4 class="clause-heading">第一條：標的物與價格 / ĐIỀU 1: HÀNG HÓA VÀ GIÁ CẢ</h4>
            <div class="table-responsive">
                <table class="contract-items-table">
                    <thead>
                        <tr>
                            <th style="width: 50px;">序號<br>STT</th>
                            <th>產品名稱<br>Tên Sản Phẩm</th>
                            <th style="width: 150px;">單價 (VND)<br>Đơn giá</th>
                            <th style="width: 90px;">數量<br>Số lượng</th>
                            <th style="width: 170px;">總價 (VND)<br>Tổng Giá</th>
                        </tr>
                    </thead>
                    <tbody>
                        {summary_row_html}
                    </tbody>
                </table>
            </div>

            <div class="total-words-box">
                <p><strong>Tổng cộng số tiền phải thanh toán:</strong> {total_formatted} VND (<em>{words_vn}</em>)</p>
                <p class="cjk-text"><strong>總金額:</strong> {total_formatted} VND (<em>{words_cn}</em>)</p>
            </div>
        </div>

        <!-- Điều 2: Tiến độ thanh toán -->
        <div class="contract-clause">
            <h4 class="clause-heading">第二條：付款方式 / ĐIỀU 2: PHƯƠNG THỨC THANH TOÁN</h4>
            {installments_html}
        </div>

        <!-- Điều 3: Thời gian giao hàng & bảo hành -->
        <div class="contract-clause">
            <h4 class="clause-heading">第三條：交貨期限及條件 / ĐIỀU 3: THỜI HẠN VÀ ĐIỀU KIỆN GIAO HÀNG</h4>
            <p class="cjk-text">• 交貨及系統建置期：自買方支付第一期款日起 <strong>{data.get('thoi_gian_giao_hang_ngay', 80)} 天</strong> 內完成交付。</p>
            <p>• Thời gian thực hiện và bàn giao: <strong>{data.get('thoi_gian_giao_hang_ngay', 80)} ngày</strong> kể từ ngày Bên A thanh toán đợt 1.</p>
            <p class="cjk-text">• 系統保固期：依製造商原廠標準保固 <strong>{data.get('thoi_gian_bao_hanh_thang', 12)} 個月</strong>。</p>
            <p>• Thời gian bảo hành hệ thống: <strong>{data.get('thoi_gian_bao_hanh_thang', 12)} tháng</strong> theo tiêu chuẩn nhà sản xuất.</p>
        </div>

        <!-- Chữ ký -->
        <div class="contract-signatures-section">
            <div class="sig-date">
                <p>合約日期 / Ngày hợp đồng (Ngày / Tháng / Năm)： &nbsp;&nbsp;&nbsp;&nbsp; / &nbsp;&nbsp;&nbsp;&nbsp; / <strong>{nam or '2026'}</strong></p>
            </div>
            <div class="sig-boxes-grid">
                <div class="sig-box text-center">
                    <p class="sig-title"><strong>買方代表 / ĐẠI DIỆN BÊN A</strong></p>
                    <p class="sig-company">{ben_a.get('ten_tieng_trung') or ben_a.get('ten_cong_ty', '')}</p>
                    <div class="sig-space"></div>
                    <p class="sig-name"><strong>{ben_a.get('nguoi_dai_dien', '')}</strong></p>
                    <p class="sig-role">{ben_a.get('chuc_vu_trung', '總經理')} {f"({ben_a.get('chuc_vu')})" if ben_a.get('chuc_vu') else ''}</p>
                </div>
                <div class="sig-box text-center">
                    <p class="sig-title"><strong>賣方代表 / ĐẠI DIỆN BÊN B</strong></p>
                    <p class="sig-company">{ben_b.get('ten_tieng_trung', '宏明環球有限公司')}</p>
                    <div class="sig-space"></div>
                    <p class="sig-name"><strong>{ben_b.get('nguoi_dai_dien', 'TANG WEI LI')}</strong></p>
                    <p class="sig-role">{ben_b.get('chuc_vu_trung', '總經理')} ({ben_b.get('chuc_vu', 'TỔNG GIÁM ĐỐC')})</p>
                </div>
            </div>
        </div>
    </div>
    """
    return preview_html
