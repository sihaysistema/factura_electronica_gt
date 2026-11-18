# -*- coding: utf-8 -*-
"""Apply FEL unit codes without rewriting the UOM record.

The old fixtures/uom.json file held full UOM documents. Frappe imports every
JSON file in fixtures/ on migrate, deletes the existing row, and inserts the
file. Those rows had no enabled key, so v15 and v16 stored enabled=0 and
blocked invoices ("Unit of Measure Unidad is disabled").

Codes now live in data/uom_fel_codes.json. An existing UOM keeps enabled,
must_be_whole_number, and any code the site already set. Only an empty
faceleccodigo_unidad_de_medida is filled. A missing UOM is inserted with
enabled=1.
"""

from __future__ import unicode_literals

import json
import os

import frappe

CODE_FIELD = "faceleccodigo_unidad_de_medida"
_DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "uom_fel_codes.json",
)


def load_uom_fel_codes(path=None):
    with open(path or _DATA_FILE, encoding="utf-8") as handle:
        rows = json.load(handle)
    codes = []
    for row in rows:
        name = row.get("name")
        code = row.get(CODE_FIELD)
        if not name or code is None or str(code) == "":
            continue
        raw = str(code)
        stripped = raw.strip()
        if not stripped:
            continue
        codes.append({"name": name, CODE_FIELD: stripped, "raw_code": raw})
    return codes


def _blank(value):
    if value is None:
        return True
    return str(value).strip() == ""


def uom_code_field_ready():
    """True when the UOM table has the FEL code column."""
    database = frappe.db
    table_exists = getattr(database, "table_exists", None)
    if table_exists and not table_exists("UOM"):
        return False
    has_column = getattr(database, "has_column", None)
    if has_column:
        return bool(has_column("UOM", CODE_FIELD))
    get_meta = getattr(frappe, "get_meta", None)
    if not get_meta:
        return False
    meta = get_meta("UOM")
    getter = getattr(meta, "get_field", None)
    if not getter:
        return False
    return bool(getter(CODE_FIELD))


def sync_uom_fel_codes(rows=None):
    """Fill empty FEL codes. Does not change enabled or a code already set."""
    if not uom_code_field_ready():
        return {"skipped": True, "filled": 0, "kept": 0, "created": 0}

    filled = 0
    kept = 0
    created = 0
    for row in rows if rows is not None else load_uom_fel_codes():
        name = row.get("name")
        code = row.get(CODE_FIELD)
        if not name or code is None or str(code) == "":
            continue
        # The catalog file keeps SAT's leading spaces. The value written is
        # stripped. An existing row is rewritten only when it still holds
        # that exact space-prefixed catalog value.
        raw = str(row.get("raw_code") if row.get("raw_code") is not None else code)
        stripped = str(code).strip()
        if not stripped:
            continue
        if frappe.db.exists("UOM", name):
            current = frappe.db.get_value("UOM", name, CODE_FIELD)
            if _blank(current) or (raw != stripped and str(current) == raw):
                frappe.db.set_value(
                    "UOM",
                    name,
                    CODE_FIELD,
                    stripped,
                    update_modified=False,
                )
                filled += 1
            else:
                kept += 1
            continue
        doc = frappe.get_doc(
            {
                "doctype": "UOM",
                "uom_name": name,
                "enabled": 1,
                CODE_FIELD: stripped,
            }
        )
        doc.insert(ignore_permissions=True)
        created += 1
    return {"skipped": False, "filled": filled, "kept": kept, "created": created}
