"""De-identification helpers (Safe Harbor style).

hash_member_id: one-way SHA-256 hash, truncated to 16 hex chars for
readability in demos. A hash is not encryption: treat hashed IDs as
still sensitive and keep them behind the same access controls.
strip_identifiers: removes direct-identifier columns from a record.
"""

import hashlib

IDENTIFIER_COLUMNS = ("patient_name", "member_id", "ssn", "email", "phone")


def hash_member_id(member_id: str) -> str:
    return hashlib.sha256(member_id.encode()).hexdigest()[:16]


def strip_identifiers(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in IDENTIFIER_COLUMNS}
