# -*- coding: utf-8 -*-
"""Receiver name for FEL NombreReceptor.

nombre_segun_sat is used only when it is a non-empty string. Otherwise
the invoice party name is used, then the Customer or Supplier master
name. The literal 'None' is never returned.
"""

from __future__ import unicode_literals


def clean_party_name(value):
    """Return a display name, or '' for None, blank, or the text None."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "none":
        return ""
    return text


def nombre_receptor(nombre_segun_sat=None, invoice_party_name=None, master_party_name=None):
    """Pick the first usable receiver name."""
    for candidate in (nombre_segun_sat, invoice_party_name, master_party_name):
        cleaned = clean_party_name(candidate)
        if cleaned:
            return cleaned
    return ""


def nombre_receptor_for_row(row):
    """Resolve NombreReceptor from an invoice row.

    Looks up Customer.customer_name or Supplier.supplier_name only when
    the SAT name and the invoice party name are both empty.
    """
    if not row:
        return ""
    sat_name = row.get("nombre_segun_sat")
    invoice_name = row.get("customer_name") or row.get("supplier_name")
    if nombre_receptor(sat_name, invoice_name):
        return nombre_receptor(sat_name, invoice_name)
    return nombre_receptor(None, None, _master_party_name(row))


def _master_party_name(row):
    try:
        import frappe
    except Exception:
        return None
    database = getattr(frappe, "db", None)
    if database is None or not hasattr(database, "get_value"):
        return None
    try:
        if row.get("customer"):
            return database.get_value("Customer", row.get("customer"), "customer_name")
        if row.get("supplier"):
            return database.get_value("Supplier", row.get("supplier"), "supplier_name")
    except Exception:
        return None
    return None
