# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Fuel purchase GL stays the ERPNext map. No Frappe site."""

from __future__ import unicode_literals

import sys
import types
import unittest


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
        frappe.db = types.SimpleNamespace()
        sys.modules["frappe"] = frappe
    if "numinwords" not in sys.modules:
        try:
            import numinwords  # noqa: F401
        except ImportError:
            numinwords = types.ModuleType("numinwords")
            numinwords.numinwords = lambda *args, **kwargs: ""
            sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

import frappe  # noqa: E402
from factura_electronica.controllers.gl_entry import (  # noqa: E402
    gl_is_balanced,
    item_expense_acct_excise_tax_gl_correction,
    purchase_gl_lines,
    tax_correction,
)


def _debit(lines, account):
    return sum(line["debit"] for line in lines if line["account"] == account)


class _Row(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _Doc(object):
    def __init__(self, items):
        self.items = items


class TestFuelGl(unittest.TestCase):
    def setUp(self):
        def forbid(*args, **kwargs):
            raise AssertionError("GL Entry was rewritten: {0}".format(args[:1]))

        frappe.db.sql = forbid
        frappe.log_error = forbid

    def _assert_left_alone(self, items, taxes):
        before = purchase_gl_lines(items, taxes)
        self.assertTrue(gl_is_balanced(before))
        doc = _Doc([_Row(**item) for item in items])
        self.assertIsNone(item_expense_acct_excise_tax_gl_correction(doc, "on_submit"))
        for item in doc.items:
            self.assertIsNone(tax_correction(item))
        after = purchase_gl_lines(items, taxes)
        self.assertEqual(after, before)
        self.assertTrue(gl_is_balanced(after))
        return after

    def test_single_fuel_line_keeps_the_item_amount(self):
        lines = self._assert_left_alone(
            [{
                "expense_account": "Gasto Combustible",
                "amount": 100,
                "facelec_p_is_fuel": 1,
                "facelec_p_gt_tax_net_fuel_amt": 80,
            }],
            [],
        )
        self.assertEqual(_debit(lines, "Gasto Combustible"), 100)
        self.assertEqual(lines[-1]["credit"], 100)

    def test_fuel_and_other_line_on_the_same_account_both_remain(self):
        lines = self._assert_left_alone(
            [
                {
                    "expense_account": "Gasto",
                    "amount": 40,
                    "facelec_p_is_fuel": 1,
                    "facelec_p_gt_tax_net_fuel_amt": 30,
                },
                {
                    "expense_account": "Gasto",
                    "amount": 60,
                    "facelec_p_is_fuel": 0,
                    "facelec_p_gt_tax_net_fuel_amt": 0,
                },
            ],
            [],
        )
        self.assertEqual(_debit(lines, "Gasto"), 100)
        self.assertEqual(lines[-1]["credit"], 100)

    def test_two_fuel_lines_are_summed(self):
        lines = self._assert_left_alone(
            [
                {
                    "expense_account": "Gasto",
                    "amount": 30,
                    "facelec_p_is_fuel": 1,
                    "facelec_p_gt_tax_net_fuel_amt": 25,
                },
                {
                    "expense_account": "Gasto",
                    "amount": 70,
                    "facelec_p_is_fuel": 1,
                    "facelec_p_gt_tax_net_fuel_amt": 55,
                },
            ],
            [],
        )
        self.assertEqual(_debit(lines, "Gasto"), 100)

    def test_zero_fuel_amount_does_not_zero_the_expense(self):
        lines = self._assert_left_alone(
            [{
                "expense_account": "Gasto",
                "amount": 50,
                "facelec_p_is_fuel": 1,
                "facelec_p_gt_tax_net_fuel_amt": 0,
            }],
            [],
        )
        self.assertEqual(_debit(lines, "Gasto"), 50)
        self.assertEqual(lines[-1]["credit"], 50)

    def test_idp_tax_row_stays_on_its_own_account(self):
        lines = self._assert_left_alone(
            [{
                "expense_account": "Gasto",
                "amount": 100,
                "facelec_p_is_fuel": 1,
                "facelec_p_gt_tax_net_fuel_amt": 89.29,
            }],
            [{"account": "IDP por pagar", "amount": 12}],
        )
        self.assertEqual(_debit(lines, "Gasto"), 100)
        self.assertEqual(_debit(lines, "IDP por pagar"), 12)
        self.assertEqual(lines[-1]["credit"], 112)

    def test_without_an_idp_row_there_is_no_idp_account(self):
        lines = self._assert_left_alone(
            [{
                "expense_account": "Gasto",
                "amount": 100,
                "facelec_p_is_fuel": 1,
                "facelec_p_gt_tax_net_fuel_amt": 89.29,
            }],
            [],
        )
        self.assertFalse(any(line["account"] == "IDP por pagar" for line in lines))
        self.assertEqual(_debit(lines, "Gasto"), 100)
        self.assertEqual(lines[-1]["credit"], 100)


if __name__ == "__main__":
    unittest.main()
