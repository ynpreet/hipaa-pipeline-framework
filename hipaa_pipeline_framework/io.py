"""CSV input/output for the governed pipeline.

read_claims_csv reads raw claims-like rows (all values strings) so a
caller can feed a file straight into run_pipeline; it tolerates the
mess real exports carry — a UTF-8 byte-order mark and whitespace
around headers and values, currency-formatted amounts such as
"$1,200.50" — skips blank rows outright, and still
fails closed on a header missing a required column. write_governed_csv
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
write_summary_json writes a run summary (the plain dict from
summarize_run, which contains counts and tallies and no record
data) to JSON so a run's outcome can be filed or reported without
any patient data attached.
"""

import csv
import json
from pathlib import Path

from .deidentification import hash_member_id

GOVERNED_COLUMNS = ("member_hash", "service_date",
                    "claim_amount", "diagnosis_code")
# Columns a claims CSV must carry for the quality gates to mean
# anything: without one of these, every row would quarantine as
# missing_required_field and the real problem — a malformed file —
# would hide inside the quarantine tally. diagnosis_code is
# deliberately NOT required (it defaults to "" for governed rows).
REQUIRED_COLUMNS = ("member_id", "service_date", "claim_amount")
QUARANTINE_COLUMNS = ("member_hash", "service_date",
                      "claim_amount", "diagnosis_code", "reason")
AUDIT_COLUMNS = ("timestamp", "action", "member_hash", "reason")


def read_claims_csv(path):
    """Read a claims CSV into a list of row dicts (string values).

    Fail closed on a malformed file: if the header (or an empty
    file, which has no header) is missing any REQUIRED_COLUMNS,
    raise ValueError naming the missing columns instead of
    returning rows that would all quarantine as missing fields.
    The CLI turns this into exit code 2 with no outputs written.
    Real exports are tolerated on the way in: a UTF-8 byte-order
    mark (the kind spreadsheet exports prepend) is stripped by the
    utf-8-sig encoding, and surrounding whitespace on headers and
    values is stripped, so " member_id " and " 2026-03-15 " mean
    the same as their clean forms instead of failing a gate.
    Blank rows — a commas-only line (",,") or a whitespace-only
    line, the kind trailing spreadsheet exports leave behind —
    are skipped outright: they carry no record, so counting one
    as a missing_required_field quarantine would inflate the
    quarantine tally with a non-record. A row with some fields
    filled and others empty is NOT blank and still quarantines
    normally. Currency formatting on claim_amount — a leading "$"
    and thousands commas, as in "$1,200.50" — is stripped on read,
    so a formatted amount governs instead of quarantining as
    invalid_amount; a value that is still not a number after
    stripping (e.g. "$abc") quarantines normally. The quality
    gates themselves stay strict: they see only the stripped
    value, never the raw formatting.
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = [name.strip() if name else name
                  for name in (reader.fieldnames or [])]
        reader.fieldnames = header
        missing = [col for col in REQUIRED_COLUMNS if col not in header]
        if missing:
            raise ValueError(
                f"claims CSV is missing required columns: "
                f"{', '.join(missing)}")
        rows = []
        for row in reader:
            cleaned = {key.strip(): (value.strip()
                                     if isinstance(value, str) else value)
                       for key, value in row.items() if key is not None}
            amount = cleaned.get("claim_amount")
            if isinstance(amount, str):
                cleaned["claim_amount"] = amount.replace(
                    "$", "").replace(",", "").strip()
            if cleaned and any(value not in (None, "")
                               for value in cleaned.values()):
                rows.append(cleaned)
        return rows


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


def write_summary_json(path, summary):
    """Write a run summary dict to JSON.

    summary is expected to be the plain dict from summarize_run:
    counts, quarantine rate, and per-reason tallies — no record
    data, so the file is safe to file or share. Keys are sorted
    for stable, diff-friendly output.
    """
    with open(path, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
