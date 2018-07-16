# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _

from valida_errores import normalizar_texto

# Permite trabajar con acentos, ñ, simbolos, etc
import os, sys
reload(sys)
sys.setdefaultencoding('utf-8')

def calculate_values_with_special_tax():
    '''Grand total, quitar sumatoria totoal shs otros imuestos, = neto para iva
    se calcula sobre ese neto, y se va a ir a modificar en glentry para reflejar los cambios'''
    pass
@frappe.whitelist()
def add_gl_entry_other_special_tax(invoice_name, account_tax, amount_tax):
    # fixme: arreglar para guardar los registos en gl entry
    if frappe.db.exists('GL Entry', {'voucher_no': invoice_name}):
        data_gl_entry = frappe.db.get_values('Sales Invoice', filters={'name': invoice_name},
                                            fieldname=['company', 'customer_name', 'party_account_currency',
                                                       'due_date'], as_dict=1)
        try:
            new_gl_entry_tax = frappe.new_doc("GL Entry")
            new_gl_entry_tax.fiscal_year = '2018'
            new_gl_entry_tax.voucher_no = invoice_name
            new_gl_entry_tax.company = data_gl_entry[0]['company']
            new_gl_entry_tax.voucher_type = 'Sales Invoice'
            new_gl_entry_tax.is_advance = 'No'
            new_gl_entry_tax.remarks = 'No Remarks'
            new_gl_entry_tax.account_currency = data_gl_entry[0]['party_account_currency']
            new_gl_entry_tax.account = account_tax
            new_gl_entry_tax.against = data_gl_entry[0]['customer_name']
            new_gl_entry_tax.credit = amount_tax
            new_gl_entry_tax.is_opening = 'No'
            new_gl_entry_tax.posting_date = data_gl_entry[0]['due_date']
            new_gl_entry_tax.credit_in_account_currency = amount_tax
            new_gl_entry_tax.save()
        except:
            frappe.msgprint(_('NO Guardado'))
