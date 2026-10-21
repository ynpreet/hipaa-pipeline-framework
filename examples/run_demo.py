"""Demo: governed pipeline on SYNTHETIC data only (seed 42).

Generates 10,000 claims-like rows with seeded defects, runs them
through de-identification + quality gates, writes governed_output.csv,
quarantine.csv, and audit.jsonl next to this script's output dir.
Run from the repo root: python3 examples/run_demo.py
"""

import csv
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hipaa_pipeline_framework import AuditLog, validate_record  # noqa: E402

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
    seen, kept, quarantined, reasons = set(), [], [], Counter()
    for r in make_raw():
        clean, reason = validate_record(r, seen)
        if reason:
            reasons[reason] += 1
            quarantined.append((r, reason))
            audit.write("quarantined", "redacted", reason)
        else:
            kept.append(clean)
            audit.write("governed", clean["member_hash"])
    with open(OUT / "governed_output.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(kept[0]))
        w.writeheader()
        w.writerows(kept)
    with open(OUT / "quarantine.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["member_id", "service_date", "claim_amount", "reason"])
        for r, why in quarantined:
            w.writerow([r["member_id"], r["service_date"],
                        r["claim_amount"], why])
    print(f"records_in=10000 records_governed={len(kept)} "
          f"records_quarantined={len(quarantined)}")
    print(f"quarantine_reasons={dict(reasons)}")
    print(f"runtime_seconds={time.perf_counter() - t0:.3f}")
    print(f"output_dir={OUT}")


if __name__ == "__main__":
    main()
