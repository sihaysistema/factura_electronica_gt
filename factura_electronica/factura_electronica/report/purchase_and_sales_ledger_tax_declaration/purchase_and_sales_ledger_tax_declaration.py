# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime
# from erpnext.accounts.report.utils import convert  # value, from_, to, date
import json

import pandas as pd

import frappe
from factura_electronica.factura_electronica.report.purchase_and_sales_ledger_tax_declaration.queries import *
from factura_electronica.factura_electronica.report.purchase_and_sales_ledger_tax_declaration.validators import *
from factura_electronica.utils.utilities_facelec import generate_asl_file, string_cleaner, validar_configuracion
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

    processed_purchase_invoices = process_purchase_invoices(purchase_invoices)
    data.extend(processed_purchase_invoices)

    processed_sales_invoices = process_sales_invoices(sales_invoices)
    data.extend(processed_sales_invoices)

    return data


def process_sales_invoice_items(invoice_name):
    pass


def process_purchase_invoice_items(invoice_name):
    """
    Obtiene el monto total de bienes y servicios, iva incluido

    Args:
        invoice_name (list): Lista de diccionarios con los items de factura

    Returns:
        dict: total de bien y servicio
    """

    try:
        # Obtenemos items de las facturas de compra, segun su parent = name
        items = get_items_purchase_invoice(invoice_name)

        # Cargamos a un dataframe
        df_items = pd.read_json(json.dumps(items))

        # Localizamos aquellos items que sean bienes, y lo sumamos
        sum_goods = (df_items.loc[df_items['is_good'] == 1].sum()).to_dict()
        frappe.msgprint(sum_goods)

        # Localizamos aquellos items que sean servicios, y lo sumamos
        sum_services = (df_items.loc[df_items['is_service'] == 1].sum()).to_dict()

        # Solo para DEBUG: si quieres ver la estructura de datos descomenta
        # with open('sum_service.json', 'w') as f:
        #     f.write(json.dumps(sum_services, indent=2))

        # with open('sum_good.json', 'w') as f:
        #     f.write(json.dumps(sum_goods, indent=2))

        return {
            'goods': sum_goods.get('amount', 0),
            'services': sum_services.get('amount', 0)
        }

    except:  # Si por alguna razon ocurre error, posiblemente item no configurado retornamos cero
        # frappe.msgprint(frappe.get_traceback())

        return {
            'goods': 0,
            'services': 0
        }


