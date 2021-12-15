# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime
# from erpnext.accounts.report.utils import convert  # value, from_, to, date
import json

import frappe
import pandas as pd
from frappe import _, _dict, scrub
from frappe.utils import cstr, flt, get_site_name, nowdate

from factura_electronica.factura_electronica.report.gt_sales_ledger.queries import (sales_invoices, sales_invoices_monthly,
                                                                                    sales_invoices_quarterly,
                                                                                    sales_invoices_weekly)

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

    # NOTA: los frappe.msgprint no estan funcionando en version Frappe ++v13.16.0
    columns = []

    if not filters:
        return columns, []

    # Conversion fechas filtro a objetos date para realizar validaciones
    start_d = datetime.datetime.strptime(filters.from_date, "%Y-%m-%d")  # en formato date
    final_d = datetime.datetime.strptime(filters.to_date, "%Y-%m-%d")

    # Validaciones de fechas
    if (start_d < final_d) or (final_d == start_d):

        # Definicion de columnas a totalizar
        # v1
        # columns_data_db = ['total', 'goods_iva', 'services_iva', 'fuel_iva', 'exempt_sales',
        #                    'net_fuel', 'sales_of_goods', 'sales_of_services', 'minus_excise_tax', 'other_tax']

        # v2
        columns_data_db = ['total']
        data = []
        invoices_db = []

        if filters.options == "No Subtotal":
            columns = get_columns(filters)
            # Se obtienen los datos de las facturas de venta
            invoices_db = sales_invoices(filters)
             # Se procesa la data de la db y los totales
            data = process_data_db(filters, invoices_db)

        if filters.options == "Weekly":
            columns = get_columns_weekly_report(filters)
            # Se obtienen los datos de las facturas de venta Semanalmente
            invoices_db = sales_invoices_weekly(filters)
            data = calculate_total(invoices_db, columns_data_db, filters, type_report="Weekly")

        if filters.options == "Monthly":
            columns = get_columns_monthly_report(filters)
            # Se obtienen los datos de las facturas de venta Mensualmente
            invoices_db = sales_invoices_monthly(filters)

            # Formatea y traduce la columna mes para reporte mensual
            [invoice.update({"month": f"{invoice.get('year_repo')} {_(MONTHS[invoice.get('month_repo')-1], lang=filters.language)}"}) for invoice in invoices_db]
            data = calculate_total(invoices_db, columns_data_db, filters, type_report="Montly")

        if filters.options == "Quarterly":
            columns = get_columns_quarterly_report(filters)
            # Se obtienen los datos de las facturas de venta Semestralmente
            invoices_db = sales_invoices_quarterly(filters)

            # Formatea la columna para reporte mensual
            [invoice.update({"quarter": f"{invoice.get('year_repo')} {_(QUARTERS[invoice.get('quarter_repo')-1], lang=filters.language)}"}) for invoice in invoices_db]
            data = calculate_total(invoices_db, columns_data_db, filters, type_report="Quarterly")

        if not data: return columns, []

        # TODO: AGREGAR GENERADOR EXCEL, JSON AQUI

        # Debug: datos de reporte
        # with open("res-gt-sales-ledger.json", 'w') as f:
        #     f.write(json.dumps(data, indent=2, default=str))

        return columns, data

    else:
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
            "options": "Sales Invoice",
            "width": 250
        },
        {
            "label": _("Tax ID"),
            "fieldname": "tax_id",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 250
        },
        {
            "label": _("Exempt Sales"),
            "fieldname": "exempt_sales",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 125
        },
        {
            "label": _("Sales Of Goods"),
            "fieldname": "sales_of_goods",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 250
        },
        {
            "label": _("Sales Of Services"),
            "fieldname": "sales_of_services",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 250
        },
        {
            "label": _("Export Sales"),
            "fieldname": "export_sales",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 125
        },
        {
            "label": _("Goods IVA"),
            "fieldname": "goods_iva",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 125
        },
        {
            "label": _("Services IVA"),
            "fieldname": "services_iva",
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
            "label": _("Accounting Document (Payment/Journal Entry)"),
            "fieldname": "accounting_document",
            "fieldtype": "Data",
            # "options": "Currency",
            "width": 250,
            # "hidden": 1
        }
    ]

    return columns


