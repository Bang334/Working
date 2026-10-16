"""Business logic for Payment Requests and AR Reminders (Song ngữ Việt - Đài Loan)."""

import html
import re
from typing import Any, Dict, List

from app.utils.currency_helper import (
    format_currency_vnd,
    number_to_chinese_words,
    number_to_vietnamese_words,
    parse_positive_integer,
)


def format_amount_display(val: Any) -> str:
    """Format numeric string or int to dot-separated VND string without 'VND' suffix."""
    n = parse_positive_integer(val)
    return f"{n:,}".replace(",", ".")


def prepare_reminder_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize, calculate totals, and normalize payment reminder payload."""
    data = dict(raw or {})
    
    cap_do = int(data.get("cap_do") or 1)
    so_cong_van = str(data.get("so_cong_van") or "HM-PR-20261013-001").strip()
    ngay_phat_hanh = str(data.get("ngay_phat_hanh") or "13/10/2026").strip()
    
    # Customer
    khach_hang = dict(data.get("khach_hang") or {})
    ten_khach = str(khach_hang.get("ten_khach_hang") or "CX Technology (VN)").strip()
    ten_trung = str(khach_hang.get("ten_tieng_trung") or ten_khach).strip()
    email_to = khach_hang.get("email_to") or ["pur04_vn@mail.cxtechnology.com"]
    if isinstance(email_to, str):
        email_to = [e.strip() for e in email_to.replace(";", ",").split(",") if e.strip()]
    email_cc = khach_hang.get("email_cc") or [
        "jenson@youngming-mes.com",
        "jessica@youngming-mes.com",
        "lisa@youngming-mes.com",
        "sales@hongming-global.com"
    ]
    if isinstance(email_cc, str):
        email_cc = [e.strip() for e in email_cc.replace(";", ",").split(",") if e.strip()]
        
    khach_hang["ten_khach_hang"] = ten_khach
    khach_hang["ten_tieng_trung"] = ten_trung
    khach_hang["email_to"] = email_to
    khach_hang["email_cc"] = email_cc
    
    # Bank
    tai_khoan = dict(data.get("tai_khoan") or {})
    ten_tk = str(tai_khoan.get("ten_tai_khoan") or "CÔNG TY TNHH TOÀN CẦU HONG MING").strip()
    so_tk = str(tai_khoan.get("so_tai_khoan") or "0318280158").strip()
    ngan_hang = str(tai_khoan.get("ngan_hang") or "Ngân hàng TMCP Á Châu (ACB) - Chi nhánh TP.HCM").strip()
    
    # Line items
    raw_items = data.get("khoan_thanh_toan") or []
    sanitized_items: List[Dict[str, Any]] = []
    total_val = 0
    contract_numbers: List[str] = []
    
    for idx, it in enumerate(raw_items, start=1):
        so_hd = str(it.get("so_hop_dong") or f"HMV-2026-{idx:03d}").strip()
        if so_hd and so_hd not in contract_numbers:
            contract_numbers.append(so_hd)
        
        hang_muc = str(it.get("hang_muc") or f"Hạng mục dịch vụ / thiết bị đợt {idx}").strip()
        noi_dung = str(it.get("noi_dung_thanh_toan") or "").strip()
        amount_num = parse_positive_integer(it.get("so_tien"))
        total_val += amount_num
        
        vat_info = str(it.get("vat_info") or "").strip()
        han_tt = str(it.get("han_thanh_toan") or "").strip()
        ghi_chu = str(it.get("ghi_chu") or "").strip()
        
        sanitized_items.append({
            "stt": idx,
            "so_hop_dong": so_hd,
            "hang_muc": hang_muc,
            "noi_dung_thanh_toan": noi_dung,
            "so_tien": amount_num,
            "so_tien_formatted": format_amount_display(amount_num),
            "vat_info": vat_info,
            "han_thanh_toan": han_tt,
            "ghi_chu": ghi_chu
        })
    
    # If explicit total given, use it, otherwise use sum
    override_total = parse_positive_integer(data.get("tong_tien_so"))
    final_total = override_total if override_total > 0 else total_val
    
    total_words_vi = number_to_vietnamese_words(final_total)
    total_words_zh = number_to_chinese_words(final_total)
    
    # Subject generation
    hd_str = "、".join(contract_numbers) if contract_numbers else "合約"
    hd_vi_str = " và ".join(contract_numbers) if contract_numbers else "hợp đồng"
    
    if cap_do == 1:
        default_subject = f"請協助安排付款 - {hd_str} 合約款項 Yêu cầu hỗ trợ thanh toán - Hợp đồng {hd_vi_str}"
    elif cap_do == 2:
        default_subject = f"【宏明環球】合約 {hd_str} 款項到期提醒 - Đôn đốc thanh toán HĐ {hd_vi_str}"
    else:
        default_subject = f"【宏明環球】逾期應收帳款催收通知函 - CÔNG VĂN ĐÔN ĐỐC CÔNG NỢ QUÁ HẠN HĐ {hd_vi_str}"
        
    tieu_de_email = str(data.get("tieu_de_email") or default_subject).strip()
    
    # Content formatting
    plain_body, html_body = generate_email_bodies(
        cap_do=cap_do,
        customer_name_zh=ten_trung,
        customer_name_vi=ten_khach,
        items=sanitized_items,
        total_amount=final_total,
        total_vi=total_words_vi,
        total_zh=total_words_zh,
        bank_name=ngan_hang,
        bank_acc=so_tk,
        bank_owner=ten_tk,
        contract_str=hd_str,
        contract_vi_str=hd_vi_str
    )
    
    # Attachments
    attachments = data.get("danh_sach_dinh_kem") or []
    if not attachments:
        attachments = [
            f"DXYCTT {format_amount_display(final_total)}.pdf",
            "Bản scan Biên bản nghiệm thu và bàn giao (驗收暨移交使用確認書)",
            "Hóa đơn giá trị gia tăng điện tử (VAT)"
        ]
        
    return {
        "cap_do": cap_do,
        "so_cong_van": so_cong_van,
        "ngay_phat_hanh": ngay_phat_hanh,
        "khach_hang": khach_hang,
        "tai_khoan": {
            "ten_tai_khoan": ten_tk,
            "so_tai_khoan": so_tk,
            "ngan_hang": ngan_hang,
            "noi_dung_chuyen_khoan": f"{ten_khach} thanh toan {hd_vi_str}"
        },
        "khoan_thanh_toan": sanitized_items,
        "tong_tien_so": final_total,
        "tong_tien_formatted": format_amount_display(final_total),
        "tong_tien_chu_viet": total_words_vi,
        "tong_tien_chu_trung": total_words_zh,
        "tieu_de_email": tieu_de_email,
        "email_nguoi_gui": data.get("email_nguoi_gui") or "pm02@hongming-global.com",
        "danh_sach_dinh_kem": attachments,
        "email_plain_body": plain_body,
        "email_html_body": html_body
    }


def generate_email_bodies(
    cap_do: int,
    customer_name_zh: str,
    customer_name_vi: str,
    items: List[Dict[str, Any]],
    total_amount: int,
    total_vi: str,
    total_zh: str,
    bank_name: str,
    bank_acc: str,
    bank_owner: str,
    contract_str: str,
    contract_vi_str: str
) -> (str, str):
    """Generate professional plain text and HTML email content matching Hong Ming 1:1 format."""
    
    # Build items text in Chinese
    zh_items_text = []
    for idx, it in enumerate(items, start=1):
        lines = [f"{idx}. {it['so_hop_dong']}"]
        lines.append(f"項目：{it['hang_muc']}")
        if it.get("noi_dung_thanh_toan"):
            lines.append(f"付款內容：{it['noi_dung_thanh_toan']}")
        vat = f" ({it['vat_info']})" if it.get("vat_info") else ""
        lines.append(f"請款金額：{it['so_tien_formatted']} VND{vat}")
        if it.get("han_thanh_toan"):
            lines.append(f"付款期限：{it['han_thanh_toan']}")
        zh_items_text.append("\n".join(lines))
        
    zh_items_str = "\n".join(zh_items_text)
    
    # Build items text in Vietnamese
    vi_items_text = []
    for idx, it in enumerate(items, start=1):
        lines = [f"{idx}. HĐ số {it['so_hop_dong']}"]
        lines.append(f"Hạng mục: {it['hang_muc']}")
        if it.get("noi_dung_thanh_toan"):
            lines.append(f"Nội dung: {it['noi_dung_thanh_toan']}")
        vat = f" ({it['vat_info']})" if it.get("vat_info") else ""
        lines.append(f"Số tiền đề nghị thanh toán: {it['so_tien_formatted']} VNĐ{vat}")
        if it.get("han_thanh_toan"):
            lines.append(f"Hạn thanh toán: {it['han_thanh_toan']}")
        vi_items_text.append("\n".join(lines))
        
    vi_items_str = "\n".join(vi_items_text)
    
    # Compose plain body
    plain_body = f"""敬啟者 {customer_name_zh} 您好：

