"""End-to-end governed pipeline runner.

run_pipeline ties the building blocks together: it refuses to start
on an insecure config (fail closed), runs every record through the
quality gates, quarantines failures with a reason (never silently
drops them), and writes one audit entry per record when an AuditLog
is supplied. Returns a dict with governed records, quarantined
(record, reason) pairs, per-reason counts, and governed /
quarantined counts so callers need not recompute them.
"""

from collections import Counter

from .config import default_pipeline_config, validate_config
from .quality import validate_record


def run_pipeline(records, config=None, audit_log=None):
    """Run records through the governed pipeline.

    records: iterable of claims-like dicts.
    config: pipeline config; defaults to secure defaults. Raises
        ValueError if the config fails validation.
    audit_log: optional AuditLog; governed entries carry the member
        hash, quarantined entries carry "redacted" (never raw PHI).
    """
    cfg = default_pipeline_config() if config is None else config
    problems = validate_config(cfg)
    if problems:
        raise ValueError(
            "refusing to run pipeline with insecure config: "
            + "; ".join(problems)
        )
    seen = set()
    governed, quarantined, reasons = [], [], Counter()
    records_in = 0
    for record in records:
        records_in += 1
        clean, reason = validate_record(record, seen)
        if reason:
            reasons[reason] += 1
            quarantined.append((record, reason))
            if audit_log is not None:
                audit_log.write("quarantined", "redacted", reason)
        else:
            governed.append(clean)
            if audit_log is not None:
                audit_log.write("governed", clean["member_hash"])
    return {
        "records_in": records_in,
        "governed": governed,
        "quarantined": quarantined,
        "governed_count": len(governed),
        "quarantined_count": len(quarantined),
        "reasons": dict(reasons),
    }
