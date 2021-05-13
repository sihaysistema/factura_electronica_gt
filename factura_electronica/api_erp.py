# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import cstr

from factura_electronica.controllers.journal_entry import JournalEntrySaleInvoice
from factura_electronica.controllers.journal_entry_special import JournalEntrySpecialISR
from factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice import batch_generator

# USAR ESTE SCRIPT COMO API PARA COMUNICAR APPS DEL ECOSISTEMA FRAPPE/ERPNEXT :)

@frappe.whitelist()
def batch_generator_api(invoices):
    try:
        valid_invoices = []
        invoices = json.loads(invoices)

        for inv in invoices:  # only valid invoices
            if frappe.db.exists('Sales Invoice', {'name': inv.get('invoice'), 'docstatus': 1}):
                valid_invoices.append(inv)

        status_invoices = batch_generator(valid_invoices)

        if status_invoices[0]:
            frappe.msgprint(_(f'Lote generado con exito, puedes verlo <a href="#Form/Batch%20Electronic%20Invoice/{status_invoices[1]}" target="_blank"><b>aqui</b></a>'))
        else:
            frappe.msgprint(_(f'Lote no pudo se creado, mas detalles en el siguiente log: {status_invoices[1]}'))

    except:
        frappe.msgprint(_(f'Lote no pudo ser creado, mas detalles en el siguiente log: {frappe.get_traceback()}'))


@frappe.whitelist()
def journal_entry_isr(invoice_name, debit_in_acc_currency, cost_center='',
                      is_isr_ret=0, is_iva_ret=0, is_multicurrency=0, description=''):
    """
    Funcion llamada desde boton Actions en Sales Invoice, encargada de crear Journal
    Entry con retencion de impuestos, en funcion a los parametros

    Args:
        invoice_name (str): name factura
        debit_in_acc_currency (str): Nombre de la cuenta en moneda de la compania para debito
        cost_center (str, optional): Nombre centro de costo. Defaults to ''.
        is_isr_ret (int, optional): 1 Si aplica retencion ISR. Defaults to 0.
        is_iva_ret (int, optional): 1 Si aplica retencion IVA. Defaults to 0.
        is_multicurrency (int, optional): 1 Si es multimoneda. Defaults to 0.
        description (str, optional): Descripcion opcional. Defaults to ''.
    """

    try:
        # NOTE: Escenarios posibles que se pueden aplicar para polizas contables
        # 1. Poliza normal
        # 2. Poliza con retencion ISR
        # 3. Poliza con retension ISR e IVA

        # Obtiene los datos de la factura de la clase Sales Invoice, (diccionario)
        sales_invoice_info = frappe.get_doc('Sales Invoice', {'name': invoice_name})


        # Para evitar problemas primero verificamos que no exista una poliza contable
        # haciendo referencia a la factura que estamo trabajando
        if frappe.db.exists('Journal Entry Account', {'reference_type': 'Sales Invoice', 'reference_name': invoice_name}):
            frappe.msgprint(msg=_('If you wish to generate a new Journal Entry for this invoice, please cancel the existing policies that reference this invoice'),
                        title=_('Sorry, there is already a Journal Entry referenced to this invoice'), indicator='red')
            return


        # Nueva instancia de la clase y aplicamos el metodo de crear
        new_je = JournalEntrySaleInvoice(sales_invoice_info, int(is_isr_ret), int(is_iva_ret),
                                         debit_in_acc_currency, is_multicurrency, cost_center, description).create()

        # si hay problema al crear la poliza
        if new_je[0] == False:
            frappe.msgprint(msg=_(f'More details in the following log \n <code>{new_je[1]}</code>'),
                        title=_('Sorry, a problem occurred while trying to generate the Journal Entry'), indicator='red')
            return

        # si se crea correctamente la poliza
        if new_je[0] == True:
            frappe.msgprint(msg=_(f'Generated with the series \n <code>{new_je[1]}</code>'),
                        title=_('Successfully generated'), indicator='green')
            return

    except:
        frappe.msgprint(msg=_(f'More details in the following log \n <code>{frappe.get_traceback()}</code>'),
                        title=_('Sorry, a problem occurred while trying to generate the Journal Entry'), indicator='red')


@frappe.whitelist()
def journal_entry_isr_purchase_inv(invoice_name, credit_in_acc_currency, cost_center='',
                                   is_multicurrency=0, description=''):
    """
    Funciona llamada desde boton Purchase Invoice, encargada de crear Journal
    Entry, en funcion a los parametros pasados

    Args:
        invoice_name (dict): Diccionario con las propiedades de la factura
    """

    try:
        # NOTE: APLICA SOLO PARA FACTURA ESPECIAL, APLICA RETENSION IVA E ISR, VER CLASE PARA FUTURAS MODIFICACIONES :D
        purchase_invoice_info = frappe.get_doc('Purchase Invoice', {'name': invoice_name})

        # Si es para una factura especial
        new_je = JournalEntrySpecialISR(purchase_invoice_info, credit_in_acc_currency,
                                        is_multicurrency, description, cost_center).create()

        if new_je[0] == False:
            frappe.msgprint(msg=_(f'More details in the following log \n {new_je[1]}'),
                            title=_('Sorry, a problem occurred while trying to generate the Journal Entry'), indicator='red')
            return
        if new_je[0] == True:
            frappe.msgprint(msg=_(f'Generated with the series \n {new_je[1]}'),
                            title=_('Successfully generated'), indicator='green')
            return

    except:
        frappe.msgprint(msg=_(f'More details in the following log \n {frappe.get_traceback()}'),
                        title=_('Sorry, a problem occurred while trying to generate the Journal Entry'), indicator='red')


@frappe.whitelist()
def download_asl_files():
    """
    Permite descargar archivo ASL
    """
    frappe.local.response.filename = "ASISTE.ASL"
    with open("ASISTE.ASL", "rb") as fileobj:
        filedata = fileobj.read()
    frappe.local.response.filecontent = filedata
    frappe.local.response.type = "download"


def custom_customer_info(doc, method):
    # Runs on event update - Customer
    # this function will get call `on_update` as we define in hook.py
    add_address_info(doc)


def add_address_info(doc):
    if doc.flags.is_new_doc and doc.get('address_line1'):
        # this name construct should work
        # because we just create this customer
        # Billing is default type
        # there shouldn't be any more address of this customer
        address_name = (
            cstr(doc.name).strip() + '-' + cstr(_('Billing')).strip()
        )
        address_doc = frappe.get_doc('Address', address_name)
        # adding custom data to address
        address_doc.email_id = doc.get('email_id')
        address_doc.county = doc.get('county')
        address_doc.phone = doc.get('phone')
        address_doc.is_primary_address = doc.get('is_primary_address')
        address_doc.save()
