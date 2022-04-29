# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
from datetime import date, datetime

import frappe
import requests
import xmltodict
from frappe import _
from frappe.utils import get_site_name

from factura_electronica.fel_api import api_interface  # Aplica para facturas de VENTA POS
from factura_electronica.utils.facelec_db import actualizarTablas as actualizartb
from factura_electronica.utils.facelec_db import guardar_factura_electronica as guardar
from factura_electronica.utils.facelec_generator import construir_xml
from factura_electronica.utils.fel_generator import FacturaElectronicaFEL
from factura_electronica.utils.utilities_facelec import encuentra_errores as errores
from factura_electronica.utils.utilities_facelec import normalizar_texto, validar_configuracion


@frappe.whitelist()
def guardar_pdf_servidor(nombre_archivo, cae_de_factura_electronica):
    '''Descarga factura en servidor y registra en base de datos

    Parametros:
    ----------
    * nombre_archivo (str) : Nombre que describe el archivo
    * cae_de_factura_electronica (str) : CAE
    '''
    import os
    modalidad_configurada = validar_configuracion()
    nombre_de_sitio = get_site_name(frappe.local.site)
    ruta_archivo = '{0}/private/files/factura-electronica/'.format(nombre_de_sitio)

    # Verifica que exista un configuracion valida para factura electronica
    if modalidad_configurada[0] == 1:
        configuracion_factura = frappe.db.get_values('Configuracion Factura Electronica',
                                                    filters={'name': modalidad_configurada[1]},
                                                    fieldname=['url_listener', 'descargar_pdf_factura_electronica',
                                                               'url_descarga_pdf'], as_dict=1)

        url_archivo = configuracion_factura[0]['url_descarga_pdf'] + cae_de_factura_electronica

        # Verifica que la funcionalidad para descargar pdf automaticamente, este activa
        if configuracion_factura[0]['descargar_pdf_factura_electronica'] == 'ACTIVAR':

            # Si no existe registro en la base de datos procede a descargar y guardar
            if not frappe.db.exists('File', {'file_name': (nombre_archivo + '.pdf')}):

                # Verifica existencia ruta de archivo, si no existe la crea, si ya existe descarga el pdf en esa ruta
                if os.path.exists(ruta_archivo):
                    descarga_archivo = os.system('curl -s -o {0}{1}.pdf {2}'.format(ruta_archivo, nombre_archivo, url_archivo))
                else:
                    frappe.create_folder(ruta_archivo)
                    descarga_archivo = os.system('curl -s -o {0}{1}.pdf {2}'.format(ruta_archivo, nombre_archivo, url_archivo))

                # Cuando la descarga es exitosa retorna 0, por lo que si es existosa procede
                if descarga_archivo == 0:
                    # Obtiene el tamaño del archivo en bytes
                    bytes_archivo = os.path.getsize("{0}/private/files/factura-electronica/{1}.pdf".format(nombre_de_sitio, nombre_archivo))
                    # Guarda los datos en la base de datos
                    try:
                        nuevo_archivo = frappe.new_doc("File")
                        nuevo_archivo.docstatus = 0
                        nuevo_archivo.file_name = str(nombre_archivo) + '.pdf'
                        nuevo_archivo.file_url = '/private/files/factura-electronica/{0}.pdf'.format(nombre_archivo)
                        nuevo_archivo.attached_to_name = nombre_archivo
                        nuevo_archivo.file_size = bytes_archivo
                        nuevo_archivo.attached_to_doctype = 'Sales Invoice'
                        nuevo_archivo.is_home_folder = 0
                        nuevo_archivo.if_folder = 0
                        nuevo_archivo.folder = 'Home/attachments'
                        nuevo_archivo.is_private = 1
                        nuevo_archivo.old_parent = 'Home/attachments'
                        nuevo_archivo.save()
                    except:
                        frappe.msgprint(_('''Error no se pudo guardar PDF de la factura electronica en la
                                            base de datos. Intente de nuevo.'''))
                    else:
                        return 'ok'

                else:
                    frappe.msgprint(_('''No se pudo obtener el archivo pdf de la factura electronica.
                                        Por favor intente de nuevo.'''))
            # else:
            #     frappe.msgprint(_('EL PDF YA EXISTE ;)'))


