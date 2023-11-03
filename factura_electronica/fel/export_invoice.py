# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import base64
import datetime

from frappe.utils import get_datetime, nowdate, nowtime
import json

import requests
import xmltodict

import frappe
from frappe import _, _dict
from frappe.utils import cint, flt

from factura_electronica.utils.utilities_facelec import get_currency_precision, remove_html_tags


class ExportInvoice:
    def __init__(self, invoice_code, conf_name, naming_series):
        """__init__
        Constructor de la clase, las propiedades iniciadas como privadas

        Args:
            invoice_code (str): Serie origianl de la factura
            conf_name (str): Nombre configuracion para factura electronica
        """
        self.__invoice_code = invoice_code
        self.__config_name = conf_name
        self.__naming_serie = naming_series
        self.__log_error = []
        self.__precision = get_currency_precision()

    def build_invoice(self):
        """
        Valida las dependencias necesarias, para construir XML desde un JSON,
        para ser firmado certificado por la SAT y finalmente generar factura electronica exportacion

        Returns:
            tuple: True/False, msj, msj
        """

        try:
            # 1 Validamos la data antes de construir
            status_validate = self.validate()

            if status_validate[0] == True:
                # 2 - Asignacion y creacion base peticion para luego ser convertida a XML
                self.__base_peticion = {
                    "dte:GTDocumento": {
                        "@xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
                        "@xmlns:dte": "http://www.sat.gob.gt/dte/fel/0.2.0",
                        "@xmlns:n1": "http://www.altova.com/samplexml/other-namespace",
                        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                        "@Version": "0.1",
                        "@xsi:schemaLocation": "http://www.sat.gob.gt/dte/fel/0.1.0 C:\\Users\\Nadir\\Desktop\\SAT_FEL_FINAL_V1\\Esquemas\\GT_Documento-0.1.0.xsd",
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
                                    "dte:Totales": self.__d_totales,
                                    "dte:Complementos": self.__complemento
                                }
                            }
                        }
                    }
                }

                # USAR SOLO PARA DEBUG:
                # with open('exportacion.json', 'w') as f:
                #     f.write(json.dumps(self.__base_peticion, indent=2))

                return True, 'OK'

            else:
                return False, status_validate[1]
        except:
            return False, str(frappe.get_traceback())

    def validate(self):
        """
        Funcion encargada de validar la data que construye la peticion a INFILE,
        Si existe por lo menos un error retornara la descripcion con dicho error

        Returns:
            tuple: True/False, msj, msj
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
        if status_phrases[0] == False:
            return status_phrases

        # Validacion y generacion seccion items
        status_items = self.items()
        if status_items[0] == False:
            return status_items

        # Validacion y generacion seccion totales
        status_totals = self.totals()
        if status_totals[0] == False:
            return status_totals

        # Validacion y generacion seccion complemento para exportacion
        status_complement = self.export_complement()
        if status_complement[0] == False:
            return status_complement

        # Si todo va bien, retorna True
        return True, 'OK'

    def general_data(self):
        """
        Construye la seccion datos generales que incluye, codigo de moneda, Fecha y Hora de emision
        Tipo de factura

        NOTA: LA FECHA Y HORA EMISION, SE GENERA CUANNDO PRESIONA EL BOTON

        Returns:
            tuple: Primera posicion True/False, Segunda posicion descripcion msj
        """

        try:
            opt_config = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'fecha_y_tiempo_documento_electronica')

            if opt_config == 'Fecha y tiempo de peticion a INFILE':
                ok_datetime = str(nowdate())+'T'+str(nowtime().rpartition('.')[0])

            else:
                date_invoice_inv = frappe.db.get_value('Sales Invoice', {'name': self.__invoice_code}, 'posting_date')
                ok_time = str(frappe.db.get_value('Sales Invoice', {'name': self.__invoice_code}, 'posting_time'))
                ok_datetime = str(date_invoice_inv)+'T'+str(datetime.datetime.strptime(ok_time.split('.')[0], "%H:%M:%S").time())

            self.__d_general = {
                "@CodigoMoneda": frappe.db.get_value('Sales Invoice', {'name': self.__invoice_code}, 'currency'),
                "@Exp": "SI",
                "@FechaHoraEmision": ok_datetime,
                "@Tipo": frappe.db.get_value('Configuracion Series FEL', {'parent': self.__config_name, 'serie': self.__naming_serie},
                                             'tipo_documento')
            }

            return True, 'OK'

        except:
            return False, f'Error en obtener data para datos generales mas detalles en :\n {str(frappe.get_traceback())}'

    def sender(self):
        """
        Valida y obtiene la data necesaria para la seccion de Emisor,
        entidad que emite la factura

        Returns:
            tuple: True/False, msj, msj
        """

        try:
            # De la factura obtenemos la compañia y direccion compañia emisora
            self.dat_fac = frappe.db.get_values('Sales Invoice', filters={'name': self.__invoice_code},
                                                fieldname=['company', 'company_address', 'nit_face_customer',
                                                           'customer_address', 'customer_name', 'total_taxes_and_charges',
                                                           'grand_total', 'customer'], as_dict=1)
            if len(self.dat_fac) == 0:
                return False, f'''No se encontro ninguna factura con serie: {self.__invoice_code}.\
                                  Por favor valida los datos de la factura que deseas procesar'''

            # Obtenemos datos necesario de company: Nombre de compañia, nit
            dat_compania = frappe.db.get_values('Company', filters={'name': self.dat_fac[0]['company']},
                                                fieldname=['company_name', 'nit_face_company', 'tax_id', 'codigo_exportador'],
                                                as_dict=1)
            if len(dat_compania) == 0:
                return False, f'''No se encontraron datos para la compañia {self.dat_fac[0]["company_name"]}.
                                  Verifica que la factura que deseas procesar tenga una compañia valida'''

            # De la compañia, obtenemos direccion 1, email, codigo postal, departamento, municipio, pais
            dat_direccion = frappe.db.get_values('Address', filters={'name': self.dat_fac[0]['company_address']},
                                                 fieldname=['address_line1', 'email_id', 'pincode', 'county',
                                                            'state', 'city', 'country', 'facelec_establishment'],
                                                 as_dict=1)
            if len(dat_direccion) == 0:
                return False, f'No se encontro ninguna direccion de la compania {dat_compania[0]["company_name"]},\
                                verifica que exista una, con data en los campos address_line1, email_id, pincode, state,\
                                city, country, y vuelve a generar la factura'

            # LA ENTIDAD EMISORA SI O SI DEBE TENER ESTOS DATOS :D
            # Validacion de existencia en los campos de direccion, ya que son obligatorio por parte de la API FEL
            # Usaremos la primera que se encuentre
            for dire in dat_direccion[0]:
                if not dat_direccion[0][dire]:
                    return False, '''No se puede completar la operacion ya que el campo {} de la direccion de compania no\
                                     tiene data, por favor asignarle un valor e intentar de nuevo'''.format(str(dire))

            # Si en configuracion de factura electronica esta seleccionada la opcion de usar datos de prueba
            if frappe.db.get_value('Configuracion Factura Electronica',
                                   {'name': self.__config_name}, 'usar_datos_prueba') == 1:
                nom_comercial = frappe.db.get_value('Configuracion Factura Electronica',
                                                    {'name': self.__config_name}, 'nombre_empresa_prueba')

                # Si la compania es de un propietario
                if frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'is_individual'):
                    nombre_emisor = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'facelec_name_of_owner')
                else:
                    nombre_emisor = nom_comercial

            # Aplica Si los datos son para producción
            else:
                nom_comercial = dat_compania[0]['company_name']

                # Si la compania es de un propietario
                if frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'is_individual'):
                    nombre_emisor = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'facelec_name_of_owner')
                else:
                    nombre_emisor = dat_compania[0]['company_name']

            # Asignacion data
            self.__d_emisor = {
                "@AfiliacionIVA": frappe.db.get_value('Configuracion Factura Electronica',
                                                      {'name': self.__config_name}, 'afiliacion_iva'),
                "@CodigoEstablecimiento": dat_direccion[0]['facelec_establishment'],
                "@CorreoEmisor": dat_direccion[0]['email_id'],
                "@NITEmisor": dat_compania[0]['nit_face_company'],
                "@NombreComercial": nom_comercial,
                "@NombreEmisor": nombre_emisor,
                "dte:DireccionEmisor": {
                    "dte:Direccion": dat_direccion[0]['address_line1'],
                    # Codig postal
                    "dte:CodigoPostal": dat_direccion[0]['pincode'],
                    "dte:Municipio": dat_direccion[0]['county'],  # Municipio
                    # Departamento
                    "dte:Departamento": dat_direccion[0]['state'],
                    # CODIG PAIS
                    "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion[0]['country']}, 'code').upper()
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
            tuple: True/False, msj, msj
        """

        # Intentara obtener data de direccion cliente
        try:
            dat_direccion = frappe.db.get_values('Address', filters={'name': self.dat_fac[0]['customer_address']},
                                                 fieldname=['address_line1', 'email_id', 'pincode', 'county',
                                                            'state', 'city', 'country'], as_dict=1)

            datos_default = {
                'email': frappe.db.get_value('Configuracion Factura Electronica',  {'name': self.__config_name}, 'correo_copia'),
                'customer_name': 'Consumidor Final',
                'address': 'Guatemala',
                'pincode': '0',
                'municipio': 'Guatemala',
                'departamento': 'Guatemala',
                'pais': 'GT'
            }

            if len(dat_direccion) == 0:  # Si no hay direccion registrada
                datos_default = {
                    'email': frappe.db.get_value('Configuracion Factura Electronica',  {'name': self.__config_name}, 'correo_copia'),
                    'customer_name': 'Consumidor Final',
                    'address': 'Guatemala',
                    'pincode': '0',
                    'municipio': 'Guatemala',
                    'departamento': 'Guatemala',
                    'pais': 'GT'
                }

                # Si es consumidor Final: para generar factura electronica obligatoriamente se debe asignar un correo
                # electronico, los demas campos se pueden dejar como defualt para ciudad
                if str(self.dat_fac[0]['nit_face_customer']).upper() == 'C/F':
                    self.__d_receptor = {
                        "@CorreoReceptor": datos_default.get('email'),
                        # NIT => CF
                        "@IDReceptor": str(self.dat_fac[0]['nit_face_customer']), #(self.dat_fac[0]['nit_face_customer']).replace('/', ''),
                        "@NombreReceptor": str(self.dat_fac[0]["customer_name"]),
                        "@TipoEspecial": str('EXT'), 
                        "dte:DireccionReceptor": {
                            "dte:Direccion": datos_default.get('address'),
                            "dte:CodigoPostal": datos_default.get('pincode'),
                            "dte:Municipio": datos_default.get('municipio'),
                            "dte:Departamento": datos_default.get('departamento'),
                            "dte:Pais": datos_default.get('pais')
                        }
                    }
                else:
                    self.__d_receptor = {
                        "@CorreoReceptor": datos_default.get('email'),
                        # NIT
                        "@IDReceptor": str(self.dat_fac[0]['nit_face_customer']),  # str(self.dat_fac[0]['nit_face_customer']).replace('-', ''),
                        "@NombreReceptor": str(self.dat_fac[0]["customer_name"]),
                        "@TipoEspecial": str('EXT'), 
                        "dte:DireccionReceptor": {
                            "dte:Direccion": datos_default.get('address'),
                            "dte:CodigoPostal": datos_default.get('pincode'),
                            "dte:Municipio": datos_default.get('municipio'),
                            "dte:Departamento": datos_default.get('departamento'),
                            "dte:Pais": datos_default.get('pais')
                        }
                    }

            else:
                # Si es consumidor Final: para generar factura electronica obligatoriamente se debe asignar un correo
                # electronico, los demas campos se pueden dejar como defualt para ciudad
                if str(self.dat_fac[0]['nit_face_customer']).upper() == 'C/F':
                    self.__d_receptor = {
                        "@CorreoReceptor": dat_direccion[0].get('email_id', datos_default.get('email')),
                        # NIT => CF
                        "@IDReceptor": str(self.dat_fac[0]['nit_face_customer']),  # (self.dat_fac[0]['nit_face_customer']).replace('/', ''),
                        "@NombreReceptor": str(self.dat_fac[0]["customer_name"]),
                        "@TipoEspecial": str('EXT'), 
                        "dte:DireccionReceptor": {
                            "dte:Direccion": dat_direccion[0].get('address_line1', datos_default.get('address')),
                            "dte:CodigoPostal": dat_direccion[0].get('pincode', datos_default.get('pincode')),
                            "dte:Municipio": dat_direccion[0].get('county', datos_default.get('municipio')),
                            "dte:Departamento": dat_direccion[0].get('state', datos_default.get('departamento')),
                            "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion[0]['country']}, 'code').upper() or 'GT'
                        }
                    }
                else:
                    self.__d_receptor = {
                        "@CorreoReceptor": dat_direccion[0].get('email_id', datos_default.get('email')),
                        # NIT
                        "@IDReceptor": str(self.dat_fac[0]['nit_face_customer']),  # str(self.dat_fac[0]['nit_face_customer']).replace('-', ''),
                        "@NombreReceptor": str(self.dat_fac[0]["customer_name"]),
                        "@TipoEspecial": str('EXT'), 
                        "dte:DireccionReceptor": {
                            "dte:Direccion": dat_direccion[0].get('address_line1', datos_default.get('address')),
                            "dte:CodigoPostal": dat_direccion[0].get('pincode', datos_default.get('pincode')),
                            "dte:Municipio": dat_direccion[0].get('county', datos_default.get('municipio')),
                            "dte:Departamento": dat_direccion[0].get('state', datos_default.get('departamento')),
                            "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion[0]['country']}, 'code').upper() or 'GT'
                        }
                    }

            return True, 'OK'

        except:
            return False, 'Error no se puede completar la operacion por: '+str(frappe.get_traceback())

    def phrases(self):
        """
        debe indicarse los regímenes y textos especiales que son requeridos en los DTE,
        de acuerdo a la afiliación del contribuyente y tipo de operación.

        La primer combinacion hace referencia a lo que se usaria en una generacion normal
        La segunda combinacion hace refenrecia que esta exento de impuesto

        Returns:
            boolean: True/False
        """
        # NOTA: La primer frase es la normal que se utilizaria en un factura
        # La segunda frase hace referencia a que realizara una expotracion, y esta se encuentra exenta de impuesto
        # funcionara solo si la compañia esta registrada para dichos tramites de lo contrario FEL no se procesara

        try:
            # Obtiene el nombre de la combinacion configurada para la serie
            combination_name = frappe.db.get_value('Configuracion Series FEL',
                                                   {'parent': self.__config_name,
                                                    'serie': self.__naming_serie}, 'combination_of_phrases')

            # Obtiene las combinaciones de frases a usar en la factura
            phrases_to_doc = frappe.db.get_values('FEL Combinations', filters={'parent': combination_name},
                                                  fieldname=['tipo_frase', 'codigo_de_escenario'], as_dict=1)

            if not phrases_to_doc:
                return False, 'Ocurrio un problema, no se encontro ninguna combinación de frases para generar la factura \
                              por favor cree una y configurela en Configuración Factura Electrónica'

            # Si hay mas de una frase
            if len(phrases_to_doc) > 1:
                self.__d_frases = {
                    "dte:Frase": []
                }

                for f in phrases_to_doc:
                    self.__d_frases["dte:Frase"].append({
                        "@CodigoEscenario": f.get("codigo_de_escenario"),
                        "@TipoFrase": f.get("tipo_frase")[:1]
                    })
            # Si solo hay una frase
            else:
                self.__d_frases = {
                    "dte:Frase": {
                        "@CodigoEscenario": phrases_to_doc[0].get("codigo_de_escenario"),
                        "@TipoFrase": phrases_to_doc[0].get("tipo_frase")[:1]
                    }
                }

            return True, 'OK'

        except:
            return False, 'Ocurrio un problema, no se pudo obtener valor de Codigo Escenario y Tipo Frase para factura exportacion \
                          , por favor configurarla en Configuracion Factura Electronica e intentar de nuevo'

    def items(self):
        """
        Procesa todos los items de la factura aplicando calculos necesarios para la SAT

        Returns:
            tuple: True/False, msj, msj
        """

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
                                                               'facelec_amount_minus_excise_tax', 'facelec_is_service',
                                                               'facelec_is_good', 'factelecis_fuel', 'facelec_si_is_exempt',
                                                               'facelec_other_tax_amount', 'facelec_three_digit_uom_code',
                                                               'facelec_gt_tax_net_fuel_amt', 'facelec_gt_tax_net_goods_amt',
                                                               'facelec_gt_tax_net_services_amt', 'facelec_is_discount'], order_by='idx asc', as_dict=True)

            switch_item_description = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'descripcion_item')

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

                    # detalle_stock = frappe.db.get_value('Item', {'name': self.__dat_items[i]['item_code']}, 'is_stock_item')
                    # # Validacion de Bien o Servicio, en base a detalle de stock
                    # if (int(detalle_stock) == 0):
                    #     obj_item["@BienOServicio"] = 'S'

                    # if (int(detalle_stock) == 1):
                    #     obj_item["@BienOServicio"] = 'B'

                    if cint(self.__dat_items[i]['facelec_is_service']) == 1:
                        obj_item["@BienOServicio"] = 'S'

                    elif cint(self.__dat_items[i]['facelec_is_good']) == 1:
                        obj_item["@BienOServicio"] = 'B'

                    elif cint(self.__dat_items[i]['factelecis_fuel']) == 1:
                        obj_item["@BienOServicio"] = 'B'
                        # apply_oil_tax = True

                    elif cint(self.__dat_items[i]['facelec_si_is_exempt']) == 1:
                        obj_item["@BienOServicio"] = 'B'

                    precio_uni = 0
                    precio_item = 0
                    desc_fila = 0

                    desc_item_fila = 0
                    if cint(self.__dat_items[i]['facelec_is_discount']) == 1:
                        desc_item_fila = self.__dat_items[i]['discount_amount']

                    # Precio unitario, (sin aplicarle descuento)
                    precio_uni = flt(self.__dat_items[i]['rate'] + desc_item_fila, self.__precision)

                    precio_item = flt(precio_uni * self.__dat_items[i]['qty'], self.__precision)

                    # Calculo descuento monto item
                    desc_fila = 0
                    desc_fila = flt(self.__dat_items[i]['qty'] * desc_item_fila, self.__precision)

                    contador += 1
                    description_to_item = self.__dat_items[i]['item_name'] if switch_item_description == "Nombre de Item" else self.__dat_items[i]['description']

                    obj_item["@NumeroLinea"] = contador
                    obj_item["dte:Cantidad"] = float(self.__dat_items[i]['qty'])
                    obj_item["dte:UnidadMedida"] = self.__dat_items[i]['facelec_three_digit_uom_code']
                    obj_item["dte:Descripcion"] = remove_html_tags(description_to_item)  #  self.__dat_items[i]['item_name']  # descrition
                    obj_item["dte:PrecioUnitario"] = flt(precio_uni, self.__precision)
                    obj_item["dte:Precio"] = flt(precio_item, self.__precision)
                    obj_item["dte:Descuento"] = flt(desc_fila, self.__precision)

                    # Agregamos los impuestos
                    obj_item["dte:Impuestos"] = {}
                    obj_item["dte:Impuestos"]["dte:Impuesto"] = {}

                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:NombreCorto"] = self.__taxes_fact[0]['tax_name']
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:CodigoUnidadGravable"] = self.__taxes_fact[0]['taxable_unit_code']
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoGravable"] = flt(self.__dat_items[i]['net_amount'], self.__precision)  # net_amount
                    obj_item["dte:Impuestos"]["dte:Impuesto"]["dte:MontoImpuesto"] = 0  # Como es exportacion, no aplica

                    obj_item["dte:Total"] = flt(self.__dat_items[i]['amount'], self.__precision)

                    items_ok.append(obj_item)

            i_fel = {"dte:Item": items_ok}
            self.__d_items = i_fel

            return True, 'OK'

        except:
            return False, 'No se pudo obtener data de los items en la factura {}, Error: {}'.format(self.serie_factura, str(frappe.get_traceback()))

    def totals(self):
        """
        Funcion encargada de realizar totales de los impuestos sobre la factura

        Returns:
            tuple: True/False, msj, msj
        """

        try:
            gran_tot = 0
            for i in self.__dat_items:
                gran_tot += i['facelec_amount_minus_excise_tax']

            self.__d_totales = {
                "dte:TotalImpuestos": {
                    "dte:TotalImpuesto": {
                        # "IVA",
                        "@NombreCorto": self.__taxes_fact[0]['tax_name'],
                        "@TotalMontoImpuesto": 0  # exportacion
                    }
                },
                "dte:GranTotal": flt(self.dat_fac[0]['grand_total'], self.__precision)
            }

            return True, 'OK'

        except:
            return False, 'No se pudo obtener data de la factura {}, Error: {}'.format(self.serie_factura, str(frappe.get_traceback()))

    def export_complement(self):
        """
        Metodo para construccion la seccion exportacion complemento

        Returns:
            tuple: True/False, msj, msj
        """
        try:
            # direccion receptor
            dat_direccion = frappe.db.get_values('Address', filters={'name': self.dat_fac[0]['customer_address']},
                                                 fieldname=['address_line1', 'email_id', 'pincode', 'county',
                                                            'state', 'city', 'country'], as_dict=1)

            dat_compania = frappe.db.get_values('Company', filters={'name': self.dat_fac[0]['company']},
                                                fieldname=['company_name', 'nit_face_company', 'tax_id', 'codigo_exportador'],
                                                as_dict=1)

            codigo_comprador = frappe.db.get_value('Customer', {'name': str(self.dat_fac[0]["customer"])}, 'codigo_comprador')
            codigo_consignatario_comprador = frappe.db.get_value('Customer', {'name': str(self.dat_fac[0]["customer"])}, 'codigo_consignatario_comprador')
            codigo_incoterm = frappe.db.get_value('Configuracion Series FEL', {'parent': self.__config_name, 'serie': self.__naming_serie},
                                                  'codigo_incoterm')

            codigo_exportador = dat_compania[0]['codigo_exportador']

            # Validaciones Direcciones
            if len(dat_direccion) == 0:
                return False, 'Complemento exportacion no generado, por favor agregar direccion de receptor, datos requeridos por INFILE'

            # Validaciones Codigo exportacion
            if not codigo_comprador:
                return False, 'Complemento exportacion no generado, por favor agregar codigo de comprador en Cliente'

            if not codigo_consignatario_comprador:
                return False, 'Complemento exportacion no generado, por favor agregar codigo consignatario de comprador en Cliente, \
                               si no tienes el dato puedes usar el mismo valor que codigo comprador'

            if not codigo_incoterm:
                return False, 'Complemento exportacion no generado, por favor agregar codigo INCOTERM en configuracion series Factura Electronica'

            if not codigo_exportador:
                return False, 'Complemento exportacion no generado, por favor agregar codigo de exportador en Compania'


            self.__complemento = {
                    "dte:Complemento": {
                    "@IDComplemento": "text",
                    "@NombreComplemento": "Complemento_Exportacion",
                    "@URIComplemento": "uri_complemento",
                    "cex:Exportacion": {
                        "@xmlns:cex": "http://www.sat.gob.gt/face2/ComplementoExportaciones/0.1.0",
                        "@Version": "1",
                        "@xsi:schemaLocation": "http://www.sat.gob.gt/face2/ComplementoExportaciones/0.1.0 C:\\Users\\Nadir\\Desktop\\SAT_FEL_FINAL_V1\\Esquemas\\GT_Complemento_Exportaciones-0.1.0.xsd",
                        "cex:NombreConsignatarioODestinatario": str(self.dat_fac[0]["customer_name"]),
                        "cex:DireccionConsignatarioODestinatario": str(dat_direccion[0].get('address_line1'))[:70],  # solo acepta 70 digitos
                        "cex:CodigoConsignatarioODestinatario": codigo_consignatario_comprador,
                        "cex:NombreComprador": str(self.dat_fac[0]["customer_name"]),
                        "cex:CodigoComprador": codigo_comprador,
                        "cex:OtraReferencia": "EXPORTACION",
                        "cex:INCOTERM": codigo_incoterm,
                        "cex:NombreExportador": dat_compania[0]['company_name'],
                        "cex:CodigoExportador": codigo_exportador
                    }
                }
            }

            return True, 'OK'

        except:
            return False, 'No se pudo generar el complemento para factura exportacion {}, Error: {}'.format(self.serie_factura, str(frappe.get_traceback()))

    def sign_invoice(self):
        """
        Funcion encargada de solicitar firma para archivo XML

        Returns:
            tuple: True/False, msj, msj
        """

        try:
            # To XML: Convierte de JSON a XML indentado
            self.__xml_string = xmltodict.unparse(self.__base_peticion, pretty=True)
            # Usar solo para debug
            with open('PREVIEW-FACT-EXPORTACION.xml', 'w') as f:
                f.write(self.__xml_string)

        except:
            return False, 'La peticion no se pudo convertir a XML. Si la falla persiste comunicarse con soporte'

        try:
            # To base64: Convierte a base64, para enviarlo en la peticion
            self.__encoded_bytes = base64.b64encode(self.__xml_string.encode("utf-8"))
            self.__encoded_str = str(self.__encoded_bytes, "utf-8")
            # Usar solo para debug
            # with open('codificado.txt', 'w') as f:
            #         f.write(self.__encoded_str)
        except:
            return False, 'La peticio no se pudo codificar. Si la falla persiste comunicarse con soporte'

        # Generamos la peticion para firmar
        try:
            url = frappe.db.get_value('Configuracion Factura Electronica',
                                      {'name': self.__config_name}, 'url_firma')

            # codigo = frappe.db.get_value('Configuracion Factura Electronica',
            #                             {'name': self.__config_name}, 'codigo')

            alias = frappe.db.get_value('Configuracion Factura Electronica',
                                        {'name': self.__config_name}, 'alias')

            anulacion = frappe.db.get_value('Configuracion Factura Electronica',
                                            {'name': self.__config_name}, 'es_anulacion')

            self.__llave = frappe.db.get_value('Configuracion Factura Electronica',
                                               {'name': self.__config_name}, 'llave_pfx')

            self.__data_a_firmar = {
                "llave": self.__llave,  # LLAVE
                "archivo": str(self.__encoded_str),  # En base64
                # "codigo": codigo, # Número interno de cada transacción
                "alias":  alias,  # USUARIO
                "es_anulacion": anulacion  # "N" si es certificacion y "S" si es anulacion
            }

            headers = {"content-type": "application/json"}
            response = requests.post(url, data=json.dumps(self.__data_a_firmar), headers=headers)

            # Guardamos en una variable privada la respuesta
            self.__doc_firmado = json.loads((response.content).decode('utf-8'))

            # Guardamos la respuesta en un archivo DEBUG
            # with open('resp_firmado_exportacion.json', 'w') as f:
            #     f.write(json.dumps(self.__doc_firmado, indent=2))

            # Si la respuesta es true
            if self.__doc_firmado.get('resultado') == True:
                # Guardamos en privado el documento firmado y encriptado
                self.__encrypted = self.__doc_firmado.get('archivo')

                # Retornamos el status del proceso
                return True, 'OK'

            else:  # Si ocurre un error retornamos la descripcion del error por INFILE
                return False, self.__doc_firmado.get('descripcion')

        except:
            return False, 'Error al tratar de firmar el documento electronico: '+str(frappe.get_traceback())

    def request_electronic_invoice(self):
        """
        Funcion encargada de solicitar factura electronica al Web Service de INFILE

        Returns:
            tuple: True/False, msj, msj
        """

        try:
            data_fac = frappe.db.get_value('Sales Invoice', {'name': self.__invoice_code}, 'company')
            nit_company = frappe.db.get_value('Company', {'name': self.dat_fac[0]['company']}, 'nit_face_company')

            url = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'url_dte')
            user = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'alias')
            llave = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'llave_ws')
            correo_copia = frappe.db.get_value('Configuracion Factura Electronica', {'name': self.__config_name}, 'correo_copia')
            ident = self.__invoice_code  # identificador

            req_dte = {
                "nit_emisor": nit_company,
                "correo_copia": correo_copia,  # "m.monroyc22@gmail.com",
                "xml_dte": self.__encrypted
            }

            headers = {
                "content-type": "application/json",
                "usuario": user,
                "llave": llave,
                "identificador": ident
            }

            # with open('peticion_fact_export.json', 'w') as f:
            #     f.write(json.dumps(req_dte, indent=2))

            self.__response = requests.post(url, data=json.dumps(req_dte), headers=headers)
            self.__response_ok = json.loads((self.__response.content).decode('utf-8'))

            # with open('response_fact_export.json', 'w') as f:
            #     f.write(json.dumps(self.__response_ok, indent=2))

            return True, 'OK'

        except:
            return False, 'Error al tratar de generar factura electronica: '+str(frappe.get_traceback())

    def response_validator(self):
        """
        Funcion encargada de verificar las respuestas de INFILE-SAT

        Returns:
            tuple: True/False, msj, msj
        """

        try:
            # Verifica que no existan errores
            if self.__response_ok['resultado'] == True and self.__response_ok['cantidad_errores'] == 0:
                # # Se encarga de guardar las respuestas de INFILE-SAT esto para llevar registro
                status_saved = self.save_answers()

                # Al primer error encontrado retornara un detalle con el mismo
                if status_saved == False:
                    return False, status_saved
                    # return {'status': 'ERROR', 'detalles_errores': status_saved, 'numero_errores':1}

                return True, {'status': 'OK', 'numero_autorizacion': self.__response_ok['uuid'],
                              'serie': self.__response_ok['serie'], 'numero': self.__response_ok['numero']}

            else:
                return False, {'status': 'ERROR', 'numero_errores': str(self.__response_ok['cantidad_errores']),
                               'detalles_errores': str(self.__response_ok['descripcion_errores'])}
        except:
            return False, {'status': 'ERROR VALIDACION', 'numero_errores': 1,
                           'detalles_errores': 'Error al tratar de validar la respuesta de INFILE-SAT: '+str(frappe.get_traceback())}

    def save_answers(self):
        """
        Funcion encargada guardar registro con respuestas de INFILE-SAT

        Returns:
            tuple: True/False, msj, msj
        """

        try:
            if not frappe.db.exists('Envio FEL', {'name': self.__response_ok['uuid']}):
                resp_fel = frappe.new_doc("Envio FEL")
                resp_fel.resultado = self.__response_ok['resultado']
                resp_fel.tipo_documento = 'Factura Exportacion'
                resp_fel.fecha = self.__response_ok['fecha']
                resp_fel.origen = self.__response_ok['origen']
                resp_fel.descripcion = self.__response_ok['descripcion']
                resp_fel.serie_factura_original = self.__invoice_code
                # resp_fel.serie_para_factura = 'FACELEC-'+str(self.__response_ok['numero'])
                resp_fel.serie_para_factura = str(self.__response_ok['serie']).replace('*', '')+str(self.__response_ok['numero'])

                if "control_emision" in self.__response_ok:
                    resp_fel.saldo = self.__response_ok['control_emision']['Saldo']
                    resp_fel.creditos = self.__response_ok['control_emision']['Creditos']

                resp_fel.alertas = self.__response_ok['alertas_infile']
                resp_fel.descripcion_alertas_infile = str(self.__response_ok['descripcion_alertas_infile'])
                resp_fel.alertas_sat = self.__response_ok['alertas_sat']
                resp_fel.descripcion_alertas_sat = str(self.__response_ok['descripcion_alertas_sat'])
                resp_fel.cantidad_errores = self.__response_ok['cantidad_errores']
                resp_fel.descripcion_errores = str(self.__response_ok['descripcion_errores'])

                if "informacion_adicional" in self.__response_ok:
                    resp_fel.informacion_adicional = self.__response_ok['informacion_adicional']

                resp_fel.uuid = self.__response_ok['uuid']
                resp_fel.serie = self.__response_ok['serie']
                resp_fel.numero = self.__response_ok['numero']

                decodedBytes = base64.b64decode(self.__response_ok['xml_certificado'])
                decodedStr = str(decodedBytes, "utf-8")
                resp_fel.xml_certificado = str(self.__xml_string)  # decodedStr

                resp_fel.save(ignore_permissions=True)

            return True, 'OK'

        except:
            return False, f'Error al tratar de guardar la rspuesta, para la factura {self.__invoice_code}, \
                            Mas detalles en {str(frappe.get_traceback())}'

    def upgrade_records(self):
        """
        Funcion encargada de actualizar todos los doctypes enlazados a la factura original, con
        la serie generada para factura electronica exportacion

        Returns:
            tuple: True/False, msj, msj
        """

        # Verifica que exista un documento en la tabla Envio FEL con el nombre de la serie original
        if frappe.db.exists('Envio FEL', {'serie_factura_original': self.__invoice_code}):
            factura_guardada = frappe.db.get_values('Envio FEL',filters={'serie_factura_original': self.__invoice_code},
                                                    fieldname=['numero', 'serie', 'uuid'], as_dict=1)
            # Esta seccion se encarga de actualizar la serie, con una nueva que es serie y numero
            # buscara en las tablas donde exista una coincidencia actualizando con la nueva serie
            # Se sustituye el * tomando en cuenta el server de pruebas FEL
            serie_sat = str(factura_guardada[0]['serie']).replace('*', '')
            # serieFEL = str('FACELEC-' + factura_guardada[0]['numero'])
            serieFEL = str(serie_sat + str(factura_guardada[0]['numero']))
            try:
                # serieFEL: guarda el numero DTE retornado por INFILE, se utilizara para reemplazar el nombre de la serie de la
                # factura que lo generó.
                # serieFEL = str(factura_guardada[0]['serie'] + '-' + factura_guardada[0]['numero'])
                # serie_fac_original: Guarda la serie original de la factura.
                serie_fac_original = self.__invoice_code

                # Actualizacion de tablas que son modificadas directamente.
                # 01 - tabSales Invoice: actualizacion con datos correctos
                frappe.db.sql('''UPDATE `tabSales Invoice`
                                 SET name=%(name)s,
                                    numero_autorizacion_fel=%(no_correcto)s,
                                    serie_original_del_documento=%(serie_orig_correcta)s
                                 WHERE name=%(serieFa)s
                              ''', {'name': serieFEL, 'no_correcto': factura_guardada[0]['uuid'],
                                    'serie_orig_correcta': serie_fac_original, 'serieFa': serie_fac_original})

                # 02 - tabSales Invoice Item: actualizacion items de la factura
                frappe.db.sql('''UPDATE `tabSales Invoice Item` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # 03 - tabGL Entry
                frappe.db.sql('''UPDATE `tabGL Entry` SET voucher_no=%(name)s, against_voucher=%(name)s
                                WHERE voucher_no=%(serieFa)s AND against_voucher=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                frappe.db.sql('''UPDATE `tabGL Entry` SET voucher_no=%(name)s, docstatus=1
                                WHERE voucher_no=%(serieFa)s AND against_voucher IS NULL''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Actualizacion de tablas que pueden ser modificadas desde Sales Invoice
                # Verificara tabla por tabla en busca de un valor existe, en caso sea verdadero actualizara,
                # en caso no encuentra nada y no hara nada
                # 04 - tabSales Taxes and Charges, actualizacion tablas de impuestos si existe
                if frappe.db.exists('Sales Taxes and Charges', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Taxes and Charges` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                if frappe.db.exists('Otros Impuestos Factura Electronica', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabOtros Impuestos Factura Electronica` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Pago programado, si existe
                # 05 - tabPayment Schedule
                if frappe.db.exists('Payment Schedule', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPayment Schedule` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # subscripcion, si existe
                # 06 - tabSubscription
                if frappe.db.exists('Subscription', {'reference_document': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSubscription` SET reference_document=%(name)s
                                    WHERE reference_document=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Entrada del libro mayor de inventarios, si existe
                # 07 - tabStock Ledger Entry
                if frappe.db.exists('Stock Ledger Entry', {'voucher_no': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabStock Ledger Entry` SET voucher_no=%(name)s
                                    WHERE voucher_no=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Hoja de tiempo de factura de ventas, si existe
                # 08 - tabSales Invoice Timesheet
                if frappe.db.exists('Sales Invoice Timesheet', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Invoice Timesheet` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Equipo Ventas, si existe
                # 09 - tabSales Team
                if frappe.db.exists('Sales Team', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Team` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Packed Item, si existe
                # 10 - tabPacked Item
                if frappe.db.exists('Packed Item', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPacked Item` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Sales Invoice Advance - Anticipos a facturas, si existe
                # 11 - tabSales Invoice Advance
                if frappe.db.exists('Sales Invoice Advance', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Invoice Advance` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Sales Invoice Payment - Pagos sobre a facturas, si existe
                # 12 - tabSales Invoice Payment
                if frappe.db.exists('Sales Invoice Payment', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Invoice Payment` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Payment Entry Reference -, si existe
                # 13 - tabPayment Entry Reference
                if frappe.db.exists('Payment Entry Reference', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Invoice Payment` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})
                    # FIXED
                    frappe.db.sql('''UPDATE `tabPayment Entry Reference` SET reference_name=%(name)s
                                    WHERE reference_name=%(serieFa)s''', {'name':serieFEL, 'serieFa':serie_fac_original})

                # Sales Order, si existe
                # 15 - tabSales Order
                if frappe.db.exists('Sales Order', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabSales Order` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Parece que este no enlaza directamente con sales invoice es el sales invoice que enlaza con este.
                # Delivery Note, si existe
                # 16 - tabDelivery Note
                if frappe.db.exists('Delivery Note', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabDelivery Note` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # JOURNAL ENTRY UPDATES
                if frappe.db.exists('Journal Entry Account', {'reference_name': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabJournal Entry Account` SET reference_name=%(name)s
                                    WHERE reference_name=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # UPDATE BATCH RECORDS OF INVOICES
                if frappe.db.exists('Batch Invoices', {'invoice': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabBatch Invoices` SET invoice=%(name)s, electronic_invoice_status="Generated"
                                    WHERE invoice=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # UPDATE RETENTIONS
                if frappe.db.exists('Tax Retention Guatemala', {'sales_invoice': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabTax Retention Guatemala` SET sales_invoice=%(name)s
                                     WHERE sales_invoice=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # UPDATE DECLARATIONS
                if frappe.db.exists('Invoice Declaration', {'link_name': serie_fac_original, 'link_doctype': 'Sales Invoice'}):
                    frappe.db.sql('''UPDATE `tabInvoice Declaration` SET link_name=%(name)s
                                     WHERE link_name=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                frappe.db.commit()

            except:
                # En caso exista un error al renombrar la factura retornara el mensaje con el error
                return False, f'Error al renombrar Factura. Por favor intente de nuevo presionando el boton Factura Electronica Exportacion \
                                mas informacion en el siguiente log: {frappe.get_traceback()}'

            else:
                # Si los datos se Guardan correctamente, se retornara la serie, que sera capturado por api.py
                # para luego ser capturado por javascript, se utilizara para recargar la url con los cambios correctos

                # Se utilizara el UUID como clave para orquestar el resto de las apps que lo necesiten
                return True, factura_guardada[0]['uuid']