首先，感謝貴公司一直以來對宏明全球有限公司的支持與配合。
有關以下兩項服務及產品款項，現已依照雙方確認內容提供請款資料，敬請貴公司協助安排付款：

{zh_items_str}

隨信附上相關請款單，敬請貴公司協助確認並安排付款，以利雙方後續合作及專案進度順利進行。
如付款流程中有任何需要補充的資料，請隨時與我們聯繫，我們將積極配合。
感謝貴公司的支持與配合。
敬祝 順心

==================================================

Kính gửi Quý Công ty {customer_name_vi},

Trước tiên, Công ty TNHH Toàn Cầu Hồng Minh xin cảm ơn Quý Công ty đã luôn hỗ trợ và phối hợp trong quá trình hợp tác.
Liên quan đến các khoản thanh toán dịch vụ và sản phẩm dưới đây, chúng tôi đã chuẩn bị đầy đủ hồ sơ đề nghị thanh toán theo đúng nội dung hai bên đã xác nhận, kính đề nghị Quý Công ty hỗ trợ thu xếp thanh toán:

{vi_items_str}

Kèm theo thư này là Giấy đề nghị thanh toán và hồ sơ liên quan, kính đề nghị Quý Công ty hỗ trợ xác nhận và sắp xếp thanh toán để việc hợp tác và tiến độ dự án được diễn ra thuận lợi.
Nếu trong quy trình thanh toán có bất kỳ thông tin hay tài liệu nào cần bổ sung, xin vui lòng liên hệ với chúng tôi, chúng tôi sẽ tích cực phối hợp.

