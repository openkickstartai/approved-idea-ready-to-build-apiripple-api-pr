"""APIRipple output formatters: text, JSON, and GitHub PR comment markdown."""
import json
from typing import Any, Dict


def format_text(results: Dict[str, Any]) -> str:
    """Human-readable terminal output with icons and summary."""
    lines = []
    changes = results.get("changes", [])
    hits = results.get("hits", [])
    risk_score = results.get("risk_score")

    if not changes:
        lines.append("✅ No breaking changes detected.")
        return "\n".join(lines)

    lines.append("🌊 APIRipple — Change Report")
    lines.append("=" * 50)
    lines.append("")

    # Changes list
    lines.append("Changed Endpoints:")
    lines.append(f"  {'Severity':<12} {'Method':<8} {'Path':<30} {'Kind':<20} Detail")
    lines.append("  " + "-" * 90)
    for c in changes:
        sev = c.get("severity", "unknown")
        icon = "🔴" if sev == "breaking" else "🟡"
        method = c.get("method", "").upper()
        path = c.get("path", "")
        kind = c.get("kind", "")
        detail = c.get("detail", "")
        lines.append(f"  {icon} {sev:<10} {method:<8} {path:<30} {kind:<20} {detail}")

    brk = sum(1 for c in changes if c.get("severity") == "breaking")
    lines.append(f"\n  📋 {len(changes)} change(s), {brk} breaking")

    # Affected components
    if hits:
        lines.append("")
        lines.append("Affected Components:")
        for h in hits:
            file = h.get("file", "")
            line = h.get("line", "")
            endpoint = h.get("endpoint", "")
            lines.append(f"  📄 {file}:{line} → {endpoint}")

    # Risk score
    if risk_score is not None:
        lines.append("")
        lines.append(f"  🎯 Risk Score: {risk_score}/100")

    return "\n".join(lines)


def format_json(results: Dict[str, Any]) -> str:
    """Structured JSON output for CI pipeline consumption."""
    return json.dumps(results, indent=2, default=str)


def format_markdown(results: Dict[str, Any]) -> str:
    """GitHub PR comment markdown with ⚠️ emoji and tables."""
    lines = []
    changes = results.get("changes", [])
    hits = results.get("hits", [])
    risk_score = results.get("risk_score")

    if not changes:
        lines.append("## ✅ APIRipple: No breaking changes detected")
        return "\n".join(lines)

    brk = sum(1 for c in changes if c.get("severity") == "breaking")

    if brk > 0:
        lines.append("## ⚠️ APIRipple: Breaking Changes Detected")
    else:
        lines.append("## 🟡 APIRipple: API Changes Detected")
    lines.append("")

    # Risk score badge
    if risk_score is not None:
        if risk_score >= 70:
            lines.append(f"**🔴 Risk Score: {risk_score}/100** — High risk, review carefully!")
        elif risk_score >= 40:
            lines.append(f"**🟡 Risk Score: {risk_score}/100** — Moderate risk")
        else:
            lines.append(f"**🟢 Risk Score: {risk_score}/100** — Low risk")
        lines.append("")

    # Changed endpoints table
    lines.append("### Changed Endpoints")
    lines.append("")
    lines.append("| Severity | Method | Path | Kind | Detail |")
    lines.append("|----------|--------|------|------|--------|")
    for c in changes:
        sev = c.get("severity", "unknown")
        icon = "⚠️" if sev == "breaking" else "🟡"
        method = c.get("method", "").upper()
        path = c.get("path", "")
        kind = c.get("kind", "")
        detail = c.get("detail", "")
        lines.append(f"| {icon} {sev} | {method} | `{path}` | {kind} | {detail} |")

    lines.append("")
    lines.append(f"**Total:** {len(changes)} change(s), {brk} breaking")

    # Affected components table
    if hits:
        lines.append("")
        lines.append("### Affected Components")
        lines.append("")
        lines.append("| File | Line | Endpoint |")
        lines.append("|------|------|----------|")
        for h in hits:
            file = h.get("file", "")
            line = h.get("line", "")
            endpoint = h.get("endpoint", "")
            lines.append(f"| `{file}` | {line} | `{endpoint}` |")

    return "\n".join(lines)


def format_results(results: Dict[str, Any], format_type: str = "text") -> str:
    """Format analysis results in the specified output format.

    Args:
        results: Dict with keys 'changes' (list of change dicts),
                 optional 'hits' (list of consumer hit dicts),
                 optional 'risk_score' (int or None).
        format_type: One of 'text', 'json', 'markdown'.

    Returns:
        Formatted string ready for output.

    Raises:
        ValueError: If format_type is not recognized.
    """
    formatters = {
        "text": format_text,
        "json": format_json,
        "markdown": format_markdown,
    }
    formatter = formatters.get(format_type)
    if formatter is None:
        raise ValueError(
            f"Unknown format: '{format_type}'. "
            f"Supported formats: {', '.join(sorted(formatters.keys()))}"
        )
    return formatter(results)
