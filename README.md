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
  it also tolerates real export mess — a UTF-8 byte-order mark
  and whitespace around headers and values are stripped, so a
  spreadsheet export reads cleanly instead of failing a gate;
  `write_governed_csv`
  writes only the fixed de-identified columns, dropping any raw
  identifier that slipped into a record dict; `write_quarantine_csv`
  writes quarantined (record, reason) pairs the same way — member
  hash plus reason, never a raw member ID or patient name;
  `read_claims_csv` also normalizes datetime-stamped service
  dates ("2026-03-15 10:30:00" or "2026-03-15T09:00:00" read as
  2026-03-15 and govern; an impossible datetime still
  quarantines as unparseable_date), including timezone-suffixed
  forms ("2026-03-15T09:00:00Z", "2026-03-15 10:30:00+05:30");
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

59 stdlib-only tests (Oct 25, 2026, all passing): hash determinism and
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
ValueError naming the missing columns), and CLI output
directories (missing parent directories are created before the
run; an unwritable output path exits 2 with an error line, no
traceback), and CSV input tolerance (a BOM-marked, whitespace-padded
export reads cleanly and governs; a padded header missing a
required column still raises naming that column), and blank-row
skipping (a commas-only or whitespace-only line is skipped, not
counted as a missing-field quarantine; a partially filled row
still quarantines normally), and currency formatting
("$1,200.50" reads as 1200.50 and governs; "$abc" still
quarantines as invalid_amount), and slash-date normalization
("03/15/2026" reads as 2026-03-15 and governs; "02/30/2026"
still quarantines as unparseable_date), and case-insensitive headers
("Member_ID" reads as member_id and governs; a mixed-case header
still missing a required column raises naming that column), and
datetime-stamped dates ("2026-03-15 10:30:00" or
"2026-03-15T09:00:00" read as 2026-03-15 and govern; an
impossible datetime still quarantines as unparseable_date), and
timezone-suffixed datetimes ("2026-03-15T09:00:00Z" or
"2026-03-15 10:30:00+05:30" read as their date part and govern;
an impossible date with a valid suffix, or a malformed offset,
still quarantines as unparseable_date), and
dot-separated dates ("2026.03.15" reads as 2026-03-15 and
governs; "2026.02.30" still quarantines as unparseable_date),
and month-name dates ("Mar 15, 2026" or "15 Mar 2026" read as
2026-03-15 and govern; "Feb 30, 2026" still quarantines as
unparseable_date), and day-first slash dates ("15/03/2026"
reads as 2026-03-15 and governs; "03/04/2026" still reads as
the US form; "32/03/2026" still quarantines as
unparseable_date).
No dependencies, no real patient data.

Oct 25, 2026 build block (10:05 AM run): day-first slash
dates (`read_claims_csv` in
`hipaa_pipeline_framework/io.py`) — a service_date written as
DD/MM/YYYY (the non-US healthcare-export convention) now
normalizes to ISO form (YYYY-MM-DD) on read and governs
instead of quarantining as unparseable_date, but only when it
is unambiguous: the US MM/DD/YYYY form is tried first, so
"03/04/2026" still reads as 2026-03-04, while "15/03/2026"
governs as 2026-03-15; an impossible day-first date
("32/03/2026" or "15/13/2026") is left untouched so the gates
quarantine it normally; the quality gates stay strict and see
only the normalized value; 2 new tests (suite now 59, all
passing). Demo re-verified same run (10,000 in → 1,589
governed, 8,411 quarantined, reasons unchanged; runtime
0.684s; governed, quarantine, and summary.json outputs
byte-identical to pre-run outputs; audit.csv 10,001 lines;
zero raw member IDs, zero patient names in all outputs; CLI
smoke-tested on a day-first slash-date 2-row CSV: 2 in, 1
governed, 1 quarantined).

