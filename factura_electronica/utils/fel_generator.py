# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime
from factura_electronica.utils.utilities_facelec import normalizar_texto
import json, xmltodict
import base64
import requests
import datetime

class FacturaElectronicaFEL:
    def __init__(self, serie, cliente, conf_name, series_conf):
        self.d_general = {}
        self.d_emisor = {}
        self.d_receptor = {}
        self.d_frases = {}
        self.d_items = {}
        self.d_totales = {}
        self.d_firma = {}
        self.serie_factura = str(serie)  # Serie original de la factura
        self.nombre_config = str(conf_name)  # Nombre doc configuracion para factura electronica
        self.nombre_cliente = str(cliente)  # Nombre cliente en factura
        self.serie_facelec_fel = str(series_conf)  # Series para factura electronica

    def construir_peticion(self):
        '''Funcion principal encargada de construir XML peticion a partir de JSON y manejar la solicitud de facelec'''
        # Verifica que todas las partes que conforman la peticion sean correctas
        e_validador = self.validador_data()

        if e_validador == True:
            # Base de la paticion para luego ser convertida a xml y enviada a INFILE-SAT
            base_peticion = {
                "dte:GTDocumento": {
                    "@xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
                    "@xmlns:dte": "http://www.sat.gob.gt/dte/fel/0.1.0",
                    "@xmlns:n1": "http://www.altova.com/samplexml/other-namespace",
                    "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "@Version": "0.4",
                    "@xsi:schemaLocation": "http://www.sat.gob.gt/dte/fel/0.1.0",
                    "dte:SAT": {
                        "@ClaseDocumento": "dte",
                        "dte:DTE": {
                            "@ID": "DatosCertificados",
                            "dte:DatosEmision": {
                                "@ID": "DatosEmision",
                                "dte:DatosGenerales": self.d_general,
                                "dte:Emisor": self.d_emisor,
                                "dte:Receptor": self.d_receptor,
                                "dte:Frases": self.d_frases,
                                "dte:Items": self.d_items,
                                "dte:Totales": self.d_totales 
                            }
                        }
                    }
                }
            }

            try:
                # To XML
                xmlString = xmltodict.unparse(base_peticion, pretty=True)
                with open('mario.xml', 'w') as f:
                    f.write(xmlString)

                # To base64
                encodedBytes = base64.b64encode(xmlString.encode("utf-8"))
                encodedStr = str(encodedBytes, "utf-8")
                # with open('codificado.txt', 'w') as f:
                #         f.write(encodedStr)

                # Hace peticion para firmar xml encoded base64
                estado_firma = self.firmar_data(encodedStr)

                # Si la firma se hace exitosamente
                if estado_firma[0] == True:
                    with open('firmado.json', 'w') as f:
                        f.write(estado_firma[1])

                    estado_fel = self.solicitar_factura_electronica(json.loads(estado_firma[1]))
                    if estado_fel[0] == True:

                        uuid_fel = self.validador_respuestas(estado_fel[1])
                        if uuid_fel['status'] == 'OK':
                            with open('ok_fel.json', 'w') as f:
                                f.write(estado_fel[1])

                            return uuid_fel['numero_autorizacion']

                        # Funcion encargada de actualizar todos los registros enlazados a la factura original

                        return estado_fel
                    else:
                        return estado_fel
                else:
                    return 'No se logro firmar el documento: '+str(estado_firma)

            except:
                return 'Error: '+str(frappe.get_traceback())

        else:
            return e_validador

    def validador_data(self):
        '''Funcion encargada de validar la data que construye la peticion a INFILE,
           Si existe por lo menos un error retornara la descripcion'''

        # Validacion y generacion seccion datos generales
        estado_dg = self.datos_generales()
        if estado_dg != True:
            return estado_dg

        estado_e = self.emisor()
        if estado_e != True:
            return estado_e

        estado_r = self.receptor()
        if estado_r != True:
            return estado_r

        estado_f = self.frases()
        if estado_f != True:
            return estado_f

        estado_i = self.items()
        if estado_i != True:
            return estado_i

        estado_t = self.totales()
        if estado_t != True:
            return estado_t

        return True

    def validador_respuestas(self, msj_fel):
        '''Funcion encargada de verificar las respuestas de INFILE-SAT'''
        try:
            mensajes = json.loads(msj_fel)
            # Verifica que no existan errores
            if mensajes['resultado'] == True and mensajes['cantidad_errores'] == 0:
                # Se encarga de guardar las respuestas de INFILE-SAT esto para llevar registro
                status_saved = self.guardar_respuesta(mensajes)
                if status_saved != True:
                    return status_saved

                return {'status': 'OK', 'numero_autorizacion': mensajes['uuid']}
            else:
                return {'status': 'ERROR', 'numero_errores': str(mensajes['cantidad_errores']), 'detalles_errores': str(mensajes['descripcion_errores'])}
        except:
            return {'status': 'ERROR', 'detalles_errores': 'Error al tratar de validar la respuesta de INFILE-SAT: '+str(frappe.get_traceback())}

    def guardar_respuesta(self, mensajes):
        '''Funcion encargada guardar registro con respuestas de INFILE-SAT'''
        try:
            resp_fel = frappe.new_doc("Envio FEL")
            resp_fel.resultado = mensajes['resultado']
            resp_fel.fecha = mensajes['fecha']
            resp_fel.origen = mensajes['origen']
            resp_fel.descripcion = mensajes['descripcion']
            resp_fel.serie_factura_original = self.serie_factura

            if "control_emision" in mensajes:
                resp_fel.saldo = mensajes['control_emision']['Saldo']
                resp_fel.creditos = mensajes['control_emision']['Creditos']

            resp_fel.alertas = mensajes['alertas_infile']
            resp_fel.descripcion_alertas_infile = str(mensajes['descripcion_alertas_infile'])
            resp_fel.alertas_sat = mensajes['alertas_sat']
            resp_fel.descripcion_alertas_sat = str(mensajes['descripcion_alertas_sat'])
            resp_fel.cantidad_errores = mensajes['cantidad_errores']
            resp_fel.descripcion_errores = str(mensajes['descripcion_errores'])

            if "informacion_adicional" in mensajes:
                resp_fel.informacion_adicional = mensajes['informacion_adicional']

            resp_fel.uuid = mensajes['uuid']
            resp_fel.serie = mensajes['serie']
            resp_fel.numero = mensajes['numero']

            decodedBytes = base64.b64decode(mensajes['xml_certificado'])
            decodedStr = str(decodedBytes, "utf-8")
            resp_fel.xml_certificado = decodedStr

            resp_fel.save()
        except:
            return 'Error al tratar de guardar la rspuesta: '+str(frappe.get_traceback())
        else:
            return True

    def datos_generales(self):
        try:
            self.d_general = {
                "@CodigoMoneda": frappe.db.get_value('Sales Invoice', {'name': self.serie_factura}, 'currency'),
                "@FechaHoraEmision": str(datetime.datetime.now().replace(microsecond=0).isoformat()),  # "2018-11-01T16:33:47Z",
                "@Tipo": 'FACT'  #self.serie_facelec_fel
            }
        except:
            return 'Error en obtener data para datos generales: '+str(frappe.get_traceback())
        else:
            return True

    def emisor(self):
        '''Funcion encargada de obtener y asignar data del Emisor/Company'''
        try:
            # Obtencion data de EMISOR
            dat_fac = frappe.db.get_values('Sales Invoice',
                                        filters={'name': self.serie_factura},
                                        fieldname=['company', 'company_address'],
                                        as_dict=1)

            # Intentara obtener data de direccion compania, si no hay mostrara error
            try:
                dat_direccion = frappe.db.get_values('Address',
                                                    filters={'name': dat_fac[0]['company_address']},
                                                    fieldname=['address_line1', 'address_line2', 'email_id', 'pincode',
                                                            'state', 'city', 'country'], as_dict=1)
            except:
                return 'No se pudo obtener data de direccion de la compania, verificar que exista una direccion con data en los campos <b>address_line1, email_id, pincode, state, city, country</b>'

            dat_compania = frappe.db.get_values('Company',
                                                filters={'name': dat_fac[0]['company']},
                                                fieldname=['company_name', 'nit_face_company'],
                                                as_dict=1)
            if len(dat_direccion) > 0:
                # Validacion data
                for dire in dat_direccion[0]:
                    if dat_direccion[0][dire] is None or dat_direccion[0][dire] is '':
                        return 'No se puede completar la operacion ya que el campo {} de la direccion de compania no tiene data, por favor asignarle un valor e intentar de nuevo'.format(str(dire))
            else:
                return 'No se encontro ninguna direccion para la compania, verificar que exista una e intentar de nuevo'
            # Asignacion data
            self.d_emisor = {
                "@AfiliacionIVA": "GEN",
                "@CodigoEstablecimiento": frappe.db.get_value('Configuracion Factura Electronica',
                                                            {'name': self.nombre_config}, 'codigo_establecimiento'),  #"1",
                "@CorreoEmisor": dat_direccion[0]['email_id'],
                "@NITEmisor": (dat_compania[0]['nit_face_company']).replace('-', ''),
                "@NombreComercial": dat_compania[0]['company_name'],
                "@NombreEmisor": dat_compania[0]['company_name'],
                "dte:DireccionEmisor": {
                    "dte:Direccion": dat_direccion[0]['address_line1'] + ' - ' + dat_direccion[0]['address_line2'],
                    "dte:CodigoPostal": dat_direccion[0]['pincode'],
                    "dte:Municipio": dat_direccion[0]['state'],
                    "dte:Departamento": dat_direccion[0]['city'],
                    "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion[0]['country']}, 'code').upper()
                }
            }
        except:
            return 'Error no se puede completar la operacion por: '+str(frappe.get_traceback())
        else:
            return True

    def receptor(self):
        '''Funcion encargada de obtener y asignar data del Receptor/Cliente'''
        try:
            # Obtencion data de RECEPTOR
            dat_fac = frappe.db.get_values('Sales Invoice',
                                           filters={'name': self.serie_factura},
                                           fieldname=['nit_face_customer', 'customer_address'],
                                           as_dict=1)

            # Intentara obtener data de direccion cliente, si no hay mostrara error
            try:
                dat_direccion = frappe.db.get_values('Address',
                                                    filters={'name': dat_fac[0]['customer_address']},
                                                    fieldname=['address_line1', 'address_line2', 'email_id', 'pincode',
                                                               'state', 'city', 'country'], as_dict=1)
            except:
                return 'No se pudo obtener data de direccion de la compania, verificar que exista una direccion con data en los campos <b>address_line1, email_id, pincode, state, city, country</b>'

            if len(dat_direccion) > 0:
                # Validacion data
                for dire in dat_direccion[0]:
                    if dat_direccion[0][dire] is None or dat_direccion[0][dire] is '':
                        return 'No se puede completar la operacion ya que el campo {} de la direccion del cliente {} no tiene data, por favor asignarle un valor e intentar de nuevo'.format(str(dire), self.nombre_cliente)
            else:
                return 'No se encontro ninguna direccion para el cliente, verificar que exista una e intentar de nuevo'

            self.d_receptor = {
                "@CorreoReceptor": dat_direccion[0]['email_id'],
                "@IDReceptor": (dat_fac[0]['nit_face_customer']).replace('-', ''),  # NIT
                "@NombreReceptor": str(self.nombre_cliente),
                "dte:DireccionReceptor": {
                    "dte:Direccion": dat_direccion[0]['address_line1']+', '+dat_direccion[0]['address_line2'],
                    "dte:CodigoPostal": dat_direccion[0]['pincode'],
                    "dte:Municipio": dat_direccion[0]['state'],
                    "dte:Departamento": dat_direccion[0]['city'],
                    "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion[0]['country']}, 'code').upper()
                }
            }
        except:
            return 'Error no se puede completar la operacion por: '+str(frappe.get_traceback())
        else:
            return True

    def frases(self):
        # TODO: Consultar todas las posibles combinaciones disponibles
        self.d_frases = {
            "dte:Frase": {
                "@CodigoEscenario": "1",
                "@TipoFrase": "1"
            }
        }

        return True

    def items(self):
        '''Funcion encargada de asignar correctamente los items'''
        try:
            i_fel = {}
            items_ok = []
            # Obtencion item de factura
            dat_items = frappe.db.get_values('Sales Invoice Item',
                                            filters={'parent': str(self.serie_factura)},
                                            fieldname=['item_name', 'qty',
                                                        'item_code', 'description',
                                                        'net_amount', 'base_net_amount',
                                                        'discount_percentage',
                                                        'discount_amount',
                                                        'net_rate', 'stock_uom',
                                                        'serial_no', 'item_group',
                                                        'rate', 'amount',
                                                        'facelec_sales_tax_for_this_row',
                                                        'facelec_amount_minus_excise_tax',
                                                        'facelec_other_tax_amount',
                                                        'facelec_three_digit_uom_code',
                                                        'facelec_gt_tax_net_fuel_amt',
                                                        'facelec_gt_tax_net_goods_amt',
                                                        'facelec_gt_tax_net_services_amt'], as_dict=True)

            # Verificacion cantidad de items
            longitems = len(dat_items)
            if longitems > 1:
                contador = 0
                for i in range(0, longitems):
                    obj_item = {}

                    detalle_stock = frappe.db.get_value('Item', {'name': dat_items[i]['item_code']}, 'is_stock_item')
                    # Validacion de Bien o Servicio, en base a detalle de stock
                    if (int(detalle_stock) == 0):
                        obj_item["@BienOServicio"] = 'S'

                    if (int(detalle_stock) == 1):
                        obj_item["@BienOServicio"] = 'B'

                    contador += 1
                    obj_item["@NumeroLinea"] = contador
                    obj_item["dte:Cantidad"] = dat_items[i]['qty']
                    obj_item["dte:UnidadMedida"] = dat_items[i]['facelec_three_digit_uom_code']
                    obj_item["dte:Descripcion"] = dat_items[i]['description']
                    obj_item["dte:PrecioUnitario"] = dat_items[i]['rate']
                    obj_item["dte:Precio"] = dat_items[i]['amount']
                    obj_item["dte:Descuento"] = dat_items[i]['discount_amount']
                    obj_item["dte:Impuestos"] = {}
                    obj_item["dte:Impuestos"]["dte:Impuesto"] = {}

                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:NombreCorto"] = 'IVA'
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:CodigoUnidadGravable"] = '1'
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoGravable"] = (float(dat_items[i]['facelec_gt_tax_net_fuel_amt']) + float(dat_items[i]['facelec_gt_tax_net_goods_amt']) + float(dat_items[i]['facelec_gt_tax_net_services_amt'])) - float(dat_items[i]['discount_amount']) #float(dat_items[i]['facelec_amount_minus_excise_tax'])
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoImpuesto"] = float(dat_items[i]['facelec_sales_tax_for_this_row'])

                    obj_item["dte:Total"] = (float(dat_items[i]['facelec_amount_minus_excise_tax']) - float(dat_items[i]['discount_amount'])) # Se suman otr impuestos+ float(dat_items[i]['facelec_sales_tax_for_this_row'])
                
                    items_ok.append(obj_item)
            else:
                obj_item = {}

                detalle_stock = frappe.db.get_value('Item', {'name': dat_items[0]['item_code']}, 'is_stock_item')
                # Validacion de Bien o Servicio, en base a detalle de stock
                if (int(detalle_stock) == 0):
                    obj_item["@BienOServicio"] = 'S'

                if (int(detalle_stock) == 1):
                    obj_item["@BienOServicio"] = 'B'

                obj_item["@NumeroLinea"] = "1"
                obj_item["dte:Cantidad"] = dat_items[0]['qty']
                obj_item["dte:UnidadMedida"] = dat_items[0]['facelec_three_digit_uom_code']
                obj_item["dte:Descripcion"] = dat_items[0]['description']
                obj_item["dte:PrecioUnitario"] = dat_items[0]['rate']
                obj_item["dte:Precio"] = dat_items[0]['amount']
                obj_item["dte:Descuento"] = dat_items[0]['discount_amount']
                obj_item["dte:Impuestos"] = {}
                obj_item["dte:Impuestos"]["dte:Impuesto"] = {}

                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:NombreCorto"] = 'IVA'
                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:CodigoUnidadGravable"] = '1'
                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoGravable"] = (float(dat_items[0]['facelec_gt_tax_net_fuel_amt']) + float(dat_items[0]['facelec_gt_tax_net_goods_amt']) + float(dat_items[0]['facelec_gt_tax_net_services_amt'])) - float(dat_items[0]['discount_amount']) # precio - descuento/1.12
                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoImpuesto"] = float(dat_items[0]['facelec_sales_tax_for_this_row'])

                obj_item["dte:Total"] = (float(dat_items[0]['facelec_amount_minus_excise_tax']) - float(dat_items[0]['discount_amount'])) # Se suma otros impuestos + float(dat_items[0]['facelec_sales_tax_for_this_row'])
            
                items_ok.append(obj_item)

            i_fel = {"dte:Item": items_ok}
            self.d_items = i_fel

        except:
            return 'No se pudo obtener data de los items en la factura {}, Error: {}'.format(self.serie_factura, str(frappe.get_traceback()))
        else:
            return True

    def totales(self):
        try:
            dat_fac = frappe.db.get_values('Sales Invoice',
                                           filters={'name': self.serie_factura},
                                           fieldname=['grand_total', 'shs_total_iva_fac'],
                                           as_dict=1)
            self.d_totales = {
                "dte:TotalImpuestos": {
                    "dte:TotalImpuesto": {
                        "@NombreCorto": "IVA",
                        "@TotalMontoImpuesto": dat_fac[0]['shs_total_iva_fac']
                    }
                },
                "dte:GranTotal": dat_fac[0]['grand_total']
            }
        except:
            return 'No se pudo obtener data de la factura {}, Error: {}'.format(self.serie_factura, str(frappe.get_traceback()))
        else:
            return True

    def firmar_data(self, encodata):
        try:
            url = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config},
                                      'url_firma')
            codigo = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config},
                                         'codigo')
            alias = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config},
                                        'alias')
            anulacion = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config},
                                            'es_anulacion')
            llave = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config},
                                        'llave_pfx')
            reqfel = { 
                "llave": llave, # LLAVE
                "archivo": str(encodata),  # En base64
                # "codigo": codigo, # Número interno de cada transacción
                "alias":  alias, # USUARIO
                "es_anulacion": anulacion # "N" si es certificacion y "S" si es anulacion
            }

            headers = {"content-type": "application/json"}
            response = requests.post(url, data=json.dumps(reqfel), headers=headers)
        except:
            return 'Error al tratar de firmar el documento electronico: '+str(frappe.get_traceback())
        else:
            return True, (response.content).decode('utf-8')

    def solicitar_factura_electronica(self, firmado):
        '''Funcion encargada de solicitar factura electronica al WS'''
        # Realizara la comunicacion al webservice
        try:
            data_fac = frappe.db.get_value('Sales Invoice', {'name': self.serie_factura}, 'company')
            nit_company = frappe.db.get_value('Company', {'name': data_fac}, 'nit_face_company')

            url = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config}, 'url_dte')
            user = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config}, 'alias')
            llave = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config}, 'llave_ws')
            ident = self.serie_factura

            req_dte = {
                "nit_emisor": nit_company,
                "correo_copia": "m.monroyc22@gmail.com",
                "xml_dte": firmado["archivo"]
            }

            headers = {
                "content-type": "application/json",
                "usuario": user,
                "llave": llave,
                "identificador": ident
            }
            response = requests.post(url, data=json.dumps(req_dte), headers=headers)
        except:
            return 'Error al tratar de generar factura electronica: '+str(frappe.get_traceback())
        else:
            return True, (response.content).decode('utf-8')

    def actualizar_registros(self):
        """Funcion permite actualizar tablas en la base de datos, despues de haber generado
       la factura electronica

       Parametros:
       ----------
       * serieOriginalFac (str) : Serie de factura original
        """
        # Verifica que exista un documento en la tabla Envios Facturas Electronicas con el nombre de la serie original
        if frappe.db.exists('Envios FEL', {'serie_factura_original': self.serie_factura}):
            factura_guardada = frappe.db.get_values('Envios FEL',
                                                    filters={'serie_factura_original': self.serie_factura},
                                                    fieldname=['numero_dte', 'cae', 'serie_factura_original'], as_dict=1)
            # Esta seccion se encarga de actualizar la serie, con una nueva que es serie y numero
            # buscara en las tablas donde exista una coincidencia actualizando con la nueva serie
            try:
                # serieDte: guarda el numero DTE retornado por INFILE, se utilizara para reemplazar el nombre de la serie de la
                # factura que lo generó.
                serieDte = str(factura_guardada[0]['numero_dte'])
                # serie_fac_original: Guarda la serie original de la factura.
                serie_fac_original = serieOriginalFac

                # Actualizacion de tablas que son modificadas directamente.
                # 01 - tabSales Invoice
                frappe.db.sql('''UPDATE `tabSales Invoice`
                                SET name=%(name)s,
                                    cae_factura_electronica=%(cae_correcto)s,
                                    serie_original_del_documento=%(serie_orig_correcta)s
                                WHERE name=%(serieFa)s
                                ''', {'name':serieDte, 'cae_correcto': factura_guardada[0]['cae'],
                                    'serie_orig_correcta': serie_fac_original, 'serieFa':serie_fac_original})

                # 02 - tabSales Invoice Item
                frappe.db.sql('''UPDATE `tabSales Invoice Item` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

                # 03 - tabGL Entry
                frappe.db.sql('''UPDATE `tabGL Entry` SET voucher_no=%(name)s, against_voucher=%(name)s
                                WHERE voucher_no=%(serieFa)s AND against_voucher=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

                frappe.db.sql('''UPDATE `tabGL Entry` SET voucher_no=%(name)s, docstatus=1
                                WHERE voucher_no=%(serieFa)s AND against_voucher IS NULL''', {'name':serieDte, 'serieFa':serie_fac_original})

                # Actualizacion de tablas que pueden ser modificadas desde Sales Invoice
                # Verificara tabla por tabla en busca de un valor existe, en caso sea verdadero actualizara,
                # en caso no encuentre nada no hara nada
                # 04 - tabSales Taxes and Charges
                if frappe.db.exists('Sales Taxes and Charges', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Taxes and Charges` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

                if frappe.db.exists('Otros Impuestos Factura Electronica', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabOtros Impuestos Factura Electronica` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})


                # Pago programado
                # 05 - tabPayment Schedule
                if frappe.db.exists('Payment Schedule', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPayment Schedule` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})


                # subscripcion
                # 06 - tabSubscription
                if frappe.db.exists('Subscription', {'reference_document': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSubscription` SET reference_document=%(name)s
                                    WHERE reference_document=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})


                # Entrada del libro mayor de inventarios
                # 07 - tabStock Ledger Entry
                if frappe.db.exists('Stock Ledger Entry', {'voucher_no': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabStock Ledger Entry` SET voucher_no=%(name)s
                                    WHERE voucher_no=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})


                # Hoja de tiempo de factura de ventas
                # 08 - tabSales Invoice Timesheet
                if frappe.db.exists('Sales Invoice Timesheet', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Invoice Timesheet` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})


                # Equipo Ventas
                # 09 - tabSales Team
                if frappe.db.exists('Sales Team', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Team` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

                # Packed Item
                # 10 - tabPacked Item
                if frappe.db.exists('Packed Item', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPacked Item` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

                # Sales Invoice Advance - Anticipos a facturas
                # 11 - tabSales Invoice Advance
                if frappe.db.exists('Sales Invoice Advance', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Invoice Advance` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})


                # Sales Invoice Payment - Pagos sobre a facturas
                # 12 - tabSales Invoice Payment
                if frappe.db.exists('Sales Invoice Payment', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Invoice Payment` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})


                # Payment Entry Reference -
                # 13 - tabPayment Entry Reference
                if frappe.db.exists('Payment Entry Reference', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Invoice Payment` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

                # Sales Order
                # 15 - tabSales Order
                if frappe.db.exists('Sales Order', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Order` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

                # Parece que este no enlaza directamente con sales invoice es el sales invoice que enlaza con este.
                # Delivery Note
                # 16 - tabDelivery Note
                if frappe.db.exists('Delivery Note', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabDelivery Note` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

                frappe.db.commit()

            except:
                # En caso exista un error al renombrar la factura retornara el mensaje con el error
                frappe.msgprint(_('Error al renombrar Factura. Por favor intente de nuevo presionando el boton Factura Electronica'))
            else:
                # Si los datos se Guardan correctamente, se retornara el Numero Dte generado, que sera capturado por api.py
                # para luego ser capturado por javascript, se utilizara para recargar la url con los cambios correctos
                return str(factura_guardada[0]['numero_dte'])

