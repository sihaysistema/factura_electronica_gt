# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from xml.sax import parseString

import frappe
from frappe import _

from factura_electronica.controllers.journal_entry_special import JournalEntrySpecialISR
from factura_electronica.fel.canceller import CancelDocument
from factura_electronica.fel.credit_note import ElectronicCreditNote
from factura_electronica.fel.debit_note import ElectronicDebitNote
from factura_electronica.fel.exchange_invoice import SalesExchangeInvoice
from factura_electronica.fel.export_invoice import ExportInvoice
from factura_electronica.fel.fel import ElectronicInvoice
from factura_electronica.fel.fel_exempt import ExemptElectronicInvoice
from factura_electronica.fel.special_invoice import ElectronicSpecialInvoice

# !USAR SOLO PARA COSAS RELACIONADAS CON FEL :)


# INICIO FEL NORMAL
# API para uso interno con apps hechas con Frappe Framework, Para
# Generar Facturas electronicas FEL
@frappe.whitelist()
def api_interface(invoice_code, naming_series):
    """
    Usar Para uso interno con otras apps hechas con frappe framework,
    destinada a ser consumida con frappe.call
    llamara a las funciones necesarias para generar factura electronica
    manejando los estados para mostrarlos amigablemente en Front-End

    Args:
        invoice_code (str): Name original de la factura
        naming_series (str): Serie de factura

    Returns:
        tuple, msgprint: (True/False, mensaje ok/descripcion error) usado para javascript,
        el msgprint es para mostrar un mensaje a usuario
    """

    try:
        # Guarda el estado de la funcion encargada de aplicar la generacion de factura electronica
        state_of = generate_electronic_invoice(invoice_code, naming_series)
        if not state_of[0]:
            if type(state_of[1]) is dict:
                frappe.msgprint(msg=_(f'{state_of[1]}'),
                                title=_('Proceso no completado'), indicator='red')
                return False, state_of[1]

            else:
                frappe.msgprint(msg=_(f'{state_of[1]}'),
                                title=_('Proceso no completado'), indicator='red')
                return False, state_of[1]

        # Si el proceso es OK
        if type(state_of[1]) is dict:
            new_serie = frappe.db.get_value('Envio FEL', {'name': state_of[1]["msj"]}, 'serie_para_factura')
            frappe.msgprint(msg=_(f'Factura Electronica generada con UUID <b>{state_of[1]["msj"]}</b>'),
                            title=_('Proceso completado exitosamente'), indicator='green')

            return True, str(new_serie)

        else:
            new_serie = frappe.db.get_value('Envio FEL', {'name': state_of[1]}, 'serie_para_factura')
            frappe.msgprint(msg=_(f'Factura Electronica generada con UUID <b>{state_of[1]}</b>'),
                            title=_('Proceso completado exitosamente'), indicator='green')

            return True, str(new_serie)

    except:
        frappe.msgprint(
            _(f'Ocurrio un problme al tratar de generar Factura Electronicas, mas detalles en el siguiente log: {frappe.get_traceback()}'))
        return False, 'An error occurred in the process of generating an electronic invoice'


# Conector API para usar con otros Frameworks
# PARA GENERAR FACTURA ELECTRONICA FEL
@frappe.whitelist()
def api_facelec(invoice_name, naming_serie):
    """
    Conector API

    Args:
        invoice_name (str): Nombre de la factura
        naming_serie (str): Serie utilizada en la factura

    Returns:
        tuple: (True/False, msj)
    """

    try:
        # llamamos a la funcion que se encarga de validaciones y finalmente generar facelec
        state_of_facelec = generate_electronic_invoice(invoice_name, str(naming_serie))
        if state_of_facelec[0] == False:
            dict_response = {
                'status': 'NO PROCESADO',
                'id_factura': invoice_name,
                'msj': state_of_facelec[1]
            }

            return dict_response

        dict_ok = {
            'status': 'OK',
            'id_factura': invoice_name,
            'uuid': state_of_facelec[1]
        }

        return dict_ok

    except:
        return {
            'status': 'ERROR',
            'id_factura': invoice_name,
            'msj': f'Ocurrio un problema al tratar de generar factura electronica, mas info en: {frappe.get_traceback()}'
        }


# generador para Lotes, Factura Individual
def generate_electronic_invoice(invoice_code, naming_series):
    """
    Llama a la clase y sus metodos encargados de generar factura electronica,
    validando primero los requisitos para que se posible la generacion

    1. Valida si hay configuracion valida para generar factura electronica
    2. valida la serie a utilizar
    3. valida que no exista una anterior ya generada
    4. Crea una instancia para construir facelec
    4.1 Construye la estructura general para la peticion en JSON
    4.2 La estrucutra JSON se convierte a XML para firmarla con la SAT
    4.3 Si la firma es exitosa se solicita la generacion de facelec
    4.4 Se validan las respuestas
    4.5 Actualiza todas las tablas de la base de datos donde existe referencia a la
    factura que se solicito como electronica, con la nueva serie brindada por la SAT


    Args:
        invoice_code (str): Name original de la factura
        naming_series (str): Serie usada en factura

    Returns:
        tuple: True/False, msj, msj
    """

    try:
        # PASO 1: VALIDAMOS QUE EXISTA UNA CONFIGURACION PARA FACTURA ELECTRONICA
        status_config = validate_configuration()

        if status_config[0] == False:
            return status_config

        # PASO 1.1: VALIDAMOS LA SERIE A UTILIZAR PARA DEFINIR EL TIPO DE FACTURA ELECTRONIC A GENERAR
        if not frappe.db.exists('Configuracion Series FEL', {'parent': str(status_config[1]), 'serie': str(naming_series)}):
            return False, f'La serie utilizada en la factura no se encuentra configurada para Factura electronica \
                            Por favor agreguela en Series Fel de Configuracion Factura Electronica, y vuelva a intentar'

        # PASO 2: VALIDACION EXTRA PARA NO GENERAR FACTURAS ELECTRONICA DUPLICADAS, SI OCURRIERA EN ALGUN ESCENARIO
        status_invoice = check_invoice_records(str(invoice_code))
        if status_invoice[0] == True:
            return False, f'La factura se encuentra registrada como ya generada, puedes validar los detalles en \
                            Envios FEL, con codigo UUID {status_invoice[1]}'

        # PASO 3: FACTURA ELECTRONICA
        # paso 3.1 - NUEVA INSTANCIA
        new_invoice = ElectronicInvoice(invoice_code, status_config[1], naming_series)

        # PASO 3.2 - VALIDA LOS DATOS NECESARIOS PARA CONSTRUIR EL XML
        status = new_invoice.build_invoice()
        if status[0] == False:  # Si la construccion de la peticion es False
            return False, f'Ocurrio un problema al tratar de generar la petición JSON, mas detalle en: {status[1]}'

        # PASO 4: FIRMA CERTIFICADA Y ENCRIPTADA
        # En este paso se convierte de JSON a XML y se codifica en base64
        status_firma = new_invoice.sign_invoice()
        if status_firma[0] == False:  # Si no se firma correctamente
            return False, f'Ocurrio un problema al tratar de firmar la petición, vericar tener la url correcta para \
                firmas en Configuracion Factura Electroónica mas detalle en: {status_firma[1]}'

        # PASO 5: SOLICITAMOS FACTURA ELECTRONICA
        status_facelec = new_invoice.request_electronic_invoice()
        if status_facelec[0] == False:
            return False, f'Ocurrio un problema al tratar de generar factura electronica, mas detalles en: {status_facelec[1]}'

        # PASO 6: VALIDAMOS LAS RESPUESTAS Y GUARDAMOS EL RESULTADO POR INFILE
        # Las respuestas en este paso no son de gran importancia ya que las respuestas ok, seran guardadas
        # automaticamente si todo va bien, aqui se retornara cualquier error que ocurra en la fase
        status_res = new_invoice.response_validator()
        if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
            return status_res  # return tuple

        # PASO 7: ACTUALIZAMOS REGISTROS DE LA BASE DE DATOS
        status_upgrade = new_invoice.upgrade_records()
        if status_upgrade[0] == False:
            return status_upgrade

        # SI cumple con exito el flujo de procesos se retorna una tupla, en ella va
        # el UUID y la nueva serie para la factura
        return True, status_upgrade[1]


    except:
        return False, str(frappe.get_traceback())
# FIN FEL NORMAL


