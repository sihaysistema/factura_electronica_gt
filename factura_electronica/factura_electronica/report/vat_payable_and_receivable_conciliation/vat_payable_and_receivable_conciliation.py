# Copyright (c) 2020, Frappe, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import datetime
# from erpnext.accounts.report.utils import convert  # value, from_, to, date
import json
import pandas as pd

# We import all the queries we will program in the queries file
from factura_electronica.factura_electronica.report.vat_payable_and_receivable_conciliation.queries import *
# We import all the queries we will program in the validators file
from factura_electronica.factura_electronica.report.vat_payable_and_receivable_conciliation.validators import *
# from factura_electronica.utils.utilities_facelec import generate_asl_file, string_cleaner, validar_configuracion
from frappe import _, _dict, scrub
from frappe.utils import cstr, flt, get_site_name, nowdate


def execute(filters=None):
    columns, data = get_columns(), get_data(filters)
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
            "label": _("Document Type"),
            "fieldname": "doc_type",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Voucher or Document ID"),
            "fieldname": "doc_id",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Transaction Date"),
            "fieldname": "trans_date",
            "fieldtype": "Date",
            "width": 150
        },
        {
            "label": _("VAT Debit"),
            "fieldname": "vat_debit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 200
        },
        {
            "label": _("VAT Credit"),
            "fieldname": "vat_credit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 200
        },
        {
            "label": _("Transaction Total"),
            "fieldname": "trans_total",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 200
        },
        {
            "label": _("Currency"),
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            "hidden": 1
        },
    ]

    return columns

def get_data(filters):
    empty_row = {}
    data = [empty_row]
    initial_vat_payable = {
        "doc_type": "",
        "doc_id": "<strong>Saldo Inicial IVA por pagar</strong>",
        "trans_date": "",
        "vat_debit": "",
        "vat_credit": "300.00",
        "trans_total": "",
        "currency": "GTQ"
    }
    por_pagar_header = {
        "doc_type": "",
        "doc_id": "<strong>IVA POR PAGAR</strong>",
        "trans_date": "",
        "vat_debit": "",
        "vat_credit": "",
        "trans_total": "",
        "currency": "GTQ"
    }
    por_pagar_footer = {
        "doc_type": "",
        "doc_id": "<strong>SUBTOTAL IVA POR PAGAR</strong>",
        "trans_date": "",
        "vat_debit": "",
        "vat_credit": "672.00",
        "trans_total": "",
        "currency": "GTQ"
    }
    por_cobrar_header = {
        "doc_type": "",
        "doc_id": "<strong>IVA POR COBRAR</strong>",
        "trans_date": "",
        "vat_debit": "",
        "vat_credit": "",
        "trans_total": "",
        "currency": "GTQ"
    }
    por_cobrar_footer = {
        "doc_type": "",
        "doc_id": "<strong>SUBTOTAL IVA POR COBRAR</strong>",
        "trans_date": "",
        "vat_debit": "",
        "vat_credit": "36.00",
        "trans_total": "",
        "currency": "GTQ"
    }
    payable_vat_this_month = {
        "doc_type": "",
        "doc_id": "<strong>IVA a liquidar este mes</strong>",
        "trans_date": "",
        "vat_debit": "",
        "vat_credit": "636.00",
        "trans_total": "",
        "currency": "GTQ"
    }
    total_vat_payable_now = {
        "doc_type": "",
        "doc_id": "<strong>Monto a Liquidar Incluyendo Saldos pendientes</strong>",
        "trans_date": "",
        "vat_debit": "",
        "vat_credit": "936.00",
        "trans_total": "",
        "currency": "GTQ"
    }
    data.append(initial_vat_payable)
    data.append(por_pagar_header)

    # en_US: Getting the transactions for vat payable accounts to insert the rows, for this month.
    # es: Obtenemos las transacciones de IVA por pagar de este mes para insertar las filas.

    payable_data = get_vat_payable_data(filters)
    if len(payable_data) > 0:
        por_pagar = apply_on_site_links(payable_data)
        data.extend(por_pagar)

        data.append(por_pagar_footer)
        data.append(empty_row)
        data.append(empty_row)
        data.append(por_cobrar_header)


    # en_US: Getting the transactions for vat receivable accounts to insert the rows, for this month.
    # es: Obtenemos las transacciones de IVA por cobrar de este mes para insertar las filas.
    receivable_data = get_vat_receivable_data(filters)
    if len(receivable_data) > 0:
        por_cobrar = apply_on_site_links(receivable_data)
        data.extend(por_cobrar)

        data.append(por_cobrar_footer)
        data.append(empty_row)
        data.append(empty_row)
        data.append(payable_vat_this_month)
        data.append(empty_row)
        data.append(total_vat_payable_now)

    return data

# Generate links to documents found.

