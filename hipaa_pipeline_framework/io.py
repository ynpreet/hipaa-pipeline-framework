"""CSV input/output for the governed pipeline.

read_claims_csv reads raw claims-like rows (all values strings) so a
caller can feed a file straight into run_pipeline. write_governed_csv
writes only governed records, under the fixed de-identified columns:
it never writes a raw member ID, patient name, or any other direct
identifier, even if one slipped into a governed record dict.
"""

import csv
from pathlib import Path

GOVERNED_COLUMNS = ("member_hash", "service_date",
                    "claim_amount", "diagnosis_code")


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
