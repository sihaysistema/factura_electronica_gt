# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""
Unit tests for factura_electronica.utils.fel_datetime

These tests mock frappe so they can run without a full bench when desired.
On a bench: bench --site <site> run-tests --module factura_electronica.tests.test_fel_datetime
"""

from __future__ import unicode_literals

import datetime
import sys
import types
import unittest
from unittest.mock import patch


def _ensure_frappe_stub():
    """Minimal frappe stub if not already importable (offline unit run)."""
    if "frappe" in sys.modules:
        return
    frappe = types.ModuleType("frappe")

    class _DB:
        @staticmethod
        def get_value(*args, **kwargs):
            return None

        @staticmethod
        def get_system_setting(*args, **kwargs):
            return "America/Guatemala"

    frappe.db = _DB()

    def _throw(message):
        raise Exception(message)

    frappe.throw = _throw
    frappe.log_error = lambda *args, **kwargs: None

    def whitelist(*args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]

        def decorator(fn):
            return fn

        return decorator

    frappe.whitelist = whitelist
    if "numinwords" not in sys.modules:
        numinwords = types.ModuleType("numinwords")
        numinwords.numinwords = lambda *args, **kwargs: ""
        sys.modules["numinwords"] = numinwords
    utils = types.ModuleType("frappe.utils")

    def get_time_zone():
        return "America/Guatemala"

    def now_datetime():
        return datetime.datetime(2026, 8, 7, 12, 0, 0)

    utils.get_time_zone = get_time_zone
    utils.now_datetime = now_datetime
    frappe.utils = utils
    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils


_ensure_frappe_stub()

from factura_electronica.utils.fel_datetime import (  # noqa: E402
    MODE_CREACION,
    MODE_PETICION,
    combine_posting_datetime,
    format_datetime_with_offset,
    get_fecha_hora_emision,
    get_fecha_hora_now,
    is_valid_fel_datetime,
)


class TestFelDatetimeFormat(unittest.TestCase):
    def test_guatemala_noon_ends_with_offset(self):
        dt = datetime.datetime(2026, 8, 7, 12, 0, 0)
        result = format_datetime_with_offset(dt, tz_name="America/Guatemala")
        self.assertTrue(result.endswith("-06:00"), result)
        self.assertEqual(result, "2026-08-07T12:00:00-06:00")

    def test_no_bare_naive_string(self):
        dt = datetime.datetime(2026, 8, 7, 12, 28, 41)
        result = format_datetime_with_offset(dt, tz_name="America/Guatemala")
        self.assertNotEqual(result, "2026-08-07T12:28:41")
        self.assertIn("-06:00", result)
        self.assertFalse(result.endswith("Z"))

    def test_is_valid_fel_datetime(self):
        self.assertTrue(is_valid_fel_datetime("2026-08-07T12:28:41-06:00"))
        self.assertFalse(is_valid_fel_datetime("2026-08-07T12:28:41"))
        self.assertFalse(is_valid_fel_datetime("2026-08-07T12:28:41Z"))
        self.assertFalse(is_valid_fel_datetime(""))

    def test_combine_posting_string_time(self):
        combined = combine_posting_datetime("2026-08-07", "08:37:29.123456")
        self.assertEqual(combined, datetime.datetime(2026, 8, 7, 8, 37, 29))

    def test_combine_posting_timedelta(self):
        combined = combine_posting_datetime(
            datetime.date(2026, 8, 7), datetime.timedelta(hours=14, minutes=5, seconds=6)
        )
        self.assertEqual(combined, datetime.datetime(2026, 8, 7, 14, 5, 6))

    def test_posting_mode_with_offset(self):
        combined = combine_posting_datetime("2026-08-07", "08:37:29")
        result = format_datetime_with_offset(combined, tz_name="America/Guatemala")
        self.assertEqual(result, "2026-08-07T08:37:29-06:00")


class TestFelDatetimeModes(unittest.TestCase):
    def _replace_get_value(self, fn):
        import factura_electronica.utils.fel_datetime as fel_datetime

        original = fel_datetime.frappe.db.get_value
        fel_datetime.frappe.db.get_value = fn
        return original

    def _restore_get_value(self, original):
        import factura_electronica.utils.fel_datetime as fel_datetime

        fel_datetime.frappe.db.get_value = original

    @patch("factura_electronica.utils.fel_datetime.now_datetime")
    def test_petition_mode_uses_now(self, mock_now):
        mock_now.return_value = datetime.datetime(2026, 8, 7, 12, 28, 41)
        original = self._replace_get_value(lambda *args, **kwargs: MODE_PETICION)
        try:
            result = get_fecha_hora_emision(
                config_name="CONFIG-TEST",
                invoice_name="SINV-001",
                tz_name="America/Guatemala",
            )
        finally:
            self._restore_get_value(original)
        self.assertEqual(result, "2026-08-07T12:28:41-06:00")
        self.assertTrue(is_valid_fel_datetime(result))

    def test_creation_mode_uses_posting(self):
        def fake_get_value(doctype, filters, field=None, **kwargs):
            fname = field
            if doctype == "Configuracion Factura Electronica":
                return MODE_CREACION
            if fname == "posting_date":
                return datetime.date(2026, 8, 7)
            if fname == "posting_time":
                return "09:15:30"
            return None

        original = self._replace_get_value(fake_get_value)
        try:
            result = get_fecha_hora_emision(
                config_name="CONFIG-TEST",
                invoice_name="SINV-001",
                doctype="Sales Invoice",
                tz_name="America/Guatemala",
            )
        finally:
            self._restore_get_value(original)
        self.assertEqual(result, "2026-08-07T09:15:30-06:00")

    @patch("factura_electronica.utils.fel_datetime.now_datetime")
    def test_force_mode_petition_ignores_invoice(self, mock_now):
        mock_now.return_value = datetime.datetime(2026, 8, 7, 15, 0, 0)
        result = get_fecha_hora_emision(
            config_name=None,
            invoice_name="SINV-001",
            mode=MODE_PETICION,
            tz_name="America/Guatemala",
        )
        self.assertEqual(result, "2026-08-07T15:00:00-06:00")

    @patch("factura_electronica.utils.fel_datetime.now_datetime")
    def test_get_fecha_hora_now(self, mock_now):
        mock_now.return_value = datetime.datetime(2026, 8, 7, 8, 37, 29)
        result = get_fecha_hora_now(tz_name="America/Guatemala")
        self.assertEqual(result, "2026-08-07T08:37:29-06:00")


if __name__ == "__main__":
    unittest.main()
