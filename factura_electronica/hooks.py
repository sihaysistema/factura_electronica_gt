# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

from factura_electronica.fixtures import fill_fixtures

app_name = "factura_electronica"
app_title = "Factura Electronica"
app_publisher = "Frappe"
app_description = "Aplicacion para la generacion de facturas electronicas."
app_icon = "octicon octicon-desktop-download"
app_color = "#112C5E"
app_email = "m.monroyc22@gmail.com"
app_license = "GNU General Public License (v3)"
app_include_js = {"public/js/facelec.js",
        "public/js/sales_invoice.js",
        "public/js/delivery_note.js",
        "public/js/sales_order.js",
        "public/js/sales_quotation.js",
        "public/js/purchase_invoice.js",
        "public/js/purchase_receipt.js",
        "public/js/purchase_order.js",
        "public/js/supplier_quotation.js",
        "public/js/goalSeek.js",
        "public/js/sales_invoice_actions.js"}
# es-GT: Indica la existencia de campos a la medida para agregar a la instalación estandar de ERPNext
# en-US: Indicates the existense of custom fields to add to existing ERPNext installation
# fixtures = ["Custom Field", "Tax Category"]

fixtures = fill_fixtures()
jenv = {
    "methods": [
        'currency_in_words:factura_electronica.currency_in_words',
        'fel_qr_svg:factura_electronica.fel.qrcode.create_fel_svg_qrcode'
    ]
}

# Includes in <head>
# ------------------
# es-GT: Incluye los archivos .js, .css en el header html del escritorio, asi cargan automaticamente.
# en-US: Includes the .js, .css in the desk.html header, for automatic loading.
# include js, css files in header of desk.html
# app_include_css = "/assets/factura_electronica/css/factura_electronica.css"
app_include_js = ["/assets/factura_electronica/js/facelec.min.js", "/assets/factura_electronica/js/qrcode.min.js"]

# include js, css files in header of web template
# web_include_css = "/assets/factura_electronica/css/factura_electronica.css"
# web_include_js = "/assets/factura_electronica/js/factura_electronica.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# "Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "factura_electronica.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "factura_electronica.install.before_install"
# after_install = "factura_electronica.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "factura_electronica.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Sales Invoice": {
        "on_submit": ["factura_electronica.api.pos_calculations",
                      "factura_electronica.api.generate_access_number"],
        "after_insert": "factura_electronica.api.generate_access_number",
    },
    "Purchase Invoice": {
        # "on_save": "factura_electronica.api.get_tax_html",
        # "on_cancel": "method",
        "on_submit": "factura_electronica.controllers.gl_entry.item_expense_acct_excise_tax_gl_correction"
    },
    # "Sales Invoice": {
    #     # "on_save": "factura_electronica.api.get_tax_html",
    #     "on_cancel": "method",
    #     "on_trash": "method"
    # }
    'Customer': {
        'on_update': 'factura_electronica.api_erp.custom_customer_info'
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"factura_electronica.tasks.all"
# 	],
# 	"daily": [
# 		"factura_electronica.tasks.daily"
# 	],
# 	"hourly": [
# 		"factura_electronica.tasks.hourly"
# 	],
# 	"weekly": [
# 		"factura_electronica.tasks.weekly"
# 	]
# 	"monthly": [
# 		"factura_electronica.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "factura_electronica.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "factura_electronica.event.get_events"
# }
