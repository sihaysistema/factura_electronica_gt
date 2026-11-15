# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""Unit tests for the SAT late-origin phrase (tipo 9, escenario 22).

No Frappe site is required.
"""

from __future__ import unicode_literals

import datetime
import sys
import types
import unittest


def _ensure_import_stubs():
    """The app package imports frappe and numinwords. These tests do not."""

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

from factura_electronica.utils.fel_frases import (  # noqa: E402
    ensure_late_origin_frase,
    needs_late_origin_frase,
)


class TestLateOriginFrase(unittest.TestCase):
    def test_exactly_two_calendar_months_does_not_add_the_phrase(self):
        self.assertFalse(needs_late_origin_frase("2026-03-15", "2026-01-15"))
        self.assertFalse(
            needs_late_origin_frase("2026-03-15T23:59:59-06:00", "2026-01-15")
        )

    def test_one_day_past_two_calendar_months_adds_the_phrase(self):
        self.assertTrue(needs_late_origin_frase("2026-03-16", "2026-01-15"))
        self.assertTrue(
            needs_late_origin_frase("2026-03-16T00:00:00-06:00", datetime.date(2026, 1, 15))
        )

    def test_december_31_lands_on_february_28_in_a_non_leap_year(self):
        self.assertFalse(needs_late_origin_frase("2026-02-28", "2025-12-31"))
        self.assertTrue(needs_late_origin_frase("2026-03-01", "2025-12-31"))

    def test_december_31_lands_on_february_29_in_a_leap_year(self):
        self.assertFalse(needs_late_origin_frase("2024-02-29", "2023-12-31"))
        self.assertTrue(needs_late_origin_frase("2024-03-01", "2023-12-31"))

    def test_january_31_lands_on_march_31(self):
        self.assertFalse(needs_late_origin_frase("2026-03-31", "2026-01-31"))
        self.assertTrue(needs_late_origin_frase("2026-04-01", "2026-01-31"))

    def test_utc_instant_uses_the_guatemala_calendar_date(self):
        # 2026-03-16 05:00 UTC is still 2026-03-15 in Guatemala (exactly 2 months).
        self.assertFalse(
            needs_late_origin_frase("2026-03-16T05:00:00+00:00", "2026-01-15")
        )
        # 06:00 UTC is 00:00 on 2026-03-16 in Guatemala (one day past).
        self.assertTrue(
            needs_late_origin_frase("2026-03-16T06:00:00+00:00", "2026-01-15")
        )

    def test_missing_dates_do_not_add_the_phrase(self):
        self.assertFalse(needs_late_origin_frase(None, "2026-01-15"))
        self.assertFalse(needs_late_origin_frase("2026-05-01", None))
        self.assertFalse(needs_late_origin_frase("not-a-date", "2026-01-15"))

    def test_configured_phrase_is_not_duplicated(self):
        single = {
            "dte:Frase": {
                "@CodigoEscenario": "22",
                "@TipoFrase": "9",
            }
        }
        kept = ensure_late_origin_frase(single, "2026-06-01", "2026-01-01")
        self.assertIs(kept, single)
        self.assertNotIsInstance(kept["dte:Frase"], list)

        several = {
            "dte:Frase": [
                {"@CodigoEscenario": "1", "@TipoFrase": "1"},
                {"@CodigoEscenario": "22", "@TipoFrase": "9"},
            ]
        }
        kept_list = ensure_late_origin_frase(several, "2026-06-01", "2026-01-01")
        self.assertEqual(len(kept_list["dte:Frase"]), 2)

    def test_other_phrases_stay_and_the_late_phrase_is_appended(self):
        original = {"dte:Frase": {"@CodigoEscenario": "1", "@TipoFrase": "1"}}
        updated = ensure_late_origin_frase(original, "2026-06-01", "2026-01-01")
        self.assertEqual(
            updated["dte:Frase"],
            [
                {"@CodigoEscenario": "1", "@TipoFrase": "1"},
                {"@CodigoEscenario": "22", "@TipoFrase": "9"},
            ],
        )

    def test_debit_note_without_phrases_gets_only_the_late_phrase(self):
        created = ensure_late_origin_frase(None, "2026-06-01", "2026-01-01")
        self.assertEqual(
            created,
            {"dte:Frase": {"@CodigoEscenario": "22", "@TipoFrase": "9"}},
        )
        self.assertIsNone(ensure_late_origin_frase(None, "2026-03-01", "2026-01-01"))


if __name__ == "__main__":
    unittest.main()
