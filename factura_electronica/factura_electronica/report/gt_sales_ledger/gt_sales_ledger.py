# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime
import json

import frappe
import pandas as pd
from frappe import _
from frappe.utils import flt, get_site_name, now
from frappe.utils.file_manager import save_file

from factura_electronica.factura_electronica.report.gt_sales_ledger.queries import (sales_invoices, sales_invoices_monthly,
                                                                                    sales_invoices_quarterly,
                                                                                    sales_invoices_weekly)
from factura_electronica.utils.utilities_facelec import create_folder, save_excel_data

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

        # Conversion fechas filtro a objetos date para realizar validaciones
        start_d = datetime.datetime.strptime(filters.from_date, "%Y-%m-%d")  # en formato date
        final_d = datetime.datetime.strptime(filters.to_date, "%Y-%m-%d")

        # Validaciones de fechas
        if (start_d < final_d) or (final_d == start_d):
            columns_data_db = ['total']
            data = []
            invoices_db = []

            if filters.options == "No Subtotal":
                columns = get_columns()
                # Se obtienen los datos de las facturas de venta
                invoices_db = sales_invoices(filters)
                # Se procesa la data de la db y los totales
                data = process_data_db(filters, invoices_db)

            if filters.options == "Weekly":
                columns = get_columns_weekly_report()
                # Se obtienen los datos de las facturas de venta Semanalmente
                invoices_db = sales_invoices_weekly(filters)
                df_inv = pd.DataFrame.from_dict(json.loads(json.dumps(invoices_db, default=str)))
                data = calculate_total(df_inv, columns_data_db, filters, 'week_repo')

            if filters.options == "Monthly":
                columns = get_columns_monthly_report()
                # Se obtienen los datos de las facturas de venta Mensualmente
                invoices_db = sales_invoices_monthly(filters)

                # Formatea y traduce la columna mes para reporte mensual: Se puede optimizar un poco mas haciendolo con pandas la diferencia es de milisegundos
                [invoice.update({"month": f"{invoice.get('year_repo')} {_(MONTHS[invoice.get('month_repo')-1], lang=filters.language)}"}) for invoice in invoices_db]
                df_inv = pd.DataFrame.from_dict(json.loads(json.dumps(invoices_db, default=str)))
                data = calculate_total(df_inv, columns_data_db, filters, 'month')

            if filters.options == "Quarterly":
                columns = get_columns_quarterly_report()
                # Se obtienen los datos de las facturas de venta Semestralmente
                invoices_db = sales_invoices_quarterly(filters)

                # Formatea y traduce la columna mes para reporte mensual: Se puede optimizar un poco mas haciendolo con pandas la diferencia es de milisegundos
                [invoice.update({"quarter": f"{invoice.get('year_repo')} {_(QUARTERS[invoice.get('quarter_repo')-1], lang=filters.language)}"}) for invoice in invoices_db]
                df_inv = pd.DataFrame.from_dict(json.loads(json.dumps(invoices_db, default=str)))
                data = calculate_total(df_inv, columns_data_db, filters, 'quarter')

            if not data: return columns, []

            # Debug: datos de reporte
            # with open("res-gt-sales-ledger.json", 'w') as f:
            #     f.write(json.dumps(data, indent=2, default=str))

            return columns, data

        else:
            return [], []
    except:
        frappe.msgprint(
            msg=f"{_('If the error persists please report it. Details:')} <br><hr> <code>{frappe.get_traceback()}</code>",
            title=_('Uncompleted Task'), indicator='red'
            # raise_exception=True
        )
        return [], []


def get_columns():
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
            "width": 300,
            # "hidden": 1
        }
    ]

    return columns


def get_columns_weekly_report():
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


def get_columns_monthly_report():
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


def get_columns_quarterly_report():
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
            "width": 200
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

        # Parsea los datos para no manejar objetos date desde `invoices`
        invoices = json.loads(json.dumps(data_db, default=str))

        # Reintegrarlo si lo pide AG
        # Si la opcion check esta marcada, agrupara toda la data
        # if filters.group:
        #     return sales_invoice_grouper(invoices, filters)

        # Se obtiene el dominio configurado para armar la url
        site_erp = get_site_name(frappe.local.site)

        # Los datos se cargan a un df
        df_inv = pd.DataFrame.from_dict(invoices)

        # Crea una columna con las referencias de pagos (si existen)
        df_inv['accounting_document'] = df_inv['num_doc'].apply(lambda x: get_payment_ref(x))

        return calculate_total(df_inv, columns, filters, 'customer')

    except:
        frappe.msgprint(
            msg=f'No se encontraron facturas con item configurados como Bien, Servicio o Combustible',
            title=_(f'No hay datos disponibles'),
            raise_exception=True
        )
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

        # Agrupamos y sumamos por type_doc ya que se obtienen datos
        # de tabla hija
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
        frappe.msgprint(
            msg=f'Detalle del error <br><hr> <code>{frappe.get_traceback()}</code>',
            title=_(f'No se pudo agrupar correctamente la data'),
            raise_exception=True
        )


