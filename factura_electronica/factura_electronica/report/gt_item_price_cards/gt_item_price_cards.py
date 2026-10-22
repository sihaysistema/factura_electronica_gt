# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt

"""Tarjetas de precios GT.

Current and previous prices come only from Item Price. Sales Invoice rates
are not list prices: they include discounts and manual overrides, so they
are not used.

How the price on a card is chosen (same rules ERPNext uses in
``get_item_price`` for a general selling/buying rate):

* the selected price list only
* customer, supplier and batch Item Prices are excluded
* a row applies on the "Hasta" date when that date falls between
  ``valid_from`` (or 2000-01-01 when it is empty) and ``valid_upto``
  (or 2500-12-31 when it is empty)
* if several rows apply, the latest ``valid_from`` wins. An empty
  ``valid_from`` loses to a real date, which is how MySQL sorts
  ``ORDER BY valid_from DESC``
* one card per item. Rows in the item's stock UOM (blank UOM counts as
  the stock UOM) are preferred. Another UOM is used only when the stock
  UOM has no price on the as-of date. Packing-unit breaks are not
  separate cards

Previous price and the date of the last change:

* each Item Price row is replayed up to the as-of date. ``tabVersion``
  (``ref_doctype = 'Item Price'``) stores ``price_list_rate``,
  ``valid_from`` and ``valid_upto`` edits because Item Price has
  ``track_changes``. Versions dated after "Hasta" are undone, so a later
  edit does not leak into the card
* the applicable rate is evaluated on every date where a row starts,
  ends or is edited. The last change is the day the current rate became
  the applicable rate. The previous price is the last different
  applicable rate before that day. A gap with no price does not erase
  the previous rate
* "Desde" hides items whose last change is older than that date. Empty
  "Desde" shows every item with a price on "Hasta"
* the percent is ``(actual - anterior) / anterior * 100``. It is blank
  when there is no previous price or the previous price is 0.
  An increase is positive (green in the card view)

Company is not a field on Item Price in v13 or v15. The company filter
keeps items that have an Item Default for that company, plus items with
no Item Default (they are available to every company).

``ref_doctype`` is Sales Invoice. Frappe also requires report permission
on the reference DocType, and the roles that open GT Monthly Sales
History already have it on Sales Invoice. Item Price itself is limited
to Sales Master Manager and Purchase Master Manager.

Limits: deleted Version rows forget an edit of the same Item Price.
Disabled items are omitted. Search matches item code and item name.
"""

from __future__ import unicode_literals

import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

import frappe
from frappe import _
from frappe.utils import getdate

OPEN_START = date(2000, 1, 1)
OPEN_END = date(2500, 12, 31)
RATE_QUANT = Decimal("0.000001")
PERCENT_QUANT = Decimal("0.01")
TRACKED_FIELDS = ("price_list_rate", "valid_from", "valid_upto")


def execute(filters=None):
    """Script Report entry point. Returns columns, rows and a message."""

    filters = normalize_price_filters(filters)
    groups = item_group_names(filters.get("item_group"))
    include_batch = bool(frappe.db.has_column("Item Price", "batch_no"))
    sql, params = item_price_query(filters, groups, include_batch)
    rows = frappe.db.sql(sql, params, as_dict=True) or []
    names = [row.get("name") for row in rows if row.get("name")]
    versions = []
    if names:
        version_sql, version_params = version_query(names)
        versions = frappe.db.sql(version_sql, version_params, as_dict=True) or []
    data = build_cards(
        rows,
        versions,
        filters["to_date"],
        filters.get("from_date"),
    )
    message = price_message(
        len(data),
        filters["to_date"],
        filters.get("from_date"),
    )
    return get_columns(), data, message


def report_today():
    """Server date. Tests patch this instead of the clock."""

    today = getdate()
    return as_date(today) or date.today()


