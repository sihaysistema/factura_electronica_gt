# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Invoice rename helper. No Frappe site is required."""

from __future__ import unicode_literals

import sys
import types
import unittest


def _ensure_import_stubs():
    if "frappe" not in sys.modules:
        frappe = types.ModuleType("frappe")

        def whitelist(*args, **kwargs):
            if len(args) == 1 and callable(args[0]) and not kwargs:
                return args[0]

            def decorator(fn):
                return fn

            return decorator

        frappe.whitelist = whitelist
        sys.modules["frappe"] = frappe
    if "numinwords" not in sys.modules:
        numinwords = types.ModuleType("numinwords")
        numinwords.numinwords = lambda *args, **kwargs: ""
        sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

from factura_electronica.utils.rename_invoice import (  # noqa: E402
    build_rename_statements,
    scaled_item_wise_amounts,
)


def _guards(missing_tables=(), missing_columns=()):
    missing_tables = set(missing_tables)
    missing_columns = set(missing_columns)

    def table_exists(doctype):
        return doctype not in missing_tables

    def has_column(doctype, column):
        return (doctype, column) not in missing_columns

    return table_exists, has_column


def _sql_for(statements):
    return "\n".join(sql for sql, _params in statements)


class TestRenameInvoice(unittest.TestCase):
    def test_sales_invoice_covers_v16_tables(self):
        table_exists, has_column = _guards()
        statements = build_rename_statements(
            "ACC-SINV-2026-00001", "A1B2C3D41", "Sales Invoice", table_exists, has_column
        )
        sql = _sql_for(statements)
        for table in (
            "Sales Invoice Item",
            "Pricing Rule Detail",
            "Item Wise Tax Detail",
            "Tax Withholding Entry",
            "Advance Payment Ledger Entry",
            "Serial and Batch Bundle",
            "Serial and Batch Entry",
        ):
            self.assertIn("`tab{0}`".format(table), sql)
        self.assertIn("parenttype=%(link_doctype)s", sql)
        self.assertIn("voucher_type=%(link_doctype)s", sql)
        joined_params = [params["link_doctype"] for _sql, params in statements]
        self.assertTrue(all(value == "Sales Invoice" for value in joined_params))
        self.assertTrue(all(params["serieFa"] == "ACC-SINV-2026-00001" for _sql, params in statements))
        self.assertTrue(all(params["name"] == "A1B2C3D41" for _sql, params in statements))

    def test_missing_table_is_skipped(self):
        table_exists, has_column = _guards(missing_tables={"Item Wise Tax Detail", "Serial and Batch Entry"})
        sql = _sql_for(
            build_rename_statements("OLD", "NEW", "Sales Invoice", table_exists, has_column)
        )
        self.assertNotIn("Item Wise Tax Detail", sql)
        self.assertNotIn("Serial and Batch Entry", sql)
        self.assertIn("Pricing Rule Detail", sql)
        self.assertIn("Serial and Batch Bundle", sql)

    def test_missing_column_is_skipped(self):
        table_exists, has_column = _guards(
            missing_columns={("Serial and Batch Entry", "voucher_no")}
        )
        sql = _sql_for(
            build_rename_statements("OLD", "NEW", "Sales Invoice", table_exists, has_column)
        )
        self.assertNotIn("Serial and Batch Entry", sql)
        self.assertIn("Serial and Batch Bundle", sql)

    def test_purchase_invoice_uses_purchase_children(self):
        table_exists, has_column = _guards()
        sql = _sql_for(
            build_rename_statements("OLD", "NEW", "Purchase Invoice", table_exists, has_column)
        )
        self.assertIn("`tabPurchase Invoice Item`", sql)
        self.assertNotIn("`tabSales Invoice Item`", sql)
        self.assertIn("`tabItem Wise Tax Detail`", sql)
        item_wise = [sql for sql, params in build_rename_statements(
            "OLD", "NEW", "Purchase Invoice", table_exists, has_column
        ) if "Item Wise Tax Detail" in sql and "parent=" in sql]
        self.assertTrue(item_wise)
        self.assertIn("parenttype=%(link_doctype)s", item_wise[0])

    def test_scaled_amounts_keep_the_rewritten_total(self):
        scaled = scaled_item_wise_amounts([1, 3], 20)
        self.assertAlmostEqual(sum(scaled), 20)
        self.assertAlmostEqual(scaled[0], 5)
        self.assertAlmostEqual(scaled[1], 15)

    def test_scaled_amounts_put_the_total_on_the_first_empty_row(self):
        self.assertEqual(scaled_item_wise_amounts([0, 0], 8), [8.0, 0.0])
        self.assertEqual(scaled_item_wise_amounts([], 8), [])


if __name__ == "__main__":
    unittest.main()