Trân trọng cảm ơn sự ủng hộ và hợp tác của Quý Công ty.
Kính chúc Quý Công ty vạn sự hanh thông và phát triển!

--------------------------------------------------
THÔNG TIN TÀI KHOẢN THỤ HƯỞNG / 收款帳戶資訊:
- Tên tài khoản / 戶名: {bank_owner}
- Số tài khoản / 帳號: {bank_acc}
- Ngân hàng / 開戶銀行: {bank_name}
- Nội dung chuyển khoản / 匯款備註: {customer_name_vi} thanh toan {contract_vi_str}

Trân trọng,
CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司)
Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh
Điện thoại: +84 966 687 109 | Email: sales@hongming-global.com
"""

    # HTML Body with rich formatting
    zh_items_html_list = []
    for idx, it in enumerate(items, start=1):
        vat_badge = f"<span style='color: #4b5563; font-size: 0.9em;'>({html.escape(it.get('vat_info',''))})</span>" if it.get("vat_info") else ""
        nd_line = f"<div style='margin-top: 3px;'>付款內容：<strong>{html.escape(it.get('noi_dung_thanh_toan',''))}</strong></div>" if it.get('noi_dung_thanh_toan') else ""
        han_line = f"<div style='margin-top: 3px;'>付款期限：<strong style='color: #b91c1c;'>{html.escape(it.get('han_thanh_toan',''))}</strong></div>" if it.get('han_thanh_toan') else ""
        
        zh_items_html_list.append(f"""
        <div style="margin-bottom: 12px; padding: 10px 14px; background-color: #f8fafc; border-left: 3px solid #1e3a8a; border-radius: 4px;">
          <div style="font-weight: 700; color: #1e3a8a; font-size: 1.05em;">{idx}. {html.escape(it['so_hop_dong'])}</div>
          <div style="margin-top: 4px;">項目：{html.escape(it['hang_muc'])}</div>
          {nd_line}
          <div style="margin-top: 3px;">請款金額：<strong style="color: #047857; font-size: 1.05em;">{html.escape(it['so_tien_formatted'])} VND</strong> {vat_badge}</div>
          {han_line}
        </div>
        """)
        
    vi_items_html_list = []
    for idx, it in enumerate(items, start=1):
        vat_badge = f"<span style='color: #4b5563; font-size: 0.9em;'>({html.escape(it.get('vat_info',''))})</span>" if it.get("vat_info") else ""
        nd_line = f"<div style='margin-top: 3px;'>Nội dung: <strong>{html.escape(it.get('noi_dung_thanh_toan',''))}</strong></div>" if it.get('noi_dung_thanh_toan') else ""
        han_line = f"<div style='margin-top: 3px;'>Hạn thanh toán: <strong style='color: #b91c1c;'>{html.escape(it.get('han_thanh_toan',''))}</strong></div>" if it.get('han_thanh_toan') else ""
        
        vi_items_html_list.append(f"""
        <div style="margin-bottom: 12px; padding: 10px 14px; background-color: #f8fafc; border-left: 3px solid #2563eb; border-radius: 4px;">
          <div style="font-weight: 700; color: #1e40af; font-size: 1.05em;">{idx}. HĐ số {html.escape(it['so_hop_dong'])}</div>
          <div style="margin-top: 4px;">Hạng mục: {html.escape(it['hang_muc'])}</div>
          {nd_line}
          <div style="margin-top: 3px;">Số tiền đề nghị: <strong style="color: #047857; font-size: 1.05em;">{html.escape(it['so_tien_formatted'])} VNĐ</strong> {vat_badge}</div>
          {han_line}
        </div>
        """)

    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #1e293b; background-color: #ffffff; margin: 0; padding: 20px; }}
  .box {{ max-width: 680px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px; }}
  .divider {{ border: 0; border-top: 1px dashed #cbd5e1; margin: 24px 0; }}
  .bank-box {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 14px 18px; margin-top: 20px; }}
  .bank-title {{ font-weight: 700; color: #166534; font-size: 0.95em; margin-bottom: 8px; text-transform: uppercase; }}
  .footer {{ margin-top: 24px; font-size: 0.88em; color: #64748b; line-height: 1.5; }}
</style>
</head>
<body>
<div class="box">
  <p><strong>敬啟者 {html.escape(customer_name_zh)} 您好：</strong></p>
  <p>首先，感謝貴公司一直以來對宏明全球有限公司的支持與配合。<br>
  有關以下兩項服務及產品款項，現已依照雙方確認內容提供請款資料，敬請貴公司協助安排付款：</p>
  
  {"".join(zh_items_html_list)}
  
  <p>隨信附上相關請款單，敬請貴公司協助確認並安排付款，以利雙方後續合作及專案進度順利進行。<br>
  如付款流程中有任何需要補充的資料，請隨時與我們聯繫，我們將積極配合。<br>
  感謝貴公司的支持與配合。<br>
  敬祝 順心</p>

  <hr class="divider">

  <p><strong>Kính gửi Quý Công ty {html.escape(customer_name_vi)},</strong></p>
  <p>Trước tiên, Công ty TNHH Toàn Cầu Hồng Minh xin cảm ơn Quý Công ty đã luôn hỗ trợ và phối hợp trong quá trình hợp tác.<br>
  Liên quan đến các khoản thanh toán dịch vụ và sản phẩm dưới đây, chúng tôi đã chuẩn bị đầy đủ hồ sơ đề nghị thanh toán theo đúng nội dung hai bên đã xác nhận, kính đề nghị Quý Công ty hỗ trợ thu xếp thanh toán:</p>
  
  {"".join(vi_items_html_list)}
  
  <p>Kèm theo thư này là Giấy đề nghị thanh toán và hồ sơ liên quan, kính đề nghị Quý Công ty hỗ trợ xác nhận và sắp xếp thanh toán để việc hợp tác và tiến độ dự án được diễn ra thuận lợi.<br>
  Nếu trong quy trình thanh toán có bất kỳ tài liệu nào cần bổ sung, xin vui lòng liên hệ với chúng tôi, chúng tôi sẽ tích cực phối hợp.<br>
  Trân trọng cảm ơn sự ủng hộ và hợp tác của Quý Công ty.<br>
  Kính chúc Quý Công ty vạn sự hanh thông và phát triển!</p>

  <div class="bank-box">
    <div class="bank-title">THÔNG TIN TÀI KHOẢN THỤ HƯỞNG / 收款帳戶資訊</div>
    <div style="font-size: 0.93em; line-height: 1.6;">
      <div>• <strong>Tên tài khoản / 戶名:</strong> {html.escape(bank_owner)}</div>
      <div>• <strong>Số tài khoản / 帳號:</strong> <span style="font-family: monospace; font-size: 1.1em; font-weight: 700; color: #047857;">{html.escape(bank_acc)}</span></div>
      <div>• <strong>Ngân hàng / 開戶銀行:</strong> {html.escape(bank_name)}</div>
      <div>• <strong>Nội dung chuyển khoản / 匯款備註:</strong> <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 3px; font-size: 0.9em;">{html.escape(customer_name_vi)} thanh toan {html.escape(contract_vi_str)}</span></div>
    </div>
  </div>

  <div class="footer">
    <strong>CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司)</strong><br>
    Địa chỉ: Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh<br>
    Điện thoại / Hotline: +84 966 687 109 &bull; Email: sales@hongming-global.com
  </div>
</div>
</body>
</html>"""

    return plain_body, html_body


