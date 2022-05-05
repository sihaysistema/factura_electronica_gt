# Copyright (c) 2022, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import base64
import json

import frappe
import requests
import xmltodict
# from frappe import _
from frappe.utils import nowdate, nowtime


class CancelDocument:
    def __init__(self, invoice_code, conf_name, reason_cancelation, doctype_name):
        """__init__
        Constructor de la clase, las propiedades iniciadas como privadas

        Args:
            invoice_code (str): Serie origianl de la factura
            conf_name (str): Nombre configuracion para factura electronica
            reason_cancelation (str): Razón por la cual se cancela doc electronico
            doctype_name (str): Nombre doctype
        """
        self.__invoice_code = invoice_code
        self.__config_name = conf_name
        self.__doctype = doctype_name
        self.__reason = reason_cancelation or "Anulacion"

    def validate_requirements(self):
        """
        Validador requerimientos para generar peticion para anulacion doc

        Returns:
            dict: msg status
        """
        self.info_invoice = frappe.db.get_value(self.__doctype, {'name': self.__invoice_code},
                                                ['numero_autorizacion_fel', 'tax_id',
                                                 'naming_series', 'company'], as_dict=1)

        if not frappe.db.exists('Envio FEL', {'name': self.info_invoice.numero_autorizacion_fel}):
            msg = 'UUID de documento electronico no valido, no se encontro guardado en base de datos, \
                si desea generar una cancelacion antes debe haber generado factura electronica FEL',
            return {
                'status': False,
                'description': msg,
                'error': ''
            }

        return {'status': True, 'description': 'OK', 'error': ''}

    def build_request(self):
        """
        Genera estructura JSON con datos para petición WS SAT, para luego ser convertida en XML

        Returns:
            dict: msg status
        """

        try:
            self.tax_id_company = frappe.db.get_value('Company',
                                                      {'name': self.info_invoice.company},
                                                      'nit_face_company').replace('-', '').upper().strip()
            # Fecha en que se emitio el documento
            issue_date = frappe.db.get_value('Envio FEL', {'name': self.info_invoice.numero_autorizacion_fel}, 'fecha')

            self.__base_peticion = {
                "dte:GTAnulacionDocumento": {
                    "@xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
                    "@xmlns:dte": "http://www.sat.gob.gt/dte/fel/0.1.0",
                    "@xmlns:n1": "http://www.altova.com/samplexml/other-namespace",
                    "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "@Version": "0.1",
                    "@xsi:schemaLocation": "http://www.sat.gob.gt/dte/fel/0.1.0",
                    "dte:SAT": {
                        "dte:AnulacionDTE": {
                            "@ID": "DatosCertificados",
                            "dte:DatosGenerales": {
                                "@FechaEmisionDocumentoAnular": str(issue_date),  # "2020-03-04T00:00:00-06:00",
                                "@FechaHoraAnulacion": str(nowdate())+'T'+str(nowtime().rpartition('.')[0]),  # "2020-04-21T00:00:00-06:00",
                                "@ID": "DatosAnulacion",
                                "@IDReceptor": str(self.info_invoice.tax_id).replace('-', '').replace('/', '').upper().strip(),
                                "@MotivoAnulacion": self.__reason,
                                "@NITEmisor": self.tax_id_company,
                                "@NumeroDocumentoAAnular": self.info_invoice.numero_autorizacion_fel
                            }
                        }
                    }
                }
            }

            # USAR SOLO PARA DEBUG:
            with open('PREVIEW-ANULADOR.xml', 'w') as f:
                f.write(xmltodict.unparse(self.__base_peticion, pretty=True))

            with open('PREVIEW-ANULADOR.json', 'w') as f:
                f.write(json.dumps(self.__base_peticion, default=str))

            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            return {'status': False,
                    'description': f'Ocurrio un problema al tratar de generar la estructura para la anulacion del documento {self.__invoice_code}',
                    'error': frappe.get_traceback()}

    def sign_invoice(self):
        """
        Funcion encargada de solicitar firma para archivo XML

        Returns:
            dict: msg status
        """

        try:
            # To XML: Convierte de JSON a XML indentado
            self.__xml_string = xmltodict.unparse(self.__base_peticion, pretty=True, encoding='utf-8')

            # Usar solo para debug
            with open('PREVIEW-ANULADOR.xml', 'w') as f:
                f.write(self.__xml_string)

        except Exception:
            return {'status': False,
                    'description': f'La peticion para el documento {self.__invoice_code} no se pudo convertir a XML. Si la falla persiste comunicarse con soporte',
                    'error': frappe.get_traceback()}

        try:
            # To base64: Convierte a base64, para enviarlo en la peticion
            self.__encoded_bytes = base64.b64encode(self.__xml_string.encode("utf-8"))
            self.__encoded_str = str(self.__encoded_bytes, "utf-8")

        except Exception:
            return {'status': False,
                    'description': f'La peticion para el documento {self.__invoice_code} no se pudo convertir a base64. Si la falla persiste comunicarse con soporte',
                    'error': frappe.get_traceback()}

        # Generamos la peticion para firmar
        try:
            url = str(frappe.db.get_value('Configuracion Factura Electronica',
                                          {'name': self.__config_name}, 'url_firma')).strip()

            alias = str(frappe.db.get_value('Configuracion Factura Electronica',
                                            {'name': self.__config_name}, 'alias')).strip()

            # anulacion = str(frappe.db.get_value('Configuracion Factura Electronica',
            #                                     {'name': self.__config_name}, 'es_anulacion')).strip()

            self.__llave = str(frappe.db.get_value('Configuracion Factura Electronica',
                                                   {'name': self.__config_name}, 'llave_pfx')).strip()

            self.__data_a_firmar = {
                "llave": self.__llave,  # LLAVE
                "archivo": str(self.__encoded_str),  # En base64
                "alias": alias,  # USUARIO
                "es_anulacion": 'S'  # "N" si es certificacion y "S" si es anulacion
            }

            # DEBUGGING WRITE JSON PETITION TO SITES FOLDER
            # with open('peticion.json', 'w') as f:
            #      f.write(json.dumps(self.__data_a_firmar, indent=2))

            headers = {"content-type": "application/json"}
            response = requests.post(url, data=json.dumps(self.__data_a_firmar), headers=headers)

            # Guardamos en una variable privada la respuesta
            self.__doc_firmado = json.loads((response.content).decode('utf-8'))

            # Guardamos la respuesta en un archivo DEBUG
            # with open('recibido_cancelador_firmado.json', 'w') as f:
            #      f.write(json.dumps(self.__doc_firmado, indent=2))

            # Si la respuesta es true
            if self.__doc_firmado.get('resultado'):
                # Guardamos en privado el documento firmado y encriptado
                self.__encrypted = self.__doc_firmado.get('archivo')

                # Retornamos el status del proceso
                return {'status': True, 'description': 'OK', 'error': ''}

            else:  # Si ocurre un error retornamos la descripcion del error por INFILE
                return {'status': False,
                        'description': f'Documento {self.__invoice_code} no pudo ser validado y firmado por INFILE',
                        'error': self.__doc_firmado.get('descripcion')}

        except Exception:
            return {'status': False,
                    'description': f'La peticion para el documento {self.__invoice_code} no se pudo enviar a INFILE. Si la falla persiste comunicarse con soporte',
                    'error': frappe.get_traceback()}

    def request_cancel(self):
        """
        Funcion encargada de solicitar factura electronica al Web Service de INFILE

        Returns:
            dict: msg status
        """

        try:
            url = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'url_de_anulacion')
            user = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'alias')
            llave = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'llave_ws')
            correo_copia = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'correo_copia')
            ident = self.__invoice_code  # identificador

            req_dte = {
                "nit_emisor": self.tax_id_company,
                "correo_copia": correo_copia,  # "m.monroyc22@gmail.com",
                "xml_dte": self.__encrypted
            }

            headers = {
                "content-type": "application/json",
                "usuario": user,
                "llave": llave,
                "identificador": ident
            }

            self.__response = requests.post(url, data=json.dumps(req_dte), headers=headers)
            self.__response_ok = json.loads((self.__response.content).decode('utf-8'))

            # DEBUGGING WRITE JSON RESPONSES TO SITES FOLDER
            # with open('response_cancelador.json', 'w') as f:
            #     f.write(json.dumps(self.__response_ok, indent=2))
            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            msg_e = f'Ocurrio un problema con la peticion para factura electronica documento {self.__invoice_code},\
                asegure de tener una configuracion completa para Factura Electronica'
            return {'status': False, 'description': msg_e, 'error': frappe.get_traceback()}

    def response_validator(self):
        """
        Funcion encargada de verificar las respuestas de INFILE-SAT

        Returns:
            dict: msg status
        """

        try:
            # Verifica que no existan errores
            if self.__response_ok['resultado'] and (self.__response_ok['cantidad_errores'] == 0):
                status_saved = self.save_answers()

                # Al primer error encontrado retornara un detalle con el mismo
                if not status_saved.get('status'):
                    return status_saved

                return {'status': True, 'description': 'Documento Anulado con Exito', 'error': ''}

            else:
                return {'status': False, 'description': 'Documento no pudo ser anulado',
                        'error': self.__response_ok['descripcion_errores']}
        except Exception:
            return {'status': False, 'description': 'La respuesta de INFILE no se pudo validar', 'error': frappe.get_traceback()}

    def save_answers(self):
        """
        Funcion encargada guardar registro con respuestas de INFILE-SAT

        Returns:
            dict: msg status
        """

        try:
            # Solo actualizamos el estado del doc ya generado marcandolo como cancelado
            doc = frappe.get_doc('Envio FEL', {'name': self.info_invoice.numero_autorizacion_fel})
            doc.status = 'Cancelled'
            doc.save(ignore_permissions=True)

            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            return {'status': False, 'description': 'Error al guardar el estado del documento en Envios FEL',
                    'error': frappe.get_traceback()}
