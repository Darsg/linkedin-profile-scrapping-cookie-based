"""Parsing of the loose date strings LinkedIn and data providers return."""

import re
from datetime import UTC, date, datetime, timedelta

_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
            ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
            ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for m in names
}  # fmt: skip

_MONTH_YEAR = re.compile(r"(?:([A-Za-z]{3,9})\.?\s+)?((?:19|20)\d{2})")
_RANGE_SPLIT = re.compile(r"\s+[-–—]\s+|\s+to\s+", re.IGNORECASE)
_PRESENT = re.compile(r"present|current|now", re.IGNORECASE)
_RELATIVE = re.compile(r"(\d+)\s*(mo|yr|[smhdwy])\b", re.IGNORECASE)
_YEAR = re.compile(r"(?:19|20)\d{2}")


def parse_month_year(text: str | None) -> date | None:
    """'Jan 2020' -> 2020-01-01, '2020' -> 2020-01-01, anything else -> None."""
    if not text:
        return None
    match = _MONTH_YEAR.search(text)
    if not match:
        return None
    month = _MONTHS.get((match.group(1) or "").lower(), 1)
    return date(int(match.group(2)), month, 1)


def parse_date_range(text: str | None) -> tuple[date | None, date | None, bool]:
    """'Jan 2020 - Present · 3 yrs' -> (2020-01-01, None, True)."""
    if not text:
        return None, None, False
    span = text.split("·")[0].strip()
    parts = _RANGE_SPLIT.split(span, maxsplit=1)
    start = parse_month_year(parts[0])
    if len(parts) == 1:
        return start, None, False
    if _PRESENT.search(parts[1]):
        return start, None, True
    return start, parse_month_year(parts[1]), False


def parse_year_range(text: str | None) -> tuple[int | None, int | None]:
    """'2014 - 2018' -> (2014, 2018); 'Sep 2019' -> (2019, None)."""
    years = [int(y) for y in _YEAR.findall(text or "")]
    if not years:
        return None, None
    return years[0], (years[1] if len(years) > 1 else None)


def looks_like_date_range(text: str) -> bool:
    return bool(_YEAR.search(text)) and len(text) < 60


_UNIT_DELTAS = {
    "s": timedelta(seconds=1),
    "m": timedelta(minutes=1),
    "h": timedelta(hours=1),
    "d": timedelta(days=1),
    "w": timedelta(weeks=1),
    "mo": timedelta(days=30),
    "y": timedelta(days=365),
    "yr": timedelta(days=365),
}


def parse_relative_time(text: str | None, now: datetime | None = None) -> datetime | None:
    """LinkedIn shows post age as '3d', '2w', '5mo', '1yr'. Returns an approximate timestamp."""
    match = _RELATIVE.search(text or "")
    if not match:
        return None
    delta = _UNIT_DELTAS[match.group(2).lower()] * int(match.group(1))
    return (now or datetime.now(UTC)) - delta


def parse_datetime(value: object) -> datetime | None:
    """Best-effort parse of ISO strings / epoch (s or ms) values from provider payloads."""
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        seconds = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(seconds, UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return parse_relative_time(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None
