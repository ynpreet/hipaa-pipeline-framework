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
- PUBLISHED v0.1, Oct 21, 2026: https://github.com/ynpreet/hipaa-pipeline-framework
  (public, main, commit eb293dfebcf1ba8c5e6d99f48ee9ffe541aa6e12, author
  Preet Mehta <preetmehta1995@gmail.com>). Repo created via browser
  (connector create failed 403), files pushed via connector and verified
  on GitHub. Generated demo outputs and __pycache__ are NOT in the repo.
- Next steps: PyPI packaging, README quickstart (done in-repo), adoption
  evidence tracking from day one.
- Oct 21, 2026 build block: stdlib test suite added
  (tests/test_framework.py, 9 tests, all passing) covering hash,
  identifier stripping, all quality gates, and audit logging; demo
  re-verified same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; governed output contains no raw member IDs or
  patient names).
- Oct 21, 2026 build block (10:30 AM run): secure-default pipeline
  config module (hipaa_pipeline_framework/config.py) — encryption at
  rest, audit on, quarantine on failure, no PHI in logs, with
  validation refusing insecure overrides; 3 new tests (suite now 12,
  all passing); README + PLAN updated. Demo re-verified same run
  (numbers below, unchanged).
- Oct 21, 2026 build block (11:00 AM run): pipeline orchestrator
  (hipaa_pipeline_framework/pipeline.py, `run_pipeline`) — fail-closed
  on insecure configs, runs records through the quality gates,
  quarantines failures with reasons, writes one audit entry per
  record when given an AuditLog; 3 new tests (suite now 15, all
  passing); README + PLAN updated. Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged).
- Oct 21, 2026 build block (11:30 AM run): timestamped audit trail
  (hipaa_pipeline_framework/audit.py) — every entry now carries a UTC
  timestamp, and AuditLog.entries() reads the trail back in order
  ([] before any entry exists); 1 new test (suite now 16, all
  passing); README + PLAN updated. Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged:
  missing_required_field 3557, unparseable_date 3198,
  invalid_amount 1646, duplicate 10; runtime 0.486s).
- Oct 21, 2026 build block (12:00 PM run): run_pipeline result counts
  (`governed_count`, `quarantined_count` alongside `records_in`, so
  callers need not recompute them); 1 new test (suite now 17, all
  passing); README + PLAN updated. Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.726s).
- Oct 21, 2026 build block (12:30 PM run): demo now runs through the
  `run_pipeline` orchestrator instead of hand-rolling the same loop
  (examples/run_demo.py) — the orchestrator is now dogfooded by its
  own demo; outputs byte-identical to the pre-refactor run (governed
  and quarantine CSV SHA-256s unchanged, audit 1,589 governed +
  8,411 quarantined entries); README test count corrected to 17.
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.362s).
- Oct 21, 2026 build block (1:30 PM run): audit-trail summary
  (`AuditLog.summary()` in hipaa_pipeline_framework/audit.py) —
  totals the trail by action and by quarantine reason, all zeros
  for an empty/missing trail; 1 new test (suite now 18, all
  passing); README + PLAN updated. Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.894s; audit summary matches the pipeline counts).
- Oct 21, 2026 build block (2:00 PM run): CSV I/O module
  (hipaa_pipeline_framework/io.py) — `read_claims_csv` feeds raw
  claims rows into run_pipeline, `write_governed_csv` writes only
  the fixed de-identified columns and drops any raw identifier
  that slipped into a governed record dict; 3 new tests (suite
  now 21, all passing); README + PLAN updated. Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.755s; audit 1,589 governed + 8,411
  quarantined entries; governed CSV has no raw member IDs).
- Oct 21, 2026 build block (2:30 PM run): de-identified quarantine
  CSV (`write_quarantine_csv` in hipaa_pipeline_framework/io.py) —
  quarantine reports now write member hash + reason per row,
  dropping patient names and raw member IDs (the demo previously
  wrote raw member IDs into quarantine.csv); demo now dogfoods
  both io writers; 2 new tests (suite now 23, all passing);
  README + PLAN updated. Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged; runtime
  0.558s; audit 1,589 governed + 8,411 quarantined entries;
  quarantine.csv verified: zero raw member IDs, zero patient
  names).
- Oct 21, 2026 build block (3:00 PM run): run summary
  (`summarize_run` in hipaa_pipeline_framework/pipeline.py) —
  turns a run_pipeline result into a plain dict (records_in,
  governed_count, quarantined_count, quarantine rate, per-reason
  tallies) with no record data, safe to log or report; rate is
  0.0 for an empty run; exported from the package; 1 new test
  (suite now 24, all passing); README + PLAN updated. Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.607s; governed and
  quarantine CSVs byte-identical to pre-run outputs; audit
  summary matches the pipeline counts).
