# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime
from valida_errores import normalizar_texto
import json
import xmltodict

# Permite trabajar con acentos, ñ, simbolos, etc
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

@frappe.whitelist()
def construir_xml_m(serie_original_factura, nombre_del_cliente, prefijo_serie, series_configuradas, nombre_config_validada):
    pass
    # '''Funcion para construir el xml con los datos necesarios para hacer una peticion de generacion de factura electronica
    #     a INFILE. La construccion del xml es en 3 partes. Los parametros que recibe se utilizan como filtro para la busqueda
    #     de datos en la base de datos para luego ser asignadas a variables y terminar construyendo el xml'''
    # # CAPTURA DE DATOS, SI ES EXITOSO PROCEDE A ARMAR EL XML
    # try:
    #     # Obtiene informacion de los campos de la tabla 'Sales Invoice'
    #     sales_invoice = frappe.db.get_values('Sales Invoice',
    #                                         filters={'name': serie_original_factura},
    #                                         fieldname=['name', 'idx', 'territory',
    #                                                     'grand_total', 'customer_name', 'company',
    #                                                     'company_address', 'naming_series', 'creation',
    #                                                     'status', 'discount_amount', 'docstatus',
    #                                                     'modified', 'conversion_rate',
    #                                                     'total_taxes_and_charges', 'net_total',
    #                                                     'shipping_address_name', 'customer_address',
    #                                                     'total', 'shs_total_iva_fac', 'currency'],
    #                                         as_dict=1)

    #     # Obtiene informacion de los campos de la tabla 'Sales Invoice Item'
    #     sales_invoice_item = frappe.db.get_values('Sales Invoice Item',
    #                                             filters={'parent': serie_original_factura},
    #                                             fieldname=['item_name', 'qty',
    #                                                         'item_code', 'description',
    #                                                         'net_amount', 'base_net_amount',
    #                                                         'discount_percentage',
    #                                                         'net_rate', 'stock_uom',
    #                                                         'serial_no', 'item_group',
    #                                                         'rate', 'amount',
    #                                                         'facelec_sales_tax_for_this_row',
    #                                                         'facelec_amount_minus_excise_tax',
    #                                                         'facelec_other_tax_amount',
    #                                                         'facelec_three_digit_uom_code',
    #                                                         'facelec_gt_tax_net_fuel_amt',
    #                                                         'facelec_gt_tax_net_goods_amt',
    #                                                         'facelec_gt_tax_net_services_amt'],
    #                                             as_dict=1)

    #     direccion_cliente = sales_invoice[0]['customer_address']
    #     dir_empresa = sales_invoice[0]['company_address']

    #     # Obtiene datos de los campos de la tabla 'Address' informacion de los clientes
    #     datos_cliente = frappe.db.get_values('Address', filters={'name': direccion_cliente},
    #                                         fieldname=['email_id', 'country', 'city',
    #                                                     'address_line1', 'state',
    #                                                     'phone', 'address_title', 'name'], as_dict=1)

    #     # Obtiene datos de direccion de la compañia de la tabla 'Address'
    #     direccion_empresa = frappe.db.get_values('Address', filters={'name': dir_empresa},
    #                                             fieldname=['email_id', 'country', 'city',
    #                                                         'address_line1', 'state',
    #                                                         'phone', 'address_title',
    #                                                         'county'], as_dict=1)

    #     # Obtiene datos de los campos de la tabla 'Company'
    #     datos_empresa = frappe.db.get_values('Company', filters={'name': sales_invoice[0]['company']},
    #                                         fieldname=['company_name', 'default_currency', 'country',
    #                                                     'nit_face_company'], as_dict=1)

    #     # Obtiene datos de los campos de la tabla 'Customer'
    #     nit_cliente = frappe.db.get_values('Customer', filters={'name': nombre_del_cliente},
    #                                         fieldname='nit_face_customer')

    #     # Obtiene datos de los campos de la tabla 'Configuracion Factura Electronica'
    #     datos_configuracion = frappe.db.get_values('Configuracion Factura Electronica',
    #                                                 filters={'name': nombre_config_validada},
    #                                                 fieldname=['descripcion_otro_impuesto', 'importe_exento',
    #                                                            'id_dispositivo', 'validador', 'clave', 'codigo_establecimiento',
    #                                                            'importe_otros_impuestos', 'regimen_2989', 'usuario', 'regimen_isr',
    #                                                            'nit_gface', 'importe_total_exento', 'url_listener'], as_dict=1)
    # except:
    #     frappe.msgprint(_('''Error: Problemas con la Base de Datos. No se pudieron obtener los datos requeridos
    #                          para realizar una peticion a INFILE. Por favor verifica que existan todos los datos
    #                          de la empresa e intenta de nuevo.'''))
    # else:
    #     data_factura = {}
    #     try:
    #         tipo_doc = str(series_configuradas[0]['tipo_documento'])

    #         # Verificacion datos del cliente
    #         if frappe.db.exists('Address', {'name': direccion_cliente}):
    #             # Verificacion email, en caso no exista se asignara N/A
    #             if ((datos_cliente[0]['email_id']) is None):
    #                 correoCompradorTag_Value = 'N/A'
    #             else:
    #                 correoCompradorTag_Value = str(datos_cliente[0]['email_id'])

    #             # Verificacion Departamento Comprador, en caso no exista se asignara N/A
    #             if ((datos_cliente[0]['city']) == ''):
    #                 departamentoCompradorTag_Value = 'N/A'
    #             else:
    #                 departamentoCompradorTag_Value = str(normalizar_texto(datos_cliente[0]['city']))

    #             # Verificacion Direccion Comercial Comprador, en caso no exista se asignara N/A
    #             if ((datos_cliente[0]['address_line1']) == ''):
    #                 direccionComercialCompradorTag_Value = 'N/A'
    #             else:
    #                 direccionComercialCompradorTag_Value = str(normalizar_texto(datos_cliente[0]['address_line1'])) #.encode('utf-8')
    #                 # frappe.msgprint(_(direccionComercialCompradorTag_Value))

    #             # Verificacion Telefono Comprador, en caso no exista se asignara N/A
    #             if ((datos_cliente[0]['phone']) == ''):
    #                 telefonoCompradorTag_Value = 'N/A'
    #             else:
    #                 telefonoCompradorTag_Value = str(datos_cliente[0]['phone'])

    #             # Verificacion Municipio Comprador, en caso no exista se asignara N/A
    #             if ((datos_cliente[0]['state']) == ''):
    #                 municipioCompradorTag_Value = 'N/A'
    #             else:
    #                 municipioCompradorTag_Value = str(normalizar_texto(datos_cliente[0]['state']))

    #         else:
    #             correoCompradorTag_Value = 'N/A'
    #             departamentoCompradorTag_Value = 'N/A'
    #             direccionComercialCompradorTag_Value = 'N/A'
    #             telefonoCompradorTag_Value = 'N/A'
    #             municipioCompradorTag_Value = 'N/A'

    #         # Verificacion Nombre Comercial Comprador, en caso sea C/F se asignara como consumidor final
    #         if (str(nit_cliente[0][0]) == 'C/F' or str(nit_cliente[0][0]) == 'c/f'):
    #             nombreComercialCompradorTag_Value = 'Consumidor Final'
    #             # nombreComercialCompradorTag_Value = str(sales_invoice[0]['customer_name'])
    #         else:
    #             nombreComercialCompradorTag_Value = str(normalizar_texto(sales_invoice[0]['customer_name']))

    #         # PRIMERA PARTE
    #         data_factura['S:Envelope'] = {}
    #         data_factura['S:Envelope']['@xmlns:S'] = 'http://schemas.xmlsoap.org/soap/envelope/'
    #         data_factura['S:Envelope']['S:Body'] = {}
    #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte'] = {}
    #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['@xmlns:ns2'] = 'http://listener.ingface.com/'
    #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte'] = {}

    #         # Clave
    #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['clave'] = str(datos_configuracion[0]['clave'])
    #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte'] = {}

    #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['codigoEstablecimiento'] = 1
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['codigoMoneda'] = str(sales_invoice[0]['currency'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['correoComprador'] = correoCompradorTag_Value
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['departamentoComprador'] = departamentoCompradorTag_Value
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['departamentoVendedor'] = str(normalizar_texto(direccion_empresa[0]['city']))
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['descripcionOtroImpuesto'] = str(datos_configuracion[0]['descripcion_otro_impuesto'])

            # # SEGUNDA PARTE
            # # Agregar n items
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte'] = {}

            # n_productos = len(sales_invoice_item)
            # if (n_productos > 1):

            #     for i in range(0, n_productos):
            #         # Iterar los n items con for in
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['cantidad'] = float(sales_invoice_item[i]['qty'])
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['codigoProducto'] = str(sales_invoice_item[i]['item_code'])
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['descripcionProducto'] = str((sales_invoice_item[i]['item_name']))
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['detalleImpuestoIva'] = float((sales_invoice_item[i]['facelec_sales_tax_for_this_row']))
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['importeExento'] = float((datos_configuracion[0]['importe_exento']))
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['importeNetoGravado'] = abs(float((sales_invoice_item[i]['facelec_amount_minus_excise_tax'])))
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['importeOtrosImpuestos'] = float((sales_invoice_item[i]['facelec_other_tax_amount']))
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['importeTotalOperacion'] = abs(float((sales_invoice_item[i]['amount'])))
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['montoBruto'] = '{0:.2f}'.format(float(((sales_invoice_item[i]['facelec_gt_tax_net_fuel_amt']) +
            #                                                                                                                                      (sales_invoice_item[i]['facelec_gt_tax_net_goods_amt']) +
            #                                                                                                                                      (sales_invoice_item[i]['facelec_gt_tax_net_services_amt']))))
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['montoDescuento'] = float(sales_invoice_item[i]['discount_percentage'])
            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['precioUnitario'] = float(sales_invoice_item[i]['rate'])

            #         # es-GT: Obtiene directamente de la db el campo de stock para luego ser verificado como Servicio o Bien.
            #         # en-US: Obtains directly from the db the stock field to be later verified as Service or Good.
            #         detalle_stock = frappe.db.get_values('Item', filters={'item_code': str(sales_invoice_item[i]['item_code'])}, fieldname=['is_stock_item'])

            #         # Validacion de Bien o Servicio, en base a detalle de stock
            #         if (int((detalle_stock[0][0])) == 0):
            #             data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['tipoProducto'] = 'S'
            #         if (int((detalle_stock[0][0])) == 1):
            #             data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['tipoProducto'] = 'B'

            #         data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte']['unidadMedida'] = str(sales_invoice_item[i]['facelec_three_digit_uom_code'])

            # # TERCERA PARTE
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleImpuestosIva'] = float((sales_invoice_item[0]['facelec_sales_tax_for_this_row']))
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['direccionComercialComprador'] = direccionComercialCompradorTag_Value
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['direccionComercialVendedor'] = str(normalizar_texto(direccion_empresa[0]['address_line1']))
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['estadoDocumento'] = str(series_configuradas[0]['estado_documento'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['fechaAnulacion'] = str((sales_invoice[0]['creation']).isoformat())
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['fechaDocumento'] = str((sales_invoice[0]['creation']).isoformat())
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['fechaResolucion'] = (series_configuradas[0]['fecha_resolucion'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['idDispositivo'] = str(datos_configuracion[0]['id_dispositivo'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeBruto'] = abs(float(sales_invoice[0]['net_total']))
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeDescuento'] = float(sales_invoice[0]['discount_amount'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeNetoGravado'] = abs(float(sales_invoice[0]['grand_total']))
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeOtrosImpuestos'] = float(datos_configuracion[0]['importe_otros_impuestos'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeTotalExento'] = float(datos_configuracion[0]['importe_total_exento'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['montoTotalOperacion'] = abs(float(sales_invoice[0]['grand_total']))
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['municipioComprador'] = municipioCompradorTag_Value
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['municipioVendedor'] = str(normalizar_texto(direccion_empresa[0]['state']))
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nitComprador'] = str(nit_cliente[0][0]).replace('-', '')
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nitGFACE'] = str(datos_configuracion[0]['nit_gface']).replace('-', '')
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nitVendedor'] = str(datos_empresa[0]['nit_face_company']).replace('-', '')
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nombreComercialComprador'] = nombreComercialCompradorTag_Value
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nombreComercialRazonSocialVendedor'] = str(normalizar_texto(datos_empresa[0]['company_name']))
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nombreCompletoVendedor'] = str(normalizar_texto(datos_empresa[0]['company_name']))

            # # es-GT: Las Facturas CFACE necesitan el correlativo de la factura, excluyendo la serie, por lo que se hace un slice
            # #        para que tome solo el correlativo, si no es CFACE tomara la serie completa.
            # # en-US: CFACE Invoices need the correlation of the invoice, excluding the series, so a slice is made so that it
            # #        takes only the correlative, if it is not CFACE it will take the complete series.
            # if (tipo_doc == 'CFACE'):
            #     nlong = len(prefijo_serie)
            #     numeroDocumentoTag_Value = str(serie_original_factura[nlong:])
            # else:
            #     numeroDocumentoTag_Value = str(serie_original_factura)

            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['numeroDocumento'] = numeroDocumentoTag_Value

            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['numeroResolucion'] = str(series_configuradas[0]['numero_resolucion']).replace('-', '')
            
            # if (datos_configuracion[0]['regimen_2989']) == 0:
            #     regimen2989Tag_Value = 'false'
            # else:
            #     regimen2989Tag_Value = 'true'

            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['regimen2989'] = regimen2989Tag_Value
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['regimenISR'] = str(datos_configuracion[0]['regimen_isr'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['serieAutorizada'] = str(series_configuradas[0]['secuencia_infile'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['serieDocumento'] = str(series_configuradas[0]['codigo_sat'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['telefonoComprador'] = telefonoCompradorTag_Value

            # # es-GT: Cuando es moneda local, obligatoriamente debe llevar 1.00
            # # en-US: When it is local currency, it must necessarily carry 1.00
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['tipoCambio'] = float(sales_invoice[0]['conversion_rate'])

            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['tipoDocumento'] = str(series_configuradas[0]['tipo_documento'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['usuario'] = str(datos_configuracion[0]['usuario'])
            # data_factura['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['validador'] = str(datos_configuracion[0]['validador'])

        # except:
        #     return 'Error :('
        # else:
        #     # return json.dumps(data_factura, indent=4)
        #     return datos_configuracion