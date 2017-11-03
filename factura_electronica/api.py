#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import requests
import xmltodict
import os
from datetime import datetime, date, time
from guardar_factura import guardar_factura_electronica as guardar
from valida_errores import encuentra_errores as errores
# es-GT: Resuelve el problema de codificacion
# en-US: Solve the coding problem
import sys
reload(sys)  
sys.setdefaultencoding('utf-8')

@frappe.whitelist()
# es-GT: Solicitud Factura Electronica del proveedor: Infile
# en-US: Supplier Electronic Invoice Request: Infile
def generar_factura_electronica(serie_factura, nombre_cliente):
	"""Obtencion de datos requeridos y construccion de request"""
	dato_factura = serie_factura
	dato_cliente = nombre_cliente
	#AGREGAR LA VERIFICACION DE QUE CONFIGURACION SE ESTA UTLIZANDO!!! por default esta utlizando la configuracion
	# CONFIG-FAC00001

	#es-GT: Verifica si ya existe una factura electronica con la serie del documento, si encuentra la serie retorna un mensaje.
	#esto para evitar que se generen facturas electronicas duplicadas. Si no encuentra la serie, el "try" capturara el error
	#procediendo con el "except".

	#en-US: Check if there is already an electronic invoice with the series of the document, if it finds the series returns a message.
	#this to avoid duplicate electronic invoices being generated. If you can not find the series, the "try" will capture the error
	#proceding with the "except".
	try:
		factura_electronica = frappe.db.get_values('Envios Facturas Electronicas', filters = {'serie_factura_original': dato_factura},
		fieldname = ['serie_factura_original', 'cae'], as_dict = 1)
		
		frappe.msgprint(_('<b>AVISO:</b> La Factura ya fue generada Anteriormente <b>{}</b>'.format(str(factura_electronica[0]['serie_factura_original']))))

		cae_Fac = str(factura_electronica[0]['cae'])

		return cae_Fac
	except:
		# es-GT: Si ocurre un error en la obtencion de datos de la base de datos, retornara un error.
		# en-US: If an error occurs in obtaining data from the database, an error will return.
		try:
		# es-GT: Obteniendo datos de la Base de Datos, necesarios para INFILE.
		# en-US: Obtaining data from the Database, necessary for INFILE.

			sales_invoice = frappe.db.get_values('Sales Invoice', filters = {'name': dato_factura},
			fieldname = ['name', 'idx', 'territory','grand_total', 'customer_name', 'company',
			'naming_series', 'creation', 'status', 'discount_amount', 'docstatus', 'modified', 'conversion_rate',
			'total_taxes_and_charges', 'net_total'], as_dict = 1)

			sales_invoice_item = frappe.db.get_values('Sales Invoice Item', filters = {'parent': dato_factura}, 
			fieldname = ['item_name', 'qty', 'item_code', 'description', 'net_amount', 'base_net_amount', 
			'discount_percentage', 'net_rate', 'stock_uom', 'serial_no', 'item_group', 'rate', 'amount'], as_dict = 1)			

			datos_compania = frappe.db.get_values('Company', filters = {'name': str(sales_invoice[0]['company'])},
			fieldname = ['company_name', 'default_currency', 'country', 'nit_face_company'], as_dict = 1)

			datos_cliente = frappe.db.get_values('Address', filters = {'address_title': dato_cliente},
			fieldname = ['email_id', 'country', 'city', 'address_line1', 'state', 'phone', 'address_title'], as_dict = 1)

			nit_cliente = frappe.db.get_values('Customer', filters = {'name': dato_cliente},
			fieldname = 'nit_face_customer')

			datos_configuracion = frappe.db.get_values('Configuracion Factura Electronica', filters = {'name': 'CONFIG-FAC00001'},
			fieldname = ['descripcion_otro_impuesto', 'importe_exento', 'id_dispositivo', 'validador', 'clave', 'fecha_resolucion',
			'codigo_establecimiento', 'estado_documento', 'importe_otros_impuestos', 'regimen_2989', 'tipo_documento',
			'serie_documento', 'usuario', 'serie_autorizada', 'numero_resolucion', 'regimen_isr', 'nit_gface', 'importe_total_exento']
			, as_dict = 1)

		except:
			frappe.msgprint(_('Error: Problemas con la Base de Datos!'))

		# es-GT: Construyendo la primera parte del cuerpo XML.
		# en-US: Building the first part of the XML body.
		try:
			# es-GT: Si no encuentra datos sobre el cliente, el "try" capturara el error y pondra los campos con valor 'N/A'.
			# en-US: If it does not find data about the client, the "try" will capture the error and put the fields with value 'N/A'.
			if ((datos_cliente[0]['address_title']) is None): fallo = True
		except:
			correoCompradorTag_Value = 'N/A'
			departamentoCompradorTag_Value = 'N/A'
			direccionComercialCompradorTag_Value = 'N/A'
			nombreComercialCompradorTag_Value = 'Consumidor Final'
			telefonoCompradorTag_Value = 'N/A'
			municipioCompradorTag_Value = 'N/A'
		else:
			# es-GT: Si se encuentran los datos del cliente, verificara uno a uno para que quede con el valor correspondiente.
			# en-US: If the client's data is found, it will verify one by one so that it remains with the corresponding value.
			if ((datos_cliente[0]['email_id']) is None): 
				correoCompradorTag_Value = 'N/A'
			else:
				correoCompradorTag_Value = str(datos_cliente[0]['email_id'])

			if ((datos_cliente[0]['state']) is None): 
				departamentoCompradorTag_Value = 'N/A'
			else: 
				departamentoCompradorTag_Value = str(datos_cliente[0]['state'])

			if ((datos_cliente[0]['address_line1']) is None): 
				direccionComercialCompradorTag_Value = 'N/A'
			else:
				direccionComercialCompradorTag_Value = str((datos_cliente[0]['address_line1']).encode('utf-8'))

			if (str(nit_cliente[0][0]) == 'C/F'):
				nombreComercialCompradorTag_Value = 'Consumidor Final'
			else:    		
				nombreComercialCompradorTag_Value = str(sales_invoice[0]['customer_name'])

			if ((datos_cliente[0]['phone']) is None):
				telefonoCompradorTag_Value = 'N/A'
			else:
				telefonoCompradorTag_Value = str(datos_cliente[0]['phone'])

			if ((datos_cliente[0]['state']) is None):
				municipioCompradorTag_Value = 'N/A'
			else:
				municipioCompradorTag_Value = str(datos_cliente[0]['state'])

		claveTag_Value = str(datos_configuracion[0]['clave'])
		codigoEstablecimientoTag_Value = str(datos_configuracion[0]['codigo_establecimiento'])
		codigoMonedaTag_Value = str(datos_compania[0]['default_currency'])

		departamentoVendedorTag_Value = str(datos_compania[0]['country']) 
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
					importeNetoGravadoTag_Value = float((sales_invoice_item[i]['amount']))
					montoBrutoTag_Value =  float(sales_invoice_item[i]['net_amount'])

					# es-GT: Calculo de IVA segun requiere infile.
					# en-US: IVA calculation as required by infile.
					detalleImpuestosIvaTag_Value = '{0:.2f}'.format(importeNetoGravadoTag_Value - (importeNetoGravadoTag_Value/1.12))

					importeOtrosImpuestosTag_Value = float((datos_configuracion[0]['importe_otros_impuestos']))
					importeTotalOperacionTag_Value = float((sales_invoice_item[i]['amount']))					
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
			importeNetoGravadoTag_Value = float((sales_invoice_item[0]['amount']))
			montoBrutoTag_Value =  float(sales_invoice_item[0]['net_amount'])

			# es-GT: Calculo de IVA segun requiere infile.
			# en-US: IVA calculation as required by infile.
			detalleImpuestosIvaTag_Value = '{0:.2f}'.format(importeNetoGravadoTag_Value - (importeNetoGravadoTag_Value/1.12))

			importeOtrosImpuestosTag_Value = float((datos_configuracion[0]['importe_otros_impuestos']))
			importeTotalOperacionTag_Value = float((sales_invoice_item[0]['amount']))					
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
		direccionComercialVendedorTag_Value = str(datos_compania[0]['country'])

		# es-GT: Depende si una factura esta cancelada o es valida, **MODIFICAR PARA FUTURAS IMPLEMENTACIONES**
		# en-US: Depends if an invoice is canceled or is valid, ** MODIFY FOR FUTURE IMPLEMENTATIONS **
		estadoDocumentoTag_Value = str(datos_configuracion[0]['estado_documento']) 

		# es-GT: Usa el mismo formato que Fecha Documento, en caso el estado del documento
		#sea activo este campo no se tomara en cuenta, ya que va de la mano con estado documento porque puede ser Anulado

		# en-US: Use the same format as Date Document, in case the document status
		#is active this field will not be taken into account, since it goes hand in hand with document status because it can be canceled
		fechaAnulacionTag_Value = str((sales_invoice[0]['creation']).isoformat()) 

		# es-GT: Formato de fechas = "2013-10-10T00:00:00.000-06:00"
		# en-US: Format of dates = "2013-10-10T00: 00: 00.000-06: 00"
		fechaDocumentoTag_Value = str((sales_invoice[0]['creation']).isoformat())  

		fechaResolucionTag_Value = (datos_configuracion[0]['fecha_resolucion'])
		idDispositivoTag_Value = str(datos_configuracion[0]['id_dispositivo']) 
		importeBrutoTag_Value = float(sales_invoice[0]['net_total'])
		importeDescuentoTag_Value = float(sales_invoice[0]['discount_amount'])
		importeNetoGravadoTag_Value = float(sales_invoice[0]['grand_total'])
		importeOtrosImpuestosTag_Value = float(datos_configuracion[0]['importe_otros_impuestos'])
		importeTotalExentoTag_Value = float(datos_configuracion[0]['importe_total_exento'])
		montoTotalOperacionTag_Value = float(sales_invoice[0]['grand_total']) 
		nitCompradorTag_Value = str(nit_cliente[0][0]) 		
		nitGFACETag_Value = str(datos_configuracion[0]['nit_gface'])
		nitVendedorTag_Value = str(datos_compania[0]['nit_face_company'])
	
		nombreComercialRazonSocialVendedorTag_Value = str(datos_compania[0]['company_name'])
		
		nombreCompletoVendedorTag_Value = str(datos_compania[0]['company_name'])
		numeroDocumentoTag_Value = str(dato_factura)
		numeroResolucionTag_Value = str(datos_configuracion[0]['numero_resolucion'])
		regimen2989Tag_Value = str(datos_configuracion[0]['regimen_2989'])
		regimenISRTag_Value = str(datos_configuracion[0]['regimen_isr'])
		serieAutorizadaTag_Value = str(datos_configuracion[0]['serie_autorizada'])
		serieDocumentoTag_Value = str(datos_configuracion[0]['serie_documento'])
		municipioVendedorTag_Value = str(datos_compania[0]['country'])

		# es-GT: Cuando es moneda local, obligatoriamente debe llevar 1.00
		# en-US: When it is local currency, it must necessarily carry 1.00
		tipoCambioTag_Value = float(sales_invoice[0]['conversion_rate']) 

		tipoDocumentoTag_Value = str(datos_configuracion[0]['tipo_documento'])
		usuarioTag_Value = str(datos_configuracion[0]['usuario'])
		validadorTag_Value = str(datos_configuracion[0]['validador'])
		detalleImpuestosIvaTag_Value = float(sales_invoice[0]['total_taxes_and_charges'])

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

		try:
			# es-GT: lee el archivo request.xml generado anteriormente para luego ser enviado a INFILE.
			# en-US: read the previously generated request.xml file and then send it to INFILE.
			envio_datos = open('envio_request.xml', 'r').read()#.splitlines()

			url="https://www.ingface.net/listener/ingface?wsdl" #URL de listener de INFILE
			headers = {'content-type': 'text/xml'} #CABECERAS: Indican el tipo de datos

			# es-GT: Obtiene la respuesta por medio del metodo post, con los argumentos data, headers y time out
			#timeout: cumple la funcion de tiempo de espera, despues del tiempo asignado deja de esperar respuestas

			# en-US: Get the answer through the post method, with the data, headers and time out arguments
			#timeout: fulfills the function of waiting time, after the assigned time stops waiting for answers
			tiempo_enviado = datetime.now()
			response = requests.post(url, data=envio_datos, headers=headers, timeout=5)
			respuesta = response.content
		except:
			frappe.msgprint(_('Error en la Comunicacion, Verifique su conexion a Internet o intente mas tarde!'))
		else:
			documento_descripcion = xmltodict.parse(respuesta)
			# es-GT: Los errores, se describen en descripcion del response.xml que envia de vuelta INFILE.
			# en-US: The errors are described in the response.xml description that you send back INFILE.
			descripciones = (documento_descripcion['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])
			
			# es-GT: en la variable se guarda un diccionario con los errores o mensaje de OK, retornados por la funcion 'errores'.
			# en-US: in the variable a dictionary is saved with the errors or OK message, returned by the 'errors' function.
			errores_diccionario = errores(descripciones)
			
			# es-GT: Tomar en cuenta que cuando la factura electronica se genera correctamente, infile retorna un mensaje
			# indicando la generacion correcta.

			# en-US: Take into account that when the electronic invoice is generated correctly, infile returns a message
			# indicating the correct generation.

			# es-GT: Proceso para la obtencion de los errores generados o mensaje de OK, en caso exista mas de uno.
			# en-US: Process for obtaining the generated errors or OK message, if there is more than one.
			if (len(errores_diccionario)>0): 
				try:
					if (((errores_diccionario['Mensaje']).lower()) == 'dte generado con exito'):
						datoCAEF = guardar(respuesta, dato_factura, tiempo_enviado)

						frappe.msgprint(_('FACTURA GENERADA CON EXITO'))
								
						with open('respuesta.xml', 'w') as recibidoxml:
							recibidoxml.write(respuesta)
							recibidoxml.close()	
								
						return datoCAEF
				except:
					frappe.msgprint(_('''
					AVISOS <span class="label label-default" style="font-size: 16px">{}</span>
					'''.format(str(len(errores_diccionario)))+ ' VERIFIQUE SU MANUAL'))
					for llave in errores_diccionario:
						frappe.msgprint(_('''
						<span class="label label-warning" style="font-size: 14px">{}</span>
						'''.format(str(llave)) + ' = '+ str(errores_diccionario[llave])))

					frappe.msgprint(_('NO GENERADA'))
						#frappe.msgprint(_('FACTURA GENERADA CON EXITO'))
						#guardar(respuesta, dato_factura, tiempo_enviado)