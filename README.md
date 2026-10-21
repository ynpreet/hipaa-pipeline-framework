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
  trail for governed and quarantined records; every entry carries a
  UTC timestamp, and `AuditLog.entries()` reads the trail back in
  order for review.
- `hipaa_pipeline_framework/config.py` — pipeline config template
  with secure defaults (encryption at rest, audit on, quarantine on
  failure, no PHI in logs) plus validation that refuses insecure
  overrides.
- `hipaa_pipeline_framework/pipeline.py` — `run_pipeline`: ties the
  blocks together — refuses insecure configs (fail closed), runs
  every record through the quality gates, quarantines failures with
  a reason, and writes one audit entry per record when given an
  AuditLog. Returns governed records, quarantined pairs, and
  per-reason counts.
- `examples/run_demo.py` — end-to-end demo on synthetic data.

## Quickstart

```bash
python3 examples/run_demo.py
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

12 stdlib-only tests (Oct 21, 2026, all passing): hash determinism and
uniqueness, identifier stripping, every quality gate (missing field,
impossible/non-ISO date, invalid amount, duplicate), audit-log
JSON-lines output, and secure-default config validation (defaults
secure, each insecure override flagged, defaults are fresh copies).
No dependencies, no real patient data.

Oct 21, 2026 build block (11:00 AM run): pipeline orchestrator
(`hipaa_pipeline_framework/pipeline.py`, `run_pipeline`) tying config
+ quality gates + audit together, fail-closed on insecure configs;
3 new tests (suite now 15, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged).

Oct 21, 2026 build block (11:30 AM run): timestamped audit trail
(`AuditLog.entries()` read-back, UTC timestamp on every entry);
1 new test (suite now 16, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged).

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