- Oct 21, 2026 build block (3:30 PM run): audit-trail CSV export
  (`write_audit_csv` in hipaa_pipeline_framework/io.py) —
  exports an AuditLog's trail under fixed audit columns for
  spreadsheet reviewers; trail stores only hashes and "redacted"
  markers, so the export carries no raw identifiers; empty or
  missing trail still writes the header; exported from the
  package; demo now dogfoods it as audit.csv; 2 new tests
  (suite now 26, all passing); README + PLAN updated. Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.699s; governed and
  quarantine CSVs byte-identical to pre-run outputs; audit.csv
  10,001 lines — header + 10,000 entries — zero raw member IDs,
  zero patient names).
- Oct 21, 2026 build block (4:00 PM run): command-line entry point
  (`hipaa_pipeline_framework/__main__.py`) — `python3 -m
  hipaa_pipeline_framework input.csv --governed … --quarantine …
  --audit … [--audit-csv …]` runs any claims CSV through
  run_pipeline under the secure defaults (fail closed) and prints
  only the run summary; missing input exits 2 with an error, never
  a traceback; 2 new tests (suite now 28, all passing); CLI
  smoke-tested on the 10,000-row synthetic CSV (same demo numbers:
  1,589 governed, 8,411 quarantined, reasons unchanged; zero raw
  member IDs in all three outputs). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.993s).
- Oct 21, 2026 build block (10:05 PM run): run-summary JSON
  export (`write_summary_json` in hipaa_pipeline_framework/io.py)
  — writes a summarize_run dict to sorted, diff-friendly JSON
  (counts, quarantine rate, per-reason tallies, no record data),
  exported from the package; demo now dogfoods it as
  summary.json; 2 new tests (suite now 30, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.575s; governed and
  quarantine CSVs byte-identical to pre-run outputs; audit.csv
  10,001 lines, governed 1,589 + quarantined 8,411; summary.json
  matches the pipeline counts, quarantine rate 0.8411, zero raw
  member IDs).
- Oct 22, 2026 build block (4:05 AM run): CLI `--summary-json`
  flag (hipaa_pipeline_framework/__main__.py) — the command line
  now writes the run summary to JSON via write_summary_json, so
  the summary export is reachable without writing Python; 2 new
  tests (suite now 32, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.576s; audit.csv 10,001 lines; zero raw
  member IDs, zero patient names in all outputs).
- Oct 22, 2026 build block (10:05 AM run): CSV header validation
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a claims
  CSV missing any REQUIRED_COLUMNS (member_id, service_date,
  claim_amount) raises ValueError naming the missing columns
  instead of silently quarantining every row as
  missing_required_field; the CLI turns that into exit 2 with no
  outputs written; empty files raise the same way. 3 new tests
  (suite now 35, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.754s; audit.csv 10,001 lines; zero raw
  member IDs, zero patient names in all outputs).
- Oct 22, 2026 build block (4:05 PM run): CLI output parent
  directories (hipaa_pipeline_framework/__main__.py) — the CLI
  creates missing parent directories for all its outputs before
  the run starts, so nested output paths work without a prior
  mkdir; an unwritable output path exits 2 with an error line,
  never a traceback. 2 new tests (suite now 37, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.775s; audit.csv
  10,001 lines; governed and quarantine CSVs byte-identical to
  pre-run outputs; zero raw member IDs, zero patient names in
  all outputs; CLI smoke-tested into fresh nested output
  directories with the same numbers).
- Oct 22, 2026 build block (10:05 PM run): CSV input tolerance
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a claims
  CSV with a UTF-8 byte-order mark and whitespace around headers
  and values now reads cleanly (BOM stripped via utf-8-sig,
  headers and values trimmed) instead of failing a quality gate,
  while a padded header still missing a required column raises
  ValueError naming that column; 2 new tests (suite now 39, all
  passing). Demo re-verified same run (10,000 in → 1,589 governed,
  8,411 quarantined, reasons unchanged; runtime 1.029s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a BOM-marked,
  padded 2-row CSV: 1 governed, 1 quarantined).
