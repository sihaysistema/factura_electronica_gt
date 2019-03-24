# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime
from utilities_facelec import normalizar_texto

# Permite trabajar con acentos, ñ, simbolos, etc
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

def construir_xml(serie_original_factura, nombre_del_cliente, prefijo_serie, series_configuradas, nombre_config_validada):
    '''Funcion para construir el xml con los datos necesarios para hacer una peticion de generacion de factura electronica
       a INFILE. La construccion del xml es en 3 partes. Los parametros que recibe se utilizan como filtro para la busqueda
       de datos en la base de datos para luego ser asignadas a variables y terminar construyendo el xml
       
       Parametros:
       ----------
       * serie_original_factura (str) : Nombre de la serie original de la factura
       * nombre_del_cliente (str) : Nombre del cliente
       * prefijo_serie (str) : Prefijo de la serie utilizada en la factura
       * series_configuradas (dict) : Diccionario con informacion de las series configuradas
       * nombre_config_validada (str) : Nombre configuracion valida de factura electronica
       '''
    
    # OBTENER DATA NECESARIA PARA GENERAR JSON TO XML
    try:
        # Obtiene informacion de los campos de la tabla 'Sales Invoice'
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
        frappe.msgprint(_('Error al obtener datos de la factura {}'.format(serie_original_factura)))

    try:
        # Obtiene informacion de los campos de la tabla 'Sales Invoice Item'
        sales_invoice_item = frappe.db.get_values('Sales Invoice Item',
                                                  filters={'parent': serie_original_factura},
                                                  fieldname=['item_name', 'qty',
                                                            'item_code', 'description',
                                                            'net_amount', 'base_net_amount',
                                                            'discount_percentage',
                                                            'net_rate', 'stock_uom',
                                                            'serial_no', 'item_group',
                                                            'rate', 'amount',
                                                            'facelec_sales_tax_for_this_row',
                                                            'facelec_amount_minus_excise_tax',
                                                            'facelec_other_tax_amount',
                                                            'facelec_three_digit_uom_code',
                                                            'facelec_gt_tax_net_fuel_amt',
                                                            'facelec_gt_tax_net_goods_amt',
                                                            'facelec_gt_tax_net_services_amt'],
                                                  as_dict=1)
    except:
        frappe.msgprint(_('Error al obtener datos de los items de la factura {}'.format(serie_original_factura)))

    try:
        direccion_cliente = sales_invoice[0]['customer_address']

        # Obtiene datos de los campos de la tabla 'Address' informacion de los clientes
        datos_cliente = frappe.db.get_values('Address', filters={'name': direccion_cliente},
                                             fieldname=['email_id', 'country', 'city',
                                                       'address_line1', 'state',
                                                       'phone', 'address_title', 'name'], as_dict=1)
    except:
        frappe.msgprint(_('''Error al obtener informacion del
                          cliente {0} de la factura {1}'''.format(nombre_del_cliente, serie_original_factura)))

    try:
        dir_empresa = sales_invoice[0]['company_address']

        # Obtiene datos de direccion de la compañia de la tabla 'Address'
        direccion_empresa = frappe.db.get_values('Address', filters={'name': dir_empresa},
                                                fieldname=['email_id', 'country', 'city',
                                                          'address_line1', 'state',
                                                          'phone', 'address_title',
                                                          'county'], as_dict=1)
    except:
        frappe.msgprint(_('''Error al obtener informacion de la
                          compania de la factura {}'''.format(serie_original_factura)))

    try:
        # Obtiene datos de los campos de la tabla 'Company'
        datos_empresa = frappe.db.get_values('Company', filters={'name': sales_invoice[0]['company']},
                                            fieldname=['company_name', 'default_currency', 'country',
                                                      'nit_face_company'], as_dict=1)
    except
        frappe.msgprint(_('''Error al obtener datos de la compania, verifique que tenga una direcccion, NIT
                             validos'''))

    try:
        # Obtiene datos de los campos de la tabla 'Customer'
        nit_cliente = frappe.db.get_values('Customer', filters={'name': nombre_del_cliente},
                                            fieldname='nit_face_customer')
    except:
        frappe.msgprint(_('Error al obtener nit del cliente {}'.format(nombre_del_cliente)))

    try:
        # Obtiene datos de los campos de la tabla 'Configuracion Factura Electronica'
        datos_configuracion = frappe.db.get_values('Configuracion Factura Electronica',
                                                  filters={'name': nombre_config_validada},
                                                  fieldname=['descripcion_otro_impuesto', 'importe_exento',
                                                            'id_dispositivo', 'validador', 'clave',
                                                            'codigo_establecimiento', 'importe_otros_impuestos',
                                                            'regimen_2989', 'usuario', 'regimen_isr',
                                                            'nit_gface', 'importe_total_exento',
                                                            'url_listener'], as_dict=1)
    except:
        frappe.msgprint(_('Error al obtener datos de la configuracion de factura electronica'))


    # VALIDAR INFORMACION Y GENERAR JSON TO XML
    