def normalize_price_filters(filters):
    raw = filters or {}
    if not isinstance(raw, dict):
        frappe.throw(_("Filtros inválidos"))

    price_list = clean_text(raw.get("price_list"))
    if not price_list:
        frappe.throw(_("Seleccione una lista de precios"))

    if raw.get("to_date") in (None, ""):
        to_date = report_today()
    else:
        to_date = as_date(raw.get("to_date"))
        if to_date is None:
            frappe.throw(_("Hasta no es una fecha válida"))

    from_date = None
    if raw.get("from_date") not in (None, ""):
        from_date = as_date(raw.get("from_date"))
        if from_date is None:
            frappe.throw(_("Desde no es una fecha válida"))
    if from_date and from_date > to_date:
        frappe.throw(_("Desde no puede ser posterior a Hasta"))

    return {
        "company": clean_text(raw.get("company")),
        "price_list": price_list,
        "item_group": clean_text(raw.get("item_group")),
        "search": clean_text(raw.get("search")),
        "from_date": from_date,
        "to_date": to_date,
    }


def price_message(count, as_of, from_date):
    text = _(
        "{0} artículos con precio vigente al {1}. "
        "El precio sale de Item Price (vigencia y cambios del documento). "
        "No se usa la tarifa de las facturas de venta."
    ).format(count, as_of.isoformat())
    if from_date:
        text += " " + _(
            "Solo cambios desde {0}."
        ).format(from_date.isoformat())
    return text