Oct 25, 2026 build block (4:05 AM run): month-name dates
(`read_claims_csv` in
`hipaa_pipeline_framework/io.py`) — a service_date written with
a month name ("Mar 15, 2026" or "15 Mar 2026", abbreviated or
full month name, another export convention) now normalizes to
ISO form (YYYY-MM-DD) on read and governs instead of
quarantining as unparseable_date, while an impossible
month-name date ("Feb 30, 2026") or an unknown month name is
left untouched so the gates quarantine it normally; the quality
gates stay strict and see only the normalized value; 2 new
tests (suite now 57, all passing). Demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons
unchanged; runtime 0.629s; governed, quarantine, and
summary.json outputs byte-identical to pre-run outputs;
audit.csv 10,001 lines; zero raw member IDs, zero patient
names in all outputs; CLI smoke-tested on a month-name-date
2-row CSV: 2 in, 1 governed, 1 quarantined).

Oct 24, 2026 build block (10:05 PM run): dot-separated
dates (`read_claims_csv` in
`hipaa_pipeline_framework/io.py`) — a service_date written as
YYYY.MM.DD (another export convention) now normalizes to ISO
form (YYYY-MM-DD) on read and governs instead of quarantining
as unparseable_date, while an impossible dot-separated date
("2026.02.30") is left untouched so the gates quarantine it
normally; the quality gates stay strict and see only the
normalized value; 2 new tests (suite now 55, all passing).
Demo re-verified same run (10,000 in → 1,589 governed, 8,411
quarantined, reasons unchanged; runtime 0.533s; governed,
quarantine, and summary.json outputs byte-identical to pre-run
outputs; audit.csv 10,001 lines; zero raw member IDs, zero
patient names in all outputs; CLI smoke-tested on a
dot-separated-date 2-row CSV: 2 in, 1 governed,
1 quarantined).

Oct 24, 2026 build block (4:05 PM run): timezone-suffixed
datetimes (`read_claims_csv` in
`hipaa_pipeline_framework/io.py`) — a service_date carrying a
timezone suffix (a trailing "Z" for UTC, or a numeric offset
such as "+05:30" or "-0500", the way API and EHR exports write
timestamps) now has that suffix stripped before parsing and
normalizes to its date part (YYYY-MM-DD) on read and governs
instead of quarantining as unparseable_date, while an impossible
date with a valid suffix ("2026-02-30T09:00:00Z") or a malformed
offset ("+99:99") is left untouched so the gates quarantine it
normally; the offset is not converted, and the quality gates stay
strict and see only the normalized value; 2 new tests (suite now
53, all passing). Demo re-verified same run (10,000 in →
1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 0.517s; governed, quarantine, and summary.json
outputs byte-identical to pre-run outputs; audit.csv 10,001
lines; zero raw member IDs, zero patient names in all
outputs; CLI smoke-tested on a timezone-suffixed 2-row CSV:
2 in, 1 governed, 1 quarantined).