@frappe.whitelist()
def obtener_numero_resolucion(nombre_serie):
    '''Retorna el numero de resolucion en base la serie de Configuracion Electronica
     NOTE: APLICA SOLO PARA FOGLIASANA

    Parametros:
    ----------
    * nombre_serie (str) : Nombre de la serie para filtrar
    '''
    if frappe.db.exists('Configuracion Series', {'serie': nombre_serie, 'docstatus': 1}):
        numero_resolucion = frappe.db.get_values('Configuracion Series', filters={'serie': nombre_serie, 'docstatus': 1},
                                                 fieldname=['numero_resolucion'], as_dict=1)

        return str(numero_resolucion[0]['numero_resolucion'])


@frappe.whitelist()
def generar_tabla_html(tabla, currency="GTQ"):
    """Funcion para generar tabla con html + jinja, para mostrar impuestos
    desglosados de cada item

    Args:
        tabla (json): Datos tabla hija items

    Returns:
        html: Formato HTML reconstruido con los parametros
    """

    headers = [_("Item"), _("Unit Tax"), _("Qty"), _("Total Tax"), _("+"),
               _("Base Value"), _("+"), _("IVA"), _("="), _("Total")]
    mi_tabla = json.loads(tabla)
    longi = (len(mi_tabla))
    if longi > 20:
        return

    # # Retorna la tabla HTML lista para renderizar
    return frappe.render_template(
        "templates/sales_invoice_tax.html", dict(
            headers=headers,
            items_tax=mi_tabla,
            index=longi,
            currency=currency
        )
    )


@frappe.whitelist()
def generar_tabla_html_factura_compra(tabla, currency="GTQ"):
    """Funcion para generar tabla con html + jinja, para mostrar impuestos
    desglosados de cada item en Purchase invoice

    Args:
        tabla (json): Datos tabla hija items

    Returns:
        html: Formato HTML reconstruido con los parametros
    """

    headers = [_("Item"), _("Unit Tax"), _("Qty"), _("Total Tax"), _("+"),
               _("Base Value"), _("+"), _("IVA"), _("="), _("Total")]

    mi_tabla = json.loads(tabla)
    longi = (len(mi_tabla))
    if longi > 20:
        return

    # with open("probando.json", "w") as file:
    #     file.write(json.dumps(mi_tabla, indent=2))

    # # Retorna la tabla HTML lista para renderizar
    return frappe.render_template(
        "templates/purchase_invoice_tax.html", dict(
            headers=headers,
            items_tax=mi_tabla,
            index=longi,
            currency=currency
        )
    )


