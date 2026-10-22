# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""Query and price-history tests for GT Item Price Cards.

History cases call ``build_cards`` with the rows Item Price and Version
would return. Filter cases run the report SQL on SQLite (same statement
the report sends to MariaDB) with a small catalog.
"""

from __future__ import unicode_literals

import json
import re
import sqlite3
import sys
import types
from datetime import date
from unittest import TestCase, main


def _ensure_import_stubs():
    if "frappe" in sys.modules and hasattr(sys.modules["frappe"], "throw"):
        return
    frappe = types.ModuleType("frappe")

    def _(text, *args, **kwargs):
        return text

    def throw(message, *args, **kwargs):
        raise ValueError(message)

    def whitelist(*args, **kwargs):
        def decorator(fn):
            return fn

        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorator

    frappe._ = _
    frappe.throw = throw
    frappe.whitelist = whitelist
    frappe.db = None
    frappe.defaults = types.SimpleNamespace(get_user_default=lambda key=None: None)
    utils = types.ModuleType("frappe.utils")
    utils.getdate = lambda value=None: date(2026, 10, 22)
    frappe.utils = utils
    numinwords = types.ModuleType("numinwords")
    numinwords.numinwords = lambda *args, **kwargs: ""
    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

from factura_electronica.factura_electronica.report.gt_item_price_cards import (  # noqa: E402
    gt_item_price_cards as price_report,
)

build_cards = price_report.build_cards
execute = price_report.execute
item_price_query = price_report.item_price_query
normalize_price_filters = price_report.normalize_price_filters


AS_OF = date(2026, 10, 22)


def price_row(**kwargs):
    row = {
        "name": "IP-1",
        "item_code": "ITEM-1",
        "item_name": "Item Uno",
        "item_group": "Productos",
        "stock_uom": "Nos",
        "uom": "Nos",
        "currency": "GTQ",
        "price_list_rate": 10,
        "valid_from": "2024-01-01",
        "valid_upto": None,
        "creation": "2024-01-01 08:00:00",
        "image": "/files/uno.jpg",
    }
    row.update(kwargs)
    return row


def version(docname, creation, changes, name=None):
    return {
        "name": name or "VER-{0}".format(creation),
        "docname": docname,
        "creation": creation,
        "data": json.dumps({"changed": changes}),
    }


def cards_for(*rows, versions=None, as_of=AS_OF, from_date=None):
    return build_cards(list(rows), versions or [], as_of, from_date)


class TestPriceHistory(TestCase):
    def test_version_edit_is_the_previous_price(self):
        rows = cards_for(
            price_row(price_list_rate=12),
            versions=[version("IP-1", "2025-06-15 09:00:00", [
                ["price_list_rate", 10, 12],
            ])],
        )
        self.assertEqual(len(rows), 1)
        card = rows[0]
        self.assertEqual(card["current_price"], 12.0)
        self.assertEqual(card["previous_price"], 10.0)
        self.assertEqual(card["change_date"], "2025-06-15")
        self.assertEqual(card["change_percent"], 20.0)
        self.assertEqual(card["image"], "/files/uno.jpg")
        self.assertEqual(card["uom"], "Nos")

    def test_later_version_is_ignored_before_its_date(self):
        rows = cards_for(
            price_row(price_list_rate=30),
            versions=[version("IP-1", "2026-12-01 09:00:00", [
                ["price_list_rate", 10, 30],
            ])],
        )
        card = rows[0]
        self.assertEqual(card["current_price"], 10.0)
        self.assertIsNone(card["previous_price"])
        self.assertIsNone(card["change_percent"])
        self.assertEqual(card["change_date"], "2024-01-01")

    def test_two_versions_keep_only_the_latest_change(self):
        rows = cards_for(
            price_row(price_list_rate=13),
            versions=[
                version("IP-1", "2024-06-01 09:00:00", [
                    ["price_list_rate", 10, 11],
                ]),
                version("IP-1", "2025-06-01 09:00:00", [
                    ["price_list_rate", 11, 13],
                ]),
            ],
        )
        card = rows[0]
        self.assertEqual(card["current_price"], 13.0)
        self.assertEqual(card["previous_price"], 11.0)
        self.assertEqual(card["change_date"], "2025-06-01")
        self.assertEqual(card["change_percent"], 18.18)

    def test_dated_rows_supersede_each_other(self):
        rows = cards_for(
            price_row(name="IP-A", price_list_rate=10, valid_from="2024-01-01"),
            price_row(
                name="IP-B",
                price_list_rate=8,
                valid_from="2025-01-01",
                creation="2025-01-01 08:00:00",
            ),
        )
        card = rows[0]
        self.assertEqual(card["current_price"], 8.0)
        self.assertEqual(card["previous_price"], 10.0)
        self.assertEqual(card["change_date"], "2025-01-01")
        self.assertEqual(card["change_percent"], -20.0)

    def test_expired_row_falls_back_to_the_older_price(self):
        rows = cards_for(
            price_row(
                name="IP-A",
                price_list_rate=10,
                valid_from="2020-01-01",
                creation="2020-01-01 08:00:00",
            ),
            price_row(
                name="IP-B",
                price_list_rate=12,
                valid_from="2024-01-01",
                valid_upto="2024-12-31",
                creation="2024-01-01 08:00:00",
            ),
            as_of=date(2025, 2, 1),
        )
        card = rows[0]
        self.assertEqual(card["current_price"], 10.0)
        self.assertEqual(card["previous_price"], 12.0)
        self.assertEqual(card["change_date"], "2025-01-01")
        self.assertEqual(card["change_percent"], -16.67)

    def test_backdated_valid_from_uses_that_business_date(self):
        rows = cards_for(
            price_row(price_list_rate=14, valid_from="2025-09-01"),
            versions=[version("IP-1", "2025-08-01 09:00:00", [
                ["price_list_rate", 10, 14],
                ["valid_from", "2024-01-01", "2025-09-01"],
            ])],
        )
        card = rows[0]
        self.assertEqual(card["current_price"], 14.0)
        self.assertEqual(card["previous_price"], 10.0)
        self.assertEqual(card["change_date"], "2025-09-01")

    def test_future_and_expired_rows_are_not_cards(self):
        self.assertEqual(cards_for(price_row(valid_from="2027-01-01")), [])
        self.assertEqual(
            cards_for(price_row(valid_from="2020-01-01", valid_upto="2021-01-01")),
            [],
        )

    def test_first_price_has_no_percent_and_from_date_filters_the_change(self):
        shown = cards_for(price_row(), from_date=date(2024, 1, 1))
        self.assertEqual(shown[0]["change_date"], "2024-01-01")
        self.assertIsNone(shown[0]["previous_price"])
        self.assertIsNone(shown[0]["change_percent"])
        hidden = cards_for(price_row(), from_date=date(2026, 3, 1))
        self.assertEqual(hidden, [])

    def test_zero_previous_price_has_no_percent(self):
        rows = cards_for(
            price_row(price_list_rate=10),
            versions=[version("IP-1", "2025-02-01 09:00:00", [
                ["price_list_rate", 0, 10],
            ])],
        )
        self.assertEqual(rows[0]["previous_price"], 0.0)
        self.assertEqual(rows[0]["current_price"], 10.0)
        self.assertIsNone(rows[0]["change_percent"])

    def test_stock_uom_is_preferred_over_another_uom(self):
        rows = cards_for(
            price_row(name="IP-NOS", uom="Nos", price_list_rate=10),
            price_row(
                name="IP-BOX",
                uom="Box",
                price_list_rate=100,
                creation="2024-02-01 08:00:00",
            ),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["current_price"], 10.0)
        self.assertEqual(rows[0]["uom"], "Nos")

    def test_other_uom_is_used_when_stock_uom_is_not_valid(self):
        rows = cards_for(
            price_row(
                name="IP-NOS",
                uom="Nos",
                price_list_rate=10,
                valid_upto="2024-12-31",
            ),
            price_row(
                name="IP-BOX",
                uom="Box",
                price_list_rate=100,
                valid_from="2025-01-01",
                creation="2025-01-01 08:00:00",
            ),
        )
        self.assertEqual(rows[0]["current_price"], 100.0)
        self.assertEqual(rows[0]["uom"], "Box")
        self.assertEqual(rows[0]["previous_price"], None)

    def test_blank_uom_counts_as_the_stock_uom(self):
        rows = cards_for(price_row(uom="", price_list_rate=7))
        self.assertEqual(rows[0]["uom"], "Nos")
        self.assertEqual(rows[0]["current_price"], 7.0)

    def test_corrupt_version_is_skipped(self):
        rows = cards_for(
            price_row(price_list_rate=12),
            versions=[
                {
                    "name": "BAD",
                    "docname": "IP-1",
                    "creation": "2025-01-01 00:00:00",
                    "data": "{not json",
                },
                version("IP-1", "2025-06-15 09:00:00", [
                    ["price_list_rate", 10, 12],
                ]),
            ],
        )
        self.assertEqual(rows[0]["current_price"], 12.0)
        self.assertEqual(rows[0]["previous_price"], 10.0)

    def test_biggest_move_is_sorted_first(self):
        rows = build_cards(
            [
                price_row(name="IP-A", item_code="A", item_name="Alfa", price_list_rate=10),
                price_row(
                    name="IP-B",
                    item_code="B",
                    item_name="Beta",
                    price_list_rate=15,
                    creation="2024-01-01 08:00:00",
                ),
            ],
            [
                version("IP-B", "2026-01-01 09:00:00", [
                    ["price_list_rate", 10, 15],
                ], name="VER-B"),
            ],
            AS_OF,
            None,
        )
        self.assertEqual([row["item_code"] for row in rows], ["B", "A"])
        self.assertEqual(rows[0]["change_percent"], 50.0)
        self.assertIsNone(rows[1]["change_percent"])


class TestPriceFilters(TestCase):
    def setUp(self):
        import frappe

        from factura_electronica.factura_electronica.report.gt_item_price_cards import (
            gt_item_price_cards as report,
        )

        self.report = report
        self._today = report.report_today
        report.report_today = lambda: AS_OF
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._schema()
        frappe.db = SqliteDB(self.conn)

    def tearDown(self):
        self.report.report_today = self._today
        self.conn.close()

    def _schema(self):
        self.conn.executescript(
            """
            CREATE TABLE `tabItem` (
                name TEXT, item_code TEXT, item_name TEXT, item_group TEXT,
                stock_uom TEXT, image TEXT, disabled INTEGER
            );
            CREATE TABLE `tabItem Price` (
                name TEXT, item_code TEXT, price_list TEXT,
                price_list_rate REAL, currency TEXT, uom TEXT,
                valid_from TEXT, valid_upto TEXT, customer TEXT,
                supplier TEXT, batch_no TEXT, creation TEXT
            );
            CREATE TABLE `tabItem Default` (
                parent TEXT, parenttype TEXT, company TEXT
            );
            CREATE TABLE `tabItem Group` (
                name TEXT, lft INTEGER, rgt INTEGER
            );
            CREATE TABLE `tabVersion` (
                name TEXT, ref_doctype TEXT, docname TEXT,
                data TEXT, creation TEXT
            );
            """
        )

    def _item(self, code, name, group="Productos", disabled=0, image=""):
        self.conn.execute(
            "INSERT INTO `tabItem` VALUES (?, ?, ?, ?, 'Nos', ?, ?)",
            (code, code, name, group, image, disabled),
        )

    def _price(self, name, code, rate=10, price_list="Venta GTQ", **extra):
        values = {
            "customer": "",
            "supplier": "",
            "batch_no": "",
            "uom": "Nos",
            "valid_from": "2024-01-01",
            "valid_upto": None,
            "creation": "2024-01-01 08:00:00",
            "currency": "GTQ",
        }
        values.update(extra)
        self.conn.execute(
            "INSERT INTO `tabItem Price` VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name, code, price_list, rate, values["currency"], values["uom"],
                values["valid_from"], values["valid_upto"], values["customer"],
                values["supplier"], values["batch_no"], values["creation"],
            ),
        )

    def test_sql_filters_party_batch_price_list_and_disabled(self):
        self._item("VISIBLE", "Visible")
        self._item("DISABLED", "Oculto", disabled=1)
        self._item("OTHER", "Otra lista")
        self._item("CLIENT", "Precio cliente")
        self._item("PROV", "Precio proveedor")
        self._item("LOTE", "Precio lote")
        self._price("IP-OK", "VISIBLE", rate=12)
        self._price("IP-OFF", "DISABLED", rate=99)
        self._price("IP-LIST", "OTHER", price_list="Compra GTQ")
        self._price("IP-CUS", "CLIENT", customer="CLI-1")
        self._price("IP-SUP", "PROV", supplier="PRO-1")
        self._price("IP-BAT", "LOTE", batch_no="LOTE-1")
        self.conn.execute(
            "INSERT INTO `tabVersion` VALUES (?, 'Note', 'IP-OK', '{}', ?)",
            ("VER-OTHER", "2025-01-01 00:00:00"),
        )
        _columns, data, message = execute({
            "price_list": "Venta GTQ",
            "to_date": "2026-10-22",
        })
        self.assertEqual([row["item_code"] for row in data], ["VISIBLE"])
        self.assertEqual(data[0]["current_price"], 12.0)
        self.assertIn("Item Price", message)
        self.assertIn("1 artículos", message)
        self.assertNotIn("batch_no", item_price_query(
            {"price_list": "Venta GTQ", "company": "", "search": ""},
            [],
            False,
        )[0])

    def test_company_keeps_global_items_and_that_companys_defaults(self):
        self._item("GLOBAL", "Global")
        self._item("MINE", "Mio")
        self._item("THEIRS", "Ajeno")
        self._item("BOTH", "Ambos")
        for code in ("GLOBAL", "MINE", "THEIRS", "BOTH"):
            self._price("IP-" + code, code)
        self.conn.executemany(
            "INSERT INTO `tabItem Default` VALUES (?, 'Item', ?)",
            [
                ("MINE", "Empresa GT"),
                ("THEIRS", "Otra"),
                ("BOTH", "Empresa GT"),
                ("BOTH", "Otra"),
            ],
        )
        _columns, data, _message = execute({
            "price_list": "Venta GTQ",
            "company": "Empresa GT",
            "to_date": "2026-10-22",
        })
        self.assertEqual(
            sorted(row["item_code"] for row in data),
            ["BOTH", "GLOBAL", "MINE"],
        )

    def test_search_and_item_group_include_children(self):
        self.conn.executemany(
            "INSERT INTO `tabItem Group` VALUES (?, ?, ?)",
            [("Todos", 1, 6), ("Bebidas", 2, 5), ("Jugos", 3, 4)],
        )
        self._item("JUGO", "100% Jugo", group="Jugos")
        self._item("AGUA", "Agua_Pura", group="Bebidas")
        self._item("PAN", "Pan", group="Todos")
        self._price("IP-JUGO", "JUGO")
        self._price("IP-AGUA", "AGUA")
        self._price("IP-PAN", "PAN")
        _columns, by_group, _message = execute({
            "price_list": "Venta GTQ",
            "item_group": "Bebidas",
            "to_date": "2026-10-22",
        })
        self.assertEqual(
            sorted(row["item_code"] for row in by_group),
            ["AGUA", "JUGO"],
        )
        _columns, by_search, _message = execute({
            "price_list": "Venta GTQ",
            "search": "100%",
            "to_date": "2026-10-22",
        })
        self.assertEqual([row["item_code"] for row in by_search], ["JUGO"])
        _columns, by_underscore, _message = execute({
            "price_list": "Venta GTQ",
            "search": "Agua_Pura",
            "to_date": "2026-10-22",
        })
        self.assertEqual([row["item_code"] for row in by_underscore], ["AGUA"])

    def test_execute_replays_version_rows(self):
        self._item("ITEM-1", "Item Uno", image="/files/uno.jpg")
        self._price("IP-1", "ITEM-1", rate=12)
        self.conn.execute(
            "INSERT INTO `tabVersion` VALUES (?, 'Item Price', ?, ?, ?)",
            (
                "VER-1",
                "IP-1",
                json.dumps({"changed": [["price_list_rate", 10, 12]]}),
                "2025-06-15 09:00:00",
            ),
        )
        _columns, data, _message = execute({
            "price_list": "Venta GTQ",
            "to_date": "2026-10-22",
        })
        self.assertEqual(data[0]["previous_price"], 10.0)
        self.assertEqual(data[0]["change_percent"], 20.0)
        self.assertEqual(data[0]["image"], "/files/uno.jpg")

    def test_invalid_filters_raise(self):
        with self.assertRaises(ValueError):
            normalize_price_filters({})
        with self.assertRaises(ValueError):
            normalize_price_filters({
                "price_list": "Venta GTQ",
                "from_date": "2026-12-01",
                "to_date": "2026-01-01",
            })
        with self.assertRaises(ValueError):
            execute({
                "price_list": "Venta GTQ",
                "item_group": "No existe",
            })


class SqliteDB(object):
    def __init__(self, conn):
        self.conn = conn

    def sql(self, query, params=None, as_dict=False, *args, **kwargs):
        converted = re.sub(r"%\((\w+)\)s", r":\1", query)
        cursor = self.conn.execute(converted, params or {})
        fetched = cursor.fetchall()
        if not as_dict:
            return [tuple(row) for row in fetched]
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in fetched]

    def get_value(self, doctype, name, fieldname, as_dict=False, **kwargs):
        table = "tab{0}".format(doctype)
        if isinstance(fieldname, (list, tuple)):
            columns = ", ".join(fieldname)
            row = self.conn.execute(
                "SELECT {0} FROM `{1}` WHERE name = ?".format(columns, table),
                (name,),
            ).fetchone()
            if row is None:
                return None
            if as_dict:
                return {field: row[index] for index, field in enumerate(fieldname)}
            return tuple(row)
        row = self.conn.execute(
            "SELECT {0} FROM `{1}` WHERE name = ?".format(fieldname, table),
            (name,),
        ).fetchone()
        if row is None:
            return None
        return row[0]

    def has_column(self, doctype, column):
        rows = self.conn.execute(
            "PRAGMA table_info('{0}')".format("tab" + doctype)
        ).fetchall()
        return any(row[1] == column for row in rows)


if __name__ == "__main__":
    main()
