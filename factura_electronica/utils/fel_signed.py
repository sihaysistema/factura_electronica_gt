# -*- coding: utf-8 -*-
"""Optional post-sign hook and the retry guard for an already certified invoice.

Other apps register dotted paths under the hook key ``on_fel_signed``.
Nothing is called when that list is empty, and a hook that raises is logged
and does not roll back the certification that already finished.
"""

from __future__ import unicode_literals

import frappe

HOOK_KEY = "on_fel_signed"

# Child and link updates from the v15 upgrade_records SQL. They run only
# when a matching row exists. File.attached_to_name is not in this list:
# the v15 rename does not update the File table.
_SALES_LINKS = (
    ("Sales Invoice Item", "parent", "parent"),
    ("Sales Taxes and Charges", "parent", "parent"),
    ("Otros Impuestos Factura Electronica", "parent", "parent"),
    ("Payment Schedule", "parent", "parent"),
    ("Subscription", "reference_document", "reference_document"),
    ("Stock Ledger Entry", "voucher_no", "voucher_no"),
    ("Sales Invoice Timesheet", "parent", "parent"),
    ("Sales Team", "parent", "parent"),
    ("Packed Item", "parent", "parent"),
    ("Sales Invoice Advance", "parent", "parent"),
    ("Sales Invoice Payment", "parent", "parent"),
    ("Payment Entry Reference", "reference_name", "reference_name"),
    ("Sales Order", "parent", "parent"),
    ("Delivery Note", "parent", "parent"),
    ("Journal Entry Account", "reference_name", "reference_name"),
    ("Batch Invoices", "invoice", "invoice", ', electronic_invoice_status="Generated"'),
    ("Tax Retention Guatemala", "sales_invoice", "sales_invoice"),
    ("Invoice Declaration", "link_name", "link_name"),
    ("Repost Item Valuation", "voucher_no", "voucher_no"),
    ("Payment Ledger Entry", "voucher_no", "voucher_no"),
    ("Payment Ledger Entry", "against_voucher_no", "against_voucher_no"),
)

_PURCHASE_LINKS = (
    ("Purchase Invoice Item", "parent", "parent"),
    ("Purchase Taxes and Charges", "parent", "parent"),
    ("Otros Impuestos Factura Electronica", "parent", "parent"),
    ("Payment Schedule", "parent", "parent"),
    ("Subscription", "reference_document", "reference_document"),
    ("Stock Ledger Entry", "voucher_no", "voucher_no"),
    ("Purchase Invoice Timesheet", "parent", "parent"),
    ("Sales Team", "parent", "parent"),
    ("Packed Item", "parent", "parent"),
    ("Purchase Invoice Advance", "parent", "parent"),
    ("Purchase Invoice Payment", "parent", "parent"),
    ("Payment Entry Reference", "reference_name", "reference_name"),
    ("Journal Entry Account", "reference_name", "reference_name"),
    ("Sales Order", "parent", "parent"),
    ("Delivery Note", "parent", "parent"),
    ("Batch Invoices", "invoice", "invoice", ', electronic_invoice_status="Generated"'),
    ("Tax Retention Guatemala", "sales_invoice", "sales_invoice"),
    ("Invoice Declaration", "link_name", "link_name"),
    ("Repost Item Valuation", "voucher_no", "voucher_no"),
    ("Payment Ledger Entry", "voucher_no", "voucher_no"),
    ("Payment Ledger Entry", "against_voucher_no", "against_voucher_no"),
)


def iter_on_fel_signed():
    """Dotted paths from every app's ``on_fel_signed`` hook."""
    getter = getattr(frappe, "get_hooks", None)
    if not getter:
        return []
    try:
        raw = getter(HOOK_KEY) or []
    except Exception:
        return []
    paths = []
    for item in raw:
        if isinstance(item, (list, tuple)):
            paths.extend([path for path in item if path])
        elif item:
            paths.append(item)
    return paths


def _log_hook_error(path, exc):
    try:
        traceback = ""
        get_traceback = getattr(frappe, "get_traceback", None)
        if get_traceback:
            traceback = get_traceback()
        frappe.log_error(
            message="{0}\n{1}".format(exc, traceback),
            title="FEL on_fel_signed {0}".format(path),
        )
    except Exception:
        return


def notify_after_sign(old_name, uuid, doctype="Sales Invoice"):
    """Call ``on_fel_signed`` after rename has finished.

    Returns immediately when no hook is registered, without reading Envio FEL.
    """
    paths = iter_on_fel_signed()
    if not paths:
        return
    row = _envio_row({"name": uuid}) or _envio_row({"uuid": uuid})
    serie = row.get("serie") if row else None
    numero = row.get("numero") if row else None
    new_name = row.get("serie_para_factura") if row else None
    envio_fel = (row.get("name") if row else None) or uuid
    resolved_uuid = (row.get("uuid") if row else None) or uuid
    for path in paths:
        try:
            callback = frappe.get_attr(path)
            callback(
                doctype=doctype,
                old_name=old_name,
                new_name=new_name,
                uuid=resolved_uuid,
                serie=serie,
                numero=numero,
                envio_fel=envio_fel,
            )
        except Exception as exc:
            _log_hook_error(path, exc)


