# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, _dict
from frappe.utils import flt
import numpy as np


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
        return (monto/currency_exchange)

    # Si hay que convertir de USD a GTQ
    if from_currency == "USD" and to_currency == "GTQ":
        return (monto * currency_exchange)

    # Si no aplica ningun escenario anterior se retornal el mismo monto,
    # tomar en cuenta que si se quieren agregar mas monedas debemos hacer una nueva
    # funcion que use todos los tipo de cambio disponibles en el erp
    return monto


# Aplicara el calculo no importando la moneda
# Nota aplicarle conversion si es necesario
def apply_formula_isr(monto, company, decimals=2):
    """
    Formula para obtener ISR

    Args:
        monto (float): Monto sin IVA

    Returns:
        float: ISR
    """
    monto_sin_iva = monto

    # Obtenemos los rangos de renteciones IVA - ISR
    retention_ranges = frappe.db.get_values('Tax Witholding Ranges', filters={'parent': company},
                                            fieldname=['isr_account_payable', 'isr_account_receivable',
                                                       'iva_account_payable', 'vat_account_receivable',
                                                       'isr_percentage_rate', 'minimum_amount',
                                                       'maximum_amount', 'iva_percentage_rate'], as_dict=1)

    # En funcion al monto, validamos que porcentaje de retencion usar
    for retention in retention_ranges:
        # Aplicamos el 5%
        if (monto > retention.get('minimum_amount')) and (monto <= retention.get('maximum_amount')):
            isr_5 = monto_sin_iva * (retention.get('isr_percentage_rate')/100)

            # return round(isr_5, int(decimals))
            return isr_5  # sin aproximaciones, redondeo

        # Aplicamos el 7%
        if (monto >= retention.get('minimum_amount')) and (retention.get('maximum_amount') == 0):
            isr_5 = retention.get('minimum_amount') * retention.get('isr_percentage_rate')
            isr_7 = (monto_sin_iva - retention.get('minimum_amount')) * (retention.get('isr_percentage_rate')/100)

            total_isr_7_reten = isr_5 + isr_7

            # return round(total_isr_7_reten, int(decimals))
            return total_isr_7_reten  # sin aproximaciones, redondeo


def apply_formula_isr_iva(grand_total, invoice_name, supplier_type, item_tax_category,
                          company_tax_category):
    """
    NOTA: La retencion de IVA lo hacen los company que son exportadores,
    operadores tarjetas de credito, contribuyentes especiales, y otros calificados
    por SAT NOTE: esto se genera sobre purchase Invoice, (si le vendo a un cliente
    que es agente retenedor de IVA tambien aplica para Sales Invoice)

    Args:
        grand_total ([type]): [description]
        invoice_name ([type]): [description]
        supplier_type ([type]): [description]
        item_tax_category ([type]): [description]
        company_tax_category ([type]): [description]
    """

    # CASOS APLICABLES
    if company_tax_category == 'SAT: Exportador' and supplier_type == 'Proveedor de bienes servicios local':

        # TODO: QUE PASA CON ESTE ESCENARIO?
        if grand_total <= 2499:
            pass

        if grand_total >= 2500:
            # Escenario 1 - proveedor de servicios a empresa exportadora, se genera 15% de retencion de IVA
            if (item_tax_category == 'Servicios') or (item_tax_category == 'No Agropecuacios'):
                vat_retention_rate = 0.15
                net_total = (grand_total_purchase_inv/1.12)
                vat_total = net_total * 0.12
                vat_retention_amount = vat_total * vat_retention_rate

                expected_cash_payment = grand_total_purchase_inv - vat_retention_amount

                return vat_retention_amount

            # Escenario 2 - proveedor de producto agricola apecuario a empresa exportadora, se genera 65% de retencion de IVA
            elif item_tax_category == 'Agricolas y Pecuarios':
                vat_retention_rate = 0.65
                net_total = (grand_total_purchase_inv/1.12)
                vat_total = net_total * 0.12
                vat_retention_amount = vat_total * vat_retention_rate

                expected_cash_payment = grand_total_purchase_inv - vat_retention_amount

                return vat_retention_amount


    # Escenario 3 - proveedor de servicios a empresa exportadora decreto 2989, se genera 65% de retencion de IVA
    if (company == 'Exportador decreto 2989') and (supplier == 'Proveedor de Bienes Servicios Local'):
        if grand_total_purchase_inv <= 2499:
            pass

        if grand_total_purchase_inv >= 2500:
            vat_retention_rate = 0.65
            net_total = (grand_total_purchase_inv/1.12)
            vat_total = net_total * 0.12
            vat_retention_amount = vat_total * vat_retention_rate

            expected_cash_payment = grand_total_purchase_inv - vat_retention_amount

            return vat_retention_amount


    # Escenario 4 - proveedor de servicios, bienes a sector publico, se genera 25% de retencion de IVA
    elif (company == 'Sector Publico expecto municipales y entes exentos') and (supplier == 'Proveedor de Bienes Servicios Local'):
        if grand_total_purchase_inv <= 29999:
            pass

        if grand_total_purchase_inv >= 30000:
            # : )(
            vat_retention_rate = 0.25
            net_total = (grand_total_purchase_inv/1.12)
            vat_total = net_total * 0.12
            vat_retention_amount = vat_total * vat_retention_rate

            expected_cash_payment = grand_total_purchase_inv - vat_retention_amount

            return vat_retention_amount

    # Escenario 5 - Pago afecto al iva a Operador de tarjeta de credito o debito, se genera 15% de retencion de IVA
    elif (company == 'Operador de tarjeta de credito o debito') and (supplier == 'Pagos afectos a IVA establecimientos afiliados'):
        vat_retention_rate = 0.15
        net_total = (grand_total_purchase_inv/1.12)
        vat_total = net_total * 0.12
        vat_retention_amount = vat_total * vat_retention_rate

        expected_cash_payment = grand_total_purchase_inv - vat_retention_amount

        return vat_retention_amount


    # TODO FIXME: VERIFICAR ESCENARIO
    # Escenario 6 - Pago afecto al iva a Peque;o contribuyente, se genera 5% de retencion de IVA
    elif (supplier == 'Pequeño contribuyente'):
        vat_retention_rate = 0.05
        net_total = (grand_total_purchase_inv/1.12)
        vat_total = net_total * 0.12
        vat_retention_amount = vat_total * vat_retention_rate

        expected_cash_payment = grand_total_purchase_inv - vat_retention_amount

        return vat_retention_amount


    # TODO FIXME: VERIFICAR COMO ES EL GRAND TOTAL,
    # Escenario X - Pago afecto al iva a Operador de tarjeta de credito o debito, se genera 15% de retencion de IVA
    elif (supplier == 'Pagos de combustible'):
        vat_retention_rate = 0.015
        net_total = (grand_total_purchase_inv/1.12)
        vat_total = net_total * 0.12
        vat_retention_amount = vat_total * vat_retention_rate

        expected_cash_payment = grand_total_purchase_inv - vat_retention_amount

        return vat_retention_amount


