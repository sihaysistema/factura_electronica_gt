# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt

"""GT Item Sales Analytics.

Ranks items for one period (an ISO week, a month or a quarter of the
selected year) against the Average of the same period in the years to
compare and against the same period last year. Items are sorted by the
selected period, largest first; a period that has not started is sorted
by its Average, which is then the expected volume.

"Group by Item Group" shows each item's current Item Group as a parent
row with its items under it. "Share %" is the item's part of the selected
period's total and "Cumulative %" adds the shares down the ranking (the
Pareto view; with grouping, cumulative runs inside each group).

Clicking an item name (or a group name) opens GT Item Sales History with
the same company, year, period type, metric and IVA choice.

Rules for invoices, weeks, the Average and the open period are in
``factura_electronica.utils.item_sales_analytics``. A period that has not
started shows the Average and last year but no selected value and no
differences.
"""

from __future__ import unicode_literals

from decimal import Decimal

import frappe
from frappe import _

from factura_electronica.utils import item_sales_analytics as engine

CHART_TOP_OPTIONS = (5, 10, 15, 20, 25)
CHART_LABEL_LENGTH = 28


def execute(filters=None):
    filters = frappe._dict(filters or {})
    company = filters.get("company") or engine.default_company()
    if not company:
        return [], []

    today = engine.report_today()
    period_type = engine.parse_period_type(filters.get("period_type"))
    metric = engine.parse_metric(filters.get("metric"))
    include_iva = engine.parse_check(filters.get("include_iva"))
    group_by_item_group = engine.parse_check(filters.get("group_by_item_group"))
    selected_year = engine.parse_year(filters.get("year"), today)
    index = engine.parse_period(filters.get("period"), period_type, selected_year, today)
    years = engine.history_years(
        selected_year, engine.parse_years_to_compare(filters.get("years_to_compare"))
    )
    chart_top = parse_chart_top(filters.get("chart_top"))
    currency = engine.company_currency(company)
    state = engine.period_state(period_type, selected_year, index, today)

    spans = []
    for year in years + [selected_year]:
        if index <= engine.periods_in_year(period_type, year):
            spans.append(engine.period_bounds(period_type, year, index))
    from_date = engine.year_bounds(period_type, years[0])[0]
    to_date = engine.year_bounds(period_type, selected_year)[1]
    rows = engine.fetch_period_rows(
        company,
        period_type,
        spans[0][0],
        spans[-1][1],
        item_group=filters.get("item_group"),
        include_iva=include_iva,
        date_ranges=spans,
    )
    covered = engine.covered_years(company, period_type, from_date, to_date)
    series, info = engine.aggregate(rows, metric)

    items = build_item_rows(series, info, period_type, selected_year, index, years, covered, state)
    data = arrange(items, group_by_item_group, state)
    data.append(total_row(items, state))
    for row in data:
        row["currency"] = currency

    columns = get_columns(period_type, selected_year, index, metric, group_by_item_group)
    chart = build_chart(items, chart_top, period_type, selected_year, index, metric, currency)
    summary = build_summary(data[-1], items, state, metric, currency)
    message = build_message(period_type, selected_year, index, metric, include_iva, state)
    return columns, data, message, chart, summary


def parse_chart_top(value):
    if value in (None, ""):
        return 10
    try:
        top = int(value)
    except (TypeError, ValueError):
        top = None
    if top not in CHART_TOP_OPTIONS:
        frappe.throw(_("Chart top must be 5, 10, 15, 20 or 25"))
    return top


def build_item_rows(series, info, period_type, selected_year, index, years, covered, state):
    items = []
    for item_code, values in series.items():
        selected = None if state == engine.FUTURE else engine.round_value(
            values.get((selected_year, index), 0)
        )
        average = engine.average_for(values, period_type, years, covered, index)
        last_year = engine.last_year_value(values, period_type, selected_year, index)
        if not any(value for value in (selected, average, last_year)):
            continue
        source = info[item_code]
        row = {
            "item_code": item_code,
            "item_name": source.get("item_name") or item_code,
            "item_group": source.get("item_group") or "",
            "selected": selected,
            "promedio": average,
            "last_year": last_year,
        }
        row.update(engine.comparison_cells(selected, average, last_year, state))
        items.append(row)
    items.sort(key=lambda row: sort_key(row, state))
    return items


def sort_key(row, state):
    primary = row["promedio"] if state == engine.FUTURE else row["selected"]
    return (-(primary or 0), -(row["promedio"] or 0), row["item_code"])


def add_shares(rows, base_total):
    cumulative = Decimal("0")
    for row in rows:
        if row["selected"] is None or not base_total:
            row["share"] = None
            row["cumulative"] = None
            continue
        share = engine.to_decimal(row["selected"]) / engine.to_decimal(base_total) * Decimal("100")
        cumulative += share
        row["share"] = engine.round_value(share)
        row["cumulative"] = engine.round_value(cumulative)


def arrange(items, group_by_item_group, state):
    period_total = _sum(row["selected"] for row in items)
    if not group_by_item_group:
        add_shares(items, period_total)
        for row in items:
            row["indent"] = 0
        return list(items)

    groups = {}
    for row in items:
        groups.setdefault(row["item_group"] or _("(No Item Group)"), []).append(row)
    parents = []
    for name, children in groups.items():
        parent = {
            "item_code": None,
            "item_name": name,
            "item_group": name,
            "is_group": 1,
            "indent": 0,
            "selected": _sum_optional(row["selected"] for row in children),
            "promedio": _sum_optional(row["promedio"] for row in children),
            "last_year": _sum_optional(row["last_year"] for row in children),
        }
        parent.update(engine.comparison_cells(
            parent["selected"], parent["promedio"], parent["last_year"], state
        ))
        parents.append((parent, children))
    parents.sort(key=lambda pair: sort_key(dict(pair[0], item_code=pair[0]["item_name"]), state))

    add_shares([parent for parent, _children in parents], period_total)
    data = []
    for parent, children in parents:
        data.append(parent)
        add_shares(children, period_total)
        # Cumulative inside a group restarts at that group's first item.
        for child in children:
            child["indent"] = 1
            child["parent_item_group"] = parent["item_name"]
            data.append(child)
    return data


