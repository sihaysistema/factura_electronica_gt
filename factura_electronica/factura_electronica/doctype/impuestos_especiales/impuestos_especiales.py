# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ImpuestosEspeciales(Document):
	pass

@frappe.whitelist()
def series_factura_especial():
	series = frappe.get_meta("Purchase Invoice").get_field("naming_series").options or ""
	series = series.split('\n')

	return series
