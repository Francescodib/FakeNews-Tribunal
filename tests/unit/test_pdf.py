"""
Unit tests for core/pdf.py — PDF report generation.

On Windows (the target platform), Arial TTF fonts are available at
C:\\Windows\\Fonts\\arial*.ttf and the tests run natively.

For CI or non-Windows environments, _add_fonts is patched to register
fpdf2's built-in Helvetica under the "Arial" family so that all
set_font("Arial", ...) calls still succeed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fpdf import FPDF


# ---------------------------------------------------------------------------
# Determine whether Windows Arial fonts are available.
# ---------------------------------------------------------------------------

_ARIAL_AVAILABLE = (
    sys.platform == "win32"
    and Path(r"C:\Windows\Fonts\arial.ttf").exists()
)

# ---------------------------------------------------------------------------
# Fallback font registration: map "Arial" to Helvetica (fpdf2 core font).
# fpdf2 doesn't support aliasing core fonts as TTF families, but we can
# register a minimal Unicode TTF via a stub. Since the goal is to test the
# PDF generation logic rather than font rendering, we simply patch set_font
# to fall back to Helvetica when Arial is not registered.
# ---------------------------------------------------------------------------


def _noop_add_fonts(pdf: FPDF) -> None:
    """No-op: do not load Arial TTF files."""


def _safe_set_font_factory(original_set_font):
    """Return a set_font wrapper that silently ignores unknown font families."""
    def _safe_set_font(self, family: str = "", style: str = "", size: int = 0, **kw):
        try:
            original_set_font(self, family=family, style=style, size=size, **kw)
        except Exception:
            # Fall back to Helvetica for any unregistered family (e.g. Arial
            # when we haven't loaded the TTF files).
            original_set_font(self, family="Helvetica", style=style, size=size, **kw)
    return _safe_set_font


# ---------------------------------------------------------------------------
# Test fixtures / data
# ---------------------------------------------------------------------------

MINIMAL_VERDICT: dict = {
    "label": "FALSE",
    "confidence": 0.9,
    "summary": "The claim is false.",
    "reasoning": "Evidence clearly contradicts the claim.",
    "supporting_source_urls": [],
    "contradicting_source_urls": ["https://example.com/source1"],
}

MINIMAL_ROUNDS: list[dict] = [
    {
        "round_number": 1,
        "researcher_report": "Research findings go here.",
        "researcher_sources": [
            {
                "url": "https://nih.gov/article",
                "title": "NIH Article",
                "domain": "nih.gov",
                "credibility_tier": "high",
            }
        ],
        "advocate_challenge": "Challenge to the research.",
        "advocate_counter_sources": [],
        "judge_continuation_reason": None,
    }
]


def _generate(claim: str, verdict: dict, rounds: list[dict]) -> bytes:
    """
    Call generate_verdict_pdf, patching font loading when Arial is unavailable.
    """
    from core import pdf as _pdf_module

    if _ARIAL_AVAILABLE:
        # Native Windows with Arial fonts: run without any patches.
        return _pdf_module.generate_verdict_pdf(
            claim=claim,
            verdict=verdict,
            rounds=rounds,
            analysis_id="00000000-0000-0000-0000-000000000001",
            created_at="2026-03-04T12:00:00",
            llm_provider="anthropic",
            llm_model="claude-sonnet-4-6",
        )

    # Non-Windows / Arial not found: patch _add_fonts and set_font to use
    # Helvetica as a fallback so we can still test the PDF structure.
    original_set_font = FPDF.set_font
    safe_set_font = _safe_set_font_factory(original_set_font)

    with (
        patch.object(_pdf_module, "_add_fonts", _noop_add_fonts),
        patch.object(FPDF, "set_font", safe_set_font),
    ):
        return _pdf_module.generate_verdict_pdf(
            claim=claim,
            verdict=verdict,
            rounds=rounds,
            analysis_id="00000000-0000-0000-0000-000000000001",
            created_at="2026-03-04T12:00:00",
            llm_provider="anthropic",
            llm_model="claude-sonnet-4-6",
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateVerdictPdf:
    def test_returns_bytes(self):
        result = _generate("The Earth is flat.", MINIMAL_VERDICT, MINIMAL_ROUNDS)
        assert isinstance(result, bytes)

    def test_non_empty(self):
        result = _generate("The Earth is flat.", MINIMAL_VERDICT, MINIMAL_ROUNDS)
        assert len(result) > 100

    def test_starts_with_pdf_magic_bytes(self):
        result = _generate("The Earth is flat.", MINIMAL_VERDICT, MINIMAL_ROUNDS)
        assert result[:4] == b"%PDF", f"Expected PDF header, got {result[:8]!r}"

    def test_empty_rounds(self):
        result = _generate("Some claim.", MINIMAL_VERDICT, [])
        assert result[:4] == b"%PDF"

    def test_unicode_em_dash_in_claim(self):
        claim = "The president \u2014 as reported \u2014 denied the allegations."
        result = _generate(claim, MINIMAL_VERDICT, MINIMAL_ROUNDS)
        assert result[:4] == b"%PDF"

    def test_unicode_arrows_in_reasoning(self):
        verdict = dict(MINIMAL_VERDICT)
        verdict = {**MINIMAL_VERDICT, "reasoning": "Evidence \u2192 conclusion. Step 1 \u2013 Step 2."}
        result = _generate("Arrow test claim here.", verdict, [])
        assert result[:4] == b"%PDF"

    @pytest.mark.parametrize("label", ["TRUE", "FALSE", "MISLEADING", "PARTIALLY_TRUE", "UNVERIFIABLE"])
    def test_all_verdict_labels(self, label: str):
        verdict = {**MINIMAL_VERDICT, "label": label}
        result = _generate(f"Claim for label {label}.", verdict, [])
        assert result[:4] == b"%PDF", f"Failed for label {label}"

    def test_multiple_rounds(self):
        rounds = [
            {
                "round_number": i,
                "researcher_report": f"Report round {i}.",
                "researcher_sources": [],
                "advocate_challenge": f"Challenge round {i}.",
                "advocate_counter_sources": [],
                "judge_continuation_reason": "Need more evidence." if i < 3 else None,
            }
            for i in range(1, 4)
        ]
        result = _generate("Multi-round claim test.", MINIMAL_VERDICT, rounds)
        assert result[:4] == b"%PDF"

    def test_sources_with_credibility_tiers(self):
        rounds = [
            {
                "round_number": 1,
                "researcher_report": "Report.",
                "researcher_sources": [
                    {"url": "https://nih.gov/a", "title": "NIH", "domain": "nih.gov", "credibility_tier": "high"},
                    {"url": "https://rt.com/b", "title": "RT", "domain": "rt.com", "credibility_tier": "low"},
                    {"url": "https://nytimes.com/c", "title": "NYT", "domain": "nytimes.com", "credibility_tier": "medium"},
                    {"url": "https://unknown.xyz/d", "title": "Unknown", "domain": "unknown.xyz", "credibility_tier": "unknown"},
                ],
                "advocate_challenge": "Challenge.",
                "advocate_counter_sources": [],
                "judge_continuation_reason": None,
            }
        ]
        result = _generate("Sources test.", MINIMAL_VERDICT, rounds)
        assert result[:4] == b"%PDF"


class TestGenerateVerdictPdfAsync:
    async def test_async_wrapper_returns_bytes(self):
        from core import pdf as _pdf_module

        if _ARIAL_AVAILABLE:
            result = await _pdf_module.generate_verdict_pdf_async(
                claim="Async test claim here.",
                verdict=MINIMAL_VERDICT,
                rounds=[],
                analysis_id="00000000-0000-0000-0000-000000000002",
                created_at="2026-03-04T12:00:00",
                llm_provider="anthropic",
                llm_model="claude-sonnet-4-6",
            )
        else:
            original_set_font = FPDF.set_font
            safe_set_font = _safe_set_font_factory(original_set_font)
            with (
                patch.object(_pdf_module, "_add_fonts", _noop_add_fonts),
                patch.object(FPDF, "set_font", safe_set_font),
            ):
                result = await _pdf_module.generate_verdict_pdf_async(
                    claim="Async test claim here.",
                    verdict=MINIMAL_VERDICT,
                    rounds=[],
                    analysis_id="00000000-0000-0000-0000-000000000002",
                    created_at="2026-03-04T12:00:00",
                    llm_provider="anthropic",
                    llm_model="claude-sonnet-4-6",
                )
        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"
