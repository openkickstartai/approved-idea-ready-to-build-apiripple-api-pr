"""APIRipple core engine: diff OpenAPI specs, scan consumers, score risk."""
import json
import re
import yaml
from pathlib import Path
from dataclasses import dataclass
from severity import Severity, classify_change

METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}
_VAR_RE = re.compile(r"\{[^}]+\}")
_PH = "__RIPPLE__"
_EXTS = {".ts", ".tsx", ".js", ".jsx", ".vue", ".py", ".go", ".rs", ".kt"}


@dataclass
class Change:
    path: str
    method: str
    kind: str
    detail: str
    severity: str = ""

    def __post_init__(self):
        self.severity = classify_change(self).value


def load_spec(fp):
    """Load an OpenAPI spec from YAML or JSON file.

    Raises:
        FileNotFoundError: if file does not exist.
        ValueError: if file is empty, not valid YAML, or not a mapping.
    """
    p = Path(fp)
    if not p.exists():
        raise FileNotFoundError(f"Spec file not found: {fp}")
    text = p.read_text()
    if not text.strip():
        raise ValueError(f"Spec file is empty: {fp}")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML/JSON in {fp}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(
            f"Spec must be a YAML/JSON mapping, got {type(data).__name__} in {fp}"
        )
    return data


def _resolve_ref(spec, ref):
    """Resolve a JSON-pointer $ref within the spec dict. Returns None on failure."""
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return None
    parts = ref[2:].split("/")
    node = spec
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _flatten_schema(schema, spec, depth=0):
    """Return a dict of {field_name: type_string} for an object schema.

    Follows $ref pointers up to 10 levels deep.
    """
    if depth > 10 or schema is None:
        return {}
    if "$ref" in schema:
        resolved = _resolve_ref(spec, schema["$ref"])
        if resolved:
            return _flatten_schema(resolved, spec, depth + 1)
        return {}
    result = {}
    if schema.get("type") == "object" and "properties" in schema:
        for fname, fschema in schema["properties"].items():
            if "$ref" in fschema:
                result[fname] = f"$ref:{fschema['$ref']}"
            else:
                result[fname] = fschema.get("type", "unknown")
    return result


def _get_response_schema(op_obj, spec):
    """Extract primary response schema (200/201) fields as {field: type}."""
    if not isinstance(op_obj, dict):
        return {}
    responses = op_obj.get("responses", {})
    if not isinstance(responses, dict):
        return {}
    for code in ("200", "201", 200, 201):
        if code not in responses:
            continue
        resp = responses[code]
        if not isinstance(resp, dict):
            continue
        # OpenAPI 3.x
        content = resp.get("content", {})
        if isinstance(content, dict):
            for media in ("application/json",):
                if media in content:
                    schema = content[media].get("schema", {})
                    return _flatten_schema(schema, spec)
        # OpenAPI 2.x / inline
        if "schema" in resp:
            return _flatten_schema(resp["schema"], spec)
    return {}


def _get_params(op_obj):
    """Extract parameters as {name: type_string}."""
    if not isinstance(op_obj, dict):
        return {}
    params = {}
    for p in op_obj.get("parameters", []):
        if not isinstance(p, dict):
            continue
        name = p.get("name", "")
        ptype = p.get("schema", {}).get("type", p.get("type", "unknown"))
        params[name] = ptype
    return params


