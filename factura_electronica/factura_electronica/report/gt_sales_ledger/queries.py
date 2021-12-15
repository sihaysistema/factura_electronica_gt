# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import json
from frappe import _

# INFO: https://dev.mysql.com/doc/refman/8.0/en/date-and-time-functions.html

def sales_invoices(filters):
    """
    Query para obtener datos sobre las facturas de venta de la base de datos.
    Especificamente obtiene todas las facturas y de las facturas sus items, todo
    esto en funcion al rango de fechas, company, cliente seleccionados en el front end.

    Args:
        filters (dict): Filtros aplicados en front end

    Returns:
        tuple: Lista diccionarios, cada dict hace referencia a una fila de la db, Facturas,
               Items de facturas
    """

    filters_query = ""

    # Si se selecciona un especifico cliente
    if filters.customer:
        filters_query += f" AND SI.customer = '{filters.customer}' "

    # LEGACY CODE: YA NO USAR :D SE DEJA COMENTADO PARA REFERENCIAS
    # Facturas
    # invoices = frappe.db.sql(
    #     f"""SELECT DISTINCT name AS num_doc, posting_date AS date, naming_series AS type_doc,
    #         nit_face_customer AS tax_id, customer, grand_total AS total, currency
    #         FROM `tabSales Invoice` WHERE docstatus=1 AND company = '{filters.company}'
    #         AND posting_date BETWEEN '{filters.from_date}'
    #         AND '{filters.to_date}' {filters_query}
    #     """, as_dict=True
    # )

    # # Items de Facturas
    # items = frappe.db.sql(
    #     f"""SELECT DISTINCT parent, docstatus, net_amount, amount, facelec_is_good AS is_good,
    #         facelec_is_service AS is_service, factelecis_fuel AS is_fuel,
    #         facelec_sales_tax_for_this_row AS tax_for_item, facelec_gt_tax_net_fuel_amt AS net_fuel,
    #         facelec_gt_tax_net_goods_amt AS net_good, facelec_gt_tax_net_services_amt AS net_service,
    #         facelec_amount_minus_excise_tax AS minus_excise_tax, facelec_other_tax_amount As other_tax
    #         FROM `tabSales Invoice Item` WHERE parent
    #         IN (SELECT DISTINCT name FROM `tabSales Invoice` WHERE docstatus=1 AND
    #         company = '{filters.company}' AND posting_date BETWEEN '{filters.from_date}'
    #         AND '{filters.to_date}' {filters_query})
    #     """, as_dict=True
    # )

    invoices = frappe.db.sql(
        f"""
        SELECT SI.name AS num_doc,
        SI.posting_date AS date, SI.naming_series AS type_doc,
        SI.nit_face_customer AS tax_id, SI.customer, SI.grand_total AS total,
        SI.currency, SUM(SII.net_amount) AS net_amount, SUM(SII.amount) AS amount,
        SUM(IF(SII.facelec_is_good=1, SII.facelec_sales_tax_for_this_row, 0)) AS goods_iva,
        SUM(IF(SII.facelec_is_service=1, SII.facelec_sales_tax_for_this_row, 0)) AS services_iva,
        SUM(IF(SII.factelecis_fuel=1, SII.facelec_sales_tax_for_this_row, 0)) AS fuel_iva,
        0 AS exempt_sales,
        SUM(SII.facelec_gt_tax_net_fuel_amt) AS net_fuel,
        SUM(SII.facelec_gt_tax_net_goods_amt) AS sales_of_goods,
        SUM(SII.facelec_gt_tax_net_services_amt) AS sales_of_services,
        SUM(SII.facelec_amount_minus_excise_tax) AS minus_excise_tax, SUM(SII.facelec_other_tax_amount) As other_tax
        FROM `tabSales Invoice` AS SI
        JOIN `tabSales Invoice Item` AS SII
        ON SI.NAME = SII.parent
        WHERE SI.docstatus=1 AND SI.company = '{filters.company}'
        AND SI.posting_date BETWEEN '{filters.from_date}' AND '{filters.to_date}'
        {filters_query} GROUP BY SI.name ORDER BY SI.posting_date ASC
        """, as_dict=True
    )

    # Debug: para ver la estructura de datos que retorna la consulta
    # with open("from-db.json", "w") as f:
    #     f.write(json.dumps(invoices, indent=2, default=str))

    return invoices # , items


