# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import frappe
from frappe import _

from factura_electronica.utils.utilities_facelec import get_currency_precision
from frappe.utils import flt


# IMPORTANTE: OJO: NOTA: CADA ITEM DE TIPO COMBUSTIBLE DEBE TENER SU PROPIA CUENTA DE INGRESO Y GASTO CONFIGURADA
# DE LO CONTRARIO NO CUADRARA EN GENERAL LEDGER. SI TIENES OTRA IDEA NO DUDES EN TESTEARLO AQUI

# Precision calculos esto se configura en System Settings en el campo currency_precision
PRECISION_CALC = get_currency_precision()


def calculate_values_with_special_tax(data_gl_entry, tax_rate, invoice_type, invoice_name, tax_accounts, is_return):
    '''Grand total, quitar sumatoria totoal shs otros imuestos, = neto para iva
       se calcula sobre ese neto, y se va a ir a modificar en glentry para reflejar los cambios

       Parametros:
       ----------
       * data_gl_entry (dict/array) : Datos de factura
       * tax_rate (dict/array) : Datos de impuestos
       * invice_type (str) : Sales Invoice or Purchase Invoice
       * invoice_name (str) : Nombre de la factura
    '''
    # IMPORTANTE: OJO: NOTA: CADA ITEM DE TIPO COMBUSTIBLE DEBE TENER SU PROPIA CUENTA DE INGRESO Y GASTO CONFIGURADA
    # DE LO CONTRARIO NO CUADRARA EN GENERAL LEDGER

    # LA LOGICA DE SALES INVOICE TAMBIEN SE APLICA PURCHASE INVOICE

    # Calculos actualizar impuesto Sales Invoice -- Purchase Invoice
    # Total de la factura original
    total = flt(data_gl_entry[0]['total'], PRECISION_CALC)
    # Total menos impuestos especiales. Ejemplo: IDP
    total_tasable = 0

    if invoice_type == 'Sales Invoice':
        # total_tasable = '{0:.2f}'.format(float(data_gl_entry[0]['total'] - data_gl_entry[0]['shs_total_otros_imp_incl']))
        total_tasable = flt(data_gl_entry[0]['total'] - data_gl_entry[0]['shs_total_otros_imp_incl'], PRECISION_CALC)
    else:
        # total_tasable = '{0:.2f}'.format(float(data_gl_entry[0]['total'] - data_gl_entry[0]['shs_pi_total_otros_imp_incl']))
        total_tasable = flt(data_gl_entry[0]['total'] - data_gl_entry[0]['shs_pi_total_otros_imp_incl'], PRECISION_CALC)

    # (total - impuestos especiales)/1.12
    # valor_neto_iva = '{0:.2f}'.format(float(float(total_tasable) / ((tax_rate[0]['rate'] / 100) + 1)))
    valor_neto_iva = flt(total_tasable / ((tax_rate[0]['rate'] / 100) + 1), PRECISION_CALC)
    # valor_iva = float(total_tasable) - float(valor_neto_iva)
    valor_iva = flt(total_tasable - valor_neto_iva, PRECISION_CALC)

    # Actualiza los montos
    try:
        # Actualizacion sobre la tabla `tabGL Entry`
        if invoice_type == 'Sales Invoice' and is_return == 0:
            # Total Tasable
            # es-GT: Monto total de la factura
            frappe.db.sql('''
                UPDATE `tabGL Entry` SET debit=%(nuevo_monto)s, debit_in_account_currency=%(nuevo_monto)s
                WHERE voucher_no=%(serie_original)s AND party_type=%(tipo)s AND party=%(customer_n)s
            ''', {'nuevo_monto': total, 'serie_original': invoice_name, 'tipo': 'Customer',
                  'customer_n': str(data_gl_entry[0]['customer'])})

            # Valor Neto Iva
            # NOTE: OJO: IMPORTANTE: SOLO SE DEBEN ACTUALIZAR LAS CUENTAS DE IMPUESTO ESPECIAL NET
            for tax_acc in tax_accounts:
                # Net Fuel: suma de `facelec_gt_tax_net_fuel` de todos los items de la factura y asignarlo a la cuenta
                # del item combustible
                net_fuel = frappe.db.sql('''
                    SELECT SUM(facelec_gt_tax_net_fuel_amt) as net_fuel FROM `tabSales Invoice Item`
                    WHERE parent=%(origin_serie)s AND facelec_tax_rate_per_uom_account=%(acc)s
                ''', {'origin_serie': invoice_name, 'acc': tax_acc}, as_dict=1)[0]

                # Obtiene Todas las cuentas de ingreso que tengan una cuenta de impuestos especial
                to_update = frappe.db.sql('''
                    SELECT income_account FROM `tabSales Invoice Item`
                    WHERE parent=%(origin_serie)s AND facelec_tax_rate_per_uom_account=%(acc)s
                    GROUP BY income_account
                ''', {'origin_serie': invoice_name, 'acc': tax_acc}, as_dict=1)

                # Por cada cuenta ingreso relacionada con una de impuestos especial
                for update_this in to_update:
                    frappe.db.sql('''
                        UPDATE `tabGL Entry` SET credit=%(nuevo_monto)s, credit_in_account_currency=%(nuevo_monto)s
                        WHERE voucher_no=%(serie_original)s AND against=%(customer_n)s AND cost_center IS NOT NULL
                        AND account=%(acc_to_update)s
                    ''', {'nuevo_monto': flt(net_fuel.get('net_fuel'), PRECISION_CALC),
                          'customer_n': str(data_gl_entry[0]['customer']),
                          'serie_original': invoice_name, 'acc_to_update': update_this.get('income_account')})

            # Valor Iva
            frappe.db.sql('''
                UPDATE `tabGL Entry` SET credit=%(nuevo_monto)s, credit_in_account_currency=%(nuevo_monto)s
                WHERE account=%(tax_c)s AND voucher_no=%(serie_original)s
            ''', {'nuevo_monto': str(valor_iva), 'tax_c': str(tax_rate[0]['account_head']),
                  'serie_original': invoice_name})

            ###
            # Actualiza el total de factura con el nuevo monto
            frappe.db.sql('''UPDATE `tabSales Invoice` SET total=%(nuevo_monto)s,
                            base_net_total=%(nuevo_monto)s, total_taxes_and_charges=%(nuevo_valor_iva)s
                            WHERE name=%(serie_original)s''', {'nuevo_monto': total, 'nuevo_valor_iva': valor_iva, 'serie_original': invoice_name})

            frappe.db.sql('''UPDATE `tabSales Taxes and Charges` SET tax_amount=%(nuevo_monto)s,
                            base_tax_amount=%(nuevo_monto)s, base_tax_amount_after_discount_amount=%(nuevo_monto)s,
                            tax_amount_after_discount_amount=%(nuevo_monto)s
                            WHERE parent=%(serie_original)s''', {'nuevo_monto': valor_iva, 'serie_original': invoice_name})

        # Actualizacion sobre la tabla `tabGL Entry` - NOTA DE CREDITO
        if invoice_type == 'Sales Invoice' and is_return == 1:
            # Total Tasable
            # es-GT: Monto total de la factura
            frappe.db.sql('''
                UPDATE `tabGL Entry` SET credit=%(nuevo_monto)s, credit_in_account_currency=%(nuevo_monto)s,
                debit=0, debit_in_account_currency=0
                WHERE voucher_no=%(serie_original)s AND party_type=%(tipo)s AND party=%(customer_n)s
            ''', {'nuevo_monto': abs(total), 'serie_original': invoice_name, 'tipo': 'Customer',
                  'customer_n': str(data_gl_entry[0]['customer'])})

            # Valor Neto Iva
            # NOTE: OJO: IMPORTANTE: SOLO SE DEBEN ACTUALIZAR LAS CUENTAS DE IMPUESTO ESPECIAL NET
            for tax_acc in tax_accounts:
                # Net Fuel: suma de `facelec_gt_tax_net_fuel` de todos los items de la factura y asignarlo a la cuenta
                # del item combustible
                net_fuel = frappe.db.sql('''
                    SELECT SUM(facelec_gt_tax_net_fuel_amt) as net_fuel FROM `tabSales Invoice Item`
                    WHERE parent=%(origin_serie)s AND facelec_tax_rate_per_uom_account=%(acc)s
                ''', {'origin_serie': invoice_name, 'acc': tax_acc}, as_dict=1)[0]

                # Obtiene Todas las cuentas de ingreso que tengan una cuenta de impuestos especial
                to_update = frappe.db.sql('''
                    SELECT income_account FROM `tabSales Invoice Item`
                    WHERE parent=%(origin_serie)s AND facelec_tax_rate_per_uom_account=%(acc)s
                    GROUP BY income_account
                ''', {'origin_serie': invoice_name, 'acc': tax_acc}, as_dict=1)

                # Por cada cuenta ingreso relacionada con una de impuestos especial
                for update_this in to_update:
                    frappe.db.sql('''
                        UPDATE `tabGL Entry` SET debit=%(nuevo_monto)s, debit_in_account_currency=%(nuevo_monto)s,
                        credit=0, credit_in_account_currency=0
                        WHERE voucher_no=%(serie_original)s AND against=%(customer_n)s AND cost_center IS NOT NULL
                        AND account=%(acc_to_update)s
                    ''', {'nuevo_monto': abs(flt(net_fuel.get('net_fuel'), PRECISION_CALC)),
                          'customer_n': str(data_gl_entry[0]['customer']),
                          'serie_original': invoice_name, 'acc_to_update': update_this.get('income_account')})

            # Valor Iva
            frappe.db.sql('''
                UPDATE `tabGL Entry` SET debit=%(nuevo_monto)s, debit_in_account_currency=%(nuevo_monto)s,
                credit=0, credit_in_account_currency=0
                WHERE account=%(tax_c)s AND voucher_no=%(serie_original)s
            ''', {'nuevo_monto': abs(valor_iva), 'tax_c': str(tax_rate[0]['account_head']),
                  'serie_original': invoice_name})

            ###
            # Actualiza el total de factura con el nuevo monto
            frappe.db.sql('''UPDATE `tabSales Invoice` SET total=%(nuevo_monto)s,
                            base_net_total=%(nuevo_monto)s, total_taxes_and_charges=%(nuevo_valor_iva)s
                            WHERE name=%(serie_original)s''', {'nuevo_monto': total, 'nuevo_valor_iva': valor_iva, 'serie_original': invoice_name})

            frappe.db.sql('''UPDATE `tabSales Taxes and Charges` SET tax_amount=%(nuevo_monto)s,
                            base_tax_amount=%(nuevo_monto)s, base_tax_amount_after_discount_amount=%(nuevo_monto)s,
                            tax_amount_after_discount_amount=%(nuevo_monto)s
                            WHERE parent=%(serie_original)s''', {'nuevo_monto': valor_iva, 'serie_original': invoice_name})

        if invoice_type == 'Purchase Invoice' and is_return == 0:
            # Total Tasable
            # es-GT: Monto total de la factura menos el total del monto del impuesto especial
            frappe.db.sql('''
                UPDATE `tabGL Entry` SET credit=%(nuevo_monto)s, credit_in_account_currency=%(nuevo_monto)s
                WHERE voucher_no=%(serie_original)s AND party_type=%(tipo)s AND party=%(supplier_n)s
            ''', {'nuevo_monto': total, 'serie_original': invoice_name, 'tipo': 'Supplier',
                  'supplier_n': str(data_gl_entry[0]['supplier_name'])})

            # Valor Neto Iva
            # NOTE: SOLO SE DEBEN ACTUALIZAR LAS CUENTAS DE IMPUESTO ESPECIAL NET
            for tax_acc in tax_accounts:
                # Net Fuel: suma de `facelec_p_gt_tax_net_fuel` de todos los items de la factura compra
                net_fuel = frappe.db.sql('''
                    SELECT SUM(facelec_p_gt_tax_net_fuel_amt) as net_fuel FROM `tabPurchase Invoice Item`
                    WHERE parent=%(origin_serie)s AND facelec_p_tax_rate_per_uom_account=%(acc)s
                ''', {'origin_serie': invoice_name, 'acc': tax_acc}, as_dict=1)[0]

                # Obtiene Todas las cuentas de ingreso que tengan una cuenta de impuestos especial
                to_update = frappe.db.sql('''
                    SELECT expense_account FROM `tabPurchase Invoice Item`
                    WHERE parent=%(origin_serie)s AND facelec_p_tax_rate_per_uom_account=%(acc)s
                    GROUP BY expense_account
                ''', {'origin_serie': invoice_name, 'acc': tax_acc}, as_dict=1)

                # Por cada cuenta gasto relacionada con una de impuestos especial
                for update_this in to_update:
                    frappe.db.sql('''
                        UPDATE `tabGL Entry` SET debit=%(nuevo_monto)s, debit_in_account_currency=%(nuevo_monto)s
                        WHERE voucher_no=%(serie_original)s AND against=%(supplier_n)s AND cost_center IS NOT NULL
                        AND account=%(acc_to_update)s
                    ''', {'nuevo_monto': flt(net_fuel.get('net_fuel'), PRECISION_CALC),
                          'supplier_n': str(data_gl_entry[0]['supplier_name']),
                          'serie_original': invoice_name, 'acc_to_update': update_this.get('expense_account')})

            # Valor Iva
            frappe.db.sql('''
                UPDATE `tabGL Entry` SET debit=%(nuevo_monto)s, debit_in_account_currency=%(nuevo_monto)s
                WHERE account=%(tax_c)s AND voucher_no=%(serie_original)s
            ''', {'nuevo_monto': str(valor_iva), 'tax_c': str(tax_rate[0]['account_head']),
                  'serie_original': invoice_name})

            ###
            # Actualiza el total de factura con el nuevo monto
            frappe.db.sql('''UPDATE `tabPurchase Invoice` SET total=%(nuevo_monto)s,
                            base_net_total=%(nuevo_monto)s, total_taxes_and_charges=%(nuevo_valor_iva)s
                            WHERE name=%(serie_original)s''', {'nuevo_monto': total, 'nuevo_valor_iva': valor_iva, 'serie_original': invoice_name})

            frappe.db.sql('''UPDATE `tabPurchase Taxes and Charges` SET tax_amount=%(nuevo_monto)s,
                            base_tax_amount=%(nuevo_monto)s, base_tax_amount_after_discount_amount=%(nuevo_monto)s,
                            tax_amount_after_discount_amount=%(nuevo_monto)s
                            WHERE parent=%(serie_original)s''', {'nuevo_monto': valor_iva, 'serie_original': invoice_name})

        # NOTA DE DEBITO
        if invoice_type == 'Purchase Invoice' and is_return == 1:
            # Total Tasable
            # es-GT: Monto total de la factura menos el total del monto del impuesto especial
            frappe.db.sql('''
                UPDATE `tabGL Entry` SET debit=%(nuevo_monto)s, debit_in_account_currency=%(nuevo_monto)s,
                credit=0, credit_in_account_currency=0
                WHERE voucher_no=%(serie_original)s AND party_type=%(tipo)s AND party=%(supplier_n)s
            ''', {'nuevo_monto': abs(total), 'serie_original': invoice_name, 'tipo': 'Supplier',
                  'supplier_n': str(data_gl_entry[0]['supplier_name'])})

            # Valor Neto Iva
            # NOTE: SOLO SE DEBEN ACTUALIZAR LAS CUENTAS DE IMPUESTO ESPECIAL NET
            for tax_acc in tax_accounts:
                # Net Fuel: suma de `facelec_p_gt_tax_net_fuel` de todos los items de la factura compra
                net_fuel = frappe.db.sql('''
                    SELECT SUM(facelec_p_gt_tax_net_fuel_amt) as net_fuel FROM `tabPurchase Invoice Item`
                    WHERE parent=%(origin_serie)s AND facelec_p_tax_rate_per_uom_account=%(acc)s
                ''', {'origin_serie': invoice_name, 'acc': tax_acc}, as_dict=1)[0]

                # Obtiene Todas las cuentas de ingreso que tengan una cuenta de impuestos especial
                to_update = frappe.db.sql('''
                    SELECT expense_account FROM `tabPurchase Invoice Item`
                    WHERE parent=%(origin_serie)s AND facelec_p_tax_rate_per_uom_account=%(acc)s
                    GROUP BY expense_account
                ''', {'origin_serie': invoice_name, 'acc': tax_acc}, as_dict=1)

                # Por cada cuenta gasto relacionada con una de impuestos especial
                for update_this in to_update:
                    frappe.db.sql('''
                        UPDATE `tabGL Entry` SET credit=%(nuevo_monto)s, credit_in_account_currency=%(nuevo_monto)s,
                        debit=0, debit_in_account_currency=0
                        WHERE voucher_no=%(serie_original)s AND against=%(supplier_n)s AND cost_center IS NOT NULL
                        AND account=%(acc_to_update)s
                    ''', {'nuevo_monto': abs(flt(net_fuel.get('net_fuel'), PRECISION_CALC)),
                          'supplier_n': str(data_gl_entry[0]['supplier_name']),
                          'serie_original': invoice_name, 'acc_to_update': update_this.get('expense_account')})

            # Valor Iva
            frappe.db.sql('''
                UPDATE `tabGL Entry` SET credit=%(nuevo_monto)s, credit_in_account_currency=%(nuevo_monto)s,
                debit=0, debit_in_account_currency=0
                WHERE account=%(tax_c)s AND voucher_no=%(serie_original)s
            ''', {'nuevo_monto': abs(valor_iva), 'tax_c': str(tax_rate[0]['account_head']),
                  'serie_original': invoice_name})

            ###
            # Actualiza el total de factura con el nuevo monto
            frappe.db.sql('''UPDATE `tabPurchase Invoice` SET total=%(nuevo_monto)s,
                            base_net_total=%(nuevo_monto)s, total_taxes_and_charges=%(nuevo_valor_iva)s
                            WHERE name=%(serie_original)s''', {'nuevo_monto': total, 'nuevo_valor_iva': valor_iva, 'serie_original': invoice_name})

            frappe.db.sql('''UPDATE `tabPurchase Taxes and Charges` SET tax_amount=%(nuevo_monto)s,
                            base_tax_amount=%(nuevo_monto)s, base_tax_amount_after_discount_amount=%(nuevo_monto)s,
                            tax_amount_after_discount_amount=%(nuevo_monto)s
                            WHERE parent=%(serie_original)s''', {'nuevo_monto': valor_iva, 'serie_original': invoice_name})

    except Exception as e:
        frappe.msgprint(_(f'Ocurrio un problema al tratar de actualizar los montos en GL Entry {e} <hr> {frappe.get_traceback()}'))


