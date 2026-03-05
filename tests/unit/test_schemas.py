"""
Unit tests for api/models/schemas.py — Pydantic validation rules.
"""

import pytest
from pydantic import ValidationError

from api.models.schemas import (
    AnalysisRequest,
    BatchRequest,
    MeUpdateRequest,
    RegisterRequest,
)


# ---------------------------------------------------------------------------
# RegisterRequest
# ---------------------------------------------------------------------------

class TestRegisterRequest:
    def test_valid_register(self):
        r = RegisterRequest(email="user@example.com", password="password123")
        assert r.email == "user@example.com"

    def test_malformed_email_missing_at(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="notanemail", password="password123")
        assert "email" in str(exc_info.value).lower() or "pattern" in str(exc_info.value).lower()

    def test_malformed_email_no_tld(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@nodot", password="password123")

    def test_malformed_email_double_at(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@@example.com", password="password123")

    def test_password_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="user@example.com", password="short")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("password",) for e in errors)

    def test_password_exactly_8_chars_is_valid(self):
        r = RegisterRequest(email="user@example.com", password="exactly8")
        assert r.password == "exactly8"

    def test_password_7_chars_fails(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="seven7!")


# ---------------------------------------------------------------------------
# AnalysisRequest
# ---------------------------------------------------------------------------

class TestAnalysisRequest:
    def test_valid_claim(self):
        r = AnalysisRequest(claim="This is a valid claim with enough characters.")
        assert r.claim == "This is a valid claim with enough characters."

    def test_claim_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            AnalysisRequest(claim="Short")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("claim",) for e in errors)

    def test_claim_too_long(self):
        with pytest.raises(ValidationError) as exc_info:
            AnalysisRequest(claim="x" * 2001)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("claim",) for e in errors)

    def test_claim_exactly_10_chars_is_valid(self):
        r = AnalysisRequest(claim="1234567890")
        assert len(r.claim) == 10

    def test_claim_exactly_2000_chars_is_valid(self):
        r = AnalysisRequest(claim="a" * 2000)
        assert len(r.claim) == 2000

    def test_default_language_is_it(self):
        r = AnalysisRequest(claim="This is a valid claim long enough")
        assert r.language == "it"

    def test_invalid_language_pattern(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(claim="This is a valid claim long enough", language="italian")

    def test_max_rounds_too_low(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(claim="This is a valid claim long enough", max_rounds=0)

    def test_max_rounds_too_high(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(claim="This is a valid claim long enough", max_rounds=11)

    def test_max_rounds_valid_boundary(self):
        r = AnalysisRequest(claim="This is a valid claim long enough", max_rounds=10)
        assert r.max_rounds == 10


# ---------------------------------------------------------------------------
# BatchRequest
# ---------------------------------------------------------------------------

class TestBatchRequest:
    def test_valid_batch(self):
        r = BatchRequest(claims=["First claim here.", "Second claim here."])
        assert len(r.claims) == 2

    def test_empty_claims_fails(self):
        with pytest.raises(ValidationError):
            BatchRequest(claims=[])

    def test_invalid_language(self):
        with pytest.raises(ValidationError):
            BatchRequest(claims=["Some claim"], language="eng")


# ---------------------------------------------------------------------------
# MeUpdateRequest
# ---------------------------------------------------------------------------

class TestMeUpdateRequest:
    def test_all_none_is_valid(self):
        r = MeUpdateRequest()
        assert r.email is None
        assert r.new_password is None
        assert r.current_password is None

    def test_new_password_too_short(self):
        with pytest.raises(ValidationError):
            MeUpdateRequest(new_password="short")

    def test_valid_new_password(self):
        r = MeUpdateRequest(new_password="longenough123")
        assert r.new_password == "longenough123"

    def test_malformed_email(self):
        with pytest.raises(ValidationError):
            MeUpdateRequest(email="bademail")
