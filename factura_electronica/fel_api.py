# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import time

import frappe
from frappe import _

from factura_electronica.controllers.journal_entry_special import JournalEntrySpecialISR
from factura_electronica.fel.canceller import CancelDocument
from factura_electronica.fel.credit_note import ElectronicCreditNote
from factura_electronica.fel.debit_note import ElectronicDebitNote
from factura_electronica.fel.exchange_invoice import PurchaseExchangeInvoice, SalesExchangeInvoice
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
        if state_of[0] == False:
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
def generate_credit_note(invoice_code, naming_series, reference_inv, reason):
    """
    Funcion intermediaria para generar nota de credito electronica

    Args:
        invoice_code (str): name, factura retorno
        naming_series (str): serie usada en la factura
        reference_inv (str): name factura original
        reason (str): Razón por la que se esta generando la nota de credito, esto es
        solicitado por el XML (SAT)

    Returns:
        tuple: (bool, desc)
    """
    try:
        actual_inv_name = invoice_code
        # PASO 1: VALIDAMOS QUE EXISTA UNA CONFIGURACION PARA FACTURA ELECTRONICA
        status_config = validate_configuration()

        if status_config[0] == False:
            return status_config

        # PASO 1.1: VALIDAMOS LA SERIE A UTILIZAR PARA DEFINIR EL TIPO DE FACTURA ELECTRONIC A GENERAR
        if not frappe.db.exists('Configuracion Series FEL', {'parent': str(status_config[1]), 'serie': str(naming_series)}):
            frappe.msgprint(msg=_('La serie utilizada en la factura no se encuentra configurada para Nota de Credito Electronica \
                                   Por favor agreguela en Series Fel de Configuracion Factura Electronica, y vuelva a intentar'),
                            title=_('Proceso no completado'), indicator='red')
            return False, 'No completed'

        # PASO 2: VALIDA EXISTENCIA DE REGISTROS EN ENVIOS FEL, PARA GENERAR EL DOCUMENTO
        # ES NECESARIO CREARLA SOBRE UN DOCUMENTO ELECTRONICA YA GENERADO, ESTO SEGUN ESQUEMA XML
        status_invoice = check_invoice_records(str(reference_inv))
        if status_invoice[0] == False:  # Si ya existe en DB
            frappe.msgprint(msg=_(f'Para poder generar correctamente la Nota de Credito Electrónica es necesario que la factura original \
                            se encuentre generada como electrónica y registrada en el ERP'), title=_('Proceso no completado'), indicator='red')

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
            frappe.msgprint(msg=_(f'Ocurrio un problema en el proceso de crear la petición para nota de credito electronica, mas detalle en: {status[1]}'),
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
        new_serie = frappe.db.get_value('Envio FEL', {'name': status_upgrade[1]}, 'serie_para_factura')
        frappe.msgprint(msg=_(f'Electronic Credit Note generated with universal unique identifier <b>{status_upgrade[1]}</b>'),
                        title=_('Process successfully completed'), indicator='green')

        return True, str(new_serie)

    except:
        return False, str(frappe.get_traceback())


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
        frappe.msgprint(msg=_(f'{_("Electronic Debit Note generated with universal unique identifier")} <b>{status_upgrade[1]}</b>'),
                        title=_('Process successfully completed'), indicator='green')

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
        frappe.msgprint(msg=_(f'Electronic Special Invoice generated with universal unique identifier <b>{status_upgrade[1]}</b>'),
                        title=_('Process successfully completed'), indicator='green')

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
                                       fieldname=['serie_factura_original', 'uuid'],
                                       as_dict=1)

        return True, str(facelec[0]['uuid'])

    else:
        return False, 'A generar una nueva'


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


# INICIO FACTURAS EXENTAS DE IMPUESTOS
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


# CANCELADOR DE DOCUMENTOS ELECTRONICOS FEL
@frappe.whitelist()
def invoice_canceller(invoice_name, reason_cancelation='Anulación', document='Sales Invoice'):
    """[summary]

    Args:
        invoice_name ([type]): [description]
        document (str, optional): [description]. Defaults to 'Sales Invoice'.
    """

    status_config = validate_configuration()

    if status_config[0] == True:
        cancel_invoice = CancelDocument(invoice_name, status_config[1], reason_cancelation, document)

        status_req = cancel_invoice.validate_requirements()
        if not status_req[0]:
            frappe.msgprint(status_req[1])
            return

        status_build = cancel_invoice.build_request()
        if not status_build[0]:
            frappe.msgprint(f'Petición no generada: No se encontraron los datos necesarios, por favor asegurese de tener los datos necesarios para compania y cliente')
            return

        status_firma = cancel_invoice.sign_invoice()
        if not status_firma[0]:
            frappe.msgprint(status_firma[1])
            return

        status_process = cancel_invoice.request_cancel()
        if not status_process[0]:
            frappe.msgprint(status_process[1])
            return

        status_validador_res = cancel_invoice.response_validator()
        if not status_validador_res[0]:
            frappe.msgprint(f'Anulacion de documento electronico no se pudo completar, encontrara mas detalle en el siguiente log {str(status_validador_res[1])}')
            return str(status_validador_res[1])
        else:
            frappe.msgprint('Factura Anulada con Exito, para ver el documento anulado, presione el boton ver PDF Documento Electronico')
            return

    else:
        frappe.msgprint(status_config[1])
        return


