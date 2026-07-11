# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from factura_electronica.fel.canceller import CancelDocument
from factura_electronica.fel.fel import ElectronicInvoice

# CANCELADOR DE DOCUMENTOS ELECTRONICOS FEL
@frappe.whitelist()
def invoice_canceller(invoice_name, reason_cancelation='Anulación', document='POS Invoice'):
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
            frappe.msgprint('Documento electronico anulado con Exito, presione el boton ver PDF Documento Electronico')
            return

    else:
        frappe.msgprint(status_config[1])
        return

# INICIO FEL NORMAL
@frappe.whitelist()
def api_interface(invoice_code, naming_series):
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

def generate_electronic_invoice(invoice_code, naming_series):
    try:
        status_config = validate_configuration()
        if status_config[0] == False:
            return status_config

        if not frappe.db.exists('Configuracion Series FEL', {'parent': str(status_config[1]), 'serie': str(naming_series)}):
            return False, f'La serie utilizada en la factura no se encuentra configurada para Factura electronica \
                            Por favor agreguela en Series Fel de Configuracion Factura Electronica, y vuelva a intentar'

        status_invoice = check_invoice_records(str(invoice_code))
        if status_invoice[0] == True:
            return False, f'La factura se encuentra registrada como ya generada, puedes validar los detalles en \
                            Envios FEL, con codigo UUID {status_invoice[1]}'

        new_invoice = ElectronicInvoice(invoice_code, status_config[1], naming_series)

        status = new_invoice.build_invoice()
        if status[0] == False:
            return False, f'Ocurrio un problema al tratar de generar la petición JSON, mas detalle en: {status[1]}'

        status_firma = new_invoice.sign_invoice()
        if status_firma[0] == False:
            return False, f'Ocurrio un problema al tratar de firmar la petición, vericar tener la url correcta para \
                firmas en Configuracion Factura Electroónica mas detalle en: {status_firma[1]}'

        status_facelec = new_invoice.request_electronic_invoice()
        if status_facelec[0] == False:
            return False, f'Ocurrio un problema al tratar de generar factura electronica, mas detalles en: {status_facelec[1]}'

        status_res = new_invoice.response_validator()
        if (status_res[1]['status'] == 'ERROR') or (status_res[1]['status'] == 'ERROR VALIDACION'):
            return status_res

        status_upgrade = new_invoice.upgrade_records()
        if status_upgrade[0] == False:
            return status_upgrade

        return True, status_upgrade[1]

    except:
        return False, str(frappe.get_traceback())

def validate_configuration():
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
    if frappe.db.exists('Envio FEL', {'serie_para_factura': invoice_code}):
        facelec = frappe.db.get_values('Envio FEL',  filters={'serie_para_factura': invoice_code},
                                       fieldname=['serie_factura_original', 'uuid'],
                                       as_dict=1)
        return True, str(facelec[0]['uuid'])
    else:
        return False, 'A generar una nueva'

@frappe.whitelist()
def is_valid_to_fel(doctype, docname):
    status_list = ['Credit Note Issued', 'Debit Note Issued', 'Return']
    stat = validate_configuration()
    docinv = frappe.get_doc(doctype, {'name': docname})

    if stat[0] == True:
        config_name = stat[1]
    else:
        return stat

    val_serie = frappe.db.exists('Configuracion Series FEL', {'parent': config_name, 'serie': docinv.naming_series})

    # Condiciones para FEL POS Invoice -> FEL Normal
    if (docinv.doctype == 'POS Invoice') and (docinv.docstatus == 1) and (docinv.status not in status_list):
        val_serie_fel = frappe.db.exists('Configuracion Series FEL', {'parent': config_name, 'serie': docinv.naming_series})
        active = frappe.db.exists('Configuracion Factura Electronica', {'name': config_name, 'factura_venta_fel': 1})

        if val_serie_fel and active:
            values = frappe.db.get_values('Configuracion Series FEL',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'valido', True
        else:
            return _('Serie de factura no configurada, por favor agregarla y \
                activarla en configuración Factura Electrónica para generar documento FEL'), False, False

    # Condiciones para FEL POS Invoice -> Cancelador de FEl Normal
    elif (docinv.doctype == 'POS Invoice') and (docinv.docstatus == 2) and (docinv.numero_autorizacion_fel):
        active = frappe.db.exists('Configuracion Factura Electronica', {'name': config_name,
                                                                        'anulador_de_facturas_ventas_fel': 1})
        if val_serie and active:
            values = frappe.db.get_values('Configuracion Series FEL',
                                          filters={'parent': config_name, 'serie': docinv.naming_series},
                                          fieldname=['tipo_documento'], as_dict=1)
            return values[0]['tipo_documento'], 'anulador', True
        else:
            return _('Serie de documento no configurada, \
                     por favor agregarla y activarla en configuración Factura Electrónica para generar documento FEL'), False

    return False, False, False,
