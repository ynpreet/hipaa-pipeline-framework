"""HIPAA-oriented pipeline building blocks (synthetic-data demos only).

Generic patterns distilled from 'Data Engineering for Healthcare:
Building HIPAA-Ready Data Pipelines'. No employer data, no client
details, no real patient data anywhere in this repo.
"""

from .audit import AuditLog
from .config import default_pipeline_config, is_secure, validate_config
from .deidentification import hash_member_id, strip_identifiers
from .io import (AUDIT_COLUMNS, GOVERNED_COLUMNS, QUARANTINE_COLUMNS,
                 read_claims_csv, write_audit_csv, write_governed_csv,
                 write_quarantine_csv, write_summary_json)
from .pipeline import run_pipeline, summarize_run
from .quality import QuarantineReason, validate_record

__all__ = [
    "AUDIT_COLUMNS",
    "AuditLog",
    "GOVERNED_COLUMNS",
    "QUARANTINE_COLUMNS",
    "QuarantineReason",
    "default_pipeline_config",
    "hash_member_id",
    "is_secure",
    "read_claims_csv",
    "run_pipeline",
    "strip_identifiers",
    "summarize_run",
    "validate_config",
    "validate_record",
    "write_audit_csv",
    "write_governed_csv",
    "write_quarantine_csv",
    "write_summary_json",
]
