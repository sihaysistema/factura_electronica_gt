#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import xmltodict
from datetime import datetime, date, time
import os
# es-GT: Resuelve el problema de codificacion
# en-US: Solve the coding problem
import sys
reload(sys)  
#sys.setdefaultencoding('Cp1252')
sys.setdefaultencoding('utf-8')

# es-GT: Guardar los datos recibidos de infile en la Tabla 'Facturas Electronicas'.
# en-US: Save the data received from infile in the 'Invoices Electronic' Table.
def guardar_factura_electronica(datos_recibidos, serie_fact, tiempo_envio):
    	'''Guarda los datos recibidos de infile en la tabla Envios Facturas Electronicas de la base de datos ERPNext'''
	try:
		# es-GT: documento: con la libreria xmltodict, se convierte de XML a Diccionario, para acceder a los datos
		#atraves de sus llaves

		# en-US: documento: with the xmltodict library, it is converted from XML to Dictionary, to access the data
		#transfer of your keys
		documento = xmltodict.parse(datos_recibidos)

		# es-GT: Crea un nuevo documento de Facturas Electronica.
		# en-US: Create a new Electronic Invoices document.
		tabFacturaElectronica = frappe.new_doc("Envios Facturas Electronicas") 

		# es-GT: Obtiene y Guarda la serie de factura.
		# en-US: Obtain and Save the invoice series.
		tabFacturaElectronica.serie_factura_original = serie_fact

		# es-GT: Obtiene y Guarda el CAE
		# en-US: Obtain and Save the CAE
		tabFacturaElectronica.cae = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['cae'])
		cae_dato = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['cae'])

		# es-GT: Obtiene y Guarda el Numero de Documento
		# en-US: Obtain and Save the Document Number
		tabFacturaElectronica.numero_documento = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDocumento'])
		
		# es-GT: Obtiene y Guarda el Estado
		# en-US: Obtain and Save the State
		tabFacturaElectronica.estado = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['estado'])
		
		# es-GT: Obtiene y Guarda las Anotaciones
		# en-US: Obtain and Save the Annotations
		tabFacturaElectronica.anotaciones = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['anotaciones'])

		# es-GT: Obtiene y Guarda la Descripcion: En este campo estan todas las descripciones de errores y mensaje de generacion correcta
		# en-US: Obtain and Save the Description: In this field are all the descriptions of errors and correct generation message
		tabFacturaElectronica.descripcion = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])

		# es-GT: Obtiene y Guarda la Validez
		# en-US: Obtain and Save the Validity
		tabFacturaElectronica.valido = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['valido'])
		
		# es-GT: Obtiene y Guarda el Numero DTE
		# en-US: Obtain and Save the DTE Number
		tabFacturaElectronica.numero_dte = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDte'])
		
		# es-GT: Obtiene y Guarda el Rango Final Autorizado
		# en-US: Obtain and Save the Authorized Final Range
		tabFacturaElectronica.rango_final_autorizado = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoFinalAutorizado'])
		
		# es-GT: Obtiene y Guarda el Rango Inicial Autorizado
		# en-US: Obtain and Save the Initial Authorized Range
		tabFacturaElectronica.rango_inicial_autorizado = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoInicialAutorizado'])
		
		# es-GT: Obtiene y Guarda el Regimen
		# en-US: Obtain and Save the Regime
		tabFacturaElectronica.regimen = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['regimen'])
		
		# es-GT: Obtiene y Guarda el tiempo en que se recibieron los datos de INFILE
		# en-US: Obtain and Save the time INFILE data was received
		tabFacturaElectronica.recibido = datetime.now()
		
		# es-GT: Obtiene y Guarda el tiempo en que se enviaron los datos a INFILE
		# en-US: Obtain and Save the time the data was sent to INFILE
		tabFacturaElectronica.enviado = tiempo_envio

		# Guarda el Link para obtener el PDF de la factura electronica
		#tabFacturaElectronica.link_pdf_factura_electronica = ("https://www.ingface.net/Ingfacereport/dtefactura.jsp?cae=" + cae_dato)
		
		# es-GT: Guarda todos los datos en la tabla llamada 'FACTURAS ELECTRONICAS' de la base de datos de ERPNEXT
		# en-US: Saves all the data in the table called 'ELECTRONIC INVOICES' of the ERPNEXT database
		tabFacturaElectronica.save()

		return cae_dato
		#frappe.msgprint(_("Factura Electronica Generada!"))
	except:
		frappe.msgprint(_("Error: No se guardo correctamente la Factura Electronica"))
