# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice import \
    batch_generator
from factura_electronica.controllers.journal_entry import JournalEntryISR, JournalEntrySpecialISR
from frappe import _

import json


# USAR ESTE SCRIPT COMO API PARA COMUNICAR APPS DEL ECOSISTEMA FRAPPE/ERPNEXT :)

@frappe.whitelist()
def batch_generator_api(invoices):
    try:
        status_invoices = batch_generator(invoices)
        frappe.msgprint(_(str(status_invoices)))

    except:
        pass


@frappe.whitelist()
def journal_entry_isr(invoice_name, is_isr_ret, is_iva_ret, cost_center,
                      debit_in_acc_currency, is_multicurrency=0, description='',
                      is_special_inv=0):
    """
    Funciona llamada desde boton Sales Invoice, encargada de crear Journal
    Entry, en funcion a los parametros pasados

    Args:
        invoice_name (dict): Diccionario con las propiedades de la factura
    """
    try:
        # NOTE: Escenarios posibles para polizas contables
        # 1. Poliza normal
        # 2. Poliza con retencion ISR
        # 3. Poliza con retension ISR e IVA
        sales_invoice_info = frappe.get_doc('Sales Invoice', {'name': invoice_name})

        # normal
        if is_special_inv == 0:
            new_je = JournalEntryISR(sales_invoice_info, is_isr_ret, is_iva_ret, cost_center,
                                    debit_in_acc_currency, is_multicurrency, description).create()

        # Si es para una factura especial
        if is_special_inv == 1:
            new_je = JournalEntrySpecialISR(sales_invoice_info, is_isr_ret, is_iva_ret, cost_center,
                                            debit_in_acc_currency, is_multicurrency, description,
                                            is_special_inv).create()

        if new_je[0] == False:
            frappe.msgprint(msg=_(f'More details in the following log \n {new_je[1]}'),
                        title=_('Sorry, a problem occurred while trying to generate the Journal Entry'), indicator='red')
            return
        if new_je[0] == True:
            frappe.msgprint(msg=_(f'Generated with the series \n {new_je[1]}'),
                        title=_('Successfully generated'), indicator='green')
            return

    except:
        frappe.msgprint(msg=_(f'More details in the following log \n {frappe.get_traceback()}'),
                        title=_('Sorry, a problem occurred while trying to generate the Journal Entry'), indicator='red')


@frappe.whitelist()
def download_asl_files():
    """
    Permite descargar
    """
    frappe.local.response.filename = "ASISTE.ASL"
    with open("ASISTE.ASL", "rb") as fileobj:
        filedata = fileobj.read()
    frappe.local.response.filecontent = filedata
    frappe.local.response.type = "download"
