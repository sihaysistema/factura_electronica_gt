# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime
import json

import frappe
from frappe import _
from frappe.utils import cstr, flt, get_site_name


MONTHS_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}


def get_vat_accounts(filters):
    """
    Obtiene la cuentas IVA por pagar/cobrar configuradas en la seccion de retencion en company,

    Args:
        filters (dict): Filtros front end

    Returns:
        dict: Diccionario con las cuenta configuradas
    """
    try:
        vat_accounts = frappe.db.get_values('Tax Witholding Ranges',
                                            filters={'parent': filters.company},
                                            fieldname=['iva_account_payable','vat_account_receivable'],
                                            as_dict=1)

        if len(vat_accounts) == 0 or len(vat_accounts) == 1:
            # Agregar aqui mensaje de advertencias
            pass

        return vat_accounts[0]

    except:
        frappe.msgprint(_("No Accounts found configured"))


def get_vat_payable_data(filters):
    """
        Query para obtener debe y haber para la cuenta por pagar iva, de la
        tabla Gl Entry
    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista diccionarios
    """

    try:
        vat_acct_payable = get_vat_accounts(filters)['iva_account_payable']
        # account = val['iva_account_payable']

        vat_payable_data = frappe.db.sql(f"""
            SELECT posting_date AS trans_date, voucher_type AS doc_type, voucher_no AS doc_id,
            debit_in_account_currency AS vat_debit, credit_in_account_currency AS vat_credit, account_currency AS currency
            FROM `tabGL Entry` WHERE company='{filters.company}'
            AND account='{vat_acct_payable}'
            AND MONTH(posting_date) = '{MONTHS_MAP.get(filters.month)}' AND YEAR(posting_date) = '{filters.year}'
            """, as_dict=1)

        # with open ('datos_iva_pagar.json', 'w') as f:
        #     f.write(json.dumps(vat_payable_data, default=str, indent=2))

        # result = apply_off_site_links(vat_payable_data)

        return vat_payable_data

    except:
        frappe.msgprint(frappe.get_traceback())


def get_vat_receivable_data(filters):
    """
        Query para obtener debe y haber para la cuenta por cobrar iva, de la
        tabla Gl Entry
    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista diccionarios
    """

    try:
        vat_acct_receivable = get_vat_accounts(filters)['vat_account_receivable']

        # account = val['iva_account_payable']
        vat_receivable_data = frappe.db.sql(f"""
            SELECT posting_date AS trans_date, voucher_type AS doc_type, voucher_no AS doc_id,
            debit_in_account_currency AS vat_debit, credit_in_account_currency AS vat_credit, account_currency AS currency
            FROM `tabGL Entry` WHERE company='{filters.company}'
            AND account='{vat_acct_receivable}'
            AND MONTH(posting_date) = '{MONTHS_MAP.get(filters.month)}' AND YEAR(posting_date) = '{filters.year}'
            """, as_dict=1)

        # with open ('datos_iva_cobrar.json', 'w') as f:
        #     f.write(json.dumps(vat_receivable_data, default=str, indent=2))

        # result = apply_off_site_links(vat_payable_data)

        return vat_receivable_data

    except:
        frappe.msgprint(frappe.get_traceback())


def apply_on_site_links(payable_data_lines):
    try:
        """Applies links for offsite reports such as excel
        Args:
            payable_data_line (object): The object contains the key
            value pairs for the query, this function will replace
            the key 'doc_id' with an html link, referring to the site.
        """
        site_erp = get_site_name(frappe.local.site)

        for line in payable_data_lines:
            # obtain the value of the doc_id key
            this_doc_type = line['doc_type']
            this_doc_id = line['doc_id']

            if this_doc_type == 'Sales Invoice':
                link_doc_type = 'Sales%20Invoice'
            elif this_doc_type == 'Purchase Invoice':
                link_doc_type = 'Purchase%20Invoice'
            elif this_doc_type == 'Journal Entry':
                link_doc_type = 'Journal%20Entry'
            else:
                link_doc_type = 'Sales%20Invoice'

            link_ref = f'#Form/{link_doc_type}/{this_doc_id}'
            assembled = f'<a href="{link_ref}">{this_doc_id}</a>'
            line.update({"doc_id": assembled})

        return payable_data_lines

    except:
        frappe.msgprint(frappe.get_traceback())


def apply_off_site_links(payable_data_lines):
    try:
        """Applies links for offsite reports such as excel
        Args:
            payable_data_line (object): The object contains the key
            value pairs for the query, this function will replace
            the key 'doc_id' with an html link, referring to the site.
        """
        site_erp = get_site_name(frappe.local.site)

        for line in payable_data_lines:
            # obtain the value of the doc_id key
            this_doc_type = line['doc_type']
            this_doc_id = line['doc_id']

            if this_doc_type == 'Sales Invoice':
                link_doc_type = 'Sales%20Invoice'
            elif this_doc_type == 'Purchase Invoice':
                link_doc_type = 'Purchase%20Invoice'
            elif this_doc_type == 'Journal Entry':
                link_doc_type = 'Journal%20Entry'
            else:
                link_doc_type = 'Sales%20Invoice'

            link_ref = f'https://{site_erp}/desk#Form/{link_doc_type}/{this_doc_id}'
            assembled = f'<a href="{link_ref}">{this_doc_id}</a>'
            line.update({"doc_id": assembled})

        return payable_data_lines

    except:
        frappe.msgprint(frappe.get_traceback())

# Credit Amount in Account Currency  =  SUMA
# Debit Amount in Account Currency  =  RESTA
# Obtener balance inicial del VAT para el periodo segun las cuentas. TODO

##  PURCHASE VAT
#  Obtain VAT Payable accounts from all Sales Taxes & Charges Templates that apply the filtered company.

# GL Entry  where account =
# Credit Amount in Account Currency  =  RESTA
# Debit Amount in Account Currency  =  SUMA