def assess_existing_envio(invoice_code, doctype="Sales Invoice"):
    """Return the same tuple ``check_invoice_records`` has always returned.

    ``(True, uuid)`` when ``serie_para_factura`` already matches.
    ``(True, "<uuid> (Envio FEL <name>)")`` when the original name was already
    certified, after trying to finish a rename that did not complete.
    ``(False, "A generar una nueva")`` when SAT may be called.
    """
    by_new_name = _envio_row({"serie_para_factura": invoice_code})
    if by_new_name:
        return True, str(by_new_name.get("uuid") or "")

    by_original = _envio_row({"serie_factura_original": invoice_code})
    if by_original:
        _finish_rename_if_incomplete(invoice_code, by_original, doctype)
        uuid = by_original.get("uuid") or ""
        envio_name = by_original.get("name") or uuid
        return True, "{0} (Envio FEL {1})".format(uuid, envio_name)

    return False, "A generar una nueva"


def gate_before_sat(invoice_code, certify, doctype="Sales Invoice"):
    """Run ``certify`` only when this name has no Envio FEL yet."""
    status = assess_existing_envio(invoice_code, doctype=doctype)
    if status[0]:
        return False, (
            "La factura se encuentra registrada como ya generada, puedes validar "
            "los detalles en Envios FEL, con codigo UUID {0}".format(status[1])
        )
    return certify()


def _envio_row(filters):
    database = getattr(frappe, "db", None)
    if database is None or not hasattr(database, "get_values"):
        return None
    try:
        if hasattr(database, "exists") and not database.exists("Envio FEL", filters):
            return None
    except Exception:
        return None
    try:
        rows = database.get_values(
            "Envio FEL",
            filters=filters,
            fieldname=[
                "name",
                "uuid",
                "serie",
                "numero",
                "serie_para_factura",
                "serie_factura_original",
            ],
            as_dict=1,
        )
    except Exception:
        return None
    if not rows:
        return None
    return rows[0]


def _target_name(serie, numero):
    return "{0}{1}".format(str(serie or "").replace("*", ""), numero or "")


def _document_doctype(old_name, preferred):
    database = frappe.db
    if preferred and database.exists(preferred, old_name):
        return preferred
    for candidate in ("Sales Invoice", "Purchase Invoice"):
        if candidate != preferred and database.exists(candidate, old_name):
            return candidate
    return None


def _table_present(table):
    checker = getattr(frappe.db, "table_exists", None)
    if checker is None:
        return True
    try:
        return bool(checker(table))
    except Exception:
        return False


def _finish_rename_if_incomplete(old_name, envio, doctype):
    new_name = _target_name(envio.get("serie"), envio.get("numero"))
    if not new_name or new_name == old_name:
        return
    try:
        current = _document_doctype(old_name, doctype)
        if current not in ("Sales Invoice", "Purchase Invoice"):
            return
        if frappe.db.exists(current, new_name):
            return
        params = {
            "name": new_name,
            "no_correcto": envio.get("uuid"),
            "serie_orig_correcta": old_name,
            "serieFa": old_name,
        }
        frappe.db.sql(
            """UPDATE `tab{doctype}`
               SET name=%(name)s,
                   numero_autorizacion_fel=%(no_correcto)s,
                   serie_original_del_documento=%(serie_orig_correcta)s
               WHERE name=%(serieFa)s
            """.format(doctype=current),
            params,
        )
        links = _SALES_LINKS if current == "Sales Invoice" else _PURCHASE_LINKS
        for spec in links:
            table, column, match_column = spec[0], spec[1], spec[2]
            extra = spec[3] if len(spec) > 3 else ""
            if not _table_present(table):
                continue
            if not frappe.db.exists(table, {match_column: old_name}):
                continue
            frappe.db.sql(
                "UPDATE `tab{table}` SET {column}=%(name)s{extra} WHERE {match}=%(serieFa)s".format(
                    table=table, column=column, extra=extra, match=match_column
                ),
                params,
            )
        if _table_present("GL Entry") and frappe.db.exists("GL Entry", {"voucher_no": old_name}):
            frappe.db.sql(
                """UPDATE `tabGL Entry` SET voucher_no=%(name)s, against_voucher=%(name)s
                   WHERE voucher_no=%(serieFa)s AND against_voucher=%(serieFa)s""",
                params,
            )
            frappe.db.sql(
                """UPDATE `tabGL Entry` SET voucher_no=%(name)s, docstatus=1
                   WHERE voucher_no=%(serieFa)s AND against_voucher IS NULL""",
                params,
            )
        commit = getattr(frappe.db, "commit", None)
        if commit:
            commit()
    except Exception as exc:
        _log_hook_error("finish_rename", exc)