- Oct 27, 2026 build block (4:05 AM run): weekday-prefixed
  month-name dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  with a weekday label in front of a month-name date
  ("Sunday, March 15, 2026", "Mon, 16 Mar 2026", or a
  weekday-prefixed ordinal date "Sunday, March 15th, 2026",
  the way human-readable exports and email-style
  timestamps write dates) now has the weekday label
  stripped on read and normalizes to ISO form (YYYY-MM-DD)
  and governs instead of quarantining as unparseable_date;
  the weekday itself is not validated against the calendar
  date (it is a label, not the date), while an impossible
  weekday-prefixed date ("Monday, Feb 30, 2026") or a bogus
  weekday label ("Funday, March 15, 2026") is left untouched
  so the gates quarantine it normally; the quality gates
  stay strict and see only the normalized value; 2 new
  tests (suite now 73, all passing). Demo re-verified same
  run (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.586s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a weekday-
  prefixed-date 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 26, 2026 build block (10:05 PM run): ordinal month-name
  dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  with an ordinal day suffix ("March 15th, 2026" or "15th Mar
  2026", the way human-written exports spell the day) now
  normalizes to ISO form (YYYY-MM-DD) on read and governs
  instead of quarantining as unparseable_date, while an
  impossible ordinal date ("Feb 30th, 2026") is left
  untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 71, all passing). Demo re-verified same
  run (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.676s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on an ordinal-
  date 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 26, 2026 build block (4:05 PM run): slash datetimes
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  in slash form carrying a time stamp ("03/15/2026 10:30:00"
  or "03/15/2026T09:00:00", the way spreadsheet exports
  write slash datetimes) now normalizes to its date part
  (YYYY-MM-DD) on read and governs instead of quarantining
  as unparseable_date, with the same US-first order
  ("15/03/2026T09:00:00" governs as 2026-03-15), while an
  impossible slash datetime ("02/30/2026 10:00:00") is left
  untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 69, all passing). Demo re-verified same
  run (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.434s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a slash-
  datetime 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 26, 2026 build block (10:05 AM run): underscore-separated
  dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written in
  underscore-separated form (YYYY_MM_DD, the way some exports
  and file-naming conventions write dates) now normalizes to
  ISO form (YYYY-MM-DD) on read and governs instead of
  quarantining as unparseable_date, while an impossible
  underscore-separated date ("2026_02_30") is left untouched
  so the gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 67, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.391s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on an underscore-
  separated-date 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 26, 2026 build block (4:05 AM run): numeric hyphen
  dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  in numeric hyphen form ("03-15-2026", the way some
  exports write the US date with hyphens instead of
  slashes) now normalizes to ISO form (YYYY-MM-DD) on read
  and governs instead of quarantining as unparseable_date,
  with the US form keeping priority ("03-04-2026" still
  reads as 2026-03-04, while an unambiguous day-first form
  "15-03-2026" governs as 2026-03-15), while an impossible
  numeric hyphen date ("02-30-2026") is left untouched so
  the gates quarantine it normally; an already-ISO date is
  not touched by this form, and the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 65, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.639s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a numeric-
  hyphen 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 25, 2026 build block (10:05 PM run): hyphenated
  month-name dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  in hyphenated month-name form ("15-Mar-2026" or
  "Mar-15-2026", abbreviated or full month name, the way
  some exports write dates without spaces) now normalizes
  to ISO form (YYYY-MM-DD) on read and governs instead of
  quarantining as unparseable_date, while an impossible
  hyphenated month-name date ("30-Feb-2026") is left
  untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 63, all passing). Demo re-verified same
  run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.789s; governed, quarantine,
  and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  hyphenated month-name 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Oct 25, 2026 build block (4:05 PM run): compact dates
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written in compact form (YYYYMMDD, the basic
  ISO 8601 form, another export convention) now normalizes
  to ISO form (YYYY-MM-DD) on read and governs instead of
  quarantining as unparseable_date, while an impossible
  compact date ("20260230") is left untouched so the gates
  quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite now
  61, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.634s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv
  10,001 lines; zero raw member IDs, zero patient names in
  all outputs; CLI smoke-tested on a compact-date 2-row
  CSV: 2 in, 1 governed, 1 quarantined).
- Oct 25, 2026 build block (10:05 AM run): day-first slash
  dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  DD/MM/YYYY (the non-US healthcare-export convention) now
  normalizes to ISO form (YYYY-MM-DD) on read and governs
  instead of quarantining as unparseable_date, but only when
  it is unambiguous: the US MM/DD/YYYY form is tried first, so
  "03/04/2026" still reads as 2026-03-04, while "15/03/2026"
  governs as 2026-03-15; an impossible day-first date
  ("32/03/2026" or "15/13/2026") is left untouched so the
  gates quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite now
  59, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.684s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv 10,001
  lines; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a day-first slash-date 2-row
  CSV: 2 in, 1 governed, 1 quarantined).
