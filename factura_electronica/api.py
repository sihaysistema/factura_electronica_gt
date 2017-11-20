#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import requests
import xmltodict

from request_xml import construir_xml
from datetime import datetime, date, time
from guardar_factura import guardar_factura_electronica as guardar
from valida_errores import encuentra_errores as errores

import sys
reload(sys)  
sys.setdefaultencoding('utf-8')

@frappe.whitelist()
def generar_factura_electronica(serie_factura, nombre_cliente):
    """Obtencion de datos requeridos y construccion de request"""
    dato_factura = serie_factura
    dato_cliente = nombre_cliente
 
    # Verifica en la tabla 'Envios Facturas Electronicas' si hay una factura electronica generada con la misma serie.
    # esto para evitar duplicadas
    if frappe.db.exists('Envios Facturas Electronicas', {'serie_factura_original': dato_factura}): 

        factura_electronica = frappe.db.get_values('Envios Facturas Electronicas', filters = {'serie_factura_original': dato_factura},
        fieldname = ['serie_factura_original', 'cae'], as_dict = 1)
        
        frappe.msgprint(_('<b>AVISO:</b> La Factura ya fue generada Anteriormente <b>{}</b>'.format(str(factura_electronica[0]['serie_factura_original']))))

        cae_factura = str(factura_electronica[0]['cae'])

        # retorna el cae de la factura electronica, que es obtenida por js del lado del cliente, para colocarla en el campo 
        return cae_factura

    else:
        # Obtiene los datos necesarios de la base de datos de ERPNEXT, si ocurre un error, retornara un mensaje con el mensaje de error.
        try:
            sales_invoice = frappe.db.get_values('Sales Invoice', filters = {'name': dato_factura},
            fieldname = ['name', 'idx', 'territory','grand_total', 'customer_name', 'company',
            'naming_series', 'creation', 'status', 'discount_amount', 'docstatus', 'modified', 'conversion_rate',
            'total_taxes_and_charges', 'net_total', 'shipping_address_name', 'customer_address'], as_dict = 1)

            direccion_cliente = str(sales_invoice[0]['customer_address'])
            nombre_serie = str(sales_invoice[0]['naming_series'])

            datos_cliente = frappe.db.get_values('Address', filters = {'name': direccion_cliente},
            fieldname = ['email_id', 'country', 'city', 'address_line1', 'state', 'phone', 'address_title', 'name'], as_dict = 1)

            sales_invoice_item = frappe.db.get_values('Sales Invoice Item', filters = {'parent': dato_factura}, 
            fieldname = ['item_name', 'qty', 'item_code', 'description', 'net_amount', 'base_net_amount', 
            'discount_percentage', 'net_rate', 'stock_uom', 'serial_no', 'item_group', 'rate', 'amount'], as_dict = 1)			

            datos_compania = frappe.db.get_values('Company', filters = {'name': str(sales_invoice[0]['company'])},
            fieldname = ['company_name', 'default_currency', 'country', 'nit_face_company'], as_dict = 1)

            nit_cliente = frappe.db.get_values('Customer', filters = {'name': dato_cliente},
            fieldname = 'nit_face_customer')

            datos_configuracion = frappe.db.get_values('Configuracion Factura Electronica', filters = {'name': 'CONFIG-FAC00001'},
            fieldname = ['descripcion_otro_impuesto', 'importe_exento', 'id_dispositivo', 'validador', 'clave',
            'codigo_establecimiento',  'importe_otros_impuestos', 'regimen_2989', 'usuario', 'regimen_isr', 'nit_gface', 'importe_total_exento']
            , as_dict = 1)
            
        except:
            frappe.msgprint(_('Error: Problemas con la Base de Datos!'))

        # Verifica que existan las series configuradas, para generar documentos: FACE, CFACE, NCE, NDE
        # En caso no existan una serie valida configurada no procede a generar el documento solicitado.
        if frappe.db.exists('Configuracion Series', {'parent': 'CONFIG-FAC00001', 'serie': nombre_serie}):
            
            series_configuradas = frappe.db.get_values('Configuracion Series', filters = {'parent': 'CONFIG-FAC00001', 'serie': nombre_serie},
            fieldname = ['fecha_resolucion', 'estado_documento', 'tipo_documento', 'serie', 'secuencia_infile',	'numero_resolucion',
            'codigo_sat'], as_dict = 1)

            # Llama al metodo 'contruir_xml' del script 'request_xml.py' para generar la peticion en XML.
            construir_xml(sales_invoice, direccion_cliente, datos_cliente, sales_invoice_item, datos_compania, nit_cliente, datos_configuracion, series_configuradas, dato_factura)

            # Si ocurre un error en la comunicacion con el servidor de INFILE, retornara el mensaje de conexion a internet.
            # En caso no exista error en comunicacion, procede con la obtencion de los datos, del documento solicitado.
            try:
                envio_datos = open('envio_request.xml', 'r').read()#.splitlines()

                url="https://www.ingface.net/listener/ingface?wsdl" #URL de listener de INFILE
                headers = {'content-type': 'text/xml'} #CABECERAS: Indican el tipo de datos

                tiempo_enviado = datetime.now()
                response = requests.post(url, data=envio_datos, headers=headers, timeout=5)
                respuesta = response.content
            except:
                frappe.msgprint(_('Error en la Comunicacion, Verifique su conexion a Internet o intente mas tarde!'))
            else:
                documento_descripcion = xmltodict.parse(respuesta)

                descripciones = (documento_descripcion['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])
                
                # en la variable 'errores_diccionario' se almacena un diccionario retornado por el metodo errores del script
                # valida_errores.py con los errores encontrados, en caso existe errores los muestra.
                # en caso no existan errores, se procede a guardar en la base de datos, en la tabla 'Envios Facturas Electronicas'.
                errores_diccionario = errores(descripciones)
                
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
        else:
            frappe.msgprint(_('No existen series configuradas'))
            

@frappe.whitelist()
def save_url_pdf():
    '''Verifica la configuracion para guardar los pdf generados'''
    try:
        configuracion_fac = frappe.db.get_values('Configuracion Factura Electronica', filters = {'name': 'CONFIG-FAC00001'},
        fieldname = ['guardar_pdf'] , as_dict = 1) 
    except:
        frappe.msgprint(_('Configuracion no encontrada'))
    else:
        if ((configuracion_fac[0]['guardar_pdf']) == 'MANUAL'):
            return 'Manual'
        else:
            return 'Automatico'

@frappe.whitelist()
def save_pdf_server(file_url, filename, dt, dn, folder, is_private):
    '''Funcion para guardar automaticamente los pdf en la base de datos de forma privada'''
    pass
    # if not (file_url.startswith("http://") or file_url.startswith("https://")):
	# 	frappe.msgprint("URL must start with 'http://' or 'https://'")
	# 	return None, None
    #try:
	#file_url = unquote(file_url)
    #    tabArchivos = frappe.new_doc("File") 
    #    tabArchivos.file_url = file_url
    #    tabArchivos.file_name = 'prueba'
    #    tabArchivos.attached_to_doctype = 'Sales Invoice'
    #    tabArchivos.attached_to_name = dn
    #    tabArchivos.folder = 'Home/Facturas Electronicas'
    #    tabArchivos.is_private = 1
    #    tabArchivos.ignore_permissions = True
    #    tabArchivos.save()
    #except:
    #    frappe.msgprint(_('Archivo no guardado'))
    #else:
    #    frappe.msgprint(_('Guardado'))