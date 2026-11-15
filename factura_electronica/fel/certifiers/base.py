# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Interfaz de un certificador FEL.

Cada certificador implementa firma, certificación (DTE) y anulación.
El XML del DTE lo construyen los generadores; el adaptador habla con el
servicio del certificador. Agregar un certificador nuevo es registrar
otra clase en este mapa, sin copiar cada tipo de documento.
"""

from __future__ import unicode_literals


class CertifierAdapter(object):
    # NIT normalizado (solo letras y números) y/o name del DocType.
    keys = ()

    def sign(self, config_name, encoded_xml, es_anulacion=None):
        """Firma el XML en base64.

        Returns:
            tuple: (True, archivo_firmado) o (False, mensaje)
        """
        raise NotImplementedError

    def certify(self, config_name, nit_emisor, xml_dte, identificador):
        """Envía el DTE firmado a certificar.

        Returns:
            tuple: (True, dict_respuesta) o (False, mensaje)
        """
        raise NotImplementedError

    def cancel(self, config_name, nit_emisor, xml_dte, identificador):
        """Envía la anulación al mismo certificador que emitió el DTE.

        Returns:
            tuple: (True, dict_respuesta) o (False, mensaje)
        """
        raise NotImplementedError

    def post_json(self, url, payload, headers):
        """HTTP JSON. Lo usa el generador legado y los métodos de INFILE."""
        raise NotImplementedError
