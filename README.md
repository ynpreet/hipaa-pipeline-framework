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
  UTC timestamp, `AuditLog.entries()` reads the trail back in
  order for review, and `AuditLog.summary()` tallies the trail by
  action and by quarantine reason.
- `hipaa_pipeline_framework/config.py` — pipeline config template
  with secure defaults (encryption at rest, audit on, quarantine on
  failure, no PHI in logs) plus validation that refuses insecure
  overrides.
- `hipaa_pipeline_framework/pipeline.py` — `run_pipeline`: ties the
  blocks together — refuses insecure configs (fail closed), runs
  every record through the quality gates, quarantines failures with
  a reason, and writes one audit entry per record when given an
  AuditLog. Returns governed records, quarantined pairs, and
  per-reason counts. `summarize_run` turns that result into a
  plain, record-free summary dict (counts, quarantine rate, and
  per-reason tallies) safe to log or paste into a report.
- `hipaa_pipeline_framework/io.py` — CSV in/out: `read_claims_csv`
  reads raw claims rows for `run_pipeline`, and fails closed on a
  malformed file — a header missing any of REQUIRED_COLUMNS
  (`member_id`, `service_date`, `claim_amount`) raises ValueError
  naming the missing columns instead of quarantining every row;
  `write_governed_csv`
  writes only the fixed de-identified columns, dropping any raw
  identifier that slipped into a record dict; `write_quarantine_csv`
  writes quarantined (record, reason) pairs the same way — member
  hash plus reason, never a raw member ID or patient name;
  `write_audit_csv` exports an AuditLog's trail to CSV (one row per
  entry, fixed audit columns) for reviewers who work in
  spreadsheets — the trail stores only hashes and "redacted"
  markers, so the export carries no raw identifiers;
  `write_summary_json` writes a `summarize_run` summary dict
  (counts, quarantine rate, per-reason tallies, no record data)
  to sorted, diff-friendly JSON for filing or reporting.
- `examples/run_demo.py` — end-to-end demo on synthetic data, via the
  `run_pipeline` orchestrator (secure defaults, gates, quarantine,
  audit trail).

## Quickstart

```bash
python3 examples/run_demo.py
```

Or run any claims CSV through the pipeline from the command line
(secure defaults, fail closed; prints only the run summary):

