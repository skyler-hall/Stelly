"""Tests for jobs/ba_source.py: the jobright.ai README table parser."""

from datetime import datetime

from jobs import ba_source

REFERENCE = datetime(2026, 8, 18, 12, 0)

TABLE = """
| Company | Job Title | Location | Work Model | Date Posted |
| ----- | --------- |  --------- | ---- | ------- |
| **[Fidelity Canada](https://www.fidelity.ca)** | **[Business Analyst - Fidelity Wealth](https://jobright.ai/jobs/info/6a67b5a25d2a117fb9cecdc3?utm_campaign=Business%20Analyst&utm_source=1103)** | Toronto, ON, Canada | Hybrid | Aug 18 |
| **[Covista](https://covista.com)** | **[Business Process Analyst](https://jobright.ai/jobs/info/6a846cedd34f700f87fb8689?utm_campaign=Business%20Analyst&utm_source=1103)** | Lisle, IL, United States | Hybrid | Aug 18 |
| ↳ | **[Business Process Analyst](https://jobright.ai/jobs/info/6a846ce158ded76ad8fe6faa?utm_campaign=Business%20Analyst&utm_source=1103)** | Columbia, MD, United States | Hybrid | Aug 18 |
| **[Charter](https://charter.ca/)** | **[Junior Business Architect](https://jobright.ai/jobs/info/6a66711be8d8d22e3293016a?utm_campaign=Business%20Analyst&utm_source=1103)** | Victoria, BC, Canada | Remote | Aug 15 |
"""


def test_parses_expected_row_count():
    assert len(ba_source.parse_table(TABLE, REFERENCE)) == 4


def test_first_row_fields():
    listing = ba_source.parse_table(TABLE, REFERENCE)[0]
    assert listing["id"] == "ba:6a67b5a25d2a117fb9cecdc3"
    assert listing["company"] == "Fidelity Canada"
    assert listing["title"] == "Business Analyst - Fidelity Wealth"
    assert listing["locations"] == ["Toronto, ON, Canada"]
    assert listing["category"] == "Business Analyst"
    assert listing["active"] is True
    assert "utm_campaign" not in listing["url"]


def test_continuation_row_inherits_company():
    listings = ba_source.parse_table(TABLE, REFERENCE)
    covista_rows = [l for l in listings if l["company"] == "Covista"]
    assert len(covista_rows) == 2
    assert covista_rows[1]["locations"] == ["Columbia, MD, United States"]
    assert covista_rows[0]["id"] != covista_rows[1]["id"]


def test_remote_work_model_adds_remote_to_locations():
    listings = ba_source.parse_table(TABLE, REFERENCE)
    charter = next(l for l in listings if l["company"] == "Charter")
    assert charter["locations"] == ["Victoria, BC, Canada", "Remote"]


def test_header_and_separator_rows_are_skipped():
    listings = ba_source.parse_table(TABLE, REFERENCE)
    assert all(l["company"] != "Company" for l in listings)


def test_row_without_a_link_is_skipped():
    broken = "| SomeCo | not a link | Remote | Remote | Aug 18 |"
    assert ba_source.parse_table(broken, REFERENCE) == []


# ---- date parsing ----

def test_same_year_date_parses_as_is():
    ts = ba_source._parse_date("Aug 18", REFERENCE)
    assert datetime.fromtimestamp(ts).date() == datetime(2026, 8, 18).date()


def test_unparseable_date_returns_none():
    assert ba_source._parse_date("not a date", REFERENCE) is None


def test_december_reference_rolls_january_date_forward_a_year():
    # A "Jan 2" row seen while today is Dec 30 means next January, not
    # a year-old January, even though naively attaching the current year
    # would put it far in the past.
    reference = datetime(2026, 12, 30)
    ts = ba_source._parse_date("Jan 2", reference)
    parsed = datetime.fromtimestamp(ts)
    assert (parsed.year, parsed.month, parsed.day) == (2027, 1, 2)


def test_january_reference_rolls_december_date_back_a_year():
    reference = datetime(2027, 1, 2)
    ts = ba_source._parse_date("Dec 30", reference)
    parsed = datetime.fromtimestamp(ts)
    assert (parsed.year, parsed.month, parsed.day) == (2026, 12, 30)