def sales_invoices_weekly(filters):
    """
    Query para obtener datos sobre las facturas de venta de la base de datos.
    Especificamente obtiene todas las facturas y de las facturas sus items, todo
    esto en funcion al rango de fechas, company, cliente seleccionados en el front end.

    Segun las fechas especificadas se obtendran las semanas y se usan como filtros
    las semanas se toman que empiezan dia lunes usando ISO 8601

    Mas detalles de YEARWEEK en: https://mysqlcode.com/mysql-yearweek/
    """

    # Al pasar el 1 a YEARWEEK, se obtiene el año y la semana de la fecha toma la semana que empieza desde lunes

    # v1 - no ordena correctamente
    # invoices = frappe.db.sql(
    #     f"""
    #     SELECT CONCAT(YEAR(SI.posting_date), '-WK', WEEK(SI.posting_date, 1)) AS week_repo,
    #     SUM(SI.grand_total) AS total, SI.currency
    #     FROM `tabSales Invoice` AS SI
    #     WHERE SI.docstatus=1 AND SI.company = '{filters.company}'
    #     AND YEARWEEK(SI.posting_date, 1) BETWEEN YEARWEEK('{filters.from_date}', 1) AND YEARWEEK('{filters.to_date}', 1)
    #     GROUP BY week_repo, currency ORDER BY week_repo ASC;
    #     """, as_dict=True
    # )

    # v2 Si ordena correctamente ASC
    invoices = frappe.db.sql(
        f"""
        SELECT CONCAT(YEAR(SI.posting_date), '-WK', WEEK(SI.posting_date, 1)) AS week_repo,
        YEAR(SI.posting_date) AS year_repo, WEEK(SI.posting_date, 1) AS week_repo_no,
        SUM(SI.grand_total) AS total, SI.currency
        FROM `tabSales Invoice` AS SI
        WHERE SI.docstatus=1 AND SI.company = '{filters.company}'
        AND YEARWEEK(SI.posting_date, 1) BETWEEN YEARWEEK('{filters.from_date}', 1) AND YEARWEEK('{filters.to_date}', 1)
        GROUP BY week_repo, SI.currency ORDER BY year_repo, week_repo_no  ASC;
        """, as_dict=True
    )

    # Debug: para ver la estructura de datos que retorna la consulta
    # with open("weekly-from-db.json", "w") as f:
    #     f.write(json.dumps(invoices, indent=2, default=str))

    return invoices


def sales_invoices_monthly(filters):
    """
    Obtiene los grand total de las facturas de venta mensualmente, basado en el rango de fechas
    que se seleccione
    """
    invoices = frappe.db.sql(
        f"""
        SELECT MONTH(SI.posting_date) AS month_repo, YEAR(SI.posting_date) AS year_repo,
        SUM(SI.grand_total) AS total, SI.currency
        FROM `tabSales Invoice` AS SI
        WHERE SI.docstatus=1 AND SI.company = '{filters.company}'
        AND DATE_FORMAT(SI.posting_date, '%Y%m') BETWEEN DATE_FORMAT('{filters.from_date}', '%Y%m') AND DATE_FORMAT('{filters.to_date}', '%Y%m')
        GROUP BY year_repo, month_repo, currency ORDER BY year_repo, month_repo ASC;
        """, as_dict=True
    )

    # Debug: para ver la estructura de datos que retorna la consulta
    # with open("monthly-from-db.json", "w") as f:
    #     f.write(json.dumps(invoices, indent=2, default=str))

    return invoices


def sales_invoices_quarterly(filters):
    """
    Obtiene los grand total de las facturas de venta trimestral, basado en el rango de fechas
    que se seleccione

    https://mysqlcode.com/mysql-quarter/
    """
    invoices = frappe.db.sql(
        f"""
        SELECT QUARTER(SI.posting_date) AS quarter_repo, YEAR(SI.posting_date) AS year_repo,
        SUM(SI.grand_total) AS total, SI.currency
        FROM `tabSales Invoice` AS SI
        WHERE SI.docstatus=1 AND SI.company = '{filters.company}'
        AND CONCAT(YEAR(SI.posting_date), QUARTER(SI.posting_date))
        BETWEEN
        CONCAT(YEAR('{filters.from_date}'), QUARTER('{filters.from_date}')) AND
        CONCAT(YEAR('{filters.to_date}'), QUARTER('{filters.to_date}'))
        GROUP BY year_repo, quarter_repo, currency ORDER BY year_repo, quarter_repo ASC;
        """, as_dict=True
    )

    # Debug: para ver la estructura de datos que retorna la consulta
    # with open("quarterly-from-db.json", "w") as f:
    #     f.write(json.dumps(invoices, indent=2, default=str))

    return invoices
