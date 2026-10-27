"""CSV input/output for the governed pipeline.

read_claims_csv reads raw claims-like rows (all values strings) so a
caller can feed a file straight into run_pipeline; it tolerates the
mess real exports carry — a UTF-8 byte-order mark and whitespace
around headers and values, headers in any letter case (so
"Member_ID" means member_id), currency-formatted amounts such as
"$1,200.50", US slash dates such as "03/15/2026",
year-first slash dates such as "2026/03/15",
day-first slash dates such as "15/03/2026" (unambiguous only:
the US form keeps priority, so a date whose first component
could be a month still reads as MM/DD/YYYY),
slash datetimes such as "03/15/2026 10:30:00" (the date part
governs, the time part is dropped),
datetime-stamped dates such as "2026-03-15 10:30:00",
timezone-suffixed datetimes such as "2026-03-15T09:00:00Z" or
"2026-03-15 10:30:00+05:30", dot-separated dates such as
"2026.03.15", compact dates such as "20260315", and
hyphenated month-name dates such as "15-Mar-2026", and
numeric hyphen dates such as "03-15-2026", and
underscore-separated dates such as "2026_03_15", and
weekday-prefixed month-name dates such as "Sunday, March 15, 2026"
(the weekday label is dropped, only the date part governs) — skips blank
rows outright, and still
fails closed on a header missing a required column. write_governed_csv
writes only governed records, under the fixed de-identified columns:
it never writes a raw member ID, patient name, or any other direct
identifier, even if one slipped into a governed record dict.
write_quarantine_csv writes quarantined (record, reason) pairs the
same way: the raw record is replaced by its member hash plus the
quarantine reason, so quarantine reports never leak identifiers.
write_audit_csv exports an AuditLog's trail to CSV for reviewers
who work in spreadsheets: one row per entry, under the fixed audit
columns, carrying only the hashed member reference the trail
already stores — never a raw identifier.
write_summary_json writes a run summary (the plain dict from
summarize_run, which contains counts and tallies and no record
data) to JSON so a run's outcome can be filed or reported without
any patient data attached.
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path

from .deidentification import hash_member_id

GOVERNED_COLUMNS = ("member_hash", "service_date",
                    "claim_amount", "diagnosis_code")
# Columns a claims CSV must carry for the quality gates to mean
# anything: without one of these, every row would quarantine as
# missing_required_field and the real problem — a malformed file —
# would hide inside the quarantine tally. diagnosis_code is
# deliberately NOT required (it defaults to "" for governed rows).
REQUIRED_COLUMNS = ("member_id", "service_date", "claim_amount")
QUARANTINE_COLUMNS = ("member_hash", "service_date",
                      "claim_amount", "diagnosis_code", "reason")
AUDIT_COLUMNS = ("timestamp", "action", "member_hash", "reason")


def read_claims_csv(path):
    """Read a claims CSV into a list of row dicts (string values).

    Fail closed on a malformed file: if the header (or an empty
    file, which has no header) is missing any REQUIRED_COLUMNS,
    raise ValueError naming the missing columns instead of
    returning rows that would all quarantine as missing fields.
    The CLI turns this into exit code 2 with no outputs written.
    Real exports are tolerated on the way in: a UTF-8 byte-order
    mark (the kind spreadsheet exports prepend) is stripped by the
    utf-8-sig encoding, and surrounding whitespace on headers and
    values is stripped, so " member_id " and " 2026-03-15 " mean
    the same as their clean forms instead of failing a gate.
    Headers are also matched case-insensitively: "Member_ID",
    "SERVICE_DATE", and "Claim_Amount" are read as member_id,
    service_date, and claim_amount, so an export's capitalisation
    no longer fails the file closed as missing columns; a header
    still missing a required column (in any case) raises
    ValueError naming that column.
    Blank rows — a commas-only line (",,") or a whitespace-only
    line, the kind trailing spreadsheet exports leave behind —
    are skipped outright: they carry no record, so counting one
    as a missing_required_field quarantine would inflate the
    quarantine tally with a non-record. A row with some fields
    filled and others empty is NOT blank and still quarantines
    normally. Currency formatting on claim_amount — a leading "$"
    and thousands commas, as in "$1,200.50" — is stripped on read,
    so a formatted amount governs instead of quarantining as
    invalid_amount; a value that is still not a number after
    stripping (e.g. "$abc") quarantines normally. A service_date
    in US slash form (MM/DD/YYYY, the convention in US healthcare
    exports) is normalized to ISO form (YYYY-MM-DD) on read, so
    "03/15/2026" governs instead of quarantining as
    unparseable_date; a slash date that is not a real calendar
    date (e.g. "02/30/2026") is left untouched so the gates
    quarantine it normally. The year-first slash form (YYYY/MM/DD,
    another export convention) normalizes the same way, so
    "2026/03/15" also governs; an impossible year-first date
    (e.g. "2026/02/30") is left untouched for the gates.
    The day-first slash form (DD/MM/YYYY, the convention in
    non-US healthcare exports) normalizes the same way, but
    only when it is unambiguous: the US form is tried first, so
    "15/03/2026" governs as 2026-03-15 while "03/04/2026" still
    reads as the US form (2026-03-04); a day-first date that is
    not a real calendar date (e.g. "32/03/2026" or "15/13/2026")
    is left untouched so the gates quarantine it normally.
    A service_date in slash form carrying a time stamp
    ("03/15/2026 10:30:00" or "03/15/2026T09:00:00", the way
    spreadsheet exports write slash datetimes) normalizes to
    its date part the same way, with the same US-first order;
    an impossible slash datetime (e.g. "02/30/2026 10:00:00")
    or a garbage time part is left untouched so the gates
    quarantine it normally.
    A service_date carrying a time stamp
    (a space- or "T"-separated datetime such as "2026-03-15
    10:30:00" or "2026-03-15T09:00:00", the way spreadsheet
    exports write datetimes) is normalized to its date part
    (YYYY-MM-DD) on read, so it governs instead of quarantining
    as unparseable_date; a datetime that is not a real calendar
    date or has a garbage time part (e.g. "2026-02-30 10:00:00")
    is left untouched so the gates quarantine it normally. The quality
    gates themselves stay strict: they see only the normalized
    value, never the raw formatting.
    A datetime-stamped date carrying a timezone suffix — a trailing
    "Z" (UTC) or a numeric offset such as "+05:30" or "-0500", the
    way API and EHR exports write timestamps — has that suffix
    stripped before the datetime is parsed, so "2026-03-15T09:00:00Z"
    and "2026-03-15 10:30:00+05:30" also govern as their date part;
    the offset itself is not converted (the gate needs the service
    date as written, not a shifted one). A suffix that is not a
    well-formed UTC designator or offset (e.g. "+99:99") is not
    stripped, so the value stays unparseable and the gates
    quarantine it normally, as does an impossible date carrying a
    valid suffix (e.g. "2026-02-30T09:00:00Z").
    A service_date in dot-separated form (YYYY.MM.DD, another
    export convention) normalizes to ISO form (YYYY-MM-DD) on
    read, so "2026.03.15" governs instead of quarantining as
    unparseable_date; an impossible dot-separated date (e.g.
    "2026.02.30") is left untouched so the gates quarantine it
    normally. A service_date written with a month name ("Mar 15,
    2026" or "15 Mar 2026", abbreviated or full month name, the
    way human-readable exports write dates) normalizes the same
    way, so it governs; an impossible month-name date (e.g.
    "Feb 30, 2026") or an unknown month name is left untouched
    so the gates quarantine it normally. A service_date in
    compact form (YYYYMMDD, the basic ISO 8601 form, another
    export convention) normalizes the same way, so "20260315"
    governs; an impossible compact date (e.g. "20260230") is
    left untouched so the gates quarantine it normally.
    A service_date in hyphenated month-name form ("15-Mar-2026"
    or "Mar-15-2026", abbreviated or full month name, the way
    some exports write dates without spaces) normalizes the same
    way, so it governs; an impossible hyphenated month-name date
    (e.g. "30-Feb-2026") is left untouched so the gates
    quarantine it normally. A service_date in numeric hyphen
    form ("03-15-2026", the way some exports write the US date
    with hyphens instead of slashes) normalizes the same way,
    with the US form keeping priority: "03-04-2026" reads as
    2026-03-04 while an unambiguous day-first form ("15-03-2026")
    governs as 2026-03-15; an impossible numeric hyphen date
    (e.g. "02-30-2026") is left untouched so the gates
    quarantine it normally. An already-ISO date ("2026-03-15")
    is not touched by this form — its four-digit first
    component does not match the numeric-hyphen pattern.
    A service_date in underscore-separated form (YYYY_MM_DD,
    the way some exports and file-naming conventions write
    dates) normalizes the same way, so "2026_03_15" governs;
    an impossible underscore-separated date (e.g.
    "2026_02_30") is left untouched so the gates quarantine
    it normally. A service_date in weekday-prefixed month-name
    form ("Sunday, March 15, 2026" or "Mon, 16 Mar 2026", the
    way human-readable exports and email-style timestamps
    write dates) has its weekday label stripped on read and
    then normalizes the same way, so it governs; the weekday
    itself is not validated against the calendar date (it is
    a label, not the date), while an impossible weekday-
    prefixed date (e.g. "Monday, Feb 30, 2026") or a bogus
    weekday label (e.g. "Funday, March 15, 2026") is left
    untouched so the gates quarantine it normally. A
    weekday-prefixed ordinal date ("Sunday, March 15th,
    2026") strips both the weekday and the ordinal suffix
    before parsing and governs the same way.
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = [name.strip().lower() if name else name
                  for name in (reader.fieldnames or [])]
        reader.fieldnames = header
        missing = [col for col in REQUIRED_COLUMNS if col not in header]
        if missing:
            raise ValueError(
                f"claims CSV is missing required columns: "
                f"{', '.join(missing)}")
        rows = []
        for row in reader:
            cleaned = {key.strip(): (value.strip()
                                     if isinstance(value, str) else value)
                       for key, value in row.items() if key is not None}
            amount = cleaned.get("claim_amount")
            if isinstance(amount, str):
                cleaned["claim_amount"] = amount.replace(
                    "$", "").replace(",", "").strip()
            date = cleaned.get("service_date")
            if isinstance(date, str) and "/" in date:
                for fmt in ("%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"):
                    try:
                        cleaned["service_date"] = datetime.strptime(
                            date, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
                if cleaned["service_date"] == date:
                    # Slash datetime: same date orders, plus a
                    # space- or "T"-separated time part, which is
                    # dropped — only the date part governs.
                    for fmt in ("%m/%d/%Y %H:%M:%S",
                                "%m/%d/%Y %H:%M",
                                "%m/%d/%Y %H:%M:%S.%f",
                                "%m/%d/%YT%H:%M:%S",
                                "%m/%d/%YT%H:%M",
                                "%Y/%m/%d %H:%M:%S",
                                "%Y/%m/%d %H:%M",
                                "%Y/%m/%dT%H:%M:%S",
                                "%d/%m/%Y %H:%M:%S",
                                "%d/%m/%Y %H:%M",
                                "%d/%m/%YT%H:%M:%S"):
                        try:
                            cleaned["service_date"] = datetime.strptime(
                                date, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                # else: not a real calendar date in any slash
                # form: left untouched, gates quarantine it.
                # The US form is tried first, so only an
                # unambiguous day-first date (first component
                # above 12) reaches the DD/MM/YYYY attempt.
            elif isinstance(date, str) and "." in date:
                try:
                    cleaned["service_date"] = datetime.strptime(
                        date, "%Y.%m.%d").strftime("%Y-%m-%d")
                except ValueError:
                    # Not a real calendar date in dot form:
                    # left untouched, gates quarantine it
                    pass
            elif isinstance(date, str) and re.fullmatch(
                    r"\d{4}_\d{2}_\d{2}", date):
                # Underscore-separated form: YYYY_MM_DD (the way
                # some exports and file-naming conventions write
                # dates). An impossible date fails parsing and
                # is left untouched so the gates quarantine it.
                try:
                    cleaned["service_date"] = datetime.strptime(
                        date, "%Y_%m_%d").strftime("%Y-%m-%d")
                except ValueError:
                    pass
            elif isinstance(date, str) and any(
                    month in date for month in
                    ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")):
                # Month-name form: "Mar 15, 2026" or "15 Mar 2026",
                # abbreviated or full month name, including the
                # hyphenated forms "15-Mar-2026" and "Mar-15-2026".
                # A name that is not a real month, or an impossible
                # day, fails every format and is left untouched so
                # the gates quarantine it normally. Ordinal day
                # suffixes ("March 15th, 2026", "15th Mar 2026",
                # the way human-written exports spell the day)
                # are stripped before the second attempt, so the
                # ordinal form governs too; an impossible
                # ordinal date ("Feb 30th, 2026") still fails
                # every format and quarantines normally.
                candidates = [date]
                # Weekday-prefixed form: "Sunday, March 15, 2026"
                # or "Mon, 16 Mar 2026" — the weekday label is
                # dropped (it is not validated against the date)
                # and the remainder parses as a month-name date.
                # Full weekday names come first in the pattern
                # so "Tuesday" is not half-stripped as "Tue".
                weekday_stripped = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", date,
                    flags=re.IGNORECASE)
                if weekday_stripped != date:
                    candidates.append(weekday_stripped)
                for base in list(candidates):
                    stripped = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", base)
                    if stripped != base and stripped not in candidates:
                        candidates.append(stripped)
                for candidate in candidates:
                    for fmt in ("%b %d, %Y", "%B %d, %Y",
                                "%d %b %Y", "%d %B %Y",
                                "%d-%b-%Y", "%b-%d-%Y",
                                "%d-%B-%Y", "%B-%d-%Y"):
                        try:
                            cleaned["service_date"] = datetime.strptime(
                                candidate, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    if cleaned["service_date"] != date:
                        break
            elif isinstance(date, str) and re.fullmatch(
                    r"\d{1,2}-\d{1,2}-\d{4}", date):
                # Numeric hyphen form: "03-15-2026" (US) or an
                # unambiguous day-first "15-03-2026". The US form
                # is tried first, mirroring the slash-date rule,
                # so only a first component above 12 reaches the
                # DD-MM-YYYY attempt. An ISO date never reaches
                # here: its four-digit first component does not
                # match the pattern. An impossible date fails
                # every format and is left untouched so the gates
                # quarantine it normally.
                for fmt in ("%m-%d-%Y", "%d-%m-%Y"):
                    try:
                        cleaned["service_date"] = datetime.strptime(
                            date, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
            elif isinstance(date, str) and date.isdigit() and len(date) == 8:
                # Compact form: YYYYMMDD (basic ISO 8601, the way
                # some EHR and API exports write dates). An
                # impossible compact date fails parsing and is
                # left untouched so the gates quarantine it.
                try:
                    cleaned["service_date"] = datetime.strptime(
                        date, "%Y%m%d").strftime("%Y-%m-%d")
                except ValueError:
                    pass
            elif isinstance(date, str) and (" " in date or "T" in date):
                candidate = date
                # Strip a timezone suffix before parsing: a trailing
                # "Z", or a well-formed numeric offset (hours 00-14,
                # minutes 00-59, colon optional). Anything else is
                # left in place so parsing fails and the gates
                # quarantine the value normally.
                if candidate.endswith("Z"):
                    candidate = candidate[:-1]
                else:
                    suffix = re.search(
                        r"([+-](?:0\d|1[0-4]):?[0-5]\d)$", candidate)
                    if suffix is not None:
                        candidate = candidate[:-len(suffix.group(1))]
                parsed = None
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
                            "%Y-%m-%d %H:%M:%S.%f",
                            "%Y-%m-%dT%H:%M:%S.%f"):
                    try:
                        parsed = datetime.strptime(candidate, fmt)
                        break
                    except ValueError:
                        continue
                if parsed is not None:
                    cleaned["service_date"] = parsed.strftime("%Y-%m-%d")
                # else: not a real datetime: gates quarantine it
            if cleaned and any(value not in (None, "")
                               for value in cleaned.values()):
                rows.append(cleaned)
        return rows


def write_governed_csv(path, governed):
    """Write governed records as a de-identified CSV.

    Columns are exactly GOVERNED_COLUMNS; any other key in a record
    (including a raw identifier) is dropped, never written out.
    An empty governed list still writes the header row.
    """
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(GOVERNED_COLUMNS))
        writer.writeheader()
        for record in governed:
            writer.writerow({col: record.get(col, "")
                             for col in GOVERNED_COLUMNS})


def write_quarantine_csv(path, quarantined):
    """Write quarantined (record, reason) pairs, de-identified.

    Columns are exactly QUARANTINE_COLUMNS. Each raw record is
    reduced to its member hash (or "" when the record has no
    member ID, e.g. a missing-field failure) plus its non-identifier
    fields and the quarantine reason — patient names and raw member
    IDs are never written out, so a quarantine report is safe to
    share with a reviewer. An empty list still writes the header.
    """
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(QUARANTINE_COLUMNS))
        writer.writeheader()
        for record, reason in quarantined:
            member_id = record.get("member_id", "")
            writer.writerow({
                "member_hash": hash_member_id(member_id) if member_id else "",
                "service_date": record.get("service_date", ""),
                "claim_amount": record.get("claim_amount", ""),
                "diagnosis_code": record.get("diagnosis_code", ""),
                "reason": reason,
            })


def write_audit_csv(path, audit_log):
    """Export an AuditLog's trail to CSV for reviewers.

    Columns are exactly AUDIT_COLUMNS. Each row is one trail entry
    (timestamp, action, member hash or "redacted", reason). The
    trail stores only hashes and "redacted" markers, so the export
    contains no raw identifiers. An empty or missing trail still
    writes the header row.
    """
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(AUDIT_COLUMNS))
        writer.writeheader()
        for entry in audit_log.entries():
            writer.writerow({col: entry.get(col, "") or ""
                             for col in AUDIT_COLUMNS})


def write_summary_json(path, summary):
    """Write a run summary dict to JSON.

    summary is expected to be the plain dict from summarize_run:
    counts, quarantine rate, and per-reason tallies — no record
    data, so the file is safe to file or share. Keys are sorted
    for stable, diff-friendly output.
    """
    with open(path, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
