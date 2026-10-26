# -*- coding: utf-8 -*-
"""
Receivables Executive Report Service.
Generates Word (.docx) and PowerPoint (.pptx) reports based on Executive Management principles:
1. Management by Exception: Exclude settled/paid items first to eliminate noise.
2. Executive Decision Viewpoint: Segment pending debt into mutually exclusive groups:
   - Must-collect items this week/month (bắt buộc phải thu - chưa quá hạn).
   - Contractual & warranty retention milestones (khoản tạm giữ theo tiến độ/nghiệm thu/bảo hành).
   - Overdue bottleneck & risk items (điểm nghẽn quá hạn/rủi ro).
   Directly answers the CEO's 3 key questions: Status? Risks? Next Action Plan?
3. Root Cause Analysis & Carry Forward: Clearly state why items are pending and schedule committed deadlines for next week.
4. Full Bilingual Standard: Vietnamese & Traditional Chinese (Tiếng Việt & 繁體中文) for all narrative and table content.
"""

import io
import math
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import docx
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

from pptx import Presentation
from pptx.dml.color import RGBColor as PptRGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches as PptInches, Pt as PptPt

from app.database import get_db_connection
from app.services.receivables_service import (
    format_currency_vn,
    list_receivables,
)


# ==============================================================================
# 1. DATA PREPARATION & SEGMENTATION LOGIC (MUTUALLY EXCLUSIVE & FILTER-AWARE)
# ==============================================================================

def format_bilingual_trigger_condition(item: Dict[str, Any]) -> str:
    """Return bilingual Vietnamese and Traditional Chinese trigger condition for retention items."""
    notes = str(item.get("notes") or "").strip()
    n_low = notes.lower()
    if "fac" in n_low and "60" in n_low:
        return "Ký biên bản nghiệm thu bàn giao (FAC), T/T 60 ngày\n簽署最終驗收移交書（FAC）後 T/T 60 天付款"
    if "fac" in n_low:
        return "Ký biên bản nghiệm thu bàn giao (FAC)\n簽署最終驗收移交確認書（FAC）"
    if "lắp đặt" in n_low or "chạy thử" in n_low:
        return "Hoàn thành lắp đặt, kiểm tra & chạy thử thiết bị\n完成設備安裝、測試及試運行驗收"
    if "60 ngày" in n_low or "t/t 60" in n_low:
        return "Thanh toán T/T 60 ngày theo tiến độ HĐ\n依合約進度 T/T 60 天付款"
    if "30 ngày" in n_low or "t/t 30" in n_low:
        return "Thanh toán T/T 30 ngày theo tiến độ HĐ\n依合約進度 T/T 30 天付款"
    return f"{notes or 'Ký biên bản nghiệm thu (FAC)'}\n完成合約階段驗收節點"


def get_contract_metadata_map() -> Dict[str, Dict[str, Any]]:
    """Retrieve mapping of contract code to bilingual metadata from SQLite contracts table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT contract_code, customer_name_vi, customer_name_zh, project_name_vi, project_name_zh FROM contracts")
        rows = cursor.fetchall()
        conn.close()
        return {str(r["contract_code"]).strip(): dict(r) for r in rows if r["contract_code"]}
    except Exception:
        return {}


def format_bilingual_customer_name(item: Dict[str, Any], contract_map: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    """Format bilingual Customer Name (Tiếng Việt & 繁體中文)."""
    cust_vi = str(item.get("customer_name") or "").strip()
    c_code = str(item.get("contract_code") or "").strip()
    c_meta = (contract_map.get(c_code) or {}) if (contract_map and c_code) else {}
    cust_zh = str(c_meta.get("customer_name_zh") or "").strip()

    if not cust_zh:
        c_low = cust_vi.lower()
        if "jinxun" in c_low or "kim tấn" in c_low or "kim tốn" in c_low:
            cust_zh = "越南金迅科技有限公司"
        elif "seiyo" in c_low or "chính dương" in c_low:
            cust_zh = "越南正揚有限責任公司"
        elif "cx technology" in c_low or "cxt" in c_low:
            cust_zh = "台灣中興電工 (CX Technology VN)"
        elif "vonmax" in c_low or "hoằng thanh" in c_low:
            cust_zh = "弘聲科技 (Vonmax VN)"
        elif "cheng feng" in c_low or "thừa phong" in c_low:
            cust_zh = "承豐樂華 (Cheng Feng Le Hua)"

    if cust_zh and cust_zh != cust_vi:
        return f"{cust_vi}\n{cust_zh}"
    return cust_vi or "-"


def format_bilingual_contract_and_project(item: Dict[str, Any], contract_map: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    """Format bilingual Contract Code, Milestone/Phase and Project Name."""
    c_code = str(item.get("contract_code") or "").strip()
    proj_raw = str(item.get("project_name") or "").strip()
    c_meta = (contract_map.get(c_code) or {}) if (contract_map and c_code) else {}

    phase_vi = ""
    phase_zh = ""
    remaining_proj = proj_raw
    m_phase = re.match(r"^(Đợt\s*(\d+)(?:\s*\(([^)]+)\))?)\s*[-:]?\s*(.*)$", proj_raw, re.IGNORECASE)
    if m_phase:
        phase_vi = m_phase.group(1).strip()
        phase_num = m_phase.group(2)
        phase_pct = m_phase.group(3)
        if phase_pct:
            phase_zh = f"第 {phase_num} 期 ({phase_pct})"
        else:
            phase_zh = f"第 {phase_num} 期"
        remaining_proj = m_phase.group(4).strip()

    p_vi = remaining_proj or str(c_meta.get("project_name_vi") or proj_raw).strip()
    p_zh = str(c_meta.get("project_name_zh") or "").strip()

    if not p_zh:
        p_low = p_vi.lower()
        if "mes" in p_low:
            p_zh = "MES Lite 系統"
        elif "seiyo" in p_low or "iiot" in p_low:
            p_zh = "SEIYO 正揚 廠區IIoT工業機聯網專案"
        elif "điện" in p_low or "ems" in p_low:
            p_zh = "綠電盾與電力監控系統"
        elif "sửa chữa" in p_low or "bảo trì" in p_low:
            p_zh = "設備維修與保養專案"
        else:
            p_zh = p_vi

    p_zh = p_zh.replace("專案報價單", "專案").strip()

    line_vi = f"{phase_vi} - {p_vi}" if phase_vi and p_vi else (phase_vi or p_vi or "-")
    line_zh = f"{phase_zh} - {p_zh}" if phase_zh and p_zh else (phase_zh or p_zh or "-")

    if c_code:
        return f"{c_code}\n{line_vi}\n{line_zh}"
    return f"{line_vi}\n{line_zh}"


def format_bilingual_project_only(item: Dict[str, Any], contract_map: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    """Format bilingual Milestone/Phase and Project Name without Contract Code prefix."""
    c_code = str(item.get("contract_code") or "").strip()
    proj_raw = str(item.get("project_name") or "").strip()
    c_meta = (contract_map.get(c_code) or {}) if (contract_map and c_code) else {}

    phase_vi = ""
    phase_zh = ""
    remaining_proj = proj_raw
    m_phase = re.match(r"^(Đợt\s*(\d+)(?:\s*\(([^)]+)\))?)\s*[-:]?\s*(.*)$", proj_raw, re.IGNORECASE)
    if m_phase:
        phase_vi = m_phase.group(1).strip()
        phase_num = m_phase.group(2)
        phase_pct = m_phase.group(3)
        if phase_pct:
            phase_zh = f"第 {phase_num} 期 ({phase_pct})"
        else:
            phase_zh = f"第 {phase_num} 期"
        remaining_proj = m_phase.group(4).strip()

    p_vi = remaining_proj or str(c_meta.get("project_name_vi") or proj_raw).strip()
    p_zh = str(c_meta.get("project_name_zh") or "").strip()

    if not p_zh:
        p_low = p_vi.lower()
        if "mes" in p_low:
            p_zh = "MES Lite 系統"
        elif "seiyo" in p_low or "iiot" in p_low:
            p_zh = "SEIYO 正揚 廠區IIoT工業機聯網專案"
        elif "điện" in p_low or "ems" in p_low:
            p_zh = "綠電盾與電力監控系統"
        else:
            p_zh = p_vi

    p_zh = p_zh.replace("專案報價單", "專案").strip()

    line_vi = f"{phase_vi} - {p_vi}" if phase_vi and p_vi else (phase_vi or p_vi or "-")
    line_zh = f"{phase_zh} - {p_zh}" if phase_zh and p_zh else (phase_zh or p_zh or "-")
    return f"{line_vi}\n{line_zh}"


def analyze_root_cause_and_carry_forward(item: Dict[str, Any]) -> Dict[str, str]:
    """
    Formulate bilingual root cause category, explanation, carry forward target date, and action plan.
    Returns a dict with Vietnamese and Traditional Chinese fields.
    """
    notes = str(item.get("notes") or "").strip()
    status = item.get("collection_status") or "PENDING"
    due_date = item.get("due_date")
    promised_date = item.get("customer_promised_date")
    proj_name = item.get("project_name") or ""
    days_left = item.get("days_left")

    today = datetime.now().date()
    days_to_tue = (1 - today.weekday()) % 7
    if days_to_tue <= 0:
        days_to_tue += 7
    default_carry_date = (today + timedelta(days=days_to_tue)).strftime("%Y-%m-%d")

    is_overdue = (status == "DELAYED") or (days_left is not None and days_left < 0)
    is_fac_retention = ("fac" in notes.lower() or "đợt 3" in proj_name.lower() or "bảo hành" in notes.lower()) and not is_overdue
    is_progress_retention = ("đợt 2" in proj_name.lower() or "nghiệm thu" in notes.lower() or "chạy thử" in notes.lower()) and not is_overdue

    # 1. Overdue Bottleneck (Quá hạn)
    if is_overdue:
        cat_vi = "Phía Khách hàng (Quy trình duyệt chi chậm)"
        cat_zh = "客戶端（內部審批與撥款延誤）"

        note_addon_vi = f" (Chi tiết: {notes})" if notes and notes != "-" else ""
        if days_left is not None and days_left < 0:
            overdue_days = abs(days_left)
            rc_vi = f"Khoản nợ đã trễ hạn {overdue_days} ngày. Khách hàng chậm xử lý thủ tục đối chiếu và phê duyệt dòng tiền nội bộ.{note_addon_vi}"
            rc_zh = f"帳款已逾期 {overdue_days} 天。客戶內部請款審核及資金調度流程延宕，需加速催收。"
        else:
            rc_vi = f"Khoản nợ đang bị chậm tiến độ thanh toán so với cam kết. Khách hàng chậm xử lý thủ tục phê duyệt nội bộ.{note_addon_vi}"
            rc_zh = "款項支付進度延誤。客戶內部請款審核及資金調度流程延宕，需重點跟進。"

        target_vi = f"Ưu tiên dứt điểm tuần tới ({default_carry_date})"
        target_zh = f"下週優先結清（{default_carry_date}）"

        act_vi = "PM phối hợp Kinh doanh làm việc trực tiếp với Kế toán trưởng đối tác; phát hành Công văn nhắc nợ chính thức."
        act_zh = "PM 協同業務主管直接聯繫客戶財務主管催款，發送正式催款公文。"

    # 2. Customer has a confirmed promised date
    elif promised_date:
        cat_vi = "Phía Khách hàng (Đã chốt lịch hẹn)"
        cat_zh = "客戶端（已確認預定付款日）"

        rc_vi = f"Khách hàng đã nhận đủ chứng từ hợp lệ; đang làm thủ tục giải ngân nội bộ và hẹn thanh toán ngày {promised_date}."
        rc_zh = f"客戶已收訖憑證，正進行內部出納審批，預定於 {promised_date} 支付。"

        target_vi = f"Đúng ngày hẹn: {promised_date}"
        target_zh = f"依約定日期：{promised_date}"

        act_vi = f"Theo dõi dòng tiền vào tài khoản ngày {promised_date}; liên hệ kế toán đối tác nhận Ủy nhiệm chi (UNC)."
        act_zh = f"於 {promised_date} 追蹤銀行入帳，聯繫對方出納索取匯款單據（UNC）。"

    # 3. Retention based on FAC or Warranty (10% giữ lại / bảo hành)
    elif is_fac_retention:
        cat_vi = "Kỹ thuật & Nghiệm thu (Theo tiến độ FAC)"
        cat_zh = "工程技術與驗收（依FAC進度款）"

        rc_vi = "Khoản giữ lại theo hợp đồng: Chờ hoàn thành nghiệm thu bàn giao toàn diện (FAC) để kích hoạt thanh toán."
        rc_zh = "合約進度保留款（10%或保固款）：待完成最終驗收移交確認書（FAC）簽署後請款。"

        target_vi = "Theo tiến độ ký FAC"
        target_zh = "依現場 FAC 簽署進度"

        act_vi = "Đôn đốc kỹ sư hiện trường hoàn thiện hồ sơ kỹ thuật, phối hợp khách hàng ký biên bản FAC."
        act_zh = "督促現場工程團隊備齊技術資料，協調客戶簽署 FAC 驗收書。"

    # 4. Progress-based Retention (Đợt 2 thi công/lắp đặt)
    elif is_progress_retention:
        cat_vi = "Kỹ thuật & Nghiệm thu (Theo tiến độ thi công)"
        cat_zh = "工程技術與驗收（依施工進度款）"

        rc_vi = "Khoản thanh toán giai đoạn thi công: Chờ hoàn tất lắp đặt, chạy thử nghiệm thu thiết bị tại hiện trường."
        rc_zh = "工程期款：待設備安裝、調試與試運行驗收完成後請款。"

        target_vi = "Theo tiến độ thi công"
        target_zh = "依現場施工進度"

        act_vi = "Kiểm tra tiến độ kỹ thuật tại nhà máy, chuẩn bị sẵn hồ sơ chứng từ thanh toán đợt tiếp theo."
        act_zh = "掌握廠端工程進度，預先備妥下一期請款憑證。"

    # 5. Cycle T/T terms
    elif "t/t" in notes.lower() or "60 ngày" in notes.lower() or "30 ngày" in notes.lower():
        cat_vi = "Quy trình Hợp đồng (Chu kỳ tín dụng T/T)"
        cat_zh = "合約帳期流程（T/T 信用期）"

        rc_vi = f"Khoản thanh toán đang trong chu kỳ tín dụng thương mại T/T theo điều khoản hợp đồng ({notes})."
        rc_zh = "款項處於合約約定之 T/T 商業信用結算週期內，依合約規範推進。"

        target_vi = f"Trước hạn thanh toán ({due_date or default_carry_date})"
        target_zh = f"付款到期日前（{due_date or default_carry_date}）"

        act_vi = "Kiểm tra trước hạn 5 ngày với kế toán đối tác để bảo đảm hồ sơ đã được trình ký phê duyệt thanh toán."
        act_zh = "於到期日前 5 天與對方會計對帳，確保請款單已送交主管審批。"

    # 6. Default Pending
    else:
        cat_vi = "Hồ sơ & Chứng từ (Đang theo dõi)"
        cat_zh = "憑證與請款作業（追蹤中）"

        rc_vi = f"Đang rà soát và theo dõi tiến độ thực hiện: {notes}" if notes and notes != "-" else "Đang rà soát và theo dõi tiến độ thực hiện hợp đồng, chuẩn bị thủ tục đối chiếu công nợ."
        rc_zh = "正持續追蹤專案履約進度，準備對帳與請款憑證作業。"

        target_vi = f"Tuần tới ({default_carry_date})"
        target_zh = f"下週排程（{default_carry_date}）"

        act_vi = "Cập nhật tiến độ dự án, liên hệ bộ phận mua hàng/kế toán đối tác để thống nhất thời gian thanh toán."
        act_zh = "更新專案進度，聯繫客戶採購/出納確認付款排程。"

    return {
        "cat_vi": cat_vi,
        "cat_zh": cat_zh,
        "root_cause_vi": rc_vi,
        "root_cause_zh": rc_zh,
        "target_date_vi": target_vi,
        "target_date_zh": target_zh,
        "action_plan_vi": act_vi,
        "action_plan_zh": act_zh,
        "trigger_condition_bilingual": format_bilingual_trigger_condition(item),
    }


def compute_filtered_stats(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute KPI statistics directly on the filtered items list."""
    total_receivable = sum(float(x.get("gross_amount") or 0.0) for x in items)
    total_received = sum(float(x.get("received_amount") or 0.0) for x in items)
    total_debt = sum(float(x.get("remaining_debt") or 0.0) for x in items)
    completion_rate = (total_received / total_receivable * 100) if total_receivable > 0 else 0.0

    overdue_count = 0
    urgent_count = 0
    paid_count = 0
    pending_count = 0

    for x in items:
        st = x.get("collection_status") or "PENDING"
        days = x.get("days_left")
        gross = float(x.get("gross_amount") or 0.0)
        rec = float(x.get("received_amount") or 0.0)
        rem = float(x.get("remaining_debt") or 0.0)

        if st == "PAID" or (gross > 0 and rec >= gross and rem <= 0):
            paid_count += 1
        elif st == "DELAYED" or (days is not None and days < 0):
            overdue_count += 1
        elif st == "URGENT" or (days is not None and 0 <= days <= 7):
            urgent_count += 1
        else:
            pending_count += 1

    return {
        "total_receivable": total_receivable,
        "total_received": total_received,
        "total_debt": total_debt,
        "completion_rate": round(completion_rate, 2),
        "total_count": len(items),
        "paid_count": paid_count,
        "overdue_count": overdue_count,
        "urgent_count": urgent_count,
        "pending_count": pending_count,
    }


