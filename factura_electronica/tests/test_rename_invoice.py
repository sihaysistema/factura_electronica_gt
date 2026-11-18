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

    def test_credit_note_ar_and_journal_payment_follow_the_new_name(self):
        table_exists, has_column = _guards()
        old = "FEL-TEMP-0001"
        new = "NCE64FSNCA001190000000154"
        statements = build_rename_statements(old, new, "Sales Invoice", table_exists, has_column)
        gl_sql = [sql for sql, _params in statements if "`tabGL Entry`" in sql]
        joined = "\n".join(gl_sql)
        self.assertNotIn("AND against_voucher=%(serieFa)s", joined)
        self.assertIn("SET voucher_no=%(name)s WHERE voucher_no=%(serieFa)s", joined)
        self.assertIn("against_voucher_type=%(link_doctype)s", joined)

        ple_against = [
            sql for sql, _params in statements
            if "`tabPayment Ledger Entry`" in sql and "against_voucher_no" in sql
        ]
        self.assertTrue(ple_against)
        self.assertIn("against_voucher_type=%(link_doctype)s", ple_against[0])
        self.assertNotIn("AND voucher_no", ple_against[0])

        gl = [
            {
                "voucher_type": "Sales Invoice",
                "voucher_no": old,
                "against_voucher": "FACT-ORIG",
                "against_voucher_type": "Sales Invoice",
                "account": "AR",
                "docstatus": 1,
            },
            {
                "voucher_type": "Sales Invoice",
                "voucher_no": old,
                "against_voucher": old,
                "against_voucher_type": "Sales Invoice",
                "account": "Income",
                "docstatus": 1,
            },
            {
                "voucher_type": "Journal Entry",
                "voucher_no": "PARTIDA-11270",
                "against_voucher": old,
                "against_voucher_type": "Sales Invoice",
                "account": "Debtors",
                "docstatus": 1,
            },
            {
                "voucher_type": "Journal Entry",
                "voucher_no": "PARTIDA-11270",
                "against_voucher": old,
                "against_voucher_type": "Purchase Invoice",
                "account": "Creditors",
                "docstatus": 1,
            },
        ]
        ple = [
            {
                "voucher_type": "Journal Entry",
                "voucher_no": "PARTIDA-11270",
                "against_voucher_no": old,
                "against_voucher_type": "Sales Invoice",
                "amount": 400,
            },
            {
                "voucher_type": "Journal Entry",
                "voucher_no": "PARTIDA-11270",
                "against_voucher_no": old,
                "against_voucher_type": "Purchase Invoice",
                "amount": 50,
            },
        ]
        _apply_rename(statements, gl, ple)

        ar = next(row for row in gl if row["account"] == "AR")
        self.assertEqual(ar["voucher_no"], new)
        self.assertEqual(ar["against_voucher"], "FACT-ORIG")
        income = next(row for row in gl if row["account"] == "Income")
        self.assertEqual(income["voucher_no"], new)
        self.assertEqual(income["against_voucher"], new)
        je_sales = next(row for row in gl if row["account"] == "Debtors")
        self.assertEqual(je_sales["voucher_no"], "PARTIDA-11270")
        self.assertEqual(je_sales["against_voucher"], new)
        je_purchase = next(row for row in gl if row["account"] == "Creditors")
        self.assertEqual(je_purchase["against_voucher"], old)

        sales_ple = next(row for row in ple if row["against_voucher_type"] == "Sales Invoice")
        self.assertEqual(sales_ple["against_voucher_no"], new)
        self.assertEqual(sales_ple["voucher_no"], "PARTIDA-11270")
        purchase_ple = next(row for row in ple if row["against_voucher_type"] == "Purchase Invoice")
        self.assertEqual(purchase_ple["against_voucher_no"], old)

        invoice_total = 1000
        paid = sum(
            row["amount"] for row in ple
            if row["against_voucher_no"] == new and row["against_voucher_type"] == "Sales Invoice"
        )
        self.assertEqual(invoice_total - paid, 600)
        self.assertFalse(any(row["against_voucher_no"] == old and row["against_voucher_type"] == "Sales Invoice" for row in ple))


def _apply_rename(statements, gl_rows, ple_rows):
    """Apply the generated updates to in-memory ledger rows."""
    for sql, params in statements:
        old = params["serieFa"]
        new = params["name"]
        doctype = params["link_doctype"]
        if "`tabGL Entry`" in sql and "SET voucher_no=%(name)s WHERE voucher_no=%(serieFa)s" in sql:
            for row in gl_rows:
                if row["voucher_no"] == old:
                    row["voucher_no"] = new
        elif "`tabGL Entry`" in sql and "SET against_voucher=%(name)s" in sql:
            for row in gl_rows:
                if row["against_voucher"] == old and row.get("against_voucher_type") == doctype:
                    row["against_voucher"] = new
        elif "`tabPayment Ledger Entry`" in sql and "SET voucher_no=%(name)s" in sql:
            for row in ple_rows:
                if row["voucher_no"] == old:
                    row["voucher_no"] = new
        elif "`tabPayment Ledger Entry`" in sql and "SET against_voucher_no=%(name)s" in sql:
            for row in ple_rows:
                if row["against_voucher_no"] == old and row.get("against_voucher_type") == doctype:
                    row["against_voucher_no"] = new


if __name__ == "__main__":
    unittest.main()
