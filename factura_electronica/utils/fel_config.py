# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Resolución de Configuración Factura Electrónica por compañía y certificador.

La configuración activa es la que está validada (docstatus = 1). Puede haber
varias activas para la misma compañía, una por certificador (Acuerdo de
Directorio SAT 13-2018, artículo 14). No puede haber dos activas para el
mismo par compañía + certificador.

Para un documento nuevo: si la compañía tiene una sola configuración activa
se usa esa; si tiene varias, se usa la marcada como certificador
predeterminado (exactamente una por compañía), salvo que el llamador pase
una configuración explícita.

Anulaciones y documentos de seguimiento no usan la configuración activa:
buscan el Envio FEL original y usan la configuración y el certificador con
los que se emitió.

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


def message_certificador_required():
    return _("El certificador es obligatorio en Configuración Factura Electrónica.")


def message_no_active_config(company, certificador=None):
    if certificador:
        return _(
            "La compañía {0} no tiene una Configuración Factura Electrónica activa "
            "para el certificador {1}."
        ).format(company, certificador)
    return _(
        "La compañía {0} no tiene una Configuración Factura Electrónica activa. "
        "Cree y valide una configuración para esa compañía."
    ).format(company)


def message_no_default_certifier(company):
    return _(
        "La compañía {0} tiene varias Configuraciones Factura Electrónica activas "
        "y ninguna está marcada como certificador predeterminado. "
        "Marque exactamente una como predeterminada."
    ).format(company)


def message_multiple_defaults(company):
    return _(
        "La compañía {0} tiene más de una Configuración Factura Electrónica "
        "marcada como certificador predeterminado. Debe existir exactamente una."
    ).format(company)


def message_duplicate_on_submit(company, certificador, existing_name):
    return _(
        "Ya existe una Configuración Factura Electrónica activa para la compañía {0} "
        "y el certificador {1} ({2}). Cancele esa configuración antes de validar otra."
    ).format(company, certificador, existing_name)


def message_certificador_disabled(certificador):
    return _(
        "El certificador {0} está deshabilitado y no puede seleccionarse en una "
        "configuración nueva o editada. Elija un certificador activo. "
        "Los documentos históricos conservan el enlace."
    ).format(certificador)


def message_cannot_delete_certificador(name, envios, configs):
    return _(
        "No se puede eliminar el certificador {0} porque lo usan {1} registro(s) de Envio FEL "
        "y {2} configuración(es) de Factura Electrónica. Deshabilítelo en lugar de eliminarlo."
    ).format(name, envios, configs)


def message_missing_original_envio(docname):
    return _(
        "No se encontró el Envio FEL del documento {0}. "
        "La anulación y los documentos de seguimiento deben usar el certificador que emitió el original."
    ).format(docname)


def message_envio_without_config(envio_name):
    return _(
        "El Envio FEL {0} no tiene la configuración con la que se certificó el documento. "
        "No es posible anular ni dar seguimiento con el certificador original."
    ).format(envio_name)


def message_config_cancelled(config_name):
    return _(
        "La Configuración Factura Electrónica {0} con la que se certificó el documento original está cancelada. "
        "No se puede anular ni emitir un documento de seguimiento con otro certificador."
    ).format(config_name)


def message_config_not_active(config_name):
    return _(
        "La Configuración Factura Electrónica {0} con la que se certificó el documento original no está validada. "
        "Valide esa configuración antes de anular o emitir el seguimiento."
    ).format(config_name)


def message_certifier_disabled_for_followup(certificador):
    return _(
        "El certificador {0} que emitió el documento original está deshabilitado. "
        "Rehabilítelo para anular o emitir el seguimiento con ese mismo certificador."
    ).format(certificador)


def message_explicit_config_missing(configuracion):
    return _(
        "No existe la Configuración Factura Electrónica {0} indicada para este documento."
    ).format(configuracion)


def message_explicit_config_company(configuracion, company):
    return _(
        "La Configuración Factura Electrónica {0} no pertenece a la compañía {1}."
    ).format(configuracion, company)


def message_explicit_config_inactive(configuracion):
    return _(
        "La Configuración Factura Electrónica {0} no está activa. "
        "Valide la configuración del certificador que desea usar."
    ).format(configuracion)


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


def _checked(value):
    return str(value) in ("1", "True", "true")


def _ok_config(row):
    return {
        "ok": True,
        "name": str(row.get("name")),
        "regimen": str(row.get("regimen") or ""),
        "certificador": row.get("certificador"),
    }


def active_config_filters(company, certificador=None):
    """Filtros de la configuración activa.

    Único lugar que define qué es una configuración activa: validada, de esa
    compañía y, si se indica, de ese certificador. Como máximo una activa por
    par compañía + certificador. Los llamadores no arman este filtro.
    """
    filters = {"docstatus": 1, "company": company}
    if certificador:
        filters["certificador"] = certificador
    return filters


