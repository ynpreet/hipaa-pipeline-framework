"""Demo: governed pipeline on SYNTHETIC data only (seed 42).

Generates 10,000 claims-like rows with seeded defects, runs them
through the run_pipeline orchestrator (secure defaults, quality
gates, quarantine with reasons, one audit entry per record), and
writes governed_output.csv, quarantine.csv, and audit.jsonl next
to this script's output dir — both CSVs via the io module, so the
quarantine report carries member hashes, never raw member IDs.
Run from the repo root: python3 examples/run_demo.py
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hipaa_pipeline_framework import (  # noqa: E402
    AuditLog,
    run_pipeline,
    write_governed_csv,
    write_quarantine_csv,
)

OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(exist_ok=True)


def make_raw(n=10000):
    random.seed(42)
    rows = []
    for i in range(n):
        rows.append({
            "member_id": f"M-{100000 + (i % 8500)}",
            "patient_name": f"Patient {i % 5000}",
            "service_date": random.choice(
                ["2026-01-05", "2026-02-30", "", "05/03/2026", "2026-03-15"]),
            "claim_amount": random.choice(
                ["120.50", "-40.00", "", "abc", "310.00"]),
            "diagnosis_code": random.choice(["E11.9", "", "J45.909"]),
        })
    return rows


def main():
    t0 = time.perf_counter()
    audit = AuditLog(OUT / "audit.jsonl")
    if (OUT / "audit.jsonl").exists():
        (OUT / "audit.jsonl").unlink()
    result = run_pipeline(make_raw(), audit_log=audit)
    kept, quarantined = result["governed"], result["quarantined"]
    reasons = result["reasons"]
    write_governed_csv(OUT / "governed_output.csv", kept)
    write_quarantine_csv(OUT / "quarantine.csv", quarantined)
    print(f"records_in=10000 records_governed={len(kept)} "
          f"records_quarantined={len(quarantined)}")
    print(f"quarantine_reasons={dict(reasons)}")
    print(f"runtime_seconds={time.perf_counter() - t0:.3f}")
    print(f"output_dir={OUT}")


if __name__ == "__main__":
    main()
