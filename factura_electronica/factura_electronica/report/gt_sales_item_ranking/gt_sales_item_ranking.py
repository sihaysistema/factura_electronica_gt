# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt

"""Ranking de artículos vendidos GT.

Submitted Sales Invoices only (``docstatus = 1``). Drafts and cancelled
invoices are excluded. Returns stay in the sum: ERPNext stores their
``qty`` and ``base_net_amount`` as negative numbers, so the totals are
net of returns.

Amount is ``SUM(base_net_amount)``, already in company currency, after
discounts and before tax. Quantity is ``SUM(qty)`` in the UOM stored on
the invoice line. The same item sold in more than one UOM is summed as
those quantities. Average price is amount / quantity, blank when the
net quantity is 0.

"% del total" is the row's net amount divided by the net amount of every
item in the result. It is blank when that total is 0. Rounded percents
can add up to 99.99 or 100.01.

"Ordenar por" sorts descending by amount, quantity or average price.
Ties break by item code. The bar chart is the first "Top del gráfico"
rows of that order. The table lists every item, then a Total row that
is not part of the chart.

Item group matches ``Sales Invoice Item.item_group``, including child
groups of the selected group. Customer matches the invoice customer.
"""

from __future__ import unicode_literals

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

import frappe
from frappe import _
from frappe.utils import getdate

RANK_AMOUNT = "Monto"
RANK_QTY = "Cantidad"
RANK_PRICE = "Precio"
RANK_CHOICES = (RANK_AMOUNT, RANK_QTY, RANK_PRICE)
CHART_TOP_MIN = 1
CHART_TOP_MAX = 50
DEFAULT_CHART_TOP = 10
MONEY_QUANT = Decimal("0.01")
QTY_QUANT = Decimal("0.001")
PERCENT_QUANT = Decimal("0.01")
ZERO_EPSILON = Decimal("0.0000001")


def execute(filters=None):
    """Script Report entry point."""

    filters = normalize_ranking_filters(filters)
    groups = item_group_names(filters.get("item_group"))
    sql, params = ranking_query(filters, groups)
    rows = frappe.db.sql(sql, params, as_dict=True) or []
    data = build_ranking(rows, filters["rank_by"])
    currency = company_currency(filters["company"])
    for row in data:
        row["currency"] = currency
    item_count = len([row for row in data if row.get("item_code")])
    message = ranking_message(
        item_count,
        currency,
        filters["chart_top"],
        filters["rank_by"],
    )
    chart = build_chart(data, filters["rank_by"], filters["chart_top"])
    return get_columns(), data, message, chart


def report_today():
    """Server date. Tests patch this instead of the clock."""

    today = getdate()
    return as_date(today) or date.today()


def default_company():
    return frappe.defaults.get_user_default("Company")


def company_currency(company):
    return frappe.db.get_value("Company", company, "default_currency") or ""


def normalize_ranking_filters(filters):
    raw = filters or {}
    if not isinstance(raw, dict):
        frappe.throw(_("Filtros inválidos"))

    company = clean_text(raw.get("company")) or clean_text(default_company())
    if not company:
        frappe.throw(_("Seleccione una empresa"))

    today = report_today()
    if raw.get("from_date") in (None, ""):
        from_date = date(today.year, 1, 1)
    else:
        from_date = as_date(raw.get("from_date"))
        if from_date is None:
            frappe.throw(_("Desde no es una fecha válida"))
    if raw.get("to_date") in (None, ""):
        to_date = today
    else:
        to_date = as_date(raw.get("to_date"))
        if to_date is None:
            frappe.throw(_("Hasta no es una fecha válida"))
    if from_date > to_date:
        frappe.throw(_("Desde no puede ser posterior a Hasta"))

    rank_by = clean_text(raw.get("rank_by")) or RANK_AMOUNT
    if rank_by not in RANK_CHOICES:
        frappe.throw(_("Ordenar por debe ser Monto, Cantidad o Precio"))

    return {
        "company": company,
        "customer": clean_text(raw.get("customer")),
        "item_group": clean_text(raw.get("item_group")),
        "from_date": from_date,
        "to_date": to_date,
        "rank_by": rank_by,
        "chart_top": parse_chart_top(raw.get("chart_top")),
    }


def parse_chart_top(value):
    if value in (None, ""):
        return DEFAULT_CHART_TOP
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = None
    if number is None or number < CHART_TOP_MIN or number > CHART_TOP_MAX:
        frappe.throw(_("Top del gráfico debe estar entre 1 y 50"))
    return number


def ranking_message(count, currency, top_n, rank_by):
    return _(
        "{0} artículos. Cantidad y monto netos de facturas enviadas; "
        "las devoluciones restan. El monto es el neto en {1}, sin impuestos. "
        "El gráfico muestra los primeros {2} ordenados por {3}."
    ).format(count, currency or "", top_n, rank_by)


def get_columns():
    return [
        {
            "label": "Puesto",
            "fieldname": "puesto",
            "fieldtype": "Int",
            "width": 70,
        },
        {
            "label": "Artículo",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 140,
        },
        {
            "label": "Nombre",
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Cantidad",
            "fieldname": "qty",
            "fieldtype": "Float",
            "precision": 3,
            "width": 110,
        },
        {
            "label": "Monto",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130,
        },
        {
            "label": "Precio promedio",
            "fieldname": "average_price",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 140,
        },
        {
            "label": "% del total",
            "fieldname": "percent_of_total",
            "fieldtype": "Percent",
            "width": 110,
        },
        {
            "label": "Moneda",
            "fieldname": "currency",
            "fieldtype": "Data",
            "hidden": 1,
        },
    ]


