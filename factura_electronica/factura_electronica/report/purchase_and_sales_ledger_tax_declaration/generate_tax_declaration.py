# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import xmltodict
from datetime import datetime, date, time
import os
import json


MONTHS_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

@frappe.whitelist()
def generate_vat_declaration(company, year, month, declared, report_data):
    try:
        # 1 - Cargar report_data con json load.
        # en_US: Loads the received data as if it was a json into a dictionary
        records = json.loads(report_data)

        # DEBUG: SI quieres saber la estrucutra de datos descomenta
        # with open('salida_report.json', 'w') as f:
        #     f.write(json.dumps(records, indent=2, default=str))

        declaration_invoices = []

        # 2 - Por cada factura
        for record in records:
            # 3 - Si no existe la declaracion se agregara
            if not frappe.db.exists('VAT Declaration', {'link_name': record.get('invoice_name')}):
                if record.get('docstatus') == 1:  # Solamente recibira docs validados
                    declaration_invoices.append({
                        'link_doctype': 'Sales Invoice' if record.get('compras_ventas') == 'V' else 'Purchase Invoice',
                        'link_name': record.get('invoice_name')
                    })

        # 4 - Validamos que por lo menos exista un elemento para crear la declaracion
        if len(declaration_invoices) > 0:

            # 4.1 - Verificamos que no existan un registro duplicado
            if not frappe.db.exists('VAT Declaration', {'name': f"VAT Declaration {date.today()}"}):
                vat_dec = frappe.get_doc({
                    "doctype": "VAT Declaration",
                    "title": f"VAT Declaration {date.today()}",
                    "company": company,
                    "posting_date": date.today(),
                    "declaration_year": year,
                    "declaration_month": MONTHS_MAP.get(str(month)),
                    "declaration_items": declaration_invoices,
                    "docstatus": 1
                })

                # for validated documents: status_journal = vat_dec.insert(ignore_permissions=True)
                # status_declaration = vat_dec.save(ignore_permissions=True)
                status_declaration = vat_dec.insert(ignore_permissions=True)

                # 5 - Actualizamos las facturas con su nueva Referencia en campo de tipo data,

            else:
                nme_reg = f'VAT Declaration {date.today()}'
                frappe.msgprint(msg=_(f"We're sorry. A statement for the same month was found: <b>{nme_reg}</b>,\
                                        if you wish to create it again please delete it and try again"),
                                title=_('Process not completed'), indicator='yellow')
                return

        else:
            frappe.msgprint(msg=_('No new statements were found to create'),
                            title=_('Process completed'), indicator='yellow')
            return

        frappe.msgprint(msg=_(f'The Tax Declaration register has been created, with name {status_declaration.name}'),
                        title=_('Process successfully completed'), indicator='green')
        return

    except:
        frappe.msgprint(msg=_(f'More details in the following log \n {frappe.get_traceback()}'),
                        title=_('Sorry, a problem occurred while trying to generate the VAT declaration'), indicator='red')
        return
