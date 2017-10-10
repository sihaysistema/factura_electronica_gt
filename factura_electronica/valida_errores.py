#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import os
import sys
reload(sys)  
#sys.setdefaultencoding('Cp1252')
sys.setdefaultencoding('utf-8')

def encuentra_errores(cadena):    
    """Reemplazo múltiple de cadenas, para finalmente retornarlo como diccionario
       y acceder a la descripcion de cada error."""
    try:
        import re
        reemplazo = {';': ','}
        regex = re.compile("(%s)" % "|".join(map(re.escape, reemplazo.keys())))
        diccionario = regex.sub(lambda x: str(reemplazo[x.string[x.start() :x.end()]]), cadena)
        diccionarioError = eval(diccionario)

        with open('registro_errores.json', 'w') as registro_error:
            registro_error.write(diccionario)
            registro_error.close()
    except:
        diccionarioError = {'Mensaje': str(cadena)}

    return (diccionarioError)