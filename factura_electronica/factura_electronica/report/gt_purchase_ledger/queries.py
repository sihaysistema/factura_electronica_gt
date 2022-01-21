# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

# Si quieres obtener basado en fecha de recepcion usa `posting_date`
# en estos queries se esta usando `bill_date` fecha de la factura de compra

def purchase_invoices(filters):
    """
    Query para obtener datos sobre las facturas de compra de la base de datos
    en funcion a los filtros aplicados

    Args:
        filters (dict): Filtros aplicados en front end

    Returns:
        list: Lista diccionarios, cada dict hace referencia a una fila de la db
    """

    filters_query = ""  # base para construir las condicionales extras

    if filters.supplier:
        filters_query += f" AND supplier_name = '{filters.supplier}' "

    purchases = frappe.db.sql(
        f"""SELECT bill_date AS date, naming_series AS type_doc, name AS num_doc,
            facelec_nit_fproveedor AS tax_id, supplier_name AS supplier,
            (net_total * conversion_rate) AS purchases,
            (facelec_p_gt_tax_goods * conversion_rate) AS goods,
            (facelec_p_gt_tax_services * conversion_rate) AS services,
            (facelec_p_total_iva * conversion_rate) AS iva,
            (grand_total * conversion_rate ) AS total,
            '{filters.company_currency}' AS currency, currency AS currency_inv
            FROM `tabPurchase Invoice` WHERE company = '{filters.company}'
            AND docstatus=1 AND bill_date BETWEEN '{filters.from_date}'
            AND '{filters.to_date}' {filters_query}
        """, as_dict=True
    )

    return purchases


def purchase_invoices_weekly(filters):
    """
    Query para obtener datos sobre las facturas de compra de la base de datos por semana usando ISO 8601
    Usando las semanas que empiezan desde dia lunes.

    Mas detalles de YEARWEEK en: https://mysqlcode.com/mysql-yearweek/
    """

    # Al pasar el 1 a YEARWEEK, se obtiene el año y la semana de la fecha toma la semana que empieza desde lunes
    invoices = frappe.db.sql(
        f"""SELECT CONCAT(YEAR(PINV.bill_date), '-WK', WEEK(PINV.bill_date, 1)) AS week_repo,
        YEAR(PINV.bill_date) AS year_repo, WEEK(PINV.bill_date, 1) AS week_repo_no,
        SUM(PINV.grand_total * PINV.conversion_rate) AS total, PINV.currency AS currency_inv,
        '{filters.company_currency}' AS currency
        FROM `tabPurchase Invoice` AS PINV
        WHERE PINV.docstatus=1 AND PINV.company = '{filters.company}'
        AND YEARWEEK(PINV.bill_date, 1) BETWEEN YEARWEEK('{filters.from_date}', 1) AND YEARWEEK('{filters.to_date}', 1)
        GROUP BY week_repo ORDER BY year_repo, week_repo_no ASC;
        """, as_dict=True
    )

    # Debug: para ver la estructura de datos que retorna la consulta
    # with open("pi-weekly-from-db.json", "w") as f:
    #     f.write(json.dumps(invoices, indent=2, default=str))

    return invoices


def purchase_invoices_monthly(filters):
    """
    Obtiene los grand total de las facturas de venta mensualmente, basado en el rango de fechas
    que se seleccione
    """
    invoices = frappe.db.sql(
        f"""SELECT MONTH(PINV.bill_date) AS month_repo, YEAR(PINV.bill_date) AS year_repo,
        SUM(PINV.grand_total * PINV.conversion_rate) AS total, PINV.currency AS currency_inv,
        '{filters.company_currency}' AS currency
        FROM `tabPurchase Invoice` AS PINV
        WHERE PINV.docstatus=1 AND PINV.company = '{filters.company}'
        AND DATE_FORMAT(PINV.bill_date, '%Y%m') BETWEEN DATE_FORMAT('{filters.from_date}', '%Y%m') AND DATE_FORMAT('{filters.to_date}', '%Y%m')
        GROUP BY year_repo, month_repo ORDER BY year_repo, month_repo ASC;
        """, as_dict=True
    )

    # Debug: para ver la estructura de datos que retorna la consulta
    # with open("pi-monthly-from-db.json", "w") as f:
    #     f.write(json.dumps(invoices, indent=2, default=str))

    return invoices


def purchase_invoices_quarterly(filters):
    """
    Obtiene los grand total de las facturas de venta trimestral, basado en el rango de fechas
    que se seleccione

    https://mysqlcode.com/mysql-quarter/
    """
    invoices = frappe.db.sql(
        f"""SELECT QUARTER(PINV.bill_date) AS quarter_repo, YEAR(PINV.bill_date) AS year_repo,
        SUM(PINV.grand_total * PINV.conversion_rate) AS total, PINV.currency AS currency_inv,
        '{filters.company_currency}' AS currency
        FROM `tabPurchase Invoice` AS PINV
        WHERE PINV.docstatus=1 AND PINV.company = '{filters.company}'
        AND CONCAT(YEAR(PINV.bill_date), QUARTER(PINV.bill_date))
        BETWEEN
        CONCAT(YEAR('{filters.from_date}'), QUARTER('{filters.from_date}')) AND
        CONCAT(YEAR('{filters.to_date}'), QUARTER('{filters.to_date}'))
        GROUP BY year_repo, quarter_repo ORDER BY year_repo, quarter_repo ASC;
        """, as_dict=True
    )

    # Debug: para ver la estructura de datos que retorna la consulta
    # with open("pi-quarterly-from-db.json", "w") as f:
    #     f.write(json.dumps(invoices, indent=2, default=str))

    return invoices
