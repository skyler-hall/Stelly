"""Tests for jobs/preferences.py: title/category/location matching."""

from jobs import preferences


def _listing(title="Software Engineer", category="Software Engineering",
             locations=None):
    return {
        "title": title,
        "category": category,
        "locations": locations if locations is not None else ["Remote"],
    }


# ---- category + keyword matching ----

def test_swe_title_and_category_and_remote_matches():
    assert preferences.matches(_listing()) is True


def test_wrong_category_does_not_match():
    listing = _listing(category="Hardware")
    assert preferences.matches(listing) is False


def test_right_category_wrong_title_does_not_match():
    listing = _listing(title="Product Marketing Manager", category="Software")
    assert preferences.matches(listing) is False


def test_data_keyword_matches_under_software_category():
    listing = _listing(title="Data Engineer", category="Software")
    assert preferences.matches(listing) is True


def test_keyword_match_is_case_insensitive():
    listing = _listing(title="SOFTWARE ENGINEER I")
    assert preferences.matches(listing) is True


# ---- Business Analyst feed: category alone is enough ----

def test_ba_category_skips_title_keyword_check():
    listing = _listing(title="Business Process Analyst",
                        category="Business Analyst")
    assert preferences.matches(listing) is True


def test_ba_category_still_requires_location_match():
    listing = _listing(title="Business Analyst", category="Business Analyst",
                        locations=["Toronto, ON, Canada"])
    assert preferences.matches(listing) is False


# ---- location matching ----

def test_remote_location_matches():
    listing = _listing(locations=["Remote in USA"])
    assert preferences.matches(listing) is True


def test_dc_to_nyc_corridor_matches():
    for loc in ["Washington, DC", "Bethesda, MD", "Philadelphia, PA",
                "Jersey City, NJ", "New York, NY", "NYC"]:
        assert preferences.matches(_listing(locations=[loc])) is True, loc


def test_out_of_corridor_location_does_not_match():
    listing = _listing(locations=["Austin, TX"])
    assert preferences.matches(listing) is False


def test_short_state_code_does_not_false_positive_on_substring():
    # "Spain" contains "pa", "Company" contains "ny": neither should match
    # the PA / NY location keywords via naive substring search.
    listing = _listing(locations=["Madrid, Spain"])
    assert preferences.matches(listing) is False


def test_no_locations_does_not_match():
    listing = _listing(locations=[])
    assert preferences.matches(listing) is False