def render_email_client_preview_html(data: Dict[str, Any]) -> str:
    """Render interactive desktop email client preview matching Image 1."""
    khach = data.get("khach_hang", {})
    to_list = khach.get("email_to", [])
    cc_list = khach.get("email_cc", [])
    subject = data.get("tieu_de_email", "")
    attachments = data.get("danh_sach_dinh_kem", [])
    html_body = data.get("email_html_body", "")
    
    to_str = "; ".join([f"'{e}'" for e in to_list])
    cc_str = "; ".join([f"'{e}'" for e in cc_list])
    
    # Build attachments preview badge with correct icon and file sizes
    attach_badges = []
    for att in attachments:
        att_str = str(att).strip()
        if not att_str:
            continue
        ext = att_str.split(".")[-1].lower() if "." in att_str else "file"
        icon_class = "attach-icon-pdf"
        badge_text = "PDF"
        if ext in ["xlsx", "xls"]:
            icon_class = "attach-icon-xlsx"
            badge_text = "XLSX"
        elif ext in ["docx", "doc"]:
            icon_class = "attach-icon-docx"
            badge_text = "DOCX"
        elif ext != "pdf":
            icon_class = "attach-icon-file"
            badge_text = ext.upper()[:4]
            
        size_str = "10.7 KB" if ext in ["xlsx", "xls"] else ("35.9 KB" if ext in ["docx", "doc"] else "1.0 MB")
        try:
            from app.services.google_integration_service import _resolve_attachment_path
            resolved_p = _resolve_attachment_path(att_str)
            if resolved_p and resolved_p.exists():
                sz = resolved_p.stat().st_size
                if sz > 1024 * 1024:
                    size_str = f"{sz / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{max(1, round(sz / 1024))} KB"
        except Exception:
            pass

        attach_badges.append(f"""
        <div class="email-attach-card" title="{html.escape(att_str)}">
          <div class="{icon_class}">{badge_text}</div>
          <div class="attach-meta">
            <span class="attach-name">{html.escape(att_str)}</span>
            <span class="attach-size">{size_str}</span>
          </div>
        </div>
        """)
    attach_html = "".join(attach_badges) if attach_badges else "<span style='color: var(--text-muted); font-size: 0.85rem;'>Không có tệp đính kèm</span>"

    return f"""
    <div class="email-client-container">
      <!-- Email Header -->
      <div class="email-client-header">
        <div class="email-avatar">PG</div>
        <div class="email-header-details">
          <div class="email-sender-line">
            <span class="sender-address">{html.escape(data.get('email_nguoi_gui', 'pm02@hongming-global.com'))}</span>
            <span class="email-timestamp">Hôm nay, 11:15 AM</span>
          </div>
          <div class="email-field-row">
            <span class="field-label">To:</span>
            <span class="field-value">{html.escape(to_str)}</span>
          </div>
          <div class="email-field-row">
            <span class="field-label">Cc:</span>
            <span class="field-value">{html.escape(cc_str)}</span>
          </div>
          <div class="email-subject-line">
            <strong>{html.escape(subject)}</strong>
          </div>
        </div>
      </div>

      <!-- Attachment Strip -->
      <div class="email-attachments-bar">
        {attach_html}
      </div>

      <!-- Email Body -->
      <div class="email-client-body">
        {html_body}
      </div>
    </div>
    """


