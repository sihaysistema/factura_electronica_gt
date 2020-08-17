# -*- coding: utf-8 -*-
# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class VATDeclaration(Document):
    def before_cancel(self):
        """
        Se ejecuta al momento antes de cancelar un documento, por cada doctype
        donde se encuentre una referencia, actualizara el campo a un valor vacio
        """
        pass

    def on_cancel(self):
        """
        Se ejecuta al momento de cancelar un documento, por cada doctype
        donde se encuentre una referencia, actualizara el campo a un valor vacio
        """
        # Por cada declaracion
        for declaration in self.declaration_items:
            # Validacion extra, si existe
            if frappe.db.exists(declaration.get('link_doctype'), {'name': declaration.get('link_name')}):

                if declaration.get('link_doctype') == 'Sales Invoice':
                    frappe.db.sql(
                        f'''
                            UPDATE `tabSales Invoice` SET facelec_s_vat_declaration=""
                            WHERE name="{declaration.get('link_name')}"
                        ''')  # actualiza a un valor ""

                if declaration.get('link_doctype') == 'Purchase Invoice':
                    frappe.db.sql(
                    f'''
                        UPDATE `tabPurchase Invoice` SET facelec_p_vat_declaration=""
                        WHERE name="{declaration.get('link_name')}"
                    ''')  # actualiza a un valor ""

    def on_submit(self):
        # TODO: Crear referencias desde aqui
        pass
