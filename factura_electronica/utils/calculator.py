# Copyright (c) 2022, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import cint, flt

from factura_electronica.utils.utilities_facelec import get_currency_precision


PRECISION = get_currency_precision()


@frappe.whitelist()
def sales_invoice_calculator(invoice_name):
    """
    Calculate the invoice amount
    :param invoice_data:
    :return:
    """

    try:
        invoice_data = frappe.get_doc("Sales Invoice", invoice_name)
        items = invoice_data.items
        taxes_inv = invoice_data.taxes

        # Limpiando campos para casos de duplicacion de facturas
        invoice_data.cae_factura_electronica = ""
        invoice_data.serie_original_del_documento = ""
        invoice_data.numero_autorizacion_fel = ""
        invoice_data.facelec_s_vat_declaration = ""
        invoice_data.facelec_tax_retention_guatemala = ""
        invoice_data.facelec_export_doc = ""
        invoice_data.facelec_export_record = ""
        invoice_data.facelec_record_type = ""
        invoice_data.facelec_consumable_record_type = ""
        invoice_data.facelec_record_number = ""
        invoice_data.facelec_record_value = ""
        invoice_data.access_number_fel = ""

        this_company_sales_tax_var = 0
        if len(taxes_inv) > 0:
            this_company_sales_tax_var = taxes_inv[0].rate

        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0

            other_tax_amount = flt(row.facelec_tax_rate_per_uom * row.qty * row.conversion_factor, PRECISION)
            row.facelec_other_tax_amount = other_tax_amount

            amount_minus_excise_tax = flt((row.qty * row.rate) - row.qty * row.facelec_tax_rate_per_uom, PRECISION)
            row.facelec_amount_minus_excise_tax = amount_minus_excise_tax

            if (row.factelecis_fuel):
                net_services = 0
                net_goods = 0
                net_fuel = flt(row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_gt_tax_net_fuel_amt = net_fuel
                row.facelec_gt_tax_net_goods_amt = net_goods
                row.facelec_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_is_good):
                net_services = 0
                net_fuel = 0
                net_goods = flt(row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_gt_tax_net_fuel_amt = net_fuel
                row.facelec_gt_tax_net_goods_amt = net_goods
                row.facelec_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_is_service):
                net_goods = 0
                net_fuel = 0
                net_services = flt(row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_gt_tax_net_fuel_amt = net_fuel
                row.facelec_gt_tax_net_goods_amt = net_goods
                row.facelec_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_gt_tax_net_services_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_sales_tax_for_this_row = tax_for_this_row

        invoice_data.save()
        invoice_data.notify_update()

    except Exception as e:
        frappe.msgprint(_("Error: {0}").format(e))
