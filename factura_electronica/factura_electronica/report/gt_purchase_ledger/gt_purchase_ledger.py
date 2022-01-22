# Copyright (c) 2022, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime
import json

import frappe
import pandas as pd
from frappe import _
from frappe.utils import flt, get_site_name

from factura_electronica.factura_electronica.report.gt_purchase_ledger.queries import (purchase_invoices,
                                                                                       purchase_invoices_monthly,
                                                                                       purchase_invoices_quarterly,
                                                                                       purchase_invoices_weekly)

PRECISION = 2
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December",)
QUARTERS = ("Q1 Jan - Feb - Mar", "Q2 Abr - May - Jun", "Q3 Jul - Aug - Sep", "Q4 Oct - Nov - Dec",)


def execute(filters=None):
    """
    Funcion principal de reporte, cada modificacion en el front end ejecuta esto

    Args:
        filters (dict, optional): Filtros aplicados en front end. Defaults to None.

    Returns:
        tuple: Posicion 0 las columnas, Posicion 1 datos para las columnas
    """

    try:
        columns = []

        if not filters:
            return columns, []

        # Conversion fechas filtro a objetos date
        start_d = datetime.datetime.strptime(filters.from_date, "%Y-%m-%d")
        final_d = datetime.datetime.strptime(filters.to_date, "%Y-%m-%d")

        # Validaciones de fechas
        if (start_d < final_d) or (final_d == start_d):
            # Definicion Columnas de valores numericos Weekly, Monthly, Quarterly
            columns_data_db = ['total']

            data = []
            invoices_db = []

            if filters.options == "Detailed":
                columns = get_columns()
                # Se obtienen las facturas de compra
                invoices_db = purchase_invoices(filters)
                # Se procesa la data de la db y los totales
                data = process_data_db(filters, invoices_db)

            if filters.options == "Weekly":
                columns = get_columns_weekly_report()
                invoices_db = purchase_invoices_weekly(filters)
                data = calculate_total(invoices_db, columns_data_db, filters, type_report="Weekly")

            if filters.options == "Monthly":
                columns = get_columns_monthly_report()
                invoices_db = purchase_invoices_monthly(filters)

                 # Formatea y traduce la columna mes para reporte mensual
                [invoice.update({"month": f"{invoice.get('year_repo')} {_(MONTHS[invoice.get('month_repo')-1], lang=filters.language)}"}) for invoice in invoices_db]
                data = calculate_total(invoices_db, columns_data_db, filters, type_report="Monthly")

            if filters.options == "Quarterly":
                columns = get_columns_quarterly_report()
                # Se obtienen los datos de las facturas de venta Semestralmente
                invoices_db = purchase_invoices_quarterly(filters)

                # Formatea la columna para reporte mensual
                [invoice.update({"quarter": f"{invoice.get('year_repo')} {_(QUARTERS[invoice.get('quarter_repo')-1], lang=filters.language)}"}) for invoice in invoices_db]
                data = calculate_total(invoices_db, columns_data_db, filters, type_report="Quarterly")

            if not data: return columns, []

            # DEBUG:
            # with open('datos-purchase.json', 'w') as f:
            #     f.write(json.dumps(data, indent=2, default=str))

            return columns, data

        else:
            return [], []
    except:
        frappe.msgprint(msg=f"{_('If the error persists please report it. Details:')} <br><hr> <code>{frappe.get_traceback()}</code>",
                        title=_('Uncompleted Task'), indicator='red')

        return [], []

def get_columns():
    """
    Asigna las propiedades para cada columna que va en el reporte

    Returns:
        list: Lista de diccionarios
    """

    columns = [
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 125
        },
        {
            "label": _("Type Doc."),
            "fieldname": "type_doc",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Num Doc."),
            "fieldname": "num_doc",
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 200
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
            "label": _("Purchases (Net Total)"),
            "fieldname": "purchases",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "label": _("Imports"),
            "fieldname": "imports",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "label": _("Services"),
            "fieldname": "services",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "label": _("Goods"),
            "fieldname": "goods",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "label": _("Exempt"),
            "fieldname": "exempt",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "label": _("IVA"),
            "fieldname": "iva",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "label": _("Total"),
            "fieldname": "total",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
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
            "width": 300,
            # "hidden": 1
        }
    ]

    return columns


def get_columns_weekly_report():
    """Columnas para el reporte semanal

    Returns:
        list: lista dict con las columnas
    """

    columns = [
        {
            "label": _("Week"),
            "fieldname": "week_repo",
            "fieldtype": "Data",
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
            "hidden": 1
        }
    ]

    return columns


