"""Resolve flexible payment schedules from user input and the approved Excel forms."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import openpyxl

from app.config import WORKING_DIR


PAYMENT_FORM_PATH = WORKING_DIR / "Bieu Mau" / "đơn yêu cầu NCC thanh toán-Gốc.xlsx"
_PERCENT_RE = re.compile(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*%")
_PAYMENT_RE = re.compile(
    r"thanh\s*to[aá]n\s+(?:tạm\s*ứng\s+)?(\d+(?:[.,]\d+)?)\s*%",
    re.IGNORECASE,
)
_DAYS_RE = re.compile(r"(?<!\d)(\d{1,3})\s*(?:ngày|ngay|days?|天)", re.IGNORECASE)


def _number(value: Any) -> float:
    return float(str(value).replace(",", ".").strip())


def _clean_percentage(value: Any) -> float | int:
    number = _number(value)
    return int(number) if number.is_integer() else round(number, 4)


def _normalise_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def _extract_note_schedule(note: str) -> Tuple[List[float | int], List[Optional[int]]]:
    matches = list(_PAYMENT_RE.finditer(note or ""))
    percentages: List[float | int] = []
    deadlines: List[Optional[int]] = []
    for index, match in enumerate(matches):
        percentages.append(_clean_percentage(match.group(1)))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(note)
        segment = note[match.end():end]
        day_match = _DAYS_RE.search(segment)
        deadlines.append(int(day_match.group(1)) if day_match else None)
    return percentages, deadlines


@lru_cache(maxsize=8)
def _load_payment_templates_cached(path_text: str, modified_ns: int) -> Tuple[Dict[str, Any], ...]:
    del modified_ns  # Cache invalidation key only.
    workbook = openpyxl.load_workbook(path_text, data_only=True, read_only=True)
    templates: List[Dict[str, Any]] = []
    try:
        for worksheet in workbook.worksheets:
            customer = str(worksheet["C10"].value or "").strip()
            project = str(worksheet["C11"].value or "").strip()
            note = str(worksheet["B23"].value or "").strip()
            percentages, deadlines = _extract_note_schedule(note)

            # A few one-time-payment sheets express 100% in the request line,
            # while their note is intentionally blank.
            if not percentages:
                request_line = " ".join(
                    str(worksheet[cell].value or "") for cell in ("B15", "D15", "I15")
                )
                pct_matches = [_clean_percentage(m.group(1)) for m in _PERCENT_RE.finditer(request_line)]
                if len(pct_matches) == 1 and abs(float(pct_matches[0]) - 100.0) < 0.001:
                    percentages = [100]
                    deadlines = [None]

            if not percentages or abs(sum(float(item) for item in percentages) - 100.0) > 0.01:
                continue

            templates.append(
                {
                    "sheet_name": worksheet.title,
                    "customer": customer,
                    "project": project,
                    "note": note,
                    "percentages": percentages,
                    "deadlines": deadlines,
                    "search_text": _normalise_text(
                        f"{worksheet.title} {customer} {project} {worksheet['B15'].value or ''}"
                    ),
                }
            )
    finally:
        workbook.close()
    return tuple(templates)


def load_payment_templates(path: Path | str = PAYMENT_FORM_PATH) -> List[Dict[str, Any]]:
    """Return payment patterns read directly from all usable sheets in the form workbook."""
    template_path = Path(path)
    if not template_path.exists():
        candidates = [
            WORKING_DIR / "Bieu Mau" / "đơn yêu cầu NCC thanh toán-Gốc.xlsx",
            WORKING_DIR / "đơn yêu cầu thanh toán - CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN) - HMV151020250001.xlsx",
            WORKING_DIR / "đơn yêu cầu thanh toán - CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM - HD-20261013-001.xlsx",
        ]
        found = None
        for cand in candidates:
            if cand.exists():
                found = cand
                break
        if found:
            template_path = found
        else:
            logger.warning("Không tìm thấy file mẫu thanh toán tại %s. Sử dụng tiến độ người dùng/mặc định.", template_path)
            return []
    try:
        rows = _load_payment_templates_cached(str(template_path), template_path.stat().st_mtime_ns)
        return [dict(row) for row in rows]
    except Exception as err:
        logger.warning("Lỗi đọc file mẫu thanh toán: %s. Trả về rỗng.", err)
        return []


def _extract_explicit_schedule(
    text: str,
) -> Optional[Tuple[List[float | int], List[Optional[int]], List[str]]]:
    """Extract a 1–4 phase sequence such as '10% 30 ngày, 30% 60 ngày, ...'."""
    if not text:
        return None

    # Ưu tiên bóc tách theo các mục được đánh số 1., 2., 3., 4. (song ngữ hoặc đơn ngữ)
    numbered_blocks = re.split(r"(?:\n|^|\s)(?=[1-4]\.\s+)", text.strip())
    numbered_blocks = [b.strip() for b in numbered_blocks if b.strip() and not b.strip().startswith("備註")]
    if 2 <= len(numbered_blocks) <= 4:
        pcts: List[float | int] = []
        dls: List[Optional[int]] = []
        descs: List[str] = []
        for block in numbered_blocks:
            m_pct = _PERCENT_RE.search(block)
            if not m_pct:
                break
            pcts.append(_clean_percentage(m_pct.group(1)))
            m_day = _DAYS_RE.search(block)
            dls.append(int(m_day.group(1)) if m_day else None)
            desc = block
            if "Thanh toán" in block:
                desc = block.split("Thanh toán", 1)[1]
                if ")" in desc:
                    desc = desc.split(")", 1)[1].strip()
            descs.append(desc.strip().rstrip("."))
        if len(pcts) == len(numbered_blocks) and abs(sum(float(p) for p in pcts) - 100.0) < 0.01:
            return pcts, dls, descs

    def parse_candidate(
        candidate: str,
    ) -> Optional[Tuple[List[float | int], List[Optional[int]], List[str]]]:
        matches = list(_PERCENT_RE.finditer(candidate))
        if not 1 <= len(matches) <= 4:
            return None
        percentages = [_clean_percentage(match.group(1)) for match in matches]
        if abs(sum(float(item) for item in percentages) - 100.0) > 0.01:
            return None
        deadlines: List[Optional[int]] = []
        descriptions: List[str] = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(candidate)
            raw_segment = candidate[match.end():end]
            segment = raw_segment.splitlines()[0] if raw_segment else ""
            day_match = _DAYS_RE.search(segment)
            deadlines.append(int(day_match.group(1)) if day_match else None)
            description = _DAYS_RE.sub("", segment)
            description = re.sub(
                r"\b(?:trong\s+vòng|thời\s+hạn|T/T)\b",
                "",
                description,
                flags=re.IGNORECASE,
            )
            description = re.sub(r"^[\s,;:./-]+|[\s,;:./-]+$", "", description).strip()
            descriptions.append(description)
        return percentages, deadlines, descriptions

    # Prefer the line/paragraph that actually discusses payment. This avoids
    # accidentally treating VAT or discount percentages as milestones.
    payment_chunks = [
        chunk
        for chunk in re.split(r"[\r\n]+", text)
        if re.search(r"thanh\s*to[aá]n|tiến\s*độ|phương\s*thức|payment|付款|đợt", chunk, re.I)
    ]
    for chunk in payment_chunks:
        parsed = parse_candidate(chunk)
        if parsed:
            return parsed
    if payment_chunks:
        parsed = parse_candidate("\n".join(payment_chunks))
        if parsed:
            return parsed
    return parse_candidate(text)


def _context_text(data: Dict[str, Any], source_text: str = "") -> str:
    ben_a = data.get("ben_a") or {}
    project = data.get("du_an") or {}
    items = data.get("hang_muc") or []
    fields: List[str] = [
        str(source_text or ""),
        str(ben_a.get("ten_cong_ty") or ""),
        str(ben_a.get("ten_tieng_trung") or ""),
        str(project.get("ten_du_an_viet") or ""),
        str(project.get("ten_du_an_trung") or ""),
    ]
    fields.extend(str((item.get("ten_san_pham") if isinstance(item, dict) else "") or "") for item in items)
    return _normalise_text(" ".join(f for f in fields if f))


def _template_score(template: Dict[str, Any], context: str) -> int:
    context_tokens = set(context.split())
    template_tokens = set(str(template.get("search_text", "")).split())
    ignored = {
        "CONG", "TY", "TNHH", "VIET", "NAM", "DU", "AN", "HE", "THONG", "VA", "CHO",
        "PROJECT", "SYSTEM", "CO", "LTD", "LIMITED", "HANG", "MUC", "THIET", "BI",
    }
    shared = (context_tokens & template_tokens) - ignored
    distinctive = {
        "JINXUN", "CHENGFENG", "CHENG", "FENG", "VONMAX", "SEIYO", "RFID", "MES",
        "SMB", "IIOT", "PRS", "CX", "HUAFENG", "HUAFON",
    }
    return len(shared) + 4 * len(shared & distinctive)


def _select_template(
    templates: Sequence[Dict[str, Any]],
    context: str,
    percentages: Optional[Sequence[float | int]] = None,
) -> Optional[Dict[str, Any]]:
    candidates = list(templates)
    if percentages is not None:
        target = [float(value) for value in percentages]
        candidates = [
            item
            for item in candidates
            if [float(value) for value in item["percentages"]] == target
        ]
    if not candidates:
        return None

    ranked = sorted(candidates, key=lambda item: _template_score(item, context), reverse=True)
    if _template_score(ranked[0], context) > 0:
        return ranked[0]
    return next((item for item in ranked if item["sheet_name"] == "712TR"), ranked[0])


DEFAULT_COMPANY_SCHEDULE: List[Dict[str, Any]] = [
    {
        "dot": 1,
        "phan_tram": 35,
        "thoi_han_tt_ngay": None,
        "nguon_mau_sheet": "Mặc định công ty (35-55-10)",
        "tieu_de_trung": "簽約定金",
        "tieu_de": "Đợt 1 (35%)",
        "dieu_kien_trung": "雙方簽約後即期以電匯（T/T）方式支付",
        "dieu_kien_viet": "Thanh toán tạm ứng 35% ngay sau khi hai bên ký kết hợp đồng",
    },
    {
        "dot": 2,
        "phan_tram": 55,
        "thoi_han_tt_ngay": None,
        "nguon_mau_sheet": "Mặc định công ty (35-55-10)",
        "tieu_de_trung": "設備安裝款",
        "tieu_de": "Đợt 2 (55%)",
        "dieu_kien_trung": "於設備安裝及系統建置完成並經雙方簽署確認文件後",
        "dieu_kien_viet": "Sau khi bàn giao thiết bị và hoàn thành cài đặt hệ thống",
    },
    {
        "dot": 3,
        "phan_tram": 10,
        "thoi_han_tt_ngay": None,
        "nguon_mau_sheet": "Mặc định công ty (35-55-10)",
        "tieu_de_trung": "驗收尾款",
        "tieu_de": "Đợt 3 (10%)",
        "dieu_kien_trung": "於最終驗收（FAC）完成並簽署驗收交付文件後",
        "dieu_kien_viet": "Sau khi khách hàng nghiệm thu hoàn tất và ký biên bản bàn giao (FAC)",
    },
]


def _phase_roles(count: int, software_project: bool) -> List[str]:
    if count == 1:
        return ["delivery"]
    if count == 2:
        return ["signing", "acceptance"]
    if count == 3:
        return ["signing", "deployment" if software_project else "installation", "acceptance"]
    if count == 4:
        return ["signing", "infrastructure", "deployment" if software_project else "installation", "acceptance"]
    raise ValueError("Mẫu Word hỗ trợ từ 1 đến 4 đợt thanh toán.")


def _condition_for_role(role: str, deadline: Optional[int]) -> Dict[str, str]:
    events = {
        "signing": (
            "ngay sau khi hai bên ký kết hợp đồng",
            "雙方簽約後即期以電匯（T/T）方式支付",
            "Tạm ứng ký hợp đồng",
            "簽約定金",
        ),
        "infrastructure": (
            "kể từ ngày ký biên bản hoàn thành kéo cáp/hạ tầng",
            "於佈線工程完成並經雙方簽署完成確認文件後",
            "Thi công kéo dây/hạ tầng",
            "佈線工程款",
        ),
        "installation": (
            "kể từ ngày ký biên bản hoàn thành lắp đặt, kiểm tra và chạy thử thiết bị",
            "於設備安裝及調測完成並經雙方簽署確認文件後",
            "Lắp đặt thiết bị",
            "設備安裝款",
        ),
        "deployment": (
            "sau khi bàn giao thiết bị và hoàn thành cài đặt hệ thống",
            "於設備安裝及系統建置完成並經雙方簽署確認文件後",
            "Bàn giao & cài đặt hệ thống",
            "設備安裝款",
        ),
        "acceptance": (
            "kể từ ngày ký biên bản nghiệm thu bàn giao (FAC)",
            "於最終驗收（FAC）完成並簽署驗收交付文件後",
            "Nghiệm thu cuối cùng (FAC)",
            "驗收尾款",
        ),
        "delivery": (
            "khách hàng nhận đủ hàng hóa và chứng từ hợp lệ",
            "客戶收到全部貨物及有效單據",
            "Thanh toán một lần",
            "一次付清",
        ),
    }
    event_vi, event_zh, title_vi, title_zh = events[role]
    clean_event_zh = event_zh.rstrip("後")
    if deadline is None:
        condition_vi = event_vi
        condition_zh = event_zh
    else:
        condition_vi = f"{event_vi}, thời hạn thanh toán T/T {deadline} ngày"
        condition_zh = f"{clean_event_zh}後，付款期限為 T/T {deadline} 天"
    return {
        "dieu_kien_viet": condition_vi,
        "dieu_kien_trung": condition_zh,
        "tieu_de": title_vi,
        "tieu_de_trung": title_zh,
    }


def build_payment_schedule(
    percentages: Sequence[float | int],
    deadlines: Optional[Sequence[Optional[int]]] = None,
    context: str = "",
    source_sheet: str = "Người dùng nhập",
) -> List[Dict[str, Any]]:
    """Build bilingual conditions for exactly the supplied number and order of phases."""
    if not 1 <= len(percentages) <= 4:
        raise ValueError("Tiến độ thanh toán phải có từ 1 đến 4 đợt.")
    if abs(sum(float(item) for item in percentages) - 100.0) > 0.01:
        raise ValueError("Tổng tỷ lệ các đợt thanh toán phải bằng 100%.")

    normalised_context = _normalise_text(context)
    software_project = bool(
        set(normalised_context.split())
        & {"MES", "SOFTWARE", "PHAN", "MEM", "API", "WEB", "SYSTEM", "HE", "THONG", "PRS"}
    )
    roles = _phase_roles(len(percentages), software_project)
    deadline_values = list(deadlines or [])
    deadline_values.extend([None] * (len(percentages) - len(deadline_values)))

    result: List[Dict[str, Any]] = []
    for index, (percentage, role) in enumerate(zip(percentages, roles), start=1):
        deadline = deadline_values[index - 1]
        condition = _condition_for_role(role, deadline)
        result.append(
            {
                "dot": index,
                "phan_tram": _clean_percentage(percentage),
                "thoi_han_tt_ngay": deadline,
                "nguon_mau_sheet": source_sheet,
                **condition,
            }
        )
    return result


def resolve_payment_schedule(
    source_text: str,
    contract_data: Dict[str, Any],
    template_path: Path | str = PAYMENT_FORM_PATH,
) -> List[Dict[str, Any]]:
    """Resolve explicit user input first; otherwise infer the closest approved sheet."""
    templates = load_payment_templates(template_path)
    context = _context_text(contract_data, source_text)
    explicit = _extract_explicit_schedule(source_text)

    if explicit:
        percentages, deadlines, descriptions = explicit
        exact_template = _select_template(templates, context, percentages)
        source_sheet = exact_template["sheet_name"] if exact_template else "Người dùng nhập"
        # User-supplied deadlines always win. Missing deadlines are inherited only
        # when the exact same percentage sequence exists in an approved sheet.
        if exact_template:
            deadlines = [
                supplied if supplied is not None else approved
                for supplied, approved in zip(deadlines, exact_template["deadlines"])
            ]
        resolved = build_payment_schedule(percentages, deadlines, context, source_sheet)

        # A user's phase-specific wording has absolute priority. Gemini may add
        # the corresponding Traditional-Chinese rendering, but it may not invent
        # a purpose for a phase the user left unspecified.
        ai_schedule = contract_data.get("phan_bo_thanh_toan") or []
        ai_percentages = [float(item.get("phan_tram", 0)) for item in ai_schedule]
        ai_matches = ai_percentages == [float(value) for value in percentages]
        for index, description in enumerate(descriptions):
            if not description:
                continue
            resolved[index]["mo_ta_nguoi_dung"] = description
            resolved[index]["dieu_kien_viet"] = description
            if ai_matches:
                ai_row = ai_schedule[index]
                if ai_row.get("dieu_kien_viet"):
                    resolved[index]["dieu_kien_viet"] = ai_row["dieu_kien_viet"]
                if ai_row.get("dieu_kien_trung"):
                    resolved[index]["dieu_kien_trung"] = ai_row["dieu_kien_trung"]
                if ai_row.get("tieu_de"):
                    resolved[index]["tieu_de"] = ai_row["tieu_de"]
                if ai_row.get("tieu_de_trung"):
                    resolved[index]["tieu_de_trung"] = ai_row["tieu_de_trung"]
        return resolved

    selected = _select_template(templates, context)
    if not selected or _template_score(selected, context) == 0:
        return [dict(row) for row in DEFAULT_COMPANY_SCHEDULE]
    return build_payment_schedule(
        selected["percentages"],
        selected["deadlines"],
        context,
        selected["sheet_name"],
    )


def normalize_payment_schedule(
    schedule: Iterable[Dict[str, Any]],
    contract_data: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Validate an edited schedule and fill only missing bilingual conditions."""
    rows = [dict(item) for item in schedule]
    percentages = [_clean_percentage(item.get("phan_tram", 0)) for item in rows]
    deadlines = [
        int(item["thoi_han_tt_ngay"])
        if item.get("thoi_han_tt_ngay") not in (None, "")
        else None
        for item in rows
    ]
    context = _context_text(contract_data or {})
    generated = build_payment_schedule(percentages, deadlines, context)
    for index, item in enumerate(rows):
        generated[index].update({key: value for key, value in item.items() if value not in (None, "")})
        generated[index]["dot"] = index + 1
        generated[index]["phan_tram"] = percentages[index]
        generated[index]["thoi_han_tt_ngay"] = deadlines[index]
    return generated
