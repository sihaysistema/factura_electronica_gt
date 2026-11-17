# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Post-sign hooks and the already-certified retry guard. No Frappe site."""

from __future__ import unicode_literals

import os
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
        frappe.db = types.SimpleNamespace()
        frappe.get_hooks = lambda key=None: []
        frappe.log_error = lambda *args, **kwargs: None
        frappe.get_traceback = lambda: ""
        sys.modules["frappe"] = frappe
    if "numinwords" not in sys.modules:
        numinwords = types.ModuleType("numinwords")
        numinwords.numinwords = lambda *args, **kwargs: ""
        sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

import frappe  # noqa: E402
from factura_electronica.utils.fel_signed import (  # noqa: E402
    _PURCHASE_LINKS,
    _SALES_LINKS,
    assess_existing_envio,
    gate_before_sat,
    notify_after_sign,
)


class _DB(object):
    def __init__(self, envios, documents):
        self.envios = envios
        self.documents = set(documents)
        self.sqls = []
        self.commits = 0
        self.reads = 0

    def exists(self, doctype, name_or_filters):
        self.reads += 1
        if doctype == "Envio FEL":
            filters = name_or_filters or {}
            return any(self._match(row, filters) for row in self.envios)
        return (doctype, name_or_filters) in self.documents

    def get_values(self, doctype, filters=None, fieldname=None, as_dict=1):
        self.reads += 1
        return [row for row in self.envios if self._match(row, filters or {})]

    def sql(self, query, params=None):
        self.sqls.append((query, params))

    def commit(self):
        self.commits += 1

    def table_exists(self, doctype):
        return False

    def has_column(self, doctype, column):
        return False

    def _match(self, row, filters):
        return all(row.get(key) == value for key, value in filters.items())


class TestFelSigned(unittest.TestCase):
    def setUp(self):
        self.errors = []
        frappe.log_error = lambda *args, **kwargs: self.errors.append((args, kwargs))
        frappe.get_traceback = lambda: "trace"
        frappe.get_hooks = lambda key=None: []
        frappe.db = _DB([], [])

    def test_raising_hook_does_not_change_the_sign_result(self):
        def explode(**kwargs):
            raise RuntimeError("park ticket failed")

        frappe.get_hooks = lambda key=None: ["park_entry.fel.on_fel_signed"]
        frappe.get_attr = lambda path: explode
        frappe.db = _DB(
            [{
                "name": "UUID-1",
                "uuid": "UUID-1",
                "serie": "A*",
                "numero": "10",
                "serie_para_factura": "A10",
                "serie_factura_original": "ACC-SINV-1",
            }],
            [],
        )

        result = notify_after_sign("ACC-SINV-1", "UUID-1", doctype="Sales Invoice")

        self.assertIsNone(result)
        self.assertEqual(len(self.errors), 1)
        self.assertIn("park_entry.fel.on_fel_signed", self.errors[0][1]["title"])
        self.assertIn("park ticket failed", self.errors[0][1]["message"])

    def test_no_hooks_does_not_read_envio_fel(self):
        def forbid(*args, **kwargs):
            raise AssertionError("database used with no hooks")

        frappe.get_hooks = lambda key=None: []
        frappe.db.exists = forbid
        frappe.db.get_values = forbid

        first = notify_after_sign("ACC-SINV-1", "UUID-1")
        second = notify_after_sign("ACC-SINV-1", "UUID-1")

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(self.errors, [])

    def test_original_name_does_not_call_the_certifier(self):
        frappe.db = _DB(
            [{
                "name": "UUID-9",
                "uuid": "UUID-9",
                "serie": "B*",
                "numero": "3",
                "serie_para_factura": "B3",
                "serie_factura_original": "ACC-SINV-9",
            }],
            [("Sales Invoice", "ACC-SINV-9")],
        )
        called = []

        def certify():
            called.append("sat")
            return True, "should-not-run"

        result = gate_before_sat("ACC-SINV-9", certify)

        self.assertEqual(called, [])
        self.assertFalse(result[0])
        self.assertIn("UUID-9", result[1])
        self.assertIn("Envio FEL UUID-9", result[1])
        self.assertEqual(len(frappe.db.sqls), 1)
        self.assertEqual(frappe.db.sqls[0][1]["name"], "B3")
        self.assertEqual(frappe.db.sqls[0][1]["serieFa"], "ACC-SINV-9")
        self.assertEqual(frappe.db.sqls[0][1]["no_correcto"], "UUID-9")
        self.assertEqual(frappe.db.commits, 1)

    def test_new_name_guard_still_returns_only_the_uuid(self):
        frappe.db = _DB(
            [{
                "name": "UUID-2",
                "uuid": "UUID-2",
                "serie": "C",
                "numero": "1",
                "serie_para_factura": "C1",
                "serie_factura_original": "ACC-SINV-2",
            }],
            [],
        )

        status = assess_existing_envio("C1")

        self.assertEqual(status, (True, "UUID-2"))
        self.assertEqual(frappe.db.sqls, [])

    def test_missing_envio_allows_certification(self):
        called = []

        def certify():
            called.append("sat")
            return True, "UUID-NEW"

        result = gate_before_sat("ACC-SINV-NEW", certify)

        self.assertEqual(called, ["sat"])
        self.assertEqual(result, (True, "UUID-NEW"))

    def test_sql_rename_does_not_update_file_attached_to_name(self):
        """The v15 rename SQL leaves File.attached_to_name on the old name."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fel_dir = os.path.join(root, "fel")
        for name in sorted(os.listdir(fel_dir)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(fel_dir, name), "r", encoding="utf-8") as handle:
                source = handle.read()
            self.assertNotIn("attached_to_name", source, name)
            self.assertNotIn("tabFile", source, name)

        tables = [row[0] for row in list(_SALES_LINKS) + list(_PURCHASE_LINKS)]
        self.assertNotIn("File", tables)

        frappe.db = _DB(
            [{
                "name": "UUID-9",
                "uuid": "UUID-9",
                "serie": "B*",
                "numero": "3",
                "serie_para_factura": "B3",
                "serie_factura_original": "ACC-SINV-9",
            }],
            [("Sales Invoice", "ACC-SINV-9")],
        )
        gate_before_sat("ACC-SINV-9", lambda: (True, "should-not-run"))
        queries = "\n".join(query for query, _params in frappe.db.sqls)
        self.assertNotIn("File", queries)
        self.assertNotIn("attached_to_name", queries)
        self.assertIn("tabSales Invoice", queries)


if __name__ == "__main__":
    unittest.main()
