"""HIPAA-oriented pipeline building blocks (synthetic-data demos only).

Generic patterns distilled from 'Data Engineering for Healthcare:
Building HIPAA-Ready Data Pipelines'. No employer data, no client
details, no real patient data anywhere in this repo.
"""

from .audit import AuditLog
from .deidentification import hash_member_id, strip_identifiers
from .quality import QuarantineReason, validate_record

__all__ = [
    "AuditLog",
    "QuarantineReason",
    "hash_member_id",
    "strip_identifiers",
    "validate_record",
]
