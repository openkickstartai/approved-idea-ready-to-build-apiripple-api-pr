"""Tests for APIRipple mapper — 9 test cases."""
import tempfile
import pytest
from pathlib import Path
from mapper import load_mapping, find_affected_callers, AffectedCaller, EndpointMapping, Caller
from analyzer import Change


SAMPLE_MAPPING = """\
mappings:
  - endpoint: "GET /api/users/{id}"
    callers:
      - file: "src/components/UserProfile.tsx"
        usage: "useQuery hook"
      - file: "src/pages/Dashboard.vue"
        usage: "fetch in mounted"
  - endpoint: "DELETE /api/users/{id}"
    callers:
      - file: "src/components/UserAdmin.tsx"
        usage: "useMutation hook"
  - endpoint: "GET /api/orders"
    callers:
      - file: "src/pages/Orders.tsx"
        usage: "useQuery hook"
"""


def _write_temp_yaml(content: str) -> str:
    """Write content to a temp YAML file, return path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
    f.write(content)
    f.flush()
    f.close()
    return f.name


def test_load_mapping_valid():
    """Valid YAML is parsed into correct EndpointMapping objects."""
    path = _write_temp_yaml(SAMPLE_MAPPING)
    mappings = load_mapping(path)
    assert len(mappings) == 3
    assert mappings[0].method == "get"
    assert mappings[0].path == "/api/users/{id}"
    assert len(mappings[0].callers) == 2
    assert mappings[0].callers[0].file == "src/components/UserProfile.tsx"
    assert mappings[0].callers[0].usage == "useQuery hook"
    assert mappings[1].method == "delete"
    assert mappings[2].path == "/api/orders"


def test_load_mapping_empty_no_key():
    """YAML without 'mappings' key returns empty list."""
    path = _write_temp_yaml("some_other_key: true\n")
    mappings = load_mapping(path)
    assert mappings == []


def test_load_mapping_empty_list():
    """YAML with empty mappings list returns empty list."""
    path = _write_temp_yaml("mappings: []\n")
    mappings = load_mapping(path)
    assert mappings == []


def test_load_mapping_file_not_found():
    """Non-existent config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_mapping("/tmp/nonexistent_apiripple_test_cfg_12345.yml")


def test_find_affected_callers_matching():
    """Changes matching a mapped endpoint return all its callers."""
    path = _write_temp_yaml(SAMPLE_MAPPING)
    mappings = load_mapping(path)
    changes = [
        Change(path="/api/users/{id}", method="get", kind="param_removed",
               detail="Param 'fields' removed from GET /api/users/{id}",
               severity="breaking"),
    ]
    affected = find_affected_callers(changes, mappings)
    assert len(affected) == 2
    files = {a.file for a in affected}
    assert "src/components/UserProfile.tsx" in files
    assert "src/pages/Dashboard.vue" in files
    assert all(a.severity == "breaking" for a in affected)
    assert all(a.change_detail == changes[0].detail for a in affected)


def test_find_affected_callers_no_match():
    """Changes for unmapped endpoints return empty list."""
    path = _write_temp_yaml(SAMPLE_MAPPING)
    mappings = load_mapping(path)
    changes = [
        Change(path="/api/products", method="get", kind="endpoint_removed",
               detail="GET /api/products removed", severity="breaking"),
    ]
    affected = find_affected_callers(changes, mappings)
    assert affected == []


def test_find_affected_callers_path_variable_normalization():
    """Different path variable names ({id} vs {user_id}) still match."""
    path = _write_temp_yaml(SAMPLE_MAPPING)
    mappings = load_mapping(path)
    changes = [
        Change(path="/api/users/{user_id}", method="get", kind="param_removed",
               detail="Param removed", severity="breaking"),
    ]
    affected = find_affected_callers(changes, mappings)
    assert len(affected) == 2
    files = {a.file for a in affected}
    assert "src/components/UserProfile.tsx" in files
    assert "src/pages/Dashboard.vue" in files


def test_find_affected_callers_method_mismatch():
    """Same path but different HTTP method does not match."""
    path = _write_temp_yaml(SAMPLE_MAPPING)
    mappings = load_mapping(path)
    changes = [
        Change(path="/api/users/{id}", method="post", kind="method_removed",
               detail="POST removed", severity="breaking"),
    ]
    affected = find_affected_callers(changes, mappings)
    assert affected == []


def test_find_affected_callers_multiple_changes():
    """Multiple changes affecting different mappings aggregate correctly."""
    path = _write_temp_yaml(SAMPLE_MAPPING)
    mappings = load_mapping(path)
    changes = [
        Change(path="/api/users/{id}", method="delete", kind="method_removed",
               detail="DELETE /api/users/{id} removed", severity="breaking"),
        Change(path="/api/orders", method="get", kind="param_added",
               detail="Required param 'org' added to GET /api/orders",
               severity="breaking"),
    ]
    affected = find_affected_callers(changes, mappings)
    assert len(affected) == 2
    files = {a.file for a in affected}
    assert "src/components/UserAdmin.tsx" in files
    assert "src/pages/Orders.tsx" in files
    # Verify each affected caller has the correct cause
    admin = [a for a in affected if a.file == "src/components/UserAdmin.tsx"][0]
    assert "DELETE" in admin.change_detail
    orders = [a for a in affected if a.file == "src/pages/Orders.tsx"][0]
    assert "org" in orders.change_detail
