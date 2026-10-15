# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Resolución de Configuración Factura Electrónica por compañía.

La configuración activa es la que está validada (docstatus = 1). Puede haber
varias en el sitio, pero como máximo una activa por compañía.

Punto único de búsqueda: get_active_config_for_company. La regla de
unicidad está en ensure_single_active_configuration. El issue #316
(Compañía + Entidad Certificadora) debe cambiar solo esas dos funciones;
el resto del código ya recibe el name de la configuración.

Las series (Configuracion Series FEL, Configuracion Series y
Serial Configuration For Purchase Invoice) son tablas hijas de
Configuracion Factura Electronica. No llevan compañía propia: quedan
ligadas a la compañía del documento padre y se consultan siempre con
el parent de la configuración ya resuelta.
"""

from __future__ import unicode_literals

import frappe
from frappe import _


def normalize_nit(value):
    """Deja solo letras y números en mayúsculas para comparar NIT."""
    if not value:
        return ""
    return "".join(ch for ch in str(value).upper() if ch.isalnum())


def message_company_required():
    return _("La compañía es obligatoria en Configuración Factura Electrónica.")


def message_missing_company():
    return _(
        "No se indicó la compañía del documento. "
        "No es posible determinar la Configuración Factura Electrónica activa."
    )


def message_no_active_config(company):
    return _(
        "La compañía {0} no tiene una Configuración Factura Electrónica activa. "
        "Cree y valide una configuración para esa compañía."
    ).format(company)


def message_multiple_active_configs(company):
    return _(
        "La compañía {0} tiene más de una Configuración Factura Electrónica activa. "
        "Debe existir solo una configuración validada por compañía."
    ).format(company)


def message_duplicate_on_submit(company, existing_name):
    return _(
        "Ya existe una Configuración Factura Electrónica activa para la compañía {0} ({1}). "
        "Cancele esa configuración antes de validar otra."
    ).format(company, existing_name)


def company_of(doctype, name):
    """Compañía de un documento (Sales Invoice, Purchase Invoice, etc.)."""
    if not doctype or not name:
        return None
    return frappe.db.get_value(doctype, name, "company")


def default_company_name():
    """Compañía por defecto del sitio, si existe."""
    company = None
    try:
        company = frappe.db.get_single_value("Global Defaults", "default_company")
    except Exception:
        company = None
    if company:
        return company
    try:
        return frappe.defaults.get_global_default("company")
    except Exception:
        return None


def active_config_filters(company):
    """Filtros de la configuración activa.

    Único lugar que define qué es una configuración activa. Hoy la clave es
    la compañía (como máximo una validada). El issue #316 ampliará esta
    función a Compañía + Entidad Certificadora; los llamadores no deben
    armar este filtro por su cuenta.
    """
    return {"docstatus": 1, "company": company}


def get_active_fel_configs(company):
    """Filas de configuración que cumplen active_config_filters."""
    if not company:
        return []
    rows = frappe.get_all(
        "Configuracion Factura Electronica",
        filters=active_config_filters(company),
        fields=["name", "regimen"],
        order_by="creation asc",
    )
    return rows or []


def get_active_config_for_company(company):
    """Única búsqueda de la configuración FEL activa de una compañía.

    Todos los generadores, anulaciones, reportes y el cliente deben pasar
    por aquí (directamente o vía validar_configuracion / validate_configuration).
    #316 solo debe cambiar esta función y ensure_single_active_configuration.

    Returns:
        dict: {"ok": True, "name": str, "regimen": str}
              o {"ok": False, "code": str, "message": str}
    """
    if not company:
        return {
            "ok": False,
            "code": "missing_company",
            "message": message_missing_company(),
        }

    configs = get_active_fel_configs(company)
    if len(configs) == 1:
        return {
            "ok": True,
            "name": str(configs[0].get("name")),
            "regimen": str(configs[0].get("regimen") or ""),
        }
    if len(configs) > 1:
        return {
            "ok": False,
            "code": "multiple",
            "message": message_multiple_active_configs(company),
        }
    return {
        "ok": False,
        "code": "none",
        "message": message_no_active_config(company),
    }


# Nombre anterior del mismo helper. No agregar otra búsqueda.
resolve_active_configuration = get_active_config_for_company


def ensure_single_active_configuration(company, current_name=None):
    """Impide validar una segunda configuración activa para la misma compañía.

    Usa get_active_fel_configs para no duplicar el filtro. #316 cambiará
    esta regla a una configuración activa por Compañía + Entidad Certificadora.
    """
    if not company:
        frappe.throw(message_company_required())

    for row in get_active_fel_configs(company):
        if row.get("name") != current_name:
            frappe.throw(message_duplicate_on_submit(company, row.get("name")))


def match_company_by_nit(nit_value, companies):
    """
    Devuelve el name de la compañía cuyo tax_id o nit_face_company coincide
    con el NIT. None si no hay coincidencia única.
    """
    target = normalize_nit(nit_value)
    if not target:
        return None

    matches = []
    for company in companies or []:
        candidates = (company.get("tax_id"), company.get("nit_face_company"))
        for candidate in candidates:
            if normalize_nit(candidate) and normalize_nit(candidate) == target:
                name = company.get("name")
                if name and name not in matches:
                    matches.append(name)
                break

    if len(matches) == 1:
        return matches[0]
    return None


def _companies_for_assignment():
    if not frappe.db.table_exists("Company"):
        return []
    fields = ["name", "tax_id"]
    if frappe.db.has_column("Company", "nit_face_company"):
        fields.append("nit_face_company")
    return frappe.get_all("Company", fields=fields) or []


def assign_company_to_existing_configurations():
    """
    Asigna compañía a configuraciones que no la tienen.

    Orden:
    1. Si el sitio tiene una sola compañía, se usa esa (no rompe sitios de una compañía).
    2. Si el NIT de la configuración coincide con una sola compañía, se usa esa.
    3. Si no, se usa la compañía por defecto del sitio.

    Returns:
        dict: {"updated": int, "skipped": int}
    """
    doctype = "Configuracion Factura Electronica"
    if not frappe.db.table_exists(doctype):
        return {"updated": 0, "skipped": 0}
    if not frappe.db.has_column(doctype, "company"):
        return {"updated": 0, "skipped": 0}

    rows = frappe.db.sql(
        """
        SELECT name, nit_gface
        FROM `tabConfiguracion Factura Electronica`
        WHERE IFNULL(company, '') = ''
        """,
        as_dict=True,
    )
    if not rows:
        return {"updated": 0, "skipped": 0}

    companies = _companies_for_assignment()
    only_company = companies[0].get("name") if len(companies) == 1 else None
    fallback = only_company or default_company_name()

    updated = 0
    skipped = 0
    for row in rows:
        company = only_company or match_company_by_nit(row.get("nit_gface"), companies) or fallback
        if not company:
            skipped += 1
            frappe.log_error(
                message="No se pudo asignar compañía a la configuración {0}".format(row.get("name")),
                title="FEL: configuración sin compañía",
            )
            continue

        frappe.db.set_value(doctype, row.get("name"), "company", company, update_modified=False)
        updated += 1

    return {"updated": updated, "skipped": skipped}
