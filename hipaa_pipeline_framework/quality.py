"""Data-quality gates for claims-like records.

validate_record returns (clean_record, reason). A record that fails
any gate is quarantined with a reason — never silently dropped.
Dates are validated against the real calendar (2026-02-30 fails).
"""

from datetime import datetime


class QuarantineReason:
    MISSING_FIELD = "missing_required_field"
    BAD_DATE = "unparseable_date"
    BAD_AMOUNT = "invalid_amount"
    DUPLICATE = "duplicate"


def validate_record(record, seen):
    """Validate one record. `seen` is a set of dedupe keys, mutated here."""
    for field in ("member_id", "service_date", "claim_amount"):
        if not record.get(field):
            return None, QuarantineReason.MISSING_FIELD
    try:
        datetime.strptime(record["service_date"], "%Y-%m-%d")
    except ValueError:
        return None, QuarantineReason.BAD_DATE
    try:
        amount = float(record["claim_amount"])
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return None, QuarantineReason.BAD_AMOUNT
    from .deidentification import hash_member_id

    key = (hash_member_id(record["member_id"]), record["service_date"], amount)
    if key in seen:
        return None, QuarantineReason.DUPLICATE
    seen.add(key)
    return {
        "member_hash": key[0],
        "service_date": record["service_date"],
        "claim_amount": amount,
        "diagnosis_code": record.get("diagnosis_code", ""),
    }, None
