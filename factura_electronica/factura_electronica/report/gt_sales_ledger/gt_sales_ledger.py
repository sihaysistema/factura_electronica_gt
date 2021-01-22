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

from factura_electronica.factura_electronica.report.gt_sales_ledger.queries import sales_invoices

# from milconnect.utils.sales_ledger_excel_generator import creator

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
    if ((final_d > start_d) or (final_d == start_d)) and (start_d.year == final_d.year):
        columns = get_columns(filters)
        datas = sales_invoices(filters)

        data = process_data_db(filters, datas)

        if len(data) > 0:
            pass
            # status_excel = creator(json.loads(json.dumps(data, default=str)), filters.company_currency,
            #                       filters.company_currency, filters.from_date, filters.to_date, filters.language, filters)
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
    Procesa datos de la base de datos

    Args:
        filters (dict): Filtros front end
        data_db (list): Lista diccionarios con datos de la base de datos

    Returns:
        list: Lista diccionarios para mostrar en el reporte
    """

    try:
        # Si no hay data retornada por la base de datos, retorna una lista vacia
        # para no mostrar error por falta de datos
        if (len(data_db[0]) == 0) or (len(data_db[1]) == 0):
            return []

        # Cargamos a la variable como diccionarios, para no manejar objetos date
        invoices = json.loads(json.dumps(data_db[0], default=str))
        items = json.loads(json.dumps(data_db[1], default=str))

        # Separamos los items segun su tipo
        items_ok = []
        for item in items:
            # Si es bien
            if item.get("is_good"):
                items_ok.append({
                    "parent": item.get("parent"),
                    "net_amount": item.get("net_amount"),
                    "amount": item.get("amount"),
                    "goods_iva": item.get("tax_for_item"),
                    "services_iva": 0.0,
                    "fuel_iva": 0.0,
                    "sales_of_goods": item.get("net_good"),
                    "sales_of_services": item.get("net_service"),
                    "net_fuel": item.get("net_fuel")
                })

            # Si es servicio
            if item.get("is_service"):
                items_ok.append({
                    "parent": item.get("parent"),
                    "net_amount": item.get("net_amount"),
                    "amount": item.get("amount"),
                    "goods_iva": 0.0,
                    "services_iva": item.get("tax_for_item"),
                    "fuel_iva": 0.0,
                    "sales_of_goods": item.get("net_good"),
                    "sales_of_services": item.get("net_service"),
                    "net_fuel": item.get("net_fuel")
                })

            # EN ESTE REPORTE NO SE TOMA EN CUENTA LAS FACTURAS DE COMBUSTIBLES (ventas)
            # Si es fuel
            # if item.get("is_fuel"):
            #     items_ok.append({
            #         "parent": item.get("parent"),
            #         "net_amount": item.get("net_amount"),
            #         "amount": item.get("amount"),
            #         "goods_iva": 0.0,
            #         "services_iva": 0.0,
            #         "fuel_iva": item.get("tax_for_item"),
            #         "sales_of_goods": item.get("net_good"),
            #         "sales_of_services": item.get("net_service"),
            #         "net_fuel": item.get("net_fuel")
            #     })


        # Carga de items categorizados a un DataFrame
        df = pd.DataFrame.from_dict(items_ok)

        # Por cada factura buscamos sus items y sumamos aquellos items que sean de
        # la misma categoria para dejarlo en una sola linea
        for invoice in invoices:
            item_inv = (df.loc[df['parent'] == invoice.get('num_doc')].sum()).to_dict()
            invoice.update(item_inv)

        # Si la opcion check esta marcada, agrupara toda la data
        if filters.group:
            return sales_invoice_grouper(invoices, filters)


        # Agregamos las referencias, puede ser de Payment Entry o Journal Entry
        # Esto aplica si la factura tiene enlace con Payment Entry o Journal Entry
        for sales_invoice in invoices:
            ref_per = frappe.db.get_value('Payment Entry Reference',
                                        {'reference_name': sales_invoice.get('num_doc')}, 'parent')
            ref_je = frappe.db.get_value('Journal Entry Account',
                                        {'reference_name': sales_invoice.get('num_doc')}, 'parent')

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

            sales_invoice.update({
                "accounting_document": link_ref
            })


        df_totals = pd.DataFrame.from_dict(invoices)
        # Sumas para dejar un total por fila factura
        totals = df_totals[['total', 'amount', 'fuel_iva', 'goods_iva', 'net_amount', 'net_fuel',
                            'sales_of_goods', 'sales_of_services', 'services_iva']].sum()
        totals = totals.to_dict()

        invoices.append({
            "type_doc": "",
            "num_doc": "",
            "tax_id": "",
            "customer": _("TOTALS"),
            "total": totals.get("total", 0.0),
            "amount": totals.get("amount", 0.0),
            "fuel_iva": totals.get("fuel_iva", 0.0),
            "goods_iva": totals.get("goods_iva", 0.0),
            "sales_of_goods": totals.get("sales_of_goods", 0.0),
            "sales_of_services": totals.get("sales_of_services", 0.0),
            "services_iva": totals.get("services_iva", 0.0),
            "net_amount": totals.get("net_amount", 0.0),
            "net_fuel": totals.get("net_fuel", 0.0),
            "currency": filters.company_currency
        })

        return invoices
    except:
        frappe.msgprint(_('Proceso no completado, no se encontraron facturas con item configurados como Bien, Servicio o Combustible'))
        return []

def sales_invoice_grouper(invoices, filters):
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
        frappe.msgprint(str(frappe.get_traceback()))
