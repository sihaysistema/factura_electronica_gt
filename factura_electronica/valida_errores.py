#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import os

import sys
 
reload(sys)  
#sys.setdefaultencoding('Cp1252')
sys.setdefaultencoding('utf-8')

def encuentra_errores(descripcion_error):
    error_recibido = str(descripcion_error)
    with open('registro_errores.txt', 'w') as recibe_error:
        recibe_error.write(error_recibido)
        recibe_error.close()

	reemplazo_A = error_recibido.replace(";", ",")
	reemplazo_B = reemplazo_A.replace("[", " ")
	json_errores = reemplazo_B.replace("]", " ")
	dic_errores = eval(json_errores)
    #frappe.msgprint(_('se recibieron las descripciones'))
    return (dic_errores)
    #return errores_diccionario
    