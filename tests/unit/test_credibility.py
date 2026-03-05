"""
Unit tests for tools/credibility.py — domain credibility scoring.
"""

import pytest

from tools.credibility import CredibilityTier, _strip_subdomain, score_domain


# ---------------------------------------------------------------------------
# _strip_subdomain
# ---------------------------------------------------------------------------

class TestStripSubdomain:
    def test_www_prefix_stripped(self):
        assert _strip_subdomain("www.bbc.com") == "bbc.com"

    def test_subdomain_stripped(self):
        assert _strip_subdomain("news.bbc.com") == "bbc.com"

    def test_deep_subdomain_stripped(self):
        assert _strip_subdomain("sub.sub2.example.org") == "example.org"

    def test_no_prefix_unchanged(self):
        assert _strip_subdomain("reuters.com") == "reuters.com"

    def test_two_part_tld_gov_it(self):
        # gov.it is a two-part TLD; salute.gov.it should keep three labels
        assert _strip_subdomain("salute.gov.it") == "salute.gov.it"

    def test_two_part_tld_co_uk(self):
        assert _strip_subdomain("news.bbc.co.uk") == "bbc.co.uk"

    def test_www_plus_two_part_tld(self):
        # www. is stripped first, then the two-part TLD is preserved
        assert _strip_subdomain("www.bbc.co.uk") == "bbc.co.uk"

    def test_single_label_returned_as_is(self):
        assert _strip_subdomain("localhost") == "localhost"

    def test_empty_string(self):
        assert _strip_subdomain("") == ""

    def test_plain_domain_no_subdomain(self):
        assert _strip_subdomain("example.com") == "example.com"


# ---------------------------------------------------------------------------
# score_domain — tier classification
# ---------------------------------------------------------------------------

class TestScoreDomain:
    def test_high_tier_nih(self):
        tier, score, note = score_domain("nih.gov")
        assert tier == CredibilityTier.HIGH
        assert score == 1.0
        assert "High" in note

    def test_high_tier_bbc(self):
        tier, score, note = score_domain("bbc.com")
        assert tier == CredibilityTier.HIGH

    def test_high_tier_with_www_prefix(self):
        tier, score, note = score_domain("www.reuters.com")
        assert tier == CredibilityTier.HIGH

    def test_high_tier_subdomain(self):
        # pubmed.ncbi.nih.gov → strips to nih.gov
        tier, score, note = score_domain("pubmed.ncbi.nih.gov")
        assert tier == CredibilityTier.HIGH

    def test_medium_tier_nytimes(self):
        tier, score, note = score_domain("nytimes.com")
        assert tier == CredibilityTier.MEDIUM
        assert score == 0.6

    def test_low_tier_infowars(self):
        tier, score, note = score_domain("infowars.com")
        assert tier == CredibilityTier.LOW
        assert score == 0.2

    def test_unknown_tier_random_blog(self):
        tier, score, note = score_domain("some-random-blog-xyz123.net")
        assert tier == CredibilityTier.UNKNOWN
        assert score == 0.5
        assert note == ""

    def test_empty_domain_returns_unknown(self):
        tier, score, note = score_domain("")
        assert tier == CredibilityTier.UNKNOWN
        assert score == 0.5

    def test_wikipedia_is_high(self):
        tier, score, note = score_domain("en.wikipedia.org")
        assert tier == CredibilityTier.HIGH

    def test_rt_is_low(self):
        tier, score, note = score_domain("rt.com")
        assert tier == CredibilityTier.LOW


# ---------------------------------------------------------------------------
# score_domain — score range invariant
# ---------------------------------------------------------------------------

class TestScoreRange:
    @pytest.mark.parametrize("domain", [
        "nih.gov",
        "nytimes.com",
        "infowars.com",
        "unknown-website-xyz.io",
        "",
        "www.bbc.com",
        "en.wikipedia.org",
    ])
    def test_score_in_range(self, domain: str):
        _, score, _ = score_domain(domain)
        assert 0.0 <= score <= 1.0, f"Score {score} out of range for {domain!r}"
