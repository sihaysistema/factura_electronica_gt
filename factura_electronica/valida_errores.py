#!/usr/local/bin/python
# -*- coding: utf-8 -*-from __future__ import unicode_literals
import frappe
from frappe import _
import os
import sys
import unicodedata
from xml.sax.saxutils import escape

reload(sys)
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

def normalizar_texto(texto):
    """Funcion para normalizar texto a abc ingles, elimina acentos, ñ, simbolos y tag a entidades html
       para ser reconocidos y evitar el error Woodstox Parser Java de INFILE"""
    # Vuelve a convertir a string el dato recibido
    string_normal = str(texto)

    # Convertir a Unicode
    # escape : permite convertir los simbolos a entidades 'html' https://www.w3schools.com/html/html_entities.asp
    # https://wiki.python.org/moin/EscapingXml
    string_a_unicode = unicode(escape(string_normal), "utf-8")

    # Normalizacion de texto NFKD: modo abc ingles
    string_normalizado = unicodedata.normalize('NFKD', string_a_unicode).encode('ASCII', 'ignore')

    # Retorna el string normalizado
    return string_normalizado
