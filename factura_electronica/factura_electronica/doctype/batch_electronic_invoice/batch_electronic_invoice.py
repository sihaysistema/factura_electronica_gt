# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date
import json

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

