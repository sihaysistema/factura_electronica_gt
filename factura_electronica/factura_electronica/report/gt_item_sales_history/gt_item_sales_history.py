# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt

"""GT Item Sales History.

The GT Monthly Sales History layout for items: one row per period of the
selected year (ISO weeks, months or quarters) plus Total, one column per
history year, the Average of those years, the selected year, and the
differences against the Average and against the same period last year.

Scope is every item, one Item, or an Item Group (with its child groups).
Metric is Units (stock quantity) or Amount (net, without IVA by default;
"Include IVA" switches to the grand-total basis). Invoice rules, weeks,
the Average and the open-period rule are in
``factura_electronica.utils.item_sales_analytics``.

Total row
    History-year totals sum every period of that year. While the selected
    year is still open, the selected year, the Average and every
    difference on the Total row use completed periods only, so the period
    in progress never shows as a loss. A closed year uses all periods.
"""

from __future__ import unicode_literals

import frappe
from frappe import _

from factura_electronica.utils import item_sales_analytics as engine


def execute(filters=None):
    filters = frappe._dict(filters or {})
    company = filters.get("company") or engine.default_company()
    if not company:
        return [], []

    today = engine.report_today()
    period_type = engine.parse_period_type(filters.get("period_type"))
    metric = engine.parse_metric(filters.get("metric"))
    include_iva = engine.parse_check(filters.get("include_iva"))
    selected_year = engine.parse_year(filters.get("year"), today)
    years = engine.history_years(
        selected_year, engine.parse_years_to_compare(filters.get("years_to_compare"))
    )
    currency = engine.company_currency(company)

    from_date = engine.year_bounds(period_type, years[0])[0]
    to_date = engine.year_bounds(period_type, selected_year)[1]
    rows = engine.fetch_period_rows(
        company,
        period_type,
        from_date,
        to_date,
        item_code=filters.get("item_code"),
        item_group=filters.get("item_group"),
        include_iva=include_iva,
        by_item=False,
    )
    covered = engine.covered_years(company, period_type, from_date, to_date)
    series = engine.total_series(engine.aggregate(rows, metric)[0])

    data = build_rows(series, period_type, selected_year, years, covered, today)
    for row in data:
        row["currency"] = currency

    columns = get_columns(period_type, years, selected_year, metric)
    chart = build_chart(data, years, selected_year, metric, currency)
    message = build_message(period_type, selected_year, metric, include_iva, today)
    return columns, data, message, chart


def build_rows(series, period_type, selected_year, years, covered, today):
    count = engine.periods_in_year(period_type, selected_year)
    month_rows = []
    for index in range(1, count + 1):
        state = engine.period_state(period_type, selected_year, index, today)
        start, end = engine.period_bounds(period_type, selected_year, index)
        row = {
            "period": engine.period_name(period_type, index),
            "period_index": index,
            "from_date": str(start),
            "to_date": str(end),
            "state": state,
        }
        for year in years:
            if index > engine.periods_in_year(period_type, year):
                row[year_field(year)] = None
            else:
                row[year_field(year)] = engine.round_value(series.get((year, index), 0))
        if state == engine.FUTURE:
            row["promedio"] = None
            row["selected"] = None
            last_year = None
        else:
            row["promedio"] = engine.average_for(series, period_type, years, covered, index)
            row["selected"] = engine.round_value(series.get((selected_year, index), 0))
            last_year = engine.last_year_value(series, period_type, selected_year, index)
        row["last_year"] = last_year
        row.update(engine.comparison_cells(row["selected"], row["promedio"], last_year, state))
        month_rows.append(row)

    month_rows.append(total_row(month_rows, years))
    return month_rows


def total_row(month_rows, years):
    total = {"period": _("Total"), "is_total_row": 1}
    for year in years:
        total[year_field(year)] = _sum(row.get(year_field(year)) for row in month_rows)

    complete = [row for row in month_rows if row["state"] == engine.COMPLETE]
    selected = _sum(row["selected"] for row in complete) if complete else None
    average = _sum(row["promedio"] for row in complete if row["promedio"] is not None) \
        if any(row["promedio"] is not None for row in complete) else None
    last_year = _sum(row["last_year"] for row in complete if row["last_year"] is not None) \
        if any(row["last_year"] is not None for row in complete) else None
    total["selected"] = selected
    total["promedio"] = average
    total["last_year"] = last_year
    total.update(engine.comparison_cells(selected, average, last_year, engine.COMPLETE))
    return total


def _sum(values):
    from decimal import Decimal

    total = Decimal("0")
    for value in values:
        if value is not None:
            total += engine.to_decimal(value)
    return engine.round_value(total)


def year_field(year):
    return "y_{0}".format(int(year))


def get_columns(period_type, years, selected_year, metric):
    columns = [
        {"label": _("Period"), "fieldname": "period", "fieldtype": "Data", "width": 110},
        {"label": _("From"), "fieldname": "from_date", "fieldtype": "Date", "width": 100},
    ]
    for year in years:
        columns.append(engine.value_column(str(year), year_field(year), metric))
    columns.append(engine.value_column(_("Average"), "promedio", metric, 120))
    columns.append(engine.value_column(str(selected_year), "selected", metric, 120))
    columns.extend(engine.comparison_columns(metric, selected_year - 1))
    return columns


def build_chart(data, years, selected_year, metric, currency):
    periods = [row for row in data if not row.get("is_total_row")]
    chart = {
        "type": "axis-mixed",
        "data": {
            "labels": [row["period"] for row in periods],
            "datasets": [
                {"name": str(selected_year), "chartType": "bar",
                 "values": [engine.chart_number(row["selected"]) for row in periods]},
                {"name": _("Average"), "chartType": "line",
                 "values": [engine.chart_number(row["promedio"]) for row in periods]},
                {"name": str(selected_year - 1), "chartType": "line",
                 "values": [engine.chart_number(row.get(year_field(selected_year - 1)))
                            for row in periods]},
            ],
        },
        "colors": ["#5e64ff", "#98d85b", "#ffa00a"],
        "height": 280,
    }
    if metric == engine.AMOUNT:
        chart.update({"fieldtype": "Currency", "options": "currency", "currency": currency})
    return chart


def build_message(period_type, selected_year, metric, include_iva, today):
    parts = []
    if metric == engine.AMOUNT:
        parts.append(_("Amount includes IVA.") if include_iva else _("Amount is net, without IVA."))
    else:
        parts.append(_("Units are stock quantities of every item in the selection."))
    if period_type == engine.WEEKLY:
        parts.append(_("Weeks are ISO weeks, Monday to Sunday; the year is the ISO week-year."))
    if int(selected_year) == engine.current_period(period_type, today)[0]:
        parts.append(_(
            "The period in progress shows its difference and percent only once it is ahead "
            "of the Average or of last year. Totals use completed periods only."
        ))
    return " ".join(parts)
