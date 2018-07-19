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
def add_gl_entry_other_special_tax(invoice_name, accounts):
    '''Crear n registros en GL Entry, dependiendo del numero de cuentas-impuestos
       detectadas, aplica cuando se valida una factura (Sales Invoice) '''
    # Convierte el objeto recibido a diccionario
    account_names = eval(accounts)

    # verifica que por lo menos exista una entrada en GL Entry
    if frappe.db.exists('GL Entry', {'voucher_no': invoice_name}):
        data_gl_entry = frappe.db.get_values('Sales Invoice', filters={'name': invoice_name},
                                            fieldname=['company', 'customer_name', 'party_account_currency',
                                                       'due_date'], as_dict=1)
        # Recorre el diccionario de cuentas, por cada cuenta inserta un nuevo
        # registro en GL Entry
        for account_n in account_names:
            # Evita el ingreso de cuentas duplicadas
            if not frappe.db.exists('GL Entry', {'account': account_n, 'voucher_no': invoice_name}):
                try:
                    new_gl_entry_tax = frappe.new_doc("GL Entry")
                    new_gl_entry_tax.fiscal_year = '2018'
                    # new_gl_entry_tax.docstatus = '1'
                    new_gl_entry_tax.voucher_no = invoice_name
                    new_gl_entry_tax.company = data_gl_entry[0]['company']
                    new_gl_entry_tax.voucher_type = 'Sales Invoice'
                    new_gl_entry_tax.is_advance = 'No'
                    new_gl_entry_tax.remarks = 'No Remarks'
                    new_gl_entry_tax.account_currency = data_gl_entry[0]['party_account_currency']
                    new_gl_entry_tax.account = account_n
                    new_gl_entry_tax.against = data_gl_entry[0]['customer_name']
                    new_gl_entry_tax.credit = account_names[account_n]
                    new_gl_entry_tax.is_opening = 'No'
                    new_gl_entry_tax.posting_date = data_gl_entry[0]['due_date']
                    new_gl_entry_tax.credit_in_account_currency = account_names[account_n]
                    new_gl_entry_tax.save()
                except:
                    frappe.msgprint(_('NO Guardado'))
                # else:
                #     frappe.msgprint(_(str(account_n) + ' = ' + str(account_names[account_n])))
            # else:
            #     frappe.msgprint(_('LAS CUENTAS YA SE AGREGARON :)'))
