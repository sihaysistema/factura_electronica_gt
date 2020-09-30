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
def validate_serie_to_special_invoice(naming_series):
    """
    Obtiene el name si existe una configuracion validada para factura electronica, para
    verificar si la serie que se esta usando el la factura de compra se puede usar
    para generar facturas especiales electronica

    Args:
        naming_series (str): Serie utilizada en la factura de compra

    Returns:
        boolean: True/False
    """
    try:
        # verifica que exista un documento validado, docstatus = 1 => validado
        if frappe.db.exists('Configuracion Factura Electronica', {'docstatus': 1}):

            configuracion_valida = frappe.db.get_values('Configuracion Factura Electronica',
                                                        filters={'docstatus': 1},
                                                        fieldname=['name', 'regimen'], as_dict=1)
            if (len(configuracion_valida) == 1):  # se encontro una sola configuracion OK

                if frappe.db.exists('Serial Configuration For Purchase Invoice',
                                   {'parent': str(configuracion_valida[0]['name']), 'serie': naming_series,
                                    'tipo_frase_factura_especial': '5 Frase de facturas especiales'}):
                    return True
                else:
                    return False

            elif (len(configuracion_valida) > 1):  # se encontro mas de una configuracion
                return False

        else:
            return False  # No se encoentro ninguna configuracion

    except:
        return False  # Por si acaso ocurre un error, no aplicara
