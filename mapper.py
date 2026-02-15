"""APIRipple mapper: resolve changed endpoints to frontend callers via YAML config."""
import re
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List

_VAR_RE = re.compile(r"\{[^}]+\}")
_PLACEHOLDER = "{*}"


@dataclass
class Caller:
    """A frontend file that calls an API endpoint."""
    file: str
    usage: str


@dataclass
class EndpointMapping:
    """Maps an API endpoint to its frontend callers."""
    endpoint: str
    method: str
    path: str
    callers: List[Caller]


@dataclass
class AffectedCaller:
    """A frontend caller affected by an API change."""
    file: str
    usage: str
    endpoint: str
    change_detail: str
    severity: str


def _normalize_path(path: str) -> str:
    """Normalize path by replacing all {var} segments with a common placeholder."""
    return _VAR_RE.sub(_PLACEHOLDER, path)


def load_mapping(config_path: str) -> List[EndpointMapping]:
    """Load caller mapping from a YAML config file.

    Expected format:
        mappings:
          - endpoint: "GET /api/users/{id}"
            callers:
              - file: "src/components/UserProfile.tsx"
                usage: "useQuery hook"

    Returns list of EndpointMapping objects.
    Raises FileNotFoundError if config_path does not exist.
    """
    text = Path(config_path).read_text()
    data = yaml.safe_load(text)

    if not data or "mappings" not in data:
        return []

    raw_mappings = data["mappings"]
    if not raw_mappings:
        return []

    result: List[EndpointMapping] = []
    for entry in raw_mappings:
        endpoint_str = entry.get("endpoint", "").strip()
        parts = endpoint_str.split(" ", 1)
        if len(parts) == 2:
            method = parts[0].lower()
            path = parts[1].strip()
        else:
            method = ""
            path = parts[0] if parts else ""

        callers: List[Caller] = []
        for c in entry.get("callers", []):
            callers.append(Caller(
                file=c.get("file", ""),
                usage=c.get("usage", ""),
            ))

        result.append(EndpointMapping(
            endpoint=endpoint_str,
            method=method,
            path=path,
            callers=callers,
        ))

    return result


def find_affected_callers(changed_endpoints, mappings: List[EndpointMapping]) -> List[AffectedCaller]:
    """Match Change objects against EndpointMappings, return affected callers.

    Path variables are normalized so {id} matches {user_id} etc.
    Method must match exactly (case-insensitive).
    """
    affected: List[AffectedCaller] = []

    for change in changed_endpoints:
        change_path_norm = _normalize_path(change.path)
        change_method = change.method.lower()

        for mapping in mappings:
            mapping_path_norm = _normalize_path(mapping.path)

            if mapping_path_norm == change_path_norm and mapping.method == change_method:
                for caller in mapping.callers:
                    affected.append(AffectedCaller(
                        file=caller.file,
                        usage=caller.usage,
                        endpoint=mapping.endpoint,
                        change_detail=change.detail,
                        severity=change.severity,
                    ))

    return affected
