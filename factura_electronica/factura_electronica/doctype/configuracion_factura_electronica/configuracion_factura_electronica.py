# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

import sys
reload(sys)  
sys.setdefaultencoding('utf-8')

class ConfiguracionFacturaElectronica(Document):
	pass

@frappe.whitelist()
def series_sales_invoice():
	naming_series = frappe.get_meta("Sales Invoice").get_field("naming_series").options or ""
	naming_series = naming_series.split("\n")
	#out = naming_series[0] or (naming_series[1] if len(naming_series) > 1 else None)

	return naming_series