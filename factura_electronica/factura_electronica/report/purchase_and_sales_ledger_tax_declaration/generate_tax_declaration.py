# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
from datetime import date, datetime, time
import pandas as pd

import frappe
import xmltodict
from frappe import _


MONTHS_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}


@frappe.whitelist()
def generate_vat_declaration(company, year, month, declared, report_data):
    """[summary]

    Args:
        company ([type]): [description]
        year ([type]): [description]
        month ([type]): [description]
        declared ([type]): [description]
        report_data ([type]): [description]
    """
    try:
        # 1 - Cargar report_data con json load.
        # en_US: Loads the received data as if it was a json into a dictionary
        records = json.loads(report_data)

        # por facilidad creamos un df para obtener el total de todas las facturas incluidas
        total_inv = 0
        if len(records) > 0:
            df_inv = pd.DataFrame.from_dict(records).fillna(0)
            total_inv = df_inv['total_valor_doc'].sum(skipna=True)

            frappe.msgprint(str(total_inv))

        # DEBUG: SI quieres saber la estrucutra de datos descomenta
        # with open('data_reporte_declaracion.json', 'w') as f:
        #     f.write(json.dumps(records, indent=2, default=str))

        # Guardara todas las facturas para la declaracion
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
                # CREAMOS EL REGISTRO COMO VALIDADO
                try:
                    data_decl = {
                        "doctype": "VAT Declaration",
                        "title": f"VAT Declaration {date.today()}",
                        "company": company,
                        "posting_date": str(date.today()),
                        "declaration_year": str(year),
                        "declaration_month": MONTHS_MAP.get(str(month)),
                        "declaration_items": declaration_invoices,
                        "total": float(total_inv),
                        "docstatus": 1
                    }

                    vat_dec = frappe.get_doc(data_decl)

                    # for validated documents: status_journal = vat_dec.insert(ignore_permissions=True)
                    # status_declaration = vat_dec.save(ignore_permissions=True)
                    status_declaration = vat_dec.insert(ignore_permissions=True)

                # SI OCURRE ALGUN ERROR
                except:
                    frappe.msgprint(msg=_(f'More details in the following log \n <code>{frappe.get_traceback()}</code>'),
                        title=_('Sorry, a problem occurred while trying to generate the VAT declaration'), indicator='red')
                    return

                # SI LA CREACION ES EXITOSA, ACTUALIZAMOS LAS FACTURAS VENTA/COMPRA CON LA REFERENCIA
                else:
                    # Por cada factura venta, compra
                    for record in records:
                        if record.get('compras_ventas') == 'V':  # si es venta
                            frappe.db.sql('''UPDATE `tabSales Invoice`
                                             SET facelec_s_vat_declaration=%(declaration)s
                                             WHERE name=%(name_inv)s
                                          ''', {'declaration': status_declaration.name, 'name_inv': str(record.get('invoice_name'))})

                        else:  # si es compra
                            frappe.db.sql('''UPDATE `tabPurchase Invoice`
                                             SET facelec_p_vat_declaration=%(declaration)s
                                             WHERE name=%(name_inv)s
                                          ''', {'declaration': status_declaration.name, 'name_inv': str(record.get('invoice_name'))})

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
