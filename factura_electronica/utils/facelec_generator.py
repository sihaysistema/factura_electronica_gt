# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime
from factura_electronica.utils.utilities_facelec import normalizar_texto
import json, xmltodict


def crear_xml_factura_electronica(datos_factura):
    '''Se encarga de convertir JSON a XML
       Parametros:
       ----------
       * datos_factura (json) : Estructura JSON con la informacion para realizar
                                una peticion a INFILE
    '''
    xml_string = xmltodict.unparse(json.loads(datos_factura), pretty=True)

    # PARA DEBUG :)
    # Escribe la data_factura json a XML
    with open('envio_test.xml', 'w') as f:
        f.write(xml_string)

    return xml_string


def construir_xml(serie_original_factura, nombre_del_cliente, prefijo_serie, series_configuradas, nombre_config_validada):
    '''Funcion para construir el xml con los datos necesarios para hacer una peticion de generacion de factura electronica
       a INFILE. La construccion del xml es en 3 partes. Los parametros que recibe se utilizan como filtro para la busqueda
       de datos en la base de datos para luego ser asignadas a variables y terminar construyendo el xml.
       
       Parametros:
       ----------
       * serie_original_factura (str) : Nombre de la serie original de la factura
       * nombre_del_cliente (str) : Nombre del cliente
       * prefijo_serie (str) : Prefijo de la serie utilizada en la factura
       * series_configuradas (dict) : Diccionario con informacion de las series configuradas
       * nombre_config_validada (str) : Nombre configuracion valida de factura electronica
    '''
    
    # OBTENCION DATA NECESARIA PARA GENERAR JSON TO XML
    # Obtiene informacion de los campos de la tabla 'Sales Invoice'
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
        frappe.msgprint(_('Error al obtener datos de la factura {}'.format(serie_original_factura)))

    # Obtiene informacion de los campos de la tabla 'Sales Invoice Item'
    try:
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

    # Obtiene datos de los campos de la tabla 'Address' informacion de los clientes
    try:
        direccion_cliente = sales_invoice[0]['customer_address']

        datos_cliente = frappe.db.get_values('Address', filters={'name': direccion_cliente},
                                             fieldname=['email_id', 'country', 'city',
                                                       'address_line1', 'state', 'address_line2',
                                                       'phone', 'address_title', 'name'], as_dict=1)
    except:
        frappe.msgprint(_('''Error al obtener informacion del
                          cliente {0} de la factura {1}'''.format(nombre_del_cliente, serie_original_factura)))

    # Obtiene datos de direccion de la compañia de la tabla 'Address'
    try:
        dir_empresa = sales_invoice[0]['company_address']

        direccion_empresa = frappe.db.get_values('Address', filters={'name': dir_empresa},
                                                fieldname=['email_id', 'country', 'city',
                                                          'address_line1', 'address_line2', 'state',
                                                          'phone', 'address_title',
                                                          'county'], as_dict=1)
    except:
        frappe.msgprint(_('''Error al obtener informacion de la
                          compania de la factura {}'''.format(serie_original_factura)))

    # Obtiene datos de los campos de la tabla 'Company'
    try:
        datos_empresa = frappe.db.get_values('Company', filters={'name': sales_invoice[0]['company']},
                                            fieldname=['company_name', 'default_currency', 'country',
                                                      'nit_face_company'], as_dict=1)
    except:
        frappe.msgprint(_('''Error al obtener datos de la compania, verifique que tenga una direcccion, NIT
                             validos'''))

    # Obtiene datos de los campos de la tabla 'Customer'
    try:
        nit_cliente = frappe.db.get_values('Customer', filters={'name': nombre_del_cliente},
                                            fieldname='nit_face_customer')
    except:
        frappe.msgprint(_('Error al obtener nit del cliente {}'.format(nombre_del_cliente)))

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
        frappe.msgprint(_('Error al obtener datos de la configuracion de factura electronica'))


    # VALIDAR INFORMACION Y GENERAR JSON TO XML
    try:
        tipo_doc = str(series_configuradas[0]['tipo_documento'])

        direccion_linea2 = ''
        if datos_cliente[0]['address_line2'] is None:
            direccion_linea2 = ''
        else:
            direccion_linea2 = str(normalizar_texto(datos_cliente[0]['address_line2']))

        # VERIFICACION DATOS CLIENTES ------------------------------------------------------------------------
        if frappe.db.exists('Address', {'name': direccion_cliente}):

            # Verificacion email, en caso no exista se asignara N/A
            if ((datos_cliente[0]['email_id']) is None):
                correoCompradorTag_Value = 'N/A'
            else:
                correoCompradorTag_Value = str(datos_cliente[0]['email_id'])

            # Verificacion Departamento Comprador, en caso no exista se asignara N/A
            if ((datos_cliente[0]['city']) == ''):
                departamentoCompradorTag_Value = 'N/A'
            else:
                departamentoCompradorTag_Value = str(normalizar_texto(datos_cliente[0]['city']))

            # Verificacion Direccion Comercial Comprador, en caso no exista se asignara N/A
            if ((datos_cliente[0]['address_line1']) == ''):
                direccionComercialCompradorTag_Value = 'N/A'
            else:
                direccionComercialCompradorTag_Value = '{0} {1}'.format(str(normalizar_texto(datos_cliente[0]['address_line1'])),
                                                                        direccion_linea2) #.encode('utf-8')

            # Verificacion Telefono Comprador, en caso no exista se asignara N/A
            if (datos_cliente[0]['phone'] == '') or (datos_cliente[0]['phone'] is None):
                telefonoCompradorTag_Value = 'N/A'
            else:
                telefonoCompradorTag_Value = str(datos_cliente[0]['phone'])

            # Verificacion Municipio Comprador, en caso no exista se asignara N/A
            if (datos_cliente[0]['state'] == '') or (datos_cliente[0]['state'] is None):
                municipioCompradorTag_Value = 'N/A'
            else:
                municipioCompradorTag_Value = str(normalizar_texto(datos_cliente[0]['state']))
        else:
            correoCompradorTag_Value = 'N/A'
            departamentoCompradorTag_Value = 'N/A'
            direccionComercialCompradorTag_Value = 'N/A'
            telefonoCompradorTag_Value = 'N/A'
            municipioCompradorTag_Value = 'N/A'

        # Verificacion Nombre Comercial Comprador, en caso sea C/F se asignara como consumidor final
        if (str(nit_cliente[0][0]).upper() == 'C/F'):
            nombreComercialCompradorTag_Value = 'Consumidor Final'
        else:
            nombreComercialCompradorTag_Value = str(normalizar_texto(sales_invoice[0]['customer_name']))

        nitCompradorTag_Value = str((nit_cliente[0][0]).replace('-', '')).upper()


        # VERIFICACION DATOS CONFIGURACION FACTURA ELECTRONICA ------------------------------------------------
        claveTag_Value = str(datos_configuracion[0]['clave'])
        codigoEstablecimientoTag_Value = str(datos_configuracion[0]['codigo_establecimiento'])
        descripcionOtroImpuestoTag_Value = str(datos_configuracion[0]['descripcion_otro_impuesto'])
        idDispositivoTag_Value = str(datos_configuracion[0]['id_dispositivo'])
        importeOtrosImpuestosTag_Value = float(datos_configuracion[0]['importe_otros_impuestos'])
        importeTotalExentoTag_Value = float(datos_configuracion[0]['importe_total_exento'])
        nitGFACETag_Value = str((datos_configuracion[0]['nit_gface']).replace('-', '')).upper()
        regimenISRTag_Value = str(datos_configuracion[0]['regimen_isr'])
        usuarioTag_Value = str(datos_configuracion[0]['usuario'])
        validadorTag_Value = str(datos_configuracion[0]['validador'])

        if (datos_configuracion[0]['regimen_2989']) == 0:
            regimen2989Tag_Value = 'false'
        else:
            regimen2989Tag_Value = 'true'


        # VERIFICACION SERIES CONFIGURADAS FACTURA ELECTRONICA --------------------------------------------------
        # es-GT: Depende si una factura esta cancelada o es valida, **MODIFICAR PARA FUTURAS IMPLEMENTACIONES**
        # en-US: Depends if an invoice is canceled or is valid, ** MODIFY FOR FUTURE IMPLEMENTATIONS **
        estadoDocumentoTag_Value = str(series_configuradas[0]['estado_documento'])
        fechaResolucionTag_Value = str(series_configuradas[0]['fecha_resolucion'])
        numeroResolucionTag_Value = str(series_configuradas[0]['numero_resolucion']).replace('-', '')
        serieAutorizadaTag_Value = str(series_configuradas[0]['secuencia_infile'])
        serieDocumentoTag_Value = str(series_configuradas[0]['codigo_sat'])
        tipoDocumentoTag_Value = str(series_configuradas[0]['tipo_documento'])

        # es-GT: Las Facturas CFACE necesitan el correlativo de la factura, excluyendo la serie, por lo que se hace un slice
        #        para que tome solo el correlativo, si no es CFACE tomara la serie completa.
        # en-US: CFACE Invoices need the correlation of the invoice, excluding the series, so a slice is made so that it
        #        takes only the correlative, if it is not CFACE it will take the complete series.
        if (tipo_doc == 'CFACE'):
            nlong = len(prefijo_serie)
            numeroDocumentoTag_Value = str(serie_original_factura[nlong:])
        else:
            numeroDocumentoTag_Value = str(serie_original_factura)


        # VERIFICACION DATOS SALES INVOICE -----------------------------------------------------------------------
        codigoMonedaTag_Value = str(sales_invoice[0]['currency'])

        # en-US: Use the same format as Date Document, in case the document status
        # is active this field will not be taken into account, since it goes hand in
        # hand with document status because it can be canceled
        fechaAnulacionTag_Value = str((sales_invoice[0]['creation']).isoformat())

        # es-GT: Formato de fechas = "2013-10-10T00:00:00.000-06:00"
        # en-US: Format of dates = "2013-10-10T00: 00: 00.000-06: 00"
        fechaDocumentoTag_Value = str((sales_invoice[0]['creation']).isoformat())

        importeBrutoTag_Value = abs(float(sales_invoice[0]['net_total']))
        importeDescuentoTag_Value = abs(float(sales_invoice[0]['discount_amount']))
        importeNetoGravadoTag_Value = abs(float(sales_invoice[0]['grand_total']))
        montoTotalOperacionTag_Value = abs(float(sales_invoice[0]['grand_total']))

        # es-GT: Cuando es moneda local, obligatoriamente debe llevar 1.00
        # en-US: When it is local currency, it must necessarily carry 1.00
        tipoCambioTag_Value = float(sales_invoice[0]['conversion_rate'])

        # detalle impuesto de IVA, el total de iva en la operacion
        # detalleImpuestosIvaTag_Value = abs(float(sales_invoice[0]['total_taxes_and_charges']))
        detalleImpuestosIvaTag_Value = '{0:.2f}'.format(abs(float(sales_invoice[0]['shs_total_iva_fac'])))


        # VERICACION DATOS COMPANY -------------------------------------------------------------------------------
        try:
            departamentoVendedorTag_Value = str(normalizar_texto(direccion_empresa[0]['city']))
            direccionComercialVendedorTag_Value = '{0} {1}'.format(str(normalizar_texto(direccion_empresa[0]['address_line1'])),
                                                                   direccion_linea2)
            municipioVendedorTag_Value = str(normalizar_texto(direccion_empresa[0]['state']))
        except:
            frappe.msgprint(_('No se puede obtener direccion de la compania, por favor crearla'))

        nitVendedorTag_Value = str((datos_empresa[0]['nit_face_company']).replace('-', '')).upper()
        nombreComercialRazonSocialVendedorTag_Value = str(normalizar_texto(datos_empresa[0]['company_name']))
        nombreCompletoVendedorTag_Value = str(normalizar_texto(datos_empresa[0]['company_name']))


        # Guardara los datos para factura electronica en un diccionario, que luego se convertir en JSON
        # Para terminar como XML
        data_factura_json = {}

        # Estructura request INFILE
        # PRIMERA PARTE
        data_factura_json['S:Envelope'] = {}
        data_factura_json['S:Envelope']['@xmlns:S'] = 'http://schemas.xmlsoap.org/soap/envelope/'
        data_factura_json['S:Envelope']['S:Body'] = {}
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte'] = {}
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['@xmlns:ns2'] = 'http://listener.ingface.com/'
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte'] = {}
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['clave'] = claveTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte'] = {}
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['codigoEstablecimiento'] = codigoEstablecimientoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['codigoMoneda'] = codigoMonedaTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['correoComprador'] = str(correoCompradorTag_Value)
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['departamentoComprador'] = str(departamentoCompradorTag_Value)
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['departamentoVendedor'] = departamentoVendedorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['descripcionOtroImpuesto'] = descripcionOtroImpuestoTag_Value


        # SEGUNDA PARTE
        # Array para items
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte'] = []

        n_productos = (len(sales_invoice_item))
        # Si existe mas de un producto
        if n_productos > 1:
            for i in range(0, n_productos):
                item_factura_json = {}
                item_factura_json['cantidad'] = float(sales_invoice_item[i]['qty'])
                item_factura_json['codigoProducto'] = str(sales_invoice_item[i]['item_code'])
                item_factura_json['descripcionProducto'] = str((sales_invoice_item[i]['item_name']))
                item_factura_json['detalleImpuestosIva'] = float((sales_invoice_item[i]['facelec_sales_tax_for_this_row']))
                item_factura_json['importeExento'] = float((datos_configuracion[0]['importe_exento']))
                item_factura_json['importeNetoGravado'] = abs(float((sales_invoice_item[i]['facelec_amount_minus_excise_tax'])))
                item_factura_json['importeOtrosImpuestos'] = float((sales_invoice_item[i]['facelec_other_tax_amount']))
                item_factura_json['importeTotalOperacion'] = abs(float((sales_invoice_item[i]['amount'])))
                item_factura_json['montoBruto'] = '{0:.2f}'.format(float(((sales_invoice_item[i]['facelec_gt_tax_net_fuel_amt']) +
                                                                    (sales_invoice_item[i]['facelec_gt_tax_net_goods_amt']) +
                                                                    (sales_invoice_item[i]['facelec_gt_tax_net_services_amt']))))
                item_factura_json['montoDescuento'] = float(sales_invoice_item[i]['discount_percentage'])
                item_factura_json['precioUnitario'] = float(sales_invoice_item[i]['rate'])

                # es-GT: Obtiene directamente de la db el campo de stock para luego ser verificado como Servicio o Bien.
                # en-US: Obtains directly from the db the stock field to be later verified as Service or Good.
                detalle_stock = frappe.db.get_values('Item', filters={'item_code': str(sales_invoice_item[i]['item_code'])},
                                                     fieldname=['is_stock_item'])
                # Validacion de Bien o Servicio, en base a detalle de stock
                if (int((detalle_stock[0][0])) == 0):
                    tipoProductoTag_Value = 'S'
                if (int((detalle_stock[0][0])) == 1):
                    tipoProductoTag_Value = 'B'

                item_factura_json['tipoProducto'] = tipoProductoTag_Value
                item_factura_json['unidadMedida'] = str(sales_invoice_item[i]['facelec_three_digit_uom_code'])

                # Agrega al array n items
                data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte'].append(item_factura_json)

        else:
            item_factura_json = {}
            item_factura_json['cantidad'] = float(sales_invoice_item[0]['qty'])
            item_factura_json['codigoProducto'] = str(sales_invoice_item[0]['item_code'])
            item_factura_json['descripcionProducto'] = str((sales_invoice_item[0]['item_name']))
            item_factura_json['detalleImpuestosIva'] = float((sales_invoice_item[0]['facelec_sales_tax_for_this_row']))
            item_factura_json['importeExento'] = float((datos_configuracion[0]['importe_exento']))
            item_factura_json['importeNetoGravado'] = abs(float((sales_invoice_item[0]['facelec_amount_minus_excise_tax'])))
            item_factura_json['importeOtrosImpuestos'] = float((sales_invoice_item[0]['facelec_other_tax_amount']))
            item_factura_json['importeTotalOperacion'] = abs(float((sales_invoice_item[0]['amount'])))
            item_factura_json['montoBruto'] = '{0:.2f}'.format(float(((sales_invoice_item[0]['facelec_gt_tax_net_fuel_amt']) +
                                                                (sales_invoice_item[0]['facelec_gt_tax_net_goods_amt']) +
                                                                (sales_invoice_item[0]['facelec_gt_tax_net_services_amt']))))
            item_factura_json['montoDescuento'] = float(sales_invoice_item[0]['discount_percentage'])
            item_factura_json['precioUnitario'] = float(sales_invoice_item[0]['rate'])

            # es-GT: Obtiene directamente de la db el campo de stock para luego ser verificado como Servicio o Bien.
            # en-US: Obtains directly from the db the stock field to be later verified as Service or Good.
            detalle_stock = frappe.db.get_values('Item', filters={'item_code': str(sales_invoice_item[0]['item_code'])},
                                                 fieldname=['is_stock_item'])
            # Validacion de Bien o Servicio, en base a detalle de stock
            if (int((detalle_stock[0][0])) == 0):
                tipoProductoTag_Value = 'S'
            if (int((detalle_stock[0][0])) == 1):
                tipoProductoTag_Value = 'B'

            item_factura_json['tipoProducto'] = tipoProductoTag_Value
            item_factura_json['unidadMedida'] = str(sales_invoice_item[0]['facelec_three_digit_uom_code'])

            # Agrega el item al array
            data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleDte'].append(item_factura_json)


        # TERCERA PARTE
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['detalleImpuestosIva'] = detalleImpuestosIvaTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['direccionComercialComprador'] = direccionComercialCompradorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['direccionComercialVendedor'] = direccionComercialVendedorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['estadoDocumento'] = estadoDocumentoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['fechaAnulacion'] = str(fechaAnulacionTag_Value)
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['fechaDocumento'] = str(fechaDocumentoTag_Value)
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['fechaResolucion'] = str(fechaResolucionTag_Value)
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['idDispositivo'] = idDispositivoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeBruto'] = importeBrutoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeDescuento'] = importeDescuentoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeNetoGravado'] = importeNetoGravadoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeOtrosImpuestos'] = importeOtrosImpuestosTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['importeTotalExento'] = importeTotalExentoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['montoTotalOperacion'] = montoTotalOperacionTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['municipioComprador'] = municipioCompradorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['municipioVendedor'] = municipioVendedorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nitComprador'] = nitCompradorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nitGFACE'] = nitGFACETag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nitVendedor'] = nitVendedorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nombreComercialComprador'] = nombreComercialCompradorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nombreComercialRazonSocialVendedor'] = nombreComercialRazonSocialVendedorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['nombreCompletoVendedor'] = nombreCompletoVendedorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['numeroDocumento'] = numeroDocumentoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['numeroResolucion'] = numeroResolucionTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['regimen2989'] = regimen2989Tag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['regimenISR'] = regimenISRTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['serieAutorizada'] = serieAutorizadaTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['serieDocumento'] = serieDocumentoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['telefonoComprador'] = telefonoCompradorTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['tipoCambio'] = tipoCambioTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['dte']['tipoDocumento'] = tipoDocumentoTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['usuario'] = usuarioTag_Value
        data_factura_json['S:Envelope']['S:Body']['ns2:registrarDte']['dte']['validador'] = validadorTag_Value

        # PARA DEBUG: escribe el resultado JSON en un archivo
        with open('envio_test.json', 'w') as salida:
            salida.write(str((json.dumps(data_factura_json))))
            salida.close()

        xml_factura_infile = crear_xml_factura_electronica(json.dumps(data_factura_json))

        # Retorna string XML a partir de JSON
        return xml_factura_infile

    except:
        frappe.msgprint(_('Error al validar los datos para generar factura electronica'))
