#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _

from datetime import datetime
import sys
reload(sys)  
sys.setdefaultencoding('utf-8')

def construir_xml(sales_invoice, direccion_cliente, datos_cliente, sales_invoice_item, datos_compania, nit_cliente, datos_configuracion, series_configuradas, dato_factura, direccion_compania):
	"""Genera el archivo xml, peticion para generar la factura electronica"""
	
	direccion_cliente = str(sales_invoice[0]['customer_address'])
	serie_doc = str(sales_invoice[0]['naming_series'])
	tipo_doc = str(series_configuradas[0]['tipo_documento'])

	# es-GT: Verifica si existe la direccion del cliente, en caso si exista la direccion, verificara uno a uno para que los datos 
	#        sean correctos.
	# en-US: Verify if the customer's address exists, in case the address exists, verify one by one so that the data is correct.
	if frappe.db.exists('Address', {'name': direccion_cliente}): 
		if ((datos_cliente[0]['email_id']) is None): 
			correoCompradorTag_Value = 'N/A'
		else:
			correoCompradorTag_Value = str(datos_cliente[0]['email_id'])

		if ((datos_cliente[0]['state']) == ''): 
			departamentoCompradorTag_Value = 'N/A'
		else: 
			departamentoCompradorTag_Value = str(datos_cliente[0]['state'])

		if ((datos_cliente[0]['address_line1']) == ''): 
			direccionComercialCompradorTag_Value = 'N/A'
		else:
			direccionComercialCompradorTag_Value = str((datos_cliente[0]['address_line1']).encode('utf-8'))

		if (str(nit_cliente[0][0]) == 'C/F' or str(nit_cliente[0][0]) == 'c/f'):
			nombreComercialCompradorTag_Value = 'Consumidor Final'
		else:    		
			nombreComercialCompradorTag_Value = str(sales_invoice[0]['customer_name'])

		if ((datos_cliente[0]['phone']) == ''):
			telefonoCompradorTag_Value = 'N/A'
		else:
			telefonoCompradorTag_Value = str(datos_cliente[0]['phone'])

		if ((datos_cliente[0]['city']) == ''):
			municipioCompradorTag_Value = 'N/A'
		else:
			municipioCompradorTag_Value = str(datos_cliente[0]['city'])

	# es-GT: En caso no exista la direccion del cliente, los valores se establecen a 'N/A' y a 'Consumidor Final'.
	# en-US: In case there is no customer address, the values are set to 'N / A' and 'Final Consumer'.
	else:
		correoCompradorTag_Value = 'N/A'
		departamentoCompradorTag_Value = 'N/A'
		direccionComercialCompradorTag_Value = 'N/A'
		nombreComercialCompradorTag_Value = 'Consumidor Final'
		telefonoCompradorTag_Value = 'N/A'
		municipioCompradorTag_Value = 'N/A'
	
	claveTag_Value = str(datos_configuracion[0]['clave'])
	codigoEstablecimientoTag_Value = str(datos_configuracion[0]['codigo_establecimiento'])
	codigoMonedaTag_Value = str(datos_compania[0]['default_currency'])

	departamentoVendedorTag_Value = str(direccion_compania[0]['state']) 
	descripcionOtroImpuestoTag_Value = str(datos_configuracion[0]['descripcion_otro_impuesto'])

	# es-GT: Formateando la Primera parte del cuerpo de request XML.
	# en-US: Formatting the first part of the request XML body.
	body_parte1 = """<?xml version="1.0" ?>
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
		<descripcionOtroImpuesto>{6}</descripcionOtroImpuesto>""".format(claveTag_Value, codigoEstablecimientoTag_Value,
	codigoMonedaTag_Value, correoCompradorTag_Value, departamentoCompradorTag_Value, departamentoVendedorTag_Value,
	descripcionOtroImpuestoTag_Value)

	# es-GT: Crear un archivo 'envio_request.xml' y luego escribe y guarda en el la primera parte del cuerpo XML.
	# en-US: Create a file 'envio_request.xml' and then write and save in the first part of the XML body.
	with open('envio_request.xml', 'w') as salida:
		salida.write(body_parte1)
		salida.close()

	# es-GT: CONSTRUYENDO LA SEGUNDA PARTE DEL CUERPO XML.
	# SI hay mas de un producto en la Factura, genera los 'detalleDte' necesarios, agregandolos al archivo 'envio_request.xml'.

	# en-US: BUILDING THE SECOND PART OF THE XML BODY.
	# If there is more than one product in the Invoice, generate the necessary 'detalleDte', adding them to the file 'envio_request.xml'.
	if (len(sales_invoice_item)>1):
		n_productos = (len(sales_invoice_item))
		with open('envio_request.xml', 'a') as salida:
			for i in range(0, n_productos):
				cantidadTag_Value = float(sales_invoice_item[i]['qty'])
				codigoProductoTag_Value = str(sales_invoice_item[i]['item_code'])
				descripcionProductoTag_Value = str((sales_invoice_item[i]['description']))
				importeExentoTag_Value = float((datos_configuracion[0]['importe_exento'])) 
				importeNetoGravadoTag_Value = abs(float((sales_invoice_item[i]['amount'])))
				montoBrutoTag_Value =  float(sales_invoice_item[i]['net_amount'])

				# es-GT: Calculo de IVA segun requiere infile.
				# en-US: IVA calculation as required by infile.
				detalleImpuestosIvaTag_Value = '{0:.2f}'.format(abs(importeNetoGravadoTag_Value - (importeNetoGravadoTag_Value/1.12)))

				importeOtrosImpuestosTag_Value = float((datos_configuracion[0]['importe_otros_impuestos']))
				importeTotalOperacionTag_Value = abs(float((sales_invoice_item[i]['amount'])))
				montoDescuentoTag_Value = float(sales_invoice_item[i]['discount_percentage'])
				precioUnitarioTag_Value = float(sales_invoice_item[i]['rate'])
				unidadMedidaTag_Value = str(sales_invoice_item[i]['stock_uom'])

				# es-GT: Obtiene directamente de la db el campo de stock para luego ser verificado como Servicio o Bien.
				# en-US: Obtains directly from the db the stock field to be later verified as Service or Good.
				detalle_stock = frappe.db.get_values('Item', filters = {'item_code': codigoProductoTag_Value},	fieldname = ['is_stock_item'])

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
	</detalleDte>""".format(cantidadTag_Value, codigoProductoTag_Value, descripcionProductoTag_Value, detalleImpuestosIvaTag_Value,
				importeExentoTag_Value, importeNetoGravadoTag_Value, importeOtrosImpuestosTag_Value, importeTotalOperacionTag_Value,
				montoBrutoTag_Value, montoDescuentoTag_Value, precioUnitarioTag_Value, tipoProductoTag_Value, unidadMedidaTag_Value) 
				salida.write(body_parte2)	
		salida.close()

	# es-GT: SI hay un solo producto en la factura, se creara directamente la segunda parte del cuerpo XML
	# en-US: If there is only one product in the invoice, the second part of the XML body will be created directly
	else:
		cantidadTag_Value = float(sales_invoice_item[0]['qty'])
		codigoProductoTag_Value = str(sales_invoice_item[0]['item_code'])
		descripcionProductoTag_Value = str((sales_invoice_item[0]['description']))
		importeExentoTag_Value = float((datos_configuracion[0]['importe_exento']))
		importeNetoGravadoTag_Value = abs(float((sales_invoice_item[0]['amount'])))
		montoBrutoTag_Value =  float(sales_invoice_item[0]['net_amount'])

		# es-GT: Calculo de IVA segun requiere infile.
		# en-US: IVA calculation as required by infile.
		detalleImpuestosIvaTag_Value = '{0:.2f}'.format(abs(importeNetoGravadoTag_Value - (importeNetoGravadoTag_Value/1.12)))

		importeOtrosImpuestosTag_Value = float((datos_configuracion[0]['importe_otros_impuestos']))
		importeTotalOperacionTag_Value = abs(float((sales_invoice_item[0]['amount'])))
		montoDescuentoTag_Value = float(sales_invoice_item[0]['discount_percentage'])
		precioUnitarioTag_Value = float(sales_invoice_item[0]['rate'])
		unidadMedidaTag_Value = str(sales_invoice_item[0]['stock_uom'])

		# es-GT: Obtiene directamente de la db el campo de stock para luego ser verificado como Servicio o Bien.
		# en-US: Obtains directly from the db the stock field to be later verified as Service or Good.
		detalle_stock = frappe.db.get_values('Item', filters = {'item_code': codigoProductoTag_Value},	fieldname = ['is_stock_item'])

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
	</detalleDte>""".format(cantidadTag_Value, codigoProductoTag_Value, descripcionProductoTag_Value, detalleImpuestosIvaTag_Value,
		importeExentoTag_Value, importeNetoGravadoTag_Value, importeOtrosImpuestosTag_Value, importeTotalOperacionTag_Value,
		montoBrutoTag_Value, montoDescuentoTag_Value, precioUnitarioTag_Value, tipoProductoTag_Value, unidadMedidaTag_Value)

		with open('envio_request.xml', 'a') as salida: 
			salida.write(body_parte2)	
			salida.close() 
	
	# es-GT: CONSTRUYENDO LA TERCERA PARTE DEL CUERPO XML
	# Asigna a cada variable su valor correspondiente	

	# en-US: BUILDING THE THIRD PART OF THE XML BODY
	# Assign each variable its corresponding value
	direccionComercialVendedorTag_Value = str(direccion_compania[0]['address_line1'])

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
	nitCompradorTag_Value = str(nit_cliente[0][0]) 		
	nitGFACETag_Value = str(datos_configuracion[0]['nit_gface'])
	nitVendedorTag_Value = str(datos_compania[0]['nit_face_company'])
		
	nombreComercialRazonSocialVendedorTag_Value = str(datos_compania[0]['company_name'])
			
	nombreCompletoVendedorTag_Value = str(datos_compania[0]['company_name'])

	# es-GT: Las Facturas CFACE necesitan el correlativo de la factura, excluyendo la serie, por lo que se hace un slice
	#        para que tome solo el correlativo, si no es CFACE tomara la serie completa.
	# en-US: CFACE Invoices need the correlation of the invoice, excluding the series, so a slice is made so that it 
	#        takes only the correlative, if it is not CFACE it will take the complete series.
	if (tipo_doc == 'CFACE'):
		nlong = len(serie_doc)
		numeroDocumentoTag_Value = str(dato_factura[nlong:])
	else:
		numeroDocumentoTag_Value = str(dato_factura)

	numeroResolucionTag_Value = str(series_configuradas[0]['numero_resolucion'])
			
	regimenISRTag_Value = str(datos_configuracion[0]['regimen_isr'])
	serieAutorizadaTag_Value = str(series_configuradas[0]['secuencia_infile'])
	serieDocumentoTag_Value = str(series_configuradas[0]['codigo_sat'])
	municipioVendedorTag_Value = str(direccion_compania[0]['city'])

	# es-GT: Cuando es moneda local, obligatoriamente debe llevar 1.00
	# en-US: When it is local currency, it must necessarily carry 1.00
	tipoCambioTag_Value = float(sales_invoice[0]['conversion_rate']) 

	tipoDocumentoTag_Value = str(series_configuradas[0]['tipo_documento'])
	usuarioTag_Value = str(datos_configuracion[0]['usuario'])
	validadorTag_Value = str(datos_configuracion[0]['validador'])
	detalleImpuestosIvaTag_Value = abs(float(sales_invoice[0]['total_taxes_and_charges']))

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
</S:Envelope>""".format(detalleImpuestosIvaTag_Value, direccionComercialCompradorTag_Value, direccionComercialVendedorTag_Value, 
	estadoDocumentoTag_Value, fechaAnulacionTag_Value, fechaDocumentoTag_Value, fechaResolucionTag_Value, idDispositivoTag_Value,
	importeBrutoTag_Value, importeDescuentoTag_Value, importeNetoGravadoTag_Value, importeOtrosImpuestosTag_Value, importeTotalExentoTag_Value,
	montoTotalOperacionTag_Value, municipioCompradorTag_Value, municipioVendedorTag_Value, nitCompradorTag_Value, nitGFACETag_Value,
	nitVendedorTag_Value, nombreComercialCompradorTag_Value, nombreComercialRazonSocialVendedorTag_Value, nombreCompletoVendedorTag_Value,
	numeroDocumentoTag_Value, numeroResolucionTag_Value, regimen2989Tag_Value, regimenISRTag_Value, serieAutorizadaTag_Value,
	serieDocumentoTag_Value, telefonoCompradorTag_Value, tipoCambioTag_Value, tipoDocumentoTag_Value, usuarioTag_Value, validadorTag_Value)

	# es-GT: Crear y Guarda la tercera parte del cuerpo XML.
	# en-US: Create and Save the third part of the XML body.
	with open('envio_request.xml', 'a') as salida: 
		salida.write(body_parte3)	
		salida.close()