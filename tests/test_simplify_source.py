"""Tests for jobs/simplify_source.py, network fully mocked."""

from unittest.mock import MagicMock, patch

from jobs import simplify_source


def _raw(id_, title="Software Engineer", company="Acme", locations=None,
         category="Software Engineering", posted=1000, active=True,
         url="https://example.com/job"):
    return {
        "id": id_,
        "title": title,
        "company_name": company,
        "locations": locations if locations is not None else ["Remote"],
        "category": category,
        "date_posted": posted,
        "date_updated": posted,
        "url": url,
        "active": active,
    }


def _mock_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status = MagicMock()
    return response


def test_normalize_namespaces_the_id():
    listing = simplify_source.normalize(_raw("abc123"))
    assert listing["id"] == "simplify:abc123"
    assert listing["company"] == "Acme"
    assert listing["active"] is True


def test_fetch_new_since_drops_inactive():
    payload = [_raw("a", active=True, posted=100), _raw("b", active=False, posted=200)]
    with patch("jobs.simplify_source.requests.get", return_value=_mock_response(payload)):
        new, cutoff = simplify_source.fetch_new_since(0)
    assert [item["id"] for item in new] == ["simplify:a"]
    assert cutoff == 100


def test_fetch_new_since_drops_anything_at_or_before_cutoff():
    payload = [_raw("old", active=True, posted=50), _raw("new", active=True, posted=150)]
    with patch("jobs.simplify_source.requests.get", return_value=_mock_response(payload)):
        new, cutoff = simplify_source.fetch_new_since(100)
    assert [item["id"] for item in new] == ["simplify:new"]
    assert cutoff == 150


def test_cutoff_unchanged_when_nothing_new():
    payload = [_raw("old", active=True, posted=50)]
    with patch("jobs.simplify_source.requests.get", return_value=_mock_response(payload)):
        new, cutoff = simplify_source.fetch_new_since(100)
    assert new == []
    assert cutoff == 100


def test_cutoff_is_the_max_of_new_postings_not_just_the_last():
    payload = [_raw("a", active=True, posted=300), _raw("b", active=True, posted=150)]
    with patch("jobs.simplify_source.requests.get", return_value=_mock_response(payload)):
        _, cutoff = simplify_source.fetch_new_since(0)
    assert cutoff == 300
