# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt

"""Historial mensual de ventas GT.

Each cell is the GT Sales Ledger total for that calendar month. The figures
come from ``sales_invoices_monthly`` (the ledger's Monthly option), so document
inclusion, currency conversion and the amount formula are not reimplemented:

* submitted Sales Invoices only (``docstatus = 1``)
* credit notes are those submitted invoices (returns) and reduce the total
  because ``grand_total`` is negative
* cancelled invoices (``docstatus = 2``) and drafts are excluded
* amount is ``SUM(grand_total * conversion_rate)`` in company currency

The value shown for a month is that sum rounded with ``flt(..., 2)``, which is
what ``gt_sales_ledger.calculate_total`` does to each monthly row.

Promedio
    A history year with no submitted sales invoices is omitted from the
    divisor. Its cells still show 0.00. A month with no invoices inside a
    year that does have invoices counts as 0 and stays in the divisor, because
    the ledger total for that month is zero. If none of the selected years
    have invoices, Promedio is 0.00. "Years to compare" chooses how many
    years before the selected year are shown (5, 4, 3 or 2; default 5).

    After Promedio, one more column shows the selected year itself (label is
    that year, for example 2026). It uses the same monthly ledger total.
    Months with no sales yet are 0.00. That column is on the Total row and
    is not part of Promedio.

    Diferencia is that selected-year amount minus Promedio (negative when
    the month is under the average). "% vs Promedio" is
    (selected - Promedio) / Promedio * 100, blank when Promedio is 0.
    "Dif. vs <year>" and "% vs <year>" compare the same month of the
    previous calendar year (selected year - 1). They do not follow the
    Years to compare filter. The percent is blank when that previous
    month is 0.

    When the selected year is the server's current year
    (``frappe.utils.getdate``), the current month and later months are
    incomplete. The current month still shows Promedio and the
    month-to-date selected-year amount, but its comparison cells are
    blank. Months that have not started are blank in Promedio, in the
    selected-year column, and in every comparison column. Past years
    treat all 12 months as complete.

    On the Total row, Promedio and the selected year sum completed
    months only, so Total Promedio plus Total Diferencia equals the
    selected-year total. The current month still shows Promedio and the
    month-to-date amount on its own row, and that row is left out of
    those totals. History-year totals, including the previous year,
    still sum all 12 months. Diferencia, both percents, and the
    previous-year difference on the Total row use the same completed
    months.

    The Total row can differ by a few cents from one GT Sales Ledger
    total run over a whole year, because the ledger rounds the
    full-period sum once and this footer sums already-rounded months.

Projections
    Two columns, "With the trend" and "Conservative", sit after the
    comparisons. They do not change the actual columns, Promedio, or the
    differences. Both show every month and a Total through December 31.

    The business date is the calendar date in America/Guatemala (fixed
    UTC-6; Guatemala has no daylight-saving time). It is not the server OS
    date and not the viewing user's personal timezone, so every user shares
    the company's sales day. ``report_today`` is that date. The same date
    decides which months are complete, current, or future.

    Actual sales in a projection are submitted invoices posted from January 1
    of the selected year through yesterday. Today and any later posting date
    are forecast, not actual. Those invoices remain inside the existing
    month column, because that column is still the monthly ledger total.

    Finished months keep the actual cell. The open month is actual through
    yesterday plus a forecast for today through the last day of the month.
    Months that have not started are forecast only.

    With the trend
        Daily rate = net actual from January 1 through yesterday / calendar
        days in that same span. The rate is applied to every remaining
        calendar day through December 31, including today. Years to compare
        does not affect it.

        On January 1, and only then for an open year, no day has elapsed.
        The rate is undefined and the column is blank. It is not a forecast
        of zero. Once a day has elapsed, a net of zero is a real rate of
        zero. Returns can make the rate negative; it is not clamped.

    Conservative
        For each pending calendar day, the average of that same month and
        day in the years already chosen by Years to compare (5, 4, 3 or 2;
        default 5). No growth uplift. There is no second history filter.

        Denominator for one pending day:
        * A history year with no submitted Sales Invoice is absent coverage.
          It is left out, which is the same signal Promedio uses, and it is
          not stored as a zero.
        * A real date in a covered year with no invoice is a zero and stays
          in the denominator.
        * A date that did not exist, such as February 29 in a non-leap
          history year, is left out. It is not a zero.
        * If nothing remains in the denominator, that day's forecast is 0.
        Five consecutive history years contain at most one February 29, so
        a pending leap day has at most one comparable observation.

    A closed selected year has no pending day, so both columns repeat the
    actuals and their totals equal the selected-year total. A future
    selected year is blank in both columns, same as its actual cells.

    Each month is rounded half up to 2 decimals. Total is the sum of those
    twelve cells, not a second rounding of the exact full year, and not the
    completed-months-only total used by the selected year. The exact trend
    identity (actual through yesterday, plus the daily rate times the days
    left) can therefore differ from the footer by a few cents.

    Open-year actuals and history days come from one grouped query with the
    same invoice rules as ``sales_invoices_monthly``: submitted documents
    only, the selected company, and ``grand_total * conversion_rate``
    (company currency, tax included, credit notes negative).
"""

