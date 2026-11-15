# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Adaptador INFILE (NIT 12521337).

Única implementación de envío disponible. El protocolo es el servicio
de firma y el de certificación/anulación de INFILE (feel.com.gt):
JSON con llave/alias para firmar, y JSON con xml_dte más encabezados
usuario/llave/identificador para certificar o anular.
"""

from __future__ import unicode_literals

import json

import frappe
import requests

from factura_electronica.fel.certifiers.base import CertifierAdapter

INFILE_NIT = "12521337"
INFILE_NAME = "INFILE"


class InfileAdapter(CertifierAdapter):
    keys = (INFILE_NAME, INFILE_NIT)

    def _config(self, config_name, *fields):
        values = frappe.db.get_value(
            "Configuracion Factura Electronica",
            config_name,
            list(fields),
            as_dict=True,
        )
        return values or {}

    def _text(self, value):
        if value is None:
            return ""
        return str(value).strip()

    def sign(self, config_name, encoded_xml, es_anulacion=None):
        try:
            row = self._config(config_name, "url_firma", "alias", "llave_pfx", "es_anulacion")
            payload = {
                "llave": self._text(row.get("llave_pfx")),
                "archivo": str(encoded_xml),
                "alias": self._text(row.get("alias")),
                "es_anulacion": self._text(es_anulacion if es_anulacion is not None else row.get("es_anulacion")),
            }
            headers = {"content-type": "application/json"}
            response = self.post_json(self._text(row.get("url_firma")), payload, headers)
            signed = json.loads(response.content.decode("utf-8"))
            if signed.get("resultado") == True:
                return True, signed.get("archivo")
            return False, signed.get("descripcion")
        except Exception:
            return False, (
                "Error al tratar de firmar el documento electronico: " + str(frappe.get_traceback())
            )

    def certify(self, config_name, nit_emisor, xml_dte, identificador):
        return self._submit(config_name, "url_dte", nit_emisor, xml_dte, identificador)

    def cancel(self, config_name, nit_emisor, xml_dte, identificador):
        return self._submit(config_name, "url_de_anulacion", nit_emisor, xml_dte, identificador)

    def _submit(self, config_name, url_field, nit_emisor, xml_dte, identificador):
        try:
            row = self._config(config_name, url_field, "alias", "llave_ws", "correo_copia")
            payload = {
                "nit_emisor": nit_emisor,
                "correo_copia": row.get("correo_copia"),
                "xml_dte": xml_dte,
            }
            headers = {
                "content-type": "application/json",
                "usuario": row.get("alias"),
                "llave": row.get("llave_ws"),
                "identificador": identificador,
            }
            response = self.post_json(self._text(row.get(url_field)), payload, headers)
            return True, json.loads(response.content.decode("utf-8"))
        except Exception:
            return False, (
                "Error al tratar de generar factura electronica: " + str(frappe.get_traceback())
            )

    def post_json(self, url, payload, headers):
        return requests.post(url, data=json.dumps(payload), headers=headers)
