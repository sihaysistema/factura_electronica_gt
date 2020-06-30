# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
    return [
        {
            "label": _("Configuración"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Configuracion Factura Electronica",
                    "description": _("Configuracion para factura electronicas"),
                    "onboard": 1,
                }
            ]
        },
        {
            "label": _("Registro Facturas Electronicas"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Envios Facturas Electronicas",
                    "description": _("Encuentre todas las facturas generadas detalladamente."),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Envio FEL",
                    "description": _("Registro estado de las peticion FEL"),
                    "onboard": 1
                }
            ]
        },
        {
            "label": _("Batches"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Batch Electronic Invoice",
                    "description": _("Batch generator for electronic invoicing"),
                    "onboard": 1
                },
                {
                    "type": "doctype",
                    "name": "Batch Status",
                    "description": _("Batch Status"),
                    "onboard": 1
                }
            ]
        },
        {
            "label": _("Taxes"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Purchase and Sales Ledger Tax Declaration",
                    "description": _("Purchase and Sales Ledger Tax Declaration"),
                    "onboard": 1
                },
                {
                    "type": "report",
                    "label": _("Purchase and Sales Ledger Tax Declaration Report"),
                    "name": "Purchase and Sales Ledger Tax Declaration",
                    "is_query_report": True,
                    "dependencies": ["Sales Invoice", "Purchase Invoice"],
                    "onboard": 1
                }
            ]
        }
    ]
