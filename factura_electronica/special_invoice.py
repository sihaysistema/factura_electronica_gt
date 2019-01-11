# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _

from api import validar_configuracion
from valida_errores import normalizar_texto

# Permite trabajar con acentos, ñ, simbolos, etc
import os, sys
reload(sys)
sys.setdefaultencoding('utf-8')

#TODO:
@frappe.whitelist()
def verificar(serie):
    validacion = validar_configuracion
    # frappe.msgprint(_(validacion))

    # if validacion == 1:
    #     if frappe.db.exists('Envios Facturas Electronicas', {'numero_dte': serie_original_factura}):
    #             factura_electronica = frappe.db.get_values('Envios Facturas Electronicas',
    #                                                     filters={'numero_dte': serie_original_factura},
    #                                                     fieldname=['serie_factura_original', 'cae', 'numero_dte'],
    #                                                     as_dict=1)
