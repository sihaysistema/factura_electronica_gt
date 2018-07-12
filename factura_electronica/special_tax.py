# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _

from valida_errores import normalizar_texto

# Permite trabajar con acentos, ñ, simbolos, etc
import os, sys
reload(sys)
sys.setdefaultencoding('utf-8')

def calculate_values_with_special_tax():
    '''Grand total, quitar sumatoria totoal shs otros imuestos, = neto para iva
    se calcula sobre ese neto, y se va a ir a modificar en glentry para reflejar los cambios'''
    pass

def add_gl_entry_other_special_tax(accoount_facelect, amount_facelec):
    # fixme: arreglar para guardar los registos en gl entry
    nuevo_archivo = frappe.new_doc("File")

    nuevo_archivo.save()
