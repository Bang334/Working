"""Currency and number conversion utilities for Vietnamese and Traditional Chinese."""

import re
from typing import Any


def parse_positive_integer(value: Any) -> int:
    """Extract integer value from currency string or number."""
    if isinstance(value, (int, float)):
        return int(value)
    digits = re.sub(r"[^\d]", "", str(value or ""))
    return int(digits) if digits else 0


def format_currency_vnd(amount: Any) -> str:
    """Format integer amount to standard VND format with period separators."""
    val = parse_positive_integer(amount)
    return f"{val:,}".replace(",", ".") + " VND"


def number_to_vietnamese_words(n: int) -> str:
    """Convert integer number into standard Vietnamese accounting text."""
    if n == 0:
        return "Không đồng chẵn."

    digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    units = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]

    def read_three_digits(num_str: str, is_first: bool = False) -> str:
        num = int(num_str)
        h = num // 100
        t = (num % 100) // 10
        u = num % 10
        parts = []

        if h > 0 or not is_first:
            parts.append(digits[h] + " trăm")

        if t == 0 and u != 0:
            if h > 0 or not is_first:
                parts.append("lẻ")
            parts.append(digits[u])
        elif t == 1:
            parts.append("mười")
            if u == 1:
                parts.append("một")
            elif u == 5:
                parts.append("lăm")
            elif u != 0:
                parts.append(digits[u])
        elif t > 1:
            parts.append(digits[t] + " mươi")
            if u == 1:
                parts.append("mốt")
            elif u == 4:
                parts.append("tư")
            elif u == 5:
                parts.append("lăm")
            elif u != 0:
                parts.append(digits[u])

        return " ".join(parts)

    s = str(abs(n))
    groups = []
    while len(s) > 3:
        groups.insert(0, s[-3:])
        s = s[:-3]
    groups.insert(0, s)

    res = []
    total_groups = len(groups)
    for i, g in enumerate(groups):
        if int(g) == 0:
            continue
        g_words = read_three_digits(g, is_first=(i == 0))
        unit_idx = total_groups - 1 - i
        unit = units[unit_idx]
        if g_words:
            res.append(g_words + (" " + unit if unit else ""))

    result = " ".join(res).strip()
    result = result[0].upper() + result[1:] + " đồng chẵn."
    return result


def number_to_chinese_words(n: int) -> str:
    """Convert integer number into Traditional Chinese capital accounting format (大寫金額)."""
    if n == 0:
        return "零越盾整"

    digits = ["零", "壹", "貳", "參", "肆", "伍", "陸", "柒", "捌", "玖"]
    units = ["", "拾", "佰", "仟"]
    big_units = ["", "萬", "億", "兆"]

    s = str(abs(n))
    groups = []
    while len(s) > 4:
        groups.insert(0, s[-4:])
        s = s[:-4]
    groups.insert(0, s)

    result_parts = []
    total_groups = len(groups)
    for i, g in enumerate(groups):
        g_num = int(g)
        if g_num == 0:
            continue
        g_str = f"{g_num:04d}" if i > 0 else str(g_num)
        group_words = ""
        zero_flag = False
        l = len(g_str)
        for j, ch in enumerate(g_str):
            digit_val = int(ch)
            pos = l - 1 - j
            if digit_val == 0:
                zero_flag = True
            else:
                if zero_flag:
                    group_words += digits[0]
                    zero_flag = False
                group_words += digits[digit_val] + units[pos]

        big_unit_idx = total_groups - 1 - i
        group_words += big_units[big_unit_idx]
        result_parts.append(group_words)

    return "越南盾" + "".join(result_parts) + "整"
