# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date

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

        return batch_created.name

    except:
        return False, str(frappe.get_traceback())
