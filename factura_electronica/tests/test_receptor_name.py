# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""NombreReceptor never becomes the literal None."""

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
        frappe.db = types.SimpleNamespace(get_value=lambda *args, **kwargs: None)
        sys.modules["frappe"] = frappe
    if "numinwords" not in sys.modules:
        numinwords = types.ModuleType("numinwords")
        numinwords.numinwords = lambda *args, **kwargs: ""
        sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

from factura_electronica.utils.receptor_name import (  # noqa: E402
    nombre_receptor,
    nombre_receptor_for_row,
)


class TestNombreReceptor(unittest.TestCase):
    def test_empty_none_and_whitespace_fall_back_to_the_invoice_name(self):
        self.assertEqual(nombre_receptor(None, "ACME SA"), "ACME SA")
        self.assertEqual(nombre_receptor("", "ACME SA"), "ACME SA")
        self.assertEqual(nombre_receptor("   ", "ACME SA"), "ACME SA")
        self.assertEqual(nombre_receptor("None", "ACME SA"), "ACME SA")
        self.assertEqual(nombre_receptor(" none ", "ACME SA"), "ACME SA")

    def test_filled_sat_name_wins(self):
        self.assertEqual(
            nombre_receptor("SAT NAME", "Invoice Name", "Master Name"),
            "SAT NAME",
        )

    def test_customer_master_is_the_last_fallback(self):
        self.assertEqual(nombre_receptor(None, None, "Master Name"), "Master Name")
        self.assertEqual(nombre_receptor("None", "None", "Master Name"), "Master Name")
        self.assertEqual(nombre_receptor(None, None, None), "")

    def test_row_uses_the_customer_record_when_the_invoice_name_is_empty(self):
        import frappe

        def get_value(doctype, name, field):
            self.assertEqual(doctype, "Customer")
            self.assertEqual(name, "CUST-1")
            self.assertEqual(field, "customer_name")
            return "Master SA"

        frappe.db.get_value = get_value
        row = {
            "nombre_segun_sat": None,
            "customer_name": " ",
            "customer": "CUST-1",
        }
        self.assertEqual(nombre_receptor_for_row(row), "Master SA")

    def test_row_does_not_emit_none_when_every_name_is_missing(self):
        import frappe

        frappe.db.get_value = lambda *args, **kwargs: None
        self.assertEqual(
            nombre_receptor_for_row({"nombre_segun_sat": None, "customer_name": None}),
            "",
        )
        self.assertNotIn("None", nombre_receptor_for_row({"nombre_segun_sat": None}))


if __name__ == "__main__":
    unittest.main()
