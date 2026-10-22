# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""Query tests for GT Sales Item Ranking.

``execute`` runs the report SQL on SQLite. The statement is the one the
report sends to MariaDB: submitted invoices, returns netted, company,
customer, dates and item group.
"""

from __future__ import unicode_literals

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
    frappe.defaults = types.SimpleNamespace(
        get_user_default=lambda key=None: "Empresa GT"
    )
    utils = types.ModuleType("frappe.utils")
    utils.getdate = lambda value=None: date(2026, 10, 22)
    frappe.utils = utils
    numinwords = types.ModuleType("numinwords")
    numinwords.numinwords = lambda *args, **kwargs: ""
    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

from factura_electronica.factura_electronica.report.gt_sales_item_ranking import (  # noqa: E402
    gt_sales_item_ranking as ranking_report,
)

build_chart = ranking_report.build_chart
build_ranking = ranking_report.build_ranking
execute = ranking_report.execute
normalize_ranking_filters = ranking_report.normalize_ranking_filters


class TestSalesItemRanking(TestCase):
    def setUp(self):
        import frappe

        from factura_electronica.factura_electronica.report.gt_sales_item_ranking import (
            gt_sales_item_ranking as report,
        )

        self.report = report
        self._today = report.report_today
        report.report_today = lambda: date(2026, 10, 22)
        self.defaults = {"Company": "Empresa GT"}

        def get_user_default(key=None):
            return self.defaults.get(key)

        frappe.defaults.get_user_default = get_user_default
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE `tabCompany` (
                name TEXT, default_currency TEXT
            );
            CREATE TABLE `tabItem Group` (
                name TEXT, lft INTEGER, rgt INTEGER
            );
            CREATE TABLE `tabSales Invoice` (
                name TEXT, docstatus INTEGER, company TEXT,
                customer TEXT, posting_date TEXT
            );
            CREATE TABLE `tabSales Invoice Item` (
                name TEXT, parent TEXT, item_code TEXT, item_name TEXT,
                item_group TEXT, qty REAL, base_net_amount REAL
            );
            """
        )
        self.conn.execute(
            "INSERT INTO `tabCompany` VALUES ('Empresa GT', 'GTQ')"
        )
        self.conn.executemany(
            "INSERT INTO `tabItem Group` VALUES (?, ?, ?)",
            [("Todos", 1, 4), ("Bebidas", 2, 3)],
        )
        frappe.db = SqliteDB(self.conn)

    def tearDown(self):
        self.report.report_today = self._today
        self.conn.close()

    def _invoice(self, name, company, customer, posting_date, docstatus, lines):
        self.conn.execute(
            "INSERT INTO `tabSales Invoice` VALUES (?, ?, ?, ?, ?)",
            (name, docstatus, company, customer, posting_date),
        )
        for index, line in enumerate(lines):
            self.conn.execute(
                "INSERT INTO `tabSales Invoice Item` VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "{0}-{1}".format(name, index),
                    name,
                    line["item_code"],
                    line.get("item_name") or line["item_code"],
                    line.get("item_group") or "Todos",
                    line["qty"],
                    line["amount"],
                ),
            )

    def _seed_net_sales(self):
        self._invoice("INV-1", "Empresa GT", "CLI-1", "2026-03-01", 1, [
            {"item_code": "AGUA", "item_name": "Agua", "item_group": "Bebidas",
             "qty": 10, "amount": 100},
            {"item_code": "PAN", "item_name": "Pan", "qty": 5, "amount": 250},
        ])
        self._invoice("RET-1", "Empresa GT", "CLI-1", "2026-03-02", 1, [
            {"item_code": "AGUA", "item_name": "Agua", "item_group": "Bebidas",
             "qty": -2, "amount": -20},
        ])
        self._invoice("DRAFT", "Empresa GT", "CLI-1", "2026-03-01", 0, [
            {"item_code": "AGUA", "qty": 100, "amount": 1000},
        ])
        self._invoice("CANCEL", "Empresa GT", "CLI-1", "2026-03-01", 2, [
            {"item_code": "PAN", "qty": 100, "amount": 1000},
        ])
        self._invoice("OTHER", "Otra Empresa", "CLI-1", "2026-03-01", 1, [
            {"item_code": "PAN", "qty": 9, "amount": 900},
        ])
        self._invoice("OLD", "Empresa GT", "CLI-1", "2025-12-31", 1, [
            {"item_code": "PAN", "qty": 4, "amount": 40},
        ])
        self._invoice("EDGE", "Empresa GT", "CLI-2", "2026-03-31", 1, [
            {"item_code": "PAN", "item_name": "Pan", "qty": 1, "amount": 10},
        ])
        self._invoice("NEXT", "Empresa GT", "CLI-1", "2026-04-01", 1, [
            {"item_code": "PAN", "qty": 8, "amount": 80},
        ])

    def test_returns_net_and_rank_by_amount_qty_and_price(self):
        self._seed_net_sales()
        filters = {
            "company": "Empresa GT",
            "from_date": "2026-03-01",
            "to_date": "2026-03-31",
            "rank_by": "Monto",
            "chart_top": "10",
        }
        columns, data, message, chart = execute(filters)
        items = [row for row in data if row["item_code"]]
        self.assertEqual([row["item_code"] for row in items], ["PAN", "AGUA"])
        agua = items[1]
        pan = items[0]
        self.assertEqual(agua["qty"], 8.0)
        self.assertEqual(agua["amount"], 80.0)
        self.assertEqual(agua["average_price"], 10.0)
        self.assertEqual(agua["percent_of_total"], 23.53)
        self.assertEqual(pan["qty"], 6.0)
        self.assertEqual(pan["amount"], 260.0)
        self.assertEqual(pan["average_price"], 43.33)
        self.assertEqual(pan["percent_of_total"], 76.47)
        self.assertEqual(pan["puesto"], 1)
        self.assertEqual(data[-1]["item_name"], "Total")
        self.assertEqual(data[-1]["qty"], 14.0)
        self.assertEqual(data[-1]["amount"], 340.0)
        self.assertEqual(data[-1]["percent_of_total"], 100.0)
        self.assertEqual(data[-1]["currency"], "GTQ")
        self.assertEqual(chart["type"], "bar")
        self.assertEqual(chart["data"]["labels"], ["PAN", "AGUA"])
        self.assertEqual(chart["data"]["datasets"][0]["values"], [260.0, 80.0])
        self.assertNotIn("", chart["data"]["labels"])
        self.assertIn("sin impuestos", message)
        self.assertIn("GTQ", message)
        fieldnames = [column["fieldname"] for column in columns]
        for row in data:
            for fieldname in fieldnames:
                self.assertIn(fieldname, row)

        _columns, by_qty, _message, qty_chart = execute(dict(
            filters, rank_by="Cantidad"
        ))
        self.assertEqual(
            [row["item_code"] for row in by_qty if row["item_code"]],
            ["AGUA", "PAN"],
        )
        self.assertEqual(qty_chart["data"]["datasets"][0]["name"], "Cantidad")
        self.assertEqual(qty_chart["fieldtype"], "Float")

        _columns, by_price, _message, price_chart = execute(dict(
            filters, rank_by="Precio"
        ))
        self.assertEqual(
            [row["item_code"] for row in by_price if row["item_code"]],
            ["PAN", "AGUA"],
        )
        self.assertEqual(
            price_chart["data"]["datasets"][0]["name"], "Precio promedio"
        )

    def test_customer_item_group_and_chart_top(self):
        self._seed_net_sales()
        _columns, data, _message, _chart = execute({
            "company": "Empresa GT",
            "from_date": "2026-03-01",
            "to_date": "2026-03-31",
            "customer": "CLI-2",
            "rank_by": "Monto",
            "chart_top": 2,
        })
        self.assertEqual(
            [row["item_code"] for row in data if row["item_code"]],
            ["PAN"],
        )
        self.assertEqual(data[0]["amount"], 10.0)

        _columns, grouped, _message, _chart = execute({
            "company": "Empresa GT",
            "from_date": "2026-03-01",
            "to_date": "2026-03-31",
            "item_group": "Bebidas",
        })
        self.assertEqual(
            [row["item_code"] for row in grouped if row["item_code"]],
            ["AGUA"],
        )

        ranked = build_ranking([
            {"item_code": "C", "item_name": "C", "qty": 1, "amount": 30},
            {"item_code": "A", "item_name": "A", "qty": 1, "amount": 10},
            {"item_code": "B", "item_name": "B", "qty": 1, "amount": 20},
        ], "Monto")
        chart = build_chart(ranked, "Monto", 2)
        self.assertEqual(chart["data"]["labels"], ["C", "B"])
        self.assertEqual(len([row for row in ranked if row["item_code"]]), 3)

    def test_lines_for_one_item_sum_and_zero_qty_has_no_average(self):
        self._invoice("INV", "Empresa GT", "CLI-1", "2026-02-01", 1, [
            {"item_code": "A", "qty": 2, "amount": 20},
            {"item_code": "A", "qty": 3, "amount": 30},
            {"item_code": "B", "qty": 0, "amount": 5},
            {"item_code": "C", "qty": 1, "amount": 1},
            {"item_code": "", "qty": 4, "amount": 4},
        ])
        self._invoice("ZERO", "Empresa GT", "CLI-1", "2026-02-02", 1, [
            {"item_code": "D", "qty": 2, "amount": 8},
        ])
        self._invoice("ZERO-R", "Empresa GT", "CLI-1", "2026-02-03", 1, [
            {"item_code": "D", "qty": -2, "amount": -8},
        ])
        _columns, data, _message, _chart = execute({
            "company": "Empresa GT",
            "from_date": "2026-02-01",
            "to_date": "2026-02-28",
        })
        by_code = {row["item_code"]: row for row in data if row["item_code"]}
        self.assertEqual(by_code["A"]["qty"], 5.0)
        self.assertEqual(by_code["A"]["amount"], 50.0)
        self.assertEqual(by_code["A"]["average_price"], 10.0)
        self.assertEqual(by_code["B"]["qty"], 0.0)
        self.assertEqual(by_code["B"]["amount"], 5.0)
        self.assertIsNone(by_code["B"]["average_price"])
        self.assertIn("C", by_code)
        self.assertNotIn("D", by_code)
        self.assertNotIn("", by_code)

    def test_ties_break_by_item_code_and_negative_share_stays_signed(self):
        ranked = build_ranking([
            {"item_code": "B", "item_name": "B", "qty": 1, "amount": 100},
            {"item_code": "A", "item_name": "A", "qty": 1, "amount": 100},
            {"item_code": "C", "item_name": "C", "qty": -4, "amount": -40},
        ], "Monto")
        items = [row for row in ranked if row["item_code"]]
        self.assertEqual([row["item_code"] for row in items], ["A", "B", "C"])
        self.assertEqual(items[2]["percent_of_total"], -25.0)
        self.assertEqual(items[2]["average_price"], 10.0)
        self.assertEqual([row["puesto"] for row in items], [1, 2, 3])

    def test_default_dates_and_invalid_filters(self):
        self._invoice("IN", "Empresa GT", "CLI-1", "2026-01-01", 1, [
            {"item_code": "A", "qty": 1, "amount": 5},
        ])
        self._invoice("OUT", "Empresa GT", "CLI-1", "2026-10-23", 1, [
            {"item_code": "B", "qty": 1, "amount": 9},
        ])
        _columns, data, _message, _chart = execute({"company": "Empresa GT"})
        self.assertEqual(
            [row["item_code"] for row in data if row["item_code"]],
            ["A"],
        )
        normalized = normalize_ranking_filters({"company": "Empresa GT"})
        self.assertEqual(normalized["from_date"], date(2026, 1, 1))
        self.assertEqual(normalized["to_date"], date(2026, 10, 22))
        self.assertEqual(normalized["rank_by"], "Monto")
        self.assertEqual(normalized["chart_top"], 10)

        with self.assertRaises(ValueError):
            normalize_ranking_filters({
                "company": "Empresa GT",
                "rank_by": "Amount",
            })
        with self.assertRaises(ValueError):
            normalize_ranking_filters({
                "company": "Empresa GT",
                "from_date": "2026-05-01",
                "to_date": "2026-04-01",
            })
        with self.assertRaises(ValueError):
            normalize_ranking_filters({
                "company": "Empresa GT",
                "chart_top": 0,
            })
        self.defaults["Company"] = None
        with self.assertRaises(ValueError):
            normalize_ranking_filters({})
        with self.assertRaises(ValueError):
            execute({
                "company": "Empresa GT",
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
                return {
                    field: row[index] for index, field in enumerate(fieldname)
                }
            return tuple(row)
        row = self.conn.execute(
            "SELECT {0} FROM `{1}` WHERE name = ?".format(fieldname, table),
            (name,),
        ).fetchone()
        if row is None:
            return None
        return row[0]

    def has_column(self, doctype, column):
        return False


if __name__ == "__main__":
    main()
