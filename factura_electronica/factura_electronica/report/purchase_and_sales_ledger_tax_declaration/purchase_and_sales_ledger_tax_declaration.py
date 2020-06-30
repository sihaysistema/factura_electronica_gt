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

def execute(filters=None):
    columns = get_columns()
    data = [{}]
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
            "fieldname": "date_of_documento",
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

