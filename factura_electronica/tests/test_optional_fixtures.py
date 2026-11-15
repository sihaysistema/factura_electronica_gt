# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Optional fixture guard. No Frappe site is required."""

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

from factura_electronica.fixtures import fill_fixtures  # noqa: E402
from factura_electronica.install import (  # noqa: E402
    expense_claim_custom_fields,
    optional_fixture_plan,
    sync_optional_fixtures,
)

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _fixture_text():
    chunks = []

    def walk(node):
        if isinstance(node, dict):
            chunks.append(str(node.get("dt", "")))
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)
        else:
            chunks.append(str(node))

    walk(fill_fixtures())
    return "\n".join(chunks)


class TestOptionalFixtures(unittest.TestCase):
    def test_plain_fixtures_do_not_name_hrms_or_healthcare(self):
        text = _fixture_text()
        self.assertNotIn("Expense Claim Detail", text)
        self.assertNotIn("Identification Document Type", text)

    def test_custom_field_fixture_file_has_no_expense_claim_rows(self):
        path = os.path.join(_APP_ROOT, "fixtures", "custom_field.json")
        with open(path, encoding="utf-8") as handle:
            rows = json.loads(handle.read())
        doctypes = {row.get("dt") for row in rows}
        self.assertNotIn("Expense Claim Detail", doctypes)
        self.assertTrue(rows)

    def test_healthcare_fixture_is_not_in_the_fixtures_folder(self):
        self.assertFalse(
            os.path.exists(os.path.join(_APP_ROOT, "fixtures", "identification_document_type.json"))
        )
        moved = os.path.join(_APP_ROOT, "data", "identification_document_type.json")
        self.assertTrue(os.path.exists(moved))

    def test_plan_skips_missing_tables_even_if_the_app_is_installed(self):
        plan = optional_fixture_plan(lambda doctype: False, ["hrms", "healthcare"])
        self.assertFalse(plan["expense_claim_detail"])
        self.assertFalse(plan["identification_document_type"])
        self.assertTrue(plan["hrms_installed"])
        self.assertTrue(plan["healthcare_installed"])

    def test_plan_applies_when_the_table_exists_without_the_app(self):
        plan = optional_fixture_plan(
            lambda doctype: doctype == "Expense Claim Detail",
            [],
        )
        self.assertTrue(plan["expense_claim_detail"])
        self.assertFalse(plan["identification_document_type"])
        self.assertFalse(plan["hrms_installed"])

    def test_expense_claim_fields_keep_fieldname_and_fieldtype(self):
        fields = expense_claim_custom_fields()
        self.assertEqual(len(fields), 16)
        for field in fields:
            self.assertTrue(field.get("fieldname"))
            self.assertTrue(field.get("fieldtype"))
            self.assertNotIn("name", field)
            self.assertNotIn("modified", field)

    def test_sync_does_not_create_fields_when_tables_are_missing(self):
        import frappe

        created = []

        def fail_import(*args, **kwargs):
            created.append("imported")

        frappe.db.table_exists = lambda doctype: False
        frappe.get_installed_apps = lambda: ["hrms", "healthcare"]
        custom = types.ModuleType("frappe.custom.doctype.custom_field.custom_field")
        custom.create_custom_fields = fail_import
        sys.modules["frappe.custom.doctype.custom_field.custom_field"] = custom
        sync_optional_fixtures()
        self.assertEqual(created, [])


if __name__ == "__main__":
    unittest.main()