def get_active_fel_configs(company, certificador=None):
    """Filas de configuración que cumplen active_config_filters."""
    if not company:
        return []
    rows = frappe.get_all(
        "Configuracion Factura Electronica",
        filters=active_config_filters(company, certificador),
        fields=["name", "regimen", "certificador", "certificador_predeterminado"],
        order_by="creation asc",
    )
    return rows or []


def get_active_config_for_company(company, certificador=None, configuracion=None):
    """Configuración FEL para un documento nuevo.

    Si se pasa configuracion, se usa esa (debe estar activa y ser de la
    compañía). Si no, una sola configuración activa se usa tal cual. Si hay
    varias, se usa la marcada como certificador predeterminado.

    Las anulaciones no pasan por aquí: usan resolve_original_configuration.

    Returns:
        dict: {"ok": True, "name": str, "regimen": str, "certificador": str}
              o {"ok": False, "code": str, "message": str}
    """
    if not company:
        return {
            "ok": False,
            "code": "missing_company",
            "message": message_missing_company(),
        }

    if configuracion:
        return _explicit_configuration(company, configuracion, certificador)

    configs = get_active_fel_configs(company, certificador)
    if len(configs) == 1:
        return _ok_config(configs[0])
    if len(configs) == 0:
        return {
            "ok": False,
            "code": "none",
            "message": message_no_active_config(company, certificador),
        }

    defaults = [row for row in configs if _checked(row.get("certificador_predeterminado"))]
    if len(defaults) == 1:
        return _ok_config(defaults[0])
    if len(defaults) == 0:
        return {
            "ok": False,
            "code": "no_default",
            "message": message_no_default_certifier(company),
        }
    return {
        "ok": False,
        "code": "multiple_defaults",
        "message": message_multiple_defaults(company),
    }


def _explicit_configuration(company, configuracion, certificador=None):
    row = frappe.db.get_value(
        "Configuracion Factura Electronica",
        configuracion,
        ["name", "regimen", "company", "certificador", "docstatus"],
        as_dict=True,
    )
    if not row:
        return {
            "ok": False,
            "code": "missing_config",
            "message": message_explicit_config_missing(configuracion),
        }
    if row.get("company") != company:
        return {
            "ok": False,
            "code": "wrong_company",
            "message": message_explicit_config_company(configuracion, company),
        }
    if certificador and row.get("certificador") != certificador:
        return {
            "ok": False,
            "code": "wrong_certificador",
            "message": message_no_active_config(company, certificador),
        }
    if int(row.get("docstatus") or 0) != 1:
        return {
            "ok": False,
            "code": "inactive",
            "message": message_explicit_config_inactive(configuracion),
        }
    return _ok_config(row)


# Nombre anterior del mismo helper. No agregar otra búsqueda.
resolve_active_configuration = get_active_config_for_company


def ensure_single_active_configuration(company, certificador, current_name=None):
    """Impide validar una segunda configuración activa del mismo certificador.

    La clave es compañía + certificador. Dos certificadores distintos de la
    misma compañía sí pueden estar activos a la vez.
    """
    if not company:
        frappe.throw(message_company_required())
    if not certificador:
        frappe.throw(message_certificador_required())

    for row in get_active_fel_configs(company, certificador):
        if row.get("name") != current_name:
            frappe.throw(message_duplicate_on_submit(company, certificador, row.get("name")))


def ensure_single_default_for_company(doc):
    """Deja exactamente un certificador predeterminado entre las activas.

    Si esta configuración es la única activa, queda marcada. Si se marca
    como predeterminada, se apaga la marca en las demás activas de la
    compañía. Si hay varias activas y ninguna marca, se rechaza el guardado.
    """
    if int(doc.docstatus or 0) != 1:
        return

    company = doc.company
    current_name = doc.name
    others = [
        row for row in get_active_fel_configs(company)
        if row.get("name") != current_name
    ]
    other_defaults = [
        row for row in others if _checked(row.get("certificador_predeterminado"))
    ]

    if _checked(doc.certificador_predeterminado):
        for row in other_defaults:
            frappe.db.set_value(
                "Configuracion Factura Electronica",
                row.get("name"),
                "certificador_predeterminado",
                0,
                update_modified=False,
            )
        return

    if not others:
        doc.certificador_predeterminado = 1
        return

    if len(other_defaults) == 1:
        return

    if len(other_defaults) > 1:
        frappe.throw(message_multiple_defaults(company))

    frappe.throw(message_no_default_certifier(company))


def assert_certificador_selectable(certificador, previous=None):
    """Impide elegir un certificador deshabilitado en una configuración nueva.

    Si la configuración ya apuntaba a ese certificador, el enlace histórico
    se conserva aunque ahora esté deshabilitado.
    """
    if not certificador:
        frappe.throw(message_certificador_required())
    if certificador == previous:
        return
    disabled = frappe.db.get_value("Certificador FEL", certificador, "disabled")
    if _checked(disabled):
        frappe.throw(message_certificador_disabled(certificador))


