# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import xmltodict
from datetime import datetime, date, time
import os

@frappe.whitelist()
def generate_vat_declaration(filters, report_data):
    try:
        # TODO
        # Crear Vat declaration
        # Opcion 1:
        # CON JS:  si se desea obtener la data desde el report, se obtiene como argumento report.data
        # CON PY:  De lo contrario, obviamos lo de arriba y solo trabajamos lo de abajo:
        # Necesitamos filters del report, pasados como argumentos desde el frappe.call: declared , company, month, year, [] 
        #  validaciones:
        if filters.declared == 'Not Declared':
            # Generate doctype for vat declaration
            this_dec = frappe.get_doc("VAT Declaration")
            this_dec.title = "Hello VAT Declaration"
            this_dec.company = filters.company
            this_dec.declaration_year = filters.year
            this_dec.declaration_month = filters.month
            this_dec.declaration_month = filters.month
            this_dec.posting_date = "2020-07-17"
            this_dec.declaration_items = [
                {
                    "link_doctype": "Purchase Invoice",
                    "link_name": "ACC-PINV-2020-00001"
                }
            ]
            this_dec.save()
            # Se agrega al vat declararion el item de cada factura presente en esta declaracion
            # Al guardar se agrega a cada una de las facturas el Doctype, Doctype ID o title en el campo de child table Dynamic Link
            # A cada factura de las que tocamos, le agregamos al campo custom field, el titulo de ESTA VAT Declaration que creamos.
        else:
            # We somehow tried to send the declared or all non declared and declared documents.  This is not allowed for our purpose!
            pass
    except:
        frappe.msgprint("algo salio mal")
    else:
        frappe.msgprint("estas fregado")

