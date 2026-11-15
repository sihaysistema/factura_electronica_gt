# -*- coding: utf-8 -*-
"""Optional fixtures that must not live in hooks.fixtures.

HRMS (Expense Claim Detail) and Healthcare (Identification Document Type)
are not installed on every site. Frappe skips an entire fixture file when
any DocType it names is missing, which would drop the FEL custom fields on
a site without HRMS. These records are applied from after_install and
after_migrate only when the target table exists.
"""

from __future__ import unicode_literals

import json
import os

import frappe

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Columns create_custom_fields forwards onto Custom Field. Fixture export
# keys such as name, owner and modified are left out.
_CUSTOM_FIELD_KEYS = (
    "fieldname",
    "label",
    "fieldtype",
    "options",
    "insert_after",
    "reqd",
    "read_only",
    "hidden",
    "default",
    "depends_on",
    "description",
    "allow_on_submit",
    "no_copy",
    "in_list_view",
    "translatable",
    "unique",
    "precision",
    "collapsible",
    "bold",
    "fetch_from",
    "fetch_if_empty",
    "mandatory_depends_on",
    "read_only_depends_on",
    "collapsible_depends_on",
    "print_hide",
    "print_hide_if_no_value",
    "report_hide",
    "permlevel",
    "allow_in_quick_entry",
    "in_preview",
    "in_standard_filter",
    "in_global_search",
    "non_negative",
    "search_index",
    "hide_border",
    "ignore_user_permissions",
)


def _load_json(filename):
    path = os.path.join(_DATA_DIR, filename)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def expense_claim_custom_fields():
    """Expense Claim Detail fields, shaped for create_custom_fields."""
    fields = []
    for row in _load_json("expense_claim_detail_fields.json"):
        field = {}
        for key in _CUSTOM_FIELD_KEYS:
            value = row.get(key)
            if value not in (None, ""):
                field[key] = value
        if field.get("fieldname") and field.get("fieldtype"):
            fields.append(field)
    return fields


def identification_document_rows():
    return _load_json("identification_document_type.json")


def optional_fixture_plan(table_exists, installed_apps=None):
    """Decide which optional records this site can receive.

    ``table_exists`` is ``frappe.db.table_exists``. ``installed_apps`` is
    ``frappe.get_installed_apps()``. A record is applied only when its
    DocType table exists. The installed-app list is accepted so a site that
    has HRMS or Healthcare is recognized, and so a missing table is never
    written just because the app name is present.
    """
    installed = {str(app).lower() for app in (installed_apps or [])}
    expense_table = bool(table_exists("Expense Claim Detail"))
    identification_table = bool(table_exists("Identification Document Type"))
    return {
        "expense_claim_detail": expense_table,
        "identification_document_type": identification_table,
        "hrms_installed": "hrms" in installed,
        "healthcare_installed": "healthcare" in installed,
    }


def _ensure_identification_documents():
    for row in identification_document_rows():
        name = row.get("name")
        if not name or frappe.db.exists("Identification Document Type", name):
            continue
        doc = frappe.get_doc(
            {
                "doctype": "Identification Document Type",
                "identification_document_type": row.get("identification_document_type") or name,
                "name": name,
            }
        )
        doc.insert(ignore_permissions=True)


def sync_optional_fixtures():
    """Create HRMS and Healthcare records when those DocTypes exist."""
    installed = []
    get_installed = getattr(frappe, "get_installed_apps", None)
    if get_installed:
        installed = get_installed() or []

    plan = optional_fixture_plan(frappe.db.table_exists, installed)
    if plan["expense_claim_detail"]:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

        create_custom_fields(
            {"Expense Claim Detail": expense_claim_custom_fields()},
            ignore_validate=True,
            update=True,
        )
    if plan["identification_document_type"]:
        _ensure_identification_documents()


def after_install():
    sync_optional_fixtures()


def after_migrate():
    sync_optional_fixtures()