def prevent_certificador_deletion(name):
    """Bloquea borrar un certificador usado por Envio FEL o por una configuración."""
    envios = 0
    configs = 0
    if frappe.db.table_exists("Envio FEL") and frappe.db.has_column("Envio FEL", "certificador"):
        envios = frappe.db.count("Envio FEL", {"certificador": name}) or 0
    if frappe.db.table_exists("Configuracion Factura Electronica") and frappe.db.has_column(
        "Configuracion Factura Electronica", "certificador"
    ):
        configs = frappe.db.count("Configuracion Factura Electronica", {"certificador": name}) or 0
    if envios or configs:
        frappe.throw(message_cannot_delete_certificador(name, envios, configs))


def apply_certifier_url_defaults(doc):
    """Copia las URL del certificador solo a los campos que siguen vacíos."""
    if not doc.certificador:
        return
    if not frappe.db.exists("Certificador FEL", doc.certificador):
        return
    cert = frappe.db.get_value(
        "Certificador FEL",
        doc.certificador,
        ["url_firma", "url_dte", "url_anulacion", "url_pdf"],
        as_dict=True,
    )
    if not cert:
        return
    if not doc.url_firma and cert.get("url_firma"):
        doc.url_firma = cert.get("url_firma")
    if not doc.url_dte and cert.get("url_dte"):
        doc.url_dte = cert.get("url_dte")
    if not doc.url_de_anulacion and cert.get("url_anulacion"):
        doc.url_de_anulacion = cert.get("url_anulacion")
    if not doc.url_descarga_pdf and cert.get("url_pdf"):
        doc.url_descarga_pdf = cert.get("url_pdf")


def stamp_envio_fel(envio, config_name):
    """Escribe compañía, configuración y certificador en el Envio FEL que se guarda."""
    if not envio or not config_name:
        return envio
    envio.configuracion = config_name
    row = frappe.db.get_value(
        "Configuracion Factura Electronica",
        config_name,
        ["company", "certificador"],
        as_dict=True,
    )
    if row:
        envio.company = row.get("company")
        envio.certificador = row.get("certificador")
    return envio


def find_envio_fel_for_document(doctype, docname):
    """Name (UUID) del Envio FEL que certificó el documento, si existe."""
    if not doctype or not docname:
        return None
    if frappe.db.has_column(doctype, "numero_autorizacion_fel"):
        uuid = frappe.db.get_value(doctype, docname, "numero_autorizacion_fel")
        if uuid and frappe.db.exists("Envio FEL", uuid):
            return uuid
    for fieldname in ("serie_para_factura", "serie_factura_original"):
        name = frappe.db.get_value("Envio FEL", {fieldname: docname}, "name")
        if name:
            return name
    return None


def resolve_original_configuration(doctype, docname):
    """Configuración y certificador del Envio FEL original.

    No consulta la configuración activa ni el predeterminado. Si esa
    configuración está cancelada o el certificador está deshabilitado,
    devuelve un error en español.

    Returns:
        dict: {"ok": True, "name", "certificador", "envio", "company"}
              o {"ok": False, "code", "message"}
    """
    envio_name = find_envio_fel_for_document(doctype, docname)
    if not envio_name:
        return {
            "ok": False,
            "code": "missing_envio",
            "message": message_missing_original_envio(docname),
        }

    envio = frappe.db.get_value(
        "Envio FEL",
        envio_name,
        ["name", "configuracion", "certificador", "company"],
        as_dict=True,
    ) or {}
    config_name = envio.get("configuracion")
    if not config_name:
        return {
            "ok": False,
            "code": "missing_config",
            "message": message_envio_without_config(envio_name),
        }

    config = frappe.db.get_value(
        "Configuracion Factura Electronica",
        config_name,
        ["name", "docstatus", "certificador", "company"],
        as_dict=True,
    )
    if not config:
        return {
            "ok": False,
            "code": "missing_config",
            "message": message_envio_without_config(envio_name),
        }

    docstatus = int(config.get("docstatus") or 0)
    if docstatus == 2:
        return {
            "ok": False,
            "code": "cancelled",
            "message": message_config_cancelled(config_name),
        }
    if docstatus != 1:
        return {
            "ok": False,
            "code": "inactive",
            "message": message_config_not_active(config_name),
        }

    certificador = envio.get("certificador") or config.get("certificador")
    if certificador:
        disabled = frappe.db.get_value("Certificador FEL", certificador, "disabled")
        if _checked(disabled):
            return {
                "ok": False,
                "code": "certificador_disabled",
                "message": message_certifier_disabled_for_followup(certificador),
            }

    return {
        "ok": True,
        "name": config.get("name"),
        "certificador": certificador,
        "envio": envio_name,
        "company": config.get("company") or envio.get("company"),
    }


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
