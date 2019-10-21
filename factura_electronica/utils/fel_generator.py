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
                    },
                    "ds:Signature": self.d_firma
                }
            }
        else:
            pass

    def validador_data(self):
        # Validacion y generacion seccion datos generales
        pass


        
        # Datos de la factura ERP

        # Datos del cliente

        # Datos de la empresa

        # Configuraciones Factura Electronica

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
                                        filters={'name': self.serie_factura}
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
                                                filters={'name': dat_fac[0]['company']}
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
                                                            {'name': self.nombre_config}, 'codigo_establecimiento')  #"1",
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
                                           filters={'name': self.serie_factura}
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

    def items(self):
        self.d_items = {
            "dte:Item": [{
                    "@BienOServicio": "E",
                    "@NumeroLinea": "1",
                    "dte:Cantidad": "2",
                    "dte:UnidadMedida": "UND",
                    "dte:Descripcion": "Prueba de esquema",
                    "dte:PrecioUnitario": "625.00",
                    "dte:Precio": "1250.00",
                    "dte:Descuento": "0.00",
                    "dte:Impuestos": {
                        "dte:Impuesto": {
                            "dte:NombreCorto": "IVA",
                            "dte:CodigoUnidadGravable": "1",
                            "dte:MontoGravable": "1116.07",
                            "dte:MontoImpuesto": "133.95"
                        }
                    },
                    "dte:Total": "1250.00"
                },
                {
                    "@BienOServicio": "E",
                    "@NumeroLinea": "1",
                    "dte:Cantidad": "2",
                    "dte:UnidadMedida": "UND",
                    "dte:Descripcion": "Prueba de esquema",
                    "dte:PrecioUnitario": "0.00",
                    "dte:Precio": "0.00",
                    "dte:Descuento": "0.00",
                    "dte:Impuestos": {
                        "dte:Impuesto": {
                            "dte:NombreCorto": "IVA",
                            "dte:CodigoUnidadGravable": "2",
                            "dte:MontoGravable": "0.07",
                            "dte:MontoImpuesto": "0.95"
                        }
                    },
                    "dte:Total": "0.00"
                }
            ]
        }

    def totales(self):
        self.d_totales = {
            "dte:TotalImpuestos": {
                "dte:TotalImpuesto": {
                    "@NombreCorto": "IVA",
                    "@TotalMontoImpuesto": "133.93"
                }
            },
            "dte:GranTotal": "1250.00"
        }

    def firma(self):
        pass
    
    def solicitar_factura_electronica(self):
        pass