- Oct 25, 2026 build block (4:05 AM run): month-name dates
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  with a month name ("Mar 15, 2026" or "15 Mar 2026",
  abbreviated or full month name, another export convention)
  now normalizes to ISO form (YYYY-MM-DD) on read and governs
  instead of quarantining as unparseable_date, while an
  impossible month-name date ("Feb 30, 2026") or an unknown
  month name is left untouched so the gates quarantine it
  normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 57, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.629s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  month-name-date 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Oct 24, 2026 build block (10:05 PM run): dot-separated
  dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
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
- Oct 24, 2026 build block (4:05 PM run): timezone-suffixed
  datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date carrying a
  timezone suffix (a trailing "Z" for UTC, or a numeric offset
  such as "+05:30" or "-0500", the way API and EHR exports write
  timestamps) now has that suffix stripped before parsing and
  normalizes to its date part (YYYY-MM-DD) on read and governs
  instead of quarantining as unparseable_date, while an impossible
  date with a valid suffix ("2026-02-30T09:00:00Z") or a
  malformed offset ("+99:99") is left untouched so the gates
  quarantine it normally; the offset is not converted (the gate
  needs the service date as written, not a shifted one), and the
  quality gates stay strict and see only the normalized value;
  2 new tests (suite now 53, all passing). Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.517s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a timezone-suffixed
  2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 24, 2026 build block (10:05 AM run): year-first slash
  dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  YYYY/MM/DD (another export convention) now normalizes to ISO
  form (YYYY-MM-DD) on read and governs instead of quarantining
  as unparseable_date, while an impossible year-first date
  ("2026/02/30") is left untouched so the gates quarantine it
  normally; the MM/DD/YYYY form keeps priority, and the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 51, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.628s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a year-first
  slash-date 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 24, 2026 build block (4:05 AM run): datetime-stamped
  service dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date carrying a
  time stamp (space- or "T"-separated, e.g. "2026-03-15 10:30:00"
  or "2026-03-15T09:00:00", the way spreadsheet exports write
  datetimes) now normalizes to its date part (YYYY-MM-DD) on
  read and governs instead of quarantining as unparseable_date,
  while an impossible datetime ("2026-02-30 10:00:00") or a
  garbage time part is left untouched so the gates quarantine
  it normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 49, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.524s; governed,
  quarantine, and summary.json outputs byte-identical to
  pre-run outputs; audit.csv 10,001 lines; zero raw member
  IDs, zero patient names in all outputs; CLI smoke-tested on
  a datetime-stamped 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 23, 2026 build block (10:05 PM run): case-insensitive CSV
  headers (read_claims_csv in hipaa_pipeline_framework/io.py) —
  headers are now matched without regard to letter case, so an
  export headed "Member_ID,SERVICE_DATE,Claim_Amount" reads as
  member_id, service_date, claim_amount and governs instead of
  failing closed as missing columns, while a mixed-case header
  still missing a required column raises ValueError naming that
  column; 2 new tests (suite now 47, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 1.546s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  mixed-case-header 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 23, 2026 build block (4:05 PM run): US slash-date
  normalization (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  MM/DD/YYYY (the US healthcare-export convention) now
  normalizes to ISO form (YYYY-MM-DD) on read and governs
  instead of quarantining as unparseable_date, while a slash
  date that is not a real calendar date ("02/30/2026") is left
  untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 45, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.735s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a slash-date
  2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 23, 2026 build block (10:05 AM run): currency-formatted
  amounts (read_claims_csv in hipaa_pipeline_framework/io.py) —
  a claim_amount written as "$1,200.50" now reads as 1200.50 and
  governs instead of quarantining as invalid_amount, while
  "$abc" still quarantines normally; the quality gates stay
  strict and see only the stripped value; 2 new tests (suite
  now 43, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged; runtime
  0.387s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  currency-formatted 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Oct 23, 2026 build block (4:05 AM run): blank-row skipping
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  commas-only line or whitespace-only line in a claims CSV is
  now skipped outright instead of inflating the quarantine tally
  as missing_required_field, while a partially filled row still
  quarantines normally; 2 new tests (suite now 41, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.488s; governed
  1,590 lines, quarantine 8,412 lines, audit.csv 10,001 lines;
  zero raw member IDs, zero patient names in all outputs; CLI
  smoke-tested on a blank-row 2-row CSV: 2 in, 2 governed,
  0 quarantined).

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
