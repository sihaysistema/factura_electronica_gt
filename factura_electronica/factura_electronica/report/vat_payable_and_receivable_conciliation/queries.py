# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.utils import cstr, flt
import json


MONTHS_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

def get_vat_accounts(filters):
    vat_accounts = frappe.db.get_values('Tax Witholding Ranges',
                        filters={'parent': filters.company},
                        fieldname=['iva_account_payable','vat_account_receivable'],
                        as_dict=1)
    return vat_accounts[0]

def get_vat_payable_data(filters):
    vat_acct_payable = get_vat_accounts(filters)['iva_account_payable']
    # account = val['iva_account_payable']
    vat_payable_data = frappe.db.sql(f"""
        SELECT
        posting_date AS trans_date,
        voucher_type AS doc_type,
        voucher_no AS doc_id,
        debit_in_account_currency AS debit,
        credit_in_account_currency AS vat_amount,
        FROM `tabGL Entry`
        WHERE company='{filters.company}'
        AND account='{vat_acct_payable}'
        AND MONTH(posting_date) = '{filters.month}' AND YEAR(posting_date) = '{filters.year}'
        """, as_dict=1)
    return vat_payable_data

# Credit Amount in Account Currency  =  SUMA
# Debit Amount in Account Currency  =  RESTA
# Obtener balance inicial del VAT para el periodo segun las cuentas. TODO

##  PURCHASE VAT
#  Obtain VAT Payable accounts from all Sales Taxes & Charges Templates that apply the filtered company.

# GL Entry  where account = 
# Credit Amount in Account Currency  =  RESTA
# Debit Amount in Account Currency  =  SUMA