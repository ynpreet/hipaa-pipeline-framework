"""HIPAA-oriented pipeline building blocks (synthetic-data demos only).

Generic patterns distilled from 'Data Engineering for Healthcare:
Building HIPAA-Ready Data Pipelines'. No employer data, no client
details, no real patient data anywhere in this repo.
"""

from .audit import AuditLog
from .config import default_pipeline_config, is_secure, validate_config
from .deidentification import hash_member_id, strip_identifiers
from .quality import QuarantineReason, validate_record

__all__ = [
    "AuditLog",
    "QuarantineReason",
    "default_pipeline_config",
    "hash_member_id",
    "is_secure",
    "strip_identifiers",
    "validate_config",
    "validate_record",
]
