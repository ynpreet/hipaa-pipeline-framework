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
- Oct 28, 2026 build block (4:05 AM run): weekday-prefixed
  compact dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  with a weekday label in front of a compact date
  ("Sunday, 20260315" or "Mon, 20260316", the way
  email-style timestamps write dates) now has the weekday
  label stripped on read and normalizes to ISO form
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, while an impossible weekday-prefixed
  compact date ("Monday, 20260230") or a bogus weekday label
  ("Funday, 20260315") is left untouched so the gates
  quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite
  now 81, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.675s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  weekday-prefixed-compact-date 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Oct 28, 2026 build block (10:05 AM run): weekday-prefixed
  numeric hyphen dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  with a weekday label in front of a numeric hyphen date
  ("Sunday, 03-15-2026" or "Mon, 15-03-2026", the way
  email-style timestamps write dates) now has the weekday
  label stripped on read and normalizes to ISO form
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, with the same US-first order ("Tues,
  03-04-2026" still reads as 2026-03-04), while an impossible
  weekday-prefixed numeric hyphen date ("Monday, 02-30-2026")
  or a bogus weekday label ("Funday, 03-15-2026") is left
  untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 83, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 1.080s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  weekday-prefixed-numeric-hyphen-date 2-row CSV: 2 in,
  1 governed, 1 quarantined).
- Oct 28, 2026 build block (4:05 PM run): weekday-prefixed
  underscore-separated dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  with a weekday label in front of an underscore-separated
  date ("Sunday, 2026_03_15" or "Mon, 2026_03_16", the way
  email-style timestamps write dates) now has the weekday
  label stripped on read and normalizes to ISO form
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, while an impossible weekday-prefixed
  underscore date ("Monday, 2026_02_30") or a bogus weekday
  label ("Funday, 2026_03_15") is left untouched so the
  gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 85, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 1.016s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  weekday-prefixed-underscore-date 2-row CSV: 2 in,
  1 governed, 1 quarantined).
- Oct 28, 2026 build block (10:05 PM run): dot-separated
  datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  as a dot-separated date carrying a time stamp
  ("2026.03.15 10:30:00" or "2026.03.15T09:00:00", the way
  some exports write dot dates with a time stamp) now
  normalizes to its date part (YYYY-MM-DD) on read and
  governs instead of quarantining as unparseable_date,
  while an impossible dot datetime ("2026.02.30 10:00:00")
  or a garbage time part is left untouched so the gates
  quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite
  now 87, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.775s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  dot-separated-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Oct 29, 2026 build block (10:05 AM run):
  timezone-suffixed month-name datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date
  written as a month-name datetime carrying a timezone
  suffix ("Mar 15, 2026 10:30:00Z",
  "15 Mar 2026T09:00:00-04:00", or a weekday-prefixed
  "Sunday, Mar 15, 2026 10:30:00+05:00", the way exports
  write month-name datetimes with a zone) now has the
  suffix stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, while an impossible timezone-suffixed
  month-name datetime ("Feb 30, 2026 10:00:00Z") or a
  malformed suffix ("Mar 15, 2026 10:30:00+99:99") is left
  untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized
  value; 2 new tests (suite now 91, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.965s;
  governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001
  lines; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a timezone-suffixed
  month-name-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Oct 29, 2026 build block (4:05 AM run): month-name
  datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  as a month-name date carrying a time stamp
  ("Mar 15, 2026 10:30:00", "15 Mar 2026T09:00:00", or a
  hyphenated month-name datetime "17-Mar-2026 10:30:00",
  the way some exports write month-name dates with a time
  stamp) now normalizes to its date part (YYYY-MM-DD) on
  read and governs instead of quarantining as
  unparseable_date, including weekday-prefixed forms
  ("Sunday, Mar 15, 2026 10:30:00"), while an impossible
  month-name datetime ("Feb 30, 2026 10:00:00") or a
  garbage time part is left untouched so the gates
  quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite
  now 89, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.742s; governed, quarantine, and
  summary.json outputs stable across a repeat run;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  month-name-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Oct 27, 2026 build block (10:05 PM run): weekday-prefixed
  dot-separated dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  with a weekday label in front of a dot-separated date
  ("Sunday, 2026.03.15" or "Mon, 2026.03.16", the way
  email-style timestamps write dates) now has the weekday
  label stripped on read and normalizes to ISO form
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, while an impossible weekday-prefixed
  dot date ("Monday, 2026.02.30") or a bogus weekday label
  ("Funday, 2026.03.15") is left untouched so the gates
  quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite
  now 79, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.546s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  weekday-prefixed-dot-date 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Oct 27, 2026 build block (4:05 PM run): weekday-prefixed
  slash dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  with a weekday label in front of a slash date or slash
  datetime ("Sunday, 03/15/2026", "Mon, 15/03/2026", or
  "Tues, 03/16/2026 10:30:00", the way email-style
  timestamps write dates) now has the weekday label
  stripped on read and normalizes to ISO form (YYYY-MM-DD)
  and governs instead of quarantining as unparseable_date,
  with the same US-first order ("Sun, 03/04/2026" still
  reads as 2026-03-04), while an impossible weekday-
  prefixed slash date ("Monday, 02/30/2026") or a bogus
  weekday label ("Funday, 03/15/2026") is left untouched
  so the gates quarantine it normally; the quality gates
  stay strict and see only the normalized value; 2 new
  tests (suite now 77, all passing). Demo re-verified same
  run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.567s; governed, quarantine,
  and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  weekday-prefixed-slash-date 2-row CSV: 2 in, 1 governed,
  1 quarantined). This push also carries the Oct 27 10:05
  AM run's PLAN.md update (weekday-prefixed ISO dates),
  whose push had stalled on a stuck connector write.
- Oct 27, 2026 build block (10:05 AM run): weekday-prefixed
  ISO dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  with a weekday label in front of an ISO date or datetime
  ("Sunday, 2026-03-15", "Mon, 2026-03-16", or
  "Tues, 2026-03-17 10:30:00", the way email-style
  timestamps write dates) now has the weekday label
  stripped on read and normalizes to ISO form (YYYY-MM-DD)
  and governs instead of quarantining as unparseable_date;
  the weekday itself is not validated against the calendar
  date, while an impossible weekday-prefixed ISO date
  ("Monday, 2026-02-30") or a bogus weekday label
  ("Funday, 2026-03-15") is left untouched so the gates
  quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite
  now 75, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.449s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a weekday-
  prefixed-ISO-date 2-row CSV: 2 in, 1 governed,
  1 quarantined).
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

