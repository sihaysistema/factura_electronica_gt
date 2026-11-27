# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt

"""Shared engine for GT Item Sales History and GT Item Sales Analytics.

Source rows
    Submitted Sales Invoices only (``docstatus = 1``) of one company,
    by ``posting_date``. Drafts and cancelled invoices are excluded.
    Credit notes (returns) stay in: ERPNext stores their quantities and
    amounts as negative numbers, so every total is net of returns.

Metrics
    * Units (default): ``SUM(Sales Invoice Item.stock_qty)``, in each
      item's stock UOM. Summing units across different SKUs adds pieces,
      not weight.
    * Amount: ``SUM(base_net_amount)``: company currency, after
      discounts, without IVA. Same basis as GT Sales Item Ranking.
    * Amount with "Include IVA": each line's ``base_net_amount`` scaled by
      its invoice's ``base_grand_total / base_net_total`` (1 when the net
      total is 0). Summed over an invoice this is its grand total, the
      same basis as GT Monthly Sales History.

Periods
    * Weekly: ISO-8601 weeks, Monday to Sunday (MariaDB ``YEARWEEK(d, 3)``).
      The year is the ISO week-year, so week 1 can start in late December
      and the last days of December can belong to week 1 of the next year.
      Some ISO years have 53 weeks (2015, 2020, 2026).
    * Monthly: calendar months. Quarterly: calendar quarters.

Average ("Promedio")
    Mean of the same period in the ``years_to_compare`` years before the
    selected year. A history year in which the company has no submitted
    invoice at all is left out of the divisor (same rule as GT Monthly
    Sales History). Inside a covered year, an item or period with no sales
    is a real 0 and stays in the divisor. Week 53 only averages history
    years that have a week 53; with none, the average is blank.

Same period last year
    Same period index in the previous year (week N, month N, quarter N).
    Week 53 is blank when the previous ISO year has no week 53.

Open period rule
    The business date is the calendar date in America/Guatemala (UTC-6,
    no daylight saving). For the period in progress each comparison pair
    (Difference / % vs Average, and Diff. / % vs last year) stays blank
    until the period-to-date value is strictly greater than that pair's
    comparison; then it shows, so it is always a gain (green). Equal is
    not exceeded. A percent over a comparison that is not positive is
    blank. Periods that have not started are blank. Closed periods show
    gains and losses.

Design note for the crop (cultivo) view
    Rows come back from SQL already grouped by item and period
    (``fetch_period_rows``). ``aggregate`` folds them with a key function,
    so a later crop view can expand each item row into crop rows (BOM in
    effect on the invoice date, crop family on top) without changing the
    period, average or comparison code.
"""

from __future__ import unicode_literals

from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import flt

PRECISION = 2
HISTORY_SPAN = 5

WEEKLY = "Weekly"
MONTHLY = "Monthly"
QUARTERLY = "Quarterly"
PERIOD_TYPES = (WEEKLY, MONTHLY, QUARTERLY)

UNITS = "Units"
AMOUNT = "Amount"
METRICS = (UNITS, AMOUNT)

COMPLETE = "complete"
CURRENT = "current"
FUTURE = "future"

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
)
MONTH_SHORT = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
    "Nov", "Dec",
)

# America/Guatemala never observes daylight-saving time.
GUATEMALA_TZ = timezone(timedelta(hours=-6))

# SQL bucket expressions. Only these fixed strings reach the query.
_BUCKET_SQL = {
    WEEKLY: "YEARWEEK(si.posting_date, 3)",
    MONTHLY: "(YEAR(si.posting_date) * 100 + MONTH(si.posting_date))",
    QUARTERLY: "(YEAR(si.posting_date) * 100 + QUARTER(si.posting_date))",
}

_ITEM_FIELDS = (
    "sii.item_code AS item_code, "
    "MAX(IFNULL(item.item_name, sii.item_name)) AS item_name, "
    "MAX(IFNULL(item.item_group, sii.item_group)) AS item_group"
)
_NO_ITEM_FIELDS = "'' AS item_code, '' AS item_name, '' AS item_group"

_GROSS_SQL = (
    "sii.base_net_amount * (CASE WHEN IFNULL(si.base_net_total, 0) = 0 THEN 1 "
    "ELSE si.base_grand_total / si.base_net_total END)"
)


# --------------------------------------------------------------------------
# Dates and filters
# --------------------------------------------------------------------------

