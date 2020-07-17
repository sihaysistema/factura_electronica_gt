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
def apply_formula_isr(monto, invoice_name, company, applicable_tax_rate):
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

    tasa_iva = (frappe.db.get_value('Sales Taxes and Charges', {'parent': invoice_name}, 'rate') / 100) + 1  # 1.12
    # tasa_isr = (frappe.db.get_value('Tax Witholding Ranges', {'parent': company}, 'isr_percentage_rate')) / 100

    # POR AHORA LA TASA ISR LA OBTENEMOS SEGUN LA VALIDACION DE GRAND TOTAL DE LA FACTURA
    tasa_isr = applicable_tax_rate

    return float('{0:.2f}'.format((float('{0:.2f}'.format(monto))/tasa_iva) * tasa_isr))
