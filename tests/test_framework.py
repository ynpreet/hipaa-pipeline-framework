"""Tests for hipaa-pipeline-framework (stdlib unittest only, no deps).

Run from the repo root: python3 -m unittest discover -s tests -v
Covers the three modules on synthetic data only — no real patient data.
"""

import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hipaa_pipeline_framework import (  # noqa: E402
    AUDIT_COLUMNS,
    AuditLog,
    GOVERNED_COLUMNS,
    QUARANTINE_COLUMNS,
    QuarantineReason,
    default_pipeline_config,
    hash_member_id,
    is_secure,
    read_claims_csv,
    run_pipeline,
    strip_identifiers,
    summarize_run,
    validate_config,
    validate_record,
    write_audit_csv,
    write_governed_csv,
    write_quarantine_csv,
    write_summary_json,
)
from hipaa_pipeline_framework.__main__ import main as cli_main  # noqa: E402


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

    def test_summary_tallies_by_action_and_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            log = AuditLog(path)
            self.assertEqual(log.summary(), {"total": 0,
                                             "by_action": {},
                                             "by_reason": {}})
            log.write("governed", "abc123")
            log.write("quarantined", "redacted",
                      QuarantineReason.BAD_DATE)
            log.write("quarantined", "redacted",
                      QuarantineReason.BAD_DATE)
            log.write("quarantined", "redacted",
                      QuarantineReason.BAD_AMOUNT)
            self.assertEqual(log.summary(), {
                "total": 4,
                "by_action": {"governed": 1, "quarantined": 3},
                "by_reason": {QuarantineReason.BAD_DATE: 2,
                              QuarantineReason.BAD_AMOUNT: 1},
            })

    def test_entries_carry_utc_timestamp_and_read_back(self):
        from datetime import datetime
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            log = AuditLog(path)
            self.assertEqual(log.entries(), [])  # no trail yet
            log.write("governed", "abc123")
            entries = log.entries()
            self.assertEqual(len(entries), 1)
            # Timestamp parses and is UTC (offset-aware, +00:00).
            ts = datetime.fromisoformat(entries[0]["timestamp"])
            self.assertIsNotNone(ts.tzinfo)
            self.assertEqual(entries[0]["action"], "governed")


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

    def test_run_reports_governed_and_quarantined_counts(self):
        result = run_pipeline([
            good_record(),
            good_record(service_date="2026-02-30"),
            good_record(claim_amount="-5"),
        ])
        self.assertEqual(result["governed_count"], 1)
        self.assertEqual(result["quarantined_count"], 2)
        self.assertEqual(result["governed_count"]
                         + result["quarantined_count"],
                         result["records_in"])

    def test_summarize_run_reports_counts_and_rate(self):
        result = run_pipeline([
            good_record(),
            good_record(service_date="2026-02-30"),
        ])
        summary = summarize_run(result)
        self.assertEqual(summary["records_in"], 2)
        self.assertEqual(summary["governed_count"], 1)
        self.assertEqual(summary["quarantined_count"], 1)
        self.assertAlmostEqual(summary["quarantine_rate"], 0.5)
        self.assertEqual(summary["reasons"],
                         {QuarantineReason.BAD_DATE: 1})
        # Empty run: rate is 0.0, not a division error.
        empty = summarize_run({"records_in": 0, "governed_count": 0,
                               "quarantined_count": 0, "reasons": {}})
        self.assertEqual(empty["quarantine_rate"], 0.0)

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


