# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.utils import cstr, flt


MONTHS_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "Jun": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}


def get_purchases_invoice(filters):
    """
    Obtiene datos de la base de datos de Facturas de compras

    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista diccionarios
    """

    filters_query = ""

    month = MONTHS_MAP.get(filters.month)

    purchase_invoices = frappe.db.sql(
        f"""SELECT DISTINCT name AS documento, 'C' AS compras_ventas, naming_series AS serie_doc, posting_date AS fecha_doc,
            facelec_nit_fproveedor AS nit_cliente_proveedor, supplier AS nombre_cliente_proveedor
            FROM `tabPurchase Invoice`
            WHERE YEAR(posting_date)='{filters.year}' AND MONTH(posting_date)='{month}' AND docstatus=1
            AND company='{filters.company}';
        """, as_dict=True
    )

    # with open('asl_purchase_invoice.json', 'w') as f:
    #     f.write(json.dumps(purchase_invoices, default=str))

    # Query para obtener datos de los items en las facturas de compras, para luego procesar con pandas
    items = frappe.db.sql(
        f"""SELECT DISTINCT parent, docstatus, net_amount, amount, facelec_p_is_good AS is_good,
            facelec_p_is_service AS is_service, facelec_p_is_fuel AS is_fuel,
            facelec_p_sales_tax_for_this_row AS tax_for_item, facelec_p_gt_tax_net_fuel_amt AS net_fuel,
            facelec_p_gt_tax_net_goods_amt AS net_good, facelec_p_gt_tax_net_services_amt AS net_service,
            facelec_p_amount_minus_excise_tax AS minus_excise_tax, facelec_p_other_tax_amount As other_tax
            FROM `tabPurchase Invoice Item` WHERE parent
            IN (SELECT DISTINCT name FROM `tabPurchase Invoice` WHERE docstatus=1 AND
            company = '{filters.company}' AND YEAR(posting_date)='{filters.year}' AND
            MONTH(posting_date)='{month}')
        """, as_dict=True
    )

    # with open('items_purchase_invoice.json', 'w') as f:
    #     f.write(json.dumps(items, indent=2))

    return purchase_invoices


def get_sales_invoice(filters):
    """
    Obtiene datos de la base de datos de Facturas de venta

    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista diccionarios
    """

    month = MONTHS_MAP.get(filters.month)

    sales_invoices = frappe.db.sql(
        f"""SELECT DISTINCT name AS documento, 'V' AS compras_ventas, naming_series AS serie_doc, posting_date AS fecha_doc,
            nit_face_customer AS nit_cliente_proveedor, customer AS nombre_cliente_proveedor
            FROM `tabSales Invoice`
            WHERE YEAR(posting_date)='{filters.year}' AND MONTH(posting_date)='{month}' AND docstatus=1
            AND company='{filters.company}';
        """, as_dict=True
    )

    # with open('asl_sales_invoice.json', 'w') as f:
    #     f.write(json.dumps(sales_invoices, default=str))

    items = frappe.db.sql(
        f"""SELECT DISTINCT parent, docstatus, net_amount, amount, facelec_is_good AS is_good,
            facelec_is_service AS is_service, factelecis_fuel AS is_fuel,
            facelec_sales_tax_for_this_row AS tax_for_item, facelec_gt_tax_net_fuel_amt AS net_fuel,
            facelec_gt_tax_net_goods_amt AS net_good, facelec_gt_tax_net_services_amt AS net_service,
            facelec_amount_minus_excise_tax AS minus_excise_tax, facelec_other_tax_amount As other_tax
            FROM `tabSales Invoice Item` WHERE parent
            IN (SELECT DISTINCT name FROM `tabSales Invoice` WHERE YEAR(posting_date)='{filters.year}'
            AND MONTH(posting_date)='{month}' AND docstatus=1
            AND company='{filters.company}')
        """, as_dict=True
    )

    # with open('items_sales_invoices.json', 'w') as f:
    #     f.write(json.dumps(items, indent=2))

    return sales_invoices
