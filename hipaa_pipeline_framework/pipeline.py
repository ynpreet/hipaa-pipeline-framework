"""End-to-end governed pipeline runner.

run_pipeline ties the building blocks together: it refuses to start
on an insecure config (fail closed), runs every record through the
quality gates, quarantines failures with a reason (never silently
drops them), and writes one audit entry per record when an AuditLog
is supplied. Returns a dict with governed records, quarantined
(record, reason) pairs, per-reason counts, and governed /
quarantined counts so callers need not recompute them.

summarize_run turns that result into a plain, log-friendly summary
dict: counts, quarantine rate (fraction quarantined; 0.0 when
nothing ran), and the per-reason tallies. Rounding is left to the
caller so the summary stays exact.
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


def summarize_run(result):
    """Summarize a run_pipeline result as a plain dict.

    result: the dict returned by run_pipeline. Returns records_in,
    governed_count, quarantined_count, quarantine_rate (fraction
    quarantined, 0.0 when no records ran), and reasons. Contains
    no record data, so it is safe to log or paste into a report.
    """
    records_in = result.get("records_in", 0) or 0
    quarantined_count = result.get("quarantined_count", 0) or 0
    return {
        "records_in": records_in,
        "governed_count": result.get("governed_count", 0) or 0,
        "quarantined_count": quarantined_count,
        "quarantine_rate": (quarantined_count / records_in
                            if records_in else 0.0),
        "reasons": dict(result.get("reasons", {})),
    }
