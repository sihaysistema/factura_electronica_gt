# Copyright (c) 2022, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

# import json

import frappe
from frappe import _
from frappe.utils import flt

from factura_electronica.api import get_special_tax
from factura_electronica.fel_api import validate_config_fel, btn_validator
from factura_electronica.utils.utilities_facelec import get_currency_precision, get_currency_precision_facelec

# NOTA IMPORTANTE: Las funciones comparten la misma logica sin embargo se mantiene separado y codigo
# repetido para no dependen der una sola funcion y estar listo a cualquier cosa repentina que pidan
# tambien se mantiene repetido ya que hay campos que no comparten el mismo nombre entre doctypes
# tomando en cuenta a usuarios legacy

PRECISION = get_currency_precision()  # decimales configuracion en el sistema


@frappe.whitelist()
def sales_invoice_calculator(invoice_name):  # invoice_name
    """Calculador montos, impuestos necesarios para generar docs electronicos

    Args:
        invoice_name (str): name of the invoice
    """

    try:
        # PRECISION = get_currency_precision()
        invoice_data = frappe.get_doc("Sales Invoice", invoice_name)
        config = validate_config_fel(invoice_data.company)[1]
        precision_facelec = get_currency_precision_facelec(config)

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

        # Si la factura es cambiaria se genera un numero de acceso
        # El numero de acceso es numero de referencia que necesita INFILE
        # por cada factura cambiaria se genera uno diferente de 1 a 999,999,999,999
        is_valid = btn_validator(invoice_data.doctype, invoice_data.name)

        if is_valid.get('type_doc') == 'cambiaria':
            # Crea un nuevo registro en 'Access Number FCAM' con ref a la factura
            # desde donde se esta generando
            doc_access = frappe.new_doc('Access Number FCAM')
            doc_access.reference = invoice_data.name
            doc_access.type = invoice_data.doctype
            doc_access.save(ignore_permissions=True)

            invoice_data.access_number_fel = doc_access.name

        # Se obtienen los pagos programados son necesarios para este tipo de doc
        payments = invoice_data.payment_schedule or []
        for payment in payments:
            payment.facelec_credit_amount = flt(invoice_data.grand_total, precision_facelec) * (payment.invoice_portion / 100)

        items = invoice_data.items
        taxes_inv = invoice_data.taxes

        this_company_sales_tax_var = 0
        if len(taxes_inv) > 0:
            this_company_sales_tax_var = taxes_inv[0].rate

        # Calculos para productos tipo bien, servicio, combustible
        total_iva = 0
        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1

            # Si el item iterado tiene monto y cuenta para impuestos especial
            special_tax = get_special_tax(row.item_code, invoice_data.company)
            row.facelec_tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
            row.facelec_tax_rate_per_uom_account = special_tax.get('facelec_tax_rate_per_uom_selling_account', '')

            if row.conversion_factor == 0:
                other_tax_amount = flt(row.facelec_tax_rate_per_uom * row.qty * conversion_fact, PRECISION)

            if row.conversion_factor > 0:
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

            total_iva += row.facelec_sales_tax_for_this_row

        invoice_data.shs_total_iva_fac = flt(total_iva, PRECISION)  # flt(sum([x.facelec_sales_tax_for_this_row for x in items]), PRECISION)
        invoice_data.save(ignore_permissions=True)

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
                shs_otros_impuestos.save(ignore_permissions=True)

        # Se obtiene de nuevo la data para calcular totales
        invoice_data_to_totals = frappe.get_doc("Sales Invoice", invoice_name)
        invoice_data_to_totals.shs_total_otros_imp_incl = flt(sum([x.total for x in invoice_data_to_totals.shs_otros_impuestos]), PRECISION)
        invoice_data_to_totals.save(ignore_permissions=True)

    except Exception as e:
        msg_err = _('Por favor verifique que cada item en la Factura de Venta se encuentren configurados adecuadamente. En el caso de productos de combustible \
            deben tener una cuenta de ingreso, gasto, monto configurado y cuenta de impuestos ingreso, gasto.\
                SI la falla persiste por favor reporte este error con soporte técnico.')
        frappe.msgprint(msg=_(f'{msg_err} <hr> <code>{frappe.get_traceback()} <br> {e}</code>'),
                        title=_('Calculos no generados correctamente'), indicator='red',
                        raise_exception=1)