def prepare_receivables_management_data(
    customer: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    overdue_only: bool = False,
) -> Dict[str, Any]:
    """
    Structure receivables into mutually exclusive management tiers fulfilling Boss's 3 rules.
    1. Completed items (PAID) - excluded from active bottlenecks.
    2. Must-collect items (Pending & Urgent / Promised - NOT overdue).
    3. Retention items (Pending & Milestones/FAC - NOT overdue).
    4. Overdue bottleneck & risk items (Overdue).
    Sum of 2 + 3 + 4 equals total_unpaid_amount exactly.
    """
    all_items = list_receivables(customer=customer, status=status, search=search, overdue_only=overdue_only)
    stats = compute_filtered_stats(all_items)
    contract_map = get_contract_metadata_map()

    enriched_items = []
    for raw_item in all_items:
        it = dict(raw_item)
        it["customer_bilingual"] = format_bilingual_customer_name(it, contract_map)
        it["contract_project_bilingual"] = format_bilingual_contract_and_project(it, contract_map)
        it["project_bilingual"] = format_bilingual_project_only(it, contract_map)
        it["trigger_condition_bilingual"] = format_bilingual_trigger_condition(it)
        enriched_items.append(it)

    completed_items = []
    unpaid_items = []

    for item in enriched_items:
        gross = float(item.get("gross_amount") or 0.0)
        rec = float(item.get("received_amount") or 0.0)
        rem = float(item.get("remaining_debt") or 0.0)
        st = item.get("collection_status") or "PENDING"

        is_completed = (st == "PAID") or (gross > 0 and rec >= gross and rem <= 0)
        if is_completed:
            completed_items.append(item)
        else:
            unpaid_items.append(item)

    # Mutually Exclusive Partitioning for Unpaid Items:
    # Group A: Overdue items (Quá hạn)
    # Group B: Retention items (Tạm giữ theo tiến độ / nghiệm thu FAC / bảo hành - chưa quá hạn)
    # Group C: Must Collect items (Đến hạn / Khách hứa / Đợt cần thu tuần này - chưa quá hạn)
    must_collect_items = []
    retention_items = []
    overdue_risk_items = []
    carry_forward_items = []

    for item in unpaid_items:
        analysis = analyze_root_cause_and_carry_forward(item)
        enhanced_item = dict(item)
        enhanced_item.update(analysis)
        enhanced_item["pic_vi"] = "PM Nguyễn Sỹ Kim Bằng"
        enhanced_item["pic_zh"] = "專案經理 阮士金榜（PM 團隊）"

        st = item.get("collection_status") or "PENDING"
        notes = str(item.get("notes") or "").lower()
        proj = str(item.get("project_name") or "").lower()
        days_left = item.get("days_left")

        is_overdue = (st == "DELAYED") or (days_left is not None and days_left < 0)
        is_retention = ("fac" in notes or "nghiệm thu" in notes or "bảo hành" in notes or "đợt 3" in proj or "đợt 2" in proj) and not is_overdue

        # STRICT MUTUALLY EXCLUSIVE CLASSIFICATION
        if is_overdue:
            overdue_risk_items.append(enhanced_item)
        elif is_retention:
            retention_items.append(enhanced_item)
        else:
            must_collect_items.append(enhanced_item)

        carry_forward_items.append(enhanced_item)

    # Verify Disjoint Partition: Must Collect + Retention + Overdue == Unpaid
    total_completed_amount = sum(float(x.get("received_amount") or 0.0) for x in completed_items)
    total_unpaid_amount = sum(float(x.get("remaining_debt") or 0.0) for x in unpaid_items)
    total_must_collect_amount = sum(float(x.get("remaining_debt") or 0.0) for x in must_collect_items)
    total_retention_amount = sum(float(x.get("remaining_debt") or 0.0) for x in retention_items)
    total_overdue_amount = sum(float(x.get("remaining_debt") or 0.0) for x in overdue_risk_items)

    today_str = datetime.now().strftime("%d/%m/%Y")
    now_time_str = datetime.now().strftime("%H:%M")

    filter_desc_vi = f"Khách hàng: {customer}" if customer else "Toàn bộ danh mục đối tác"
    filter_desc_zh = f"篩選客戶：{customer}" if customer else "全體合作客戶清單"

    return {
        "report_date": today_str,
        "report_time": now_time_str,
        "reporter": "PM Nguyễn Sỹ Kim Bằng (阮士金榜 / PM Team)",
        "approver": "Tổng Giám Đốc Tang Wei Li (唐偉力 總經理)",
        "company_vi": "CÔNG TY TNHH TOÀN CẦU HONG MING",
        "company_zh": "宏明環球有限公司",
        "filter_desc_vi": filter_desc_vi,
        "filter_desc_zh": filter_desc_zh,
        "stats": stats,
        "completed_items": completed_items,
        "unpaid_items": unpaid_items,
        "must_collect_items": must_collect_items,
        "retention_items": retention_items,
        "overdue_risk_items": overdue_risk_items,
        "carry_forward_items": carry_forward_items,
        "total_completed_amount": total_completed_amount,
        "total_unpaid_amount": total_unpaid_amount,
        "total_must_collect_amount": total_must_collect_amount,
        "total_retention_amount": total_retention_amount,
        "total_overdue_amount": total_overdue_amount,
    }