class TestCsvIO(unittest.TestCase):
    def test_csv_rows_feed_run_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text(
                "member_id,patient_name,service_date,claim_amount,"
                "diagnosis_code\n"
                "M-100001,Patient 1,2026-03-15,120.50,E11.9\n"
                "M-100002,Patient 2,2026-02-30,40.00,J45.909\n"
            )
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["claim_amount"], "120.50")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 1)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_missing_column_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text(
                "member_id,service_date\n"
                "M-100001,2026-03-15\n"
            )
            with self.assertRaises(ValueError) as ctx:
                read_claims_csv(path)
            self.assertIn("claim_amount", str(ctx.exception))

    def test_read_claims_csv_empty_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            path.write_text("")
            with self.assertRaises(ValueError) as ctx:
                read_claims_csv(path)
            for col in ("member_id", "service_date", "claim_amount"):
                self.assertIn(col, str(ctx.exception))

    def test_read_claims_csv_tolerates_bom_and_padding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            # Spreadsheet-style export: UTF-8 BOM plus whitespace
            # around headers and values.
            path.write_bytes(
                b"\xef\xbb\xbf member_id , service_date , "
                b"claim_amount , diagnosis_code \n"
                b" M-100001 , 2026-03-15 , 120.50 , E11.9 \n"
            )
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["member_id"], "M-100001")
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 1)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_skips_blank_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            # Trailing spreadsheet-export junk: a commas-only
            # line and a whitespace-only line between real rows.
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15,120.50\n"
                            ",,\n"
                            "   \n"
                            "M-100002,2026-03-16,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["records_in"], 2)
            self.assertEqual(result["governed_count"], 2)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_strips_currency_formatting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            # Spreadsheet-style amount: quoted because of the comma.
            path.write_text("member_id,service_date,claim_amount\n"
                            'M-100001,2026-03-15,"$1,200.50"\n')
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["claim_amount"], "1200.50")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 1)
            self.assertEqual(result["quarantined_count"], 0)
            self.assertEqual(result["governed"][0]["claim_amount"],
                             1200.50)

    def test_read_claims_csv_currency_garbage_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15,$abc\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_AMOUNT: 1})

    def test_read_claims_csv_partial_row_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15,\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.MISSING_FIELD: 1})

    def test_read_claims_csv_normalizes_slash_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 1)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_slash_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02/30/2026,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_year_first_slash_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026/03/15,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 1)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_year_first_slash_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026/02/30,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_day_first_slash_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15/03/2026,120.50\n"
                            "M-100002,03/04/2026,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            # The US form keeps priority: an ambiguous slash date
            # still reads as MM/DD/YYYY, not DD/MM/YYYY.
            self.assertEqual(rows[1]["service_date"], "2026-03-04")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 2)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_day_first_slash_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,32/03/2026,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_slash_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00,120.50\n"
                            "M-100002,15/03/2026T09:00:00,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 2)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_slash_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02/30/2026 10:00:00,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_dot_separated_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 1)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_dot_separated_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.02.30,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_dot_separated_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15 10:30:00,120.50\n"
                            "M-100002,2026.03.16T09:00:00,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 2)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_dot_separated_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.02.30 10:00:00,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_tz_suffixed_dot_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15 10:30:00Z,120.50\n"
                            "M-100002,2026.03.16T09:00:00-04:00,200.00\n"
                            "M-100003,\"Sunday, 2026.03.17 10:30:00+05:30\",310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-17")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 3)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_tz_suffixed_dot_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.02.30 10:00:00Z,120.50\n"
                            "M-100002,2026.03.15 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_space_separated_tz_dot_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15 10:30:00 +05:00,120.50\n"
                            "M-100002,2026.03.15 10:30:00 -0400,200.00\n"
                            "\"M-100003\",\"Sunday, 2026.03.16 10:30:00 Z\",310.00\n"
                            "M-100004,2026.03.15 10:30:00.123 +05:00,410.00\n"
                            "\"M-100005\",\"2026.03.15 10:30:00 +05:00 AM\",510.00\n"
                            "M-100006,2026.03.15T09:00:00 +05:00,610.00\n"
                            "M-100007,03.15.26 10:30:00 +05:00,710.00\n"
                            "M-100008,15.03.26 10:30:00 +05:30,810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            self.assertEqual(rows[7]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 8)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_tz_dot_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15 10:30:00 +99:99,120.50\n"
                            "M-100002,2026.02.30 10:00:00 +05:00,200.00\n"
                            "\"M-100003\",\"2026.03.15 10:30:00 +05:00 XM\",310.00\n"
                            "\"M-100004\",\"Funday, 2026.03.15 10:30:00 +05:00\",410.00\n"
                            "M-100005,2026.03.15 10:30:00 +25:00,510.00\n"
                            "M-100006,2026.03.15 10:30:00 +05:60,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_month_name_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026\",120.50\n"
                            "M-100002,15 March 2026,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 2)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_normalizes_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026 10:30:00\",120.50\n"
                            "M-100002,15 Mar 2026T09:00:00,200.00\n"
                            "M-100003,\"Sunday, Mar 15, 2026 10:30:00\",310.00\n"
                            "M-100004,\"Mon, 17-Mar-2026 10:30:00\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-17")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_month_name_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026 10:00:00\",120.50\n"
                            "M-100002,\"Mar 15, 2026 not-a-time\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_tz_suffixed_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026 10:30:00Z\",120.50\n"
                            "M-100002,15 Mar 2026T09:00:00-04:00,200.00\n"
                            "M-100003,\"Sunday, Mar 15, 2026 10:30:00+05:00\",310.00\n"
                            "M-100004,\"Mon, 17-Mar-2026 10:30:00Z\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-17")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_tz_suffixed_month_name_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026 10:00:00Z\",120.50\n"
                            "M-100002,\"Mar 15, 2026 10:30:00+99:99\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_tz_suffixed_slash_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00Z,120.50\n"
                            "M-100002,03/15/2026T09:00:00-04:00,200.00\n"
                            "M-100003,\"Sunday, 03/16/2026 10:30:00+05:30\",310.00\n"
                            "M-100004,15/03/2026 10:30:00Z,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_tz_suffixed_slash_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02/30/2026 10:00:00Z,120.50\n"
                            "M-100002,03/15/2026 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_bad_month_name_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026\",120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_compact_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 1)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_compact_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_hyphenated_month_name_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15-Mar-2026,120.50\n"
                            "M-100002,Mar-16-2026,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 2)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_hyphenated_month_name_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,30-Feb-2026,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_numeric_hyphen_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026,120.50\n"
                            "M-100002,15-03-2026,200.00\n"
                            "M-100003,03-04-2026,310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            # The US form keeps priority: an ambiguous hyphen date
            # still reads as MM-DD-YYYY, not DD-MM-YYYY.
            self.assertEqual(rows[2]["service_date"], "2026-03-04")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 3)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_numeric_hyphen_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02-30-2026,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_weekday_prefixed_numeric_hyphen_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Sunday, 03-15-2026\",120.50\n"
                            "M-100002,\"Mon, 15-03-2026\",200.00\n"
                            "M-100003,\"Tues, 03-04-2026\",310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            # The US form keeps priority: an ambiguous hyphen date
            # still reads as MM-DD-YYYY, not DD-MM-YYYY.
            self.assertEqual(rows[2]["service_date"], "2026-03-04")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 3)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_weekday_prefixed_numeric_hyphen_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Monday, 02-30-2026\",120.50\n"
                            "M-100002,\"Funday, 03-15-2026\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_underscore_separated_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 1)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_underscore_separated_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_02_30,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_weekday_prefixed_underscore_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Sunday, 2026_03_15\",120.50\n"
                            "M-100002,\"Mon, 2026_03_16\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 2)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_weekday_prefixed_underscore_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Monday, 2026_02_30\",120.50\n"
                            "M-100002,\"Funday, 2026_03_15\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ordinal_month_name_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"March 15th, 2026\",120.50\n"
                            "M-100002,15th Mar 2026,200.00\n"
                            "M-100003,\"March 1st, 2026\",310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-01")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 3)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ordinal_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30th, 2026\",120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 1})

    def test_read_claims_csv_normalizes_weekday_prefixed_month_name_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Sunday, March 15, 2026\",120.50\n"
                            "M-100002,\"Mon, 16 Mar 2026\",200.00\n"
                            "M-100003,\"Sunday, March 1st, 2026\",310.00\n"
                            "M-100004,\"Tues, 17 Mar 2026\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-01")
            self.assertEqual(rows[3]["service_date"], "2026-03-17")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_weekday_prefixed_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Monday, Feb 30, 2026\",120.50\n"
                            "M-100002,\"Funday, March 15, 2026\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_weekday_prefixed_iso_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Sunday, 2026-03-15\",120.50\n"
                            "M-100002,\"Mon, 2026-03-16\",200.00\n"
                            "M-100003,\"Tues, 2026-03-17 10:30:00\",310.00\n"
                            "M-100004,\"Sun, 2026-03-18T09:00:00\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-17")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_weekday_prefixed_iso_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Monday, 2026-02-30\",120.50\n"
                            "M-100002,\"Funday, 2026-03-15\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_weekday_prefixed_slash_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Sunday, 03/15/2026\",120.50\n"
                            "M-100002,\"Mon, 15/03/2026\",200.00\n"
                            "M-100003,\"Tues, 03/16/2026 10:30:00\",310.00\n"
                            "M-100004,\"Sun, 03/04/2026\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            # The US form keeps priority: an ambiguous slash date
            # still reads as MM/DD/YYYY, not DD/MM/YYYY.
            self.assertEqual(rows[3]["service_date"], "2026-03-04")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_weekday_prefixed_slash_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Monday, 02/30/2026\",120.50\n"
                            "M-100002,\"Funday, 03/15/2026\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_weekday_prefixed_dot_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Sunday, 2026.03.15\",120.50\n"
                            "M-100002,\"Mon, 2026.03.16\",200.00\n"
                            "M-100003,\"Tues, 2026.03.17\",310.00\n"
                            "M-100004,\"Sun, 2026.03.18\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-17")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_weekday_prefixed_dot_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Monday, 2026.02.30\",120.50\n"
                            "M-100002,\"Funday, 2026.03.15\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_weekday_prefixed_compact_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Sunday, 20260315\",120.50\n"
                            "M-100002,\"Mon, 20260316\",200.00\n"
                            "M-100003,\"Tues, 20260317\",310.00\n"
                            "M-100004,\"Sun, 20260318\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-17")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_weekday_prefixed_compact_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Monday, 20260230\",120.50\n"
                            "M-100002,\"Funday, 20260315\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_timezone_suffixed_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 10:30:00Z,120.50\n"
                            "M-100002,20260316T09:00:00-04:00,200.00\n"
                            "M-100003,\"Sunday, 20260317 10:30:00+05:30\",310.00\n"
                            "M-100004,20260318T08:00:00+0500,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-17")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_timezone_suffixed_compact_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230 10:00:00Z,120.50\n"
                            "M-100002,20260315 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_space_separated_tz_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 10:30:00 +05:00,120.50\n"
                            "M-100002,20260315 10:30:00 -0400,200.00\n"
                            "\"M-100003\",\"Sunday, 20260316 10:30:00 Z\",310.00\n"
                            "M-100004,20260315 10:30:00.123 +05:00,410.00\n"
                            "\"M-100005\",\"20260315 10:30:00 +05:00 AM\",510.00\n"
                            "M-100006,20260315T09:00:00 +05:00,610.00\n"
                            "M-100007,20260315 10:30 +05:00,710.00\n"
                            "M-100008,20260315 10:30:00 +0530,810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            self.assertEqual(rows[7]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 8)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_tz_compact_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 10:30:00 +99:99,120.50\n"
                            "M-100002,20260230 10:00:00 +05:00,200.00\n"
                            "\"M-100003\",\"20260315 10:30:00 +05:00 XM\",310.00\n"
                            "\"M-100004\",\"Funday, 20260315 10:30:00 +05:00\",410.00\n"
                            "M-100005,20260315 10:30:00 +25:00,510.00\n"
                            "M-100006,20260315 10:30:00 +05:60,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_space_separated_tz_underscore_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15 10:30:00 +05:00,120.50\n"
                            "M-100002,2026_03_15 10:30:00 -0400,200.00\n"
                            "\"M-100003\",\"Sunday, 2026_03_16 10:30:00 Z\",310.00\n"
                            "M-100004,2026_03_15 10:30:00.123 +05:00,410.00\n"
                            "\"M-100005\",\"2026_03_15 10:30:00 +05:00 AM\",510.00\n"
                            "M-100006,2026_03_15T09:00:00 +05:00,610.00\n"
                            "M-100007,2026_03_15 10:30 +05:00,710.00\n"
                            "M-100008,2026_03_15 10:30:00 +0530,810.00\n"
                            "M-100009,03_15_26 10:30:00 +05:00,910.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 9)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            self.assertEqual(rows[7]["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 9)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_tz_underscore_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15 10:30:00 +99:99,120.50\n"
                            "M-100002,2026_02_30 10:00:00 +05:00,200.00\n"
                            "\"M-100003\",\"2026_03_15 10:30:00 +05:00 XM\",310.00\n"
                            "\"M-100004\",\"Funday, 2026_03_15 10:30:00 +05:00\",410.00\n"
                            "M-100005,2026_03_15 10:30:00 +25:00,510.00\n"
                            "M-100006,2026_03_15 10:30:00 +05:60,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_space_separated_tz_numeric_hyphen_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026 10:30:00 +05:00,120.50\n"
                            "M-100002,03-15-2026 10:30:00 -0400,200.00\n"
                            "\"M-100003\",\"Sunday, 03-16-2026 10:30:00 Z\",310.00\n"
                            "M-100004,03-15-2026 10:30:00.123 +05:00,410.00\n"
                            "\"M-100005\",\"03-15-2026 10:30:00 +05:00 AM\",510.00\n"
                            "M-100006,03-15-2026T09:00:00 +05:00,610.00\n"
                            "M-100007,03-15-2026 10:30 +05:00,710.00\n"
                            "M-100008,03-15-2026 10:30:00 +0530,810.00\n"
                            "M-100009,03-15-26 10:30:00 +05:00,910.00\n"
                            "M-100010,15-03-2026 10:30:00 +05:00,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            self.assertEqual(rows[7]["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-15")
            self.assertEqual(rows[9]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 10)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_tz_numeric_hyphen_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026 10:30:00 +99:99,120.50\n"
                            "M-100002,02-30-2026 10:00:00 +05:00,200.00\n"
                            "\"M-100003\",\"03-15-2026 10:30:00 +05:00 XM\",310.00\n"
                            "\"M-100004\",\"Funday, 03-15-2026 10:30:00 +05:00\",410.00\n"
                            "M-100005,03-15-2026 10:30:00 +25:00,510.00\n"
                            "M-100006,03-15-2026 10:30:00 +05:60,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_fractional_second_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 10:30:00.123Z,120.50\n"
                            "M-100002,20260316T09:00:00.5-04:00,200.00\n"
                            "M-100003,\"Sunday, 20260317 10:30:00.123456+05:30\",310.00\n"
                            "M-100004,20260318 10:30:00.999,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-17")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_fractional_second_compact_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230 10:00:00.123Z,120.50\n"
                            "M-100002,20260315 10:30:00.123+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_timezone_suffixed_underscore_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15 10:30:00Z,120.50\n"
                            "M-100002,2026_03_16T09:00:00-04:00,200.00\n"
                            "M-100003,\"Sunday, 2026_03_17 10:30:00+05:30\",310.00\n"
                            "M-100004,2026_03_18T08:00:00+0500,410.00\n"
                            "M-100005,2026_03_19 10:30:00,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-17")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            self.assertEqual(rows[4]["service_date"], "2026-03-19")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_timezone_suffixed_underscore_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_02_30 10:00:00Z,120.50\n"
                            "M-100002,2026_03_15 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_fractional_second_underscore_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15 10:30:00.123Z,120.50\n"
                            "M-100002,2026_03_16T09:00:00.5-04:00,200.00\n"
                            "M-100003,\"Sunday, 2026_03_17 10:30:00.123456+05:30\",310.00\n"
                            "M-100004,2026_03_18 10:30:00.999,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-17")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_fractional_second_underscore_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_02_30 10:00:00.123Z,120.50\n"
                            "M-100002,2026_03_15 10:30:00.123+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_timezone_suffixed_numeric_hyphen_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026 10:30:00Z,120.50\n"
                            "M-100002,15-03-2026T09:00:00-04:00,200.00\n"
                            "M-100003,\"Sunday, 03-16-2026 10:30:00+05:30\",310.00\n"
                            "M-100004,03-18-2026T08:00:00+0500,410.00\n"
                            "M-100005,03-19-2026 10:30:00,510.00\n"
                            "M-100006,03-04-2026 10:30:00Z,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            self.assertEqual(rows[4]["service_date"], "2026-03-19")
            # The US form keeps priority: an ambiguous hyphen
            # datetime still reads as MM-DD-YYYY.
            self.assertEqual(rows[5]["service_date"], "2026-03-04")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_timezone_suffixed_numeric_hyphen_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02-30-2026 10:00:00Z,120.50\n"
                            "M-100002,03-15-2026 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_fractional_second_numeric_hyphen_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026 10:30:00.123Z,120.50\n"
                            "M-100002,15-03-2026T09:00:00.5-04:00,200.00\n"
                            "M-100003,\"Sunday, 03-16-2026 10:30:00.123456+05:30\",310.00\n"
                            "M-100004,03-18-2026 10:30:00.999,410.00\n"
                            "M-100005,03-04-2026T08:00:00.25Z,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            # The US form keeps priority: an ambiguous hyphen
            # datetime still reads as MM-DD-YYYY.
            self.assertEqual(rows[4]["service_date"], "2026-03-04")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_fractional_second_numeric_hyphen_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02-30-2026 10:00:00.123Z,120.50\n"
                            "M-100002,03-15-2026 10:30:00.123+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_fractional_second_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026 10:30:00.123Z\",120.50\n"
                            "M-100002,15 Mar 2026T09:00:00.5-04:00,200.00\n"
                            "M-100003,\"Sunday, March 16, 2026 10:30:00.123456+05:30\",310.00\n"
                            "M-100004,\"Mar 18, 2026 10:30:00.999\",410.00\n"
                            "M-100005,15-Mar-2026 08:00:00.25Z,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_fractional_second_month_name_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026 10:00:00.123Z\",120.50\n"
                            "M-100002,\"Mar 15, 2026 10:30:00.123+99:99\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_t_separated_hyphenated_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15-Mar-2026T09:00:00,120.50\n"
                            "M-100002,Mar-15-2026T09:00:00Z,200.00\n"
                            "M-100003,15-Mar-2026T09:00:00.5-04:00,310.00\n"
                            "M-100004,Mar-15-2026T10:30:00.123456+05:30,410.00\n"
                            "M-100005,\"Sunday, 16-Mar-2026T09:00:00.123Z\",510.00\n"
                            "M-100006,March-15-2026T09:00:00,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_t_separated_hyphenated_month_name_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,30-Feb-2026T10:00:00.123Z,120.50\n"
                            "M-100002,Mar-15-2026T10:30:00.123+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026 10:30:00 AM\",120.50\n"
                            "M-100002,\"15 Mar 2026 02:30 PM\",200.00\n"
                            "M-100003,\"March 15, 2026 10:30:00.123 AM\",310.00\n"
                            "M-100004,\"Sunday, Mar 16, 2026 09:00:00 pm\",410.00\n"
                            "M-100005,15-Mar-2026 10:30:00 AM,510.00\n"
                            "M-100006,\"Mar 15th, 2026 2:30pm\",610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_month_name_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026 10:00:00 AM\",120.50\n"
                            "M-100002,\"Mar 15, 2026 10:30:00 XM\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_tz_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026 10:30:00 AM Z\",120.50\n"
                            "M-100002,\"15 Mar 2026T09:00:00 PM -04:00\",200.00\n"
                            "M-100003,\"Mar 15, 2026 10:30:00.123 AM +05:30\",310.00\n"
                            "M-100004,\"Sunday, Mar 16, 2026 10:30:00 am +05:30\",410.00\n"
                            "M-100005,\"Mar 15, 2026 10:30:00Z AM\",510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_tz_month_name_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026 10:00:00 AM Z\",120.50\n"
                            "M-100002,\"Mar 15, 2026 10:30:00 AM +99:99\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_two_digit_year_slash_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/26,120.50\n"
                            "M-100002,15/03/26,200.00\n"
                            "M-100003,03/15/26 10:30:00,310.00\n"
                            "M-100004,15/03/26T09:00:00.5-04:00,410.00\n"
                            "M-100005,\"Sunday, 03/16/26 10:30:00 am +05:30\",510.00\n"
                            "M-100006,03/15/99,610.00\n"
                            "M-100007,26/03/15,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            # The %y pivot reads 69-99 as 1969-1999.
            self.assertEqual(rows[5]["service_date"], "1999-03-15")
            # A leading component above 12 reads day-first under
            # the standing US-first order, so 26/03/15 is
            # 26 Mar 2015 — there is no separate year-first
            # two-digit form.
            self.assertEqual(rows[6]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_slash_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02/30/26,120.50\n"
                            "M-100002,03/15/26 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_two_digit_year_dot_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03.15.26,120.50\n"
                            "M-100002,15.03.26,200.00\n"
                            "M-100003,03.15.26 10:30:00,310.00\n"
                            "M-100004,15.03.26T09:00:00.5-04:00,410.00\n"
                            "M-100005,\"Sunday, 03.16.26 10:30:00 am +05:30\",510.00\n"
                            "M-100006,03.15.99,610.00\n"
                            "M-100007,26.03.15,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            # The %y pivot reads 69-99 as 1969-1999.
            self.assertEqual(rows[5]["service_date"], "1999-03-15")
            # A leading component above 12 reads day-first under
            # the standing US-first order, so 26.03.15 is
            # 26 Mar 2015 — there is no separate year-first
            # two-digit form.
            self.assertEqual(rows[6]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_dot_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02.30.26,120.50\n"
                            "M-100002,03.15.26 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_four_digit_year_dot_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03.15.2026,120.50\n"
                            "M-100002,15.03.2026,200.00\n"
                            "M-100003,03.15.2026 10:30:00,310.00\n"
                            "M-100004,15.03.2026T09:00:00.5-04:00,410.00\n"
                            "M-100005,\"Sunday, 03.16.2026 10:30:00 am +05:30\",510.00\n"
                            "M-100006,03.15.1999,610.00\n"
                            "M-100007,26.03.2015,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            self.assertEqual(rows[5]["service_date"], "1999-03-15")
            # A leading component above 12 reads day-first under
            # the standing US-first order, so 26.03.2015 is
            # 26 Mar 2015 — there is no separate year-first
            # four-digit form.
            self.assertEqual(rows[6]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_four_digit_year_dot_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02.30.2026,120.50\n"
                            "M-100002,03.15.2026 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_four_digit_year_underscore_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03_15_2026,120.50\n"
                            "M-100002,15_03_2026,200.00\n"
                            "M-100003,03_15_2026 10:30:00,310.00\n"
                            "M-100004,15_03_2026T09:00:00.5-04:00,410.00\n"
                            "M-100005,\"Sunday, 03_16_2026 10:30:00 am +05:30\",510.00\n"
                            "M-100006,03_15_1999,610.00\n"
                            "M-100007,26_03_2015,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            self.assertEqual(rows[5]["service_date"], "1999-03-15")
            # A leading component above 12 reads day-first under
            # the standing US-first order, so 26_03_2015 is
            # 26 Mar 2015 — there is no separate year-first
            # four-digit form.
            self.assertEqual(rows[6]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_four_digit_year_underscore_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02_30_2026,120.50\n"
                            "M-100002,03_15_2026 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_four_digit_year_compact_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03152026,120.50\n"
                            "M-100002,15032026,200.00\n"
                            "M-100003,03152026 10:30:00,310.00\n"
                            "M-100004,15032026T09:00:00.5-04:00,410.00\n"
                            "M-100005,\"Sunday, 03162026 10:30:00 am +05:30\",510.00\n"
                            "M-100006,03151999,610.00\n"
                            "M-100007,26032015,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            self.assertEqual(rows[5]["service_date"], "1999-03-15")
            # A leading component above 12 reads day-first under
            # the standing US-first order, so 26032015 is
            # 26 Mar 2015 — there is no separate year-first
            # four-digit form.
            self.assertEqual(rows[6]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_four_digit_year_compact_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02302026,120.50\n"
                            "M-100002,03152026 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_zero_pads_sub_thousand_year_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,01120315,120.50\n"
                            "M-100002,03150112,200.00\n"
                            "M-100003,0112/03/15,310.00\n"
                            "M-100004,03/15/0112,410.00\n"
                            "M-100005,0112.03.15,510.00\n"
                            "M-100006,03_15_0112,610.00\n"
                            "M-100007,0112-03-15 10:30:00,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "0112-03-15")
            # "03150112" is ambiguous: the year-first compact
            # reading (0315-01-12) is a real date and keeps
            # priority over the non-year-first reading, so the
            # short year is the 0315 one, padded back to four
            # digits the same way.
            self.assertEqual(rows[1]["service_date"], "0315-01-12")
            self.assertEqual(rows[2]["service_date"], "0112-03-15")
            self.assertEqual(rows[3]["service_date"], "0112-03-15")
            self.assertEqual(rows[4]["service_date"], "0112-03-15")
            self.assertEqual(rows[5]["service_date"], "0112-03-15")
            self.assertEqual(rows[6]["service_date"], "0112-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_sub_thousand_year_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,0112-02-30,120.50\n"
                            "M-100002,02/30/0112,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_two_digit_year_hyphen_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-26,120.50\n"
                            "M-100002,15-03-26,200.00\n"
                            "M-100003,03-15-26 10:30:00,310.00\n"
                            "M-100004,15-03-26T09:00:00.5-04:00,410.00\n"
                            "M-100005,\"Sunday, 03-16-26 10:30:00 am +05:30\",510.00\n"
                            "M-100006,03-15-99,610.00\n"
                            "M-100007,26-03-15,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            # The %y pivot reads 69-99 as 1969-1999.
            self.assertEqual(rows[5]["service_date"], "1999-03-15")
            # A leading component above 12 reads day-first under
            # the standing US-first order, so 26-03-15 is
            # 26 Mar 2015 — there is no separate year-first
            # two-digit form.
            self.assertEqual(rows[6]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_hyphen_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02-30-26,120.50\n"
                            "M-100002,03-15-26 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_two_digit_year_underscore_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03_15_26,120.50\n"
                            "M-100002,15_03_26,200.00\n"
                            "M-100003,03_15_26 10:30:00,310.00\n"
                            "M-100004,15_03_26T09:00:00.5-04:00,410.00\n"
                            "M-100005,\"Sunday, 03_16_26 10:30:00 am +05:30\",510.00\n"
                            "M-100006,03_15_99,610.00\n"
                            "M-100007,26_03_15,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            # The %y pivot reads 69-99 as 1969-1999.
            self.assertEqual(rows[5]["service_date"], "1999-03-15")
            # A leading component above 12 reads day-first under
            # the standing US-first order, so 26_03_15 is
            # 26 Mar 2015 — there is no separate year-first
            # two-digit form.
            self.assertEqual(rows[6]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_underscore_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02_30_26,120.50\n"
                            "M-100002,03_15_26 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_two_digit_year_month_name_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 26\",120.50\n"
                            "M-100002,15 Mar 26,200.00\n"
                            "M-100003,15-Mar-26,310.00\n"
                            "M-100004,Mar-15-26 10:30:00,410.00\n"
                            "M-100005,\"Sunday, March 16, 26 10:30:00 am +05:30\",510.00\n"
                            "M-100006,\"Mar 15, 99\",610.00\n"
                            "M-100007,\"March 15th, 26\",710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            # The %y pivot reads 69-99 as 1969-1999.
            self.assertEqual(rows[5]["service_date"], "1999-03-15")
            # The ordinal suffix is stripped before parsing.
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_month_name_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 26\",120.50\n"
                            "M-100002,\"Mar 15, 26 10:30:00+99:99\",200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_two_digit_year_compact_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,031526,120.50\n"
                            "M-100002,150326,200.00\n"
                            "M-100003,260315,310.00\n"
                            "M-100004,031526 10:30:00Z,410.00\n"
                            "M-100005,\"Sunday, 031626 10:30:00 am +05:30\",510.00\n"
                            "M-100006,031599,610.00\n"
                            "M-100007,031526 10:30:00.123Z,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            # A leading component above 12 reads day-first.
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2015-03-26")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            # The %y pivot reads 69-99 as 1969-1999.
            self.assertEqual(rows[5]["service_date"], "1999-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_compact_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,023026,120.50\n"
                            "M-100002,031526 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_space_separated_tz_two_digit_year_compact(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,031526 10:30:00 +05:00,120.50\n"
                            "M-100002,031526 10:30:00 -0400,200.00\n"
                            "M-100003,031526 10:30:00 Z,310.00\n"
                            "M-100004,150326 10:30:00 +05:00,410.00\n"
                            "M-100005,031526 10:30:00.123 +05:30,510.00\n"
                            "M-100006,031526T10:30:00 +05:00,610.00\n"
                            "M-100007,\"Sunday, 031626 10:30:00 +05:30\",710.00\n"
                            "M-100008,031526 10:30:00 +05:00 AM,810.00\n"
                            "M-100009,031526 10:30 +05:00,910.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 9)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            # A leading component above 12 reads day-first.
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-16")
            # The suffix before the marker governs too.
            self.assertEqual(rows[7]["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 9)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_tz_two_digit_year_compact(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,023026 10:30:00 +05:00,120.50\n"
                            "M-100002,031526 10:30:00 +99:99,200.00\n"
                            "M-100003,031526 10:30:00 +25:00,310.00\n"
                            "M-100004,\"Funday, 031526 10:30:00 +05:00\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 4)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 4})

    def test_read_claims_csv_normalizes_plain_two_digit_year_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,260315 10:30:00,120.50\n"
                            "M-100002,031526 10:30:00,200.00\n"
                            "M-100003,031526T09:00:00,310.00\n"
                            "M-100004,031526 10:30,410.00\n"
                            "M-100005,\"Sunday, 031626 10:30:00\",510.00\n"
                            "M-100006,031526T09:00,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            # A leading component above 12 reads day-first.
            self.assertEqual(rows[0]["service_date"], "2015-03-26")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_plain_two_digit_year_compact_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,023026 10:00:00,120.50\n"
                            "M-100002,031526 10:30:00 XYZ,200.00\n"
                            "M-100003,\"Funday, 031526 10:30:00\",310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 3)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 3)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 3})

    def test_read_claims_csv_normalizes_epoch_timestamps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,1710460800,120.50\n"
                            "M-100002,1710460800000,200.00\n"
                            "M-100003,1710500000,310.00\n"
                            "M-100004,946684800,410.00\n"
                            "M-100005,4102444800000,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2024-03-15")
            self.assertEqual(rows[1]["service_date"], "2024-03-15")
            # A non-midnight epoch still governs as its UTC date.
            self.assertEqual(rows[2]["service_date"], "2024-03-15")
            # Range bounds are inclusive: 2000-01-01 and 2100-01-01.
            self.assertEqual(rows[3]["service_date"], "2000-01-01")
            self.assertEqual(rows[4]["service_date"], "2100-01-01")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_normalizes_microsecond_epoch_timestamps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,1710460800000000,120.50\n"
                            "M-100002,1710500000000000,200.00\n"
                            "M-100003,946684800000000,310.00\n"
                            "M-100004,4102444800000000,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2024-03-15")
            # A non-midnight epoch still governs as its UTC date.
            self.assertEqual(rows[1]["service_date"], "2024-03-15")
            # Range bounds are inclusive: 2000-01-01 and 2100-01-01.
            # The lower bound is fifteen digits, the upper sixteen.
            self.assertEqual(rows[2]["service_date"], "2000-01-01")
            self.assertEqual(rows[3]["service_date"], "2100-01-01")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_microsecond_epoch_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,9999999999999999,120.50\n"
                            "M-100002,171046080000000,200.00\n"
                            "M-100003,12345678901234,310.00\n"
                            "M-100004,17104608000000000,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 4)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 4})

    def test_read_claims_csv_normalizes_nanosecond_epoch_timestamps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,1710460800000000000,120.50\n"
                            "M-100002,1710500000000000000,200.00\n"
                            "M-100003,946684800000000000,310.00\n"
                            "M-100004,4102444800000000000,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["service_date"], "2024-03-15")
            # A non-midnight epoch still governs as its UTC date.
            self.assertEqual(rows[1]["service_date"], "2024-03-15")
            # Range bounds are inclusive: 2000-01-01 and 2100-01-01.
            # The lower bound is eighteen digits, the upper nineteen.
            self.assertEqual(rows[2]["service_date"], "2000-01-01")
            self.assertEqual(rows[3]["service_date"], "2100-01-01")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 4)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_nanosecond_epoch_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,9999999999999999999,120.50\n"
                            "M-100002,171046080000000000,200.00\n"
                            "M-100003,123456789012345678,310.00\n"
                            "M-100004,17104608000000000000,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 4)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 4})

    def test_read_claims_csv_normalizes_fractional_epoch_timestamps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,1710460800.5,120.50\n"
                            "M-100002,1710460800000.25,200.00\n"
                            "M-100003,1710500000.999,310.00\n"
                            "M-100004,1710460800000000.5,410.00\n"
                            "M-100005,1710460800000000000.5,510.00\n"
                            "M-100006,946684800.0,610.00\n"
                            "M-100007,4102444800000.999,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2024-03-15")
            self.assertEqual(rows[1]["service_date"], "2024-03-15")
            # A non-midnight fractional epoch still governs as its
            # UTC date; the sub-second part never shifts the date.
            self.assertEqual(rows[2]["service_date"], "2024-03-15")
            self.assertEqual(rows[3]["service_date"], "2024-03-15")
            self.assertEqual(rows[4]["service_date"], "2024-03-15")
            # Range bounds are inclusive: 2000-01-01 and 2100-01-01.
            self.assertEqual(rows[5]["service_date"], "2000-01-01")
            self.assertEqual(rows[6]["service_date"], "2100-01-01")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_fractional_epoch_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,710460800.5,120.50\n"
                            "M-100002,9999999999999999999.5,200.00\n"
                            "M-100003,17104608000.5,310.00\n"
                            "M-100004,17104608000000.5,410.00\n"
                            "M-100005,17104608000000000.5,510.00\n"
                            "M-100006,1710460800.,610.00\n"
                            "M-100007,1710460800.5x,710.00\n"
                            "M-100008,.5,810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_read_claims_csv_normalizes_ordinal_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026074,120.50\n"
                            "M-100002,2026-074,200.00\n"
                            "M-100003,2024366,310.00\n"
                            "M-100004,\"Sunday, 2026075\",410.00\n"
                            "M-100005,2026074 10:30:00Z,510.00\n"
                            "M-100006,2026-074T09:00:00-04:00,610.00\n"
                            "M-100007,2026074 10:30:00 AM,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            # Day 366 exists in leap year 2024: Dec 31.
            self.assertEqual(rows[2]["service_date"], "2024-12-31")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ordinal_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026366,120.50\n"
                            "M-100002,2026-366,200.00\n"
                            "M-100003,2026000,310.00\n"
                            "M-100004,2026367,410.00\n"
                            "M-100005,\"Funday, 2026074\",510.00\n"
                            "M-100006,2026074 10:30:00+99:99,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_space_separated_tz_ordinal_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026074 10:30:00 +05:00,120.50\n"
                            "M-100002,2026-074 10:30:00 -0400,200.00\n"
                            "M-100003,2026074 10:30:00 Z,310.00\n"
                            "M-100004,\"Sunday, 2026075 10:30:00 +05:30\",410.00\n"
                            "M-100005,2026074 10:30:00.123 +05:00,510.00\n"
                            "M-100006,2026074 10:30 +05:00,610.00\n"
                            "M-100007,2026074 10:30:00 +05:00 AM,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_tz_ordinal_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026366 10:30:00 +05:00,120.50\n"
                            "M-100002,2026074 10:30:00 +25:00,200.00\n"
                            "M-100003,2026074 10:30:00 +99:99,310.00\n"
                            "M-100004,2026074 10:30:00 +05:60,410.00\n"
                            "M-100005,\"Funday, 2026074 10:30:00 +05:00\",510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_named_zone_iso_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15 10:30:00 GMT,120.50\n"
                            "M-100002,2026-03-15T09:00:00 EST,200.00\n"
                            "M-100003,\"Sunday, 2026-03-15 10:30:00 GMT\",310.00\n"
                            "M-100004,2026-03-15 10:30:00.123 GMT,410.00\n"
                            "M-100005,2026-03-15 10:30 UTC,510.00\n"
                            "M-100006,2026-03-15 10:30:00 AM GMT,610.00\n"
                            "M-100007,2026-03-15 10:30:00 GMT AM,710.00\n"
                            "M-100008,2026-03-15 10:30:00 utc,810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 8)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_named_zone_iso_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15 10:30:00 XYZ,120.50\n"
                            "M-100002,2026-02-30 10:00:00 GMT,200.00\n"
                            "M-100003,\"Funday, 2026-03-15 10:30:00 GMT\",310.00\n"
                            "M-100004,2026-03-15 10:30:00 AM XYZ,410.00\n"
                            "M-100005,2026-03-15 10:30:00 WEST,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_named_zone_slash_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00 GMT,120.50\n"
                            "M-100002,03/15/2026T09:00:00 EST,200.00\n"
                            "M-100003,\"Sunday, 03/15/2026 10:30:00 GMT\",310.00\n"
                            "M-100004,03/15/2026 10:30:00.123 GMT,410.00\n"
                            "M-100005,03/15/2026 10:30 GMT,510.00\n"
                            "M-100006,03/15/2026 10:30:00 AM GMT,610.00\n"
                            "M-100007,03/15/2026 10:30:00 GMT AM,710.00\n"
                            "M-100008,03/15/2026 10:30:00 utc,810.00\n"
                            "M-100009,15/03/2026 10:30:00 GMT,910.00\n"
                            "M-100010,2026/03/15 10:30:00 EST,1010.00\n"
                            "M-100011,03/15/26 10:30:00 GMT,1110.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 11)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 11)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_named_zone_slash_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00 XYZ,120.50\n"
                            "M-100002,02/30/2026 10:00:00 GMT,200.00\n"
                            "M-100003,\"Funday, 03/15/2026 10:30:00 GMT\",310.00\n"
                            "M-100004,03/15/2026 10:30:00 AM XYZ,410.00\n"
                            "M-100005,03/15/2026 10:30:00 WEST,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_named_zone_dot_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15 10:30:00 GMT,120.50\n"
                            "M-100002,2026.03.15T09:00:00 EST,200.00\n"
                            "M-100003,\"Sunday, 2026.03.15 10:30:00 GMT\",310.00\n"
                            "M-100004,2026.03.15 10:30:00.123 GMT,410.00\n"
                            "M-100005,2026.03.15 10:30 GMT,510.00\n"
                            "M-100006,2026.03.15 10:30:00 AM GMT,610.00\n"
                            "M-100007,2026.03.15 10:30:00 GMT AM,710.00\n"
                            "M-100008,2026.03.15 10:30:00 utc,810.00\n"
                            "M-100009,03.15.26 10:30:00 GMT,910.00\n"
                            "M-100010,2026.03.15 10:30:00 PST,1010.00\n"
                            "M-100011,15.03.26 10:30:00 GMT,1110.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 11)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 11)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_named_zone_dot_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15 10:30:00 XYZ,120.50\n"
                            "M-100002,2026.02.30 10:00:00 GMT,200.00\n"
                            "M-100003,\"Funday, 2026.03.15 10:30:00 GMT\",310.00\n"
                            "M-100004,2026.03.15 10:30:00 AM XYZ,410.00\n"
                            "M-100005,2026.03.15 10:30:00 WEST,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_named_zone_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 10:30:00 GMT,120.50\n"
                            "M-100002,20260315T09:00:00 EST,200.00\n"
                            "M-100003,\"Sunday, 20260315 10:30:00 GMT\",310.00\n"
                            "M-100004,20260315 10:30:00.123 GMT,410.00\n"
                            "M-100005,20260315 10:30 GMT,510.00\n"
                            "M-100006,20260315 10:30:00 AM GMT,610.00\n"
                            "M-100007,20260315 10:30:00 GMT AM,710.00\n"
                            "M-100008,20260315 10:30:00 utc,810.00\n"
                            "M-100009,20260315T09:00:00 PDT,910.00\n"
                            "M-100010,20260315 10:30:00 PST,1010.00\n"
                            "M-100011,20260315 10:30:00 CST,1110.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 11)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 11)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_named_zone_compact_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 10:30:00 XYZ,120.50\n"
                            "M-100002,20260230 10:00:00 GMT,200.00\n"
                            "M-100003,\"Funday, 20260315 10:30:00 GMT\",310.00\n"
                            "M-100004,20260315 10:30:00 AM XYZ,410.00\n"
                            "M-100005,20260315 10:30:00 WEST,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_named_zone_two_digit_year_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,031526 10:30:00 GMT,120.50\n"
                            "M-100002,031526T09:00:00 EST,200.00\n"
                            "M-100003,\"Sunday, 031526 10:30:00 GMT\",310.00\n"
                            "M-100004,031526 10:30:00.123 GMT,410.00\n"
                            "M-100005,031526 10:30 GMT,510.00\n"
                            "M-100006,031526 10:30:00 AM GMT,610.00\n"
                            "M-100007,031526 10:30:00 GMT AM,710.00\n"
                            "M-100008,031526 10:30:00 utc,810.00\n"
                            "M-100009,031526T09:00:00 PDT,910.00\n"
                            "M-100010,031526 10:30:00 PST,1010.00\n"
                            "M-100011,150326 10:30:00 GMT,1110.00\n"
                            "M-100012,031599 10:30:00 GMT,1210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 12)
            for row in rows[:11]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[11]["service_date"], "1999-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 12)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_named_zone_two_digit_year_compact_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,031526 10:30:00 XYZ,120.50\n"
                            "M-100002,023026 10:00:00 GMT,200.00\n"
                            "M-100003,\"Funday, 031526 10:30:00 GMT\",310.00\n"
                            "M-100004,031526 10:30:00 AM XYZ,410.00\n"
                            "M-100005,031526 10:30:00 WEST,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_named_zone_ordinal_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026074 10:30:00 GMT,120.50\n"
                            "M-100002,2026-074T09:00:00 EST,200.00\n"
                            "M-100003,\"Sunday, 2026075 10:30:00 GMT\",310.00\n"
                            "M-100004,2026074 10:30:00.123 GMT,410.00\n"
                            "M-100005,2026074 10:30 GMT,510.00\n"
                            "M-100006,2026074 10:30:00 AM GMT,610.00\n"
                            "M-100007,2026074 10:30:00 GMT AM,710.00\n"
                            "M-100008,2026074 10:30:00 utc,810.00\n"
                            "M-100009,2026-074T09:00:00 PDT,910.00\n"
                            "M-100010,2026074 10:30:00 PST,1010.00\n"
                            "M-100011,2026075 10:30:00 GMT,1110.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 11)
            for row in rows:
                self.assertIn(row["service_date"],
                              ("2026-03-15", "2026-03-16"))
            # Day 074 of 2026 is March 15; day 075 is March 16.
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[10]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 11)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_named_zone_ordinal_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026074 10:30:00 XYZ,120.50\n"
                            "M-100002,2026366 10:00:00 GMT,200.00\n"
                            "M-100003,\"Funday, 2026074 10:30:00 GMT\",310.00\n"
                            "M-100004,2026074 10:30:00 AM XYZ,410.00\n"
                            "M-100005,2026074 10:30:00 WEST,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_named_zone_underscore_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15 10:30:00 GMT,120.50\n"
                            "M-100002,2026_03_15T09:00:00 EST,200.00\n"
                            "M-100003,\"Sunday, 2026_03_15 10:30:00 GMT\",310.00\n"
                            "M-100004,2026_03_15 10:30:00.123 GMT,410.00\n"
                            "M-100005,2026_03_15 10:30 GMT,510.00\n"
                            "M-100006,2026_03_15 10:30:00 AM GMT,610.00\n"
                            "M-100007,2026_03_15 10:30:00 GMT AM,710.00\n"
                            "M-100008,2026_03_15 10:30:00 utc,810.00\n"
                            "M-100009,03_15_26 10:30:00 GMT,910.00\n"
                            "M-100010,2026_03_15 10:30:00 PST,1010.00\n"
                            "M-100011,15_03_26 10:30:00 GMT,1110.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 11)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 11)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_named_zone_underscore_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15 10:30:00 XYZ,120.50\n"
                            "M-100002,2026_02_30 10:00:00 GMT,200.00\n"
                            "M-100003,\"Funday, 2026_03_15 10:30:00 GMT\",310.00\n"
                            "M-100004,2026_03_15 10:30:00 AM XYZ,410.00\n"
                            "M-100005,2026_03_15 10:30:00 WEST,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_named_zone_hyphen_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026 10:30:00 GMT,120.50\n"
                            "M-100002,03-15-2026T09:00:00 EST,200.00\n"
                            "M-100003,\"Sunday, 03-15-2026 10:30:00 GMT\",310.00\n"
                            "M-100004,03-15-2026 10:30:00.123 GMT,410.00\n"
                            "M-100005,03-15-2026 10:30 GMT,510.00\n"
                            "M-100006,03-15-2026 10:30:00 AM GMT,610.00\n"
                            "M-100007,03-15-2026 10:30:00 GMT AM,710.00\n"
                            "M-100008,03-15-2026 10:30:00 utc,810.00\n"
                            "M-100009,15-03-2026 10:30:00 PST,910.00\n"
                            "M-100010,03-15-26 10:30:00 GMT,1010.00\n"
                            "M-100011,15-03-26 10:30:00 GMT,1110.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 11)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 11)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_named_zone_hyphen_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026 10:30:00 XYZ,120.50\n"
                            "M-100002,02-30-2026 10:00:00 GMT,200.00\n"
                            "M-100003,\"Funday, 03-15-2026 10:30:00 GMT\",310.00\n"
                            "M-100004,03-15-2026 10:30:00 AM XYZ,410.00\n"
                            "M-100005,03-15-2026 10:30:00 WEST,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_iso_week_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-W11-1,120.50\n"
                            "M-100002,2026W111,200.00\n"
                            "M-100003,2026-W11,310.00\n"
                            "M-100004,\"Sunday, 2026-W11-2\",410.00\n"
                            "M-100005,2026-W11-1 10:30:00Z,510.00\n"
                            "M-100006,2026-W11-1T09:00:00.123-04:00,610.00\n"
                            "M-100007,2026-W11-3 10:30:00,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-09")
            self.assertEqual(rows[1]["service_date"], "2026-03-09")
            # Week alone is its Monday.
            self.assertEqual(rows[2]["service_date"], "2026-03-09")
            # Weekday label is a label, not the date: W11-2 is Tuesday.
            self.assertEqual(rows[3]["service_date"], "2026-03-10")
            self.assertEqual(rows[4]["service_date"], "2026-03-09")
            self.assertEqual(rows[5]["service_date"], "2026-03-09")
            self.assertEqual(rows[6]["service_date"], "2026-03-11")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_iso_week_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2025-W53-1,120.50\n"
                            "M-100002,2026-W00-1,200.00\n"
                            "M-100003,2026-W11-8,310.00\n"
                            "M-100004,2026-W54-1,410.00\n"
                            "M-100005,\"Funday, 2026-W11-1\",510.00\n"
                            "M-100006,2026-W11-1 10:30:00+99:99,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_space_separated_tz_week_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-W11-1 10:30:00 +05:00,120.50\n"
                            "M-100002,2026-W11-1 10:30:00 -0400,200.00\n"
                            "M-100003,2026-W11-1 10:30:00 Z,310.00\n"
                            "M-100004,\"Sunday, 2026-W11-2 10:30:00 +05:30\",410.00\n"
                            "M-100005,2026W111T09:00:00.123 +05:00,510.00\n"
                            "M-100006,2026-W11-3 10:30 +05:00,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["service_date"], "2026-03-09")
            self.assertEqual(rows[1]["service_date"], "2026-03-09")
            self.assertEqual(rows[2]["service_date"], "2026-03-09")
            # Weekday label is a label, not the date: W11-2 is Tuesday.
            self.assertEqual(rows[3]["service_date"], "2026-03-10")
            self.assertEqual(rows[4]["service_date"], "2026-03-09")
            self.assertEqual(rows[5]["service_date"], "2026-03-11")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_tz_week_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2025-W53-1 10:30:00 +05:00,120.50\n"
                            "M-100002,2026-W11-1 10:30:00 +25:00,200.00\n"
                            "M-100003,2026-W11-1 10:30:00 +99:99,310.00\n"
                            "M-100004,2026-W11-1 10:30:00 +05:60,410.00\n"
                            "M-100005,\"Funday, 2026-W11-1 10:30:00 +05:00\",510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_named_zone_week_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-W11-1 10:30:00 GMT,120.50\n"
                            "M-100002,2026-W11-1T09:00:00 EST,200.00\n"
                            "M-100003,2026-W11-1 10:30:00.123 UTC,310.00\n"
                            "M-100004,\"Sunday, 2026-W11-2 10:30:00 GMT\",410.00\n"
                            "M-100005,2026W111 10:30:00 GMT,510.00\n"
                            "M-100006,2026-W11-1 10:30 GMT,610.00\n"
                            "M-100007,2026-W11-1 10:30:00 utc,710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["service_date"], "2026-03-09")
            self.assertEqual(rows[1]["service_date"], "2026-03-09")
            self.assertEqual(rows[2]["service_date"], "2026-03-09")
            # Weekday label is a label, not the date: W11-2 is Tuesday.
            self.assertEqual(rows[3]["service_date"], "2026-03-10")
            self.assertEqual(rows[4]["service_date"], "2026-03-09")
            self.assertEqual(rows[5]["service_date"], "2026-03-09")
            self.assertEqual(rows[6]["service_date"], "2026-03-09")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 7)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_named_zone_week_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-W11-1 10:30:00 XYZ,120.50\n"
                            "M-100002,2026-W11-1 10:30:00 WEST,200.00\n"
                            "M-100003,2025-W53-1 10:00:00 GMT,310.00\n"
                            "M-100004,2026-W11-8 10:30:00 GMT,410.00\n"
                            "M-100005,\"Funday, 2026-W11-1 10:30:00 GMT\",510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_ampm_week_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-W11-1 10:30:00 AM,120.50\n"
                            "M-100002,2026-W11-1T09:00:00 PM,200.00\n"
                            "M-100003,2026-W11-1 10:30:00.123 am,310.00\n"
                            "M-100004,\"Sunday, 2026-W11-2 09:00:00 pm\",410.00\n"
                            "M-100005,2026W111 10:30:00 AM,510.00\n"
                            "M-100006,2026-W11-1 10:30 AM,610.00\n"
                            "M-100007,2026-W11-1 10:30:00 PM GMT,710.00\n"
                            "M-100008,2026-W11-1T09:00:00 AM EST,810.00\n"
                            "M-100009,2026-W11-1 10:30:00Z AM,910.00\n"
                            "M-100010,2026-W11-1 10:30:00+05:30 PM,1010.00\n"
                            "M-100011,\"Sunday, 2026-W11-2 10:30:00 AM +05:30\",1110.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 11)
            self.assertEqual(rows[0]["service_date"], "2026-03-09")
            self.assertEqual(rows[1]["service_date"], "2026-03-09")
            self.assertEqual(rows[2]["service_date"], "2026-03-09")
            # Weekday label is a label, not the date: W11-2 is Tuesday.
            self.assertEqual(rows[3]["service_date"], "2026-03-10")
            self.assertEqual(rows[4]["service_date"], "2026-03-09")
            self.assertEqual(rows[5]["service_date"], "2026-03-09")
            self.assertEqual(rows[6]["service_date"], "2026-03-09")
            self.assertEqual(rows[7]["service_date"], "2026-03-09")
            self.assertEqual(rows[8]["service_date"], "2026-03-09")
            self.assertEqual(rows[9]["service_date"], "2026-03-09")
            self.assertEqual(rows[10]["service_date"], "2026-03-10")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 11)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_week_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-W11-1 10:30:00 XM,120.50\n"
                            "M-100002,2026-W11-1 10:30:00 AM XYZ,200.00\n"
                            "M-100003,2026-W11-1 10:30:00 AM +99:99,310.00\n"
                            "M-100004,2025-W53-1 10:00:00 AM Z,410.00\n"
                            "M-100005,2026-W11-8 10:30:00 AM,510.00\n"
                            "M-100006,\"Funday, 2026-W11-1 10:30:00 AM\",610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_space_separated_tz_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "\"M-100001\",\"Mar 15, 2026 10:30:00 +05:00\",120.50\n"
                            "M-100002,15 Mar 2026 10:30:00 -0400,200.00\n"
                            "\"M-100003\",\"Sunday, 15 Mar 2026 10:30:00 GMT\",310.00\n"
                            "M-100004,15 Mar 2026 10:30:00 EST,410.00\n"
                            "\"M-100005\",\"Mar 15, 2026 10:30:00 UTC\",510.00\n"
                            "\"M-100006\",\"Mar 15, 2026 10:30:00 Z\",610.00\n"
                            "M-100007,15 Mar 2026 10:30:00.123 GMT,710.00\n"
                            "\"M-100008\",\"Mar 15, 2026 10:30:00 AM GMT\",810.00\n"
                            "M-100009,15-Mar-2026 10:30:00 PDT,910.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 9)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 9)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_tz_month_name_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15 Mar 2026 10:30:00 XYZ,120.50\n"
                            "\"M-100002\",\"Mar 15, 2026 10:30:00 +99:99\",200.00\n"
                            "\"M-100003\",\"Feb 30, 2026 10:00:00 GMT\",310.00\n"
                            "\"M-100004\",\"Mar 15, 2026 10:30:00 AM XYZ\",410.00\n"
                            "M-100005,15 Mar 2026 10:30:00GMT,510.00\n"
                            "\"M-100006\",\"Funday, 15 Mar 2026 10:30:00 GMT\",610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_space_separated_tz_slash_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00 +05:00,120.50\n"
                            "M-100002,03/15/2026 10:30:00 -0400,200.00\n"
                            "\"M-100003\",\"Sunday, 03/16/2026 10:30:00 Z\",310.00\n"
                            "M-100004,15/03/2026 10:30:00 +05:30,410.00\n"
                            "M-100005,03/15/2026 10:30:00.123 +05:00,510.00\n"
                            "\"M-100006\",\"03/15/2026 10:30:00 +05:00 AM\",610.00\n"
                            "M-100007,2026/03/15 10:30:00 Z,710.00\n"
                            "M-100008,03/15/26 10:30:00 +05:00,810.00\n"
                            "M-100009,03/15/2026T09:00:00 +05:00,910.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 9)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            self.assertEqual(rows[7]["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 9)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_tz_slash_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00 +99:99,120.50\n"
                            "M-100002,02/30/2026 10:00:00 +05:00,200.00\n"
                            "\"M-100003\",\"03/15/2026 10:30:00 +05:00 XM\",310.00\n"
                            "\"M-100004\",\"Funday, 03/15/2026 10:30:00 +05:00\",410.00\n"
                            "M-100005,03/15/2026 10:30:00 +25:00,510.00\n"
                            "M-100006,03/15/2026 10:30:00 +05:60,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_bad_epoch_timestamp_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,9999999999,120.50\n"
                            "M-100002,0000000000,200.00\n"
                            "M-100003,12345678901,310.00\n"
                            "M-100004,17104608000,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 4)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 4})

    def test_read_claims_csv_normalizes_fractional_second_slash_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00.123Z,120.50\n"
                            "M-100002,15/03/2026T09:00:00.5-04:00,200.00\n"
                            "M-100003,\"Sunday, 03/16/2026 10:30:00.123456+05:30\",310.00\n"
                            "M-100004,03/18/2026 10:30:00.999,410.00\n"
                            "M-100005,2026/03/15 08:00:00.25Z,510.00\n"
                            "M-100006,16/03/2026 10:30:00.123Z,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-16")
            self.assertEqual(rows[3]["service_date"], "2026-03-18")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_fractional_second_slash_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02/30/2026 10:00:00.123Z,120.50\n"
                            "M-100002,03/15/2026 10:30:00.123+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_slash_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00 AM,120.50\n"
                            "M-100002,15/03/2026 02:30 PM,200.00\n"
                            "M-100003,2026/03/15 10:30:00 AM,310.00\n"
                            "M-100004,03/15/2026 10:30:00.123 AM,410.00\n"
                            "M-100005,\"Sunday, 03/16/2026 09:00:00 pm\",510.00\n"
                            "M-100006,03/15/2026 2:30pm,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-16")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_slash_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02/30/2026 10:00:00 AM,120.50\n"
                            "M-100002,03/15/2026 10:30:00 XM,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_tz_slash_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00 AM Z,120.50\n"
                            "M-100002,03/15/2026T09:00:00 PM -04:00,200.00\n"
                            "M-100003,03/15/2026 10:30:00.123 AM +05:30,310.00\n"
                            "M-100004,\"Sunday, 03/16/2026 09:00:00 pm Z\",410.00\n"
                            "M-100005,15/03/2026 10:30:00 AM Z,510.00\n"
                            "M-100006,03/15/2026 10:30:00Z AM,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_tz_slash_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02/30/2026 10:00:00 AM Z,120.50\n"
                            "M-100002,03/15/2026 10:30:00 AM +99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_dot_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15 10:30:00 AM,120.50\n"
                            "M-100002,2026.03.15 10:30:00.123 AM,200.00\n"
                            "M-100003,2026.03.15T09:00:00 PM,310.00\n"
                            "M-100004,\"Sunday, 2026.03.16 09:00:00 pm\",410.00\n"
                            "M-100005,2026.03.15 2:30pm,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_dot_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.02.30 10:00:00 AM,120.50\n"
                            "M-100002,2026.03.15 10:30:00 XM,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_tz_dot_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15 10:30:00 AM Z,120.50\n"
                            "M-100002,2026.03.15T09:00:00 PM -04:00,200.00\n"
                            "M-100003,2026.03.15 10:30:00.123 AM +05:30,310.00\n"
                            "M-100004,\"Sunday, 2026.03.17 10:30:00 am +05:30\",410.00\n"
                            "M-100005,2026.03.15 10:30:00Z AM,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-17")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_tz_dot_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.02.30 10:00:00 AM Z,120.50\n"
                            "M-100002,2026.03.15 10:30:00 AM +99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 10:30:00 AM,120.50\n"
                            "M-100002,20260315 10:30:00.123 AM,200.00\n"
                            "M-100003,20260315T09:00:00 PM,310.00\n"
                            "M-100004,\"Sunday, 20260316 09:00:00 pm\",410.00\n"
                            "M-100005,20260315 2:30pm,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_compact_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230 10:00:00 AM,120.50\n"
                            "M-100002,20260315 10:30:00 XM,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_tz_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 10:30:00 AM Z,120.50\n"
                            "M-100002,20260315T09:00:00 PM -04:00,200.00\n"
                            "M-100003,20260315 10:30:00.123 AM +05:30,310.00\n"
                            "M-100004,\"Sunday, 20260316 10:30:00 am +05:30\",410.00\n"
                            "M-100005,20260315 10:30:00Z AM,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_tz_compact_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230 10:00:00 AM Z,120.50\n"
                            "M-100002,20260315 10:30:00 AM +99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_plain_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 10:30:00,120.50\n"
                            "M-100002,20260315T09:00:00,200.00\n"
                            "M-100003,20260315 10:30,310.00\n"
                            "M-100004,\"Sunday, 20260316 10:30:00\",410.00\n"
                            "M-100005,20260315T09:00,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_plain_compact_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230 10:00:00,120.50\n"
                            "M-100002,20260315 10:30:00 XYZ,200.00\n"
                            "M-100003,\"Funday, 20260315 10:30:00\",310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 3)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 3)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 3})

    def test_read_claims_csv_normalizes_basic_iso_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315T103000,120.50\n"
                            "M-100002,20260315T103000Z,200.00\n"
                            "M-100003,20260315T103000.123,310.00\n"
                            "M-100004,20260315T103000+05:30,410.00\n"
                            "M-100005,20260315T103000+0530,510.00\n"
                            "M-100006,20260315T103000 GMT,610.00\n"
                            "M-100007,20260315T1030,710.00\n"
                            "M-100008,20260315T1030Z,810.00\n"
                            "M-100009,\"Sunday, 20260316T103000\",910.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 9)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            self.assertEqual(rows[7]["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 9)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_basic_iso_compact_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230T103000,120.50\n"
                            "M-100002,20260315T256000,200.00\n"
                            "M-100003,20260315T103000+99:99,310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 3)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 3)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 3})

    def test_read_claims_csv_normalizes_space_separated_basic_iso_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315 103000,120.50\n"
                            "M-100002,20260315 103000Z,200.00\n"
                            "M-100003,20260315 103000.123,310.00\n"
                            "M-100004,20260315 103000+05:30,410.00\n"
                            "M-100005,20260315 103000+0530,510.00\n"
                            "M-100006,20260315 103000 GMT,610.00\n"
                            "M-100007,20260315 1030,710.00\n"
                            "M-100008,20260315 1030Z,810.00\n"
                            "M-100009,\"Sunday, 20260316 103000\",910.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 9)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-15")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-15")
            self.assertEqual(rows[7]["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 9)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_basic_iso_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230 103000,120.50\n"
                            "M-100002,20260315 256000,200.00\n"
                            "M-100003,20260315 103000+99:99,310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 3)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 3)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 3})

    def test_read_claims_csv_normalizes_two_digit_year_compact_basic_iso_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,031526T103000,120.50\n"
                            "M-100002,031526T1030,200.00\n"
                            "M-100003,031526T103000.123,310.00\n"
                            "M-100004,031526T103000Z,410.00\n"
                            "M-100005,031526T103000+05:30,510.00\n"
                            "M-100006,031526T103000 GMT,610.00\n"
                            "M-100007,\"Sunday, 031626T103000\",710.00\n"
                            "M-100008,031526 103000,810.00\n"
                            "M-100009,031526 1030,910.00\n"
                            "M-100010,031526 103000.123,1010.00\n"
                            "M-100011,031526 103000Z,1110.00\n"
                            "M-100012,031526T103000 AM,1210.00\n"
                            "M-100013,031526T103000 AM Z,1310.00\n"
                            "M-100014,031526T103000Z AM,1410.00\n"
                            "M-100015,150326T103000,1510.00\n"
                            "M-100016,031599T103000,1610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 16)
            for i in (0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14):
                self.assertEqual(rows[i]["service_date"], "2026-03-15")
            self.assertEqual(rows[6]["service_date"], "2026-03-16")
            self.assertEqual(rows[15]["service_date"], "1999-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 16)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_compact_basic_iso_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,023026T103000,120.50\n"
                            "M-100002,031526T256000,200.00\n"
                            "M-100003,031526T103000+99:99,310.00\n"
                            "M-100004,031526T103000 XYZ,410.00\n"
                            "M-100005,031526T103000 XM,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_basic_iso_ordinal_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026074T103000,120.50\n"
                            "M-100002,2026074T1030,200.00\n"
                            "M-100003,2026074T103000.123,310.00\n"
                            "M-100004,2026074T103000Z,410.00\n"
                            "M-100005,2026074T103000+05:30,510.00\n"
                            "M-100006,2026074T103000+0530,610.00\n"
                            "M-100007,2026074T103000 GMT,710.00\n"
                            "M-100008,2026074 103000,810.00\n"
                            "M-100009,2026074 1030,910.00\n"
                            "M-100010,2026074 103000.123,1010.00\n"
                            "M-100011,2026074 103000Z,1110.00\n"
                            "M-100012,2026074T103000 AM,1210.00\n"
                            "M-100013,2026074T103000 AM Z,1310.00\n"
                            "M-100014,2026074T103000Z AM,1410.00\n"
                            "M-100015,2026074T103000am,1510.00\n"
                            "M-100016,2026074T103000 PM EST,1610.00\n"
                            "M-100017,\"Sunday, 2026074T103000\",1710.00\n"
                            "M-100018,2026-074T103000,1810.00\n"
                            "M-100019,2026-074 103000.5,1910.00\n"
                            "M-100020,2026075T103000,2010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 20)
            for i in range(19):
                self.assertEqual(rows[i]["service_date"], "2026-03-15")
            self.assertEqual(rows[19]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 20)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_basic_iso_ordinal_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026366T103000,120.50\n"
                            "M-100002,2026074T256000,200.00\n"
                            "M-100003,2026074T103000+99:99,310.00\n"
                            "M-100004,2026074T103000 XYZ,410.00\n"
                            "M-100005,2026074T103000 XM,510.00\n"
                            "M-100006,2026000T103000,610.00\n"
                            "M-100007,\"Funday, 2026074T103000\",710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 7)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 7})

    def test_read_claims_csv_normalizes_basic_iso_week_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-W11-1T103000,120.50\n"
                            "M-100002,2026-W11-1T1030,200.00\n"
                            "M-100003,2026-W11-1T103000.123,310.00\n"
                            "M-100004,2026-W11-1T103000Z,410.00\n"
                            "M-100005,2026-W11-1T103000+05:30,510.00\n"
                            "M-100006,2026-W11-1T103000+0530,610.00\n"
                            "M-100007,2026-W11-1T103000 GMT,710.00\n"
                            "M-100008,2026-W11-1 103000,810.00\n"
                            "M-100009,2026-W11-1 1030,910.00\n"
                            "M-100010,2026-W11-1 103000.123,1010.00\n"
                            "M-100011,2026-W11-1 103000Z,1110.00\n"
                            "M-100012,2026-W11-1T103000 AM,1210.00\n"
                            "M-100013,2026-W11-1T103000 AM Z,1310.00\n"
                            "M-100014,2026-W11-1T103000Z AM,1410.00\n"
                            "M-100015,2026-W11-1T103000am,1510.00\n"
                            "M-100016,2026-W11-1T103000 PM EST,1610.00\n"
                            "M-100017,\"Sunday, 2026-W11-1T103000\",1710.00\n"
                            "M-100018,2026W111T103000,1810.00\n"
                            "M-100019,2026W111 103000.5,1910.00\n"
                            "M-100020,2026-W11-2T103000,2010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 20)
            for i in range(19):
                self.assertEqual(rows[i]["service_date"], "2026-03-09")
            self.assertEqual(rows[19]["service_date"], "2026-03-10")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 20)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_basic_iso_week_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2025-W53-1T103000,120.50\n"
                            "M-100002,2026-W11-8T103000,200.00\n"
                            "M-100003,2026-W11-1T256000,310.00\n"
                            "M-100004,2026-W11-1T103000+99:99,410.00\n"
                            "M-100005,2026-W11-1T103000 XYZ,510.00\n"
                            "M-100006,2026-W11-1T103000 XM,610.00\n"
                            "M-100007,\"Funday, 2026-W11-1T103000\",710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 7)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 7)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 7})

    def test_read_claims_csv_normalizes_week_only_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-W11 10:30:00,120.50\n"
                            "M-100002,2026-W11T10:30:00,200.00\n"
                            "M-100003,2026-W11 10:30,310.00\n"
                            "M-100004,2026-W11 10:30:00.123,410.00\n"
                            "M-100005,2026-W11 10:30:00Z,510.00\n"
                            "M-100006,2026-W11 10:30:00 +05:30,610.00\n"
                            "M-100007,2026-W11 10:30:00 GMT,710.00\n"
                            "M-100008,2026-W11 10:30:00 AM,810.00\n"
                            "M-100009,2026-W11 10:30:00 PM GMT,910.00\n"
                            "M-100010,2026-W11 10:30:00Z AM,1010.00\n"
                            "M-100011,\"Sunday, 2026-W11 10:30:00\",1110.00\n"
                            "M-100012,2026W11 10:30:00,1210.00\n"
                            "M-100013,2026W11T10:30:00,1310.00\n"
                            "M-100014,2026-W11 2:30 PM,1410.00\n"
                            "M-100015,2026-W11T09:00:00.123-04:00,1510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 15)
            for row in rows:
                # A week alone is its Monday; the time is dropped.
                self.assertEqual(row["service_date"], "2026-03-09")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 15)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_normalizes_basic_iso_week_only_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-W11T103000,120.50\n"
                            "M-100002,2026-W11T1030,200.00\n"
                            "M-100003,2026-W11T103000.123,310.00\n"
                            "M-100004,2026-W11T103000Z,410.00\n"
                            "M-100005,2026-W11T103000+05:30,510.00\n"
                            "M-100006,2026-W11T103000+0530,610.00\n"
                            "M-100007,2026-W11T103000 GMT,710.00\n"
                            "M-100008,2026-W11 103000,810.00\n"
                            "M-100009,2026-W11 1030,910.00\n"
                            "M-100010,2026-W11T103000 AM,1010.00\n"
                            "M-100011,2026-W11T103000 AM Z,1110.00\n"
                            "M-100012,2026-W11T103000Z AM,1210.00\n"
                            "M-100013,2026-W11T103000am,1310.00\n"
                            "M-100014,2026-W11T103000 PM EST,1410.00\n"
                            "M-100015,\"Sunday, 2026-W11T103000\",1510.00\n"
                            "M-100016,2026W11T103000,1610.00\n"
                            "M-100017,2026W11 103000.5,1710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 17)
            for row in rows:
                # A week alone is its Monday; the time is dropped.
                self.assertEqual(row["service_date"], "2026-03-09")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 17)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_week_only_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2025-W53 10:30:00,120.50\n"
                            "M-100002,2025-W53T103000,200.00\n"
                            "M-100003,2026-W11 25:60:00,310.00\n"
                            "M-100004,2026-W11T256000,410.00\n"
                            "M-100005,2026-W11 10:30:00+99:99,510.00\n"
                            "M-100006,2026-W11T103000+99:99,610.00\n"
                            "M-100007,2026-W11 10:30:00 XYZ,710.00\n"
                            "M-100008,2026-W11T103000 XYZ,810.00\n"
                            "M-100009,2026-W11 10:30:00 XM,910.00\n"
                            "M-100010,2026-W11T103000 XM,1010.00\n"
                            "M-100011,\"Funday, 2026-W11 10:30:00\",1110.00\n"
                            "M-100012,\"Funday, 2026-W11T103000\",1210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 12)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 12)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 12})

    def test_read_claims_csv_normalizes_compact_week_only_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026W11,120.50\n"
                            "M-100002,\"Sunday, 2026W11\",200.00\n"
                            "M-100003,2020W53,310.00\n"
                            "M-100004,2026W01,410.00\n"
                            "M-100005,2026W52,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            # A compact week alone is its Monday, like "2026-W11".
            self.assertEqual(
                [row["service_date"] for row in rows],
                ["2026-03-09", "2026-03-09", "2020-12-28",
                 "2025-12-29", "2026-12-21"])
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_compact_week_only_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2025W53,120.50\n"
                            "M-100002,2026W00,200.00\n"
                            "M-100003,2026W54,310.00\n"
                            "M-100004,\"Funday, 2026W11\",410.00\n"
                            "M-100005,2026W1,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_two_digit_year_week_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,26W111,120.50\n"
                            "M-100002,26-W11-1,200.00\n"
                            "M-100003,26W11,310.00\n"
                            "M-100004,26-W11,410.00\n"
                            "M-100005,\"Sunday, 26-W11-1\",510.00\n"
                            "M-100006,\"Sunday, 26W11\",610.00\n"
                            "M-100007,99-W01-1,710.00\n"
                            "M-100008,99W011,810.00\n"
                            "M-100009,69W111,910.00\n"
                            "M-100010,68W111,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            # A two-digit-year week date governs as its calendar
            # date; a week alone is its Monday, like "2026-W11".
            self.assertEqual(
                [row["service_date"] for row in rows],
                ["2026-03-09", "2026-03-09", "2026-03-09",
                 "2026-03-09", "2026-03-09", "2026-03-09",
                 "1999-01-04", "1999-01-04", "1969-03-10",
                 "2068-03-12"])
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 10)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_week_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,25-W53-1,120.50\n"
                            "M-100002,26-W11-8,200.00\n"
                            "M-100003,26-W00,310.00\n"
                            "M-100004,26-W54,410.00\n"
                            "M-100005,26-W1,510.00\n"
                            "M-100006,\"Funday, 26-W11-1\",610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_two_digit_year_week_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,26-W11-1 10:30:00,120.50\n"
                            "M-100002,26W111T103000,200.00\n"
                            "M-100003,26-W11 10:30:00,310.00\n"
                            "M-100004,26W11 10:30:00,410.00\n"
                            "M-100005,26-W11-1T10:30:00,510.00\n"
                            "M-100006,26-W11-1 10:30:00.123,610.00\n"
                            "M-100007,26-W11-1 10:30:00Z,710.00\n"
                            "M-100008,26-W11-1 10:30:00 +05:00,810.00\n"
                            "M-100009,26-W11-1 10:30:00 GMT,910.00\n"
                            "M-100010,26-W11-1 10:30:00 AM,1010.00\n"
                            "M-100011,26-W11-1 10:30:00 PM GMT,1110.00\n"
                            "M-100012,26-W11-1 10:30:00Z AM,1210.00\n"
                            "M-100013,26W111T103000am,1310.00\n"
                            "M-100014,\"Sunday, 26-W11-1 10:30:00\",1410.00\n"
                            "M-100015,26-W11T103000,1510.00\n"
                            "M-100016,26-W11 10:30,1610.00\n"
                            "M-100017,99-W01-1 10:30:00,1710.00\n"
                            "M-100018,69W111T103000,1810.00\n"
                            "M-100019,26-W11-1T1030,1910.00\n"
                            "M-100020,26-W11 10:30:00.123 +05:30,2010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 20)
            # A two-digit-year week-date datetime governs as its
            # calendar date; a week-only datetime governs as its
            # Monday; the time part is dropped, only the date part
            # governs.
            self.assertEqual(
                [row["service_date"] for row in rows],
                ["2026-03-09", "2026-03-09", "2026-03-09",
                 "2026-03-09", "2026-03-09", "2026-03-09",
                 "2026-03-09", "2026-03-09", "2026-03-09",
                 "2026-03-09", "2026-03-09", "2026-03-09",
                 "2026-03-09", "2026-03-09", "2026-03-09",
                 "2026-03-09", "1999-01-04", "1969-03-10",
                 "2026-03-09", "2026-03-09"])
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 20)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_week_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,25-W53-1 10:00:00,120.50\n"
                            "M-100002,26-W11-1 25:60:00,200.00\n"
                            "M-100003,26W111T256000,310.00\n"
                            "M-100004,26-W11-1 10:30:00+99:99,410.00\n"
                            "M-100005,26-W11-1 10:30:00 XYZ,510.00\n"
                            "M-100006,26-W11-1 10:30:00 XM,610.00\n"
                            "M-100007,25-W53 10:30:00,710.00\n"
                            "M-100008,26-W11 25:60:00,810.00\n"
                            "M-100009,\"Funday, 26-W11-1 10:30:00\",910.00\n"
                            "M-100010,26-W11-1 10:30:00 AM +99:99,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 10)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 10})

    def test_read_claims_csv_normalizes_two_digit_year_ordinal_dates_and_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,26074,120.50\n"
                            "M-100002,26-074,200.00\n"
                            "M-100003,\"Sunday, 26074\",310.00\n"
                            "M-100004,\"Sunday, 26-074\",410.00\n"
                            "M-100005,99074,510.00\n"
                            "M-100006,69074,610.00\n"
                            "M-100007,68074,710.00\n"
                            "M-100008,12345,810.00\n"
                            "M-100009,26-074 10:30:00,910.00\n"
                            "M-100010,26074T103000,1010.00\n"
                            "M-100011,26-074T10:30:00Z,1110.00\n"
                            "M-100012,26074 10:30:00 AM,1210.00\n"
                            "M-100013,26074 10:30:00.123Z,1310.00\n"
                            "M-100014,26074 10:30:00 GMT,1410.00\n"
                            "M-100015,26-074 10:30:00 PM GMT,1510.00\n"
                            "M-100016,26074T103000am,1610.00\n"
                            "M-100017,\"Sunday, 26-074 10:30:00\",1710.00\n"
                            "M-100018,26074 10:30,1810.00\n"
                            "M-100019,26-074T1030,1910.00\n"
                            "M-100020,26074 10:30:00 +05:00,2010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 20)
            # A two-digit-year ordinal date governs as its calendar
            # date; a bare five-digit number reads as YYDDD, so
            # "12345" governs as 2012-12-10 rather than quarantining
            # as a bad epoch timestamp. A two-digit-year ordinal
            # datetime governs as its date part; the time part is
            # dropped, only the date part governs.
            self.assertEqual(
                [row["service_date"] for row in rows],
                ["2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "1999-03-15", "1969-03-15",
                 "2068-03-14", "2012-12-10", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15"])
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 20)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_ordinal_dates_and_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,26366,120.50\n"
                            "M-100002,26000,200.00\n"
                            "M-100003,\"Funday, 26074\",310.00\n"
                            "M-100004,26-074 25:60:00,410.00\n"
                            "M-100005,26074T256000,510.00\n"
                            "M-100006,26074 10:30:00+99:99,610.00\n"
                            "M-100007,26074 10:30:00 XYZ,710.00\n"
                            "M-100008,26074 10:30:00 XM,810.00\n"
                            "M-100009,26366 10:00:00 AM,910.00\n"
                            "M-100010,26-074 10:30:00 AM +99:99,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 10)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 10})

    def test_read_claims_csv_normalizes_no_comma_month_name_dates_and_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,March 15 2026,120.50\n"
                            "M-100002,Mar 15 2026,200.00\n"
                            "M-100003,March 15th 2026,310.00\n"
                            "M-100004,Mar 15th 2026,410.00\n"
                            "M-100005,March 15 2026 10:30:00,510.00\n"
                            "M-100006,Mar 15 2026 10:30:00,610.00\n"
                            "M-100007,March 15 2026T10:30:00,710.00\n"
                            "M-100008,March 15 2026 10:30,810.00\n"
                            "M-100009,March 15 2026 10:30:00.123Z,910.00\n"
                            "M-100010,March 15 2026 10:30:00 AM,1010.00\n"
                            "M-100011,March 15 2026 10:30:00 AM GMT,1110.00\n"
                            "M-100012,March 15 2026 10:30:00Z AM,1210.00\n"
                            "M-100013,March 15 2026 10:30:00 +05:30,1310.00\n"
                            "M-100014,March 15 2026 10:30:00 GMT,1410.00\n"
                            "M-100015,\"Sunday, March 15 2026\",1510.00\n"
                            "M-100016,\"Sunday, March 15 2026 10:30:00\",1610.00\n"
                            "M-100017,March 15 26,1710.00\n"
                            "M-100018,Mar 15 26,1810.00\n"
                            "M-100019,Mar 15 99,1910.00\n"
                            "M-100020,March 15th 26 10:30:00 am +05:30,2010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 20)
            # A month-name date without the comma governs as its
            # calendar date; a no-comma month-name datetime governs
            # as its date part; the time part is dropped, only the
            # date part governs. The two-digit year follows
            # Python's %y pivot, so "Mar 15 99" governs as
            # 1999-03-15.
            self.assertEqual(
                [row["service_date"] for row in rows],
                ["2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "1999-03-15", "2026-03-15"])
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 20)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_no_comma_month_name_dates_and_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,Feb 30 2026,120.50\n"
                            "M-100002,March 32 2026,200.00\n"
                            "M-100003,Foo 15 2026,310.00\n"
                            "M-100004,\"Funday, March 15 2026\",410.00\n"
                            "M-100005,March 15 2026 25:00:00,510.00\n"
                            "M-100006,March 15 2026 10:30:00 XM,610.00\n"
                            "M-100007,March 15 2026 10:30:00+99:99,710.00\n"
                            "M-100008,March 15 2026 10:30:00 XYZ,810.00\n"
                            "M-100009,Feb 30 26,910.00\n"
                            "M-100010,March 15 2026 10:30:00 AM +99:99,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 10)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 10})

    def test_read_claims_csv_normalizes_day_of_month_name_dates_and_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15th of March 2026,120.50\n"
                            "M-100002,15 of March 2026,200.00\n"
                            "M-100003,15th of Mar 2026,310.00\n"
                            "M-100004,15 of Mar 2026,410.00\n"
                            "M-100005,the 15th of March 2026,510.00\n"
                            "M-100006,15th of March 26,610.00\n"
                            "M-100007,15th of Mar 99,710.00\n"
                            "M-100008,\"Sunday, 15th of March 2026\",810.00\n"
                            "M-100009,15th of March 2026 10:30:00,910.00\n"
                            "M-100010,15th of March 2026T10:30:00,1010.00\n"
                            "M-100011,15th of March 2026 10:30,1110.00\n"
                            "M-100012,15th of March 2026 10:30:00.123Z,1210.00\n"
                            "M-100013,15th of March 2026 10:30:00+05:30,1310.00\n"
                            "M-100014,15th of March 2026 10:30:00 GMT,1410.00\n"
                            "M-100015,15th of March 2026 10:30:00 AM,1510.00\n"
                            "M-100016,15th of March 2026 10:30:00 AM Z,1610.00\n"
                            "M-100017,15th of March 2026 10:30:00Z AM,1710.00\n"
                            "M-100018,\"Sunday, 15th of March 2026 10:30:00 am +05:30\",1810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 18)
            # A day-of-month-name date governs as its calendar
            # date; a day-of month-name datetime governs as its
            # date part; the time part is dropped, only the date
            # part governs. The two-digit year follows Python's
            # %y pivot, so "15th of Mar 99" governs as
            # 1999-03-15.
            self.assertEqual(
                [row["service_date"] for row in rows],
                ["2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "1999-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15"])
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 18)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_day_of_month_name_dates_and_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,30th of February 2026,120.50\n"
                            "M-100002,32nd of March 2026,200.00\n"
                            "M-100003,15th of Foo 2026,310.00\n"
                            "M-100004,\"Funday, 15th of March 2026\",410.00\n"
                            "M-100005,15th of March 2026 25:60:00,510.00\n"
                            "M-100006,15th of March 2026 10:30:00 XYZ,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_space_separated_iso_dates_and_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026 03 15,120.50\n"
                            "M-100002,2026 3 15,200.00\n"
                            "M-100003,2026 03 5,310.00\n"
                            "M-100004,2026 3 5,410.00\n"
                            "M-100005,\"Sunday, 2026 03 15\",510.00\n"
                            "M-100006,\"Mon, 2026 03 15\",610.00\n"
                            "M-100007,2026 03 15 10:30:00,710.00\n"
                            "M-100008,2026 03 15T10:30:00,810.00\n"
                            "M-100009,2026 03 15 10:30,910.00\n"
                            "M-100010,2026 03 15 10:30:00.123,1010.00\n"
                            "M-100011,2026 03 15 10:30:00Z,1110.00\n"
                            "M-100012,2026 03 15 10:30:00+05:30,1210.00\n"
                            "M-100013,2026 03 15 10:30:00 GMT,1310.00\n"
                            "M-100014,2026 03 15 10:30:00 AM,1410.00\n"
                            "M-100015,2026 03 15 10:30:00 pm,1510.00\n"
                            "M-100016,2026 03 15 10:30:00 AM Z,1610.00\n"
                            "M-100017,2026 03 15 10:30:00Z AM,1710.00\n"
                            "M-100018,\"Sunday, 2026 03 15 10:30:00 am +05:30\",1810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 18)
            # A space-separated ISO date governs as its calendar
            # date; a space-separated ISO datetime governs as its
            # date part; the time part is dropped, only the date
            # part governs. Single-digit month and day govern
            # too, as their calendar date ("2026 03 5" governs
            # as 2026-03-05, not 2026-03-15).
            self.assertEqual(
                [row["service_date"] for row in rows],
                ["2026-03-15", "2026-03-15", "2026-03-05",
                 "2026-03-05", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15"])
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 18)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_iso_dates_and_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026 02 30,120.50\n"
                            "M-100002,2026 13 15,200.00\n"
                            "M-100003,2026 03 32,310.00\n"
                            "M-100004,\"Funday, 2026 03 15\",410.00\n"
                            "M-100005,2026 03 15 25:60:00,510.00\n"
                            "M-100006,2026 03 15 10:30:00 XYZ,610.00\n"
                            "M-100007,2026 03 15 10:30:00 XM,710.00\n"
                            "M-100008,2026 03 15 10:30:00+99:99,810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_read_claims_csv_normalizes_two_digit_year_and_non_year_first_space_separated_dates_and_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,26 03 15,120.50\n"
                            "M-100002,03 15 26,200.00\n"
                            "M-100003,15 03 26,310.00\n"
                            "M-100004,03 15 2026,410.00\n"
                            "M-100005,15 03 2026,510.00\n"
                            "M-100006,03 15 99,610.00\n"
                            "M-100007,03 15 69,710.00\n"
                            "M-100008,03 15 68,810.00\n"
                            "M-100009,3 5 26,910.00\n"
                            "M-100010,03 15 26 10:30:00,1010.00\n"
                            "M-100011,15 03 26T10:30:00,1110.00\n"
                            "M-100012,03 15 26 10:30,1210.00\n"
                            "M-100013,03 15 26 10:30:00.123,1310.00\n"
                            "M-100014,03 15 26 10:30:00Z,1410.00\n"
                            "M-100015,03 15 26 10:30:00+05:30,1510.00\n"
                            "M-100016,03 15 26 10:30:00 GMT,1610.00\n"
                            "M-100017,03 15 26 10:30:00 AM,1710.00\n"
                            "M-100018,\"Sunday, 03 15 26 10:30:00 am +05:30\",1810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 18)
            # A two-digit-year or non-year-first space-separated
            # date governs as its calendar date; a datetime
            # governs as its date part; the time part is
            # dropped, only the date part governs. The US form
            # is tried first, so only an unambiguous day-first
            # date reads day-first ("26 03 15" governs as
            # 2015-03-26, not 2026-03-15, and "15 03 26" as
            # 2026-03-15); there is no separate year-first
            # two-digit form. The two-digit year follows the
            # %y pivot ("03 15 99" governs as 1999-03-15,
            # "03 15 68" as 2068-03-15). Single-digit month and
            # day govern too, as their calendar date ("3 5 26"
            # governs as 2026-03-05).
            self.assertEqual(
                [row["service_date"] for row in rows],
                ["2015-03-26", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "1999-03-15",
                 "1969-03-15", "2068-03-15", "2026-03-05",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15",
                 "2026-03-15", "2026-03-15", "2026-03-15"])
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 18)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_two_digit_year_and_non_year_first_space_separated_dates_and_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02 30 26,120.50\n"
                            "M-100002,13 15 26,200.00\n"
                            "M-100003,03 32 26,310.00\n"
                            "M-100004,\"Funday, 03 15 26\",410.00\n"
                            "M-100005,03 15 26 25:60:00,510.00\n"
                            "M-100006,03 15 26 10:30:00 XYZ,610.00\n"
                            "M-100007,03 15 26 10:30:00 XM,710.00\n"
                            "M-100008,03 15 26 10:30:00+99:99,810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_read_claims_csv_normalizes_ampm_basic_iso_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315T103000 AM,120.50\n"
                            "M-100002,20260315T103000 PM,200.00\n"
                            "M-100003,20260315T1030 AM,310.00\n"
                            "M-100004,20260315T103000.123 AM,410.00\n"
                            "M-100005,20260315T103000 AM Z,510.00\n"
                            "M-100006,20260315T103000 AM +05:30,610.00\n"
                            "M-100007,20260315T103000 AM GMT,710.00\n"
                            "M-100008,20260315T103000Z AM,810.00\n"
                            "M-100009,20260315 103000 AM,910.00\n"
                            "M-100010,20260315 1030 PM,1010.00\n"
                            "M-100011,20260315T103000am,1110.00\n"
                            "M-100012,\"Sunday, 20260316T103000 AM\",1210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 12)
            for i in range(11):
                self.assertEqual(rows[i]["service_date"], "2026-03-15")
            self.assertEqual(rows[11]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 12)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_basic_iso_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230T103000 AM,120.50\n"
                            "M-100002,20260315T256000 AM,200.00\n"
                            "M-100003,20260315T103000 AM +99:99,310.00\n"
                            "M-100004,20260315T103000 AM XYZ,410.00\n"
                            "M-100005,20260315T103000 XM,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_ampm_underscore_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15 10:30:00 AM,120.50\n"
                            "M-100002,2026_03_15 10:30:00.123 AM,200.00\n"
                            "M-100003,2026_03_15T09:00:00 PM,310.00\n"
                            "M-100004,\"Sunday, 2026_03_16 09:00:00 pm\",410.00\n"
                            "M-100005,2026_03_15 2:30pm,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_underscore_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_02_30 10:00:00 AM,120.50\n"
                            "M-100002,2026_03_15 10:30:00 XM,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_tz_underscore_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15 10:30:00 AM Z,120.50\n"
                            "M-100002,2026_03_15T09:00:00 PM -04:00,200.00\n"
                            "M-100003,2026_03_15 10:30:00.123 AM +05:30,310.00\n"
                            "M-100004,\"Sunday, 2026_03_16 10:30:00 am +05:30\",410.00\n"
                            "M-100005,2026_03_15 10:30:00Z AM,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_tz_underscore_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_02_30 10:00:00 AM Z,120.50\n"
                            "M-100002,2026_03_15 10:30:00 AM +99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_numeric_hyphen_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026 10:30:00 AM,120.50\n"
                            "M-100002,03-15-2026 10:30:00.123 AM,200.00\n"
                            "M-100003,15-03-2026T09:00:00 PM,310.00\n"
                            "M-100004,\"Sunday, 03-16-2026 09:00:00 pm\",410.00\n"
                            "M-100005,03-15-2026 2:30pm,510.00\n"
                            "M-100006,03-04-2026 10:30:00 AM,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-04")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_numeric_hyphen_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02-30-2026 10:00:00 AM,120.50\n"
                            "M-100002,03-15-2026 10:30:00 XM,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_tz_numeric_hyphen_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026 10:30:00 AM Z,120.50\n"
                            "M-100002,03-15-2026T09:00:00 PM -04:00,200.00\n"
                            "M-100003,03-15-2026 10:30:00.123 AM +05:30,310.00\n"
                            "M-100004,\"Sunday, 03-16-2026 10:30:00 am +05:30\",410.00\n"
                            "M-100005,03-15-2026 10:30:00Z AM,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_tz_numeric_hyphen_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02-30-2026 10:00:00 AM Z,120.50\n"
                            "M-100002,03-15-2026 10:30:00 AM +99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_iso_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15 10:30:00 AM,120.50\n"
                            "M-100002,2026-03-15 10:30:00.123 AM,200.00\n"
                            "M-100003,2026-03-15T09:00:00 PM,310.00\n"
                            "M-100004,\"Sunday, 2026-03-16 09:00:00 pm\",410.00\n"
                            "M-100005,2026-03-15 2:30pm,510.00\n"
                            "M-100006,2026-03-17T08:00:00.25 PM,610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            self.assertEqual(rows[5]["service_date"], "2026-03-17")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 6)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_iso_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-02-30 10:00:00 AM,120.50\n"
                            "M-100002,2026-03-15 10:30:00 XM,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_ampm_tz_iso_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15 10:30:00 AM Z,120.50\n"
                            "M-100002,2026-03-15T09:00:00 PM -04:00,200.00\n"
                            "M-100003,2026-03-15 10:30:00.123 AM +05:30,310.00\n"
                            "M-100004,\"Sunday, 2026-03-16 09:00:00 pm Z\",410.00\n"
                            "M-100005,2026-03-15 10:30:00Z AM,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-15")
            self.assertEqual(rows[2]["service_date"], "2026-03-15")
            self.assertEqual(rows[3]["service_date"], "2026-03-16")
            self.assertEqual(rows[4]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 5)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_ampm_tz_iso_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-02-30 10:00:00 AM Z,120.50\n"
                            "M-100002,2026-03-15 10:30:00 AM +99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_lowercase_iso_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15t10:30:00z,120.50\n"
                            "M-100002,2026-03-15t10:30:00,200.00\n"
                            "M-100003,2026-03-15T09:00:00z,310.00\n"
                            "M-100004,2026-03-15 10:30:00z,410.00\n"
                            "M-100005,2026-03-15t10:30:00.123z,510.00\n"
                            "M-100006,2026-03-15t10:30:00+05:30,610.00\n"
                            "M-100007,2026-03-15t10:30,710.00\n"
                            "M-100008,2026-03-15t10:30:00am,810.00\n"
                            "M-100009,\"Sunday, 2026-03-16t10:30:00z\",910.00\n"
                            "M-100010,2026 03 15t10:30:00,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            for row in rows[:8]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-16")
            self.assertEqual(rows[9]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 10)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_lowercase_iso_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-02-30t10:30:00z,120.50\n"
                            "M-100002,2026-03-15t10:30:00+99:99,200.00\n"
                            "M-100003,2026-03-15t10:30:00 xyz,310.00\n"
                            "M-100004,2026-03-15t10:30:00 xm,410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 4)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 4})

    def test_read_claims_csv_normalizes_lowercase_z_slash_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026 10:30:00z,120.50\n"
                            "M-100002,03/15/2026t10:30:00z,200.00\n"
                            "M-100003,15/03/2026 10:30:00z,310.00\n"
                            "M-100004,03/15/2026 10:30:00.123z,410.00\n"
                            "M-100005,03/15/2026 10:30:00 z,510.00\n"
                            "M-100006,03/15/2026T09:00:00z,610.00\n"
                            "M-100007,2026/03/15 10:30:00z,710.00\n"
                            "M-100008,03/15/26 10:30:00z,810.00\n"
                            "M-100009,\"Sunday, 03/16/2026 10:30:00z\",910.00\n"
                            "M-100010,03/15/2026 10:30:00 am z,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            for row in rows[:8]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-16")
            self.assertEqual(rows[9]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 10)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_lowercase_z_slash_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02/30/2026 10:00:00z,120.50\n"
                            "M-100002,03/15/2026 10:30:00.123+99:99,200.00\n"
                            "M-100003,03/15/2026 10:30:00 xyz,310.00\n"
                            "M-100004,\"Funday, 03/15/2026 10:30:00z\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 4)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 4})

    def test_read_claims_csv_normalizes_lowercase_z_dot_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15 10:30:00z,120.50\n"
                            "M-100002,2026.03.15t10:30:00z,200.00\n"
                            "M-100003,03.15.2026 10:30:00z,310.00\n"
                            "M-100004,2026.03.15 10:30:00.123z,410.00\n"
                            "M-100005,2026.03.15 10:30:00 z,510.00\n"
                            "M-100006,2026.03.15T09:00:00z,610.00\n"
                            "M-100007,15.03.2026 10:30:00z,710.00\n"
                            "M-100008,03.15.26 10:30:00z,810.00\n"
                            "M-100009,\"Sunday, 2026.03.16 10:30:00z\",910.00\n"
                            "M-100010,2026.03.15 10:30:00 am z,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            for row in rows[:8]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-16")
            self.assertEqual(rows[9]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 10)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_lowercase_z_dot_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.02.30 10:00:00z,120.50\n"
                            "M-100002,2026.03.15 10:30:00.123+99:99,200.00\n"
                            "M-100003,2026.03.15 10:30:00 xyz,310.00\n"
                            "M-100004,\"Funday, 2026.03.15 10:30:00z\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 4)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 4})

    def test_read_claims_csv_normalizes_lowercase_z_underscore_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15 10:30:00z,120.50\n"
                            "M-100002,2026_03_15t10:30:00z,200.00\n"
                            "M-100003,03_15_2026 10:30:00z,310.00\n"
                            "M-100004,2026_03_15 10:30:00.123z,410.00\n"
                            "M-100005,2026_03_15 10:30:00 z,510.00\n"
                            "M-100006,2026_03_15T09:00:00z,610.00\n"
                            "M-100007,15_03_2026 10:30:00z,710.00\n"
                            "M-100008,03_15_26 10:30:00z,810.00\n"
                            "M-100009,\"Sunday, 2026_03_16 10:30:00z\",910.00\n"
                            "M-100010,2026_03_15 10:30:00 am z,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            for row in rows[:8]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-16")
            self.assertEqual(rows[9]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 10)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_lowercase_z_underscore_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_02_30 10:00:00z,120.50\n"
                            "M-100002,2026_03_15 10:30:00.123+99:99,200.00\n"
                            "M-100003,2026_03_15 10:30:00 xyz,310.00\n"
                            "M-100004,\"Funday, 2026_03_15 10:30:00z\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 4)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 4})

    def test_read_claims_csv_normalizes_lowercase_z_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260315T103000z,120.50\n"
                            "M-100002,20260315t103000z,200.00\n"
                            "M-100003,20260315 10:30:00z,310.00\n"
                            "M-100004,20260315T103000.123z,410.00\n"
                            "M-100005,20260315 10:30:00 z,510.00\n"
                            "M-100006,20260315T09:00:00z,610.00\n"
                            "M-100007,20260315T1030z,710.00\n"
                            "M-100008,20260315 10:30z,810.00\n"
                            "M-100009,\"Sunday, 20260316T103000z\",910.00\n"
                            "M-100010,20260315 10:30:00z AM,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            for row in rows[:8]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-16")
            self.assertEqual(rows[9]["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 10)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_lowercase_z_compact_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,20260230T103000z,120.50\n"
                            "M-100002,20260315T103000+99:99,200.00\n"
                            "M-100003,20260315T103000 xyz,310.00\n"
                            "M-100004,\"Funday, 20260315T103000z\",410.00\n"
                            "M-100005,20260315T256000z,510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_lowercase_month_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"mar 15, 2026\",120.50\n"
                            "M-100002,15 mar 2026,200.00\n"
                            "M-100003,\"march 15, 2026\",310.00\n"
                            "M-100004,15 march 2026,410.00\n"
                            "M-100005,mar-15-2026,510.00\n"
                            "M-100006,15-mar-2026,610.00\n"
                            "M-100007,march 15 2026,710.00\n"
                            "M-100008,\"mar 15, 2026 10:30:00\",810.00\n"
                            "M-100009,15th of march 2026,910.00\n"
                            "M-100010,\"sunday, mar 16, 2026\",1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            for row in rows[:9]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[9]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 10)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_normalizes_lowercase_z_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"mar 15, 2026 10:30:00z\",120.50\n"
                            "M-100002,\"Mar 15, 2026 10:30:00z\",200.00\n"
                            "M-100003,\"mar 15, 2026 10:30:00 z\",310.00\n"
                            "M-100004,15 mar 2026 10:30:00z,410.00\n"
                            "M-100005,\"mar 15, 2026T10:30:00z\",510.00\n"
                            "M-100006,\"mar 15, 2026 10:30:00.123z\",610.00\n"
                            "M-100007,\"Mar 15, 2026 10:30:00z AM\",710.00\n"
                            "M-100008,\"mar 15, 2026 10:30:00 am z\",810.00\n"
                            "M-100009,\"sunday, mar 16, 2026 10:30:00z\",910.00\n"
                            "M-100010,15th of march 2026 10:30:00z,1010.00\n"
                            "M-100011,mar-15-2026 10:30:00z,1110.00\n"
                            "M-100012,\"mar 15, 26 10:30:00z\",1210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 12)
            for row in rows[:8]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[8]["service_date"], "2026-03-16")
            for row in rows[9:]:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 12)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_lowercase_month_name_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"feb 30, 2026\",120.50\n"
                            "M-100002,\"mar 15, 2026 10:30:00 xyz\",200.00\n"
                            "M-100003,\"funday, mar 15, 2026\",310.00\n"
                            "M-100004,\"mar 32, 2026\",410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 4)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 4)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 4})

    def test_read_claims_csv_bad_lowercase_z_month_name_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"feb 30, 2026 10:00:00z\",120.50\n"
                            "M-100002,\"mar 15, 2026 10:30:00+99:99\",200.00\n"
                            "M-100003,\"mar 15, 2026 25:30:00z\",310.00\n"
                            "M-100004,\"mar 15, 2026 10:30:00zz\",410.00\n"
                            "M-100005,\"funday, mar 15, 2026 10:30:00z\",510.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 5)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 5)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 5})

    def test_read_claims_csv_normalizes_lowercase_w_week_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-w11-1,120.50\n"
                            "M-100002,2026w111,200.00\n"
                            "M-100003,2026-w11,310.00\n"
                            "M-100004,2026w11,410.00\n"
                            "M-100005,\"2026-w11 10:30:00\",510.00\n"
                            "M-100006,2026-w11T103000,610.00\n"
                            "M-100007,\"2026-w11 10:30:00 AM\",710.00\n"
                            "M-100008,\"Sunday, 2026-w11-1\",810.00\n"
                            "M-100009,26-w11-1,910.00\n"
                            "M-100010,26w111,1010.00\n"
                            "M-100011,26-w11,1110.00\n"
                            "M-100012,26w11,1210.00\n"
                            "M-100013,\"26-w11 10:30:00\",1310.00\n"
                            "M-100014,\"26-w11-1 10:30:00\",1410.00\n"
                            "M-100015,26w111T103000,1510.00\n"
                            "M-100016,99-w01-1,1610.00\n"
                            "M-100017,69w111,1710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 17)
            for row in rows[:15]:
                self.assertEqual(row["service_date"], "2026-03-09")
            self.assertEqual(rows[15]["service_date"], "1999-01-04")
            self.assertEqual(rows[16]["service_date"], "1969-03-10")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 17)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_lowercase_w_week_date_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2025-w53-1,120.50\n"
                            "M-100002,2026-w11-8,200.00\n"
                            "M-100003,2026-w00,310.00\n"
                            "M-100004,\"Funday, 2026-w11-1\",410.00\n"
                            "M-100005,\"2026-w11-1 25:60:00\",510.00\n"
                            "M-100006,\"2026-w11-1 10:30:00 XM\",610.00\n"
                            "M-100007,\"2026-w11-1 10:30:00+99:99\",710.00\n"
                            "M-100008,25-w53-1,810.00\n"
                            "M-100009,26-w11-8,910.00\n"
                            "M-100010,26-w00,1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 10)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 10})

    def test_read_claims_csv_normalizes_lowercase_z_week_date_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"2026-W11-1 10:30:00z\",120.50\n"
                            "M-100002,2026-W11-1T103000z,200.00\n"
                            "M-100003,\"2026-W11 10:30:00z\",310.00\n"
                            "M-100004,\"2026-W11-1 10:30:00 z\",410.00\n"
                            "M-100005,\"2026-W11-1 10:30:00z AM\",510.00\n"
                            "M-100006,\"2026-W11-1 10:30:00 AM z\",610.00\n"
                            "M-100007,\"Sunday, 2026-W11-1 10:30:00z\",710.00\n"
                            "M-100008,\"2026-w11-1 10:30:00z\",810.00\n"
                            "M-100009,\"26-W11-1 10:30:00z\",910.00\n"
                            "M-100010,26W111T103000z,1010.00\n"
                            "M-100011,\"26-W11 10:30:00z\",1110.00\n"
                            "M-100012,\"26-W11-1 10:30:00z AM\",1210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 12)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-09")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 12)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_lowercase_z_week_date_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"2025-W53-1 10:30:00z\",120.50\n"
                            "M-100002,\"2026-W11-8 10:30:00z\",200.00\n"
                            "M-100003,\"2026-W00 10:30:00z\",310.00\n"
                            "M-100004,\"Funday, 2026-W11-1 10:30:00z\",410.00\n"
                            "M-100005,\"2026-W11-1 25:60:00z\",510.00\n"
                            "M-100006,\"2026-W11-1 10:30:00z XM\",610.00\n"
                            "M-100007,\"2026-W11-1 10:30:00zz\",710.00\n"
                            "M-100008,\"25-W53-1 10:30:00z\",810.00\n"
                            "M-100009,\"26-W11-8 10:30:00z\",910.00\n"
                            "M-100010,\"26-W00 10:30:00z\",1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 10)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 10})

    def test_read_claims_csv_normalizes_lowercase_z_ordinal_hyphen_compact_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"2026-074 10:30:00z\",120.50\n"
                            "M-100002,2026074T103000z,200.00\n"
                            "M-100003,2026-074T103000z,310.00\n"
                            "M-100004,\"2026-074 10:30:00 z\",410.00\n"
                            "M-100005,\"2026-074 10:30:00z AM\",510.00\n"
                            "M-100006,\"Sunday, 2026-074 10:30:00z\",610.00\n"
                            "M-100007,\"26-074 10:30:00z\",710.00\n"
                            "M-100008,26074T103000z,810.00\n"
                            "M-100009,26-074T103000z,910.00\n"
                            "M-100010,\"26074 10:30:00z AM\",1010.00\n"
                            "M-100011,\"15-03-2026 10:30:00z\",1110.00\n"
                            "M-100012,\"03-15-2026 10:30:00z\",1210.00\n"
                            "M-100013,\"03-15-2026 10:30:00 z\",1310.00\n"
                            "M-100014,\"03-15-2026 10:30:00z AM\",1410.00\n"
                            "M-100015,\"Sunday, 03-15-2026 10:30:00z\",1510.00\n"
                            "M-100016,\"15-03-26 10:30:00z\",1610.00\n"
                            "M-100017,\"03-15-26 10:30:00z\",1710.00\n"
                            "M-100018,\"031526 10:30:00z\",1810.00\n"
                            "M-100019,031526T103000z,1910.00\n"
                            "M-100020,\"031526 10:30:00 z\",2010.00\n"
                            "M-100021,\"031526 10:30:00z AM\",2110.00\n"
                            "M-100022,\"Sunday, 031526 10:30:00z\",2210.00\n"
                            "M-100023,\"150326 10:30:00z\",2310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 23)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 23)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_lowercase_z_ordinal_hyphen_compact_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"2026-366 10:30:00z\",120.50\n"
                            "M-100002,\"2026074 10:30:00zz\",200.00\n"
                            "M-100003,\"2026-074 10:30:00+99:99\",310.00\n"
                            "M-100004,\"Funday, 2026-074 10:30:00z\",410.00\n"
                            "M-100005,\"26-366 10:30:00z\",510.00\n"
                            "M-100006,\"26074 10:30:00zz\",610.00\n"
                            "M-100007,\"02-30-2026 10:30:00z\",710.00\n"
                            "M-100008,\"03-15-2026 10:30:00 XM\",810.00\n"
                            "M-100009,\"15-13-2026 10:30:00z\",910.00\n"
                            "M-100010,\"023026 10:30:00z\",1010.00\n"
                            "M-100011,\"031526 10:30:00zz\",1110.00\n"
                            "M-100012,\"031526 10:30:00+99:99\",1210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 12)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 12)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 12})

    def test_read_claims_csv_normalizes_colonless_t_hyphen_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15-03-2026T103000z,120.50\n"
                            "M-100002,03-15-2026T103000z,200.00\n"
                            "M-100003,03-15-2026T103000Z,310.00\n"
                            "M-100004,15-03-2026T103000.123z,410.00\n"
                            "M-100005,03-15-2026T103000+05:30,510.00\n"
                            "M-100006,03-15-2026T103000+0530,610.00\n"
                            "M-100007,03-15-2026T103000-04:00,710.00\n"
                            "M-100008,03-15-2026T103000.123+05:30,810.00\n"
                            "M-100009,\"Sunday, 03-15-2026T103000z\",910.00\n"
                            "M-100010,\"03-15-2026T103000 AM\",1010.00\n"
                            "M-100011,\"03-15-2026T103000z AM\",1110.00\n"
                            "M-100012,\"03-15-2026T103000 AM Z\",1210.00\n"
                            "M-100013,03-15-2026T103000 GMT,1310.00\n"
                            "M-100014,\"03-15-2026T103000 AM GMT\",1410.00\n"
                            "M-100015,\"03-15-2026T103000 GMT AM\",1510.00\n"
                            "M-100016,15-03-26T103000z,1610.00\n"
                            "M-100017,03-15-26T103000z,1710.00\n"
                            "M-100018,03-15-26T103000.123z,1810.00\n"
                            "M-100019,\"03-15-26T103000 AM\",1910.00\n"
                            "M-100020,\"Sunday, 03-15-26T103000z\",2010.00\n"
                            "M-100021,26-03-15T103000z,2110.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 21)
            for row in rows[:20]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[20]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 21)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_colonless_t_hyphen_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02-30-2026T103000z,120.50\n"
                            "M-100002,03-15-2026T103000zz,200.00\n"
                            "M-100003,03-15-2026T103000+99:99,310.00\n"
                            "M-100004,\"Funday, 03-15-2026T103000z\",410.00\n"
                            "M-100005,\"03-15-2026T103000 XM\",510.00\n"
                            "M-100006,15-13-2026T103000z,610.00\n"
                            "M-100007,03-15-2026T103000 XYZ,710.00\n"
                            "M-100008,\"03-15-2026T103000 AM +99:99\",810.00\n"
                            "M-100009,02-30-26T103000z,910.00\n"
                            "M-100010,03-15-2026T103000.123zz,1010.00\n"
                            "M-100011,03-15-2026T10300z,1110.00\n"
                            "M-100012,03-15-2026T1030000z,1210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 12)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 12)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 12})

    def test_read_claims_csv_normalizes_noseconds_and_space_colonless_hyphen_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03-15-2026T1030z,120.50\n"
                            "M-100002,15-03-2026T1030z,200.00\n"
                            "M-100003,03-15-26T1030z,310.00\n"
                            "M-100004,03-15-2026T1030Z,410.00\n"
                            "M-100005,03-15-2026T1030,510.00\n"
                            "M-100006,03-15-2026T1030+05:30,610.00\n"
                            "M-100007,03-15-2026T1030+0530,710.00\n"
                            "M-100008,03-15-2026T1030 GMT,810.00\n"
                            "M-100009,\"Sunday, 03-15-2026T1030z\",910.00\n"
                            "M-100010,\"03-15-2026T1030 AM\",1010.00\n"
                            "M-100011,\"03-15-2026T1030z AM\",1110.00\n"
                            "M-100012,\"03-15-2026T1030 AM Z\",1210.00\n"
                            "M-100013,\"03-15-2026T1030 AM GMT\",1310.00\n"
                            "M-100014,\"03-15-2026T1030 GMT AM\",1410.00\n"
                            "M-100015,15-03-26T1030z,1510.00\n"
                            "M-100016,03-15-2026 103000z,1610.00\n"
                            "M-100017,03-15-2026 103000,1710.00\n"
                            "M-100018,15-03-2026 103000z,1810.00\n"
                            "M-100019,03-15-26 103000z,1910.00\n"
                            "M-100020,03-15-2026 103000.123z,2010.00\n"
                            "M-100021,03-15-2026 103000+05:30,2110.00\n"
                            "M-100022,03-15-2026 103000 GMT,2210.00\n"
                            "M-100023,\"Sunday, 03-15-2026 103000z\",2310.00\n"
                            "M-100024,\"03-15-2026 103000 AM\",2410.00\n"
                            "M-100025,\"03-15-2026 103000z AM\",2510.00\n"
                            "M-100026,\"03-15-2026 103000 AM Z\",2610.00\n"
                            "M-100027,03-15-2026 1030z,2710.00\n"
                            "M-100028,03-15-2026 1030,2810.00\n"
                            "M-100029,15-03-2026 1030z,2910.00\n"
                            "M-100030,03-15-26 1030z,3010.00\n"
                            "M-100031,\"Sunday, 03-15-2026 1030z\",3110.00\n"
                            "M-100032,\"03-15-2026 1030 AM\",3210.00\n"
                            "M-100033,26-03-15T1030z,3310.00\n"
                            "M-100034,26-03-15 103000z,3410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 34)
            for row in rows[:32]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[32]["service_date"], "2015-03-26")
            self.assertEqual(rows[33]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 34)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_noseconds_and_space_colonless_hyphen_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02-30-2026T1030z,120.50\n"
                            "M-100002,03-15-2026T1030zz,200.00\n"
                            "M-100003,03-15-2026T1030+99:99,310.00\n"
                            "M-100004,\"Funday, 03-15-2026T1030z\",410.00\n"
                            "M-100005,\"03-15-2026T1030 XM\",510.00\n"
                            "M-100006,15-13-2026T1030z,610.00\n"
                            "M-100007,03-15-2026T1030 XYZ,710.00\n"
                            "M-100008,\"03-15-2026T1030 AM +99:99\",810.00\n"
                            "M-100009,02-30-26T1030z,910.00\n"
                            "M-100010,03-15-2026T1030.123z,1010.00\n"
                            "M-100011,03-15-2026T10300z,1110.00\n"
                            "M-100012,03-15-2026T1030000z,1210.00\n"
                            "M-100013,02-30-2026 103000z,1310.00\n"
                            "M-100014,03-15-2026 103000zz,1410.00\n"
                            "M-100015,03-15-2026 103000+99:99,1510.00\n"
                            "M-100016,\"Funday, 03-15-2026 103000z\",1610.00\n"
                            "M-100017,\"03-15-2026 103000 XM\",1710.00\n"
                            "M-100018,03-15-2026 103000 XYZ,1810.00\n"
                            "M-100019,02-30-2026 1030z,1910.00\n"
                            "M-100020,03-15-2026 10300z,2010.00\n"
                            "M-100021,03-15-2026 1030000z,2110.00\n"
                            "M-100022,\"03-15-2026 1030 AM +99:99\",2210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 22)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 22)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 22})

    def test_read_claims_csv_normalizes_colonless_slash_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,03/15/2026T103000z,120.50\n"
                            "M-100002,15/03/2026T103000z,200.00\n"
                            "M-100003,03/15/26T103000z,310.00\n"
                            "M-100004,03/15/2026T103000Z,410.00\n"
                            "M-100005,03/15/2026T103000,510.00\n"
                            "M-100006,03/15/2026T103000+05:30,610.00\n"
                            "M-100007,03/15/2026T103000+0530,710.00\n"
                            "M-100008,03/15/2026T103000 GMT,810.00\n"
                            "M-100009,\"Sunday, 03/15/2026T103000z\",910.00\n"
                            "M-100010,\"03/15/2026T103000 AM\",1010.00\n"
                            "M-100011,\"03/15/2026T103000z AM\",1110.00\n"
                            "M-100012,\"03/15/2026T103000 AM Z\",1210.00\n"
                            "M-100013,\"03/15/2026T103000 AM GMT\",1310.00\n"
                            "M-100014,\"03/15/2026T103000 GMT AM\",1410.00\n"
                            "M-100015,03/15/2026T103000.123z,1510.00\n"
                            "M-100016,03/15/2026T103000am,1610.00\n"
                            "M-100017,15/03/26T103000z,1710.00\n"
                            "M-100018,2026/03/15T103000z,1810.00\n"
                            "M-100019,03/15/2026T1030z,1910.00\n"
                            "M-100020,15/03/2026T1030z,2010.00\n"
                            "M-100021,03/15/26T1030z,2110.00\n"
                            "M-100022,03/15/2026T1030,2210.00\n"
                            "M-100023,03/15/2026T1030+05:30,2310.00\n"
                            "M-100024,03/15/2026T1030 GMT,2410.00\n"
                            "M-100025,\"Sunday, 03/15/2026T1030z\",2510.00\n"
                            "M-100026,\"03/15/2026T1030 AM\",2610.00\n"
                            "M-100027,\"03/15/2026T1030z AM\",2710.00\n"
                            "M-100028,03/15/2026 103000z,2810.00\n"
                            "M-100029,03/15/2026 103000,2910.00\n"
                            "M-100030,15/03/2026 103000z,3010.00\n"
                            "M-100031,03/15/26 103000z,3110.00\n"
                            "M-100032,2026/03/15 103000z,3210.00\n"
                            "M-100033,03/15/2026 103000.123z,3310.00\n"
                            "M-100034,03/15/2026 103000+05:30,3410.00\n"
                            "M-100035,03/15/2026 103000 GMT,3510.00\n"
                            "M-100036,\"Sunday, 03/15/2026 103000z\",3610.00\n"
                            "M-100037,\"03/15/2026 103000 AM\",3710.00\n"
                            "M-100038,\"03/15/2026 103000z AM\",3810.00\n"
                            "M-100039,\"03/15/2026 103000 AM Z\",3910.00\n"
                            "M-100040,03/15/2026 1030z,4010.00\n"
                            "M-100041,03/15/2026 1030,4110.00\n"
                            "M-100042,15/03/2026 1030z,4210.00\n"
                            "M-100043,03/15/26 1030z,4310.00\n"
                            "M-100044,\"Sunday, 03/15/2026 1030z\",4410.00\n"
                            "M-100045,\"03/15/2026 1030 AM\",4510.00\n"
                            "M-100046,26/03/15T103000z,4610.00\n"
                            "M-100047,26/03/15 103000z,4710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 47)
            for row in rows[:45]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[45]["service_date"], "2015-03-26")
            self.assertEqual(rows[46]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 47)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_colonless_slash_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,02/30/2026T103000z,120.50\n"
                            "M-100002,03/15/2026T103000zz,200.00\n"
                            "M-100003,03/15/2026T103000+99:99,310.00\n"
                            "M-100004,\"Funday, 03/15/2026T103000z\",410.00\n"
                            "M-100005,\"03/15/2026T103000 XM\",510.00\n"
                            "M-100006,15/13/2026T103000z,610.00\n"
                            "M-100007,03/15/2026T103000 XYZ,710.00\n"
                            "M-100008,\"03/15/2026T103000 AM +99:99\",810.00\n"
                            "M-100009,02/30/26T103000z,910.00\n"
                            "M-100010,03/15/2026T256000z,1010.00\n"
                            "M-100011,03/15/2026T106000z,1110.00\n"
                            "M-100012,03/15/2026T1030000z,1210.00\n"
                            "M-100013,02/30/2026T1030z,1310.00\n"
                            "M-100014,03/15/2026T1030+99:99,1410.00\n"
                            "M-100015,03/15/2026T103060z,1510.00\n"
                            "M-100016,02/30/2026 103000z,1610.00\n"
                            "M-100017,03/15/2026 103000zz,1710.00\n"
                            "M-100018,03/15/2026 103000+99:99,1810.00\n"
                            "M-100019,\"Funday, 03/15/2026 103000z\",1910.00\n"
                            "M-100020,\"03/15/2026 103000 XM\",2010.00\n"
                            "M-100021,03/15/2026 256000z,2110.00\n"
                            "M-100022,03/15/2026 1030000z,2210.00\n"
                            "M-100023,03/15/2026T103000.1234567z,2310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 23)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 23)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 23})

    def test_read_claims_csv_normalizes_colonless_dot_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15T103000z,120.50\n"
                            "M-100002,03.15.2026T103000z,200.00\n"
                            "M-100003,15.03.2026T103000z,310.00\n"
                            "M-100004,03.15.26T103000z,410.00\n"
                            "M-100005,15.03.26T103000z,510.00\n"
                            "M-100006,2026.03.15T103000Z,610.00\n"
                            "M-100007,2026.03.15T103000,710.00\n"
                            "M-100008,2026.03.15T103000+05:30,810.00\n"
                            "M-100009,2026.03.15T103000+0530,910.00\n"
                            "M-100010,2026.03.15T103000 GMT,1010.00\n"
                            "M-100011,\"Sunday, 2026.03.15T103000z\",1110.00\n"
                            "M-100012,\"2026.03.15T103000 AM\",1210.00\n"
                            "M-100013,\"2026.03.15T103000z AM\",1310.00\n"
                            "M-100014,\"2026.03.15T103000 AM Z\",1410.00\n"
                            "M-100015,\"2026.03.15T103000 AM GMT\",1510.00\n"
                            "M-100016,\"2026.03.15T103000 GMT AM\",1610.00\n"
                            "M-100017,2026.03.15T103000.123z,1710.00\n"
                            "M-100018,2026.03.15T103000am,1810.00\n"
                            "M-100019,26.03.15T103000z,1910.00\n"
                            "M-100020,26.03.2015T103000z,2010.00\n"
                            "M-100021,2026.03.15T1030z,2110.00\n"
                            "M-100022,03.15.2026T1030z,2210.00\n"
                            "M-100023,15.03.2026T1030z,2310.00\n"
                            "M-100024,03.15.26T1030z,2410.00\n"
                            "M-100025,2026.03.15T1030,2510.00\n"
                            "M-100026,2026.03.15T1030+05:30,2610.00\n"
                            "M-100027,2026.03.15T1030 GMT,2710.00\n"
                            "M-100028,\"Sunday, 2026.03.15T1030z\",2810.00\n"
                            "M-100029,\"2026.03.15T1030 AM\",2910.00\n"
                            "M-100030,\"2026.03.15T1030z AM\",3010.00\n"
                            "M-100031,2026.03.15T1030.123z,3110.00\n"
                            "M-100032,2026.03.15 103000z,3210.00\n"
                            "M-100033,2026.03.15 103000,3310.00\n"
                            "M-100034,03.15.2026 103000z,3410.00\n"
                            "M-100035,15.03.2026 103000z,3510.00\n"
                            "M-100036,03.15.26 103000z,3610.00\n"
                            "M-100037,2026.03.15 103000.123z,3710.00\n"
                            "M-100038,2026.03.15 103000+05:30,3810.00\n"
                            "M-100039,2026.03.15 103000 GMT,3910.00\n"
                            "M-100040,\"Sunday, 2026.03.15 103000z\",4010.00\n"
                            "M-100041,\"2026.03.15 103000 AM\",4110.00\n"
                            "M-100042,\"2026.03.15 103000z AM\",4210.00\n"
                            "M-100043,\"2026.03.15 103000 AM Z\",4310.00\n"
                            "M-100044,2026.03.15 1030z,4410.00\n"
                            "M-100045,2026.03.15 1030,4510.00\n"
                            "M-100046,03.15.26 1030z,4610.00\n"
                            "M-100047,\"Sunday, 2026.03.15 1030z\",4710.00\n"
                            "M-100048,\"2026.03.15 1030 AM\",4810.00\n"
                            "M-100049,26.03.15 103000z,4910.00\n"
                            "M-100050,26.03.2015 103000z,5010.00\n"
                            "M-100051,2026.03.15T10300z,5110.00\n"
                            "M-100052,2026.03.15T103z,5210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 52)
            for row in rows[:18]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[18]["service_date"], "2015-03-26")
            self.assertEqual(rows[19]["service_date"], "2015-03-26")
            for row in rows[20:48]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[48]["service_date"], "2015-03-26")
            self.assertEqual(rows[49]["service_date"], "2015-03-26")
            for row in rows[50:52]:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 52)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_colonless_dot_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.02.30T103000z,120.50\n"
                            "M-100002,2026.03.15T103000zz,200.00\n"
                            "M-100003,2026.03.15T103000+99:99,310.00\n"
                            "M-100004,\"Funday, 2026.03.15T103000z\",410.00\n"
                            "M-100005,\"2026.03.15T103000 XM\",510.00\n"
                            "M-100006,15.13.2026T103000z,610.00\n"
                            "M-100007,2026.03.15T103000 XYZ,710.00\n"
                            "M-100008,\"2026.03.15T103000 AM +99:99\",810.00\n"
                            "M-100009,02.30.26T103000z,910.00\n"
                            "M-100010,2026.03.15T256000z,1010.00\n"
                            "M-100011,2026.03.15T106000z,1110.00\n"
                            "M-100012,2026.03.15T1030000z,1210.00\n"
                            "M-100013,2026.02.30T1030z,1310.00\n"
                            "M-100014,2026.03.15T1030+99:99,1410.00\n"
                            "M-100015,2026.03.15T103060z,1510.00\n"
                            "M-100016,2026.02.30 103000z,1610.00\n"
                            "M-100017,2026.03.15 103000zz,1710.00\n"
                            "M-100018,2026.03.15 103000+99:99,1810.00\n"
                            "M-100019,\"Funday, 2026.03.15 103000z\",1910.00\n"
                            "M-100020,\"2026.03.15 103000 XM\",2010.00\n"
                            "M-100021,2026.03.15 256000z,2110.00\n"
                            "M-100022,2026.03.15 1030000z,2210.00\n"
                            "M-100023,2026.03.15T103000.1234567z,2310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 23)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 23)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 23})

    def test_read_claims_csv_normalizes_colonless_underscore_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_03_15T103000z,120.50\n"
                            "M-100002,03_15_2026T103000z,200.00\n"
                            "M-100003,15_03_2026T103000z,310.00\n"
                            "M-100004,03_15_26T103000z,410.00\n"
                            "M-100005,15_03_26T103000z,510.00\n"
                            "M-100006,2026_03_15T103000Z,610.00\n"
                            "M-100007,2026_03_15T103000,710.00\n"
                            "M-100008,2026_03_15T103000+05:30,810.00\n"
                            "M-100009,2026_03_15T103000+0530,910.00\n"
                            "M-100010,2026_03_15T103000 GMT,1010.00\n"
                            "M-100011,\"Sunday, 2026_03_15T103000z\",1110.00\n"
                            "M-100012,\"2026_03_15T103000 AM\",1210.00\n"
                            "M-100013,\"2026_03_15T103000z AM\",1310.00\n"
                            "M-100014,\"2026_03_15T103000 AM Z\",1410.00\n"
                            "M-100015,\"2026_03_15T103000 AM GMT\",1510.00\n"
                            "M-100016,\"2026_03_15T103000 GMT AM\",1610.00\n"
                            "M-100017,2026_03_15T103000.123z,1710.00\n"
                            "M-100018,2026_03_15T103000am,1810.00\n"
                            "M-100019,26_03_15T103000z,1910.00\n"
                            "M-100020,26_03_2015T103000z,2010.00\n"
                            "M-100021,2026_03_15T1030z,2110.00\n"
                            "M-100022,03_15_2026T1030z,2210.00\n"
                            "M-100023,15_03_2026T1030z,2310.00\n"
                            "M-100024,03_15_26T1030z,2410.00\n"
                            "M-100025,2026_03_15T1030,2510.00\n"
                            "M-100026,2026_03_15T1030+05:30,2610.00\n"
                            "M-100027,2026_03_15T1030 GMT,2710.00\n"
                            "M-100028,\"Sunday, 2026_03_15T1030z\",2810.00\n"
                            "M-100029,\"2026_03_15T1030 AM\",2910.00\n"
                            "M-100030,\"2026_03_15T1030z AM\",3010.00\n"
                            "M-100031,2026_03_15 103000z,3110.00\n"
                            "M-100032,2026_03_15 103000,3210.00\n"
                            "M-100033,03_15_2026 103000z,3310.00\n"
                            "M-100034,15_03_2026 103000z,3410.00\n"
                            "M-100035,03_15_26 103000z,3510.00\n"
                            "M-100036,2026_03_15 103000.123z,3610.00\n"
                            "M-100037,2026_03_15 103000+05:30,3710.00\n"
                            "M-100038,2026_03_15 103000 GMT,3810.00\n"
                            "M-100039,\"Sunday, 2026_03_15 103000z\",3910.00\n"
                            "M-100040,\"2026_03_15 103000 AM\",4010.00\n"
                            "M-100041,\"2026_03_15 103000z AM\",4110.00\n"
                            "M-100042,\"2026_03_15 103000 AM Z\",4210.00\n"
                            "M-100043,2026_03_15 1030z,4310.00\n"
                            "M-100044,2026_03_15 1030,4410.00\n"
                            "M-100045,03_15_26 1030z,4510.00\n"
                            "M-100046,\"Sunday, 2026_03_15 1030z\",4610.00\n"
                            "M-100047,\"2026_03_15 1030 AM\",4710.00\n"
                            "M-100048,26_03_15 103000z,4810.00\n"
                            "M-100049,26_03_2015 103000z,4910.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 49)
            for row in rows[:18]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[18]["service_date"], "2015-03-26")
            self.assertEqual(rows[19]["service_date"], "2015-03-26")
            for row in rows[20:47]:
                self.assertEqual(row["service_date"], "2026-03-15")
            self.assertEqual(rows[47]["service_date"], "2015-03-26")
            self.assertEqual(rows[48]["service_date"], "2015-03-26")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 49)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_colonless_underscore_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026_02_30T103000z,120.50\n"
                            "M-100002,2026_03_15T103000zz,200.00\n"
                            "M-100003,2026_03_15T103000+99:99,310.00\n"
                            "M-100004,\"Funday, 2026_03_15T103000z\",410.00\n"
                            "M-100005,\"2026_03_15T103000 XM\",510.00\n"
                            "M-100006,15_13_2026T103000z,610.00\n"
                            "M-100007,2026_03_15T103000 XYZ,710.00\n"
                            "M-100008,\"2026_03_15T103000 AM +99:99\",810.00\n"
                            "M-100009,02_30_26T103000z,910.00\n"
                            "M-100010,2026_03_15T256000z,1010.00\n"
                            "M-100011,2026_03_15T106000z,1110.00\n"
                            "M-100012,2026_03_15T1030000z,1210.00\n"
                            "M-100013,2026_02_30T1030z,1310.00\n"
                            "M-100014,2026_03_15T1030+99:99,1410.00\n"
                            "M-100015,2026_03_15T103060z,1510.00\n"
                            "M-100016,2026_02_30 103000z,1610.00\n"
                            "M-100017,2026_03_15 103000zz,1710.00\n"
                            "M-100018,2026_03_15 103000+99:99,1810.00\n"
                            "M-100019,\"Funday, 2026_03_15 103000z\",1910.00\n"
                            "M-100020,\"2026_03_15 103000 XM\",2010.00\n"
                            "M-100021,2026_03_15 256000z,2110.00\n"
                            "M-100022,2026_03_15 1030000z,2210.00\n"
                            "M-100023,2026_03_15T103000.1234567z,2310.00\n"
                            "M-100024,2026_03_15T1030.123z,2410.00\n"
                            "M-100025,2026_03_15T10300z,2510.00\n"
                            "M-100026,2026_03_15T103000GMT,2610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 26)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 26)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 26})

    def test_read_claims_csv_normalizes_colonless_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026T103000z\",120.50\n"
                            "M-100002,\"March 15, 2026T103000z\",200.00\n"
                            "M-100003,15 Mar 2026T103000z,310.00\n"
                            "M-100004,15-Mar-2026T103000z,410.00\n"
                            "M-100005,Mar-15-2026T103000z,510.00\n"
                            "M-100006,\"Mar 15, 2026T103000Z\",610.00\n"
                            "M-100007,\"Mar 15, 2026T103000\",710.00\n"
                            "M-100008,\"Mar 15, 2026T103000+05:30\",810.00\n"
                            "M-100009,\"Mar 15, 2026T103000+0530\",910.00\n"
                            "M-100010,\"Mar 15, 2026T103000 GMT\",1010.00\n"
                            "M-100011,\"Mar 15, 2026T103000.123z\",1110.00\n"
                            "M-100012,\"Mar 15, 2026 103000z\",1210.00\n"
                            "M-100013,\"Mar 15, 2026 103000\",1310.00\n"
                            "M-100014,15 Mar 2026 103000z,1410.00\n"
                            "M-100015,\"Mar 15, 2026T1030z\",1510.00\n"
                            "M-100016,\"Mar 15, 2026T1030\",1610.00\n"
                            "M-100017,\"Mar 15, 2026 1030z\",1710.00\n"
                            "M-100018,\"Mar 15, 2026T103000 AM\",1810.00\n"
                            "M-100019,\"Mar 15, 2026T103000z AM\",1910.00\n"
                            "M-100020,\"Mar 15, 2026T103000 AM Z\",2010.00\n"
                            "M-100021,\"Mar 15, 2026T103000 AM GMT\",2110.00\n"
                            "M-100022,\"Mar 15, 2026T103000 GMT AM\",2210.00\n"
                            "M-100023,\"Mar 15, 2026T103000am\",2310.00\n"
                            "M-100024,\"Sunday, Mar 15, 2026T103000z\",2410.00\n"
                            "M-100025,\"Mar 15, 26T103000z\",2510.00\n"
                            "M-100026,15 Mar 26T103000z,2610.00\n"
                            "M-100027,\"mar 15, 2026T103000z\",2710.00\n"
                            "M-100028,\"Mar 15th, 2026T103000z\",2810.00\n"
                            "M-100029,15th of March 2026T103000z,2910.00\n"
                            "M-100030,\"Mar 15, 2026T103000.123456z\",3010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 30)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 30)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_colonless_month_name_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026T103000z\",120.50\n"
                            "M-100002,\"Mar 15, 2026T103000zz\",200.00\n"
                            "M-100003,\"Mar 15, 2026T103000+99:99\",310.00\n"
                            "M-100004,\"Funday, Mar 15, 2026T103000z\",410.00\n"
                            "M-100005,\"Mar 15, 2026T103000 XM\",510.00\n"
                            "M-100006,\"Mar 32, 2026T103000z\",610.00\n"
                            "M-100007,\"Mar 15, 2026T103000 XYZ\",710.00\n"
                            "M-100008,\"Mar 15, 2026T103000 AM +99:99\",810.00\n"
                            "M-100009,\"Feb 30, 26T103000z\",910.00\n"
                            "M-100010,\"Mar 15, 2026T256000z\",1010.00\n"
                            "M-100011,\"Mar 15, 2026T106000z\",1110.00\n"
                            "M-100012,\"Mar 15, 2026T1030000z\",1210.00\n"
                            "M-100013,\"Feb 30, 2026T1030z\",1310.00\n"
                            "M-100014,\"Mar 15, 2026T1030+99:99\",1410.00\n"
                            "M-100015,\"Mar 15, 2026T103060z\",1510.00\n"
                            "M-100016,\"Feb 30, 2026 103000z\",1610.00\n"
                            "M-100017,\"Mar 15, 2026 103000zz\",1710.00\n"
                            "M-100018,\"Mar 15, 2026 103000+99:99\",1810.00\n"
                            "M-100019,\"Funday, Mar 15, 2026 103000z\",1910.00\n"
                            "M-100020,\"Mar 15, 2026 103000 XM\",2010.00\n"
                            "M-100021,\"Mar 15, 2026 256000z\",2110.00\n"
                            "M-100022,\"Mar 15, 2026 1030000z\",2210.00\n"
                            "M-100023,\"Mar 15, 2026T103000.1234567z\",2310.00\n"
                            "M-100024,\"Mar 15, 2026T1030.123z\",2410.00\n"
                            "M-100025,\"Mar 15, 2026T10300z\",2510.00\n"
                            "M-100026,\"Mar 15, 2026T103000GMT\",2610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 26)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 26)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 26})

    def test_read_claims_csv_normalizes_space_separated_colonless_month_name_datetimes_two_digit_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15 Mar 26 103000,120.50\n"
                            "M-100002,15 Mar 26 1030,200.00\n"
                            "M-100003,15 Mar 26 103000.123,310.00\n"
                            "M-100004,15-Mar-26 103000,410.00\n"
                            "M-100005,15-Mar-26 1030,510.00\n"
                            "M-100006,\"March 15 26 103000\",610.00\n"
                            "M-100007,\"March 15 26 1030\",710.00\n"
                            "M-100008,\"March 15 26 103000.123\",810.00\n"
                            "M-100009,Mar-15-26 103000,910.00\n"
                            "M-100010,Mar-15-26 1030,1010.00\n"
                            "M-100011,15 Mar 26 103000z,1110.00\n"
                            "M-100012,15 Mar 26 103000 AM,1210.00\n"
                            "M-100013,\"Sunday, 15 Mar 26 103000\",1310.00\n"
                            "M-100014,15 mar 26 103000,1410.00\n"
                            "M-100015,15th of March 26 103000,1510.00\n"
                            "M-100016,\"March 15 26 103000 GMT\",1610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 16)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 16)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_separated_colonless_month_name_datetimes_two_digit_year_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15 Mar 26 10300,120.50\n"
                            "M-100002,15 Mar 26 1030.123,200.00\n"
                            "M-100003,15 Mar 26 1030000,310.00\n"
                            "M-100004,15 Mar 26 103000.1234567,410.00\n"
                            "M-100005,15 Mar 26 256000,510.00\n"
                            "M-100006,15 Mar 26 10300z,610.00\n"
                            "M-100007,15 Mar 26 10300 AM,710.00\n"
                            "M-100008,\"Sunday, 15 Mar 26 10300\",810.00\n"
                            "M-100009,15-Mar-26 10300,910.00\n"
                            "M-100010,15-Mar-26 1030.123,1010.00\n"
                            "M-100011,\"March 15 26 10300\",1110.00\n"
                            "M-100012,\"March 15 26 1030.123\",1210.00\n"
                            "M-100013,\"March 15 26 1030000\",1310.00\n"
                            "M-100014,\"March 15 26 256000\",1410.00\n"
                            "M-100015,\"March 15 26 10300z\",1510.00\n"
                            "M-100016,Mar-15-26 10300,1610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 16)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 16)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 16})

    def test_read_claims_csv_normalizes_sept_month_name_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Sept 15, 2026\",120.50\n"
                            "M-100002,15 Sept 2026,200.00\n"
                            "M-100003,\"Sept. 15, 2026\",310.00\n"
                            "M-100004,15 Sept. 2026,410.00\n"
                            "M-100005,Sept-15-2026,510.00\n"
                            "M-100006,15-Sept-2026,610.00\n"
                            "M-100007,\"Sept 15, 26\",710.00\n"
                            "M-100008,15 Sept 26,810.00\n"
                            "M-100009,\"sept 15, 2026\",910.00\n"
                            "M-100010,\"SEPT 15, 2026\",1010.00\n"
                            "M-100011,\"Sept 15 2026 10:30:00\",1110.00\n"
                            "M-100012,\"Sept 15, 2026 10:30:00 AM\",1210.00\n"
                            "M-100013,\"Sept 15, 2026T103000z\",1310.00\n"
                            "M-100014,\"Sept 15, 2026 10:30:00 GMT\",1410.00\n"
                            "M-100015,\"Sunday, Sept 15, 2026\",1510.00\n"
                            "M-100016,15th of Sept 2026,1610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 16)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-09-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 16)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_sept_month_name_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Sept 31, 2026\",120.50\n"
                            "M-100002,\"Sept 15, 2026T10300z\",200.00\n"
                            "M-100003,\"Sept 15, 2026T1030.123z\",310.00\n"
                            "M-100004,\"Sept 15, 2026T1030000z\",410.00\n"
                            "M-100005,\"Sept 15, 2026T256000z\",510.00\n"
                            "M-100006,\"Sept 15, 2026 10:30:00 XYZ\",610.00\n"
                            "M-100007,\"Sept 15, 2026 10:30:00 XM\",710.00\n"
                            "M-100008,\"Funday, Sept 15, 2026\",810.00\n"
                            "M-100009,\"Sept 15, 2026 10:30:00 +99:99\",910.00\n"
                            "M-100010,\"Sept 32, 2026\",1010.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 10)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 10)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 10})

    def test_read_claims_csv_normalizes_period_month_name_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar. 15, 2026\",120.50\n"
                            "M-100002,15 Mar. 2026,200.00\n"
                            "M-100003,\"Mar. 15 2026\",310.00\n"
                            "M-100004,Mar.-15-2026,410.00\n"
                            "M-100005,15-Mar.-2026,510.00\n"
                            "M-100006,\"Mar. 15, 26\",610.00\n"
                            "M-100007,15 Mar. 26,710.00\n"
                            "M-100008,\"mar. 15, 2026\",810.00\n"
                            "M-100009,\"MAR. 15, 2026\",910.00\n"
                            "M-100010,\"Jan. 5, 2026\",1010.00\n"
                            "M-100011,\"Dec. 31, 2026\",1110.00\n"
                            "M-100012,\"Mar. 15, 2026 10:30:00\",1210.00\n"
                            "M-100013,\"Mar. 15, 2026 10:30:00 AM\",1310.00\n"
                            "M-100014,\"Mar. 15, 2026T103000z\",1410.00\n"
                            "M-100015,\"Sunday, Mar. 15, 2026\",1510.00\n"
                            "M-100016,15th of Mar. 2026,1610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 16)
            expected = ["2026-03-15"] * 9 + ["2026-01-05",
                                              "2026-12-31",
                                              "2026-03-15",
                                              "2026-03-15",
                                              "2026-03-15",
                                              "2026-03-15",
                                              "2026-03-15"]
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 16)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_period_month_name_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb. 30, 2026\",120.50\n"
                            "M-100002,\"Mar. 15, 2026T10300z\",200.00\n"
                            "M-100003,\"Mar. 15, 2026T1030.123z\",310.00\n"
                            "M-100004,\"Mar. 15, 2026 10:30:00 XYZ\",410.00\n"
                            "M-100005,\"Funday, Mar. 15, 2026\",510.00\n"
                            "M-100006,\"Mar. 32, 2026\",610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 6)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 6)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 6})

    def test_read_claims_csv_normalizes_full_period_month_name_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"March. 15, 2026\",120.50\n"
                            "M-100002,15 March. 2026,200.00\n"
                            "M-100003,\"March. 15 2026\",310.00\n"
                            "M-100004,March.-15-2026,410.00\n"
                            "M-100005,15-March.-2026,510.00\n"
                            "M-100006,\"March. 15, 26\",610.00\n"
                            "M-100007,15 March. 26,710.00\n"
                            "M-100008,\"march. 15, 2026\",810.00\n"
                            "M-100009,\"MARCH. 15, 2026\",910.00\n"
                            "M-100010,\"January. 5, 2026\",1010.00\n"
                            "M-100011,\"December. 31, 2026\",1110.00\n"
                            "M-100012,\"March. 15, 2026 10:30:00\",1210.00\n"
                            "M-100013,\"March. 15, 2026 10:30:00 AM\",1310.00\n"
                            "M-100014,\"March. 15, 2026T103000z\",1410.00\n"
                            "M-100015,\"Sunday, March. 15, 2026\",1510.00\n"
                            "M-100016,15th of March. 2026,1610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 16)
            expected = ["2026-03-15"] * 9 + ["2026-01-05",
                                              "2026-12-31",
                                              "2026-03-15",
                                              "2026-03-15",
                                              "2026-03-15",
                                              "2026-03-15",
                                              "2026-03-15"]
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 16)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_full_period_month_name_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"February. 30, 2026\",120.50\n"
                            "M-100002,\"March. 15, 2026T10300z\",200.00\n"
                            "M-100003,\"March. 15, 2026T1030.123z\",310.00\n"
                            "M-100004,\"March. 15, 2026 10:30:00 XYZ\",410.00\n"
                            "M-100005,\"Funday, March. 15, 2026\",510.00\n"
                            "M-100006,\"March. 32, 2026\",610.00\n"
                            "M-100007,\"March.. 15, 2026\",710.00\n"
                            "M-100008,\"March.ing 15, 2026\",810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_read_claims_csv_normalizes_trailing_period_year_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"March 15, 2026.\",120.50\n"
                            "M-100002,15 March 2026.,200.00\n"
                            "M-100003,\"March 15 2026.\",310.00\n"
                            "M-100004,\"Mar 15, 2026.\",410.00\n"
                            "M-100005,\"March. 15, 2026.\",510.00\n"
                            "M-100006,\"March 15, 26.\",610.00\n"
                            "M-100007,\"March 15, 2026 10:30:00.\",710.00\n"
                            "M-100008,\"Sunday, March 15, 2026.\",810.00\n"
                            "M-100009,15th of March 2026.,910.00\n"
                            "M-100010,March-15-2026.,1010.00\n"
                            "M-100011,15-March-2026.,1110.00\n"
                            "M-100012,\"march 15, 2026.\",1210.00\n"
                            "M-100013,\"January 5, 2026.\",1310.00\n"
                            "M-100014,\"December 31, 2026.\",1410.00\n"
                            "M-100015,\"Sept 15, 2026.\",1510.00\n"
                            "M-100016,\"Mar. 15, 2026.\",1610.00\n"
                            "M-100017,\"March 15, 2026T103000.\",1710.00\n"
                            "M-100018,\"March 15, 2026 10:30:00.123.\",1810.00\n"
                            "M-100019,\"March 15, 26 10:30:00.\",1910.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 19)
            expected = ["2026-03-15"] * 12 + ["2026-01-05",
                                               "2026-12-31",
                                               "2026-09-15",
                                               "2026-03-15",
                                               "2026-03-15",
                                               "2026-03-15",
                                               "2026-03-15"]
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 19)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_trailing_period_year_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"March 15, 2026..\",120.50\n"
                            "M-100002,\"February 30, 2026.\",200.00\n"
                            "M-100003,\"March 15, 2026.10:30:00\",310.00\n"
                            "M-100004,\"March 32, 2026.\",410.00\n"
                            "M-100005,\"Funday, March 15, 2026.\",510.00\n"
                            "M-100006,\"March 15, 2026. XYZ\",610.00\n"
                            "M-100007,\"March 15, 2026. 10300\",710.00\n"
                            "M-100008,\"March 15, 2026T10300.\",810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_read_claims_csv_normalizes_missing_space_after_month_period_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"March.15, 2026\",120.50\n"
                            "M-100002,15 March.2026,200.00\n"
                            "M-100003,\"Mar.15, 2026\",310.00\n"
                            "M-100004,15 Mar.2026,410.00\n"
                            "M-100005,\"March.15 2026\",510.00\n"
                            "M-100006,\"March.15, 26\",610.00\n"
                            "M-100007,15 March.26,710.00\n"
                            "M-100008,\"Sunday, March.15, 2026\",810.00\n"
                            "M-100009,\"March.15, 2026 10:30:00\",910.00\n"
                            "M-100010,\"March.15, 2026T103000z\",1010.00\n"
                            "M-100011,\"March.15, 2026 10:30:00 AM\",1110.00\n"
                            "M-100012,\"March.15th, 2026\",1210.00\n"
                            "M-100013,15th March.2026,1310.00\n"
                            "M-100014,\"Sept.15, 2026\",1410.00\n"
                            "M-100015,\"Jan.5, 2026\",1510.00\n"
                            "M-100016,\"March.15, 2026.\",1610.00\n"
                            "M-100017,\"March.15, 2026 10:30:00 GMT\",1710.00\n"
                            "M-100018,\"march.15, 2026\",1810.00\n"
                            "M-100019,15th of March.2026,1910.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 19)
            expected = ["2026-03-15"] * 13 + ["2026-09-15",
                                               "2026-01-05",
                                               "2026-03-15",
                                               "2026-03-15",
                                               "2026-03-15",
                                               "2026-03-15"]
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 19)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_missing_space_after_month_period_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb.30, 2026\",120.50\n"
                            "M-100002,\"March.32, 2026\",200.00\n"
                            "M-100003,\"March.15, 2026T10300z\",310.00\n"
                            "M-100004,\"Funday, March.15, 2026\",410.00\n"
                            "M-100005,\"March.ing 15, 2026\",510.00\n"
                            "M-100006,\"March..15, 2026\",610.00\n"
                            "M-100007,\"March.15, 2026 XYZ\",710.00\n"
                            "M-100008,\"March.15, 2026.10:30:00\",810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_read_claims_csv_normalizes_period_before_year_hyphenated_month_name_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15-Mar.2026,120.50\n"
                            "M-100002,15-March.2026,200.00\n"
                            "M-100003,15-Sept.2026,310.00\n"
                            "M-100004,15-Mar.26,410.00\n"
                            "M-100005,15-Mar.2026 10:30:00,510.00\n"
                            "M-100006,15-Mar.2026T09:00:00,610.00\n"
                            "M-100007,15-Mar.2026 10:30:00 AM,710.00\n"
                            "M-100008,15-Mar.2026 10:30:00 PDT,810.00\n"
                            "M-100009,\"Sunday, 15-Mar.2026\",910.00\n"
                            "M-100010,15-mar.2026,1010.00\n"
                            "M-100011,15-MAR.2026,1110.00\n"
                            "M-100012,15-Mar.2026.,1210.00\n"
                            "M-100013,15-Jan.2026,1310.00\n"
                            "M-100014,15-Dec.2026,1410.00\n"
                            "M-100015,Mar-15.2026,1510.00\n"
                            "M-100016,Mar-15.2026 10:30:00,1610.00\n"
                            "M-100017,Mar-15.2026T09:00:00,1710.00\n"
                            "M-100018,Mar-15.26,1810.00\n"
                            "M-100019,15-Mar.2026T103000z,1910.00\n"
                            "M-100020,15-Mar.2026 103000,2010.00\n"
                            "M-100021,15-Mar.26 103000,2110.00\n"
                            "M-100022,15-Mar.2026 10:30:00.123456+05:30,2210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 22)
            expected = ["2026-03-15", "2026-03-15",
                        "2026-09-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-01-15", "2026-12-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15"]
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 22)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_period_before_year_hyphenated_month_name_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,15-Mar..2026,120.50\n"
                            "M-100002,15-Mar.2026.10:30:00,200.00\n"
                            "M-100003,15-Mar.2026 XYZ,310.00\n"
                            "M-100004,30-Feb.2026,410.00\n"
                            "M-100005,\"Funday, 15-Mar.2026\",510.00\n"
                            "M-100006,15-Mar.2026T10300z,610.00\n"
                            "M-100007,15-Mar.2026 10300,710.00\n"
                            "M-100008,Mar-15..2026,810.00\n"
                            "M-100009,Mar-15.2026.10:30:00,910.00\n"
                            "M-100010,Mar-15.2026 XYZ,1010.00\n"
                            "M-100011,15-Mar.202610,1110.00\n"
                            "M-100012,15-Mar.2026. 10300,1210.00\n"
                            "M-100013,15-Mar.2026T1030000z,1310.00\n"
                            "M-100014,Mar-15.2026T10300z,1410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 14)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 14)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 14})

    def test_read_claims_csv_normalizes_period_after_month_hyphenated_month_first_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,Mar.15-2026,120.50\n"
                            "M-100002,Mar. 15-2026,200.00\n"
                            "M-100003,Mar.15.2026,310.00\n"
                            "M-100004,Mar. 15.2026,410.00\n"
                            "M-100005,March.15-2026,510.00\n"
                            "M-100006,March. 15-2026,610.00\n"
                            "M-100007,March.15.2026,710.00\n"
                            "M-100008,Sept.15-2026,810.00\n"
                            "M-100009,Mar.15-26,910.00\n"
                            "M-100010,Mar.15.26,1010.00\n"
                            "M-100011,Mar.15-2026 10:30:00,1110.00\n"
                            "M-100012,Mar.15-2026T09:00:00,1210.00\n"
                            "M-100013,Mar.15-2026 10:30:00.123,1310.00\n"
                            "M-100014,Mar.15-2026 10:30:00Z,1410.00\n"
                            "M-100015,Mar.15-2026 10:30:00+05:30,1510.00\n"
                            "M-100016,Mar.15-2026 10:30:00 AM,1610.00\n"
                            "M-100017,Mar.15-2026 10:30:00 PDT,1710.00\n"
                            "M-100018,\"Sunday, Mar.15-2026\",1810.00\n"
                            "M-100019,mar.15-2026,1910.00\n"
                            "M-100020,Mar.15-2026.,2010.00\n"
                            "M-100021,Mar.15-2026T103000z,2110.00\n"
                            "M-100022,Mar.15-2026 103000,2210.00\n"
                            "M-100023,Jan.15-2026,2310.00\n"
                            "M-100024,Dec.15-2026,2410.00\n"
                            "M-100025,Mar 15-2026,2510.00\n"
                            "M-100026,Mar 15.2026,2610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 26)
            expected = ["2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-09-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-03-15", "2026-03-15",
                        "2026-01-15", "2026-12-15",
                        "2026-03-15", "2026-03-15"]
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 26)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_period_after_month_hyphenated_month_first_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,Mar..15-2026,120.50\n"
                            "M-100002,Mar.15-2026.10:30:00,200.00\n"
                            "M-100003,Mar.15-2026 XYZ,310.00\n"
                            "M-100004,Feb.30-2026,410.00\n"
                            "M-100005,\"Funday, Mar.15-2026\",510.00\n"
                            "M-100006,Mar.15-2026T10300z,610.00\n"
                            "M-100007,Mar.15-2026 10300,710.00\n"
                            "M-100008,Mar.15-202610,810.00\n"
                            "M-100009,Mar.15-2026. 10300,910.00\n"
                            "M-100010,Mar.15-2026T1030000z,1010.00\n"
                            "M-100011,Mar.15-2026 10:30:00 XYZ,1110.00\n"
                            "M-100012,Mar.15-2026 10:30:00.1234567,1210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 12)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 12)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 12})

    def test_read_claims_csv_normalizes_no_seconds_ampm_hyphenated_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,Mar-15-2026 10:30 AM,120.50\n"
                            "M-100002,15-Mar-2026 10:30 AM,200.00\n"
                            "M-100003,Mar-15-2026 10:30 PM,310.00\n"
                            "M-100004,15-Mar-2026 2:30 pm,410.00\n"
                            "M-100005,March-15-2026 10:30 AM,510.00\n"
                            "M-100006,15-March-2026 10:30 AM,610.00\n"
                            "M-100007,Mar-15-2026T10:30 AM,710.00\n"
                            "M-100008,15-Mar-2026T10:30 AM,810.00\n"
                            "M-100009,Mar-15-2026 10:30 AM Z,910.00\n"
                            "M-100010,15-Mar-2026 10:30 AM GMT,1010.00\n"
                            "M-100011,Mar-15-2026 10:30Z AM,1110.00\n"
                            "M-100012,Mar-15-2026 10:30 AM +05:30,1210.00\n"
                            "M-100013,Mar-15-26 10:30 AM,1310.00\n"
                            "M-100014,15-Mar-26 10:30 AM,1410.00\n"
                            "M-100015,Mar-15-26T10:30 AM,1510.00\n"
                            "M-100016,15-Mar-26T10:30 PM,1610.00\n"
                            "M-100017,\"Sunday, Mar-15-2026 10:30 AM\",1710.00\n"
                            "M-100018,\"Sunday, 15-Mar-2026 10:30 AM\",1810.00\n"
                            "M-100019,Mar-15-2026 10:30am,1910.00\n"
                            "M-100020,Mar.15-2026 10:30 AM,2010.00\n"
                            "M-100021,15-Mar.2026 10:30 AM,2110.00\n"
                            "M-100022,Sept-15-2026 10:30 AM,2210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 22)
            expected = ["2026-03-15"] * 21 + ["2026-09-15"]
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 22)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_no_seconds_ampm_hyphenated_month_name_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,Feb-30-2026 10:30 AM,120.50\n"
                            "M-100002,Mar-15-2026 10:30 XM,200.00\n"
                            "M-100003,Mar-15-2026 25:30 AM,310.00\n"
                            "M-100004,Mar-15-2026 10:60 AM,410.00\n"
                            "M-100005,Mar-15-2026 10:30 AM XYZ,510.00\n"
                            "M-100006,Mar-15-2026 10:30 AM +99:99,610.00\n"
                            "M-100007,\"Funday, Mar-15-2026 10:30 AM\",710.00\n"
                            "M-100008,Mar-15-2026 10:30.123 AM,810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_read_claims_csv_normalizes_t_separated_no_seconds_ampm_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026T10:30 AM\",120.50\n"
                            "M-100002,15 Mar 2026T10:30 AM,200.00\n"
                            "M-100003,\"Mar 15, 2026T10:30 PM\",310.00\n"
                            "M-100004,15 Mar 2026T2:30 pm,410.00\n"
                            "M-100005,\"March 15, 2026T10:30 AM\",510.00\n"
                            "M-100006,15 March 2026T10:30 AM,610.00\n"
                            "M-100007,Mar 15 2026T10:30 AM,710.00\n"
                            "M-100008,15 Mar 2026T10:30 AM,810.00\n"
                            "M-100009,\"Mar 15, 26T10:30 AM\",910.00\n"
                            "M-100010,15 Mar 26T10:30 AM,1010.00\n"
                            "M-100011,\"March 15, 26T10:30 PM\",1110.00\n"
                            "M-100012,15 March 26T10:30 AM,1210.00\n"
                            "M-100013,Mar 15 26T10:30 AM,1310.00\n"
                            "M-100014,15 Mar 26T10:30 AM,1410.00\n"
                            "M-100015,\"Sunday, Mar 15, 2026T10:30 AM\",1510.00\n"
                            "M-100016,\"Sunday, 15 Mar 2026T10:30 AM\",1610.00\n"
                            "M-100017,\"Mar 15, 2026T10:30am\",1710.00\n"
                            "M-100018,\"Mar. 15, 2026T10:30 AM\",1810.00\n"
                            "M-100019,15 Mar. 2026T10:30 AM,1910.00\n"
                            "M-100020,\"Sept 15, 2026T10:30 AM\",2010.00\n"
                            "M-100021,\"Mar 15, 2026T10:30 AM Z\",2110.00\n"
                            "M-100022,\"Mar 15, 2026T10:30 AM GMT\",2210.00\n"
                            "M-100023,\"Mar 15, 2026T10:30Z AM\",2310.00\n"
                            "M-100024,\"Mar 15, 2026T10:30 AM +05:30\",2410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 24)
            expected = (["2026-03-15"] * 19 + ["2026-09-15"]
                        + ["2026-03-15"] * 4)
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 24)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_t_separated_no_seconds_ampm_month_name_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026T10:30 AM\",120.50\n"
                            "M-100002,\"Mar 15, 2026T10:30 XM\",200.00\n"
                            "M-100003,\"Mar 15, 2026T25:30 AM\",310.00\n"
                            "M-100004,\"Mar 15, 2026T10:60 AM\",410.00\n"
                            "M-100005,\"Mar 15, 2026T10:30 AM XYZ\",510.00\n"
                            "M-100006,\"Mar 15, 2026T10:30 AM +99:99\",610.00\n"
                            "M-100007,\"Funday, Mar 15, 2026T10:30 AM\",710.00\n"
                            "M-100008,\"Mar 15, 2026T10:30.123 AM\",810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_read_claims_csv_normalizes_space_t_no_seconds_ampm_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026 T10:30 AM\",120.50\n"
                            "M-100002,15 Mar 2026 T10:30 AM,200.00\n"
                            "M-100003,\"Mar 15, 2026 T10:30 PM\",310.00\n"
                            "M-100004,15 Mar 2026 T2:30 pm,410.00\n"
                            "M-100005,\"March 15, 2026 T10:30 AM\",510.00\n"
                            "M-100006,15 March 2026 T10:30 AM,610.00\n"
                            "M-100007,Mar 15 2026 T10:30 AM,710.00\n"
                            "M-100008,15 Mar 2026 T10:30 AM,810.00\n"
                            "M-100009,\"Mar 15, 26 T10:30 AM\",910.00\n"
                            "M-100010,15 Mar 26 T10:30 AM,1010.00\n"
                            "M-100011,\"March 15, 26 T10:30 PM\",1110.00\n"
                            "M-100012,15 March 26 T10:30 AM,1210.00\n"
                            "M-100013,Mar 15 26 T10:30 AM,1310.00\n"
                            "M-100014,15 Mar 26 T10:30 AM,1410.00\n"
                            "M-100015,\"Sunday, Mar 15, 2026 T10:30 AM\",1510.00\n"
                            "M-100016,\"Sunday, 15 Mar 2026 T10:30 AM\",1610.00\n"
                            "M-100017,\"Mar 15, 2026 T10:30am\",1710.00\n"
                            "M-100018,\"Mar. 15, 2026 T10:30 AM\",1810.00\n"
                            "M-100019,15 Mar. 2026 T10:30 AM,1910.00\n"
                            "M-100020,\"Sept 15, 2026 T10:30 AM\",2010.00\n"
                            "M-100021,\"Mar 15, 2026 T10:30 AM Z\",2110.00\n"
                            "M-100022,\"Mar 15, 2026 T10:30 AM GMT\",2210.00\n"
                            "M-100023,\"Mar 15, 2026 T10:30Z AM\",2310.00\n"
                            "M-100024,\"Mar 15, 2026 T10:30 AM +05:30\",2410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 24)
            expected = (["2026-03-15"] * 19 + ["2026-09-15"]
                        + ["2026-03-15"] * 4)
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 24)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_t_no_seconds_ampm_month_name_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026 T10:30 AM\",120.50\n"
                            "M-100002,\"Mar 15, 2026 T10:30 XM\",200.00\n"
                            "M-100003,\"Mar 15, 2026 T25:30 AM\",310.00\n"
                            "M-100004,\"Mar 15, 2026 T10:60 AM\",410.00\n"
                            "M-100005,\"Mar 15, 2026 T10:30 AM XYZ\",510.00\n"
                            "M-100006,\"Mar 15, 2026 T10:30 AM +99:99\",610.00\n"
                            "M-100007,\"Funday, Mar 15, 2026 T10:30 AM\",710.00\n"
                            "M-100008,\"Mar 15, 2026 T10:30.123 AM\",810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_read_claims_csv_normalizes_trailing_period_iso_slash_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15.,120.50\n"
                            "M-100002,2026-3-5.,200.00\n"
                            "M-100003,2026-12-31.,310.00\n"
                            "M-100004,2026-01-05.,410.00\n"
                            "M-100005,\"2026-03-15 10:30:00.\",510.00\n"
                            "M-100006,2026-03-15T09:00:00.,610.00\n"
                            "M-100007,\"2026-03-15 10:30:00.123.\",710.00\n"
                            "M-100008,\"2026-03-15 10:30:00Z.\",810.00\n"
                            "M-100009,\"2026-03-15 10:30:00 AM.\",910.00\n"
                            "M-100010,\"2026-03-15 10:30:00 AM Z.\",1010.00\n"
                            "M-100011,\"Sunday, 2026-03-15.\",1110.00\n"
                            "M-100012,2026 03 15.,1210.00\n"
                            "M-100013,\"2026-03-15 10:30:00 GMT.\",1310.00\n"
                            "M-100014,2026-03-15t10:30:00z.,1410.00\n"
                            "M-100015,03/15/2026.,1510.00\n"
                            "M-100016,15/03/2026.,1610.00\n"
                            "M-100017,2026/03/15.,1710.00\n"
                            "M-100018,03/15/26.,1810.00\n"
                            "M-100019,\"03/15/2026 10:30:00.\",1910.00\n"
                            "M-100020,03/15/2026T09:00:00Z.,2010.00\n"
                            "M-100021,\"03/15/2026 10:30:00 AM.\",2110.00\n"
                            "M-100022,\"Sunday, 03/15/2026.\",2210.00\n"
                            "M-100023,\"03/15/2026 10:30:00.123.\",2310.00\n"
                            "M-100024,03/15/2026T103000z.,2410.00\n"
                            "M-100025,\"03/15/2026 10:30:00 GMT.\",2510.00\n"
                            "M-100026,03/15/2026T10300z.,2610.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 26)
            expected = ["2026-03-15", "2026-03-05",
                        "2026-12-31", "2026-01-05"] + ["2026-03-15"] * 22
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 26)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_trailing_period_iso_slash_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15..,120.50\n"
                            "M-100002,2026-02-30.,200.00\n"
                            "M-100003,2026-03-15.10:30:00,310.00\n"
                            "M-100004,\"2026-03-15. XYZ\",410.00\n"
                            "M-100005,\"Funday, 2026-03-15.\",510.00\n"
                            "M-100006,\"2026-03-15 10:30:00.1234567.\",610.00\n"
                            "M-100007,2026-03-15T103000.,710.00\n"
                            "M-100008,03/15/2026..,810.00\n"
                            "M-100009,02/30/2026.,910.00\n"
                            "M-100010,03/15/2026.10:30:00,1010.00\n"
                            "M-100011,\"03/15/2026. XYZ\",1110.00\n"
                            "M-100012,\"Funday, 03/15/2026.\",1210.00\n"
                            "M-100013,\"03/15/2026 10:30:00.1234567.\",1310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 13)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 13)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 13})

    def test_read_claims_csv_normalizes_trailing_period_dot_underscore_hyphen_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15.,120.50\n"
                            "M-100002,03.15.2026.,200.00\n"
                            "M-100003,03.15.26.,310.00\n"
                            "M-100004,15.03.2026.,410.00\n"
                            "M-100005,\"2026.03.15 10:30:00.\",510.00\n"
                            "M-100006,\"2026.03.15 10:30:00 AM.\",610.00\n"
                            "M-100007,\"Sunday, 2026.03.15.\",710.00\n"
                            "M-100008,\"2026.03.15 10:30:00.123Z.\",810.00\n"
                            "M-100009,2026_03_15.,910.00\n"
                            "M-100010,03_15_2026.,1010.00\n"
                            "M-100011,03_15_26.,1110.00\n"
                            "M-100012,15_03_2026.,1210.00\n"
                            "M-100013,\"2026_03_15 10:30:00.\",1310.00\n"
                            "M-100014,\"2026_03_15 10:30:00 AM.\",1410.00\n"
                            "M-100015,\"2026_03_15 10:30:00 GMT.\",1510.00\n"
                            "M-100016,\"Sunday, 2026_03_15.\",1610.00\n"
                            "M-100017,2026_03_15T103000z.,1710.00\n"
                            "M-100018,03-15-2026.,1810.00\n"
                            "M-100019,15-03-2026.,1910.00\n"
                            "M-100020,03-15-26.,2010.00\n"
                            "M-100021,\"03-15-2026 10:30:00.\",2110.00\n"
                            "M-100022,\"03-15-2026 10:30:00 AM.\",2210.00\n"
                            "M-100023,\"03-15-2026 10:30:00 GMT.\",2310.00\n"
                            "M-100024,\"Sunday, 03-15-2026.\",2410.00\n"
                            "M-100025,03-15-2026T103000.,2510.00\n"
                            "M-100026,\"2026.03.15 10:30:00 GMT.\",2610.00\n"
                            "M-100027,\"2026_03_15 10:30:00.123Z.\",2710.00\n"
                            "M-100028,\"03-15-2026 10:30:00.123Z.\",2810.00\n"
                            "M-100029,\"03-15-2026 10:30:00 AM Z.\",2910.00\n"
                            "M-100030,03-15-2026T103000z.,3010.00\n"
                            "M-100031,2026.03.15T103000.,3110.00\n"
                            "M-100032,2026.03.15T103000z.,3210.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 32)
            for row in rows:
                self.assertEqual(row["service_date"], "2026-03-15")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 32)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_trailing_period_dot_underscore_hyphen_dates_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026.03.15..,120.50\n"
                            "M-100002,2026_03_15..,200.00\n"
                            "M-100003,03-15-2026..,310.00\n"
                            "M-100004,2026.02.30.,410.00\n"
                            "M-100005,2026_02_30.,510.00\n"
                            "M-100006,02-30-2026.,610.00\n"
                            "M-100007,03-15-2026.10:30:00,710.00\n"
                            "M-100008,\"2026.03.15. XYZ\",810.00\n"
                            "M-100009,\"2026_03_15. XYZ\",910.00\n"
                            "M-100010,\"03-15-2026. XYZ\",1010.00\n"
                            "M-100011,\"Funday, 2026.03.15.\",1110.00\n"
                            "M-100012,\"Funday, 2026_03_15.\",1210.00\n"
                            "M-100013,\"2026.03.15 10:30:00 AM XYZ.\",1310.00\n"
                            "M-100014,2026.13.15.,1410.00\n"
                            "M-100015,2026_13_15.,1510.00\n"
                            "M-100016,13-15-2026.,1610.00\n"
                            "M-100017,\"2026.03.15 10:30:00.1234567.\",1710.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 17)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 17)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 17})

    def test_read_claims_csv_normalizes_datetime_stamped_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15 10:30:00,120.50\n"
                            "M-100002,2026-03-16T09:00:00,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 2)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_datetime_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-02-30 10:00:00,120.50\n"
                            "M-100002,2026-03-15 not-a-time,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_normalizes_timezone_suffixed_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-03-15T09:00:00Z,120.50\n"
                            "M-100002,2026-03-16 10:30:00+05:30,200.00\n"
                            "M-100003,2026-03-17T08:00:00-0500,310.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["service_date"], "2026-03-15")
            self.assertEqual(rows[1]["service_date"], "2026-03-16")
            self.assertEqual(rows[2]["service_date"], "2026-03-17")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 3)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_timezone_suffix_still_quarantines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,2026-02-30T09:00:00Z,120.50\n"
                            "M-100002,2026-03-15 10:30:00+99:99,200.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 2)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 2)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 2})

    def test_read_claims_csv_padded_header_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text(" member_id , service_date \n"
                            " M-100001 , 2026-03-15 \n")
            with self.assertRaises(ValueError) as ctx:
                read_claims_csv(path)
            self.assertIn("claim_amount", str(ctx.exception))

    def test_read_claims_csv_matches_headers_case_insensitively(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("Member_ID,SERVICE_DATE,Claim_Amount\n"
                            "M-100001,2026-03-15,120.50\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["member_id"], "M-100001")
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 1)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_mixed_case_header_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("Member_ID,Service_Date\n"
                            "M-100001,2026-03-15\n")
            with self.assertRaises(ValueError) as ctx:
                read_claims_csv(path)
            self.assertIn("claim_amount", str(ctx.exception))

    def test_write_governed_csv_drops_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "governed.csv"
            result = run_pipeline([good_record(),
                                   good_record(member_id="M-100002")])
            # Slip a raw identifier into a governed record dict:
            result["governed"][0]["member_id"] = "M-100001"
            write_governed_csv(path, result["governed"])
            with open(path) as f:
                header = f.readline().strip().split(",")
            self.assertEqual(header, list(GOVERNED_COLUMNS))
            body = path.read_text()
            self.assertNotIn("member_id", body)
            self.assertNotIn("M-100001", body)
            self.assertNotIn("Patient", body)
            self.assertIn(hash_member_id("M-100001"), body)

    def test_write_governed_csv_empty_still_writes_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            write_governed_csv(path, [])
            self.assertEqual(path.read_text().strip(),
                             ",".join(GOVERNED_COLUMNS))

    def test_write_quarantine_csv_hashes_not_raw_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quarantine.csv"
            result = run_pipeline([good_record(),
                                   good_record(service_date="2026-02-30"),
                                   good_record(member_id="")])
            write_quarantine_csv(path, result["quarantined"])
            with open(path) as f:
                header = f.readline().strip().split(",")
            self.assertEqual(header, list(QUARANTINE_COLUMNS))
            body = path.read_text()
            self.assertNotIn("M-100001", body)
            self.assertNotIn("Patient", body)
            self.assertNotIn("member_id", body)
            self.assertIn(hash_member_id("M-100001"), body)
            self.assertIn(QuarantineReason.BAD_DATE, body)
            self.assertIn(QuarantineReason.MISSING_FIELD, body)

    def test_write_quarantine_csv_empty_still_writes_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            write_quarantine_csv(path, [])
            self.assertEqual(path.read_text().strip(),
                             ",".join(QUARANTINE_COLUMNS))

    def test_write_audit_csv_exports_trail_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(Path(tmp) / "audit.jsonl")
            log.write("governed", hash_member_id("M-100001"))
            log.write("quarantined", "redacted",
                      QuarantineReason.BAD_DATE)
            path = Path(tmp) / "audit.csv"
            write_audit_csv(path, log)
            with open(path) as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], list(AUDIT_COLUMNS))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[1][1], "governed")
            self.assertEqual(rows[1][2], hash_member_id("M-100001"))
            self.assertEqual(rows[2][1], "quarantined")
            self.assertEqual(rows[2][2], "redacted")
            self.assertEqual(rows[2][3], QuarantineReason.BAD_DATE)
            self.assertNotIn("M-100001", path.read_text())

    def test_write_audit_csv_empty_trail_still_writes_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(Path(tmp) / "audit.jsonl")  # no trail yet
            path = Path(tmp) / "audit.csv"
            write_audit_csv(path, log)
            self.assertEqual(path.read_text().strip(),
                             ",".join(AUDIT_COLUMNS))

    def test_write_summary_json_round_trips_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_pipeline([good_record(),
                                   good_record(service_date="2026-02-30")])
            summary = summarize_run(result)
            path = Path(tmp) / "summary.json"
            write_summary_json(path, summary)
            loaded = json.loads(path.read_text())
            self.assertEqual(loaded, summary)
            self.assertEqual(loaded["records_in"], 2)
            self.assertEqual(loaded["governed_count"], 1)
            self.assertEqual(loaded["quarantined_count"], 1)
            self.assertNotIn("M-100001", path.read_text())
            self.assertNotIn("Patient 1", path.read_text())

    def test_write_summary_json_empty_run_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = summarize_run(run_pipeline([]))
            path = Path(tmp) / "summary.json"
            write_summary_json(path, summary)
            loaded = json.loads(path.read_text())
            self.assertEqual(loaded["records_in"], 0)
            self.assertEqual(loaded["quarantine_rate"], 0.0)
            self.assertEqual(loaded["reasons"], {})


