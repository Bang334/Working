# -*- coding: utf-8 -*-
"""Service to aggregate procurement orders for visual project hardware readiness and timeline charts."""

from datetime import datetime, timedelta
import re
from typing import Any, Dict, List, Optional

from app.database import get_db_connection
from app.services.procurement_service import list_procurement_orders, get_status_label


def _clean_project_title_bilingual(raw_proj: Optional[str], cust_comp: Optional[str] = None) -> Dict[str, str]:
    """Extract clean bilingual Vietnamese and Traditional Chinese names for projects."""
    if not raw_proj:
        return {"vi": cust_comp or "Dự án khác", "zh": cust_comp or "其他專案"}

    lines = [line.strip() for line in str(raw_proj).split("\n") if line.strip()]
    if len(lines) >= 2:
        return {"vi": lines[0], "zh": lines[1]}
    
    text = lines[0] if lines else str(raw_proj).strip()
    if "/" in text:
        parts = [p.strip() for p in text.split("/", 1)]
        return {"vi": parts[0], "zh": parts[1]}
    
    # Predefined known company/project names
    text_upper = text.upper()
    if "CHENG FENG" in text_upper:
        return {"vi": "Cheng Feng Le Hua Việt Nam", "zh": "承豐樂華 (越南)"}
    if "SEIYO" in text_upper or "正揚" in text:
        return {"vi": "Seiyo Việt Nam", "zh": "正揚 (SEIYO)"}
    if "DARFON" in text_upper or "達方" in text:
        return {"vi": "Darfon Electronics GĐ 2", "zh": "達方電子第二階段"}
    if "CX" in text_upper or "錩新" in text:
        return {"vi": "CX Technology", "zh": "錩新科技 (CX)"}
    if "HONGMING" in text_upper or "浤詺" in text:
        return {"vi": "Nội bộ Hong Ming", "zh": "浤詺內部"}
    if "JI YANG" in text_upper:
        return {"vi": "Ji Yang", "zh": "吉陽 (JI YANG)"}
    if "JING GUANG" in text_upper or "景光" in text:
        return {"vi": "Jing Guang", "zh": "景光電子"}

    return {"vi": text, "zh": text}


def _shorten_item_name(item_name: str, max_chars: int = 42) -> str:
    """Produce clean short title for bar segment labels and tooltips."""
    if not item_name:
        return "Thiết bị"
    first_line = [l.strip() for l in item_name.split("\n") if l.strip()][0]
    # Remove leading numbering like '1.0', '1.'
    cleaned = re.sub(r"^\d+[\.\)]\s*", "", first_line).strip()
    if len(cleaned) > max_chars:
        return cleaned[:max_chars - 1] + "…"
    return cleaned


