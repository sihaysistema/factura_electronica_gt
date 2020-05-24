# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict

import json, xmltodict
import base64
import requests
import datetime


# NOTAS:
# 1. INSTANCIA FACT

# 2. BUILD
# 2.1 VALIDATOR

# 3. FIRMAR FACTURA
# 3.1 VALIDAR RESPUESTAS

# 4. SOLICITAR FEL
# 4.1 VALIDAR RESPUESTAS

# 5 GUARDAR REGISTROS ENVIOS, LOG
# 5.1 ACTUALIZAR REGISTROS

class ElectronicInvoice:
    def __init__(self, invoice_code, conf_name):
        self.__invoice_code = ''
        self.__config_name = ''
        self.__log_error = []
        # self.__general_data = {}
        # self.__data_sender = {}
        # self.__data_receiver = {}
        # self.__data_phrases = {}
        # self.__items = {}
        # self.__totals = {}

    def build_invoice(self):
        # 1 Validamos la data antes de construir
        status_validate = self.validate()

    def validate(self):
        """
        Funcion encargada de validar la data que construye la peticion a INFILE,
        Si existe por lo menos un error retornara la descripcion con dicho error

        Returns:
            [type]: [description]
        """

        # Validacion y generacion seccion datos generales
        status_data_gen = self.general_data()
        if status_data_gen[0] == False:
            # Si existe algun error se retornara una tupla
            return status_data_gen

        # Validacion y generacion seccion emisor
        status_sender = self.sender()
        if status_sender[0] == False:
            # Si existe algun error se retornara una tupla
            return status_sender

        # Validacion y generacion seccion receptor
        estado_r = self.receptor()
        if estado_r != True:
            return estado_r

        # Validacion y generacion seccion frases
        estado_f = self.frases()
        if estado_f != True:
            return estado_f

        # Validacion y generacion seccion items
        estado_i = self.items()
        if estado_i != True:
            return estado_i

        # Validacion y generacion seccion totales
        estado_t = self.totales()
        if estado_t != True:
            return estado_t

        return True

    def general_data(self):
        """
        Construye la seccion datos generales que incluye, codigo de moneda, Fecha y Hora de emision
        Tipo de factura

        Returns:
            tuple: Primera posicion True/False, Segunda posicion descripcion msj
        """

        try:
            self.d_general = {
                "@CodigoMoneda": frappe.db.get_value('Sales Invoice', {'name': self.serie_factura}, 'currency'),
                "@FechaHoraEmision": str(datetime.datetime.now().replace(microsecond=0).isoformat()),  # "2018-11-01T16:33:47Z",
                "@Tipo": frappe.db.get_value('Configuracion Series FEL', {'parent': self.nombre_config}, 'tipo_documento')  # 'FACT'  #self.serie_facelec_fel TODO: Poder usar todas las disponibles
            }
        except:
            return False, f'Error en obtener data para datos generales: {str(frappe.get_traceback())}'
        else:
            return True, 'OK'

    def sender(self):
        """
        Valida y obtiene la data necesaria para la seccion de Emisor

        Returns:
            str: Descripcion con el status de la trasaccion
        """

        # De la factura obtenemos la compañia y direccion compañia emisora
        dat_fac = frappe.db.get_values('Sales Invoice',
                                       filters={'name': self.__invoice_code},
                                       fieldname=['company', 'company_address'],
                                       as_dict=1)
        if len(dat_fac) == 0:
            return False, f'No se encontro ninguna factura con serie: {self.__invoice_code}. Por favor valida los datos de la factura que deseas procesar'


        # Obtenemos datos necesario de company: Nombre de compañia, nit
        dat_compania = frappe.db.get_values('Company',
                                            filters={'name': dat_fac[0]['company']},
                                            fieldname=['company_name', 'nit_face_company', 'tax_id'],
                                            as_dict=1)
        if len(dat_compania) == 0:
            return False, f'No se encontraron datos para la compañia {dat_fac[0]["company_name"]}. Verifica que la factura que deseas procesar tenga una compañia valida'


        # De la compañia, obtenemos direccion 1, email, codigo postal, departamento, municipio, pais
        dat_direccion = frappe.db.get_values('Address',
                                             filters={'name': dat_fac[0]['company_address']},
                                             fieldname=['address_line1', 'email_id', 'pincode',
                                                        'state', 'city', 'country'], as_dict=1)
        if len(dat_direccion) == 0:
            return False, f'No se encontro ninguna direccion de la compania {dat_fac[0]["company_name"]}, verifica que exista una con data en los campos address_line1, email_id, pincode, state, city, country'


        # Validacion de existencia en los campos de direccion, ya que son obligatorio por parte de la API FEL
        # Usaremos la primera que se encuentre
        for dire in dat_direccion[0]:
            if dat_direccion[0][dire] is None or dat_direccion[0][dire] is '':
                return 'No se puede completar la operacion ya que el campo {} de la direccion de compania no tiene data, por favor asignarle un valor e intentar de nuevo'.format(str(dire))

        # Asignacion data
        self.d_emisor = {
            "@AfiliacionIVA": frappe.db.get_value('Configuracion Factura Electronica',
                                                 {'name': self.nombre_config}, 'afiliacion_iva'),
            "@CodigoEstablecimiento": frappe.db.get_value('Configuracion Factura Electronica',
                                                         {'name': self.nombre_config}, 'codigo_establecimiento'),  #"1",
            "@CorreoEmisor": dat_direccion[0]['email_id'],
            "@NITEmisor": (dat_compania[0]['nit_face_company']).replace('-', ''),
            "@NombreComercial": dat_compania[0]['company_name'],
            "@NombreEmisor": dat_compania[0]['company_name'],
            "dte:DireccionEmisor": {
                "dte:Direccion": dat_direccion[0]['address_line1'],
                "dte:CodigoPostal": dat_direccion[0]['pincode'],  # Codig postal
                "dte:Municipio": dat_direccion[0]['state'],  # Municipio
                "dte:Departamento": dat_direccion[0]['city'],  # Departamento
                "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion[0]['country']}, 'code').upper()  # CODIG PAIS
            }
        }


    def receiver(self):
        pass

    def phrases(self):
        pass

    def items(self):
        pass

    def totals(self):
        pass

    def sign_invoice(self):
        pass

    def request_electronic_invoice(self):
        pass

    def response_validator(self):
        pass

    def save_answers(self):
        pass

    def upgrade_records(self):
        pass

    def save_deliveries(self):
        pass

    def send_email(self):
        pass
