# -*- coding: utf-8 -*-
"""Optional SAT receiver-name lookup on Sales Invoice submit."""

from __future__ import unicode_literals

import json
import urllib.request

import frappe

SAT_RECEIVER_URL = "https://consultareceptores.feel.com.gt/rest/action"
SAT_LOOKUP_TIMEOUT = 10
SAT_LOOKUP_FIELD = "lookup_receiver_name_on_submit"


def sat_lookup_enabled():
    """True only when a submitted FEL configuration turns the lookup on."""
    try:
        value = frappe.db.get_value(
            "Configuracion Factura Electronica",
            {"docstatus": 1},
            SAT_LOOKUP_FIELD,
        )
    except Exception:
        return False
    return value in (1, "1", True)


def buscar_nombre(doc, method):
    """Look up the SAT receiver name when the setting is on.

    customer_name is never changed. Network and parse errors are logged
    and do not block submit.
    """
    if not sat_lookup_enabled():
        return None
    if getattr(doc, "es_dpi", False) or getattr(doc, "es_pasaporte", False):
        return None
    try:
        result_llave = frappe.db.sql(
            "SELECT `tabConfiguracion Factura Electronica`.`llave_ws` "
            "FROM `tabConfiguracion Factura Electronica` "
            "WHERE `tabConfiguracion Factura Electronica`.`docstatus` = 1"
        )
        llave = result_llave[0][0] if result_llave else None
        result_alias = frappe.db.sql(
            "SELECT `tabConfiguracion Factura Electronica`.`Alias` "
            "FROM `tabConfiguracion Factura Electronica` "
            "WHERE `tabConfiguracion Factura Electronica`.`docstatus` = 1"
        )
        alias = result_alias[0][0] if result_alias else None
        payload = {
            "emisor_codigo": alias,
            "emisor_clave": llave,
            "nit_consulta": doc.nit_face_customer,
        }
        payload_json = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        request = urllib.request.Request(SAT_RECEIVER_URL, data=payload_json, headers=headers)
        with urllib.request.urlopen(request, timeout=SAT_LOOKUP_TIMEOUT) as response:
            response_json = json.loads(response.read().decode("utf-8"))
        if response_json and response_json.get("nombre"):
            frappe.db.set_value(
                "Sales Invoice",
                doc.name,
                "nombre_segun_sat",
                response_json.get("nombre"),
            )
        else:
            frappe.log_error(
                message="The SAT response has no receiver name",
                title="FEL receiver lookup",
            )
        return response_json
    except Exception as exc:
        frappe.log_error(
            message="FEL receiver lookup failed: {0}".format(exc),
            title="FEL receiver lookup",
        )
        return None
