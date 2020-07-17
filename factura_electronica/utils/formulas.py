# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict
from frappe.utils import flt


def amount_converter(monto, currency_exchange, from_currency="GTQ", to_currency="GTQ"):
    """
    Conversor de montos, en funcion a from_currency, to_currency

    Args:
        monto (float): Monto a convertir
        currency_exchange (float): Tipo cambio usando en factura de venta
        from_currency (str, optional): Moneda en codigo ISO. Defaults to "GTQ".
        to_currency (str, optional): Moneda en codigo ISO. Defaults to "GTQ".

    Returns:
        float: Monto con conversion, en caso aplique
    """

    # Si se maneja la misma moneda se retorna el mismo monto
    if (from_currency == "GTQ" and to_currency == "GTQ") \
        or (from_currency == "USD" and to_currency == "USD"):
        return monto

    # Si hay que convertir de GTQ a USD
    if from_currency == "GTQ" and to_currency == "USD":
        return (monto * (1/currency_exchange))

    # Si hay que convertir de USD a GTQ
    if from_currency == "USD" and to_currency == "GTQ":
        return (monto * currency_exchange)

    return monto


# Aplicara el calculo no importando la moneda
# Nota aplicarle conversion si es necesario
def apply_formula_isr(monto, invoice_name, company, applicable_tax_rate, scenario):
    """
    Formula para obtener ISR

    Args:
        monto (float): Monto con IVA

    Returns:
        float: ISR
    """
    if not invoice_name:
        frappe.msgprint(_('No se encontro tasa de iva'))
        return
    rango_isr = (0, 30000,)

    tasa_iva = (frappe.db.get_value('Sales Taxes and Charges', {'parent': invoice_name}, 'rate') / 100) + 1  # 1.12

    # POR AHORA LA TASA ISR LA OBTENEMOS SEGUN LA VALIDACION DE GRAND TOTAL DE LA FACTURA
    tasa_isr = applicable_tax_rate

    # Segun el escenario, aplicamos la formula
    if scenario == 1:
        # tasa_isr = (frappe.db.get_value('Tax Witholding Ranges', {'parent': company}, 'isr_percentage_rate')) / 100
        return float('{0:.2f}'.format((float('{0:.2f}'.format(monto))/tasa_iva) * tasa_isr))

    elif scenario == 2:
        grand_total_isr_7 = (monto - rango_isr[1])
        grand_total_isr_5 = (monto - grand_total_isr_7)

        net_total_isr_7 = (grand_total_isr_7 / tasa_iva)
        monto_retencion_isr_7 = net_total_isr_7 * tasas_isr

        net_total_isr_5 = (grand_total_isr_5 / tasa_iva)
        monto_retencion_isr_5 = net_total_isr_5 * tasas_isr

        total = monto_retencion_isr_5 + monto_retencion_isr_7

        return float('{0:2.f}'.format(total))

    else:
        frappe.msgprint(_('Escenario ISR no completado, no se aplico ningun escenario'))
        return
