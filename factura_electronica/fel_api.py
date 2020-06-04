# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import time
# import datetime
import json
# from timeit import default_timer as timer usar para medir tiempo ejecucion
from factura_electronica.fel.fel import ElectronicInvoice


# API para uso interno con apps hechas con Frappe Framework
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
            frappe.msgprint(msg=_(f'Electronic invoice generated with universal unique identifier <b>{state_of[1]["msj"]}</b>'),
                            title=_('Process successfully completed'), indicator='green')

            return True, str(state_of[1]["serie_nueva"])

        else:
            # end = timer()
            frappe.msgprint(msg=_(f'Electronic invoice generated with universal unique identifier <b>{state_of[1]}</b>'),
                            title=_('Process successfully completed'), indicator='green')

            return True, str(state_of[1])

    except:
        frappe.msgprint(_(f'Ocurrio un problema al procesar la solicitud, mas info en: {frappe.get_traceback()}'))
        return False, 'Ocurrio un error en el proceso de generar factura electronia'


# Conector API para usar con otros Frameworks
@frappe.whitelist()
def api_connector():
    pass


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
        new_invoice = ElectronicInvoice(invoice_code, status_config[1])

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
        status_res = new_invoice.response_validator()
        if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
            return status_res  # return tuple

        # PASO 7: ACTUALIZAMOS REGISTROS DE LA BASE DE DATOS
        status_upgrade = new_invoice.upgrade_records()
        if status_upgrade[1]['status'] == 'ERROR':
            return status_upgrade

        # SI cumple con exito el flujo de procesos se retorna una tupla, en ella va
        # el UUID y la nueva serie para la factura
        return status_upgrade
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
    if frappe.db.exists('Envio FEL', {'name': invoice_code}):
        facelec = frappe.db.get_values('Envio FEL',
                                       filters={'name': invoice_code},
                                       fieldname=['serie_factura_original', 'uuid'],
                                       as_dict=1)

        return True, str(facelec[0]['uiid'])

    else:
        return False, 'A generar una nueva'
