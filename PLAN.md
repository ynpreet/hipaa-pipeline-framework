# Lane 3 — HIPAA-ready data pipeline framework (Preet's own project)

Started Oct 20, 2026 on Preet's "research and act / start", following the
EB-1A criteria research: an owned artifact is the only Criterion 5 asset
fully under his control. Patterns derive from his book manuscript
"Data Engineering for Healthcare" (generic patterns only — no employer
data, no client details, no Adobe mentions).

## What it is
A small, genuinely useful open-source Python framework of reusable,
HIPAA-oriented pipeline building blocks for healthcare data engineering:
- de-identification helpers (Safe Harbor identifier handling)
- PHI access audit logging patterns
- data-quality gates for clinical datasets
- pipeline config templates with encryption/access-control defaults

## Status
- SCAFFOLD ONLY (this folder). Not published. Publishing the public repo
  under ynpreet needs Preet's explicit tap (submit-permission rule).
- Next steps when he taps: create repo via browser (connector cannot),
  push scaffold, PyPI packaging, README with quickstart.

## Adoption evidence plan (from day one — adoption must predate filing)
- PyPI download stats tracked monthly (trend, not snapshot)
- GitHub dependents / "used by" watched; named adopters logged with links
- Issues/PRs from outside users welcomed and logged
- Write-ups (his Substack/LinkedIn series) driving real users to it
- Letter writers: adopters and healthcare-data experts who actually used it

## Guardrails
- Generic patterns only; nothing from EXL/Adobe work product.
- No invented metrics, ever. Numbers enter the evidence log only from
  PyPI/GitHub dashboards with dates and screenshots (URL visible).