@frappe.whitelist()
def is_valid_to_fel(doctype, docname):
    """
    Validador escenario para mostrar u ocultar botones para generar docs electronicos

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


@frappe.whitelist()
def generate_exchange_invoice_si(invoice_code: str, naming_series: str) -> tuple:
    """
    Funcion intermediaria para generar factura cambiaria

    Args:
        invoice_code (str): name, factura retorno
        naming_series (str): serie usada en la factura
        reference_inv (str): name factura original
        reason (str): Razón por la que se esta generando la nota de credito, esto es
        solicitado por el XML (SAT)

    Returns:
        tuple: (bool, desc)
    """
    try:
        # Validacion configuracion serie para doc electronico
        status_config = validate_configuration()
        if status_config[0] == False:
            return status_config

        if not frappe.db.exists('Configuracion Series FEL', {'parent': status_config[1], 'serie': naming_series}):
            frappe.msgprint(msg=_('La serie utilizada en la factura no se encuentra configurada para Factura Cambiaria Electronica \
                                   Por favor agreguela en Series Fel de Configuracion Factura Electronica, y vuelva a intentar'),
                            title=_('Proceso no completado'), indicator='red')
            return False, 'No completed'

        # validacion existencias, para evitar duplicados
        status_inv = check_invoice_records(invoice_code)
        if status_inv[0] == True:  # Si ya existe en DB
            new_serie_cre = frappe.db.get_value('Envio FEL', {'serie_para_factura': invoice_code}, 'name')
            frappe.msgprint(msg=_(f'El documento electronico que solicitas generar, ya se encuentra registrada como generada en ENVIOS FEL, con UUID {new_serie_cre}'),
                            title=_('Proceso no completado'), indicator='yellow')

            return False, 'No completed'

        # Generacion peticion
        new_exch_inv = SalesExchangeInvoice(invoice_code, status_config[1], naming_series)

        status = new_exch_inv.build_invoice()
        if status[0] == False:
            frappe.msgprint(msg=_(f'No se pudo construir la peticion XML para factura cambiaria, mas detalle en: {status[1]}'),
                            title=_('Proceso no completado'), indicator='red')

            return False, 'No completed'

        # Firma certificacion
        # # En este paso se convierte de JSON a XML y se codifica en base64
        status_firma = new_exch_inv.sign_invoice()
        if status_firma[0] == False:  # Si no se firma correctamente
            frappe.msgprint(msg=_(f'No se pudo generar la certificacion de la peticion para generar documento electronico, mas detalles en: {status_firma[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return False, f'Ocurrio un problema en el proceso, mas detalle en: {status_firma[1]}'

        # Solicitud generacion Doc Electronico
        status_facelec = new_exch_inv.request_electronic_invoice()
        if status_facelec[0] == False:
            frappe.msgprint(msg=_(f'No se pudo generar el documento electronico solicitado, mas detalles en el siguiente log: {status_facelec[1]}'),
                            title=_('Proceso no completado'), indicator='red')
            return False, f'Ocurrio un problema al tratar de generar Factura Cambiaria Electronica, mas detalles en: {status_facelec[1]}'

        # # PASO 6: VALIDAMOS LAS RESPUESTAS Y GUARDAMOS EL RESULTADO POR INFILE
        # # Las respuestas en este paso no son de gran importancia ya que las respuestas ok, seran guardadas
        # # automaticamente si todo va bien, aqui se retornara cualquier error que ocurra en la fase
        # status_res = new_exch_inv.response_validator()
        # if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
        #     frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de generar nota de credito electronica con INFILE, mas detalle en {status_res[1]}'),
        #                     title=_('Proceso no completado'), indicator='red')
        #     return status_res  # return tuple

        # # # PASO 7: ACTUALIZAMOS REGISTROS DE LA BASE DE DATOS
        # status_upgrade = new_credit_note.upgrade_records()
        # if status_upgrade[0] == False:
        #     frappe.msgprint(msg=_(f'Ocurrio un problema al tratar de actualizar registros relacionados al documento, mas detalle en {status_upgrade[1]}'),
        #                     title=_('Proceso no completado'), indicator='red')
        #     return status_upgrade

        # # PASO 8: SI cumple con exito el flujo de procesos se retorna una tupla, en ella va
        # # # el UUID y la nueva serie para la factura
        # new_serie = frappe.db.get_value('Envio FEL', {'name': status_upgrade[1]}, 'serie_para_factura')
        # frappe.msgprint(msg=_(f'Electronic Credit Note generated with universal unique identifier <b>{status_upgrade[1]}</b>'),
        #                 title=_('Process successfully completed'), indicator='green')

        # return True, str(new_serie)
        frappe.msgprint('Test Factura Cambiaria')
    except:
        return False, str(frappe.get_traceback())

