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
    the ledger total for that month is zero. If none of the five years have
    invoices, Promedio is 0.00.

    The Total row sums the twelve displayed monthly cells (including Promedio)
    so the columns add down. That footer can differ by a few cents from one
    GT Sales Ledger total run over a whole year, because the ledger rounds the
    full-period sum once and this footer sums already-rounded months.
"""

from __future__ import unicode_literals

from datetime import date

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


def execute(filters=None):
    """Script Report entry point. Returns (columns, rows)."""

    filters = frappe._dict(filters or {})
    company = filters.get("company") or default_company()
    if not company:
        return [], []

    selected_year = parse_year(filters.get("year"))
    years = history_years(selected_year)
    currency = company_currency(company)

    # Full calendar years. The ledger monthly query filters by YYYYMM, so this
    # range is exactly the months that a GT Sales Ledger Monthly run would
    # include for each of those years.
    ledger_rows = sales_invoices_monthly(frappe._dict({
        "company": company,
        "company_currency": currency,
        "from_date": "{0}-01-01".format(years[0]),
        "to_date": "{0}-12-31".format(years[-1]),
    }))

    data = build_history(selected_year, ledger_rows)
    for row in data:
        row["currency"] = currency

    return get_columns(years), data


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


def history_years(selected_year):
    """Five calendar years before ``selected_year`` (year-5 .. year-1)."""

    selected_year = int(selected_year)
    return [selected_year - offset for offset in range(HISTORY_SPAN, 0, -1)]


def year_fieldname(year):
    return "y_{0}".format(int(year))


def get_columns(years):
    columns = [{
        "label": "Mes",
        "fieldname": "mes",
        "fieldtype": "Data",
        "width": 140,
    }]

    for year in years:
        columns.append({
            "label": str(year),
            "fieldname": year_fieldname(year),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        })

    columns.append({
        "label": "Promedio",
        "fieldname": "promedio",
        "fieldtype": "Currency",
        "options": "currency",
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


def build_history(selected_year, ledger_rows):
    """Pivot GT Sales Ledger monthly totals into 12 month rows plus Total.

    ``ledger_rows`` is the list returned by ``sales_invoices_monthly``:
    ``month_repo``, ``year_repo`` and ``total`` (already summed in SQL).
    """

    years = history_years(selected_year)
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
    for month_index, month_name in enumerate(SPANISH_MONTHS, start=1):
        row = {"mes": month_name}
        values = {}
        for year in years:
            amount = month_total(year, month_index)
            row[year_fieldname(year)] = amount
            values[year] = amount
        row["promedio"] = average_month(values, years, years_with_data)
        rows.append(row)

    total_row = {"mes": TOTAL_LABEL}
    for year in years:
        total_row[year_fieldname(year)] = flt(
            sum(row[year_fieldname(year)] for row in rows), PRECISION
        )
    total_row["promedio"] = flt(sum(row["promedio"] for row in rows), PRECISION)
    rows.append(total_row)
    return rows


def average_month(values, years, years_with_data):
    """Average of the five history years, skipping years with no invoices.

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