# FUNCION ESPECIAL PARA API - FEL
def facelec_api(serie_factura, nombre_cliente, pre_se):
    '''Verifica que todos los datos esten correctos para realizar una
       peticion a INFILE y generar la factura electronica

       Parametros
       ----------
       * serie_factura (str) : Serie de la factura
       * nombre_cliente (str) : Nombre del cliente
       * pre_se (str) : Prefijo de la serie
    '''

    serie_original_factura = str(serie_factura)
    nombre_del_cliente = str(nombre_cliente)
    prefijo_serie = str(pre_se)

    # Verifica que exista una configuracion validada para Factura Electronicaa
    validar_config = validar_configuracion()

    # Si es igual a 1, hay una configuracion valida
    if validar_config[0] == 1:
        # Verifica si existe una factura con la misma serie, evita duplicadas
        if frappe.db.exists('Envios Facturas Electronicas', {'numero_dte': serie_original_factura}):
            factura_electronica = frappe.db.get_values('Envios Facturas Electronicas',
                                                    filters={'numero_dte': serie_original_factura},
                                                    fieldname=['serie_factura_original', 'cae', 'numero_dte'],
                                                    as_dict=1)
            # return True, '''
            # <b>AVISO:</b> La Factura ya fue generada Anteriormente <b>{}</b>
            # '''.format(str(factura_electronica[0]['numero_dte']))
            return {
                "status": "OK",
                "cantidad_errores": 0,
                "detalle_errores_facelec": [],
                "uuid": str(factura_electronica[0]['numero_dte']),
                "descripcion": "La factura electronica ya fue generada anteriormente"
            }

        elif frappe.db.exists('Envio FEL', {'serie_para_factura': serie_original_factura}):
            factura_electronica = frappe.db.get_values('Envio FEL',
                                                    filters={'serie_para_factura': serie_original_factura},
                                                    fieldname=['serie_para_factura'],
                                                    as_dict=1)
            return {
                "status": "OK",
                "cantidad_errores": 0,
                "detalle_errores_facelec": [],
                "uuid": "",
                "descripcion": "La Factura ya fue generada Anteriormente con serie: "+str(factura_electronica[0]['serie_para_factura'])
            }
            # return True, "La Factura ya fue generada Anteriormente,"+str(factura_electronica[0]['serie_para_factura'])

        else:  # Si no existe se creara
            nombre_config_validada = str(validar_config[1])
            # Verificacion regimen GFACE
            if validar_config[2] == 'GFACE':
                return {
                    "status": "ERROR",
                    "cantidad_errores": 1,
                    "detalle_errores_facelec": ["GFACE no habilitado para API"],
                    "uuid": ""
                }
                # VERIFICACION EXISTENCIA SERIES CONFIGURADAS, EN CONFIGURACION FACTURA ELECTRONICA
                # if frappe.db.exists('Configuracion Series', {'parent': nombre_config_validada, 'serie': prefijo_serie}):
                #     series_configuradas = frappe.db.get_values('Configuracion Series',
                #                                                 filters={'parent': nombre_config_validada, 'serie': prefijo_serie},
                #                                                 fieldname=['fecha_resolucion', 'estado_documento',
                #                                                             'tipo_documento', 'serie', 'secuencia_infile',
                #                                                             'numero_resolucion', 'codigo_sat'], as_dict=1)


                #     url_configurada = frappe.db.get_values('Configuracion Factura Electronica',
                #                                         filters={'name': nombre_config_validada},
                #                                         fieldname=['url_listener', 'descargar_pdf_factura_electronica',
                #                                                 'url_descarga_pdf'], as_dict=1)

                #     # Verificacion regimen GFACE
                #     # CONTRUCCION XML Y PETICION A WEBSERVICE
                #     try:
                #         xml_factura = construir_xml(serie_original_factura, nombre_del_cliente, prefijo_serie, series_configuradas, nombre_config_validada)
                #     except:
                #         return 'Error crear xml para factura electronica: {}'.format(frappe.get_traceback())
                #     else:
                #         url = str(url_configurada[0]['url_listener'])
                #         tiempo_enviado = datetime.now()
                #         respuesta_infile = peticion_factura_electronica(xml_factura, url)
                #         # Usar para debug
                #         # with open('reci.xml', 'w') as f:
                #         #     f.write(str(respuesta_infile))

                #     # VALIDACION RESPUESTA
                #     try:
                #         # xmltodic parsea la respuesta por parte de INFILE
                #         documento_descripcion = xmltodict.parse(respuesta_infile)
                #         # En la descripcion se encuentra el mensaje, si el documento electronico se realizo con exito
                #         descripciones = (documento_descripcion['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])
                #     except:
                #         return '''Error: INFILE no pudo recibir los datos: {0} \n {1}'''.format(str(respuesta_infile), frappe.get_traceback())
                #     else:
                #         # La funcion errores se encarga de verificar si existen errores o si la
                #         # generacion de factura electronica fue exitosa
                #         errores_diccionario = errores(descripciones)

                #         if (len(errores_diccionario) > 0):
                #             try:
                #                 # Si el mensaje indica que la factura electronica se genero con exito se procede
                #                 # a guardar la respuesta de INFILE en la DB
                #                 if ((str(errores_diccionario['Mensaje']).lower()) == 'dte generado con exito'):

                #                     cae_fac_electronica = guardar(respuesta_infile, serie_original_factura, tiempo_enviado)
                #                     # frappe.msgprint(_('FACTURA GENERADA CON EXITO'))
                #                     # el archivo rexpuest.xml se encuentra en la ruta, /home/frappe/frappe-bench/sites

                #                     # USAR PARA DEBUG
                #                     # with open('respuesta_infile.xml', 'w') as recibidoxml:
                #                     #     recibidoxml.write(str(respuesta_infile))
                #                     #     recibidoxml.close()

                #                     # es-GT:  Esta funcion es la nueva funcion para actualizar todas las tablas en las cuales puedan aparecer.
                #                     numero_dte_correcto = actualizartb(serie_original_factura)
                #                     # Funcion para descargar y guardar pdf factura electronica
                #                     descarga_pdf = guardar_pdf_servidor(numero_dte_correcto, cae_fac_electronica)

                #                     # Este dato sera capturado por Js actualizando la url
                #                     return numero_dte_correcto
                #             except:
                #                 for llave in errores_diccionario:
                #                     return '''
                #                     <span class="label label-warning" style="font-size: 14px">{}</span>
                #                     '''.format(str(llave)) + ' = ' + str(errores_diccionario[llave])

                #                 # frappe.msgprint(_('NO GENERADA: {}'.format(frappe.get_traceback())))


                # else:
                #     return '''La serie utilizada en esta factura no esta configurada para Facturas Electronicas.
                #                         Por favor configura la serie <b>{0}</b> en
                #                         <a href='#List/Configuracion Factura Electronica'><b>Configuracion Factura Electronica</b></a>
                #                         e intenta de nuevo.
                #                     '''.format(prefijo_serie)

            # Verificacion regimen FEL
            if validar_config[2] == 'FEL':
                if frappe.db.exists('Configuracion Series FEL', {'parent': nombre_config_validada, 'serie': prefijo_serie}):
                    series_configuradas_fel = frappe.db.get_values('Configuracion Series FEL',
                                                                    filters={'parent': nombre_config_validada, 'serie': prefijo_serie},
                                                                    fieldname=['tipo_documento'], as_dict=1)

                    url_configurada = frappe.db.get_values('Configuracion Factura Electronica',
                                                        filters={'name': nombre_config_validada},
                                                        fieldname=['url_listener', 'descargar_pdf_factura_electronica',
                                                                'url_descarga_pdf'], as_dict=1)
                    est = ''
                    try:
                        factura_electronica = FacturaElectronicaFEL(serie_original_factura, nombre_del_cliente, nombre_config_validada, series_configuradas_fel)
                        est = factura_electronica.generar_facelec()
                        if est['status'] != 'OK':
                            return {
                                "status": "ERROR",
                                "cantidad_errores": len(est['detalle_errores_facelec']),
                                "detalle_errores_facelec": est['detalle_errores_facelec'],
                                "uuid": ""
                            }
                        else:
                            return {
                                "status": "OK",
                                "cantidad_errores": 0,
                                "detalle_errores_facelec": [],
                                "uuid": est['uuid']
                            }
                    except:
                        # return False, 'No se pudo generar la factura electronica: '+(est)
                        return {
                            "status": "ERROR",
                            "cantidad_errores": 1,
                            "detalle_errores_facelec": [est],
                            "uuid": ""
                        }
                else:
                    # return False, '''La serie utilizada en esta factura no esta configurada para Facturas Electronicas.
                    #         Por favor configura la serie <b>{0}</b> en
                    #         <a href='#List/Configuracion Factura Electronica'><b>Configuracion Factura Electronica</b></a>
                    #         e intenta de nuevo.
                    #     '''.format(prefijo_serie)
                    return {
                        "status": "ERROR",
                        "cantidad_errores": 1,
                        "detalle_errores_facelec": ['''La serie utilizada en esta factura no esta configurada para Facturas Electronicas.
                            Por favor configura la serie <b>{0}</b> en
                            <a href='#List/Configuracion Factura Electronica'><b>Configuracion Factura Electronica</b></a>
                            e intenta de nuevo.
                        '''.format(prefijo_serie)],
                        "uuid": ""
                    }

    elif validar_config[0] == 2:
        return {
            "status": "ERROR",
            "cantidad_errores": 1,
            "detalle_errores_facelec": ['''Existe más de una configuración para factura electrónica.
                             Verifique que solo exista una validada en
                             <a href='#List/Configuracion Factura Electronica'><b>Configuracion Factura Electronica</b></a>'''],
            "uuid": ""
        }

    elif validar_config[0] == 3:
        return {
            "status": "ERROR",
            "cantidad_errores": 1,
            "detalle_errores_facelec": ['''No se encontró una configuración válida. Verifique que exista una configuración validada en
                             <a href='#List/Configuracion Factura Electronica'><b>Configuracion Factura Electronica</b></a>'''],
            "uuid": ""
        }


