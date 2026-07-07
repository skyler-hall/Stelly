"""
Decides which application an incoming email belongs to.

The rules collapsed to something simple after looking at real data:
recruiters almost never reply inside ATS threads, so thread IDs are
useless. Company name is the lookup key, and anything genuinely
ambiguous (multiple open applications at the same company) gets flagged
for Skyler's manual review rather than guessed at by code.

extract_company pulls a company name out of the sender field. ATS
platforms (Greenhouse, Lever, Workday and friends) send from their own
domains, so for those the display name is the trustworthy part, for
everything else the domain is.
"""

import re

# Senders whose domain says nothing about the company hiring.
ATS_DOMAINS = (
    "greenhouse.io",
    "greenhouse-mail.io",
    "lever.co",
    "hire.lever.co",
    "myworkday.com",
    "myworkdayjobs.com",
    "icims.com",
    "ashbyhq.com",
    "smartrecruiters.com",
    "jobvite.com",
    "taleo.net",
    "bamboohr.com",
    "linkedin.com",
    "indeed.com",
    "workablemail.com",
)

# Noise words that show up in ATS display names around the company name.
_NAME_NOISE = re.compile(
    r"\b(careers?|recruiting|recruitment|talent|jobs?|team|hiring|hr|"
    r"no[- ]?reply|notifications?|applications?)\b",
    re.IGNORECASE,
)


def _split_sender(sender):
    """'Acme Careers <no-reply@greenhouse.io>' -> ('Acme Careers',
    'no-reply@greenhouse.io'). Either piece can come back empty."""
    match = re.match(r"^\s*\"?([^\"<]*?)\"?\s*<([^>]+)>\s*$", sender or "")
    if match:
        return match.group(1).strip(), match.group(2).strip().lower()
    if sender and "@" in sender:
        return "", sender.strip().lower()
    return (sender or "").strip(), ""


def _clean_display_name(name):
    """Strip recruiting noise words and leftover punctuation from a
    display name, leaving what is hopefully just the company."""
    cleaned = _NAME_NOISE.sub("", name)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" .,@|-_").strip()


def _company_from_domain(address):
    """'talent@stripe.com' -> 'Stripe'. Uses the registrable chunk just
    left of the TLD, which is right for the common case."""
    domain = address.split("@")[-1]
    parts = domain.split(".")
    if len(parts) < 2:
        return ""
    return parts[-2].capitalize()


def _is_ats(address):
    domain = address.split("@")[-1]
    return any(domain == ats or domain.endswith("." + ats) for ats in ATS_DOMAINS)


def extract_company(sender):
    """Best-effort company name from an email's From field. Returns an
    empty string when there is nothing trustworthy to extract, which
    callers should treat as needs-manual-review, not as a company."""
    display, address = _split_sender(sender)

    if address and not _is_ats(address):
        from_domain = _company_from_domain(address)
        if from_domain:
            return from_domain

    cleaned = _clean_display_name(display)
    return cleaned


def decide_match(company, existing_applications):
    """Apply the locked matching rule.

    Returns (decision, application_or_None) where decision is one of:
      'new'        no application for this company exists yet
      'matched'    exactly one exists, safe to attach
      'ambiguous'  multiple exist, flag for Skyler, attach to none
    """
    if not existing_applications:
        return "new", None
    if len(existing_applications) == 1:
        return "matched", existing_applications[0]
    return "ambiguous", None