def report_today():
    """Calendar date in America/Guatemala. Tests patch this."""

    return guatemala_today()


def guatemala_today(now=None):
    current = now if now is not None else datetime.now(GUATEMALA_TZ)
    if current.tzinfo is not None:
        current = current.astimezone(GUATEMALA_TZ)
    return current.date()


def default_company():
    return frappe.defaults.get_user_default("Company")


def company_currency(company):
    return frappe.db.get_value("Company", company, "default_currency") or ""


def parse_year(value, today=None):
    if value in (None, ""):
        return (today or report_today()).year
    try:
        year = int(value)
    except (TypeError, ValueError):
        frappe.throw(_("Year must be a whole number"))
    if year < 1900 or year > 9999:
        frappe.throw(_("Year is out of range"))
    return year


def parse_years_to_compare(value):
    if value in (None, ""):
        return HISTORY_SPAN
    try:
        span = int(value)
    except (TypeError, ValueError):
        span = None
    if span not in (2, 3, 4, 5):
        frappe.throw(_("Years to compare must be 5, 4, 3 or 2"))
    return span


def parse_period_type(value):
    if value in (None, ""):
        return MONTHLY
    if value not in PERIOD_TYPES:
        frappe.throw(_("Period type must be Weekly, Monthly or Quarterly"))
    return value


def parse_metric(value):
    if value in (None, ""):
        return UNITS
    if value not in METRICS:
        frappe.throw(_("Metric must be Units or Amount"))
    return value


def parse_check(value):
    if value in (None, "", 0, "0", False):
        return False
    return str(value).lower() not in ("false", "no")


def history_years(selected_year, years_to_compare=HISTORY_SPAN):
    """``years_to_compare`` years before the selected one, oldest first."""

    return [int(selected_year) - offset for offset in range(int(years_to_compare), 0, -1)]


def iso_weeks_in_year(year):
    """52 or 53. December 28 is always in the last ISO week of its year."""

    return date(int(year), 12, 28).isocalendar()[1]


def periods_in_year(period_type, year):
    if period_type == WEEKLY:
        return iso_weeks_in_year(year)
    if period_type == QUARTERLY:
        return 4
    return 12


def period_bounds(period_type, year, index):
    """First and last calendar day of one period."""

    year = int(year)
    index = int(index)
    if period_type == WEEKLY:
        start = iso_week_monday(year, index)
        return start, start + timedelta(days=6)
    if period_type == QUARTERLY:
        first_month = (index - 1) * 3 + 1
        start = date(year, first_month, 1)
        return start, _month_end(year, first_month + 2)
    return date(year, index, 1), _month_end(year, index)


def iso_week_monday(year, week):
    # date.fromisocalendar is Python 3.8+; this works on every version.
    jan4 = date(int(year), 1, 4)
    week1_monday = jan4 - timedelta(days=jan4.isoweekday() - 1)
    return week1_monday + timedelta(weeks=int(week) - 1)


def _month_end(year, month):
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def year_bounds(period_type, year):
    """Date range covered by every period of ``year``."""

    first, _last = period_bounds(period_type, year, 1)
    _first, last = period_bounds(period_type, year, periods_in_year(period_type, year))
    return first, last


def current_period(period_type, today):
    """(year, index) of the period that contains ``today``."""

    if period_type == WEEKLY:
        iso = today.isocalendar()
        return iso[0], iso[1]
    if period_type == QUARTERLY:
        return today.year, (today.month - 1) // 3 + 1
    return today.year, today.month


def period_state(period_type, year, index, today):
    key = (int(year), int(index))
    now = current_period(period_type, today)
    if key < now:
        return COMPLETE
    if key == now:
        return CURRENT
    return FUTURE


def parse_period(value, period_type, year, today):
    """Selected period index. Empty means the current period (or the last
    period of a past year, or 1 for a future year)."""

    count = periods_in_year(period_type, year)
    if value in (None, ""):
        now_year, now_index = current_period(period_type, today)
        if int(year) == now_year:
            return now_index
        return count if int(year) < now_year else 1
    try:
        index = int(value)
    except (TypeError, ValueError):
        index = None
    if index is None or index < 1 or index > count:
        frappe.throw(_("Period must be between 1 and {0} for {1}").format(count, year))
    return index