@frappe.whitelist()
def generate_debit_note(invoice_code, naming_series, uuid_purch_inv, date_inv_origin, reason):
    """
    Endpoint para generar notas de debito desde Purchase Invoice Doctype

    Args:
        invoice_code (str): `name` purchase invoice
        naming_series (str): serie utilizada en nota de debito
        uuid_purch_inv (str): UUID factura electronica por proveedor
        date_inv_origin (str): Fecha emision en factura
        reason (str): Razón de la nota de debito (requerido por la SAT)

    Returns:
        tuple: [description]
    """
    try:
        status_config = validate_configuration()

        if status_config[0] == False:
            return status_config

        # PASO 1.1: VALIDAMOS LA SERIE A UTILIZAR PARA DEFINIR EL TIPO DE FACTURA ELECTRONIC A GENERAR
        if not frappe.db.exists('Serial Configuration For Purchase Invoice', {'parent': str(status_config[1]), 'serie': str(naming_series)}):
            frappe.msgprint(msg=_('La serie utilizada en la factura no se encuentra configurada para Nota de Credito Electronica \
                                   Por favor agreguela en Series Fel de Configuracion Factura Electronica, y vuelva a intentar'),
                            title=_('Proceso no completado'), indicator='red')
            return False, 'No completed'

        # PASO 2: PARA UNA NOTA DEBITO ELEC, ES NECESARIO TENER EL UUID de la factura de venta dada por el proveedor
        if not uuid_purch_inv and not date_inv_origin:
            frappe.msgprint(msg=_(f'Para poder generar correctamente la Nota de Credito Electrónica es necesario tener la serie de factura original \
                            se encuentre generada como electrónica por parte del proveedor'), title=_('Proceso no completado'), indicator='red')

            return False, 'No completed'

        # 2.1 - VALIDAMOS QUE NO SE HAYA GENERANDO ANTEIORMENTE OTRA NOTA DE DEBITO CON LA MISMA DATA
        status_debit_note = check_invoice_records(str(invoice_code))
        if status_debit_note[0] == True:  # Si ya existe en DB
            new_serie_cre = frappe.db.get_value('Envio FEL', {'serie_para_factura': invoice_code}, 'name')
            frappe.msgprint(msg=_(f'La nota de debito que solicitas generar, ya se encuentra registrada como generada en ENVIOS FEL, con UUID {new_serie_cre}'),
                            title=_('Proceso no completado'), indicator='yellow')

            return False, 'No completed'

        # PASO 3: NOTA DE DEBITO ELECTRONICA
        # paso 3.1 - NUEVA INSTANCIA
        new_debit_note = ElectronicDebitNote(invoice_code, status_config[1], naming_series, uuid_purch_inv, date_inv_origin, reason)

        # PASO 3.2 - VALIDA LOS DATOS NECESARIOS PARA CONSTRUIR EL XML
        status = new_debit_note.build_invoice()
        if status[0] == False:  # Si la construccion de la peticion es False
            frappe.msgprint(msg=_(f'Ocurrio un problema en el proceso de crear la petición para nota de debito electronica, mas detalle en: {status[1]}'),
                            title=_('Proceso no completado'), indicator='red')

            return False, 'No completed'

        # PASO 4: FIRMA CERTIFICADA Y ENCRIPTADA
        # En este paso se convierte de JSON a XML y se codifica en base64
        status_firma = new_debit_note.sign_invoice()
        if status_firma[0] == False:  # Si no se firma correctamente
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de firmar Nota de Debito electronica, mas detalles en: {status_firma[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status_firma[1]}'

        # PASO 5: SOLICITAMOS NOTA DE DEBITO ELECTRONICA
        status_facelec = new_debit_note.request_electronic_invoice()
        if status_facelec[0] == False:
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de generar Nota de Debito electronica, mas detalles en: {status_facelec[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return False, f'Ocurrio un problema al tratar de generar Nota de Credito electronica, mas detalles en: {status_facelec[1]}'

        # PASO 6: VALIDAMOS LAS RESPUESTAS Y GUARDAMOS EL RESULTADO POR INFILE
        # Las respuestas en este paso no son de gran importancia solo las respuestas ok seran guardadas
        # automaticamente si todo va bien, aqui se retornara cualquier error que ocurra en la fase
        status_res = new_debit_note.response_validator()
        if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de generar nota de debito electronica con INFILE, mas detalle en {status_res[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return status_res  # return tuple

        # # # PASO 7: ACTUALIZAMOS REGISTROS DE LA BASE DE DATOS
        status_upgrade = new_debit_note.upgrade_records()
        if status_upgrade[0] == False:
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de actualizar registros relacionados al documento, mas detalle en {status_upgrade[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return status_upgrade

        # # PASO 8: SI cumple con exito el flujo de procesos se retorna una tupla, en ella va
        # # el UUID y la nueva serie para la nota de debito
        new_serie = frappe.db.get_value('Envio FEL', {'name': status_upgrade[1]}, 'serie_para_factura')
        frappe.msgprint(msg=_(f'{_("Documento electronico generado exitosamente con identificador")} <b>{status_upgrade[1]}</b>'),
                        title=_('Nota de debito electronica'), indicator='green')

        return True, str(new_serie)

    except:
        return False, str(frappe.get_traceback())


@frappe.whitelist()
def generate_special_invoice(invoice_code, naming_series):
    try:
        # PASO 1: VALIDAMOS QUE EXISTA UNA CONFIGURACION PARA FACTURA ELECTRONICA
        status_config = validate_configuration()

        if status_config[0] == False:
            return status_config

        # PASO 1.1: VALIDAMOS LA SERIE A UTILIZAR PARA DEFINIR EL TIPO DE FACTURA ELECTRONIC A GENERAR
        if not frappe.db.exists('Serial Configuration For Purchase Invoice', {'parent': str(status_config[1]), 'serie': str(naming_series)}):
            frappe.msgprint(msg=_('La serie utilizada en la factura no se encuentra configurada para Factura especial electronica \
                                   Por favor agreguela en Purchase Invoice Series de Configuracion Factura Electronica, y vuelva a intentar'),
                            title=_('Proceso no completado'), indicator='red')
            return False, 'No completed'

        # PASO 2: VALIDA EXISTENCIA DE REGISTROS EN ENVIOS FEL, PARA GENERAR EL DOCUMENTO
        # ES NECESARIO CREARLA SOBRE UN DOCUMENTO ELECTRONICA YA GENERADO
        status_invoice = check_invoice_records(str(invoice_code))
        if status_invoice[0] == True:  # Si ya existe en DB
            frappe.msgprint(msg=_(f'La factura especial se encuentra registrada como ya generada, puedes validar los detalles en \
                                    Envios FEL, con codigo UUID {status_invoice[1]}'),
                            title=_('Proceso no completado'), indicator='yellow')

            return False, 'No completed'

        # PASO 3: FACTURA ESPECIAL ELECTRONICA
        # paso 3.1 - NUEVA INSTANCIA
        new_special_invoice = ElectronicSpecialInvoice(invoice_code, status_config[1], naming_series)

        # PASO 4 - VALIDA LOS DATOS NECESARIOS Y CONSTRUYE EL ESQUEMA JSON PARA LUEGO CONVERTIRLO A XML
        status = new_special_invoice.build_special_invoice()
        if status[0] == False:  # Si la construccion de la peticion es False
            frappe.msgprint(msg=_(f'Ocurrio un problema en el proceso de crear Factura Especial Electronica, mas detalle en: {status[1]}'),
                            title=_('Proceso no completado'), indicator='red')

            return False, 'No completed'

        # PASO 5: FIRMAR CERTIFICAR Y ENCRIPTAR
        # En este paso se convierte de JSON a XML y se codifica en base64
        status_firma = new_special_invoice.sign_invoice()
        if status_firma[0] == False:  # Si no se firma correctamente
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de firmar Factura Especial Electronica, mas detalles en: {status_firma[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status_firma[1]}'

        # # PASO 6: SOLICITAMOS DOCUMENTO ELECTRONICO
        status_facelec = new_special_invoice.request_electronic_invoice()
        if status_facelec[0] == False:
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de generar Factura Especial, mas detalles en: {status_facelec[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return False, f'Ocurrio un problema al tratar de generar factura especial electronica, mas detalles en: {status_facelec[1]}'

        # # PASO 7: VALIDAMOS LAS RESPUESTAS Y GUARDAMOS EL RESULTADO POR INFILE
        # # Las respuestas en este paso no son de gran importancia ya que las respuestas ok, seran guardadas
        # # automaticamente si todo va bien, aqui se retornara cualquier error que ocurra en la fase
        status_res = new_special_invoice.response_validator()
        if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de generar nota de Factura Especial Electronica con INFILE, mas detalle en {status_res[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return status_res  # return tuple

        # # PASO 8: ACTUALIZAMOS REGISTROS DE LA BASE DE DATOS
        status_upgrade = new_special_invoice.upgrade_records()
        if status_upgrade[0] == False:
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de actualizar registros relacionados al documento, mas detalle en {status_upgrade[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return status_upgrade

        # PASO 9: SI cumple con exito el flujo de procesos se retorna una tupla, en ella va
        # # el UUID y la nueva serie para la factura

        new_serie = frappe.db.get_value('Envio FEL', {'name': status_upgrade[1]}, 'serie_para_factura')
        frappe.msgprint(msg=_(f'Documento electronico generado exitosamente con identificador <b>{status_upgrade[1]}</b>'),
                        title=_('Factura especial electronica'), indicator='green')

        return True, str(new_serie)

        # return True, status_upgrade[1]
        # frappe.msgprint(_(str(status_upgrade)))

    except:
        return False, str(frappe.get_traceback())


def validate_configuration():
    """
    Verifica que exista una configuracion valida para generar Factura electronica

    Returns:
        tuple: En primera posicion True/False, segunda posicion mensaje status
    """

    # verifica que exista un documento validado, docstatus = 1 => validado
    if frappe.db.exists('Configuracion Factura Electronica', {'docstatus': 1}):

        configuracion_valida = frappe.db.get_values('Configuracion Factura Electronica',
                                                    filters={'docstatus': 1},
                                                    fieldname=['name', 'regimen'], as_dict=1)
        if (len(configuracion_valida) == 1):
            return (True, str(configuracion_valida[0]['name']))

        elif (len(configuracion_valida) > 1):
            return (False, 'Se encontro mas de una configuración, por favor verifica que solo exista \
                    una en Configuracion Factura Electronia')

    else:
        return (False, 'No se encontro ninguna configuración valida para generacion de facturas electronicas, por favor crea y valida una en \
                        Configuracion Factura Electronica')


def check_invoice_records(invoice_code):
    """
    Verifica las existencias de envios de facturas electronicas en Envio FEL, si no encuentra registro
    da paso a generar una nueva

    Args:
        invoice_code (str): Serie de factura

    Returns:
        tuple: Primera posicion True/False, Segunda poscion: mensaje descriptivo
    """

    # Verifica si existe una factura con la misma serie, evita duplicadas
    if frappe.db.exists('Envio FEL', {'serie_para_factura': invoice_code}):
        facelec = frappe.db.get_values('Envio FEL',  filters={'serie_para_factura': invoice_code},
                                       fieldname=['serie_factura_original', 'uuid', 'serie_para_factura'],
                                       as_dict=1)[0]

        return True, facelec['uuid'], facelec['serie_para_factura'],

    else:
        return False, '', '',


# INICIO EXPORTACIONES ###################################################################################################

# Conector API para usar con otros Frameworks
# PARA GENERAR FACTURA ELECTRONICA FEL EXPORTACION
@frappe.whitelist()
def api_facelec_export(invoice_name, naming_serie):
    """
    Conector API para Exportaciones

    Args:
        invoice_name (str): Nombre de la factura
        naming_serie (str): Serie utilizada en la factura

    Returns:
        tuple: (True/False, msj)
    """

    try:
        # llamamos a la funcion que se encarga de validaciones y finalmente generar facelec
        state_of_facelec = generate_electronic_export_invoice(invoice_name, str(naming_serie))
        if state_of_facelec[0] == False:
            dict_response = {
                'status': 'NO PROCESADO',
                'id_factura': invoice_name,
                'msj': state_of_facelec[1]
            }

            return dict_response

        dict_ok = {
            'status': 'OK',
            'id_factura': invoice_name,
            'uuid': state_of_facelec[1]
        }

        return dict_ok

    except:
        return {
            'status': 'ERROR',
            'id_factura': invoice_name,
            'msj': f'Ocurrio un problema al tratar de generar factura electronica Exportacion, mas info en: {frappe.get_traceback()}'
        }


# API para uso interno con apps hechas con Frappe Framework, Para
# PARA GENERAR FACTURA ELECTRONICA FEL EXPORTACION
@frappe.whitelist()
def api_interface_export(invoice_code, naming_series):
    """
    Usar Para uso interno con otras apps hechas con frappe framework,
    destinada a ser consumida con frappe.call
    llamara a las funciones necesarias para generar factura electronica
    manejando los estados para mostrarlos amigablemente en Front-End

    Args:
        invoice_code (str): Name original de la factura
        naming_series (str): Serie de factura

    Returns:
        tuple, msgprint: (True/False, mensaje ok/descripcion error) usado para javascript,
        el msgprint es para mostrar un mensaje a usuario
    """

    try:
        # Guarda el estado de la funcion encargada de aplicar la generacion de factura electronica
        state_of = generate_electronic_export_invoice(invoice_code, naming_series)
        if state_of[0] == False:
            # Si ocurre algun error en la fase final de facelec
            # Aplica para los mensjaes base de datos actualizados
            if type(state_of[1]) is dict:
                frappe.msgprint(msg=_(f'<code>{state_of[1]}</code>'),
                                title=_('Process not completed'), indicator='red')
                return False, state_of[1]
            else:
                frappe.msgprint(msg=_(f'<code>{state_of[1]}</code>'),
                                title=_('Process not completed'), indicator='red')
                return False, state_of[1]

        # Si el proceso es OK
        if type(state_of[1]) is dict:
            new_serie = frappe.db.get_value('Envio FEL', {'name': state_of[1]["msj"]}, 'serie_para_factura')
            frappe.msgprint(msg=_(f'Electronic invoice generated with universal unique identifier <b>{state_of[1]["msj"]}</b>'),
                            title=_('Process successfully completed'), indicator='green')

            return True, str(new_serie)

        else:
            new_serie = frappe.db.get_value('Envio FEL', {'name': state_of[1]}, 'serie_para_factura')
            frappe.msgprint(msg=_(f'Electronic invoice generated with universal unique identifier <b>{state_of[1]}</b>'),
                            title=_('Process successfully completed'), indicator='green')

            return True, str(new_serie)

    except:
        frappe.msgprint(_(f'Ocurrio un problema mientras procesabamos la peticion, mas info en')+f': <code>{frappe.get_traceback()}</code>')
        return False, 'Ocurrio un problema mientras procesabamos la solicitud para generar Factura Electronica Exportacion'


def generate_electronic_export_invoice(invoice_code, naming_series):
    """
    Llama a la clase y sus metodos encargados de generar factura electronica,
    validando primero los requisitos para que se posible la generacion

    1. Valida si hay configuracion valida para generar factura electronica
    2. valida la serie a utilizar
    3. valida que no exista una anterior ya generada
    4. Crea una instancia para construir facelec
    4.1 Construye la estructura general para la peticion en JSON
    4.2 La estrucutra JSON se convierte a XML para firmarla con la SAT
    4.3 Si la firma es exitosa se solicita la generacion de facelec
    4.4 Se validan las respuestas
    4.5 Actualiza todas las tablas de la base de datos donde existe referencia a la
    factura que se solicito como electronica, con la nueva serie brindada por la SAT


    Args:
        invoice_code (str): Name original de la factura
        naming_series (str): Serie usada en factura

    Returns:
        tuple: True/False, msj, msj
    """

    try:

        # PASO 1: VALIDAMOS QUE EXISTA UNA CONFIGURACION PARA FACTURA ELECTRONICA
        status_config = validate_configuration()

        if status_config[0] == False:
            return status_config

        # PASO 1.1: VALIDAMOS LA SERIE A UTILIZAR PARA DEFINIR EL TIPO DE FACTURA ELECTRONICA A GENERAR
        if not frappe.db.exists('Configuracion Series FEL', {'parent': str(status_config[1]), 'serie': str(naming_series)}):
            return False, f'La serie utilizada en la factura no se encuentra configurada para Factura electronica Exportacion \
                            Por favor agreguela en Series Fel de Configuracion Factura Electronica, y vuelva a intentar'

        # PASO 2: VALIDACION EXTRA PARA NO GENERAR FACTURAS ELECTRONICA EXPORTACION DUPLICADAS, SI OCURRIERA EN ALGUN ESCENARIO
        status_invoice = check_invoice_records(str(invoice_code))
        if status_invoice[0] == True:
            return False, f'La factura se encuentra registrada como ya generada, puedes validar los detalles en \
                            Envios FEL, con codigo UUID {status_invoice[1]}'

        # Validamos que el rate en la tabla de impuestos sea 0, se hace para tener lo mismo en facelec y facelec normal
        if not frappe.db.exists('Sales Taxes and Charges', {'parent': invoice_code, 'parenttype': 'Sales Invoice', 'rate': 0}):
            return False, f'No se puede proceder con la generacion de la factura electronica exportacion, se encontro un valor diferente de 0 \
                            en el impuesto, si desea generarla intente nuevamente manualmente estableciendo 0 al impuesto'

        # PASO 3: FACTURA ELECTRONICA EXPORTACION
        # paso 3.1 - NUEVA INSTANCIA
        new_invoice = ExportInvoice(invoice_code, status_config[1], naming_series)

        # # PASO 3.2 - VALIDA LOS DATOS NECESARIOS PARA CONSTRUIR EL XML
        status = new_invoice.build_invoice()
        if status[0] == False:  # Si la construccion de la peticion es False
            return False, f'Ocurrio un problema en el proceso de generacion XML para peticion, mas detalle en: {status}'


        # PASO 4: FIRMA CERTIFICADA Y ENCRIPTADA
        # En este paso se convierte de JSON a XML y se codifica en base64
        status_firma = new_invoice.sign_invoice()
        if status_firma[0] == False:  # Si no se firma correctamente
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status_firma[1]}'


        # # PASO 5: SOLICITAMOS FACTURA ELECTRONICA EXPORTACION
        status_facelec = new_invoice.request_electronic_invoice()
        if status_facelec[0] == False:
            return False, f'Ocurrio un problema al tratar de generar facturas electronica, mas detalles en: {status_facelec[1]}'

        # PASO 6: VALIDAMOS LAS RESPUESTAS Y GUARDAMOS EL RESULTADO POR INFILE
        # Las respuestas en este paso no son de gran importancia ya que las respuestas ok, seran guardadas
        # automaticamente si todo va bien, aqui se retornara cualquier error que ocurra en la fase
        status_res = new_invoice.response_validator()
        if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
            return status_res  # return tuple

        # PASO 7: ACTUALIZAMOS REGISTROS DE LA BASE DE DATOS
        status_upgrade = new_invoice.upgrade_records()
        if status_upgrade[0] == False:
            return status_upgrade

        # SI cumple con exito el flujo de procesos se retorna una tupla, en ella va
        # el UUID y la nueva serie para la factura
        return True, status_upgrade[1]
        # frappe.msgprint(_(str(status_upgrade)))


        # frappe.msgprint('OK')
        # return True, 'Construccion completa'

    except:
        frappe.msgprint(str(frappe.get_traceback()))
        return False, str(frappe.get_traceback())

# FIN EXPORTACIONES ############################################################################################################


# INICIO FACTURAS EXENTAS DE IMPUESTOS - DESARROLLO NO COMPLETADO PARA ESTA
# APLICA PARA ENTIDADES EXENTAS
@frappe.whitelist()
def generate_exempt_electronic_invoice(invoice_code, naming_series):
    """
        Llama a la clase y sus metodos encargados de generar factura electronica,
        validando primero los requisitos para que se posible la generacion

        1. Valida si hay configuracion valida para generar factura electronica
        2. valida la serie a utilizar
        3. valida que no exista una anterior ya generada
        4. Crea una instancia para construir facelec
        4.1 Construye la estructura general para la peticion en JSON
        4.2 La estrucutra JSON se convierte a XML para firmarla con la SAT
        4.3 Si la firma es exitosa se solicita la generacion de facelec
        4.4 Se validan las respuestas
        4.5 Actualiza todas las tablas de la base de datos donde existe referencia a la
        factura que se solicito como electronica, con la nueva serie brindada por la SAT


        Args:
            invoice_code (str): Name original de la factura
            naming_series (str): Serie usada en factura

        Returns:
            tuple: True/False, msj, msj
    """

    try:

        # PASO 1: VALIDAMOS QUE EXISTA UNA CONFIGURACION PARA FACTURA ELECTRONICA
        status_config = validate_configuration()

        if status_config[0] == False:
            frappe.msgprint(_(status_config[1]))
            return status_config

        # PASO 1.1: VALIDAMOS LA SERIE A UTILIZAR PARA DEFINIR EL TIPO DE FACTURA ELECTRONICA A GENERAR
        if not frappe.db.exists('Configuracion Series FEL', {'parent': str(status_config[1]), 'serie': str(naming_series)}):
            frappe.msgprint(_(f'La serie utilizada en la factura no se encuentra configurada para Factura electronica exenta \
                                Por favor agreguela en Series Fel de Configuracion Factura Electronica, y vuelva a intentar'))
            return False, f'La serie utilizada en la factura no se encuentra configurada para Factura electronica Exenta \
                            Por favor agreguela en Series Fel de Configuracion Factura Electronica, y vuelva a intentar'

        # PASO 2: VALIDACION EXTRA PARA NO GENERAR FACTURAS ELECTRONICA EXPORTACION DUPLICADAS, SI OCURRIERA EN ALGUN ESCENARIO
        status_invoice = check_invoice_records(str(invoice_code))
        if status_invoice[0] == True:
            frappe.msgprint(_(f'La factura se encuentra registrada como ya generada, puedes validar los detalles en \
                                Envios FEL, con codigo UUID {status_invoice[1]}'))
            return False, f'La factura se encuentra registrada como ya generada, puedes validar los detalles en \
                            Envios FEL, con codigo UUID {status_invoice[1]}'

        # PASO 3: FACTURA ELECTRONICA EXPORTACION
        # paso 3.1 - NUEVA INSTANCIA
        new_invoice = ExemptElectronicInvoice(invoice_code, status_config[1], naming_series)

        # # PASO 3.2 - VALIDA LOS DATOS NECESARIOS PARA CONSTRUIR EL XML
        status = new_invoice.build_invoice()
        if status[0] == False:  # Si la construccion de la peticion es False
            frappe.msgprint(_(f'Ocurrio un problema en el proceso, mas detalle en: {status}'))
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status}'


        # PASO 4: FIRMA CERTIFICADA Y ENCRIPTADA
        # En este paso se convierte de JSON a XML y se codifica en base64
        status_firma = new_invoice.sign_invoice()
        if status_firma[0] == False:  # Si no se firma correctamente
            frappe.msgprint(_(f'Ocurrio un problema en el proceso, mas detalle en: {status_firma[1]}'))
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status_firma[1]}'


        # # PASO 5: SOLICITAMOS FACTURA ELECTRONICA EXPORTACION
        status_facelec = new_invoice.request_electronic_invoice()
        if status_facelec[0] == False:
            frappe.msgprint(_(f'Ocurrio un problema al tratar de generar factura electronica Exportacion, mas detalles en: {status_facelec[1]}'))
            return False, f'Ocurrio un problema al tratar de generar factura electronica Exportacion, mas detalles en: {status_facelec[1]}'


        # PASO 6: VALIDAMOS LAS RESPUESTAS Y GUARDAMOS EL RESULTADO POR INFILE
        # Las respuestas en este paso no son de gran importancia ya que las respuestas ok, seran guardadas
        # automaticamente si todo va bien, aqui se retornara cualquier error que ocurra en la fase
        # status_res = new_invoice.response_validator()
        # if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
        #     return status_res  # return tuple

        # PASO 7: ACTUALIZAMOS REGISTROS DE LA BASE DE DATOS
        # status_upgrade = new_invoice.upgrade_records()
        # if status_upgrade[0] == False:
        #     return status_upgrade

        # SI cumple con exito el flujo de procesos se retorna una tupla, en ella va
        # el UUID y la nueva serie para la factura
        # return True, status_upgrade[1]
        # frappe.msgprint(_(str(status_upgrade)))


        frappe.msgprint('OK')
        return True, 'test'

    except:
        frappe.msgprint(str(frappe.get_traceback()))
        return False, str(frappe.get_traceback())
# FIN FACTURAS EXENTAS DE IMPUESTOS


@frappe.whitelist()
def is_valid_to_fel(doctype, docname):
    """
    Validador de escenarios para mostrar u ocultar botones para generar docs electronicos
    Factura FEL, Anulador, Nota de Credito, etc.

    Args:
        doctype (str): Nombre doctype
        docname (str): Nombre del doc
    """

    # FACT, FACTEXP, NCRED, FESP, NDEB, CANCEL
    status_list = ['Credit Note Issued', 'Debit Note Issued', 'Return']
    stat = validate_configuration()
    docinv = frappe.get_doc(doctype, {'name': docname})

    if stat[0] == True:
        config_name = stat[1]
    else:
        return stat

    val_serie = frappe.db.exists('Configuracion Series FEL', {'parent': config_name, 'serie': docinv.naming_series})
    val_serie_pi = frappe.db.exists('Serial Configuration For Purchase Invoice', {'parent': config_name, 'serie': docinv.naming_series})

    # DOCTYPE SALES INVOICE
    # Condiciones para FEL Sales Invoice -> FEL Normal
    if (docinv.doctype == 'Sales Invoice') and (docinv.docstatus == 1) and (docinv.status not in status_list) and \
        (not docinv.is_it_an_international_invoice):
        # Validacion de serie
        val_serie_fel = frappe.db.exists('Configuracion Series FEL', {'parent': config_name, 'serie': docinv.naming_series,
                                                                      'codigo_incoterm': ['==', '']})
        active = frappe.db.exists('Configuracion Factura Electronica', {'name': config_name, 'factura_venta_fel': 1})

        if val_serie_fel and active:
            values = frappe.db.get_values('Configuracion Series FEL',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'valido', True
        else:
            return _('Serie de factura no configurada, por favor agregarla y \
                activarla en configuración Factura Electrónica para generar documento FEL'), False, False

    # Condiciones para FEL Sales Invoice -> Factura Exportación
    elif (docinv.doctype == 'Sales Invoice') and (docinv.docstatus == 1) and (docinv.status not in status_list) and \
        (docinv.is_it_an_international_invoice):
        # Validacion de serie
        val_serie_exp = frappe.db.exists('Configuracion Series FEL', {'parent': config_name, 'serie': docinv.naming_series,
                                                                      'codigo_incoterm': ['!=', '']})
        active = frappe.db.exists('Configuracion Factura Electronica', {'name': config_name, 'factura_exportacion_fel': 1})

        if val_serie and active:
            values = frappe.db.get_values('Configuracion Series FEL',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'export', True
        else:
            return _('Serie de factura no configurada, por favor agregarla y \
                     activarla en configuración Factura Electrónica para generar documento FEL Exportación'), False, False

    # Condiciones para FEL Sales Invoice -> Nota Credito
    elif (docinv.doctype == 'Sales Invoice') and (docinv.docstatus == 1) and (docinv.is_return == 1) and \
        (docinv.return_against):

        # Validacion de serie
        active = frappe.db.exists('Configuracion Factura Electronica', {'name': config_name, 'nota_credito_fel': 1})

        if val_serie and active:
            values = frappe.db.get_values('Configuracion Series FEL',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'valido', True
        else:
            return _('Serie de documento para nota de credito electrónica no configurada, \
                por favor agregarla y activarla en configuración Factura Electrónica para generar documento FEL'), False, False

    # Condiciones para FEL Sales Invoice -> Cancelador de FEl Normal, Exportacion, Nota de credito
    elif (docinv.doctype in ['Sales Invoice', 'Purchase Invoice']) and (docinv.docstatus == 2) and (docinv.numero_autorizacion_fel):

        # Validacion de serie
        active = frappe.db.exists('Configuracion Factura Electronica', {'name': config_name,
                                                                        'anulador_de_facturas_ventas_fel': 1})

        if val_serie and active:  # Sales Invoice
            values = frappe.db.get_values('Configuracion Series FEL',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'anulador', True

        elif val_serie_pi and active:  # Purchase Invoice
            values = frappe.db.get_values('Serial Configuration For Purchase Invoice',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'anulador', True

        else:
            return _('Serie de documento para nota de credito electrónica no configurada, \
                     por favor agregarla y activarla en configuración Factura Electrónica para generar documento FEL'), False

    # FACTURA CAMBIARIA
    elif (docinv.doctype == 'Sales Invoice') and (docinv.docstatus == 1) and (docinv.status not in status_list) and \
        (not docinv.is_it_an_international_invoice):
        # Validacion de serie
        val_serie_fel = frappe.db.exists('Configuracion Series FEL', {'parent': config_name, 'serie': docinv.naming_series,
                                                                      'codigo_incoterm': ['==', '']})
        active = frappe.db.exists('Configuracion Factura Electronica', {'name': config_name, 'factura_cambiaria_fel': 1})

        if val_serie_fel and active:
            values = frappe.db.get_values('Configuracion Series FEL',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'valido', True
        else:
            return _('Serie de factura no configurada, por favor agregarla y \
                activarla en configuración Factura Electrónica para generar documento FEL'), False, False


    # DOCTYPE PURCHASE INVOICES
    # Condiciones para FEL Purchase Invoice - Factura Especial
    elif (docinv.doctype == 'Purchase Invoice') and (docinv.docstatus == 1) and (docinv.status not in status_list):

        # Validacion de serie
        active = frappe.db.exists('Configuracion Factura Electronica', {'name': config_name, 'factura_especial_fel': 1})

        if val_serie_pi and active:
            values = frappe.db.get_values('Serial Configuration For Purchase Invoice',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'valido', True
        else:
            return _('Serie de factura no configurada, por favor agregarla y activarla \
                     en configuración Factura Electrónica para generar documento FEL'), False, False

    # NOTAS DEBITO
    elif (docinv.doctype == 'Purchase Invoice') and (docinv.docstatus == 1) and (docinv.is_return == 1) and \
        (docinv.bill_no) and (docinv.bill_date) and (docinv.return_against):

        # Validacion de serie
        active = frappe.db.exists('Configuracion Factura Electronica', {'name': config_name, 'nota_de_debito_electronica': 1})

        if val_serie_pi and active:
            values = frappe.db.get_values('Serial Configuration For Purchase Invoice',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'valido', True
        else:
            return _('Serie de factura no configurada, por favor agregarla y activarla \
                     en configuración Factura Electrónica para generar documento FEL'), False, False

    return False, False, False,


# ------------------------------------------------------------------------------------------------------------
# REFACTOR OK
# ------------------------------------------------------------------------------------------------------------

@frappe.whitelist()
def validate_config_fel(company):
    """Valida y retorna que configuracion se encuentra activa para la compañia/establecimiento

    Args:
        company (str): nombre de la compañia en el doc

    Returns:
        tuple: bool/str
    """
    # Guarda las posibles configuraciones para X Compania
    list_config = frappe.db.get_list('Configuracion Factura Electronica', filters={'docstatus': 1, 'company': company},
                                     fields=['count(name) as count', 'name'])[0]

    if list_config.get('count') > 1:
        return False, f'Existe mas de una configuracion para la compañia {company}, solo se permite 1 configuracion validada por compañia'

    if list_config.get('count') == 0:
        return False, f'No existe ninguna configuracion para la compañia {company}'

    if list_config.get('count') == 1:
        # status/nombre de la config valida
        return True, list_config.get('name')


@frappe.whitelist()
def btn_validator(doctype, docname):
    """Valida que tipo de boton se deben mostrar en la factura segun la serie y configuracion
        NOTA: La validacion se hace en backend para obtener datos sin manipulacion

    Args:
        doctype (str): doctype name
        docname (str): PK name

    Returns:
        dict: status
    """
    # FACT, FACTEXP, NCRED, FESP, NDEB, CANCEL
    doc = frappe.get_doc(doctype, {'name': docname})
    status_list = ['Credit Note Issued', 'Debit Note Issued', 'Return']

    config = validate_config_fel(doc.company)
    if not config[0]:
        return {'type_doc': ''}

    # Obtiene informacion de los tipos de generadores activos en la configuracion
    options = ['factura_venta_fel', 'nota_credito_fel', 'anulador_de_facturas_ventas_fel', 'factura_exportacion_fel',
               'nota_de_debito_electronica', 'factura_cambiaria_fel', 'factura_especial_fel', 'factura_electronica_fel_pos']
    options_fel = frappe.db.get_list('Configuracion Factura Electronica', filters={'name': config[1]}, fields=options)[0]

    # Anulador de docs electronicos: Aplica para cualquier doc electronico
    if doc.docstatus == 2 and doc.numero_autorizacion_fel and options_fel['anulador_de_facturas_ventas_fel'] == 1:
        is_cancelled = invoice_exists(doc.numero_autorizacion_fel)

        if doctype == 'Sales Invoice' and not is_cancelled:  # Si no esta cancelada
            type_doc_fel = frappe.db.get_value('Configuracion Series FEL', {'parent': config[1], 'serie': doc.naming_series}, 'tipo_documento')
            return {'type_doc': 'anulador_si', 'show_btn': True}
        if doctype == 'Sales Invoice' and is_cancelled:  # Si ya esta cancelada
            type_doc_fel = frappe.db.get_value('Configuracion Series FEL', {'parent': config[1], 'serie': doc.naming_series}, 'tipo_documento')
            return {'type_doc': 'anulador_si', 'show_btn': False}

        if doctype == 'Purchase Invoice' and not is_cancelled:
            type_doc_fel = frappe.db.get_value('Serial Configuration For Purchase Invoice',
                                               {'parent': config[1], 'serie': doc.naming_series}, 'tipo_documento')
            return {'type_doc': 'anulador_pi', 'show_btn': True}
        if doctype == 'Purchase Invoice' and is_cancelled:
            type_doc_fel = frappe.db.get_value('Serial Configuration For Purchase Invoice',
                                               {'parent': config[1], 'serie': doc.naming_series}, 'tipo_documento')
            return {'type_doc': 'anulador_pi', 'show_btn': False}

    # Validacion para Doctype SALES INVOICE
    if doctype == 'Sales Invoice' and doc.docstatus == 1:
        # Factura Venta FEL Normal y Factura Cambiaria
        if ((doc.status not in status_list) and (not doc.is_it_an_international_invoice) and
                (options_fel['factura_venta_fel'] == 1 or options_fel['factura_cambiaria_fel'] == 1)):
            type_doc_fel = frappe.db.get_value('Configuracion Series FEL', {'parent': config[1], 'serie': doc.naming_series}, 'tipo_documento')
            # Puede ser cambiaria o normal
            if type_doc_fel == 'FCAM':
                return {'type_doc': 'cambiaria'}
            if type_doc_fel == 'FACT':
                return {'type_doc': 'factura_fel'}

        # Factura Venta FEL - Exportacion
        if (doc.status not in status_list) and doc.is_it_an_international_invoice and options_fel['factura_exportacion_fel'] == 1:
            type_doc_fel = frappe.db.get_value('Configuracion Series FEL', {'parent': config[1], 'serie': doc.naming_series,
                                                                            'es_exportacion': 1}, 'tipo_documento')
            if type_doc_fel == 'FACT':
                return {'type_doc': 'exportacion'}

        # Nota de Credito FEL
        if doc.is_return == 1 and doc.return_against and options_fel['nota_credito_fel'] == 1:
            type_doc_fel = frappe.db.get_value('Configuracion Series FEL', {'parent': config[1], 'serie': doc.naming_series}, 'tipo_documento')
            if type_doc_fel == 'NCRE':
                return {'type_doc': 'nota_credito'}

    # Validacion para Doctype PURCHASE INVOICE
    if doctype == 'Purchase Invoice' and doc.docstatus == 1:
        # Factura Especial
        if (doc.status not in status_list) and options_fel['factura_especial_fel'] == 1:
            type_doc_fel = frappe.db.get_value('Serial Configuration For Purchase Invoice',
                                               {'parent': config[1], 'serie': doc.naming_series}, 'tipo_documento')
            if type_doc_fel == 'FESP':
                return {'type_doc': 'factura_especial'}

        # Nota de Debito
        if doc.is_return == 1 and doc.bill_no and doc.bill_date and doc.return_against:
            type_doc_fel = frappe.db.get_value('Serial Configuration For Purchase Invoice',
                                               {'parent': config[1], 'serie': doc.naming_series}, 'tipo_documento')
            if type_doc_fel == 'NDEB':
                return {'type_doc': 'nota_debito'}

    # SI no aplica a ninguna condicion
    return {'type_doc': ''}


@frappe.whitelist()
def invoice_exists(uuid):
    """Valida si el documento electronico se encuentra como cancelado en Envios FEL
    segun su UUID

    Args:
        uuid (str): Identificador único universal

    Returns:
        bool: true/false
    """
    if frappe.db.exists('Envio FEL', {'name': uuid, 'status': 'Cancelled'}):
        return True
    else:
        return False


@frappe.whitelist()
def api_generate_sales_invoice_fel(invoice_name, company, naming_series):
    """Generador de Factura Electronica para Facturas de Venta

    Args:
        invoice_name (str): `name` de la factura
        company (str): nombre de la compañia
        naming_series (str): serie utilizada para la factura

    Returns:
        dict: estado de la operacion
    """
    try:
        # 1 - VALIDACION EXISTENCIA DE FACTURA EN ENVIOS FEL: PARA EVITAR DUPLICIDAD EN CASO SE DE EL ESCENARIO
        status_invoice = check_invoice_records(invoice_name)
        if status_invoice[0]:
            return {
                'status': False,
                'description': f'{_("La factura ya se encuentra generada como FEL con codigo UUID")} <strong>{status_invoice[1]}</strong>',
                'uuid': status_invoice[1],
                'serie_fel': status_invoice[2],
                'indicator': 'yellow',
                'error': '',
                'title': _('Factura ya generada como FEL')
            }

        # 2 - VALIDACION CONFIGURACION VALIDA (PUEDE HABER 1 POR COMPANY)
        config = validate_config_fel(company)
        if not config[0]:
            return {
                'status': False,
                'description': _('No se encontro una configuracion valida de FACELEC para la empresa'),
                'uuid': '',
                'serie_fel': '',
                'indicator': 'yellow',
                'error': '',
                'title': _('Factura Electronica No Configurada')
            }

        # 3 - Se crea una instancia de la clase FacturaElectronica para generarla
        new_invoice = ElectronicInvoice(invoice_name, config[1], naming_series)

        # 4 - Se valida y construye la peticion para INFILE en formato JSON
        build_inv = new_invoice.build_invoice()
        if not build_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': build_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': build_inv.get('error'),
                'indicator': 'red',
                'title': _('Datos necesarios para generar factura no procesados')
            }

        # 5 - INFILE valida y firma los datos de la peticion (La peticion se convierte a XML)
        sign_inv = new_invoice.sign_invoice()
        if not sign_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': sign_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': sign_inv.get('error'),
                'indicator': 'red',
                'title': _('Datos no validados por INFILE')
            }

        # 6 - Con la peticion firmada y validada, se solicita la generacion del FEL
        req_inv = new_invoice.request_electronic_invoice()
        if not req_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': req_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': req_inv.get('error'),
                'indicator': 'red',
                'title': _('Factura Electronica No Generada')
            }

        # 7 - Se valida la respuesta del FEL
        # En esta fase se valida si hay errores en la respuesta por parte FEL
        res_validate = new_invoice.response_validator()
        if not res_validate.get('status'):  # True/False
            return {
                'status': False,
                'description': res_validate.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': res_validate.get('error'),
                'indicator': 'red',
                'title': _('Datos Recibidos por INFILE no validos')
            }

        # 8 - Si la generacion con INFILE fue exitosa, se actualizan las referencia en el ERP
        upgrade_inv = new_invoice.upgrade_records()
        if not upgrade_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': upgrade_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': upgrade_inv.get('error'),
                'indicator': 'red',
                'title': _('Referencias de la factura no fueron actualizadas por completo')
            }

        # 9 - Si la ejecucion llega a este punto, es decir que todas las fases se ejecutaron correctamente, se genera una respuesta positiva
        if upgrade_inv.get('status') and upgrade_inv.get('uuid'):
            msg_ok = f'Factura Electronica generada correctamente con codigo UUID {upgrade_inv.get("uuid")}\
                y serie {upgrade_inv.get("serie")}'
            return {
                'status': True,
                'description': msg_ok,
                'uuid': upgrade_inv.get('uuid'),
                'serie_fel': upgrade_inv.get('serie'),
                'indicator': 'green',
                'error': '',
                'title': _('Factura Electronica Generada')
            }

    except Exception:
        frappe.throw(_(f"Error al generar la factura electrónica. Mas detalles en el siguiente log: <hr> {frappe.get_traceback()}"))
        return


@frappe.whitelist()
def api_generate_exchange_invoice_fel(invoice_name, company, naming_series):
    """Generador de Factura Electronica Cambiaria para Facturas de Venta

    Args:
        invoice_name (str): `name` de la factura
        company (str): nombre de la compañia
        naming_series (str): serie utilizada para la factura

    Returns:
        dict: estado de la operacion
    """
    try:
        # 1 - VALIDACION EXISTENCIA DE FACTURA EN ENVIOS FEL: PARA EVITAR DUPLICIDAD EN CASO SE DE EL ESCENARIO
        status_invoice = check_invoice_records(invoice_name)
        if status_invoice[0]:
            return {
                'status': False,
                'description': f'{_("La factura ya se encuentra generada como FEL con codigo UUID")} <strong>{status_invoice[1]}</strong>',
                'uuid': status_invoice[1],
                'serie_fel': status_invoice[2],
                'indicator': 'yellow',
                'error': '',
                'title': _('Factura ya generada como FEL')
            }

        # 2 - VALIDACION CONFIGURACION VALIDA (PUEDE HABER 1 POR COMPANY)
        config = validate_config_fel(company)
        if not config[0]:
            return {
                'status': False,
                'description': _('No se encontro una configuracion valida de FACELEC para la empresa'),
                'uuid': '',
                'serie_fel': '',
                'indicator': 'yellow',
                'error': '',
                'title': _('Factura Electronica No Configurada')
            }

        # 3 - Se crea una instancia de la clase FacturaElectronica para generarla
        new_invoice = SalesExchangeInvoice(invoice_name, config[1], naming_series)

        # 4 - Se valida y construye la peticion para INFILE en formato JSON
        build_inv = new_invoice.build_invoice()
        if not build_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': build_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': build_inv.get('error'),
                'indicator': 'red',
                'title': _('Datos necesarios para generar factura no procesados')
            }

        # 5 - INFILE valida y firma los datos de la peticion (La peticion se convierte a XML)
        sign_inv = new_invoice.sign_invoice()
        if not sign_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': sign_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': sign_inv.get('error'),
                'indicator': 'red',
                'title': _('Datos no validados por INFILE')
            }

        # 6 - Con la peticion firmada y validada, se solicita la generacion del FEL
        req_inv = new_invoice.request_electronic_invoice()
        if not req_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': req_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': req_inv.get('error'),
                'indicator': 'red',
                'title': _('Factura Electronica No Generada')
            }

        # 7 - Se valida la respuesta del FEL
        # En esta fase se valida si hay errores en la respuesta por parte FEL
        res_validate = new_invoice.response_validator()
        if not res_validate.get('status'):  # True/False
            return {
                'status': False,
                'description': res_validate.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': res_validate.get('error'),
                'indicator': 'red',
                'title': _('Datos Recibidos por INFILE no validos')
            }

        # 8 - Si la generacion con INFILE fue exitosa, se actualizan las referencia en el ERP
        upgrade_inv = new_invoice.upgrade_records()
        if not upgrade_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': upgrade_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': upgrade_inv.get('error'),
                'indicator': 'red',
                'title': _('Referencias de la factura no fueron actualizadas por completo')
            }

        # 9 - Si la ejecucion llega a este punto, es decir que todas las fases se ejecutaron correctamente, se genera una respuesta positiva
        if upgrade_inv.get('status') and upgrade_inv.get('uuid'):
            msg_ok = f'Factura Electronica generada correctamente con codigo UUID {upgrade_inv.get("uuid")}\
                y serie {upgrade_inv.get("serie")}'
            return {
                'status': True,
                'description': msg_ok,
                'uuid': upgrade_inv.get('uuid'),
                'serie_fel': upgrade_inv.get('serie'),
                'indicator': 'green',
                'error': '',
                'title': _('Factura Electronica Cambiaria Generada')
            }

    except Exception:
        frappe.throw(_(f"Error al generar la factura electrónica cambiaria. Mas detalles en el siguiente log: <hr> {frappe.get_traceback()}"))
        return


@frappe.whitelist()
def fel_doc_canceller(company, invoice_name, reason_cancelation='Anulación', document='Sales Invoice'):
    """Anulador de documentos electronicos

    Args:
        company (str): company
        invoice_name (str): PK de la factura
        reason_cancelation (str, optional): Razon de anulacion de doc. Defaults to 'Anulación'.
        document (str, optional): Sales Invoice/Purchase Invoice. Defaults to 'Sales Invoice'.

    Returns:
        dict: _description_
    """
    config = validate_config_fel(company)
    if not config[0]:
        return {
            'status': False,
            'description': _('No se encontro una configuracion valida de FACELEC para la empresa'),
            'uuid': '',
            'serie_fel': '',
            'indicator': 'yellow',
            'error': '',
            'title': _('Factura Electronica No Configurada')
        }

    cancel_invoice = CancelDocument(invoice_name, config[1], reason_cancelation, document)

    # Se validan los requerimientos para anular X documento
    status_req = cancel_invoice.validate_requirements()
    if not status_req.get('status'):
        return {
            'status': False,
            'description': status_req.get('description'),
            'uuid': '',
            'serie_fel': '',
            'indicator': 'yellow',
            'error': '',
            'title': _('Documento Electronico No Anulado')
        }

    # Se construye la peticion para anular X documento
    status_build = cancel_invoice.build_request()
    if not status_build.get('status'):
        return {
            'status': False,
            'description': status_build.get('description'),
            'uuid': '',
            'serie_fel': '',
            'indicator': 'red',
            'error': status_build.get('error'),
            'title': _('Peticion XML no generada')
        }

    # Se firma y valida la peticion
    status_firma = cancel_invoice.sign_invoice()
    if not status_firma.get('status'):
        return {
            'status': False,
            'description': status_firma.get('description'),
            'uuid': '',
            'serie_fel': '',
            'indicator': 'red',
            'error': status_firma.get('error'),
            'title': _('Documento No Validado y Firmado')
        }

    # Se anula el documento
    status_process = cancel_invoice.request_cancel()
    if not status_process.get('status'):
        return {
            'status': False,
            'description': status_process.get('description'),
            'uuid': '',
            'serie_fel': '',
            'indicator': 'red',
            'error': status_process.get('error'),
            'title': _('Peticion no completada')
        }

    # Se validan las posibles respuestas
    status_validador_res = cancel_invoice.response_validator()
    if not status_validador_res.get('status'):
        return {
            'status': False,
            'description': status_validador_res.get('description'),
            'uuid': '',
            'serie_fel': '',
            'indicator': 'red',
            'error': status_validador_res.get('error'),
            'title': _('Respuesta de INFILE no valida')
        }

    # Si el doc se anula correctamente
    else:
        return {
            'status': True,
            'description': _('Documento anulado, presione boton para ver PDF'),
            'uuid': '',
            'serie_fel': '',
            'indicator': 'green',
            'error': '',
            'title': _('Documento Anulado Correctamente')
        }


@frappe.whitelist()
def api_generate_credit_note_fel(credit_note_name, company, naming_series, inv_original, reason):
    """Generador de Notas de Credito para Facturas de Venta

    Args:
        invoice_name (str): `name` de la factura
        company (str): nombre de la compañia
        naming_series (str): serie utilizada para la factura

    Returns:
        dict: estado de la operacion
    """
    try:
        # 1 - VALIDACION EXISTENCIA DE FACTURA EN ENVIOS FEL: PARA EVITAR DUPLICIDAD EN CASO SE DE EL ESCENARIO
        status_invoice = check_invoice_records(inv_original)
        if not status_invoice[0]:  # Se debe realizar sobre un doc ya generado
            return {
                'status': False,
                'description': _("Para generar una nota de credito FEL es necesario hacerlo sobre una factura electronica ya generada"),
                'uuid': '',
                'serie_fel': '',
                'indicator': 'yellow',
                'error': '',
                'title': _('Nota de credito FEL no generada')
            }

        # 2 - VALIDACION CONFIGURACION VALIDA (PUEDE HABER 1 POR COMPANY)
        config = validate_config_fel(company)
        if not config[0]:
            return {
                'status': False,
                'description': _('No se encontro una configuracion valida de FACELEC para la empresa'),
                'uuid': '',
                'serie_fel': '',
                'indicator': 'yellow',
                'error': '',
                'title': _('Factura Electronica No Configurada')
            }

        # 3 - Se crea una instancia de la clase ElectronicCreditNote para generarla
        new_cred_note = ElectronicCreditNote(credit_note_name, inv_original, config[1], naming_series, reason)

        # 4 - Se valida y construye la peticion para INFILE en formato JSON
        build_inv = new_cred_note.build_invoice()
        if not build_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': build_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': build_inv.get('error'),
                'indicator': 'red',
                'title': _('Datos necesarios para generar factura no procesados')
            }

        # 5 - INFILE valida y firma los datos de la peticion (La peticion se convierte a XML)
        sign_inv = new_cred_note.sign_invoice()
        if not sign_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': sign_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': sign_inv.get('error'),
                'indicator': 'red',
                'title': _('Datos no validados por INFILE')
            }

        # 6 - Con la peticion firmada y validada, se solicita la generacion del FEL
        req_inv = new_cred_note.request_electronic_invoice()
        if not req_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': req_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': req_inv.get('error'),
                'indicator': 'red',
                'title': _('Factura Electronica No Generada')
            }

        # 7 - Se valida la respuesta del FEL
        # En esta fase se valida si hay errores en la respuesta por parte FEL
        res_validate = new_cred_note.response_validator()
        if not res_validate.get('status'):  # True/False
            return {
                'status': False,
                'description': res_validate.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': res_validate.get('error'),
                'indicator': 'red',
                'title': _('Datos Recibidos por INFILE no validos')
            }

        # 8 - Si la generacion con INFILE fue exitosa, se actualizan las referencia en el ERP
        upgrade_inv = new_cred_note.upgrade_records()
        if not upgrade_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': upgrade_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': upgrade_inv.get('error'),
                'indicator': 'red',
                'title': _('Referencias de la factura no fueron actualizadas por completo')
            }

        # 9 - Si la ejecucion llega a este punto, es decir que todas las fases se ejecutaron correctamente, se genera una respuesta positiva
        if upgrade_inv.get('status') and upgrade_inv.get('uuid'):
            msg_ok = f'Factura Electronica generada correctamente con codigo UUID {upgrade_inv.get("uuid")}\
                y serie {upgrade_inv.get("serie")}'
            return {
                'status': True,
                'description': msg_ok,
                'uuid': upgrade_inv.get('uuid'),
                'serie_fel': upgrade_inv.get('serie'),
                'indicator': 'green',
                'error': '',
                'title': _('Factura Electronica Cambiaria Generada')
            }

    except Exception:
        frappe.throw(_(f"Error al generar la factura electrónica cambiaria. Mas detalles en el siguiente log: <hr> {frappe.get_traceback()}"))
        return


@frappe.whitelist()
def api_generate_special_invoice_fel(credit_note_name, company, naming_series, inv_original, reason):
    """Generador de Notas de Credito para Facturas de Venta

    Args:
        invoice_name (str): `name` de la factura
        company (str): nombre de la compañia
        naming_series (str): serie utilizada para la factura

    Returns:
        dict: estado de la operacion
    """
    try:
        # 1 - VALIDACION EXISTENCIA DE FACTURA EN ENVIOS FEL: PARA EVITAR DUPLICIDAD EN CASO SE DE EL ESCENARIO
        status_invoice = check_invoice_records(inv_original)
        if not status_invoice[0]:  # Se debe realizar sobre un doc ya generado
            return {
                'status': False,
                'description': _("Para generar una nota de credito FEL es necesario hacerlo sobre una factura electronica ya generada"),
                'uuid': '',
                'serie_fel': '',
                'indicator': 'yellow',
                'error': '',
                'title': _('Nota de credito FEL no generada')
            }

        # 2 - VALIDACION CONFIGURACION VALIDA (PUEDE HABER 1 POR COMPANY)
        config = validate_config_fel(company)
        if not config[0]:
            return {
                'status': False,
                'description': _('No se encontro una configuracion valida de FACELEC para la empresa'),
                'uuid': '',
                'serie_fel': '',
                'indicator': 'yellow',
                'error': '',
                'title': _('Factura Electronica No Configurada')
            }

        # 3 - Se crea una instancia de la clase ElectronicCreditNote para generarla
        new_cred_note = ElectronicCreditNote(credit_note_name, inv_original, config[1], naming_series, reason)

        # 4 - Se valida y construye la peticion para INFILE en formato JSON
        build_inv = new_cred_note.build_invoice()
        if not build_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': build_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': build_inv.get('error'),
                'indicator': 'red',
                'title': _('Datos necesarios para generar factura no procesados')
            }

        # 5 - INFILE valida y firma los datos de la peticion (La peticion se convierte a XML)
        sign_inv = new_cred_note.sign_invoice()
        if not sign_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': sign_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': sign_inv.get('error'),
                'indicator': 'red',
                'title': _('Datos no validados por INFILE')
            }

        # 6 - Con la peticion firmada y validada, se solicita la generacion del FEL
        req_inv = new_cred_note.request_electronic_invoice()
        if not req_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': req_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': req_inv.get('error'),
                'indicator': 'red',
                'title': _('Factura Electronica No Generada')
            }

        # 7 - Se valida la respuesta del FEL
        # En esta fase se valida si hay errores en la respuesta por parte FEL
        res_validate = new_cred_note.response_validator()
        if not res_validate.get('status'):  # True/False
            return {
                'status': False,
                'description': res_validate.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': res_validate.get('error'),
                'indicator': 'red',
                'title': _('Datos Recibidos por INFILE no validos')
            }

        # 8 - Si la generacion con INFILE fue exitosa, se actualizan las referencia en el ERP
        upgrade_inv = new_cred_note.upgrade_records()
        if not upgrade_inv.get('status'):  # True/False
            return {
                'status': False,
                'description': upgrade_inv.get('description'),
                'uuid': '',
                'serie_fel': '',
                'error': upgrade_inv.get('error'),
                'indicator': 'red',
                'title': _('Referencias de la factura no fueron actualizadas por completo')
            }

        # 9 - Si la ejecucion llega a este punto, es decir que todas las fases se ejecutaron correctamente, se genera una respuesta positiva
        if upgrade_inv.get('status') and upgrade_inv.get('uuid'):
            msg_ok = f'Factura Electronica generada correctamente con codigo UUID {upgrade_inv.get("uuid")}\
                y serie {upgrade_inv.get("serie")}'
            return {
                'status': True,
                'description': msg_ok,
                'uuid': upgrade_inv.get('uuid'),
                'serie_fel': upgrade_inv.get('serie'),
                'indicator': 'green',
                'error': '',
                'title': _('Factura Electronica Cambiaria Generada')
            }

    except Exception:
        frappe.throw(_(f"Error al generar la factura electrónica cambiaria. Mas detalles en el siguiente log: <hr> {frappe.get_traceback()}"))
        return


@frappe.whitelist()
def fel_generator(doctype, docname, type_doc, docname_ref="", reason=""):
    """Valida que tipo de doc electronico se debe generar

    Args:
        doctype (str): nombre doctype
        docname (str): name del documento
        type_doc (str): tipo de doc electronico a generar

    Returns:
        dict: status operacion
    """

    naming_series = frappe.db.get_value(doctype, {'name': docname}, 'naming_series')
    company = frappe.db.get_value(doctype, {'name': docname}, 'company')

    if doctype == 'Sales Invoice':
        if type_doc == 'factura_fel':  # Factura Normal
            fel_si = api_generate_sales_invoice_fel(docname, company, naming_series)
            return fel_si

        if type_doc == 'cambiaria':  # Factura Cambiaria
            exchange_inv = api_generate_exchange_invoice_fel(docname, company, naming_series)
            return exchange_inv

        if type_doc == 'nota_credito':  # Nota de Credito
            credit_note = api_generate_credit_note_fel(docname, company, naming_series, docname_ref, reason)
            return credit_note

        # TODO: ES NECESARIO TENER CREDENCIALES DE UNA EMPRESA QUE APLIQUE ESTE TIPO DE DOCS
        # Y HACER PRUEBAS CON CREDENCIALES, EN DOLARES Y GTQ
        if type_doc == 'exportacion':  # Factura Exportacion
            pass
            # credit_note = api_generate_credit_note_fel(docname, company, naming_series, docname_ref, reason)
            # return credit_note

        # TODO: ES NECESARIO TENER CREDENCIALES DE UNA EMPRESA QUE APLIQUE ESTE TIPO DE DOCS
        if type_doc == 'exenta':  # Factura Exenta de impuestos
            pass
            # credit_note = api_generate_credit_note_fel(docname, company, naming_series, docname_ref, reason)
            # return credit_note

    if doctype == 'Purchase Invoice':
        if type_doc == 'factura_especial':
            special_inv = api_generate_special_invoice_fel(docname, company, naming_series, docname_ref, reason)
            return special_inv

    else:
        return {'status': False}