@frappe.whitelist()
def delivery_note_calculator(invoice_name):
    """Calculador montos, impuestos para Notas de Entrega

    Args:
        invoice_name (str): name of the invoice
    """

    try:
        # PRECISION = get_currency_precision()
        invoice_data = frappe.get_doc("Delivery Note", invoice_name)
        items = invoice_data.items
        taxes_inv = invoice_data.taxes

        this_company_sales_tax_var = 0
        if len(taxes_inv) > 0:
            this_company_sales_tax_var = taxes_inv[0].rate

        # Calculos para productos tipo bien, servicio, combustible
        total_iva = 0
        total_goods = 0
        total_services = 0
        total_fuels = 0

        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1

            # Si el item iterado tiene monto y cuenta para impuestos especial
            special_tax = get_special_tax(row.item_code, invoice_data.company)
            row.shs_dn_tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
            row.shs_dn_tax_rate_per_uom_account = special_tax.get('facelec_tax_rate_per_uom_selling_account', '')

            if row.conversion_factor == 0:
                other_tax_amount = flt(row.shs_dn_tax_rate_per_uom * row.qty * conversion_fact, PRECISION)

            if row.conversion_factor > 0:
                other_tax_amount = flt(row.shs_dn_tax_rate_per_uom * row.qty * row.conversion_factor, PRECISION)

            row.shs_dn_other_tax_amount = other_tax_amount

            amount_minus_excise_tax = flt((row.qty * row.rate) - row.qty * row.shs_dn_tax_rate_per_uom, PRECISION)
            row.shs_dn_amount_minus_excise_tax = amount_minus_excise_tax

            if (row.shs_dn_is_fuel):
                net_services = 0
                net_goods = 0
                net_fuel = flt(row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.shs_dn_gt_tax_net_fuel_amt = net_fuel
                row.shs_dn_gt_tax_net_goods_amt = net_goods
                row.shs_dn_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.shs_dn_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.shs_dn_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.shs_dn_is_good):
                net_services = 0
                net_fuel = 0
                net_goods = flt(row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.shs_dn_gt_tax_net_fuel_amt = net_fuel
                row.shs_dn_gt_tax_net_goods_amt = net_goods
                row.shs_dn_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.shs_dn_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.shs_dn_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.shs_dn_is_service):
                net_goods = 0
                net_fuel = 0
                net_services = flt(row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.shs_dn_gt_tax_net_fuel_amt = net_fuel
                row.shs_dn_gt_tax_net_goods_amt = net_goods
                row.shs_dn_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.shs_dn_gt_tax_net_services_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.shs_dn_sales_tax_for_this_row = tax_for_this_row

            # Totales
            total_iva += row.shs_dn_sales_tax_for_this_row
            total_goods += row.shs_dn_gt_tax_net_goods_amt
            total_services += row.shs_dn_gt_tax_net_services_amt
            total_fuels += row.shs_dn_gt_tax_net_fuel_amt

        invoice_data.shs_dn_total_iva = flt(total_iva, PRECISION)
        invoice_data.shs_dn_gt_tax_fuel = flt(total_fuels, PRECISION)
        invoice_data.shs_dn_gt_tax_goods = flt(total_goods, PRECISION)
        invoice_data.shs_dn_gt_tax_services = flt(total_services, PRECISION)
        invoice_data.save(ignore_permissions=True)

    except Exception as e:
        msg_err = _('Por favor verifique que cada item en la Nota de Entrega se encuentren configurados adecuadamente. \
        SI la falla persiste por favor reporte este error con soporte técnico.')
        frappe.msgprint(msg=_(f'{msg_err} <hr> <code>{frappe.get_traceback()} <br> {e}</code>'),
                        title=_('Calculos no generados correctamente'), indicator='red',
                        raise_exception=1)


@frappe.whitelist()
def purchase_invoice_calculator(invoice_name):
    """Calculador montos, impuestos necesarios para generar docs electronicos

    Args:
        invoice_name (str): name of the invoice
    """

    try:
        # PRECISION = get_currency_precision()
        invoice_data = frappe.get_doc("Purchase Invoice", invoice_name)
        items = invoice_data.items
        taxes_inv = invoice_data.taxes

        # Limpiando campos para casos de duplicacion de facturas
        invoice_data.facelec_tax_retention_guatemala = ""
        invoice_data.numero_autorizacion_fel = ""
        invoice_data.serie_original_del_documento = ""

        this_company_sales_tax_var = 0
        if len(taxes_inv) > 0:
            this_company_sales_tax_var = taxes_inv[0].rate

        # Calculos para productos tipo bien, servicio, combustible
        total_iva = 0
        total_goods = 0
        total_services = 0
        total_fuels = 0

        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1

            # Si el item iterado tiene monto y cuenta para impuestos especial
            special_tax = get_special_tax(row.item_code, invoice_data.company)
            row.facelec_p_tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
            row.facelec_p_tax_rate_per_uom_account = special_tax.get('facelec_tax_rate_per_uom_purchase_account', '')

            if row.conversion_factor == 0:
                other_tax_amount = flt(row.facelec_p_tax_rate_per_uom * row.qty * conversion_fact, PRECISION)

            if row.conversion_factor > 0:
                other_tax_amount = flt(row.facelec_p_tax_rate_per_uom * row.qty * row.conversion_factor, PRECISION)

            row.facelec_p_other_tax_amount = other_tax_amount

            amount_minus_excise_tax = flt((row.qty * row.rate) - row.qty * row.facelec_p_tax_rate_per_uom, PRECISION)
            row.facelec_p_amount_minus_excise_tax = amount_minus_excise_tax

            if (row.facelec_p_is_fuel):
                net_services = 0
                net_goods = 0
                net_fuel = flt(row.facelec_p_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_p_gt_tax_net_fuel_amt = net_fuel
                row.facelec_p_gt_tax_net_goods_amt = net_goods
                row.facelec_p_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_p_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_p_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_p_is_good):
                net_services = 0
                net_fuel = 0
                net_goods = flt(row.facelec_p_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_p_gt_tax_net_fuel_amt = net_fuel
                row.facelec_p_gt_tax_net_goods_amt = net_goods
                row.facelec_p_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_p_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_p_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_p_is_service):
                net_goods = 0
                net_fuel = 0
                net_services = flt(row.facelec_p_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_p_gt_tax_net_fuel_amt = net_fuel
                row.facelec_p_gt_tax_net_goods_amt = net_goods
                row.facelec_p_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_p_gt_tax_net_services_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_p_sales_tax_for_this_row = tax_for_this_row

            # Totales
            total_goods += row.facelec_p_gt_tax_net_goods_amt
            total_services += row.facelec_p_gt_tax_net_services_amt
            total_fuels += row.facelec_p_gt_tax_net_fuel_amt
            total_iva += row.facelec_p_sales_tax_for_this_row

        invoice_data.facelec_p_total_iva = flt(total_iva, PRECISION)  # flt(sum([x.facelec_p_sales_tax_for_this_row for x in items]), PRECISION)
        invoice_data.facelec_p_gt_tax_fuel = flt(total_fuels, PRECISION)
        invoice_data.facelec_p_gt_tax_goods = flt(total_goods, PRECISION)
        invoice_data.facelec_p_gt_tax_services = flt(total_services, PRECISION)
        invoice_data.save(ignore_permissions=True)

        # Agregando otros impuestos si existen
        # Se obtienen las cuentas de impuestos especiales (unicas)
        accounts = list(set([x.facelec_p_tax_rate_per_uom_account for x in items if x.facelec_p_tax_rate_per_uom_account]))

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
                    'parenttype': "Purchase Invoice",
                    'parentfield': "shs_pi_otros_impuestos",
                    'account_head': acc,
                    'total': flt(sum([x.facelec_p_other_tax_amount for x in items if x.facelec_p_tax_rate_per_uom_account == acc]),
                                 PRECISION),
                })
                shs_otros_impuestos.save(ignore_permissions=True)

        # Se obtiene de nuevo la data para calcular totales
        invoice_data_to_totals = frappe.get_doc("Purchase Invoice", invoice_name)
        invoice_data_to_totals.shs_pi_total_otros_imp_incl = flt(sum([x.total for x in invoice_data_to_totals.shs_pi_otros_impuestos]), PRECISION)
        invoice_data_to_totals.save(ignore_permissions=True)

    except Exception as e:
        msg_err = _('Por favor verifique que cada item en la Factura de Compra se encuentren configurados adecuadamente. En el caso de productos de combustible \
            deben tener una cuenta de ingreso, gasto, monto configurado y cuenta de impuestos ingreso, gasto.\
                SI la falla persiste por favor reporte este error con soporte técnico.')
        frappe.msgprint(msg=_(f'{msg_err} <hr> <code>{frappe.get_traceback()} <br> {e}</code>'),
                        title=_('Calculos no generados correctamente'), indicator='red',
                        raise_exception=1)


