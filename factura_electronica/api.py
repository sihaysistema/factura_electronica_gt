#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import requests
import xmltodict
import time 
import os
import xml.etree.cElementTree as ET

# Resuelve el problema de decodificacion
import sys

reload(sys)  
 
#sys.setdefaultencoding('Cp1252')
sys.setdefaultencoding('utf-8')

#Guardar los datos recibidos de infile en la Tabla 'Facturas Electronicas'
def guardar_factura_electronica(datos_recibidos, serie_fact, tiempo_envio):
	try:
		#documento: con la libreria xmltodict, se convierte de XML a Diccionario, para acceder a los datos
		#atraves de sus llaves
		documento = xmltodict.parse(datos_recibidos)

		# Crea un nuevo documento de Facturas Electronica
		tabFacturaElectronica = frappe.new_doc("Facturas Electronicas") 

		# Obtiene y Guarda la serie de factura
		tabFacturaElectronica.serie_factura_original = serie_fact

		# Obtiene y Guarda el CAE
		#tabFacturaElectronica.cae = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['cae'])
		
		# Obtiene y Guarda el Numero de Documento
		tabFacturaElectronica.numero_documento = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDocumento'])
		
		# Obtiene y Guarda el Estado
		#tabFacturaElectronica.estado = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['estado'])
		
		# Obtiene y Guarda las Anotaciones
		tabFacturaElectronica.anotaciones = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['anotaciones'])

#FIXME:
		# Obtiene y Guarda la Descripcion
		#tabFacturaElectronica.descripcion = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])
		
		# Obtiene y Guarda la Validez
		tabFacturaElectronica.valido = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['valido'])
		
		# Obtiene y Guarda el Numero DTE
		tabFacturaElectronica.numero_dte = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDte'])
		
		# Obtiene y Guarda el Rango Final Autorizado
		#tabFacturaElectronica.rango_final_autorizado = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoFinalAutorizado'])
		
		# Obtiene y Guarda el Rango Inicial Autorizado
		#tabFacturaElectronica.rango_inicio_autorizado = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoInicialAutorizado'])
		
		# Obtiene y Guarda el Regimen
		#tabFacturaElectronica.regimen = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['regimen'])
		
		# Obtiene y Guarda el tiempo en que se recibieron los datos de INFILE
		tabFacturaElectronica.recibido = time.strftime("%c")
		
		# Obtiene y Guarda el tiempo en que se enviaron los datos a INFILE
		tabFacturaElectronica.enviado = tiempo_envio
		
		# Guarda todos los datos en la tabla llamada 'FACTURAS ELECTRONICAS' de la base de datos de ERPNEXT
		tabFacturaElectronica.save()

		frappe.msgprint(_("Factura Electronica Generada!"))
	except:
		frappe.msgprint(_("Error: No se genero correctamente la Factura Electronica"))


@frappe.whitelist()
#Conexion y Consumo del Web Service Infile
def generar_factura_electronica(serie_factura, nombre_cliente):
##############################		OBTENER DATOS REQUERIDOS DE LA BASE DE DATOS ##############################
	dato_factura = serie_factura
	dato_cliente = nombre_cliente

	try:
	# Obteniendo datos necesarios para INFILE
		sales_invoice = frappe.db.get_values('Sales Invoice', filters = {'name': dato_factura},
	fieldname = ['name', 'idx', 'territory','total','grand_total', 'customer_name', 'company',
	'naming_series', 'creation', 'status', 'discount_amount', 'docstatus', 'modified'], as_dict = 1)

		sales_invoice_item = frappe.db.get_values('Sales Invoice Item', filters = {'parent': dato_factura}, 
	fieldname = ['item_name', 'qty', 'item_code', 'description', 'net_amount', 'base_net_amount', 
	'discount_percentage', 'net_rate', 'stock_uom', 'serial_no'], as_dict = 1)			

		datos_compania = frappe.db.get_values('Company', filters = {'name': 'CODEX'},
	fieldname = ['company_name', 'default_currency', 'country', 'nit'], as_dict = 1)

		datos_cliente = frappe.db.get_values('Address', filters = {'address_title': dato_cliente},
	fieldname = ['email_id', 'country', 'city', 'address_line1', 'state', 'phone'], as_dict = 1)

		nit_cliente = frappe.db.get_values('Customer', filters = {'name': dato_cliente},
	fieldname = 'nit')

		datos_configuracion = frappe.db.get_values('Configuracion Factura Electronica', filters = {'name': 'CONFIG-FAC00001'},
	fieldname = ['descripcion_otro_impuesto', 'importe_exento', 'id_dispositivo', 'validador', 'clave', 'fecha_resolucion',
	'codigo_establecimiento', 'numero_documento', 'importe_otros_impuestos', 'regimen_2989', 'tipo_documento',
	'serie_documento', 'usuario', 'serie_autorizada', 'numero_resolucion', 'regimen_isr', 'nit_gface', 'importe_total_exento'
	], as_dict = 1)

		frappe.msgprint(_('DATOS OBTENIDOS CON EXITO'))
	except:
		frappe.msgprint(_('Error: Con Base de Datos!'))