```bash
python3 -m hipaa_pipeline_framework input.csv \
  --governed governed.csv --quarantine quarantine.csv \
  --audit audit.jsonl --audit-csv audit.csv \
  --summary-json summary.json
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

35 stdlib-only tests (Oct 22, 2026, all passing): hash determinism and
uniqueness, identifier stripping, every quality gate (missing field,
impossible/non-ISO date, invalid amount, duplicate), audit-log
JSON-lines output, read-back, and summary tallies, secure-default config validation
(defaults secure, each insecure override flagged, defaults are fresh
copies), pipeline orchestration (govern/quarantine, counts,
fail-closed config, one audit entry per record, run-summary counts
and quarantine rate), and CSV I/O (rows
feed the pipeline, governed CSV drops identifiers, quarantine CSV
writes hashes not raw IDs, audit CSV exports the trail rows,
empty writes still write the header), and the CLI (de-identified
outputs + summary on a real CSV, missing input exits 2, optional
--summary-json writes the summary file and is absent when the flag
is omitted, bad-header input exits 2 and writes no outputs), and
summary JSON export (round-trip of a real run summary and of
an empty run, no raw identifiers in the file), and CSV header
validation (missing required column and empty file both raise
ValueError naming the missing columns).
No dependencies, no real patient data.

Oct 22, 2026 build block (4:05 AM run): CLI `--summary-json` flag
(`hipaa_pipeline_framework/__main__.py`) — the command line can now
write the run summary to JSON via `write_summary_json`, so the
summary export is reachable without writing Python; 2 new tests
(suite now 32, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 0.576s; governed and quarantine CSVs byte-identical to
pre-run outputs; audit.csv 10,001 lines; zero raw member IDs,
zero patient names in all outputs).

Oct 22, 2026 build block (10:05 AM run): CSV header validation
(`read_claims_csv` in `hipaa_pipeline_framework/io.py`) — a claims
CSV missing any REQUIRED_COLUMNS (`member_id`, `service_date`,
`claim_amount`) now raises ValueError naming the missing columns
instead of silently quarantining every row as missing-field, and
the CLI turns that into exit 2 with no outputs written; 3 new
tests (suite now 35, all passing). Demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 0.754s; audit.csv 10,001 lines; zero raw member IDs,
zero patient names in all outputs).

Oct 21, 2026 build block (11:00 AM run): pipeline orchestrator
(`hipaa_pipeline_framework/pipeline.py`, `run_pipeline`) tying config
+ quality gates + audit together, fail-closed on insecure configs;
3 new tests (suite now 15, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged).

Oct 21, 2026 build block (11:30 AM run): timestamped audit trail
(`AuditLog.entries()` read-back, UTC timestamp on every entry);
1 new test (suite now 16, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged).

Oct 21, 2026 build block (12:00 PM run): `run_pipeline` result now
also reports `governed_count` and `quarantined_count`; 1 new test
(suite now 17, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged).

Oct 21, 2026 build block (12:30 PM run): demo refactored onto the
`run_pipeline` orchestrator (no more hand-rolled loop in
`examples/run_demo.py`); outputs byte-identical to the pre-refactor
run (governed and quarantine CSV SHA-256s unchanged; audit 1,589
governed + 8,411 quarantined entries); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged).

Oct 21, 2026 build block (1:30 PM run): `AuditLog.summary()` —
tallies the audit trail (total, by action, by quarantine reason),
returning all zeros for an empty or missing trail; 1 new test
(suite now 18, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
audit summary matches: governed 1,589, quarantined 8,411).

Oct 21, 2026 build block (2:00 PM run): CSV I/O module
(`hipaa_pipeline_framework/io.py`) — `read_claims_csv` feeds raw
claims rows straight into `run_pipeline`, and `write_governed_csv`
writes only the fixed de-identified columns, dropping any raw
identifier that slipped into a governed record dict; 3 new tests
(suite now 21, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 0.755s; audit 1,589 governed + 8,411 quarantined entries).

Oct 21, 2026 build block (2:30 PM run): `write_quarantine_csv`
(`hipaa_pipeline_framework/io.py`) — quarantine reports now write
the member hash plus reason per row (previously the demo wrote raw
member IDs into quarantine.csv), dropping patient names and raw
IDs; demo dogfoods both io writers; 2 new tests (suite now 23, all
passing); demo re-verified same run (10,000 in → 1,589 governed,
8,411 quarantined, reasons unchanged; runtime 0.558s; audit 1,589
governed + 8,411 quarantined entries; quarantine.csv verified to
contain zero raw member IDs and zero patient names).

Oct 21, 2026 build block (3:00 PM run): `summarize_run`
(`hipaa_pipeline_framework/pipeline.py`) — turns a `run_pipeline`
result into a plain summary dict (records_in, governed_count,
quarantined_count, quarantine rate, per-reason tallies) with no
record data, safe to log or paste into a report; rate is 0.0 for
an empty run; 1 new test (suite now 24, all passing); demo
re-verified same run (10,000 in → 1,589 governed, 8,411
quarantined, reasons unchanged; runtime 0.607s; governed and
quarantine CSVs byte-identical to the pre-run outputs; audit
summary matches the pipeline counts).

Oct 21, 2026 build block (3:30 PM run): `write_audit_csv`
(`hipaa_pipeline_framework/io.py`) — exports an AuditLog's trail
to CSV (fixed audit columns, one row per entry; the trail stores
only hashes and "redacted" markers, so the export carries no raw
identifiers), and the demo now dogfoods it as audit.csv; 2 new
tests (suite now 26, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 0.699s; governed and quarantine CSVs byte-identical to the
pre-run outputs; audit.csv has 10,001 lines — header + 10,000
entries — with zero raw member IDs and zero patient names).

Oct 21, 2026 build block (10:05 PM run): `write_summary_json`
(`hipaa_pipeline_framework/io.py`) — writes a `summarize_run`
summary dict to sorted, diff-friendly JSON (counts, quarantine
rate, per-reason tallies, no record data), exported from the
package, and the demo now dogfoods it as summary.json; 2 new
tests (suite now 30, all passing); demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 0.575s; governed and quarantine CSVs byte-identical to the
pre-run outputs; audit.csv 10,001 lines with governed 1,589 +
quarantined 8,411; summary.json matches the pipeline counts,
quarantine rate 0.8411, zero raw member IDs).

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
