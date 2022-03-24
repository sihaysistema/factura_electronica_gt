# Copyright (c) 2022, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, nowdate, nowtime

from factura_electronica.utils.utilities_facelec import get_currency_precision


PRECISION = get_currency_precision()


@frappe.whitelist()
def sales_invoice_calculator(invoice_name):
    """
    Calculate the invoice amount
    :param invoice_data:
    :return:
    """

    try:
        invoice_data = frappe.get_doc("Sales Invoice", invoice_name)

        items = invoice_data.items
        for invoice_row in items:
            # frappe.msgprint(invoice_row.item_code)
            invoice_row.facelec_amount_minus_excise_tax = 1999
            # invoice_row.db_set('facelec_amount_minus_excise_tax', 555)

        # other_tax_amount = flt()
        invoice_data.save()
        # invoice_data.notify_update()

        # frappe.msgprint(_("Invoice data saved "))

    except Exception as e:
        frappe.msgprint(_("Error: {0}").format(e))