from __future__ import unicode_literals

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import flt

from factura_electronica.factura_electronica.report.gt_sales_ledger.queries import sales_invoices_monthly

# Same decimal precision as gt_sales_ledger.calculate_total (PRECISION).
PRECISION = 2

SPANISH_MONTHS = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)

TOTAL_LABEL = "Total"
HISTORY_SPAN = 5
TREND_LABEL = "With the trend"
CONSERVATIVE_LABEL = "Conservative"
TREND_FIELD = "with_the_trend"
CONSERVATIVE_FIELD = "conservative"

# America/Guatemala never observes daylight-saving time.
GUATEMALA_TZ = timezone(timedelta(hours=-6))


def execute(filters=None):
    """Script Report entry point. Returns (columns, rows)."""

    filters = frappe._dict(filters or {})
    company = filters.get("company") or default_company()
    if not company:
        return [], []

    selected_year = parse_year(filters.get("year"))
    years_to_compare = parse_years_to_compare(filters.get("years_to_compare"))
    years = history_years(selected_year, years_to_compare)
    currency = company_currency(company)

    # History years plus the selected year. The ledger monthly query filters
    # by YYYYMM, so this range is exactly the months a GT Sales Ledger Monthly
    # run would include for each of those years.
    from_date = "{0}-01-01".format(years[0])
    to_date = "{0}-12-31".format(selected_year)
    ledger_rows = sales_invoices_monthly(frappe._dict({
        "company": company,
        "company_currency": currency,
        "from_date": from_date,
        "to_date": to_date,
    }))

    today = report_today()
    # One grouped read, and only while the selected year is still open.
    # Closed and future years do not need a day split.
    daily_rows = []
    if int(selected_year) == today.year:
        daily_rows = sales_invoices_by_day(
            company, from_date, to_date, selected_year, today
        )

    data = build_history(
        selected_year,
        ledger_rows,
        years_to_compare,
        today=today,
        daily_rows=daily_rows,
    )
    for row in data:
        row["currency"] = currency

    return get_columns(years, selected_year), data, comparison_message(selected_year, today)


def report_today():
    """Calendar date in America/Guatemala. Tests patch this instead of the clock."""

    return guatemala_today()


def guatemala_today(now=None):
    """Date of ``now`` in America/Guatemala.

    ``now`` defaults to the current instant. An aware value is converted.
    A naive value is already a Guatemala wall time, which is how tests pin
    a calendar day without involving UTC.
    """

    current = now if now is not None else datetime.now(GUATEMALA_TZ)
    if current.tzinfo is not None:
        current = current.astimezone(GUATEMALA_TZ)
    return current.date()


def comparison_message(selected_year, today):
    """Note shown when the selected year still has an open month."""

    if int(selected_year) != today.year:
        return None
    return _(
        "Totales y comparaciones solo de meses completos. {0} muestra el acumulado "
        "y el promedio, sin diferencia ni porcentaje, y no entra en los totales. "
        "Los meses que aún no inician van en blanco. "
        "With the trend y Conservative proyectan hasta el 31 de diciembre: "
        "real hasta ayer y pronóstico desde hoy."
    ).format(SPANISH_MONTHS[today.month - 1])