def total_row(items, state):
    total = {
        "item_code": None,
        "item_name": _("Total"),
        "is_total_row": 1,
        "indent": 0,
        "selected": _sum_optional(row["selected"] for row in items),
        "promedio": _sum_optional(row["promedio"] for row in items),
        "last_year": _sum_optional(row["last_year"] for row in items),
    }
    total.update(engine.comparison_cells(
        total["selected"], total["promedio"], total["last_year"], state
    ))
    total["share"] = 100.0 if total["selected"] else None
    total["cumulative"] = None
    return total


def _sum(values):
    total = Decimal("0")
    for value in values:
        if value is not None:
            total += engine.to_decimal(value)
    return engine.round_value(total)


def _sum_optional(values):
    values = [value for value in values if value is not None]
    if not values:
        return None
    return _sum(values)


def get_columns(period_type, selected_year, index, metric, group_by_item_group):
    columns = []
    columns.append({"label": _("Item") if not group_by_item_group else _("Item Group / Item"),
                    "fieldname": "item_name", "fieldtype": "Data", "width": 260})
    columns.append({"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link",
                    "options": "Item", "width": 130})
    if not group_by_item_group:
        columns.append({"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link",
                        "options": "Item Group", "width": 160})
    columns.append(engine.value_column(
        engine.period_label(period_type, index, selected_year), "selected", metric, 120
    ))
    columns.append(engine.value_column(_("Average"), "promedio", metric, 120))
    columns.append(engine.value_column(
        engine.period_label(period_type, index, selected_year - 1), "last_year", metric, 120
    ))
    columns.extend(engine.comparison_columns(metric, selected_year - 1))
    columns.append({"label": _("Share %"), "fieldname": "share", "fieldtype": "Float",
                    "precision": engine.PRECISION, "width": 90})
    columns.append({"label": _("Cumulative %"), "fieldname": "cumulative", "fieldtype": "Float",
                    "precision": engine.PRECISION, "width": 110})
    return columns


def build_chart(items, chart_top, period_type, selected_year, index, metric, currency):
    top = items[:chart_top]
    if not top:
        return None
    chart = {
        "type": "bar",
        "data": {
            "labels": [short_label(row["item_name"]) for row in top],
            "datasets": [
                {"name": engine.period_label(period_type, index, selected_year),
                 "values": [engine.chart_number(row["selected"]) for row in top]},
                {"name": _("Average"),
                 "values": [engine.chart_number(row["promedio"]) for row in top]},
                {"name": engine.period_label(period_type, index, selected_year - 1),
                 "values": [engine.chart_number(row["last_year"]) for row in top]},
            ],
        },
        "colors": ["#5e64ff", "#98d85b", "#ffa00a"],
        "barOptions": {"spaceRatio": 0.3},
        "height": 300,
    }
    if metric == engine.AMOUNT:
        chart.update({"fieldtype": "Currency", "options": "currency", "currency": currency})
    return chart


def short_label(text):
    text = text or ""
    if len(text) <= CHART_LABEL_LENGTH:
        return text
    return text[: CHART_LABEL_LENGTH - 1] + "…"


def build_summary(total, items, state, metric, currency):
    datatype = "Currency" if metric == engine.AMOUNT else "Float"

    def card(label, value, indicator, kind=datatype):
        entry = {"label": label, "value": value if value is not None else "", "indicator": indicator,
                 "datatype": kind}
        if kind == "Currency":
            entry["currency"] = currency
        return entry

    def indicator(value):
        if value is None:
            return "Blue"
        if value > 0:
            return "Green"
        # The open period never shows red (cells are blank until ahead).
        return "Red" if state == engine.COMPLETE and value < 0 else "Blue"

    return [
        card(_("Selected period"), total["selected"], "Blue"),
        card(_("Average"), total["promedio"], "Blue"),
        card(_("% vs Average"), total["vs_promedio"], indicator(total["vs_promedio"]), "Percent"),
        card(_("% vs last year"), total["pct_vs_prev"], indicator(total["pct_vs_prev"]), "Percent"),
        card(_("Items sold"), len([row for row in items if row["selected"]]), "Blue", "Int"),
    ]


def build_message(period_type, selected_year, index, metric, include_iva, state):
    start, end = engine.period_bounds(period_type, selected_year, index)
    parts = [_("{0}: {1} to {2}.").format(
        engine.period_label(period_type, index, selected_year), start, end
    )]
    if metric == engine.AMOUNT:
        parts.append(_("Amount includes IVA.") if include_iva else _("Amount is net, without IVA."))
    if period_type == engine.WEEKLY:
        parts.append(_("Weeks are ISO weeks, Monday to Sunday; the year is the ISO week-year."))
    if state == engine.CURRENT:
        parts.append(_(
            "This period is in progress: differences show only once an item is ahead of the "
            "Average or of last year."
        ))
    elif state == engine.FUTURE:
        parts.append(_("This period has not started: Average and last year show what to expect."))
    parts.append(_("Click an item to open its history."))
    return " ".join(parts)
