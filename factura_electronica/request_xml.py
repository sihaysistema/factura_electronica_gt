# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime
from valida_errores import normalizar_texto

# Permite trabajar con acentos, ñ, simbolos, etc
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

def construir_xml(serie_original_factura, nombre_del_cliente, prefijo_serie, series_configuradas, nombre_config_validada):
    """Funcion para construir el xml con los datos necesarios para hacer una peticion de generacion de factura electronica
        a INFILE. La construccion del xml es en 3 partes. Los parametros que recibe se utilizan como filtro para la busqueda
        de datos en la base de datos para luego ser asignadas a variables y terminar construyendo el xml"""
    # CAPTURA DE DATOS, SI ES EXITOSO PROCEDE A ARMAR EL XML
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
                                                        'total', 'facelec_total_iva', 'currency'],
                                            as_dict=1)

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

        direccion_cliente = sales_invoice[0]['customer_address']
        dir_empresa = sales_invoice[0]['company_address']

        # Obtiene datos de los campos de la tabla 'Address' informacion de los clientes
        datos_cliente = frappe.db.get_values('Address', filters={'name': direccion_cliente},
                                            fieldname=['email_id', 'country', 'city',
                                                        'address_line1', 'state',
                                                        'phone', 'address_title', 'name'], as_dict=1)

        # Obtiene datos de direccion de la compañia de la tabla 'Address'
        direccion_empresa = frappe.db.get_values('Address', filters={'name': dir_empresa},
                                                fieldname=['email_id', 'country', 'city',
                                                            'address_line1', 'state',
                                                            'phone', 'address_title',
                                                            'county'], as_dict=1)

        # Obtiene datos de los campos de la tabla 'Company'
        datos_empresa = frappe.db.get_values('Company', filters={'name': sales_invoice[0]['company']},
                                            fieldname=['company_name', 'default_currency', 'country',
                                                        'nit_face_company'], as_dict=1)

        # Obtiene datos de los campos de la tabla 'Customer'
        nit_cliente = frappe.db.get_values('Customer', filters={'name': nombre_del_cliente},
                                            fieldname='nit_face_customer')

        # Obtiene datos de los campos de la tabla 'Configuracion Factura Electronica'
        datos_configuracion = frappe.db.get_values('Configuracion Factura Electronica',
                                                    filters={'name': nombre_config_validada},
                                                    fieldname=['descripcion_otro_impuesto', 'importe_exento',
                                                               'id_dispositivo', 'validador', 'clave', 'codigo_establecimiento',
                                                               'importe_otros_impuestos', 'regimen_2989', 'usuario', 'regimen_isr',
                                                               'nit_gface', 'importe_total_exento', 'url_listener'], as_dict=1)
    except:
        frappe.msgprint(_('''Error: Problemas con la Base de Datos. No se pudieron obtener los datos requeridos
                             para realizar una peticion a INFILE. Por favor verifica que existan todos los datos
                             de la empresa e intenta de nuevo.'''))
    else:
        # Empieza asignacion de datos y la construccion del xml
        # Para mas informacion de los campos consulte el xls documentado 'Campos Request' - monroy95
