# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

# import datetime
import json
import time

import frappe
from factura_electronica.controllers.journal_entry_special import JournalEntrySpecialISR
from factura_electronica.fel.credit_note import ElectronicCreditNote
# from timeit import default_timer as timer usar para medir tiempo ejecucion
from factura_electronica.fel.fel import ElectronicInvoice
from factura_electronica.fel.special_invoice import ElectronicSpecialInvoice
from frappe import _


# API para uso interno con apps hechas con Frappe Framework, Para
# Generar Facturas electronicas FEL
@frappe.whitelist()
def api_interface(invoice_code, naming_series):
    """
    Para uso interno con otras apps hechas con frappe framework,
    llamara a las funciones necesarias para generar factura electronica

    Args:
        invoice_code (str): Serie original de la factura

    Returns:
        tuple, msgprint: (True/False, mensaje ok/descripcion error) usado para javascript,
        el msgprint es para mostrar un mensaje a usuario
    """

    # start = timer() usar para medir tyiempo de ejecucion
    try:
        state_of = generate_electronic_invoice(invoice_code, naming_series)
        if state_of[0] == False:
            # end = timer()  \n\n\n {end - start}

            # Si ocurre algun error en la fase final de facelec
            if type(state_of[1]) is dict:  # Aplica para los mensjaes base de datos actualizados
                frappe.msgprint(msg=_(f'A problem occurred in the process, more details in the following log: {state_of[1]}'),
                               title=_('Process not completed'), indicator='red')
                return False, state_of[1]
            else:
                frappe.msgprint(msg=_(f'A problem occurred in the process, more details in the following log: {state_of[1]}'),
                               title=_('Process not completed'), indicator='red')
                return False, state_of[1]


        if type(state_of[1]) is dict:
            # end = timer()  \n\n\n {end - start}
            new_serie = frappe.db.get_value('Envio FEL', {'name': state_of[1]["msj"]}, 'serie_para_factura')
            frappe.msgprint(msg=_(f'Electronic invoice generated with universal unique identifier <b>{state_of[1]["msj"]}</b>'),
                            title=_('Process successfully completed'), indicator='green')

            return True, str(new_serie)

        else:
            # end = timer()
            new_serie = frappe.db.get_value('Envio FEL', {'name': state_of[1]}, 'serie_para_factura')
            frappe.msgprint(msg=_(f'Electronic invoice generated with universal unique identifier <b>{state_of[1]}</b>'),
                            title=_('Process successfully completed'), indicator='green')

            return True, str(new_serie)

    except:
        frappe.msgprint(_(f'A problem occurred while processing the request, more info at: {frappe.get_traceback()}'))
        return False, 'An error occurred in the process of generating an electronic invoice'



# Conector API para usar con otros Frameworks
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