def process_purchase_invoices(purchase_invoices):
    """
    Procesa todas facturas de compra, asignando correctamente a un diccionario
    los datos necesarios para mostrar en reporte

    Args:
        purchase_invoices (list): Lista diccionarios con data db

    Returns:
        list: lista diccionarios datos procesados
    """

    data = []

    # Si existen datos
    if len(purchase_invoices) > 0:
        # Procesamos facturas de compra, por cada factura
        for purchase_invoice in purchase_invoices:
            inv_name = purchase_invoice.get('documento')

            # Column I: OK
            # Validamos tipo de trasaccion
            column_i = validate_trasaction(purchase_invoice)
            # Actualizamos el valor del diccionario iterado
            purchase_invoice.update(column_i)

            # Column A: Establecimiento - OK
            establ_comp = frappe.db.get_value('Address', {'name': purchase_invoice.get('company_address_invoice', '')},
                                              'facelec_establishment')
            purchase_invoice.update({'establecimiento': establ_comp})

            # Column B: Compras/Ventas (ya viene procesado de la base de datos) C o V, OK

            # Column C: Documento, OK
            document_inv = validate_serie(purchase_invoice.get('serie_doc'))
            purchase_invoice.update({'documento': document_inv})

            # Column D, Serie del documento, OK
            # Primero se validara en envios FEL, si no existe se usara la data que ya viene procesada de db
            serie_docu = validate_document_serie(inv_name)
            if serie_docu[0] == True:
                purchase_invoice.update({'serie_doc': serie_docu[1]})

            # Column E: Numero de factura, se aplica el mism proceso anterior, OK
            number_docu = validate_document_number(inv_name)
            if number_docu[0] == True:
                purchase_invoice.update({'no_doc': number_docu[1]})

            # Si no aplica lo anterior, name de factura se pasa por un limpiador de strings, dejando solamente el numero de la factura
            purchase_invoice.update({'no_doc': string_cleaner(inv_name, opt=True)})

            # Column F, Fecha del documento: se esta usando posting date de la factura, OK

            # Column G, NIT del cliente/proveedor: ya procesado por la db, OK

            # Column H, Nombre del cliente/proveedor: ya procesado por la db, OK

            # Column J, Tipo de Operación (Bien o Servicio): OK
            # Si todos los items de la factura son bienes se clasifica como bien
            # Si todos los items de la factura son servicios se clasifica con servicio
            # Si los items in invoice are mixed then, empty row
            purchase_invoice.update({'tipo_ope': validate_invoice_of_goods_or_services(inv_name, type_inv=purchase_invoice.get('compras_ventas'))})

            # Column K: Si es compra, va vacio, si en el libro se incluyen ventas/compras y tiene descuento la factura OK
            # debe ir D, Si es venta ok E de emitido, si es factura de venta cancelada debe ir A de anulado
            purchase_invoice.update({'status_doc': validate_status_document(purchase_invoice)})

            # Las validaciones para L y M se basa en si hay data en contact va se por Customer, Supplier
            # Si no hay dato se dejara en blanco, especificar bien esto en manual user
            # Column L: No. de orden de la cédula, DPI o Pasaporte, OK
            contact_name = frappe.db.get_value('Contact', {'address': purchase_invoice.get('invoice_address')}, 'name')
            ord_doc_entity = frappe.db.get_value('Contact Identification', {'parent': contact_name}, 'ip_prefix') or ""
            purchase_invoice.update({'no_orden_cedula_dpi_pasaporte': ord_doc_entity})

            # Coumn M: No. de registro de la cédula, DPI o Pasaporte, OK
            no_doc_entity = frappe.db.get_value('Contact Identification', {'parent': contact_name}, 'id_number') or ""
            purchase_invoice.update({'no_regi_cedula_dpi_pasaporte': no_doc_entity})

            # Column N: Tipo Documento de Operación POR AHORA NO APLICA, puede ser DUA o FAUCA, eaplica solo exportador
            # Column O: Número del documento de Operación, POR AHORA NO APLICA, solo para exportadores


            # Column P, R Locales, OK
            # Si la factura es local, obtenemos el monto de bienes en al factura
            # con iva incluido
            amt_local = process_purchase_invoice_items(inv_name)
            template_tax_name = purchase_invoice.get('taxes_and_charges', '')
            is_exempt = validate_if_exempt(template_tax_name, purchase_invoice.get('compras_ventas'))
            tax_category = frappe.db.get_value('Company', {'name': purchase_invoice.get('company')},
                                               'tax_category')

            # OPERACIONES LOCALES
            if column_i.get('tipo_transaccion') == 'L':
                if tax_category == 'SAT: Pequeño Contribuyente':  # Si company es peque;o contribuyente
                        # Column AA: OK
                        purchase_invoice.update({'peque_contri_total_facturado_ope_local_bienes': amt_local.get('goods')})
                        # Column AB, OK
                        purchase_invoice.update({'peque_contri_total_facturado_ope_local_servicios': amt_local.get('services')})
                else:
                    if is_exempt == 1:
                        # Column T
                        purchase_invoice.update({'total_exento_doc_bien_ope_local': amt_local.get('goods')})
                        # Column V
                        purchase_invoice.update({'total_exento_doc_servi_ope_local': amt_local.get('services')})

                    else:
                        # Actualizamos el valor de ... con el de bienes obtenido de la factura
                        purchase_invoice.update({'total_gravado_doc_bien_ope_local': amt_local.get('goods')})
                        # col r
                        purchase_invoice.update({'total_gravado_doc_servi_ope_local': amt_local.get('services')})


            # OPERACIONES EXTERIORES
            # Columna Q, S: Si es exterior, OK
            if column_i.get('tipo_transaccion') == 'E':
                if tax_category == 'SAT: Pequeño Contribuyente':  # Si company es peque;o contribuyente
                        # Column AC: OK
                        purchase_invoice.update({'peque_contri_total_facturado_ope_exterior_bienes': amt_local.get('goods')})
                        # Column AD, OK
                        purchase_invoice.update({'peque_contri_total_facturado_ope_exterior_servicios': amt_local.get('services')})

                else:
                    if is_exempt == 1:
                        # Column U
                        purchase_invoice.update({'total_exento_doc_bien_ope_exterior': amt_local.get('goods')})
                        # Column W
                        purchase_invoice.update({'total_exento_doc_servi_ope_exterior': amt_local.get('services')})
                    else:
                        # Actualizamos el valor de ... con el de bienes obtenido de la factura
                        purchase_invoice.update({'total_gravado_doc_bien_ope_exterior': amt_local.get('goods')})

                        # col S
                        purchase_invoice.update({'total_gravado_doc_servi_ope_exterior': amt_local.get('services')})

            # Columna X, Y, Z: Tipo de constancia, solo para ventas
            # CADI = CONSTANCIA DE ADQUISICIÓN DE INSUMOS
            # CEXE = CONSTANCIA DE EXENCIÓN DE IVA
            # CRIVA = CONSTANCIA DE RETENCIÓN DE IVA

            data.append(purchase_invoice)

    return data


