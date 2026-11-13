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
governs, the time part is dropped), and
fractional-second slash datetimes such as
"03/15/2026 10:30:00.123Z" (the fractional seconds are dropped
with the time part, only the date part governs), and
AM/PM slash datetimes such as "03/15/2026 10:30:00 AM" (the
marker is dropped, only the date part governs), and
AM/PM timezone-suffixed slash datetimes such as
"03/15/2026 10:30:00 AM Z" or a named RFC 2822 zone such as
"03/15/2026 10:30:00 AM GMT" (the suffix trailing the marker is
dropped first, then the marker, only the date part governs), and
two-digit-year slash dates such as "03/15/26" (a legacy export
convention; the two-digit year follows Python's %y pivot,
00-68 read as 2000-2068 and 69-99 as 1969-1999, with the same
US-first order), and
datetime-stamped dates such as "2026-03-15 10:30:00",
AM/PM ISO datetimes such as "2026-03-15 10:30:00 AM" (the
marker is dropped, only the date part governs), and
timezone-suffixed datetimes such as "2026-03-15T09:00:00Z" or
"2026-03-15 10:30:00+05:30", dot-separated dates such as
"2026.03.15", two-digit-year dot-separated dates such as
"03.15.26" (a legacy export convention; the two-digit year
follows Python's %y pivot, 00-68 read as 2000-2068 and 69-99
as 1969-1999, with the same US-first order), compact dates such as "20260315", weekday-prefixed
compact dates such as "Sunday, 20260315" (the weekday label is
dropped, only the compact date governs), and
hyphenated month-name dates such as "15-Mar-2026", and
numeric hyphen dates such as "03-15-2026", and
two-digit-year numeric hyphen dates such as "03-15-26" (a legacy
export convention; the two-digit year follows Python's %y pivot,
00-68 read as 2000-2068 and 69-99 as 1969-1999, with the same
US-first order), and
dot-separated datetimes such as "2026.03.15 10:30:00" (the
date part governs, the time part is dropped), and
AM/PM dot-separated datetimes such as "2026.03.15 10:30:00 AM"
(the marker is dropped, only the date part governs), and
AM/PM timezone-suffixed dot-separated datetimes such as
"2026.03.15 10:30:00 AM Z" (the suffix trailing the marker is
dropped first, then the marker, only the date part governs), and
underscore-separated dates such as "2026_03_15", and
two-digit-year underscore-separated dates such as "03_15_26"
(a legacy export convention; the two-digit year follows
Python's %y pivot, 00-68 read as 2000-2068 and 69-99 as
1969-1999, with the same US-first order), and
weekday-prefixed underscore-separated dates such as
"Sunday, 2026_03_15" (the weekday label is dropped, only the
underscore date governs), and
timezone-suffixed underscore datetimes such as
"2026_03_15 10:30:00Z" or "2026_03_15T09:00:00-04:00" (the suffix
is dropped, only the date part governs), and
fractional-second underscore datetimes such as
"2026_03_15 10:30:00.123Z" (the fractional seconds are dropped
with the time part, only the date part governs), and
AM/PM underscore datetimes such as "2026_03_15 10:30:00 AM"
(the marker is dropped, only the date part governs), and
AM/PM timezone-suffixed underscore datetimes such as
"2026_03_15 10:30:00 AM Z" (the suffix trailing the marker is
dropped first, then the marker, only the date part governs), and
timezone-suffixed compact datetimes such as
"20260315 10:30:00Z" or "20260315T09:00:00-04:00" (the suffix
is dropped, only the date part governs), and
fractional-second compact datetimes such as
"20260315 10:30:00.123Z" (the fractional seconds are dropped
with the time part, only the date part governs), and
AM/PM timezone-suffixed compact datetimes such as
"20260315 10:30:00 AM Z" (the suffix trailing the marker is
dropped first, then the marker, only the date part governs), and
two-digit-year compact dates such as "031526" (a legacy export
convention; the two-digit year follows Python's %y pivot, 00-68 read as
2000-2068 and 69-99 as 1969-1999, with the same US-first order), and
Unix epoch timestamps such as "1710460800" (seconds, nine or ten
digits), "1710460800000" (milliseconds, twelve or thirteen
digits), "1710460800000000" (microseconds, fifteen or sixteen
digits), or "1710460800000000000" (nanoseconds, eighteen or
nineteen digits, the way API and database exports write
timestamps) — the
UTC date governs, and an epoch whose UTC date falls outside
2000-01-01..2100-01-01, or an eleven-digit bare number (ambiguous
between seconds and milliseconds), or a fourteen-digit bare number
(microseconds before 2000 only), or a seventeen-digit bare number
(nanoseconds before 2000 only), is left untouched so the gates
quarantine it normally, and
ordinal (Julian) dates such as "2026074" (YYYYDDD, the day-of-year
form the way mainframe exports write dates) or "2026-074" (the
ISO 8601 ordinal form) — the day of the year converts to its
calendar date (YYYY-MM-DD) and governs instead of quarantining
as unparseable_date; a day-of-year that is not a real day of that
year ("2026366" in 2026, which has 365 days, or "2026000") is
left untouched so the gates quarantine it normally, as is a
weekday-prefixed ordinal date with a bogus label ("Funday,
2026074"); ordinal datetimes ("2026074 10:30:00Z", fractional and
timezone-suffixed forms, and weekday-prefixed AM/PM forms such as
"Sunday, 2026075 10:30:00 am +05:30") normalize to their date
part the same way, as do space-separated timezone-suffixed
ordinal datetimes ("2026074 10:30:00 +05:00", "2026-074
10:30:00 Z"); the quality gates stay strict and see only the
normalized value, and
ISO week dates such as "2026-W11-1" (the ISO 8601 week-date form,
the way scheduling exports write dates) or "2026W111" (the compact
form) or "2026-W11" (the week alone, its Monday) — the ISO week
and weekday convert to their calendar date (YYYY-MM-DD) and govern
instead of quarantining as unparseable_date; a week that does not
exist in that year ("2025-W53-1", a 52-week year) or a weekday
outside 1-7 ("2026-W11-8") is left untouched so the gates
quarantine it normally, as is a weekday-prefixed week date with a
bogus label ("Funday, 2026-W11-1"); week-date datetimes
("2026-W11-1 10:30:00Z", fractional and timezone-suffixed forms)
normalize to their date part the same way, as do
space-separated timezone-suffixed week-date datetimes
("2026-W11-1 10:30:00 +05:00", "2026-W11-1 10:30:00 Z"); the quality gates stay
strict and see only the normalized value, and
weekday-prefixed month-name dates such as "Sunday, March 15, 2026"
(the weekday label is dropped, only the date part governs), and
weekday-prefixed ISO dates such as "Sunday, 2026-03-15" (the
weekday label is dropped, only the ISO date governs), and
weekday-prefixed slash dates such as "Sunday, 03/15/2026" (the
weekday label is dropped, only the slash date governs), and
weekday-prefixed dot-separated dates such as "Sunday, 2026.03.15"
(the weekday label is dropped, only the dot date governs), and
weekday-prefixed numeric hyphen dates such as "Sunday, 03-15-2026"
(the weekday label is dropped, only the hyphen date governs), and
timezone-suffixed numeric hyphen datetimes such as
"03-15-2026 10:30:00Z" or "15-03-2026T09:00:00-04:00" (the suffix
is dropped, only the date part governs), and
space-separated timezone-suffixed numeric hyphen datetimes such as
"03-15-2026 10:30:00 +05:00" or "03-15-2026 10:30:00 Z" (the suffix
and its separating space are dropped, only the date part governs), and
fractional-second numeric hyphen datetimes such as
"03-15-2026 10:30:00.123Z" (the fractional seconds are dropped
with the time part, only the date part governs), and
AM/PM numeric hyphen datetimes such as "03-15-2026 10:30:00 AM"
(the marker is dropped, only the date part governs), and
month-name datetimes such as "Mar 15, 2026 10:30:00" (the date part
governs, the time part is dropped), and
fractional-second month-name datetimes such as
"Mar 15, 2026 10:30:00.123Z" (the fractional seconds are dropped
with the time part, only the date part governs), and
AM/PM month-name datetimes such as "Mar 15, 2026 10:30:00 AM" (the
marker is dropped, only the date part governs), and
AM/PM timezone-suffixed month-name datetimes such as
"Mar 15, 2026 10:30:00 AM Z" (the suffix trailing the marker is
dropped first, then the marker, only the date part governs), and
space-separated timezone-suffixed month-name datetimes such as
"Mar 15, 2026 10:30:00 +05:00" or "Sun, 15 Mar 2026 10:30:00 GMT"
(the suffix and its separating space are dropped, only the date
part governs; named zones are the RFC 2822 list plus UTC), and
two-digit-year month-name dates such as "Mar 15, 26" (a legacy export
convention; the two-digit year follows Python's %y pivot, 00-68 read as
2000-2068 and 69-99 as 1969-1999, with the same forms as the
four-digit-year month-name dates) — skips blank
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
from datetime import datetime, timezone
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
    A service_date in two-digit-year slash form (MM/DD/YY, the
    way legacy exports write dates) normalizes the same way, so
    "03/15/26" governs as 2026-03-15; the two-digit year follows
    Python's strptime %y pivot (00-68 read as 2000-2068, 69-99
    as 1969-1999), so "03/15/99" governs as 1999-03-15. The
    same US-first order holds ("03/04/26" reads as 2026-03-04,
    while an unambiguous day-first "15/03/26" governs as
    2026-03-15); a leading component above 12 with a two-digit
    year therefore reads day-first ("26/03/15" governs as
    2015-03-26), and there is no separate year-first two-digit
    form. Two-digit-year slash datetimes ("03/15/26 10:30:00",
    fractional and timezone-suffixed forms included) normalize
    to their date part the same way; an impossible two-digit
    date ("02/30/26") or a malformed suffix is left untouched
    so the gates quarantine it normally.
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
    a fractional-second slash datetime ("03/15/2026
    10:30:00.123Z", "15/03/2026T09:00:00.5-04:00", or a
    weekday-prefixed "Sunday, 03/16/2026
    10:30:00.123456+05:30", the way high-resolution API and
    EHR exports write slash datetimes) normalizes the same
    way — the fractional seconds are dropped with the time
    part — as does a plain fractional-second slash datetime
    without a suffix ("03/18/2026 10:30:00.999"); an
    impossible slash datetime (e.g. "02/30/2026 10:00:00")
    or a garbage time part is left untouched so the gates
    quarantine it normally, as is a fractional slash datetime
    with a malformed suffix ("03/15/2026
    10:30:00.123+99:99"). A slash datetime carrying a named
    RFC 2822 zone ("03/15/2026 10:30:00 GMT",
    "03/15/2026T09:00:00 EST", or a weekday-prefixed "Sunday,
    03/15/2026 10:30:00 GMT", the way email headers write zoned
    slash timestamps) has the zone stripped on read and
    normalizes to its date part the same way, so it governs; the
    same holds for a named zone trailing the AM/PM marker
    ("03/15/2026 10:30:00 AM GMT") and for the
    suffix-before-marker order ("03/15/2026 10:30:00 GMT AM").
    Only the RFC 2822 obsolete-zone list plus UTC is accepted
    (UT, GMT, UTC, EST, EDT, CST, CDT, MST, MDT, PST, PDT), so
    an unknown zone (e.g. "03/15/2026 10:30:00 XYZ") is left in
    place and the gates quarantine it normally, as does an
    impossible date carrying a valid zone (e.g. "02/30/2026
    10:00:00 GMT").
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
    An AM/PM ISO datetime ("2026-03-15 10:30:00 AM" or
    "2026-03-15T09:00:00 PM", the way exports write ISO
    datetimes on a 12-hour clock) has its marker dropped on read
    and normalizes to its date part (YYYY-MM-DD) the same way,
    with the same marker handling for weekday-prefixed
    ("Sunday, 2026-03-16 09:00:00 pm") and attached-marker
    ("2026-03-15 2:30pm") forms, since the marker is stripped
    before the ISO datetime formats run; a timezone suffix
    trailing the marker ("2026-03-15 10:30:00 AM Z" or
    "2026-03-15T09:00:00 PM -04:00", or a named RFC 2822 zone
    such as "2026-03-15 10:30:00 AM GMT") is dropped first so the
    marker strips normally, as is a named zone in the
    suffix-before-marker order ("2026-03-15 10:30:00 GMT AM");
    while an impossible
    AM/PM ISO datetime ("2026-02-30 10:00:00 AM") or a
    malformed marker ("2026-03-15 10:30:00 XM") is left
    untouched so the gates quarantine it normally; the quality
    gates stay strict and see only the normalized value.
    A datetime-stamped date carrying a timezone suffix — a trailing
    "Z" (UTC), a numeric offset such as "+05:30" or "-0500", or a
    named RFC 2822 zone such as "GMT" or "EST" (the way email headers
    write zoned ISO timestamps), the way API and EHR exports write
    timestamps — has that suffix stripped before the datetime is
    parsed, so "2026-03-15T09:00:00Z", "2026-03-15 10:30:00+05:30",
    and "2026-03-15 10:30:00 GMT" also govern as their date part;
    the offset itself is not converted (the gate needs the service
    date as written, not a shifted one). Only the RFC 2822
    obsolete-zone list plus UTC is accepted (UT, GMT, UTC, EST,
    EDT, CST, CDT, MST, MDT, PST, PDT), so an unknown zone
    (e.g. "2026-03-15 10:30:00 XYZ") is left in place and the gates
    quarantine it normally. A suffix that is not a well-formed UTC
    designator or offset (e.g. "+99:99") is not stripped, so the
    value stays unparseable and the gates quarantine it normally,
    as does an impossible date carrying a valid suffix (e.g.
    "2026-02-30T09:00:00Z" or "2026-02-30 10:00:00 GMT").
    A service_date in dot-separated form (YYYY.MM.DD, another
    export convention) normalizes to ISO form (YYYY-MM-DD) on
    read, so "2026.03.15" governs instead of quarantining as
    unparseable_date; an impossible dot-separated date (e.g.
    "2026.02.30") is left untouched so the gates quarantine it
    normally. A service_date in two-digit-year dot-separated
    form ("03.15.26" or "15.03.26", the way legacy exports
    write dates) normalizes the same way, so it governs; the
    two-digit year follows Python's strptime %y pivot (00-68
    read as 2000-2068, 69-99 as 1969-1999), so "03.15.99"
    governs as 1999-03-15. The same US-first order holds
    ("03.04.26" reads as 2026-03-04, while an unambiguous
    day-first "15.03.26" governs as 2026-03-15); a leading
    component above 12 with a two-digit year therefore reads
    day-first ("26.03.15" governs as 2015-03-26), and there
    is no separate year-first two-digit form. Two-digit-year
    dot datetimes ("03.15.26 10:30:00", fractional and
    timezone-suffixed forms included) normalize to their date
    part the same way; an impossible two-digit date
    ("02.30.26") or a malformed suffix is left untouched so
    the gates quarantine it normally. A dot-separated datetime ("2026.03.15 10:30:00"
    or "2026.03.15T09:00:00", the way some exports write dot
    dates with a time stamp) normalizes to its date part the
    same way, so it governs; an impossible dot datetime (e.g.
    "2026.02.30 10:00:00") or a garbage time part is left
    untouched so the gates quarantine it normally. An AM/PM dot
    datetime ("2026.03.15 10:30:00 AM" or a weekday-prefixed
    "Sunday, 2026.03.16 09:00:00 pm", the way exports write dot
    datetimes on a 12-hour clock) has its marker dropped on read
    and normalizes the same way; an impossible AM/PM dot datetime
    or a malformed marker is left untouched so the gates
    quarantine it normally. A named RFC 2822 zone on a dot
    datetime ("2026.03.15 10:30:00 GMT",
    "2026.03.15T09:00:00 EST", or a weekday-prefixed "Sunday,
    2026.03.15 10:30:00 GMT", the way email headers write zoned
    dot timestamps) has the zone stripped on read and normalizes
    to its date part the same way, so it governs; the same holds
    for a named zone trailing the AM/PM marker ("2026.03.15
    10:30:00 AM GMT") and for the suffix-before-marker order
    ("2026.03.15 10:30:00 GMT AM"). Only the RFC 2822
    obsolete-zone list plus UTC is accepted (UT, GMT, UTC, EST,
    EDT, CST, CDT, MST, MDT, PST, PDT), so an unknown zone
    (e.g. "2026.03.15 10:30:00 XYZ") is left in place and the
    gates quarantine it normally, as does an impossible date
    carrying a valid zone (e.g. "2026.02.30 10:00:00 GMT"). A service_date in weekday-prefixed dot-separated
    form ("Sunday, 2026.03.15" or "Mon, 2026.03.16", the way
    email-style timestamps write dates) has its weekday label
    stripped on read and then normalizes the same way, so it
    governs; the weekday itself is not validated against the
    calendar date, while an impossible weekday-prefixed dot
    date ("Monday, 2026.02.30") or a bogus weekday label
    ("Funday, 2026.03.15") is left untouched so the gates
    quarantine it normally. A service_date written with a month name ("Mar 15,
    2026" or "15 Mar 2026", abbreviated or full month name, the
    way human-readable exports write dates) normalizes the same
    way, so it governs; an impossible month-name date (e.g.
    "Feb 30, 2026") or an unknown month name is left untouched
    so the gates quarantine it normally. A service_date in
    compact form (YYYYMMDD, the basic ISO 8601 form, another
    export convention) normalizes the same way, so "20260315"
    governs; a weekday-prefixed compact date ("Sunday,
    20260315" or "Mon, 20260316", the way email-style
    timestamps write dates) has its weekday label stripped
    on read and then normalizes the same way, so it governs;
    the weekday itself is not validated against the calendar
    date, while an impossible weekday-prefixed compact date
    ("Monday, 20260230") or a bogus weekday label ("Funday,
    20260315") is left untouched so the gates quarantine it
    normally; an impossible compact date (e.g. "20260230")
    is left untouched so the gates quarantine it normally.
    A timezone-suffixed compact datetime ("20260315
    10:30:00Z", "20260315T09:00:00-04:00", or a
    weekday-prefixed "Sunday, 20260316 10:30:00+05:30", the
    way API and EHR exports write compact datetimes with a
    zone) has its suffix stripped on read and normalizes to
    its date part the same way, so it governs; an impossible
    timezone-suffixed compact datetime ("20260230
    10:00:00Z") or a malformed suffix ("20260315
    10:30:00+99:99") is left untouched so the gates
    quarantine it normally. A fractional-second compact
    datetime ("20260315 10:30:00.123Z", the way
    high-resolution exports write compact datetimes)
    normalizes the same way — the fractional seconds are
    dropped with the time part — as does a plain
    fractional-second compact datetime without a suffix
    ("20260315 10:30:00.999"); an impossible fractional
    compact datetime or a malformed suffix is left
    untouched so the gates quarantine it normally. An AM/PM compact
    datetime ("20260315 10:30:00 AM", "20260315T09:00:00 PM", or a
    fractional-second "20260315 10:30:00.123 AM", the way
    exports write compact datetimes with an AM/PM marker)
    now has the marker dropped on read and normalizes to its
    date part (YYYY-MM-DD) and governs instead of quarantining
    as unparseable_date, with the same marker handling for
    weekday-prefixed ("Sunday, 20260316 09:00:00 pm") and
    attached-marker ("20260315 2:30pm") forms, since the
    marker is stripped as a candidate before the compact datetime
    formats run; while an impossible AM/PM compact datetime
    ("20260230 10:00:00 AM") or a malformed marker ("20260315
    10:30:00 XM") is left untouched so the gates quarantine it
    normally; the quality gates stay strict and see only the
    normalized value. An AM/PM timezone-suffixed compact datetime
    ("20260315 10:30:00 AM Z", "20260315T09:00:00 PM -04:00",
    or a weekday-prefixed "Sunday, 20260316 10:30:00 am
    +05:30", the way exports write zoned 12-hour compact
    timestamps) has the suffix trailing the marker dropped
    first so the marker strips normally, then normalizes the
    same way; the suffix-before-marker order ("20260315
    10:30:00Z AM") governs too, via the suffix strip after
    the marker strip; while an impossible AM/PM
    timezone-suffixed compact datetime ("20260230 10:00:00
    AM Z") or a malformed suffix ("20260315 10:30:00 AM
    +99:99") is left untouched so the gates quarantine it
    normally. A named RFC 2822 zone on a compact datetime
    ("20260315 10:30:00 GMT", "20260315T09:00:00 EST", or a
    weekday-prefixed "Sunday, 20260315 10:30:00 GMT", the way
    email headers write zoned compact timestamps) has the zone
    stripped on read and normalizes to its date part the same
    way, so it governs; the same holds for a named zone trailing
    the AM/PM marker ("20260315 10:30:00 AM GMT") and for the
    suffix-before-marker order ("20260315 10:30:00 GMT AM").
    Only the RFC 2822 obsolete-zone list plus UTC is accepted
    (UT, GMT, UTC, EST, EDT, CST, CDT, MST, MDT, PST, PDT), so
    an unknown zone (e.g. "20260315 10:30:00 XYZ") is left in
    place and the gates quarantine it normally, as does an
    impossible date carrying a valid zone (e.g. "20260230
    10:00:00 GMT"). A service_date in hyphenated month-name
    form ("15-Mar-2026"
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
    A service_date in two-digit-year numeric hyphen form
    ("03-15-26" or "15-03-26", the way legacy exports write
    dates) normalizes the same way, so it governs; the
    two-digit year follows Python's %y pivot (00-68 read as
    2000-2068, 69-99 as 1969-1999), so "03-15-99" governs as
    1999-03-15. The same US-first order holds ("03-04-26"
    reads as 2026-03-04, while an unambiguous day-first
    "15-03-26" governs as 2026-03-15); a leading component
    above 12 with a two-digit year therefore reads day-first
    ("26-03-15" governs as 2015-03-26), and there is no
    separate year-first two-digit form. Two-digit-year
    hyphen datetimes ("03-15-26 10:30:00", fractional and
    timezone-suffixed forms included) normalize to their date
    part the same way; an impossible two-digit date
    ("02-30-26") or a malformed suffix is left untouched so
    the gates quarantine it normally.
    A numeric hyphen datetime ("03-15-2026 10:30:00") or a
    timezone-suffixed numeric hyphen datetime ("03-15-2026
    10:30:00Z", "15-03-2026T09:00:00-04:00", or a
    weekday-prefixed "Sunday, 03-16-2026 10:30:00+05:30")
    normalizes to its date part the same way, with the same
    US-first order; a fractional-second numeric hyphen datetime
    ("03-15-2026 10:30:00.123Z", the way high-resolution exports
    write hyphen datetimes) normalizes the same way — the
    fractional seconds are dropped with the time part. A
    space-separated suffix ("03-15-2026 10:30:00 +05:00" or
    "03-15-2026 10:30:00 Z", the way API and EHR exports write
    zoned hyphen timestamps with a space before the zone) strips
    the same way, and the separating space goes with it. An
    impossible timezone-suffixed numeric
    hyphen datetime ("02-30-2026 10:00:00Z") or a malformed
    suffix ("03-15-2026 10:30:00+99:99") is left untouched
    so the gates quarantine it normally.
    A service_date in underscore-separated form (YYYY_MM_DD,
    the way some exports and file-naming conventions write
    dates) normalizes the same way, so "2026_03_15" governs;
    an impossible underscore-separated date (e.g.
    "2026_02_30") is left untouched so the gates quarantine
    it normally. A service_date in weekday-prefixed
    underscore-separated form ("Sunday, 2026_03_15" or "Mon,
    2026_03_16", the way email-style timestamps write dates)
    has its weekday label stripped on read and then normalizes
    the same way, so it governs; the weekday itself is not
    validated against the calendar date, while an impossible
    weekday-prefixed underscore date ("Monday, 2026_02_30")
    or a bogus weekday label ("Funday, 2026_03_15") is left
    untouched so the gates quarantine it normally.
    An underscore datetime ("2026_03_15 10:30:00") or a
    timezone-suffixed underscore datetime ("2026_03_15
    10:30:00Z", "2026_03_15T09:00:00-04:00", or a
    weekday-prefixed "Sunday, 2026_03_16 10:30:00+05:30")
    has its suffix stripped on read and normalizes to its
    date part the same way, so it governs; an impossible
    timezone-suffixed underscore datetime ("2026_02_30
    10:00:00Z") or a malformed suffix ("2026_03_15
    10:30:00+99:99") is left untouched so the gates
    quarantine it normally. A service_date in
    two-digit-year underscore-separated form ("03_15_26"
    or "15_03_26", the way legacy exports write dates)
    normalizes the same way, so it governs; the two-digit
    year follows Python's strptime %y pivot (00-68 read as
    2000-2068, 69-99 as 1969-1999), so "03_15_99" governs
    as 1999-03-15. The same US-first order holds
    ("03_04_26" reads as 2026-03-04, while an unambiguous
    day-first "15_03_26" governs as 2026-03-15); a leading
    component above 12 with a two-digit year therefore
    reads day-first ("26_03_15" governs as 2015-03-26),
    and there is no separate year-first two-digit form.
    Two-digit-year underscore datetimes ("03_15_26
    10:30:00", fractional and timezone-suffixed forms
    included) normalize to their date part the same way;
    an impossible two-digit date ("02_30_26") or a
    malformed suffix is left untouched so the gates
    quarantine it normally. A fractional-second underscore
    datetime ("2026_03_15 10:30:00.123Z",
    "2026_03_15T09:00:00.5-04:00", or a weekday-prefixed
    "Sunday, 2026_03_16 10:30:00.123456+05:30", the way
    high-resolution API and EHR exports write underscore
    datetimes) normalizes the same way — the fractional
    seconds are dropped with the time part — as does a plain
    fractional-second underscore datetime without a suffix
    ("2026_03_15 10:30:00.999"); an impossible fractional
    underscore datetime or a malformed suffix is left
    untouched so the gates quarantine it normally. An AM/PM
    underscore datetime ("2026_03_15 10:30:00 AM",
    "2026_03_15T09:00:00 PM", or a fractional-second
    "2026_03_15 10:30:00.123 AM", the way exports write
    underscore datetimes with an AM/PM marker) now has the
    marker dropped on read and normalizes to its date part
    (YYYY-MM-DD) and governs instead of quarantining as
    unparseable_date, with the same marker handling for
    weekday-prefixed ("Sunday, 2026_03_16 09:00:00 pm") and
    attached-marker ("2026_03_15 2:30pm") forms, since the
    marker is stripped as a candidate before the underscore
    datetime formats run; while an impossible AM/PM underscore
    datetime ("2026_02_30 10:00:00 AM") or a malformed marker
    ("2026_03_15 10:30:00 XM") is left untouched so the gates
    quarantine it normally; the quality gates stay strict and
    see only the normalized value. A named RFC 2822 zone on an
    underscore datetime ("2026_03_15 10:30:00 GMT",
    "2026_03_15T09:00:00 EST", or a weekday-prefixed "Sunday,
    2026_03_15 10:30:00 GMT", the way email headers write zoned
    underscore timestamps) has the zone stripped on read and
    normalizes to its date part the same way, so it governs; the
    same holds for a named zone trailing the AM/PM marker
    ("2026_03_15 10:30:00 AM GMT") and for the
    suffix-before-marker order ("2026_03_15 10:30:00 GMT AM").
    Only the RFC 2822 obsolete-zone list plus UTC is accepted
    (UT, GMT, UTC, EST, EDT, CST, CDT, MST, MDT, PST, PDT), so
    an unknown zone (e.g. "2026_03_15 10:30:00 XYZ") is left in
    place and the gates quarantine it normally, as does an
    impossible date carrying a valid zone (e.g. "2026_02_30
    10:00:00 GMT").
    A service_date in weekday-prefixed month-name
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
    before parsing and governs the same way. A service_date
    in two-digit-year month-name form ("Mar 15, 26" or
    "15 Mar 26", "15-Mar-26" or "Mar-15-26", the way legacy
    exports write dates) normalizes the same way, so it
    governs; the two-digit year follows Python's %y pivot
    (00-68 read as 2000-2068, 69-99 as 1969-1999), so
    "Mar 15, 99" governs as 1999-03-15. Two-digit-year
    month-name datetimes ("Mar 15, 26 10:30:00", fractional
    and timezone-suffixed forms included) and
    weekday-prefixed and ordinal forms ("Sunday, March 16,
    26 10:30:00 am +05:30", "March 15th, 26") normalize to
    their date part the same way; an impossible
    two-digit-year month-name date ("Feb 30, 26") or a
    malformed suffix is left untouched so the gates
    quarantine it normally. A service_date in two-digit-year
    compact form (MMDDYY or DDMMYY, "031526" or "150326",
    the way legacy mainframe exports write dates)
    normalizes the same way, so it governs; the two-digit
    year follows Python's %y pivot (00-68 read as
    2000-2068, 69-99 as 1969-1999), so "031599" governs as
    1999-03-15; the same US-first order holds, and a
    leading component above 12 reads day-first ("260315"
    governs as 2015-03-26), so there is no separate
    year-first two-digit form. Two-digit-year compact
    datetimes ("031526 10:30:00Z", fractional and
    timezone-suffixed forms, and weekday-prefixed AM/PM
    forms such as "Sunday, 031626 10:30:00 am +05:30")
    normalize to their date part the same way; while an
    impossible two-digit-year compact date ("023026") or a
    malformed suffix ("031526 10:30:00+99:99") is left
    untouched so the gates quarantine it normally; the
    quality gates stay strict and see only the normalized
    value. A service_date written as a Unix epoch timestamp —
    a bare nine- or ten-digit count of seconds since 1970-01-01
    UTC ("1710460800"), a twelve- or thirteen-digit count of
    milliseconds ("1710460800000"), a fifteen- or
    sixteen-digit count of microseconds ("1710460800000000"),
    or an eighteen- or nineteen-digit count of nanoseconds
    ("1710460800000000000"),
    the way API and database exports write timestamps —
    converts to its UTC date (YYYY-MM-DD) on read and governs
    instead of quarantining as unparseable_date; only epochs
    whose UTC date falls in 2000-01-01..2100-01-01 are accepted,
    so an epoch outside that window ("9999999999999999999" reads
    as 2286, "0000000000000000000" as 1970) or a bare number of any
    other length ("12345") is left untouched so the gates
    quarantine it normally, as is an eleven-digit bare number,
    which is ambiguous between seconds and milliseconds, and a
    fourteen-digit bare number, which can only be microseconds
    before 2000, and a seventeen-digit bare number, which can
    only be nanoseconds before 2000; the quality gates stay
    strict and see only the normalized value. A service_date
    written as an ordinal (Julian) date — a seven-digit YYYYDDD
    day-of-year form ("2026074", the way mainframe exports write
    dates) or the ISO 8601 ordinal form ("2026-074") — converts
    to its calendar date (YYYY-MM-DD) on read and governs instead
    of quarantining as unparseable_date; a day-of-year that is not
    a real day of that year ("2026366" in 2026, which has 365
    days, or "2026000") is left untouched so the gates quarantine
    it normally, as is a weekday-prefixed ordinal date with a
    bogus label ("Funday, 2026074"), which the pattern does not
    strip. A weekday-prefixed ordinal date ("Sunday, 2026075" or
    "Mon, 2026-074", the way email-style timestamps write dates)
    has its weekday label stripped on read and then normalizes the
    same way, so it governs; the weekday itself is not validated
    against the calendar date. An ordinal datetime ("2026074
    10:30:00Z", "2026-074T09:00:00-04:00", or a weekday-prefixed
    "Sunday, 2026075 10:30:00+05:30", the way API and EHR exports
    write ordinal datetimes with a zone) has its suffix stripped
    on read and normalizes to its date part the same way, so it
    governs; the offset itself is not converted. A space-separated
    suffix ("2026074 10:30:00 +05:00" or "2026-074 10:30:00 Z",
    the way API and EHR exports write zoned ordinal timestamps
    with a space before the zone) strips the same way, and the
    separating space goes with it — stripping the suffix alone
    leaves a trailing space that strptime rejects, so the
    space-separated form quarantined until now while the attached
    form governed. A fractional-second
    ordinal datetime ("2026074 10:30:00.123Z", the way
    high-resolution exports write ordinal datetimes) normalizes
    the same way — the fractional seconds are dropped with the
    time part — as does a plain fractional-second ordinal datetime
    without a suffix ("2026074 10:30:00.999"). An AM/PM ordinal
    datetime ("2026074 10:30:00 AM", "2026-074T09:00:00 PM", or a
    fractional-second "2026074 10:30:00.123 AM", the way exports
    write ordinal datetimes on a 12-hour clock) has its marker
    dropped on read and normalizes to its date part the same way,
    with the same marker handling for weekday-prefixed ("Sunday,
    2026075 09:00:00 pm") and attached-marker ("2026074 2:30pm")
    forms, since the marker is stripped as a candidate before the
    ordinal datetime formats run; while an impossible AM/PM ordinal
    datetime ("2026366 10:00:00 AM") or a malformed marker
    ("2026074 10:30:00 XM") is left untouched so the gates
    quarantine it normally; the quality gates stay strict and see
    only the normalized value. An AM/PM timezone-suffixed ordinal
    datetime ("2026074 10:30:00 AM Z", "2026-074T09:00:00 PM
    -04:00", or a weekday-prefixed "Sunday, 2026075 10:30:00 am
    +05:30", the way exports write zoned 12-hour ordinal
    timestamps) has the suffix trailing the marker dropped first
    so the marker strips normally, then normalizes the same way;
    the suffix-before-marker order ("2026074 10:30:00Z AM")
    governs too, via the suffix strip after the marker strip;
    while an impossible AM/PM timezone-suffixed ordinal datetime
    ("2026366 10:00:00 AM Z") or a malformed suffix ("2026074
    10:30:00 AM +99:99") is left untouched so the gates quarantine
    it normally. A service_date
    in weekday-prefixed ISO form ("Sunday, 2026-03-15" or
    "Mon, 2026-03-16 10:30:00", the way email-style
    timestamps write dates) has its weekday label stripped
    on read and then normalizes the same way, so it
    governs; the weekday itself is not validated against
    the calendar date, while an impossible weekday-
    prefixed ISO date ("Monday, 2026-02-30") or a bogus
    weekday label ("Funday, 2026-03-15") is left untouched
    so the gates quarantine it normally. A service_date in
    weekday-prefixed slash form ("Sunday, 03/15/2026", "Mon,
    15/03/2026", or a weekday-prefixed slash datetime "Tues,
    03/16/2026 10:30:00", the way email-style timestamps write
    dates) has its weekday label stripped on read and then
    normalizes the same way as a plain slash date, with the
    same US-first order, so it governs; the weekday itself is
    not validated against the calendar date, while an
    impossible weekday-prefixed slash date ("Monday,
    02/30/2026") or a bogus weekday label ("Funday,
    03/15/2026") is left untouched so the gates quarantine
    it normally.
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
                # Weekday-prefixed slash form: "Sunday, 03/15/2026"
                # or "Mon, 15/03/2026" — the weekday label is
                # dropped (it is not validated against the date)
                # and the remainder parses as a slash date. A
                # bogus label ("Funday, 03/15/2026") is not
                # stripped, so parsing fails and the gates
                # quarantine it normally, as does an impossible
                # weekday-prefixed date ("Monday, 02/30/2026").
                slash_date = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", date,
                    flags=re.IGNORECASE)
                # AM/PM timezone-suffixed slash datetime:
                # "03/15/2026 10:30:00 AM Z" or
                # "03/15/2026T09:00:00 PM -04:00", the way
                # exports write zoned 12-hour slash timestamps
                # — the suffix trailing the marker (a "Z", a
                # well-formed numeric offset, or a named RFC 2822
                # zone such as "03/15/2026 10:30:00 AM GMT")
                # is dropped first so the marker strips normally
                # below; the suffix-before-marker order
                # ("03/15/2026 10:30:00Z AM") already governed
                # and still does, via the timezone branch
                # further down. A malformed suffix ("10:30:00 AM
                # +99:99") or an unknown zone ("10:30:00 AM XYZ")
                # is not stripped, so the marker does not strip
                # either and the gates quarantine it normally, as
                # does an impossible date carrying a valid suffix
                # ("02/30/2026 10:00:00 AM Z").
                slash_date = re.sub(
                    r"((?:AM|PM))\s+(Z|[+-](?:0\d|1[0-4]):?[0-5]\d|"
                    r"UT|GMT|UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT)$",
                    r"\1", slash_date, flags=re.IGNORECASE)
                # AM/PM slash datetime: "03/15/2026 10:30:00 AM"
                # or "15/03/2026 02:30 PM", the way exports write
                # slash datetimes on a 12-hour clock — the marker
                # (spaced or attached, either case) is dropped
                # and the remainder parses as a slash datetime;
                # only the date part governs, so the hour itself
                # needs no conversion. A malformed marker
                # ("10:30:00 XM") is not stripped, so parsing
                # fails and the gates quarantine it normally, as
                # does an impossible AM/PM datetime ("02/30/2026
                # 10:00:00 AM").
                slash_date = re.sub(
                    r"\s*(?:AM|PM)$", "", slash_date,
                    flags=re.IGNORECASE).rstrip()
                # Two-digit-year slash form: "03/15/26" or
                # "15/03/26", the way legacy exports write dates
                # — the two-digit year follows Python's %y pivot
                # (00-68 read as 2000-2068, 69-99 as 1969-1999).
                # The US form is tried first, mirroring the
                # four-digit rule, so only an unambiguous
                # day-first date reaches the DD/MM/YY attempt; a
                # leading component above 12 therefore reads
                # day-first ("26/03/15" governs as 2015-03-26)
                # and there is no separate year-first two-digit
                # form. A four-digit year never reaches the %y
                # formats: %Y matches it first, and %y fails on
                # it (it consumes two digits, then expects "/").
                for fmt in ("%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y",
                            "%m/%d/%y", "%d/%m/%y"):
                    try:
                        cleaned["service_date"] = datetime.strptime(
                            slash_date, fmt).strftime("%Y-%m-%d")
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
                                "%m/%d/%YT%H:%M:%S.%f",
                                "%Y/%m/%d %H:%M:%S",
                                "%Y/%m/%d %H:%M",
                                "%Y/%m/%d %H:%M:%S.%f",
                                "%Y/%m/%dT%H:%M:%S",
                                "%Y/%m/%dT%H:%M:%S.%f",
                                "%d/%m/%Y %H:%M:%S",
                                "%d/%m/%Y %H:%M",
                                "%d/%m/%Y %H:%M:%S.%f",
                                "%d/%m/%YT%H:%M:%S",
                                "%d/%m/%YT%H:%M:%S.%f",
                                "%m/%d/%y %H:%M:%S",
                                "%m/%d/%y %H:%M",
                                "%m/%d/%y %H:%M:%S.%f",
                                "%m/%d/%yT%H:%M:%S",
                                "%m/%d/%yT%H:%M",
                                "%m/%d/%yT%H:%M:%S.%f",
                                "%d/%m/%y %H:%M:%S",
                                "%d/%m/%y %H:%M",
                                "%d/%m/%y %H:%M:%S.%f",
                                "%d/%m/%yT%H:%M:%S",
                                "%d/%m/%yT%H:%M:%S.%f"):
                        try:
                            cleaned["service_date"] = datetime.strptime(
                                slash_date, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    if cleaned["service_date"] == date:
                        # Timezone-suffixed slash datetime:
                        # "03/15/2026 10:30:00Z" or
                        # "03/15/2026T09:00:00-04:00", the way
                        # API and EHR exports write slash
                        # datetimes with a zone — the suffix is
                        # stripped (a trailing "Z", a
                        # well-formed numeric offset, hours
                        # 00-14, minutes 00-59, colon optional,
                        # or a named RFC 2822 zone such as
                        # "03/15/2026 10:30:00 GMT", the way
                        # email headers write zoned slash
                        # timestamps) and the date part governs;
                        # the offset itself is not converted.
                        # Only the RFC 2822 obsolete-zone list
                        # plus UTC is accepted (UT, GMT, UTC,
                        # EST, EDT, CST, CDT, MST, MDT, PST,
                        # PDT), so an unknown zone ("03/15/2026
                        # 10:30:00 XYZ") is left in place and the
                        # gates quarantine it normally. This step
                        # is also what catches the
                        # suffix-before-marker order ("03/15/2026
                        # 10:30:00 GMT AM"), where the marker
                        # strip above runs first and leaves the
                        # zone at the end. A space-separated
                        # suffix ("03/15/2026 10:30:00 +05:00"
                        # or "03/15/2026 10:30:00 Z", the way
                        # API and EHR exports write zoned slash
                        # timestamps with a space before the zone)
                        # strips the same way, and the separating
                        # space goes with it — stripping the suffix
                        # alone leaves a trailing space that
                        # strptime rejects, so the space-separated
                        # form quarantined until now while the
                        # attached form governed. A malformed
                        # suffix ("+99:99") or an unknown zone is
                        # left in place so parsing fails and the
                        # gates quarantine it normally, as does
                        # an impossible date carrying a valid
                        # suffix ("02/30/2026 10:00:00Z").
                        tz_stripped = slash_date
                        if tz_stripped.endswith("Z"):
                            tz_stripped = tz_stripped[:-1]
                        else:
                            suffix = re.search(
                                r"([+-](?:0\d|1[0-4]):?[0-5]\d)$",
                                tz_stripped)
                            if suffix is not None:
                                tz_stripped = tz_stripped[:-len(
                                    suffix.group(1))]
                            else:
                                named = re.search(
                                    r"\s+(?:UT|GMT|UTC|EST|EDT|CST|"
                                    r"CDT|MST|MDT|PST|PDT)$",
                                    tz_stripped,
                                    flags=re.IGNORECASE)
                                if named is not None:
                                    tz_stripped = tz_stripped[:-len(
                                        named.group(0))]
                        tz_stripped = tz_stripped.rstrip()
                        if tz_stripped != slash_date:
                            for fmt in ("%m/%d/%Y %H:%M:%S",
                                        "%m/%d/%Y %H:%M",
                                        "%m/%d/%Y %H:%M:%S.%f",
                                        "%m/%d/%YT%H:%M:%S",
                                        "%m/%d/%YT%H:%M",
                                        "%m/%d/%YT%H:%M:%S.%f",
                                        "%Y/%m/%d %H:%M:%S",
                                        "%Y/%m/%d %H:%M",
                                        "%Y/%m/%d %H:%M:%S.%f",
                                        "%Y/%m/%dT%H:%M:%S",
                                        "%Y/%m/%dT%H:%M:%S.%f",
                                        "%d/%m/%Y %H:%M:%S",
                                        "%d/%m/%Y %H:%M",
                                        "%d/%m/%Y %H:%M:%S.%f",
                                        "%d/%m/%YT%H:%M:%S",
                                        "%d/%m/%YT%H:%M:%S.%f",
                                        "%m/%d/%y %H:%M:%S",
                                        "%m/%d/%y %H:%M",
                                        "%m/%d/%y %H:%M:%S.%f",
                                        "%m/%d/%yT%H:%M:%S",
                                        "%m/%d/%yT%H:%M",
                                        "%m/%d/%yT%H:%M:%S.%f",
                                        "%d/%m/%y %H:%M:%S",
                                        "%d/%m/%y %H:%M",
                                        "%d/%m/%y %H:%M:%S.%f",
                                        "%d/%m/%yT%H:%M:%S",
                                        "%d/%m/%yT%H:%M:%S.%f"):
                                try:
                                    cleaned["service_date"] = (
                                        datetime.strptime(
                                            tz_stripped,
                                            fmt).strftime("%Y-%m-%d"))
                                    break
                                except ValueError:
                                    continue
                # else: not a real calendar date in any slash
                # form: left untouched, gates quarantine it.
                # The US form is tried first, so only an
                # unambiguous day-first date (first component
                # above 12) reaches the DD/MM/YYYY attempt.
            elif isinstance(date, str) and (
                    re.match(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                        r"Thu|Fri|Sat|Sun)[,\s]+)?\d{4}\.",
                        date, flags=re.IGNORECASE)
                    or re.match(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                        r"Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{1,2}\.\d{1,2}\.\d{2}(?:[ T]|$)",
                        date, flags=re.IGNORECASE)):
                # Dot-separated form only: the branch claims
                # year-first dot dates ("2026.03.15", optionally
                # weekday-prefixed) and two-digit-year dot dates
                # ("03.15.26", "15.03.26", optionally
                # weekday-prefixed or carrying a time part), not
                # every value carrying a dot — a fractional second
                # in another family ("03-15-2026 10:30:00.123Z",
                # "2026-03-15T09:00:00.123Z") must fall through
                # to its own branch instead of being claimed
                # here and left unparseable. The two-digit-year
                # guard requires the two-digit year to be
                # followed by the end of the value or a space or
                # "T", so a four-digit-year dot date ("15.03.2026")
                # is not claimed by it and still quarantines.
                # weekday-prefixed dot form ("Sunday, 2026.03.15"
                # or "Mon, 2026.03.16") has its weekday label
                # dropped (it is not validated against the date)
                # and the remainder parses as a dot-separated
                # date. A bogus label ("Funday, 2026.03.15") is
                # not stripped, so parsing fails and the gates
                # quarantine it normally, as does an impossible
                # weekday-prefixed date ("Monday, 2026.02.30").
                dot_date = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", date,
                    flags=re.IGNORECASE)
                # AM/PM timezone-suffixed dot datetime:
                # "2026.03.15 10:30:00 AM Z" or
                # "2026.03.15T09:00:00 PM -04:00", the way
                # exports write zoned 12-hour dot timestamps
                # — the suffix trailing the marker (a "Z", a
                # well-formed numeric offset, or a named RFC
                # 2822 zone such as "2026.03.15 10:30:00 AM
                # GMT") is dropped first so the marker strips
                # normally below; the suffix-before-marker order
                # ("2026.03.15 10:30:00Z AM") already governed
                # and still does, via the timezone branch
                # further down. A malformed suffix ("10:30:00
                # AM +99:99") or an unknown zone ("10:30:00 AM
                # XYZ") is not stripped, so the marker does not
                # strip either and the gates quarantine it
                # normally, as does an impossible date carrying
                # a valid suffix ("2026.02.30 10:00:00 AM Z").
                dot_date = re.sub(
                    r"((?:AM|PM))\s+(Z|[+-](?:0\d|1[0-4]):?[0-5]\d|"
                    r"UT|GMT|UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT)$",
                    r"\1", dot_date, flags=re.IGNORECASE)
                # AM/PM dot datetime: "2026.03.15 10:30:00 AM"
                # or "2026.03.15 10:30:00.123 AM", the way
                # exports write dot datetimes on a 12-hour
                # clock — the marker (spaced or attached,
                # either case) is dropped and the remainder
                # parses as a dot datetime; only the date part
                # governs, so the hour itself needs no
                # conversion. A malformed marker
                # ("10:30:00 XM") is not stripped, so parsing
                # fails and the gates quarantine it normally,
                # as does an impossible AM/PM datetime
                # ("2026.02.30 10:00:00 AM").
                dot_date = re.sub(
                    r"\s*(?:AM|PM)$", "", dot_date,
                    flags=re.IGNORECASE).rstrip()
                # Two-digit-year dot form: "03.15.26" or
                # "15.03.26", the way legacy exports write dates
                # — the two-digit year follows Python's %y pivot
                # (00-68 read as 2000-2068, 69-99 as 1969-1999).
                # The US form is tried first, mirroring the
                # four-digit rule, so only an unambiguous
                # day-first date reaches the DD.MM.YY attempt; a
                # leading component above 12 therefore reads
                # day-first ("26.03.15" governs as 2015-03-26)
                # and there is no separate year-first two-digit
                # form. A four-digit year never reaches the %y
                # formats: %Y matches it first, and %y fails on
                # it (it consumes two digits, then expects ".").
                for fmt in ("%Y.%m.%d", "%m.%d.%y", "%d.%m.%y"):
                    try:
                        cleaned["service_date"] = datetime.strptime(
                            dot_date, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
                if cleaned["service_date"] == date:
                    # Dot-separated datetime: "2026.03.15 10:30:00"
                    # or "2026.03.15T09:00:00", the way some
                    # exports write dot dates with a time stamp
                    # — the date part governs, the time part is
                    # dropped. An impossible dot datetime (e.g.
                    # "2026.02.30 10:00:00") or a garbage time
                    # part fails every format and is left
                    # untouched so the gates quarantine it.
                    # Two-digit-year dot datetimes ("03.15.26
                    # 10:30:00", fractional and timezone-suffixed
                    # forms included) normalize to their date part
                    # the same way.
                    for fmt in ("%Y.%m.%d %H:%M:%S",
                                "%Y.%m.%d %H:%M",
                                "%Y.%m.%d %H:%M:%S.%f",
                                "%Y.%m.%dT%H:%M:%S",
                                "%Y.%m.%dT%H:%M",
                                "%Y.%m.%dT%H:%M:%S.%f",
                                "%m.%d.%y %H:%M:%S",
                                "%m.%d.%y %H:%M",
                                "%m.%d.%y %H:%M:%S.%f",
                                "%m.%d.%yT%H:%M:%S",
                                "%m.%d.%yT%H:%M",
                                "%m.%d.%yT%H:%M:%S.%f",
                                "%d.%m.%y %H:%M:%S",
                                "%d.%m.%y %H:%M",
                                "%d.%m.%y %H:%M:%S.%f",
                                "%d.%m.%yT%H:%M:%S",
                                "%d.%m.%yT%H:%M",
                                "%d.%m.%yT%H:%M:%S.%f"):
                        try:
                            cleaned["service_date"] = datetime.strptime(
                                dot_date, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    if cleaned["service_date"] == date:
                        # Timezone-suffixed dot datetime:
                        # "2026.03.15 10:30:00Z" or
                        # "2026.03.15T09:00:00-04:00", the way
                        # API and EHR exports write dot
                        # datetimes with a zone — the suffix is
                        # stripped (a trailing "Z", a
                        # well-formed numeric offset, hours
                        # 00-14, minutes 00-59, colon optional,
                        # or a named RFC 2822 zone such as
                        # "2026.03.15 10:30:00 GMT", the way
                        # email headers write zoned dot
                        # timestamps) and the date part governs;
                        # the offset itself is not converted.
                        # Only the RFC 2822 obsolete-zone list
                        # plus UTC is accepted (UT, GMT, UTC,
                        # EST, EDT, CST, CDT, MST, MDT, PST,
                        # PDT), so an unknown zone ("2026.03.15
                        # 10:30:00 XYZ") is left in place and the
                        # gates quarantine it normally. A
                        # space-separated suffix ("2026.03.15
                        # 10:30:00 +05:00" or "2026.03.15
                        # 10:30:00 Z", the way API and EHR
                        # exports write zoned dot timestamps
                        # with a space before the zone) strips
                        # the same way, and the separating space
                        # goes with it — stripping the suffix
                        # alone leaves a trailing space that
                        # strptime rejects, so the space-separated
                        # form quarantined until now while the
                        # attached form governed. A malformed
                        # suffix ("+99:99") is left in place so
                        # parsing fails and the gates quarantine
                        # it normally, as does an impossible date
                        # carrying a valid suffix
                        # ("2026.02.30 10:00:00Z").
                        tz_stripped = dot_date
                        if tz_stripped.endswith("Z"):
                            tz_stripped = tz_stripped[:-1]
                        else:
                            suffix = re.search(
                                r"([+-](?:0\d|1[0-4]):?[0-5]\d)$",
                                tz_stripped)
                            if suffix is not None:
                                tz_stripped = tz_stripped[:-len(
                                    suffix.group(1))]
                            else:
                                named = re.search(
                                    r"\s+(?:UT|GMT|UTC|EST|EDT|CST|"
                                    r"CDT|MST|MDT|PST|PDT)$",
                                    tz_stripped,
                                    flags=re.IGNORECASE)
                                if named is not None:
                                    tz_stripped = tz_stripped[:-len(
                                        named.group(0))]
                        tz_stripped = tz_stripped.rstrip()
                        if tz_stripped != dot_date:
                            for fmt in ("%Y.%m.%d %H:%M:%S",
                                        "%Y.%m.%d %H:%M",
                                        "%Y.%m.%d %H:%M:%S.%f",
                                        "%Y.%m.%dT%H:%M:%S",
                                        "%Y.%m.%dT%H:%M",
                                        "%Y.%m.%dT%H:%M:%S.%f",
                                        "%m.%d.%y %H:%M:%S",
                                        "%m.%d.%y %H:%M",
                                        "%m.%d.%y %H:%M:%S.%f",
                                        "%m.%d.%yT%H:%M:%S",
                                        "%m.%d.%yT%H:%M",
                                        "%m.%d.%yT%H:%M:%S.%f",
                                        "%d.%m.%y %H:%M:%S",
                                        "%d.%m.%y %H:%M",
                                        "%d.%m.%y %H:%M:%S.%f",
                                        "%d.%m.%yT%H:%M:%S",
                                        "%d.%m.%yT%H:%M",
                                        "%d.%m.%yT%H:%M:%S.%f"):
                                try:
                                    cleaned["service_date"] = (
                                        datetime.strptime(
                                            tz_stripped,
                                            fmt).strftime("%Y-%m-%d"))
                                    break
                                except ValueError:
                                    continue
                    # else: not a real calendar date in dot form:
                    # left untouched, gates quarantine it
            elif isinstance(date, str) and (
                    re.fullmatch(r"\d{4}_\d{2}_\d{2}", date)
                    or re.fullmatch(
                        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                        r"Thu|Fri|Sat|Sun)[,\s]+\d{4}_\d{2}_\d{2}",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{4}_\d{2}_\d{2}[ T]\d{2}:\d{2}"
                        r"(?::\d{2}(?:\.\d+)?)?"
                        r"(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|GMT|"
                        r"UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT))?",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{4}_\d{2}_\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{4}_\d{2}_\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)\s+"
                        r"(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|GMT|UTC|"
                        r"EST|EDT|CST|CDT|MST|MDT|PST|PDT)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{4}_\d{2}_\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|"
                        r"GMT|UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT))"
                        r"\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(r"\d{1,2}_\d{1,2}_\d{2}", date)
                    or re.fullmatch(
                        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                        r"Thu|Fri|Sat|Sun)[,\s]+\d{1,2}_\d{1,2}_\d{2}",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{1,2}_\d{1,2}_\d{2}[ T]\d{2}:\d{2}"
                        r"(?::\d{2}(?:\.\d+)?)?"
                        r"(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|GMT|"
                        r"UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT))?",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{1,2}_\d{1,2}_\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{1,2}_\d{1,2}_\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)\s+"
                        r"(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|GMT|UTC|"
                        r"EST|EDT|CST|CDT|MST|MDT|PST|PDT)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{1,2}_\d{1,2}_\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|"
                        r"GMT|UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT))"
                        r"\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)):
                # Underscore-separated form: YYYY_MM_DD (the way
                # some exports and file-naming conventions write
                # dates), or the weekday-prefixed form ("Sunday,
                # 2026_03_15" or "Mon, 2026_03_16", the way
                # email-style timestamps write dates) — the
                # weekday label is dropped (it is not validated
                # against the date) and the remainder parses as
                # an underscore-separated date. An underscore
                # datetime ("2026_03_15 10:30:00", the way some
                # exports write underscore dates with a time
                # stamp) normalizes to its date part the same
                # way, as does a timezone-suffixed underscore
                # datetime ("2026_03_15 10:30:00Z",
                # "2026_03_15T09:00:00-04:00", or a
                # weekday-prefixed "Sunday, 2026_03_16
                # 10:30:00+05:30", the way API and EHR exports
                # write underscore datetimes with a zone) — the
                # suffix is stripped (a trailing "Z", or a
                # well-formed numeric offset, hours 00-14,
                # minutes 00-59, colon optional) and the date
                # part governs; the offset itself is not
                # converted. A space-separated suffix
                # ("2026_03_15 10:30:00 +05:00" or
                # "2026_03_15 10:30:00 Z", the way API and EHR
                # exports write zoned underscore timestamps
                # with a space before the zone) strips the same
                # way, and the separating space goes with it —
                # stripping the suffix alone leaves a trailing
                # space that strptime rejects, so the
                # space-separated form quarantined until now
                # while the attached form governed (verified by
                # probe before the fix; the guard arms are
                # strict fullmatches, so they widen to accept
                # an optional space before the trailing zone
                # too; the same latent issue still stands in
                # the two-digit-year compact family for a later
                # run). A fractional-second
                # underscore datetime ("2026_03_15 10:30:00.123Z", the
                # way high-resolution exports write underscore
                # datetimes) normalizes the same way — the
                # fractional seconds are dropped with the time
                # part. An AM/PM underscore datetime
                # ("2026_03_15 10:30:00 AM", the way exports
                # write underscore datetimes on a 12-hour
                # clock) has its marker dropped on read and
                # normalizes to its date part the same way,
                # with the same marker handling for
                # weekday-prefixed ("Sunday, 2026_03_16
                # 09:00:00 pm") and attached-marker
                # ("2026_03_15 2:30pm") forms, since the marker
                # is stripped as a candidate before the
                # underscore datetime formats run; while an
                # impossible AM/PM underscore datetime
                # ("2026_02_30 10:00:00 AM") or a malformed
                # marker ("2026_03_15 10:30:00 XM") is left
                # untouched so the gates quarantine it
                # normally. An AM/PM timezone-suffixed
                # underscore datetime ("2026_03_15 10:30:00
                # AM Z", "2026_03_15T09:00:00 PM -04:00", or a
                # weekday-prefixed "Sunday, 2026_03_16
                # 10:30:00 am +05:30") has the suffix trailing
                # the marker dropped first so the marker
                # strips normally, and the suffix-before-
                # marker order ("2026_03_15 10:30:00Z AM")
                # governs too; while an impossible AM/PM
                # timezone-suffixed underscore datetime
                # ("2026_02_30 10:00:00 AM Z") or a malformed
                # suffix ("2026_03_15 10:30:00 AM +99:99") is
                # left untouched so the gates quarantine it
                # normally. A named RFC 2822 zone on an
                # underscore datetime ("2026_03_15 10:30:00
                # GMT", "2026_03_15T09:00:00 EST", or a
                # weekday-prefixed "Sunday, 2026_03_15
                # 10:30:00 GMT", the way email headers write
                # zoned underscore timestamps) has the zone
                # stripped the same way and normalizes to its
                # date part; only the RFC 2822 obsolete-zone
                # list plus UTC is accepted (UT, GMT, UTC, EST,
                # EDT, CST, CDT, MST, MDT, PST, PDT), so an
                # unknown zone ("2026_03_15 10:30:00 XYZ") is
                # left in place and the gates quarantine it
                # normally, as does an impossible date carrying
                # a valid zone ("2026_02_30 10:00:00 GMT").
                # The same holds for a named zone trailing the
                # AM/PM marker ("2026_03_15 10:30:00 AM GMT")
                # and for the suffix-before-marker order
                # ("2026_03_15 10:30:00 GMT AM"), which governs
                # via the suffix strip after the marker strip.
                # A two-digit-year underscore date
                # ("03_15_26" or "15_03_26", the way legacy
                # exports write dates) normalizes the same way:
                # the guard admits a two-digit year alongside
                # the four-digit one, and the %y formats below
                # follow Python's strptime pivot (00-68 read as
                # 2000-2068, 69-99 as 1969-1999). The US form
                # is tried first, so only an unambiguous
                # day-first date reaches the DD_MM_YY attempt; a
                # leading component above 12 therefore reads
                # day-first ("26_03_15" governs as 2015-03-26)
                # and there is no separate year-first two-digit
                # form. Two-digit-year underscore datetimes
                # (fractional and timezone-suffixed forms
                # included) normalize to their date part the
                # same way; an impossible two-digit date
                # ("02_30_26") or a malformed suffix is left
                # untouched so the gates quarantine it normally.
                # An impossible date fails parsing
                # and is left untouched so the gates quarantine
                # it, as does a bogus weekday label ("Funday,
                # 2026_03_15"), which the pattern does not
                # strip, and a malformed suffix ("2026_03_15
                # 10:30:00+99:99"), which the guard does not
                # match, so the value falls through to the
                # generic datetime branch and quarantines.
                underscore_date = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", date,
                    flags=re.IGNORECASE)
                # AM/PM timezone-suffixed underscore datetime:
                # "2026_03_15 10:30:00 AM Z" or
                # "2026_03_15T09:00:00 PM -04:00", the way
                # exports write zoned 12-hour underscore
                # timestamps — the suffix trailing the marker
                # (a "Z", a well-formed numeric offset, or a
                # named RFC 2822 zone such as "2026_03_15
                # 10:30:00 AM GMT") is dropped first so the
                # marker strips normally below; the
                # suffix-before-marker order ("2026_03_15
                # 10:30:00Z AM") governs too, via the suffix
                # strip after the marker strip further down. A
                # malformed suffix ("10:30:00 AM +99:99") or an
                # unknown zone ("10:30:00 AM XYZ") is not
                # stripped, so the marker does not strip either
                # and the gates quarantine it normally, as does an
                # impossible date carrying a valid suffix
                # ("2026_02_30 10:00:00 AM Z").
                underscore_date = re.sub(
                    r"((?:AM|PM))\s+(Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|"
                    r"GMT|UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT)$",
                    r"\1", underscore_date, flags=re.IGNORECASE)
                # AM/PM underscore datetime: "2026_03_15 10:30:00 AM"
                # or "2026_03_15 10:30:00.123 AM", the way
                # exports write underscore datetimes on a 12-hour
                # clock — the marker (spaced or attached,
                # either case) is dropped and the remainder
                # parses as an underscore datetime; only the date
                # part governs, so the hour itself needs no
                # conversion. A malformed marker
                # ("10:30:00 XM") is not stripped, so parsing
                # fails and the gates quarantine it normally, as
                # does an impossible AM/PM datetime
                # ("2026_02_30 10:00:00 AM").
                underscore_date = re.sub(
                    r"\s*(?:AM|PM)$", "", underscore_date,
                    flags=re.IGNORECASE).rstrip()
                if underscore_date.endswith("Z"):
                    underscore_date = underscore_date[:-1]
                else:
                    suffix = re.search(
                        r"([+-](?:0\d|1[0-4]):?[0-5]\d)$",
                        underscore_date)
                    if suffix is not None:
                        underscore_date = underscore_date[:-len(
                            suffix.group(1))]
                    else:
                        named = re.search(
                            r"\s+(?:UT|GMT|UTC|EST|EDT|CST|CDT|"
                            r"MST|MDT|PST|PDT)$",
                            underscore_date,
                            flags=re.IGNORECASE)
                        if named is not None:
                            underscore_date = underscore_date[:-len(
                                named.group(0))]
                # A space-separated suffix ("2026_03_15 10:30:00
                # +05:00") leaves a trailing space behind after
                # the strip above, which strptime rejects, so the
                # space goes with the suffix.
                underscore_date = underscore_date.rstrip()
                try:
                    cleaned["service_date"] = datetime.strptime(
                        underscore_date, "%Y_%m_%d").strftime("%Y-%m-%d")
                except ValueError:
                    for fmt in ("%Y_%m_%d %H:%M:%S.%f",
                                "%Y_%m_%dT%H:%M:%S.%f",
                                "%Y_%m_%d %H:%M:%S",
                                "%Y_%m_%d %H:%M",
                                "%Y_%m_%dT%H:%M:%S",
                                "%Y_%m_%dT%H:%M"):
                        try:
                            cleaned["service_date"] = datetime.strptime(
                                underscore_date, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    if cleaned["service_date"] == date:
                        # Two-digit-year underscore form: "03_15_26"
                        # or "15_03_26", the way legacy exports
                        # write dates — the two-digit year follows
                        # Python's %y pivot (00-68 read as
                        # 2000-2068, 69-99 as 1969-1999). The US
                        # form is tried first, mirroring the
                        # four-digit rule, so only an unambiguous
                        # day-first date reaches the DD_MM_YY
                        # attempt; a leading component above 12
                        # therefore reads day-first ("26_03_15"
                        # governs as 2015-03-26) and there is no
                        # separate year-first two-digit form.
                        # Two-digit-year underscore datetimes
                        # (fractional and timezone-suffixed forms
                        # included) normalize to their date part
                        # the same way; an impossible two-digit
                        # date ("02_30_26") or a malformed suffix
                        # is left untouched so the gates quarantine
                        # it normally.
                        for fmt in ("%m_%d_%y %H:%M:%S.%f",
                                    "%m_%d_%yT%H:%M:%S.%f",
                                    "%d_%m_%y %H:%M:%S.%f",
                                    "%d_%m_%yT%H:%M:%S.%f",
                                    "%m_%d_%y %H:%M:%S", "%m_%d_%y %H:%M",
                                    "%m_%d_%yT%H:%M:%S", "%m_%d_%yT%H:%M",
                                    "%d_%m_%y %H:%M:%S", "%d_%m_%y %H:%M",
                                    "%d_%m_%yT%H:%M:%S", "%d_%m_%yT%H:%M",
                                    "%m_%d_%y", "%d_%m_%y"):
                            try:
                                cleaned["service_date"] = (
                                    datetime.strptime(
                                        underscore_date,
                                        fmt).strftime("%Y-%m-%d"))
                                break
                            except ValueError:
                                continue
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
                # every format and quarantines normally. A
                # month-name datetime ("Mar 15, 2026 10:30:00"
                # or "15 Mar 2026T09:00:00", the way exports
                # write month-name dates with a time stamp)
                # normalizes to its date part the same way, so
                # it governs; an impossible month-name datetime
                # (e.g. "Feb 30, 2026 10:00:00") or a garbage
                # time part is left untouched so the gates
                # quarantine it normally. A fractional-second
                # month-name datetime ("Mar 15, 2026
                # 10:30:00.123Z" or "15 Mar 2026T09:00:00.5-04:00",
                # the way high-resolution exports write
                # month-name datetimes) normalizes the same way
                # — the fractional seconds are dropped with the
                # time part — as does a plain fractional-second
                # month-name datetime without a suffix ("Mar 15,
                # 2026 10:30:00.999"); an impossible fractional
                # month-name datetime or a malformed suffix is
                # left untouched so the gates quarantine it
                # normally. A weekday-prefixed
                # month-name datetime ("Sunday, Mar 15, 2026
                # 10:30:00") strips the weekday label first and
                # then normalizes the same way. A timezone
                # suffix on a month-name datetime ("Mar 15,
                # 2026 10:30:00Z" or "15 Mar 2026T09:00:00-04:00",
                # the way exports write month-name datetimes
                # with a zone) is stripped before parsing, so
                # it governs; a malformed suffix ("Mar 15,
                # 2026 10:30:00+99:99") is left in place so the
                # gates quarantine it normally. A space-separated
                # suffix ("Mar 15, 2026 10:30:00 +05:00") or a
                # named RFC 2822 zone ("Sun, 15 Mar 2026
                # 10:30:00 GMT") strips the same way — see the
                # timezone step below; an unknown zone is left
                # in place so the gates quarantine it normally. A T-separated
                # hyphenated month-name datetime
                # ("15-Mar-2026T09:00:00" or
                # "Mar-15-2026T09:00:00.123Z", the way exports
                # write hyphenated month-name datetimes with a
                # T separator) normalizes to its date part the
                # same way, with the same timezone-suffix and
                # fractional-second handling; an impossible
                # T-separated hyphenated month-name datetime
                # or a malformed suffix is left untouched so
                # the gates quarantine it normally. An AM/PM
                # month-name datetime ("Mar 15, 2026 10:30:00
                # AM" or "15 Mar 2026 02:30 PM", the way exports
                # write month-name datetimes on a 12-hour
                # clock) has its marker dropped and normalizes
                # the same way; an impossible AM/PM datetime
                # or a malformed marker ("10:30:00 XM") is left
                # untouched so the gates quarantine it normally.
                # An AM/PM timezone-suffixed month-name
                # datetime ("Mar 15, 2026 10:30:00 AM Z" or
                # "15 Mar 2026T09:00:00 PM -04:00", the way
                # exports write zoned 12-hour month-name
                # timestamps) has the suffix trailing the
                # marker dropped first so the marker strips
                # normally, and the suffix-before-marker
                # order ("Mar 15, 2026 10:30:00Z AM") governs
                # too; while an impossible AM/PM
                # timezone-suffixed month-name datetime
                # ("Feb 30, 2026 10:00:00 AM Z") or a
                # malformed suffix ("Mar 15, 2026 10:30:00
                # AM +99:99") is left untouched so the gates
                # quarantine it normally. A two-digit-year
                # month-name date ("Mar 15, 26" or "15 Mar 26",
                # "15-Mar-26" or "Mar-15-26", the way legacy
                # exports write dates) normalizes the same way:
                # the %y formats below follow Python's strptime
                # pivot (00-68 read as 2000-2068, 69-99 as
                # 1969-1999), so "Mar 15, 99" governs as
                # 1999-03-15; the four-digit formats are tried
                # first, so a four-digit year never reaches a
                # %y format. Two-digit-year month-name
                # datetimes (fractional and timezone-suffixed
                # forms included) and weekday-prefixed and
                # ordinal forms ("Sunday, March 16, 26
                # 10:30:00 am +05:30", "March 15th, 26")
                # normalize to their date part the same way,
                # through the same candidate stripping; an
                # impossible two-digit-year month-name date
                # ("Feb 30, 26") or a malformed suffix is left
                # untouched so the gates quarantine it normally.
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
                # AM/PM timezone-suffixed month-name datetime:
                # "Mar 15, 2026 10:30:00 AM Z" or "15 Mar
                # 2026T09:00:00 PM -04:00", the way exports
                # write zoned 12-hour month-name timestamps —
                # the suffix trailing the marker (a "Z", or a
                # well-formed numeric offset) is dropped first
                # so the marker strips normally in the step
                # below; the suffix-before-marker order
                # ("Mar 15, 2026 10:30:00Z AM") governs too,
                # via the suffix strip after the marker strip
                # further down. A malformed suffix ("Mar 15,
                # 2026 10:30:00 AM +99:99") is not stripped,
                # so the marker does not strip either and the
                # gates quarantine it normally, as does an
                # impossible date carrying a valid suffix
                # ("Feb 30, 2026 10:00:00 AM Z").
                for base in list(candidates):
                    marker_suffix_stripped = re.sub(
                        r"((?:AM|PM))\s+"
                        r"(Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|GMT|UTC|"
                        r"EST|EDT|CST|CDT|MST|MDT|PST|PDT)$",
                        r"\1", base, flags=re.IGNORECASE)
                    if (marker_suffix_stripped != base
                            and marker_suffix_stripped not in candidates):
                        candidates.append(marker_suffix_stripped)
                # AM/PM form: "Mar 15, 2026 10:30:00 AM" or
                # "15 Mar 2026 02:30 PM", the way exports write
                # month-name datetimes on a 12-hour clock — the
                # marker (spaced or attached, either case) is
                # dropped and the remainder parses as a
                # month-name datetime; only the date part
                # governs, so the hour itself needs no
                # conversion. A malformed marker ("10:30:00 XM")
                # is not stripped, so parsing fails and the
                # gates quarantine it normally, as does an
                # impossible AM/PM datetime ("Feb 30, 2026
                # 10:00:00 AM"). Added before the ordinal and
                # timezone steps so those also apply to the
                # AM/PM-stripped candidates.
                for base in list(candidates):
                    ampm_stripped = re.sub(
                        r"\s*(?:AM|PM)$", "", base,
                        flags=re.IGNORECASE).rstrip()
                    if (ampm_stripped != base
                            and ampm_stripped not in candidates):
                        candidates.append(ampm_stripped)
                for base in list(candidates):
                    stripped = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", base)
                    if stripped != base and stripped not in candidates:
                        candidates.append(stripped)
                # Space-separated timezone suffix on a month-name
                # datetime ("Mar 15, 2026 10:30:00 +05:00" or
                # "15 Mar 2026 10:30:00 -0400", the way API and
                # EHR exports write zoned month-name timestamps
                # with a space before the offset): the offset
                # is stripped, and the separating space goes
                # with it — stripping the suffix alone leaves
                # a trailing space that strptime rejects, so
                # the space-separated form quarantined until
                # now while the attached form governed. A space
                # before a "Z" ("Mar 15, 2026 10:30:00 Z")
                # strips the same way. A named RFC 2822 zone
                # ("Sun, 15 Mar 2026 10:30:00 GMT", "15 Mar
                # 2026 10:30:00 EST", "Mar 15, 2026 10:30:00
                # UTC", the way email headers write zoned
                # month-name timestamps) is stripped too, but
                # only from the RFC 2822 obsolete-zone list
                # plus UTC — UT, GMT, UTC, EST, EDT, CST, CDT,
                # MST, MDT, PST, PDT — so an unknown zone
                # ("15 Mar 2026 10:30:00 XYZ") is left in place
                # and the gates quarantine it normally, as is
                # a malformed numeric suffix ("Mar 15, 2026
                # 10:30:00 +99:99") or an impossible date
                # carrying a valid suffix ("Feb 30, 2026
                # 10:00:00 GMT"). Only the date part governs,
                # so no zone is ever converted. The AM/PM
                # marker step above already drops a named zone
                # trailing a marker ("10:30:00 AM GMT").
                for base in list(candidates):
                    tz_stripped = base
                    if tz_stripped.endswith("Z"):
                        tz_stripped = tz_stripped[:-1]
                    else:
                        suffix = re.search(
                            r"([+-](?:0\d|1[0-4]):?[0-5]\d)$",
                            tz_stripped)
                        if suffix is not None:
                            tz_stripped = tz_stripped[:-len(
                                suffix.group(1))]
                        else:
                            named = re.search(
                                r"\s+(?:UT|GMT|UTC|EST|EDT|CST|CDT|"
                                r"MST|MDT|PST|PDT)$",
                                tz_stripped, flags=re.IGNORECASE)
                            if named is not None:
                                tz_stripped = tz_stripped[:-len(
                                    named.group(0))]
                    tz_stripped = tz_stripped.rstrip()
                    if (tz_stripped != base
                            and tz_stripped not in candidates):
                        candidates.append(tz_stripped)
                for candidate in candidates:
                    for fmt in ("%b %d, %Y", "%B %d, %Y",
                                "%d %b %Y", "%d %B %Y",
                                "%d-%b-%Y", "%b-%d-%Y",
                                "%d-%B-%Y", "%B-%d-%Y",
                                "%b %d, %Y %H:%M:%S",
                                "%B %d, %Y %H:%M:%S",
                                "%b %d, %Y %H:%M",
                                "%B %d, %Y %H:%M",
                                "%b %d, %YT%H:%M:%S",
                                "%B %d, %YT%H:%M:%S",
                                "%d %b %Y %H:%M:%S",
                                "%d %B %Y %H:%M:%S",
                                "%d %b %Y %H:%M",
                                "%d %B %Y %H:%M",
                                "%d %b %YT%H:%M:%S",
                                "%d %B %YT%H:%M:%S",
                                "%d-%b-%Y %H:%M:%S",
                                "%b-%d-%Y %H:%M:%S",
                                "%d-%B-%Y %H:%M:%S",
                                "%B-%d-%Y %H:%M:%S",
                                "%d-%b-%YT%H:%M:%S",
                                "%b-%d-%YT%H:%M:%S",
                                "%d-%B-%YT%H:%M:%S",
                                "%B-%d-%YT%H:%M:%S",
                                "%b %d, %Y %H:%M:%S.%f",
                                "%B %d, %Y %H:%M:%S.%f",
                                "%b %d, %YT%H:%M:%S.%f",
                                "%B %d, %YT%H:%M:%S.%f",
                                "%d %b %Y %H:%M:%S.%f",
                                "%d %B %Y %H:%M:%S.%f",
                                "%d %b %YT%H:%M:%S.%f",
                                "%d %B %YT%H:%M:%S.%f",
                                "%d-%b-%Y %H:%M:%S.%f",
                                "%b-%d-%Y %H:%M:%S.%f",
                                "%d-%B-%Y %H:%M:%S.%f",
                                "%B-%d-%Y %H:%M:%S.%f",
                                "%d-%b-%YT%H:%M:%S.%f",
                                "%b-%d-%YT%H:%M:%S.%f",
                                "%d-%B-%YT%H:%M:%S.%f",
                                "%B-%d-%YT%H:%M:%S.%f",
                                "%b %d, %y", "%B %d, %y",
                                "%d %b %y", "%d %B %y",
                                "%d-%b-%y", "%b-%d-%y",
                                "%d-%B-%y", "%B-%d-%y",
                                "%b %d, %y %H:%M:%S",
                                "%B %d, %y %H:%M:%S",
                                "%b %d, %y %H:%M",
                                "%B %d, %y %H:%M",
                                "%b %d, %yT%H:%M:%S",
                                "%B %d, %yT%H:%M:%S",
                                "%d %b %y %H:%M:%S",
                                "%d %B %y %H:%M:%S",
                                "%d %b %y %H:%M",
                                "%d %B %y %H:%M",
                                "%d %b %yT%H:%M:%S",
                                "%d %B %yT%H:%M:%S",
                                "%d-%b-%y %H:%M:%S",
                                "%b-%d-%y %H:%M:%S",
                                "%d-%B-%y %H:%M:%S",
                                "%B-%d-%y %H:%M:%S",
                                "%d-%b-%yT%H:%M:%S",
                                "%b-%d-%yT%H:%M:%S",
                                "%d-%B-%yT%H:%M:%S",
                                "%B-%d-%yT%H:%M:%S",
                                "%b %d, %y %H:%M:%S.%f",
                                "%B %d, %y %H:%M:%S.%f",
                                "%b %d, %yT%H:%M:%S.%f",
                                "%B %d, %yT%H:%M:%S.%f",
                                "%d %b %y %H:%M:%S.%f",
                                "%d %B %y %H:%M:%S.%f",
                                "%d %b %yT%H:%M:%S.%f",
                                "%d %B %yT%H:%M:%S.%f",
                                "%d-%b-%y %H:%M:%S.%f",
                                "%b-%d-%y %H:%M:%S.%f",
                                "%d-%B-%y %H:%M:%S.%f",
                                "%B-%d-%y %H:%M:%S.%f",
                                "%d-%b-%yT%H:%M:%S.%f",
                                "%b-%d-%yT%H:%M:%S.%f",
                                "%d-%B-%yT%H:%M:%S.%f",
                                "%B-%d-%yT%H:%M:%S.%f"):
                        try:
                            cleaned["service_date"] = datetime.strptime(
                                candidate, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    if cleaned["service_date"] != date:
                        break
            elif isinstance(date, str) and (
                    re.fullmatch(r"\d{1,2}-\d{1,2}-(?:\d{4}|\d{2})", date)
                    or re.fullmatch(
                        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                        r"Thu|Fri|Sat|Sun)[,\s]+\d{1,2}-\d{1,2}-(?:\d{4}|\d{2})",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{1,2}-\d{1,2}-(?:\d{4}|\d{2})[ T]\d{2}:\d{2}"
                        r"(?::\d{2}(?:\.\d+)?)?"
                        r"(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d))?",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{1,2}-\d{1,2}-(?:\d{4}|\d{2})[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{1,2}-\d{1,2}-(?:\d{4}|\d{2})[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)\s+"
                        r"(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{1,2}-\d{1,2}-(?:\d{4}|\d{2})[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d))"
                        r"\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)):
                # Numeric hyphen form: "03-15-2026" (US) or an
                # unambiguous day-first "15-03-2026", or the
                # weekday-prefixed form ("Sunday, 03-15-2026" or
                # "Mon, 15-03-2026", the way email-style
                # timestamps write dates) — the weekday label is
                # dropped (it is not validated against the date)
                # and the remainder parses as a numeric hyphen
                # date. The US form is tried first, mirroring the
                # slash-date rule, so only a first component
                # above 12 reaches the DD-MM-YYYY attempt. An ISO
                # date never reaches here: its four-digit first
                # component does not match the pattern. An
                # impossible date fails every format and is left
                # untouched so the gates quarantine it normally,
                # as does a bogus weekday label ("Funday,
                # 03-15-2026"), which the pattern does not strip.
                # A numeric hyphen datetime ("03-15-2026
                # 10:30:00", the way some exports write hyphen
                # dates with a time stamp) normalizes to its
                # date part the same way, as does a
                # timezone-suffixed numeric hyphen datetime
                # ("03-15-2026 10:30:00Z",
                # "15-03-2026T09:00:00-04:00", or a
                # weekday-prefixed "Sunday, 03-16-2026
                # 10:30:00+05:30", the way API and EHR exports
                # write hyphen datetimes with a zone) — the
                # suffix is stripped (a trailing "Z", or a
                # well-formed numeric offset, hours 00-14,
                # minutes 00-59, colon optional) and the date
                # part governs; the offset itself is not
                # converted. A space-separated suffix
                # ("03-15-2026 10:30:00 +05:00" or
                # "03-15-2026 10:30:00 Z", the way API and EHR
                # exports write zoned hyphen timestamps with a
                # space before the zone) strips the same way,
                # and the separating space goes with it —
                # stripping the suffix alone leaves a trailing
                # space that strptime rejects, so the
                # space-separated form quarantined until now
                # while the attached form governed (verified by
                # probe before the fix; the guard arms are
                # strict fullmatches, so they widen to accept
                # an optional space before the trailing zone
                # too; the same latent issue still stands in
                # the two-digit-year compact family for a later
                # run). A fractional-second hyphen datetime
                # ("03-15-2026 10:30:00.123Z", the way
                # high-resolution exports write hyphen datetimes)
                # normalizes the same way — the fractional
                # seconds are dropped with the time part. An
                # AM/PM numeric hyphen datetime ("03-15-2026
                # 10:30:00 AM", the way exports write hyphen
                # datetimes on a 12-hour clock) has its marker
                # dropped on read and normalizes to its date
                # part the same way, with the same marker
                # handling for weekday-prefixed ("Sunday,
                # 03-16-2026 09:00:00 pm") and attached-marker
                # ("03-15-2026 2:30pm") forms, since the marker
                # is stripped before the hyphen datetime formats
                # run; while an impossible AM/PM hyphen datetime
                # ("02-30-2026 10:00:00 AM") or a malformed
                # marker ("03-15-2026 10:30:00 XM") is left
                # untouched so the gates quarantine it normally.
                # An AM/PM timezone-suffixed numeric hyphen
                # datetime ("03-15-2026 10:30:00 AM Z",
                # "15-03-2026T09:00:00 PM -04:00", or a
                # weekday-prefixed "Sunday, 03-16-2026
                # 10:30:00 am +05:30") has the suffix trailing
                # the marker dropped first so the marker
                # strips normally, and the suffix-before-
                # marker order ("03-15-2026 10:30:00Z AM")
                # governs too; while an impossible AM/PM
                # timezone-suffixed hyphen datetime
                # ("02-30-2026 10:00:00 AM Z") or a malformed
                # suffix ("03-15-2026 10:30:00 AM +99:99") is
                # left untouched so the gates quarantine it
                # normally. A malformed suffix ("03-15-2026
                # 10:30:00+99:99") does not match the guard, so
                # the value falls through to the generic
                # datetime branch and quarantines.
                # A two-digit-year numeric hyphen date
                # ("03-15-26" or "15-03-26", the way legacy
                # exports write dates) normalizes the same way:
                # the guard admits a two-digit year alongside
                # the four-digit one, and the %y formats below
                # follow Python's strptime pivot (00-68 read as
                # 2000-2068, 69-99 as 1969-1999). The US form
                # is tried first, so only an unambiguous
                # day-first date reaches the DD-MM-YY attempt; a
                # leading component above 12 therefore reads
                # day-first ("26-03-15" governs as 2015-03-26)
                # and there is no separate year-first two-digit
                # form. Two-digit-year hyphen datetimes
                # (fractional and timezone-suffixed forms
                # included) normalize to their date part the
                # same way; an impossible two-digit date
                # ("02-30-26") or a malformed suffix is left
                # untouched so the gates quarantine it normally.
                hyphen_date = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", date,
                    flags=re.IGNORECASE)
                # AM/PM numeric hyphen datetime: "03-15-2026
                # 10:30:00 AM" or "03-15-2026 10:30:00.123 AM",
                # the way exports write hyphen datetimes on a
                # 12-hour clock — the marker (spaced or attached,
                # either case) is dropped and the remainder
                # parses as a numeric hyphen datetime; only the
                # date part governs, so the hour itself needs no
                # conversion. A malformed marker
                # ("10:30:00 XM") is not stripped, so parsing
                # fails and the gates quarantine it normally, as
                # does an impossible AM/PM datetime
                # ("02-30-2026 10:00:00 AM").
                # AM/PM timezone-suffixed numeric hyphen
                # datetime: "03-15-2026 10:30:00 AM Z" or
                # "03-15-2026T09:00:00 PM -04:00", the way
                # exports write zoned 12-hour hyphen
                # timestamps — the suffix trailing the marker
                # (a "Z", or a well-formed numeric offset) is
                # dropped first so the marker strips normally
                # below; the suffix-before-marker order
                # ("03-15-2026 10:30:00Z AM") governs too, via
                # the suffix strip after the marker strip
                # further down. A malformed suffix
                # ("10:30:00 AM +99:99") is not stripped, so
                # the marker does not strip either and the
                # gates quarantine it normally, as does an
                # impossible date carrying a valid suffix
                # ("02-30-2026 10:00:00 AM Z").
                hyphen_date = re.sub(
                    r"((?:AM|PM))\s+(Z|[+-](?:0\d|1[0-4]):?[0-5]\d)$",
                    r"\1", hyphen_date, flags=re.IGNORECASE)
                hyphen_date = re.sub(
                    r"\s*(?:AM|PM)$", "", hyphen_date,
                    flags=re.IGNORECASE).rstrip()
                if hyphen_date.endswith("Z"):
                    hyphen_date = hyphen_date[:-1]
                else:
                    suffix = re.search(
                        r"([+-](?:0\d|1[0-4]):?[0-5]\d)$",
                        hyphen_date)
                    if suffix is not None:
                        hyphen_date = hyphen_date[:-len(
                            suffix.group(1))]
                # A space-separated suffix ("03-15-2026 10:30:00
                # +05:00") leaves a trailing space behind after
                # the strip above, which strptime rejects, so the
                # space goes with the suffix.
                hyphen_date = hyphen_date.rstrip()
                for fmt in ("%m-%d-%Y %H:%M:%S.%f",
                            "%m-%d-%YT%H:%M:%S.%f",
                            "%d-%m-%Y %H:%M:%S.%f",
                            "%d-%m-%YT%H:%M:%S.%f",
                            "%m-%d-%Y %H:%M:%S", "%m-%d-%Y %H:%M",
                            "%m-%d-%YT%H:%M:%S", "%m-%d-%YT%H:%M",
                            "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M",
                            "%d-%m-%YT%H:%M:%S", "%d-%m-%YT%H:%M",
                            "%m-%d-%Y", "%d-%m-%Y",
                            "%m-%d-%y %H:%M:%S.%f",
                            "%m-%d-%yT%H:%M:%S.%f",
                            "%d-%m-%y %H:%M:%S.%f",
                            "%d-%m-%yT%H:%M:%S.%f",
                            "%m-%d-%y %H:%M:%S", "%m-%d-%y %H:%M",
                            "%m-%d-%yT%H:%M:%S", "%m-%d-%yT%H:%M",
                            "%d-%m-%y %H:%M:%S", "%d-%m-%y %H:%M",
                            "%d-%m-%yT%H:%M:%S", "%d-%m-%yT%H:%M",
                            "%m-%d-%y", "%d-%m-%y"):
                    try:
                        cleaned["service_date"] = datetime.strptime(
                            hyphen_date, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
            elif isinstance(date, str) and (
                    (date.isdigit() and len(date) == 8)
                    or re.fullmatch(
                        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                        r"Thu|Fri|Sat|Sun)[,\s]+\d{8}", date,
                        flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{8}[ T]\d{2}:\d{2}(?::\d{2})?"
                        r"(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|GMT|"
                        r"UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT))",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{8}[ T]\d{2}:\d{2}:\d{2}\.\d+"
                        r"(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|GMT|"
                        r"UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT))?",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{8}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{8}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)\s+"
                        r"(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|GMT|UTC|"
                        r"EST|EDT|CST|CDT|MST|MDT|PST|PDT)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{8}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d|"
                        r"UT|GMT|UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT))"
                        r"\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)):
                # Compact form: YYYYMMDD (basic ISO 8601, the way
                # some EHR and API exports write dates), or the
                # weekday-prefixed compact form ("Sunday,
                # 20260315" or "Mon, 20260316", the way
                # email-style timestamps write dates) — the
                # weekday label is dropped (it is not validated
                # against the date) and the remainder parses as
                # a compact date. A timezone-suffixed compact
                # datetime ("20260315 10:30:00Z",
                # "20260315T09:00:00-04:00", or a weekday-prefixed
                # "Sunday, 20260316 10:30:00+05:30", the way API
                # and EHR exports write compact datetimes with a
                # zone) has its suffix stripped (a trailing "Z",
                # or a well-formed numeric offset, hours 00-14,
                # minutes 00-59, colon optional) and normalizes
                # to its date part the same way; the offset
                # itself is not converted. A space-separated
                # suffix ("20260315 10:30:00 +05:00" or
                # "20260315 10:30:00 Z", the way API and EHR
                # exports write zoned compact timestamps with a
                # space before the zone) strips the same way,
                # and the separating space goes with it —
                # stripping the suffix alone leaves a trailing
                # space that strptime rejects, so the
                # space-separated form quarantined until now
                # while the attached form governed (verified by
                # probe before the fix; the same latent issue
                # in the two-digit-year compact family was
                # closed by a later run, as were the
                # underscore and numeric-hyphen families). A named
                # RFC 2822 zone on a compact datetime ("20260315
                # 10:30:00 GMT", "20260315T09:00:00 EST", or a
                # weekday-prefixed "Sunday, 20260315 10:30:00 GMT",
                # the way email headers write zoned compact
                # timestamps) has the zone stripped the same way
                # and normalizes to its date part; only the RFC
                # 2822 obsolete-zone list plus UTC is accepted
                # (UT, GMT, UTC, EST, EDT, CST, CDT, MST, MDT,
                # PST, PDT), so an unknown zone ("20260315
                # 10:30:00 XYZ") is left in place and the gates
                # quarantine it normally, as does an impossible
                # date carrying a valid zone ("20260230 10:00:00
                # GMT"). The same holds for a named zone trailing
                # the AM/PM marker ("20260315 10:30:00 AM GMT")
                # and for the suffix-before-marker order
                # ("20260315 10:30:00 GMT AM"), which governs via
                # the suffix strip after the marker strip. A fractional-second
                # compact datetime ("20260315 10:30:00.123Z",
                # "20260315T09:00:00.5-04:00", or a
                # weekday-prefixed "Sunday, 20260316
                # 10:30:00.123456+05:30", the way high-resolution
                # API and EHR exports write compact datetimes)
                # normalizes the same way — the fractional
                # seconds are dropped with the time part — as
                # does a plain fractional-second compact
                # datetime without a suffix ("20260315
                # 10:30:00.999"). An impossible compact
                # date fails parsing and is left untouched so the
                # gates quarantine it normally, as does a bogus
                # weekday label ("Funday, 20260315"), which the
                # pattern does not strip, and a malformed suffix
                # ("20260315 10:30:00+99:99"), which the guard
                # does not match, so the value falls through to
                # the generic datetime branch and quarantines.
                compact_date = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", date,
                    flags=re.IGNORECASE)
                # AM/PM timezone-suffixed compact datetime:
                # "20260315 10:30:00 AM Z" or
                # "20260315T09:00:00 PM -04:00", the way
                # exports write zoned 12-hour compact timestamps
                # — the suffix trailing the marker (a "Z", a
                # well-formed numeric offset, or a named RFC 2822
                # zone such as "20260315 10:30:00 AM GMT") is
                # dropped first
                # so the marker strips normally below; the
                # suffix-before-marker order ("20260315
                # 10:30:00Z AM") governs too, via the suffix
                # strip after the marker strip further down. A
                # malformed suffix ("10:30:00 AM +99:99") or an
                # unknown zone ("10:30:00 AM XYZ") is not
                # stripped, so the marker does not strip either
                # and the gates quarantine it normally, as does
                # an impossible date carrying a valid suffix
                # ("20260230 10:00:00 AM Z").
                compact_date = re.sub(
                    r"((?:AM|PM))\s+(Z|[+-](?:0\d|1[0-4]):?[0-5]\d|UT|"
                    r"GMT|UTC|EST|EDT|CST|CDT|MST|MDT|PST|PDT)$",
                    r"\1", compact_date, flags=re.IGNORECASE)
                # AM/PM compact datetime: "20260315 10:30:00 AM"
                # or "20260315 10:30:00.123 AM", the way
                # exports write compact datetimes on a 12-hour
                # clock — the marker (spaced or attached,
                # either case) is dropped and the remainder
                # parses as a compact datetime; only the date
                # part governs, so the hour itself needs no
                # conversion. A malformed marker
                # ("10:30:00 XM") is not stripped, so parsing
                # fails and the gates quarantine it normally,
                # as does an impossible AM/PM datetime
                # ("20260230 10:00:00 AM").
                compact_date = re.sub(
                    r"\s*(?:AM|PM)$", "", compact_date,
                    flags=re.IGNORECASE).rstrip()
                if compact_date.endswith("Z"):
                    compact_date = compact_date[:-1]
                else:
                    suffix = re.search(
                        r"([+-](?:0\d|1[0-4]):?[0-5]\d)$",
                        compact_date)
                    if suffix is not None:
                        compact_date = compact_date[:-len(
                            suffix.group(1))]
                    else:
                        named = re.search(
                            r"\s+(?:UT|GMT|UTC|EST|EDT|CST|"
                            r"CDT|MST|MDT|PST|PDT)$",
                            compact_date,
                            flags=re.IGNORECASE)
                        if named is not None:
                            compact_date = compact_date[:-len(
                                named.group(0))]
                # A space-separated suffix ("20260315 10:30:00
                # +05:00") leaves a trailing space behind after
                # the strip above, which strptime rejects, so the
                # space goes with the suffix.
                compact_date = compact_date.rstrip()
                try:
                    cleaned["service_date"] = datetime.strptime(
                        compact_date, "%Y%m%d").strftime("%Y-%m-%d")
                except ValueError:
                    for fmt in ("%Y%m%d %H:%M:%S.%f",
                                "%Y%m%dT%H:%M:%S.%f",
                                "%Y%m%d %H:%M:%S", "%Y%m%d %H:%M",
                                "%Y%m%dT%H:%M:%S", "%Y%m%dT%H:%M"):
                        try:
                            cleaned["service_date"] = datetime.strptime(
                                compact_date, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
            elif isinstance(date, str) and (
                    (date.isdigit() and len(date) == 6)
                    or re.fullmatch(
                        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                        r"Thu|Fri|Sat|Sun)[,\s]+\d{6}", date,
                        flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{6}[ T]\d{2}:\d{2}(?::\d{2})?"
                        r"(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d))",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{6}[ T]\d{2}:\d{2}:\d{2}\.\d+"
                        r"(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d))?",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{6}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{6}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?\s*(?:AM|PM)\s+"
                        r"(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"\d{6}[ T]\d{1,2}:\d{2}(?::\d{2})?"
                        r"(?:\.\d+)?(?:\s*(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d))"
                        r"\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)):
                # Two-digit-year compact form: MMDDYY or DDMMYY
                # ("031526" or "150326", the way legacy mainframe
                # exports write dates) — the two-digit year
                # follows Python's %y pivot (00-68 read as
                # 2000-2068, 69-99 as 1969-1999), so "031599"
                # governs as 1999-03-15; the same US-first order
                # holds, and a leading component above 12 reads
                # day-first ("260315" governs as 2015-03-26),
                # so there is no separate year-first two-digit
                # form. Weekday-prefixed, timezone-suffixed,
                # fractional-second, and AM/PM forms normalize
                # the same way as the eight-digit compact forms
                # above. A space-separated suffix ("031526
                # 10:30:00 +05:00" or "031526 10:30:00 Z", the
                # way API and EHR exports write zoned compact
                # timestamps with a space before the zone)
                # strips the same way, and the separating space
                # goes with it — stripping the suffix alone
                # leaves a trailing space that strptime rejects,
                # so the space-separated form quarantined until
                # now while the attached form governed (verified
                # by probe before the fix). This closes the last
                # latent trailing-space gap: the month-name,
                # slash, dot, compact, underscore, and
                # numeric-hyphen families were all closed by
                # earlier runs. An impossible date ("023026") or
                # a malformed suffix ("031526 10:30:00+99:99")
                # fails parsing and is left untouched so the
                # gates quarantine it normally.
                short_compact_date = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", date,
                    flags=re.IGNORECASE)
                # AM/PM timezone-suffixed compact datetime:
                # "031526 10:30:00 AM Z" or
                # "031526T09:00:00 PM -04:00" — the suffix
                # trailing the marker is dropped first so the
                # marker strips normally below; the
                # suffix-before-marker order ("031526
                # 10:30:00Z AM") governs too, via the suffix
                # strip after the marker strip further down. A
                # malformed suffix ("10:30:00 AM +99:99") is not
                # stripped, so the marker does not strip either
                # and the gates quarantine it normally, as does
                # an impossible date carrying a valid suffix
                # ("023026 10:00:00 AM Z").
                short_compact_date = re.sub(
                    r"((?:AM|PM))\s+(Z|[+-](?:0\d|1[0-4]):?[0-5]\d)$",
                    r"\1", short_compact_date, flags=re.IGNORECASE)
                # AM/PM compact datetime: "031526 10:30:00 AM"
                # or "031526 10:30:00.123 AM" — the marker
                # (spaced or attached, either case) is dropped
                # and the remainder parses as a compact
                # datetime; only the date part governs. A
                # malformed marker ("10:30:00 XM") is not
                # stripped, so parsing fails and the gates
                # quarantine it normally, as does an impossible
                # AM/PM datetime ("023026 10:00:00 AM").
                short_compact_date = re.sub(
                    r"\s*(?:AM|PM)$", "", short_compact_date,
                    flags=re.IGNORECASE).rstrip()
                if short_compact_date.endswith("Z"):
                    short_compact_date = short_compact_date[:-1]
                else:
                    suffix = re.search(
                        r"([+-](?:0\d|1[0-4]):?[0-5]\d)$",
                        short_compact_date)
                    if suffix is not None:
                        short_compact_date = short_compact_date[:-len(
                            suffix.group(1))]
                # A space-separated suffix ("031526 10:30:00
                # +05:00") leaves a trailing space behind after
                # the strip above, which strptime rejects, so the
                # space goes with the suffix.
                short_compact_date = short_compact_date.rstrip()
                for fmt in ("%m%d%y", "%d%m%y"):
                    try:
                        cleaned["service_date"] = datetime.strptime(
                            short_compact_date, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
                else:
                    for fmt in ("%m%d%y %H:%M:%S.%f",
                                "%m%d%yT%H:%M:%S.%f",
                                "%d%m%y %H:%M:%S.%f",
                                "%d%m%yT%H:%M:%S.%f",
                                "%m%d%y %H:%M:%S", "%m%d%y %H:%M",
                                "%m%d%yT%H:%M:%S", "%m%d%yT%H:%M",
                                "%d%m%y %H:%M:%S", "%d%m%y %H:%M",
                                "%d%m%yT%H:%M:%S", "%d%m%yT%H:%M"):
                        try:
                            cleaned["service_date"] = datetime.strptime(
                                short_compact_date, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
            elif isinstance(date, str) and (
                    (date.isdigit() and len(date) == 7)
                    or re.fullmatch(r"\d{4}-\d{3}", date)
                    or re.fullmatch(
                        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                        r"Thu|Fri|Sat|Sun)[,\s]+(?:\d{7}|\d{4}-\d{3})",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"(?:\d{7}|\d{4}-\d{3})[ T]\d{2}:\d{2}"
                        r"(?::\d{2})?"
                        r" ?(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"(?:\d{7}|\d{4}-\d{3})[ T]\d{2}:\d{2}:\d{2}\.\d+"
                        r"(?: ?(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d))?",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"(?:\d{7}|\d{4}-\d{3})[ T]\d{1,2}:\d{2}"
                        r"(?::\d{2})?(?:\.\d+)?\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"(?:\d{7}|\d{4}-\d{3})[ T]\d{1,2}:\d{2}"
                        r"(?::\d{2})?(?:\.\d+)?\s*(?:AM|PM)\s+"
                        r"(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d)",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"(?:\d{7}|\d{4}-\d{3})[ T]\d{1,2}:\d{2}"
                        r"(?::\d{2})?(?:\.\d+)?"
                        r" ?(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d)"
                        r"\s*(?:AM|PM)",
                        date, flags=re.IGNORECASE)):
                # Ordinal (Julian) form: YYYYDDD ("2026074") or the
                # ISO 8601 ordinal form ("2026-074"), the way
                # mainframe exports write dates — the day of the
                # year converts to its calendar date and governs
                # instead of quarantining as unparseable_date. A
                # weekday-prefixed ordinal date ("Sunday, 2026075"
                # or "Mon, 2026-074", the way email-style
                # timestamps write dates) has its weekday label
                # dropped (it is not validated against the date)
                # and the remainder parses as an ordinal date. A
                # timezone-suffixed ordinal datetime ("2026074
                # 10:30:00Z", "2026-074T09:00:00-04:00", or a
                # weekday-prefixed "Sunday, 2026075
                # 10:30:00+05:30", the way API and EHR exports
                # write ordinal datetimes with a zone) has its
                # suffix stripped (a trailing "Z", or a
                # well-formed numeric offset, hours 00-14,
                # minutes 00-59, colon optional) and normalizes
                # to its date part the same way; the offset
                # itself is not converted. A space-separated
                # suffix ("2026074 10:30:00 +05:00" or
                # "2026-074 10:30:00 Z", the way API and EHR
                # exports write zoned ordinal timestamps with a
                # space before the zone) strips the same way,
                # and the separating space goes with it —
                # stripping the suffix alone leaves a trailing
                # space that strptime rejects, so the
                # space-separated form quarantined until now
                # while the attached form governed. A
                # fractional-second
                # ordinal datetime ("2026074 10:30:00.123Z", the
                # way high-resolution exports write ordinal
                # datetimes) normalizes the same way — the
                # fractional seconds are dropped with the time
                # part. An AM/PM ordinal datetime ("2026074
                # 10:30:00 AM", the way exports write ordinal
                # datetimes on a 12-hour clock) has its marker
                # dropped on read and normalizes to its date
                # part the same way, with the same marker
                # handling for weekday-prefixed ("Sunday,
                # 2026075 09:00:00 pm") and attached-marker
                # ("2026074 2:30pm") forms, since the marker is
                # stripped as a candidate before the ordinal
                # datetime formats run; while an impossible
                # AM/PM ordinal datetime ("2026366 10:00:00 AM")
                # or a malformed marker ("2026074 10:30:00 XM")
                # is left untouched so the gates quarantine it
                # normally. An AM/PM timezone-suffixed ordinal
                # datetime ("2026074 10:30:00 AM Z",
                # "2026-074T09:00:00 PM -04:00", or a
                # weekday-prefixed "Sunday, 2026075 10:30:00 am
                # +05:30") has the suffix trailing the marker
                # dropped first so the marker strips normally,
                # and the suffix-before-marker order ("2026074
                # 10:30:00Z AM") governs too; while an
                # impossible AM/PM timezone-suffixed ordinal
                # datetime ("2026366 10:00:00 AM Z") or a
                # malformed suffix ("2026074 10:30:00 AM
                # +99:99") is left untouched so the gates
                # quarantine it normally. A day-of-year that is
                # not a real day of that year ("2026366" in
                # 2026, which has 365 days, or "2026000") is
                # left untouched so the gates quarantine it
                # normally: strptime's %j rolls a too-large day
                # into the next year instead of failing, so the
                # parsed year is checked against the written
                # year and a mismatch rejects the value. A bogus
                # weekday label ("Funday, 2026074") is not
                # stripped by the pattern, so the value falls
                # through to the generic datetime branch and
                # quarantines, as does a malformed suffix
                # ("2026074 10:30:00+99:99"), which the guard
                # does not match.
                ordinal_date = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", date,
                    flags=re.IGNORECASE)
                # AM/PM timezone-suffixed ordinal datetime:
                # "2026074 10:30:00 AM Z" or
                # "2026-074T09:00:00 PM -04:00", the way
                # exports write zoned 12-hour ordinal
                # timestamps — the suffix trailing the marker
                # (a "Z", or a well-formed numeric offset) is
                # dropped first so the marker strips normally
                # below; the suffix-before-marker order
                # ("2026074 10:30:00Z AM") governs too, via the
                # suffix strip after the marker strip further
                # down. A malformed suffix ("10:30:00 AM
                # +99:99") is not stripped, so the marker does
                # not strip either and the gates quarantine it
                # normally, as does an impossible date carrying
                # a valid suffix ("2026366 10:00:00 AM Z").
                ordinal_date = re.sub(
                    r"((?:AM|PM))\s+(Z|[+-](?:0\d|1[0-4]):?[0-5]\d)$",
                    r"\1", ordinal_date, flags=re.IGNORECASE)
                # AM/PM ordinal datetime: "2026074 10:30:00 AM"
                # or "2026074 10:30:00.123 AM", the way exports
                # write ordinal datetimes on a 12-hour clock —
                # the marker (spaced or attached, either case)
                # is dropped and the remainder parses as an
                # ordinal datetime; only the date part governs,
                # so the hour itself needs no conversion. A
                # malformed marker ("10:30:00 XM") is not
                # stripped, so parsing fails and the gates
                # quarantine it normally, as does an impossible
                # AM/PM datetime ("2026366 10:00:00 AM").
                ordinal_date = re.sub(
                    r"\s*(?:AM|PM)$", "", ordinal_date,
                    flags=re.IGNORECASE).rstrip()
                if ordinal_date.endswith("Z"):
                    ordinal_date = ordinal_date[:-1]
                else:
                    suffix = re.search(
                        r"([+-](?:0\d|1[0-4]):?[0-5]\d)$",
                        ordinal_date)
                    if suffix is not None:
                        ordinal_date = ordinal_date[:-len(
                            suffix.group(1))]
                # A space-separated suffix ("2026074 10:30:00
                # +05:00") leaves a trailing space behind after
                # the strip above, which strptime rejects, so the
                # space goes with the suffix.
                ordinal_date = ordinal_date.rstrip()
                ordinal_year = int(ordinal_date[:4])
                parsed = None
                for fmt in ("%Y%j", "%Y-%j"):
                    try:
                        candidate_parsed = datetime.strptime(
                            ordinal_date, fmt)
                        if candidate_parsed.year == ordinal_year:
                            parsed = candidate_parsed
                        break
                    except ValueError:
                        continue
                if parsed is None:
                    for fmt in ("%Y%j %H:%M:%S.%f",
                                "%Y%jT%H:%M:%S.%f",
                                "%Y-%j %H:%M:%S.%f",
                                "%Y-%jT%H:%M:%S.%f",
                                "%Y%j %H:%M:%S", "%Y%j %H:%M",
                                "%Y%jT%H:%M:%S", "%Y%jT%H:%M",
                                "%Y-%j %H:%M:%S", "%Y-%j %H:%M",
                                "%Y-%jT%H:%M:%S", "%Y-%jT%H:%M"):
                        try:
                            candidate_parsed = datetime.strptime(
                                ordinal_date, fmt)
                            if candidate_parsed.year == ordinal_year:
                                parsed = candidate_parsed
                            break
                        except ValueError:
                            continue
                if parsed is not None:
                    cleaned["service_date"] = parsed.strftime("%Y-%m-%d")
            elif isinstance(date, str) and (
                    re.fullmatch(r"\d{4}-W\d{2}-[1-7]", date)
                    or re.fullmatch(r"\d{4}W\d{2}[1-7]", date)
                    or re.fullmatch(r"\d{4}-W\d{2}", date)
                    or re.fullmatch(
                        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                        r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                        r"Thu|Fri|Sat|Sun)[,\s]+(?:\d{4}-W\d{2}-[1-7]|"
                        r"\d{4}W\d{2}[1-7]|\d{4}-W\d{2})",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"(?:\d{4}-W\d{2}-[1-7]|\d{4}W\d{2}[1-7])"
                        r"[ T]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?",
                        date, flags=re.IGNORECASE)
                    or re.fullmatch(
                        r"(?:(?:Monday|Tuesday|Wednesday|Thursday|"
                        r"Friday|Saturday|Sunday|Mon|Tues|Tue|Wed|"
                        r"Thurs|Thur|Thu|Fri|Sat|Sun)[,\s]+)?"
                        r"(?:\d{4}-W\d{2}-[1-7]|\d{4}W\d{2}[1-7])"
                        r"[ T]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?"
                        r" ?(?:Z|[+-](?:0\d|1[0-4]):?[0-5]\d)",
                        date, flags=re.IGNORECASE)):
                # ISO week dates: "2026-W11-1" (the ISO 8601
                # week-date form), "2026W111" (the compact form),
                # or "2026-W11" (the week alone, its Monday), the
                # way scheduling exports write dates — the ISO week
                # and weekday convert to their calendar date and
                # govern instead of quarantining as
                # unparseable_date. A weekday-prefixed week date
                # ("Sunday, 2026-W11-2", the way email-style
                # timestamps write dates) has its weekday label
                # dropped (it is not validated against the date)
                # and the remainder parses as a week date. A
                # week-date datetime ("2026-W11-1 10:30:00Z", or a
                # fractional-second "2026-W11-1T09:00:00.123-04:00",
                # the way API and EHR exports write week-date
                # datetimes with a zone) has its suffix stripped
                # and normalizes to its date part the same way; the
                # offset itself is not converted. A space-separated
                # suffix ("2026-W11-1 10:30:00 +05:00" or
                # "2026-W11-1 10:30:00 Z", the way API and EHR
                # exports write zoned week-date timestamps with a
                # space before the zone) strips the same way, and
                # the separating space goes with it — stripping the
                # suffix alone leaves a trailing space that
                # strptime rejects, so the space-separated form
                # quarantined until now while the attached form
                # governed. A week that does not exist in that year
                # ("2025-W53-1", a 52-week year) or a weekday
                # outside 1-7 ("2026-W11-8") is
                # left untouched so the gates quarantine it
                # normally, as is a weekday-prefixed week date with
                # a bogus label ("Funday, 2026-W11-1") or a
                # malformed suffix ("2026-W11-1 10:30:00+99:99"),
                # which the guard does not match. strptime's
                # %G-W%V-%u raises on a week that does not exist,
                # and the parsed ISO year and week are checked
                # against the written ones; the week-only form has
                # no weekday for strptime to take, so it parses via
                # fromisocalendar instead.
                week_date = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", date,
                    flags=re.IGNORECASE)
                if week_date.endswith("Z"):
                    week_date = week_date[:-1]
                else:
                    suffix = re.search(
                        r"([+-](?:0\d|1[0-4]):?[0-5]\d)$",
                        week_date)
                    if suffix is not None:
                        week_date = week_date[:-len(suffix.group(1))]
                week_date = week_date.rstrip()
                iso_year = int(week_date[:4])
                iso_week = (int(week_date[6:8])
                            if week_date[4] == "-"
                            else int(week_date[5:7]))
                parsed = None
                if re.fullmatch(r"\d{4}-W\d{2}", week_date):
                    try:
                        parsed = datetime.fromisocalendar(
                            iso_year, iso_week, 1)
                    except ValueError:
                        parsed = None
                if parsed is None:
                    for fmt in ("%G-W%V-%u", "%GW%V%u",
                                "%G-W%V-%u %H:%M:%S.%f",
                                "%G-W%V-%uT%H:%M:%S.%f",
                                "%GW%V%u %H:%M:%S.%f",
                                "%GW%V%uT%H:%M:%S.%f",
                                "%G-W%V-%u %H:%M:%S",
                                "%G-W%V-%u %H:%M",
                                "%G-W%V-%uT%H:%M:%S",
                                "%G-W%V-%uT%H:%M",
                                "%GW%V%u %H:%M:%S",
                                "%GW%V%u %H:%M",
                                "%GW%V%uT%H:%M:%S",
                                "%GW%V%uT%H:%M"):
                        try:
                            candidate_parsed = datetime.strptime(
                                week_date, fmt)
                            iso = candidate_parsed.isocalendar()
                            if iso[0] == iso_year and iso[1] == iso_week:
                                parsed = candidate_parsed
                            break
                        except ValueError:
                            continue
                if parsed is not None:
                    cleaned["service_date"] = parsed.strftime("%Y-%m-%d")
            elif isinstance(date, str) and date.isdigit() and (
                    len(date) in (9, 10, 12, 13, 15, 16, 18, 19)):
                # Unix epoch timestamps: a bare nine- or
                # ten-digit count of seconds since 1970-01-01 UTC
                # ("1710460800"), a twelve- or thirteen-digit
                # count of milliseconds ("1710460800000"), a
                # fifteen- or sixteen-digit count of microseconds
                # ("1710460800000000"), or an eighteen- or
                # nineteen-digit count of nanoseconds
                # ("1710460800000000000"), the way API and database
                # exports write timestamps — converts to its UTC
                # date (YYYY-MM-DD) and governs instead of
                # quarantining as unparseable_date. Only epochs
                # whose UTC date falls in 2000-01-01..2100-01-01
                # are accepted, so an epoch outside that window
                # ("9999999999999999999" reads as 2286,
                # "0000000000000000000" as 1970) is left untouched
                # so the gates quarantine it normally, as is a
                # bare number of any other length ("12345"), which
                # no branch claims. An eleven-digit bare number is
                # ambiguous — seconds past 2100 or milliseconds
                # before 2001 — so it is left untouched too, as is
                # a fourteen-digit bare number, which can only be
                # microseconds before 2000, and a seventeen-digit
                # bare number, which can only be nanoseconds
                # before 2000. A non-midnight epoch
                # still governs as its UTC date part; the time of
                # day needs no conversion.
                seconds = int(date)
                if len(date) in (12, 13):
                    seconds //= 1000
                elif len(date) in (15, 16):
                    seconds //= 1000000
                elif len(date) in (18, 19):
                    seconds //= 1000000000
                if 946684800 <= seconds <= 4102444800:
                    cleaned["service_date"] = datetime.fromtimestamp(
                        seconds, tz=timezone.utc).strftime("%Y-%m-%d")
            elif isinstance(date, str) and (" " in date or "T" in date):
                candidate = date
                # Weekday-prefixed ISO form: "Sunday, 2026-03-15"
                # or "Mon, 2026-03-16 10:30:00", the way
                # email-style timestamps write dates — the
                # weekday label is dropped (it is not validated
                # against the date) and the remainder parses as
                # an ISO date or datetime. A bogus weekday label
                # ("Funday, 2026-03-15") is not stripped, so
                # parsing fails and the gates quarantine it
                # normally, as does an impossible weekday-
                # prefixed date ("Monday, 2026-02-30"). This
                # branch is only reached by values no earlier
                # branch claimed, so weekday-prefixed month-name
                # dates still take the month-name branch above.
                weekday_stripped = re.sub(
                    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
                    r"Saturday|Sunday|Mon|Tues|Tue|Wed|Thurs|Thur|"
                    r"Thu|Fri|Sat|Sun)[,\s]+", "", candidate,
                    flags=re.IGNORECASE)
                if weekday_stripped != candidate:
                    candidate = weekday_stripped
                # A timezone suffix trailing the AM/PM marker:
                # "2026-03-15 10:30:00 AM Z" or
                # "2026-03-15T09:00:00 PM -04:00", the way
                # exports write a zoned 12-hour timestamp — the
                # suffix is dropped first so the marker below
                # is at the end again and strips normally; a
                # named RFC 2822 zone ("2026-03-15 10:30:00
                # AM GMT", the way email headers write zoned
                # 12-hour timestamps) strips the same way, as
                # does a plain named-zone suffix with no marker
                # ("2026-03-15 10:30:00 GMT") — the step runs
                # before the marker strip either way. Only the
                # RFC 2822 obsolete-zone list plus UTC is
                # accepted — UT, GMT, UTC, EST, EDT, CST, CDT,
                # MST, MDT, PST, PDT — so an unknown zone
                # ("AM XYZ") is left in place and the gates
                # quarantine it normally; a malformed suffix
                # ("AM +99:99") is not a well-formed
                # designator or offset, so it stays and
                # parsing fails and the gates quarantine
                # the value normally.
                if candidate.endswith("Z"):
                    candidate = candidate[:-1].rstrip()
                else:
                    _ampm_suffix = re.search(
                        r"([+-](?:0\d|1[0-4]):?[0-5]\d)$", candidate)
                    if _ampm_suffix is not None:
                        candidate = candidate[
                            :-len(_ampm_suffix.group(1))].rstrip()
                    else:
                        _ampm_named = re.search(
                            r"\s+(?:UT|GMT|UTC|EST|EDT|CST|CDT|"
                            r"MST|MDT|PST|PDT)$", candidate,
                            flags=re.IGNORECASE)
                        if _ampm_named is not None:
                            candidate = candidate[
                                :-len(_ampm_named.group(0))].rstrip()
                # AM/PM ISO datetime: "2026-03-15 10:30:00 AM" or
                # "2026-03-15T09:00:00 PM", the way exports write
                # ISO datetimes on a 12-hour clock — the marker
                # (spaced or attached, either case) is dropped
                # and the remainder parses as an ISO datetime;
                # only the date part governs, so the hour itself
                # needs no conversion. A malformed marker
                # ("10:30:00 XM") is not stripped, so parsing
                # fails and the gates quarantine it normally, as
                # does an impossible AM/PM datetime
                # ("2026-02-30 10:00:00 AM").
                candidate = re.sub(
                    r"\s*(?:AM|PM)$", "", candidate,
                    flags=re.IGNORECASE).rstrip()
                # Strip a timezone suffix before parsing: a trailing
                # "Z", or a well-formed numeric offset (hours 00-14,
                # minutes 00-59, colon optional). A named RFC 2822
                # zone ("2026-03-15 10:30:00 GMT", the way email
                # headers write zoned ISO timestamps) strips the
                # same way — this step is what catches the
                # suffix-before-marker order ("2026-03-15
                # 10:30:00 GMT AM"), where the marker strip above
                # runs first and leaves the zone at the end. Only
                # the RFC 2822 obsolete-zone list plus UTC is
                # accepted, so an unknown zone ("2026-03-15
                # 10:30:00 XYZ") is left in place so parsing
                # fails and the gates quarantine the value
                # normally. Anything else is left in place so
                # parsing fails and the gates quarantine the
                # value normally.
                if candidate.endswith("Z"):
                    candidate = candidate[:-1]
                else:
                    suffix = re.search(
                        r"([+-](?:0\d|1[0-4]):?[0-5]\d)$", candidate)
                    if suffix is not None:
                        candidate = candidate[:-len(suffix.group(1))]
                    else:
                        named = re.search(
                            r"\s+(?:UT|GMT|UTC|EST|EDT|CST|CDT|"
                            r"MST|MDT|PST|PDT)$", candidate,
                            flags=re.IGNORECASE)
                        if named is not None:
                            candidate = candidate[
                                :-len(named.group(0))].rstrip()
                parsed = None
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
                            "%Y-%m-%d %H:%M:%S.%f",
                            "%Y-%m-%dT%H:%M:%S.%f",
                            "%Y-%m-%d"):
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