# -----------------------------------------------------------------------------------------------------------------------------
        # DATOS PARTE 1
        tipo_doc = str(series_configuradas[0]['tipo_documento'])
        # Verificacion datos del cliente
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
                direccionComercialCompradorTag_Value = str(normalizar_texto(datos_cliente[0]['address_line1'])) #.encode('utf-8')
                # frappe.msgprint(_(direccionComercialCompradorTag_Value))

            # Verificacion Telefono Comprador, en caso no exista se asignara N/A
            if ((datos_cliente[0]['phone']) == ''):
                telefonoCompradorTag_Value = 'N/A'
            else:
                telefonoCompradorTag_Value = str(datos_cliente[0]['phone'])

            # Verificacion Municipio Comprador, en caso no exista se asignara N/A
            if ((datos_cliente[0]['state']) == ''):
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
        if (str(nit_cliente[0][0]) == 'C/F' or str(nit_cliente[0][0]) == 'c/f'):
            nombreComercialCompradorTag_Value = 'Consumidor Final'
            # nombreComercialCompradorTag_Value = str(sales_invoice[0]['customer_name'])
        else:
            nombreComercialCompradorTag_Value = str(normalizar_texto(sales_invoice[0]['customer_name']))

        claveTag_Value = str(datos_configuracion[0]['clave'])
        codigoEstablecimientoTag_Value = str(datos_configuracion[0]['codigo_establecimiento'])
        codigoMonedaTag_Value = str(sales_invoice[0]['currency'])
        departamentoVendedorTag_Value = str(normalizar_texto(direccion_empresa[0]['city']))
        descripcionOtroImpuestoTag_Value = str(datos_configuracion[0]['descripcion_otro_impuesto'])
        # ----------------------------------------------------------------------------------------------------------------

        # es-GT: Formateando la Primera parte del cuerpo de request XML.
        # en-US: Formatting the first part of the request XML body.
        body_parte1 = """<?xml version="1.0" encoding="utf-8"?>
<S:Envelope xmlns:S="http://schemas.xmlsoap.org/soap/envelope/">
    <S:Body>
        <ns2:registrarDte xmlns:ns2="http://listener.ingface.com/">

            <dte>
                <clave>{0}</clave>

                <dte>
                    <codigoEstablecimiento>{1}</codigoEstablecimiento>
                    <codigoMoneda>{2}</codigoMoneda>
                    <correoComprador>{3}</correoComprador>
                    <departamentoComprador>{4}</departamentoComprador>
                    <departamentoVendedor>{5}</departamentoVendedor>
                    <descripcionOtroImpuesto>{6}</descripcionOtroImpuesto>
        """.format(claveTag_Value, codigoEstablecimientoTag_Value,
                   codigoMonedaTag_Value, correoCompradorTag_Value,
                   departamentoCompradorTag_Value, departamentoVendedorTag_Value,
                   descripcionOtroImpuestoTag_Value)

        with open('envio_request.xml', 'w') as salida:
            salida.write(body_parte1)
            salida.close()