def default_company():
    return frappe.defaults.get_user_default("Company")


def company_currency(company):
    return frappe.db.get_value("Company", company, "default_currency") or ""


def parse_year(value):
    if value in (None, ""):
        return date.today().year

    try:
        year = int(value)
    except (TypeError, ValueError):
        frappe.throw(_("Year must be a whole number"))

    if year < 1900 or year > 9999:
        frappe.throw(_("Year is out of range"))

    return year


def parse_years_to_compare(value):
    """How many years before the selector to show. Empty means 5."""

    if value in (None, ""):
        return HISTORY_SPAN

    try:
        span = int(value)
    except (TypeError, ValueError):
        span = None

    if span not in (2, 3, 4, 5):
        frappe.throw(_("Years to compare must be 5, 4, 3 or 2"))

    return span


def history_years(selected_year, years_to_compare=HISTORY_SPAN):
    """The ``years_to_compare`` calendar years before ``selected_year``.

    2026 with 5 is 2021..2025. 2026 with 3 is 2023, 2024, 2025.
    """

    span = int(years_to_compare)
    selected_year = int(selected_year)
    return [selected_year - offset for offset in range(span, 0, -1)]


def year_fieldname(year):
    return "y_{0}".format(int(year))


def year_column(year):
    return {
        "label": str(int(year)),
        "fieldname": year_fieldname(year),
        "fieldtype": "Currency",
        "options": "currency",
        "width": 120,
    }


def get_columns(years, selected_year):
    columns = [{
        "label": "Mes",
        "fieldname": "mes",
        "fieldtype": "Data",
        "width": 140,
    }]

    for year in years:
        columns.append(year_column(year))

    columns.append({
        "label": "Promedio",
        "fieldname": "promedio",
        "fieldtype": "Currency",
        "options": "currency",
        "width": 130,
    })
    # The selected year is shown, and it is not one of the Promedio inputs.
    columns.append(year_column(selected_year))
    columns.append({
        "label": "Diferencia",
        "fieldname": "diferencia",
        "fieldtype": "Currency",
        "options": "currency",
        "width": 130,
    })
    columns.append({
        "label": "% vs Promedio",
        "fieldname": "vs_promedio",
        "fieldtype": "Percent",
        "precision": 2,
        "width": 140,
    })
    previous_year = int(selected_year) - 1
    columns.append({
        "label": "Dif. vs {0}".format(previous_year),
        "fieldname": "dif_vs_prev",
        "fieldtype": "Currency",
        "options": "currency",
        "width": 140,
    })
    columns.append({
        "label": "% vs {0}".format(previous_year),
        "fieldname": "pct_vs_prev",
        "fieldtype": "Percent",
        "precision": 2,
        "width": 130,
    })
    # After the comparisons so the existing column order stays put.
    columns.append({
        "label": TREND_LABEL,
        "fieldname": TREND_FIELD,
        "fieldtype": "Currency",
        "options": "currency",
        "width": 150,
    })
    columns.append({
        "label": CONSERVATIVE_LABEL,
        "fieldname": CONSERVATIVE_FIELD,
        "fieldtype": "Currency",
        "options": "currency",
        "width": 140,
    })
    columns.append({
        "label": _("Currency"),
        "fieldname": "currency",
        "fieldtype": "Link",
        "options": "Currency",
        "hidden": 1,
    })
    return columns


