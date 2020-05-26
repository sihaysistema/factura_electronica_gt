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

    def build_invoice(self):
        try:
            # 1 Validamos la data antes de construir
            status_validate = self.validate()

            if status_validate[0] == True:
                # 2 - Asignacion y creacion base peticion para luego ser convertida a XML
                self.__base_peticion = {
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
                                    "dte:DatosGenerales": self.__d_general,
                                    "dte:Emisor": self.__d_emisor,
                                    "dte:Receptor": self.__d_receptor,
                                    "dte:Frases": self.__d_frases,
                                    "dte:Items": self.__d_items,
                                    "dte:Totales": self.__d_totales
                                }
                            }
                        }
                    }
                }

                with open('mi_factura.json', 'w') as f:
                    f.write(json.dumps(self.__base_peticion))
                return True,'OK'
            else:
                return False, status_validate[1]
        except:
            return False, str(frappe.get_traceback())

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
        status_items = self.items()
        if status_items == False:
            return status_items

        # Validacion y generacion seccion totales
        status_totals = self.totals()
        if status_totals == False:
            return status_totals

        # Si todo va bien, retorna True
        return True, 'OK'

    def general_data(self):
        """
        Construye la seccion datos generales que incluye, codigo de moneda, Fecha y Hora de emision
        Tipo de factura

        Returns:
            tuple: Primera posicion True/False, Segunda posicion descripcion msj
        """

        try:
            self.__d_general = {
                "@CodigoMoneda": frappe.db.get_value('Sales Invoice', {'name': self.__invoice_code}, 'currency'),
                "@FechaHoraEmision": str(datetime.datetime.now().replace(microsecond=0).isoformat()),  # "2018-11-01T16:33:47Z",
                "@Tipo": frappe.db.get_value('Configuracion Series FEL', {'parent': self.__config_name}, 'tipo_documento')  # 'FACT'  #self.serie_facelec_fel TODO: Poder usar todas las disponibles
            }

            return True, 'OK'

        except:
            return False, f'Error en obtener data para datos generales mas detalles en :\n {str(frappe.get_traceback())}'

    def sender(self):
        """
        Valida y obtiene la data necesaria para la seccion de Emisor

        Returns:
            str: Descripcion con el status de la trasaccion
        """
        try:
            # De la factura obtenemos la compañia y direccion compañia emisora
            self.dat_fac = frappe.db.get_values('Sales Invoice', filters={'name': self.__invoice_code},
                                                fieldname=['company', 'company_address', 'nit_face_customer',
                                                           'customer_address', 'customer_name', 'total_taxes_and_charges',
                                                           'grand_total'], as_dict=1)
            if len(self.dat_fac) == 0:
                return False, f'''No se encontro ninguna factura con serie: {self.__invoice_code}.\
                                  Por favor valida los datos de la factura que deseas procesar'''


            # Obtenemos datos necesario de company: Nombre de compañia, nit
            dat_compania = frappe.db.get_values('Company', filters={'name': self.dat_fac[0]['company']},
                                                fieldname=['company_name', 'nit_face_company', 'tax_id'],
                                                as_dict=1)
            if len(dat_compania) == 0:
                return False, f'''No se encontraron datos para la compañia {self.dat_fac[0]["company_name"]}.
                                  Verifica que la factura que deseas procesar tenga una compañia valida'''


            # De la compañia, obtenemos direccion 1, email, codigo postal, departamento, municipio, pais
            dat_direccion = frappe.db.get_values('Address', filters={'name': self.dat_fac[0]['company_address']},
                                                 fieldname=['address_line1', 'email_id', 'pincode',
                                                            'state', 'city', 'country'], as_dict=1)
            if len(dat_direccion) == 0:
                return False, f'No se encontro ninguna direccion de la compania {dat_compania[0]["company_name"]},\
                                verifica que exista una con data en los campos address_line1, email_id, pincode, state,\
                                city, country, y vuelve a generar la factura'


            # Validacion de existencia en los campos de direccion, ya que son obligatorio por parte de la API FEL
            # Usaremos la primera que se encuentre
            for dire in dat_direccion[0]:
                if dat_direccion[0][dire] is None or dat_direccion[0][dire] is '':
                    return False, '''No se puede completar la operacion ya que el campo {} de la direccion de compania no\
                                     tiene data, por favor asignarle un valor e intentar de nuevo'''.format(str(dire))

            # Asignacion data
            self.__d_emisor = {
                "@AfiliacionIVA": frappe.db.get_value('Configuracion Factura Electronica',
                                                     {'name': self.__config_name}, 'afiliacion_iva'),
                "@CodigoEstablecimiento": frappe.db.get_value('Configuracion Factura Electronica',
                                                             {'name': self.__config_name}, 'codigo_establecimiento'),  #"1",
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

            return True, 'OK'

        except:
            return False, 'Proceso no completado, no se pudieron obtener todos los datos necesarios, verifica tener todos\
                           los campos necesario en Configuracion Factura Electronica. Mas detalles en: \n'+str(frappe.get_traceback())

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
                return False, f'''No se encontro ninguna direccion para el cliente {self.dat_fac[0]["customer_name"]}.\
                                  Por favor asigna un direccion y vuelve a intentarlo'''

            # Validacion data direccion cliente
            for dire in dat_direccion[0]:
                if dat_direccion[0][dire] is None or dat_direccion[0][dire] is '':
                    return False, '''No se puede completar la operacion ya que el campo {} de la direccion del cliente {} no\
                                     tiene data, por favor asignarle un valor e intentar de nuevo'''.format(str(dire), self.dat_fac[0]["customer_name"])


            # Si es consumidor Final: para generar factura electronica obligatoriamente se debe asignar un correo
            # electronico, los demas campos se pueden dejar como defualt para ciudad
            if str(self.dat_fac[0]['nit_face_customer']).upper() == 'C/F':
                self.__d_receptor = {
                    "@CorreoReceptor": dat_direccion[0]['email_id'],
                    "@IDReceptor": (self.dat_fac[0]['nit_face_customer']).replace('/', ''),  # NIT => CF
                    "@NombreReceptor": str(self.dat_fac[0]["customer_name"]),
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
                    "@IDReceptor": str(self.dat_fac[0]['nit_face_customer']).replace('-', ''),  # NIT
                    "@NombreReceptor": str(self.dat_fac[0]["customer_name"]),
                    "dte:DireccionReceptor": {
                        "dte:Direccion": dat_direccion[0]['address_line1'],
                        "dte:CodigoPostal": dat_direccion[0]['pincode'],
                        "dte:Municipio": dat_direccion[0]['state'],
                        "dte:Departamento": dat_direccion[0]['city'],
                        "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion[0]['country']}, 'code').upper()
                    }
                }

            return True, 'OK'

        except:
            return False, 'Error no se puede completar la operacion por: '+str(frappe.get_traceback())

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

            return True, 'OK'

        except:
            return False, 'Error, no se puedo obtener valor de Codigo Escenario y Tipo Frase'

    def items(self):
        try:
            i_fel = {}  # Guardara la seccion de items ok
            items_ok = []  # Guardara todos los items OK

            # Obtenemos los items de la factura
            self.__dat_items = frappe.db.get_values('Sales Invoice Item', filters={'parent': str(self.__invoice_code)},
                                             fieldname=['item_name', 'qty', 'item_code', 'description',
                                                        'net_amount', 'base_net_amount', 'discount_percentage',
                                                        'discount_amount', 'price_list_rate', 'net_rate',
                                                        'stock_uom', 'serial_no', 'item_group', 'rate',
                                                        'amount', 'facelec_sales_tax_for_this_row',
                                                        'facelec_amount_minus_excise_tax',
                                                        'facelec_other_tax_amount', 'facelec_three_digit_uom_code',
                                                        'facelec_gt_tax_net_fuel_amt', 'facelec_gt_tax_net_goods_amt',
                                                        'facelec_gt_tax_net_services_amt'], as_dict=True)

            # TODO VER ESCENARIO CUANDO HAY MAS DE UN IMPUESTO?????
            # TODO VER ESCENARIO CUANDO NO HAY IMPUESTOS, ES POSIBLE???
            # Obtenemos los impuesto cofigurados para x compañia en la factura
            self.__taxes_fact = frappe.db.get_values('Sales Taxes and Charges', filters={'parent': self.__invoice_code},
                                                     fieldname=['tax_name', 'taxable_unit_code', 'rate'], as_dict=True)

            # Verificamos la cantidad de items
            longitems = len(self.__dat_items)

            if longitems != 0:
                contador = 0  # Utilizado para enumerar las lineas en factura electronica

                # Si existe un solo item a facturar la iteracion se hara una vez, si hay mas lo contrario mas iteraciones
                for i in range(0, longitems):
                    obj_item = {}  # por fila

                    detalle_stock = frappe.db.get_value('Item', {'name': self.__dat_items[i]['item_code']}, 'is_stock_item')
                    # Validacion de Bien o Servicio, en base a detalle de stock
                    if (int(detalle_stock) == 0):
                        obj_item["@BienOServicio"] = 'S'

                    if (int(detalle_stock) == 1):
                        obj_item["@BienOServicio"] = 'B'

                    # Calculo precio unitario
                    precio_uni = 0
                    precio_uni = float(self.__dat_items[i]['rate']) + float(self.__dat_items[i]['price_list_rate'] - self.__dat_items[i]['rate'])

                    # Calculo precio item
                    precio_item = 0
                    precio_item = float(self.__dat_items[i]['qty']) * float(self.__dat_items[i]['price_list_rate'])

                    # Calculo descuento item
                    desc_item = 0
                    desc_item = float(self.__dat_items[i]['price_list_rate'] * self.__dat_items[i]['qty']) - float(self.__dat_items[i]['amount'])

                    contador += 1
                    obj_item["@NumeroLinea"] = contador
                    obj_item["dte:Cantidad"] = float(self.__dat_items[i]['qty'])
                    obj_item["dte:UnidadMedida"] = self.__dat_items[i]['facelec_three_digit_uom_code']
                    obj_item["dte:Descripcion"] = self.__dat_items[i]['description']
                    obj_item["dte:PrecioUnitario"] = precio_uni
                    obj_item["dte:Precio"] = precio_item
                    obj_item["dte:Descuento"] = desc_item

                    # Agregamos los impuestos
                    obj_item["dte:Impuestos"] = {}
                    obj_item["dte:Impuestos"]["dte:Impuesto"] = {}

                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:NombreCorto"] = self.__taxes_fact[0]['tax_name']
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:CodigoUnidadGravable"] = self.__taxes_fact[0]['taxable_unit_code']
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoGravable"] = '{0:.2f}'.format(float(self.__dat_items[i]['net_amount']))
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoImpuesto"] = '{0:.2f}'.format(float(self.__dat_items[i]['net_amount']) *
                                                                                                      float(self.__taxes_fact[0]['rate']/100))

                    obj_item["dte:Total"] = '{0:.2f}'.format((float(self.__dat_items[i]['amount'])))
                    # obj_item["dte:Total"] = '{0:.2f}'.format((float(self.__dat_items[i]['price_list_rate']) - float((self.__dat_items[i]['price_list_rate'] - self.__dat_items[i]['rate']) * self.__dat_items[i]['qty'])))

                    items_ok.append(obj_item)


            i_fel = {"dte:Item": items_ok}
            self.__d_items = i_fel

            return True, 'OK'

        except:
            return False, 'No se pudo obtener data de los items en la factura {}, Error: {}'.format(self.serie_factura, str(frappe.get_traceback()))

    def totals(self):
        '''Funcion encargada de realizar totales de los impuestos sobre la factura'''
        try:
            gran_tot = 0
            for i in self.__dat_items:
                gran_tot += i['facelec_amount_minus_excise_tax']

            self.__d_totales = {
                "dte:TotalImpuestos": {
                    "dte:TotalImpuesto": {
                        "@NombreCorto": "IVA",
                        "@TotalMontoImpuesto": '{0:.2f}'.format(float(self.dat_fac[0]['total_taxes_and_charges']))
                    }
                },
                "dte:GranTotal": '{0:.2f}'.format(float(self.dat_fac[0]['grand_total']))
            }

            return True, 'OK'

        except:
            return False, 'No se pudo obtener data de la factura {}, Error: {}'.format(self.serie_factura, str(frappe.get_traceback()))

    def sign_invoice(self):
        '''Funcion encargada de solicitar firma para archivo XML '''

        try:
            # To XML: Convierte de JSON a XML indentado
            self.__xml_string = xmltodict.unparse(self.__base_peticion, pretty=True)
            # Usar solo para debug
            with open('mi_factura.xml', 'w') as f:
                f.write(self.__xml_string)

        except:
            return False, 'La peticion no se pudo convertir a XML. Si la falla persiste comunicarse con soporte'

        try:
            # To base64: Convierte a base64, para enviarlo en la peticion
            self.__encoded_bytes = base64.b64encode(self.__xml_string.encode("utf-8"))
            self.__encoded_str = str(self.__encoded_bytes, "utf-8")
            # Usar solo para debug
            with open('codificado.txt', 'w') as f:
                    f.write(self.__encoded_str)
        except:
            return False, 'La peticio no se pudo codificar. Si la falla persiste comunicarse con soporte'


        # Generamos la peticion para firmar
        try:
            url = frappe.db.get_value('Configuracion Factura Electronica',
                                     {'name': self.__config_name}, 'url_firma')

            codigo = frappe.db.get_value('Configuracion Factura Electronica',
                                        {'name': self.__config_name}, 'codigo')

            alias = frappe.db.get_value('Configuracion Factura Electronica',
                                       {'name': self.__config_name}, 'alias')

            anulacion = frappe.db.get_value('Configuracion Factura Electronica',
                                           {'name': self.__config_name}, 'es_anulacion')

            self.__llave = frappe.db.get_value('Configuracion Factura Electronica',
                                              {'name': self.__config_name}, 'llave_pfx')

            self.__data_a_firmar = {
                "llave": self.__llave, # LLAVE
                "archivo": str(self.__encoded_str),  # En base64
                # "codigo": codigo, # Número interno de cada transacción
                "alias":  alias, # USUARIO
                "es_anulacion": anulacion # "N" si es certificacion y "S" si es anulacion
            }

            headers = {"content-type": "application/json"}
            response = requests.post(url, data=json.dumps(self.__data_a_firmar), headers=headers)

            return True, (response.content).decode('utf-8')

        except:
            return False, 'Error al tratar de firmar el documento electronico: '+str(frappe.get_traceback())

    # def request_electronic_invoice(self):
    #     '''Funcion encargada de solicitar factura electronica al WS de INFILE'''
    #     try:
    #         data_fac = frappe.db.get_value('Sales Invoice', {'name': self.serie_factura}, 'company')
    #         nit_company = frappe.db.get_value('Company', {'name': data_fac}, 'nit_face_company')

    #         url = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config}, 'url_dte')
    #         user = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config}, 'alias')
    #         llave = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config}, 'llave_ws')
    #         correo_copia = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.nombre_config}, 'correo_copia')
    #         ident = self.serie_factura

    #         req_dte = {
    #             "nit_emisor": nit_company,
    #             "correo_copia": correo_copia,  # "m.monroyc22@gmail.com",
    #             "xml_dte": firmado["archivo"]
    #         }

    #         headers = {
    #             "content-type": "application/json",
    #             "usuario": user,
    #             "llave": llave,
    #             "identificador": ident
    #         }
    #         response = requests.post(url, data=json.dumps(req_dte), headers=headers)
    #     except:
    #         return False, 'Error al tratar de generar factura electronica: '+str(frappe.get_traceback())
    #     else:
    #         return True, (response.content).decode('utf-8')

    # def response_validator(self):
    #     pass

    # def save_answers(self):
    #     pass

    # def upgrade_records(self):
    #     pass

    # def save_deliveries(self):
    #     pass

    # def send_email(self):
    #     pass