# -----------------------------------------------------------------------------------------------------------------------------
        # PARTE 2 CONSTRUCCION XML
        n_productos = (len(sales_invoice_item))

        if (n_productos > 1):

            with open('envio_request.xml', 'a') as salida:

                for i in range(0, n_productos):
                    cantidadTag_Value = float(sales_invoice_item[i]['qty'])
                    codigoProductoTag_Value = str(sales_invoice_item[i]['item_code'])
                    descripcionProductoTag_Value = str((sales_invoice_item[i]['item_name']))
                    importeExentoTag_Value = float((datos_configuracion[0]['importe_exento']))
                    importeNetoGravadoTag_Value = abs(float((sales_invoice_item[i]['facelec_amount_minus_excise_tax'])))

                    # FORMA 1
                    # montoBrutoTag_Value =  float(sales_invoice_item[i]['net_amount'])
                    # FORMA 2
                    montoBrutoTag_Value = '{0:.2f}'.format(float(((sales_invoice_item[i]['facelec_gt_tax_net_fuel_amt']) +
                                                                  (sales_invoice_item[i]['facelec_gt_tax_net_goods_amt']) +
                                                                  (sales_invoice_item[i]['facelec_gt_tax_net_services_amt']))))

                    # es-GT: Calculo de IVA segun requiere infile.
                    # en-US: IVA calculation as required by infile.
                    # FORMA 1
                    # detalleImpuestosIvaTag_Value = '{0:.2f}'.format(abs(importeNetoGravadoTag_Value - (importeNetoGravadoTag_Value/1.12)))
                    # FORMA 2
                    detalleImpuestosIvaTag_Value = float((sales_invoice_item[i]['facelec_sales_tax_for_this_row']))

                    importeOtrosImpuestosTag_Value = float((sales_invoice_item[i]['facelec_other_tax_amount']))
                    importeTotalOperacionTag_Value = abs(float((sales_invoice_item[i]['amount'])))
                    montoDescuentoTag_Value = float(sales_invoice_item[i]['discount_percentage'])
                    precioUnitarioTag_Value = float(sales_invoice_item[i]['rate'])
                    unidadMedidaTag_Value = str(sales_invoice_item[i]['facelec_three_digit_uom_code'])

                    # es-GT: Obtiene directamente de la db el campo de stock para luego ser verificado como Servicio o Bien.
                    # en-US: Obtains directly from the db the stock field to be later verified as Service or Good.
                    detalle_stock = frappe.db.get_values('Item', filters={'item_code': codigoProductoTag_Value}, fieldname=['is_stock_item'])

                    # Validacion de Bien o Servicio, en base a detalle de stock
                    if (int((detalle_stock[0][0])) == 0):
                        tipoProductoTag_Value = 'S'
                    if (int((detalle_stock[0][0])) == 1):
                        tipoProductoTag_Value = 'B'

                    body_parte2 = """
                    <detalleDte>
                        <cantidad>{0}</cantidad>
                        <codigoProducto>{1}</codigoProducto>
                        <descripcionProducto>{2}</descripcionProducto>
                        <detalleImpuestosIva>{3}</detalleImpuestosIva>
                        <importeExento>{4}</importeExento>
                        <importeNetoGravado>{5}</importeNetoGravado>
                        <importeOtrosImpuestos>{6}</importeOtrosImpuestos>
                        <importeTotalOperacion>{7}</importeTotalOperacion>
                        <montoBruto>{8}</montoBruto>
                        <montoDescuento>{9}</montoDescuento>
                        <precioUnitario>{10}</precioUnitario>
                        <tipoProducto>{11}</tipoProducto>
                        <unidadMedida>{12}</unidadMedida>
                    </detalleDte>
                    """.format(cantidadTag_Value, codigoProductoTag_Value, descripcionProductoTag_Value,
                               detalleImpuestosIvaTag_Value, importeExentoTag_Value, importeNetoGravadoTag_Value,
                               importeOtrosImpuestosTag_Value, importeTotalOperacionTag_Value, montoBrutoTag_Value,
                               montoDescuentoTag_Value, precioUnitarioTag_Value, tipoProductoTag_Value,
                               unidadMedidaTag_Value)

                    salida.write(body_parte2)
            salida.close()

        # es-GT: SI hay un solo producto en la factura, se creara directamente la segunda parte del cuerpo XML
        # en-US: If there is only one product in the invoice, the second part of the XML body will be created directly
        else:
            cantidadTag_Value = float(sales_invoice_item[0]['qty'])
            codigoProductoTag_Value = str(sales_invoice_item[0]['item_code'])
            descripcionProductoTag_Value = str((sales_invoice_item[0]['item_name']))
            importeExentoTag_Value = float((datos_configuracion[0]['importe_exento']))
            importeNetoGravadoTag_Value = abs(float((sales_invoice_item[0]['facelec_amount_minus_excise_tax'])))

            # montoBrutoTag_Value =  float(sales_invoice_item[0]['net_amount'])
            # FIXME: Mejor opcion, obtener el valor del iva directo de la tabla de DB
            montoBrutoTag_Value = '{0:.2f}'.format(float(((sales_invoice_item[0]['facelec_gt_tax_net_fuel_amt']) +
                                                          (sales_invoice_item[0]['facelec_gt_tax_net_goods_amt']) +
                                                          (sales_invoice_item[0]['facelec_gt_tax_net_services_amt']))))

            # es-GT: Calculo de IVA segun requiere infile.
            # en-US: IVA calculation as required by infile.
            # FORMA 1
            # detalleImpuestosIvaTag_Value = '{0:.2f}'.format(abs(importeNetoGravadoTag_Value - (importeNetoGravadoTag_Value/1.12)))
            # FORMA 2
            detalleImpuestosIvaTag_Value = float((sales_invoice_item[0]['facelec_sales_tax_for_this_row']))

            importeOtrosImpuestosTag_Value = float((sales_invoice_item[0]['facelec_other_tax_amount']))
            importeTotalOperacionTag_Value = abs(float((sales_invoice_item[0]['amount'])))
            montoDescuentoTag_Value = float(sales_invoice_item[0]['discount_percentage'])
            precioUnitarioTag_Value = float(sales_invoice_item[0]['rate'])
            unidadMedidaTag_Value = str(sales_invoice_item[0]['facelec_three_digit_uom_code'])

            # es-GT: Obtiene directamente de la db el campo de stock para luego ser verificado como Servicio o Bien.
            # en-US: Obtains directly from the db the stock field to be later verified as Service or Good.
            detalle_stock = frappe.db.get_values('Item', filters={'item_code': codigoProductoTag_Value}, fieldname=['is_stock_item'])

            # Validacion de Bien (B) o Servicio (S), en base a detalle de stock
            if (int((detalle_stock[0][0])) == 0):
                tipoProductoTag_Value = 'S'
            if (int((detalle_stock[0][0])) == 1):
                tipoProductoTag_Value = 'B'

            body_parte2 = """
                    <detalleDte>
                        <cantidad>{0}</cantidad>
                        <codigoProducto>{1}</codigoProducto>
                        <descripcionProducto>{2}</descripcionProducto>
                        <detalleImpuestosIva>{3}</detalleImpuestosIva>
                        <importeExento>{4}</importeExento>
                        <importeNetoGravado>{5}</importeNetoGravado>
                        <importeOtrosImpuestos>{6}</importeOtrosImpuestos>
                        <importeTotalOperacion>{7}</importeTotalOperacion>
                        <montoBruto>{8}</montoBruto>
                        <montoDescuento>{9}</montoDescuento>
                        <precioUnitario>{10}</precioUnitario>
                        <tipoProducto>{11}</tipoProducto>
                        <unidadMedida>{12}</unidadMedida>
                    </detalleDte>
            """.format(cantidadTag_Value, codigoProductoTag_Value, descripcionProductoTag_Value,
                       detalleImpuestosIvaTag_Value, importeExentoTag_Value, importeNetoGravadoTag_Value,
                       importeOtrosImpuestosTag_Value, importeTotalOperacionTag_Value, montoBrutoTag_Value,
                       montoDescuentoTag_Value, precioUnitarioTag_Value, tipoProductoTag_Value, unidadMedidaTag_Value)

            with open('envio_request.xml', 'a') as salida:
                salida.write(body_parte2)
                salida.close()