# ==============================================================================
# 2. WORD (.DOCX) GENERATOR SERVICE (BILINGUAL, BORDERED & FIXED WIDTHS)
# ==============================================================================

def set_cell_background(cell, color_hex: str):
    """Set background color for a docx cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)


def set_cell_padding(cell, top=80, bottom=80, left=100, right=100):
    """Set cell padding in dxa."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    """Apply crisp subtle border grid to a docx table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def set_table_col_widths(table, col_widths_in_inches: List[float]):
    """Set strict explicit width on table columns and their cells."""
    for col_idx, col in enumerate(table.columns):
        if col_idx < len(col_widths_in_inches):
            w = Inches(col_widths_in_inches[col_idx])
            col.width = w
            for cell in col.cells:
                cell.width = w


def add_table_row_cells(
    table,
    row_idx: int,
    texts: List[str],
    alignments: List[WD_ALIGN_PARAGRAPH],
    font_size=8.5,
    bold=False,
    bg_hex=None,
    text_color_rgb=None,
):
    """Format row cells in docx table with font consistency."""
    row = table.rows[row_idx]
    for c_idx, text in enumerate(texts):
        cell = row.cells[c_idx]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = alignments[c_idx] if c_idx < len(alignments) else WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15

        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
        r.font.size = Pt(font_size)
        r.bold = bold
        if text_color_rgb:
            r.font.color.rgb = text_color_rgb

        if bg_hex:
            set_cell_background(cell, bg_hex)
        set_cell_padding(cell, top=70, bottom=70, left=90, right=90)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def generate_receivables_word_report(data: Dict[str, Any]) -> bytes:
    """Generate professional executive Word report (.docx) conforming to Boss's 3 rules and bilingual standard."""
    doc = Document()

    # Standard A4 Portrait (8.27 in x 11.69 in). Margins: 0.7 in on each side. Usable width = 6.87 in.
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    # 1. Header & Title Block
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_c1 = p_comp.add_run(f"{data['company_vi']} / {data['company_zh']}\n")
    r_c1.font.name = "Times New Roman"
    r_c1._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_c1.font.size = Pt(11)
    r_c1.bold = True
    r_c1.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t1 = p_title.add_run("BÁO CÁO ĐIỀU HÀNH CÔNG NỢ DỰ ÁN & QUẢN TRỊ DÒNG TIỀN PHẢI THU\n")
    r_t1.font.name = "Times New Roman"
    r_t1.font.size = Pt(14)
    r_t1.bold = True
    r_t1.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    r_t2 = p_title.add_run("專案應收帳款管理、資金流向與卡點決策週報\n")
    r_t2.font.name = "Times New Roman"
    r_t2._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_t2.font.size = Pt(11.5)
    r_t2.bold = True
    r_t2.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    r_t3 = p_title.add_run(f"Ngày lập / 製表日期: {data['report_date']} ({data['report_time']}) · Người lập / 製表人: {data['reporter']} · {data['filter_desc_vi']}")
    r_t3.font.name = "Times New Roman"
    r_t3._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_t3.font.size = Pt(9)
    r_t3.italic = True
    r_t3.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    # Divider line
    p_div = doc.add_paragraph()
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_div.paragraph_format.space_before = Pt(2)
    p_div.paragraph_format.space_after = Pt(6)
    r_d = p_div.add_run("─────────────────────────────────────────────────────────────")
    r_d.font.size = Pt(8)
    r_d.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    # 3. KPI Summary Table (Filter-aware)
    stats = data["stats"]
    p_kpi_head = doc.add_paragraph()
    p_kpi_head.paragraph_format.space_before = Pt(6)
    p_kpi_head.paragraph_format.space_after = Pt(3)
    r_kh = p_kpi_head.add_run("BẢNG TỔNG HỢP CHỈ SỐ KPI DÒNG TIỀN / 財務與資金總覽")
    r_kh.bold = True
    r_kh.font.name = "Times New Roman"
    r_kh._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_kh.font.size = Pt(10.5)
    r_kh.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    kpi_table = doc.add_table(rows=2, cols=4)
    kpi_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(kpi_table, color="CBD5E1")
    set_table_col_widths(kpi_table, [1.71, 1.72, 1.72, 1.72])

    kpi_headers = [
        "Tổng Công Nợ\n應收總額",
        "Đã Thu Hồi Về TK\n已收回金額",
        "Còn Phải Thu (Dư Nợ)\n尚欠尾款 (未收)",
        "Cảnh Báo Quá Hạn\n逾期與緊急催收",
    ]
    add_table_row_cells(kpi_table, 0, kpi_headers, [WD_ALIGN_PARAGRAPH.CENTER] * 4, font_size=8.5, bold=True, bg_hex="1F4E79", text_color_rgb=RGBColor(0xFF, 0xFF, 0xFF))

    kpi_values = [
        format_currency_vn(stats.get("total_receivable", 0.0)),
        f"{format_currency_vn(stats.get('total_received', 0.0))}\n({stats.get('completion_rate', 0.0):.1f}%)",
        format_currency_vn(stats.get("total_debt", 0.0)),
        f"{stats.get('overdue_count', 0)} đợt quá hạn\n({stats.get('urgent_count', 0)} đợt sắp đến hạn)",
    ]
    add_table_row_cells(kpi_table, 1, kpi_values, [WD_ALIGN_PARAGRAPH.CENTER] * 4, font_size=9.5, bold=True, bg_hex="F1F5F9", text_color_rgb=RGBColor(0x0F, 0x17, 0x2A))

    # 4. PART 1: SETTLED ITEMS (EXCLUDED FIRST)
    p_p1 = doc.add_paragraph()
    p_p1.paragraph_format.space_before = Pt(10)
    p_p1.paragraph_format.space_after = Pt(2)
    r_p1 = p_p1.add_run("PHẦN 1: CÁC KHOẢN ĐÃ XÁC NHẬN THU TIỀN XONG (LOẠI TRỪ KHỎI DIỆN NGHẼN - 已結清項目)")
    r_p1.bold = True
    r_p1.font.name = "Times New Roman"
    r_p1._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_p1.font.size = Pt(10.5)
    r_p1.font.color.rgb = RGBColor(0x05, 0x96, 0x69)

    p_p1_note = doc.add_paragraph()
    p_p1_note.paragraph_format.space_after = Pt(4)
    r_p1_n = p_p1_note.add_run(
        f"✓ Đã hoàn tất đối chiếu và thu đủ 100% về tài khoản công ty. "
        f"Tổng cộng: {len(data['completed_items'])} khoản — Số tiền đã thu: {format_currency_vn(data['total_completed_amount'])}. "
        f"（全額收訖結清，排除在卡點名單之外，不佔用催收資源）。"
    )
    r_p1_n.font.name = "Times New Roman"
    r_p1_n._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_p1_n.font.size = Pt(8.5)
    r_p1_n.italic = True
    r_p1_n.font.color.rgb = RGBColor(0x05, 0x96, 0x69)

    if data["completed_items"]:
        t1 = doc.add_table(rows=len(data["completed_items"]) + 1, cols=6)
        t1.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(t1, color="A7F3D0")
        set_table_col_widths(t1, [0.5, 1.1, 1.6, 1.7, 1.2, 0.77])
        h1 = ["STT\n序號", "Mã HĐ / PO\n合約編號", "Khách Hàng\n客戶名稱", "Dự Án & Đợt Thanh Toán\n專案與期款", "Số Tiền Đã Thu\n已收金額", "Ngày Thu\n收款日"]
        add_table_row_cells(t1, 0, h1, [WD_ALIGN_PARAGRAPH.CENTER] * 6, font_size=8, bold=True, bg_hex="059669", text_color_rgb=RGBColor(0xFF, 0xFF, 0xFF))
        for idx, item in enumerate(data["completed_items"], start=1):
            row_texts = [
                str(idx),
                str(item.get("contract_code") or "-"),
                str(item.get("customer_bilingual") or item.get("customer_name") or "-"),
                str(item.get("project_bilingual") or item.get("project_name") or "-"),
                format_currency_vn(float(item.get("received_amount") or 0.0)),
                str(item.get("paid_date") or item.get("due_date") or "Đã thu"),
            ]
            add_table_row_cells(t1, idx, row_texts, [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.CENTER], font_size=8, bg_hex="F0FDF4" if idx % 2 == 1 else "FFFFFF")

    # 5. PART 2: EXECUTIVE FOCUS ON UNPAID ITEMS (MUTUALLY EXCLUSIVE)
    p_p2 = doc.add_paragraph()
    p_p2.paragraph_format.space_before = Pt(12)
    p_p2.paragraph_format.space_after = Pt(2)
    r_p2 = p_p2.add_run(
        f"PHẦN 2: TRỌNG TÂM CÔNG NỢ ĐANG THEO DÕI & ĐIỂM NGHẼN (未收款項深度分析)\n"
        f"Tổng dư nợ đang theo dõi: {format_currency_vn(data['total_unpaid_amount'])} "
        f"= [Mục 2.1: {format_currency_vn(data['total_must_collect_amount'])}] "
        f"+ [Mục 2.2: {format_currency_vn(data['total_retention_amount'])}] "
        f"+ [Mục 2.3: {format_currency_vn(data['total_overdue_amount'])}] (Khớp 100% không trùng lặp)"
    )
    r_p2.bold = True
    r_p2.font.name = "Times New Roman"
    r_p2._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_p2.font.size = Pt(10)
    r_p2.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    # 2.1 MUST COLLECT THIS WEEK / MONTH (NOT OVERDUE)
    p_21 = doc.add_paragraph()
    p_21.paragraph_format.space_before = Pt(6)
    p_21.paragraph_format.space_after = Pt(2)
    r_21 = p_21.add_run(f"2.1. Các khoản BẮT BUỘC / CHẮC CHẮN PHẢI THU trong tuần/tháng này (本週/月重點必收項目 - Chưa quá hạn): {len(data['must_collect_items'])} khoản — {format_currency_vn(data['total_must_collect_amount'])}")
    r_21.bold = True
    r_21.font.name = "Times New Roman"
    r_21._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_21.font.size = Pt(9.5)
    r_21.font.color.rgb = RGBColor(0xB4, 0x53, 0x09)

    if data["must_collect_items"]:
        t21 = doc.add_table(rows=len(data["must_collect_items"]) + 1, cols=6)
        t21.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(t21, color="FDE68A")
        set_table_col_widths(t21, [0.45, 1.5, 1.5, 1.1, 0.9, 1.42])
        h21 = ["STT\n序號", "Khách Hàng\n客戶名稱", "Hợp Đồng & Đợt\n合約與期款", "Số Tiền Phải Thu\n應收金額", "Hạn / Ngày Hẹn\n到期/預定日", "Kế Hoạch Đôn Đốc\n催收行動方案"]
        add_table_row_cells(t21, 0, h21, [WD_ALIGN_PARAGRAPH.CENTER] * 6, font_size=8, bold=True, bg_hex="D97706", text_color_rgb=RGBColor(0xFF, 0xFF, 0xFF))
        for idx, item in enumerate(data["must_collect_items"], start=1):
            target_str = str(item.get("customer_promised_date") or item.get("due_date") or "Trong tuần")
            row_texts = [
                str(idx),
                str(item.get("customer_bilingual") or item.get("customer_name") or "-"),
                str(item.get("contract_project_bilingual") or "-"),
                format_currency_vn(float(item.get("remaining_debt") or 0.0)),
                target_str,
                f"{item.get('action_plan_vi')}\n{item.get('action_plan_zh')}",
            ]
            add_table_row_cells(t21, idx, row_texts, [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT], font_size=8, bg_hex="FFFBEB" if idx % 2 == 1 else "FFFFFF")
    else:
        p_empty21 = doc.add_paragraph("Không có khoản cấp bách chưa quá hạn nào cần thu gấp trong tuần này.")
        p_empty21.paragraph_format.space_after = Pt(2)

    # 2.2 RETENTION / PROGRESS-BASED ITEMS
    p_22 = doc.add_paragraph()
    p_22.paragraph_format.space_before = Pt(6)
    p_22.paragraph_format.space_after = Pt(2)
    r_22 = p_22.add_run(f"2.2. Các khoản TẠM GIỮ THEO TIẾN ĐỘ HỢP ĐỒNG & BẢO HÀNH (依合約進度/保固保留款): {len(data['retention_items'])} khoản — {format_currency_vn(data['total_retention_amount'])}")
    r_22.bold = True
    r_22.font.name = "Times New Roman"
    r_22._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_22.font.size = Pt(9.5)
    r_22.font.color.rgb = RGBColor(0x25, 0x63, 0xEB)

    if data["retention_items"]:
        t22 = doc.add_table(rows=len(data["retention_items"]) + 1, cols=6)
        t22.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(t22, color="BFDBFE")
        set_table_col_widths(t22, [0.45, 1.5, 1.5, 1.1, 1.1, 1.22])
        h22 = ["STT\n序號", "Khách Hàng\n客戶名稱", "Hợp Đồng & Dự Án\n合約與專案", "Số Tiền Tạm Giữ\n保留金額", "Điều Kiện Kích Hoạt\n請款觸發條件", "Lý Do Chưa Thu\n未收原因說明"]
        add_table_row_cells(t22, 0, h22, [WD_ALIGN_PARAGRAPH.CENTER] * 6, font_size=8, bold=True, bg_hex="2563EB", text_color_rgb=RGBColor(0xFF, 0xFF, 0xFF))
        for idx, item in enumerate(data["retention_items"], start=1):
            row_texts = [
                str(idx),
                str(item.get("customer_bilingual") or item.get("customer_name") or "-"),
                str(item.get("contract_project_bilingual") or "-"),
                format_currency_vn(float(item.get("remaining_debt") or 0.0)),
                str(item.get("trigger_condition_bilingual") or "Ký biên bản nghiệm thu (FAC)\n簽署最終驗收移交書"),
                f"Đang thực hiện đúng tiến độ HĐ.\n合約正常履約中，待達到請款節點。",
            ]
            add_table_row_cells(t22, idx, row_texts, [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT], font_size=8, bg_hex="EFF6FF" if idx % 2 == 1 else "FFFFFF")
    else:
        p_empty22 = doc.add_paragraph("Không có khoản tạm giữ theo tiến độ.")
        p_empty22.paragraph_format.space_after = Pt(2)

    # 2.3 OVERDUE / BOTTLENECK / RISK ITEMS
    p_23 = doc.add_paragraph()
    p_23.paragraph_format.space_before = Pt(6)
    p_23.paragraph_format.space_after = Pt(2)
    r_23 = p_23.add_run(f"2.3. Các khoản QUÁ HẠN / ĐIỂM NGHẼN & NGUY CƠ RỦI RO (已逾期卡點與風險項目): {len(data['overdue_risk_items'])} khoản — {format_currency_vn(data['total_overdue_amount'])}")
    r_23.bold = True
    r_23.font.name = "Times New Roman"
    r_23._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_23.font.size = Pt(9.5)
    r_23.font.color.rgb = RGBColor(0xDC, 0x26, 0x26)

    if data["overdue_risk_items"]:
        t23 = doc.add_table(rows=len(data["overdue_risk_items"]) + 1, cols=6)
        t23.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(t23, color="FECACA")
        set_table_col_widths(t23, [0.45, 1.5, 1.5, 1.1, 0.9, 1.42])
        h23 = ["STT\n序號", "Khách Hàng\n客戶名稱", "Mã HĐ & Đợt\n合約與期款", "Số Tiền Nghẽn\n逾期金額", "Quá Hạn\n逾期天數", "Đánh Giá Rủi Ro & Biện Pháp\n風險評估與應對措施"]
        add_table_row_cells(t23, 0, h23, [WD_ALIGN_PARAGRAPH.CENTER] * 6, font_size=8, bold=True, bg_hex="DC2626", text_color_rgb=RGBColor(0xFF, 0xFF, 0xFF))
        for idx, item in enumerate(data["overdue_risk_items"], start=1):
            days_left = item.get("days_left")
            if days_left is not None and days_left < 0:
                overdue_days_str = f"Trễ {abs(days_left)} ngày\n逾期 {abs(days_left)} 天"
            else:
                overdue_days_str = "Chậm tiến độ\n付款進度延誤"
            row_texts = [
                str(idx),
                str(item.get("customer_bilingual") or item.get("customer_name") or "-"),
                str(item.get("contract_project_bilingual") or "-"),
                format_currency_vn(float(item.get("remaining_debt") or 0.0)),
                overdue_days_str,
                f"{item.get('action_plan_vi')}\n{item.get('action_plan_zh')}",
            ]
            add_table_row_cells(t23, idx, row_texts, [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT], font_size=8, bg_hex="FEF2F2" if idx % 2 == 1 else "FFFFFF")
    else:
        p_empty23 = doc.add_paragraph("✓ Hiện tại không có khoản công nợ nào bị trễ hạn quá mức kiểm soát（無重大逾期風險）.")
        p_empty23.paragraph_format.space_after = Pt(2)

    # 6. PART 3: ROOT CAUSE ANALYSIS & CARRY FORWARD TO NEXT WEEK (BILINGUAL)
    p_p3 = doc.add_paragraph()
    p_p3.paragraph_format.space_before = Pt(12)
    p_p3.paragraph_format.space_after = Pt(2)
    r_p3 = p_p3.add_run("PHẦN 3: BẢNG PHÂN TÍCH NGUYÊN NHÂN GỐC RỄ & CARRY FORWARD SANG TUẦN TIẾP THEO (卡點原因分析與下週轉移計畫)")
    r_p3.bold = True
    r_p3.font.name = "Times New Roman"
    r_p3._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_p3.font.size = Pt(10.5)
    r_p3.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    p_p3_note = doc.add_paragraph()
    p_p3_note.paragraph_format.space_after = Pt(4)
    r_p3_n = p_p3_note.add_run(
        "Kế hoạch hành động cụ thể và cam kết thời hạn dứt điểm cho các khoản công nợ đang theo dõi "
        "（各項未結清款項之歸因分析與下週具體承諾執行方案）。"
    )
    r_p3_n.font.name = "Times New Roman"
    r_p3_n._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_p3_n.font.size = Pt(8.5)
    r_p3_n.bold = True
    r_p3_n.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    if data["carry_forward_items"]:
        t3 = doc.add_table(rows=len(data["carry_forward_items"]) + 1, cols=6)
        t3.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(t3, color="CBD5E1")
        set_table_col_widths(t3, [0.45, 1.5, 1.05, 1.75, 0.85, 1.27])
        h3 = [
            "STT\n序號",
            "Mã HĐ & Khách Hàng\n客戶與合約",
            "Dư Nợ Còn Lại\n剩餘尾款",
            "Nguyên Nhân Gốc Rễ Chưa Thu\n未收款根本原因",
            "Cam Kết Tuần Tới\n下週承諾期限",
            "Kế Hoạch Dứt Điểm\n下週執行方案",
        ]
        add_table_row_cells(t3, 0, h3, [WD_ALIGN_PARAGRAPH.CENTER] * 6, font_size=8, bold=True, bg_hex="1F4E79", text_color_rgb=RGBColor(0xFF, 0xFF, 0xFF))
        for idx, item in enumerate(data["carry_forward_items"], start=1):
            row_texts = [
                str(idx),
                f"{item.get('customer_bilingual') or item.get('customer_name') or '-'}\n({item.get('contract_code') or '-'})",
                format_currency_vn(float(item.get("remaining_debt") or 0.0)),
                f"[{item.get('cat_vi')} / {item.get('cat_zh')}]\n{item.get('root_cause_vi')}\n{item.get('root_cause_zh')}",
                f"{item.get('target_date_vi')}\n{item.get('target_date_zh')}",
                f"{item.get('action_plan_vi')}\n{item.get('action_plan_zh')}",
            ]
            add_table_row_cells(t3, idx, row_texts, [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT], font_size=8, bg_hex="F8FAFC" if idx % 2 == 1 else "FFFFFF")

    # 7. PART 4: EXECUTIVE DECISION SUMMARY (ANSWERS TO CEO'S 3 QUESTIONS IN BILINGUAL) & SIGNATURES
    p_p4 = doc.add_paragraph()
    p_p4.paragraph_format.space_before = Pt(12)
    p_p4.paragraph_format.space_after = Pt(2)
    r_p4 = p_p4.add_run("PHẦN 4: TỔNG KẾT ĐIỀU HÀNH & ĐỀ XUẤT HÀNH ĐỘNG CHO TỔNG GIÁM ĐỐC (領導決策與三問核心解答)")
    r_p4.bold = True
    r_p4.font.name = "Times New Roman"
    r_p4._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    r_p4.font.size = Pt(10.5)
    r_p4.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    # Q1
    p_q1 = doc.add_paragraph()
    p_q1.paragraph_format.space_after = Pt(2)
    rq1_t = p_q1.add_run("1. Hiện trạng là gì? / 現況說明：\n")
    rq1_t.bold = True
    rq1_t.font.name = "Times New Roman"
    rq1_t._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    rq1_t.font.size = Pt(9.5)
    rq1_b = p_q1.add_run(
        f"• Tiếng Việt: Tổng công nợ danh mục là {format_currency_vn(stats.get('total_receivable', 0.0))}, đã thu hồi dứt điểm {format_currency_vn(data['total_completed_amount'])} "
        f"(chiếm {stats.get('completion_rate', 0.0):.1f}%). Dư nợ đang kiểm soát là {format_currency_vn(data['total_unpaid_amount'])}, trong đó nhóm bắt buộc thu tuần này là {format_currency_vn(data['total_must_collect_amount'])}.\n"
        f"• 繁體中文：本期應收帳款總額為 {format_currency_vn(stats.get('total_receivable', 0.0))}，已全額收訖結清 {format_currency_vn(data['total_completed_amount'])} "
        f"（資金回收率 {stats.get('completion_rate', 0.0):.1f}%）。尚待管理之未收尾款為 {format_currency_vn(data['total_unpaid_amount'])}，其中本週重點必收款項為 {format_currency_vn(data['total_must_collect_amount'])}。"
    )
    rq1_b.font.name = "Times New Roman"
    rq1_b._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    rq1_b.font.size = Pt(8.5)

    # Q2
    p_q2 = doc.add_paragraph()
    p_q2.paragraph_format.space_after = Pt(2)
    rq2_t = p_q2.add_run("2. Điểm rủi ro nằm ở đâu? / 風險卡點：\n")
    rq2_t.bold = True
    rq2_t.font.name = "Times New Roman"
    rq2_t._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    rq2_t.font.size = Pt(9.5)
    rq2_b = p_q2.add_run(
        f"• Tiếng Việt: Có {len(data['overdue_risk_items'])} khoản nợ quá hạn với tổng giá trị {format_currency_vn(data['total_overdue_amount'])}. "
        f"Điểm nghẽn rủi ro chính do quy trình luân chuyển chứng từ nội bộ của khách hàng chậm trễ. Nhóm tạm giữ theo tiến độ có {len(data['retention_items'])} khoản ({format_currency_vn(data['total_retention_amount'])}) đang chờ hoàn tất nghiệm thu kỹ thuật (FAC) tại nhà máy.\n"
        f"• 繁體中文：清單中共有 {len(data['overdue_risk_items'])} 筆逾期帳款，金額為 {format_currency_vn(data['total_overdue_amount'])}，主要卡點為客戶內部審批付款流程延宕。另有 {len(data['retention_items'])} 筆依合約進度暫留款（{format_currency_vn(data['total_retention_amount'])}），正等待廠端最終驗收（FAC）簽核。"
    )
    rq2_b.font.name = "Times New Roman"
    rq2_b._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    rq2_b.font.size = Pt(8.5)

    # Q3
    p_q3 = doc.add_paragraph()
    p_q3.paragraph_format.space_after = Pt(6)
    rq3_t = p_q3.add_run("3. Kế hoạch hành động tiếp theo là gì? / 後續行動方案：\n")
    rq3_t.bold = True
    rq3_t.font.name = "Times New Roman"
    rq3_t._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    rq3_t.font.size = Pt(9.5)
    rq3_b = p_q3.add_run(
        "• Tiếng Việt: PM sẽ bám sát lịch hẹn cam kết mới của từng khách hàng để thu hồi ngay nhóm bắt buộc; phát hành công văn/thư nhắc nợ chính thức đối với các khoản quá hạn; "
        "đồng thời đôn đốc kỹ sư hiện trường hoàn thành nghiệm thu FAC để kích hoạt giải ngân các khoản tạm giữ tiến độ.\n"
        "• 繁體中文：PM 將依各客戶最新承諾付款期程緊密跟進，確保本週必收款入帳；針對逾期項目發送正式催款公文；並督促現場工程團隊加速完成 FAC 驗收，啟動進度保留款請款。"
    )
    rq3_b.font.name = "Times New Roman"
    rq3_b._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    rq3_b.font.size = Pt(8.5)

    # Signatures Table
    p_sig_space = doc.add_paragraph()
    p_sig_space.paragraph_format.space_before = Pt(10)
    sig_table = doc.add_table(rows=3, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(sig_table, color="FFFFFF", val="none")
    set_table_col_widths(sig_table, [3.43, 3.44])
    add_table_row_cells(sig_table, 0, ["NGƯỜI LẬP BÁO CÁO / 製表人", "TỔNG GIÁM ĐỐC PHÊ DUYỆT / 總經理簽核"], [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER], font_size=9.5, bold=True)
    add_table_row_cells(sig_table, 1, ["(Ký và ghi rõ họ tên / 簽名)", "(Ký và phê duyệt / 簽名與核准)"], [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER], font_size=8.5, bold=False)
    add_table_row_cells(sig_table, 2, [f"\n\n\n{data['reporter']}", f"\n\n\n{data['approver']}"], [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER], font_size=9.5, bold=True)

    # Output to bytes
    doc_io = io.BytesIO()
    doc.save(doc_io)
    return doc_io.getvalue()


# ==============================================================================
# 3. POWERPOINT (.PPTX) GENERATOR SERVICE (BILINGUAL & AUTO-PAGINATED)
# ==============================================================================

def create_pptx_slide_header(slide, title_text: str, subtitle_text: str):
    """Create a standardized header banner on 16:9 widescreen slide."""
    header_box = slide.shapes.add_textbox(PptInches(0.6), PptInches(0.4), PptInches(12.13), PptInches(0.95))
    tf = header_box.text_frame
    tf.word_wrap = True
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.margin_left = 0
    tf.margin_right = 0

    p_title = tf.paragraphs[0]
    p_title.text = title_text
    p_title.font.size = PptPt(19)
    p_title.font.bold = True
    p_title.font.color.rgb = PptRGBColor(0x1F, 0x4E, 0x79)
    p_title.font.name = "Segoe UI"

    p_sub = tf.add_paragraph()
    p_sub.text = subtitle_text
    p_sub.font.size = PptPt(11)
    p_sub.font.color.rgb = PptRGBColor(0x64, 0x74, 0x8B)
    p_sub.font.name = "Segoe UI"


def format_pptx_table_header(table, cols: int, col_widths: List[float], header_texts: List[str], bg_rgb=(0x1F, 0x4E, 0x79), font_size=10.0):
    """Format table header row in PPTX with consistent multi-line styling."""
    for c_idx in range(cols):
        table.columns[c_idx].width = PptInches(col_widths[c_idx])
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = PptRGBColor(*bg_rgb)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE

        tf = cell.text_frame
        tf.word_wrap = True
        tf.margin_top = PptInches(0.04)
        tf.margin_bottom = PptInches(0.04)
        tf.margin_left = PptInches(0.06)
        tf.margin_right = PptInches(0.06)

        raw_header = header_texts[c_idx]
        lines = [line.strip() for line in raw_header.split("\n") if line.strip()]
        if not lines:
            lines = [raw_header]

        p0 = tf.paragraphs[0]
        p0.text = lines[0]
        p0.alignment = PP_ALIGN.CENTER
        p0.font.size = PptPt(font_size)
        p0.font.bold = True
        p0.font.color.rgb = PptRGBColor(0xFF, 0xFF, 0xFF)
        p0.font.name = "Segoe UI"

        for line in lines[1:]:
            p = tf.add_paragraph()
            p.text = line
            p.alignment = PP_ALIGN.CENTER
            p.font.size = PptPt(max(8.5, font_size - 1.0))
            p.font.bold = True
            p.font.color.rgb = PptRGBColor(0xE2, 0xE8, 0xF0)
            p.font.name = "Microsoft JhengHei" if any('\u4e00' <= ch <= '\u9fff' for ch in line) else "Segoe UI"


def add_pptx_table_row(
    table,
    row_idx: int,
    texts: List[str],
    alignments: List[PP_ALIGN],
    bg_rgb=None,
    text_rgb=(0x0F, 0x17, 0x2A),
    font_size=8.5,
    bold=False
):
    """
    Add and format data row in PPTX table.
    Guarantees every line across all paragraphs has uniform font sizing, typography, colors, and margins.
    Completely eliminates PowerPoint default expansion of multi-line cells into giant 18pt font.
    """
    for c_idx, raw_text in enumerate(texts):
        cell = table.cell(row_idx, c_idx)
        if bg_rgb:
            cell.fill.solid()
            cell.fill.fore_color.rgb = PptRGBColor(*bg_rgb)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE

        tf = cell.text_frame
        tf.word_wrap = True
        tf.margin_top = PptInches(0.04)
        tf.margin_bottom = PptInches(0.04)
        tf.margin_left = PptInches(0.06)
        tf.margin_right = PptInches(0.06)

        lines = [line.strip() for line in (raw_text or "").split("\n") if line.strip()]
        if not lines:
            lines = ["-"]

        align = alignments[c_idx] if c_idx < len(alignments) else PP_ALIGN.LEFT

        p0 = tf.paragraphs[0]
        p0.text = lines[0]
        p0.alignment = align
        p0.font.name = "Segoe UI"
        p0.font.size = PptPt(font_size)
        p0.font.bold = bold
        p0.font.color.rgb = PptRGBColor(*text_rgb)

        for line in lines[1:]:
            p = tf.add_paragraph()
            p.text = line
            p.alignment = align
            p.space_before = PptPt(2.0)
            p.space_after = PptPt(0)

            is_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in line)
            is_tag = line.startswith("[") and line.endswith("]")

            if is_tag:
                p.font.name = "Segoe UI"
                p.font.size = PptPt(max(7.0, font_size - 1.0))
                p.font.italic = True
                p.font.bold = True
                p.font.color.rgb = PptRGBColor(0x1F, 0x4E, 0x79)
            elif is_chinese:
                p.font.name = "Microsoft JhengHei"
                p.font.size = PptPt(max(7.5, font_size - 0.5))
                p.font.bold = False
                p.font.color.rgb = PptRGBColor(0x47, 0x55, 0x69)
            else:
                p.font.name = "Segoe UI"
                p.font.size = PptPt(font_size)
                p.font.bold = False
                p.font.color.rgb = PptRGBColor(*text_rgb)


