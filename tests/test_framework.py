"""Tests for hipaa-pipeline-framework (stdlib unittest only, no deps).

Run from the repo root: python3 -m unittest discover -s tests -v
Covers the three modules on synthetic data only — no real patient data.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hipaa_pipeline_framework import (  # noqa: E402
    AuditLog,
    QuarantineReason,
    default_pipeline_config,
    hash_member_id,
    is_secure,
    run_pipeline,
    strip_identifiers,
    validate_config,
    validate_record,
)


def good_record(**overrides):
    rec = {
        "member_id": "M-100001",
        "patient_name": "Patient 1",
        "service_date": "2026-03-15",
        "claim_amount": "120.50",
        "diagnosis_code": "E11.9",
    }
    rec.update(overrides)
    return rec


class TestDeidentification(unittest.TestCase):
    def test_hash_is_deterministic_and_16_hex(self):
        h = hash_member_id("M-100001")
        self.assertEqual(h, hash_member_id("M-100001"))
        self.assertEqual(len(h), 16)
        int(h, 16)  # must be valid hex

    def test_hash_distinguishes_members(self):
        self.assertNotEqual(hash_member_id("M-100001"),
                            hash_member_id("M-100002"))

    def test_strip_removes_identifiers_only(self):
        stripped = strip_identifiers(good_record())
        for col in ("patient_name", "member_id", "ssn", "email", "phone"):
            self.assertNotIn(col, stripped)
        self.assertEqual(stripped["service_date"], "2026-03-15")
        self.assertEqual(stripped["diagnosis_code"], "E11.9")


class TestQualityGates(unittest.TestCase):
    def test_valid_record_governed_with_hash(self):
        clean, reason = validate_record(good_record(), set())
        self.assertIsNone(reason)
        self.assertEqual(clean["member_hash"],
                         hash_member_id("M-100001"))
        self.assertEqual(clean["claim_amount"], 120.50)
        self.assertNotIn("patient_name", clean)

    def test_missing_field_quarantined(self):
        for field in ("member_id", "service_date", "claim_amount"):
            rec = good_record()
            rec[field] = ""
            _, reason = validate_record(rec, set())
            self.assertEqual(reason, QuarantineReason.MISSING_FIELD)

    def test_impossible_and_non_iso_dates_quarantined(self):
        for bad_date in ("2026-02-30", "05/03/2026", "not-a-date"):
            _, reason = validate_record(
                good_record(service_date=bad_date), set())
            self.assertEqual(reason, QuarantineReason.BAD_DATE)

    def test_invalid_amounts_quarantined(self):
        for bad_amount in ("-40.00", "0", "abc"):
            _, reason = validate_record(
                good_record(claim_amount=bad_amount), set())
            self.assertEqual(reason, QuarantineReason.BAD_AMOUNT)

    def test_exact_duplicate_quarantined_second_time(self):
        seen = set()
        clean, reason = validate_record(good_record(), seen)
        self.assertIsNone(reason)
        _, reason2 = validate_record(good_record(), seen)
        self.assertEqual(reason2, QuarantineReason.DUPLICATE)


class TestAuditLog(unittest.TestCase):
    def test_writes_one_json_line_per_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            log = AuditLog(path)
            log.write("governed", "abc123")
            log.write("quarantined", "redacted",
                      QuarantineReason.BAD_DATE)
            entries = [json.loads(line) for line in
                       path.read_text().splitlines()]
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["action"], "governed")
            self.assertEqual(entries[1]["reason"],
                             QuarantineReason.BAD_DATE)


class TestConfig(unittest.TestCase):
    def test_defaults_are_secure(self):
        cfg = default_pipeline_config()
        self.assertEqual(validate_config(cfg), [])
        self.assertTrue(is_secure(cfg))

    def test_each_insecure_override_is_flagged(self):
        for bad in ({"encryption_at_rest": False},
                    {"audit_enabled": False},
                    {"quarantine_on_failure": False},
                    {"log_phi": True}):
            cfg = default_pipeline_config()
            cfg.update(bad)
            self.assertFalse(is_secure(cfg))
            self.assertEqual(len(validate_config(cfg)), 1)

    def test_defaults_are_fresh_copies(self):
        a = default_pipeline_config()
        a["log_phi"] = True
        self.assertTrue(is_secure(default_pipeline_config()))


class TestPipeline(unittest.TestCase):
    def test_run_governs_good_and_quarantines_bad(self):
        result = run_pipeline([
            good_record(),
            good_record(service_date="2026-02-30"),
            good_record(claim_amount="-5"),
        ])
        self.assertEqual(result["records_in"], 3)
        self.assertEqual(len(result["governed"]), 1)
        self.assertEqual(len(result["quarantined"]), 2)
        self.assertEqual(result["reasons"],
                         {QuarantineReason.BAD_DATE: 1,
                          QuarantineReason.BAD_AMOUNT: 1})
        self.assertNotIn("patient_name", result["governed"][0])

    def test_run_refuses_insecure_config(self):
        cfg = default_pipeline_config()
        cfg["log_phi"] = True
        with self.assertRaises(ValueError):
            run_pipeline([good_record()], config=cfg)

    def test_run_writes_one_audit_entry_per_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            result = run_pipeline([good_record(),
                                   good_record(service_date="")],
                                  audit_log=AuditLog(path))
            entries = [json.loads(line) for line in
                       path.read_text().splitlines()]
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["action"], "governed")
            self.assertEqual(entries[1]["action"], "quarantined")
            self.assertEqual(entries[1]["member_hash"], "redacted")
            self.assertEqual(len(result["governed"]), 1)


if __name__ == "__main__":
    unittest.main()