def number_of_decimals(number):
    """
    Obtiene cuantos decimales tiene un numero float

    Args:
        number (float): Numero a evaluar

    Returns:
        [int]: Numero de decimales
    """

    number_dec = len(str(number).split('.')[1])

    return number_dec


def GoalSeek(fun, goal ,x0, fTol=0.0001, MaxIter=10000):
    # Goal Seek function of Excel
    #   via use of Line Search and Bisection Methods
    # Este código involucra métodos de búsqueda de raíz;
    # en un primer paso, a través del método de Búsqueda de línea y,
    # en el segundo paso, el método de Bisección.

    # Practicamente se puede usar como si se fuese a resolver una ecuacion de primer grado :D

    # Inputs
    #   fun     : Function to be evaluated
    #   goal    : Expected result/output
    #   x0      : Initial estimate/Starting point

    # Initial check
    if fun(x0) == goal:
        # print('Exact solution found')  # Si encuentra una solucion exacta
        return x0

    # Line Search Method, metodo de busqueda lineal
    step_sizes = np.logspace(-1, 4, 6)
    scopes = np.logspace(1, 5, 5)

    vFun = np.vectorize(fun)

    for scope in scopes:
        break_nested = False
        for step_size in step_sizes:

            cApos = np.linspace(x0, x0+step_size * scope, int(scope))
            cAneg = np.linspace(x0, x0-step_size * scope, int(scope))

            cA = np.concatenate((cAneg[::-1], cApos[1:]), axis=0)

            fA = vFun(cA) - goal

            if np.any(np.diff(np.sign(fA))):

                index_lb = np.nonzero(np.diff(np.sign(fA)))

                if len(index_lb[0]) == 1:

                    index_ub = index_lb + np.array([1])

                    x_lb = np.asscalar(np.array(cA)[index_lb][0])
                    x_ub = np.asscalar(np.array(cA)[index_ub][0])
                    break_nested = True
                    break
                else: # Two or more roots possible

                    index_ub = index_lb + np.array([1])

                    # print('Other solution possible at around, x0 = ', np.array(cA)[index_lb[0][1]])

                    x_lb = np.asscalar(np.array(cA)[index_lb[0][0]])
                    x_ub = np.asscalar(np.array(cA)[index_ub[0][0]])
                    break_nested = True
                    break

        if break_nested:
            break
    if not x_lb or not x_ub:
        # print('No Solution Found')
        return

    # Bisection Method
    iter_num = 0
    error = 10

    while iter_num < MaxIter and fTol < error:

        x_m = (x_lb + x_ub) / 2
        f_m = fun(x_m) - goal

        error = abs(f_m)

        if (fun(x_lb) - goal) * (f_m) < 0:
            x_ub=x_m
        elif (fun(x_ub) - goal) * (f_m) < 0:
            x_lb = x_m
        elif f_m == 0:
            # print('Exact spolution found')
            return x_m
        else:
            # print('Failure in Bisection Method')
            pass

        iter_num += 1

    return x_m
