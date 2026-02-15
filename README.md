# 🌊 APIRipple — API Change Ripple Analyzer

**Know what breaks before it ships.** APIRipple diffs your OpenAPI specs and traces every breaking change to the exact frontend file and line that will blow up in production.

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```bash
# Diff two OpenAPI specs
python apiripple.py diff old-spec.yaml new-spec.yaml

# Diff with JSON output
python apiripple.py diff old-spec.yaml new-spec.yaml --format json

# Full analysis: diff + scan frontend code + risk score
python apiripple.py analyze old-spec.yaml new-spec.yaml ./frontend/src

# CI mode: fail if risk > 50, output SARIF for GitHub
python apiripple.py analyze old.yaml new.yaml ./src --format sarif --threshold 50
```

### Example Output

```
🌊 APIRipple — Change Report
==================================================

  🔴 [BREAKING] DELETE /api/users/{id} removed
  🟡 [WARNING]  PUT /api/users/{id} request body field 'email' removed

  📋 2 change(s), 1 breaking

  Affected files:
    📄 src/components/UserProfile.tsx:42 → DELETE /api/users/{id}

  🎯 Risk Score: 73/100
```

## ⚙️ Configuration

Create a `.apiripple.yml` file in your project root to customize behavior:

```yaml
# .apiripple.yml — APIRipple project configuration

# Plan: free | pro | team
# Free: up to 20 endpoints, text/json output only
# Pro/Team: unlimited endpoints, all output formats
plan: free

# Default output format (overridden by --format CLI flag)
output_format: text

# Endpoints to exclude from analysis
ignored_endpoints:
  - /health
  - /metrics
  - /internal/debug

# Path to caller mapping file for precise impact analysis
mapping_file: apiripple-mappings.yml
```

### Configuration Priority

Settings are resolved with the following priority (highest wins):

1. **CLI arguments** — `--format json` always wins
2. **Config file** — `.apiripple.yml` values
3. **Defaults** — `plan: free`, `output_format: text`

APIRipple automatically discovers `.apiripple.yml` by walking up from the current directory.

### Caller Mapping File

For precise impact analysis, create a mapping file:

```yaml
# apiripple-mappings.yml
mappings:
  - endpoint: "GET /api/users/{id}"
    callers:
      - file: "src/components/UserProfile.tsx"
        usage: "useQuery hook on line 42"
      - file: "src/pages/Settings.tsx"
        usage: "fetchUser() call"
  - endpoint: "POST /api/orders"
    callers:
      - file: "src/components/Checkout.tsx"
        usage: "submitOrder mutation"
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
| Endpoints scanned | ≤ 20 | Unlimited | Unlimited |
| Markdown output | — | ✅ | ✅ |
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

**B2B engineering teams (5-200 devs)** with separate backend and frontend repos.
Teams that have been burned by breaking API changes in production.

→ [**Upgrade to Pro**](https://apiripple.dev/pricing) for unlimited endpoints and all output formats.

## 🛠️ Development

```bash
# Run tests
pytest test_config.py -v

# Run all tests
pytest -v
```

## 📄 License

BSL 1.1 — Free for teams under 5 devs. [Contact us](https://apiripple.dev/pricing) for commercial licensing.
