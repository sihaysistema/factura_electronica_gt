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
				}
			]
		}
	]
