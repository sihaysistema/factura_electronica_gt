# -*- coding: utf-8 -*-
"""Rename rows that still point at an invoice after FEL certification.

Several FEL flows replace the Sales Invoice or Purchase Invoice name with
the SAT series plus DTE number. The child-table and ledger updates used to
be copied in each flow, and the copies omitted tables added in ERPNext 16
plus a few tables version 15 already had. This helper is the single list.

Every statement is skipped when ``table_exists`` or ``has_column`` says the
schema does not have that table or column, so the same code runs on older
sites.
"""

from __future__ import unicode_literals

# Child tables of Sales Invoice on ERPNext 16, plus the custom FEL child
# and the child tables the previous rename already updated.
SALES_CHILD_TABLES = (
    "Sales Invoice Item",
    "Sales Taxes and Charges",
    "Otros Impuestos Factura Electronica",
    "Payment Schedule",
    "Sales Invoice Timesheet",
    "Sales Team",
    "Packed Item",
    "Sales Invoice Advance",
    "Sales Invoice Payment",
    "Pricing Rule Detail",
    "Item Wise Tax Detail",
    "Tax Withholding Entry",
)

PURCHASE_CHILD_TABLES = (
    "Purchase Invoice Item",
    "Purchase Taxes and Charges",
    "Otros Impuestos Factura Electronica",
    "Payment Schedule",
    "Purchase Invoice Timesheet",
    "Sales Team",
    "Packed Item",
    "Purchase Invoice Advance",
    "Purchase Invoice Payment",
    "Pricing Rule Detail",
    "Item Wise Tax Detail",
    "Tax Withholding Entry",
)

# The previous rename updated parent on these DocTypes when a row matched.
# They are not invoice children. The statements stay so that behavior is
# not dropped, and parenttype is applied when the column exists.
LEGACY_PARENT_TABLES = (
    "Sales Order",
    "Delivery Note",
)

# (table, column to set, column to match, optional type column)
# Type columns are applied only for tables the old SQL did not update.
# Payment Ledger Entry keeps the previous untyped match.
_VOUCHER_LINKS = (
    ("Stock Ledger Entry", "voucher_no", "voucher_no", None),
    ("Repost Item Valuation", "voucher_no", "voucher_no", None),
    # Own rows of this voucher, then every allocation that points at it.
    # The two Payment Ledger updates stay separate: a return's AR row has
    # voucher_no = the note and against_voucher_no = the original invoice.
    ("Payment Ledger Entry", "voucher_no", "voucher_no", None),
    ("Payment Ledger Entry", "against_voucher_no", "against_voucher_no", "against_voucher_type"),
    ("Advance Payment Ledger Entry", "voucher_no", "voucher_no", "voucher_type"),
    ("Advance Payment Ledger Entry", "against_voucher_no", "against_voucher_no", "against_voucher_type"),
    ("Serial and Batch Bundle", "voucher_no", "voucher_no", "voucher_type"),
    ("Serial and Batch Entry", "voucher_no", "voucher_no", "voucher_type"),
)

# (table, column to set, column to match, optional type column)
# Type columns keep a Purchase Invoice from stealing a Sales Invoice name.
_REFERENCE_LINKS = (
    ("Subscription", "reference_document", "reference_document", None),
    ("Journal Entry Account", "reference_name", "reference_name", "reference_type"),
    ("Payment Entry Reference", "reference_name", "reference_name", "reference_doctype"),
    ("Payment Request", "reference_name", "reference_name", "reference_doctype"),
    ("Unreconcile Payment Entries", "reference_name", "reference_name", "reference_doctype"),
    (
        "Process Payment Reconciliation Log Allocations",
        "invoice_number",
        "invoice_number",
        "invoice_type",
    ),
    ("Invoice Declaration", "link_name", "link_name", None),
    ("Tax Retention Guatemala", "sales_invoice", "sales_invoice", None),
    ("Tax Withholding Entry", "taxable_name", "taxable_name", "taxable_doctype"),
    ("Tax Withholding Entry", "withholding_name", "withholding_name", "withholding_doctype"),
)


def child_tables_for(doctype):
    if doctype == "Purchase Invoice":
        children = PURCHASE_CHILD_TABLES
    else:
        children = SALES_CHILD_TABLES
    return tuple(children) + LEGACY_PARENT_TABLES


def _typed_children(doctype):
    if doctype == "Purchase Invoice":
        return set(PURCHASE_CHILD_TABLES)
    return set(SALES_CHILD_TABLES)


def _table(doctype):
    return "`tab{0}`".format(doctype)


