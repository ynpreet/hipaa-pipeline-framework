"""Command-line entry point: run a claims CSV through the pipeline.

Usage: python3 -m hipaa_pipeline_framework input.csv \
    --governed governed.csv --quarantine quarantine.csv \
    --audit audit.jsonl [--audit-csv audit.csv] \
    [--summary-json summary.json]

Reads raw claims rows, runs them through run_pipeline under the
secure defaults (fail closed: any insecure config override refuses
to run), and writes the de-identified outputs via the io module —
governed records, the quarantine report, and the audit trail — so
no raw identifier ever reaches an output file. Prints only the run
summary (counts, quarantine rate, per-reason tallies), never record
data. Missing parent directories of the output files are created
before the run starts, so a nested output path works without a
prior mkdir; an unwritable output path still returns 2, with an
error line instead of a traceback. Returns 2 on a usage or input
error.
"""

import argparse
import sys
from pathlib import Path

from .audit import AuditLog
from .io import (read_claims_csv, write_audit_csv, write_governed_csv,
                 write_quarantine_csv, write_summary_json)
from .pipeline import run_pipeline, summarize_run


def build_parser():
    parser = argparse.ArgumentParser(
        prog="hipaa_pipeline_framework",
        description="Run a claims CSV through the governed pipeline.")
    parser.add_argument("input", help="input claims CSV (raw rows)")
    parser.add_argument("--governed", required=True,
                        help="output CSV for governed records")
    parser.add_argument("--quarantine", required=True,
                        help="output CSV for the quarantine report")
    parser.add_argument("--audit", required=True,
                        help="output JSONL audit trail")
    parser.add_argument("--audit-csv", default=None,
                        help="optional CSV export of the audit trail")
    parser.add_argument("--summary-json", default=None,
                        help="optional JSON export of the run summary")
    return parser


def _ensure_parent_dirs(paths):
    """Create the parent directory of each output path, if needed.

    A path with no parent component (a bare filename in the current
    directory) needs nothing. Anything else is created, nested
    levels included, before any output is written, so the run
    never fails halfway through on a missing directory. Raises
    OSError when a parent cannot be created (e.g. a path component
    is a regular file); the caller turns that into exit code 2.
    """
    for path in paths:
        parent = Path(path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        records = read_claims_csv(args.input)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read input: {exc}", file=sys.stderr)
        return 2
    outputs = [args.governed, args.quarantine, args.audit]
    if args.audit_csv:
        outputs.append(args.audit_csv)
    if args.summary_json:
        outputs.append(args.summary_json)
    try:
        _ensure_parent_dirs(outputs)
        audit = AuditLog(args.audit)
        result = run_pipeline(records, audit_log=audit)
        write_governed_csv(args.governed, result["governed"])
        write_quarantine_csv(args.quarantine, result["quarantined"])
        if args.audit_csv:
            write_audit_csv(args.audit_csv, audit)
        summary = summarize_run(result)
        if args.summary_json:
            write_summary_json(args.summary_json, summary)
    except OSError as exc:
        print(f"error: cannot write output: {exc}", file=sys.stderr)
        return 2
    print(f"records_in={summary['records_in']} "
          f"governed={summary['governed_count']} "
          f"quarantined={summary['quarantined_count']} "
          f"quarantine_rate={summary['quarantine_rate']:.3f}")
    print(f"quarantine_reasons={summary['reasons']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
