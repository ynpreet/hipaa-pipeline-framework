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