def item_group_names(item_group):
    if not item_group:
        return []
    bounds = frappe.db.get_value(
        "Item Group", item_group, ["lft", "rgt"], as_dict=True
    )
    if not bounds:
        frappe.throw(
            _("El grupo de artículos {0} no existe").format(item_group)
        )
    if isinstance(bounds, dict):
        left = bounds.get("lft")
        right = bounds.get("rgt")
    else:
        left, right = bounds[0], bounds[1]
    if left is None or right is None:
        return [item_group]
    sql = (
        "SELECT name AS name FROM `tabItem Group` "
        "WHERE lft >= %(lft)s AND rgt <= %(rgt)s"
    )
    found = frappe.db.sql(
        sql, {"lft": left, "rgt": right}, as_dict=True
    ) or []
    names = [row.get("name") for row in found if row.get("name")]
    return names or [item_group]


def ranking_query(filters, item_groups):
    """Net submitted sales lines. Parameters are bound."""

    params = {
        "company": filters["company"],
        "from_date": filters["from_date"].isoformat(),
        "to_date": filters["to_date"].isoformat(),
    }
    where = [
        "si.docstatus = 1",
        "si.company = %(company)s",
        "si.posting_date BETWEEN %(from_date)s AND %(to_date)s",
        "IFNULL(sii.item_code, '') != ''",
    ]
    if filters.get("customer"):
        params["customer"] = filters["customer"]
        where.append("si.customer = %(customer)s")
    if item_groups:
        placeholders = bind_in(params, "item_group", item_groups)
        where.append("sii.item_group IN ({0})".format(placeholders))
    sql = (
        "SELECT sii.item_code AS item_code, "
        "MAX(sii.item_name) AS item_name, "
        "SUM(IFNULL(sii.qty, 0)) AS qty, "
        "SUM(IFNULL(sii.base_net_amount, 0)) AS amount "
        "FROM `tabSales Invoice Item` sii "
        "INNER JOIN `tabSales Invoice` si ON si.name = sii.parent "
        "WHERE {0} "
        "GROUP BY sii.item_code "
        "HAVING ABS(SUM(IFNULL(sii.qty, 0))) > 0.0000001 "
        "OR ABS(SUM(IFNULL(sii.base_net_amount, 0))) > 0.0000001"
    ).format(" AND ".join(where))
    return sql, params


def bind_in(params, prefix, values):
    keys = []
    for index, value in enumerate(values):
        key = "{0}_{1}".format(prefix, index)
        params[key] = value
        keys.append("%({0})s".format(key))
    return ", ".join(keys)


def build_ranking(raw_rows, rank_by):
    """Sort, average price, share of net amount, and a Total row."""

    prepared = []
    for row in raw_rows or []:
        code = row.get("item_code")
        if not code:
            continue
        qty = quantize(row.get("qty"), QTY_QUANT)
        amount = quantize(row.get("amount"), MONEY_QUANT)
        if abs(qty) <= ZERO_EPSILON and abs(amount) <= ZERO_EPSILON:
            continue
        if qty == 0:
            average = None
        else:
            average = (amount / qty).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )
        prepared.append({
            "item_code": code,
            "item_name": row.get("item_name") or code,
            "_qty": qty,
            "_amount": amount,
            "_average": average,
        })

    def sort_key(row):
        if rank_by == RANK_QTY:
            metric = row["_qty"]
        elif rank_by == RANK_PRICE:
            metric = row["_average"]
        else:
            metric = row["_amount"]
        if metric is None:
            return (1, Decimal("0"), row["item_code"])
        return (0, -metric, row["item_code"])

    prepared.sort(key=sort_key)
    total_amount = sum(
        (row["_amount"] for row in prepared), Decimal("0")
    )
    total_qty = sum((row["_qty"] for row in prepared), Decimal("0"))
    data = []
    for index, row in enumerate(prepared, start=1):
        data.append({
            "puesto": index,
            "item_code": row["item_code"],
            "item_name": row["item_name"],
            "qty": float(row["_qty"]),
            "amount": float(row["_amount"]),
            "average_price": (
                None if row["_average"] is None else float(row["_average"])
            ),
            "percent_of_total": percent_of(row["_amount"], total_amount),
        })
    if not data:
        return data
    if total_qty == 0:
        total_average = None
    else:
        total_average = (total_amount / total_qty).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
    data.append({
        "puesto": None,
        "item_code": "",
        "item_name": "Total",
        "qty": float(total_qty),
        "amount": float(total_amount),
        "average_price": (
            None if total_average is None else float(total_average)
        ),
        "percent_of_total": None if total_amount == 0 else 100.0,
    })
    return data


def build_chart(data, rank_by, top_n):
    rows = [row for row in data if row.get("item_code")][: int(top_n)]
    if not rows:
        return None
    labels = [row["item_code"] for row in rows]
    if rank_by == RANK_QTY:
        values = [row["qty"] for row in rows]
        fieldtype = "Float"
        name = "Cantidad"
    elif rank_by == RANK_PRICE:
        values = [row["average_price"] or 0 for row in rows]
        fieldtype = "Currency"
        name = "Precio promedio"
    else:
        values = [row["amount"] for row in rows]
        fieldtype = "Currency"
        name = "Monto"
    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": name, "values": values}],
        },
        "type": "bar",
        "colors": ["#112C5E"],
        "fieldtype": fieldtype,
    }


def percent_of(amount, total):
    if total == 0:
        return None
    ratio = (amount / total) * Decimal("100")
    return float(ratio.quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP))


def quantize(value, quant):
    if value is None or value == "":
        number = Decimal("0")
    else:
        number = Decimal(str(value))
    return number.quantize(quant, rounding=ROUND_HALF_UP)


def as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if len(text) < 10:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()
