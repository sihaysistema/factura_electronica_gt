# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
# import datetime
# import json
import timeit
from factura_electronica.fel.fel import ElectronicInvoice


# API para uso interno de sistema ERPNext
@frappe.whitelist()
def api_interface():
    pass


# Conector API para usar con otros lenguajes de programacion
@frappe.whitelist()
def api_connector():
    pass


@frappe.whitelist()
def generate_electronic_invoice(invoice_code):
    # start = timeit.timeit()
    try:
        # PASO 1: validamos que exista una configuracion valida para generar facturas electronicas
        status_config = validate_configuration()

        if status_config[0] == False:
            return False, str(status_config[1])

        # PASO 2: validamos que no se haya generado factura electronica anteriormente, para la serie recibida
        # en parametro
        status_invoice = check_invoice_records(str(invoice_code))
        if status_invoice[0] == True:
            return False, f'La factura se encuentra como ya generada, puedes validar los detalles en Envio FEL, con codigo UUID {status_invoice[1]}'

        # PASO 3: Creacion Factura Electronica
        # Creamos instancia: Valida todas las dependencias para crear el XML para factura electronica
        new_invoice = ElectronicInvoice(invoice_code, status_config[1])
        status = new_invoice.build_invoice()

        # PASO 4: Conversion de JSON a XML, firmamos el documento y procesamos las respuestas
        if status[0] == True:
            status_firma = new_invoice.sign_invoice()
            # Guardamos la respuesta en un archivo
            if status_firma[0] == True:
                with open('reciibo.txt', 'w') as f:
                    f.write(str(status_firma[1]))

                frappe.msgprint(_('Completado'))
            else:
                frappe.msgprint(_(f'NO: {status_firma[1]}'))
        else:
            frappe.msgprint(_(f'No: {status[1]}'))
        # end = timeit.timeit()
        # tiempo_ejecucion = start - end

        # frappe.msgprint(_(f'Ejecutado en: {tiempo_ejecucion}'))
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
            return (False, 'Se encontro mas de una configuración, por favor verifica que solo exista una en Configuracion Factura Electronia')

    else:
        return (False, 'No se encontro ninguna configuración, por favor crea y valida una en Configuracion Factura Electronica')


def check_invoice_records(invoice_code):
    # Verifica si existe una factura con la misma serie, evita duplicadas
    if frappe.db.exists('Envio FEL', {'name': invoice_code}):
        facelec = frappe.db.get_values('Envio FEL',
                                       filters={'name': invoice_code},
                                       fieldname=['serie_factura_original', 'uuid'],
                                       as_dict=1)

        return True, str(facelec[0]['uiid'])

    else:
        return False, 'A generar una nueva'