@frappe.whitelist()
def purchase_order_calculator(invoice_name):
    """Calculador montos, impuestos para Ordenes de Compra

    Args:
        invoice_name (str): name of the invoice
    """

    try:
        # PRECISION = get_currency_precision()
        invoice_data = frappe.get_doc("Purchase Order", invoice_name)
        items = invoice_data.items
        taxes_inv = invoice_data.taxes

        this_company_sales_tax_var = 0
        if len(taxes_inv) > 0:
            this_company_sales_tax_var = taxes_inv[0].rate

        # Calculos para productos tipo bien, servicio, combustible
        total_iva = 0
        total_goods = 0
        total_services = 0
        total_fuels = 0

        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1

            # Si el item iterado tiene monto y cuenta para impuestos especial
            special_tax = get_special_tax(row.item_code, invoice_data.company)
            row.facelec_po_tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
            row.shs_po_tax_rate_per_uom_account = special_tax.get('facelec_tax_rate_per_uom_selling_account', '')

            if row.conversion_factor == 0:
                other_tax_amount = flt(row.facelec_po_tax_rate_per_uom * row.qty * conversion_fact, PRECISION)

            if row.conversion_factor > 0:
                other_tax_amount = flt(row.facelec_po_tax_rate_per_uom * row.qty * row.conversion_factor, PRECISION)

            row.facelec_po_other_tax_amount = other_tax_amount

            amount_minus_excise_tax = flt((row.qty * row.rate) - row.qty * row.facelec_po_tax_rate_per_uom, PRECISION)
            row.facelec_po_amount_minus_excise_tax = amount_minus_excise_tax

            if (row.facelec_po_is_fuel):
                net_services = 0
                net_goods = 0
                net_fuel = flt(row.facelec_po_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_po_gt_tax_net_fuel_amt = net_fuel
                row.facelec_po_gt_tax_net_goods_amt = net_goods
                row.facelec_po_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_po_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_po_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_po_is_good):
                net_services = 0
                net_fuel = 0
                net_goods = flt(row.facelec_po_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_po_gt_tax_net_fuel_amt = net_fuel
                row.facelec_po_gt_tax_net_goods_amt = net_goods
                row.facelec_po_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_po_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_po_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_po_is_service):
                net_goods = 0
                net_fuel = 0
                net_services = flt(row.facelec_po_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_po_gt_tax_net_fuel_amt = net_fuel
                row.facelec_po_gt_tax_net_goods_amt = net_goods
                row.facelec_po_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_po_gt_tax_net_services_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_po_sales_tax_for_this_row = tax_for_this_row

            # Totales
            total_iva += row.facelec_po_sales_tax_for_this_row
            total_goods += row.facelec_po_gt_tax_net_goods_amt
            total_services += row.facelec_po_gt_tax_net_services_amt
            total_fuels += row.facelec_po_gt_tax_net_fuel_amt

        invoice_data.facelec_po_total_iva = flt(total_iva, PRECISION)
        invoice_data.facelec_po_gt_tax_fuel = flt(total_fuels, PRECISION)
        invoice_data.facelec_po_gt_tax_goods = flt(total_goods, PRECISION)
        invoice_data.facelec_po_gt_tax_services = flt(total_services, PRECISION)
        invoice_data.save(ignore_permissions=True)

    except Exception as e:
        msg_err = _('Por favor verifique que cada item en la Orden de compra se encuentren configurados adecuadamente. \
            SI la falla persiste por favor reporte este error con soporte técnico.')
        frappe.msgprint(msg=_(f'{msg_err} <hr> <code>{frappe.get_traceback()} <br> {e}</code>'),
                        title=_('Calculos no generados correctamente'), indicator='red',
                        raise_exception=1)


@frappe.whitelist()
def purchase_receipt_calculator(invoice_name):
    """Calculador montos, impuestos para Recibos de Compra

    Args:
        invoice_name (str): name of the invoice
    """

    try:
        PRECISION = get_currency_precision()
        invoice_data = frappe.get_doc("Purchase Receipt", invoice_name)
        items = invoice_data.items
        taxes_inv = invoice_data.taxes

        this_company_sales_tax_var = 0
        if len(taxes_inv) > 0:
            this_company_sales_tax_var = taxes_inv[0].rate

        # Calculos para productos tipo bien, servicio, combustible
        total_iva = 0
        total_goods = 0
        total_services = 0
        total_fuels = 0

        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1

            # Si el item iterado tiene monto y cuenta para impuestos especial
            special_tax = get_special_tax(row.item_code, invoice_data.company)
            row.facelec_pr_tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
            row.facelec_pr_tax_rate_per_uom_account = special_tax.get('facelec_tax_rate_per_uom_selling_account', '')

            if row.conversion_factor == 0:
                other_tax_amount = flt(row.facelec_pr_tax_rate_per_uom * row.qty * conversion_fact, PRECISION)

            if row.conversion_factor > 0:
                other_tax_amount = flt(row.facelec_pr_tax_rate_per_uom * row.qty * row.conversion_factor, PRECISION)

            row.facelec_pr_other_tax_amount = other_tax_amount

            amount_minus_excise_tax = flt((row.qty * row.rate) - row.qty * row.facelec_pr_tax_rate_per_uom, PRECISION)
            row.facelec_pr_amount_minus_excise_tax = amount_minus_excise_tax

            if (row.facelec_pr_is_fuel):
                net_services = 0
                net_goods = 0
                net_fuel = flt(row.facelec_pr_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_pr_gt_tax_net_fuel_amt = net_fuel
                row.facelec_pr_gt_tax_net_goods_amt = net_goods
                row.facelec_pr_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_pr_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_pr_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_pr_is_good):
                net_services = 0
                net_fuel = 0
                net_goods = flt(row.facelec_pr_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_pr_gt_tax_net_fuel_amt = net_fuel
                row.facelec_pr_gt_tax_net_goods_amt = net_goods
                row.facelec_pr_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_pr_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_pr_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_pr_is_service):
                net_goods = 0
                net_fuel = 0
                net_services = flt(row.facelec_pr_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_pr_gt_tax_net_fuel_amt = net_fuel
                row.facelec_pr_gt_tax_net_goods_amt = net_goods
                row.facelec_pr_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_pr_gt_tax_net_services_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_pr_sales_tax_for_this_row = tax_for_this_row

            # Totales
            total_iva += row.facelec_pr_sales_tax_for_this_row
            total_goods += row.facelec_pr_gt_tax_net_goods_amt
            total_services += row.facelec_pr_gt_tax_net_services_amt
            total_fuels += row.facelec_pr_gt_tax_net_fuel_amt

        invoice_data.facelec_pr_total_iva = flt(total_iva, PRECISION)
        invoice_data.facelec_pr_gt_tax_fuel = flt(total_fuels, PRECISION)
        invoice_data.facelec_pr_gt_tax_goods = flt(total_goods, PRECISION)
        invoice_data.facelec_pr_gt_tax_services = flt(total_services, PRECISION)
        invoice_data.save(ignore_permissions=True)

    except Exception as e:
        msg_err = _('Por favor verifique que cada item en el Recibo de compra se encuentren configurados adecuadamente. \
            SI la falla persiste por favor reporte este error con soporte técnico.')
        frappe.msgprint(msg=_(f'{msg_err} <hr> <code>{frappe.get_traceback()} <br> {e}</code>'),
                        title=_('Calculos no generados correctamente'), indicator='red',
                        raise_exception=1)


@frappe.whitelist()
def sales_order_calculator(invoice_name):
    """Calculador montos, impuestos para Ordenes de Venta

    Args:
        invoice_name (str): name of the invoice
    """

    try:
        PRECISION = get_currency_precision()
        invoice_data = frappe.get_doc("Sales Order", invoice_name)
        items = invoice_data.items
        taxes_inv = invoice_data.taxes

        this_company_sales_tax_var = 0
        if len(taxes_inv) > 0:
            this_company_sales_tax_var = taxes_inv[0].rate

        # Calculos para productos tipo bien, servicio, combustible
        total_iva = 0
        total_goods = 0
        total_services = 0
        total_fuels = 0

        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1

            # Si el item iterado tiene monto y cuenta para impuestos especial
            special_tax = get_special_tax(row.item_code, invoice_data.company)
            row.shs_so_tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
            row.shs_so_tax_rate_per_uom_account = special_tax.get('facelec_tax_rate_per_uom_selling_account', '')

            if row.conversion_factor == 0:
                other_tax_amount = flt(row.shs_so_tax_rate_per_uom * row.qty * conversion_fact, PRECISION)

            if row.conversion_factor > 0:
                other_tax_amount = flt(row.shs_so_tax_rate_per_uom * row.qty * row.conversion_factor, PRECISION)

            row.shs_so_other_tax_amount = other_tax_amount

            amount_minus_excise_tax = flt((row.qty * row.rate) - row.qty * row.shs_so_tax_rate_per_uom, PRECISION)
            row.shs_so_amount_minus_excise_tax = amount_minus_excise_tax

            if (row.shs_so_is_fuel):
                net_services = 0
                net_goods = 0
                net_fuel = flt(row.shs_so_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.shs_so_gt_tax_net_fuel_amt = net_fuel
                row.shs_so_gt_tax_net_goods_amt = net_goods
                row.shs_so_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.shs_so_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.shs_so_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.shs_so_is_good):
                net_services = 0
                net_fuel = 0
                net_goods = flt(row.shs_so_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.shs_so_gt_tax_net_fuel_amt = net_fuel
                row.shs_so_gt_tax_net_goods_amt = net_goods
                row.shs_so_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.shs_so_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.shs_so_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.shs_so_is_service):
                net_goods = 0
                net_fuel = 0
                net_services = flt(row.shs_so_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.shs_so_gt_tax_net_fuel_amt = net_fuel
                row.shs_so_gt_tax_net_goods_amt = net_goods
                row.shs_so_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.shs_so_gt_tax_net_services_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.shs_so_sales_tax_for_this_row = tax_for_this_row

            # Totales
            total_iva += row.shs_so_sales_tax_for_this_row
            total_goods += row.shs_so_gt_tax_net_goods_amt
            total_services += row.shs_so_gt_tax_net_services_amt
            total_fuels += row.shs_so_gt_tax_net_fuel_amt

        invoice_data.shs_so_total_iva = flt(total_iva, PRECISION)
        invoice_data.shs_gt_tax_fuel = flt(total_fuels, PRECISION)
        invoice_data.shs_so_gt_tax_goods = flt(total_goods, PRECISION)
        invoice_data.shs_so_gt_tax_services = flt(total_services, PRECISION)
        invoice_data.save(ignore_permissions=True)

    except Exception as e:
        msg_err = _('Por favor verifique que cada item en la Orden de Venta se encuentren configurados adecuadamente. \
            SI la falla persiste por favor reporte este error con soporte técnico.')
        frappe.msgprint(msg=_(f'{msg_err} <hr> <code>{frappe.get_traceback()} <br> {e}</code>'),
                        title=_('Calculos no generados correctamente'), indicator='red',
                        raise_exception=1)


@frappe.whitelist()
def sales_quotation_calculator(invoice_name):
    """Calculador montos, impuestos para Cotizaciones de venta

    Args:
        invoice_name (str): name of the invoice
    """

    try:
        PRECISION = get_currency_precision()
        invoice_data = frappe.get_doc("Quotation", invoice_name)
        items = invoice_data.items
        taxes_inv = invoice_data.taxes

        this_company_sales_tax_var = 0
        if len(taxes_inv) > 0:
            this_company_sales_tax_var = taxes_inv[0].rate

        # Calculos para productos tipo bien, servicio, combustible
        total_iva = 0
        total_goods = 0
        total_services = 0
        total_fuels = 0

        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1

            # Si el item iterado tiene monto y cuenta para impuestos especial
            special_tax = get_special_tax(row.item_code, invoice_data.company)
            row.facelec_qt_tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
            row.facelec_qt_tax_rate_per_uom_account = special_tax.get('facelec_tax_rate_per_uom_selling_account', '')

            if row.conversion_factor == 0:
                other_tax_amount = flt(row.facelec_qt_tax_rate_per_uom * row.qty * conversion_fact, PRECISION)

            if row.conversion_factor > 0:
                other_tax_amount = flt(row.facelec_qt_tax_rate_per_uom * row.qty * row.conversion_factor, PRECISION)

            row.facelec_qt_other_tax_amount = other_tax_amount

            amount_minus_excise_tax = flt((row.qty * row.rate) - row.qty * row.facelec_qt_tax_rate_per_uom, PRECISION)
            row.facelec_qt_amount_minus_excise_tax = amount_minus_excise_tax

            if (row.facelec_qt_is_fuel):
                net_services = 0
                net_goods = 0
                net_fuel = flt(row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_qt_gt_tax_net_fuel_amt = net_fuel
                row.facelec_qt_gt_tax_net_goods_amt = net_goods
                row.facelec_qt_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_qt_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_qt_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_qt_is_good):
                net_services = 0
                net_fuel = 0
                net_goods = flt(row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_qt_gt_tax_net_fuel_amt = net_fuel
                row.facelec_qt_gt_tax_net_goods_amt = net_goods
                row.facelec_qt_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_qt_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_qt_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.facelec_qt_is_service):
                net_goods = 0
                net_fuel = 0
                net_services = flt(row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.facelec_qt_gt_tax_net_fuel_amt = net_fuel
                row.facelec_qt_gt_tax_net_goods_amt = net_goods
                row.facelec_qt_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.facelec_qt_gt_tax_net_services_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.facelec_qt_sales_tax_for_this_row = tax_for_this_row

            # Totales
            total_iva += row.facelec_qt_sales_tax_for_this_row
            total_goods += row.facelec_qt_gt_tax_net_goods_amt
            total_services += row.facelec_qt_gt_tax_net_services_amt
            total_fuels += row.facelec_qt_gt_tax_net_fuel_amt

        invoice_data.facelec_qt_total_iva = flt(total_iva, PRECISION)
        invoice_data.facelec_qt_gt_tax_fuel = flt(total_fuels, PRECISION)
        invoice_data.facelec_qt_gt_tax_goods = flt(total_goods, PRECISION)
        invoice_data.facelec_qt_gt_tax_services = flt(total_services, PRECISION)
        invoice_data.save(ignore_permissions=True)

        # Agregando otros impuestos si existen
        # Se obtienen las cuentas de impuestos especiales (unicas)
        accounts = list(set([x.facelec_qt_tax_rate_per_uom_account for x in items if x.facelec_qt_tax_rate_per_uom_account]))

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
                    'parenttype': "Quotation",
                    'parentfield': "shs_tax_quotation",
                    'account_head': acc,
                    'total': flt(sum([x.facelec_qt_other_tax_amount for x in items if x.facelec_qt_tax_rate_per_uom_account == acc]),
                                 PRECISION),
                })
                shs_otros_impuestos.save(ignore_permissions=True)

        # Se obtiene de nuevo la data para calcular totales
        invoice_data_to_totals = frappe.get_doc("Quotation", invoice_name)
        invoice_data_to_totals.shs_qt_total_otros_imp_incl = flt(sum([x.total for x in invoice_data_to_totals.shs_tax_quotation]), PRECISION)
        invoice_data_to_totals.save(ignore_permissions=True)

    except Exception as e:
        msg_err = _('Por favor verifique que cada item en la Cotizacion se encuentren configurados adecuadamente. \
            SI la falla persiste por favor reporte este error con soporte técnico.')
        frappe.msgprint(msg=_(f'{msg_err} <hr> <code>{frappe.get_traceback()} <br> {e}</code>'),
                        title=_('Calculos no generados correctamente'), indicator='red',
                        raise_exception=1)


@frappe.whitelist()
def supplier_quotation_calculator(invoice_name):
    """Calculador montos, impuestos para Cotizacion de proveedor

    Args:
        invoice_name (str): name of the invoice
    """

    try:
        PRECISION = get_currency_precision()
        invoice_data = frappe.get_doc("Supplier Quotation", invoice_name)
        items = invoice_data.items
        taxes_inv = invoice_data.taxes

        this_company_sales_tax_var = 0
        if len(taxes_inv) > 0:
            this_company_sales_tax_var = taxes_inv[0].rate

        # Calculos para productos tipo bien, servicio, combustible
        total_iva = 0
        total_goods = 0
        total_services = 0
        total_fuels = 0

        for row in items:
            amount_minus_excise_tax = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1

            # Si el item iterado tiene monto y cuenta para impuestos especial
            special_tax = get_special_tax(row.item_code, invoice_data.company)
            row.shs_spq_tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
            row.shs_spq_tax_rate_per_uom_account = special_tax.get('facelec_tax_rate_per_uom_selling_account', '')

            if row.conversion_factor == 0:
                other_tax_amount = flt(row.shs_spq_tax_rate_per_uom * row.qty * conversion_fact, PRECISION)

            if row.conversion_factor > 0:
                other_tax_amount = flt(row.shs_spq_tax_rate_per_uom * row.qty * row.conversion_factor, PRECISION)

            row.shs_spq_other_tax_amount = other_tax_amount

            amount_minus_excise_tax = flt((row.qty * row.rate) - row.qty * row.shs_spq_tax_rate_per_uom, PRECISION)
            row.shs_spq_amount_minus_excise_tax = amount_minus_excise_tax

            if (row.shs_spq_is_fuel):
                net_services = 0
                net_goods = 0
                net_fuel = flt(row.shs_spq_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.shs_spq_gt_tax_net_fuel_amt = net_fuel
                row.shs_spq_gt_tax_net_goods_amt = net_goods
                row.shs_spq_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.shs_spq_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.shs_spq_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.shs_spq_is_good):
                net_services = 0
                net_fuel = 0
                net_goods = flt(row.shs_spq_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.shs_spq_gt_tax_net_fuel_amt = net_fuel
                row.shs_spq_gt_tax_net_goods_amt = net_goods
                row.shs_spq_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.shs_spq_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.shs_spq_sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (row.shs_spq_is_service):
                net_goods = 0
                net_fuel = 0
                net_services = flt(row.shs_spq_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), PRECISION)

                row.shs_spq_gt_tax_net_fuel_amt = net_fuel
                row.shs_spq_gt_tax_net_goods_amt = net_goods
                row.shs_spq_gt_tax_net_services_amt = net_services

                tax_for_this_row = flt(row.shs_spq_gt_tax_net_services_amt * (this_company_sales_tax_var / 100), PRECISION)
                row.shs_spq_sales_tax_for_this_row = tax_for_this_row

            # Totales
            total_iva += row.shs_spq_sales_tax_for_this_row
            total_goods += row.shs_spq_gt_tax_net_goods_amt
            total_services += row.shs_spq_gt_tax_net_services_amt
            total_fuels += row.shs_spq_gt_tax_net_fuel_amt

        invoice_data.shs_spq_total_iva = flt(total_iva, PRECISION)
        invoice_data.shs_spq_gt_tax_fuel = flt(total_fuels, PRECISION)
        invoice_data.shs_spq_gt_tax_goods = flt(total_goods, PRECISION)
        invoice_data.shs_spq_gt_tax_services = flt(total_services, PRECISION)
        invoice_data.save(ignore_permissions=True)

    except Exception as e:
        msg_err = _('Por favor verifique que cada item en la Cotizacion de Proveedor se encuentren configurados adecuadamente. \
            SI la falla persiste por favor reporte este error con soporte técnico.')
        frappe.msgprint(msg=_(f'{msg_err} <hr> <code>{frappe.get_traceback()} <br> {e}</code>'),
                        title=_('Calculos no generados correctamente'), indicator='red',
                        raise_exception=1)


@frappe.whitelist()
def remove_items_overview(doctype, parent):
    """Elimina las referencias de items agrupados a X factura

    Args:
        doctype (str): Sales Invoice/Purchase Invoice
        parent (str): name PK
    """
    frappe.db.delete('Item Overview', {
        'parent': parent,
        'parenttype': doctype,
    })
    frappe.db.set_value(doctype, parent, 'facelec_total_items_overview', 0)


@frappe.whitelist()
def items_overview(doctype, child_table, docname, company, tax_amt):
    """Genera filas agrupando por item y recalculando los montos de impuestos para item
    para generar doc electronicos, aplica para el escenario de facturas con demasiadas filas
    esto evita que se generen facturas PDF con multiples paginas. Los datos generados
    se usaran para generar el documento electronico.

    Args:
        doctype (str): Sales Invoice/Purchase Invoice
        child_table (str): Sales Invoice Item/Purchase Invoice Item
        docname (str): name PK
        company (str): compania usada en factura
        precision (int): precision de la moneda
        tax_amt (float): tasa iva (12)
    """

    try:
        config = validate_config_fel(company)[1]
        # El usuario puede definir el numero de decimales a usar en la generacion de docs electronicos
        # independiente del numero de decimales del sistema
        precision = get_currency_precision_facelec(config)

        this_company_sales_tax_var = flt(tax_amt, precision)

        # Se obtienen los productos de la factura agrupados
        agrupar = 'item_code, uom, facelec_is_service, facelec_is_good, factelecis_fuel, conversion_factor'
        fields_dt = ['item_code', 'item_name', 'description', 'SUM(qty) AS qty', 'SUM(amount) AS amount',
                     'AVG(rate) AS rate', 'uom', 'facelec_three_digit_uom_code', 'uom', 'conversion_factor',
                     'stock_qty', 'facelec_is_service', 'facelec_is_good', 'factelecis_fuel']

        items_dt = frappe.db.get_list(child_table, filters={'parent': docname, 'parenttype': doctype},
                                      fields=fields_dt, group_by=agrupar)

        if not items_dt:  # Si no hay datos no se hace nada
            return False

        # Para evitar duplicidad se eliminan las referencias y se vuelven a crear
        # Aplica para casos de duplicar/enmendar docs cancelados
        remove_items_overview(doctype, docname)

        # ? * qty = amount ---> amount / qty = rate
        total = 0
        for row in items_dt:
            row.update({
                'qty': flt(row.get('amount'), precision) / flt(row.get('rate', 1), precision)  # encontramos la incognita
            })

            # Calculos sobre los montos ya agrupados
            amount_minus_excise_tax_ok = 0
            other_tax_amount = 0
            net_fuel = 0
            net_services = 0
            net_goods = 0
            tax_for_this_row = 0
            conversion_fact = 1
            special_tax = get_special_tax(row.get('item_code'), company)

            # Por cada fila iterada se creara una nueva fila en la tabla Item Overview
            # con sus respectivos calculos
            item_o = frappe.new_doc('Item Overview')
            item_o.parent = docname
            item_o.parenttype = doctype
            item_o.parentfield = 'items_overview'
            item_o.item_code = row.get('item_code')
            item_o.item_name = row.get('item_name')
            item_o.description = row.get('description')
            item_o.qty = flt(row.get('qty'), PRECISION)  # usa la cantidad de decimales del sistema
            item_o.rate = flt(row.get('rate'), precision)
            item_o.amount = flt(row.get('amount'), precision)
            item_o.tax_rate_per_uom = special_tax.get('facelec_tax_rate_per_uom', 0)
            item_o.uom = row.get('uom')
            item_o.three_digit_uom = row.get('facelec_three_digit_uom_code')
            item_o.conversion_factor = row.get('conversion_factor')
            # item_o.stock_qty = row.get('stock_qty')
            item_o.is_service = row.get('facelec_is_service')
            item_o.is_good = row.get('facelec_is_good')
            item_o.is_fuel = row.get('factelecis_fuel')

            if row.get('conversion_factor') == 0:
                other_tax_amount = flt(item_o.tax_rate_per_uom * item_o.qty * conversion_fact, precision)

            if row.get('conversion_factor') > 0:
                other_tax_amount = flt(item_o.tax_rate_per_uom * item_o.qty * item_o.conversion_factor, precision)

            item_o.other_tax_amount = other_tax_amount

            amount_minus_excise_tax_ok = flt((item_o.qty * item_o.rate) - item_o.qty * item_o.tax_rate_per_uom, precision)
            item_o.amount_minus_excise_tax = amount_minus_excise_tax_ok

            if (item_o.is_fuel):
                net_services = 0
                net_goods = 0
                net_fuel = flt(item_o.amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), precision)

                item_o.net_fuel_amount = net_fuel
                item_o.net_goods_amount = net_goods
                item_o.net_services_amount = net_services

                tax_for_this_row = flt(item_o.net_fuel_amount * (this_company_sales_tax_var / 100), precision)
                item_o.sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (item_o.is_good):
                net_services = 0
                net_fuel = 0
                net_goods = flt(item_o.amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), precision)

                item_o.net_fuel_amount = net_fuel
                item_o.net_goods_amount = net_goods
                item_o.net_services_amount = net_services

                tax_for_this_row = flt(item_o.net_goods_amount * (this_company_sales_tax_var / 100), precision)
                item_o.sales_tax_for_this_row = tax_for_this_row

            tax_for_this_row = 0
            if (item_o.is_service):
                net_goods = 0
                net_fuel = 0
                net_services = flt(item_o.amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)), precision)

                item_o.net_fuel_amount = net_fuel
                item_o.net_goods_amount = net_goods
                item_o.net_services_amount = net_services

                tax_for_this_row = flt(item_o.net_services_amount * (this_company_sales_tax_var / 100), precision)
                item_o.sales_tax_for_this_row = tax_for_this_row

            total += item_o.amount
            item_o.save(ignore_permissions=True)

        # Se actualiza el total de los productos que fueron agrupados
        frappe.db.set_value(doctype, docname, 'facelec_total_items_overview', total)

    except Exception as e:
        msg_err = _('Producto no se agruparon correctamente, verifique que exista una configuracion valida para factura electronica')
        frappe.msgprint(msg=_(f'{msg_err} <hr> <code>{frappe.get_traceback()} <br> {e}</code>'),
                        title=_('Productos no agrupados'), indicator='red',
                        raise_exception=1)
