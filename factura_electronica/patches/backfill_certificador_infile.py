# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Crea el catálogo SAT de certificadores y marca lo ya emitido como INFILE. #316

Pensado para un sitio grande (fogliasana.com, v13): los Envio FEL y las
configuraciones se actualizan con UPDATE masivos, no documento por documento.
No pasa por validate(), así que también cubre configuraciones canceladas.
Es idempotente: solo llena campos vacíos y no vuelve a insertar un NIT.
"""

from __future__ import unicode_literals

import json
import os

import frappe

from factura_electronica.utils.fel_config import normalize_nit

INFILE_NAME = "INFILE"
INFILE_NIT = "12521337"
FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "fixtures",
    "certificador_fel.json",
)


def execute():
    # Frappe v13 corre patches.txt antes de sincronizar el modelo, así que
    # las columnas nuevas todavía no existen. Sincronizar esta app las crea
    # (en v15 el sync global ya ocurrió y esta llamada no cambia nada).
    from frappe.model.sync import sync_for

    sync_for("factura_electronica")
    seed_official_certificadores()
    backfill_infile_links()


def load_official_certificadores():
    with open(FIXTURE, "r") as handle:
        return json.load(handle)


def seed_official_certificadores():
    """Inserta los certificadores del listado SAT que todavía no existen."""
    doctype = "Certificador FEL"
    if not frappe.db.table_exists(doctype):
        return {"created": 0, "skipped": 0}

    created = 0
    skipped = 0
    for row in load_official_certificadores():
        if _certificador_exists(row.get("name"), row.get("nit")):
            skipped += 1
            continue
        doc = frappe.get_doc({
            "doctype": doctype,
            "razon_social": row.get("razon_social"),
            "nit": row.get("nit"),
            "nombre_comercial": row.get("nombre_comercial"),
            "sitio_web": row.get("sitio_web"),
            "fecha_autorizacion_sat": row.get("fecha_autorizacion_sat"),
            "disabled": row.get("disabled") or 0,
            "notes": row.get("notes"),
        })
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True, set_name=row.get("name"))
        created += 1
    return {"created": created, "skipped": skipped}


def _certificador_exists(name, nit):
    if name and frappe.db.exists("Certificador FEL", name):
        return True
    target = normalize_nit(nit)
    if not target:
        return False
    found = frappe.db.sql(
        """
        SELECT name
        FROM `tabCertificador FEL`
        WHERE REPLACE(REPLACE(UPPER(IFNULL(nit, '')), '-', ''), ' ', '') = %s
        LIMIT 1
        """,
        (target,),
    )
    return bool(found)


def infile_certificador_name():
    """Name del certificador INFILE. Lo crea el seed; si ya existía por NIT, usa ese name."""
    if frappe.db.exists("Certificador FEL", INFILE_NAME):
        return INFILE_NAME
    found = frappe.db.sql(
        """
        SELECT name
        FROM `tabCertificador FEL`
        WHERE REPLACE(REPLACE(UPPER(IFNULL(nit, '')), '-', ''), ' ', '') = %s
        LIMIT 1
        """,
        (normalize_nit(INFILE_NIT),),
    )
    if found:
        return found[0][0]
    return INFILE_NAME


def backfill_infile_links():
    """Asigna INFILE y, donde se puede, compañía y configuración. Todo por SQL."""
    if not frappe.db.table_exists("Configuracion Factura Electronica"):
        return {"configs": 0, "envios": 0}
    if not frappe.db.has_column("Configuracion Factura Electronica", "certificador"):
        return {"configs": 0, "envios": 0}

    infile = infile_certificador_name()
    configs = _sql_update(
        """
        UPDATE `tabConfiguracion Factura Electronica`
        SET certificador = %s
        WHERE IFNULL(certificador, '') = ''
        """,
        (infile,),
    )
    _mark_single_default_per_company()

    envios = 0
    if frappe.db.table_exists("Envio FEL") and frappe.db.has_column("Envio FEL", "certificador"):
        envios = _sql_update(
            """
            UPDATE `tabEnvio FEL`
            SET certificador = %s
            WHERE IFNULL(certificador, '') = ''
            """,
            (infile,),
        )
        _backfill_envio_company()
        _backfill_envio_configuracion()

    return {"configs": configs, "envios": envios, "infile": infile}


def _mark_single_default_per_company():
    """Una predeterminada por compañía, la de nombre menor, si todavía no hay ninguna."""
    if not frappe.db.has_column("Configuracion Factura Electronica", "certificador_predeterminado"):
        return 0
    # Las subconsultas van en tablas derivadas: MariaDB no deja leer y
    # actualizar la misma tabla en un solo UPDATE.
    return _sql_update(
        """
        UPDATE `tabConfiguracion Factura Electronica` cfg
        INNER JOIN (
            SELECT company, MIN(name) AS name
            FROM `tabConfiguracion Factura Electronica`
            WHERE docstatus = 1 AND IFNULL(company, '') != ''
            GROUP BY company
        ) pick ON pick.name = cfg.name
        LEFT JOIN (
            SELECT company
            FROM `tabConfiguracion Factura Electronica`
            WHERE docstatus = 1 AND IFNULL(certificador_predeterminado, 0) = 1
            GROUP BY company
        ) already ON already.company = cfg.company
        SET cfg.certificador_predeterminado = 1
        WHERE IFNULL(cfg.certificador_predeterminado, 0) = 0
          AND already.company IS NULL
        """
    )


def _backfill_envio_company():
    """Compañía del Envio FEL desde la factura enlazada. Tres pases, todos masivos."""
    for doctype, table in (
        ("Sales Invoice", "tabSales Invoice"),
        ("Purchase Invoice", "tabPurchase Invoice"),
    ):
        if not frappe.db.table_exists(doctype):
            continue
        if not frappe.db.has_column(doctype, "company"):
            continue
        if frappe.db.has_column(doctype, "numero_autorizacion_fel"):
            _sql_update(
                """
                UPDATE `tabEnvio FEL` envio
                INNER JOIN `{table}` factura
                    ON factura.numero_autorizacion_fel = envio.name
                SET envio.company = factura.company
                WHERE IFNULL(envio.company, '') = ''
                  AND IFNULL(factura.company, '') != ''
                  AND IFNULL(factura.numero_autorizacion_fel, '') != ''
                """.format(table=table)
            )
        _sql_update(
            """
            UPDATE `tabEnvio FEL` envio
            INNER JOIN `{table}` factura
                ON factura.name = envio.serie_para_factura
            SET envio.company = factura.company
            WHERE IFNULL(envio.company, '') = ''
              AND IFNULL(envio.serie_para_factura, '') != ''
              AND IFNULL(factura.company, '') != ''
            """.format(table=table)
        )
        _sql_update(
            """
            UPDATE `tabEnvio FEL` envio
            INNER JOIN `{table}` factura
                ON factura.name = envio.serie_factura_original
            SET envio.company = factura.company
            WHERE IFNULL(envio.company, '') = ''
              AND IFNULL(envio.serie_factura_original, '') != ''
              AND IFNULL(factura.company, '') != ''
            """.format(table=table)
        )


def _backfill_envio_configuracion():
    """Configuración de la compañía y el certificador del envío, si hay una sola candidata clara."""
    if not frappe.db.has_column("Envio FEL", "configuracion"):
        return
    # Un solo documento de configuración para ese par, en cualquier estado.
    _sql_update(
        """
        UPDATE `tabEnvio FEL` envio
        INNER JOIN (
            SELECT company, certificador, MIN(name) AS name
            FROM `tabConfiguracion Factura Electronica`
            WHERE IFNULL(company, '') != '' AND IFNULL(certificador, '') != ''
            GROUP BY company, certificador
            HAVING COUNT(*) = 1
        ) cfg
            ON cfg.company = envio.company AND cfg.certificador = envio.certificador
        SET envio.configuracion = cfg.name
        WHERE IFNULL(envio.configuracion, '') = ''
          AND IFNULL(envio.company, '') != ''
          AND IFNULL(envio.certificador, '') != ''
        """
    )
    # Varias configuraciones: la activa marcada como predeterminada, si es única.
    _sql_update(
        """
        UPDATE `tabEnvio FEL` envio
        INNER JOIN (
            SELECT company, certificador, MIN(name) AS name
            FROM `tabConfiguracion Factura Electronica`
            WHERE docstatus = 1 AND IFNULL(certificador_predeterminado, 0) = 1
            GROUP BY company, certificador
            HAVING COUNT(*) = 1
        ) cfg
            ON cfg.company = envio.company AND cfg.certificador = envio.certificador
        SET envio.configuracion = cfg.name
        WHERE IFNULL(envio.configuracion, '') = ''
          AND IFNULL(envio.company, '') != ''
        """
    )
    # Si no hay predeterminada, la única configuración validada del par.
    _sql_update(
        """
        UPDATE `tabEnvio FEL` envio
        INNER JOIN (
            SELECT company, certificador, MIN(name) AS name
            FROM `tabConfiguracion Factura Electronica`
            WHERE docstatus = 1
            GROUP BY company, certificador
            HAVING COUNT(*) = 1
        ) cfg
            ON cfg.company = envio.company AND cfg.certificador = envio.certificador
        SET envio.configuracion = cfg.name
        WHERE IFNULL(envio.configuracion, '') = ''
          AND IFNULL(envio.company, '') != ''
        """
    )


def _sql_update(query, values=None):
    frappe.db.sql(query, values or ())
    row = frappe.db.sql("SELECT ROW_COUNT()")
    if not row:
        return 0
    try:
        return int(row[0][0] or 0)
    except (TypeError, ValueError):
        return 0
