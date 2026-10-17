def format_inr(val) -> str:
    """
    Format a number using Indian currency numbering grouping.
    e.g. 100000.00 -> "1,00,000.00", 1234567.89 -> "12,34,567.89", 500 -> "500.00"
    """
    if val is None:
        return "0.00"
    try:
        f = float(val)
    except (ValueError, TypeError):
        return str(val)

    is_neg = f < 0
    f = abs(f)
    s = f"{f:.2f}"
    parts = s.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last3 = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted = ",".join(groups) + "," + last3

    if is_neg:
        formatted = "-" + formatted
    return f"{formatted}.{decimal_part}"