def build_rename_statements(old_name, new_name, doctype, table_exists, has_column):
    """Return ``(sql, params)`` pairs for one invoice rename.

    ``table_exists(doctype)`` and ``has_column(doctype, column)`` are the
    Frappe database guards. Names are passed as parameters.
    """
    statements = []
    base = {"name": new_name, "serieFa": old_name, "link_doctype": doctype}

    def add(sql, extra=None):
        params = dict(base)
        if extra:
            params.update(extra)
        statements.append((sql, params))

    for child in child_tables_for(doctype):
        if not table_exists(child) or not has_column(child, "parent"):
            continue
        sql = "UPDATE {table} SET parent=%(name)s WHERE parent=%(serieFa)s".format(table=_table(child))
        # Real child tables carry parenttype. Sales Order and Delivery Note
        # keep the previous untyped parent match.
        if child in _typed_children(doctype) and has_column(child, "parenttype"):
            sql += " AND parenttype=%(link_doctype)s"
        add(sql)

    if table_exists("GL Entry") and has_column("GL Entry", "voucher_no"):
        # Every row of this voucher, including a credit note's AR line whose
        # against_voucher is the original invoice rather than the note itself.
        add("UPDATE `tabGL Entry` SET voucher_no=%(name)s WHERE voucher_no=%(serieFa)s")
        if has_column("GL Entry", "against_voucher"):
            type_sql = ""
            if has_column("GL Entry", "against_voucher_type"):
                type_sql = " AND against_voucher_type=%(link_doctype)s"
            # Any voucher (journal entry, payment, return) that still points here.
            add(
                "UPDATE `tabGL Entry` SET against_voucher=%(name)s "
                "WHERE against_voucher=%(serieFa)s{type_sql}".format(type_sql=type_sql)
            )
            if has_column("GL Entry", "docstatus"):
                add(
                    "UPDATE `tabGL Entry` SET docstatus=1 "
                    "WHERE voucher_no=%(name)s AND against_voucher IS NULL"
                )

    for table, set_col, where_col, type_col in _VOUCHER_LINKS + _REFERENCE_LINKS:
        if not table_exists(table):
            continue
        if not has_column(table, set_col) or not has_column(table, where_col):
            continue
        sql = "UPDATE {table} SET {column}=%(name)s WHERE {where}=%(serieFa)s".format(
            table=_table(table), column=set_col, where=where_col
        )
        if type_col and has_column(table, type_col):
            sql += " AND {type_col}=%(link_doctype)s".format(type_col=type_col)
        add(sql)

    if table_exists("Batch Invoices") and has_column("Batch Invoices", "invoice"):
        status_sql = ""
        if has_column("Batch Invoices", "electronic_invoice_status"):
            status_sql = ", electronic_invoice_status='Generated'"
        add(
            "UPDATE `tabBatch Invoices` SET invoice=%(name)s{status} WHERE invoice=%(serieFa)s".format(
                status=status_sql
            )
        )

    return statements


def rename_invoice_links(old_name, new_name, doctype):
    """Apply :func:`build_rename_statements` on the current site."""
    import frappe

    statements = build_rename_statements(
        old_name,
        new_name,
        doctype,
        frappe.db.table_exists,
        frappe.db.has_column,
    )
    for sql, params in statements:
        frappe.db.sql(sql, params)


def scaled_item_wise_amounts(amounts, new_total):
    """Scale item-wise tax amounts so they sum to ``new_total``.

    The fuel IDP rewrite sets the Sales Taxes and Charges amount to one
    value. Item Wise Tax Detail rows are the v16 per-item breakdown of
    that amount. An empty breakdown puts the full amount on the first row.
    """
    values = [float(amount or 0) for amount in amounts]
    if not values:
        return []
    target = float(new_total or 0)
    current = sum(values)
    if current == 0:
        scaled = [0.0 for _ in values]
        scaled[0] = target
        return scaled
    factor = target / current
    scaled = [value * factor for value in values]
    scaled[-1] = target - sum(scaled[:-1])
    return scaled


def sync_item_wise_tax_amounts(invoice_name, new_amount, parenttype="Sales Invoice"):
    """Rewrite Item Wise Tax Detail.amount after a raw tax_amount update."""
    import frappe

    if not frappe.db.table_exists("Item Wise Tax Detail"):
        return
    if not frappe.db.has_column("Item Wise Tax Detail", "amount"):
        return
    if not frappe.db.has_column("Item Wise Tax Detail", "parent"):
        return

    where = "parent=%(parent)s"
    params = {"parent": invoice_name, "parenttype": parenttype}
    if frappe.db.has_column("Item Wise Tax Detail", "parenttype"):
        where += " AND parenttype=%(parenttype)s"
    order = "idx, name" if frappe.db.has_column("Item Wise Tax Detail", "idx") else "name"
    rows = frappe.db.sql(
        "SELECT name, amount FROM `tabItem Wise Tax Detail` WHERE {where} ORDER BY {order}".format(
            where=where, order=order
        ),
        params,
        as_dict=True,
    )
    if not rows:
        return
    scaled = scaled_item_wise_amounts([row.get("amount") for row in rows], new_amount)
    for row, amount in zip(rows, scaled):
        frappe.db.sql(
            "UPDATE `tabItem Wise Tax Detail` SET amount=%(amount)s WHERE name=%(name)s",
            {"amount": amount, "name": row.get("name")},
        )