def get_columns_weekly_report(filters):
    """
    Asigna las propiedades para cada columna que va en el reporte

    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista de diccionarios
    """

    columns = [
        {
            "label": _("Week"),
            "fieldname": "week_repo",
            "fieldtype": "Data",
            "width": 150
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
        # {
        #     "label": _("Accounting Document (Payment/Journal Entry)"),
        #     "fieldname": "accounting_document",
        #     "fieldtype": "Data",
        #     # "options": "Currency",
        #     "width": 250,
        #     # "hidden": 1
        # }
    ]

    return columns


def get_columns_monthly_report(filters):
    """
    Asigna las propiedades para cada columna que va en el reporte

    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista de diccionarios
    """

    columns = [
        {
            "label": _("Month"),
            "fieldname": "month",
            "fieldtype": "Data",
            "width": 150
        },
        # {
        #     "label": _("Year"),
        #     "fieldname": "year_repo",
        #     "fieldtype": "Data",
        #     "width": 150
        # },
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
        # {
        #     "label": _("Accounting Document (Payment/Journal Entry)"),
        #     "fieldname": "accounting_document",
        #     "fieldtype": "Data",
        #     # "options": "Currency",
        #     "width": 250,
        #     # "hidden": 1
        # }
    ]

    return columns


def get_columns_quarterly_report(filters):
    """
    Asigna las propiedades para cada columna que va en el reporte

    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista de diccionarios
    """

    columns = [
        {
            "label": _("Quarter"),
            "fieldname": "quarter",
            "fieldtype": "Data",
            "width": 150
        },
        # {
        #     "label": _("Quarterly"),
        #     "fieldname": "quarter_repo",
        #     "fieldtype": "Data",
        #     "width": 150
        # },
        # {
        #     "label": _("Year"),
        #     "fieldname": "year_repo",
        #     "fieldtype": "Data",
        #     "width": 150
        # },
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
        # {
        #     "label": _("Accounting Document (Payment/Journal Entry)"),
        #     "fieldname": "accounting_document",
        #     "fieldtype": "Data",
        #     # "options": "Currency",
        #     "width": 250,
        #     # "hidden": 1
        # }
    ]

    return columns


def process_data_db(filters, data_db):
    """
    Procesa datos de la base de datos y obtener las referencias de pagos por cada factura
    sea Journal Entry o Payment Entry

    Args:
        filters (dict): Filtros front end
        data_db (list): Lista diccionarios con datos de la base de datos

    Returns:
        list: Lista diccionarios para mostrar en el reporte
    """

    try:
        # Si no hay data retornada por la base de datos, retorna una lista vacia
        # para no mostrar error por falta de datos
        if not data_db: return []

        # Definicion de columnas con valores numericos
        columns = ['total', 'amount', 'fuel_iva', 'goods_iva', 'net_amount', 'net_fuel', 'sales_of_goods', 'sales_of_services', 'services_iva']

        # Cargamos a la variable como diccionarios, para no manejar objetos date
        # Se carga a JSON para parsear las fechas a string
        invoices = json.loads(json.dumps(data_db, default=str))

        # Si la opcion check esta marcada, agrupara toda la data
        if filters.group:
            return sales_invoice_grouper(invoices, filters)

        # Por cada factura que se obtuvo de la base de datos
        for sales_invoice in invoices:
            # Agregamos las referencias, puede ser de Payment Entry o Journal Entry
            # Esto aplica si la factura tiene enlace con Payment Entry o Journal Entry
            ref_per = frappe.db.get_value('Payment Entry Reference', {'reference_name': sales_invoice.get('num_doc')}, 'parent')
            ref_je = frappe.db.get_value('Journal Entry Account', {'reference_name': sales_invoice.get('num_doc')}, 'parent')

            # Se obtiene el dominio configurado para armar la url
            site_erp = get_site_name(frappe.local.site)
            link_ref = ''

            # Si aplica se generan los link a Payment Entry o Journal Entry
            if ref_per:
                link_ref = f'https://{site_erp}/app/payment-entry/{ref_per}'  # para v13

            if ref_je:
                link_ref = f'https://{site_erp}/app/journal-entry/{ref_je}'

            # Se actualiza el diccionario con la url
            sales_invoice.update({
                "accounting_document": link_ref
            })

        final_data = calculate_total(invoices, columns, filters)

        return final_data
    except:
        # DEBUG
        # with open("error-report.txt", "w") as f:
        #     f.write(str(frappe.get_traceback()))

        frappe.msgprint(_('Proceso no completado, no se encontraron facturas con item configurados como Bien, Servicio o Combustible'))
        return []


def sales_invoice_grouper(invoices, filters):
    """
    Agrupa las facturas por tipo de serie y suma todos los montos para mostrarlo en una sola linea
    como VARIOS

    Args:
        invoices (list): Lista diccionarios de la base de datos
        filters (dict): Filtros front end

    Returns:
        list: Lista de diccionarios
    """
    try:
        df_purchase_invoice = pd.DataFrame.from_dict(invoices)

        # Agrupamos y sumamos por type_doc
        grouped = df_purchase_invoice.groupby(['type_doc']).sum()
        grouped.reset_index(inplace=True)

        # Sumamos los montos agrupados
        total_grouped = grouped[['amount', 'fuel_iva', 'goods_iva', 'net_amount', 'net_fuel',
                                 'sales_of_goods', 'sales_of_services', 'services_iva', 'total']].sum()

        # Convertimos a diccionario y
        # Agregamos las propiedades necesarias para que se muestre en el reporte
        total_dict = total_grouped.to_dict()
        total_dict.update({
            "customer": _("TOTALS"),
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

            if "customer" not in group:
                group.update({"customer": _("VARIOUS")})

            if "currency" not in group:
                group.update({"currency": filters.company_currency})

        grouped_dict.append(total_dict)

        return grouped_dict

    except:
        # with open("error-report-grouper.json", "w") as f:
        #     f.write(str(frappe.get_traceback()))
        frappe.msgprint(str(frappe.get_traceback()))


def calculate_total(data, columns, filters, type_report="Default"):
    """Obtiene el total de cada columna que se le especifique

    Args:
        data (list): Lista diccionarios
        columns (list): Lista columnas a totalizar
        filters (dict): Filtros frontend
        type_report (str, optional): Tipo de reporte. Defaults to "Default".

    Returns:
        list: Lista diccionarios con datos + fila total a mostrar en reporte
    """

    data_total = json.loads(json.dumps(data, default=str))
    # Calculo fila de totales
    df_totals = pd.DataFrame.from_dict(data_total)

    # Se especifican que columnas se va a sumar
    totals = df_totals[list(columns)].sum()
    totals = totals.to_dict()

    # frappe.publish_realtime(event='msgprint', message=str(columns)) # ,user='user@example.com'

    # DEBUG
    # with open("res-antes-de-redondeo.json", "w") as f:
    #     f.write(json.dumps(data_total, indent=2, default=str))
    # with open("res-total-antes-de-redondeo.json", "w") as f:
    #     f.write(json.dumps(totals, indent=2, default=str))

    # Se aplican los decimales a la data iterada:
    # Si la clave del diccionario que se esta iterando se encuentra en columns,
    # entonces se aplica el redondeo de decimales al valor numerico
    for row_data in data_total:
        [row_data.update({x: flt(row_data[x], PRECISION)}) for x in row_data if x in columns]

    if type_report == "Default":
        # Al objeto original se le agrega la fila con los totales correspondientes
        data_total.append({
            "type_doc": "",
            "num_doc": "",
            "tax_id": "",
            "customer": _("TOTALS"),
            # "total": f'<span style="font-weight: bold">{flt(totals.get("total", 0.0), PRECISION)}</span>', NO FUNCIONA POR QUE EL CAMPO DEBE SER NUMERICO
            "total": flt(totals.get("total", 0.0), PRECISION),
            "amount": flt(totals.get("amount", 0.0), PRECISION),
            "fuel_iva": flt(totals.get("fuel_iva", 0.0), PRECISION),
            "goods_iva": flt(totals.get("goods_iva", 0.0), PRECISION),
            "sales_of_goods": flt(totals.get("sales_of_goods", 0.0), PRECISION),
            "sales_of_services": flt(totals.get("sales_of_services", 0.0), PRECISION),
            "services_iva": flt(totals.get("services_iva", 0.0), PRECISION),
            "net_amount": flt(totals.get("net_amount", 0.0), PRECISION),
            "net_fuel": flt(totals.get("net_fuel", 0.0), PRECISION),
            "currency": filters.company_currency
        })
    else:
        data_total.append({
            "week_repo": f"<span style='font-weight: bold'>{_('TOTAL')}</span>",
            "total": flt(totals.get("total", 0.0), PRECISION),
            "currency": filters.company_currency
        })

    return data_total