Oct 24, 2026 build block (4:05 AM run): datetime-stamped
service dates (`read_claims_csv` in
`hipaa_pipeline_framework/io.py`) — a service_date carrying a
time stamp (space- or "T"-separated, e.g. "2026-03-15 10:30:00"
or "2026-03-15T09:00:00", the way spreadsheet exports write
datetimes) now normalizes to its date part (YYYY-MM-DD) on
read and governs instead of quarantining as
unparseable_date, while an impossible datetime ("2026-02-30
10:00:00") or a garbage time part is left untouched so the
gates quarantine it normally; the quality gates stay strict
and see only the normalized value; 2 new tests (suite now
49, all passing). Demo re-verified same run (10,000 in →
1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 0.524s; governed, quarantine, and summary.json
outputs byte-identical to pre-run outputs; audit.csv 10,001
lines; zero raw member IDs, zero patient names in all
outputs; CLI smoke-tested on a datetime-stamped 2-row CSV:
2 in, 1 governed, 1 quarantined).

Oct 23, 2026 build block (10:05 PM run): case-insensitive CSV
headers (`read_claims_csv` in
`hipaa_pipeline_framework/io.py`) — headers are now matched
without regard to letter case, so an export headed
"Member_ID,SERVICE_DATE,Claim_Amount" reads as member_id,
service_date, claim_amount and governs instead of failing
closed as missing columns, while a mixed-case header still
missing a required column raises ValueError naming that
column; 2 new tests (suite now 47, all passing). Demo
re-verified same run (10,000 in → 1,589 governed, 8,411
quarantined, reasons unchanged; runtime 1.546s; governed,
quarantine, and summary.json outputs byte-identical to
pre-run outputs; audit.csv 10,001 lines; zero raw member
IDs, zero patient names in all outputs; CLI smoke-tested
on a mixed-case-header 2-row CSV: 2 in, 1 governed,
1 quarantined).

Oct 23, 2026 build block (4:05 PM run): US slash-date
normalization (`read_claims_csv` in
`hipaa_pipeline_framework/io.py`) — a service_date written as
MM/DD/YYYY (the US healthcare-export convention) now normalizes
to ISO form (YYYY-MM-DD) on read and governs instead of
quarantining as unparseable_date, while a slash date that is
not a real calendar date ("02/30/2026") is left untouched so
the gates quarantine it normally; the quality gates stay
strict and see only the normalized value; 2 new tests (suite
now 45, all passing). Demo re-verified same run (10,000 in →
1,589 governed, 8,411 quarantined, reasons unchanged; runtime
0.735s; governed, quarantine, and summary.json outputs
byte-identical to pre-run outputs; audit.csv 10,001 lines;
zero raw member IDs, zero patient names in all outputs; CLI
smoke-tested on a slash-date 2-row CSV: 2 in, 1 governed,
1 quarantined).

Oct 23, 2026 build block (10:05 AM run): currency-formatted
amounts (`read_claims_csv` in `hipaa_pipeline_framework/io.py`) —
a claim_amount written as "$1,200.50" (leading "$" plus
thousands commas, the way spreadsheet exports write money) now
reads as 1200.50 and governs instead of quarantining as
invalid_amount, while a value that is still not a number after
stripping ("$abc") still quarantines normally; the quality
gates stay strict and see only the stripped value; 2 new tests
(suite now 43, all passing). Demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 0.387s; governed, quarantine, and summary.json outputs
byte-identical to pre-run outputs; zero raw member IDs, zero
patient names in all outputs; CLI smoke-tested on a
currency-formatted 2-row CSV: 2 in, 1 governed, 1 quarantined).

Oct 23, 2026 build block (4:05 AM run): blank-row skipping
(`read_claims_csv` in `hipaa_pipeline_framework/io.py`) — a
claims CSV with a commas-only line or a whitespace-only line
(the trailing junk spreadsheet exports leave behind) now skips
those rows outright instead of counting each as a
missing_required_field quarantine, while a row with some fields
filled and others empty still quarantines normally; 2 new tests
(suite now 41, all passing). Demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 0.488s; governed 1,590 lines, quarantine 8,412 lines,
audit.csv 10,001 lines; zero raw member IDs, zero patient names
in all outputs; CLI smoke-tested on a blank-row 2-row CSV: 2 in,
2 governed, 0 quarantined).

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

Oct 22, 2026 build block (4:05 PM run): CLI output parent
directories (`hipaa_pipeline_framework/__main__.py`) — the CLI now
creates missing parent directories for all its outputs (governed,
quarantine, audit, --audit-csv, --summary-json) before the run
starts, so a nested output path works without a prior mkdir, and
an unwritable output path exits 2 with an error line instead of a
traceback; 2 new tests (suite now 37, all passing). Demo
re-verified same run (10,000 in → 1,589 governed, 8,411
quarantined, reasons unchanged; runtime 0.775s; audit.csv 10,001
lines; governed and quarantine CSVs byte-identical to pre-run
outputs; zero raw member IDs, zero patient names in all outputs;
CLI smoke-tested on a 10,000-row synthetic CSV into fresh nested
output directories with the same numbers).

Oct 22, 2026 build block (10:05 PM run): CSV input tolerance
(`read_claims_csv` in `hipaa_pipeline_framework/io.py`) — a claims
CSV with a UTF-8 byte-order mark and whitespace around headers
and values now reads cleanly (BOM stripped, headers and values
trimmed) instead of failing a quality gate, while a padded header
still missing a required column raises naming that column; 2 new
tests (suite now 39, all passing). Demo re-verified same run
(10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
runtime 1.029s; governed, quarantine, and summary.json outputs
byte-identical to pre-run outputs; audit.csv 10,001 lines; zero raw
member IDs, zero patient names in all outputs; CLI smoke-tested on
a BOM-marked, padded 2-row CSV: 1 governed, 1 quarantined).

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
