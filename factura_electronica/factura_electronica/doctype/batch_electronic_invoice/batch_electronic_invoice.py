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
    """
    Creador de lotes, todos seran guardados solo hasta el nivel save, para
    que el usuario tenga la posibilidad de hacer la validacion automaticamente

    Args:
        invoice_list (list): Lista de facturas a agregar

    Returns:
        tuple: (True/False, mensaje de descripcion)
    """

    try:
        if len(invoice_list) == 0:
            return False, 'Las Facturas procesadas ya se encuentran generadas en lote, para verificar \
                           puedes ver en <a href="#List/Batch Electronic Invoice"><b>Batch Electronic Invoice</b></a>'

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
    """
    Valida serialmente todas las facturas que se encuentren en la tabla hija de Batch Invoices

    Args:
        invoices (list): Lista de facturas a validar
    """
    invoices = json.loads(invoices)

    for invoice in invoices:
        # Si la factura iterada se encuentra como draft, se validara
        if frappe.db.exists('Sales Invoice', {'name': str(invoice.get('invoice')), 'status': 'Draft', 'docstatus': 0}):
            # if not frappe.db.exists('Sales Invoice', {'name': str(invoice.get('invoice')), 'docstatus': 1, 'status': 'Draft'}) and \
            #     frappe.db.exists('Sales Invoice', {'name': str(invoice.get('invoice'))}):
            invoice = frappe.get_doc('Sales Invoice', {'name': str(invoice.get('invoice'))})
            invoice.docstatus = 1
            invoice.submit()

    frappe.msgprint(msg=_('Validated Invoices'), title=_('Success'), indicator='green')


@frappe.whitelist()
def electronic_invoices_batch(invoice_list, doc_name, doct):
    """
    Conector a Doctype Batch Electronic Invoice, para generar serialmente Facturas electronicas FEL

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
                if status_elec_invoice[0] == False:
                    log_invoices.append({
                        'status': False,
                        'invoice': invoice_code,
                        'details': status_elec_invoice[1]
                    })
                else:
                    log_invoices.append({
                        'status': True,
                        'invoice': invoice_code,
                        'details': status_elec_invoice[1]  # contiene el UUID de facelec
                    })

                # Al campo details del doctype, se le asignara el log, para luego js leer esa data y
                # renderizar el log
                frappe.db.set_value('Batch Electronic Invoice', doc_name, 'details', json.dumps(log_invoices))

        # return doc_name
        frappe.msgprint(msg=_('You will find more details in the log'), title=_('Processed batch'), indicator='green')

    except:
        frappe.msgprint(_(str(frappe.get_traceback())))


@frappe.whitelist()
def verify_validated_invoices(invoices):
    """
    Verifica si todas las facturas se encuentran validadas, esto para hacer mostrar
    el boton para factura electronica, solo y solo si todas las facturas estan validadas,
    tambien permite crear facelec por facelec

    Args:
        invoices (list): Lista dicconarios con los nombre de factura

    Returns:
        bool: True/False
    """

    invoice_list = json.loads(invoices)

    if len(invoice_list) > 0:
        for invoice in invoice_list:
            if not frappe.db.exists('Sales Invoice', {'name': invoice.get('invoice'), 'docstatus':1}):
                return False

        return True

    else:
        return False
