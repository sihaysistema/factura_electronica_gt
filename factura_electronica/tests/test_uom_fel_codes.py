# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""UOM FEL codes stay off the fixture sync path. No Frappe site is required."""

from __future__ import unicode_literals

import json
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
        frappe.get_installed_apps = lambda: []
        sys.modules["frappe"] = frappe
    if "numinwords" not in sys.modules:
        numinwords = types.ModuleType("numinwords")
        numinwords.numinwords = lambda *args, **kwargs: ""
        sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

import frappe  # noqa: E402
import factura_electronica.install as install  # noqa: E402
from factura_electronica.fixtures import fill_fixtures  # noqa: E402
from factura_electronica.utils.uom_fel_codes import (  # noqa: E402
    CODE_FIELD,
    load_uom_fel_codes,
    sync_uom_fel_codes,
)

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CATALOG = [
    {"name": "Unidad", CODE_FIELD: "UNI"},
    {"name": "Galon", CODE_FIELD: "GAL"},
    {"name": "Caja", CODE_FIELD: "CAJ"},
]


class _Store(object):
    def __init__(self, rows, column=True):
        self.rows = rows
        self.column = column
        self.set_calls = []
        self.inserts = []

    def table_exists(self, doctype):
        return doctype == "UOM"

    def has_column(self, doctype, field):
        return self.column and doctype == "UOM" and field == CODE_FIELD

    def exists(self, doctype, name):
        return doctype == "UOM" and name in self.rows

    def get_value(self, doctype, name, field):
        return self.rows[name].get(field)

    def set_value(self, doctype, name, field, value, update_modified=True):
        self.set_calls.append(
            {
                "doctype": doctype,
                "name": name,
                "field": field,
                "value": value,
                "update_modified": update_modified,
            }
        )
        self.rows[name][field] = value


class _Doc(object):
    def __init__(self, payload):
        self.payload = dict(payload)

    def insert(self, ignore_permissions=False):
        frappe.db.inserts.append(self.payload)
        frappe.db.rows[self.payload["uom_name"]] = {
            "enabled": self.payload.get("enabled"),
            CODE_FIELD: self.payload.get(CODE_FIELD),
            "must_be_whole_number": self.payload.get("must_be_whole_number"),
        }


