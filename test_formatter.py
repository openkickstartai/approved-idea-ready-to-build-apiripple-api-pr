"""Tests for APIRipple formatter — 9 test cases covering text, JSON, and markdown."""
import json
import pytest
from formatter import format_results, format_text, format_json, format_markdown


SAMPLE_CHANGES = [
    {
        "path": "/users",
        "method": "get",
        "kind": "param_added",
        "detail": "Required param 'org_id' added to GET /users",
        "severity": "breaking",
    },
    {
        "path": "/legacy/health",
        "method": "get",
        "kind": "endpoint_removed",
        "detail": "GET /legacy/health removed",
        "severity": "breaking",
    },
    {
        "path": "/users/{id}",
        "method": "delete",
        "kind": "method_removed",
        "detail": "DELETE removed from /users/{id}",
        "severity": "breaking",
    },
]

SAMPLE_HITS = [
    {"file": "src/api/users.ts", "line": 42, "endpoint": "/users"},
    {"file": "src/components/Health.tsx", "line": 15, "endpoint": "/legacy/health"},
]

FULL_RESULTS = {
    "changes": SAMPLE_CHANGES,
    "hits": SAMPLE_HITS,
    "risk_score": 75,
}

EMPTY_RESULTS = {"changes": [], "hits": [], "risk_score": None}

CHANGES_ONLY = {"changes": SAMPLE_CHANGES, "hits": [], "risk_score": None}


# --- Text format tests ---

def test_text_format_displays_changes():
    """Text output should list all changed endpoints with severity icons."""
    output = format_results(FULL_RESULTS, "text")
    assert "/users" in output
    assert "/legacy/health" in output
    assert "/users/{id}" in output
    assert "🔴" in output  # breaking changes get red icon
    assert "3 change(s)" in output
    assert "3 breaking" in output


def test_text_format_empty_shows_no_changes():
    """Text output with no changes should show success message."""
    output = format_results(EMPTY_RESULTS, "text")
    assert "No breaking changes" in output
    assert "✅" in output


# --- JSON format tests ---

def test_json_format_is_valid_json():
    """JSON output must be parseable by json.loads()."""
    output = format_results(FULL_RESULTS, "json")
    parsed = json.loads(output)
    assert isinstance(parsed, dict)


def test_json_format_contains_all_data():
    """JSON output should preserve all changes, hits, and risk_score."""
    output = format_results(FULL_RESULTS, "json")
    parsed = json.loads(output)
    assert len(parsed["changes"]) == 3
    assert len(parsed["hits"]) == 2
    assert parsed["risk_score"] == 75
    # Verify change structure
    change = parsed["changes"][0]
    assert "path" in change
    assert "method" in change
    assert "kind" in change
    assert "detail" in change
    assert "severity" in change


def test_json_format_empty_results():
    """JSON output with empty results should still be valid JSON."""
    output = format_results(EMPTY_RESULTS, "json")
    parsed = json.loads(output)
    assert parsed["changes"] == []
    assert parsed["hits"] == []
    assert parsed["risk_score"] is None


# --- Markdown format tests ---

def test_markdown_format_has_endpoint_table():
    """Markdown output should include a changed endpoints table."""
    output = format_results(FULL_RESULTS, "markdown")
    # Table header row
    assert "| Severity |" in output
    assert "| Method |" in output or "Method" in output
    # Table separator
    assert "|--------" in output
    # Endpoint paths in backticks
    assert "`/users`" in output
    assert "`/legacy/health`" in output
    assert "`/users/{id}`" in output


def test_markdown_format_has_warning_emoji():
    """Markdown output with breaking changes should include ⚠️ emoji."""
    output = format_results(FULL_RESULTS, "markdown")
    assert "⚠️" in output


def test_markdown_format_has_affected_components():
    """Markdown output should list affected frontend components."""
    output = format_results(FULL_RESULTS, "markdown")
    assert "Affected Components" in output
    assert "`src/api/users.ts`" in output
    assert "`src/components/Health.tsx`" in output
    assert "42" in output
    assert "15" in output


def test_markdown_format_empty_shows_success():
    """Markdown output with no changes should show success header."""
    output = format_results(EMPTY_RESULTS, "markdown")
    assert "No breaking changes" in output
    assert "✅" in output


# --- Error handling ---

def test_format_results_rejects_unknown_format():
    """format_results should raise ValueError for unsupported format types."""
    with pytest.raises(ValueError, match="Unknown format"):
        format_results(FULL_RESULTS, "xml")