def calculate_total(data, columns, filters, key_total):
    """Obtiene el total de cada columna que se le especifique

    Args:
        data (DataFrame): Dataframe con datos de la db
        columns (list): Lista columnas a totalizar
        filters (dict): Filtros frontend
        type_report (str, optional): Tipo de reporte. Defaults to "Default".

    Returns:
        list: Lista diccionarios con datos + fila total a mostrar en reporte
    """

    df_inv = data

    # Se totalizan las columnas numericas
    totals = df_inv[list(columns)].sum()
    # El resultado es un objeto de tipo Series se convierte a df y se aplica transpuesta
    # para que coincidan las columnas
    totals = totals.to_frame().T
    # Se agrega la descripcion TOTALES a la columna que se le especifique
    totals[key_total] = f"<span style='font-weight: bold'>{_('TOTALS')}</span>"
    # Se especifica la moneda default de la compañia ya los montos estan convertidos
    totals['currency'] = filters.company_currency

    # Se aplica el redondeo de decimales definida por `PRECISION`
    df_inv[columns] = df_inv[columns].apply(lambda x: round(x, PRECISION))
    totals[columns] = totals[columns].apply(lambda x: round(x, PRECISION))

    # Conversion a diccionario
    ok_data = df_inv.to_dict(orient='records')
    ok_data.extend(totals.to_dict(orient='records'))

    return ok_data


def save_json_data(file_name, content, to_dt, to_dn, folder, is_private):
    """Guarda los datos del reporte como archivo .JSON que se adjunta
    al Doctype Prepared Report Facelec de Factura Electronica

    Args:
        file_name (str): Nombre para el archivo
        content (json): Datos que contendra el archivo
        to_dt (str): Nombre Doctype
        to_dn (str): Nombre Docname `name`
        folder (str): Path destino
        is_private (int): 1 privado ! publico

    Returns:
        Object: datos de archivo creado de Doctype File
    """
    return save_file(file_name, content, to_dt, to_dn, folder=folder, is_private=is_private)


@frappe.whitelist()
def generate_report_files(data, col_idx, filters, report_name, f_type="JSON", r_name="GT Sales Ledger"):
    """Genera y guarda archivos, se consume desde el reporte `gt-sales-ledger` y `gt-purchase-ledger`

    Args:
        data (list): Datos de reporte recien generado
        f_type (str, optional): str. Tipo de archivo a generar/guardar to "JSON".

    Returns:
        tuple: details
    """

    OPTIONS = {
        "No Subtotal": "date", # Sales
        "Detailed": "date", # Purchases
        "Weekly": "week_repo",
        "Monthly": "month",
        "Quarterly": "quarter"
    }

    try:
        # Se carga la data del reporte
        data = json.loads(data)

        # Se crea un registro en Prepared Report Facelec para adjuntar los archivos
        # que se generen
        new_doc = frappe.new_doc('Prepared Report Facelec')
        new_doc.filters = json.dumps(json.loads(filters), default=str)
        new_doc.report_name = report_name
        new_doc.insert(ignore_permissions=True)

        # Se crea el carpeta donde se almacenaran los reportes generados
        # Si ya existe se retorna el path de la carpeta
        doctype_folder = create_folder(new_doc.doctype)
        to_doctype = new_doc.doctype
        to_name = new_doc.name

        # Se genera y guarda el archivo .json
        if f_type == "JSON":
            formato = ".json"
            file_name = f"{r_name} {col_idx} {now()}{formato}"
            content = json.dumps(data, indent=2, default=str)
            saved_file = save_json_data(file_name, content, to_doctype, to_name, doctype_folder, 1)

        # Se genera y guarda el archivo tipo .xlsx Excel
        if f_type == "Excel":
            file_name = f"{r_name} {col_idx}"
            saved_file = save_excel_data(file_name, data, to_doctype, to_name, doctype_folder, 1, OPTIONS.get(col_idx))

        return True, saved_file.file_url

    except:
        frappe.msgprint(
            msg=f'Si la falla persiste, por favor reportelo con soporte. Detalle del error <br><hr> <code>{frappe.get_traceback()}</code>',
            title=_(f'Archivo {f_type} no pudo ser generado'),
            raise_exception=True
        )

        return False, None


def get_payment_ref(ref_inv):
    """Busca referenicas de pagos"""
    # Agregamos las referencias, puede ser de Payment Entry o Journal Entry
    # Esto aplica si la factura tiene enlace con Payment Entry o Journal Entry

    ref_per = frappe.db.get_values('Payment Entry Reference', filters={'reference_name': ref_inv, 'docstatus': 1},
                                   fieldname=['parent'], as_dict=1)
    ref_je = frappe.db.get_values('Journal Entry Account', filters={'reference_name': ref_inv, 'docstatus': 1},
                                  fieldname=['parent'], as_dict=1)

    link_ref = ''

    # Si aplica se generan los link a Payment Entry o Journal Entry
    for i in ref_per:
        if i.get("parent"):
            link_ref += f'''<a class="btn-open no-decoration" href="/app/payment-entry/{i.get('parent')}" target="_blank">{i.get("parent")}</a>, '''
            # link_ref = f'https://{site_erp}/app/payment-entry/{ref_per}'  # para v13

    for i in ref_je:
        if i.get("parent"):
            link_ref += f'''<a class="btn-open no-decoration" href="/app/journal-entry/{i.get('parent')}" target="_blank">{i.get("parent")}</a>, '''
            # link_ref = f'https://{site_erp}/app/journal-entry/{ref_je}'

    return link_ref
