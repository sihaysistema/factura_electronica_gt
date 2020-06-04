# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import date
import json

from factura_electronica.fel_api import generate_electronic_invoice

class BatchElectronicInvoice(Document):
	pass


def batch_generator(invoice_list):

    try:
        if len(invoice_list) == 0:
            return False, 'No se recibio ninguna factura'

        BATCH = frappe.get_doc({
            "doctype": "Batch Electronic Invoice",
            "posting_date": str(date.today()),
            "batch_invoices": invoice_list,
            "docstatus": 0  # 0 = Draft, 1 = Validate, 2 = Cancel
        })

        batch_created = BATCH.insert(ignore_permissions=True)

        return True, batch_created.name

    except:
        return False, str(frappe.get_traceback())


@frappe.whitelist()
def submit_invoice(invoices):
    invoices = json.loads(invoices)

    for invoice in invoices:
        # get an existing document
        if not frappe.db.exists('Sales Invoice', {'name': str(invoice.get('invoice')), 'docstatus': 1, 'status': 'Draft'}) and \
        frappe.db.exists('Sales Invoice', {'name': str(invoice.get('invoice'))}):

            invoice = frappe.get_doc('Sales Invoice', {'name': str(invoice.get('invoice'))})
            invoice.docstatus = 1
            invoice.submit()

    frappe.msgprint(msg=_('Validated Invoices'), title=_('Success'), indicator='green')


@frappe.whitelist()
def electronic_invoices_batch(invoice_list, doc_name, doct):
    """
    Conector a Doctype Batch Electronic Invoice, para generar serialmente Facturas electronicas

    Args:
        invoice_list (list): Lista de facturas a generar
        docname (str): Nombre del doctype

    Returns:
        bool: True, para que javascript refresque la pagina y refleje los ultimso cambios
    """

    try:
        invoice_list = json.loads(invoice_list)
        log_invoices = []

        if len(invoice_list) > 0:
            fin_c = len(invoice_list)
            conta = 1
            for index, invoice in enumerate(invoice_list):
                conta += index
                # Formula para calcular el porcentarje sobre la cantidad de registros
                progress = (((conta) * 100) / fin_c)
                descr = f'Invoice {conta} of {fin_c}'
                frappe.publish_progress(percent=progress, title="Generating electronic invoices",
                                        description=descr, doctype=str(doct), docname=str(doc_name))

                invoice_code = invoice.get('invoice')
                naming_serie = frappe.db.get_value('Sales Invoice', {'name': invoice_code}, 'naming_series')
                status_elec_invoice = generate_electronic_invoice(invoice_code, naming_serie)

                # time.sleep(0.5)

        # return doc_name
        frappe.msgprint(msg=_('Electronic Invoices generated'), title=_('Success'), indicator='green')

    except:
        frappe.msgprint(_(str(frappe.get_traceback())))


