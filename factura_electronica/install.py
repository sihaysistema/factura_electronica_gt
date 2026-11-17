# -*- coding: utf-8 -*-
"""Migrate hooks that must not ship as full-record fixtures.

UOM FEL codes used to live in fixtures/uom.json. Frappe deletes and
reinserts every JSON file in fixtures/ on migrate. Those rows had no
enabled key, so v15 stored enabled=0. The codes are applied here and
never change enabled on a UOM that already exists.

HRMS (Expense Claim Detail) and Healthcare (Identification Document Type)
are not installed on every site. Frappe skips an entire fixture file when
any DocType it names is missing, which would drop the FEL custom fields on
a site without HRMS. These records are applied only when that DocType exists.
"""

from __future__ import unicode_literals

import json
import os

import frappe

from factura_electronica.utils.uom_fel_codes import sync_uom_fel_codes

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

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


def doctype_installed(name, table_exists=None, exists=None):
    """True when this site actually has the DocType.

    Prefer ``frappe.db.exists('DocType', name)``. Also require the table
    when ``table_exists`` is available, so a DocType row without a table
    is not written.
    """
    if exists is None:
        exists = getattr(frappe.db, "exists", None)
    if table_exists is None:
        table_exists = getattr(frappe.db, "table_exists", None)
    has_row = None
    if exists:
        try:
            has_row = bool(exists("DocType", name))
        except Exception:
            has_row = None
    has_table = None
    if table_exists:
        try:
            has_table = bool(table_exists(name))
        except Exception:
            has_table = None
    if has_row is True:
        if has_table is False:
            return False
        return True
    if has_table is True and has_row is not False:
        return True
    return False


def optional_fixture_plan(table_exists, installed_apps=None, exists=None):
    """Decide which optional records this site can receive."""
    installed = {str(app).lower() for app in (installed_apps or [])}

    def ready(name):
        return doctype_installed(name, table_exists=table_exists, exists=exists)

    return {
        "expense_claim_detail": ready("Expense Claim Detail"),
        "identification_document_type": ready("Identification Document Type"),
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

    plan = optional_fixture_plan(
        getattr(frappe.db, "table_exists", None),
        installed,
        exists=getattr(frappe.db, "exists", None),
    )
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
    sync_uom_fel_codes()


def after_migrate():
    sync_optional_fixtures()
    sync_uom_fel_codes()