# CONSTRUYENDO PRIMERA PARTE DEL CUERPO XML
	# A cada variable se le asigna el valor que requiere
	claveTag_Value = (datos_configuracion[0]['clave'])
	codigoEstablecimientoTag_Value = str(datos_configuracion[0]['codigo_establecimiento'])
	codigoMonedaTag_Value = str(datos_compania[0]['default_currency'])
	correoCompradorTag_Value = str(datos_cliente[0]['email_id'])
	departamentoCompradorTag_Value = str(datos_cliente[0]['state'])
	departamentoVendedorTag_Value = str(datos_compania[0]['country'])
	descripcionOtroImpuestoTag_Value = str(datos_configuracion[0]['descripcion_otro_impuesto'])

# Formatenado la Primera parte del cuerpo XML
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

# Crear un archivo 'envio_request.xml' y luego escribe y guarda en el la primera parte del cuerpo XML
	with open('envio_request.xml', 'w') as salida:
		salida.write(body_parte1)
		salida.close()
 
	frappe.msgprint(_('Primera parte XML generada!'))

# CONSTRUYENDO LA SEGUNDA PARTE DEL CUERPO XML
# SI hay mas de un producto en la Factura, genera los 'detalleDte' necesarios, agregandolos al archivo 'envio_request.xml'
	if (len(sales_invoice_item)>1):
		n_productos = (len(sales_invoice_item))
		with open('envio_request.xml', 'a') as salida:
			for i in range(0, n_productos):
				cantidadTag_Value = str(sales_invoice_item[i]['qty'])
				codigoProductoTag_Value = str(sales_invoice_item[i]['item_code'])
				descripcionProductoTag_Value = str((sales_invoice_item[i]['description']))
				detalleImpuestosIvaTag_Value = str(24.0)
				importeExentoTag_Value = str((datos_configuracion[0]['importe_exento']))
				importeNetoGravadoTag_Value = str((sales_invoice[0]['grand_total']))
				importeOtrosImpuestosTag_Value = str((datos_configuracion[0]['importe_otros_impuestos']))
				importeTotalOperacionTag_Value = str(sales_invoice_item[i]['net_amount'])
				montoBrutoTag_Value = str(sales_invoice_item[i]['base_net_amount'])
				montoDescuentoTag_Value = str(sales_invoice_item[i]['discount_percentage'])
				precioUnitarioTag_Value = str(sales_invoice_item[i]['net_rate'])
				tipoProductoTag_Value = str(sales_invoice_item[i]['item_code'])
				unidadMedidaTag_Value = str(sales_invoice_item[i]['stock_uom'])

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

		frappe.msgprint(_('Segunda parte XML generada!'))

# SI hay un solo producto en la factura, se creara directamente la segunda parte del cuerpo XML
	else:
		cantidadTag_Value = str(sales_invoice_item[0]['qty'])
		codigoProductoTag_Value = str(sales_invoice_item[0]['item_code'])
		descripcionProductoTag_Value = str((sales_invoice_item[0]['description']))
		detalleImpuestosIvaTag_Value = str(24.0)
		importeExentoTag_Value = str((datos_configuracion[0]['importe_exento']))
		importeNetoGravadoTag_Value = str((sales_invoice[0]['grand_total']))
		importeOtrosImpuestosTag_Value = str((datos_configuracion[0]['importe_otros_impuestos']))
		importeTotalOperacionTag_Value = str(sales_invoice_item[0]['net_amount'])
		montoBrutoTag_Value = str(sales_invoice_item[0]['base_net_amount'])
		montoDescuentoTag_Value = str(sales_invoice_item[0]['discount_percentage'])
		precioUnitarioTag_Value = str(sales_invoice_item[0]['net_rate'])
		tipoProductoTag_Value = str(sales_invoice_item[0]['item_code'])
		unidadMedidaTag_Value = str(sales_invoice_item[0]['stock_uom'])

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

		frappe.msgprint(_('Segunda parte XML generada!'))

