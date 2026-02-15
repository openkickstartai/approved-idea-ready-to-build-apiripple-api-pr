"""Tests for APIRipple core analyzer — 7 test cases."""
import tempfile
from pathlib import Path
from analyzer import diff_specs, scan_sources, score_risk, to_sarif

OLD = {"openapi": "3.0.0", "paths": {
    "/users": {"get": {"parameters": [{"name": "limit", "in": "query"}],
                       "responses": {"200": {}}}},
    "/users/{id}": {"get": {"parameters": [{"name": "id", "in": "path"}],
                            "responses": {"200": {}}},
                     "delete": {"responses": {"204": {}}}},
    "/legacy/health": {"get": {"responses": {"200": {}}}}
}}

NEW = {"openapi": "3.0.0", "paths": {
    "/users": {"get": {"parameters": [
        {"name": "limit", "in": "query"},
        {"name": "org_id", "in": "query", "required": True}
    ], "responses": {"200": {}}}},
    "/users/{id}": {"get": {"parameters": [{"name": "id", "in": "path"}],
                            "responses": {}}}
}}


def test_detects_removed_endpoint():
    changes = diff_specs(OLD, NEW)
    removed = [c for c in changes if c.kind == "endpoint_removed"]
    assert any("/legacy/health" in c.path for c in removed)
    assert all(c.severity == "breaking" for c in removed)


def test_detects_removed_method():
    changes = diff_specs(OLD, NEW)
    removed = [c for c in changes if c.kind == "method_removed"]
    assert len(removed) == 1
    assert removed[0].path == "/users/{id}"
    assert removed[0].method == "delete"


def test_detects_added_required_param():
    changes = diff_specs(OLD, NEW)
    added = [c for c in changes if c.kind == "param_added"]
    assert len(added) == 1
    assert "org_id" in added[0].detail
    assert added[0].severity == "warning"



def test_detects_removed_response_code():
    changes = diff_specs(OLD, NEW)
    resp = [c for c in changes if c.kind == "response_removed"]
    assert len(resp) == 1
    assert "200" in resp[0].detail
    assert resp[0].severity == "warning"


def test_scan_finds_affected_source_files():
    changes = diff_specs(OLD, NEW)
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "UserList.tsx").write_text(
            'export const list = () => fetch("/users");\n')
        (Path(d) / "UserDetail.tsx").write_text(
            'const rm = () => api.delete(`/users/${userId}`);\n')
        (Path(d) / "docs.md").write_text("/users endpoint\n")
        hits = scan_sources(d, changes)
        assert len(hits) >= 2
        assert all(h["file"].endswith(".tsx") for h in hits)


def test_risk_score_increases_with_hits():
    changes = diff_specs(OLD, NEW)
    score_empty = score_risk(changes, [])
    many_hits = [{"file": "a.ts", "line": 1, "api_path": "/x", "code": ""}] * 10
    score_full = score_risk(changes, many_hits)
    assert 0 < score_empty < score_full <= 100
    assert score_risk([], []) == 0


def test_sarif_output_structure():
    hits = [{"file": "App.tsx", "line": 42, "api_path": "/users",
             "code": "fetch('/users')"}]
    sarif = to_sarif([], hits)
    assert sarif["version"] == "2.1.0"
    results = sarif["runs"][0]["results"]
    assert len(results) == 1
    loc = results[0]["locations"][0]["physicalLocation"]
    assert loc["region"]["startLine"] == 42
    assert loc["artifactLocation"]["uri"] == "App.tsx"
