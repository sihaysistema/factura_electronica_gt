# Copyright (c) 2013, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json

import pandas as pd

import frappe
from factura_electronica.utils.utilities_facelec import generate_asl_file
from frappe import _, _dict, scrub
from frappe.utils import cstr, flt, get_site_name, nowdate


def execute(filters=None):
    """
    Funcion principal del reporte

    Args:
        filters (dict, optional): Filtros front end. Defaults to None.

    Returns:
        tuple: columnas y datos
    """

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    """
    Asigna las propiedades para cada columna que va en el reporte

    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista de diccionarios
    """

    columns = [
        {
            "label": _("Retention Date"),
            "fieldname": "retention_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Invoice Number"),
            "fieldname": "invoice_number",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Tax ID"),
            "fieldname": "tax_id",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Entity"),
            "fieldname": "entity",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Invoice Date"),
            "fieldname": "invoice_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Invoice Total"),
            "fieldname": "invoice_total",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Retention Amount"),
            "fieldname": "retention_amount",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Purchase Ledger Number"),
            "fieldname": "purchase_ledger_number",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Journal Entry"),
            "fieldname": "journal_entry",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Retention Confirmation Number"),
            "fieldname": "retention_confirmation_number",
            "fieldtype": "Data",
            "width": 100
        },
    ]

    return columns


def get_data(filters):
    """
    Llama a las funciones encargadas de correr los queries que obtienen datos
    de la base de datos, de Facturas de compra, venta

    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista diccionarios
    """

    data = []

    # Escenarios
    # 1 - En filtros solo se selecciono Supplier
    # Obtenemos datos solo de proveedores, Facturas de compra
    if str(filters.tipo_de_factura) == "Supplier":
        purchase_inv = get_purchases_invoice(filters)
        frappe.msgprint(str(purchase_inv))
        if len(purchase_inv) > 0:  # Si por lo menos hay un registro
            return purchase_inv

    # 2 - En filtros solo se seleccino Customer
    # Obtendremos datos solo de clientes, Facturas de Venta
    if filters.tipo_de_factura == "Customer":
        sales_inv = get_sales_invoice(filters)
        if len(sales_inv) > 0:  # Si por lo menos hay un registro
            return sales_inv

    # 3 - En filtros no se selecciono ni Supplier, ni Customer
    # Obtendremos datos de proveedores y clientes, Facturas Venta y Compra
    if filters.tipo_de_factura is None:
        purchase_inv = get_purchases_invoice(filters)
        sales_inv = get_sales_invoice(filters)

        if len(purchase_inv) > 0:  # Si por lo menos hay un registro
            data.extend(purchase_inv)

        if len(sales_inv) > 0:  # Si por lo menos hay un registro
            data.extend(sales_inv)

        return data


def get_purchases_invoice(filters):
    """get_purchases_invoice [summary]

    [extended_summary]

    Args:
        filters ([type]): [description]

    Returns:
        [type]: [description]
    """
    filters_query = ""

    purchase_invoices = frappe.db.sql(
        f"""SELECT DISTINCT name AS invoce_number, posting_date AS invoice_date,
            facelec_nit_fproveedor AS tax_id, supplier AS entity, grant_total AS invoice_total
            FROM `tabPurchase Invoice`
            WHERE posting_date BETWEEN '{filters.from_date}' AND '{filters.to_date}'
            AND docstatus=1 AND company='{filters.company}';
        """, as_dict=True
    )

    # Descomentar solo para debug
    # with open('asl_purchase_invoice.json', 'w') as f:
    #     f.write(json.dumps(purchase_invoices, default=str))

    # Query para obtener datos de los items en las facturas de compras, para luego procesar con pandas
    return purchase_invoices


def get_sales_invoice(filters):
    return []
    # sales_invoices = frappe.db.sql(
    #     f"""SELECT DISTINCT name AS invoce_number, posting_date AS postin_date,
    #         nit_face_customer AS tax_id, customer AS FROM `tabSales Invoice`
    #         WHERE posting_date BETWEEN '{filters.from_date}' AND '{filters.to_date}' AND docstatus=1
    #         AND company='{filters.company}';
    #     """, as_dict=True
    # )

    # # with open('asl_sales_invoice.json', 'w') as f:
    # #     f.write(json.dumps(sales_invoices, default=str))
    # return sales_invoices