def build_history(selected_year, ledger_rows, years_to_compare=HISTORY_SPAN, today=None,
                  daily_rows=None):
    """Pivot GT Sales Ledger monthly totals into 12 month rows plus Total.

    ``ledger_rows`` is the list returned by ``sales_invoices_monthly``:
    ``month_repo``, ``year_repo`` and ``total`` (already summed in SQL).
    The ``years_to_compare`` years before ``selected_year`` are the history
    columns. ``selected_year`` is its own column after Promedio.
    ``today`` defaults to the Guatemala business date.

    ``daily_rows`` are per-day sums (``year_repo``, ``month_repo``,
    ``day_repo``, ``total``) for the open year. Actuals stop at yesterday
    even when a row is dated today or later. Finished months still display
    the monthly ledger cell. When a finished month has no daily rows, its
    raw ledger total is used in the trend numerator so a monthly-only
    caller does not drop that month; the open month never falls back to the
    ledger total, because that total can include today.
    """

    selected_year = int(selected_year)
    if today is None:
        today = report_today()
    years = history_years(selected_year, years_to_compare)
    previous_year = selected_year - 1
    raw_totals = {}
    years_with_data = set()

    for row in ledger_rows or []:
        year = int(row.get("year_repo"))
        month = int(row.get("month_repo"))
        if month < 1 or month > 12:
            continue

        key = (year, month)
        amount = row.get("total") or 0
        if key in raw_totals:
            raw_totals[key] = _to_decimal(raw_totals[key]) + _to_decimal(amount)
        else:
            raw_totals[key] = amount
        years_with_data.add(year)

    def month_total(year, month):
        if (year, month) not in raw_totals:
            return 0.0
        return flt(raw_totals[(year, month)], PRECISION)

    projection = build_year_projection(
        selected_year, today, years, years_with_data, raw_totals, daily_rows
    )

    rows = []
    complete_selected = []
    complete_promedio = []
    complete_previous = []
    selected_field = year_fieldname(selected_year)

    for month_index, month_name in enumerate(SPANISH_MONTHS, start=1):
        row = {"mes": month_name}
        values = {}
        for year in years:
            amount = month_total(year, month_index)
            row[year_fieldname(year)] = amount
            values[year] = amount
        # ``years`` is the history window only, so the selected year stays
        # out of Promedio even when that year has invoices.
        promedio = average_month(values, years, years_with_data)
        selected_amount = month_total(selected_year, month_index)
        previous_amount = month_total(previous_year, month_index)
        state = month_state(selected_year, month_index, today)

        if state == "future":
            row["promedio"] = None
            row[selected_field] = None
            clear_comparisons(row)
        elif state == "current":
            row["promedio"] = promedio
            row[selected_field] = selected_amount
            clear_comparisons(row)
        else:
            row["promedio"] = promedio
            row[selected_field] = selected_amount
            fill_comparisons(row, selected_amount, promedio, previous_amount)
            complete_selected.append(selected_amount)
            complete_promedio.append(promedio)
            complete_previous.append(previous_amount)
        assign_projection(row, projection, month_index, selected_amount)
        rows.append(row)

    total_row = {"mes": TOTAL_LABEL}
    for year in years:
        total_row[year_fieldname(year)] = flt(
            sum(row[year_fieldname(year)] for row in rows), PRECISION
        )
    # Current and future months stay off these two totals, so
    # Promedio + Diferencia equals the selected-year total.
    total_row["promedio"] = sum_amounts(complete_promedio)
    total_row[selected_field] = sum_amounts(complete_selected)
    if complete_selected:
        fill_comparisons(
            total_row,
            sum_amounts(complete_selected),
            sum_amounts(complete_promedio),
            sum_amounts(complete_previous),
        )
    else:
        clear_comparisons(total_row)
    assign_projection_total(total_row, rows, projection, selected_field)
    rows.append(total_row)
    return rows


def month_state(selected_year, month_index, today):
    """complete, current (month already started), or future (not started)."""

    if selected_year < today.year:
        return "complete"
    if selected_year > today.year or month_index > today.month:
        return "future"
    if month_index == today.month:
        return "current"
    return "complete"


def sum_amounts(values):
    if not values:
        return 0.0
    return flt(sum(values), PRECISION)


def fill_comparisons(row, selected_amount, promedio, previous_amount):
    row["diferencia"] = month_difference(selected_amount, promedio)
    row["vs_promedio"] = percent_vs_promedio(selected_amount, promedio)
    row["dif_vs_prev"] = month_difference(selected_amount, previous_amount)
    row["pct_vs_prev"] = percent_vs_promedio(selected_amount, previous_amount)


def clear_comparisons(row):
    row["diferencia"] = None
    row["vs_promedio"] = None
    row["dif_vs_prev"] = None
    row["pct_vs_prev"] = None


