# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import unicodedata
from xml.sax.saxutils import escape

import pandas as pd
import json

import frappe
from frappe import _


def encuentra_errores(cadena):
    """Reemplazo múltiple de cadenas, para finalmente retornarlo como diccionario
       y acceder a la descripcion de cada error."""
    try:
        import re
        reemplazo = {';': ','}
        regex = re.compile("(%s)" % "{delimiter}".join(map(re.escape, reemplazo.keys())))
        diccionario = regex.sub(lambda x: str(reemplazo[x.string[x.start() :x.end()]]), cadena)
        diccionarioError = eval(diccionario)

        # Guarda en un archiv json el registro de los ultimos errores ocurridos
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
                                                   fieldname=['name', 'regimen'], as_dict=1)
        if (len(configuracion_valida) == 1):
            return (int(1), str(configuracion_valida[0]['name']), str(configuracion_valida[0]['regimen']))

        elif (len(configuracion_valida) > 1):
            return (int(2), 'Error 2')

    else:
        return (int(3), 'Error 3')


def generate_asl_file(datos_asiste, file_name='ASISTE', delimiter='|', extension='.ASL'):
    """
    Utilidad para crear archivos para asiste libros SAT Guatemala

    Args:
        data_asl (list): Lista diccionarios
        file_name (str, optional): Nombre para el archivo. Defaults to 'ASISTE'.
        delimiter (str, optional): Delimitador a usar en el archivo. Defaults to '|'.
        extension (str, optional): Extension a usar en el archivo. Defaults to '.ASL'
    """

    try:
        # Cargamos a un df la data, para limpiar los valores None
        df = pd.DataFrame(json.loads(datos_asiste)).fillna('')
        data_asl = df.to_dict(orient='records')

        # Para debug
        # with open('testasl.json', 'w') as f:
        #     f.write(json.dumps(data_asl, default=str))

        with open(f'{file_name}{extension}', 'a') as archivo_asl:
            archivo_asl.seek(0)
            archivo_asl.truncate()

            for d in data_asl:
                asl_row = f"""{d.get('establecimiento', '')}{delimiter}{d.get('compras_ventas', '')}{delimiter}{d.get('documento', '')}{delimiter}{d.get('serie_doc', '')}{delimiter}\
{d.get('no_doc', '')}{delimiter}{d.get('fecha_doc', '')}{delimiter}{d.get('nit_cliente_proveedor', '')}{delimiter}{d.get('nombre_cliente_proveedor', '')}{delimiter}\
{d.get('tipo_transaccion', '')}{delimiter}{d.get('tipo_ope', '')}{delimiter}{d.get('status_doc', '')}{delimiter}{d.get('no_orden_cedula_dpi_pasaporte', '')}{delimiter}\
{d.get('no_regi_cedula_dpi_pasaporte', '')}{delimiter}{d.get('tipo_doc_ope', '')}{delimiter}{d.get('no_doc_operacion', '')}{delimiter}{d.get('total_gravado_doc_bien_ope_local', '')}{delimiter}\
{d.get('total_gravado_doc_bien_ope_exterior', '')}{delimiter}{d.get('total_gravado_doc_servi_ope_local', '')}{delimiter}{d.get('total_gravado_doc_servi_ope_exterior', '')}{delimiter}{d.get('total_exempt_doc_local_ope_assets', '')}{delimiter}\
{d.get('total_exento_doc_bien_ope_local', '')}{delimiter}{d.get('total_exento_doc_bien_ope_exterior', '')}{delimiter}{d.get('total_exento_doc_servi_ope_local', '')}{delimiter}{d.get('total_exento_doc_servi_ope_exterior', '')}{delimiter}\
{d.get('tipo_constancia', '')}{delimiter}{d.get('no_constancia_exension_adqui_insu_reten_iva', '')}{delimiter}{d.get('valor_constancia_exension_adqui_insu_reten_iva', '')}{delimiter}{d.get('peque_contri_total_facturado_ope_local_bienes', '')}{delimiter}\
{d.get('peque_contri_total_facturado_ope_local_servicios', '')}{delimiter}{d.get('peque_contri_total_facturado_ope_exterior_bienes', '')}{delimiter}{d.get('peque_contri_total_facturado_ope_exterior_servicios', '')}{delimiter}\
{d.get('iva', '')}{d.get('total_valor_doc', '')}\n"""
                archivo_asl.writelines(asl_row)

        archivo_asl.close()

        return True, 'OK'

    except:
        return False, str(frappe.get_traceback())


def string_cleaner(str_to_clean, opt=False):
    """
    De un string permite eliminar todos los numeros o todas las letras,
    si opt=False eliminara numeros dejando solo letras
    si opt=True eliminara letras dejando solo numeros

    Args:
        str_to_clean (str): String a limpiar
        opt (bool, optional): True para eliminar numeros,
        False para eliminar letras. Defaults to False.

    Returns:
        str/bool: Si todo va bien retorna el string limpio, sino retornara
        False como no procesado
    """

    try:
        s = str(str_to_clean)

        if opt == False:
            # removiendo numeros
            result = ''.join([i for i in s if not i.isdigit()])

        elif opt == True:
            # removiendo letras
            result = ''.join([i for i in s if i.isdigit()])
        else:
            return False
    except:
        return False
    else:
        return result


def clean_traceback_py(mensaje):
    '''Funcion encargada de recorrer el string de traceback python y obtener el error especifico'''
    import re

    x = re.split("\n", str(mensaje))
    msj_e = len(x) - 2

    return str(x[msj_e]) + str(x[msj_e+1])
