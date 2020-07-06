# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import pandas as pd

import frappe
from factura_electronica.factura_electronica.report.purchase_and_sales_ledger_tax_declaration.queries import *
from factura_electronica.utils.utilities_facelec import generate_asl_file, string_cleaner, validar_configuracion
from frappe import _
from frappe.utils import cstr, flt


def validate_trasaction(invoice):
    """
    Validaciones para la columna I

    Args:
        invoice ([type]): [description]
    """

    try:
        venta_o_compra = invoice.get('compras_ventas')
        company_country = frappe.db.get_value('Company', {'name': invoice.get('company')}, 'country')

        invoice_country = frappe.db.get_value('Address', {'name': invoice.get('invoice_address')},
                                            'country') or "Guatemala"

        # Local
        if ((company_country == 'Guatemala' and invoice_country == 'Guatemala')
            and (venta_o_compra == 'C' or venta_o_compra == 'V')):
            return {'tipo_transaccion': 'L'}

        # Exportacion
        if ((company_country == 'Guatemala' and invoice_country != 'Guatemala')
            and (venta_o_compra == 'V')):
            return {'tipo_transaccion': 'E'}

        # Importacion
        if ((company_country == 'Guatemala' and invoice_country != 'Guatemala')
            and venta_o_compra == 'C'):
            return {'tipo_transaccion': 'I'}

        # TODO: A=ADQUISICION, T=TRANSFERENCIA

        # Si no se aplica ningu escenario anterior se retorna como Local
        return {'tipo_transaccion': 'L'}

    except:
        # Si no hay direccion usamos como default Local
        return {'tipo_transaccion': 'L'}


def validate_status_document(invoice):
    """
    Valida el estado de la factura, puede ser Emitida, Anulada, o con Descuentos

    Args:
        invoice (dict): Factura iterada

    Returns:
        str: Escenario aplicado
    """

    # Si es compra, se deja vacio
    if invoice.get('compras_ventas') == 'C':
        return ''

    # Si es venta y esta validada, se retorna como E de Emitida
    if invoice.get('compras_ventas') == 'V' and invoice.get('docstatus') == 1:
        return 'E'

    # Si es venta y esta cancelada, se retorna como A de Anulada
    if invoice.get('compras_ventas') == 'V' and invoice.get('docstatus') == 2:
        return 'A'

    return ''
    # Validar el caso de facturas con descuentos, si lleva descuento es D


def validate_serie(naming_serie):
    """
    Busca el tipo de documento relacionado a la serie usado en la factura venta/compra
    esto en configuraciones de series de factura electronica

    Args:
        naming_serie (str): Serie utilizada en factura compra/venta

    Returns:
        str: Documento SAT
    """

    # Obtenemos datos y status de la configuracion para factura electroncia
    status_config_facelec =  validar_configuracion()

    # Si se encuentra una configuracion valida
    if status_config_facelec[0] == 1:
        name_conf = status_config_facelec[1]

        # Obtnemos el tipo de documento para la serie utilizada en la factura
        # Primero buscamos para las facturas de venta
        doc_ok_invoice = frappe.db.get_value('Configuracion Series FEL',
                                            {'parent': name_conf, 'serie': naming_serie},
                                             'serie_sat')

        # Buscamos para las facturas de compra
        if not doc_ok_invoice:
            doc_ok_invoice = frappe.db.get_value('Serial Configuration For Purchase Invoice',
                                                {'parent': name_conf, 'serie': naming_serie},
                                                 'serie_sat')

        return doc_ok_invoice

    else:
        return ''


def validate_document_serie(invoice_name):
    """
    Valida la serie utilizada en la factura venta/compra, primero en Envios FEL
    donde hay registros de factura electronica

    Args:
        invoice_name (str): name Factura venta/compra

    Returns:
        str: Serie de la Factura
    """
    # En el caso de documento electronicos, si se encuentra registrados en envio
    # se utilizara la serie y numero
    if frappe.db.exists('Envio FEL', {'serie_para_factura': invoice_name}):
        serie = frappe.db.get_value('Envio FEL', {'serie_para_factura': invoice_name}, 'serie')

        return True, serie

    else:
        return False, 'No encontrada'


def validate_document_number(invoice_name):
    """
    Valida el numero utilizado en la factura venta/compra, primero en Envios FEL
    donde hay registros de factura electronica

    Args:
        invoice_name (str): name Factura compra/venta

    Returns:
        str: Numero de factura
    """

    # En el caso de documento electronicos, si se encuentra registrados en envio
    # se utilizara la serie y numero
    if frappe.db.exists('Envio FEL', {'serie_para_factura': invoice_name}):
        numero = frappe.db.get_value('Envio FEL', {'serie_para_factura': invoice_name}, 'numero')

        return True, numero

    else:
        return False, 'No encontrado'


def validate_invoice_of_goods_or_services(invoice_name):
    """
    Valida si la factura es de bien o servicios, en funcion a la cantidad
    de items de servicios o bienes

    Args:
        invoice_name (str): name Factura compra/venta

    Returns:
        str: BIEN, SERVICIO O string vacio
    """

    items = get_items_purchase_invoice(invoice_name)

    # Cargamos a un dataframe
    df = pd.read_json(json.dumps(items))

    # Obtenemos todos los registros que sean bienes, luego hacemos un conteo
    # y luego obtenemos solamente el conteo del campo que nos interesa
    subset_goods = df[df["is_good"] == 1].count().is_good

    subset_services = df[df["is_service"] == 1].count().is_service

    # Verificamos el mayor
    if int(subset_goods) > int(subset_services):
        return 'BIEN'

    elif int(subset_services) > int(subset_goods):
        return 'SERVICIOS'

    else:
        return ''


def validate_if_exempt(template_tax_name='', purchase_or_sale='V'):
    if not template_tax_name:
        return 0

    if purchase_or_sale == 'V':
        is_exempt = frappe.db.get_value('Sales Taxes and Charges Template',
                                        {'name': template_tax_name}, 'facelec_is_exempt')
        return is_exempt

    if purchase_or_sale == 'C':
        is_exempt = frappe.db.get_value('Purchase Taxes and Charges Template',
                                        {'name': template_tax_name}, 'facelec_is_exempt')
        return is_exempt

    # Si no se cumplete ninguna de la anterior retornamos que no es exenta
    return 0
