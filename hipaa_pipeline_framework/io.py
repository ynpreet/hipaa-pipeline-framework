"""CSV input/output for the governed pipeline.

read_claims_csv reads raw claims-like rows (all values strings) so a
caller can feed a file straight into run_pipeline. write_governed_csv
writes only governed records, under the fixed de-identified columns:
it never writes a raw member ID, patient name, or any other direct
identifier, even if one slipped into a governed record dict.
write_quarantine_csv writes quarantined (record, reason) pairs the
same way: the raw record is replaced by its member hash plus the
quarantine reason, so quarantine reports never leak identifiers.
write_audit_csv exports an AuditLog's trail to CSV for reviewers
who work in spreadsheets: one row per entry, under the fixed audit
columns, carrying only the hashed member reference the trail
already stores — never a raw identifier.
"""

import csv
from pathlib import Path

from .deidentification import hash_member_id

GOVERNED_COLUMNS = ("member_hash", "service_date",
                    "claim_amount", "diagnosis_code")
QUARANTINE_COLUMNS = ("member_hash", "service_date",
                      "claim_amount", "diagnosis_code", "reason")
AUDIT_COLUMNS = ("timestamp", "action", "member_hash", "reason")


def read_claims_csv(path):
    """Read a claims CSV into a list of row dicts (string values)."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_governed_csv(path, governed):
    """Write governed records as a de-identified CSV.

    Columns are exactly GOVERNED_COLUMNS; any other key in a record
    (including a raw identifier) is dropped, never written out.
    An empty governed list still writes the header row.
    """
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(GOVERNED_COLUMNS))
        writer.writeheader()
        for record in governed:
            writer.writerow({col: record.get(col, "")
                             for col in GOVERNED_COLUMNS})


def write_quarantine_csv(path, quarantined):
    """Write quarantined (record, reason) pairs, de-identified.

    Columns are exactly QUARANTINE_COLUMNS. Each raw record is
    reduced to its member hash (or "" when the record has no
    member ID, e.g. a missing-field failure) plus its non-identifier
    fields and the quarantine reason — patient names and raw member
    IDs are never written out, so a quarantine report is safe to
    share with a reviewer. An empty list still writes the header.
    """
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(QUARANTINE_COLUMNS))
        writer.writeheader()
        for record, reason in quarantined:
            member_id = record.get("member_id", "")
            writer.writerow({
                "member_hash": hash_member_id(member_id) if member_id else "",
                "service_date": record.get("service_date", ""),
                "claim_amount": record.get("claim_amount", ""),
                "diagnosis_code": record.get("diagnosis_code", ""),
                "reason": reason,
            })


def write_audit_csv(path, audit_log):
    """Export an AuditLog's trail to CSV for reviewers.

    Columns are exactly AUDIT_COLUMNS. Each row is one trail entry
    (timestamp, action, member hash or "redacted", reason). The
    trail stores only hashes and "redacted" markers, so the export
    contains no raw identifiers. An empty or missing trail still
    writes the header row.
    """
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(AUDIT_COLUMNS))
        writer.writeheader()
        for entry in audit_log.entries():
            writer.writerow({col: entry.get(col, "") or ""
                             for col in AUDIT_COLUMNS})