def period_label(period_type, index, year=None):
    if period_type == WEEKLY:
        text = _("W{0}").format("{0:02d}".format(int(index)))
    elif period_type == QUARTERLY:
        text = _("Q{0}").format(int(index))
    else:
        text = _(MONTH_SHORT[int(index) - 1])
    if year is None:
        return text
    return "{0} {1}".format(text, int(year))


def period_name(period_type, index):
    """Longer label for History rows."""

    if period_type == MONTHLY:
        return _(MONTH_NAMES[int(index) - 1])
    return period_label(period_type, index)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

def item_group_bounds(item_group):
    if not item_group:
        return None
    bounds = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True)
    if not bounds:
        frappe.throw(_("Item Group {0} does not exist").format(item_group))
    return bounds


def item_codes_in_group(item_group):
    """Items whose current Item Group is ``item_group`` or a child of it."""

    bounds = item_group_bounds(item_group)
    rows = frappe.db.sql(
        """
        SELECT item.name AS item_code
        FROM `tabItem` item
        INNER JOIN `tabItem Group` ig ON ig.name = item.item_group
        WHERE ig.lft >= %(lft)s AND ig.rgt <= %(rgt)s
        """,
        {"lft": bounds.get("lft"), "rgt": bounds.get("rgt")},
        as_dict=True,
    )
    return [row["item_code"] for row in rows]


def fetch_period_rows(company, period_type, from_date, to_date, item_code=None,
                      item_group=None, include_iva=False, date_ranges=None, by_item=True):
    """One grouped read: item x period.

    Returns dicts with item_code, item_name, item_group (current Item
    master), year, period and the sums qty and amount. ``amount`` is net
    or with IVA depending on ``include_iva``. ``date_ranges`` (a list of
    (from, to) pairs inside from_date..to_date) narrows the read to those
    spans, so a one-period ranking does not scan whole years.
    ``by_item=False`` groups by period only (one row per period, item_code
    ``""``), which is all GT Item Sales History needs.
    """

    bucket = _BUCKET_SQL[parse_period_type(period_type)]
    amount_sql = _GROSS_SQL if include_iva else "sii.base_net_amount"
    conditions = [
        "si.docstatus = 1",
        "si.company = %(company)s",
        "si.posting_date BETWEEN %(from_date)s AND %(to_date)s",
    ]
    values = {
        "company": company,
        "from_date": str(from_date),
        "to_date": str(to_date),
    }
    if date_ranges:
        spans = []
        for position, (start, end) in enumerate(date_ranges):
            spans.append(
                "si.posting_date BETWEEN %(span_from_{0})s AND %(span_to_{0})s".format(position)
            )
            values["span_from_{0}".format(position)] = str(start)
            values["span_to_{0}".format(position)] = str(end)
        conditions.append("(" + " OR ".join(spans) + ")")
    if item_code:
        conditions.append("sii.item_code = %(item_code)s")
        values["item_code"] = item_code
    if item_group:
        codes = item_codes_in_group(item_group)
        if not codes:
            return []
        # Item codes use the Sales Invoice Item index; a join on Item Group
        # scans every invoice line of the range.
        conditions.append("sii.item_code IN %(item_codes)s")
        values["item_codes"] = tuple(codes)

    rows = frappe.db.sql(
        """
        /* gt-item-sales-analytics */
        SELECT {item_fields},
               {bucket} AS bucket,
               SUM(sii.stock_qty) AS qty,
               SUM({amount}) AS amount
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        LEFT JOIN `tabItem` item ON item.name = sii.item_code
        WHERE {conditions}
        GROUP BY {group_by}
        """.format(
            item_fields=_ITEM_FIELDS if by_item else _NO_ITEM_FIELDS,
            bucket=bucket,
            amount=amount_sql,
            conditions=" AND ".join(conditions),
            group_by="sii.item_code, bucket" if by_item else "bucket",
        ),
        values,
        as_dict=True,
    )
    return [split_bucket(row) for row in rows]


def split_bucket(row):
    out = dict(row)
    bucket = int(out.pop("bucket"))
    out["year"] = bucket // 100
    out["period"] = bucket % 100
    return out


def covered_years(company, period_type, from_date, to_date):
    """Years (ISO years for Weekly) with at least one submitted invoice."""

    bucket = _BUCKET_SQL[parse_period_type(period_type)]
    rows = frappe.db.sql(
        """
        /* gt-item-sales-analytics-coverage */
        SELECT DISTINCT FLOOR({bucket} / 100) AS year
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1
          AND si.company = %(company)s
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        """.format(bucket=bucket),
        {"company": company, "from_date": str(from_date), "to_date": str(to_date)},
        as_dict=True,
    )
    return set(int(row["year"]) for row in rows if row.get("year") is not None)


