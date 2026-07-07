"""Tests for tracker/matcher.py, company extraction and the match rule."""

from tracker import matcher


# ---- extract_company ----

def test_company_from_normal_domain():
    assert matcher.extract_company("Recruiting <talent@stripe.com>") == "Stripe"


def test_ats_domain_uses_display_name():
    company = matcher.extract_company("Acme Careers <no-reply@greenhouse.io>")
    assert company == "Acme"


def test_lever_subdomain_is_recognized_as_ats():
    company = matcher.extract_company("Globex Recruiting <jobs@hire.lever.co>")
    assert company == "Globex"


def test_workday_uses_display_name():
    company = matcher.extract_company("Initech Talent Team <initech@myworkday.com>")
    assert company == "Initech"


def test_bare_address_falls_back_to_domain():
    assert matcher.extract_company("careers@vandelay.com") == "Vandelay"


def test_ats_with_noise_only_display_name_returns_empty():
    # Display name is pure recruiting noise, nothing trustworthy remains.
    assert matcher.extract_company("No Reply <notifications@linkedin.com>") == ""


def test_empty_sender_returns_empty():
    assert matcher.extract_company("") == ""


# ---- decide_match: the locked rule ----

def test_no_existing_means_new():
    decision, app = matcher.decide_match("Acme", [])
    assert decision == "new"
    assert app is None


def test_exactly_one_existing_means_matched():
    existing = [{"id": 7, "company": "Acme"}]
    decision, app = matcher.decide_match("Acme", existing)
    assert decision == "matched"
    assert app["id"] == 7


def test_multiple_existing_means_ambiguous_never_guess():
    existing = [{"id": 7}, {"id": 8}]
    decision, app = matcher.decide_match("Acme", existing)
    assert decision == "ambiguous"
    assert app is None
