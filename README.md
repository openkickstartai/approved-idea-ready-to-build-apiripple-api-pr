# 🌊 APIRipple — API Change Ripple Analyzer

**Know what breaks before it ships.** APIRipple diffs your OpenAPI specs and traces every breaking change to the exact frontend file and line that will blow up in production.

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Diff two OpenAPI specs
python apiripple.py diff old-spec.yaml new-spec.yaml

# Full analysis: diff + scan frontend code + risk score
python apiripple.py analyze old-spec.yaml new-spec.yaml ./frontend/src

# CI mode: fail if risk > 50, output SARIF for GitHub
python apiripple.py analyze old.yaml new.yaml ./src --format sarif --threshold 50
```

## 📊 Why Teams Pay for APIRipple

| Pain Point | Without APIRipple | With APIRipple |
|---|---|---|
| Breaking API deployed | Find out from Sentry at 2am | Blocked in CI before merge |
| "Which frontends use this endpoint?" | Grep + pray | Exact file:line report |
| Risk assessment | "Looks fine to me" | Quantified 0-100 risk score |
| Compliance audit trail | Nothing | SARIF reports in every PR |

> *"We caught 3 breaking changes in one sprint that would have taken down our React dashboard."* — Early design partner

## 💰 Pricing

| Feature | Free | Pro ($29/mo) | Enterprise ($149/mo) |
|---|:---:|:---:|:---:|
| OpenAPI diff detection | ✅ | ✅ | ✅ |
| Breaking change reports | ✅ | ✅ | ✅ |
| Text + JSON output | ✅ | ✅ | ✅ |
| Endpoints scanned | ≤ 25 | Unlimited | Unlimited |
| Frontend source scanning | — | ✅ | ✅ |
| Risk scoring engine | — | ✅ | ✅ |
| SARIF output for GitHub | — | ✅ | ✅ |
| GitHub Action (prebuilt) | — | ✅ | ✅ |
| Multi-repo consumer scan | — | — | ✅ |
| Slack/Teams notifications | — | — | ✅ |
| Historical trend dashboard | — | — | ✅ |
| SSO + audit logs | — | — | ✅ |
| Priority support | — | — | ✅ |

### Who pays?

**B2B engineering teams (5-200 devs)** with separate backend and frontend repos. Platform teams, API governance leads, and DevOps engineers who are tired of "surprise" breaking changes.

### Why they pay?

One production incident from a missed breaking API change costs 4-40 engineering hours ($1k-$10k+). APIRipple Pro pays for itself the first time it blocks a bad merge.

## ⚙️ CLI Reference

```
apiripple diff OLD NEW [--format text|json]
apiripple analyze OLD NEW SRC_DIR [--format text|json|sarif] [--threshold 50]
```

Exit code `1` = breaking changes detected (or risk above threshold). Perfect for CI.

## 🔌 GitHub Actions

```yaml
- name: APIRipple Check
  run: |
    pip install typer pyyaml
    python apiripple.py analyze spec-old.yaml spec-new.yaml ./frontend/src \
      --format sarif --threshold 40 > ripple.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: ripple.sarif
```

## License

BSL 1.1 — Free for teams ≤ 5 devs. Commercial license required for larger teams.
