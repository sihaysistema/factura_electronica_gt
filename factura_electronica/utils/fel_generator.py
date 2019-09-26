# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime
from factura_electronica.utils.utilities_facelec import normalizar_texto
import json, xmltodict
import base64

def generar_fac_fel():
    
    # Obtener data emisor
    try:
        sales_invoice = frappe.db.get_values('Sales Invoice',
                                             filters={'name': serie_original_factura},
                                             fieldname=['name', 'idx', 'territory',
                                                       'grand_total', 'customer_name', 'company',
                                                       'company_address', 'naming_series', 'creation',
                                                       'status', 'discount_amount', 'docstatus',
                                                       'modified', 'conversion_rate',
                                                       'total_taxes_and_charges', 'net_total',
                                                       'shipping_address_name', 'customer_address',
                                                       'total', 'shs_total_iva_fac', 'currency'],
                                             as_dict=1)
    except:
        pass
    else:
        pass

    # Obtener data receptor - cliente facturado
    try:
        sales_invoice = frappe.db.get_values('Sales Invoice',
                                             filters={'name': serie_original_factura},
                                             fieldname=['name', 'idx', 'territory',
                                                       'grand_total', 'customer_name', 'company',
                                                       'company_address', 'naming_series', 'creation',
                                                       'status', 'discount_amount', 'docstatus',
                                                       'modified', 'conversion_rate',
                                                       'total_taxes_and_charges', 'net_total',
                                                       'shipping_address_name', 'customer_address',
                                                       'total', 'shs_total_iva_fac', 'currency'],
                                             as_dict=1)
    except:
        pass
    else:
        pass

    # Obtner data configuracion
    try:
        sales_invoice = frappe.db.get_values('Sales Invoice',
                                             filters={'name': serie_original_factura},
                                             fieldname=['name', 'idx', 'territory',
                                                       'grand_total', 'customer_name', 'company',
                                                       'company_address', 'naming_series', 'creation',
                                                       'status', 'discount_amount', 'docstatus',
                                                       'modified', 'conversion_rate',
                                                       'total_taxes_and_charges', 'net_total',
                                                       'shipping_address_name', 'customer_address',
                                                       'total', 'shs_total_iva_fac', 'currency'],
                                             as_dict=1)
    except:
        pass
    else:
        pass

    # Obtener data items

    # Obtneer data factura