# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import requests
import xmltodict, json

from resources_facelec.utilities import encuentra_errores as errores
from resources_facelec.utilities import normalizar_texto, validar_configuracion

from resources_facelec.facelec_generator import 

# Permite trabajar con acentos, ñ, simbolos, etc
import os, sys
reload(sys)
sys.setdefaultencoding('utf-8')


@frappe.whitelist()
def generar_factura_electronica(serie_factura, nombre_cliente, pre_se):
    '''Verifica que todos los datos esten correctos para realizar una
       peticion a INFILE y generar la factura electronica

       Parametros
       ----------
       * serie_factura (str) : Serie de la factura
       * nombre_cliente (str) : Nombre del cliente
       * pre_se (str) : Prefijo de la serie
    '''

    serie_original_factura = str(serie_factura)
    nombre_del_cliente = str(nombre_cliente)
    prefijo_serie = str(pre_se)

    validar_config = validar_configuracion()

    # Si cumple, pasa el proceso de generar factura electronica
    if validar_config[0] == 1:
        # Verifica si existe una factura con la misma serie, evita duplicadas
        if frappe.db.exists('Envios Facturas Electronicas', {'numero_dte': serie_original_factura}):
            factura_electronica = frappe.db.get_values('Envios Facturas Electronicas',
                                                    filters={'numero_dte': serie_original_factura},
                                                    fieldname=['serie_factura_original', 'cae', 'numero_dte'],
                                                    as_dict=1)
            frappe.msgprint(_('''
            <b>AVISO:</b> La Factura ya fue generada Anteriormente <b>{}</b>
            '''.format(str(factura_electronica[0]['numero_dte']))))

            dte_factura = str(factura_electronica[0]['numero_dte'])

            return dte_factura

        else:
            nombre_config_validada = str(validar_config[1])

            try:
                crear_xml_fac = 
            except:
                pass
            else:
                pass


    elif validar_config[0] == 2:
        frappe.show_alert(_('Existe mas de una configuracion electronica'))
    elif validar_config[0] == 3:
        pass