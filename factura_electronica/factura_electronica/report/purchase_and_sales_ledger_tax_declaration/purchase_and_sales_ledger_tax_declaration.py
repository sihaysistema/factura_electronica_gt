# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime
# from erpnext.accounts.report.utils import convert  # value, from_, to, date
import json

import pandas as pd

import frappe
from frappe import _, _dict, scrub
from frappe.utils import cstr, flt, nowdate
from frappe.utils import get_site_name


MONTHS_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "Jun": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}


def execute(filters=None):
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
            "label": _("Establishment"),
            "fieldname": "establishment",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Purchases/Sales"),
            "fieldname": "purchases_sales",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Document"),
            "fieldname": "document",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Document series"),
            "fieldname": "document_series",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Document number"),
            "fieldname": "document_number",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Date of document"),
            "fieldname": "date_of_document",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Customer/Supplier NIT"),
            "fieldname": "customer_supplier_nit",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Name of customer/supplier"),
            "fieldname": "name_customer_supplier",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Type of transaction"),
            "fieldname": "type_of_transaction",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Type of operation (Good or Service)"),
            "fieldname": "type_operation_good_service",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Document status"),
            "fieldname": "document_status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("DPI card or passport order number"),
            "fieldname": "no_order_cedula_dpi_or_passport",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Registration number of the ID card, DPI or passport"),
            "fieldname": "no_cedula_dpi_passport",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Operation Document Type"),
            "fieldname": "operation_doc_type",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Operation document number"),
            "fieldname": "operation_doc_number",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Taxed Value of Document, Local Operating Goods "),
            "fieldname": "total_tax_doc_local_op_goods",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Taxed Value of Document, Foreign Operation Goods"),
            "fieldname": "total_tax_doc_local_foreign_goods",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Taxed Value of the document Services operation Local "),
            "fieldname": "total_tax_doc_local_ope_service",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Taxed Value of the document Services operation of the use Outside"),
            "fieldname": "total_tax_doc_local_ope_service_outside",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Exempt Document Value, Locally Operated Assets"),
            "fieldname": "total_exempt_doc_local_ope_assets",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Exempt Document Value, Foreign Operating Goods"),
            "fieldname": "total_exempt_doc_foreign_ope_goods",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Exempt Document Value, Local Operation Services"),
            "fieldname": "total_exempt_doc_local_ope_services",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Exempt Document Value, Foreign Operation Services"),
            "fieldname": "total_exempt_doc_foreign_ope_services",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Type of certificate"),
            "fieldname": "type_of_certificate",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Number of the certificate of exemption/purchase of inputs/withholding of IVA"),
            "fieldname": "no_certificate_exemp_purchase_inp_withholding_iva",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Value of the certificate of exemption/purchase of inputs/withholding of VAT"),
            "fieldname": "value_certificate_exemp_purchase_inp_withholding_iva",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Small Taxpayer Total Billed Local Operation Goods"),
            "fieldname": "small_taxpayer_total_billed_local_ope_goods",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Small Taxpayer Total Billed Local Operation Services"),
            "fieldname": "small_taxpayer_total_billed_local_ope_services",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Small Taxpayer Total Invoiced Foreign Operation Goods"),
            "fieldname": "small_taxpayer_total_invoiced_foreign_ope_goods",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Small Taxpayer Total Billed Foreign Operation Services IVA"),
            "fieldname": "small_taxpayer_total_billed_foreign_ope_services_iva",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Document Value"),
            "fieldname": "total_document_value",
            "fieldtype": "Data",
            "width": 100,
        },
    ]

    return columns


def get_data(filters):
    data = []
    data.extend(get_purchases_invoice(filters))
    data.extend(get_sales_invoice(filters))

    return data


def get_purchases_invoice(filters):
    filters_query = ""

    month = MONTHS_MAP.get(filters.month)

    purchase_invoices = frappe.db.sql(
        f"""SELECT DISTINCT name AS document, naming_series AS document_series, posting_date AS date_of_document,
            facelec_nit_fproveedor AS customer_supplier_nit, supplier AS name_customer_supplier
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

    month = MONTHS_MAP.get(filters.month)

    sales_invoices = frappe.db.sql(
        f"""SELECT DISTINCT name AS document, naming_series AS document_series, posting_date AS date_of_document,
            nit_face_customer AS customer_supplier_nit, customer AS name_customer_supplier
            FROM `tabSales Invoice`
            WHERE YEAR(posting_date)='{filters.year}' AND MONTH(posting_date)='{month}' AND docstatus=1
            AND company='{filters.company}';
        """, as_dict=True
    )

    with open('asl_sales_invoice.json', 'w') as f:
        f.write(json.dumps(sales_invoices, default=str))

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

    with open('items_sales_invoices.json', 'w') as f:
        f.write(json.dumps(items, indent=2))

    return sales_invoices
