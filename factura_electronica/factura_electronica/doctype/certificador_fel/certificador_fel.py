# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document

from factura_electronica.utils.fel_config import prevent_certificador_deletion


class CertificadorFEL(Document):
    def validate(self):
        if self.nit:
            self.nit = str(self.nit).strip()
        if self.razon_social:
            self.razon_social = str(self.razon_social).strip()

    def on_trash(self):
        prevent_certificador_deletion(self.name)
