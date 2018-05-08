#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import requests
import xmltodict

from request_xml import construir_xml
from datetime import datetime, date
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

    # es-GT: Verifica la existencia de facturas generadas con la misma serie,
    # esto para evitar duplicadas. En caso no se encuentre, se procede a la 
    # generacion del documento.
    # en-US: Verify the existence of invoices generated with the same series,
    # this to avoid duplicates. If it is not found, the document is generated.
    if frappe.db.exists('Envios Facturas Electronicas', {'serie_factura_original': dato_factura}):
        factura_electronica = frappe.db.get_values('Envios Facturas Electronicas',
                                                   filters={'serie_factura_original': dato_factura},
                                                   fieldname=['serie_factura_original', 'cae'],
                                                   as_dict=1)

        frappe.msgprint(_('''
        <b>AVISO:</b> La Factura ya fue generada Anteriormente <b>{}</b>
        '''.format(str(factura_electronica[0]['serie_factura_original']))))

        cae_factura = str(factura_electronica[0]['cae'])

        # es-GT: retorna el cae de la factura electronica, que es obtenida por js del lado del cliente,
        #        para colocarla en 'Sales Invoice'.
        # en-US: returns the fall of the electronic invoice, which is obtained by js from the client's
        #        side, to place it in 'Sales Invoice'.
        return cae_factura
    else:
        # es-GT: Obtiene los datos necesarios de la base de datos de ERPNEXT, si ocurre un error, retornara
        #        un mensaje de error.
        # en-US: Obtain the necessary data from the ERPNEXT database, if an error occurs, it will return an
        #        error message.
        try:
            sales_invoice = frappe.db.get_values('Sales Invoice',
                                                 filters={'name': dato_factura},
                                                 fieldname=['name', 'idx', 'territory',
                                                            'grand_total', 'customer_name', 'company',
                                                            'company_address', 'naming_series', 'creation',
                                                            'status', 'discount_amount', 'docstatus',
                                                            'modified', 'conversion_rate',
                                                            'total_taxes_and_charges', 'net_total',
                                                            'shipping_address_name', 'customer_address',
                                                            'total', 'facelec_total_iva', 'currency'],
                                                 as_dict=1)

            sales_invoice_item = frappe.db.get_values('Sales Invoice Item',
                                                      filters={'parent': dato_factura},
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

            direccion_cliente = str(sales_invoice[0]['customer_address'])
            nombre_serie = str(sales_invoice[0]['naming_series'])
            dir_compania = str(sales_invoice[0]['company_address'])

            datos_cliente = frappe.db.get_values('Address', filters={'name': direccion_cliente},
                                                 fieldname=['email_id', 'country', 'city',
                                                            'address_line1', 'state',
                                                            'phone', 'address_title', 'name'], as_dict=1)

            direccion_compania = frappe.db.get_values('Address', filters={'name': dir_compania},
                                                      fieldname=['email_id', 'country', 'city',
                                                                 'address_line1', 'state',
                                                                 'phone', 'address_title',
                                                                 'county'], as_dict=1)

            datos_compania = frappe.db.get_values('Company', filters={'name': (sales_invoice[0]['company'])},
                                                  fieldname=['company_name', 'default_currency', 'country',
                                                             'nit_face_company'], as_dict=1)

            nit_cliente = frappe.db.get_values('Customer', filters={'name': dato_cliente},
                                               fieldname='nit_face_customer')

            datos_configuracion = frappe.db.get_values('Configuracion Factura Electronica',
                                                       filters={'name': 'CONFIG-FAC00001'},
                                                       fieldname=['descripcion_otro_impuesto', 'importe_exento',
                                                                  'id_dispositivo', 'validador', 'clave', 'codigo_establecimiento',
                                                                  'importe_otros_impuestos', 'regimen_2989', 'usuario', 'regimen_isr',
                                                                  'nit_gface', 'importe_total_exento', 'url_listener'], as_dict=1)

        except:
            frappe.msgprint(_('Error: Problemas con la Base de Datos!'))
        # es-GT: Si la obtencion de los datos de la base de datos es exitosa, se procede a la generacion del documento solicitado.
        #        de lo contrario solo mostrara el error de 'Problemas con la base de datos'
        # en-US: If the obtaining of the data of the database is successful, it proceeds to the generation of the requested document.
        #        Otherwise, it will only show the error of 'Problems with the database'
        else:
            # es-GT: Verifica que existan las series configuradas, para generar documentos: FACE, CFACE, NCE, NDE
            #        En caso no existan una serie valida configurada no procede a generar el documento solicitado.
            # en-US: Verify that the configured series exist, to generate documents: FACE, CFACE, NCE, NDE
            #        In case there is not a valid configured series, it does not proceed to generate the requested document.
            if frappe.db.exists('Configuracion Series', {'parent': 'CONFIG-FAC00001', 'serie': nombre_serie}):
                series_configuradas = frappe.db.get_values('Configuracion Series',
                                                           filters={'parent': 'CONFIG-FAC00001', 'serie': nombre_serie},
                                                           fieldname=['fecha_resolucion', 'estado_documento',
                                                                      'tipo_documento', 'serie', 'secuencia_infile',
                                                                      'numero_resolucion', 'codigo_sat'], as_dict=1)

                # es-GT: Llama al metodo 'contruir_xml' del script 'request_xml.py' para generar la peticion en XML.
                # en-US: Call the 'contruir_xml' method of the 'request_xml.py' script to generate the request in XML.
                construir_xml(sales_invoice, direccion_cliente, datos_cliente, sales_invoice_item,
                              datos_compania, nit_cliente, datos_configuracion, series_configuradas,
                              dato_factura, direccion_compania)

                # es-GT: Si ocurre un error en la comunicacion con el servidor de INFILE, retornara el mensaje de advertencia.
                #        En caso no exista error en comunicacion, procede con la obtencion de los datos, del documento solicitado.
                # en-US: If an error occurs in the communication with the INFILE server, the warning message will return.
                #        In case there is no error in communication, proceed with the obtaining of the data, of the requested document.
                try:
                    # Si existe problemas al abrir archivo XML, mostrara un error.
                    envio_datos = open('envio_request.xml', 'r').read()
                except:
                    frappe.msgprint(_('Error al abrir los datos XML. Comuniquese al No.'))
                else:
                    try:
                        # Si existe un error en la captura de tiempo del momento de envio mostrara un error
                        tiempo_enviado = datetime.now()
                    except:
                        frappe.msgprint(_('Error: No se puede capturar el momento de envio. Comuniquese al No.'))
                    else:
                        try:
                            # Si existe un problema con la comunicacion a INFILE o se sobrepasa el tiempo de espera
                            # Mostrara un error
                            # 2018-01-23 Se valido claramente que funciona el envío al servidor de INFILE
                            # URL de listener de INFILE FUNCIONA OK!!!
                            url = str(datos_configuracion[0]['url_listener'])
                            # CABECERAS: Indican el tipo de datos FUNCIONA OK!!!
                            headers = {"content-type": "text/xml"}
                            # FUNCIONA OK!!!
                            response = requests.post(url, data=envio_datos, headers=headers, timeout=15)
                            respuesta = response.content
                        except:
                            frappe.msgprint(_('Error en la Comunicacion al servidor de INFILE. Verifique al PBX: +502 2208-2208'))
                        else:
                            try:
                                # Si no se recibe ningun dato del servidor de INFILE mostrara el error
                                respuesta = response.content
                            except:
                                frappe.msgprint(_('Error en la comunicacion no se recibieron datos de INFILE'))
                            else:
                                documento_descripcion = xmltodict.parse(respuesta)

                                descripciones = (documento_descripcion['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])
                                # es-GT: en la variable 'errores_diccionario' se almacena un diccionario retornado
                                #        por el metodo errores del script valida_errores.py con los errores encontrados,
                                #        en caso existan errores los muestra. en caso no existan errores, se procede a
                                #        guardar en la base de datos, en la tabla 'Envios Facturas Electronicas'.
                                # en-US: In the variable 'errors_dictionary' a dictionary returned by the error method of
                                #        the valida_errors.py script is stored with the errors found, if there are errors,
                                #        it shows them. In case there are no errors, we proceed to save in the database,
                                #        in the 'Shipping Electronic Invoices' table.
                                errores_diccionario = errores(descripciones)
                                if (len(errores_diccionario) > 0):
                                    try:
                                        if (((errores_diccionario['Mensaje']).lower()) == 'dte generado con exito'):
                                            datoCAEF = guardar(respuesta, dato_factura, tiempo_enviado)

                                            # frappe.msgprint(_('FACTURA GENERADA CON EXITO'))

                                            with open('respuesta.xml', 'w') as recibidoxml:
                                                recibidoxml.write(respuesta)
                                                recibidoxml.close()

                                            return datoCAEF
                                    except:
                                        frappe.msgprint(_('''
                                        AVISOS <span class="label label-default" style="font-size: 16px">{}</span>
                                        '''.format(str(len(errores_diccionario))) + ' VERIFIQUE SU MANUAL'))
                                        for llave in errores_diccionario:
                                            frappe.msgprint(_('''
                                            <span class="label label-warning" style="font-size: 14px">{}</span>
                                            '''.format(str(llave)) + ' = ' + str(errores_diccionario[llave])))

                                        frappe.msgprint(_('NO GENERADA'))
            else:
                frappe.msgprint(_('No existen series configuradas'))

@frappe.whitelist()
def obtenerConfiguracionManualAutomatica():
    '''Verifica la configuracion guardada ya sea Automatica o Manual, aplica para la generacion de 
       facturas o la forma en que se guarda'''
    try:
        configuracion_fac = frappe.db.get_values('Configuracion Factura Electronica', filters={'name': 'CONFIG-FAC00001'},
                                                 fieldname=['generacion_factura'], as_dict=1)
    except:
        frappe.msgprint(_('Configuracion no encontrada'))
    else:
        if ((configuracion_fac[0]['generacion_factura']) == 'MANUAL'):
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
    # try:
    # ile_url = unquote(file_url)
    #    tabArchivos = frappe.new_doc("File")
    #    tabArchivos.file_url = file_url
    #    tabArchivos.file_name = 'prueba'
    #    tabArchivos.attached_to_doctype = 'Sales Invoice'
    #    tabArchivos.attached_to_name = dn
    #    tabArchivos.folder = 'Home/Facturas Electronicas'
    #    tabArchivos.is_private = 1
    #    tabArchivos.ignore_permissions = True
    #    tabArchivos.save()
    # except:
    #    frappe.msgprint(_('Archivo no guardado'))
    # else:
    #    frappe.msgprint(_('Guardado'))

@frappe.whitelist()
def get_data_tax_account(name_account_tax_gt):
    '''Funcion para obtener los datos de impuestos dependiendo el tipo de cuenta recibido'''
    if frappe.db.exists('Account', {'name': name_account_tax_gt}):

        datos_cuenta = frappe.db.get_values('Account', filters={'name': name_account_tax_gt},
                                            fieldname=['tax_rate', 'name'], as_dict=1)

        return str(datos_cuenta[0]['tax_rate'])
    else:
        frappe.msgprint(_('No existe cuenta relacionada con el producto'))
