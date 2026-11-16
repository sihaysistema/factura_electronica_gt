# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""SAT receiver lookup on submit is optional and never changes customer_name."""

from __future__ import unicode_literals

import json
import sys
import types
import unittest
import urllib.error


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
        frappe.db = types.SimpleNamespace(
            get_value=lambda *args, **kwargs: 0,
            sql=lambda *args, **kwargs: [("key",)],
            set_value=lambda *args, **kwargs: None,
        )
        frappe.log_error = lambda *args, **kwargs: None
        sys.modules["frappe"] = frappe
    if "numinwords" not in sys.modules:
        numinwords = types.ModuleType("numinwords")
        numinwords.numinwords = lambda *args, **kwargs: ""
        sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

import frappe  # noqa: E402
import urllib.request  # noqa: E402
from factura_electronica.buscar_nit import buscar_nombre  # noqa: E402


class _Doc(object):
    def __init__(self):
        self.name = "ACC-SINV-0001"
        self.es_dpi = False
        self.es_pasaporte = False
        self.nit_face_customer = "1234567-8"
        self.customer_name = "Original Customer"


class _Response(object):
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestBuscarNit(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.writes = []
        self.errors = []
        self.enabled = 0

        def get_value(*args, **kwargs):
            return self.enabled

        def set_value(*args, **kwargs):
            self.writes.append(args)

        def log_error(*args, **kwargs):
            self.errors.append((args, kwargs))

        def urlopen(request, timeout=None):
            self.calls.append((request.full_url, timeout))
            if getattr(self, "raise_timeout", False):
                raise urllib.error.URLError("timed out")
            return _Response({"nombre": "NOMBRE SAT"})

        frappe.db.get_value = get_value
        frappe.db.sql = lambda *args, **kwargs: [("secret",)]
        frappe.db.set_value = set_value
        frappe.log_error = log_error
        self._original_urlopen = urllib.request.urlopen
        urllib.request.urlopen = urlopen

    def tearDown(self):
        urllib.request.urlopen = self._original_urlopen

    def test_off_does_not_call_the_service(self):
        self.enabled = 0
        doc = _Doc()
        self.assertIsNone(buscar_nombre(doc, "on_submit"))
        self.assertEqual(self.calls, [])
        self.assertEqual(self.writes, [])
        self.assertEqual(doc.customer_name, "Original Customer")

    def test_timeout_does_not_block_submit(self):
        self.enabled = 1
        self.raise_timeout = True
        doc = _Doc()
        self.assertIsNone(buscar_nombre(doc, "on_submit"))
        self.assertEqual(self.calls[0][1], 10)
        self.assertTrue(self.errors)
        self.assertEqual(self.writes, [])
        self.assertEqual(doc.customer_name, "Original Customer")

    def test_success_stores_the_sat_name_and_leaves_customer_name(self):
        self.enabled = 1
        doc = _Doc()
        result = buscar_nombre(doc, "on_submit")
        self.assertEqual(result["nombre"], "NOMBRE SAT")
        self.assertEqual(
            self.writes,
            [("Sales Invoice", "ACC-SINV-0001", "nombre_segun_sat", "NOMBRE SAT")],
        )
        self.assertEqual(doc.customer_name, "Original Customer")
        self.assertFalse(any("customer_name" in args for args in self.writes))


if __name__ == "__main__":
    unittest.main()
