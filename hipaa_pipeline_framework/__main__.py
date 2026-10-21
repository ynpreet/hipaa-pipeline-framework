"""Command-line entry point: run a claims CSV through the pipeline.

Usage: python3 -m hipaa_pipeline_framework input.csv \
    --governed governed.csv --quarantine quarantine.csv \
    --audit audit.jsonl [--audit-csv audit.csv]

Reads raw claims rows, runs them through run_pipeline under the
secure defaults (fail closed: any insecure config override refuses
to run), and writes the de-identified outputs via the io module —
governed records, the quarantine report, and the audit trail — so
no raw identifier ever reaches an output file. Prints only the run
summary (counts, quarantine rate, per-reason tallies), never record
data. Returns 2 on a usage or input error.
"""

import argparse
import sys

from .audit import AuditLog
from .io import (read_claims_csv, write_audit_csv, write_governed_csv,
                 write_quarantine_csv)
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
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        records = read_claims_csv(args.input)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read input: {exc}", file=sys.stderr)
        return 2
    audit = AuditLog(args.audit)
    result = run_pipeline(records, audit_log=audit)
    write_governed_csv(args.governed, result["governed"])
    write_quarantine_csv(args.quarantine, result["quarantined"])
    if args.audit_csv:
        write_audit_csv(args.audit_csv, audit)
    summary = summarize_run(result)
    print(f"records_in={summary['records_in']} "
          f"governed={summary['governed_count']} "
          f"quarantined={summary['quarantined_count']} "
          f"quarantine_rate={summary['quarantine_rate']:.3f}")
    print(f"quarantine_reasons={summary['reasons']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