def render_dxyctt_preview_html(data: Dict[str, Any]) -> str:
    """Render official A4 Payment Request Document (GIẤY ĐỀ NGHỊ THANH TOÁN / 付款申請書)."""
    khach = data.get("khach_hang", {})
    items = data.get("khoan_thanh_toan", [])
    bank = data.get("tai_khoan", {})
    
    item_rows = []
    for idx, it in enumerate(items, start=1):
        vat_tag = f" <small style='color: #4b5563;'>({it.get('vat_info', '')})</small>" if it.get("vat_info") else ""
        item_rows.append(f"""
        <tr>
          <td style="text-align: center; width: 45px;">{idx}</td>
          <td style="font-weight: 600;">{html.escape(it.get('so_hop_dong', ''))}</td>
          <td>
            <strong>{html.escape(it.get('hang_muc', ''))}</strong>
            {f"<div style='font-size: 0.85em; color: #4b5563; margin-top: 2px;'>{html.escape(it.get('noi_dung_thanh_toan', ''))}</div>" if it.get('noi_dung_thanh_toan') else ""}
          </td>
          <td style="text-align: center; color: #b91c1c; font-weight: 600;">{html.escape(it.get('han_thanh_toan', ''))}</td>
          <td style="text-align: right; font-weight: 700; color: #047857;">{html.escape(it.get('so_tien_formatted', ''))} VNĐ{vat_tag}</td>
        </tr>
        """)
        
    items_table_html = "".join(item_rows)

    return f"""
    <div class="dxyctt-paper">
      <!-- Header -->
      <div class="dxyctt-top-row">
        <div>
          <div style="font-size: 1.1rem; font-weight: 800; color: #1e3a8a; text-transform: uppercase;">CÔNG TY TNHH TOÀN CẦU HONG MING</div>
          <div style="font-size: 0.95rem; font-weight: 700; color: #475569;">宏明環球有限公司</div>
          <div style="font-size: 0.8rem; color: #64748b; margin-top: 2px;">Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh &bull; MST: 0318280158</div>
        </div>
        <div style="text-align: right; font-size: 0.85rem; color: #64748b;">
          <div>Số / 編號: <strong>{html.escape(data.get('so_cong_van', ''))}</strong></div>
          <div>Ngày / 日期: {html.escape(data.get('ngay_phat_hanh', ''))}</div>
        </div>
      </div>

      <div class="dxyctt-title-box">
        <h1>GIẤY ĐỀ NGHỊ THANH TOÁN</h1>
        <h2>付款申請書</h2>
      </div>

      <!-- Recipient -->
      <div class="dxyctt-meta-box">
        <div><strong>Kính gửi / 致:</strong> Ban Quản Lý, Phòng Mua Hàng & Phòng Kế Toán &mdash; <strong>{html.escape(khach.get('ten_khach_hang', ''))} ({html.escape(khach.get('ten_tieng_trung', ''))})</strong></div>
        <div style="margin-top: 4px; font-size: 0.88rem; color: #475569;">Căn cứ các thỏa thuận Hợp đồng và Biên bản giao nhận, hoàn thành dịch vụ giữa hai bên.</div>
      </div>

      <!-- Items Table -->
      <table class="dxyctt-table">
        <thead>
          <tr>
            <th style="width: 45px;">STT</th>
            <th style="width: 140px;">Số Hợp Đồng</th>
            <th>Nội Dung Hạng Mục / 請款項目</th>
            <th style="width: 110px;">Hạn Trả</th>
            <th style="width: 150px; text-align: right;">Số Tiền (VND)</th>
          </tr>
        </thead>
        <tbody>
          {items_table_html}
          <tr style="background: #f8fafc; font-weight: 700;">
            <td colspan="4" style="text-align: right; padding-right: 15px; font-size: 0.95rem;">TỔNG CỘNG ĐỀ NGHỊ THANH TOÁN / 本期應付總金額:</td>
            <td style="text-align: right; font-size: 1.1rem; color: #047857;">{html.escape(data.get('tong_tien_formatted', ''))} VNĐ</td>
          </tr>
        </tbody>
      </table>

      <!-- Words -->
      <div style="margin-top: 12px; font-size: 0.9rem; line-height: 1.6; background: #fafafa; padding: 10px 14px; border-radius: 4px; border: 1px solid #e2e8f0;">
        <div>&bull; Bằng chữ (Tiếng Việt): <strong>{html.escape(data.get('tong_tien_chu_viet', ''))}</strong></div>
        <div style="margin-top: 2px;">&bull; 金額大寫 (Tiếng Trung): <strong>{html.escape(data.get('tong_tien_chu_trung', ''))}</strong></div>
      </div>

      <!-- Bank Details -->
      <div class="dxyctt-bank-box">
        <div style="font-weight: 700; color: #1e3a8a; margin-bottom: 6px; font-size: 0.92rem;">THÔNG TIN TÀI KHOẢN THỤ HƯỞNG / 收款帳戶:</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.88rem;">
          <div>&bull; Tên chủ tài khoản: <strong>{html.escape(bank.get('ten_tai_khoan', ''))}</strong></div>
          <div>&bull; Số tài khoản: <strong style="font-family: monospace; font-size: 1.05em; color: #047857;">{html.escape(bank.get('so_tai_khoan', ''))}</strong></div>
          <div style="grid-column: span 2;">&bull; Ngân hàng: <strong>{html.escape(bank.get('ngan_hang', ''))}</strong></div>
        </div>
      </div>

      <!-- Signatures -->
      <div class="dxyctt-sign-row">
        <div class="dxyctt-sign-col">
          <div class="sign-title">ĐẠI DIỆN KHÁCH HÀNG / 客戶代表</div>
          <div class="sign-sub">(Ký và ghi rõ họ tên)</div>
          <div class="sign-space"></div>
          <div class="sign-name">Phòng Mua Hàng / Kế Toán</div>
        </div>
        <div class="dxyctt-sign-col">
          <div class="sign-title">ĐẠI DIỆN CÔNG TY HONG MING GLOBAL</div>
          <div class="sign-sub">(Ký tên và đóng dấu)</div>
          <div class="sign-space"></div>
          <div class="sign-name"><strong>TANG WEI LI</strong> (Tổng Giám Đốc)</div>
        </div>
      </div>
    </div>
    """
