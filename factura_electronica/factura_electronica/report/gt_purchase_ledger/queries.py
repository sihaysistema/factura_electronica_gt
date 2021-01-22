# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


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

    # Si quieres obtener basado en fecha de recepcion usa `posting_date`
    # en este query se esta usando `bill_date` fecha de la factura de compra

    purchases = frappe.db.sql(
        f"""SELECT bill_date AS date, naming_series AS type_doc, name AS num_doc,
            facelec_nit_fproveedor AS tax_id, supplier_name AS supplier,
            net_total AS purchases, facelec_p_gt_tax_services AS services,
            facelec_p_total_iva AS iva, grand_total AS total, currency
            FROM `tabPurchase Invoice` WHERE company = '{filters.company}'
            AND docstatus=1 AND bill_date BETWEEN '{filters.from_date}'
            AND '{filters.to_date}' {filters_query}
        """, as_dict=True
    )

    return purchases