- Oct 29, 2026 build block (4:05 PM run):
  timezone-suffixed slash datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  as a slash date carrying a time stamp and a timezone
  suffix ("03/15/2026 10:30:00Z",
  "03/15/2026T09:00:00-04:00", or a weekday-prefixed
  "Sunday, 03/16/2026 10:30:00+05:30", the way API and EHR
  exports write slash datetimes with a zone) now has the
  suffix stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, with the same US-first order
  ("15/03/2026 10:30:00Z" governs as 2026-03-15), while an
  impossible timezone-suffixed slash datetime
  ("02/30/2026 10:00:00Z") or a malformed suffix
  ("03/15/2026 10:30:00+99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 93, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.583s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  timezone-suffixed slash-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Oct 29, 2026 build block (10:05 PM run):
  timezone-suffixed dot datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  as a dot-separated date carrying a time stamp and a
  timezone suffix ("2026.03.15 10:30:00Z",
  "2026.03.15T09:00:00-04:00", or a weekday-prefixed
  "Sunday, 2026.03.17 10:30:00+05:30", the way API and EHR
  exports write dot datetimes with a zone) now has the
  suffix stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, while an impossible timezone-suffixed
  dot datetime ("2026.02.30 10:00:00Z") or a malformed
  suffix ("2026.03.15 10:30:00+99:99") is left untouched
  so the gates quarantine it normally; the quality gates
  stay strict and see only the normalized value; 2 new
  tests (suite now 95, all passing). Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.683s; governed, quarantine,
  and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on
  a timezone-suffixed dot-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Oct 30, 2026 build block (4:05 AM run):
  timezone-suffixed compact datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  as a compact date carrying a time stamp and a timezone
  suffix ("20260315 10:30:00Z",
  "20260315T09:00:00-04:00", or a weekday-prefixed
  "Sunday, 20260316 10:30:00+05:30", the way API and EHR
  exports write compact datetimes with a zone) now has the
  suffix stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, while an impossible timezone-suffixed
  compact datetime ("20260230 10:00:00Z") or a malformed
  suffix ("20260315 10:30:00+99:99") is left untouched so
  the gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 97, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.635s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  timezone-suffixed compact-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Oct 30, 2026 build block (10:05 AM run):
  timezone-suffixed underscore datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date
  written as an underscore-separated date carrying a time
  stamp and a timezone suffix ("2026_03_15 10:30:00Z",
  "2026_03_15T09:00:00-04:00", or a weekday-prefixed
  "Sunday, 2026_03_16 10:30:00+05:30", the way API and EHR
  exports write underscore datetimes with a zone) now has
  the suffix stripped on read and normalizes to its date
  part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, as does a plain underscore datetime
  without a suffix ("2026_03_19 10:30:00"); while an
  impossible timezone-suffixed underscore datetime
  ("2026_02_30 10:00:00Z") or a malformed suffix
  ("2026_03_15 10:30:00+99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 99, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.390s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  timezone-suffixed underscore-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Oct 30, 2026 build block (4:05 PM run):
  timezone-suffixed numeric hyphen datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date written
  as a numeric hyphen date carrying a time stamp and a
  timezone suffix ("03-15-2026 10:30:00Z",
  "15-03-2026T09:00:00-04:00", or a weekday-prefixed
  "Sunday, 03-16-2026 10:30:00+05:30", the way API and EHR
  exports write hyphen datetimes with a zone) now has the
  suffix stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, with the same US-first order
  ("03-04-2026 10:30:00Z" governs as 2026-03-04), as does a
  plain numeric hyphen datetime without a suffix
  ("03-19-2026 10:30:00"); while an impossible
  timezone-suffixed numeric hyphen datetime
  ("02-30-2026 10:00:00Z") or a malformed suffix
  ("03-15-2026 10:30:00+99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 101, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 1.013s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  timezone-suffixed numeric-hyphen-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Oct 30, 2026 build block (10:05 PM run):
  fractional-second numeric hyphen datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date written
  as a numeric hyphen datetime carrying fractional seconds
  ("03-15-2026 10:30:00.123Z",
  "15-03-2026T09:00:00.5-04:00", or a weekday-prefixed
  "Sunday, 03-16-2026 10:30:00.123456+05:30", the way
  high-resolution API and EHR exports write hyphen datetimes)
  now normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date, with the same
  US-first order ("03-04-2026T08:00:00.25Z" governs as
  2026-03-04), as does a plain fractional-second hyphen
  datetime without a suffix ("03-18-2026 10:30:00.999");
  while an impossible fractional-second hyphen datetime
  ("02-30-2026 10:00:00.123Z") or a malformed suffix
  ("03-15-2026 10:30:00.123+99:99") is left untouched so the
  gates quarantine it normally. The fix also narrowed the
  dot-separated branch to year-first dot dates only, so a
  fractional second in another family no longer gets claimed
  by the dot branch and left unparseable — ISO fractional
  datetimes ("2026-03-15T09:00:00.123Z") now govern through
  the generic datetime branch as a side effect, verified, not
  claimed as a separate feature; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 103, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.989s; governed and quarantine outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  differing only in its timestamp column; zero raw member
  IDs, zero patient names in all outputs; CLI smoke-tested
  on a fractional-second numeric-hyphen-datetime 2-row CSV:
  2 in, 1 governed, 1 quarantined).

- Oct 31, 2026 build block (4:05 AM run):
  fractional-second compact datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date written
  as a compact datetime carrying fractional seconds
  ("20260315 10:30:00.123Z",
  "20260315T09:00:00.5-04:00", or a weekday-prefixed
  "Sunday, 20260316 10:30:00.123456+05:30", the way
  high-resolution API and EHR exports write compact
  datetimes) now normalizes to its date part (YYYY-MM-DD)
  and governs instead of quarantining as unparseable_date,
  as does a plain fractional-second compact datetime
  without a suffix ("20260315 10:30:00.999"); while an
  impossible fractional-second compact datetime
  ("20260230 10:00:00.123Z") or a malformed suffix
  ("20260315 10:30:00.123+99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 105, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.457s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, differing only in its timestamp
  column; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a fractional-second
  compact-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Oct 31, 2026 build block (10:05 AM run):
  fractional-second underscore datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date written
  as an underscore datetime carrying fractional seconds
  ("2026_03_15 10:30:00.123Z",
  "2026_03_15T09:00:00.5-04:00", or a weekday-prefixed
  "Sunday, 2026_03_16 10:30:00.123456+05:30", the way
  high-resolution API and EHR exports write underscore
  datetimes) now normalizes to its date part (YYYY-MM-DD)
  and governs instead of quarantining as unparseable_date,
  as does a plain fractional-second underscore datetime
  without a suffix ("2026_03_15 10:30:00.999"); while an
  impossible fractional-second underscore datetime
  ("2026_02_30 10:00:00.123Z") or a malformed suffix
  ("2026_03_15 10:30:00.123+99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 107, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.477s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, differing only in its timestamp
  column; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a fractional-second
  underscore-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Oct 31, 2026 build block (4:05 PM run):
  fractional-second month-name datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date written
  as a month-name datetime carrying fractional seconds
  ("Mar 15, 2026 10:30:00.123Z",
  "15 Mar 2026T09:00:00.5-04:00", or a weekday-prefixed
  "Sunday, March 16, 2026 10:30:00.123456+05:30", the way
  high-resolution exports write month-name datetimes) now
  normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date, as does a
  plain fractional-second month-name datetime without a
  suffix ("Mar 18, 2026 10:30:00.999") and a hyphenated
  month-name fractional datetime ("15-Mar-2026
  08:00:00.25Z"); while an impossible fractional-second
  month-name datetime ("Feb 30, 2026 10:00:00.123Z") or a
  malformed suffix ("Mar 15, 2026 10:30:00.123+99:99") is
  left untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized
  value; 2 new tests (suite now 109, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.453s; governed,
  quarantine, and summary.json outputs byte-identical to
  pre-run outputs; audit.csv 10,001 lines and audit.jsonl
  differing only in their timestamp columns; zero raw member
  IDs, zero patient names in all outputs; CLI smoke-tested
  on a fractional-second month-name-datetime 2-row CSV: 2
  in, 1 governed, 1 quarantined).

- Oct 31, 2026 build block (10:05 PM run):
  fractional-second slash datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  as a slash datetime carrying fractional seconds
  ("03/15/2026 10:30:00.123Z",
  "15/03/2026T09:00:00.5-04:00", or a weekday-prefixed
  "Sunday, 03/16/2026 10:30:00.123456+05:30", the way
  high-resolution API and EHR exports write slash
  datetimes) now normalizes to its date part (YYYY-MM-DD)
  and governs instead of quarantining as unparseable_date,
  with the same US-first order ("16/03/2026
  10:30:00.123Z" governs as 2026-03-16), as does a plain
  fractional-second slash datetime without a suffix
  ("03/18/2026 10:30:00.999") and a year-first fractional
  slash datetime ("2026/03/15 08:00:00.25Z"); the US
  fractional form already governed through the existing
  slash branch, and this block closes the day-first,
  year-first, and weekday-prefixed fractional gaps; while
  an impossible fractional-second slash datetime
  ("02/30/2026 10:00:00.123Z") or a malformed suffix
  ("03/15/2026 10:30:00.123+99:99") is left untouched so
  the gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 111, all passing). This push also carries the
  Oct 31 4:05 PM run's fractional-second month-name
  datetime block (suite 109), which had not been pushed
  before — remote head before this push was still the
  107-test commit 5384cee5. Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.432s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, differing only in its timestamp
  column; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a fractional-second
  slash-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Nov 1, 2026 build block (3:05 AM run):
  T-separated hyphenated month-name datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as a hyphenated month-name datetime
  with a T separator ("15-Mar-2026T09:00:00" or
  "Mar-15-2026T09:00:00.123Z", the way exports write
  hyphenated month-name datetimes with a T separator) now
  normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date, with the same
  timezone-suffix stripping ("Mar-15-2026T09:00:00Z",
  "15-Mar-2026T09:00:00.5-04:00") and fractional-second
  handling, including weekday-prefixed ("Sunday,
  16-Mar-2026T09:00:00.123Z") and full-month ("March-15-2026T09:00:00")
  forms; the space-separated hyphenated datetimes already
  governed, this block closes the T-separated gap; while an
  impossible T-separated hyphenated month-name datetime
  ("30-Feb-2026T10:00:00.123Z") or a malformed suffix
  ("Mar-15-2026T10:30:00.123+99:99") is left untouched so
  the gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 113, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.450s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a
  T-separated hyphenated month-name-datetime 2-row CSV: 2
  in, 1 governed, 1 quarantined).

- Nov 1, 2026 build block (9:05 AM run):
  AM/PM month-name datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  as a month-name datetime on a 12-hour clock
  ("Mar 15, 2026 10:30:00 AM", "15 Mar 2026 02:30 PM", or a
  fractional-second "March 15, 2026 10:30:00.123 AM", the way
  exports write month-name datetimes with an AM/PM marker)
  now has the marker dropped on read and normalizes to its
  date part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, with the same marker handling for
  weekday-prefixed ("Sunday, Mar 16, 2026 09:00:00 pm"),
  hyphenated ("15-Mar-2026 10:30:00 AM"), and ordinal
  ("Mar 15th, 2026 2:30pm", spaced or attached marker)
  forms, since the marker is stripped as a candidate before
  the ordinal and timezone steps run; while an impossible
  AM/PM datetime ("Feb 30, 2026 10:00:00 AM") or a
  malformed marker ("Mar 15, 2026 10:30:00 XM") is left
  untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized
  value; 2 new tests (suite now 115, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.405s; governed,
  quarantine, and summary.json outputs byte-identical to
  pre-run outputs; audit.csv 10,001 lines, differing only
  in its timestamp column; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on an
  AM/PM month-name-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Nov 1, 2026 build block (3:05 PM run):
  AM/PM slash datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a slash datetime on a 12-hour clock
  ("03/15/2026 10:30:00 AM", "15/03/2026 02:30 PM", or a
  fractional-second "03/15/2026 10:30:00.123 AM", the way
  exports write slash datetimes with an AM/PM marker)
  now has the marker dropped on read and normalizes to its
  date part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, with the same marker handling for
  year-first ("2026/03/15 10:30:00 AM"), weekday-prefixed
  ("Sunday, 03/16/2026 09:00:00 pm"), and attached-marker
  ("03/15/2026 2:30pm") forms, since the marker is stripped
  as a candidate before the slash datetime formats run; while
  an impossible AM/PM slash datetime ("02/30/2026 10:00:00
  AM") or a malformed marker ("03/15/2026 10:30:00 XM") is
  left untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized
  value; 2 new tests (suite now 117, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.457s; governed,
  quarantine, and summary.json outputs byte-identical to
  pre-run outputs; audit.csv 10,001 lines; zero raw member
  IDs, zero patient names in all outputs; CLI smoke-tested
  on an AM/PM slash-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Nov 1, 2026 build block (9:05 PM run):
  AM/PM dot datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a dot-separated datetime on a 12-hour clock
  ("2026.03.15 10:30:00 AM", "2026.03.15T09:00:00 PM", or a
  fractional-second "2026.03.15 10:30:00.123 AM", the way
  exports write dot datetimes with an AM/PM marker)
  now has the marker dropped on read and normalizes to its
  date part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, with the same marker handling for
  weekday-prefixed ("Sunday, 2026.03.16 09:00:00 pm") and
  attached-marker ("2026.03.15 2:30pm") forms, since the
  marker is stripped as a candidate before the dot datetime
  formats run; while an impossible AM/PM dot datetime
  ("2026.02.30 10:00:00 AM") or a malformed marker
  ("2026.03.15 10:30:00 XM") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 119,
  all passing; README count updated to 119, which also
  corrects the 115 figure left by the prior run). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.475s; governed,
  quarantine, and summary.json outputs byte-identical to
  pre-run outputs; audit.csv 10,001 lines; zero raw member
  IDs, zero patient names in all outputs; CLI smoke-tested
  on an AM/PM dot-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Nov 2, 2026 build block (3:05 AM run):
  AM/PM compact datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a compact datetime on a 12-hour clock
  ("20260315 10:30:00 AM", "20260315T09:00:00 PM", or a
  fractional-second "20260315 10:30:00.123 AM", the way
  exports write compact datetimes with an AM/PM marker)
  now has the marker dropped on read and normalizes to its
  date part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, with the same marker handling for
  weekday-prefixed ("Sunday, 20260316 09:00:00 pm") and
  attached-marker ("20260315 2:30pm") forms, since the
  marker is stripped as a candidate before the compact datetime
  formats run; while an impossible AM/PM compact datetime
  ("20260230 10:00:00 AM") or a malformed marker
  ("20260315 10:30:00 XM") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 121,
  all passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.465s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines;
  zero raw member IDs, zero patient names in all outputs;
  CLI smoke-tested on an AM/PM compact-datetime 2-row CSV:
  2 in, 1 governed, 1 quarantined).

- Nov 2, 2026 build block (9:05 AM run):
  AM/PM underscore datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an underscore datetime on a 12-hour clock
  ("2026_03_15 10:30:00 AM", "2026_03_15T09:00:00 PM", or a
  fractional-second "2026_03_15 10:30:00.123 AM", the way
  exports write underscore datetimes with an AM/PM marker)
  now has the marker dropped on read and normalizes to its
  date part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, with the same marker handling for
  weekday-prefixed ("Sunday, 2026_03_16 09:00:00 pm") and
  attached-marker ("2026_03_15 2:30pm") forms, since the
  marker is stripped as a candidate before the underscore
  datetime formats run; while an impossible AM/PM underscore
  datetime ("2026_02_30 10:00:00 AM") or a malformed marker
  ("2026_03_15 10:30:00 XM") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 123,
  all passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.459s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines;
  zero raw member IDs, zero patient names in all outputs;
  CLI smoke-tested on an AM/PM underscore-datetime 2-row CSV:
  2 in, 1 governed, 1 quarantined).

- Nov 2, 2026 build block (3:05 PM run):
  AM/PM numeric hyphen datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a numeric hyphen datetime on a 12-hour clock
  ("03-15-2026 10:30:00 AM", "15-03-2026T09:00:00 PM", or a
  fractional-second "03-15-2026 10:30:00.123 AM", the way
  exports write hyphen datetimes with an AM/PM marker)
  now has the marker dropped on read and normalizes to its
  date part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, with the same US-first order
  ("03-04-2026 10:30:00 AM" governs as 2026-03-04), and the
  same marker handling for weekday-prefixed
  ("Sunday, 03-16-2026 09:00:00 pm") and attached-marker
  ("03-15-2026 2:30pm") forms, since the marker is stripped
  before the hyphen datetime formats run; while an
  impossible AM/PM hyphen datetime ("02-30-2026 10:00:00
  AM") or a malformed marker ("03-15-2026 10:30:00 XM") is
  left untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized
  value; 2 new tests (suite now 125, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.438s; governed,
  quarantine, and summary.json outputs byte-identical to
  pre-run outputs; audit.csv 10,001 lines; zero raw member
  IDs, zero patient names in all outputs; CLI smoke-tested
  on an AM/PM numeric-hyphen-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Nov 3, 2026 build block (9:05 AM run):
  AM/PM timezone-suffixed ISO datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date written
  as an ISO datetime on a 12-hour clock carrying a timezone
  suffix AFTER the AM/PM marker ("2026-03-15 10:30:00 AM Z",
  "2026-03-15T09:00:00 PM -04:00", or a fractional-second
  "2026-03-15 10:30:00.123 AM +05:30", the way exports write
  zoned 12-hour timestamps) now has the suffix dropped first
  so the marker strips normally, then normalizes to its date
  part (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date, with the same handling for
  weekday-prefixed ("Sunday, 2026-03-16 09:00:00 pm Z")
  forms; the suffix-before-marker order ("2026-03-15
  10:30:00Z AM") already governed and still does; while an
  impossible AM/PM timezone-suffixed ISO datetime
  ("2026-02-30 10:00:00 AM Z") or a malformed suffix
  ("2026-03-15 10:30:00 AM +99:99") is left untouched so
  the gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 129, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.462s; audit.csv 10,001 lines; zero raw
  member IDs, zero patient names in all outputs; CLI
  smoke-tested on an AM/PM timezone-suffixed ISO-datetime
  2-row CSV: 2 in, 1 governed, 1 quarantined).

- Nov 3, 2026 build block (3:05 AM run):
  AM/PM ISO datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an ISO datetime on a 12-hour clock
  ("2026-03-15 10:30:00 AM", "2026-03-15T09:00:00 PM", or a
  fractional-second "2026-03-15 10:30:00.123 AM", the way
  exports write ISO datetimes with an AM/PM marker)
  now has the marker dropped on read and normalizes to its
  date part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, with the same marker handling for
  weekday-prefixed ("Sunday, 2026-03-16 09:00:00 pm") and
  attached-marker ("2026-03-15 2:30pm") forms, since the
  marker is stripped in the generic ISO-datetime branch
  before the ISO datetime formats run; while an
  impossible AM/PM ISO datetime ("2026-02-30 10:00:00 AM")
  or a malformed marker ("2026-03-15 10:30:00 XM") is
  left untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized
  value; 2 new tests (suite now 127, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.443s; governed,
  quarantine, and summary.json outputs byte-identical to
  pre-run outputs; audit.csv 10,001 lines; zero raw member
  IDs, zero patient names in all outputs; CLI smoke-tested
  on an AM/PM ISO-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Nov 3, 2026 build block (3:05 PM run):
  AM/PM timezone-suffixed slash datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  slash datetime on a 12-hour clock carrying a timezone suffix
  AFTER the AM/PM marker ("03/15/2026 10:30:00 AM Z",
  "03/15/2026T09:00:00 PM -04:00", or a fractional-second
  "03/15/2026 10:30:00.123 AM +05:30", the way exports write
  zoned 12-hour slash timestamps) now has the suffix dropped
  first so the marker strips normally, then normalizes to its
  date part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, with the same US-first order
  ("15/03/2026 10:30:00 AM Z" governs as 2026-03-15), and the
  same handling for weekday-prefixed
  ("Sunday, 03/16/2026 09:00:00 pm Z") forms; the
  suffix-before-marker order ("03/15/2026 10:30:00Z AM")
  already governed and still does; while an impossible
  AM/PM timezone-suffixed slash datetime
  ("02/30/2026 10:00:00 AM Z") or a malformed suffix
  ("03/15/2026 10:30:00 AM +99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 131, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.415s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on an AM/PM
  timezone-suffixed slash-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Nov 4, 2026 build block (3:05 AM run):
  AM/PM timezone-suffixed dot datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date written
  as a dot-separated datetime on a 12-hour clock carrying a
  timezone suffix AFTER the AM/PM marker ("2026.03.15
  10:30:00 AM Z", "2026.03.15T09:00:00 PM -04:00", or a
  fractional-second "2026.03.15 10:30:00.123 AM +05:30",
  the way exports write zoned 12-hour dot timestamps) now
  has the suffix dropped first so the marker strips
  normally, then normalizes to its date part (YYYY-MM-DD)
  and governs instead of quarantining as
  unparseable_date, with the same handling for
  weekday-prefixed ("Sunday, 2026.03.17 10:30:00 am
  +05:30") forms; the suffix-before-marker order
  ("2026.03.15 10:30:00Z AM") already governed and still
  does; while an impossible AM/PM timezone-suffixed dot
  datetime ("2026.02.30 10:00:00 AM Z") or a malformed
  suffix ("2026.03.15 10:30:00 AM +99:99") is left
  untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized
  value; 2 new tests (suite now 133, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.517s;
  governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001
  lines; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on an AM/PM
  timezone-suffixed dot-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Nov 4, 2026 build block (9:05 AM run):
  AM/PM timezone-suffixed compact datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date written
  as a compact datetime on a 12-hour clock carrying a
  timezone suffix AFTER the AM/PM marker ("20260315
  10:30:00 AM Z", "20260315T09:00:00 PM -04:00", or a
  fractional-second "20260315 10:30:00.123 AM +05:30",
  the way exports write zoned 12-hour compact timestamps) now
  has the suffix dropped first so the marker strips
  normally, then normalizes to its date part (YYYY-MM-DD)
  and governs instead of quarantining as
  unparseable_date, with the same handling for
  weekday-prefixed ("Sunday, 20260316 10:30:00 am
  +05:30") forms; the suffix-before-marker order
  ("20260315 10:30:00Z AM") governs too, via the suffix
  strip after the marker strip; while an impossible AM/PM
  timezone-suffixed compact datetime ("20260230 10:00:00
  AM Z") or a malformed suffix ("20260315 10:30:00 AM
  +99:99") is left untouched so the gates quarantine it
  normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 135, all
  passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged;
  runtime 0.410s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv
  10,001 lines; zero raw member IDs, zero patient names in
  all outputs; CLI smoke-tested on an AM/PM
  timezone-suffixed compact-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Nov 4, 2026 build block (3:05 PM run):
  AM/PM timezone-suffixed underscore datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as an underscore datetime on a
  12-hour clock carrying a timezone suffix AFTER the AM/PM
  marker ("2026_03_15 10:30:00 AM Z",
  "2026_03_15T09:00:00 PM -04:00", or a fractional-second
  "2026_03_15 10:30:00.123 AM +05:30", the way exports write
  zoned 12-hour underscore timestamps) now has the suffix
  dropped first so the marker strips normally, then
  normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date, with the same
  handling for weekday-prefixed ("Sunday, 2026_03_16
  10:30:00 am +05:30") forms; the suffix-before-marker order
  ("2026_03_15 10:30:00Z AM") governs too, via the suffix
  strip after the marker strip; while an impossible AM/PM
  timezone-suffixed underscore datetime ("2026_02_30
  10:00:00 AM Z") or a malformed suffix ("2026_03_15
  10:30:00 AM +99:99") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 137,
  all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.444s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv
  10,001 lines; zero raw member IDs, zero patient names in
  all outputs; CLI smoke-tested on an AM/PM
  timezone-suffixed underscore-datetime 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Nov 4, 2026 build block (9:05 PM run):
  AM/PM timezone-suffixed numeric hyphen datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as a numeric hyphen datetime on a
  12-hour clock carrying a timezone suffix ("03-15-2026
  10:30:00 AM Z", "15-03-2026T09:00:00 PM -04:00", or a
  weekday-prefixed "Sunday, 03-16-2026 10:30:00 am +05:30",
  the way exports write zoned 12-hour hyphen timestamps)
  now has the suffix trailing the marker dropped first so
  the marker strips normally, and normalizes to its date
  part (YYYY-MM-DD) and governs instead of quarantining
  as unparseable_date, with the same US-first order and
  the same suffix-before-marker handling ("03-15-2026
  10:30:00Z AM" governs too); while an impossible AM/PM
  timezone-suffixed hyphen datetime ("02-30-2026 10:00:00
  AM Z") or a malformed suffix ("03-15-2026 10:30:00 AM
  +99:99") is left untouched so the gates quarantine it
  normally; the quality gates stay strict and see only
  the normalized value; 2 new tests (suite now 139, all
  passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.538s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001
  lines; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on an AM/PM timezone-suffixed
  numeric-hyphen-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Nov 5, 2026 build block (3:05 AM run):
  AM/PM timezone-suffixed month-name datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as a month-name datetime on a
  12-hour clock carrying a timezone suffix ("Mar 15, 2026
  10:30:00 AM Z", "15 Mar 2026T09:00:00 PM -04:00", or a
  weekday-prefixed "Sunday, Mar 16, 2026 10:30:00 am
  +05:30", the way exports write zoned 12-hour month-name
  timestamps) now has the suffix trailing the marker
  dropped first so the marker strips normally, and
  normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date, with the
  same suffix-before-marker handling ("Mar 15, 2026
  10:30:00Z AM" governs too); while an impossible AM/PM
  timezone-suffixed month-name datetime ("Feb 30, 2026
  10:00:00 AM Z") or a malformed suffix ("Mar 15, 2026
  10:30:00 AM +99:99") is left untouched so the gates
  quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite
  now 141, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.497s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on an
  AM/PM timezone-suffixed month-name-datetime 2-row CSV:
  2 in, 1 governed, 1 quarantined).

- Nov 5, 2026 build block (9:05 AM run):
  two-digit-year slash dates and datetimes (read_claims_csv
  in hipaa_pipeline_framework/io.py) — a service_date written
  in legacy two-digit-year slash form ("03/15/26" or
  "15/03/26", the way legacy exports write dates) now
  normalizes to ISO form (YYYY-MM-DD) on read and governs
  instead of quarantining as unparseable_date; the two-digit
  year follows Python's strptime %y pivot (00-68 read as
  2000-2068, 69-99 as 1969-1999), so "03/15/99" governs as
  1999-03-15; the same US-first order holds ("03/04/26"
  reads as 2026-03-04), and a leading component above 12
  reads day-first ("26/03/15" governs as 2015-03-26), so
  there is no separate year-first two-digit form;
  two-digit-year slash datetimes ("03/15/26 10:30:00",
  fractional and timezone-suffixed forms, and
  weekday-prefixed AM/PM forms such as "Sunday, 03/16/26
  10:30:00 am +05:30") normalize to their date part the same
  way; while an impossible two-digit-year date ("02/30/26")
  or a malformed suffix ("03/15/26 10:30:00+99:99") is left
  untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 143, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.459s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a two-digit-year
  slash-date 2-row CSV: 2 in, 1 governed, 1 quarantined).
  This push also carries the Nov 5 3:05 AM run's AM/PM
  timezone-suffixed month-name datetime block (suite 141),
  which had not been pushed before — remote head before this
  push was still the 139-test commit f8f6cc53.

- Nov 5, 2026 build block (3:05 PM run):
  two-digit-year dot-separated dates and datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written in legacy two-digit-year dot form
  ("03.15.26" or "15.03.26", the way legacy exports write
  dates) now normalizes to ISO form (YYYY-MM-DD) on read and
  governs instead of quarantining as unparseable_date; the
  two-digit year follows Python's strptime %y pivot (00-68
  read as 2000-2068, 69-99 as 1969-1999), so "03.15.99"
  governs as 1999-03-15; the same US-first order holds
  ("03.04.26" reads as 2026-03-04), and a leading component
  above 12 reads day-first ("26.03.15" governs as
  2015-03-26), so there is no separate year-first two-digit
  form; two-digit-year dot datetimes ("03.15.26 10:30:00",
  fractional and timezone-suffixed forms, and weekday-prefixed
  AM/PM forms such as "Sunday, 03.16.26 10:30:00 am +05:30")
  normalize to their date part the same way; while an
  impossible two-digit-year date ("02.30.26") or a malformed
  suffix ("03.15.26 10:30:00+99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite now
  145, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.556s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv 10,001
  lines; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a two-digit-year dot-date
  2-row CSV: 2 in, 1 governed, 1 quarantined).

- Nov 5, 2026 build block (9:05 PM run):
  two-digit-year numeric hyphen dates and datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written in legacy two-digit-year hyphen form
  ("03-15-26" or "15-03-26", the way legacy exports write
  dates) now normalizes to ISO form (YYYY-MM-DD) on read and
  governs instead of quarantining as unparseable_date; the
  two-digit year follows Python's strptime %y pivot (00-68
  read as 2000-2068, 69-99 as 1969-1999), so "03-15-99"
  governs as 1999-03-15; the same US-first order holds
  ("03-04-26" reads as 2026-03-04), and a leading component
  above 12 reads day-first ("26-03-15" governs as
  2015-03-26), so there is no separate year-first two-digit
  form; two-digit-year hyphen datetimes ("03-15-26 10:30:00",
  fractional and timezone-suffixed forms, and weekday-prefixed
  AM/PM forms such as "Sunday, 03-16-26 10:30:00 am +05:30")
  normalize to their date part the same way; while an
  impossible two-digit-year date ("02-30-26") or a malformed
  suffix ("03-15-26 10:30:00+99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite now
  147, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.499s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv 10,001
  lines; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a two-digit-year hyphen-date
  2-row CSV: 2 in, 1 governed, 1 quarantined).

- Nov 6, 2026 build block (3:05 AM run):
  two-digit-year underscore dates and datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written in legacy two-digit-year underscore
  form ("03_15_26" or "15_03_26", the way legacy exports
  write dates) now normalizes to ISO form (YYYY-MM-DD) on
  read and governs instead of quarantining as
  unparseable_date; the two-digit year follows Python's
  strptime %y pivot (00-68 read as 2000-2068, 69-99 as
  1969-1999), so "03_15_99" governs as 1999-03-15; the same
  US-first order holds ("03_04_26" reads as 2026-03-04),
  and a leading component above 12 reads day-first
  ("26_03_15" governs as 2015-03-26), so there is no
  separate year-first two-digit form; two-digit-year
  underscore datetimes ("03_15_26 10:30:00", fractional and
  timezone-suffixed forms, and weekday-prefixed AM/PM forms
  such as "Sunday, 03_16_26 10:30:00 am +05:30") normalize
  to their date part the same way; while an impossible
  two-digit-year date ("02_30_26") or a malformed suffix
  ("03_15_26 10:30:00+99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite now
  149, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.522s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv 10,001
  lines, differing only in its timestamp column; zero raw
  member IDs, zero patient names in all outputs; CLI
  smoke-tested on a two-digit-year underscore-date 2-row CSV:
  2 in, 1 governed, 1 quarantined).

- Nov 6, 2026 build block (9:05 PM run):
  two-digit-year month-name dates and datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written in legacy two-digit-year month-name
  form ("Mar 15, 26" or "15 Mar 26", "15-Mar-26" or
  "Mar-15-26", the way legacy exports write dates) now
  normalizes to ISO form (YYYY-MM-DD) on read and governs
  instead of quarantining as unparseable_date; the
  two-digit year follows Python's strptime %y pivot (00-68
  read as 2000-2068, 69-99 as 1969-1999), so "Mar 15, 99"
  governs as 1999-03-15; the four-digit-year formats are
  tried first, so a four-digit year never reaches a %y
  format; two-digit-year month-name datetimes ("Mar 15, 26
  10:30:00", fractional and timezone-suffixed forms
  included) and weekday-prefixed and ordinal forms
  ("Sunday, March 16, 26 10:30:00 am +05:30",
  "March 15th, 26") normalize to their date part the same
  way, through the same candidate stripping; while an
  impossible two-digit-year month-name date ("Feb 30, 26")
  or a malformed suffix ("Mar 15, 26 10:30:00+99:99") is
  left untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized
  value; 2 new tests (suite now 151, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.522s;
  governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001
  lines, differing only in its timestamp column; zero raw
  member IDs, zero patient names in all outputs; CLI
  smoke-tested on a two-digit-year month-name-date 2-row
  CSV: 2 in, 1 governed, 1 quarantined).

- Nov 7, 2026 build block (3:05 AM run):
  two-digit-year compact dates and datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written in legacy two-digit-year compact
  form ("031526" or "150326", the way legacy mainframe
  exports write dates) now normalizes to ISO form
  (YYYY-MM-DD) on read and governs instead of quarantining
  as unparseable_date; the two-digit year follows Python's
  strptime %y pivot (00-68 read as 2000-2068, 69-99 as
  1969-1999), so "031599" governs as 1999-03-15; the same
  US-first order holds ("030426" reads as 2026-03-04),
  and a leading component above 12 reads day-first
  ("260315" governs as 2015-03-26), so there is no
  separate year-first two-digit form; two-digit-year
  compact datetimes ("031526 10:30:00Z", fractional and
  timezone-suffixed forms, and weekday-prefixed AM/PM
  forms such as "Sunday, 031626 10:30:00 am +05:30")
  normalize to their date part the same way; while an
  impossible two-digit-year compact date ("023026") or a
  malformed suffix ("031526 10:30:00+99:99") is left
  untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized
  value; 2 new tests (suite now 153, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.601s;
  governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001
  lines, differing only in its timestamp column; zero raw
  member IDs, zero patient names in all outputs; CLI
  smoke-tested on a two-digit-year compact-date 2-row
  CSV: 2 in, 1 governed, 1 quarantined).

- Nov 7, 2026 build block (9:05 AM run):
  Unix epoch timestamps (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written
  as a bare Unix epoch — a nine- or ten-digit count of
  seconds since 1970-01-01 UTC ("1710460800") or a twelve-
  or thirteen-digit count of milliseconds
  ("1710460800000"), the way API and database exports
  write timestamps — now converts to its UTC date
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; only epochs whose UTC date falls in
  2000-01-01..2100-01-01 are accepted, so an epoch outside
  that window ("9999999999" reads as 2286, "0000000000"
  as 1970) is left untouched so the gates quarantine it
  normally, as is an eleven-digit bare number, which is
  ambiguous between seconds and milliseconds, and a bare
  number of any other length ("12345"); a non-midnight
  epoch still governs as its UTC date part; the quality
  gates stay strict and see only the normalized value; 2
  new tests (suite now 155, all passing). Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.473s; governed, quarantine,
  and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on
  an epoch-timestamp 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Nov 7, 2026 build block (3:05 PM run):
  Unix microsecond epoch timestamps (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a bare Unix epoch in microseconds — a fifteen- or
  sixteen-digit count since 1970-01-01 UTC
  ("1710460800000000"), the way API and database exports
  write timestamps — now converts to its UTC date
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; only epochs whose UTC date falls in
  2000-01-01..2100-01-01 are accepted, so a microsecond
  epoch outside that window ("9999999999999999" reads as
  2286, "171046080000000" reads as 1975) is left untouched
  so the gates quarantine it normally, as is a
  fourteen-digit bare number, which can only be
  microseconds before 2000, and a seventeen-digit bare
  number, which no branch claims; a non-midnight
  microsecond epoch still governs as its UTC date part;
  the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 157, all
  passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.389s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv
  10,001 lines; zero raw member IDs, zero patient names
  in all outputs; CLI smoke-tested on a microsecond-epoch
  2-row CSV: 2 in, 1 governed, 1 quarantined).
- Nov 7, 2026 build block (9:05 PM run):
  Unix nanosecond epoch timestamps (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a bare Unix epoch in nanoseconds — an eighteen- or
  nineteen-digit count since 1970-01-01 UTC
  ("1710460800000000000"), the way API and database exports
  write timestamps — now converts to its UTC date
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; only epochs whose UTC date falls in
  2000-01-01..2100-01-01 are accepted, so a nanosecond epoch
  outside that window ("9999999999999999999" reads as 2286,
  "171046080000000000" reads as 1975) is left untouched so
  the gates quarantine it normally, as is a seventeen-digit
  bare number, which can only be nanoseconds before 2000,
  and a twenty-digit bare number, which no branch claims; a
  non-midnight nanosecond epoch still governs as its UTC date
  part; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 159, all
  passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.390s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001
  lines, differing only in its timestamp column; zero raw
  member IDs, zero patient names in all outputs; CLI
  smoke-tested on a nanosecond-epoch 2-row CSV: 2 in, 1
  governed, 1 quarantined).
- Nov 8, 2026 build block (9:05 AM run):
  Ordinal (Julian) dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a seven-digit YYYYDDD day-of-year form ("2026074", the way
  mainframe exports write dates) or the ISO 8601 ordinal form
  ("2026-074") now converts to its calendar date (YYYY-MM-DD)
  and governs instead of quarantining as unparseable_date;
  weekday-prefixed ("Sunday, 2026075"), timezone-suffixed
  ("2026074 10:30:00Z"), fractional-second, and AM/PM ordinal
  datetimes normalize to their date part the same way; a
  day-of-year that is not a real day of that year ("2026366"
  in 2026, which has 365 days, or "2026000") is left untouched
  so the gates quarantine it normally, as is a weekday-prefixed
  ordinal date with a bogus label ("Funday, 2026074") or a
  malformed suffix ("2026074 10:30:00+99:99"); the parsed year
  is checked against the written year because strptime's %j
  rolls a too-large day into the next year instead of failing
  (verified: "2026366" parses to 2027-01-01, so the check is
  what rejects it); the quality gates stay strict and see only
  the normalized value; 2 new tests (suite now 161, all
  passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.489s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  differing only in its timestamp column; audit.jsonl identical
  ignoring timestamps; zero raw member IDs, zero patient names
  in all outputs; CLI smoke-tested on an ordinal-date 2-row
  CSV: 2 in, 1 governed, 1 quarantined).
- Nov 8, 2026 build block (9:05 PM run):
  ISO week dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an ISO 8601 week date ("2026-W11-1", the way scheduling
  exports write dates) or the compact form ("2026W111") or the
  week alone ("2026-W11", its Monday) now converts to its
  calendar date (YYYY-MM-DD) and governs instead of
  quarantining as unparseable_date; weekday-prefixed ("Sunday,
  2026-W11-2"), timezone-suffixed ("2026-W11-1 10:30:00Z"),
  and fractional-second week-date datetimes normalize to their
  date part the same way; a week that does not exist in that
  year ("2025-W53-1", a 52-week year) or a weekday outside 1-7
  ("2026-W11-8") is left untouched so the gates quarantine it
  normally, as is a weekday-prefixed week date with a bogus
  label ("Funday, 2026-W11-1") or a malformed suffix
  ("2026-W11-1 10:30:00+99:99"); the week-only form parses via
  fromisocalendar because strptime's %G needs a weekday
  directive (verified: "%G-W%V" without one raises
  ValueError), and the parsed ISO year and week are checked
  against the written ones; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 163,
  all passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.504s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  differing only in its timestamp column; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on an
  ISO-week-date 2-row CSV: 2 in, 1 governed, 1 quarantined).
- Nov 9, 2026 build block (9:05 AM run):
  space-separated timezone suffixes on month-name datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as a month-name datetime carrying its
  zone after a space ("Mar 15, 2026 10:30:00 +05:00", "15 Mar
  2026 10:30:00 -0400", or "Mar 15, 2026 10:30:00 Z", the way
  API and EHR exports write zoned month-name timestamps) now
  has the suffix and its separating space stripped on read and
  normalizes to its date part (YYYY-MM-DD) and governs instead
  of quarantining as unparseable_date; a named RFC 2822 zone
  ("Sun, 15 Mar 2026 10:30:00 GMT", "15 Mar 2026 10:30:00
  EST", "Mar 15, 2026 10:30:00 UTC", the way email headers
  write zoned month-name timestamps) strips the same way, but
  only from the RFC 2822 obsolete-zone list plus UTC (UT, GMT,
  UTC, EST, EDT, CST, CDT, MST, MDT, PST, PDT), and the
  AM/PM marker step drops a named zone trailing a marker
  ("Mar 15, 2026 10:30:00 AM GMT"); weekday-prefixed,
  fractional-second, hyphenated, and AM/PM forms normalize
  the same way. This also fixes a latent gap: stripping an
  attached suffix left no trailing space, but stripping a
  space-separated one left "10:30:00 " behind, which strptime
  rejects — the space-separated form quarantined until now
  while the attached form governed (verified by probe before
  the fix; the same latent trailing-space issue was probed in
  the slash, dot, compact, underscore, and numeric-hyphen
  families and still stands there for a later run). An unknown
  zone ("15 Mar 2026 10:30:00 XYZ"), an attached named zone
  with no space ("15 Mar 2026 10:30:00GMT"), a malformed
  numeric suffix ("Mar 15, 2026 10:30:00 +99:99"), an
  impossible date carrying a valid suffix ("Feb 30, 2026
  10:00:00 GMT"), or a bogus weekday label ("Funday, 15 Mar
  2026 10:30:00 GMT") is left untouched so the gates
  quarantine it normally; only the date part governs, so no
  zone is ever converted; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 165,
  all passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.400s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines;
  zero raw member IDs, zero patient names in all outputs;
  CLI smoke-tested on a space-separated-tz 2-row CSV: 2 in,
  1 governed, 1 quarantined).
- Nov 9, 2026 build block (3:05 PM run):
  space-separated timezone suffixes on slash datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as a slash datetime carrying its zone
  after a space ("03/15/2026 10:30:00 +05:00", "03/15/2026
  10:30:00 -0400", or "03/15/2026 10:30:00 Z", the way API and
  EHR exports write zoned slash timestamps) now has the suffix
  and its separating space stripped on read and normalizes to
  its date part (YYYY-MM-DD) and governs instead of
  quarantining as unparseable_date; weekday-prefixed,
  fractional-second, day-first, year-first, two-digit-year,
  T-separated, and AM/PM forms (suffix before the marker,
  "03/15/2026 10:30:00 +05:00 AM") normalize the same way.
  This closes the latent trailing-space gap the 9:05 AM run
  probed in this family: stripping a space-separated suffix
  left "10:30:00 " behind, which strptime rejects — the
  space-separated form quarantined until now while the
  attached form governed (verified by probe before the fix;
  the same latent issue still stands in the dot, compact,
  underscore, and numeric-hyphen families for a later run).
  A malformed numeric suffix ("03/15/2026 10:30:00 +99:99"),
  an out-of-range offset ("+25:00", "+05:60"), a malformed
  marker ("03/15/2026 10:30:00 +05:00 XM"), an impossible
  date carrying a valid suffix ("02/30/2026 10:30:00
  +05:00"), or a bogus weekday label ("Funday, 03/15/2026
  10:30:00 +05:00") is left untouched so the gates
  quarantine it normally; only the date part governs, so no
  zone is ever converted; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 167,
  all passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.479s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  differing only in its timestamp column; audit.jsonl
  identical ignoring timestamps; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  space-separated-tz 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Nov 10, 2026 build block (3:05 AM run):
  space-separated timezone suffixes on dot datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as a dot datetime carrying its zone
  after a space ("2026.03.15 10:30:00 +05:00", "2026.03.15
  10:30:00 -0400", or "2026.03.15 10:30:00 Z", the way API and
  EHR exports write zoned dot timestamps) now has the suffix
  and its separating space stripped on read and normalizes to
  its date part (YYYY-MM-DD) and governs instead of
  quarantining as unparseable_date; weekday-prefixed,
  fractional-second, two-digit-year (US and day-first),
  T-separated, and AM/PM forms (suffix before the marker,
  "2026.03.15 10:30:00 +05:00 AM") normalize the same way.
  This closes the latent trailing-space gap the Nov 9 3:05 PM
  run probed in this family: stripping a space-separated suffix
  left "10:30:00 " behind, which strptime rejects — the
  space-separated form quarantined until now while the
  attached form governed (verified by probe before the fix;
  the same latent issue still stands in the compact,
  underscore, and numeric-hyphen families for a later run).
  A malformed numeric suffix ("2026.03.15 10:30:00 +99:99"),
  an out-of-range offset ("+25:00", "+05:60"), a malformed
  marker ("2026.03.15 10:30:00 +05:00 XM"), an impossible
  date carrying a valid suffix ("2026.02.30 10:00:00
  +05:00"), or a bogus weekday label ("Funday, 2026.03.15
  10:30:00 +05:00") is left untouched so the gates
  quarantine it normally; only the date part governs, so no
  zone is ever converted; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 169,
  all passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.454s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  identical ignoring its timestamp column; audit.jsonl
  identical ignoring timestamps; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  space-separated-tz 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Nov 10, 2026 build block (9:05 AM run):
  space-separated timezone suffixes on compact datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as a compact datetime carrying its zone
  after a space ("20260315 10:30:00 +05:00", "20260315
  10:30:00 -0400", or "20260315 10:30:00 Z", the way API and
  EHR exports write zoned compact timestamps) now has the suffix
  and its separating space stripped on read and normalizes to
  its date part (YYYY-MM-DD) and governs instead of
  quarantining as unparseable_date; weekday-prefixed,
  fractional-second, no-seconds, no-colon-offset, T-separated,
  and AM/PM forms (suffix before the marker,
  "20260315 10:30:00 +05:00 AM") normalize the same way.
  Unlike the slash and dot families, the compact guards are
  strict fullmatches, so the fix also widens the guard arms to
  accept an optional space before the trailing zone — the
  trailing-space strip alone would never have been reached.
  This closes the latent gap the Nov 10 3:05 AM run probed in
  this family: the space-separated form quarantined until now
  while the attached form governed (verified by probe before
  the fix; the same latent issue still stands in the
  two-digit-year compact, underscore, and numeric-hyphen
  families for a later run). A malformed numeric suffix
  ("20260315 10:30:00 +99:99"), an out-of-range offset
  ("+25:00", "+05:60"), a malformed marker ("20260315
  10:30:00 +05:00 XM"), an impossible date carrying a valid
  suffix ("20260230 10:00:00 +05:00"), or a bogus weekday
  label ("Funday, 20260315 10:30:00 +05:00") is left untouched
  so the gates quarantine it normally; only the date part
  governs, so no zone is ever converted; the quality gates stay
  strict and see only the normalized value; 2 new tests (suite
  now 171, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged; runtime
  0.496s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  identical ignoring its timestamp column; audit.jsonl
  identical ignoring timestamps; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  space-separated-tz 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Nov 10, 2026 build block (9:05 PM run):
  space-separated timezone suffixes on underscore datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as an underscore datetime carrying its zone
  after a space ("2026_03_15 10:30:00 +05:00", "2026_03_15
  10:30:00 -0400", or "2026_03_15 10:30:00 Z", the way API and
  EHR exports write zoned underscore timestamps) now has the suffix
  and its separating space stripped on read and normalizes to
  its date part (YYYY-MM-DD) and governs instead of
  quarantining as unparseable_date; weekday-prefixed,
  fractional-second, two-digit-year, no-seconds, no-colon-offset,
  T-separated, and AM/PM forms (suffix before the marker,
  "2026_03_15 10:30:00 +05:00 AM") normalize the same way.
  Like the compact family, the underscore guards are strict
  fullmatches, so the fix also widens the guard arms to accept an
  optional space before the trailing zone — the trailing-space
  strip alone would never have been reached. This closes the
  latent gap the Nov 10 3:05 AM run probed in this family: the
  space-separated form quarantined until now while the attached
  form governed (verified by probe before the fix; the same latent
  issue still stands in the two-digit-year compact and
  numeric-hyphen families for a later run). A malformed numeric
  suffix ("2026_03_15 10:30:00 +99:99"), an out-of-range offset
  ("+25:00", "+05:60"), a malformed marker ("2026_03_15
  10:30:00 +05:00 XM"), an impossible date carrying a valid
  suffix ("2026_02_30 10:00:00 +05:00"), or a bogus weekday
  label ("Funday, 2026_03_15 10:30:00 +05:00") is left untouched
  so the gates quarantine it normally; only the date part
  governs, so no zone is ever converted; the quality gates stay
  strict and see only the normalized value; 2 new tests (suite
  now 173, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged; runtime
  0.447s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  identical ignoring its timestamp column; audit.jsonl
  identical ignoring timestamps; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  space-separated-tz 2-row CSV: 2 in, 1 governed,
  1 quarantined).
- Nov 11, 2026 build block (3:05 AM run):
  space-separated timezone suffixes on numeric hyphen datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as a numeric hyphen datetime carrying its
  zone after a space ("03-15-2026 10:30:00 +05:00", "03-15-2026
  10:30:00 -0400", or "03-15-2026 10:30:00 Z", the way API and EHR
  exports write zoned hyphen timestamps) now has the suffix and
  its separating space stripped on read and normalizes to its date
  part (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; weekday-prefixed, fractional-second,
  two-digit-year, day-first, no-seconds, no-colon-offset,
  T-separated, and AM/PM forms (suffix before the marker,
  "03-15-2026 10:30:00 +05:00 AM") normalize the same way.
  Like the compact and underscore families, the hyphen guards are
  strict fullmatches, so the fix also widens the guard arms to
  accept an optional space before the trailing zone — the
  trailing-space strip alone would never have been reached.
  This closes the latent gap the Nov 10 3:05 AM run probed in this
  family: the space-separated form quarantined until now while the
  attached form governed (verified by probe before the fix; the
  same latent issue now stands only in the two-digit-year compact
  family for a later run). A malformed numeric suffix
  ("03-15-2026 10:30:00 +99:99"), an out-of-range offset
  ("+25:00", "+05:60"), a malformed marker ("03-15-2026
  10:30:00 +05:00 XM"), an impossible date carrying a valid
  suffix ("02-30-2026 10:00:00 +05:00"), or a bogus weekday
  label ("Funday, 03-15-2026 10:30:00 +05:00") is left untouched
  so the gates quarantine it normally; only the date part
  governs, so no zone is ever converted; the quality gates stay
  strict and see only the normalized value; 2 new tests (suite
  now 175, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged; runtime
  0.424s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines and
  audit.jsonl identical ignoring their timestamp columns; zero
  raw member IDs, zero patient names in all outputs; CLI
  smoke-tested on a space-separated-tz numeric-hyphen 2-row CSV:
  2 in, 1 governed, 1 quarantined).

- Nov 11, 2026 build block (9:05 AM run):
  space-separated timezone suffixes on two-digit-year compact
  datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a two-digit-year compact datetime carrying its zone after a
  space ("031526 10:30:00 +05:00", "031526 10:30:00 -0400",
  or "031526 10:30:00 Z", the way API and EHR exports write
  zoned compact timestamps) now has the suffix and its
  separating space stripped on read and normalizes to its date
  part (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; weekday-prefixed, fractional-second,
  day-first, no-seconds, T-separated, and AM/PM forms (suffix
  before the marker, "031526 10:30:00 +05:00 AM") normalize
  the same way. Like the compact, underscore, and
  numeric-hyphen families, the guards are strict fullmatches,
  so the fix widens the guard arms to accept an optional space
  before the trailing zone, and adds the trailing-space strip
  after the suffix strip that the short-compact branch was
  missing — the strip alone would never have been reached.
  This closes the last latent trailing-space gap: the
  month-name, slash, dot, compact, underscore, and
  numeric-hyphen families were all closed by earlier runs. A
  malformed numeric suffix ("031526 10:30:00 +99:99"), an
  out-of-range offset ("+25:00"), an impossible date carrying
  a valid suffix ("023026 10:30:00 +05:00"), or a bogus
  weekday label ("Funday, 031526 10:30:00 +05:00") is left
  untouched so the gates quarantine it normally; only the date
  part governs, so no zone is ever converted; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 177, all passing). Demo re-verified same
  run (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.415s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, identical ignoring its timestamp
  column; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a space-separated-tz
  two-digit-year-compact 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Nov 11, 2026 build block (3:05 PM run):
  space-separated timezone suffixes on ISO week-date
  datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an ISO week-date datetime carrying its zone after a space
  ("2026-W11-1 10:30:00 +05:00", "2026-W11-1 10:30:00 -0400",
  or "2026-W11-1 10:30:00 Z", the way API and EHR exports write
  zoned week-date timestamps) now has the suffix and its
  separating space stripped on read and normalizes to its date
  part (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; weekday-prefixed, fractional-second,
  T-separated, compact-form, and no-seconds forms normalize
  the same way. Like the compact, underscore, and
  numeric-hyphen families, the week-date guards are strict
  fullmatches, so the fix widens the guard arm to accept an
  optional space before the trailing zone, and adds the
  trailing-space strip after the suffix strip that the
  week-date branch was missing — the strip alone would never
  have been reached. This closes a gap the Nov 11 3:05 PM
  probe found: the space-separated form quarantined until now
  while the attached form governed (verified by probe before
  the fix; the same latent issue now stands only in the
  ordinal-date family, and named zones such as GMT/EST are
  still unhandled outside the month-name family, for later
  runs). A malformed numeric suffix ("2026-W11-1 10:30:00
  +99:99"), an out-of-range offset ("+25:00", "+05:60"), an
  impossible week carrying a valid suffix ("2025-W53-1
  10:30:00 +05:00"), or a bogus weekday label ("Funday,
  2026-W11-1 10:30:00 +05:00") is left untouched so the
  gates quarantine it normally; only the date part governs,
  so no zone is ever converted; the quality gates stay
  strict and see only the normalized value; 2 new tests
  (suite now 179, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.660s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, audit counts match the pipeline
  counts; zero raw member IDs in all outputs; CLI
  smoke-tested on a space-separated-tz week-date 2-row CSV:
  2 in, 1 governed, 1 quarantined).

- Nov 11, 2026 build block (9:05 PM run):
  space-separated timezone suffixes on ordinal-date
  datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an ordinal-date datetime carrying its zone after a space
  ("2026074 10:30:00 +05:00", "2026-074 10:30:00 -0400",
  or "2026074 10:30:00 Z", the way API and EHR exports write
  zoned ordinal timestamps) now has the suffix and its
  separating space stripped on read and normalizes to its date
  part (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; weekday-prefixed, fractional-second,
  T-separated, no-seconds, and AM/PM forms (suffix before the
  marker, "2026074 10:30:00 +05:00 AM") normalize the same
  way. Like the compact, underscore, numeric-hyphen, and
  week-date families, the ordinal guards are strict
  fullmatches, so the fix widens the guard arms to accept an
  optional space before the trailing zone (the attached-tz,
  fractional, and suffix-before-marker AM/PM arms), and adds
  the trailing-space strip after the suffix strip that the
  ordinal branch was missing — the strip alone would never
  have been reached. This closes a gap the Nov 11 9:05 PM
  probe found: the space-separated form quarantined until now
  while the attached form governed (verified by probe before
  the fix; the ordinal family was the last one standing with
  this latent issue — month-name, slash, dot, compact,
  underscore, numeric-hyphen, two-digit-year compact, and
  week-date are all closed; named zones such as GMT/EST are
  still unhandled outside the month-name family, for later
  runs). A malformed numeric suffix ("2026074 10:30:00
  +99:99"), an out-of-range offset ("+25:00", "+05:60"), an
  impossible day carrying a valid suffix ("2026366 10:30:00
  +05:00"), or a bogus weekday label ("Funday, 2026074
  10:30:00 +05:00") is left untouched so the gates quarantine
  it normally; only the date part governs, so no zone is ever
  converted; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 181, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed,
  8,411 quarantined, reasons unchanged; runtime 0.457s;
  governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  audit counts match the pipeline counts; zero raw member IDs
  in all outputs; CLI smoke-tested on a space-separated-tz
  ordinal 2-row CSV: 2 in, 1 governed, 1 quarantined).

- Nov 12, 2026 build block (3:05 AM run):
  named RFC 2822 timezone zones on ISO datetimes
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an ISO datetime carrying a named zone ("2026-03-15 10:30:00
  GMT", "2026-03-15T09:00:00 EST", or a weekday-prefixed
  "Sunday, 2026-03-15 10:30:00 GMT", the way email headers
  write zoned ISO timestamps) now has the zone stripped on
  read and normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date; fractional-second,
  no-seconds, lowercase ("utc"), and AM/PM forms normalize the
  same way, in both orders — suffix trailing the marker
  ("2026-03-15 10:30:00 AM GMT") and suffix before the marker
  ("2026-03-15 10:30:00 GMT AM"). The ISO branch strips zones
  in two places (before the marker strip, and again after it),
  so the fix adds the named-zone alternative to both: only the
  RFC 2822 obsolete-zone list plus UTC is accepted — UT, GMT,
  UTC, EST, EDT, CST, CDT, MST, MDT, PST, PDT — mirroring the
  month-name family, which was the only family handling named
  zones until now. This closes a gap the Nov 12 3:05 AM probe
  found: the named-zone form quarantined until now while the
  attached "Z" and numeric-offset forms governed (verified by
  probe before the fix; named zones still stand in the slash,
  dot, compact, underscore, numeric-hyphen, two-digit-year,
  ordinal, and week-date families, for later runs). An unknown
  zone ("2026-03-15 10:30:00 XYZ"), a zone-like tail that is
  not a zone ("2026-03-15 10:30:00 WEST"), an impossible date
  carrying a valid zone ("2026-02-30 10:00:00 GMT"), an unknown
  zone trailing a marker ("2026-03-15 10:30:00 AM XYZ"), or a
  bogus weekday label ("Funday, 2026-03-15 10:30:00 GMT") is
  left untouched so the gates quarantine it normally; only the
  date part governs, so no zone is ever converted; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 183, all passing). Demo re-verified same
  run (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.438s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a named-zone ISO
  2-row CSV: 2 in, 1 governed, 1 quarantined).

- Nov 12, 2026 build block (9:05 AM run):
  named RFC 2822 timezone zones on slash datetimes
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a slash datetime carrying a named zone ("03/15/2026 10:30:00
  GMT", "03/15/2026T09:00:00 EST", or a weekday-prefixed
  "Sunday, 03/15/2026 10:30:00 GMT", the way email headers
  write zoned slash timestamps) now has the zone stripped on
  read and normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date; fractional-second,
  no-seconds, lowercase ("utc"), day-first, year-first,
  two-digit-year, and AM/PM forms normalize the same way, in
  both orders — suffix trailing the marker ("03/15/2026
  10:30:00 AM GMT") and suffix before the marker ("03/15/2026
  10:30:00 GMT AM"). The slash branch strips zones in two
  places (the AM/PM suffix step, and the timezone branch after
  the marker strip), so the fix adds the named-zone alternative
  to both: only the RFC 2822 obsolete-zone list plus UTC is
  accepted — UT, GMT, UTC, EST, EDT, CST, CDT, MST, MDT, PST,
  PDT — mirroring the ISO and month-name families. This closes
  a gap the Nov 12 9:05 AM probe found: the named-zone form
  quarantined until now while the attached "Z" and numeric-offset
  forms governed (verified by probe before the fix; named zones
  still stand in the dot, compact, underscore, numeric-hyphen,
  two-digit-year compact, ordinal, and week-date families, for
  later runs). An unknown zone ("03/15/2026 10:30:00 XYZ"), a
  zone-like tail that is not a zone ("03/15/2026 10:30:00
  WEST"), an impossible date carrying a valid zone
  ("02/30/2026 10:00:00 GMT"), an unknown zone trailing a
  marker ("03/15/2026 10:30:00 AM XYZ"), or a bogus weekday
  label ("Funday, 03/15/2026 10:30:00 GMT") is left untouched
  so the gates quarantine it normally; only the date part
  governs, so no zone is ever converted; the quality gates stay
  strict and see only the normalized value; 2 new tests (suite
  now 185, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged; runtime
  0.623s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  audit counts match the pipeline counts; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  named-zone slash 2-row CSV: 2 in, 1 governed, 1 quarantined).

- Nov 12, 2026 build block (3:05 PM run):
  named RFC 2822 timezone zones on dot datetimes
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a dot datetime carrying a named zone ("2026.03.15 10:30:00
  GMT", "2026.03.15T09:00:00 EST", or a weekday-prefixed
  "Sunday, 2026.03.15 10:30:00 GMT", the way email headers
  write zoned dot timestamps) now has the zone stripped on
  read and normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date;
  fractional-second, no-seconds, lowercase ("utc"),
  two-digit-year, day-first two-digit-year, and AM/PM forms
  normalize the same way, in both orders — suffix trailing the
  marker ("2026.03.15 10:30:00 AM GMT") and suffix before the
  marker ("2026.03.15 10:30:00 GMT AM"). The dot branch strips
  zones in two places (the AM/PM suffix step, and the timezone
  branch after the marker strip), so the fix adds the
  named-zone alternative to both: only the RFC 2822
  obsolete-zone list plus UTC is accepted — UT, GMT, UTC, EST,
  EDT, CST, CDT, MST, MDT, PST, PDT — mirroring the ISO,
  month-name, and slash families. This closes a gap the Nov 12
  3:05 PM probe found: the named-zone form quarantined until
  now while the attached "Z" and numeric-offset forms governed
  (verified by probe before the fix; named zones still stand in
  the compact, underscore, numeric-hyphen, two-digit-year
  compact, ordinal, and week-date families, for later runs). An
  unknown zone ("2026.03.15 10:30:00 XYZ"), a zone-like tail
  that is not a zone ("2026.03.15 10:30:00 WEST"), an
  impossible date carrying a valid zone ("2026.02.30 10:00:00
  GMT"), an unknown zone trailing a marker ("2026.03.15
  10:30:00 AM XYZ"), or a bogus weekday label ("Funday,
  2026.03.15 10:30:00 GMT") is left untouched so the gates
  quarantine it normally; only the date part governs, so no
  zone is ever converted; the quality gates stay strict and see
  only the normalized value; 2 new tests (suite now 187, all
  passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.496s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  audit counts match the pipeline counts; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  named-zone dot 11-row CSV: 11 in, 10 governed,
  1 quarantined).

- Nov 12, 2026 build block (9:05 PM run):
  named RFC 2822 timezone zones on compact datetimes
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a compact datetime carrying a named zone ("20260315 10:30:00
  GMT", "20260315T09:00:00 EST", or a weekday-prefixed
  "Sunday, 20260315 10:30:00 GMT", the way email headers
  write zoned compact timestamps) now has the zone stripped on
  read and normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date;
  fractional-second, no-seconds, lowercase ("utc"),
  and AM/PM forms normalize the same way, in both orders —
  suffix trailing the marker ("20260315 10:30:00 AM GMT") and
  suffix before the marker ("20260315 10:30:00 GMT AM"). The
  compact branch strips zones in two places (the AM/PM suffix
  step, and the suffix strip after the marker strip), so the fix
  adds the named-zone alternative to both, and to the four
  timezone-carrying guard arms: only the RFC 2822 obsolete-zone
  list plus UTC is accepted — UT, GMT, UTC, EST, EDT, CST, CDT,
  MST, MDT, PST, PDT — mirroring the ISO, month-name, slash,
  and dot families. This closes a gap the Nov 12 9:05 PM probe
  found: the named-zone form quarantined until now while the
  attached "Z" and numeric-offset forms governed (verified by
  probe before the fix; named zones still stand in the
  underscore, numeric-hyphen, two-digit-year compact, ordinal,
  and week-date families, for later runs). An unknown zone
  ("20260315 10:30:00 XYZ"), a zone-like tail that is not a zone
  ("20260315 10:30:00 WEST"), an impossible date carrying a
  valid zone ("20260230 10:00:00 GMT"), an unknown zone trailing
  a marker ("20260315 10:30:00 AM XYZ"), or a bogus weekday
  label ("Funday, 20260315 10:30:00 GMT") is left untouched so
  the gates quarantine it normally; only the date part governs,
  so no zone is ever converted; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite now
  189, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.599s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  audit counts match the pipeline counts; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  named-zone compact 11-row CSV: 11 in, 10 governed,
  1 quarantined).

- Nov 13, 2026 build block (3:05 AM run):
  named RFC 2822 timezone zones on underscore datetimes
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an underscore datetime carrying a named zone ("2026_03_15
  10:30:00 GMT", "2026_03_15T09:00:00 EST", or a
  weekday-prefixed "Sunday, 2026_03_15 10:30:00 GMT", the way
  email headers write zoned underscore timestamps) now has the
  zone stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; fractional-second, no-seconds, lowercase
  ("utc"), two-digit-year, day-first two-digit-year, and AM/PM
  forms normalize the same way, in both orders — suffix
  trailing the marker ("2026_03_15 10:30:00 AM GMT") and suffix
  before the marker ("2026_03_15 10:30:00 GMT AM"). The
  underscore branch strips zones in two places (the AM/PM
  suffix step, and the suffix strip after the marker strip), so
  the fix adds the named-zone alternative to both, and to the
  six timezone-carrying guard arms (four-digit and
  two-digit-year forms each): only the RFC 2822 obsolete-zone
  list plus UTC is accepted — UT, GMT, UTC, EST, EDT, CST, CDT,
  MST, MDT, PST, PDT — mirroring the ISO, month-name, slash,
  dot, and compact families. This closes a gap the Nov 13 3:05
  AM probe found: the named-zone form quarantined until now
  while the attached "Z" and numeric-offset forms governed
  (verified by probe before the fix; named zones still stand in
  the numeric-hyphen, two-digit-year compact, ordinal, and
  week-date families, for later runs). An unknown zone
  ("2026_03_15 10:30:00 XYZ"), a zone-like tail that is not a
  zone ("2026_03_15 10:30:00 WEST"), an impossible date carrying
  a valid zone ("2026_02_30 10:00:00 GMT"), an unknown zone
  trailing a marker ("2026_03_15 10:30:00 AM XYZ"), or a bogus
  weekday label ("Funday, 2026_03_15 10:30:00 GMT") is left
  untouched so the gates quarantine it normally; only the date
  part governs, so no zone is ever converted; the quality gates
  stay strict and see only the normalized value; 2 new tests
  (suite now 191, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.445s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, audit counts match the pipeline
  counts; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a named-zone underscore 11-row
  CSV: 11 in, 10 governed, 1 quarantined).

- Nov 13, 2026 build block (9:05 AM run):
  named RFC 2822 timezone zones on numeric hyphen datetimes
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a numeric hyphen datetime carrying a named zone ("03-15-2026
  10:30:00 GMT", "15-03-2026T09:00:00 EST", or a
  weekday-prefixed "Sunday, 03-15-2026 10:30:00 GMT", the way
  email headers write zoned hyphen timestamps) now has the
  zone stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; fractional-second, no-seconds, lowercase
  ("utc"), two-digit-year, day-first two-digit-year, and AM/PM
  forms normalize the same way, in both orders — suffix
  trailing the marker ("03-15-2026 10:30:00 AM GMT") and suffix
  before the marker ("03-15-2026 10:30:00 GMT AM"). The
  hyphen branch strips zones in two places (the AM/PM
  suffix step, and the suffix strip after the marker strip), so
  the fix adds the named-zone alternative to both, and to the
  three timezone-carrying guard arms: only the RFC 2822
  obsolete-zone list plus UTC is accepted — UT, GMT, UTC, EST,
  EDT, CST, CDT, MST, MDT, PST, PDT — mirroring the ISO,
  month-name, slash, dot, compact, and underscore families.
  This closes a gap the Nov 13 9:05 AM probe found: the
  named-zone form quarantined until now while the attached "Z"
  and numeric-offset forms governed (verified by probe before
  the fix; named zones still stand in the two-digit-year
  compact, ordinal, and week-date families, for later runs).
  An unknown zone ("03-15-2026 10:30:00 XYZ"), a zone-like tail
  that is not a zone ("03-15-2026 10:30:00 WEST"), an impossible
  date carrying a valid zone ("02-30-2026 10:00:00 GMT"), an
  unknown zone trailing a marker ("03-15-2026 10:30:00 AM XYZ"),
  or a bogus weekday label ("Funday, 03-15-2026 10:30:00 GMT")
  is left untouched so the gates quarantine it normally; only
  the date part governs, so no zone is ever converted; the
  quality gates stay strict and see only the normalized value;
  2 new tests (suite now 193, all passing). Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.435s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, audit counts match the pipeline
  counts; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a named-zone hyphen 11-row CSV:
  11 in, 10 governed, 1 quarantined).

- Nov 13, 2026 build block (3:05 PM run):
  named RFC 2822 timezone zones on two-digit-year compact
  datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a two-digit-year compact datetime carrying a named zone
  ("031526 10:30:00 GMT", "031526T09:00:00 EST", or a
  weekday-prefixed "Sunday, 031526 10:30:00 GMT", the way
  email headers write zoned compact timestamps) now has the
  zone stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; fractional-second, no-seconds, lowercase
  ("utc"), two-digit-year ("031599" governs as 1999-03-15),
  day-first, and AM/PM forms normalize the same way, in both
  orders — suffix trailing the marker ("031526 10:30:00 AM
  GMT") and suffix before the marker ("031526 10:30:00 GMT
  AM"). The two-digit-year compact branch strips zones in two
  places (the AM/PM suffix step, and the suffix strip after
  the marker strip), so the fix adds the named-zone
  alternative to both, and to the four timezone-carrying guard
  arms (plain, fractional-second, AM/PM-trailing, and
  suffix-before-marker): only the RFC 2822 obsolete-zone list
  plus UTC is accepted — UT, GMT, UTC, EST, EDT, CST, CDT,
  MST, MDT, PST, PDT — mirroring the ISO, month-name, slash,
  dot, compact, underscore, and numeric-hyphen families.
  This closes a gap the Nov 13 3:05 PM probe found: the
  named-zone form quarantined until now while the attached "Z"
  and numeric-offset forms governed (verified by probe before
  the fix; named zones still stand in the ordinal and
  week-date families, for later runs).
  An unknown zone ("031526 10:30:00 XYZ"), a zone-like tail
  that is not a zone ("031526 10:30:00 WEST"), an impossible
  date carrying a valid zone ("023026 10:00:00 GMT"), an
  unknown zone trailing a marker ("031526 10:30:00 AM XYZ"),
  or a bogus weekday label ("Funday, 031526 10:30:00 GMT")
  is left untouched so the gates quarantine it normally; only
  the date part governs, so no zone is ever converted; the
  quality gates stay strict and see only the normalized value;
  2 new tests (suite now 195, all passing). Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.600s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, audit counts match the pipeline
  counts; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a named-zone two-digit-year
  compact 11-row CSV: 11 in, 10 governed, 1 quarantined).

- Nov 13, 2026 build block (9:05 PM run):
  named RFC 2822 timezone zones on ordinal (Julian) datetimes
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an ordinal datetime carrying a named zone ("2026074
  10:30:00 GMT", "2026-074T09:00:00 EST", or a
  weekday-prefixed "Sunday, 2026075 10:30:00 GMT", the way
  email headers write zoned ordinal timestamps) now has the
  zone stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; fractional-second, no-seconds, lowercase
  ("utc"), ISO-ordinal ("2026-074"), day 075, and AM/PM forms
  normalize the same way, in both orders — suffix trailing
  the marker ("2026074 10:30:00 AM GMT") and suffix before
  the marker ("2026074 10:30:00 GMT AM"). The ordinal branch
  strips zones in two places (the AM/PM suffix step, and the
  suffix strip after the marker strip), so the fix adds the
  named-zone alternative to both, and to the four
  timezone-carrying guard arms (plain, fractional-second,
  AM/PM-trailing, and suffix-before-marker): only the RFC
  2822 obsolete-zone list plus UTC is accepted — UT, GMT,
  UTC, EST, EDT, CST, CDT, MST, MDT, PST, PDT — mirroring
  the ISO, month-name, slash, dot, compact, underscore,
  numeric-hyphen, and two-digit-year compact families. This
  closes a gap the Nov 13 9:05 PM probe found: the named-zone
  form quarantined until now while the attached "Z" and
  numeric-offset forms governed (verified by probe before
  the fix; named zones still stand in the week-date family,
  for a later run). An unknown zone ("2026074 10:30:00 XYZ"),
  a zone-like tail that is not a zone ("2026074 10:30:00
  WEST"), an impossible date carrying a valid zone ("2026366
  10:00:00 GMT"), an unknown zone trailing a marker
  ("2026074 10:30:00 AM XYZ"), or a bogus weekday label
  ("Funday, 2026074 10:30:00 GMT") is left untouched so the
  gates quarantine it normally; only the date part governs,
  so no zone is ever converted; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite now
  197, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.518s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv
  10,001 lines, audit counts match the pipeline counts;
  zero raw member IDs, zero patient names in all outputs;
  CLI smoke-tested on a named-zone ordinal 11-row CSV: 11
  in, 11 governed, 0 quarantined).

- Nov 14, 2026 build block (3:05 AM run):
  named RFC 2822 timezone zones on ISO week-date datetimes
  (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an ISO week-date datetime carrying a named zone ("2026-W11-1
  10:30:00 GMT", "2026-W11-1T09:00:00 EST", or a
  weekday-prefixed "Sunday, 2026-W11-2 10:30:00 GMT", the way
  email headers write zoned week-date timestamps) now has the
  zone stripped on read and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; fractional-second, no-seconds, lowercase
  ("utc"), and compact ("2026W111") forms normalize the same
  way. Only the RFC 2822 obsolete-zone list plus UTC is
  accepted — UT, GMT, UTC, EST, EDT, CST, CDT, MST, MDT, PST,
  PDT — mirroring the ordinal family. This closes the gap the
  Nov 13 9:05 PM run left open: the named-zone form quarantined
  until now while the attached "Z" and numeric-offset forms
  governed (verified by probe before the fix). An unknown zone
  ("2026-W11-1 10:30:00 XYZ"), a zone-like tail that is not a
  zone ("2026-W11-1 10:30:00 WEST"), an impossible week
  carrying a valid zone ("2025-W53-1 10:00:00 GMT"), a weekday
  outside 1-7 carrying a valid zone ("2026-W11-8 10:30:00
  GMT"), or a bogus weekday label ("Funday, 2026-W11-1
  10:30:00 GMT") is left untouched so the gates quarantine it
  normally; only the date part governs, so no zone is ever
  converted; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 199, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed,
  8,411 quarantined, reasons unchanged; runtime 0.534s;
  governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  audit counts match the pipeline counts; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  named-zone week-date 2-row CSV: 2 in, 1 governed,
  1 quarantined). Remaining gap noted: AM/PM week-date
  datetimes ("2026-W11-1 10:30:00 AM", with or without a
  trailing named zone) still quarantine — the week-date branch
  has no AM/PM handling yet — for a later run.

- Nov 14, 2026 build block (9:05 AM run):
  AM/PM ISO week-date datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  an ISO week-date datetime on a 12-hour clock ("2026-W11-1
  10:30:00 AM", "2026-W11-1T09:00:00 PM", or a
  weekday-prefixed "Sunday, 2026-W11-2 09:00:00 pm", the way
  exports write week-date datetimes with a 12-hour clock) now
  has its marker dropped on read and normalizes to its date
  part (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; fractional-second, no-seconds, lowercase
  ("am"), and compact ("2026W111") forms normalize the same
  way, as does an AM/PM form carrying a zone after the marker
  ("2026-W11-1 10:30:00 PM GMT") or before it ("2026-W11-1
  10:30:00Z AM", "2026-W11-1 10:30:00+05:30 PM"). This closes
  the gap the Nov 14 3:05 AM run left open: the AM/PM form
  quarantined until now while the 24-hour forms governed
  (verified by probe before the fix). A malformed marker
  ("2026-W11-1 10:30:00 XM"), an unknown zone after the
  marker ("2026-W11-1 10:30:00 AM XYZ"), a malformed offset
  after the marker ("2026-W11-1 10:30:00 AM +99:99"), an
  impossible week carrying a valid marker and zone
  ("2025-W53-1 10:00:00 AM Z"), a weekday outside 1-7
  carrying a valid marker ("2026-W11-8 10:30:00 AM"), or a
  bogus weekday label ("Funday, 2026-W11-1 10:30:00 AM") is
  left untouched so the gates quarantine it normally; only the
  date part governs, so the hour needs no conversion; the
  quality gates stay strict and see only the normalized value;
  2 new tests (suite now 201, all passing). Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.671s; governed, quarantine,
  and summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, audit counts match the pipeline
  counts; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on an AM/PM week-date 2-row CSV:
  2 in, 1 governed, 1 quarantined).

- Nov 14, 2026 build block (3:05 PM run):
  plain 24-hour compact datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a compact datetime with no zone or marker ("20260315
  10:30:00", "20260315T09:00:00", or a weekday-prefixed
  "Sunday, 20260316 10:30:00", the way exports write compact
  datetimes) now normalizes to its date part (YYYY-MM-DD)
  and governs instead of quarantining as unparseable_date;
  no-seconds forms ("20260315 10:30", "20260315T09:00")
  normalize the same way. This closes the gap the probe
  found: every suffixed and marked compact variant governed
  while the plain form quarantined (verified by probe before
  the fix). An impossible plain compact datetime ("20260230
  10:00:00"), an unknown zone ("20260315 10:30:00 XYZ"), or
  a bogus weekday label ("Funday, 20260315 10:30:00") is left
  untouched so the gates quarantine it normally; only the
  date part governs, so the hour needs no conversion; the
  quality gates stay strict and see only the normalized value;
  2 new tests (suite now 203, all passing). Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.609s; governed, quarantine,
  and summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, audit counts match the pipeline
  counts; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a plain compact-datetime
  2-row CSV: 2 in, 1 governed, 1 quarantined). Remaining
  gaps noted: the plain 24-hour form in the two-digit-year
  compact family ("260315 10:30:00" still quarantines) and
  colon-less basic ISO times ("20260315T103000", with or
  without a trailing "Z") — for later runs.

- Nov 14, 2026 build block (9:05 PM run):
  plain 24-hour two-digit-year compact datetimes
  (read_claims_csv in hipaa_pipeline_framework/io.py) — a
  service_date written as a two-digit-year compact datetime
  with no zone or marker ("031526 10:30:00", "031526T09:00:00",
  or a weekday-prefixed "Sunday, 031626 10:30:00", the way
  exports write compact datetimes) now normalizes to its date
  part (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; no-seconds forms ("031526 10:30",
  "031526T09:00") normalize the same way, and a leading
  component above 12 reads day-first ("260315 10:30:00"
  governs as 2015-03-26). This closes the gap the probe
  found: every suffixed and marked two-digit-year compact
  variant governed while the plain form quarantined (verified
  by probe before the fix) — the guard had no plain
  alternative, so the plain form never reached the parsers.
  An impossible plain two-digit-year compact datetime
  ("023026 10:00:00"), an unknown zone ("031526 10:30:00
  XYZ"), or a bogus weekday label ("Funday, 031526 10:30:00")
  is left untouched so the gates quarantine it normally; only
  the date part governs, so the hour needs no conversion; the
  quality gates stay strict and see only the normalized value;
  2 new tests (suite now 205, all passing). Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.421s; governed, quarantine,
  and summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, audit counts match the pipeline
  counts; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a plain two-digit-year
  compact-datetime 2-row CSV: 2 in, 1 governed,
  1 quarantined). Remaining gap noted: colon-less basic ISO
  times ("20260315T103000", with or without a trailing "Z") —
  for a later run.

- Nov 15, 2026 build block (3:05 AM run):
  colon-less basic ISO times (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  compact datetime with a colon-less basic ISO time
  ("20260315T103000", with or without a trailing "Z", the way
  some API exports write compact datetimes with no colons in the
  time) now normalizes to its date part (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date; a no-seconds form
  ("20260315T1030"), a fractional-second form
  ("20260315T103000.123"), a timezone-suffixed form
  ("20260315T103000+05:30", a colon-less offset
  "20260315T103000+0530", or a named RFC 2822 zone
  "20260315T103000 GMT"), and a weekday-prefixed form ("Sunday,
  20260315T103000") normalize the same way. This closes the gap
  the Nov 14 9:05 PM run noted: every colon form governed while
  the colon-less form quarantined (verified by probe before the
  fix) — the guard had no colon-less alternative, so the value
  never reached the parsers. An impossible basic ISO datetime
  ("20260230T103000"), an out-of-range time ("20260315T256000"),
  or a malformed suffix ("20260315T103000+99:99") is left
  untouched so the gates quarantine it normally; only the date
  part governs, so the hour needs no conversion; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 207, all passing). This push also carries the
  Nov 14 9:05 PM run's plain 24-hour two-digit-year compact
  datetime block (suite 205), which had not been pushed before
  — remote head before this push was still the 203-test commit
  72a1f963. Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.436s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  identical ignoring its timestamp column; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  colon-less basic ISO-time 2-row CSV: 2 in, 1 governed,
  1 quarantined). Remaining gaps noted: a space-separated
  basic ISO time ("20260315 103000"), an AM/PM basic ISO time
  ("20260315T103000 AM"), and a two-digit-year compact basic
  ISO time ("031526T103000") — for later runs.

- Nov 15, 2026 build block (9:05 AM run):
  space-separated basic ISO times (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  compact datetime with a space-separated colon-less basic ISO
  time ("20260315 103000", the way some exports write a compact
  datetime with a space instead of the "T" separator) now
  normalizes to its date part (YYYY-MM-DD) and governs instead
  of quarantining as unparseable_date; a no-seconds form
  ("20260315 1030"), a fractional-second form
  ("20260315 103000.123"), a timezone-suffixed form
  ("20260315 103000Z", "20260315 103000+05:30", a colon-less
  offset "20260315 103000+0530", or a named RFC 2822 zone
  "20260315 103000 GMT"), and a weekday-prefixed form ("Sunday,
  20260316 103000") normalize the same way. This closes the gap
  the Nov 15 3:05 AM run noted: every T-separated form governed
  while the space-separated form quarantined (verified by probe
  before the fix) — the guard had no space-separated
  alternative, so the value never reached the parsers. An
  impossible space-separated basic ISO datetime
  ("20260230 103000"), an out-of-range time ("20260315 256000"),
  or a malformed suffix ("20260315 103000+99:99") is left
  untouched so the gates quarantine it normally; only the date
  part governs, so the hour needs no conversion; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 209, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.389s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines, audit counts match the pipeline
  counts; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a space-separated basic ISO-time
  2-row CSV: 2 in, 1 governed, 1 quarantined). Remaining gaps
  noted: an AM/PM basic ISO time ("20260315T103000 AM") and a
  two-digit-year compact basic ISO time ("031526T103000") — for
  later runs.

- Nov 15, 2026 build block (3:05 PM run):
  AM/PM basic ISO times (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  compact datetime with an AM/PM marker on a colon-less basic ISO
  time ("20260315T103000 AM", the way some exports write a compact
  datetime on a 12-hour clock with no colons in the time) now
  normalizes to its date part (YYYY-MM-DD) and governs instead of
  quarantining as unparseable_date; a no-seconds form
  ("20260315T1030 AM"), a fractional-second form
  ("20260315T103000.123 AM"), a timezone-suffixed form
  ("20260315T103000 AM Z", "20260315T103000 AM +05:30", a named
  RFC 2822 zone "20260315T103000 AM GMT", or the
  suffix-before-marker order "20260315T103000Z AM"), a
  space-separated form ("20260315 103000 AM", "20260315 1030
  PM"), an attached-marker form ("20260315T103000am"), and a
  weekday-prefixed form ("Sunday, 20260315T103000 AM") normalize
  the same way; only the date part governs, so the hour needs no
  conversion. This closes the gap the Nov 15 9:05 AM run noted:
  every 24-hour basic ISO form governed while the AM/PM form
  quarantined (verified by probe before the fix) — the guard had
  no AM/PM alternative for a colon-less time, so the value never
  reached the parsers; the existing marker/suffix strips and
  strptime formats already handled the form once the guard let
  it in. An impossible AM/PM basic ISO datetime
  ("20260230T103000 AM"), an out-of-range time
  ("20260315T256000 AM"), a malformed suffix
  ("20260315T103000 AM +99:99"), an unknown zone
  ("20260315T103000 AM XYZ"), or a malformed marker
  ("20260315T103000 XM") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and see
  only the normalized value; 2 new tests (suite now 211, all
  passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.738s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  identical ignoring its timestamp column; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on an
  AM/PM basic ISO-time 2-row CSV: 2 in, 1 governed,
  1 quarantined). Remaining gap noted: a two-digit-year compact
  basic ISO time ("031526T103000") — for a later run.

- Nov 15, 2026 build block (9:05 PM run):
  two-digit-year compact basic ISO datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  two-digit-year compact datetime with a colon-less basic ISO time
  ("031526T103000", the basic ISO 8601 form on a two-digit-year
  date, the way some API exports write legacy compact datetimes
  with no colons in the time) now normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; a no-seconds form ("031526T1030"), a
  fractional-second form ("031526T103000.123"), a
  timezone-suffixed form ("031526T103000Z",
  "031526T103000+05:30", a colon-less offset "031526T103000+0530",
  or a named RFC 2822 zone "031526T103000 GMT"), a
  space-separated form ("031526 103000"), an AM/PM form
  ("031526T103000 AM", including suffix-before-marker
  "031526T103000Z AM" and marker-before-suffix "031526T103000 AM
  Z"), a day-first form ("150326T103000" governs as 2026-03-15),
  and a weekday-prefixed form ("Sunday, 031626T103000") normalize
  the same way; the two-digit year follows Python's %y pivot, so
  "031599T103000" governs as 1999-03-15; only the date part
  governs, so the hour needs no conversion. This closes the gap
  the Nov 15 3:05 PM run noted: every colon form governed while
  the colon-less form quarantined (verified by probe before the
  fix — 23 valid forms quarantined) — the guard had no colon-less
  alternative, so the value never reached the parsers; the
  existing marker/suffix strips and strptime formats already
  handled the form once the guard let it in, with 12 new basic
  ISO formats added to the parse list. An impossible basic ISO
  datetime ("023026T103000"), an out-of-range time
  ("031526T256000"), a malformed suffix ("031526T103000+99:99"),
  an unknown zone ("031526T103000 XYZ"), or a malformed marker
  ("031526T103000 XM") is left untouched so the gates quarantine
  it normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 213, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.594s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines, differing only in its
  timestamp column; zero raw member IDs, zero patient names in
  all outputs; CLI smoke-tested on a two-digit-year compact
  basic ISO-time 2-row CSV: 2 in, 1 governed, 1 quarantined).
  Remaining gap noted: ordinal basic ISO times ("2026074T103000")
  are unprobed — for a later run.

- Nov 16, 2026 build block (3:05 AM run):
  ordinal basic ISO datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as an
  ordinal datetime with a colon-less basic ISO time
  ("2026074T103000", the basic ISO 8601 form on an ordinal date,
  the way some API exports write ordinal datetimes with no colons
  in the time) now normalizes to its date part (YYYY-MM-DD) and
  governs instead of quarantining as unparseable_date; a
  no-seconds form ("2026074T1030"), a fractional-second form
  ("2026074T103000.123"), a timezone-suffixed form
  ("2026074T103000Z", "2026074T103000+05:30", a colon-less offset
  "2026074T103000+0530", or a named RFC 2822 zone
  "2026074T103000 GMT"), a space-separated form ("2026074
  103000"), an AM/PM form ("2026074T103000 AM", including
  suffix-before-marker "2026074T103000Z AM" and
  marker-before-suffix "2026074T103000 AM Z"), an attached-marker
  form ("2026074T103000am"), and a weekday-prefixed form
  ("Sunday, 2026074T103000") normalize the same way, as does the
  ISO ordinal spelling ("2026-074T103000"); only the date part
  governs, so the hour needs no conversion. This closes the gap
  the Nov 15 9:05 PM run noted: every colon form governed while
  the colon-less form quarantined (verified by probe before the
  fix — 20 valid forms quarantined) — the guard had no colon-less
  alternative, so the value never reached the parsers; the
  existing marker/suffix strips and strptime formats already
  handled the form once the guard let it in, with 12 new basic
  ISO formats added to the parse list. An impossible basic ISO
  ordinal datetime ("2026366T103000"), an out-of-range time
  ("2026074T256000"), a malformed suffix
  ("2026074T103000+99:99"), an unknown zone
  ("2026074T103000 XYZ"), or a malformed marker
  ("2026074T103000 XM") is left untouched so the gates quarantine
  it normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 215, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.455s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines, differing only in its
  timestamp column; zero raw member IDs, zero patient names in
  all outputs; CLI smoke-tested on an ordinal basic ISO-time
  2-row CSV: 2 in, 1 governed, 1 quarantined).
  Remaining gap noted: week-date basic ISO times
  ("2026-W11-1T103000") are unprobed — for a later run.

- Nov 16, 2026 build block (9:05 AM run):
  week-date basic ISO datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  week-date datetime with a colon-less basic ISO time
  ("2026-W11-1T103000", the basic ISO 8601 form on a week date,
  the way some API exports write week-date datetimes with no
  colons in the time) now normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date; a no-seconds form ("2026-W11-1T1030"), a
  fractional-second form ("2026-W11-1T103000.123"), a
  timezone-suffixed form ("2026-W11-1T103000Z",
  "2026-W11-1T103000+05:30", a colon-less offset
  "2026-W11-1T103000+0530", or a named RFC 2822 zone
  "2026-W11-1T103000 GMT"), a space-separated form
  ("2026-W11-1 103000"), an AM/PM form
  ("2026-W11-1T103000 AM", including suffix-before-marker
  "2026-W11-1T103000Z AM" and marker-before-suffix
  "2026-W11-1T103000 AM Z"), an attached-marker form
  ("2026-W11-1T103000am"), and a weekday-prefixed form
  ("Sunday, 2026-W11-1T103000") normalize the same way, as does
  the compact week-date spelling ("2026W111T103000"); only the
  date part governs, so the hour needs no conversion. This
  closes the gap the Nov 16 3:05 AM run noted: every colon form
  governed while the colon-less form quarantined (verified by
  probe before the fix — 19 valid forms quarantined) — the guard
  had no colon-less alternative, so the value never reached the
  parsers; the existing marker/suffix strips and strptime formats
  already handled the form once the guard let it in, with 12 new
  basic ISO formats added to the parse list. An impossible basic
  ISO week-date datetime ("2025-W53-1T103000"), an out-of-range
  time ("2026-W11-1T256000"), a malformed suffix
  ("2026-W11-1T103000+99:99"), an unknown zone
  ("2026-W11-1T103000 XYZ"), or a malformed marker
  ("2026-W11-1T103000 XM") is left untouched so the gates
  quarantine it normally, as is a week-only form carrying a
  basic ISO time ("2026-W11T103000", no weekday — the same as
  the colon form); the quality gates stay strict and see only
  the normalized value; 2 new tests (suite now 217, all
  passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.501s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines,
  differing only in its timestamp column; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  week-date basic ISO-time 2-row CSV: 2 in, 1 governed,
  1 quarantined).

- Nov 16, 2026 build block (9:05 PM run):
  week-only datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  week alone carrying a time ("2026-W11 10:30:00", the way
  scheduling exports write a week with a timestamp) now
  normalizes to the Monday of that week (YYYY-MM-DD) and governs
  instead of quarantining as unparseable_date; a no-seconds form
  ("2026-W11 10:30"), a fractional-second form
  ("2026-W11 10:30:00.123"), a timezone-suffixed form
  ("2026-W11 10:30:00Z", "2026-W11 10:30:00 +05:30", or a named
  RFC 2822 zone "2026-W11 10:30:00 GMT"), an AM/PM form
  ("2026-W11 10:30:00 AM", including suffix-before-marker
  "2026-W11 10:30:00Z AM" and marker-before-suffix
  "2026-W11 10:30:00 PM GMT"), a weekday-prefixed form
  ("Sunday, 2026-W11 10:30:00"), and the compact week-only
  spelling ("2026W11 10:30:00", "2026W11T10:30:00") normalize
  the same way, as does the colon-less basic ISO form
  ("2026-W11T103000", including no-seconds, fractional-second,
  timezone-suffixed, space-separated, AM/PM in both orders, and
  attached-marker "2026-W11T103000am" variants); only the date
  part governs, so the hour needs no conversion. This closes the
  gap the Nov 16 9:05 AM run noted: the bare week-only date
  governed while a week carrying a time quarantined (verified by
  probe before the fix — 32 valid forms quarantined) — the guard
  had no week-only datetime alternative, so the value never
  reached the parsers; the time part is now parsed only to
  validate it, and the Monday comes from fromisocalendar. An
  impossible week-only datetime ("2025-W53 10:30:00"), an
  out-of-range time ("2026-W11 25:60:00"), a malformed suffix
  ("2026-W11 10:30:00+99:99"), an unknown zone
  ("2026-W11 10:30:00 XYZ"), or a malformed marker
  ("2026-W11 10:30:00 XM") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and see
  only the normalized value; 3 new tests (suite now 220, all
  passing), and the earlier negative test no longer lists
  "2026-W11T103000" as quarantining — it now governs. Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.580s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines and audit.jsonl 10,000 lines,
  each differing only in its timestamp column; zero raw member
  IDs, zero patient names in all outputs; CLI smoke-tested on a
  week-only datetime 2-row CSV: 2 in, 1 governed, 1 quarantined).
  Remaining gap noted: the bare compact week-only date
  ("2026W11", no hyphen, no time) still quarantines while the
  hyphenated form ("2026-W11") governs — for a later run.

- Nov 17, 2026 build block (3:05 AM run):
  compact week-only dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  bare compact week alone ("2026W11", the way some scheduling
  exports write a week with no hyphen and no time) now normalizes
  to the Monday of that week (YYYY-MM-DD) and governs instead of
  quarantining as unparseable_date, as does a weekday-prefixed
  compact week-only date ("Sunday, 2026W11"); a 53-week year
  ("2020W53") governs as 2020-12-28 and a week 1 that starts in
  the prior year ("2026W01") governs as 2025-12-29. This closes
  the gap the Nov 16 9:05 PM run noted: the bare compact week-only
  date quarantined while the hyphenated form ("2026-W11") governed
  (verified by probe before the fix — 5 valid forms quarantined)
  — the guard had no compact week-only alternative and the parser
  only took the hyphenated form, so the value never reached
  fromisocalendar. An impossible compact week-only date
  ("2025W53", a 52-week year), a week outside 1-53 ("2026W00",
  "2026W54"), a weekday-prefixed compact week-only date with a
  bogus label ("Funday, 2026W11"), or a short week ("2026W1") is
  left untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new tests
  (suite now 222, all passing). Demo re-verified same run (10,000
  in → 1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.484s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines and
  audit.jsonl 10,000 lines, each identical ignoring the timestamp
  column across repeat runs; zero raw member IDs, zero patient
  names in all outputs; CLI smoke-tested on a compact week-only
  2-row CSV: 2 in, 1 governed, 1 quarantined).
  Remaining gap noted: two-digit-year week dates ("26W111",
  "26-W11-1", "26W11", "26-W11") still quarantine — probed this
  run, 0 of 6 two-digit-year week forms govern — for a later run.

- Nov 17, 2026 build block (9:05 AM run):
  two-digit-year week dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  week date with a two-digit year ("26W111", "26-W11-1", the week
  alone "26W11" or "26-W11", the way legacy exports write week
  dates) now normalizes to its calendar date (YYYY-MM-DD) and
  governs instead of quarantining as unparseable_date, as does a
  weekday-prefixed form ("Sunday, 26-W11-1"); a week alone is its
  Monday, like "2026-W11". The two-digit year follows Python's %y
  pivot (00-68 read as 2000-2068, 69-99 as 1969-1999), so
  "99-W01-1" governs as 1999-01-04 and "69W111" as 1969-03-10;
  the pivot is taken from strptime itself so it cannot drift from
  the other two-digit-year forms. This closes the gap the Nov 17
  3:05 AM run noted: two-digit-year week dates quarantined while
  the four-digit forms governed (verified by probe before the fix
  — 0 of 6 forms governed) — no branch claimed the two-digit
  spellings, so the values never reached fromisocalendar. An
  impossible two-digit-year week date ("25-W53-1", a 52-week
  year), a weekday outside 1-7 ("26-W11-8"), a week outside 1-53
  ("26-W00", "26-W54"), a short week ("26-W1"), or a
  weekday-prefixed week date with a bogus label ("Funday,
  26-W11-1") is left untouched so the gates quarantine it
  normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 224, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.596s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines and audit.jsonl 10,000 lines,
  each identical ignoring the timestamp column across repeat runs;
  zero raw member IDs, zero patient names in all outputs; CLI
  smoke-tested on a two-digit-year week-date 2-row CSV: 2 in, 1
  governed, 1 quarantined).
  Remaining gap noted: two-digit-year week-date datetimes
  ("26-W11-1 10:30:00", "26W111T103000", "26-W11 10:30:00") still
  quarantine — probed this run, 0 of 6 forms govern — for a later
  run.

- Nov 17, 2026 build block (3:05 PM run):
  two-digit-year week-date datetimes (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  week-date datetime with a two-digit year ("26-W11-1 10:30:00",
  the colon form, or the colon-less basic form "26W111T103000",
  the way legacy exports write week-date datetimes) now
  normalizes to its date part (YYYY-MM-DD) and governs instead of
  quarantining as unparseable_date, as do fractional-second,
  timezone-suffixed, space-separated, and AM/PM forms (including
  suffix-before-marker "26-W11-1 10:30:00Z AM" and
  marker-before-suffix "26-W11-1 10:30:00 PM GMT"), attached-marker
  forms ("26W111T103000am"), and weekday-prefixed forms
  ("Sunday, 26-W11-1 10:30:00"), in both week-date spellings; a
  week-only datetime ("26-W11 10:30:00" or "26W11 10:30:00")
  governs as its Monday the same way. The two-digit year follows
  Python's %y pivot (00-68 read as 2000-2068, 69-99 as
  1969-1999), taken from strptime itself so it cannot drift from
  the other two-digit-year forms, and the date part parses via
  fromisocalendar, so no %y/%G strptime mix is needed. This closes
  the gap the Nov 17 9:05 AM run noted: two-digit-year week-date
  datetimes quarantined while the four-digit forms governed
  (verified by probe before the fix — 0 of 6 forms governed) —
  the guard had no two-digit-year datetime alternatives, so the
  values never reached the parser. An impossible two-digit-year
  week-date datetime ("25-W53-1 10:00:00", a 52-week year), an
  out-of-range time ("26-W11-1 25:60:00", "26W111T256000"), a
  malformed suffix ("26-W11-1 10:30:00+99:99"), an unknown zone
  ("26-W11-1 10:30:00 XYZ"), a malformed marker ("26-W11-1
  10:30:00 XM"), or a weekday-prefixed week-date datetime with a
  bogus label ("Funday, 26-W11-1 10:30:00") is left untouched so
  the gates quarantine it normally; the date-only fallback is
  gated on the value still being a bare date after stripping, so
  a datetime whose time failed validation cannot fall through
  and govern as a bare date; the quality gates stay strict and see
  only the normalized value; 2 new tests (suite now 226, all
  passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.488s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines and audit.jsonl 10,000 lines,
  each identical ignoring the timestamp column across repeat runs;
  zero raw member IDs, zero patient names in all outputs; CLI
  smoke-tested on a two-digit-year week-date datetime 2-row CSV:
  2 in, 1 governed, 1 quarantined).
  Remaining gap noted: two-digit-year ordinal dates ("26-074",
  "26074") and their datetimes ("26-074 10:30:00") still
  quarantine — probed this run, 0 of 3 forms govern — for a later
  run.

- Nov 17, 2026 build block (9:05 PM run):
  two-digit-year ordinal (Julian) dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as a
  YYDDD ordinal date ("26074") or the ISO 8601 ordinal form with
  a two-digit year ("26-074"), the way legacy mainframe exports
  write dates, now normalizes to its calendar date (YYYY-MM-DD)
  and governs instead of quarantining as unparseable_date, as do
  weekday-prefixed forms ("Sunday, 26074", "Mon, 26-074") and
  pivot examples ("99074" governs as 1999-03-15, "69074" as
  1969-03-15, "68074" as 2068-03-14). Two-digit-year ordinal
  datetimes ("26-074 10:30:00", the colon form, or the colon-less
  basic form "26074T103000", the way legacy exports write ordinal
  datetimes with a two-digit year) normalize the same way — the
  time part is dropped and only the date part governs — as do
  fractional-second, timezone-suffixed (attached and
  space-separated), named RFC 2822 zone, and AM/PM forms (in both
  orders, attached markers included), and weekday-prefixed forms,
  in both ordinal spellings. The two-digit year follows Python's
  %y pivot (00-68 read as 2000-2068, 69-99 as 1969-1999), taken
  from strptime itself so it cannot drift from the other
  two-digit-year forms. This closes the gap the Nov 17 3:05 PM run
  noted: two-digit-year ordinal dates quarantined while the
  four-digit forms governed (verified by probe before the fix — 0
  of 18 forms governed) — the guard had no two-digit-year ordinal
  alternatives, so the values never reached the parsers. Collision
  resolved and documented: a bare five-digit number now reads as a
  YYDDD ordinal date, so "12345" governs as 2012-12-10 rather than
  quarantining as a bad epoch timestamp — the bad-epoch test now
  uses an eleven-digit ambiguous number ("12345678901") instead,
  and the epoch docstrings note the five-digit exception. An
  impossible two-digit-year ordinal date ("26366" in 2026, which
  has 365 days, or "26000"), an impossible datetime ("26366
  10:00:00 AM"), an out-of-range time ("26-074 25:60:00",
  "26074T256000"), a malformed suffix ("26074 10:30:00+99:99",
  "26-074 10:30:00 AM +99:99"), an unknown zone ("26074 10:30:00
  XYZ"), a malformed marker ("26074 10:30:00 XM"), or a
  weekday-prefixed date with a bogus label ("Funday, 26074") is
  left untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new tests
  (suite now 228, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.531s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines and audit.jsonl 10,000 lines,
  each identical ignoring the timestamp column across repeat runs;
  zero raw member IDs, zero patient names in all outputs; CLI
  smoke-tested on a two-digit-year ordinal-date 2-row CSV:
  2 in, 1 governed, 1 quarantined).
  Adjacent forms probed same run (12 forms — attached
  single-digit-hour marker, fractional-plus-offset colon-less,
  short weekday prefix, suffix-before-marker, marker-before-suffix,
  named zone on colon-less, space-separated colon-less — all govern
  as 2026-03-15); no new gap noted in the ordinal family — both
  year widths now complete.

  Nov 18, 2026 build block (3:05 AM run): no-comma month-name
  dates ("March 15 2026", "Mar 15 2026") now normalize on read
  in `read_claims_csv` (io.py) — the month-first form with no
  comma after the day governs as its calendar date, as do
  ordinal-suffix ("March 15th 2026"), weekday-prefixed
  ("Sunday, March 15 2026"), and two-digit-year ("March 15 26",
  "Mar 15 99" → 1999-03-15) forms, and no-comma month-name
  datetimes (space- or T-separated, no-seconds, fractional,
  timezone-suffixed, named zone, AM/PM in both orders,
  weekday-prefixed) normalize to their date part. Probe verified
  before the fix (0 of 18 valid forms governed) and after (18
  govern as 2026-03-15, 6 invalid quarantine). 2 new tests,
  suite now 230, all passing. Demo re-verified: 10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  governed/quarantine/summary.json byte-identical; audit.csv
  10,001 lines and audit.jsonl 10,000 lines, identical ignoring
  the timestamp column across repeat runs; zero raw member IDs /
  patient names in outputs; runtime 0.642s. CLI smoke test on
  no-comma month-name 2-row CSV: 2 in, 1 governed,
  1 quarantined. README test count updated 224 → 230; PLAN.md +
  README changelogs updated. Remaining gap noted: "15th of
  March 2026" still quarantines — for a later run.

  Nov 18, 2026 build block (9:05 AM run): day-of-month-name
  dates ("15th of March 2026", "15 of Mar 2026") now normalize
  on read in `read_claims_csv` (io.py) — the day-of form with
  or without the ordinal suffix, and with an optional leading
  "the", governs as its calendar date, as do weekday-prefixed
  ("Sunday, 15th of March 2026") and two-digit-year ("15th of
  March 26", "15th of Mar 99" → 1999-03-15) forms, and
  day-of month-name datetimes (space- or T-separated,
  no-seconds, fractional, timezone-suffixed, named zone, AM/PM
  in both orders, weekday-prefixed) normalize to their date
  part. Probe verified before the fix (0 of 18 valid forms
  governed) and after (18 govern as 2026-03-15, 6 invalid
  quarantine). 2 new tests, suite now 232, all passing. Demo
  re-verified: 10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; governed/quarantine/summary.json
  byte-identical; audit.csv 10,001 lines and audit.jsonl
  10,000 lines, identical ignoring the timestamp column across
  repeat runs; zero raw member IDs / patient names in outputs;
  runtime 0.459s. CLI smoke test on day-of-month-name 2-row
  CSV: 2 in, 1 governed, 1 quarantined. README test count
  updated 230 → 232; PLAN.md + README changelogs updated.
  Remaining gap noted: space-separated ISO dates ("2026 03 15")
  still quarantine — for a later run.

- Nov 18, 2026 build block (3:05 PM run):
  space-separated ISO dates (read_claims_csv in
  hipaa_pipeline_framework/io.py) — a service_date written as
  a year-first date with spaces instead of hyphens ("2026 03
  15", the way some exports write dates) now normalizes to its
  calendar date (YYYY-MM-DD) and governs instead of
  quarantining as unparseable_date, as do single-digit month
  and day forms ("2026 3 15", "2026 03 5" → 2026-03-05) and
  weekday-prefixed forms ("Sunday, 2026 03 15"). Space-separated
  ISO datetimes ("2026 03 15 10:30:00", the space- or
  T-separated form, or a no-seconds form "2026 03 15 10:30")
  normalize the same way — the time part is dropped and only
  the date part governs — as do fractional-second,
  timezone-suffixed (attached and space-separated), named RFC
  2822 zone, and AM/PM forms (in both orders), and
  weekday-prefixed forms. This closes the gap the Nov 18 9:05
  AM run left open: day-of month-name dates ("15th of March
  2026") governed while the space-separated ISO form
  quarantined (verified by probe before the fix — 0 of 18
  valid forms governed). An impossible space-separated ISO
  date ("2026 02 30", "2026 13 15", "2026 03 32"), an
  out-of-range time ("2026 03 15 25:60:00"), an unknown zone
  ("2026 03 15 10:30:00 XYZ"), a malformed marker ("2026 03
  15 10:30:00 XM"), a malformed suffix ("2026 03 15
  10:30:00+99:99"), or a weekday-prefixed date with a bogus
  label ("Funday, 2026 03 15") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 234,
  all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.537s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines and audit.jsonl 10,000 lines,
  each identical ignoring the timestamp column across repeat runs;
  zero raw member IDs, zero patient names in all outputs; CLI
  smoke-tested on a space-separated-ISO-date 2-row CSV:
  2 in, 1 governed, 1 quarantined).
  Remaining gap noted: two-digit-year and non-year-first
  space-separated forms ("26 03 15", "03 15 26", "15 03 26",
  "03 15 2026", "15 03 2026") still quarantine — probed this
  run, 0 of 5 forms govern — for a later run.

- Nov 18, 2026 build block (9:05 PM run):
  two-digit-year and non-year-first space-separated dates
  (read_claims_csv in io.py) — "03 15 26", "15 03 26",
  "03 15 2026", and "15 03 2026" now normalize on read and
  govern as their calendar date, as do single-digit month and
  day forms ("3 5 26" → 2026-03-05) and weekday-prefixed forms
  ("Sunday, 03 15 26"). Two-digit-year and non-year-first
  space-separated datetimes ("03 15 26 10:30:00", the space- or
  T-separated form, or a no-seconds form "03 15 26 10:30")
  normalize the same way — the time part is dropped and only
  the date part governs — as do fractional-second,
  timezone-suffixed (attached and space-separated), named RFC
  2822 zone, and AM/PM forms (in both orders), and
  weekday-prefixed forms. The US form is tried first, so only
  an unambiguous day-first date reads day-first ("26 03 15"
  governs as 2015-03-26, "15 03 26" as 2026-03-15) and there
  is no separate year-first two-digit form — the same
  convention as the two-digit-year dot and underscore forms.
  The two-digit year follows Python's strptime %y pivot
  (00-68 read as 2000-2068, 69-99 as 1969-1999), so
  "03 15 99" governs as 1999-03-15 and "03 15 68" as
  2068-03-15. This closes the gap the Nov 18 3:05 PM run left
  open: space-separated ISO dates ("2026 03 15") governed
  while the two-digit-year and non-year-first forms
  quarantined (verified by probe before the fix — 0 of 14
  valid forms governed, 3 of 3 invalid quarantined). An
  impossible two-digit date ("02 30 26", "03 32 26"), a
  day-first read giving an impossible month ("13 15 26"), an
  out-of-range time ("03 15 26 25:60:00"), an unknown zone
  ("03 15 26 10:30:00 XYZ"), a malformed marker ("03 15 26
  10:30:00 XM"), a malformed suffix ("03 15 26 10:30:00+99:99"),
  or a weekday-prefixed date with a bogus label ("Funday,
  03 15 26") is left untouched so the gates quarantine it
  normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 236, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.127s; CLI governed,
  quarantine, and summary.json outputs byte-identical to a
  pre-change run this run; audit.csv 10,001 lines and audit.jsonl
  10,000 lines, each identical ignoring the timestamp column
  across repeat runs; zero raw member IDs, zero patient names in
  all outputs; CLI smoke-tested on a two-digit-year
  space-separated-date 2-row CSV: 2 in, 1 governed,
  1 quarantined).
  Remaining gap noted: year-month-only ("2026 03") and
  four-digit-year non-year-first dot dates ("03.15.2026")
  still quarantine — probed this run, 0 of 2 forms govern —
  for a later run.

- Nov 19, 2026 build block (3:05 AM run):
  four-digit-year non-year-first dot dates (read_claims_csv in
  io.py) — "03.15.2026" and "15.03.2026" now normalize on read
  and govern as their calendar date, as do single-digit month
  and day forms and weekday-prefixed forms ("Sunday,
  03.16.2026"). Four-digit-year non-year-first dot datetimes
  ("03.15.2026 10:30:00", the space- or T-separated form, or a
  no-seconds form) normalize the same way — the time part is
  dropped and only the date part governs — as do
  fractional-second, timezone-suffixed (attached and
  space-separated), named RFC 2822 zone, and AM/PM forms (in
  both orders), and weekday-prefixed forms. The US form is
  tried first, so only an unambiguous day-first date reads
  day-first ("03.04.2026" governs as 2026-03-04, "15.03.2026"
  as 2026-03-15) and a leading component above 12 reads
  day-first ("26.03.2015" governs as 2015-03-26) — the same
  convention as the two-digit-year dot forms. This closes one
  half of the gap the Nov 18 9:05 PM run left open (verified by
  probe before the fix — 0 of 8 valid forms governed, 5 of 5
  invalid quarantined). The other half is closed by decision,
  not by code: a year-month-only value ("2026 03") carries no
  day, so there is no calendar date to govern — mapping it to
  the 1st of the month would fabricate a service date, which a
  fail-closed governance framework must not do — so it stays
  quarantined as unparseable_date (verified this run: 0
  governed, 1 quarantined). An impossible four-digit-year dot
  date ("02.30.2026"), a malformed suffix ("03.15.2026
  10:30:00+99:99"), an unknown zone ("03.15.2026 10:30:00
  XYZ"), or a weekday-prefixed date with a bogus label
  ("Funday, 03.15.2026") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 238,
  all passing). The fractional-second trap was re-checked:
  "03-15-2026 10:30:00.123Z" and "2026-03-15T09:00:00.123Z"
  still govern through their own branches, not the dot branch.
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.572s; governed,
  quarantine, and summary.json outputs byte-identical to
  pre-run outputs; audit.csv 10,001 lines and audit.jsonl
  10,000 lines; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a four-digit-year dot-date 2-row
  CSV: 2 in, 1 governed, 1 quarantined).

- Nov 19, 2026 build block (9:05 AM run):
  four-digit-year non-year-first underscore dates
  (read_claims_csv in io.py) — "03_15_2026" and "15_03_2026"
  now normalize on read and govern as their calendar date, as
  do single-digit month and day forms ("3_5_2026" →
  2026-03-05) and weekday-prefixed forms ("Sunday,
  03_16_2026"). Four-digit-year non-year-first underscore
  datetimes ("03_15_2026 10:30:00", the space- or T-separated
  form, or a no-seconds form) normalize the same way — the
  time part is dropped and only the date part governs — as do
  fractional-second, timezone-suffixed (attached and
  space-separated), named RFC 2822 zone, and AM/PM forms (in
  both orders), and weekday-prefixed forms. The US form is
  tried first, so only an unambiguous day-first date reads
  day-first ("03_04_2026" governs as 2026-03-04, "15_03_2026"
  as 2026-03-15) and a leading component above 12 reads
  day-first ("26_03_2015" governs as 2015-03-26) — the same
  convention as the four-digit-year dot forms. This closes
  the gap the Nov 19 3:05 AM run left open: four-digit-year
  non-year-first dot dates ("03.15.2026") governed while the
  underscore forms quarantined (verified by probe before the
  fix — 0 of 6 valid forms governed). An impossible four-digit-year underscore
  date ("02_30_2026"), a day-first read giving an impossible
  month ("13_15_2026"), an out-of-range time ("03_15_2026
  25:60:00"), an unknown zone ("03_15_2026 10:30:00 XYZ"),
  a malformed suffix ("03_15_2026 10:30:00+99:99"), or a
  weekday-prefixed date with a bogus label ("Funday,
  03_15_2026") is left untouched so the gates quarantine it
  normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 240, all
  passing). The year-month-only form ("2026_03") carries no
  day, so there is no calendar date to govern — mapping it to
  the 1st of the month would fabricate a service date, which
  a fail-closed governance framework must not do — so it
  stays quarantined as unparseable_date (verified this run:
  0 governed, 1 quarantined), the same decision as the
  "2026 03" form. Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.450s; governed, quarantine, and summary.json
  outputs byte-identical to a pre-run run this run; audit.csv
  10,001 lines and audit.jsonl 10,000 lines; zero raw member
  IDs, zero patient names in all outputs; CLI smoke-tested
  on a four-digit-year underscore-date 2-row CSV: 2 in, 1
  governed, 1 quarantined).
  Remaining gap noted: compact non-year-first dates
  ("03152026", "15032026") still quarantine — probed this
  run, 0 of 2 forms govern — for a later run.

- Nov 19, 2026 build block (3:05 PM run):
  four-digit-year non-year-first compact dates
  (read_claims_csv in io.py) — "03152026" and "15032026"
  now normalize on read and govern as their calendar date, as
  do weekday-prefixed forms ("Sunday, 03152026").
  Four-digit-year non-year-first compact datetimes
  ("03152026 10:30:00", the space- or T-separated form, or a
  no-seconds form) normalize the same way — the time part is
  dropped and only the date part governs — as do
  fractional-second, timezone-suffixed (attached and
  space-separated), named RFC 2822 zone, and AM/PM forms (in
  both orders, attached-marker included), colon-less basic ISO
  forms ("03152026T103000", "03152026 103000"), and
  weekday-prefixed forms. The US form is tried first, so only
  an unambiguous day-first date reads day-first ("03042026"
  governs as 2026-03-04, "15032026" as 2026-03-15) and a
  leading component above 12 reads day-first ("26032015"
  governs as 2015-03-26) — the same convention as the
  four-digit-year underscore forms; the year-first compact
  form keeps priority, so a value valid both ways ("01120315")
  still takes its year-first reading. This closes the gap the
  Nov 19 9:05 AM run left open (verified by probe before the
  fix — 0 of 8 valid forms governed). An impossible
  four-digit-year compact date ("02302026"), a day-first read
  giving an impossible month ("13152026"), an out-of-range
  time ("03152026 25:60:00"), an unknown zone ("03152026
  10:30:00 XYZ"), a malformed suffix ("03152026
  10:30:00+99:99"), a malformed marker ("03152026 10:30:00
  XM"), or a weekday-prefixed date with a bogus label
  ("Funday, 03152026") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 242,
  all passing). The full probe matrix this run: 22 of 23 valid
  forms govern end-to-end; the 23rd ("01120315") normalizes to
  "112-03-15" on read but the gates then quarantine it, since
  strftime does not zero-pad years below 1000 and the gate's
  %Y expects exactly four digits — pre-existing year-first
  behavior, not a regression from this block. Demo re-verified
  same run (10,000 in → 1,589 governed, 8,411 quarantined,
  reasons unchanged; runtime 0.447s; governed, quarantine,
  and summary.json outputs stable across two runs this run;
  audit.csv 10,001 lines and audit.jsonl 10,000 lines; zero
  raw member IDs, zero patient names in all outputs; CLI
  smoke-tested on a four-digit-year compact-date 2-row CSV: 2
  in, 1 governed, 1 quarantined).
  Remaining gap noted: a year-first compact date whose year
  is below 1000 ("01120315") normalizes on read as
  "112-03-15" but the gates quarantine it, since the gate's
  %Y expects exactly four digits — a later run must decide
  whether to zero-pad the normalized year or leave the
  fail-closed quarantine in place.

- Nov 19, 2026 build block (9:05 PM run):
  sub-1000-year dates (read_claims_csv in io.py) — a
  normalized date in a year below 1000 now governs instead of
  quarantining: strftime("%Y") does not zero-pad such years,
  so "01120315" came out as "112-03-15" and the gates (which
  need exactly four year digits) quarantined it. The short year
  is now padded back to four digits on read, once, at the point
  rows are collected, so the fix covers every date form at once
  — compact ("01120315" governs as 0112-03-15), slash
  ("0112/03/15", "03/15/0112"), dot ("0112.03.15",
  "03.15.0112"), underscore ("0112_03_15", "03_15_0112"), and
  ISO datetimes ("0112-03-15 10:30:00"); an already-ISO
  "0112-03-15" governed before and still does. This closes the
  gap the Nov 19 3:05 PM run left open (verified by probe
  before the fix — 1 of 11 valid forms governed, the other 10
  quarantined on the short year; after the fix all 11 govern
  end-to-end). An ambiguous compact value ("03150112") keeps
  its year-first reading and governs as 0315-01-12, and a
  compact value whose year-first reading is impossible
  ("01120230") takes the non-year-first fallback and governs
  as 0230-01-12; an impossible date in a sub-1000 year
  ("0112-02-30", "02/30/0112") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 244,
  all passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.639s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines
  and audit.jsonl 10,000 lines; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  sub-1000-year 2-row CSV: 2 in, 1 governed, 1 quarantined).

- Nov 20, 2026 build block (3:05 AM run):
  fractional-second epoch timestamps (read_claims_csv in
  io.py) — a service_date written as a Unix epoch carrying a
  fractional part ("1710460800.5", "1710460800.123"), the way
  high-resolution API and database exports write timestamps
  as a float, now converts to its UTC date (YYYY-MM-DD) and
  governs instead of quarantining as unparseable_date; the
  sub-second part is dropped and only the whole count is
  scaled, so seconds ("1710460800.5"), milliseconds
  ("1710460800000.25"), microseconds
  ("1710460800000000.5"), and nanoseconds
  ("1710460800000000000.5") all govern as 2024-03-15, as does
  a non-midnight fractional epoch ("1710500000.999"), and the
  window bounds are inclusive ("946684800.0" governs as
  2000-01-01, "4102444800000.999" as 2100-01-01). This closes
  a gap found by probe before the fix — 0 of 4 fractional
  epoch forms governed. A fractional epoch outside the
  2000-01-01..2100-01-01 window ("710460800.5" reads as 1992,
  "9999999999999999999.5" as 2286), a fractional number whose
  whole part has an ambiguous length ("17104608000.5",
  eleven digits; "17104608000000.5", fourteen digits;
  "17104608000000000.5", seventeen digits), or a value that
  is not plain digits-dot-digits ("1710460800.",
  "1710460800.5x", ".5") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and
  see only the normalized value; 2 new tests (suite now 246,
  all passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.544s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines
  and audit.jsonl 10,000 lines, differing only in their
  timestamp columns; zero raw member IDs, zero patient names
  in all outputs; CLI smoke-tested on a fractional-epoch
  3-row CSV: 3 in, 2 governed, 1 quarantined).

- Nov 20, 2026 build block (9:05 AM run):
  lowercase ISO datetimes (read_claims_csv in io.py) — a
  service_date written as an ISO 8601 datetime in lowercase
  ("2026-03-15t10:30:00z", the way some exports write ISO
  timestamps) now normalizes to its date part (YYYY-MM-DD) and
  governs instead of quarantining as unparseable_date: the ISO
  branch guard now also accepts a lowercase "t", and a trailing
  lowercase "z" is stripped as "Z" before parsing (the "T"
  formats already matched case-insensitively, which is why only
  the spaced AM/PM form governed before). This closes the gap
  the 3:05 AM run left open (verified by probe before the fix —
  1 of 9 lowercase forms governed, the spaced AM/PM form only;
  after the fix all 10 forms in the new test govern end-to-end):
  "2026-03-15t10:30:00z", "2026-03-15t10:30:00",
  "2026-03-15T09:00:00z", "2026-03-15 10:30:00z",
  "2026-03-15t10:30:00.123z", "2026-03-15t10:30:00+05:30",
  "2026-03-15t10:30", "2026-03-15t10:30:00am",
  "Sunday, 2026-03-16t10:30:00z", and "2026 03 15t10:30:00".
  An impossible lowercase date ("2026-02-30t10:30:00z"), a
  malformed offset ("2026-03-15t10:30:00+99:99"), an unknown
  zone ("2026-03-15t10:30:00 xyz"), or a malformed marker
  ("2026-03-15t10:30:00 xm") is left untouched so the gates
  quarantine it normally, as is a colon-less time
  ("2026-03-15T103000"); the quality gates stay strict and see
  only the normalized value; 2 new tests (suite now 248, all
  passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.530s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines
  and audit.jsonl 10,000 lines, differing only in their
  timestamp columns; zero raw member IDs, zero patient names
  in all outputs; CLI smoke-tested on a lowercase-ISO 3-row
  CSV: 3 in, 2 governed, 1 quarantined).

- Nov 20, 2026 build block (3:05 PM run):
  lowercase-z slash datetimes (read_claims_csv in io.py) — a
  service_date written as a slash datetime carrying a lowercase
  "z" designator ("03/15/2026 10:30:00z", the way some exports
  write slash timestamps) now has the "z" stripped as "Z" in
  the slash timezone branch and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date: the slash branch guard already accepted a
  lowercase "t" separator (strptime literals match
  case-insensitively, which is why "03/15/2026t10:30:00"
  governed before), so only the trailing "z" needed the fix.
  This closes the gap the 9:05 AM run left open (verified by
  probe before the fix — 0 of 6 lowercase-z slash forms
  governed; after the fix all 10 forms in the new test govern
  end-to-end): "03/15/2026 10:30:00z",
  "03/15/2026t10:30:00z", "15/03/2026 10:30:00z",
  "03/15/2026 10:30:00.123z", "03/15/2026 10:30:00 z",
  "03/15/2026T09:00:00z", "2026/03/15 10:30:00z",
  "03/15/26 10:30:00z", "Sunday, 03/16/2026 10:30:00z", and
  "03/15/2026 10:30:00 am z". An impossible lowercase-z date
  ("02/30/2026 10:00:00z"), a malformed offset ("03/15/2026
  10:30:00.123+99:99"), an unknown zone ("03/15/2026 10:30:00
  xyz"), or a bogus weekday label ("Funday, 03/15/2026
  10:30:00z") is left untouched so the gates quarantine it
  normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 250, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed,
  8,411 quarantined, reasons unchanged; runtime 0.516s;
  governed, quarantine, and summary.json outputs byte-identical
  to pre-run outputs; audit.csv 10,001 lines and audit.jsonl
  10,000 lines, differing only in their timestamp columns;
  zero raw member IDs, zero patient names in all outputs; CLI
  smoke-tested on a lowercase-z slash 3-row CSV: 3 in,
  2 governed, 1 quarantined).

- Nov 20, 2026 build block (9:05 PM run):
  lowercase-z dot datetimes (read_claims_csv in io.py) — a
  service_date written as a dot datetime carrying a lowercase
  "z" designator ("2026.03.15 10:30:00z", the way some exports
  write dot timestamps) now has the "z" stripped as "Z" in
  the dot timezone branch and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date: the dot branch guard already accepted a
  lowercase "t" separator (strptime literals match
  case-insensitively, which is why "2026.03.15t10:30:00"
  governed before), so only the trailing "z" needed the fix.
  This closes the gap the 3:05 PM run left open (verified by
  probe before the fix — 0 of 6 lowercase-z dot forms
  governed; after the fix all 10 forms in the new test govern
  end-to-end): "2026.03.15 10:30:00z",
  "2026.03.15t10:30:00z", "03.15.2026 10:30:00z",
  "2026.03.15 10:30:00.123z", "2026.03.15 10:30:00 z",
  "2026.03.15T09:00:00z", "15.03.2026 10:30:00z",
  "03.15.26 10:30:00z", "Sunday, 2026.03.16 10:30:00z", and
  "2026.03.15 10:30:00 am z". An impossible lowercase-z date
  ("2026.02.30 10:00:00z"), a malformed offset ("2026.03.15
  10:30:00.123+99:99"), an unknown zone ("2026.03.15 10:30:00
  xyz"), or a bogus weekday label ("Funday, 2026.03.15
  10:30:00z") is left untouched so the gates quarantine it
  normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 252, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed,
  8,411 quarantined, reasons unchanged; runtime 0.459s;
  governed, quarantine, and summary.json outputs byte-identical
  to pre-run outputs; audit.csv 10,001 lines and audit.jsonl
  10,000 lines, differing only in their timestamp columns;
  zero raw member IDs, zero patient names in all outputs; CLI
  smoke-tested on a lowercase-z dot 3-row CSV: 3 in,
  2 governed, 1 quarantined).

- Nov 21, 2026 build block (3:05 AM run):
  lowercase-z underscore datetimes (read_claims_csv in io.py) — a
  service_date written as an underscore datetime carrying a lowercase
  "z" designator ("2026_03_15 10:30:00z", the way some exports
  write underscore timestamps) now has the "z" stripped as "Z" in
  the underscore timezone branch and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date: the underscore branch guard already accepted a
  lowercase "t" separator (strptime literals match
  case-insensitively, which is why "2026_03_15t10:30:00"
  governed before), so only the trailing "z" needed the fix.
  This closes the gap the 9:05 PM run left open (verified by
  probe before the fix — 1 of 10 lowercase-z underscore forms
  governed, the "am z" form only; after the fix all 10 forms in
  the new test govern end-to-end): "2026_03_15 10:30:00z",
  "2026_03_15t10:30:00z", "03_15_2026 10:30:00z",
  "2026_03_15 10:30:00.123z", "2026_03_15 10:30:00 z",
  "2026_03_15T09:00:00z", "15_03_2026 10:30:00z",
  "03_15_26 10:30:00z", "Sunday, 2026_03_16 10:30:00z", and
  "2026_03_15 10:30:00 am z". An impossible lowercase-z date
  ("2026_02_30 10:00:00z"), a malformed offset ("2026_03_15
  10:30:00.123+99:99"), an unknown zone ("2026_03_15 10:30:00
  xyz"), or a bogus weekday label ("Funday, 2026_03_15 10:30:00z")
  is left untouched so the gates quarantine it normally; the
  quality gates stay strict and see only the normalized value;
  2 new tests (suite now 254, all passing). Demo re-verified same
  run (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.813s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines and audit.jsonl 10,000 lines, differing
  only in their timestamp columns; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
- Nov 21, 2026 build block (9:05 AM run):
  lowercase-z compact datetimes (read_claims_csv in io.py) — a
  service_date written as a compact datetime carrying a lowercase
  "z" designator ("20260315T103000z", the way some API exports
  write compact datetimes) now has the "z" stripped as "Z" in
  the compact timezone branch and normalizes to its date part
  (YYYY-MM-DD) and governs instead of quarantining as
  unparseable_date: the compact branch guard already accepted a
  lowercase "t" separator (strptime literals match
  case-insensitively, which is why "20260315t103000"
  governed before), so only the trailing "z" needed the fix.
  This closes the gap the 3:05 AM run left open (verified by
  probe before the fix — 0 of 10 lowercase-z compact forms
  governed; after the fix all 10 forms in the new test govern
  end-to-end): "20260315T103000z", "20260315t103000z",
  "20260315 10:30:00z", "20260315T103000.123z",
  "20260315 10:30:00 z", "20260315T09:00:00z",
  "20260315T1030z", "20260315 10:30z",
  "Sunday, 20260316T103000z", and "20260315 10:30:00z AM". An
  impossible lowercase-z date ("20260230T103000z"), a malformed
  offset ("20260315T103000+99:99"), an unknown zone
  ("20260315T103000 xyz"), a bogus weekday label ("Funday,
  20260315T103000z"), or an out-of-range time
  ("20260315T256000z") is left untouched so the gates quarantine
  it normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 256, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.970s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines and audit.jsonl 10,000 lines,
  differing only in their timestamp columns; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  lowercase-z compact 3-row CSV: 3 in, 2 governed,
  1 quarantined).

- Nov 21, 2026 build block (3:05 PM run):
  lowercase month names (read_claims_csv in io.py) — a
  service_date written with a month name in lowercase ("mar 15,
  2026" or "15 march 2026", the way some exports write month
  names without capitals) now normalizes to ISO form (YYYY-MM-DD)
  on read and governs instead of quarantining as
  unparseable_date: the month-name dispatch guard matched month
  names case-sensitively, so a lowercase month never reached the
  branch, while strptime %b/%B already matches
  case-insensitively — only the guard needed the fix. Probe
  before the fix: 0 of 11 lowercase month-name forms governed;
  after the fix all 10 forms in the new test govern end-to-end:
  "mar 15, 2026", "15 mar 2026", "march 15, 2026",
  "15 march 2026", "mar-15-2026", "15-mar-2026",
  "march 15 2026", "mar 15, 2026 10:30:00",
  "15th of march 2026", and "sunday, mar 16, 2026". An
  impossible lowercase month-name date ("feb 30, 2026"), an
  unknown zone ("mar 15, 2026 10:30:00 xyz"), a bogus weekday
  label ("funday, mar 15, 2026"), an impossible day
  ("mar 32, 2026"), or a lowercase-z month-name datetime
  ("mar 15, 2026 10:30:00z" — the timezone strip in this branch
  still takes only an uppercase "Z", the next gap) is left
  untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 258, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.662s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines and audit.jsonl 10,000 lines; zero raw
  member IDs, zero patient names in all outputs; CLI
  smoke-tested on a lowercase month-name 2-row CSV: 2 in,
  1 governed, 1 quarantined).

- Nov 21, 2026 build block (9:05 PM run):
  lowercase-z month-name datetimes (read_claims_csv in io.py)
  — a service_date written with a month name and a lowercase
  "z" suffix ("mar 15, 2026 10:30:00z" or "15 mar 2026
  10:30:00z", the way some exports write zoned month-name
  timestamps without capitals) now normalizes to ISO form
  (YYYY-MM-DD) on read and governs instead of quarantining as
  unparseable_date: the timezone strip in the month-name branch
  took only an uppercase "Z", so a lowercase "z" was never
  stripped. Probe before the fix: 1 of 12 lowercase-z
  month-name datetime forms governed (only "mar 15, 2026
  10:30:00 am z", via the AM/PM marker-suffix step, which
  already matches case-insensitively); after the fix all 12
  forms in the new test govern end-to-end: "mar 15, 2026
  10:30:00z", "Mar 15, 2026 10:30:00z", "mar 15, 2026
  10:30:00 z", "15 mar 2026 10:30:00z", "mar 15, 2026T10:30:00z",
  "mar 15, 2026 10:30:00.123z", "Mar 15, 2026 10:30:00z AM",
  "mar 15, 2026 10:30:00 am z", "sunday, mar 16, 2026
  10:30:00z", "15th of march 2026 10:30:00z",
  "mar-15-2026 10:30:00z", and "mar 15, 26 10:30:00z". An
  impossible lowercase-z month-name datetime ("feb 30, 2026
  10:00:00z"), a malformed suffix ("mar 15, 2026 10:30:00+99:99"),
  an out-of-range time ("mar 15, 2026 25:30:00z"), a doubled
  suffix ("mar 15, 2026 10:30:00zz"), or a bogus weekday label
  ("funday, mar 15, 2026 10:30:00z") is left untouched so the
  gates quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite now
  260, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.701s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv 10,001
  lines and audit.jsonl 10,000 lines, differing only in their
  timestamp columns; zero raw member IDs, zero patient names
  in all outputs; CLI smoke-tested on a lowercase-z
  month-name 2-row CSV: 2 in, 1 governed, 1 quarantined).

- Nov 22, 2026 build block (3:05 AM run):
  lowercase-w ISO week dates (read_claims_csv in io.py) — a
  service_date written with a lowercase "w" week designator
  ("2026-w11-1", "2026w111", "2026-w11", "2026w11", or the
  two-digit-year "26-w11-1", "26w111", "26-w11", "26w11", the way
  some exports write ISO week dates without capitals) now
  normalizes to its calendar date and governs instead of
  quarantining as unparseable_date: the bare-date guard
  alternatives matched the designator case-sensitively, so a
  lowercase "w" never reached the parsers, while the datetime
  alternatives already matched either case — which is why
  week-date datetimes such as "2026-w11-1 10:30:00" governed
  while every bare lowercase-w form quarantined. Probe before
  the fix: 0 of 7 bare lowercase-w forms governed; after the
  fix all 17 forms in the new test govern end-to-end:
  "2026-w11-1", "2026w111", "2026-w11", "2026w11",
  "2026-w11 10:30:00", "2026-w11T103000", "2026-w11 10:30:00
  AM", "Sunday, 2026-w11-1", "26-w11-1", "26w111", "26-w11",
  "26w11", "26-w11 10:30:00", "26-w11-1 10:30:00",
  "26w111T103000", "99-w01-1" (1999-01-04), and "69w111"
  (1969-03-10). The week-only datetimes needed the same
  case-insensitive match in the body (their fullmatch checks
  took only an uppercase "W"), and the two-digit-year body
  needed it on its datetime, week-only datetime, and bare-date
  checks too, since it parses via fromisocalendar with
  position-based slicing rather than strptime. An impossible
  lowercase-w week date ("2025-w53-1", "25-w53-1"), a weekday
  outside 1-7 ("2026-w11-8", "26-w11-8"), a week outside 1-53
  ("2026-w00", "26-w00"), a bogus weekday label ("Funday,
  2026-w11-1"), an out-of-range time ("2026-w11-1 25:60:00"),
  a malformed marker ("2026-w11-1 10:30:00 XM"), or a malformed
  suffix ("2026-w11-1 10:30:00+99:99") is left untouched so the
  gates quarantine it normally; the quality gates stay strict
  and see only the normalized value; 2 new tests (suite now
  262, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged;
  runtime 0.455s; governed, quarantine, and summary.json
  outputs byte-identical to pre-run outputs; audit.csv 10,001
  lines and audit.jsonl 10,000 lines, differing only in their
  timestamp columns; zero raw member IDs, zero patient names
  in all outputs; CLI smoke-tested on a lowercase-w week-date
  3-row CSV: 3 in, 2 governed, 1 quarantined). Next gap noted:
  lowercase-z week-date datetimes ("2026-W11-1 10:30:00z")
  still quarantine — the trailing-"Z" strip in the week-date
  bodies takes only an uppercase "Z".

- Nov 22, 2026 build block (9:05 AM run):
  lowercase-z ISO week-date datetimes (read_claims_csv in io.py) — a
  week-date datetime carrying a lowercase "z" zone designator
  ("2026-W11-1 10:30:00z", "2026-W11-1T103000z", "2026-W11 10:30:00z",
  "2026-W11-1 10:30:00 z", "2026-W11-1 10:30:00z AM", "Sunday,
  2026-W11-1 10:30:00z", or the two-digit-year "26-W11-1 10:30:00z",
  "26W111T103000z", "26-W11 10:30:00z", "26-W11-1 10:30:00z AM", the
  way some exports write the UTC designator without capitals) now
  normalizes to its calendar date and governs instead of quarantining
  as unparseable_date: the trailing-"Z" strip in both week-date bodies
  (four-digit and two-digit year) took only an uppercase "Z", while
  the guards and the AM/PM-suffix strip already matched either case —
  which is why "2026-W11-1 10:30:00 AM z" already governed while every
  other lowercase-z week-date datetime quarantined. Probe before the
  fix: 1 of 12 forms governed; after the fix all 12 forms in the new
  test govern end-to-end, all to 2026-03-09, including the combined
  lowercase-w + lowercase-z form "2026-w11-1 10:30:00z". An impossible
  lowercase-z week date ("2025-W53-1 10:30:00z", "25-W53-1 10:30:00z"),
  a weekday outside 1-7 ("2026-W11-8 10:30:00z", "26-W11-8 10:30:00z"),
  a week outside 1-53 ("2026-W00 10:30:00z", "26-W00 10:30:00z"), a
  bogus weekday label ("Funday, 2026-W11-1 10:30:00z"), an out-of-range
  time ("2026-W11-1 25:60:00z"), a malformed marker ("2026-W11-1
  10:30:00z XM"), or a doubled suffix ("2026-W11-1 10:30:00zz") is left
  untouched so the gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests (suite now
  264, all passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime 0.557s;
  governed, quarantine, and summary.json outputs byte-identical to
  pre-run outputs; audit.csv 10,001 lines and audit.jsonl 10,000 lines,
  differing only in their timestamp columns; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a lowercase-z
  week-date 3-row CSV: 3 in, 2 governed, 1 quarantined). Next gap noted:
  lowercase-z ordinal datetimes ("2026-074 10:30:00z",
  "2026074T103000z", "2026-074T103000z") and lowercase-z day-first /
  month-first hyphen datetimes ("15-03-2026 10:30:00z",
  "03-15-2026 10:30:00z") still quarantine — the trailing-"Z" strips
  in the ordinal and hyphen bodies take only an uppercase "Z"
  (verified by probe: the uppercase forms govern to 2026-03-15).

- Nov 22, 2026 build block (9:05 PM run):
  lowercase-z ordinal, hyphen, and two-digit compact datetimes
  (read_claims_csv in io.py) — an ordinal datetime carrying a
  lowercase "z" zone designator ("2026-074 10:30:00z",
  "2026074T103000z", "2026-074T103000z", "2026-074 10:30:00 z",
  "2026-074 10:30:00z AM", "Sunday, 2026-074 10:30:00z", or the
  two-digit-year "26-074 10:30:00z", "26074T103000z",
  "26-074T103000z", "26074 10:30:00z AM"), a day-first /
  month-first hyphen datetime ("15-03-2026 10:30:00z",
  "03-15-2026 10:30:00z", "03-15-2026 10:30:00 z",
  "03-15-2026 10:30:00z AM", "Sunday, 03-15-2026 10:30:00z", or
  the two-digit-year "15-03-26 10:30:00z", "03-15-26 10:30:00z"),
  and a two-digit compact datetime ("031526 10:30:00z",
  "031526T103000z", "031526 10:30:00 z", "031526 10:30:00z AM",
  "Sunday, 031526 10:30:00z", "150326 10:30:00z", the way some
  exports write the UTC designator without capitals) now
  normalizes to its calendar date and governs instead of
  quarantining as unparseable_date: the trailing-"Z" strips in
  the ordinal bodies (four-digit and two-digit year), the hyphen
  body, and the two-digit compact body took only an uppercase
  "Z", while the guards and the AM/PM-suffix strips already
  matched either case. Probe before the fix: 0 of 10 ordinal,
  0 of 9 hyphen, and 0 of 6 compact lowercase-z forms governed;
  after the fix all 23 forms in the new test govern end-to-end,
  all to 2026-03-15. An impossible lowercase-z ordinal date
  ("2026-366 10:30:00z", "26-366 10:30:00z"), a doubled suffix
  ("2026074 10:30:00zz", "26074 10:30:00zz", "031526 10:30:00zz"),
  a malformed suffix ("2026-074 10:30:00+99:99", "031526
  10:30:00+99:99"), a bogus weekday label ("Funday, 2026-074
  10:30:00z"), an impossible hyphen date ("02-30-2026 10:30:00z",
  "15-13-2026 10:30:00z"), a malformed marker ("03-15-2026
  10:30:00 XM"), or an impossible compact date ("023026
  10:30:00z") is left untouched so the gates quarantine it
  normally; the quality gates stay strict and see only the
  normalized value; 2 new tests (suite now 266, all passing).
  Demo re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.589s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines and audit.jsonl 10,000 lines,
  differing only in their timestamp columns; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  lowercase-z ordinal/hyphen 3-row CSV: 3 in, 2 governed, 1
  quarantined). Next gap noted: colon-less hyphen times without
  seconds ("03-15-2026T1030z") and space-separated colon-less
  times ("03-15-2026 103000z") still quarantine — the guard
  admits six-digit T-separated times only (verified by probe:
  0 of 4 such forms govern).
- Nov 23, 2026 build block (3:05 AM run):
  colon-less T-separated numeric hyphen datetimes
  (read_claims_csv in io.py) — a hyphen datetime whose time has
  no colons ("03-15-2026T103000Z", "15-03-2026T103000z", or the
  two-digit-year "03-15-26T103000z", the way compact-timestamp
  exports write hyphen datetimes) now normalizes to its calendar
  date and governs instead of quarantining as unparseable_date:
  the hyphen guard and format list had no colon-less time
  alternative, so every such form quarantined in either case.
  Four new guard arms admit a T followed by six digits
  (fractional seconds and a zone suffix optional, AM/PM forms
  included), and the %H%M%S formats parse the colon-less time.
  Probe before the fix: 0 of 20 forms governed; after the fix
  20 of the 21 forms in the new test govern to 2026-03-15 and
  the year-first two-digit form "26-03-15T103000z" governs as
  2015-03-26, following the existing no-separate-year-first-form
  rule. An impossible colon-less hyphen date
  ("02-30-2026T103000z", "15-13-2026T103000z"), a doubled suffix
  ("03-15-2026T103000zz", "03-15-2026T103000.123zz"), a
  malformed suffix ("03-15-2026T103000+99:99",
  "03-15-2026T103000 AM +99:99"), a bogus weekday label
  ("Funday, 03-15-2026T103000z"), a malformed marker
  ("03-15-2026T103000 XM"), an unknown zone
  ("03-15-2026T103000 XYZ"), or a wrong-length time
  ("03-15-2026T10300z", "03-15-2026T1030000z") is left untouched
  so the gates quarantine it normally; the quality gates stay
  strict and see only the normalized value; 2 new tests (suite
  now 268, all passing). Demo re-verified same run (10,000 in →
  1,589 governed, 8,411 quarantined, reasons unchanged; runtime
  0.488s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines and
  audit.jsonl 10,000 lines, differing only in their timestamp
  columns; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a colon-less T-separated hyphen
  3-row CSV: 3 in, 2 governed, 1 quarantined). Next gap noted:
  colon-less hyphen times without seconds ("03-15-2026T1030z")
  and space-separated colon-less times ("03-15-2026 103000z")
  still quarantine — the guard admits six-digit T-separated
  times only (verified by probe: 0 of 4 such forms govern).
- Nov 23, 2026 build block (9:05 AM run):
  no-seconds colon-less T-separated numeric hyphen datetimes
  and space-separated colon-less numeric hyphen datetimes
  (read_claims_csv in io.py) — a hyphen datetime whose time has
  no seconds and no colons ("03-15-2026T1030z",
  "15-03-2026T1030z", or the two-digit-year "03-15-26T1030z")
  or whose colon-less time is space-separated ("03-15-2026
  103000z", "03-15-2026 1030z", two-digit-year forms included)
  now normalizes to its calendar date and governs instead of
  quarantining as unparseable_date: the hyphen guard admitted
  six-digit T-separated times only, so every no-seconds and
  space-separated colon-less hyphen form quarantined. Twelve
  new guard arms admit a T followed by four digits and a space
  followed by six or four digits (fractional seconds on the
  six-digit space form, zone suffix and AM/PM forms included),
  and the %H%M / %H%M%S formats parse the colon-less times.
  Probe before the fix: 0 of 29 forms governed; after the fix
  28 of the 29 forms in the probe govern to 2026-03-15 and only
  the fractional-second no-seconds form ("03-15-2026T1030.123z")
  still quarantines, by design. An impossible no-seconds or
  space-separated colon-less hyphen date ("02-30-2026T1030z",
  "02-30-2026 103000z"), a doubled suffix
  ("03-15-2026T1030zz", "03-15-2026 103000zz"), a malformed
  suffix ("03-15-2026T1030+99:99",
  "03-15-2026 103000+99:99"), a bogus weekday label ("Funday,
  03-15-2026T1030z"), a malformed marker ("03-15-2026T1030 XM",
  "03-15-2026 103000 XM"), an unknown zone
  ("03-15-2026T1030 XYZ", "03-15-2026 103000 XYZ"), or a
  wrong-length time ("03-15-2026T10300z",
  "03-15-2026T1030000z", "03-15-2026 10300z",
  "03-15-2026 1030000z") is left untouched so the gates
  quarantine it normally; the quality gates stay strict and see
  only the normalized value; 2 new tests (suite now 270, all
  passing). Demo re-verified same run (10,000 in → 1,589
  governed, 8,411 quarantined, reasons unchanged; runtime
  0.421s; governed, quarantine, and summary.json outputs
  byte-identical to pre-run outputs; audit.csv 10,001 lines and
  audit.jsonl 10,000 lines, differing only in their timestamp
  columns; zero raw member IDs, zero patient names in all
  outputs; CLI smoke-tested on a no-seconds / space-separated
  colon-less hyphen 3-row CSV: 3 in, 2 governed, 1 quarantined).
  No further gap found in this family this run: adjacent variants
  probed after the fix already govern — lowercase-t separator
  ("03-15-2026t103000z", "03-15-2026t1030z", 4 of 4), attached
  markers ("03-15-2026 103000am", "03-15-2026T1030am"), colon-less
  offsets ("03-15-2026T1030+0530", "03-15-2026 103000-0500"), a
  bare fractional six-digit space form ("03-15-2026 103000.123"),
  and AM/PM with a named zone ("03-15-2026 103000 AM GMT",
  "03-15-2026T1030 AM EST"); the fractional no-seconds space form
  ("03-15-2026 1030.123z") still quarantines, by design, matching
  the T-separated form.
- Nov 23, 2026 build block (3:05 PM run):
  Colon-less slash datetimes now normalize on read
  (read_claims_csv in io.py) — a slash datetime whose time has
  no colons ("03/15/2026T103000z", "15/03/2026T103000z", or the
  two-digit-year "03/15/26T103000z", the way compact-timestamp
  exports write slash datetimes) now normalizes to its calendar
  date and governs instead of quarantining as unparseable_date:
  the slash datetime formats had no colon-less alternative, so
  every such form quarantined. Thirty new %H%M%S / %H%M /
  %H%M%S.%f formats (T- and space-separated, in all five slash
  date orders) were added to both the plain and the
  timezone-stripped slash datetime format lists. Probe before
  the fix: 0 of 42 forms governed; after the fix all 42 govern
  to 2026-03-15. An impossible colon-less slash datetime
  ("02/30/2026T103000z"), a doubled suffix
  ("03/15/2026T103000zz"), a malformed suffix
  ("03/15/2026T103000+99:99"), a bogus weekday label ("Funday,
  03/15/2026T103000z"), a malformed marker ("03/15/2026T103000
  XM"), an unknown zone ("03/15/2026T103000 XYZ"), an
  out-of-range time ("03/15/2026T256000z",
  "03/15/2026T106000z", "03/15/2026T103060z"), a time with too
  many digits ("03/15/2026T1030000z"), or a fractional second
  longer than six digits ("03/15/2026T103000.1234567z") is left
  untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 272, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.469s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines and audit.jsonl 10,000 lines; zero raw
  member IDs, zero patient names in all outputs; CLI
  smoke-tested on a colon-less slash 3-row CSV: 3 in, 2 governed,
  1 quarantined).
  Found while writing the negative test: strptime reads one- or
  two-digit time components, so a short colon-less time
  ("03/15/2026T10300z", "03/15/2026T103z") and a fractional
  no-seconds form ("03/15/2026T1030.123z") govern — the same
  leniency the colon forms already carry ("03/15/2026 1:30:00"
  governs) — and only the date part governs, so the date is
  still correct; unlike the hyphen family, where the strict
  guard quarantines the fractional no-seconds form by design.
  The negative test asserts out-of-range times, over-long digit
  runs, and over-long fractional seconds instead.
- Nov 23, 2026 build block (9:05 PM run):
  Colon-less dot datetimes now normalize on read
  (read_claims_csv in io.py) — a dot datetime whose time has
  no colons ("2026.03.15T103000z", "03.15.2026T103000z", or the
  two-digit-year "03.15.26T103000z", the way compact-timestamp
  exports write dot datetimes) now normalizes to its calendar
  date and governs instead of quarantining as unparseable_date:
  the dot datetime formats had no colon-less alternative, so
  every such form quarantined. Thirty new %H%M%S / %H%M /
  %H%M%S.%f formats (T- and space-separated, in all five dot
  date orders) were added to both the plain and the
  timezone-stripped dot datetime format lists; the dot branch
  dispatch already claimed colon-less dot datetimes, so no
  guard change was needed. Probe before the fix: 0 of 5 forms
  governed; after the fix all 5 govern to 2026-03-15. An
  impossible colon-less dot datetime ("2026.02.30T103000z"),
  a doubled suffix ("2026.03.15T103000zz"), a malformed suffix
  ("2026.03.15T103000+99:99"), a bogus weekday label ("Funday,
  2026.03.15T103000z"), a malformed marker ("2026.03.15T103000
  XM"), an unknown zone ("2026.03.15T103000 XYZ"), an
  out-of-range time ("2026.03.15T256000z",
  "2026.03.15T106000z", "2026.03.15T103060z"), a time with too
  many digits ("2026.03.15T1030000z"), or a fractional second
  longer than six digits ("2026.03.15T103000.1234567z") is left
  untouched so the gates quarantine it normally; the quality
  gates stay strict and see only the normalized value; 2 new
  tests (suite now 274, all passing). Demo re-verified same run
  (10,000 in → 1,589 governed, 8,411 quarantined, reasons
  unchanged; runtime 0.477s; governed, quarantine, and
  summary.json outputs byte-identical to pre-run outputs;
  audit.csv 10,001 lines and audit.jsonl 10,000 lines, differing
  only in their timestamp columns; zero raw member IDs, zero
  patient names in all outputs; CLI smoke-tested on a
  colon-less dot 3-row CSV: 3 in, 2 governed, 1 quarantined).
  Short colon-less times ("2026.03.15T10300z",
  "2026.03.15T103z") and a fractional no-seconds form
  ("2026.03.15T1030.123z") govern, the same strptime leniency
  the colon forms already carry.
  Next gap noted: colon-less datetimes on underscore-separated
  ("2026_03_15T103000z") and month-name ("Mar 15,
  2026T103000z") dates still quarantine — probe: 0 of 5, 0 of
  3 govern. The underscore branch also needs its dispatch
  guards widened (its strict fullmatch guards require a colon
  in the time), unlike the dot branch.
- Nov 24, 2026, 03:05 run: colon-less underscore datetimes now
  normalize on read. "2026_03_15T103000z", "03_15_2026T103000z",
  "15_03_2026T103000z", "03_15_26T103000z" (plus bare, Z/z,
  fractional, numeric-offset, named-zone, weekday-prefixed, and
  AM/PM variants), no-seconds "2026_03_15T1030z" (same variants),
  and space-separated "2026_03_15 103000z" / "2026_03_15 1030z"
  (same variants) govern instead of quarantining as
  unparseable_date. Cause: the underscore dispatch guards were
  strict fullmatches requiring a colon in the time, and the
  format lists had no colon-less alternative. All 12 guard arms
  (24h + AM/PM + AM/PM-with-zone + suffix-before-marker, across
  the year-first, non-year-first, and two-digit-year families)
  widened to accept six-digit and four-digit colon-less times,
  and 30 new %H%M%S / %H%M / %H%M%S.%f formats added across the
  three format lists. Probe before the fix: 0 of 28 colon-less
  underscore forms governed; after: all 28 govern to their
  calendar date, and day-first two-digit-year forms
  ("26_03_15T103000z") govern as 2015-03-26 per the existing
  no-separate-year-first-form rule. Bad forms still quarantine
  (impossible dates, out-of-range times, doubled/malformed
  suffixes, bogus weekday, malformed marker, unknown zone,
  wrong-length times, fractional longer than six digits).
  Attached named zone ("2026_03_15T103000GMT") quarantines,
  matching the colon family exactly. A fractional no-seconds
  form ("2026_03_15T1030.123z") quarantines by design — a
  fractional part follows a seconds-bearing time only, the same
  rule the colon forms already carry; the AM/PM arms were
  tightened to match after a probe showed the widened arm
  admitting it. 2 new tests (suite now 276, all passing). Demo
  re-verified same run (10,000 in → 1,589 governed, 8,411
  quarantined, reasons unchanged; runtime 0.601s; governed,
  quarantine, and summary.json outputs byte-identical to pre-run
  outputs; audit.csv 10,001 lines and audit.jsonl 10,000 lines,
  differing only in their timestamp columns; zero raw member IDs,
  zero patient names in all outputs; CLI smoke-tested on a
  colon-less underscore 3-row CSV: 3 in, 2 governed, 1
  quarantined).
  Next gap noted: colon-less datetimes on month-name dates
  ("Mar 15, 2026T103000z") still quarantine — probe: 0 of 14
  govern.

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
