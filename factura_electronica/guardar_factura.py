#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import xmltodict
from datetime import datetime, date, time
import os
# Resuelve el problema de codificacion
import sys
reload(sys)  
#sys.setdefaultencoding('Cp1252')
sys.setdefaultencoding('utf-8')

#Guardar los datos recibidos de infile en la Tabla 'Facturas Electronicas'
def guardar_factura_electronica(datos_recibidos, serie_fact, tiempo_envio):
    	'''Guarda los datos recibidos de infile en la tabla Envios Facturas Electronicas de la base de datos ERPNext'''
	try:
		#documento: con la libreria xmltodict, se convierte de XML a Diccionario, para acceder a los datos
		#atraves de sus llaves
		documento = xmltodict.parse(datos_recibidos)

		# Crea un nuevo documento de Facturas Electronica
		tabFacturaElectronica = frappe.new_doc("Envios Facturas Electronicas") 

		# Obtiene y Guarda la serie de factura
		tabFacturaElectronica.serie_factura_original = serie_fact

		 	# Obtiene y Guarda el CAE
		tabFacturaElectronica.cae = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['cae'])
		
		# Obtiene y Guarda el Numero de Documento
		tabFacturaElectronica.numero_documento = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDocumento'])
		
		 	# Obtiene y Guarda el Estado
		tabFacturaElectronica.estado = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['estado'])
		
		# Obtiene y Guarda las Anotaciones
		tabFacturaElectronica.anotaciones = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['anotaciones'])

		# Obtiene y Guarda la Descripcion: En este campo estan todas las descripciones de errores y mensaje de generacion correcta
		# Se mantiene comentada ya que puede contener cadenas de tamaño que sobrepasan los campos de la DB
		#descripciones = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])

		# Obtiene y Guarda la Validez
		tabFacturaElectronica.valido = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['valido'])
		
			# Obtiene y Guarda el Numero DTE
		tabFacturaElectronica.numero_dte = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDte'])
		
			# Obtiene y Guarda el Rango Final Autorizado
		tabFacturaElectronica.rango_final_autorizado = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoFinalAutorizado'])
		
			# Obtiene y Guarda el Rango Inicial Autorizado
		tabFacturaElectronica.rango_inicio_autorizado = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoInicialAutorizado'])
		
			# Obtiene y Guarda el Regimen
		tabFacturaElectronica.regimen = (documento['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['regimen'])
		
		# Obtiene y Guarda el tiempo en que se recibieron los datos de INFILE
		tabFacturaElectronica.recibido = datetime.now()
		
		# Obtiene y Guarda el tiempo en que se enviaron los datos a INFILE
		tabFacturaElectronica.enviado = tiempo_envio
		
		# Guarda todos los datos en la tabla llamada 'FACTURAS ELECTRONICAS' de la base de datos de ERPNEXT
		tabFacturaElectronica.save()

		#frappe.msgprint(_("Factura Electronica Generada!"))
	except:
		frappe.msgprint(_("Error: No se guardo correctamente la Factura Electronica"))