# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _

from factura_electronica.utils.utilities_facelec import normalizar_texto


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


@frappe.whitelist()
def validate_serie_to_special_invoice(naming_series, company=None):
    """
    Verifica si la serie de la factura de compra está habilitada para factura
    especial en la configuración activa de la compañía.

    Args:
        naming_series (str): Serie utilizada en la factura de compra
        company (str): Compañía del documento

    Returns:
        boolean: True/False
    """
    try:
        from factura_electronica.utils.fel_config import get_active_config_for_company

        result = get_active_config_for_company(company)
        if not result.get("ok"):
            return False

        return bool(frappe.db.exists(
            'Serial Configuration For Purchase Invoice',
            {
                'parent': result.get("name"),
                'serie': naming_series,
                'tipo_frase_factura_especial': '5 Frase de facturas especiales',
            },
        ))

    except Exception:
        return False
