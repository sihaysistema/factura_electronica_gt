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

# es-GT: Guarda los datos recibidos de infile en la Tabla 'Facturas Electronicas'.
# en-US: Saves the data received from infile in the 'Electronic Invoices' Table.
# es-GT: Cada factura electronica que se genere exitosamente, deja este registro como constancia.
# en-US: Saves the data received from infile in the 'Electronic Invoices' Table.
# en-US: For every succesfully generated electronic invoice, a record is added to keep as confirmation.
def guardar_factura_electronica(datos_recibidos, serie_fact, tiempo_envio):
    	'''Guarda los datos recibidos de infile en la tabla Envios Facturas Electronicas de la base de datos ERPNext'''
	try:
		# es-GT: documento: con la libreria xmltodict, se convierte de XML a Diccionario, para acceder a los datos atraves de sus llaves.
        # es-GT: Se asigna a la variable 'documento'

		# en-US: documento: with the xmltodict library, it is converted from XML to Dictionary, to access the data through the dictionary keys
        # en-US: All this is assigned to the 'document' variable.
		documento = xmltodict.parse(datos_recibidos)

		# es-GT: Crea un nuevo record de Envios Facturas Electronica en la base de datos.
		# en-US: Creates a new Electronic Invoice Sent record in the database
		tabFacturaElectronica = frappe.new_doc("Envios Facturas Electronicas") 

		# es-GT: Obtiene y Guarda la serie de factura.
		# en-US: Obtains and Saves the invoice series.
		tabFacturaElectronica.serie_factura_original = serie_fact

		# es-GT: Obtiene y Guarda el CAE (Codigo de Autorización Electronico)
		# en-US: Obtains and Saves the CAE or literally translated: "Code of Electronic Authorization"
		tabFacturaElectronica.cae = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['cae'])
		cae_dato = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['cae'])

		# es-GT: Obtiene y Guarda el Numero de Documento que quedo registrada ante el Generador de Factura Electronica y la SAT
		# en-US: Obtains and Saves the Document Number that was registered with the Electronic Invoice Generator and SAT
		tabFacturaElectronica.numero_documento = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDocumento'])
		
		# es-GT: Obtiene y Guarda el Estado según GFACE (GFACE = Generador de Factura Electronica)
		# en-US: Obtains and Saves the current State of the document as per GFACE (Electronic Invoice Generator)
		tabFacturaElectronica.estado = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['estado'])
		
		# es-GT: Obtiene y Guarda las Anotaciones segun GFACE
		# en-US: Obtains and Saves the Annotations as per GFACE
		tabFacturaElectronica.anotaciones = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['anotaciones'])

		# es-GT: Obtiene y Guarda la Descripcion: En este campo estan todas las descripciones de errores y mensaje de generacion correcta
		# en-US: Obtains and Saves the Description: This field contains all the descriptions of errors and correct generation messages
		tabFacturaElectronica.descripcion = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])

		# es-GT: Obtiene y Guarda la Validez del documento
		# en-US: Obtains and Saves the Validity state of the document
		tabFacturaElectronica.valido = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['valido'])
		
		# es-GT: Obtiene y Guarda el Numero DTE
		# en-US: Obtains and Saves the DTE Number
		tabFacturaElectronica.numero_dte = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDte'])
		
		# es-GT: Obtiene y Guarda el Rango Final Autorizado
		# en-US: Obtains and Saves the Authorized Final Range
		tabFacturaElectronica.rango_final_autorizado = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoFinalAutorizado'])
		
		# es-GT: Obtiene y Guarda el Rango Inicial Autorizado
		# en-US: Obtains and Saves the Initial Authorized Range
		tabFacturaElectronica.rango_inicial_autorizado = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoInicialAutorizado'])
		
		# es-GT: Obtiene y Guarda el Regimen de impuestos
		# en-US: Obtains and Saves the Legal Tax Structure, aka 'Regimen'
		tabFacturaElectronica.regimen = str(documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['regimen'])
		
		# es-GT: Obtiene y Guarda el tiempo en que se recibieron los datos de INFILE
		# en-US: Obtains and Saves the timestamp of data reception from INFILE
		tabFacturaElectronica.recibido = datetime.now()
		
		# es-GT: Obtiene y Guarda el tiempo en que se enviaron los datos a INFILE
        # es-GT: Estos datos de tiempo se obtienen para poder monitorear el tiempo de transacción
		# en-US: Obtains and Saves the timestamp the data was sent to INFILE
        # en-US: These timestamps are obtained to keep track of transaction time
		tabFacturaElectronica.enviado = tiempo_envio
		
		# es-GT: Guarda todos los datos en la tabla llamada 'FACTURAS ELECTRONICAS' de la base de datos de ERPNext
		# en-US: Saves all the data in the table called 'ELECTRONIC INVOICES' of the ERPNext database
		tabFacturaElectronica.save()
		# es-GT: Al terminar de guardar el registro en la base de datos, retorna el CAE
		# en-US: When done saving the records to the database, it returns de CAE
		return cae_dato
		#frappe.msgprint(_("Factura Electronica Generada!"))
	except:
		# es-GT: Si algo falla, muestra el error en el navegador.
        # es-GT: Este mensaje solo indica que no se guardo la confirmacion de la factura electronica.
		# en-US: If something fails, the exception shows this message in the browser
        # en-US: This message simply states that the Electronic Invoice Confirmation was not saved.
		frappe.msgprint(_("Error: No se guardo correctamente la Factura Electronica"))
		# es-GT: FIXME  Que accion se le sugiere tomar al usuario ahora?
        # es-GT: FIXME  Sugerir por lo menos un par de opciones: Verificar configuracion local e intentar de nuevo, o llamar a INFILE.
		# en-US: FIXME What course of action may we suggest to the user?
        # en-US: FIXME Suggest a couple of options: verify local configuration and try Again or call INFILE?