def process_sales_invoices(sales_invoices):
    """
    Procesa todas facturas de compra, asignando correctamente a un diccionario
    los datos necesarios para mostrar en reporte

    Args:
        purchase_invoices (list): Lista diccionarios con data db

    Returns:
        list: lista diccionarios datos procesados
    """

    data = []

    # Si existen datos
    if len(sales_invoices) > 0:
        # Procesamos facturas de venta, por cada factura
        for sales_invoice in sales_invoices:
            inv_name = sales_invoice.get('documento')

            # get_items_sales_invoice(inv_name)
            # Column I: OK
            # Validamos tipo de trasaccion
            column_i = validate_trasaction(sales_invoice)
            # Actualizamos el valor del diccionario iterado
            sales_invoice.update(column_i)

            # Column A: Establecimiento - OK
            establ_comp = frappe.db.get_value('Address', {'name': sales_invoice.get('company_address_invoice', '')},
                                              'facelec_establishment')
            sales_invoice.update({'establecimiento': establ_comp})

            # Column B: Compras/Ventas (ya viene procesado de la base de datos) C o V, OK

            # Column C: Documento, OK
            document_inv = validate_serie(sales_invoice.get('serie_doc'))
            sales_invoice.update({'documento': document_inv})

            # Column D, Serie del documento, OK
            # Primero se validara en envios FEL, si no existe se usara la data que ya viene procesada de db
            serie_docu = validate_document_serie(inv_name)
            if serie_docu[0] == True:
                sales_invoice.update({'serie_doc': serie_docu[1]})

            # Column E: Numero de factura, se aplica el mism proceso anterior, OK
            number_docu = validate_document_number(inv_name)
            if number_docu[0] == True:
                sales_invoice.update({'no_doc': number_docu[1]})

            # # Si no aplica lo anterior, name de factura se pasa por un limpiador de strings, dejando solamente el numero de la factura
            sales_invoice.update({'no_doc': string_cleaner(inv_name, opt=True)})

            # Column F, Fecha del documento: se esta usando posting date de la factura, OK

            # Column G, NIT del cliente/proveedor: ya procesado por la db, OK

            # Column H, Nombre del cliente/proveedor: ya procesado por la db, OK

            # Column J, Tipo de Operación (Bien o Servicio): OK
            # Si todos los items de la factura son bienes se clasifica como bien
            # Si todos los items de la factura son servicios se clasifica con servicio
            # Si los items in invoice are mixed then, empty row
            sales_invoice.update({'tipo_ope': validate_invoice_of_goods_or_services(inv_name, type_inv=sales_invoice.get('compras_ventas'))})

            # # Column K: Si es compra, va vacio, si en el libro se incluyen ventas/compras y tiene descuento la factura OK
            # # debe ir D, Si es venta ok E de emitido, si es factura de venta cancelada debe ir A de anulado
            # sales_invoice.update({'status_doc': validate_status_document(sales_invoice)})

            # # Las validaciones para L y M se basa en si hay data en contact va se por Customer, Supplier
            # # Si no hay dato se dejara en blanco, especificar bien esto en manual user
            # # Column L: No. de orden de la cédula, DPI o Pasaporte, OK
            # contact_name = frappe.db.get_value('Contact', {'address': sales_invoice.get('invoice_address')}, 'name')
            # ord_doc_entity = frappe.db.get_value('Contact Identification', {'parent': contact_name}, 'ip_prefix') or ""
            # sales_invoice.update({'no_orden_cedula_dpi_pasaporte': ord_doc_entity})

            # # Coumn M: No. de registro de la cédula, DPI o Pasaporte, OK
            # no_doc_entity = frappe.db.get_value('Contact Identification', {'parent': contact_name}, 'id_number') or ""
            # sales_invoice.update({'no_regi_cedula_dpi_pasaporte': no_doc_entity})

            # # Column N: Tipo Documento de Operación POR AHORA NO APLICA, puede ser DUA o FAUCA, eaplica solo exportador
            # # Column O: Número del documento de Operación, POR AHORA NO APLICA, solo para exportadores


            # # Column P, R Locales, OK
            # # Si la factura es local, obtenemos el monto de bienes en al factura
            # # con iva incluido
            # amt_local = process_sales_invoice_items(inv_name)
            # template_tax_name = sales_invoice.get('taxes_and_charges', '')
            # is_exempt = validate_if_exempt(template_tax_name, sales_invoice.get('compras_ventas'))
            # tax_category = frappe.db.get_value('Company', {'name': sales_invoice.get('company')},
            #                                    'tax_category')

            # # OPERACIONES LOCALES
            # if column_i.get('tipo_transaccion') == 'L':
            #     if tax_category == 'SAT: Pequeño Contribuyente':  # Si company es peque;o contribuyente
            #             # Column AA: OK
            #             sales_invoice.update({'peque_contri_total_facturado_ope_local_bienes': amt_local.get('goods')})
            #             # Column AB, OK
            #             sales_invoice.update({'peque_contri_total_facturado_ope_local_servicios': amt_local.get('services')})
            #     else:
            #         if is_exempt == 1:
            #             # Column T
            #             sales_invoice.update({'total_exento_doc_bien_ope_local': amt_local.get('goods')})
            #             # Column V
            #             sales_invoice.update({'total_exento_doc_servi_ope_local': amt_local.get('services')})

            #         else:
            #             # Actualizamos el valor de ... con el de bienes obtenido de la factura
            #             sales_invoice.update({'total_gravado_doc_bien_ope_local': amt_local.get('goods')})
            #             # col r
            #             sales_invoice.update({'total_gravado_doc_servi_ope_local': amt_local.get('services')})


            # # OPERACIONES EXTERIORES
            # # Columna Q, S: Si es exterior, OK
            # if column_i.get('tipo_transaccion') == 'E':
            #     if tax_category == 'SAT: Pequeño Contribuyente':  # Si company es peque;o contribuyente
            #             # Column AC: OK
            #             sales_invoice.update({'peque_contri_total_facturado_ope_exterior_bienes': amt_local.get('goods')})
            #             # Column AD, OK
            #             sales_invoice.update({'peque_contri_total_facturado_ope_exterior_servicios': amt_local.get('services')})

            #     else:
            #         if is_exempt == 1:
            #             # Column U
            #             sales_invoice.update({'total_exento_doc_bien_ope_exterior': amt_local.get('goods')})
            #             # Column W
            #             sales_invoice.update({'total_exento_doc_servi_ope_exterior': amt_local.get('services')})
            #         else:
            #             # Actualizamos el valor de ... con el de bienes obtenido de la factura
            #             sales_invoice.update({'total_gravado_doc_bien_ope_exterior': amt_local.get('goods')})

            #             # col S
            #             sales_invoice.update({'total_gravado_doc_servi_ope_exterior': amt_local.get('services')})

            # Columna X, Y, Z: Tipo de constancia, solo para ventas
            # CADI = CONSTANCIA DE ADQUISICIÓN DE INSUMOS
            # CEXE = CONSTANCIA DE EXENCIÓN DE IVA
            # CRIVA = CONSTANCIA DE RETENCIÓN DE IVA

            data.append(sales_invoice)

    return data
