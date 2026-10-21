# hipaa-pipeline-framework

Reusable, HIPAA-oriented building blocks for healthcare data pipelines,
distilled from the generic patterns in "Data Engineering for Healthcare:
Building HIPAA-Ready Data Pipelines" (book manuscript by Preet Mehta).

No employer data, no client details, no real patient data anywhere
in this repo. Demos use synthetic data only.

## Modules

- `hipaa_pipeline_framework/deidentification.py` — Safe Harbor style
  identifier handling: one-way member-ID hashing, identifier stripping.
- `hipaa_pipeline_framework/quality.py` — data-quality gates for
  claims-like records: required fields, real-calendar date validation,
  positive amounts, dedupe. Failures are quarantined with a reason,
  never silently dropped.
- `hipaa_pipeline_framework/audit.py` — append-only JSON-lines audit
  trail for governed and quarantined records.
- `examples/run_demo.py` — end-to-end demo on synthetic data.

## Quickstart

```bash
python3 examples/run_demo.py
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

9 stdlib-only tests (Oct 21, 2026, all passing): hash determinism and
uniqueness, identifier stripping, every quality gate (missing field,
impossible/non-ISO date, invalid amount, duplicate), and audit-log
JSON-lines output. No dependencies, no real patient data.

## Measured demo run (Oct 21, 2026, seed 42, synthetic data only)

- Records in: 10,000
- Records governed: 1,589
- Records quarantined: 8,411 — missing field 3,557; unparseable date
  3,198 (including Feb 30 and non-ISO formats); invalid amount 1,646;
  duplicate 10
- Runtime: ~0.4 seconds on this run (audit writes included)
- Output has no raw member IDs (SHA-256 hashed) and no patient-name
  column. The quarantine rate is a property of the seeded demo defects,
  not of any real dataset.

## Status

v0.1, Oct 21, 2026. See PLAN.md for the roadmap and the adoption
evidence plan (PyPI/GitHub stats tracked with dates, named adopters
logged with links — no invented metrics, ever).
