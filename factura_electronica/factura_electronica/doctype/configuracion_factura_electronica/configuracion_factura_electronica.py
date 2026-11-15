# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class ConfiguracionFacturaElectronica(Document):
    def before_insert(self):
        from factura_electronica.utils.fel_config import apply_certifier_url_defaults

        apply_certifier_url_defaults(self)

    def before_save(self):
        from factura_electronica.utils.fel_config import apply_certifier_url_defaults

        apply_certifier_url_defaults(self)

    def validate(self):
        # Compañía y certificador obligatorios. Al validar (docstatus 1) solo
        # puede existir una configuración activa por par compañía + certificador
        # (Acuerdo 13-2018, art. 14). Las series son tablas hijas.
        from factura_electronica.utils.fel_config import (
            apply_certifier_url_defaults,
            assert_certificador_selectable,
            ensure_single_active_configuration,
            ensure_single_default_for_company,
        )

        apply_certifier_url_defaults(self)

        if not self.company:
            frappe.throw(_("La compañía es obligatoria en Configuración Factura Electrónica."))
        if not self.certificador:
            frappe.throw(_("El certificador es obligatorio en Configuración Factura Electrónica."))

        previous = None
        if not self.is_new() and self.name and frappe.db.exists(self.doctype, self.name):
            previous = frappe.db.get_value(self.doctype, self.name, "certificador")
        assert_certificador_selectable(self.certificador, previous)

        if self.docstatus == 1:
            ensure_single_active_configuration(self.company, self.certificador, self.name)
            ensure_single_default_for_company(self)
# es-GT: Se hace whitelist o abre permiso para permitir llamados Asincronicos desde el navegador del usuario
# en-US: Whitelisting the function to permit Asyncrhonous calls from the user's web browser
# es-GT: Esta funcion obtiene el contenido del campo "Naming Series" configurada por el usuario para "Sale Invoice". (Las series configuradas por el usuario para Facturas de Venta)
# es-GT: Luego de obtenerlas, se separan las series por cada linea, usando el indicador de escape de nueva linea: "\n"
# es-GT: Retorna cada una de las series como lista o diccionario FIXME (No estoy seguro!)
# en-US: This function obtains the contents of "Naming Series" field for "Sales Invoice", a field which lists the series configured by the user.
# en-US: After obtaining them, the series are separated by each new line, using the new line excape character "\n"
# en-US: Returns the naming_series as a list or dictionary. FIXME (Not sure!)
@frappe.whitelist()
def series_sales_invoice():
    naming_series = frappe.get_meta("Sales Invoice").get_field("naming_series").options or ""
    naming_series = naming_series.split("\n")
    #out = naming_series[0] or (naming_series[1] if len(naming_series) > 1 else None)

    return naming_series

@frappe.whitelist()
def series_factura_especial():
    series = frappe.get_meta("Purchase Invoice").get_field("naming_series").options or ""
    series = series.split('\n')

    return series


@frappe.whitelist()
def get_phrases_fel(code_type):
    frases_list = frappe.db.get_list('Frases FEL', filters={'parent': code_type},
                                     fields=['codigo_escenario'], as_list=True)

    # Ejemplo de lo retornado: (('2',), ('1',), ('3',), ('4',))

    list_ok = []
    for frase in frases_list:
        list_ok.append(frase[0])

    return list_ok


@frappe.whitelist()
def get_description_phrase_fel(frase_catalogo='', codigo_frase_hija=''):
    if frappe.db.exists('Frases FEL', {'parent': frase_catalogo,'codigo_escenario': codigo_frase_hija}):
        descr = frappe.db.get_value('Frases FEL', {'parent': frase_catalogo, 'codigo_escenario': codigo_frase_hija}, 'escenario')
        descr_especi = frappe.db.get_value('Frases FEL', {'parent': frase_catalogo, 'codigo_escenario': codigo_frase_hija}, 'texto_a_colocar')

        return {'descr': descr, 'descr_especi': descr_especi}

    else:
        return '<code>Codigo No disponible, para la frase seleccionada</code>'
