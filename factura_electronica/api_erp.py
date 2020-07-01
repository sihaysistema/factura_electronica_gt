# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice import \
    batch_generator
from factura_electronica.controllers.journal_entry import JournalEntryISR
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
def journal_entry_isr(data_invoice):
    """
    Funciona llamada desde boton Sales Invoice, encargada de crear Journal
    Entry, en funcion a los parametros pasados

    Args:
        data_invoice (dict): Diccionario con las propiedades de la factura
    """
    try:
        # NOTE: Escenarios posibles para polizas contables
        # 1. Poliza normal
        # 2. Poliza con retencion ISR
        # 3. Poliza con retension ISR e IVA

        new_je = JournalEntryISR(json.loads(data_invoice))  # Creamos una nueva instancia
        new_je.validate_dependencies()  # Aplicamos validaciones
        new_je.generate_je_accounts()  # Generamos las filas para el journal entry
        new_je.create_journal_entry()  # Guardamos registro en base de datos
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