# CREANDO LA TERCERA PARTE DEL CUERPO XML
	#Asigna a cada variable su valor correspondiente	
	detalleImpuestosIvaTag_Value = "24.0"
	direccionComercialCompradorTag_Value = str((datos_cliente[0]['address_line1']).encode('utf-8'))
	direccionComercialVendedorTag_Value = str(datos_compania[0]['country'])
	estadoDocumentoTag_Value = "ACTIVO" #str(sales_invoice[0]['status'])
	fechaAnulacionTag_Value = "2013-10-10T00:00:00.000-06:00"
	fechaDocumentoTag_Value = "2013-10-10T00:00:00.000-06:00" #str(sales_invoice[0]['creation'])
	fechaResolucionTag_Value = "2013-02-15T00:00:00.000-06:00"
	idDispositivoTag_Value = str(datos_configuracion[0]['id_dispositivo']) 
	importeBrutoTag_Value = str(sales_invoice_item[0]['net_amount'])
	importeDescuentoTag_Value = str(sales_invoice[0]['discount_amount'])
	importeNetoGravadoTag_Value = str(sales_invoice[0]['grand_total'])
	importeOtrosImpuestosTag_Value = str(datos_configuracion[0]['importe_otros_impuestos'])
	importeTotalExentoTag_Value = str(datos_configuracion[0]['importe_total_exento'])
	montoTotalOperacionTag_Value = str(sales_invoice[0]['total'])
	municipioCompradorTag_Value = str(datos_cliente[0]['state'])
	nitCompradorTag_Value = str(nit_cliente[0][0])
	nitGFACETag_Value = str(datos_configuracion[0]['nit_gface'])
	nitVendedorTag_Value = str(datos_compania[0]['nit'])
	nombreComercialCompradorTag_Value = str(sales_invoice[0]['customer_name'])
	nombreComercialRazonSocialVendedorTag_Value = "DEMO,S.A."
	nombreCompletoVendedorTag_Value = str(datos_compania[0]['company_name'])
	numeroDocumentoTag_Value = str(datos_configuracion[0]['numero_documento'])
	numeroResolucionTag_Value = str(datos_configuracion[0]['numero_resolucion'])
	regimen2989Tag_Value = str(datos_configuracion[0]['regimen_2989'])
	regimenISRTag_Value = str(datos_configuracion[0]['regimen_isr'])
	serieAutorizadaTag_Value = str(datos_configuracion[0]['serie_autorizada'])
	serieDocumentoTag_Value = str(datos_configuracion[0]['serie_documento'])
	telefonoCompradorTag_Value = str(datos_cliente[0]['phone'])
	municipioVendedorTag_Value = str(datos_compania[0]['country'])
	tipoCambioTag_Value = "7.35" #AGREGAR A DOCTYPE
	tipoDocumentoTag_Value = str(datos_configuracion[0]['tipo_documento'])
	usuarioTag_Value = str(datos_configuracion[0]['usuario'])
	validadorTag_Value = str(datos_configuracion[0]['validador'])

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
	importeTotalOperacionTag_Value, municipioCompradorTag_Value, municipioVendedorTag_Value, nitCompradorTag_Value, nitGFACETag_Value,
	nitVendedorTag_Value, nombreComercialCompradorTag_Value, nombreComercialRazonSocialVendedorTag_Value, nombreCompletoVendedorTag_Value,
	numeroDocumentoTag_Value, numeroResolucionTag_Value, regimen2989Tag_Value, regimenISRTag_Value, serieAutorizadaTag_Value,
	serieDocumentoTag_Value, telefonoCompradorTag_Value, tipoCambioTag_Value, tipoDocumentoTag_Value, usuarioTag_Value, validadorTag_Value)

# Crear y Guarda la tercera parte del cuerpo XML
	with open('envio_request.xml', 'a') as salida: 
		salida.write(body_parte3)	
		salida.close()

	frappe.msgprint(_('Tercera parte XML generada!'))

	try:
		# lee el archivo request.xml generado para ser enviado a INFILE
		envio_datos = open('envio_request.xml', 'r').read()#.splitlines()

		#Obtiene el tiempo en que se envian los datos a INFILE
		tiempo_enviado = time.strftime("%c") #fixme:

		url="https://www.ingface.net/listener/ingface?wsdl" #URL de listener de INFILE
		headers = {'content-type': 'text/xml'} #CABECERAS: Indican el tipo de datos

		#Obtiene la respuesta por medio del metodo post, con los argumentos data, headers y time out
		#timeout: cumple la funcion de tiempo de espera, despues del tiempo asignado deja de esperar respuestas
		response = requests.post(url, data=envio_datos, headers=headers, timeout=3)

		#respuesta: guarda el cotenido 
		respuesta = response.content

		#frappe.msgprint(_(respuesta))

		#La funcion se encarga de guardar la respuesta de Infile en la base de datos de ERPNEXT
		guardar_factura_electronica(respuesta, dato_factura, tiempo_enviado)

		# Crea y Guarda la respuesta en XML que envia INFILE
		
		with open('respuesta.xml', 'w') as recibidoxml:
			recibidoxml.write(respuesta)
			recibidoxml.close()
	except:
		frappe.msgprint(_('Error en la comunicacion, intente mas tarde!'))