class TestUomFelCodes(unittest.TestCase):
    def setUp(self):
        self.store = _Store(
            {
                "Unidad": {
                    "enabled": 0,
                    CODE_FIELD: None,
                    "must_be_whole_number": 1,
                },
                "Galon": {
                    "enabled": 1,
                    CODE_FIELD: "SITE",
                    "must_be_whole_number": 0,
                },
            }
        )
        frappe.db = self.store
        frappe.get_doc = lambda payload: _Doc(payload)

    def test_existing_disabled_uom_keeps_enabled_and_gains_an_empty_code(self):
        result = sync_uom_fel_codes(_CATALOG)
        self.assertEqual(result["filled"], 1)
        self.assertEqual(self.store.rows["Unidad"]["enabled"], 0)
        self.assertEqual(self.store.rows["Unidad"]["must_be_whole_number"], 1)
        self.assertEqual(self.store.rows["Unidad"][CODE_FIELD], "UNI")
        self.assertEqual(len(self.store.set_calls), 1)
        call = self.store.set_calls[0]
        self.assertEqual(call["name"], "Unidad")
        self.assertEqual(call["field"], CODE_FIELD)
        self.assertEqual(call["value"], "UNI")
        self.assertFalse(call["update_modified"])

    def test_existing_enabled_uom_keeps_enabled_and_its_code(self):
        sync_uom_fel_codes(_CATALOG)
        self.assertEqual(self.store.rows["Galon"]["enabled"], 1)
        self.assertEqual(self.store.rows["Galon"][CODE_FIELD], "SITE")
        self.assertEqual(self.store.rows["Galon"]["must_be_whole_number"], 0)
        written = [call["name"] for call in self.store.set_calls]
        self.assertNotIn("Galon", written)

    def test_whitespace_code_is_empty_and_a_spaced_catalog_code_is_kept(self):
        self.store.rows["Unidad"][CODE_FIELD] = "   "
        self.store.rows["Galon"][CODE_FIELD] = " GAL"
        sync_uom_fel_codes(_CATALOG)
        self.assertEqual(self.store.rows["Unidad"][CODE_FIELD], "UNI")
        self.assertEqual(self.store.rows["Galon"][CODE_FIELD], " GAL")

    def test_missing_uom_is_created_enabled(self):
        result = sync_uom_fel_codes(_CATALOG)
        self.assertEqual(result["created"], 1)
        self.assertEqual(len(self.store.inserts), 1)
        created = self.store.inserts[0]
        self.assertEqual(created["doctype"], "UOM")
        self.assertEqual(created["uom_name"], "Caja")
        self.assertEqual(created["enabled"], 1)
        self.assertEqual(created[CODE_FIELD], "CAJ")
        self.assertNotIn("must_be_whole_number", created)
        self.assertEqual(self.store.rows["Caja"]["enabled"], 1)

    def test_second_run_does_not_write_again(self):
        first = sync_uom_fel_codes(_CATALOG)
        writes = len(self.store.set_calls)
        inserts = len(self.store.inserts)
        second = sync_uom_fel_codes(_CATALOG)
        self.assertEqual(first["filled"], 1)
        self.assertEqual(first["created"], 1)
        self.assertEqual(second["filled"], 0)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["kept"], 3)
        self.assertEqual(len(self.store.set_calls), writes)
        self.assertEqual(len(self.store.inserts), inserts)
        self.assertEqual(self.store.rows["Unidad"]["enabled"], 0)
        self.assertEqual(self.store.rows["Galon"]["enabled"], 1)
        self.assertEqual(self.store.rows["Caja"]["enabled"], 1)

    def test_missing_code_column_does_not_write(self):
        self.store.column = False
        result = sync_uom_fel_codes(_CATALOG)
        self.assertTrue(result["skipped"])
        self.assertEqual(self.store.set_calls, [])
        self.assertEqual(self.store.inserts, [])
        self.assertIsNone(self.store.rows["Unidad"][CODE_FIELD])
        self.assertEqual(self.store.rows["Unidad"]["enabled"], 0)

    def test_after_migrate_runs_the_sync(self):
        result = {}

        def record(rows=None):
            result["rows"] = rows
            return {"skipped": False, "filled": 0, "kept": 0, "created": 0}

        original = install.sync_uom_fel_codes
        install.sync_uom_fel_codes = record
        try:
            install.after_migrate()
        finally:
            install.sync_uom_fel_codes = original
        self.assertIsNone(result["rows"])

    def test_uom_is_not_a_fixture(self):
        doctypes = []
        for entry in fill_fixtures():
            if isinstance(entry, dict):
                doctypes.append(entry.get("dt") or entry.get("doctype"))
            else:
                doctypes.append(entry)
        self.assertNotIn("UOM", doctypes)
        self.assertFalse(os.path.exists(os.path.join(_APP_ROOT, "fixtures", "uom.json")))

    def test_data_file_keeps_only_name_and_code(self):
        path = os.path.join(_APP_ROOT, "data", "uom_fel_codes.json")
        with open(path, encoding="utf-8") as handle:
            rows = json.load(handle)
        self.assertEqual(len(rows), 186)
        by_name = {}
        for row in rows:
            self.assertEqual(set(row), {"name", CODE_FIELD})
            by_name[row["name"]] = row[CODE_FIELD]
        self.assertEqual(by_name["Box"], " CJ")
        self.assertEqual(by_name["Unidad"], "UNI")
        self.assertEqual(by_name["Galón"], "GAL")
        self.assertEqual(by_name["Caja"], "CJ")
        self.assertEqual(by_name["Bolsa"], "BLS")
        loaded = load_uom_fel_codes(path)
        self.assertEqual(len(loaded), 186)
        self.assertEqual(loaded[0][CODE_FIELD], " CJ")


if __name__ == "__main__":
    unittest.main()
