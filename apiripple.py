#!/usr/bin/env python3
"""🌊 APIRipple CLI — API change ripple analyzer."""
import json
import typer
from analyzer import load_spec, diff_specs, scan_sources, score_risk, to_sarif

app = typer.Typer(help="🌊 APIRipple — Catch breaking API changes before they break prod.")


@app.command()
def diff(old: str = typer.Argument(..., help="Path to old OpenAPI spec"),
         new: str = typer.Argument(..., help="Path to new OpenAPI spec"),
         fmt: str = typer.Option("text", "--format", "-f", help="text|json")):
    """Diff two OpenAPI specs and list breaking changes."""
    changes = diff_specs(load_spec(old), load_spec(new))
    if fmt == "json":
        typer.echo(json.dumps([c.__dict__ for c in changes], indent=2))
    else:
        if not changes:
            typer.echo("✅ No breaking changes detected.")
            raise typer.Exit(0)
        for c in changes:
            icon = "🔴" if c.severity == "breaking" else "🟡"
            typer.echo(f"  {icon} [{c.severity.upper()}] {c.detail}")
        brk = sum(1 for c in changes if c.severity == "breaking")
        typer.echo(f"\n  📋 {len(changes)} change(s), {brk} breaking")
    raise typer.Exit(1 if any(c.severity == "breaking" for c in changes) else 0)


@app.command()
def analyze(old: str = typer.Argument(..., help="Old OpenAPI spec"),
            new: str = typer.Argument(..., help="New OpenAPI spec"),
            src: str = typer.Argument(..., help="Source directory to scan"),
            fmt: str = typer.Option("text", "--format", "-f", help="text|json|sarif"),
            threshold: int = typer.Option(50, "--threshold", "-t",
                                          help="Risk score threshold to fail CI (0-100)")):
    """Full pipeline: diff specs → scan consumers → risk score."""
    changes = diff_specs(load_spec(old), load_spec(new))
    hits = scan_sources(src, changes) if changes else []
    risk = score_risk(changes, hits)
    if fmt == "sarif":
        typer.echo(json.dumps(to_sarif(changes, hits), indent=2))
    elif fmt == "json":
        typer.echo(json.dumps({"changes": [c.__dict__ for c in changes],
                                "hits": hits, "risk_score": risk}, indent=2))
    else:
        typer.echo(f"\n🌊 APIRipple Analysis Report\n{'=' * 42}")
        for c in changes:
            icon = "🔴" if c.severity == "breaking" else "🟡"
            typer.echo(f"  {icon} {c.detail}")
        if not changes:
            typer.echo("  ✅ No API changes detected.")
        typer.echo(f"\n📍 Affected call sites: {len(hits)}")
        for h in hits[:15]:
            typer.echo(f"  → {h['file']}:{h['line']}  ← {h['api_path']}")
        if len(hits) > 15:
            typer.echo(f"  ... and {len(hits) - 15} more (use --format json)")
        status = "🟢" if risk < threshold else "🔴"
        typer.echo(f"\n{status} Risk Score: {risk}/100 (threshold: {threshold})")
    raise typer.Exit(1 if risk >= threshold else 0)


if __name__ == "__main__":
    app()