def row_value(row, metric):
    return row.get("qty") if metric == UNITS else row.get("amount")


def aggregate(rows, metric, key=lambda row: row["item_code"]):
    """{group key: {(year, period): Decimal}} plus {group key: first row}."""

    series = {}
    info = {}
    for row in rows:
        group = key(row)
        if group is None:
            continue
        info.setdefault(group, row)
        cell = (int(row["year"]), int(row["period"]))
        bucket = series.setdefault(group, {})
        bucket[cell] = bucket.get(cell, Decimal("0")) + to_decimal(row_value(row, metric))
    return series, info


def total_series(series):
    out = {}
    for values in series.values():
        for cell, amount in values.items():
            out[cell] = out.get(cell, Decimal("0")) + amount
    return out


# --------------------------------------------------------------------------
# Numbers and comparisons
# --------------------------------------------------------------------------

def to_decimal(value):
    if isinstance(value, Decimal):
        return value
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def round_value(value):
    if value is None:
        return None
    rounded = to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return flt(rounded, PRECISION)


def average_for(series_values, period_type, years, covered, index):
    """Average of one period index over the history years.

    None when no history year qualifies (not covered, or no such week).
    """

    included = [
        year for year in years
        if year in covered and int(index) <= periods_in_year(period_type, year)
    ]
    if not included:
        return None
    total = sum((round_value(series_values.get((year, int(index)), 0)) for year in included), 0.0)
    return round_value(Decimal(str(total)) / Decimal(len(included)))


def last_year_value(series_values, period_type, year, index):
    previous = int(year) - 1
    if int(index) > periods_in_year(period_type, previous):
        return None
    return round_value(series_values.get((previous, int(index)), 0))


def difference(selected, comparison):
    if selected is None or comparison is None:
        return None
    return round_value(to_decimal(selected) - to_decimal(comparison))


def percent(selected, comparison):
    if selected is None or comparison is None:
        return None
    base = to_decimal(comparison)
    if base == 0:
        return None
    ratio = (to_decimal(selected) - base) / base * Decimal("100")
    return round_value(ratio)


def comparison_cells(selected, average, last_year, state):
    """The four comparison cells for one row in one period state."""

    cells = {"diferencia": None, "vs_promedio": None, "dif_vs_prev": None, "pct_vs_prev": None}
    if state == FUTURE or selected is None:
        return cells
    if state == COMPLETE:
        cells["diferencia"] = difference(selected, average)
        cells["vs_promedio"] = percent(selected, average)
        cells["dif_vs_prev"] = difference(selected, last_year)
        cells["pct_vs_prev"] = percent(selected, last_year)
        return cells
    # Open period: blank until strictly exceeded, then a gain.
    if average is not None and to_decimal(selected) > to_decimal(average):
        cells["diferencia"] = difference(selected, average)
        cells["vs_promedio"] = percent(selected, average) if to_decimal(average) > 0 else None
    if last_year is not None and to_decimal(selected) > to_decimal(last_year):
        cells["dif_vs_prev"] = difference(selected, last_year)
        cells["pct_vs_prev"] = percent(selected, last_year) if to_decimal(last_year) > 0 else None
    return cells


def value_column(label, fieldname, metric, width=110):
    column = {"label": label, "fieldname": fieldname, "width": width}
    if metric == AMOUNT:
        column.update({"fieldtype": "Currency", "options": "currency"})
    else:
        column.update({"fieldtype": "Float", "precision": PRECISION})
    return column


def comparison_columns(metric, previous_year):
    return [
        value_column(_("Difference"), "diferencia", metric),
        {"label": _("% vs Average"), "fieldname": "vs_promedio", "fieldtype": "Float",
         "precision": PRECISION, "width": 110},
        value_column(_("Diff. vs {0}").format(previous_year), "dif_vs_prev", metric),
        {"label": _("% vs {0}").format(previous_year), "fieldname": "pct_vs_prev",
         "fieldtype": "Float", "precision": PRECISION, "width": 100},
    ]


def chart_number(value):
    if value is None:
        return 0
    return flt(value, PRECISION)
