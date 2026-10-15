# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Mapa certificador -> adaptador y despacho de firma, DTE y anulación."""

from __future__ import unicode_literals

import frappe
from frappe import _

from factura_electronica.utils.fel_config import normalize_nit

ADAPTERS = {}


def register_adapter(adapter_cls):
    """Registra un adaptador por cada NIT o nombre en adapter_cls.keys."""
    for key in getattr(adapter_cls, "keys", ()) or ():
        ADAPTERS[_adapter_key(key)] = adapter_cls
    return adapter_cls


def _adapter_key(value):
    text = "" if value is None else str(value).strip()
    normalized = normalize_nit(text)
    if normalized and any(ch.isdigit() for ch in normalized):
        return normalized
    return text.upper()


def resolve_adapter_class(certificador_name=None, nit=None):
    """Devuelve la clase adaptadora, o None si ese certificador no está implementado."""
    for candidate in (nit, certificador_name):
        if not candidate:
            continue
        adapter_cls = ADAPTERS.get(_adapter_key(candidate))
        if adapter_cls:
            return adapter_cls
    return None


def message_not_implemented(certificador_name, nit=None):
    label = certificador_name or nit or ""
    if nit and certificador_name:
        label = "{0} (NIT {1})".format(certificador_name, nit)
    return _(
        "El certificador {0} no está implementado aún. "
        "Hoy solo INFILE puede firmar, certificar y anular documentos."
    ).format(label)


def get_adapter(certificador_name):
    """Instancia el adaptador del Certificador FEL indicado.

    Lanza frappe.throw con «no está implementado aún» si no hay adaptador.
    """
    nit = None
    razon = certificador_name
    if certificador_name and frappe.db.exists("Certificador FEL", certificador_name):
        row = frappe.db.get_value(
            "Certificador FEL",
            certificador_name,
            ["nit", "razon_social"],
            as_dict=True,
        )
        if row:
            nit = row.get("nit")
            razon = row.get("razon_social") or certificador_name
    adapter_cls = resolve_adapter_class(certificador_name, nit)
    if not adapter_cls:
        frappe.throw(message_not_implemented(razon, nit))
    return adapter_cls()


def get_adapter_for_config(config_name):
    """Adaptador de la configuración FEL (vía su Link certificador)."""
    certificador = frappe.db.get_value(
        "Configuracion Factura Electronica",
        config_name,
        "certificador",
    )
    if not certificador:
        frappe.throw(
            _(
                "La configuración {0} no tiene certificador FEL. "
                "Seleccione un certificador antes de firmar o certificar."
            ).format(config_name)
        )
    return get_adapter(certificador)


def _as_failure(exc):
    text = str(exc).strip()
    return False, text or _("No se pudo usar el certificador de esta configuración.")


def sign_xml(config_name, encoded_xml, es_anulacion=None):
    try:
        adapter = get_adapter_for_config(config_name)
    except Exception as exc:
        return _as_failure(exc)
    return adapter.sign(config_name, encoded_xml, es_anulacion=es_anulacion)


def certify_dte(config_name, nit_emisor, xml_dte, identificador):
    try:
        adapter = get_adapter_for_config(config_name)
    except Exception as exc:
        return _as_failure(exc)
    return adapter.certify(config_name, nit_emisor, xml_dte, identificador)


def cancel_dte(config_name, nit_emisor, xml_dte, identificador):
    try:
        adapter = get_adapter_for_config(config_name)
    except Exception as exc:
        return _as_failure(exc)
    return adapter.cancel(config_name, nit_emisor, xml_dte, identificador)


def post_json(config_name, url, payload, headers):
    """Envía JSON con el adaptador de la configuración.

    Lo conserva el generador legado. Un certificador sin adaptador no llega
    a la red: get_adapter_for_config lanza el error de no implementado.
    """
    adapter = get_adapter_for_config(config_name)
    return adapter.post_json(url, payload, headers)
