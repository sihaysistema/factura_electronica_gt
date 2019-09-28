# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime
from factura_electronica.utils.utilities_facelec import normalizar_texto
import json, xmltodict
import base64


def generar_fac_fel(serie_original_factura, nombre_del_cliente, nombre_config_validada, series_fel):
    '''Funcion maestra para crear factura electronica para el regimen FEL'''

    # data_peticion = preparar_data(obtener_data(serie_original_factura))
    data_factura = obtener_data(serie_original_factura, nombre_del_cliente, nombre_config_validada)
    status = preparar_data(data_factura, series_fel)
    return status


@frappe.whitelist()
def obtener_data(serie_original_factura, nombre_del_cliente, nombre_config_validada):
    # Obtener data emisor
    # OBTENCION DATA NECESARIA PARA GENERAR JSON TO XML

    data_fac = {}

    # Obtiene informacion de los campos de la tabla 'Sales Invoice'
    try:
        sales_invoice = frappe.db.get_values('Sales Invoice',
                                             filters={'name': serie_original_factura},
                                             fieldname=['name', 'grand_total', 'customer_name', 'company',
                                                       'company_address', 'naming_series', 'creation',
                                                       'status', 'discount_amount', 'docstatus',
                                                       'modified', 'conversion_rate',
                                                       'total_taxes_and_charges', 'net_total',
                                                       'shipping_address_name', 'customer_address',
                                                       'total', 'shs_total_iva_fac', 'currency'], as_dict=1)
    except:
        return 'Error al obtener datos de la factura {}: {}'.format(serie_original_factura, frappe.get_traceback())
    else:
        data_fac['sales_invoice'] = sales_invoice

    # Obtiene informacion de los campos de la tabla 'Sales Invoice Item'
    try:
        sales_invoice_item = frappe.db.get_values('Sales Invoice Item',
                                                  filters={'parent': serie_original_factura},
                                                  fieldname=['item_name', 'qty', 'posting_date',
                                                            'item_code', 'description',
                                                            'net_amount', 'base_net_amount',
                                                            'discount_percentage', 'posting_time',
                                                            'net_rate', 'stock_uom',
                                                            'serial_no', 'item_group',
                                                            'rate', 'amount',
                                                            'facelec_sales_tax_for_this_row',
                                                            'facelec_amount_minus_excise_tax',
                                                            'facelec_other_tax_amount',
                                                            'facelec_three_digit_uom_code',
                                                            'facelec_gt_tax_net_fuel_amt',
                                                            'facelec_gt_tax_net_goods_amt',
                                                            'facelec_gt_tax_net_services_amt'], as_dict=1)
    except:
        return 'Error al obtener datos de los items de la factura {}: {}'.format(serie_original_factura, frappe.get_traceback())
    else:
        data_fac['sales_invoice_item'] = sales_invoice_item

    # Obtiene datos de los campos de la tabla 'Address' informacion de los clientes
    try:
        direccion_cliente = sales_invoice[0]['customer_address']
        datos_cliente = frappe.db.get_values('Address', filters={'name': direccion_cliente},
                                             fieldname=['email_id', 'country', 'city',
                                                       'address_line1', 'state', 'address_line2',
                                                       'phone', 'address_title', 'name', 'pincode'], as_dict=1)
    except:
        return '''Error al obtener informacion del
                  cliente {0} de la factura \
                  {1}: {2}'''.format(nombre_del_cliente, serie_original_factura, frappe.get_traceback())
    else:
        data_fac['direccion_cliente'] = direccion_cliente
        data_fac['datos_cliente'] = datos_cliente

    # Obtiene datos de direccion de la compañia de la tabla 'Address'
    try:
        dir_empresa = sales_invoice[0]['company_address']
        direccion_empresa = frappe.db.get_values('Address', filters={'name': dir_empresa},
                                                fieldname=['email_id', 'country', 'city',
                                                          'address_line1', 'address_line2', 'state',
                                                          'phone', 'address_title',
                                                          'county', 'pincode'], as_dict=1)
    except:
        return '''Error al obtener informacion de la
                  compania de la factura {}: {}'''.format(serie_original_factura, frappe.get_traceback())
    else:
        data_fac['direccion_empresa'] = direccion_empresa

    # Obtiene datos de los campos de la tabla 'Company'
    try:
        datos_empresa = frappe.db.get_values('Company', filters={'name': sales_invoice[0]['company']},
                                            fieldname=['company_name', 'default_currency', 'country',
                                                      'nit_face_company'], as_dict=1)
    except:
        return '''Error al obtener datos de la compania, verifique que tenga una direcccion, NIT
                  validos: {}'''.format(frappe.get_traceback())
    else:
        data_fac['datos_empresa'] = datos_empresa

    # Obtiene datos de los campos de la tabla 'Customer'
    try:
        nit_cliente = frappe.db.get_values('Customer', filters={'name': nombre_del_cliente},
                                            fieldname='nit_face_customer')
    except:
        return 'Error al obtener nit del cliente {}: {}'.format(nombre_del_cliente, frappe.get_traceback())
    else:
        data_fac['nit_cliente'] = nit_cliente

    # Obtiene datos de los campos de la tabla 'Configuracion Factura Electronica'
    try:
        datos_configuracion = frappe.db.get_values('Configuracion Factura Electronica',
                                                  filters={'name': str(nombre_config_validada)},
                                                  fieldname=['descripcion_otro_impuesto', 'importe_exento',
                                                            'id_dispositivo', 'validador', 'clave',
                                                            'codigo_establecimiento', 'importe_otros_impuestos',
                                                            'regimen_2989', 'usuario', 'regimen_isr',
                                                            'nit_gface', 'importe_total_exento',
                                                            'url_listener'], as_dict=1)
    except:
        return 'Error al obtener datos de la configuracion de factura electronica: {}'.format(frappe.get_traceback())
    else:
        data_fac['datos_configuracion'] = datos_configuracion

    # return data_fac
    with open('obt_data.json', 'w') as f:
        f.write(json.dumps(str(data_fac), indent=2))

    return data_fac


