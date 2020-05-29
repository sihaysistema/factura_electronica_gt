# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice import \
    batch_generator
from frappe import _

# USAR ESTE SCRIPT COMO API PARA COMUNICAR APPS DEL ECOSISTEMA FRAPPE/ERPNEXT :)

@frappe.whitelist()
def generate_batch(invoices):
    try:
        status_invoices = batch_generator(invoices)

    except :
        pass