@frappe.whitelist()
def get_address(company):
    """Retorna la dirección de la compania para usarse como filtro en el reportes
    GT Purchase Ledger

    Args:
        company (str): Nombre de la compania

    Returns:
        str: Direccion linea 1
    """
    try:
        link_address = frappe.db.get_value('Dynamic Link', {'link_doctype': 'Company', 'parenttype': 'Address',
                                                            'link_name': str(company)}, 'parent')

        address = frappe.db.get_value('Address', {'name': link_address}, 'address_line1')

        return address

    except:
        return ''


@frappe.whitelist()
def download_excel_purchase_ledger():
    """
    Permite descargar el excel con nombre Libro compras GT
    """
    frappe.local.response.filename = "Libro Compras.xlsx"
    with open("Libro Compras.xlsx", "rb") as fileobj:
        filedata = fileobj.read()
    frappe.local.response.filecontent = filedata
    frappe.local.response.type = "download"


@frappe.whitelist()
def download_excel_sales_ledger():
    """
    Permite descargar el excel con nombre Libro compras GT
    """
    frappe.local.response.filename = "Libro Ventas.xlsx"
    with open("Libro Ventas.xlsx", "rb") as fileobj:
        filedata = fileobj.read()
    frappe.local.response.filecontent = filedata
    frappe.local.response.type = "download"


