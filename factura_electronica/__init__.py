# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from numinwords import numinwords
from frappe import _
import locale
import math
import datetime
locale.setlocale(locale.LC_ALL, str('en_US.UTF-8'))

__version__ = '5.0.0'

@frappe.whitelist()
def currency_in_words(amount, currency, cent_in_numb=0):
    '''
    Function that calls the numinwords pip package by Si Hay Sistema
    and then capitalizes the result, returning a properly capitalized sentence.
    https://pypi.org/project/numinwords/
    https://www.geeksforgeeks.org/string-capitalize-python/
    Arguments:
    Amount: Float number
    Currency: ISO4217 Currency code, eg. 'GTQ', 'USD'
    Cent in Number = 1  enables cent in numbers
    '''
    # mapa traducciones es
    mapa_es = {
        'cero': '0', 'uno': '1', 'dos': '2', 'tres': '3', 'cuatro': '4',
        'cinco': '5', 'seis': '6', 'siete': '7', 'ocho': '8', 'nueve': '9'
    }

    if cent_in_numb:
        # Convierte el monto a palabras moneda
        words = numinwords(float(amount), lang='es')
        # Convierte el string en una lista, separando por la palabra 'punto'
        x2 = str(words).split('punto')

        # Validaciones
        if len(x2) == 1:  # si es numero entero
            return str(x2[0]).capitalize()

        elif len(x2) > 1:  # Si tiene centavos
            # Extrae los centavos del monto y lo convierte a numeros sobre 100
            # Extraccion texto de centavos y conversion a lista donde exstan espacio en blanco
            x3 = x2[1].strip().split(' ')

            if len(x3) > 1:  # Si los centavos son de mas de dos cifras
                return str(x2[0].strip() + ' con ' + str(mapa_es[x3[0]]) + str(mapa_es[x3[1]]) + '/100').capitalize()
            else:  # Si los centavos tiene una sola cifra
                return str(x2[0].strip() + ' con ' + str(mapa_es[x3[0]]) + '0' + '/100').capitalize()

    else:
        words = numinwords(float(amount), to='currency', lang='es', currency=currency)
        text = words.capitalize()
        return text
