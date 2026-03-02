import pytest

from agents.judge import _parse_judge_response


def test_parse_valid_verdict():
    raw = """
Some preamble text.
{
  "continue": false,
  "verdict": {
    "label": "FALSE",
    "confidence": 0.9,
    "summary": "The claim is false.",
    "reasoning": "Detailed reasoning here.",
    "supporting_source_urls": [],
    "contradicting_source_urls": ["https://example.com"]
  }
}
"""
    result = _parse_judge_response(raw)
    assert result["continue"] is False
    assert result["verdict"]["label"] == "FALSE"
    assert result["verdict"]["confidence"] == 0.9


def test_parse_continue_response():
    raw = '{"continue": true, "reason": "Need more evidence about X."}'
    result = _parse_judge_response(raw)
    assert result["continue"] is True
    assert "evidence" in result["reason"]


def test_parse_markdown_code_fence():
    raw = """Here is my verdict:
```json
{
  "continue": false,
  "verdict": {
    "label": "FALSE",
    "confidence": 0.95,
    "summary": "The claim is false.",
    "reasoning": "### Evidence\n- Point 1 {note} end\n- Point 2",
    "supporting_source_urls": [],
    "contradicting_source_urls": ["https://example.com"]
  }
}
```"""
    result = _parse_judge_response(raw)
    assert result["continue"] is False
    assert result["verdict"]["label"] == "FALSE"
    assert result["verdict"]["confidence"] == 0.95


def test_parse_reasoning_with_curly_braces():
    raw = """{
  "continue": false,
  "verdict": {
    "label": "MISLEADING",
    "confidence": 0.8,
    "summary": "Misleading claim.",
    "reasoning": "The formula {x + y = z} is relevant here.",
    "supporting_source_urls": [],
    "contradicting_source_urls": []
  }
}"""
    result = _parse_judge_response(raw)
    assert result["continue"] is False
    assert result["verdict"]["label"] == "MISLEADING"


def test_parse_fallback_on_invalid_json():
    raw = "Sorry, I cannot provide a JSON response right now."
    result = _parse_judge_response(raw)
    assert result["continue"] is True
    assert isinstance(result["reason"], str)