@frappe.whitelist()
def btn_activator(electronic_doc):
    """Define si se muestra/oculta el boton generador de docs electronicos en el SI/PI

    Args:
        electronic_doc (str): Sales Invoice/Purchase Invoice

    Returns:
        bool
    """
    try:
        status = validar_configuracion()
        if status[0] == 1:
            # Verifica si el doc electronico a generar esta activado en config facelec
            if frappe.db.exists('Configuracion Factura Electronica', {'name': status[1], electronic_doc: 1}):
                return True
            else:
                return False
    except:
        return False


@frappe.whitelist()
def calculations(obj_sales_invoice):
    """
    Aplicador de calculos universal, para quien consuma la funcion

    Args:
        obj_sales_invoice (Object): Objeto de la clase Sales Invoice

    Returns:
        Object: Objeto de la clase Sales Invoice modificado con calculos correspondientes
    """

    # TODO: WIP: ADAPTAR ESCENARIO IDP

    sales_invoice = obj_sales_invoice
    taxes = sales_invoice.taxes
    # Obtiene monto impuesto
    rate_iva = taxes[0].rate

    try:
        total_iva_factura = 0
        # Calculos
        for item in sales_invoice.items:
            # Aplica para impuestos, en caso sea diferente sera 0
            rate_per_uom = item.facelec_tax_rate_per_uom or 0
            this_row_tax_amount = (item.qty) * rate_per_uom
            this_row_taxable_amount = ((item.rate) * (item.qty)) - ((item.qty) * rate_per_uom)

            item.facelec_other_tax_amount = rate_per_uom * ((item.qty) * 1)
            item.facelec_amount_minus_excise_tax = ((item.qty * item.rate) - (item.qty * rate_per_uom))

            # calculos para combustible
            if (item.facelecis_fuel):
                item.facelec_gt_tax_net_fuel_amt = (item.facelec_amount_minus_excise_tax) / (1 + (rate_iva / 100))
                item.facelec_sales_tax_for_this_row = (item.facelec_gt_tax_net_fuel_amt) * (rate_iva / 100)

            # calculos para bienes
            if (item.facelec_is_good):
                item.facelec_gt_tax_net_goods_amt = (item.facelec_amount_minus_excise_tax) / (1 + (rate_iva / 100))
                item.facelec_sales_tax_for_this_row = (item.facelec_gt_tax_net_goods_amt) * (rate_iva / 100)

            # # calculos para servicios
            if (item.facelec_is_service):
                item.facelec_gt_tax_net_services_amt = (item.facelec_amount_minus_excise_tax) / (1 + (rate_iva / 100))
                item.facelec_sales_tax_for_this_row = (item.facelec_gt_tax_net_services_amt) * (rate_iva / 100)

        for item_iva in sales_invoice.items:
            total_iva_factura += item_iva.facelec_sales_tax_for_this_row

        sales_invoice.shs_total_iva_fac = total_iva_factura

    except:
        return False, f'Ocurrio un problema al aplicar los calculos, asegurese de tener correctamente configurados los items, mas detalles en: {frappe.get_traceback()} '

    else:
        return True, 'OK'