def generate_receivables_ppt_presentation(data: Dict[str, Any]) -> bytes:
    """
    Generate executive PowerPoint (.pptx) presentation fulfilling Boss's 3 rules.
    Automatically paginates tables chunk by chunk (5 rows max per slide) so zero rows are truncated.
    """
    prs = Presentation()
    prs.slide_width = PptInches(13.333)
    prs.slide_height = PptInches(7.5)
    blank_layout = prs.slide_layouts[6]
    stats = data["stats"]
    ROWS_PER_SLIDE = 5

    # -------------------------------------------------------------
    # SLIDE 1: TITLE SLIDE (Cover Slide)
    # -------------------------------------------------------------
    slide1 = prs.slides.add_slide(blank_layout)

    bg_card = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PptInches(0.8), PptInches(0.8), PptInches(11.733), PptInches(5.9))
    bg_card.fill.solid()
    bg_card.fill.fore_color.rgb = PptRGBColor(0xF8, 0xFA, 0xFC)
    bg_card.line.color.rgb = PptRGBColor(0xCB, 0xD5, 0xE1)

    accent_bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, PptInches(0.8), PptInches(0.8), PptInches(0.3), PptInches(5.9))
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = PptRGBColor(0x1F, 0x4E, 0x79)
    accent_bar.line.fill.background()

    tb1 = slide1.shapes.add_textbox(PptInches(1.5), PptInches(1.4), PptInches(10.5), PptInches(4.6))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = f"{data['company_vi']} / {data['company_zh']}"
    p0.font.size = PptPt(14)
    p0.font.bold = True
    p0.font.color.rgb = PptRGBColor(0x1F, 0x4E, 0x79)

    p1 = tf1.add_paragraph()
    p1.text = "BÁO CÁO QUẢN TRỊ CÔNG NỢ DỰ ÁN & DÒNG TIỀN PHẢI THU"
    p1.font.size = PptPt(26)
    p1.font.bold = True
    p1.font.color.rgb = PptRGBColor(0x0F, 0x17, 0x2A)

    p2 = tf1.add_paragraph()
    p2.text = "專案應收帳款管理、資金流向與卡點決策週報"
    p2.font.size = PptPt(19)
    p2.font.bold = True
    p2.font.color.rgb = PptRGBColor(0x47, 0x55, 0x69)

    p4 = tf1.add_paragraph()
    p4.text = f"\nKính trình / 呈核: {data['approver']} · Người lập / 製表人: {data['reporter']} · {data['filter_desc_vi']} ({data['report_date']})"
    p4.font.size = PptPt(12.5)
    p4.font.bold = True
    p4.font.color.rgb = PptRGBColor(0x33, 0x41, 0x55)

    # -------------------------------------------------------------
    # SLIDE 2: EXECUTIVE KPI OVERVIEW & DEBT PORTFOLIO BREAKDOWN
    # -------------------------------------------------------------
    slide2 = prs.slides.add_slide(blank_layout)
    create_pptx_slide_header(
        slide2,
        "TỔNG QUAN ĐIỀU HÀNH & BỘ CHỈ SỐ KPI DÒNG TIỀN (EXECUTIVE OVERVIEW / 財務與資金總覽)",
        f"{data['filter_desc_vi']} / {data['filter_desc_zh']} · Nắm bắt tức thì bức tranh toàn cảnh dòng tiền và cơ cấu công nợ"
    )

    kpi_boxes = [
        ("TỔNG CÔNG NỢ\n應收總額", format_currency_vn(stats.get("total_receivable", 0.0)), "Toàn bộ danh mục báo cáo", (0x1F, 0x4E, 0x79), (0xEB, 0xF8, 0xFF)),
        ("ĐÃ THU HỒI VỀ TK\n已收回金額", format_currency_vn(stats.get("total_received", 0.0)), f"Tỷ lệ thu: {stats.get('completion_rate', 0.0):.1f}%", (0x05, 0x96, 0x69), (0xEC, 0xFD, 0xF5)),
        ("CÒN PHẢI THU (DƯ NỢ)\n尚欠尾款 (未收)", format_currency_vn(stats.get("total_debt", 0.0)), "Đang trong diện quản trị thu hồi", (0xD9, 0x77, 0x06), (0xFF, 0xFB, 0xEB)),
        ("CẢNH BÁO QUÁ HẠN\n逾期與緊急催收", f"{stats.get('overdue_count', 0)} đợt quá hạn", f"{stats.get('urgent_count', 0)} đợt sắp đến hạn trong tuần", (0xDC, 0x26, 0x26), (0xFE, 0xF2, 0xF2)),
    ]

    card_width = 2.85
    card_gap = 0.24
    for idx, (title, val, sub, border_rgb, bg_rgb) in enumerate(kpi_boxes):
        cx = 0.6 + idx * (card_width + card_gap)
        box = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PptInches(cx), PptInches(1.5), PptInches(card_width), PptInches(1.9))
        box.fill.solid()
        box.fill.fore_color.rgb = PptRGBColor(*bg_rgb)
        box.line.color.rgb = PptRGBColor(*border_rgb)
        box.line.width = PptPt(1.5)

        tf = box.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = PptPt(10.5)
        p_t.font.bold = True
        p_t.font.color.rgb = PptRGBColor(*border_rgb)

        p_v = tf.add_paragraph()
        p_v.text = val
        p_v.font.size = PptPt(17)
        p_v.font.bold = True
        p_v.font.color.rgb = PptRGBColor(0x0F, 0x17, 0x2A)

        p_s = tf.add_paragraph()
        p_s.text = sub
        p_s.font.size = PptPt(9.0)
        p_s.font.color.rgb = PptRGBColor(0x64, 0x74, 0x8B)

    # Lower section: Debt Structure Breakdown Table (Analytical & Executive)
    sub_title_box = slide2.shapes.add_textbox(PptInches(0.6), PptInches(3.6), PptInches(12.13), PptInches(0.4))
    stf = sub_title_box.text_frame
    stf.word_wrap = True
    sp = stf.paragraphs[0]
    sp.text = "CƠ CẤU VÀ ĐỊNH HƯỚNG QUẢN TRỊ DƯ NỢ ĐANG THEO DÕI (DEBT PORTFOLIO BREAKDOWN / 未收款結構分析)"
    sp.font.size = PptPt(11.0)
    sp.font.bold = True
    sp.font.color.rgb = PptRGBColor(0x1F, 0x4E, 0x79)

    t_breakdown_shape = slide2.shapes.add_table(5, 5, PptInches(0.6), PptInches(4.05), PptInches(12.13), PptInches(2.9))
    tb2 = t_breakdown_shape.table
    format_pptx_table_header(
        tb2,
        5,
        [3.6, 1.2, 2.3, 1.2, 3.83],
        ["Nhóm Phân Loại Dư Nợ\n未收款項分類", "Số Lượng\n筆數", "Số Tiền Còn Lại\n剩餘金額", "Tỷ Lệ\n佔比", "Định Hướng Điều Hành & Kế Hoạch Xử Lý\n管理決策方針與執行計畫"],
        bg_rgb=(0x1F, 0x4E, 0x79),
        font_size=9.5
    )

    tot_unpaid = float(data.get("total_unpaid_amount") or 0.0)
    pct_must = (float(data.get("total_must_collect_amount") or 0.0) / tot_unpaid * 100) if tot_unpaid > 0 else 0.0
    pct_ret = (float(data.get("total_retention_amount") or 0.0) / tot_unpaid * 100) if tot_unpaid > 0 else 0.0
    pct_over = (float(data.get("total_overdue_amount") or 0.0) / tot_unpaid * 100) if tot_unpaid > 0 else 0.0

    breakdown_rows = [
        (
            "2.1. Bắt buộc / chắc chắn phải thu tuần này (Chưa quá hạn)\n本週重點必收款項（未逾期）",
            f"{len(data.get('must_collect_items') or [])} khoản\n{len(data.get('must_collect_items') or [])} 筆",
            format_currency_vn(float(data.get("total_must_collect_amount") or 0.0)),
            f"{pct_must:.1f}%",
            "Thu hồi ngay theo đúng ngày hẹn; lấy Ủy nhiệm chi (UNC)\n緊跟約定入帳日，向對方出納索取匯款水單",
            (0xFF, 0xFB, 0xEB),
            (0xB4, 0x53, 0x09)
        ),
        (
            "2.2. Tạm giữ theo tiến độ hợp đồng & bảo hành (Chưa quá hạn)\n依合約進度/保固期保留款（正常履約）",
            f"{len(data.get('retention_items') or [])} khoản\n{len(data.get('retention_items') or [])} 筆",
            format_currency_vn(float(data.get("total_retention_amount") or 0.0)),
            f"{pct_ret:.1f}%",
            "Đôn đốc kỹ sư hiện trường hoàn thiện biên bản nghiệm thu FAC\n督促現場工程團隊驗收，簽署 FAC 移交書啟動請款",
            (0xEF, 0xF6, 0xFF),
            (0x25, 0x63, 0xEB)
        ),
        (
            "2.3. Các khoản quá hạn / điểm nghẽn rủi ro\n已逾期卡點與風險項目（需重點催收）",
            f"{len(data.get('overdue_risk_items') or [])} khoản\n{len(data.get('overdue_risk_items') or [])} 筆",
            format_currency_vn(float(data.get("total_overdue_amount") or 0.0)),
            f"{pct_over:.1f}%",
            "Lãnh đạo can thiệp trực tiếp; phát hành công văn nhắc nợ chính thức\n主管層級直接對接催款，發送正式催款公文催繳",
            (0xFE, 0xF2, 0xF2),
            (0xDC, 0x26, 0x26)
        ),
        (
            "TỔNG CỘNG DƯ NỢ ĐANG THEO DÕI (Mục 2.1 + 2.2 + 2.3)\n尚待管理未收總額（100% 帳目核對一致）",
            f"{len(data.get('unpaid_items') or [])} khoản\n{len(data.get('unpaid_items') or [])} 筆",
            format_currency_vn(tot_unpaid),
            "100.0%",
            "Kiểm soát chặt chẽ 100% dòng tiền chưa thu, không để phát sinh nợ xấu\n嚴格掌控未收資金流，防止逾期呆帳產生",
            (0xF1, 0xF5, 0xF9),
            (0x0F, 0x17, 0x2A)
        )
    ]

    for r_i, (col1, col2, col3, col4, col5, bg_c, text_c) in enumerate(breakdown_rows, start=1):
        add_pptx_table_row(
            tb2,
            r_i,
            [col1, col2, col3, col4, col5],
            [PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.RIGHT, PP_ALIGN.CENTER, PP_ALIGN.LEFT],
            bg_rgb=bg_c,
            font_size=8.5,
            bold=(r_i == 4)
        )

    # -------------------------------------------------------------
    # SLIDE 3+: PART 1: EXCLUDE SETTLED ITEMS (AUTO-PAGINATED)
    # -------------------------------------------------------------
    completed = data["completed_items"]
    num_comp_pages = max(1, math.ceil(len(completed) / ROWS_PER_SLIDE))
    for page in range(num_comp_pages):
        slide = prs.slides.add_slide(blank_layout)
        page_suffix = f" (Trang {page+1}/{num_comp_pages} - 頁次 {page+1}/{num_comp_pages})" if num_comp_pages > 1 else ""
        create_pptx_slide_header(
            slide,
            f"PHẦN 1: CÁC KHOẢN ĐÃ XÁC NHẬN THU XONG (LOẠI TRỪ KHỎI DIỆN NGHẼN - 已結清項目){page_suffix}",
            f"Đã đối chiếu và thu đủ 100%: {len(completed)} khoản · Tổng tiền đã thu: {format_currency_vn(data['total_completed_amount'])}"
        )

        chunk = completed[page * ROWS_PER_SLIDE : (page + 1) * ROWS_PER_SLIDE]
        if chunk:
            rows_cnt = len(chunk) + 1
            table_shape = slide.shapes.add_table(rows_cnt, 5, PptInches(0.6), PptInches(1.6), PptInches(12.13), PptInches(4.2))
            t = table_shape.table
            format_pptx_table_header(
                t,
                5,
                [0.9, 3.2, 3.8, 2.23, 2.0],
                ["STT / 序號", "Khách Hàng / 客戶名稱", "Hợp Đồng & Dự Án / 專案與期款", "Số Tiền Đã Thu / 已收金額", "Ngày Thu / 收款日"],
                bg_rgb=(0x05, 0x96, 0x69),
            )
            for idx, item in enumerate(chunk, start=1 + page * ROWS_PER_SLIDE):
                row_idx = idx - (page * ROWS_PER_SLIDE)
                row_texts = [
                    str(idx),
                    str(item.get("customer_bilingual") or item.get("customer_name") or "-"),
                    str(item.get("contract_project_bilingual") or "-"),
                    format_currency_vn(float(item.get("received_amount") or 0.0)),
                    str(item.get("paid_date") or item.get("due_date") or "Đã thu 100% / 已結清"),
                ]
                bg_c = (0xF0, 0xFD, 0xF4) if row_idx % 2 == 1 else (0xFF, 0xFF, 0xFF)
                add_pptx_table_row(t, row_idx, row_texts, [PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.CENTER], bg_rgb=bg_c)

        # Note at bottom
        note_box = slide.shapes.add_textbox(PptInches(0.6), PptInches(6.05), PptInches(12.13), PptInches(0.9))
        ntf = note_box.text_frame
        np = ntf.paragraphs[0]
        np.text = "✓ Ghi chú kế toán / 財務備註: Toàn bộ các khoản trên đã hoàn tất thu tiền 100% về tài khoản công ty, không còn phát sinh nghĩa vụ nợ (已全額收訖結清，無後續應收債權)."
        np.font.size = PptPt(10.0)
        np.font.bold = True
        np.font.color.rgb = PptRGBColor(0x05, 0x96, 0x69)

    # -------------------------------------------------------------
    # SLIDE 4+: PART 2.1: MUST COLLECT (AUTO-PAGINATED - NOT OVERDUE)
    # -------------------------------------------------------------
    must_col = data["must_collect_items"]
    num_must_pages = max(1, math.ceil(len(must_col) / ROWS_PER_SLIDE))
    for page in range(num_must_pages):
        slide = prs.slides.add_slide(blank_layout)
        page_suffix = f" (Trang {page+1}/{num_must_pages} - 頁次 {page+1}/{num_must_pages})" if num_must_pages > 1 else ""
        create_pptx_slide_header(
            slide,
            f"PHẦN 2.1: CÁC KHOẢN BẮT BUỘC / CHẮC CHẮN PHẢI THU (本週/月重點必收項目 - Chưa quá hạn){page_suffix}",
            f"Mục tiêu dòng tiền tuần này: {len(must_col)} khoản · Tổng tiền cần thu: {format_currency_vn(data['total_must_collect_amount'])}"
        )

        chunk = must_col[page * ROWS_PER_SLIDE : (page + 1) * ROWS_PER_SLIDE]
        if chunk:
            rows_cnt = len(chunk) + 1
            table_shape = slide.shapes.add_table(rows_cnt, 6, PptInches(0.6), PptInches(1.6), PptInches(12.13), PptInches(4.5))
            t = table_shape.table
            format_pptx_table_header(
                t,
                6,
                [0.8, 2.6, 2.7, 1.9, 1.7, 2.43],
                ["STT / 序號", "Khách Hàng / 客戶名稱", "Hợp Đồng & Đợt / 期款", "Số Tiền / 應收金額", "Hạn / 預定付款日", "Kế Hoạch Đôn Đốc / 催收方案"],
                bg_rgb=(0xD9, 0x77, 0x06),
            )
            for idx, item in enumerate(chunk, start=1 + page * ROWS_PER_SLIDE):
                row_idx = idx - (page * ROWS_PER_SLIDE)
                target_str = str(item.get("customer_promised_date") or item.get("due_date") or "Trong tuần")
                row_texts = [
                    str(idx),
                    str(item.get("customer_bilingual") or item.get("customer_name") or "-"),
                    str(item.get("contract_project_bilingual") or "-"),
                    format_currency_vn(float(item.get("remaining_debt") or 0.0)),
                    target_str,
                    f"{item.get('action_plan_vi')}\n{item.get('action_plan_zh')}",
                ]
                bg_c = (0xFF, 0xFB, 0xEB) if row_idx % 2 == 1 else (0xFF, 0xFF, 0xFF)
                add_pptx_table_row(t, row_idx, row_texts, [PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.CENTER, PP_ALIGN.LEFT], bg_rgb=bg_c, font_size=8.5)
        else:
            box = slide.shapes.add_textbox(PptInches(1.0), PptInches(2.5), PptInches(11.3), PptInches(2.0))
            tf = box.text_frame
            p = tf.paragraphs[0]
            p.text = "✓ Hiện tại không có khoản cấp bách chưa quá hạn nào cần thu trong tuần này."
            p.font.size = PptPt(15)
            p.font.bold = True
            p.font.color.rgb = PptRGBColor(0x05, 0x96, 0x69)

    # -------------------------------------------------------------
    # SLIDE 5+: PART 2.2: RETENTION / PROGRESS-BASED (AUTO-PAGINATED)
    # -------------------------------------------------------------
    retention = data["retention_items"]
    num_ret_pages = max(1, math.ceil(len(retention) / ROWS_PER_SLIDE))
    for page in range(num_ret_pages):
        slide = prs.slides.add_slide(blank_layout)
        page_suffix = f" (Trang {page+1}/{num_ret_pages} - 頁次 {page+1}/{num_ret_pages})" if num_ret_pages > 1 else ""
        create_pptx_slide_header(
            slide,
            f"PHẦN 2.2: KHOẢN TẠM GIỮ THEO TIẾN ĐỘ HỢP ĐỒNG & BẢO HÀNH (依進度/保固保留款){page_suffix}",
            f"Đang thực hiện đúng tiến độ HĐ: {len(retention)} khoản · Tổng tiền tạm giữ: {format_currency_vn(data['total_retention_amount'])}"
        )

        chunk = retention[page * ROWS_PER_SLIDE : (page + 1) * ROWS_PER_SLIDE]
        if chunk:
            rows_cnt = len(chunk) + 1
            table_shape = slide.shapes.add_table(rows_cnt, 5, PptInches(0.6), PptInches(1.6), PptInches(12.13), PptInches(4.5))
            t = table_shape.table
            format_pptx_table_header(
                t,
                5,
                [0.8, 3.2, 3.2, 2.2, 2.73],
                ["STT / 序號", "Khách Hàng / 客戶名稱", "Hợp Đồng & Dự Án / 合約與專案", "Số Tiền / 保留金額", "Điều Kiện Kích Hoạt / 請款條件"],
                bg_rgb=(0x25, 0x63, 0xEB),
            )
            for idx, item in enumerate(chunk, start=1 + page * ROWS_PER_SLIDE):
                row_idx = idx - (page * ROWS_PER_SLIDE)
                row_texts = [
                    str(idx),
                    str(item.get("customer_bilingual") or item.get("customer_name") or "-"),
                    str(item.get("contract_project_bilingual") or "-"),
                    format_currency_vn(float(item.get("remaining_debt") or 0.0)),
                    str(item.get("trigger_condition_bilingual") or "Ký biên bản nghiệm thu (FAC)\n簽署最終驗收移交書"),
                ]
                bg_c = (0xEF, 0xF6, 0xFF) if row_idx % 2 == 1 else (0xFF, 0xFF, 0xFF)
                add_pptx_table_row(t, row_idx, row_texts, [PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.LEFT], bg_rgb=bg_c, font_size=8.5)
        else:
            box = slide.shapes.add_textbox(PptInches(1.0), PptInches(2.5), PptInches(11.3), PptInches(2.0))
            tf = box.text_frame
            p = tf.paragraphs[0]
            p.text = "✓ Hiện tại không có khoản tạm giữ theo tiến độ nào."
            p.font.size = PptPt(15)
            p.font.bold = True
            p.font.color.rgb = PptRGBColor(0x25, 0x63, 0xEB)

    # -------------------------------------------------------------
    # SLIDE 6+: PART 2.3: OVERDUE BOTTLENECKS & RISKS (AUTO-PAGINATED)
    # -------------------------------------------------------------
    overdue = data["overdue_risk_items"]
    num_over_pages = max(1, math.ceil(len(overdue) / ROWS_PER_SLIDE))
    for page in range(num_over_pages):
        slide = prs.slides.add_slide(blank_layout)
        page_suffix = f" (Trang {page+1}/{num_over_pages} - 頁次 {page+1}/{num_over_pages})" if num_over_pages > 1 else ""
        create_pptx_slide_header(
            slide,
            f"PHẦN 2.3: ĐIỂM NGHẼN QUÁ HẠN & NGUY CƠ RỦI RO DÒNG TIỀN (逾期卡點與風險項目){page_suffix}",
            f"Cần can thiệp cứng rắn: {len(overdue)} khoản · Tổng tiền nghẽn: {format_currency_vn(data['total_overdue_amount'])}"
        )

        chunk = overdue[page * ROWS_PER_SLIDE : (page + 1) * ROWS_PER_SLIDE]
        if chunk:
            rows_cnt = len(chunk) + 1
            table_shape = slide.shapes.add_table(rows_cnt, 5, PptInches(0.6), PptInches(1.6), PptInches(12.13), PptInches(4.5))
            t = table_shape.table
            format_pptx_table_header(
                t,
                5,
                [0.8, 3.2, 2.4, 2.0, 3.73],
                ["STT / 序號", "Khách Hàng / 客戶名稱", "Hợp Đồng / 合約", "Số Tiền / 逾期金額", "Biện Pháp Xử Lý / 應對方案"],
                bg_rgb=(0xDC, 0x26, 0x26),
            )
            for idx, item in enumerate(chunk, start=1 + page * ROWS_PER_SLIDE):
                row_idx = idx - (page * ROWS_PER_SLIDE)
                days_left = item.get("days_left")
                if days_left is not None and days_left < 0:
                    overdue_str = f"Trễ {abs(days_left)} ngày / 逾期 {abs(days_left)} 天"
                else:
                    overdue_str = "Chậm tiến độ / 進度延誤"
                row_texts = [
                    str(idx),
                    str(item.get("customer_bilingual") or item.get("customer_name") or "-"),
                    str(item.get("contract_project_bilingual") or f"{item.get('contract_code') or '-'}\n({overdue_str})"),
                    format_currency_vn(float(item.get("remaining_debt") or 0.0)),
                    f"{item.get('action_plan_vi')}\n{item.get('action_plan_zh')}",
                ]
                bg_c = (0xFE, 0xF2, 0xF2) if row_idx % 2 == 1 else (0xFF, 0xFF, 0xFF)
                add_pptx_table_row(t, row_idx, row_texts, [PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.LEFT], bg_rgb=bg_c, font_size=8.5)
        else:
            box = slide.shapes.add_textbox(PptInches(1.0), PptInches(2.5), PptInches(11.3), PptInches(2.0))
            tf = box.text_frame
            p = tf.paragraphs[0]
            p.text = "✓ TÌNH TRẠNG LÝ TƯỞNG: Hiện tại không có khoản công nợ nào bị trễ hạn quá mức kiểm soát（無逾期風險）."
            p.font.size = PptPt(15)
            p.font.bold = True
            p.font.color.rgb = PptRGBColor(0x05, 0x96, 0x69)

    # -------------------------------------------------------------
    # SLIDE 7+: PART 3: ROOT CAUSE & CARRY FORWARD (AUTO-PAGINATED)
    # -------------------------------------------------------------
    carry = data["carry_forward_items"]
    num_carry_pages = max(1, math.ceil(len(carry) / ROWS_PER_SLIDE))
    for page in range(num_carry_pages):
        slide = prs.slides.add_slide(blank_layout)
        page_suffix = f" (Trang {page+1}/{num_carry_pages} - 頁次 {page+1}/{num_carry_pages})" if num_carry_pages > 1 else ""
        create_pptx_slide_header(
            slide,
            f"PHẦN 3: NGUYÊN NHÂN GỐC RỄ & CARRY FORWARD SANG TUẦN TỚI (下週轉移計畫){page_suffix}",
            "Phân tích nguyên nhân khách quan, kế hoạch hành động cụ thể và cam kết thời hạn dứt điểm (卡點歸因分析與具體執行方案)"
        )

        chunk = carry[page * ROWS_PER_SLIDE : (page + 1) * ROWS_PER_SLIDE]
        if chunk:
            rows_cnt = len(chunk) + 1
            table_shape = slide.shapes.add_table(rows_cnt, 5, PptInches(0.6), PptInches(1.6), PptInches(12.13), PptInches(4.8))
            t = table_shape.table
            format_pptx_table_header(
                t,
                5,
                [0.8, 3.1, 3.8, 1.7, 2.73],
                ["STT / 序號", "Khách Hàng & Hợp Đồng / 客戶與合約", "Nguyên Nhân Chưa Thu / 根本原因", "Cam Kết Tuần Tới / 下週承諾期限", "Kế Hoạch Dứt Điểm / 執行方案"],
                bg_rgb=(0x1F, 0x4E, 0x79),
            )
            for idx, item in enumerate(chunk, start=1 + page * ROWS_PER_SLIDE):
                row_idx = idx - (page * ROWS_PER_SLIDE)
                row_texts = [
                    str(idx),
                    f"{item.get('customer_bilingual') or item.get('customer_name') or '-'}\n({item.get('contract_code') or '-'})",
                    f"[{item.get('cat_vi')} / {item.get('cat_zh')}]\n{item.get('root_cause_vi')}\n{item.get('root_cause_zh')}",
                    f"{item.get('target_date_vi')}\n{item.get('target_date_zh')}",
                    f"{item.get('action_plan_vi')}\n{item.get('action_plan_zh')}",
                ]
                bg_c = (0xF8, 0xFA, 0xFC) if row_idx % 2 == 1 else (0xFF, 0xFF, 0xFF)
                add_pptx_table_row(t, row_idx, row_texts, [PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.LEFT], bg_rgb=bg_c, font_size=8.5)

    # -------------------------------------------------------------
    # SLIDE 8: EXECUTIVE DECISION & ACTION RECOMMENDATIONS (BILINGUAL)
    # -------------------------------------------------------------
    slide8 = prs.slides.add_slide(blank_layout)
    create_pptx_slide_header(
        slide8,
        "PHẦN 4: ĐỀ XUẤT HÀNH ĐỘNG DÀNH CHO TỔNG GIÁM ĐỐC (LEADERSHIP DECISION / 領導決策)",
        "Trả lời trực diện 3 câu hỏi cốt lõi của Lãnh đạo để phê duyệt và chỉ đạo hành động"
    )

    q_boxes = [
        ("CÂU HỎI 1: HIỆN TRẠNG LÀ GÌ?\n現況說明", (
            f"• Tổng công nợ: {format_currency_vn(stats.get('total_receivable', 0.0))}\n"
            f"• Đã thu hồi dứt điểm: {format_currency_vn(data['total_completed_amount'])} ({stats.get('completion_rate', 0.0):.1f}%)\n"
            f"• Dư nợ đang quản lý: {format_currency_vn(data['total_unpaid_amount'])}\n"
            f"• Đã loại trừ {len(data['completed_items'])} khoản xong trước, dồn lực giải quyết {len(data['unpaid_items'])} khoản dở dang.\n"
            f"• 本期應收總額 {format_currency_vn(stats.get('total_receivable', 0.0))}，已收回 {stats.get('completion_rate', 0.0):.1f}%，尚欠尾款 {format_currency_vn(data['total_unpaid_amount'])}。"
        ), (0x1F, 0x4E, 0x79), (0xEB, 0xF8, 0xFF)),

        ("CÂU HỎI 2: ĐIỂM RỦI RO NẰM Ở ĐÂU?\n風險卡點", (
            f"• {len(data['overdue_risk_items'])} khoản quá hạn ({format_currency_vn(data['total_overdue_amount'])})\n"
            f"• Điểm nghẽn chính: Thủ tục đối chiếu chứng từ nội bộ của khách hàng chậm trễ.\n"
            f"• Tiến độ nghiệm thu: {len(data['retention_items'])} khoản tạm giữ ({format_currency_vn(data['total_retention_amount'])}) đang chờ ký biên bản FAC.\n"
            f"• 共有 {len(data['overdue_risk_items'])} 筆逾期卡點，主因為客戶內部審批緩慢；另有 {len(data['retention_items'])} 筆進度款等待廠端 FAC 驗收。"
        ), (0xDC, 0x26, 0x26), (0xFE, 0xF2, 0xF2)),

        ("CÂU HỎI 3: KẾ HOẠCH TIẾP THEO?\n後續行動方案", (
            f"• Thu hồi ngay {format_currency_vn(data['total_must_collect_amount'])} theo lịch hẹn tuần tới.\n"
            f"• Phát hành công văn nhắc nợ chính thức đối với các mã quá hạn.\n"
            f"• Đôn đốc kỹ sư ký nghiệm thu FAC để giải ngân các khoản tạm giữ tiến độ.\n"
            f"• 緊跟最新付款承諾，下週收回必收款；對逾期項目發送正式催款函；督促現場簽署 FAC 啟動保留款請款。"
        ), (0x05, 0x96, 0x69), (0xEC, 0xFD, 0xF5)),
    ]

    card_h = 4.9
    card_w = 3.8
    card_g = 0.35
    for idx, (title, content, border_rgb, bg_rgb) in enumerate(q_boxes):
        cx = 0.6 + idx * (card_w + card_g)
        box = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PptInches(cx), PptInches(1.6), PptInches(card_w), PptInches(card_h))
        box.fill.solid()
        box.fill.fore_color.rgb = PptRGBColor(*bg_rgb)
        box.line.color.rgb = PptRGBColor(*border_rgb)
        box.line.width = PptPt(1.5)

        tf = box.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = title
        pt.font.size = PptPt(11.5)
        pt.font.bold = True
        pt.font.color.rgb = PptRGBColor(*border_rgb)

        pc = tf.add_paragraph()
        pc.text = content
        pc.font.size = PptPt(10)
        pc.font.color.rgb = PptRGBColor(0x0F, 0x17, 0x2A)

    # Save to bytes
    ppt_io = io.BytesIO()
    prs.save(ppt_io)
    return ppt_io.getvalue()