def generate_electronic_invoice(invoice_code, naming_series):
    """
    Llama a la clase y sus metodos encargados de generar factura electronica,
    validando primer los requisitos para que se posible la generacion

    Args:
        invoice_code (str): Serie original de la factura

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
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status[1]}'

        # PASO 4: FIRMA CERTIFICADA Y ENCRIPTADA
        # En este paso se convierte de JSON a XML y se codifica en base64
        status_firma = new_invoice.sign_invoice()
        if status_firma[0] == False:  # Si no se firma correctamente
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status_firma[1]}'

        # PASO 5: SOLICITAMOS FACTURA ELECTRONICA
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

    except:
        return False, str(frappe.get_traceback())


@frappe.whitelist()
def generate_credit_note(invoice_code, naming_series, reference_inv, reason):
    try:
        actual_inv_name = invoice_code
        # PASO 1: VALIDAMOS QUE EXISTA UNA CONFIGURACION PARA FACTURA ELECTRONICA
        status_config = validate_configuration()

        if status_config[0] == False:
            return status_config


        # PASO 1.1: VALIDAMOS LA SERIE A UTILIZAR PARA DEFINIR EL TIPO DE FACTURA ELECTRONIC A GENERAR
        if not frappe.db.exists('Configuracion Series FEL', {'parent': str(status_config[1]), 'serie': str(naming_series)}):
            frappe.msgprint(msg=_('La serie utilizada en la factura no se encuentra configurada para Factura electronica \
                                   Por favor agreguela en Series Fel de Configuracion Factura Electronica, y vuelva a intentar'),
                            title=_('Proceso no completado'), indicator='red')
            return False, 'No completed'


        # PASO 2: VALIDA EXISTENCIA DE REGISTROS EN ENVIOS FEL, PARA GENERAR EL DOCUMENTO
        # ES NECESARIO CREARLA SOBRE UN DOCUMENTO ELECTRONICA YA GENERADO, ESTO SEGUN ESQUEMA XML
        status_invoice = check_invoice_records(str(reference_inv))
        if status_invoice[0] == False:  # Si ya existe en DB
            frappe.msgprint(msg=_(f'La factura no se encuentra registrada como ya generada, para proceder es necesario tener la factura generada original\
                                    como electronica FEL'),
                            title=_('Proceso no completado'), indicator='yellow')

            return False, 'No completed'

        # 2.1 - VALIDAMOS QUE NO SE HAYA GENERANDO ANTEIORMENTE OTRA NOTA DE CREDITO CON LA MISMA DATA
        status_credit_note = check_invoice_records(str(invoice_code))
        if status_credit_note[0] == True:  # Si ya existe en DB
            new_serie_cre = frappe.db.get_value('Envio FEL', {'serie_para_factura': invoice_code}, 'name')
            frappe.msgprint(msg=_(f'La nota de credito que solicitas generar, ya se encuentra registrada como generada en ENVIOS FEL, con UUID {new_serie_cre}'),
                            title=_('Proceso no completado'), indicator='yellow')

            return False, 'No completed'


        # PASO 3: NOTA DE CREDITO ELECTRONICA
        # paso 3.1 - NUEVA INSTANCIA
        # new_credit_note = ElectronicCreditNote(invoice_code, status_config[1], naming_series, reason)
        new_credit_note = ElectronicCreditNote(actual_inv_name, reference_inv, status_config[1], naming_series, reason)

        # PASO 3.2 - VALIDA LOS DATOS NECESARIOS PARA CONSTRUIR EL XML
        status = new_credit_note.build_credit_note()
        if status[0] == False:  # Si la construccion de la peticion es False
            frappe.msgprint(msg=_(f'Ocurrio un problema en el proceso de crear nota de credito electronica, mas detalle en: {status[1]}'),
                            title=_('Proceso no completado'), indicator='red')

            return False, 'No completed'


        # PASO 4: FIRMA CERTIFICADA Y ENCRIPTADA
        # En este paso se convierte de JSON a XML y se codifica en base64
        status_firma = new_credit_note.sign_invoice()
        if status_firma[0] == False:  # Si no se firma correctamente
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de firmar Nota de Credito electronica, mas detalles en: {status_firma[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status_firma[1]}'


        # # PASO 5: SOLICITAMOS FACTURA ELECTRONICA
        status_facelec = new_credit_note.request_electronic_invoice()
        if status_facelec[0] == False:
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de generar Nota de Credito electronica, mas detalles en: {status_facelec[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return False, f'Ocurrio un problema al tratar de generar Nota de Credito electronica, mas detalles en: {status_facelec[1]}'


        # # PASO 6: VALIDAMOS LAS RESPUESTAS Y GUARDAMOS EL RESULTADO POR INFILE
        # # Las respuestas en este paso no son de gran importancia ya que las respuestas ok, seran guardadas
        # # automaticamente si todo va bien, aqui se retornara cualquier error que ocurra en la fase
        status_res = new_credit_note.response_validator()
        if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de generar nota de credito electronica con INFILE, mas detalle en {status_res[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return status_res  # return tuple


        # # PASO 7: ACTUALIZAMOS REGISTROS DE LA BASE DE DATOS
        status_upgrade = new_credit_note.upgrade_records()
        if status_upgrade[0] == False:
            frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de actualizar registros relacionados al documento, mas detalle en {status_upgrade[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return status_upgrade


        # PASO 8: SI cumple con exito el flujo de procesos se retorna una tupla, en ella va
        # # el UUID y la nueva serie para la factura
        # return True,
        # frappe.msgprint(_(str(status_upgrade)))

        new_serie = frappe.db.get_value('Envio FEL', {'name': status_upgrade[1]}, 'serie_para_factura')
        frappe.msgprint(msg=_(f'Electronic Credit Note generated with universal unique identifier <b>{status_upgrade[1]}</b>'),
                        title=_('Process successfully completed'), indicator='green')

        return True, str(new_serie)

    except:
        return False, str(frappe.get_traceback())


@frappe.whitelist()
def generate_debit_note(invoice_code, naming_series):
    frappe.msgprint(_('Hola'))


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
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status_firma[1]}'


        # # PASO 6: SOLICITAMOS DOCUMENTO ELECTRONICO
        status_facelec = new_special_invoice.request_electronic_invoice()
        if status_facelec[0] == False:
            return False, f'Ocurrio un problema al tratar de generar factura especial electronica, mas detalles en: {status_facelec[1]}'

        frappe.msgprint(msg=_('OK esquema XML generado'),
                        title=_('Proceso completado'), indicator='green')

        # # PASO 7: VALIDAMOS LAS RESPUESTAS Y GUARDAMOS EL RESULTADO POR INFILE
        # # Las respuestas en este paso no son de gran importancia ya que las respuestas ok, seran guardadas
        # # automaticamente si todo va bien, aqui se retornara cualquier error que ocurra en la fase
        # status_res = new_credit_note.response_validator()
        # if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
        #     return status_res  # return tuple

        # # PASO 8: ACTUALIZAMOS REGISTROS DE LA BASE DE DATOS
        # status_upgrade = new_credit_note.upgrade_records()
        # if status_upgrade[0] == False:
        #     return status_upgrade

        # PASO 9: SI cumple con exito el flujo de procesos se retorna una tupla, en ella va
        # # el UUID y la nueva serie para la factura
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
        return (False, 'No se encontro ninguna configuración, por favor crea y valida una en \
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
        facelec = frappe.db.get_values('Envio FEL',
                                       filters={'serie_para_factura': invoice_code},
                                       fieldname=['serie_factura_original', 'uuid'],
                                       as_dict=1)

        return True, str(facelec[0]['uuid'])

    else:
        return False, 'A generar una nueva'
