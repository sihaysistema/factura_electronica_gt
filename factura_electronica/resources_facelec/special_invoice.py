# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _

from utilities_facelec import normalizar_texto


@frappe.whitelist()
def verificar_existencia_series(serie):
    """Se encarga de verificar existencia de series configuradas para Purchase Invoice.
        Retorna las series configuradas y las cuentas de la plantilla de impuestos con
        sus valores"""

    # Verifica la existencia de la serie recibida en Single DT
    if frappe.db.exists('Series Factura Especial', {'serie': serie, 'parent': 'Impuestos Especiales'}):
        # Obtiene los campos de Series Factura Especial
        series_especiales = frappe.db.get_values('Series Factura Especial',
                                                filters={'serie': serie, 'parent': 'Impuestos Especiales'},
                                                fieldname=['serie', 'rate_isr', 'account_iva_credito',
                                                           'account_isr_por_pagar'], as_dict=1)

        # Guarda el nombre de la plantilla de impuestos configurada en Single DT
        plantilla_impuesto = frappe.db.get_single_value('Impuestos Especiales', 'plantilla_impuestos', cache=False)

        # Obtiene las cuentas y sus valores que se cargaran en Purchase Taxes and Charges de Purchase Invoice
        impuestos = frappe.db.get_values('Purchase Taxes and Charges',
                                        filters={'parent': str(plantilla_impuesto)},
                                        fieldname=['rate', 'account_head', 'description'])

        return series_especiales, impuestos, plantilla_impuesto
        
    else:
        # Mensaje alternativo
        # frappe.msgprint(_('No se encontraron series configuradas para Facturas Especiales'))
        return 'fail'
