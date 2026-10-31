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