# -----------------------------------------------------------------------------------------------------------------------------

        # PARTE 3 CONTRUCCION XML
        direccionComercialVendedorTag_Value = str(normalizar_texto(direccion_empresa[0]['address_line1']))

        # es-GT: Depende si una factura esta cancelada o es valida, **MODIFICAR PARA FUTURAS IMPLEMENTACIONES**
        # en-US: Depends if an invoice is canceled or is valid, ** MODIFY FOR FUTURE IMPLEMENTATIONS **
        estadoDocumentoTag_Value = str(series_configuradas[0]['estado_documento'])

        # es-GT: Usa el mismo formato que Fecha Documento, en caso el estado del documento
        # sea activo este campo no se tomara en cuenta, ya que va de la mano con estado documento porque puede ser Anulado

        # en-US: Use the same format as Date Document, in case the document status
        # is active this field will not be taken into account, since it goes hand in hand with document status because it can be canceled
        fechaAnulacionTag_Value = str((sales_invoice[0]['creation']).isoformat())

        # es-GT: Formato de fechas = "2013-10-10T00:00:00.000-06:00"
        # en-US: Format of dates = "2013-10-10T00: 00: 00.000-06: 00"
        fechaDocumentoTag_Value = str((sales_invoice[0]['creation']).isoformat())
        fechaResolucionTag_Value = (series_configuradas[0]['fecha_resolucion'])
        idDispositivoTag_Value = str(datos_configuracion[0]['id_dispositivo'])
        importeBrutoTag_Value = abs(float(sales_invoice[0]['net_total']))
        importeDescuentoTag_Value = float(sales_invoice[0]['discount_amount'])
        importeNetoGravadoTag_Value = abs(float(sales_invoice[0]['grand_total']))
        importeOtrosImpuestosTag_Value = float(datos_configuracion[0]['importe_otros_impuestos'])
        importeTotalExentoTag_Value = float(datos_configuracion[0]['importe_total_exento'])
        montoTotalOperacionTag_Value = abs(float(sales_invoice[0]['grand_total']))
        nitCompradorTag_Value = str(nit_cliente[0][0]).replace('-', '')
        nitGFACETag_Value = str(datos_configuracion[0]['nit_gface']).replace('-', '')
        nitVendedorTag_Value = str(datos_empresa[0]['nit_face_company']).replace('-', '')
        nombreComercialRazonSocialVendedorTag_Value = str(normalizar_texto(datos_empresa[0]['company_name']))
        nombreCompletoVendedorTag_Value = str(normalizar_texto(datos_empresa[0]['company_name']))

        # es-GT: Las Facturas CFACE necesitan el correlativo de la factura, excluyendo la serie, por lo que se hace un slice
        #        para que tome solo el correlativo, si no es CFACE tomara la serie completa.
        # en-US: CFACE Invoices need the correlation of the invoice, excluding the series, so a slice is made so that it
        #        takes only the correlative, if it is not CFACE it will take the complete series.
        if (tipo_doc == 'CFACE'):
            nlong = len(prefijo_serie)
            numeroDocumentoTag_Value = str(serie_original_factura[nlong:])
        else:
            numeroDocumentoTag_Value = str(serie_original_factura)

        # Numero de resolucion asignado por la SAT
        numeroResolucionTag_Value = str(series_configuradas[0]['numero_resolucion']).replace('-', '')
        regimenISRTag_Value = str(datos_configuracion[0]['regimen_isr'])
        serieAutorizadaTag_Value = str(series_configuradas[0]['secuencia_infile'])
        serieDocumentoTag_Value = str(series_configuradas[0]['codigo_sat'])
        municipioVendedorTag_Value = str(normalizar_texto(direccion_empresa[0]['state']))

        # es-GT: Cuando es moneda local, obligatoriamente debe llevar 1.00
        # en-US: When it is local currency, it must necessarily carry 1.00
        tipoCambioTag_Value = float(sales_invoice[0]['conversion_rate'])
        tipoDocumentoTag_Value = str(series_configuradas[0]['tipo_documento'])
        usuarioTag_Value = str(datos_configuracion[0]['usuario'])
        validadorTag_Value = str(datos_configuracion[0]['validador'])

        # detalle impuesto de IVA, el total de iva en la operacion
        # detalleImpuestosIvaTag_Value = abs(float(sales_invoice[0]['total_taxes_and_charges']))
        detalleImpuestosIvaTag_Value = '{0:.2f}'.format(abs(float(sales_invoice[0]['facelec_total_iva'])))

        if (datos_configuracion[0]['regimen_2989']) == 0:
            regimen2989Tag_Value = 'false'
        else:
            regimen2989Tag_Value = 'true'

        body_parte3 = """
                    <detalleImpuestosIva>{0}</detalleImpuestosIva>
                    <direccionComercialComprador>{1}</direccionComercialComprador>
                    <direccionComercialVendedor>{2}</direccionComercialVendedor>
                    <estadoDocumento>{3}</estadoDocumento>
                    <fechaAnulacion>{4}</fechaAnulacion>
                    <fechaDocumento>{5}</fechaDocumento>
                    <fechaResolucion>{6}</fechaResolucion>
                    <idDispositivo>{7}</idDispositivo>
                    <importeBruto>{8}</importeBruto>
                    <importeDescuento>{9}</importeDescuento>
                    <importeNetoGravado>{10}</importeNetoGravado>
                    <importeOtrosImpuestos>{11}</importeOtrosImpuestos>
                    <importeTotalExento>{12}</importeTotalExento>
                    <montoTotalOperacion>{13}</montoTotalOperacion>
                    <municipioComprador>{14}</municipioComprador>
                    <municipioVendedor>{15}</municipioVendedor>
                    <nitComprador>{16}</nitComprador>
                    <nitGFACE>{17}</nitGFACE>
                    <nitVendedor>{18}</nitVendedor>
                    <nombreComercialComprador>{19}</nombreComercialComprador>
                    <nombreComercialRazonSocialVendedor>{20}</nombreComercialRazonSocialVendedor>
                    <nombreCompletoVendedor>{21}</nombreCompletoVendedor>
                    <numeroDocumento>{22}</numeroDocumento>
                    <numeroResolucion>{23}</numeroResolucion>
                    <regimen2989>{24}</regimen2989>
                    <regimenISR>{25}</regimenISR>
                    <serieAutorizada>{26}</serieAutorizada>
                    <serieDocumento>{27}</serieDocumento>
                    <telefonoComprador>{28}</telefonoComprador>
                    <tipoCambio>{29}</tipoCambio>
                    <tipoDocumento>{30}</tipoDocumento>

                </dte>

                <usuario>{31}</usuario>
                <validador>{32}</validador>

            </dte>

        </ns2:registrarDte>
    </S:Body>
</S:Envelope>""".format(detalleImpuestosIvaTag_Value, direccionComercialCompradorTag_Value,
                        direccionComercialVendedorTag_Value, estadoDocumentoTag_Value,
                        fechaAnulacionTag_Value, fechaDocumentoTag_Value,
                        fechaResolucionTag_Value, idDispositivoTag_Value,
                        importeBrutoTag_Value, importeDescuentoTag_Value,
                        importeNetoGravadoTag_Value, importeOtrosImpuestosTag_Value,
                        importeTotalExentoTag_Value, montoTotalOperacionTag_Value,
                        municipioCompradorTag_Value, municipioVendedorTag_Value,
                        nitCompradorTag_Value, nitGFACETag_Value, nitVendedorTag_Value,
                        nombreComercialCompradorTag_Value,
                        nombreComercialRazonSocialVendedorTag_Value,
                        nombreCompletoVendedorTag_Value, numeroDocumentoTag_Value,
                        numeroResolucionTag_Value, regimen2989Tag_Value,
                        regimenISRTag_Value, serieAutorizadaTag_Value,
                        serieDocumentoTag_Value, telefonoCompradorTag_Value,
                        tipoCambioTag_Value, tipoDocumentoTag_Value,
                        usuarioTag_Value, validadorTag_Value)

        with open('envio_request.xml', 'a') as salida:
            salida.write(body_parte3)
            salida.close()
# -----------------------------------------------------------------------------------------------------------------------------
