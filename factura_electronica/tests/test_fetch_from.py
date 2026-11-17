# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Every fetch_from points at a field that exists.

App DocTypes and Custom Fields are read from this app. Link fields and
target fields that live on ERPNext or Frappe are checked against the
ERPNext v16 names verified for this test. A fetch whose link field or
target doctype is not in either set is reported as unresolved instead of
failed.
"""

from __future__ import unicode_literals

import json
import os
import unittest

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ERPNext v16 Link fields used as the left side of fetch_from.
# (parent doctype, link fieldname) -> linked doctype.
_CORE_LINKS = {
    ("Item", "stock_uom"): "UOM",
    ("Sales Invoice", "customer"): "Customer",
    ("Sales Invoice Item", "item_code"): "Item",
    ("Sales Invoice Item", "uom"): "UOM",
    ("Purchase Invoice", "supplier"): "Supplier",
    ("Purchase Invoice Item", "item_code"): "Item",
    ("Purchase Order", "supplier"): "Supplier",
    ("Purchase Order Item", "item_code"): "Item",
    ("Supplier Quotation", "supplier"): "Supplier",
    ("Supplier Quotation Item", "item_code"): "Item",
    ("Purchase Receipt", "supplier"): "Supplier",
    ("Purchase Receipt Item", "item_code"): "Item",
    ("Sales Order", "customer"): "Customer",
    ("Sales Order Item", "item_code"): "Item",
    ("Delivery Note", "customer"): "Customer",
    ("Delivery Note Item", "item_code"): "Item",
    ("Quotation Item", "item_code"): "Item",
}

# ERPNext v16 fields used as the right side of fetch_from.
_CORE_FIELDS = {
    ("Company", "tax_id"),
}


def _load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _app_doctype_fields():
    """fieldname -> {fieldtype, options} for each app DocType."""
    found = {}
    doctype_root = os.path.join(_APP_ROOT, "factura_electronica", "doctype")
    for folder in os.listdir(doctype_root):
        path = os.path.join(doctype_root, folder, folder + ".json")
        if not os.path.exists(path):
            continue
        data = _load_json(path)
        if data.get("doctype") != "DocType":
            continue
        fields = {}
        for row in data.get("fields") or []:
            fields[row.get("fieldname")] = {
                "fieldtype": row.get("fieldtype"),
                "options": row.get("options"),
            }
        found[data.get("name")] = fields
    return found


def _custom_fields():
    rows = _load_json(os.path.join(_APP_ROOT, "fixtures", "custom_field.json"))
    by_dt = {}
    for row in rows:
        by_dt.setdefault(row.get("dt"), {})[row.get("fieldname")] = {
            "fieldtype": row.get("fieldtype"),
            "options": row.get("options"),
        }
    return rows, by_dt


def _fields_on(doctype, app_doctypes, custom_by_dt):
    fields = {}
    fields.update(app_doctypes.get(doctype) or {})
    fields.update(custom_by_dt.get(doctype) or {})
    return fields


def _iter_fetch_from(custom_rows):
    for row in custom_rows:
        source = row.get("fetch_from")
        if source:
            yield {
                "where": row.get("name"),
                "parent": row.get("dt"),
                "fieldname": row.get("fieldname"),
                "fetch_from": source,
            }
    doctype_root = os.path.join(_APP_ROOT, "factura_electronica", "doctype")
    for folder in os.listdir(doctype_root):
        path = os.path.join(doctype_root, folder, folder + ".json")
        if not os.path.exists(path):
            continue
        data = _load_json(path)
        if data.get("doctype") != "DocType":
            continue
        for row in data.get("fields") or []:
            source = row.get("fetch_from")
            if source:
                yield {
                    "where": data.get("name") + "." + row.get("fieldname"),
                    "parent": data.get("name"),
                    "fieldname": row.get("fieldname"),
                    "fetch_from": source,
                }


def classify_fetch_from():
    """Return (missing, unresolved) for every fetch_from in fixtures and DocTypes."""
    app_doctypes = _app_doctype_fields()
    custom_rows, custom_by_dt = _custom_fields()
    missing = []
    unresolved = []
    for item in _iter_fetch_from(custom_rows):
        source = item["fetch_from"]
        if "." not in source:
            missing.append(dict(item, reason="fetch_from has no target field"))
            continue
        link_field, target_field = source.split(".", 1)
        parent_fields = _fields_on(item["parent"], app_doctypes, custom_by_dt)
        link = parent_fields.get(link_field)
        if link and link.get("fieldtype") == "Link" and link.get("options"):
            target_dt = link.get("options")
        elif (item["parent"], link_field) in _CORE_LINKS:
            target_dt = _CORE_LINKS[(item["parent"], link_field)]
        else:
            unresolved.append(dict(item, reason="link field is not in this app or the ERPNext v16 list"))
            continue
        target_fields = _fields_on(target_dt, app_doctypes, custom_by_dt)
        if target_field in target_fields or (target_dt, target_field) in _CORE_FIELDS:
            continue
        if target_dt not in app_doctypes and target_field not in target_fields:
            unresolved.append(dict(
                item,
                reason="target {0}.{1} is not in this app or the ERPNext v16 list".format(
                    target_dt, target_field
                ),
            ))
            continue
        missing.append(dict(
            item,
            reason="target {0}.{1} does not exist".format(target_dt, target_field),
        ))
    return missing, unresolved


class TestFetchFrom(unittest.TestCase):
    def test_resolved_fetch_from_targets_exist(self):
        missing, unresolved = classify_fetch_from()
        self.assertEqual(
            [(row["where"], row["fetch_from"], row["reason"]) for row in missing],
            [],
        )
        # Nothing in the current fixtures falls outside the app DocTypes
        # and the ERPNext v16 link/field list above.
        self.assertEqual(
            [(row["where"], row["fetch_from"], row["reason"]) for row in unresolved],
            [],
        )

    def test_consumable_record_type_does_not_fetch_a_missing_field(self):
        rows = _load_json(os.path.join(_APP_ROOT, "fixtures", "custom_field.json"))
        row = [item for item in rows if item.get("name") == "Sales Invoice-facelec_consumable_record_type"][0]
        self.assertIsNone(row.get("fetch_from"))
        self.assertEqual(row.get("fieldname"), "facelec_consumable_record_type")

    def test_quotation_nit_does_not_fetch_from_customer(self):
        rows = _load_json(os.path.join(_APP_ROOT, "fixtures", "custom_field.json"))
        row = [item for item in rows if item.get("name") == "Quotation-facelec_qt_nit"][0]
        self.assertIsNone(row.get("fetch_from"))
        self.assertEqual(row.get("fieldname"), "facelec_qt_nit")


if __name__ == "__main__":
    unittest.main()