def month_difference(selected, promedio):
    """Selected-year amount minus Promedio, rounded half up to 2 decimals."""

    from decimal import ROUND_HALF_UP, Decimal

    difference = (_to_decimal(selected) - _to_decimal(promedio)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return flt(difference, PRECISION)


def percent_vs_promedio(selected, promedio):
    """Percent change versus Promedio. Blank when Promedio is 0."""

    promedio_amount = _to_decimal(promedio)
    if promedio_amount == 0:
        return None

    from decimal import ROUND_HALF_UP, Decimal

    ratio = ((_to_decimal(selected) - promedio_amount) / promedio_amount) * Decimal("100")
    rounded = ratio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return flt(rounded, PRECISION)


def average_month(values, years, years_with_data):
    """Average of the selected history years, skipping years with no invoices.

    ``values`` are the already-rounded month cells (what the grid shows).
    The average is rounded half up to 2 decimals from those cells, so v13 and
    v15 ``flt`` do not disagree by a cent on values such as 100.10 / 4.
    """

    included = [year for year in years if year in years_with_data]
    if not included:
        return 0.0

    from decimal import Decimal, ROUND_HALF_UP

    total = sum((Decimal(str(values[year])) for year in included), Decimal("0"))
    average = (total / Decimal(len(included))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return flt(average, PRECISION)


def _to_decimal(value):
    from decimal import Decimal

    if isinstance(value, Decimal):
        return value
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def round_money(value):
    """Half-up to the same 2 decimals as a monthly ledger cell."""

    from decimal import ROUND_HALF_UP, Decimal

    rounded = _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return flt(rounded, PRECISION)


def sales_invoices_by_day(company, from_date, to_date, selected_year, today):
    """One grouped day-total for the open year's forecast.

    Same population as ``sales_invoices_monthly``: submitted Sales Invoices
    for this company, amount ``grand_total * conversion_rate`` (company
    currency, tax included). Credit notes stay in the sum because their
    ``grand_total`` is negative. Drafts and cancellations stay out.

    The selected year's rows stop before ``today``. History rows are limited
    to month-days that are still pending in the selected year, so February
    of a prior year is not read once March has started. This is a single
    ``GROUP BY`` scan, not a query per day. ``frappe.db.sql`` is the same
    path the monthly ledger uses; the report roles are unchanged.
    """

    selected_year = int(selected_year)
    today = as_date(today)
    return frappe.db.sql(
        """
        SELECT YEAR(SI.posting_date) AS year_repo,
               MONTH(SI.posting_date) AS month_repo,
               DAY(SI.posting_date) AS day_repo,
               SUM(SI.grand_total * SI.conversion_rate) AS total
        FROM `tabSales Invoice` AS SI
        WHERE SI.docstatus = 1
          AND SI.company = %(company)s
          AND SI.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND (
                (SI.posting_date >= %(year_start)s AND SI.posting_date < %(today)s)
                OR (
                    SI.posting_date < %(year_start)s
                    AND (
                        MONTH(SI.posting_date) > %(month)s
                        OR (
                            MONTH(SI.posting_date) = %(month)s
                            AND DAY(SI.posting_date) >= %(day)s
                        )
                    )
                )
          )
        GROUP BY year_repo, month_repo, day_repo
        ORDER BY year_repo, month_repo, day_repo
        """,
        {
            "company": company,
            "from_date": _as_iso(from_date),
            "to_date": _as_iso(to_date),
            "year_start": date(selected_year, 1, 1).isoformat(),
            "today": today.isoformat(),
            "month": today.month,
            "day": today.day,
        },
        as_dict=True,
    )


def build_year_projection(selected_year, today, years, years_with_data, raw_totals,
                          daily_rows=None):
    """Month projections for one selected year, plus the trend identity.

    ``mode`` is ``closed`` (repeat actuals), ``future`` (blank), or ``open``.
    For an open year each month dict carries the rounded cells and the exact
    Decimal pieces. ``trend_exact`` sums to ``ytd_actual + daily_rate *
    remaining_days`` when the rate exists.
    """

    selected_year = int(selected_year)
    today = as_date(today)
    if today.year > selected_year:
        return {"mode": "closed"}
    if today.year < selected_year:
        return {"mode": "future"}

    index = index_daily_rows(daily_rows, selected_year, today)
    elapsed = elapsed_days(selected_year, today)
    remaining = remaining_days(selected_year, today)
    ytd = year_to_date_actual(index, raw_totals, selected_year, today, elapsed)
    rate = None
    if elapsed:
        rate = ytd / Decimal(elapsed)

    months = []
    for month in range(1, 13):
        state = month_state(selected_year, month, today)
        ledger_amount = rounded_month_total(raw_totals, selected_year, month)
        actual_exact = month_actual_exact(
            index, raw_totals, selected_year, month, today, state
        )
        if state == "complete":
            months.append(_projection_month(
                ledger_amount, ledger_amount, actual_exact, actual_exact
            ))
            continue

        history_forecast = conservative_forecast_for_month(
            month, today, years, years_with_data, index, selected_year
        )
        if rate is None:
            months.append(_projection_month(
                None, round_money(history_forecast), None, history_forecast
            ))
            continue

        forecast_days = month_forecast_days(selected_year, month, today)
        trend_exact = actual_exact + (rate * Decimal(forecast_days))
        conservative_exact = actual_exact + history_forecast
        months.append(_projection_month(
            round_money(trend_exact),
            round_money(conservative_exact),
            trend_exact,
            conservative_exact,
        ))

    return {
        "mode": "open",
        "elapsed_days": elapsed,
        "remaining_days": remaining,
        "ytd_actual": ytd,
        "daily_rate": rate,
        "months": months,
    }


def _projection_month(trend_display, conservative_display, trend_exact, conservative_exact):
    return {
        TREND_FIELD: trend_display,
        CONSERVATIVE_FIELD: conservative_display,
        "trend_exact": trend_exact,
        "conservative_exact": conservative_exact,
    }


def assign_projection(row, projection, month_index, selected_amount):
    mode = projection["mode"]
    if mode == "closed":
        row[TREND_FIELD] = selected_amount
        row[CONSERVATIVE_FIELD] = selected_amount
        return
    if mode == "future":
        row[TREND_FIELD] = None
        row[CONSERVATIVE_FIELD] = None
        return
    month = projection["months"][month_index - 1]
    row[TREND_FIELD] = month[TREND_FIELD]
    row[CONSERVATIVE_FIELD] = month[CONSERVATIVE_FIELD]


def assign_projection_total(total_row, month_rows, projection, selected_field):
    """Full-year footer. Closed years reuse the selected-year total."""

    if projection["mode"] == "closed":
        total_row[TREND_FIELD] = total_row[selected_field]
        total_row[CONSERVATIVE_FIELD] = total_row[selected_field]
        return
    if projection["mode"] == "future":
        total_row[TREND_FIELD] = None
        total_row[CONSERVATIVE_FIELD] = None
        return
    total_row[TREND_FIELD] = footer_projection(month_rows, TREND_FIELD)
    total_row[CONSERVATIVE_FIELD] = footer_projection(month_rows, CONSERVATIVE_FIELD)


def footer_projection(month_rows, fieldname):
    values = [row[fieldname] for row in month_rows]
    if all(value is None for value in values):
        return None
    total = sum((_to_decimal(value) for value in values), Decimal("0"))
    return round_money(total)


def elapsed_days(year, today):
    """Calendar days from January 1 through yesterday. Zero on January 1."""

    today = as_date(today)
    start = date(int(year), 1, 1)
    if today <= start:
        return 0
    yesterday = today - timedelta(days=1)
    if yesterday < start:
        return 0
    return (yesterday - start).days + 1


def remaining_days(year, today):
    """Calendar days from today through December 31, inclusive."""

    today = as_date(today)
    year = int(year)
    if today.year != year:
        return 0
    end = date(year, 12, 31)
    if today > end:
        return 0
    return (end - today).days + 1


def month_forecast_days(year, month, today):
    """Days of this month that are still forecast, including today."""

    today = as_date(today)
    start = pending_start(year, month, today)
    if start is None:
        return 0
    end = last_day(year, month)
    return (end - start).days + 1


def pending_start(year, month, today):
    """First forecast day in the month, or None when the month is finished."""

    today = as_date(today)
    month_start = date(int(year), int(month), 1)
    month_end = last_day(year, month)
    if today > month_end:
        return None
    if today.year == int(year) and today.month == int(month):
        return today
    return month_start


def last_day(year, month):
    return date(int(year), int(month), monthrange(int(year), int(month))[1])


def is_real_date(year, month, day):
    try:
        date(int(year), int(month), int(day))
    except (TypeError, ValueError):
        return False
    return True


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    year, month, day = text.split("-")
    return date(int(year), int(month), int(day))


def _as_iso(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def index_daily_rows(daily_rows, selected_year, today):
    """Sum day totals. Selected-year dates on or after ``today`` are dropped."""

    index = {}
    selected_year = int(selected_year)
    today = as_date(today)
    for row in daily_rows or []:
        year = row.get("year_repo")
        month = row.get("month_repo")
        day = row.get("day_repo")
        if year in (None, "") or month in (None, "") or day in (None, ""):
            continue
        year = int(year)
        month = int(month)
        day = int(day)
        if not is_real_date(year, month, day):
            continue
        posted = date(year, month, day)
        if year == selected_year and posted >= today:
            continue
        key = (year, month, day)
        index[key] = index.get(key, Decimal("0")) + _to_decimal(row.get("total"))
    return index


def sum_indexed_days(index, year, start, end):
    if end < start:
        return Decimal("0")
    total = Decimal("0")
    current = start
    while current <= end:
        total += index.get((int(year), current.month, current.day), Decimal("0"))
        current += timedelta(days=1)
    return total


def month_has_daily(index, year, month):
    prefix = (int(year), int(month))
    return any(key[0] == prefix[0] and key[1] == prefix[1] for key in index)


def raw_ledger_month(raw_totals, year, month):
    if (int(year), int(month)) not in raw_totals:
        return Decimal("0")
    return _to_decimal(raw_totals[(int(year), int(month))])


def rounded_month_total(raw_totals, year, month):
    if (int(year), int(month)) not in raw_totals:
        return 0.0
    return flt(raw_totals[(int(year), int(month))], PRECISION)


def year_to_date_actual(index, raw_totals, year, today, elapsed):
    """Net actual from January 1 through yesterday.

    Daily rows are the source when present. A finished month that has no
    daily row falls back to the raw monthly ledger total. The open month
    does not: its ledger total can contain today.
    """

    if not elapsed:
        return Decimal("0")
    today = as_date(today)
    yesterday = today - timedelta(days=1)
    total = sum_indexed_days(index, year, date(int(year), 1, 1), yesterday)
    for month in range(1, today.month):
        if month_has_daily(index, year, month):
            continue
        total += raw_ledger_month(raw_totals, year, month)
    return total


def month_actual_exact(index, raw_totals, year, month, today, state):
    """Raw actual inside one month, stopping at yesterday."""

    if state == "future":
        return Decimal("0")
    month_start = date(int(year), int(month), 1)
    month_end = last_day(year, month)
    if state == "complete":
        if month_has_daily(index, year, month):
            return sum_indexed_days(index, year, month_start, month_end)
        return raw_ledger_month(raw_totals, year, month)
    yesterday = as_date(today) - timedelta(days=1)
    if yesterday < month_start:
        return Decimal("0")
    return sum_indexed_days(index, year, month_start, min(yesterday, month_end))


def conservative_day_parts(month, day, years, years_with_data, index):
    """Return ``(average, observations)`` for one calendar day.

    Observations are covered history years in which that date existed.
    A missing invoice on a real date counts as zero. A nonexistent date
    and a year with no invoices do not.
    """

    numerator = Decimal("0")
    observations = 0
    for year in years:
        if year not in years_with_data:
            continue
        if not is_real_date(year, month, day):
            continue
        numerator += index.get((int(year), int(month), int(day)), Decimal("0"))
        observations += 1
    if observations == 0:
        return Decimal("0"), 0
    return numerator / Decimal(observations), observations


def conservative_forecast_for_month(month, today, years, years_with_data, index, year):
    start = pending_start(year, month, today)
    if start is None:
        return Decimal("0")
    total = Decimal("0")
    current = start
    end = last_day(year, month)
    while current <= end:
        amount, _observations = conservative_day_parts(
            current.month, current.day, years, years_with_data, index
        )
        total += amount
        current += timedelta(days=1)
    return total