@frappe.whitelist()
def add_gl_entry_other_special_tax(invoice_name, accounts, invoice_type, is_return):
    '''Agrega entradas a Gl Entry de facturas con la cuenta especial asignada.

    Parametros:
    ----------
    * invoice_name (str) : Nombre de la factura
    * accounts (dict) : Diccionario de cuentas
    * invoice_type (str) : Tipo de factura
    '''

    # IMPORTANTE: OJO: NOTA: CADA ITEM DE TIPO COMBUSTIBLE DEBE TENER SU PROPIA CUENTA DE INGRESO Y GASTO CONFIGURADA
    # DE LO CONTRARIO NO CUADRARA EN GENERAL LEDGER
    is_return = int(is_return)
    account_names = json.loads(accounts)

    # Verificacion extra para recibir Sales Invoice o Purchase Invoice del Front End
    if invoice_type == 'Sales Invoice' or invoice_type == 'Purchase Invoice':
        # verifica que por lo menos exista una entrada en GL Entry para esa factura
        if frappe.db.exists('GL Entry', {'voucher_no': invoice_name}):
            data_gl_entry = ''
            tax_rate = ''

            if invoice_type == 'Sales Invoice':
                # Obtiene datos de Sales Invoice
                data_gl_entry = frappe.db.get_values('Sales Invoice', filters={'name': invoice_name},
                                                     fieldname=['company', 'customer_name', 'party_account_currency',
                                                                'posting_date', 'total', 'shs_total_otros_imp_incl',
                                                                'customer'], as_dict=1)
                # Obtiene el valor de iva utilizado en la factura de venta normalmente 12
                tax_rate = frappe.db.get_values('Sales Taxes and Charges', filters={'parent': invoice_name},
                                                fieldname=['rate', 'account_head'], as_dict=1)

            if invoice_type == 'Purchase Invoice':
                # Obtiene datos de Purchase Invoice
                data_gl_entry = frappe.db.get_values('Purchase Invoice', filters={'name': invoice_name},
                                                     fieldname=['company', 'supplier_name', 'party_account_currency',
                                                                'posting_date', 'total', 'shs_pi_total_otros_imp_incl',
                                                                'supplier'], as_dict=1)
                # Obtiene el valor de iva utilizado en la factura normalmente 12
                tax_rate = frappe.db.get_values('Purchase Taxes and Charges', filters={'parent': invoice_name},
                                                fieldname=['rate', 'account_head', 'cost_center'], as_dict=1)

            # Recorre el diccionario de cuentas, por cada cuenta inserta un nuevo registro en GL Entry
            for account_n in account_names:
                # Evita duplicar el ingreso de datos
                if not frappe.db.exists('GL Entry', {'account': account_n, 'voucher_no': invoice_name}):
                    try:
                        new_gl_entry_tax = frappe.new_doc("GL Entry")
                        new_gl_entry_tax.fiscal_year = frappe.defaults.get_user_default("fiscal_year")
                        new_gl_entry_tax.docstatus = 1
                        new_gl_entry_tax.voucher_no = invoice_name
                        new_gl_entry_tax.company = data_gl_entry[0]['company']
                        new_gl_entry_tax.voucher_type = invoice_type
                        new_gl_entry_tax.is_advance = 'No'
                        new_gl_entry_tax.remarks = 'No Remarks'
                        new_gl_entry_tax.account_currency = data_gl_entry[0]['party_account_currency']
                        new_gl_entry_tax.account = account_n

                        if invoice_type == 'Sales Invoice' and is_return == 0:
                            new_gl_entry_tax.against = data_gl_entry[0]['customer']
                            new_gl_entry_tax.credit_in_account_currency = account_names[account_n]
                            new_gl_entry_tax.credit = account_names[account_n]

                        if invoice_type == 'Sales Invoice' and is_return == 1:
                            new_gl_entry_tax.against = data_gl_entry[0]['customer']
                            new_gl_entry_tax.debit_in_account_currency = abs(account_names[account_n])
                            new_gl_entry_tax.debit = abs(account_names[account_n])

                        if invoice_type == 'Purchase Invoice' and is_return == 0:
                            new_gl_entry_tax.against = data_gl_entry[0]['supplier']
                            new_gl_entry_tax.debit_in_account_currency = account_names[account_n]
                            new_gl_entry_tax.debit = account_names[account_n]
                            new_gl_entry_tax.cost_center = tax_rate[0]['cost_center']

                        if invoice_type == 'Purchase Invoice' and is_return == 1:
                            new_gl_entry_tax.against = data_gl_entry[0]['supplier']
                            new_gl_entry_tax.credit_in_account_currency = abs(account_names[account_n])
                            new_gl_entry_tax.credit = abs(account_names[account_n])
                            new_gl_entry_tax.cost_center = tax_rate[0]['cost_center']

                        new_gl_entry_tax.is_opening = 'No'
                        new_gl_entry_tax.posting_date = data_gl_entry[0]['posting_date']

                        new_gl_entry_tax.insert(ignore_permissions=True)
                    except Exception as e:
                        frappe.msgprint(_(f'Error al insertar las cuentas de impuestos especiales en GL Entry, \
                            por favor verifique que el año fiscal sea el actual, cancele esta factura y vuelvala \
                            a generarla con los datos corregidos, mas detalles en: <code>{e}<hr>{frappe.get_traceback()}</code>'))

            # Funcion encargada de realizar calculos con los impuestos especiales, y actualizar la factura
            # con los monton correctos
            calculate_values_with_special_tax(data_gl_entry, tax_rate, invoice_type, invoice_name, account_names, is_return)
    else:
        frappe.msgprint(_('No procesado, se recibio un valor diferente de Sales Invoice o Purchase Invoice'))
