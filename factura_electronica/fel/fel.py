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
        self.__invoice_code = invoice_code
        self.__config_name = conf_name
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
        status_receiver = self.receiver()
        if status_receiver[0] == False:
            return status_receiver

        # Validacion y generacion seccion frases
        status_phrases = self.phrases()
        if status_phrases == False:
            return status_phrases

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
                "@CodigoMoneda": frappe.db.get_value('Sales Invoice', {'name': self.__invoice_code}, 'currency'),
                "@FechaHoraEmision": str(datetime.datetime.now().replace(microsecond=0).isoformat()),  # "2018-11-01T16:33:47Z",
                "@Tipo": frappe.db.get_value('Configuracion Series FEL', {'parent': self.__config_name}, 'tipo_documento')  # 'FACT'  #self.serie_facelec_fel TODO: Poder usar todas las disponibles
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
        try:
            # De la factura obtenemos la compañia y direccion compañia emisora
            self.dat_fac = frappe.db.get_values('Sales Invoice', filters={'name': self.__invoice_code},
                                                fieldname=['company', 'company_address', 'nit_face_customer', 'customer_address',
                                                           'customer_name'], as_dict=1)
            if len(self.dat_fac) == 0:
                return False, f'No se encontro ninguna factura con serie: {self.__invoice_code}. Por favor valida los datos de la factura que deseas procesar'


            # Obtenemos datos necesario de company: Nombre de compañia, nit
            dat_compania = frappe.db.get_values('Company', filters={'name': self.dat_fac[0]['company']},
                                                fieldname=['company_name', 'nit_face_company', 'tax_id'],
                                                as_dict=1)
            if len(dat_compania) == 0:
                return False, f'No se encontraron datos para la compañia {self.dat_fac[0]["company_name"]}. Verifica que la factura que deseas procesar tenga una compañia valida'


            # De la compañia, obtenemos direccion 1, email, codigo postal, departamento, municipio, pais
            dat_direccion = frappe.db.get_values('Address', filters={'name': self.dat_fac[0]['company_address']},
                                                 fieldname=['address_line1', 'email_id', 'pincode',
                                                            'state', 'city', 'country'], as_dict=1)
            if len(dat_direccion) == 0:
                return False, f'No se encontro ninguna direccion de la compania {self.dat_fac[0]["company_name"]}, verifica que exista una con data en los campos address_line1, email_id, pincode, state, city, country'


            # Validacion de existencia en los campos de direccion, ya que son obligatorio por parte de la API FEL
            # Usaremos la primera que se encuentre
            for dire in dat_direccion[0]:
                if dat_direccion[0][dire] is None or dat_direccion[0][dire] is '':
                    return False, 'No se puede completar la operacion ya que el campo {} de la direccion de compania no tiene data, por favor asignarle un valor e intentar de nuevo'.format(str(dire))

            # Asignacion data
            self.__d_emisor = {
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
        except:
            return False, 'Problema al tratar de generar data para emisor'

    def receiver(self):
        """
        Validacion y generacion datos de Receptor (cliente)

        Returns:
            [type]: [description]
        """

        # Intentara obtener data de direccion cliente
        try:
            dat_direccion = frappe.db.get_values('Address', filters={'name': self.dat_fac[0]['customer_address']},
                                                 fieldname=['address_line1', 'email_id', 'pincode',
                                                            'state', 'city', 'country'], as_dict=1)
            if len(dat_direccion) == 0:
                return False, f'No se encontro ninguna direccion para el cliente {self.dat_fac[0]["customer_name"]}. Por favor asigna un direccion y vuelve a intentarlo'

            # Validacion data direccion cliente
            for dire in dat_direccion[0]:
                if dat_direccion[0][dire] is None or dat_direccion[0][dire] is '':
                    return False, 'No se puede completar la operacion ya que el campo {} de la direccion del cliente {} no tiene data, por favor asignarle un valor e intentar de nuevo'.format(str(dire), self.nombre_cliente)


            # Si es consumidor Final: para generar factura electronica obligatoriamente se debe asignar un correo
            # electronico, los demas campos se pueden dejar como defualt para ciudad
            if str(dat_fac[0]['nit_face_customer']).upper() == 'C/F':
                self.__d_receptor = {
                    "@CorreoReceptor": dat_direccion[0]['email_id'],
                    "@IDReceptor": (dat_fac[0]['nit_face_customer']).replace('/', ''),  # NIT => CF
                    "@NombreReceptor": str(self.nombre_cliente),
                    "dte:DireccionReceptor": {
                        "dte:Direccion": dat_direccion[0]['address_line1'],
                        "dte:CodigoPostal": dat_direccion[0]['pincode'],
                        "dte:Municipio": dat_direccion[0]['state'],
                        "dte:Departamento": dat_direccion[0]['city'],
                        "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion[0]['country']}, 'code').upper()
                    }
                }
            else:
                self.__d_receptor = {
                    "@CorreoReceptor": dat_direccion[0]['email_id'],
                    "@IDReceptor": (dat_fac[0]['nit_face_customer']).replace('-', ''),  # NIT
                    "@NombreReceptor": str(self.nombre_cliente),
                    "dte:DireccionReceptor": {
                        "dte:Direccion": dat_direccion[0]['address_line1'],
                        "dte:CodigoPostal": dat_direccion[0]['pincode'],
                        "dte:Municipio": dat_direccion[0]['state'],
                        "dte:Departamento": dat_direccion[0]['city'],
                        "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion[0]['country']}, 'code').upper()
                    }
                }
        except:
            return False, 'Error no se puede completar la operacion por: '+str(frappe.get_traceback())
        else:
            return True, 'OK'

    def phrases(self):
        """
        debe indicarse los regímenes y textos especiales que son requeridos en los DTE,
        de acuerdo a la afiliación del contribuyente y tipo de operación.

        Returns:
            boolean: True/False
        """

        try:
            # TODO: Consultar todas las posibles combinaciones disponibles
            self.__d_frases = {
                "dte:Frase": {
                    "@CodigoEscenario": frappe.db.get_value('Configuracion Factura Electronica',
                                                           {'name': self.__config_name}, 'codigo_escenario'), #"1",
                    "@TipoFrase": frappe.db.get_value('Configuracion Factura Electronica',
                                                     {'name': self.__config_name}, 'tipo_frase')[:1]  # "1"
                }
            }
        except:
            return False, 'Error, no se puedo obtener valor de Codigo Escenario y Tipo Frase'
        else:
            return True, 'OK'

    def items(self):
        try:
            i_fel = {}  # Guardara la seccion de items ok
            items_ok = []  # Guardara todos los items OK

            # Obtenemos los items de la factura
            dat_items = frappe.db.get_values('Sales Invoice Item', filters={'parent': str(self.__invoice_code)},
                                             fieldname=['item_name', 'qty', 'item_code', 'description',
                                                        'net_amount', 'base_net_amount', 'discount_percentage',
                                                        'discount_amount', 'price_list_rate', 'net_rate',
                                                        'stock_uom', 'serial_no', 'item_group', 'rate',
                                                        'amount', 'facelec_sales_tax_for_this_row',
                                                        'facelec_amount_minus_excise_tax',
                                                        'facelec_other_tax_amount', 'facelec_three_digit_uom_code',
                                                        'facelec_gt_tax_net_fuel_amt', 'facelec_gt_tax_net_goods_amt',
                                                        'facelec_gt_tax_net_services_amt'], as_dict=True)

            # Verificamos la cantidad de items
            longitems = len(dat_items)
            # Si hay mas de un item a facturar
            if longitems > 1:
                contador = 0  # Utilizado para enumerar las lineas en factura electronica

                for i in range(0, longitems):
                    obj_item = {}  # por fila

                    detalle_stock = frappe.db.get_value('Item', {'name': dat_items[i]['item_code']}, 'is_stock_item')
                    # Validacion de Bien o Servicio, en base a detalle de stock
                    if (int(detalle_stock) == 0):
                        obj_item["@BienOServicio"] = 'S'

                    if (int(detalle_stock) == 1):
                        obj_item["@BienOServicio"] = 'B'

                    # Calculo precio unitario
                    precio_uni = 0
                    precio_uni = float(dat_items[i]['rate']) + float(dat_items[i]['price_list_rate'] - dat_items[i]['rate'])

                    # Calculo precio item
                    precio_item = 0
                    precio_item = float(dat_items[i]['qty']) * float(dat_items[i]['price_list_rate'])

                    # Calculo descuento item
                    desc_item = 0
                    desc_item = float(dat_items[i]['price_list_rate'] * dat_items[i]['qty']) - float(dat_items[i]['amount'])

                    contador += 1
                    obj_item["@NumeroLinea"] = contador
                    obj_item["dte:Cantidad"] = float(dat_items[i]['qty'])
                    obj_item["dte:UnidadMedida"] = dat_items[i]['facelec_three_digit_uom_code']
                    obj_item["dte:Descripcion"] = dat_items[i]['description']
                    obj_item["dte:PrecioUnitario"] = precio_uni
                    obj_item["dte:Precio"] = precio_item
                    obj_item["dte:Descuento"] = desc_item

                    # Agregamos los impuestos
                    # Obtenemos los impuesto cofigurados para x compañia en la factura
                    taxes_fact = frappe.db.get_values('Sales Taxes and Charges', filters={'parent': self.__invoice_code},
                                                      fieldname=['tax_name', 'taxable_unit_code'], as_dict=True)
                    obj_item["dte:Impuestos"] = {}
                    obj_item["dte:Impuestos"]["dte:Impuesto"] = {}

                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:NombreCorto"] = 'IVA'
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:CodigoUnidadGravable"] = '1'
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoGravable"] = '{0:.2f}'.format(float(dat_items[i]['net_amount']))
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoImpuesto"] = '{0:.2f}'.format(float(dat_items[i]['net_amount']) * 0.12)

                    obj_item["dte:Total"] = '{0:.2f}'.format((float(dat_items[i]['amount'])))
                    # obj_item["dte:Total"] = '{0:.2f}'.format((float(dat_items[i]['price_list_rate']) - float((dat_items[i]['price_list_rate'] - dat_items[i]['rate']) * dat_items[i]['qty'])))

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
                obj_item["dte:Cantidad"] = float(dat_items[0]['qty'])
                obj_item["dte:UnidadMedida"] = dat_items[0]['facelec_three_digit_uom_code']
                obj_item["dte:Descripcion"] = dat_items[0]['description']
                obj_item["dte:PrecioUnitario"] = float(dat_items[0]['rate']) + float(dat_items[0]['price_list_rate'] - dat_items[0]['rate'])
                obj_item["dte:Precio"] = float(dat_items[0]['qty']) * float(dat_items[0]['price_list_rate']) #float(dat_items[0]['amount']) + float(dat_items[0]['price_list_rate'] - dat_items[0]['rate'])
                obj_item["dte:Descuento"] = float(dat_items[0]['price_list_rate'] * dat_items[0]['qty']) - float(dat_items[0]['amount'])
                obj_item["dte:Impuestos"] = {}
                obj_item["dte:Impuestos"]["dte:Impuesto"] = {}

                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:NombreCorto"] = 'IVA'
                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:CodigoUnidadGravable"] = '1'
                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoGravable"] = '{0:.2f}'.format(float(dat_items[0]['net_amount'])) #'{0:.2f}'.format((float(dat_items[0]['facelec_gt_tax_net_fuel_amt']) + float(dat_items[0]['facelec_gt_tax_net_goods_amt']) + float(dat_items[0]['facelec_gt_tax_net_services_amt']))) #- float(dat_items[0]['discount_amount'])) # precio - descuento/1.12
                obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoImpuesto"] = '{0:.2f}'.format(float(dat_items[0]['net_amount']) * 0.12) #'{0:.2f}'.format(float(dat_items[0]['facelec_sales_tax_for_this_row']))

                obj_item["dte:Total"] = '{0:.2f}'.format((float(dat_items[0]['amount']))) # - float(dat_items[0]['discount_amount'])) # Se suma otros impuestos + float(dat_items[0]['facelec_sales_tax_for_this_row'])
                # obj_item["dte:Total"] = '{0:.2f}'.format((float(dat_items[0]['price_list_rate']) - float((dat_items[0]['price_list_rate'] - dat_items[0]['rate']) * dat_items[0]['qty'])))

                items_ok.append(obj_item)

            i_fel = {"dte:Item": items_ok}
            self.__d_items = i_fel

        except:
            return 'No se pudo obtener data de los items en la factura {}, Error: {}'.format(self.serie_factura, str(frappe.get_traceback()))
        else:
            return True

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
