"""APIRipple core engine: diff OpenAPI specs, scan consumers, score risk."""
import json
import re
import yaml
from pathlib import Path
from dataclasses import dataclass

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
    severity: str


def load_spec(fp):
    """Load an OpenAPI spec from YAML or JSON file."""
    text = Path(fp).read_text()
    return json.loads(text) if fp.endswith(".json") else yaml.safe_load(text)


def diff_specs(old, new):
    """Compare two OpenAPI spec dicts, return list of Change objects."""
    out = []
    op, np = old.get("paths", {}), new.get("paths", {})
    for path, ops in op.items():
        if path not in np:
            for m in ops:
                if m in METHODS:
                    out.append(Change(path, m, "endpoint_removed",
                                      f"{m.upper()} {path} removed", "breaking"))
            continue
        for m in ops:
            if m not in METHODS:
                continue
            if m not in np[path]:
                out.append(Change(path, m, "method_removed",
                                  f"{m.upper()} removed from {path}", "breaking"))
                continue
            old_p = {p["name"]: p for p in ops[m].get("parameters", []) if "name" in p}
            new_p = {p["name"]: p for p in np[path][m].get("parameters", []) if "name" in p}
            for n in old_p:
                if n not in new_p:
                    out.append(Change(path, m, "param_removed",
                                      f"Param '{n}' removed from {m.upper()} {path}", "breaking"))
            for n in new_p:
                if n not in old_p and new_p[n].get("required"):
                    out.append(Change(path, m, "param_added",
                                      f"Required param '{n}' added to {m.upper()} {path}", "breaking"))
            for code in set(ops[m].get("responses", {})) - set(np[path][m].get("responses", {})):
                out.append(Change(path, m, "response_removed",
                                  f"Response {code} removed from {m.upper()} {path}", "warning"))
    return out


def _to_re(api_path):
    """Convert OpenAPI path template to regex for source scanning."""
    escaped = re.escape(_VAR_RE.sub(_PH, api_path))
    return re.compile(escaped.replace(_PH, ".+"))


def scan_sources(src_dir, changes):
    """Scan source files for references to changed API endpoints."""
    hits = []
    pats = {c.path: _to_re(c.path) for c in changes}
    for f in Path(src_dir).rglob("*"):
        if f.suffix not in _EXTS or not f.is_file():
            continue
        try:
            lines = f.read_text(errors="ignore").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            for ap, pat in pats.items():
                if pat.search(line):
                    hits.append({"file": str(f), "line": i, "api_path": ap,
                                 "code": line.strip()[:120]})
    return hits


def score_risk(changes, hits):
    """Compute 0-100 risk score from changes and affected call sites."""
    weights = {"breaking": 10, "warning": 3, "info": 1}
    base = sum(weights.get(c.severity, 1) for c in changes)
    return min(100, base + len(hits) * 2)


def to_sarif(changes, hits):
    """Generate SARIF 2.1.0 report for GitHub Code Scanning."""
    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "APIRipple", "version": "1.0.0",
                  "rules": [{"id": "apiripple/breaking-change",
                              "shortDescription": {"text": "API consumer affected by breaking change"}}]}},
                  "results": [{"ruleId": "apiripple/breaking-change",
                               "message": {"text": f"Affected by change to {h['api_path']}"},
                               "locations": [{"physicalLocation": {
                                   "artifactLocation": {"uri": h["file"]},
                                   "region": {"startLine": h["line"]}}}]}
                              for h in hits]}]}