class TestCli(unittest.TestCase):
    def _write_input(self, tmp):
        path = Path(tmp) / "input.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "member_id", "patient_name", "service_date",
                "claim_amount", "diagnosis_code"])
            writer.writeheader()
            writer.writerow(good_record())
            writer.writerow(good_record(service_date="2026-02-30"))
        return path

    def test_cli_writes_deidentified_outputs_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = self._write_input(tmp)
            gov, quar = Path(tmp) / "g.csv", Path(tmp) / "q.csv"
            aud, aud_csv = Path(tmp) / "a.jsonl", Path(tmp) / "a.csv"
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli_main([str(inp), "--governed", str(gov),
                                 "--quarantine", str(quar),
                                 "--audit", str(aud),
                                 "--audit-csv", str(aud_csv)])
            self.assertEqual(code, 0)
            self.assertIn("records_in=2 governed=1 quarantined=1",
                          out.getvalue())
            self.assertIn(QuarantineReason.BAD_DATE, out.getvalue())
            for path in (gov, quar, aud, aud_csv):
                self.assertTrue(path.exists())
                self.assertNotIn("M-100001", path.read_text())
                self.assertNotIn("Patient 1", path.read_text())
            self.assertIn(hash_member_id("M-100001"), gov.read_text())

    def test_cli_missing_input_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = cli_main([str(Path(tmp) / "nope.csv"),
                             "--governed", str(Path(tmp) / "g.csv"),
                             "--quarantine", str(Path(tmp) / "q.csv"),
                             "--audit", str(Path(tmp) / "a.jsonl")])
            self.assertEqual(code, 2)

    def test_cli_bad_header_returns_2_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "bad.csv"
            inp.write_text("member_id,service_date\n"
                           "M-100001,2026-03-15\n")
            gov, quar = Path(tmp) / "g.csv", Path(tmp) / "q.csv"
            aud = Path(tmp) / "a.jsonl"
            code = cli_main([str(inp), "--governed", str(gov),
                             "--quarantine", str(quar),
                             "--audit", str(aud)])
            self.assertEqual(code, 2)
            for path in (gov, quar, aud):
                self.assertFalse(path.exists())

    def test_cli_summary_json_flag_writes_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = self._write_input(tmp)
            gov, quar = Path(tmp) / "g.csv", Path(tmp) / "q.csv"
            aud = Path(tmp) / "a.jsonl"
            summ = Path(tmp) / "summary.json"
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli_main([str(inp), "--governed", str(gov),
                                 "--quarantine", str(quar),
                                 "--audit", str(aud),
                                 "--summary-json", str(summ)])
            self.assertEqual(code, 0)
            loaded = json.loads(summ.read_text())
            self.assertEqual(loaded["records_in"], 2)
            self.assertEqual(loaded["governed_count"], 1)
            self.assertEqual(loaded["quarantined_count"], 1)
            self.assertEqual(loaded["quarantine_rate"], 0.5)
            self.assertEqual(loaded["reasons"],
                             {QuarantineReason.BAD_DATE: 1})
            self.assertNotIn("M-100001", summ.read_text())
            self.assertNotIn("Patient 1", summ.read_text())

    def test_cli_creates_missing_output_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = self._write_input(tmp)
            base = Path(tmp) / "out" / "nested"
            gov = base / "g.csv"
            quar = base / "q.csv"
            aud = base / "a.jsonl"
            aud_csv = base / "a.csv"
            summ = base / "summary.json"
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli_main([str(inp), "--governed", str(gov),
                                 "--quarantine", str(quar),
                                 "--audit", str(aud),
                                 "--audit-csv", str(aud_csv),
                                 "--summary-json", str(summ)])
            self.assertEqual(code, 0)
            for path in (gov, quar, aud, aud_csv, summ):
                self.assertTrue(path.exists())
                self.assertNotIn("M-100001", path.read_text())
                self.assertNotIn("Patient 1", path.read_text())

    def test_cli_unwritable_output_parent_returns_2_no_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = self._write_input(tmp)
            blocker = Path(tmp) / "blocker"
            blocker.write_text("not a directory")
            gov = blocker / "g.csv"
            err = io.StringIO()
            with redirect_stderr(err):
                code = cli_main([str(inp), "--governed", str(gov),
                                 "--quarantine", str(Path(tmp) / "q.csv"),
                                 "--audit", str(Path(tmp) / "a.jsonl")])
            self.assertEqual(code, 2)
            self.assertNotIn("Traceback", err.getvalue())
            self.assertIn("cannot write output", err.getvalue())

    def test_read_claims_csv_normalizes_space_t_seconds_month_name_datetimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Mar 15, 2026 T10:30:00\",120.50\n"
                            "M-100002,15 Mar 2026 T10:30:00,200.00\n"
                            "M-100003,\"Mar 15, 2026 T10:30:00 PM\",310.00\n"
                            "M-100004,15 Mar 2026 T2:30:00 pm,410.00\n"
                            "M-100005,\"March 15, 2026 T10:30:00\",510.00\n"
                            "M-100006,15 March 2026 T10:30:00,610.00\n"
                            "M-100007,Mar 15 2026 T10:30:00,710.00\n"
                            "M-100008,15 Mar 2026 T10:30:00 AM,810.00\n"
                            "M-100009,\"Mar 15, 26 T10:30:00\",910.00\n"
                            "M-100010,15 Mar 26 T10:30:00,1010.00\n"
                            "M-100011,\"March 15, 26 T10:30:00 PM\",1110.00\n"
                            "M-100012,15 March 26 T10:30:00,1210.00\n"
                            "M-100013,Mar 15 26 T10:30:00,1310.00\n"
                            "M-100014,15 Mar 26 T10:30:00 PM,1410.00\n"
                            "M-100015,\"Sunday, Mar 15, 2026 T10:30:00\",1510.00\n"
                            "M-100016,\"Sunday, 15 Mar 2026 T10:30:00\",1610.00\n"
                            "M-100017,\"Mar 15, 2026 T10:30:00am\",1710.00\n"
                            "M-100018,\"Mar. 15, 2026 T10:30:00\",1810.00\n"
                            "M-100019,15 Mar. 2026 T10:30:00,1910.00\n"
                            "M-100020,\"Sept 15, 2026 T10:30:00\",2010.00\n"
                            "M-100021,\"Mar 15, 2026 T10:30:00 Z\",2110.00\n"
                            "M-100022,\"Mar 15, 2026 T10:30:00 GMT\",2210.00\n"
                            "M-100023,\"Mar 15, 2026 T10:30:00Z\",2310.00\n"
                            "M-100024,\"Mar 15, 2026 T10:30:00 AM +05:30\",2410.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 24)
            expected = (["2026-03-15"] * 19 + ["2026-09-15"]
                        + ["2026-03-15"] * 4)
            for row, want in zip(rows, expected):
                self.assertEqual(row["service_date"], want)
            result = run_pipeline(rows)
            self.assertEqual(result["governed_count"], 24)
            self.assertEqual(result["quarantined_count"], 0)

    def test_read_claims_csv_bad_space_t_seconds_month_name_datetimes_still_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claims.csv"
            path.write_text("member_id,service_date,claim_amount\n"
                            "M-100001,\"Feb 30, 2026 T10:30:00\",120.50\n"
                            "M-100002,\"Mar 15, 2026 T10:30:00 XM\",200.00\n"
                            "M-100003,\"Mar 15, 2026 T25:30:00\",310.00\n"
                            "M-100004,\"Mar 15, 2026 T10:60:00\",410.00\n"
                            "M-100005,\"Mar 15, 2026 T10:30:00 XYZ\",510.00\n"
                            "M-100006,\"Mar 15, 2026 T10:30:00 +99:99\",610.00\n"
                            "M-100007,\"Funday, Mar 15, 2026 T10:30:00\",710.00\n"
                            "M-100008,\"Mar 15, 2026 T10:30:60\",810.00\n")
            rows = read_claims_csv(path)
            self.assertEqual(len(rows), 8)
            result = run_pipeline(rows)
            self.assertEqual(result["quarantined_count"], 8)
            self.assertEqual(result["reasons"],
                             {QuarantineReason.BAD_DATE: 8})

    def test_cli_without_summary_json_flag_writes_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = self._write_input(tmp)
            summ = Path(tmp) / "summary.json"
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli_main([str(inp),
                                 "--governed", str(Path(tmp) / "g.csv"),
                                 "--quarantine", str(Path(tmp) / "q.csv"),
                                 "--audit", str(Path(tmp) / "a.jsonl")])
            self.assertEqual(code, 0)
            self.assertFalse(summ.exists())


if __name__ == "__main__":
    unittest.main()
