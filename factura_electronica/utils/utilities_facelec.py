# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import unicodedata
from xml.sax.saxutils import escape


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

    return diccionarioError


def normalizar_texto(texto):
    """Funcion para normalizar texto a abc ingles, elimina acentos, ñ, simbolos y
       tag a entidades html para ser reconocidos y evitar el error Woodstox Parser
       Java de INFILE. (Python 3.6)

       Recibe como parametro un string y retorna un string normalizado"""

    string_normal = str(texto)

    # Normalizacion de texto NFKD: modo abc ingles
    string_normalizado = unicodedata.normalize('NFKD', string_normal).encode('ASCII', 'ignore').decode("utf-8")

    return string_normalizado


def validar_configuracion():
    """Permite verificar que exista una configuración validada para Factura Electrónica,
       retorna 1 de 3 opciones:
       1 : Una configuracion valida
       2 : Hay mas de una configuracion
       3 : No hay configuraciones"""
    # verifica que exista un documento validado, docstatus = 1 => validado
    if frappe.db.exists('Configuracion Factura Electronica', {'docstatus': 1}):

        configuracion_valida = frappe.db.get_values('Configuracion Factura Electronica',
                                                   filters={'docstatus': 1},
                                                   fieldname=['name'], as_dict=1)
        if (len(configuracion_valida) == 1):
            return (int(1), str(configuracion_valida[0]['name']))

        elif (len(configuracion_valida) > 1):
            return (int(2), 'Error 2')

    else:
        return (int(3), 'Error 3')
