# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import xmltodict
from datetime import datetime, date, time
import os

@frappe.whitelist()
def generate_vat_declaration(company, year, month, declared):
    try:
           # Cargar report_data con json load.
        # en_US: Loads the received data as if it was a json into a dictionary
        # es: Carga como json-diccionario la data recibida
        # documents = json.loads(report_data)
        # TODO
        # Crear Vat declaration
        # Opcion 1:
        # CON JS:  si se desea obtener la data desde el report, se obtiene como argumento report.data
        # CON PY:  De lo contrario, obviamos lo de arriba y solo trabajamos lo de abajo:
        # Necesitamos filters del report, pasados como argumentos desde el frappe.call: declared , company, month, year, [] 
        #  validaciones:
        # frappe.msgprint((str(company) + str(year) + str(month) + str(declared)))
        if declared == 'Not Declared':
            vat_dec = frappe.get_doc({
                    "doctype": "VAT Declaration",
                    "title": "Hello VAT Declaration",
                    "company": company,
                    "posting_date": "2020-07-17",
                    "declaration_year": year,
                    "declaration_month": 7,
                    "declaration_items": [
                        {
                            "link_doctype": "Purchase Invoice",
                            "link_name": "ACC-PINV-2020-00001"
                        }
                    ],
                    "docstatus": 0
                })
                # for validated documents: status_journal = vat_dec.insert(ignore_permissions=True)
            status_declaration = vat_dec.save(ignore_permissions=True)

            # Se agrega al vat declararion el item de cada factura presente en esta declaracion
            # Al guardar se agrega a cada una de las facturas el Doctype, Doctype ID o title en el campo de child table Dynamic Link
            # A cada factura de las que tocamos, le agregamos al campo custom field, el titulo de ESTA VAT Declaration que creamos.
        else:
            # We somehow tried to send the declared or all non declared and declared documents.  This is not allowed for our purpose!
           pass
    except:
        frappe.msgprint("algo salio mal" + str(frappe.get_traceback()))

    else:
        frappe.msgprint("no estas fregado")