def preparar_data(data_fac, series_fel):
    '''Funcion encargada de asignar la data correspondiente a la peticion necesaria para INFILE'''

    # Datos generales de la factura
    datos_generales = {
        '@CodigoMoneda': data_fac['sales_invoice'][0]['currency'], #'GTQ',
        '@FechaHoraEmision': (data_fac['sales_invoice'][0]['posting_date'] + 'T' + \
                              data_fac['sales_invoice'][0]['posting_time']), #'2019-09-10T16:26:46-06:00',
        '@Tipo': series_fel[0]['tipo_documento']
    }

    # Datos configuracion del emisor
    emisor = {
        '@AfiliacionIVA': 'GEN', # TODO: ?
        '@CodigoEstablecimiento': data_fac['datos_configuracion'][0]['codigo_establecimiento'],
        '@CorreoEmisor': data_fac['direccion_empresa'][0]['email_id'],
        '@NITEmisor': data_fac['datos_empresa'][0]['nit_face_company'],
        '@NombreComercial': data_fac['datos_empresa'][0]['company_name'],
        '@NombreEmisor': data_fac['datos_empresa'][0]['company_name'],
        'dte:DireccionEmisor': {
            'dte:Direccion': data_fac['direccion_empresa'][0]['address_line1'],
            'dte:CodigoPostal': data_fac['direccion_empresa'][0]['pincode'],
            'dte:Municipio': data_fac['direccion_empresa'][0]['state'],
            'dte:Departamento': data_fac['direccion_empresa'][0]['city'],
            'dte:Pais': data_fac['direccion_empresa'][0]['country']
        }
    }

    # Datos del cliente facturado
    receptor = {
        '@CorreoReceptor': data_fac['datos_cliente'][0]['email_id'],
        '@IDReceptor': '76365204', # TODO: ?
        '@NombreReceptor': data_fac['sales_invoice'][0]['customer_name'],
        'dte:DireccionReceptor': {
            'dte:Direccion': data_fac['datos_cliente'][0]['address_line1'],
            'dte:CodigoPostal': data_fac['datos_cliente'][0]['pincode'],
            'dte:Municipio': data_fac['datos_cliente'][0]['state'],
            'dte:Departamento': data_fac['datos_cliente'][0]['city'],
            'dte:Pais': data_fac['datos_cliente'][0]['country'] # 'GT'
        }
    }

    # TODO: PENDIENTE DOCS?
    frases = {
        'dte:Frase': {
            '@CodigoEscenario': '1',
            '@TipoFrase': '1'
        }
    }

    # Items y sus detalles incluidos en la factura
    n_prod = len(data_fac['sales_invoice_item'])
    items_factura = []

    if n_prod > 1:
        for i in range(0, n_prod):
            item = {
                '@BienOServicio': 'B',
                '@NumeroLinea': i,
                'dte:Cantidad': float(data_fac['sales_invoice_item'][i]['qty']),
                'dte:UnidadMedida': data_fac['sales_invoice_item'][i]['facelec_three_digit_uom_code'],
                'dte:Descripcion': data_fac['sales_invoice_item'][i]['item_name'],
                'dte:PrecioUnitario': float(data_fac['sales_invoice_item'][i][rate]),
                'dte:Precio': float(data_fac['sales_invoice_item'][i]['rate']),
                'dte:Descuento': float(data_fac['sales_invoice_item'][i]['discount_percentage']),
                'dte:Impuestos': {
                    'dte:Impuesto': {
                        'dte:NombreCorto': 'IVA',
                        'dte:CodigoUnidadGravable': '1',
                        'dte:MontoGravable': '8400.0000',
                        'dte:MontoImpuesto': '1008.0000'
                    }
                },
                'dte:Total': float(abs(data_fac['sales_invoice_item'][i]['amount']))
            }
            


    items = {
        'dte:Item': [
            {
                '@BienOServicio': 'B',
                '@NumeroLinea': '1',
                'dte:Cantidad': '196.000',
                'dte:UnidadMedida': 'CJ',
                'dte:Descripcion': '100120406-HIG ROSAL VERDE 2P 12X4',
                'dte:PrecioUnitario': '60.0000',
                'dte:Precio': '11760.0000',
                'dte:Descuento': '2352.0000',
                'dte:Impuestos': {
                    'dte:Impuesto': {
                        'dte:NombreCorto': 'IVA',
                        'dte:CodigoUnidadGravable': '1',
                        'dte:MontoGravable': '8400.0000',
                        'dte:MontoImpuesto': '1008.0000'
                    }
                },
                'dte:Total': '9408.0000'
            },
            {
                '@BienOServicio': 'B',
                '@NumeroLinea': '2',
                'dte:Cantidad': '196.000',
                'dte:UnidadMedida': 'CJ',
                'dte:Descripcion': '100120407-HIG ROSAL VINOTINTO 2P 12X4',
                'dte:PrecioUnitario': '96.0000',
                'dte:Precio': '18816.0000',
                'dte:Descuento': '3763.1999',
                'dte:Impuestos': {
                    'dte:Impuesto': {
                        'dte:NombreCorto': 'IVA',
                        'dte:CodigoUnidadGravable': '1',
                        'dte:MontoGravable': '13440.0000',
                        'dte:MontoImpuesto': '1612.8000'
                    }
                },
                'dte:Total': '15052.8000'
            },
            {
                '@BienOServicio': 'B',
                '@NumeroLinea': '3',
                'dte:Cantidad': '242.000',
                'dte:UnidadMedida': 'CJ',
                'dte:Descripcion': '101910101-HIG NUBE BLANCA 1000H 1P 24X1',
                'dte:PrecioUnitario': '96.0000',
                'dte:Precio': '23232.0000',
                'dte:Descuento': '4646.3999',
                'dte:Impuestos': {
                    'dte:Impuesto': {
                        'dte:NombreCorto': 'IVA',
                        'dte:CodigoUnidadGravable': '1',
                        'dte:MontoGravable': '16594.2851',
                        'dte:MontoImpuesto': '1991.3148'
                    }
                },
                'dte:Total': '18585.6000'
            },
            {
                '@BienOServicio': 'B',
                '@NumeroLinea': '4',
                'dte:Cantidad': '10.000',
                'dte:UnidadMedida': 'CJ',
                'dte:Descripcion': '301920102-TOA NUBE BLANCA 60H 2P 24X1',
                'dte:PrecioUnitario': '105.6000',
                'dte:Precio': '1056.0000',
                'dte:Descuento': '211.1999',
                'dte:Impuestos': {
                    'dte:Impuesto': {
                        'dte:NombreCorto': 'IVA',
                        'dte:CodigoUnidadGravable': '1',
                        'dte:MontoGravable': '754.2851',
                        'dte:MontoImpuesto': '90.5148'
                    }
                },
                'dte:Total': '844.8000'
            }
        ]
    }

    totales = {
        'dte:TotalImpuestos': {
            'dte:TotalImpuesto': {
                '@NombreCorto': 'IVA',
                '@TotalMontoImpuesto': '4702.63'
            }
        },
        'dte:GranTotal': '43891.20'
    }

    base_petiion = {
        'dte:GTDocumento': {
            '@xmlns:ds': 'http://www.w3.org/2000/09/xmldsig#',
            '@xmlns:dte': 'http://www.sat.gob.gt/dte/fel/0.1.0',
            '@xmlns:n1': 'http://www.altova.com/samplexml/other-namespace',
            '@xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            '@Version': '0.4',
            '@xsi:schemaLocation': 'http://www.sat.gob.gt/dte/fel/0.1.0 ',
            'dte:SAT': {
                '@ClaseDocumento': 'dte',
                'dte:DTE': {
                    '@ID': 'DatosCertificados',
                    'dte:DatosEmision': {
                        '@ID': 'DatosEmision',
                        'dte:DatosGenerales': datos_generales,
                        'dte:Emisor': emisor,
                        'dte:Receptor': receptor,
                        'dte:Frases': frases,
                        'dte:Items': items,
                        'dte:Totales': 
                    }
                }
            }
        }
    }