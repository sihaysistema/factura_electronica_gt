# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime
# from erpnext.accounts.report.utils import convert  # value, from_, to, date
import json

import pandas as pd

import frappe
from frappe import _, _dict, scrub
from frappe.utils import cstr, flt, nowdate
from frappe.utils import get_site_name

from factura_electronica.factura_electronica.report.gt_purchase_ledger.queries import purchase_invoices
# Para este reporte tambien se generara excel?
# from factura_electronica.utils_factura_electronica.purchase_ledger_excel_generator import creator


def execute(filters=None):
    """
    Funcion principal de reporte, cada modificacion en el front end ejecuta esto

    Args:
        filters (dict, optional): Filtros aplicados en front end. Defaults to None.

    Returns:
        tuple: Posicion 0 las columnas, Posicion 1 datos para las columnas
    """

    # Conversion fechas filtro a objetos date
    start_d = datetime.datetime.strptime(filters.from_date, "%Y-%m-%d")  # en formato date
    final_d = datetime.datetime.strptime(filters.to_date, "%Y-%m-%d")

    # Validaciones de fechas
    # Solo se permiten fechas en un mismo anio,
    if ((final_d > start_d) or (final_d == start_d)) and (start_d.year == final_d.year):

        columns = get_columns(filters)
        data_pi = purchase_invoices(filters)

        data = process_data_db(filters, data_pi)


        if len(data) > 0:
            pass
            # TODO: SE GENERARA EXCEL?
            # Llamamos a la funcion para crear excel
            # status_excel = creator(json.loads(json.dumps(data, indent=2, default=str)), filters.company_currency,
            #                        filters.company_currency, filters.from_date, filters.to_date, filters.language, filters)

            # Descomentar si quiers mostrar la notificacion
            # if status_excel[0] == True:
            #     frappe.msgprint(msg=_('Successfully generated report and excel'),
            #                     title=_('Process completed'), indicator='green')

        return columns, data

    else:
        frappe.msgprint(msg=_('The initial date must be less than the final date and for the same year'),
                        title=_('Uncompleted Task'), indicator='yellow')
        return [], []


def get_columns(filters):
    """
    Asigna las propiedades para cada columna que va en el reporte

    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista de diccionarios
    """

    columns = [
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 150
        },
        {
            "label": _("Type Doc."),
            "fieldname": "type_doc",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("Num Doc."),
            "fieldname": "num_doc",
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 250
        },
        {
            "label": _("Tax ID"),
            "fieldname": "tax_id",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 250
        },
        {
            "label": _("Purchases"),
            "fieldname": "purchases",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 125
        },
        {
            "label": _("Imports"),
            "fieldname": "imports",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 250
        },
        {
            "label": _("Services"),
            "fieldname": "services",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 250
        },
        {
            "label": _("Exempt"),
            "fieldname": "exempt",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 125
        },
        {
            "label": _("IVA"),
            "fieldname": "iva",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 125
        },
        {
            "label": _("Total"),
            "fieldname": "total",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 125
        },
        {
            "label": _("Currency"),
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            # "width": 250,
            "hidden": 1
        },
        {
            "label": _("Accounting Document"),
            "fieldname": "accounting_document",
            "fieldtype": "Data",
            # "options": "Currency",
            "width": 250,
            # "hidden": 1
        }
    ]

    return columns


def process_data_db(filters, data_db):
    """
    procesa los datos obtenidos de la base de datos para agregar una fila con
    los totales para las columnas purchases, services, iva, total

    Args:
        filters (dict): Filtros front end
        data_db (list): Lista diccionarios

    Returns:
        list: Lista diccionarios
    """

    if len(data_db) == 0:
        return data_db

    # Cnvertirmos a json, para no trabajar los objeto date
    processed = json.dumps(data_db, default=str)

    df = pd.read_json(processed)

    totals = df[['purchases', 'services', 'iva', 'total']].sum()
    totals = totals.to_dict()

    # si el check group esta marcado
    if filters.group:
        return purchase_invoice_grouper(processed, filters)


    # Agregamos las referencias
    for purchase_invoice in data_db:
        ref_per = frappe.db.get_value('Payment Entry Reference',
                                     {'reference_name': purchase_invoice.get('num_doc')}, 'parent')
        ref_je = frappe.db.get_value('Journal Entry Account',
                                    {'reference_name': purchase_invoice.get('num_doc')}, 'parent')

        site_erp = get_site_name(frappe.local.site)
        link_ref = ''

        if ref_per:
            # link_ref = f'''
            #     {ref_per}
            # <a class="btn-open no-decoration" title="Open Link"
            #     href="#Form/Payment%20Entry/{ref_per}">
            #     <i class="octicon octicon-arrow-right"></i>
            # </a>'''
            link_ref = f'https://{site_erp}/desk#Form/Payment%20Entry/{ref_per}'

        if ref_je:
            # link_ref = f'''
            #     {ref_je}
            # <a class="btn-open no-decoration" title="Open Link"
            #     href="#Form/Journal%20Entry/{ref_je}">
            #     <i class="octicon octicon-arrow-right"></i>
            # </a>'''
            link_ref = f'https://{site_erp}/desk#Form/Journal%20Entry/{ref_je}'

        purchase_invoice.update({
            "accounting_document": link_ref
        })


    # Agrega la fila de totales
    data_db.append({
        "type_doc": "",
        "num_doc": "",
        "tax_id": "",
        "supplier": _("TOTALS"),
        "purchases": totals.get("purchases", 0.0),
        "services": totals.get("services", 0.0),
        "iva": totals.get("iva", 0.0),
        "total": totals.get("total", 0.0),
        "currency": filters.company_currency
    })

    # PARA DEBUG
    # with open('purchase_report.json', 'w') as f:
    #     f.write(json.dumps(data_db, indent=2, default=str))

    return data_db


def purchase_invoice_grouper(invoices, filters):
    """
    Agrupa por facturas y suma todos los montos para mostrarlo en una sola linea
    como VARIOS

    Args:
        invoices (list): Lista diccionarios de la base de datos
        filters (dict): Filtros front end

    Returns:
        list: Lista de diccionarios
    """
    try:
        df_purchase_invoice = pd.read_json(invoices)

        # Agrupamos y sumamos por type_doc
        grouped = df_purchase_invoice.groupby(['type_doc']).sum()
        grouped.reset_index(inplace=True)

        # Sumamos los monto agrupados, para la fila de totales
        total_grouped = grouped[['purchases', 'services', 'iva', 'total']].sum()

        # Convertimos a diccionario y
        # Agregamos las propiedades necesarias para que se muestre en el reporte
        total_dict = total_grouped.to_dict()
        total_dict.update({
            "supplier": _("TOTALS"),
            "num_doc": "",
            "tax_id": "",
            "currency": filters.company_currency,
            "date": "",
            "type_doc": ""
        })

        # El resultado agrupado lo pasamos a diccionario
        grouped_dict = grouped.to_dict(orient='records')  # Accedemos al diccionario

        # Agregamos la propiedaes necesarias, para mostrar en reporte
        for group in grouped_dict:
            group.update({"date": ""})
            if "num_doc" not in group:
                group.update({"num_doc": _("VARIOUS")})

            if "tax_id" not in group:
                group.update({"tax_id": _("VARIOUS")})

            if "supplier" not in group:
                group.update({"supplier": _("VARIOUS")})

            if "currency" not in group:
                group.update({"currency": filters.company_currency})

        grouped_dict.append(total_dict)

        return grouped_dict

    except:
        frappe.msgprint(str(frappe.get_traceback()))

