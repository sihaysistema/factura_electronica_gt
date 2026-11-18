# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Post-sign hooks and the already-certified retry guard. No Frappe site."""

from __future__ import unicode_literals

import os
import sys
import types
import unittest
from unittest.mock import patch

_MISSING = object()


def _ensure_import_stubs():
    try:
        import frappe  # noqa: F401
    except ImportError:
        frappe = types.ModuleType("frappe")

        def whitelist(*args, **kwargs):
            if len(args) == 1 and callable(args[0]) and not kwargs:
                return args[0]

            def decorator(fn):
                return fn

            return decorator

        frappe.whitelist = whitelist
        frappe._ = lambda message, *args, **kwargs: message
        frappe._dict = dict
        frappe.throw = lambda *args, **kwargs: (_ for _ in ()).throw(Exception(args[0] if args else ""))
        frappe.msgprint = lambda *args, **kwargs: None
        frappe.db = types.SimpleNamespace()
        frappe.get_hooks = lambda key=None: []
        frappe.log_error = lambda *args, **kwargs: None
        frappe.get_traceback = lambda: ""
        frappe.get_attr = lambda path: None
        sys.modules["frappe"] = frappe
    if "numinwords" not in sys.modules:
        try:
            import numinwords  # noqa: F401
        except ImportError:
            numinwords = types.ModuleType("numinwords")
            numinwords.numinwords = lambda *args, **kwargs: ""
            sys.modules["numinwords"] = numinwords


def _load_generate_electronic_invoice():
    import frappe as frappe_mod

    if not hasattr(frappe_mod, "__path__"):
        frappe_mod.__path__ = []
    utils = sys.modules.get("frappe.utils")
    if utils is None:
        utils = types.ModuleType("frappe.utils")
        utils.__path__ = []
        sys.modules["frappe.utils"] = utils
        frappe_mod.utils = utils
    for name in (
        "flt", "cint", "get_datetime", "nowdate", "nowtime",
        "now_datetime", "get_site_name", "now",
    ):
        if not hasattr(utils, name):
            setattr(utils, name, lambda *args, **kwargs: None)
    if "requests" not in sys.modules:
        requests = types.ModuleType("requests")
        requests.post = lambda *args, **kwargs: None
        sys.modules["requests"] = requests
    if "pandas" not in sys.modules:
        sys.modules["pandas"] = types.ModuleType("pandas")
    file_manager = sys.modules.get("frappe.utils.file_manager")
    if file_manager is None:
        file_manager = types.ModuleType("frappe.utils.file_manager")
        sys.modules["frappe.utils.file_manager"] = file_manager
        utils.file_manager = file_manager
    if not hasattr(file_manager, "save_file"):
        file_manager.save_file = lambda *args, **kwargs: None
    from factura_electronica.fel_api import generate_electronic_invoice

    return generate_electronic_invoice


def _patch_frappe(name, value):
    saved = frappe.__dict__.get(name, _MISSING)
    proxy = saved is not _MISSING and type(saved).__name__ == "LocalProxy"
    if proxy:
        frappe.__dict__[name] = None
    patcher = patch.object(frappe, name, value, create=(saved is _MISSING))
    patcher.start()

    def restore():
        patcher.stop()
        if proxy:
            frappe.__dict__[name] = saved

    return restore


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
        self.db = _DB([], [])
        self.addCleanup(_patch_frappe("log_error", lambda *args, **kwargs: self.errors.append((args, kwargs))))
        self.addCleanup(_patch_frappe("get_traceback", lambda: "trace"))
        self.addCleanup(_patch_frappe("get_hooks", lambda key=None: []))
        self.addCleanup(_patch_frappe("get_attr", lambda path: None))
        self.addCleanup(_patch_frappe("db", self.db))

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

    def _envio(self, name, serie, numero, new_name, original):
        return {
            "name": name,
            "uuid": name,
            "serie": serie,
            "numero": numero,
            "serie_para_factura": new_name,
            "serie_factura_original": original,
        }

    def test_unfinished_rename_calls_the_hook_once(self):
        calls = []

        def hook(**kwargs):
            calls.append(kwargs)

        frappe.get_hooks = lambda key=None: ["park_entry.fel.on_fel_signed"]
        frappe.get_attr = lambda path: hook
        frappe.db = _DB(
            [self._envio("UUID-9", "B*", "3", "B3", "ACC-SINV-9")],
            [("Sales Invoice", "ACC-SINV-9")],
        )

        first = assess_existing_envio("ACC-SINV-9")
        self.assertTrue(first[0])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["doctype"], "Sales Invoice")
        self.assertEqual(calls[0]["old_name"], "ACC-SINV-9")
        self.assertEqual(calls[0]["new_name"], "B3")
        self.assertEqual(calls[0]["uuid"], "UUID-9")
        self.assertEqual(calls[0]["serie"], "B*")
        self.assertEqual(calls[0]["numero"], "3")
        self.assertEqual(calls[0]["envio_fel"], "UUID-9")

    def test_finished_rename_does_not_notify_again(self):
        calls = []

        def hook(**kwargs):
            calls.append(kwargs)

        frappe.get_hooks = lambda key=None: ["park_entry.fel.on_fel_signed"]
        frappe.get_attr = lambda path: hook
        frappe.db = _DB(
            [self._envio("UUID-9", "B*", "3", "B3", "ACC-SINV-9")],
            [("Sales Invoice", "B3")],
        )

        by_new_name = assess_existing_envio("B3")
        by_old_name = assess_existing_envio("ACC-SINV-9")

        self.assertEqual(by_new_name, (True, "UUID-9"))
        self.assertTrue(by_old_name[0])
        self.assertEqual(calls, [])
        self.assertEqual(frappe.db.sqls, [])

    def test_hook_error_on_retry_still_reports_the_existing_envio(self):
        def explode(**kwargs):
            raise RuntimeError("park ticket failed")

        frappe.get_hooks = lambda key=None: ["park_entry.fel.on_fel_signed"]
        frappe.get_attr = lambda path: explode
        frappe.db = _DB(
            [self._envio("UUID-9", "B*", "3", "B3", "ACC-SINV-9")],
            [("Sales Invoice", "ACC-SINV-9")],
        )

        result = assess_existing_envio("ACC-SINV-9")
        self.assertTrue(result[0])
        self.assertIn("UUID-9", result[1])
        self.assertEqual(len(self.errors), 1)

    def test_old_name_after_a_full_sign_does_not_look_up_the_company(self):
        generate_electronic_invoice = _load_generate_electronic_invoice()
        companies = []
        frappe.db = _DB(
            [self._envio("UUID-9", "B*", "3", "B3", "ACC-SINV-9")],
            [("Sales Invoice", "B3")],
        )

        def company(doctype, name):
            companies.append((doctype, name))
            return None

        with patch("factura_electronica.fel_api._company_for", company):
            result = generate_electronic_invoice("ACC-SINV-9", "ACC-SINV-.YYYY.-")

        self.assertEqual(companies, [])
        self.assertFalse(result[0])
        self.assertIn("ya generada", result[1])
        self.assertIn("UUID-9", result[1])

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
