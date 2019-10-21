# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime
from factura_electronica.utils.utilities_facelec import normalizar_texto
import json, xmltodict
import base64


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
        self.series_facelec = str(series_conf)  # Series para factura electronica

    def construir_peticion(self):
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
                    # "ds:Signature": self.d_firma
                }
            }
            try:
                # To XML
                xmlString = xmltodict.unparse(base_peticion, pretty=True)
                with open('mario.xml', 'w') as f:
                    f.write(xmlString)

                # A base64
                encodedBytes = base64.b64encode(xmlString.encode("utf-8"))
                encodedStr = str(encodedBytes, "utf-8")

                reqfel = { 
                    "llave": , #  LLAVE
                    "archivo": encodedStr
                    "codigo": , # Número interno de cada transacción
                    "alias":  usuario, # USUARIO
                    "es_anulacion":  # "N" si es certificacion y "S" si es anulacion
                }

            except:
                return 'Error: '+str(frappe.get_traceback())
            else:
                return 'OK'

        else:
            return e_validador

    def validador_data(self):
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
        if estado_f != True:
            return estado_f

        estado_t = self.totales()
        if estado_f != True:
            return estado_f

        return True

    def validador_respuetas(self):
        pass

    def datos_generales(self):
        try:
            self.d_general = {
                "@CodigoMoneda": frappe.db.get_value('Sales Invoice', {'name': self.serie_factura}, 'currency'),
                "@FechaHoraEmision": str(datetime.now().utcnow()),  # "2018-11-01T16:33:47Z",
                "@Tipo": "FACT"
            }
        except:
            return 'Error en obtener data para datos generales: '+str(frappe.get_traceback())
        else:
            return True

    def emisor(self):
        '''Funcion encargada de obtener y asignar data del Emisor'''
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

            # Validacion data
            for dire in dat_direccion[0]:
                if dat_direccion[0][dire] is None or dat_direccion[0][dire] is '':
                    return 'No se puede completar la operacion ya que el campo {} de la direccion de compania no tiene data, por favor asignarle un valor e intentar de nuevo'.format(str(dire))

            # Asignacion data
            self.d_emisor = {
                "@AfiliacionIVA": "GEN",
                "@CodigoEstablecimiento": frappe.db.get_value('Configuracion Factura Electronica',
                                                            {'name': self.nombre_config}, 'codigo_establecimiento'),  #"1",
                "@CorreoEmisor": dat_direccion[0]['email_id'],
                "@NITEmisor": dat_compania[0]['nit_face_company'],
                "@NombreComercial": dat_compania[0]['company_name'],
                "@NombreEmisor": dat_compania[0]['company_name'],
                "dte:DireccionEmisor": {
                    "dte:Direccion": dat_direccion[0]['address_line1'] + ' - ' + dat_direccion[0]['address_line2'],
                    "dte:CodigoPostal": dat_direccion[0]['pincode'],
                    "dte:Municipio": dat_direccion[0]['state'],
                    "dte:Departamento": dat_direccion[0]['city'],
                    "dte:Pais": dat_direccion[0]['country']
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

            # Validacion data
            for dire in dat_direccion[0]:
                if dat_direccion[0][dire] is None or dat_direccion[0][dire] is '':
                    return 'No se puede completar la operacion ya que el campo {} de la direccion del cliente {} no tiene data, por favor asignarle un valor e intentar de nuevo'.format(str(dire), self.nombre_cliente)

            self.d_receptor = {
                "@CorreoReceptor": dat_direccion[0]['email_id'],
                "@IDReceptor": dat_fac[0]['nit_face_customer'],  # NIT
                "@NombreReceptor": str(self.nombre_cliente),
                "dte:DireccionReceptor": {
                    "dte:Direccion": dat_direccion[0]['address_line1']+', '+dat_direccion[0]['address_line2'],
                    "dte:CodigoPostal": dat_direccion[0]['pincode'],
                    "dte:Municipio": dat_direccion[0]['state'],
                    "dte:Departamento": dat_direccion[0]['city'],
                    "dte:Pais": dat_direccion[0]['country']
                }
            }
        except:
            return 'Error no se puede completar la operacion por: '+str(frappe.get_traceback())
        else:
            return True

    def frases(self):
        self.d_frases = {
            "dte:Frase": {
                "@CodigoEscenario": "1",
                "@TipoFrase": "1"
            }
        }

        return True

    def items(self):
        try:
            items_ok = []
            # Obtencion item de factura
            dat_items = frappe.db.get_values('Sales Invoice Item',
                                            filters = {'parent': self.serie_factura},
                                            fieldname = ['item_name', 'qty',
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
                                                        'facelec_gt_tax_net_services_amt'], as_dict = 1)

            # Verificacion cantidad de items
            if len(dat_items) > 1:
                for i in range(0, len(dat_items)):
                    obj_item = {}

                    detalle_stock = frappe.db.get_value('Item', {'name': dat_items[i]['item_code']}, 'is_stock_item')
                    # Validacion de Bien o Servicio, en base a detalle de stock
                    if (int(detalle_stock) == 0):
                        obj_item["@BienOServicio"] = 'S'

                    if (int(detalle_stock) == 1):
                        obj_item["@BienOServicio"] = 'B'

                    obj_item["@NumeroLinea"] = "1"
                    obj_item["dte:Cantidad"] = dat_items[i]['qty']
                    obj_item["dte:UnidadMedida"] = dat_items[i]['facelec_three_digit_uom_code']
                    obj_item["dte:Descripcion"] = dat_items[i]['description']
                    obj_item["dte:PrecioUnitario"] = dat_items[i]['rate']
                    obj_item["dte:Precio"] = dat_items[i]['rate']
                    obj_item["dte:Descuento"] = dat_items[i]['discount_amount']
                    obj_item["dte:Impuestos"] = {}
                    obj_item["dte:Impuestos"]["dte:Impuesto"] = {}

                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:NombreCorto"] = 'IVA'
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:CodigoUnidadGravable"] = '1'
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoGravable"] = float(dat_items[i]['grand_total'])
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoImpuesto"] = float(dat_items[i]['facelec_sales_tax_for_this_row'])

                    obj_item["dte:Total"] = float(dat_items[i]['grand_total']) + float(dat_items[i]['facelec_sales_tax_for_this_row'])
                
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
                obj_item["dte:Precio"] = dat_items[0]['rate']
                obj_item["dte:Descuento"] = dat_items[0]['discount_amount']
                obj_item["dte:Impuestos"] = {}
                obj_item["dte:Impuestos"]["dte:Impuesto"] = {}

                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:NombreCorto"] = 'IVA'
                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:CodigoUnidadGravable"] = '1'
                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoGravable"] = float(dat_items[0]['grand_total'])
                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoImpuesto"] = float(dat_items[0]['facelec_sales_tax_for_this_row'])

                obj_item["dte:Total"] = float(dat_items[i]['grand_total']) + float(dat_items[0]['facelec_sales_tax_for_this_row'])
            
                items_ok.append(obj_item)

            self.d_items = {
                "dte:Item": items_ok
            }
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
                        "@TotalMontoImpuesto": dat_fac[0]['grand_total']
                    }
                },
                "dte:GranTotal": dat_fac[0]['shs_total_iva_fac']
            }
        except:
            return 'No se pudo obtener data de la factura {}, Error: {}'.format(self.serie_factura, str(frappe.get_traceback()))
        else:
            return True

    def firma(self):
        pass
    
    def solicitar_factura_electronica(self):
        # Realizara la comunicacion al webservice
        try:
            headers = {"content-type": "json/xml"}
            response = requests.post(url_servicio, data=datos_xml, headers=headers, timeout=15)
        except:
            frappe.msgprint(_('''Tiempo de espera agotado para webservice, verificar conexion a internet
                            e intentar de nuevo: \n {}'''.format(frappe.get_traceback())))

        # Si hay algun error en la respuesta, lo capturara y mostrara
        try:
            respuesta_webservice = response.content
        except:
            frappe.msgprint(_('Error en la comunicacion no se recibieron datos de INFILE: {}'.format(frappe.get_traceback())))
        else:
            return respuesta_webservice