def get_columns():
    return [
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
            "label": "Grupo",
            "fieldname": "item_group",
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 140,
        },
        {
            "label": "UDM",
            "fieldname": "uom",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": "Precio actual",
            "fieldname": "current_price",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130,
        },
        {
            "label": "Último cambio",
            "fieldname": "change_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Precio anterior",
            "fieldname": "previous_price",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 140,
        },
        {
            "label": "Cambio %",
            "fieldname": "change_percent",
            "fieldtype": "Percent",
            "width": 100,
        },
        {
            "label": "Moneda",
            "fieldname": "currency",
            "fieldtype": "Data",
            "hidden": 1,
        },
        {
            "label": "Imagen",
            "fieldname": "image",
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
    sql, params = item_group_query(left, right)
    found = frappe.db.sql(sql, params, as_dict=True) or []
    names = [row.get("name") for row in found if row.get("name")]
    return names or [item_group]


def item_group_query(left, right):
    return (
        "SELECT name AS name FROM `tabItem Group` "
        "WHERE lft >= %(lft)s AND rgt <= %(rgt)s",
        {"lft": left, "rgt": right},
    )


def item_price_query(filters, item_groups, include_batch):
    """General Item Prices for the list. Parameters are bound."""

    params = {
        "price_list": filters["price_list"],
        "company": filters.get("company") or "",
    }
    where = [
        "ip.price_list = %(price_list)s",
        "IFNULL(ip.customer, '') = ''",
        "IFNULL(ip.supplier, '') = ''",
        "IFNULL(i.disabled, 0) = 0",
    ]
    if include_batch:
        where.append("IFNULL(ip.batch_no, '') = ''")
    if item_groups:
        placeholders = bind_in(params, "item_group", item_groups)
        where.append("i.item_group IN ({0})".format(placeholders))
    if filters.get("search"):
        params["search"] = like_contains(filters["search"])
        where.append(
            "(i.item_code LIKE %(search)s ESCAPE '!' "
            "OR i.item_name LIKE %(search)s ESCAPE '!')"
        )
    where.append(
        "("
        "%(company)s = '' "
        "OR NOT EXISTS ("
        "SELECT 1 FROM `tabItem Default` d "
        "WHERE d.parent = i.name "
        "AND IFNULL(d.parenttype, 'Item') = 'Item'"
        ") OR EXISTS ("
        "SELECT 1 FROM `tabItem Default` d "
        "WHERE d.parent = i.name "
        "AND IFNULL(d.parenttype, 'Item') = 'Item' "
        "AND d.company = %(company)s"
        "))"
    )
    sql = (
        "SELECT ip.name AS name, ip.item_code AS item_code, "
        "ip.price_list AS price_list, "
        "ip.price_list_rate AS price_list_rate, "
        "ip.currency AS currency, ip.uom AS uom, "
        "ip.valid_from AS valid_from, ip.valid_upto AS valid_upto, "
        "ip.creation AS creation, i.item_name AS item_name, "
        "i.item_group AS item_group, i.stock_uom AS stock_uom, "
        "IFNULL(i.image, '') AS image "
        "FROM `tabItem Price` ip "
        "INNER JOIN `tabItem` i ON i.name = ip.item_code "
        "WHERE {0} "
        "ORDER BY i.item_name ASC, ip.item_code ASC, ip.name ASC"
    ).format(" AND ".join(where))
    return sql, params


def version_query(names):
    params = {}
    placeholders = bind_in(params, "docname", names)
    sql = (
        "SELECT name AS name, docname AS docname, data AS data, "
        "creation AS creation FROM `tabVersion` "
        "WHERE ref_doctype = 'Item Price' "
        "AND docname IN ({0}) "
        "ORDER BY creation ASC, name ASC"
    ).format(placeholders)
    return sql, params


def bind_in(params, prefix, values):
    keys = []
    for index, value in enumerate(values):
        key = "{0}_{1}".format(prefix, index)
        params[key] = value
        keys.append("%({0})s".format(key))
    return ", ".join(keys)


def like_contains(text):
    """Substring LIKE pattern. '!' is the escape character."""

    escaped = (
        text.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    )
    return "%{0}%".format(escaped)


def build_cards(price_rows, version_rows, as_of, from_date=None):
    """One card per item that has a price on ``as_of``."""

    versions = versions_by_docname(version_rows)
    grouped = {}
    order = []
    for row in price_rows or []:
        code = row.get("item_code")
        if not code:
            continue
        if code not in grouped:
            grouped[code] = []
            order.append(code)
        grouped[code].append(row)

    cards = []
    for code in order:
        rows = grouped[code]
        sample = rows[0]
        snapshot = price_snapshot(rows, versions, as_of)
        if not snapshot:
            continue
        change_date = snapshot["change_date"]
        if from_date and (not change_date or change_date < from_date):
            continue
        current = snapshot["current_rate"]
        previous = snapshot["previous_rate"]
        cards.append({
            "item_code": code,
            "item_name": sample.get("item_name") or code,
            "item_group": sample.get("item_group") or "",
            "uom": snapshot["uom"] or sample.get("stock_uom") or "",
            "currency": snapshot["currency"] or "",
            "current_price": as_float(current),
            "previous_price": as_float(previous),
            "change_date": change_date.isoformat() if change_date else None,
            "change_percent": percent_change(current, previous),
            "image": sample.get("image") or "",
        })
    cards.sort(key=card_sort_key)
    return cards


def card_sort_key(card):
    percent = card.get("change_percent")
    name = card.get("item_name") or ""
    code = card.get("item_code") or ""
    if percent is None:
        return (1, 0.0, name, code)
    return (0, -abs(percent), name, code)


def price_snapshot(rows, versions_by_name, on_date):
    chosen = rows_for_history(rows, versions_by_name, on_date)
    if not chosen:
        return None
    current = applicable_state(chosen, versions_by_name, on_date)
    if not current:
        return None
    current_rate = current["rate"]
    change_date = None
    previous_rate = None
    seen = None
    for day in event_dates(chosen, versions_by_name, on_date):
        state = applicable_state(chosen, versions_by_name, day)
        value = None if state is None else state["rate"]
        if value is None:
            continue
        if seen is not None and not rates_differ(value, seen):
            continue
        if not rates_differ(value, current_rate):
            change_date = day
            previous_rate = seen
        seen = value
    if change_date is None:
        change_date = on_date
    uom = current["uom"] or (chosen[0].get("stock_uom") or "")
    return {
        "current_rate": current_rate,
        "previous_rate": previous_rate,
        "change_date": change_date,
        "uom": uom,
        "currency": current["currency"] or "",
    }


def rows_for_history(rows, versions_by_name, on_date):
    if not rows:
        return []
    stock_uom = rows[0].get("stock_uom") or ""
    preferred = family(rows, stock_uom, stock_uom)
    if preferred and applicable_state(preferred, versions_by_name, on_date):
        return preferred
    winner = applicable_state(rows, versions_by_name, on_date)
    if not winner:
        return []
    winner_uom = winner["uom"] or stock_uom
    return family(rows, stock_uom, winner_uom)


def family(rows, stock_uom, uom):
    wanted = uom or ""
    return [
        row for row in rows
        if normalized_uom(row, stock_uom) == wanted
    ]


def normalized_uom(row, stock_uom):
    uom = row.get("uom") or ""
    if not uom:
        return stock_uom or ""
    return uom


def applicable_state(rows, versions_by_name, on_date):
    found = []
    for row in rows:
        history = versions_by_name.get(row.get("name")) or []
        state = state_on(row, history, on_date)
        if state and in_window(state, on_date):
            found.append(state)
    if not found:
        return None

    def sort_key(state):
        valid_from = state["valid_from"] or date.min
        created = state["creation"] or date.min
        return (valid_from, created, state["name"] or "")

    return max(found, key=sort_key)


def state_on(row, versions, on_date):
    """Item Price field values as they were on ``on_date``."""

    created = as_date(row.get("creation"))
    if created and created > on_date:
        return None
    state = {
        "name": row.get("name"),
        "rate": as_rate(row.get("price_list_rate")),
        "valid_from": as_date(row.get("valid_from")),
        "valid_upto": as_date(row.get("valid_upto")),
        "uom": row.get("uom") or "",
        "currency": row.get("currency") or "",
        "creation": created,
    }
    dated = []
    for version in versions or []:
        if as_date(version.get("creation")):
            dated.append(version)
    for version in reversed(dated):
        for field, old, _new in parse_changes(version):
            if field in TRACKED_FIELDS:
                assign_field(state, field, old)
    for version in dated:
        version_date = as_date(version.get("creation"))
        if version_date > on_date:
            continue
        for field, _old, new in parse_changes(version):
            if field in TRACKED_FIELDS:
                assign_field(state, field, new)
    if state["rate"] is None:
        return None
    return state


def in_window(state, on_date):
    start = state["valid_from"] or OPEN_START
    end = state["valid_upto"] or OPEN_END
    return start <= on_date <= end


def event_dates(rows, versions_by_name, on_date):
    events = set([on_date])
    for row in rows:
        created = as_date(row.get("creation"))
        if created and created <= on_date:
            events.add(created)
        valid_from = as_date(row.get("valid_from"))
        if valid_from and valid_from <= on_date:
            events.add(valid_from)
        add_expiry(events, on_date, as_date(row.get("valid_upto")))
        history = versions_by_name.get(row.get("name")) or []
        for version in history:
            version_date = as_date(version.get("creation"))
            if version_date and version_date <= on_date:
                events.add(version_date)
            for field, old, new in parse_changes(version):
                if field not in ("valid_from", "valid_upto"):
                    continue
                for raw in (old, new):
                    parsed = as_date(raw)
                    if parsed and parsed <= on_date:
                        events.add(parsed)
                    if field == "valid_upto":
                        add_expiry(events, on_date, parsed)
    return sorted(events)


def add_expiry(events, on_date, valid_upto):
    if not valid_upto:
        return
    following = valid_upto + timedelta(days=1)
    if following <= on_date:
        events.add(following)


def assign_field(state, field, value):
    if field == "price_list_rate":
        state["rate"] = as_rate(value)
    elif field == "valid_from":
        state["valid_from"] = as_date(value)
    elif field == "valid_upto":
        state["valid_upto"] = as_date(value)


def parse_changes(version):
    data = version.get("data") if isinstance(version, dict) else None
    if isinstance(data, str):
        text = data.strip()
        if not text:
            return []
        try:
            data = json.loads(text)
        except ValueError:
            return []
    if not isinstance(data, dict):
        return []
    parsed = []
    for entry in data.get("changed") or []:
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            continue
        parsed.append((entry[0], entry[1], entry[2]))
    return parsed


def versions_by_docname(version_rows):
    grouped = {}
    for row in version_rows or []:
        grouped.setdefault(row.get("docname"), []).append(row)
    for name in grouped:
        grouped[name].sort(key=lambda row: (
            str(row.get("creation") or ""),
            str(row.get("name") or ""),
        ))
    return grouped


def percent_change(current, previous):
    if previous is None or not rates_differ(previous, Decimal("0")):
        return None
    if current is None:
        return None
    ratio = ((current - previous) / previous) * Decimal("100")
    return float(ratio.quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP))


def rates_differ(left, right):
    if left is None and right is None:
        return False
    if left is None or right is None:
        return True
    return left != right


def as_rate(value):
    if value is None or value == "":
        return None
    try:
        number = Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None
    return number.quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def as_float(number):
    if number is None:
        return None
    return float(number)


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
