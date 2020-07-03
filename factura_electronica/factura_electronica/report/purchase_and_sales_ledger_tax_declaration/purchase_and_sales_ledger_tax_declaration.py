# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime
# from erpnext.accounts.report.utils import convert  # value, from_, to, date
import json

import pandas as pd

import frappe
from factura_electronica.factura_electronica.report.purchase_and_sales_ledger_tax_declaration.queries import *
from factura_electronica.utils.utilities_facelec import generate_asl_file, string_cleaner
from frappe import _, _dict, scrub
from frappe.utils import cstr, flt, get_site_name, nowdate


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    if len(data) > 0:
        status_file = generate_asl_file(data)
        if status_file[0] == True:
            with open('asl_report.json', 'w') as f:
                f.write(json.dumps(data, indent=2, default=str))

            frappe.msgprint(msg=_('Press the download button to get the ASL files'),
                            title=_('Successfully generated ASL report and file'), indicator='green')
            return columns, data
        else:
            frappe.msgprint(msg=_(f'More details in the following log \n {status_file[1]}'),
                            title=_('Sorry, a problem occurred while trying to generate the Journal Entry'), indicator='red')
            return columns, [{}]
    else:
        return columns, [{}]


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
            "label": _("Establecimiento"),
            "fieldname": "establecimiento",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Compras/Ventas"),
            "fieldname": "compras_ventas",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Documento"),
            "fieldname": "documento",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Serie del documento"),
            "fieldname": "serie_doc",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Número del documento"),
            "fieldname": "no_doc",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Fecha del documento"),
            "fieldname": "fecha_doc",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("NIT del cliente/proveedor"),
            "fieldname": "nit_cliente_proveedor",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Nombre del cliente/proveedor"),
            "fieldname": "nombre_cliente_proveedor",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Tipo de transacción"),
            "fieldname": "tipo_transaccion",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Tipo de Operación (Bien o Servicio)"),
            "fieldname": "tipo_ope",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Estado del documento"),
            "fieldname": "status_doc",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("No. de orden de la cédula, DPI o Pasaporte"),
            "fieldname": "no_orden_cedula_dpi_pasaporte",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("No. de registro de la cédula, DPI o Pasaporte"),
            "fieldname": "no_regi_cedula_dpi_pasaporte",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Tipo Documento de Operación"),
            "fieldname": "tipo_doc_ope",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Número del documento de Operación"),
            "fieldname": "no_doc_operacion",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Valor Gravado del documento, Bienes operación Local"),
            "fieldname": "total_gravado_doc_bien_ope_local",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Valor Gravado del documento, Bienes operación del Exterior"),
            "fieldname": "total_gravado_doc_bien_ope_exterior",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Valor Gravado del documento Servicios operación Local"),
            "fieldname": "total_gravado_doc_servi_ope_local",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Valor Gravado del documento Servicios operación del uso Exterior"),
            "fieldname": "total_gravado_doc_servi_ope_exterior",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Valor Exento del documento, Bienes operación Local"),
            "fieldname": "total_exento_doc_bien_ope_local",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Valor Exento del documento, Bienes operación del Exterior"),
            "fieldname": "total_exento_doc_bien_ope_exterior",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Valor Exento del documento, Servicios operación Local"),
            "fieldname": "total_exento_doc_servi_ope_local",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Valor Exento del documento, Servicios operación del Exterior"),
            "fieldname": "total_exento_doc_servi_ope_exterior",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Tipo de Constancia"),
            "fieldname": "tipo_constancia",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Número de la constancia de exención/adquisición de insumos/reten-ción del IVA"),
            "fieldname": "no_constancia_exension_adqui_insu_reten_iva",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Valor de la constancia de exención/adquisición de insumos/reten-ción del IVA"),
            "fieldname": "valor_constancia_exension_adqui_insu_reten_iva",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Pequeño Contribuyente Total Facturado Operación Local Bienes"),
            "fieldname": "peque_contri_total_facturado_ope_local_bienes",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Pequeño Contribuyente Total Facturado Operación Local Servicios"),
            "fieldname": "peque_contri_total_facturado_ope_local_servicios",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Pequeño Contribuyente Total Facturado Operación al Exterior Bienes"),
            "fieldname": "peque_contri_total_facturado_ope_exterior_bienes",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Pequeño Contribuyente Total Facturado Operación al Exterior Servicios"),
            "fieldname": "peque_contri_total_facturado_ope_exterior_servicios",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("IVA"),
            "fieldname": "iva",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Valor del Documento"),
            "fieldname": "total_valor_doc",
            "fieldtype": "Data",
            "width": 100,
        },
    ]

    return columns


def get_data(filters):
    """
    Procesador de datos obtenidos de la base de datos para mostrarlos correctamente
    en el reporte

    Args:
        filters (dict): Filtros front end

    Returns:
        list: Lista de diccionarios
    """

    data = []
    sales_invoices = get_sales_invoice(filters)
    purchase_invoices = get_purchases_invoice(filters)

    # Si existen datos
    if len(purchase_invoices) > 0:
        # Procesamos facturas de compra, por cada factura
        for purchase_invoice in purchase_invoices:
            # Validamos tipo de trasaccion
            column_i = validate_trasaction(purchase_invoice)
            # Actualizamos el valor del diccionario iterado
            purchase_invoice.update(column_i)

            # Column A: Establecimiento
            establ_comp = frappe.db.get_value('Address', {'name': purchase_invoice.get('company_address_invoice', '')},
                                              'facelec_establishment')
            purchase_invoice.update({'establecimiento': establ_comp})

            # Column E: Numero de factura, de name se pasara por una funcionq ue elimina string(letras)
            purchase_invoice.update({'no_doc': string_cleaner(purchase_invoice.get('documento'), opt=True)})

            # Column K: Si es compra, va vacio, si en el libro se incluyen ventas/compras y tiene descuento la factura
            # debe ir D, Si es venta ok E de emitido, si es factura de venta cancelada debe ir A de anulado
            purchase_invoice.update({'status_doc': validate_status_document(purchase_invoice)})


            # Column P, R Locales
            # Si la factura es local, obtenemos el monto de bienes en al factura
            # con iva incluido
            if column_i.get('tipo_transaccion') == 'L':
                # Actualizamos el valor de ... con el de bienes obtenido de la factura
                purchase_invoice.update({'total_gravado_doc_bien_ope_local': purchase_invoice.get('net_total')})

                # col r
                purchase_invoice.update({'total_gravado_doc_servi_ope_local': purchase_invoice.get('net_total')})

            # Columna Q, S: Si es exterior
            if column_i.get('tipo_transaccion') == 'E':
                # Actualizamos el valor de ... con el de bienes obtenido de la factura
                purchase_invoice.update({'total_gravado_doc_bien_ope_exterior': purchase_invoice.get('net_total')})

                # col S
                purchase_invoice.update({'total_gravado_doc_servi_ope_exterior': purchase_invoice.get('net_total')})


            data.append(purchase_invoice)

    # if len(sales_invoices) > 0:
    #     # Procesamos facturas de venta
    #     for sales_invoice in sales_invoices:
    #         pass
    #     data.extend(sales_invoices)

    return data


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

        # TODO: VERIFICAR QUE ES 'A' y 'T'

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
    # Valida el caso de facturas con descuentos, si lleva descuento es D