def get_procurement_chart_data(
    supplier: Optional[str] = None,
    project: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate structured chart data for project hardware readiness bars and weekly timeline analysis."""
    orders = list_procurement_orders(status=status, supplier=supplier, project=project, search=search)
    
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")

    # Current week window (Monday to Sunday)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Next week window
    start_of_next_week = end_of_week + timedelta(days=1)
    end_of_next_week = start_of_next_week + timedelta(days=6)

    # 1. Group by Project for Hardware Readiness Bar Charts
    projects_map: Dict[str, Dict[str, Any]] = {}

    total_orders_count = len(orders)
    delivered_total = 0
    in_transit_total = 0
    delayed_total = 0
    pending_total = 0
    pending_payment_total = 0

    # Categorized lists for Timeline view (3 Phần theo yêu cầu Sếp)
    delivered_this_week: List[Dict[str, Any]] = []
    delayed_items: List[Dict[str, Any]] = []
    next_week_plan_items: List[Dict[str, Any]] = []

    for ord_row in orders:
        ord_id = ord_row["id"]
        proj_raw = ord_row.get("project_name") or ord_row.get("customer_company") or "Dự án khác"
        cust_comp = ord_row.get("customer_company") or ""
        
        # Standardize project key
        proj_names = _clean_project_title_bilingual(proj_raw, cust_comp)
        proj_key = proj_names["vi"].strip().lower()

        if proj_key not in projects_map:
            projects_map[proj_key] = {
                "project_key": proj_key,
                "project_name_vi": proj_names["vi"],
                "project_name_zh": proj_names["zh"],
                "customer_company": cust_comp,
                "total_items": 0,
                "delivered_count": 0,
                "not_arrived_count": 0,
                "readiness_pct": 0.0,
                "all_arrived": False,
                "order_ids": [],
                "segments": [],
            }

        st = (ord_row.get("delivery_status") or "PENDING").upper()
        actual_date_str = ord_row.get("actual_delivery_date")
        eta_date_str = ord_row.get("eta_date")

        # Binary status: ĐÃ ĐẾN (Delivered/Arrived) vs CHƯA ĐẾN (Not Arrived/Pending)
        is_arrived = (st == "DELIVERED") or bool(actual_date_str and actual_date_str != "-")

        if is_arrived:
            color_class = "seg-delivered"
            delivered_total += 1
            projects_map[proj_key]["delivered_count"] += 1
            status_text = "Đã đến / 已到貨"
        else:
            color_class = "seg-pending"
            pending_total += 1
            projects_map[proj_key]["not_arrived_count"] += 1
            status_text = "Chưa đến / 待到貨"

        projects_map[proj_key]["total_items"] += 1
        projects_map[proj_key]["order_ids"].append(ord_id)

        # Timeline classification (Hàng vừa về tuần này vs Hàng chưa về)
        if is_arrived and actual_date_str:
            try:
                ad = datetime.strptime(actual_date_str[:10], "%Y-%m-%d").date()
                if start_of_week <= ad <= end_of_week or (today - ad).days <= 7:
                    delivered_this_week.append(ord_row)
            except Exception:
                pass
        elif not is_arrived:
            if eta_date_str:
                try:
                    ed = datetime.strptime(eta_date_str[:10], "%Y-%m-%d").date()
                    if ed < today or st == "DELAYED":
                        delayed_items.append(ord_row)
                    elif start_of_next_week <= ed <= end_of_next_week:
                        next_week_plan_items.append(ord_row)
                    else:
                        delayed_items.append(ord_row)
                except Exception:
                    delayed_items.append(ord_row)
            else:
                delayed_items.append(ord_row)

        short_name = _shorten_item_name(ord_row.get("item_name", "Thiết bị"))
        projects_map[proj_key]["segments"].append({
            "id": ord_id,
            "order_no": ord_row.get("order_no") or ord_id,
            "item_name": short_name,
            "item_name_full": ord_row.get("item_name") or "",
            "category": ord_row.get("category") or "Thiết bị",
            "quantity": ord_row.get("quantity") or 1,
            "unit": ord_row.get("unit") or "Bộ",
            "supplier_name": ord_row.get("supplier_name") or "Chưa rõ",
            "customer_company": cust_comp,
            "project_name": proj_names["vi"],
            "order_date": ord_row.get("order_date") or "-",
            "eta_date": ord_row.get("eta_date") or "-",
            "actual_delivery_date": ord_row.get("actual_delivery_date") or "-",
            "delivery_status": "DELIVERED" if is_arrived else "PENDING",
            "delivery_status_label": status_text,
            "is_arrived": is_arrived,
            "supplier_payment_status": ord_row.get("supplier_payment_status") or "-",
            "shipping_notes": ord_row.get("shipping_notes") or "-",
            "unit_price": ord_row.get("unit_price") or 0.0,
            "total_amount": ord_row.get("total_amount") or 0.0,
            "currency": ord_row.get("currency") or "VND",
            "color_class": color_class,
        })

    # Compute width % and readiness % for each project batch
    projects_list = list(projects_map.values())
    for proj in projects_list:
        total = proj["total_items"]
        if total > 0:
            deliv = proj["delivered_count"]
            proj["readiness_pct"] = round((deliv / total) * 100.0, 1)
            proj["all_arrived"] = (deliv == total)
            # Equal segment width in the 100% project batch bar
            seg_width = round(100.0 / total, 2)
            for seg in proj["segments"]:
                seg["width_pct"] = seg_width

    # Sort projects:
    # 1. Projects with items NOT yet arrived come first (Cần PM theo dõi)
    # 2. Projects with 100% arrived pushed to bottom (Đã về đủ ép xuống dưới)
    projects_list.sort(
        key=lambda p: (
            1 if p["all_arrived"] else 0,
            -p["not_arrived_count"],
            -p["total_items"]
        )
    )

    completed_projects_count = sum(1 for p in projects_list if p["all_arrived"])
    total_projects_count = len(projects_list)
    summary_text = f"{delivered_total}/{total_orders_count} thiết bị đã về kho ({completed_projects_count}/{total_projects_count} lô hoàn tất)"

    return {
        "status": "success",
        "dates": {
            "today": today_str,
            "start_of_week": start_of_week.strftime("%Y-%m-%d"),
            "end_of_week": end_of_week.strftime("%Y-%m-%d"),
            "start_of_next_week": start_of_next_week.strftime("%Y-%m-%d"),
            "end_of_next_week": end_of_next_week.strftime("%Y-%m-%d"),
        },
        "kpi": {
            "total_orders": total_orders_count,
            "delivered_count": delivered_total,
            "not_arrived_count": pending_total,
            "completed_projects_count": completed_projects_count,
            "total_projects_count": total_projects_count,
            "overall_readiness_pct": round((delivered_total / total_orders_count * 100.0), 1) if total_orders_count > 0 else 0.0,
            "summary_text": summary_text,
            "active_projects_count": total_projects_count,
        },
        "projects_readiness": projects_list,
        "timeline_analysis": {
            "delivered_this_week_count": len(delivered_this_week),
            "delivered_this_week": delivered_this_week,
            "not_arrived_count": len(delayed_items),
            "not_arrived_items": delayed_items,
            "next_week_plan_count": len(next_week_plan_items),
            "next_week_plan_items": next_week_plan_items,
        }
    }
