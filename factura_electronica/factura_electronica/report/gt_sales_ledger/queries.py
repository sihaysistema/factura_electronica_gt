# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import json
from frappe import _


def sales_invoices(filters):
    """
    Query para obtener datos sobre las facturas de venta de la base de datos.
    Especificamente obtiene todas las facturas y de las facturas sus items, todo
    esto en funcion al rango de fechas seleccionadas en el front end.

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

    # LEGACY CODE: YA NO USAR :D
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
        SELECT SI.name AS num_doc, SI.posting_date AS date, SI.naming_series AS type_doc,
        SI.nit_face_customer AS tax_id, SI.customer, SI.grand_total AS total, SI.currency,
        SUM(SII.net_amount) AS net_amount, SUM(SII.amount) AS amount, SII.facelec_is_good AS is_good,
        SII.facelec_is_service AS is_service, SII.factelecis_fuel AS is_fuel,
        SUM(SII.facelec_sales_tax_for_this_row) AS tax_for_item, SUM(SII.facelec_gt_tax_net_fuel_amt) AS net_fuel,
        SUM(SII.facelec_gt_tax_net_goods_amt) AS net_good, SUM(SII.facelec_gt_tax_net_services_amt) AS net_service,
        SUM(SII.facelec_amount_minus_excise_tax) AS minus_excise_tax, SUM(SII.facelec_other_tax_amount) As other_tax
        FROM `tabSales Invoice` AS SI
        JOIN `tabSales Invoice Item` AS SII
        ON SI.NAME = SII.parent
        WHERE SI.docstatus=1 AND SI.company = '{filters.company}'
        AND SI.posting_date BETWEEN '{filters.from_date}'
        AND '{filters.to_date}' {filters_query} GROUP BY SI.name
        """, as_dict=True
    )

    with open("from-db.json", "w") as f:
        f.write(json.dumps(invoices, indent=2, default=str))

    return invoices # , items
