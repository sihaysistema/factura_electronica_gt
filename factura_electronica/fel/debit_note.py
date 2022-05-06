# Copyright (c) 2022, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import base64
import datetime
import json

import frappe
import requests
import xmltodict
from frappe import _
from frappe.utils import cint, flt, get_datetime, nowdate, nowtime

from factura_electronica.utils.utilities_facelec import (create_folder, get_currency_precision_facelec, remove_html_tags,
                                                         save_json_file)

# Una nota de débito o memorando de débito es un documento comercial emitido por
# un comprador a un vendedor para solicitar formalmente una nota de crédito.
# La nota de débito actúa como el documento fuente del diario de devoluciones
# de compras. Wikipedia (Inglés)


class ElectronicDebitNote:
    def __init__(self, invoice_code, conf_name, naming_series, uuid_purch_inv, date_inv_origin, reason):
        """__init__
        Constructor de la clase, las propiedades iniciadas como privadas
        Args:
            invoice_code (str): Serie original de la factura
            conf_name (str): Nombre configuracion para factura electronica
        """
        self.__invoice_code = invoice_code
        self.__config_name = conf_name
        self.__naming_serie = naming_series
        self.__precision = get_currency_precision_facelec(conf_name)
        self.__default_address = False
        self.__uuid_inv_origin = uuid_purch_inv
        self.__date_inv_origin = date_inv_origin
        self.__reason = reason
        self.__start_datetime = get_datetime()

    def build_invoice(self):
        """
        Valida las dependencias necesarias, para construir XML desde un JSON
        para ser firmado certificado por la SAT y finalmente generar factura electronica

        Returns:
            dict: msg status
        """

        try:
            # Definicion campos a consultar de la DB
            fields_sales_invoice = ['company', 'shipping_address', 'facelec_nit_fproveedor',
                                    'supplier_address', 'supplier_name', 'total_taxes_and_charges',
                                    'grand_total', 'net_total', 'currency', 'credit_to',
                                    'conversion_rate', 'contact_person', 'posting_date', 'posting_time']

            fields_config = ['fecha_y_tiempo_documento_electronica', 'usar_datos_prueba', 'nombre_empresa_prueba',
                             'is_it_an_establishment', 'parent_company', 'is_individual', 'facelec_name_of_owner',
                             'afiliacion_iva', 'correo_copia', 'descripcion_item', 'url_firma', 'alias', 'es_anulacion',
                             'llave_pfx', 'url_dte', 'llave_ws']

            self.__doc_inv = frappe.db.get_value('Purchase Invoice', self.__invoice_code, fields_sales_invoice, as_dict=1)
            self.__config_facelec = frappe.db.get_value('Configuracion Factura Electronica', self.__config_name, fields_config, as_dict=1)

            # 1 Valida y construye por partes el XML desde un dict
            status_validate = self.validate()  # True/False

            if status_validate.get('status'):  # True/False
                # 2 - Asignacion y creacion base peticion para luego ser convertida a XML
                self.__base_peticion = {
                    "dte:GTDocumento": {
                        "@xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",  # Version 2
                        "@xmlns:dte": "http://www.sat.gob.gt/dte/fel/0.2.0",
                        "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                        "@Version": "0.1",
                        "dte:SAT": {
                            "@ClaseDocumento": "dte",
                            "dte:DTE": {
                                "@ID": "DatosCertificados",
                                "dte:DatosEmision": {
                                    "@ID": "DatosEmision",
                                    "dte:DatosGenerales": self.__d_general,
                                    "dte:Emisor": self.__d_emisor,
                                    "dte:Receptor": self.__d_receptor,
                                    "dte:Items": self.__d_items,
                                    "dte:Totales": self.__d_totales,
                                    "dte:Complementos": self.__complemento,
                                }
                            }
                        }
                    }
                }

                # USAR SOLO PARA DEBUG (XML y JSON):
                # Los archivos al tener el mismo nombre en cada generacion, se sobreescriben en cada generacion
                with open('PREVIEW-NOTA-DEBITO-FEL.xml', 'w') as f:
                    f.write(xmltodict.unparse(self.__base_peticion, pretty=True))

                with open('PREVIEW-NOTA-DEBITO-FEL.json', 'w') as f:
                    f.write(json.dumps(self.__base_peticion, default=str))

                return {'status': True, 'description': 'OK', 'error': ''}

            else:
                return {'status': False, 'description': status_validate.get('description'), 'error': status_validate.get('error')}

        except Exception:
            return {'status': False, 'description': 'Peticion XML no construido', 'error': frappe.get_traceback()}

    def validate(self):
        """
        Metodo encargado de validar y generar cada seccion que constituye el XML para la peticion
        Si existe algun error retorna el status y el problema para ser solucionado

        Returns:
            dict: msg status
        """

        # Validacion y generacion seccion datos generales
        status_data_gen = self.general_data()
        if not status_data_gen.get('status'):
            return status_data_gen

        # Validacion y generacion seccion emisor
        status_sender = self.sender()
        if not status_sender.get('status'):
            # Si existe algun error se retornara una tupla
            return status_sender

        # Validacion y generacion seccion receptor
        status_receiver = self.receiver()
        if not status_receiver.get('status'):
            return status_receiver

        # Validacion y generacion seccion items
        status_items = self.items()
        if not status_items.get('status'):
            return status_items

        # Validacion y generacion seccion totales
        status_totals = self.totals()
        if not status_totals.get('status'):
            return status_totals

        # Validacion generacion complemento
        status_comp = self.deb_note_complement()
        if not status_comp.get('status'):
            return status_comp

        # Si todo va bien, retorna True
        return {'status': True, 'description': 'OK', 'error': ''}

    def general_data(self):
        """
        Construye la seccion datos generales que incluye, codigo de moneda, Fecha y Hora de emision
        Tipo de factura

        Returns:
            dict: msg status
        """

        try:
            if self.__config_facelec.fecha_y_tiempo_documento_electronica == 'Fecha y tiempo de peticion a INFILE':
                ok_datetime = str(nowdate())+'T'+str(nowtime().rpartition('.')[0])

            else:  # Se usa fecha y tiempo de la factura (posting_date, posting_time)
                date_invoice_inv = str(self.__doc_inv.posting_date)
                ok_time = str(self.__doc_inv.posting_time)
                ok_datetime = f'{date_invoice_inv}T{datetime.datetime.strptime(ok_time.split(".")[0], "%H:%M:%S").time()}'

            self.__d_general = {
                "@CodigoMoneda": self.__doc_inv.currency,
                "@FechaHoraEmision": ok_datetime,
                "@Tipo": frappe.db.get_value('Serial Configuration For Purchase Invoice', {'parent': self.__config_name, 'serie': self.__naming_serie},
                                             'tipo_documento')
            }

            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            msg_gen = _('No se obtuvo la data para generar la sección datos generales, verifique que la configuración de facelec este completa')
            return {'status': False, 'description': msg_gen, 'error': frappe.get_traceback()}

    def sender(self):
        """
        Valida y obtiene la data necesaria para la seccion de Emisor,
        entidad que emite la factura

        Returns:
            dict: msg status
        """

        try:
            status_sender = True
            msg_e = []

            # Obtenemos datos necesario de company: Nombre de compañia, nit
            self.dat_compania = frappe.db.get_value('Company', filters={'name': self.__doc_inv.company},
                                                    fieldname=['company_name', 'nit_face_company', 'tax_id',
                                                               'facelec_trade_name'], as_dict=1)
            if not self.dat_compania:
                status_sender = False
                msg_e.append(f'{_("No se encontraron datos para la compañia")} {self.__doc_inv.company}.\
                                  {_("Verifique que los datos de la compañia esten completos e intente de nuevo")}')

            # De la compañia, obtenemos direccion 1, email, codigo postal, departamento, municipio, pais ...
            dat_direccion = frappe.db.get_value('Address', filters={'name': self.__doc_inv.shipping_address},
                                                fieldname=['address_line1', 'email_id', 'pincode', 'county',
                                                           'state', 'city', 'country', 'facelec_establishment', 'phone'], as_dict=1)
            if not dat_direccion:
                status_sender = False
                msg_e.append(f'{_("No se encontro ninguna direccion para la compania")} {self.dat_compania.company_name}, \
                            {_("verifica que exista una, con datos en sus campos")} Direccion Linea 1, Direccion de correo electronico, \
                                Codigo Postal, Departamento, Ciudad, Pais e intente de nuevo')

            # LA ENTIDAD EMISORA SI O SI DEBE TENER ESTOS DATOS :D
            # Validacion de existencia en los campos de direccion, ya que son obligatorio por parte de la API FEL
            # Usaremos la primera que se encuentre
            for dire in dat_direccion:
                if not dat_direccion.get(dire):
                    status_sender = False
                    msg_e.append(f'{_("El campo: ")} <strong>{dire}</strong> {_("de la direccion de compania no tiene dato")}\
                                     , {_("por favor asignarle un valor e intentar de nuevo")}')

            # Si en configuracion de factura electronica esta seleccionada la opcion de usar datos de prueba
            # SE APLICAN DATOS DE LAS CREDENCIALES DE PRUEBAS
            if self.__config_facelec.usar_datos_prueba == 1:
                nom_comercial = self.__config_facelec.nombre_empresa_prueba

                # Si la compañia esta configurada como establecimiento (sucursal), se usa el nombre de la compañia configurada
                if self.__config_facelec.is_it_an_establishment:
                    nombre_emisor = self.__config_facelec.parent_company

                # Si la compania es de un propietario (INDIVIDUAL): Se usa el nombre del propietario
                elif self.__config_facelec.is_individual:
                    nombre_emisor = self.__config_facelec.facelec_name_of_owner

                else:
                    # Si no es de propiedad individual, se usa el nombre de pruebas
                    nombre_emisor = nom_comercial

            # Aplica Si los datos son para producción
            else:
                nom_comercial = self.dat_compania.company_name  # must be company_name, do not use trade name

                # Si la compañia esta configurada como establecimiento (sucursal), se usa el nombre de la compañia configurada
                if self.__config_facelec.is_it_an_establishment:
                    nombre_emisor = self.__config_facelec.parent_company
                    nom_comercial = self.__config_facelec.parent_company

                # Si la compania es de un propietario (INDIVIDUAL): se usa el nombre del propietario
                elif self.__config_facelec.is_individual:
                    nombre_emisor = self.__config_facelec.facelec_name_of_owner

                else:
                    # Si no es de propiedad individual, se usa el nombre de la empresa
                    nombre_emisor = nom_comercial

            # Asignacion data
            self.__d_emisor = {
                "@AfiliacionIVA": self.__config_facelec.afiliacion_iva,
                "@CodigoEstablecimiento": dat_direccion.facelec_establishment,
                "@CorreoEmisor": dat_direccion.email_id,
                "@NITEmisor": str((self.dat_compania.nit_face_company).replace('-', '')).upper().strip(),
                "@NombreComercial": nom_comercial,
                "@NombreEmisor": nombre_emisor,
                "dte:DireccionEmisor": {
                    "dte:Direccion": dat_direccion.address_line1,
                    "dte:CodigoPostal": dat_direccion.pincode,  # Codig postal
                    "dte:Municipio": dat_direccion.county,  # Municipio
                    "dte:Departamento": dat_direccion.state,  # Departamento
                    "dte:Pais": frappe.db.get_value('Country', {'name': dat_direccion.country}, 'code').upper() or 'GT'  # CODIG PAIS
                }
            }

            if not status_sender:
                return {'status': False,
                        'description': _('Los datos de la direccion de la compañia no estan configurados por completo, reconfigure e intente de nuevo'),
                        'error': msg_e}
            else:
                return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            return {'status': False,
                    'description': _('No se logro obtener toda la data necesaria de la direccion de la compañia,\
                        verifique que todos los campos de la direccion esten completos e intente de nuevo'),
                    'error': frappe.get_traceback()}

    def receiver(self):
        """
        Validacion y generacion datos de Receptor (cliente)
        NOTA: Si no hay datos de clientes, se usaran datos default

        Returns:
            dict: msg status
        """

        try:
            customer_addr = frappe.db.get_value('Address', filters={'name': self.__doc_inv.supplier_address},
                                                fieldname=['address_line1', 'email_id', 'pincode', 'county',
                                                           'state', 'city', 'country'], as_dict=1)

            # Cuando se trata de una factura especial es necesario tener el DPI de la persona
            # contact_per = frappe.db.get_value('Contact Identification',
            #                                   filters={'parent': self.__doc_inv.contact_person, 'id_prefix': 'DPI'},
            #                                   fieldname=['id_number'], as_dict=1)

            # Se usara en caso de que no exista un direccion enlazada al cliente
            datos_default = {
                'email': self.__config_facelec.correo_copia,
                'supplier_name': 'Consumidor Final',
                'address': 'Guatemala',
                'pincode': '0',
                'municipio': 'Guatemala',
                'departamento': 'Guatemala',
                'pais': 'GT'
            }

            # SI NO HAY UNA DIRECCION DE CLIENTE, SE USARA LOS DATOS DEFAULT
            if not customer_addr:
                self.__default_address = True
                datos_default = {
                    'email': self.__config_facelec.correo_copia,
                    'supplier_name': 'Consumidor Final',
                    'address': 'Guatemala',
                    'pincode': '0',
                    'municipio': 'Guatemala',
                    'departamento': 'Guatemala',
                    'pais': 'GT'
                }

                # SI ES CONSUMIRDOR FINAL Y NO TIENE DIRECCION
                # Si es consumidor Final: para generar factura electronica obligatoriamente se debe asignar un correo
                # electronico, los demas campos se pueden dejar como defualt para ciudad
                if str(self.__doc_inv.facelec_nit_fproveedor).upper() == 'C/F':
                    # dpi = contact_per.id_number

                    # if not dpi:
                    #     return {'status': False, 'description': 'No se encontro un DPI enlazado al proveedor, por favor agreguelo \
                    #         en contacto e intente de nuevo', 'error': ''}

                    self.__d_receptor = {
                        "@CorreoReceptor": datos_default.get('email'),
                        "@IDReceptor": str((self.__doc_inv.facelec_nit_fproveedor).replace('/', '').replace('-', '')).upper().strip(),  # NIT,
                        "@NombreReceptor": self.__doc_inv.supplier_name,
                        # "@TipoEspecial": "CUI",
                        "dte:DireccionReceptor": {
                            "dte:Direccion": datos_default.get('address'),
                            "dte:CodigoPostal": datos_default.get('pincode'),
                            "dte:Municipio": datos_default.get('municipio'),
                            "dte:Departamento": datos_default.get('departamento'),
                            "dte:Pais": datos_default.get('pais')
                        }
                    }
                else:
                    # SI NO ES CONSUMIDOR FINAL Y NO TIENE DIRECCION
                    self.__d_receptor = {
                        "@CorreoReceptor": datos_default.get('email'),
                        "@IDReceptor": str((self.__doc_inv.facelec_nit_fproveedor).replace('/', '').replace('-', '')).upper().strip(),  # NIT
                        "@NombreReceptor": self.__doc_inv.supplier_name,
                        # "@TipoEspecial": "CUI",
                        "dte:DireccionReceptor": {
                            "dte:Direccion": datos_default.get('address'),
                            "dte:CodigoPostal": datos_default.get('pincode'),
                            "dte:Municipio": datos_default.get('municipio'),
                            "dte:Departamento": datos_default.get('departamento'),
                            "dte:Pais": datos_default.get('pais')
                        }
                    }

            # SI HAY UNA DIRECCION DE CLIENTE
            else:
                self.__default_address = False

                # SI ES CONSUMIDOR FINAL Y TIENE DIRECCION
                # Si es consumidor Final: para generar factura electronica obligatoriamente se debe asignar un correo
                # electronico, los demas campos se pueden dejar como defualt para ciudad
                if str(self.__doc_inv.facelec_nit_fproveedor).upper() == 'C/F':
                    # dpi = contact_per.id_number

                    # if not dpi:
                    #     return {'status': False, 'description': 'No se encontro un DPI enlazado al proveedor, por favor agreguelo \
                    #         en contacto e intente de nuevo', 'error': ''}

                    self.__d_receptor = {
                        "@CorreoReceptor": customer_addr.get('email_id', datos_default.get('email')),
                        "@IDReceptor": str((self.__doc_inv.facelec_nit_fproveedor).replace('/', '').replace('-', '')).upper().strip(),  # NIT,
                        "@NombreReceptor": self.__doc_inv.supplier_name,
                        # "@TipoEspecial": "CUI",
                        "dte:DireccionReceptor": {
                            "dte:Direccion": customer_addr.get('address_line1', datos_default.get('address')),
                            "dte:CodigoPostal": customer_addr.get('pincode', datos_default.get('pincode')),
                            "dte:Municipio": customer_addr.get('county', datos_default.get('municipio')),
                            "dte:Departamento": customer_addr.get('state', datos_default.get('departamento')),
                            "dte:Pais": frappe.db.get_value('Country', {'name': customer_addr['country']}, 'code').upper() or 'GT'
                        }
                    }
                else:
                    # SI NO ES CONSUMIDOR FINAL Y TIENE DIRECCION
                    self.__d_receptor = {
                        "@CorreoReceptor": customer_addr.get('email_id', datos_default.get('email')),
                        "@IDReceptor": str((self.__doc_inv.facelec_nit_fproveedor).replace('/', '').replace('-', '')).upper().strip(),  # NIT
                        "@NombreReceptor": self.__doc_inv.supplier_name,
                        "@TipoEspecial": "CUI",
                        "dte:DireccionReceptor": {
                            "dte:Direccion": customer_addr.get('address_line1', datos_default.get('address')),
                            "dte:CodigoPostal": customer_addr.get('pincode', datos_default.get('pincode')),
                            "dte:Municipio": customer_addr.get('county', datos_default.get('municipio')),
                            "dte:Departamento": customer_addr.get('state', datos_default.get('departamento')),
                            "dte:Pais": frappe.db.get_value('Country', {'name': customer_addr['country']}, 'code').upper() or 'GT'
                        }
                    }

            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            return {'status': False, 'description': _('No se obtuvieron los datos necesarios del proveedor, por favor reconfigurelo para facelec e intente de nuevo'),
                    'error': frappe.get_traceback()}

    def items(self):
        """
        Procesa todos los items de la factura aplicando calculos necesarios para la SAT

        Returns:
            dict: msg status
        """

        # NOTE: IMPORTANTE: LOS CALCULOS SOLO SE REALIZAN PARA BIENES Y SERVICIOS
        # CONSULTAR CON CONTADOR E INFILE SI SE DEBEN INCLUIR LOS IMPUESTOS ESPECIALES
        # EN CASO LA EMPRESA CLIENTE NECESITE ESTO

        try:
            i_fel = {}  # Guardara la seccion de items ok
            items_ok = []  # Guardara todos los items OK

            # Obtenemos los impuesto cofigurados para x compañia en la factura (IVA)
            self.__taxes_fact = frappe.db.get_values('Purchase Taxes and Charges', filters={'parent': self.__invoice_code},
                                                     fieldname=['facelec_tax_name', 'facelec_taxable_unit_code', 'rate'], as_dict=True)

            self.iva_rate = self.__taxes_fact[0]['rate']

            # Obtenemos los items de la factura
            self.__dat_items = frappe.db.get_values('Purchase Invoice Item', filters={'parent': self.__invoice_code},
                                                    fieldname=['item_name', 'qty', 'item_code', 'description',
                                                               'net_amount', 'base_net_amount', 'discount_percentage',
                                                               'discount_amount', 'price_list_rate', 'net_rate',
                                                               'stock_uom', 'item_group', 'rate', 'amount',
                                                               'facelec_p_sales_tax_for_this_row',
                                                               'facelec_p_amount_minus_excise_tax', 'facelec_p_is_fuel',
                                                               'facelec_p_is_good', 'facelec_p_is_service', 'facelec_pr_is_exempt',
                                                               'facelec_p_other_tax_amount', 'facelec_p_purchase_three_digit',
                                                               'facelec_p_gt_tax_net_fuel_amt', 'facelec_p_gt_tax_net_goods_amt',
                                                               'facelec_p_gt_tax_net_services_amt', 'facelec_is_discount'], order_by='idx', as_dict=True)

            # Configuracion para obtener descripcion de item de Item Name o de Descripcion (segun user)
            switch_item_description = self.__config_facelec.descripcion_item

            # Verificamos la cantidad de items
            longitems = len(self.__dat_items)

            if longitems == 0:
                return {'status': False, 'description': _('Debe existir al menos un producto en la factura para poder generarse'), 'error': ''}

            contador = 0  # Utilizado para enumerar las lineas en factura electronica

            # Si existe un solo item a facturar la iteracion se hara una vez, si hay mas lo contrario mas iteraciones
            for i in range(0, longitems):
                obj_item = {}  # por fila
                net_amt = 0  # Neto por fila

                # Is Service, Is Good.  Si Is Fuel = Is Good. Si Is Exempt = Is Good.
                if cint(self.__dat_items[i]['facelec_p_is_service']) == 1:
                    obj_item["@BienOServicio"] = 'S'
                    net_amt = flt(self.__dat_items[i]['net_amount'], self.__precision)

                elif cint(self.__dat_items[i]['facelec_p_is_good']) == 1:
                    obj_item["@BienOServicio"] = 'B'
                    net_amt = flt(self.__dat_items[i]['net_amount'], self.__precision)

                elif cint(self.__dat_items[i]['facelec_p_is_fuel']) == 1:
                    obj_item["@BienOServicio"] = 'B'
                    net_amt = flt(self.__dat_items[i]['facelec_p_gt_tax_net_fuel_amt'], self.__precision)

                # NOTA: AUN NO SE HA DESARROLLADO LA FUNCIONALIDAD DE FACTURAS EXENTAS
                elif cint(self.__dat_items[i]['facelec_pr_is_exempt']) == 1:
                    obj_item["@BienOServicio"] = 'B'
                    net_amt = flt(self.__dat_items[i]['net_amount'], self.__precision)

                precio_uni = 0
                precio_item = 0

                # Logica para validacion si aplica Descuento
                desc_item_fila = self.__dat_items[i].get('facelec_discount_amount', 0)

                # Precio unitario, (sin aplicarle descuento)
                # NOTA: UNA FACTURA ESPECIAL NO LLEVA IMPUESTOS ESPECIALES COMO IDP CONSULTAR CON CONTADOR PARA SALIR DE DUDAS
                # Al precio unitario se le suma el descuento que genera ERP, ya que es neceario enviar precio sin descuentos,
                # en las operaciones restantes es neceario
                # (Precio Unitario) + Descuento --> se le resta el IDP ya que viene incluido en el precio
                precio_uni = flt(self.__dat_items[i]['rate'] + desc_item_fila, self.__precision)

                precio_item = flt(precio_uni * self.__dat_items[i]['qty'], self.__precision)

                desc_fila = 0
                desc_fila = flt(self.__dat_items[i]['qty'] * desc_item_fila, self.__precision)

                contador += 1
                description_to_item = self.__dat_items[i]['item_name'] if switch_item_description == "Nombre de Item" else self.__dat_items[i]['description']

                obj_item["@NumeroLinea"] = contador
                obj_item["dte:Cantidad"] = abs(float(self.__dat_items[i]['qty']))
                obj_item["dte:UnidadMedida"] = self.__dat_items[i]['facelec_p_purchase_three_digit']
                obj_item["dte:Descripcion"] = remove_html_tags(description_to_item)  # description
                obj_item["dte:PrecioUnitario"] = abs(flt(precio_uni, self.__precision))
                obj_item["dte:Precio"] = abs(flt(precio_item, self.__precision))  # Correcto según el esquema XML)
                obj_item["dte:Descuento"] = abs(flt(desc_fila, self.__precision))

                # Generacion seccion de impuestos
                obj_item["dte:Impuestos"] = {}
                obj_item["dte:Impuestos"]["dte:Impuesto"] = [
                    {
                        "dte:NombreCorto": self.__taxes_fact[0]['facelec_tax_name'],
                        "dte:CodigoUnidadGravable": self.__taxes_fact[0]['facelec_taxable_unit_code'],
                        "dte:MontoGravable": abs(net_amt),  # net_amount
                        "dte:MontoImpuesto": abs(flt(net_amt * (self.__taxes_fact[0]['rate']/100),
                                                 self.__precision))
                    }
                ]

                obj_item["dte:Total"] = abs(flt(self.__dat_items[i]['amount'], self.__precision))

                items_ok.append(obj_item)

            i_fel = {"dte:Item": items_ok}
            self.__d_items = i_fel

            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            msg_ei = _('Los productos no fueron procesados, por favor verifique que los productos esten configurados para Factura Electronica e intente nuevamente.')
            return {'status': False, 'description': msg_ei, 'error': frappe.get_traceback()}

    def totals(self):
        """
        Funcion encargada de realizar totales de los impuestos sobre la factura
        y grand total

        Returns:
            dict: msg status
        """

        try:
            gran_tot = 0

            # Por cada fila se obtiene el total de IVA e IDP en caso exista
            for i in self.__dat_items:
                gran_tot += flt(i['facelec_p_sales_tax_for_this_row'], self.__precision)

            self.__d_totales = {
                "dte:TotalImpuestos": {
                    "dte:TotalImpuesto": [{
                        "@NombreCorto": self.__taxes_fact[0]['facelec_tax_name'],  # "IVA",
                        "@TotalMontoImpuesto": abs(flt(gran_tot, self.__precision))
                    }]
                },
                "dte:GranTotal": abs(flt(self.__doc_inv.grand_total, self.__precision))
            }

            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            msg_tot = _('La seccion de totales no pudo ser generada, por favor verifique que la plantilla de impuestos este configurada correctamente\
                e intente de nuevo.')
            return {'status': False, 'description': msg_tot, 'error': frappe.get_traceback()}

    def deb_note_complement(self):
        """
        Metodo para construccion la seccion complemento para la nota de debito

        Returns:
            tuple: True/False, msj, msj
        """
        try:
            self.__complemento = {
                "dte:Complemento": {
                    "@IDComplemento": "ReferenciasNota",
                    "@NombreComplemento": "Nota de Debito",
                    "@URIComplemento": "text",
                    "cno:ReferenciasNota": {
                        "@xmlns:cno": "http://www.sat.gob.gt/face2/ComplementoReferenciaNota/0.1.0",
                        "@FechaEmisionDocumentoOrigen": self.__date_inv_origin,
                        "@MotivoAjuste": self.__reason,
                        "@NumeroAutorizacionDocumentoOrigen": self.__uuid_inv_origin,
                        "@Version": "0.0"
                    }
                }
            }

            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            return {'status': False, 'description': 'No se pudo generar el complemento XML para la peticion', 'error': frappe.get_traceback()}

    def sign_invoice(self):
        """
        Funcion encargada de solicitar firma para archivo XML

        Returns:
            dict: msg status
        """

        try:
            # To XML: Convierte de JSON a XML indentado
            self.__xml_string = xmltodict.unparse(self.__base_peticion, pretty=True)

        except Exception:
            return {'status': False, 'description': 'No se pudo generar el archivo XML para la peticion', 'error': frappe.get_traceback()}

        try:
            # To base64: Convierte a base64, para enviarlo en la peticion
            self.__encoded_bytes = base64.b64encode(self.__xml_string.encode("utf-8"))
            self.__encoded_str = str(self.__encoded_bytes, "utf-8")
            # Usar solo para debug
            # with open('codificado.txt', 'w') as f:
            #         f.write(self.__encoded_str)
        except Exception:
            return {'status': False, 'description': 'No se pudo codificar el archivo XML', 'error': frappe.get_traceback()}

        # Generamos la peticion para firmar
        try:
            # codigo = frappe.db.get_value('Configuracion Factura Electronica',
            #                             {'name': self.__config_name}, 'codigo')

            url = str(self.__config_facelec.url_firma).strip()
            alias = str(self.__config_facelec.alias).strip()
            anulacion = str(self.__config_facelec.es_anulacion).strip()
            self.__llave = str(self.__config_facelec.llave_pfx).strip()

            self.__data_a_firmar = {
                "llave": self.__llave,  # LLAVE
                "archivo": str(self.__encoded_str),  # En base64
                # "codigo": codigo, # Número interno de cada transacción
                "alias": alias,  # USUARIO
                "es_anulacion": anulacion  # "N" si es certificacion y "S" si es anulacion
            }

            # DEBUGGING WRITE JSON PETITION TO SITES FOLDER
            # with open('peticion.json', 'w') as f:
            #      f.write(json.dumps(self.__data_a_firmar, indent=2))

            headers = {"content-type": "application/json"}
            response = requests.post(url, data=json.dumps(self.__data_a_firmar), headers=headers)

            # Guardamos en una variable privada la respuesta
            self.__doc_firmado = json.loads((response.content).decode('utf-8'))

            # Guardamos la respuesta en un archivo DEBUG
            # with open('recibido_firmado.json', 'w') as f:
            #     f.write(json.dumps(self.__doc_firmado, indent=2))

            # Si la respuesta es true
            if self.__doc_firmado.get('resultado'):  # True/False
                # Guardamos en privado el documento firmado y encriptado
                self.__encrypted = self.__doc_firmado.get('archivo')

                # Retornamos el status del proceso
                return {'status': True, 'description': 'OK', 'error': ''}

            else:  # Si ocurre un error retornamos la descripcion del error por INFILE
                return {'status': False, 'description': 'Los datos no fueron validados ni firmados', 'error': self.__doc_firmado.get('descripcion')}

        except Exception:
            return {'status': False, 'description': 'No se pudo firmar la factura', 'error': frappe.get_traceback()}

    def request_electronic_invoice(self):
        """
        Funcion encargada de solicitar factura electronica al Web Service de INFILE

        Returns:
            dict: msg status
        """

        try:
            nit_company = str(frappe.db.get_value('Company', {'name': self.__doc_inv.company}, 'nit_face_company').replace('-', '')).upper().strip()

            url = self.__config_facelec.url_dte
            user = self.__config_facelec.alias
            ident = self.__invoice_code  # identificador
            llave = self.__config_facelec.llave_ws
            correo_copia = self.__config_facelec.correo_copia

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

            # DEBUG: Para ver que datos se estan enviando al Web Service
            # with open("peticion-fel.json", "w") as file:
            #     file.write(json.dumps(req_dte, indent=2))

            self.__response = requests.post(url, data=json.dumps(req_dte), headers=headers)
            self.__response_ok = json.loads((self.__response.content).decode('utf-8'))

            # DEBUGGING WRITE JSON RESPONSES TO SITES FOLDER
            # with open('RESPONSE-FACTURA-FEL.json', 'w') as f:
            #     f.write(json.dumps(self.__response_ok, indent=2))

            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            return {'status': False, 'description': 'No se pudo solicitar la factura a INFILE', 'error': frappe.get_traceback()}

    def response_validator(self):
        """
        Funcion encargada de verificar las respuestas de INFILE-SAT

        Returns:
            dict: msg status
        """

        try:
            # Verifica que no existan errores
            if self.__response_ok['resultado'] and (self.__response_ok['cantidad_errores'] == 0):
                # # Se encarga de guardar las respuestas de INFILE-SAT esto para llevar registro
                status_saved = self.save_answers()

                # Al primer error encontrado retornara un detalle con el mismo
                if not status_saved:
                    return status_saved

                return {'status': True, 'description': 'OK', 'error': '',
                        'numero_autorizacion': self.__response_ok['uuid'],
                        'serie': self.__response_ok['serie'], 'numero': self.__response_ok['numero']}

            else:
                return {'status': False, 'description': self.__response_ok['descripcion'],
                        'error': str(self.__response_ok['descripcion_errores'])}

        except Exception:
            return {'status': False, 'description': 'No se pudo validar la respuesta enviada por INFILE', 'error': frappe.get_traceback()}

    def save_answers(self):
        """
        Funcion encargada guardar registro con respuestas de INFILE-SAT
        NOTA: Guarda solo aquellas que se generaron correctamente
        Returns:
            tuple: True/False, msj, msj
        """

        try:
            self.__end_datetime = get_datetime()

            # Valida que no se haya guardado con anterioridad
            if not frappe.db.exists('Envio FEL', {'name': self.__response_ok['uuid']}):
                resp_fel = frappe.new_doc("Envio FEL")
                resp_fel.resultado = self.__response_ok['resultado']
                resp_fel.status = 'Valid'
                resp_fel.tipo_documento = 'Nota de Debito'
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

                # Guarda el documento firmado encriptado en base64
                # decodedBytes = str(self.__response_ok['xml_certificado']) # base64.b64decode(self.__response_ok['xml_certificado'])
                # decodedStr = str(decodedBytes, "utf-8")
                # NOTA: OJO: Pueden hacer archivos, data que supera la capacidad del campo en la DB
                # por lo que queda desactivado el guardado de este campo
                # resp_fel.xml_certificado = str(self.__xml_string)  # json.dumps(self.__doc_firmado, indent=2) # decodedStr
                resp_fel.enviado = str(self.__start_datetime)
                resp_fel.recibido = str(self.__end_datetime)

                resp_fel.save(ignore_permissions=True)

                # Una vez guarda la respuesta, se adjunta el .json de la peticion para mantener un registro de lo que se envia
                # NOTA: para ver la peticion original hay que convertir el json a XML, se guarda en json por su facil
                # manipulacion
                content_f = json.dumps(self.__base_peticion, default=str)
                # Si no existe el fonder contender, se crea
                fel_folder_container = create_folder('ENVIOS_FEL')
                # Si no existe el folder para almacenar los json, se crea
                fel_folder = create_folder('FACT_NDEB', fel_folder_container)
                # Se guarda el archivo json y quedara como adjunto al registro anteriormente creado
                save_json_file(f'{self.__response_ok["uuid"]}.json', content_f, 'Envio FEL', resp_fel.name, fel_folder, 1)

            return {'status': True, 'description': 'OK', 'error': ''}

        except Exception:
            return {'status': False, 'description': f'No se pudo guardar la respuesta de la factura {self.__invoice_code} en Envios FEL',
                    'error': frappe.get_traceback()}

    def upgrade_records(self):
        """
        Funcion encargada de actualizar todos los doctypes enlazados a la factura original, con
        la serie generada para factura electronica

        Returns:
            tuple: True/False, msj, msj
        """

        # Verifica que exista un documento en la tabla Envio FEL con el nombre de la serie original
        if frappe.db.exists('Envio FEL', {'serie_factura_original': self.__invoice_code}):
            factura_guardada = frappe.db.get_values('Envio FEL',
                                                    filters={'serie_factura_original': self.__invoice_code},
                                                    fieldname=['numero', 'serie', 'uuid'], as_dict=1)
            # Esta seccion se encarga de actualizar la serie, con una nueva que es serie y numero
            # buscara en las tablas donde exista una coincidencia actualizando con la nueva serie
            serie_sat = str(factura_guardada[0]['serie']).replace('*', '')  # Se sustituye el * tomando en cuenta el server de pruebas FEL
            # serieFEL = str('FACELEC-' + factura_guardada[0]['numero'])
            serieFEL = str(serie_sat + str(factura_guardada[0]['numero']))
            try:
                # serieFEL: guarda el numero DTE retornado por INFILE, se utilizara para reemplazar el nombre de la serie de la
                # factura que lo generó.
                # serieFEL = str(factura_guardada[0]['serie'] + '-' + factura_guardada[0]['numero'])
                # serie_fac_original: Guarda la serie original de la factura.
                serie_fac_original = self.__invoice_code

                # Actualizacion de tablas que son modificadas directamente.
                # 01 - tabPurchase Invoice: actualizacion con datos correctos
                frappe.db.sql('''UPDATE `tabPurchase Invoice`
                                 SET name=%(name)s,
                                    numero_autorizacion_fel=%(no_correcto)s,
                                    serie_original_del_documento=%(serie_orig_correcta)s
                                 WHERE name=%(serieFa)s
                              ''', {'name': serieFEL, 'no_correcto': factura_guardada[0]['uuid'],
                                    'serie_orig_correcta': serie_fac_original, 'serieFa': serie_fac_original})

                # 02 - tabPurchase Invoice Item: actualizacion items de la factura
                frappe.db.sql('''UPDATE `tabPurchase Invoice Item` SET parent=%(name)s
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
                if frappe.db.exists('Purchase Taxes and Charges', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPurchase Taxes and Charges` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                if frappe.db.exists('Otros Impuestos Factura Electronica', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabOtros Impuestos Factura Electronica` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # NOTA: USAR ESTE QUERY SI SE AGRUPARAN ITEMS EN PURCHASE INVOICE
                # if frappe.db.exists('Item Overview', {'parent': serie_fac_original}):
                #     frappe.db.sql('''UPDATE `tabItem Overview` SET parent=%(name)s
                #                     WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

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
                # 08 - tabPurchase Invoice Timesheet
                if frappe.db.exists('Purchase Invoice Timesheet', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPurchase Invoice Timesheet` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Equipo Ventas, si existe
                # 09 - tabSales Team
                if frappe.db.exists('Purchase Team', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPurchase Team` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Packed Item, si existe
                # 10 - tabPacked Item
                if frappe.db.exists('Packed Item', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPacked Item` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Sales Invoice Advance - Anticipos a facturas, si existe
                # 11 - tabPurchase Invoice Advance
                if frappe.db.exists('Purchase Invoice Advance', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPurchase Invoice Advance` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Sales Invoice Payment - Pagos sobre a facturas, si existe
                # 12 - tabPurchase Invoice Payment
                if frappe.db.exists('Purchase Invoice Payment', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPurchase Invoice Payment` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

                # Payment Entry Reference -, si existe
                # 13 - tabPayment Entry Reference
                if frappe.db.exists('Payment Entry Reference', {'parent': serie_fac_original}):
                    frappe.db.sql('''UPDATE `tabPurchase Invoice Payment` SET parent=%(name)s
                                    WHERE parent=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})
                    # FIXED
                    frappe.db.sql('''UPDATE `tabPayment Entry Reference` SET reference_name=%(name)s
                                    WHERE reference_name=%(serieFa)s''', {'name': serieFEL, 'serieFa': serie_fac_original})

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

            except Exception:
                # En caso exista un error al renombrar la factura retornara el mensaje con el error
                return {'status': False, 'description': 'Referencias de la nota de debito no actualizadas', 'error': frappe.get_traceback()}

            else:
                # Si los datos se Guardan correctamente, se retornara la serie, que sera capturado por api.py
                # para luego ser capturado por javascript, se utilizara para recargar la url con los cambios correctos
                if self.__default_address:
                    frappe.msgprint(_('Nota de Debito generada exitosamente, sin embargo se sugiere configurar correctamente la dirección del cliente, \
                        ya que se usaron datos default. Haga clic <a href="#List/Address/List"><b>Aquí</b></a> para configurarlo si lo desea.'))
                # Se utilizara el UUID como clave para orquestar el resto de las apps que lo necesiten
                # return True, factura_guardada[0]['uuid']
                return {'status': True, 'description': 'Nota de debito generada exitosamente',
                        'uuid': factura_guardada[0]['uuid'], 'serie': serieFEL}
