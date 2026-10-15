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
"""

from __future__ import unicode_literals

from datetime import date

import frappe
from frappe import _
from frappe.utils import flt, getdate

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
    ledger_rows = sales_invoices_monthly(frappe._dict({
        "company": company,
        "company_currency": currency,
        "from_date": "{0}-01-01".format(years[0]),
        "to_date": "{0}-12-31".format(selected_year),
    }))

    today = report_today()
    data = build_history(selected_year, ledger_rows, years_to_compare, today=today)
    for row in data:
        row["currency"] = currency

    return get_columns(years, selected_year), data, comparison_message(selected_year, today)


def report_today():
    """Server date. Tests patch this instead of the clock."""

    return getdate()


def comparison_message(selected_year, today):
    """Note shown when the selected year still has an open month."""

    if int(selected_year) != today.year:
        return None
    return _(
        "Totales y comparaciones solo de meses completos. {0} muestra el acumulado "
        "y el promedio, sin diferencia ni porcentaje, y no entra en los totales. "
        "Los meses que aún no inician van en blanco."
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
    columns.append({
        "label": _("Currency"),
        "fieldname": "currency",
        "fieldtype": "Link",
        "options": "Currency",
        "hidden": 1,
    })
    return columns


def build_history(selected_year, ledger_rows, years_to_compare=HISTORY_SPAN, today=None):
    """Pivot GT Sales Ledger monthly totals into 12 month rows plus Total.

    ``ledger_rows`` is the list returned by ``sales_invoices_monthly``:
    ``month_repo``, ``year_repo`` and ``total`` (already summed in SQL).
    The ``years_to_compare`` years before ``selected_year`` are the history
    columns. ``selected_year`` is its own column after Promedio.
    ``today`` defaults to the server date.
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