def get_columns_monthly_report():
    """Columnas para el reporte Mensual

    Returns:
        list: lista dict con las columnas
    """

    columns = [
        {
            "label": _("Month"),
            "fieldname": "month",
            "fieldtype": "Data",
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
            "hidden": 1
        }
    ]

    return columns


def get_columns_quarterly_report():
    """Columnas para el reporte Trimestral

    Returns:
        list: lista dict con las columnas
    """

    columns = [
        {
            "label": _("Quarter"),
            "fieldname": "quarter",
            "fieldtype": "Data",
            "width": 200
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
            "hidden": 1
        }
    ]

    return columns


def process_data_db(filters, data_db):
    """
    procesa los datos obtenidos de la base de datos para agregar una fila de
    totales y por cada uno de los registros generar un link de acceso

    Se utiliza para el reporte Default

    Args:
        filters (dict): Filtros front end
        data_db (list): Lista diccionarios

    Returns:
        list: Lista diccionarios
    """

    if len(data_db) == 0:
        return data_db

    # Definicion columnas con valores numericos para ser totalizados
    columns = ['purchases', 'goods', 'services', 'iva', 'total']

    # NOTE: REINTEGRAR SI LO PIDE AG
    # si el check group esta marcado
    # if filters.group:
    #     return purchase_invoice_grouper(processed, filters)
    site_erp = get_site_name(frappe.local.site)

    # Agregamos las referencias
    for purchase_invoice in data_db:
        ref_per = frappe.db.get_value('Payment Entry Reference',
                                     {'reference_name': purchase_invoice.get('num_doc')}, 'parent')
        ref_je = frappe.db.get_value('Journal Entry Account',
                                    {'reference_name': purchase_invoice.get('num_doc')}, 'parent')

        link_ref = ''

        if ref_per:
            link_ref = f'''<a class="btn-open no-decoration" href="/app/payment-entry/{ref_per}" target="_blank">{ref_per}</a>'''
            # link_ref = f'https://{site_erp}/app/payment-entry/{ref_per}'

        if ref_je:
            link_ref = f'''<a class="btn-open no-decoration" href="/app/journal-entry/{ref_je}" target="_blank">{ref_je}</a>'''
            # link_ref = f'https://{site_erp}/app/journal-entry/{ref_je}'

        purchase_invoice.update({
            "accounting_document": link_ref
        })

    return calculate_total(data_db, columns, filters)


def calculate_total(data, columns, filters, type_report="Default"):
    """Agrega una fila de totales segun el tipo de reporte y aplica
    redondeo de decimales usando `flt`

    Args:
        data (list): List Dict
        columns (list): Valores numericos
        filters (dict): Filtros front end
        type_report (str, optional): Tipo de reporte. Defaults to "Default".

    Returns:
        list: List Dict
    """
    if not data: return []

    # Cnvertirmos a json, para no trabajar los objeto `date`
    processed = json.loads(json.dumps(data, default=str))

    # Los datos se cargan a un dataframe para sumar de forma facil los totales
    # por columna
    df = pd.DataFrame.from_dict(processed)
    totals = df[columns].sum()
    totals = totals.to_dict()

    # Se aplica redondeo a los valores numericos
    for row_data in data:
        [row_data.update({x: flt(row_data[x], PRECISION)}) for x in row_data if x in columns]

    if type_report == "Default":
        # Agrega la fila de totales
        data.append({
            "type_doc": "",
            "num_doc": "",
            "tax_id": "",
            "supplier": f"<span style='font-weight: bold'>{_('TOTALS')}</span>",
            "purchases": flt(totals.get("purchases", 0.0), PRECISION),
            "services": flt(totals.get("services", 0.0), PRECISION),
            "iva": flt(totals.get("iva", 0.0), PRECISION),
            "total": flt(totals.get("total", 0.0), PRECISION),
            "currency": filters.company_currency
        })

    if type_report == "Weekly":
        data.append({
            "week_repo": f"<span style='font-weight: bold'>{_('TOTAL')}</span>",
            "total": flt(totals.get("total", 0.0), PRECISION),
            "currency": filters.company_currency
        })

    if type_report == "Monthly":
        data.append({
            "month": f"<span style='font-weight: bold'>{_('TOTAL')}</span>",
            "total": flt(totals.get("total", 0.0), PRECISION),
            "currency": filters.company_currency
        })

    if type_report == "Quarterly":
        data.append({
            "Quarterly": f"<span style='font-weight: bold'>{_('TOTAL')}</span>",
            "total": flt(totals.get("total", 0.0), PRECISION),
            "currency": filters.company_currency
        })

    return data


# NO IMPLEMENTADO, REINTEGRARLO SOLO SI LO PIDE AG
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

