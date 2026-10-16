"""Time and timezone utilities enforcing Vietnam Standard Time (ICT / UTC+7 / Asia/Ho_Chi_Minh)."""

from datetime import datetime, date, timedelta, timezone
from typing import Optional, Tuple

# Múi giờ chuẩn Việt Nam (ICT - Indochina Time: UTC+7 / GMT+7)
VIETNAM_TZ = timezone(timedelta(hours=7))

WEEKDAYS_VI = [
    "Thứ Hai",
    "Thứ Ba",
    "Thứ Tư",
    "Thứ Năm",
    "Thứ Sáu",
    "Thứ Bảy",
    "Chủ Nhật",
]


def get_vietnam_now() -> datetime:
    """Trả về datetime hiện tại chuẩn 100% theo múi giờ Việt Nam (UTC+7 / Asia/Ho_Chi_Minh)."""
    return datetime.now(VIETNAM_TZ)


def get_vietnam_today() -> date:
    """Trả về ngày date hiện tại theo chuẩn múi giờ Việt Nam."""
    return get_vietnam_now().date()


def get_vietnam_today_str(fmt: str = "%Y-%m-%d") -> str:
    """Trả về chuỗi ngày hôm nay theo giờ Việt Nam (mặc định YYYY-MM-DD)."""
    return get_vietnam_today().strftime(fmt)


def get_vietnam_time_str(fmt: str = "%H:%M") -> str:
    """Trả về chuỗi giờ phút hiện tại theo giờ Việt Nam (HH:MM)."""
    return get_vietnam_now().strftime(fmt)


def get_day_of_week_vi(dt: date) -> str:
    """Trả về tên thứ trong tuần bằng tiếng Việt chuẩn (Thứ Hai, Thứ Ba... Chủ Nhật)."""
    return WEEKDAYS_VI[dt.weekday()]


def parse_date_to_iso(date_str: Optional[str]) -> str:
    """Chuyển đổi chuỗi ngày linh hoạt sang chuẩn ISO YYYY-MM-DD theo giờ Việt Nam."""
    if not date_str or not str(date_str).strip():
        return get_vietnam_today_str("%Y-%m-%d")
    clean_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(clean_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return clean_str


def format_due_string_vn(due_date_str: str, due_time_str: str = "09:00") -> Tuple[str, str, int, bool, bool, bool, bool]:
    """Tính toán quan hệ thời gian, thứ trong tuần, và nhãn hiển thị theo chuẩn giờ Việt Nam (UTC+7).
    
    Returns:
        (formatted_full, timing_badge_text, days_diff, is_today, is_overdue, is_upcoming, is_time_passed)
    """
    iso_date = parse_date_to_iso(due_date_str)
    today = get_vietnam_today()
    now_vn = get_vietnam_now()
    curr_time_str = now_vn.strftime("%H:%M")

    try:
        due_d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    except Exception:
        due_d = today

    days_diff = (due_d - today).days
    day_name = get_day_of_week_vi(due_d)
    date_display = due_d.strftime("%d/%m/%Y")
    time_display = (due_time_str or "09:00").strip()

    is_today = (days_diff == 0)
    is_time_passed = False
    if is_today and time_display and time_display < curr_time_str:
        is_time_passed = True

    is_overdue = (days_diff < 0) or (is_today and is_time_passed)
    is_upcoming = (days_diff > 0)

    formatted_full = f"{day_name}, {date_display} ({time_display})"

    if is_today:
        if is_time_passed:
            timing_badge = f"Hôm nay ({time_display}) - Đã qua giờ hẹn"
        else:
            timing_badge = f"Hôm nay ({time_display})"
    elif days_diff == 1:
        timing_badge = "Ngày mai"
    elif days_diff == -1:
        timing_badge = "Hôm qua (Quá hạn 1 ngày)"
    elif days_diff < -1:
        timing_badge = f"Quá hạn {abs(days_diff)} ngày"
    elif days_diff <= 7:
        timing_badge = f"{day_name} tới ({days_diff} ngày nữa)"
    else:
        timing_badge = f"Còn {days_diff} ngày"

    return formatted_full, timing_badge, days_diff, is_today, is_overdue, is_upcoming, is_time_passed
