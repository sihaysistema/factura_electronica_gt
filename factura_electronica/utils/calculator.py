# Copyright (c) 2022, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from factura_electronica.utils.utilities_facelec import get_currency_precision
from factura_electronica.api import get_special_tax

PRECISION = get_currency_precision()


@frappe.whitelist()
def sales_invoice_calculator(invoice_name):
    """
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

        # Calculos para productos tipo bien, servicio, combustible
        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1

            if row.conversion_factor == 0:
                other_tax_amount = flt(row.facelec_tax_rate_per_uom * row.qty * conversion_fact, PRECISION)

            if row.conversion_factor > 0:
                other_tax_amount = flt(row.facelec_tax_rate_per_uom * row.qty * row.conversion_factor, PRECISION)

            row.facelec_other_tax_amount = other_tax_amount

            amount_minus_excise_tax = flt((row.qty * row.rate) - row.qty * row.facelec_tax_rate_per_uom, PRECISION)
            row.facelec_amount_minus_excise_tax = amount_minus_excise_tax

            if (row.factelecis_fuel):
                # Se obtiene monto y cuenta para impuestos especial
                special_tax = get_special_tax(row.item_code, invoice_data.company)
                row.facelec_tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
                row.facelec_tax_rate_per_uom_account = special_tax.get('facelec_tax_rate_per_uom_selling_account', '')

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

        invoice_data.shs_total_iva_fac = flt(sum([x.facelec_sales_tax_for_this_row for x in items]), PRECISION)
        invoice_data.save()

        # Agregando otros impuestos si existen

        # Se obtienen las cuentas de impuestos especiales (unicas)
        accounts = list(set([x.facelec_tax_rate_per_uom_account for x in items if x.facelec_tax_rate_per_uom_account]))

        # Para tener siempre un calculo correcto: se eliminan las referencias y se vuelven a generar
        frappe.db.delete('Otros Impuestos Factura Electronica', {
            'parent': invoice_data.name,
        })

        # Si hay cuenta para procesar
        if accounts:
            # Por cada cuenta se agrega un fila a 'Otros Impuestos Factura Electronica'
            for acc in accounts:
                shs_otros_impuestos = frappe.get_doc({
                    'doctype': 'Otros Impuestos Factura Electronica',
                    'parent': invoice_data.name,
                    'parenttype': "Sales Invoice",
                    'parentfield': "shs_otros_impuestos",
                    'account_head': acc,
                    'total': flt(sum([x.facelec_other_tax_amount for x in items if x.facelec_tax_rate_per_uom_account == acc]),
                                 PRECISION),
                })
                shs_otros_impuestos.save()

        # Se obtiene de nuevo la data para calcular totales
        invoice_data_to_totals = frappe.get_doc("Sales Invoice", invoice_name)
        invoice_data_to_totals.shs_total_otros_imp_incl = flt(sum([x.total for x in invoice_data_to_totals.shs_otros_impuestos]), PRECISION)
        invoice_data_to_totals.save()

    except Exception as e:
        frappe.msgprint(frappe.get_traceback())
        frappe.msgprint(_("Error: {0}").format(e))
