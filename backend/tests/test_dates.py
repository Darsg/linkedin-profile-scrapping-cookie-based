from datetime import UTC, date, datetime

from app.utils.dates import (
    parse_date_range,
    parse_datetime,
    parse_month_year,
    parse_relative_time,
    parse_year_range,
)


def test_month_year() -> None:
    assert parse_month_year("Jan 2020") == date(2020, 1, 1)
    assert parse_month_year("September 2019") == date(2019, 9, 1)
    assert parse_month_year("2018") == date(2018, 1, 1)
    assert parse_month_year("soon") is None
    assert parse_month_year(None) is None


def test_date_range() -> None:
    assert parse_date_range("Jan 2020 - Present · 3 yrs") == (date(2020, 1, 1), None, True)
    assert parse_date_range("Jul 2019 – Dec 2021 · 2 yrs 6 mos") == (
        date(2019, 7, 1),
        date(2021, 12, 1),
        False,
    )
    assert parse_date_range("2015 - 2017") == (date(2015, 1, 1), date(2017, 1, 1), False)
    assert parse_date_range(None) == (None, None, False)


def test_year_range() -> None:
    assert parse_year_range("2012 - 2016") == (2012, 2016)
    assert parse_year_range("Sep 2019") == (2019, None)
    assert parse_year_range("n/a") == (None, None)


def test_relative_time() -> None:
    now = datetime(2026, 11, 15, tzinfo=UTC)
    assert parse_relative_time("2w • ", now) == datetime(2026, 11, 1, tzinfo=UTC)
    assert parse_relative_time("3mo • Edited", now) == datetime(2026, 8, 17, tzinfo=UTC)
    assert parse_relative_time("5h", now) == datetime(2026, 11, 14, 19, tzinfo=UTC)
    assert parse_relative_time("just now", now) is None


def test_datetime_from_provider_payloads() -> None:
    assert parse_datetime("2026-01-02T03:04:05Z") == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert parse_datetime(1767322800000) == datetime.fromtimestamp(1767322800, UTC)
    assert parse_datetime("") is None