@frappe.whitelist()
def pos_calculations(doc, event):
    """
    Realiza calculos sobre Bienes, Servicios, Combustibles (No disponible) en el trigger Pagar
    de POS nativo de ERP

    Args:
        doc (obj): Object de la clase Sales Invoice/Sales Invoice Item
        event (str): Nombre del evento ejecutado
    """
    try:
        validar_config = validar_configuracion()
        sales_invoice = frappe.get_doc('Sales Invoice', {'name': doc.name})

        # Si es una factura generada desde POS y exista una configuracion facelc
        if sales_invoice.is_pos:
            taxes = sales_invoice.taxes
            rate_iva = taxes[0].rate

            rate_per_uom = 0
            this_row_tax_amount = 0
            facelec_other_tax_amount = 0
            this_row_taxable_amount = 0
            facelec_amount_minus_excise_tax = 0
            facelec_gt_tax_net_fuel_amt = 0
            facelec_gt_tax_net_goods_amt = 0
            facelec_gt_tax_net_services_amt = 0
            facelec_sales_tax_for_this_row = 0
            total_iva_fact = 0

            # Calculos
            for item in sales_invoice.items:
                # Aplica para impuestos, en caso sea diferente sera 0
                rate_per_uom = item.facelec_tax_rate_per_uom or 0
                this_row_tax_amount = (item.qty) * rate_per_uom
                this_row_taxable_amount = ((item.rate) * (item.qty)) - ((item.qty) * rate_per_uom)

                facelec_other_tax_amount = rate_per_uom * ((item.qty) * 1)
                facelec_amount_minus_excise_tax = ((item.qty * item.rate) - (item.qty * rate_per_uom))

                if item.discount_percentage != 0:
                    facelec_is_discount = 1

                elif item.discount_amount != 0:
                    facelec_is_discount = 1

                else:
                    facelec_is_discount = 0

                # calculos para combustible
                if (item.factelecis_fuel):
                    facelec_gt_tax_net_fuel_amt = (facelec_amount_minus_excise_tax) / (1 + (rate_iva / 100))
                    facelec_sales_tax_for_this_row = (facelec_gt_tax_net_fuel_amt) * (rate_iva / 100)
                    total_iva_fact += facelec_sales_tax_for_this_row

                # calculos para bienes
                if (item.facelec_is_good):
                    facelec_gt_tax_net_goods_amt = (facelec_amount_minus_excise_tax) / (1 + (rate_iva / 100))
                    facelec_sales_tax_for_this_row = (facelec_gt_tax_net_goods_amt) * (rate_iva / 100)
                    total_iva_fact += facelec_sales_tax_for_this_row

                # calculos para servicios
                if (item.facelec_is_service):
                    facelec_gt_tax_net_services_amt = (facelec_amount_minus_excise_tax) / (1 + (rate_iva / 100))
                    facelec_sales_tax_for_this_row = (facelec_gt_tax_net_services_amt) * (rate_iva / 100)
                    total_iva_fact += facelec_sales_tax_for_this_row

                frappe.db.set_value('Sales Invoice Item', {'parent': doc.name, 'item_code': item.item_code, 'qty': item.qty, 'rate': item.rate}, {
                    'facelec_other_tax_amount': facelec_other_tax_amount,
                    'facelec_amount_minus_excise_tax': facelec_amount_minus_excise_tax,
                    'facelec_gt_tax_net_fuel_amt': facelec_gt_tax_net_fuel_amt,
                    'facelec_sales_tax_for_this_row': facelec_sales_tax_for_this_row,
                    'facelec_gt_tax_net_goods_amt': facelec_gt_tax_net_goods_amt,
                    'facelec_gt_tax_net_services_amt': facelec_gt_tax_net_services_amt,
                    'facelec_is_discount': facelec_is_discount
                })

            frappe.db.set_value('Sales Invoice', doc.name, 'shs_total_iva_fac', total_iva_fact, update_modified=True)

            # Si los calculos se aplican correctamente se genera factura electronica
            validar_config = validar_configuracion()
            if validar_config[0] == 1:
                is_facelec_pos = frappe.db.get_value('Configuracion Factura Electronica', {'name': validar_config[1]}, 'factura_electronica_fel_pos')
                if is_facelec_pos == 1:
                    api_interface(doc.name, sales_invoice.naming_series)

    except:
        frappe.msgprint(f'Mas detalles en el siguiente log {frappe.get_traceback()}', title="Error ejecución calculos Factura Electronica", raise_exception=1)


@frappe.whitelist()
def get_special_tax(item_code='', company=''):
    fields = ['facelec_tax_rate_per_uom', 'facelec_tax_rate_per_uom_purchase_account',
              'facelec_tax_rate_per_uom_selling_account']
    taxes = frappe.db.get_value('Item Default', filters={'parent': item_code, 'company': company},
                                fieldname=fields, as_dict=1)

    return taxes or False
