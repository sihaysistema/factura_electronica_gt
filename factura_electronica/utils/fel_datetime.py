# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""
FEL emission datetime helpers.

SAT / INFILE require FechaHoraEmision as ISO-8601 with a numeric timezone
offset. Naive local strings are treated as UTC and break same-day firma
emisor renewals (FEL-GUI-88 / 3.7.6).
"""

from __future__ import unicode_literals

import datetime
import re

import frappe
from frappe.utils import now_datetime

# Configuracion Factura Electronica options (must match DocType Select)
MODE_PETICION = "Fecha y tiempo de peticion a INFILE"
MODE_CREACION = "Fecha y tiempo creacion documento"

# ISO with offset, no microseconds, no trailing Z
# Accept +HH:MM / -HH:MM (preferred) and compact +HHMM (legacy formatters)
_OFFSET_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|[+-]\d{4})$"
)


def get_system_tz_name():
    """
    System timezone name for the site.

    Frappe v13 exposes get_time_zone(); newer versions also have
    get_system_timezone(). Prefer the v13 API first (Fogliasana is v13).
    """
    try:
        from frappe.utils import get_time_zone

        return get_time_zone()
    except Exception:
        pass
    try:
        from frappe.utils import get_system_timezone

        return get_system_timezone()
    except Exception:
        pass
    try:
        return frappe.db.get_system_setting("time_zone") or "America/Guatemala"
    except Exception:
        return "America/Guatemala"


def get_tzinfo(tz_name=None):
    """
    Return a tzinfo for the ERPNext system timezone (or the given name).

    Order tuned for Frappe v13 / Python 3.6 (pytz first), then zoneinfo (3.9+),
    then fixed -06:00 for America/Guatemala as last resort.
    """
    if not tz_name:
        tz_name = get_system_tz_name()

    # Frappe v13 / Python 3.6 sites ship pytz
    try:
        import pytz

        return pytz.timezone(str(tz_name))
    except Exception:
        pass

    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(str(tz_name))
    except Exception:
        pass

    # Last resort: Guatemala has no DST
    if str(tz_name) in ("America/Guatemala", "Guatemala", "CST6"):
        return datetime.timezone(datetime.timedelta(hours=-6))

    # Unknown TZ without zoneinfo/pytz: keep wall time labeled as UTC offset 0
    # (better than raising mid-certify; still prefer fixing deps)
    try:
        frappe.log_error(
            title="FEL datetime: timezone fallback",
            message="Could not resolve tzinfo for {0}; using fixed +00:00".format(tz_name),
        )
    except Exception:
        pass
    return datetime.timezone.utc


def _localize(naive_dt, tzinfo):
    """Attach timezone to a naive datetime representing wall clock in that TZ."""
    if naive_dt.tzinfo is not None:
        return naive_dt.astimezone(tzinfo)

    # pytz
    if hasattr(tzinfo, "localize"):
        return tzinfo.localize(naive_dt)

    return naive_dt.replace(tzinfo=tzinfo)


def _isoformat_with_offset(aware_dt):
    """
    ISO-8601 with numeric offset, no microseconds.

    Avoids isoformat(timespec=...) which is Python 3.7+ only (Fogliasana is 3.6).
    Normalizes compact ±HHMM to ±HH:MM for SAT-friendly strings.
    """
    text = aware_dt.replace(microsecond=0).isoformat()
    if text.endswith("Z"):
        return text[:-1] + "+00:00"
    # Python/pytz usually already yields -06:00; compact form → insert colon
    m = re.search(r"([+-])(\d{2})(\d{2})$", text)
    if m and ":" not in text[-6:]:
        text = text[: m.start()] + "{0}{1}:{2}".format(m.group(1), m.group(2), m.group(3))
    return text


def format_datetime_with_offset(dt, tz_name=None):
    """
    Format a datetime as ISO-8601 with numeric offset, no microseconds.

    Example: 2026-08-07T12:28:41-06:00

    Naive datetimes are interpreted as wall time in the system timezone
    (not as UTC).
    """
    tzinfo = get_tzinfo(tz_name)
    if not isinstance(dt, datetime.datetime):
        dt = datetime.datetime.combine(dt, datetime.time(0, 0, 0))

    aware = _localize(dt.replace(microsecond=0), tzinfo)
    return _isoformat_with_offset(aware)


def combine_posting_datetime(posting_date, posting_time):
    """
    Build a naive datetime from Sales/Purchase Invoice posting_date + posting_time.

    Handles date/datetime/str for date and time/timedelta/str for time
    (as returned by different MariaDB/Frappe versions).
    """
    if posting_date is None:
        raise ValueError("posting_date is required")

    if isinstance(posting_date, datetime.datetime):
        d = posting_date.date()
    elif isinstance(posting_date, datetime.date):
        d = posting_date
    else:
        d = datetime.datetime.strptime(str(posting_date)[:10], "%Y-%m-%d").date()

    if posting_time is None:
        t = datetime.time(0, 0, 0)
    elif isinstance(posting_time, datetime.datetime):
        t = posting_time.time().replace(microsecond=0)
    elif isinstance(posting_time, datetime.time):
        t = posting_time.replace(microsecond=0)
    elif isinstance(posting_time, datetime.timedelta):
        total = int(posting_time.total_seconds())
        # Clamp to one day
        total = total % (24 * 3600)
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        t = datetime.time(hours, minutes, seconds)
    else:
        raw = str(posting_time).strip().split(".")[0]
        # Accept HH:MM:SS or HH:MM
        if len(raw.split(":")) == 2:
            raw = raw + ":00"
        t = datetime.datetime.strptime(raw, "%H:%M:%S").time()

    return datetime.datetime.combine(d, t)


def get_fecha_hora_now(tz_name=None):
    """
    Current system time as FEL ISO string with offset.

    Used for petition-to-INFILE mode and FechaHoraAnulacion.
    """
    # frappe.utils.now_datetime() is wall clock in system TZ (typically naive)
    return format_datetime_with_offset(now_datetime(), tz_name=tz_name)


def get_fecha_hora_emision(
    config_name=None,
    invoice_name=None,
    doctype="Sales Invoice",
    mode=None,
    tz_name=None,
):
    """
    Build FechaHoraEmision for FEL DTE builders.

    Args:
        config_name: Configuracion Factura Electronica name (reads mode if mode is None)
        invoice_name: Sales Invoice / Purchase Invoice name (required for creation mode)
        doctype: Document type for posting fields (default Sales Invoice)
        mode: Optional override — MODE_PETICION or MODE_CREACION
        tz_name: Optional TZ name; defaults to system timezone

    Returns:
        str: e.g. 2026-08-07T12:28:41-06:00
    """
    if mode is None and config_name:
        mode = frappe.db.get_value(
            "Configuracion Factura Electronica",
            {"name": config_name},
            "fecha_y_tiempo_documento_electronica",
        )

    # Default / missing config → petition time (safest for live certify)
    if not mode or mode == MODE_PETICION or not invoice_name:
        return get_fecha_hora_now(tz_name=tz_name)

    # Document creation mode
    posting_date = frappe.db.get_value(doctype, {"name": invoice_name}, "posting_date")
    posting_time = frappe.db.get_value(doctype, {"name": invoice_name}, "posting_time")
    if posting_date is None:
        frappe.throw(
            "No se encontro posting_date para {0} {1}".format(doctype, invoice_name)
        )

    combined = combine_posting_datetime(posting_date, posting_time)
    return format_datetime_with_offset(combined, tz_name=tz_name)


def is_valid_fel_datetime(value):
    """Return True if value looks like FEL emission datetime with offset."""
    if not value or not isinstance(value, str):
        return False
    return bool(_OFFSET_RE.match(value.strip()))