def diff_specs(old, new):
    """Compare two OpenAPI spec dicts, return list of Change objects."""
    out = []
    op = old.get("paths", {}) or {}
    np_ = new.get("paths", {}) or {}

    # --- Removed / modified endpoints ---
    for path, ops in op.items():
        if not isinstance(ops, dict):
            continue
        if path not in np_:
            for m in ops:
                if m in METHODS:
                    out.append(Change(path, m, "endpoint_removed",
                                      f"{m.upper()} {path} removed"))
            continue

        for m in ops:
            if m not in METHODS:
                continue
            if m not in np_[path]:
                out.append(Change(path, m, "method_removed",
                                  f"{m.upper()} {path} method removed"))
                continue

            old_op = ops[m] if isinstance(ops[m], dict) else {}
            new_op = np_[path][m] if isinstance(np_[path][m], dict) else {}

            # Parameter changes
            old_params = _get_params(old_op)
            new_params = _get_params(new_op)
            for pname, ptype in old_params.items():
                if pname not in new_params:
                    out.append(Change(path, m, "param_removed",
                                      f"Parameter '{pname}' removed from {m.upper()} {path}"))
                elif new_params[pname] != ptype:
                    out.append(Change(path, m, "param_type_changed",
                                      f"Parameter '{pname}' type changed from {ptype} to {new_params[pname]} in {m.upper()} {path}"))
            for pname in new_params:
                if pname not in old_params:
                    out.append(Change(path, m, "param_added",
                                      f"Parameter '{pname}' added to {m.upper()} {path}"))

            # Response schema changes
            old_schema = _get_response_schema(old_op, old)
            new_schema = _get_response_schema(new_op, new)
            for fname, ftype in old_schema.items():
                if fname not in new_schema:
                    out.append(Change(path, m, "response_field_removed",
                                      f"Response field '{fname}' removed from {m.upper()} {path}"))
                elif new_schema[fname] != ftype:
                    out.append(Change(path, m, "response_field_type_changed",
                                      f"Response field '{fname}' type changed from {ftype} to {new_schema[fname]} in {m.upper()} {path}"))
            for fname in new_schema:
                if fname not in old_schema:
                    out.append(Change(path, m, "response_field_added",
                                      f"Response field '{fname}' added to {m.upper()} {path}"))

    # --- New endpoints ---
    for path, ops in np_.items():
        if not isinstance(ops, dict):
            continue
        if path not in op:
            for m in ops:
                if m in METHODS:
                    out.append(Change(path, m, "endpoint_added",
                                      f"{m.upper()} {path} added"))

    return out


def scan_sources(src_dir, changes):
    """Scan source files for references to changed endpoints.

    Returns a list of hit dicts with file, line, endpoint, change, severity.
    """
    hits = []
    src_path = Path(src_dir)
    if not src_path.exists():
        return hits

    patterns = {}
    for c in changes:
        simple = c.path.split("{")[0].rstrip("/")
        if simple:
            patterns[simple] = c

    if not patterns:
        return hits

    for fpath in src_path.rglob("*"):
        if fpath.suffix not in _EXTS:
            continue
        try:
            content = fpath.read_text(errors="ignore")
        except (OSError, IOError):
            continue
        for line_no, line in enumerate(content.splitlines(), 1):
            for pattern, change in patterns.items():
                if pattern in line:
                    hits.append({
                        "file": str(fpath),
                        "line": line_no,
                        "endpoint": f"{change.method.upper()} {change.path}",
                        "change": change.detail,
                        "severity": change.severity,
                    })
    return hits


def score_risk(changes, hits):
    """Compute a 0-100 risk score from changes and affected source hits."""
    if not changes:
        return 0
    score = 0
    for c in changes:
        if c.severity == "breaking":
            score += 15
        elif c.severity == "warning":
            score += 5
        else:
            score += 1
    unique_files = len({h["file"] for h in hits}) if hits else 0
    score += unique_files * 10
    return min(score, 100)


def to_sarif(changes, hits):
    """Convert analysis results to SARIF 2.1.0 format dict."""
    results = []
    for c in changes:
        result = {
            "ruleId": c.kind,
            "level": "error" if c.severity == "breaking" else "warning",
            "message": {"text": c.detail},
            "locations": [],
        }
        for h in hits:
            if h["endpoint"].lower().endswith(c.path):
                result["locations"].append({
                    "physicalLocation": {
                        "artifactLocation": {"uri": h["file"]},
                        "region": {"startLine": h["line"]},
                    }
                })
        results.append(result)
    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "APIRipple", "version": "0.1.0"}},
            "results": results,
        }],
    }
