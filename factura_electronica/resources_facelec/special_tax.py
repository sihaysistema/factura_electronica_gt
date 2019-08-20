# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import datetime

from utilities_facelec import normalizar_texto


def calculate_values_with_special_tax(data_gl_entry, tax_rate, invoice_type, invoice_name):
    '''Grand total, quitar sumatoria totoal shs otros imuestos, = neto para iva
       se calcula sobre ese neto, y se va a ir a modificar en glentry para reflejar los cambios

       Parametros:
       ----------
       * data_gl_entry (dict/array) : Datos de factura
       * tax_rate (dict/array) : Datos de impuestos
       * invice_type (str) : Sales Invoice or Purchase Invoice
       * invoice_name (str) : Nombre de la factura
    '''

    # Calculos actualizar impuesto Sales Invoice -- Purchase Invoice
    total = '{0:.2f}'.format(float(data_gl_entry[0]['total']))
    total_tasable = 0

    if invoice_type == 'Sales Invoice':
        total_tasable = '{0:.2f}'.format(float(data_gl_entry[0]['total'] - data_gl_entry[0]['shs_total_otros_imp_incl']))
    else:
        total_tasable = '{0:.2f}'.format(float(data_gl_entry[0]['total'] - data_gl_entry[0]['shs_pi_total_otros_imp_incl']))

    valor_neto_iva = '{0:.2f}'.format(float(float(total_tasable) / ((tax_rate[0]['rate'] / 100) + 1)))
    valor_iva = float(total_tasable) - float(valor_neto_iva)

    # Actualiza los montos
    try:
        if invoice_type == 'Sales Invoice':
            # Total Tasable
            # es-GT: Monto total de la factura menos el total del monto del impuesto especial
            frappe.db.sql('''UPDATE `tabGL Entry` SET debit=%(nuevo_monto)s, debit_in_account_currency=%(nuevo_monto)s
                            WHERE voucher_no=%(serie_original)s AND party_type=%(tipo)s AND party=%(customer_n)s
                            ''', {'nuevo_monto': str(total), 'serie_original': invoice_name, 'tipo': 'Customer',
                                'customer_n': str(data_gl_entry[0]['customer_name'])})
            # Valor Neto Iva
            frappe.db.sql('''UPDATE `tabGL Entry` SET credit=%(nuevo_monto)s, credit_in_account_currency=%(nuevo_monto)s
                            WHERE voucher_no=%(serie_original)s AND against=%(customer_n)s AND cost_center IS NOT NULL
                            ''', {'nuevo_monto': str(valor_neto_iva), 'customer_n': str(data_gl_entry[0]['customer_name']),
                                'serie_original': invoice_name})
            # Valor Iva
            frappe.db.sql('''UPDATE `tabGL Entry` SET credit=%(nuevo_monto)s, credit_in_account_currency=%(nuevo_monto)s
                            WHERE account=%(tax_c)s AND voucher_no=%(serie_original)s
                            ''', {'nuevo_monto': str(valor_iva), 'tax_c': str(tax_rate[0]['account_head']),
                                'serie_original': invoice_name})

        if invoice_type == 'Purchase Invoice':
            # Total Tasable
            # es-GT: Monto total de la factura menos el total del monto del impuesto especial
            frappe.db.sql('''UPDATE `tabGL Entry` SET credit=%(nuevo_monto)s, credit_in_account_currency=%(nuevo_monto)s
                            WHERE voucher_no=%(serie_original)s AND party_type=%(tipo)s AND party=%(supplier_n)s
                            ''', {'nuevo_monto': str(total), 'serie_original': invoice_name, 'tipo': 'Supplier',
                                'supplier_n': str(data_gl_entry[0]['supplier_name'])})
            # Valor Neto Iva
            frappe.db.sql('''UPDATE `tabGL Entry` SET debit=%(nuevo_monto)s, debit_in_account_currency=%(nuevo_monto)s
                            WHERE voucher_no=%(serie_original)s AND against=%(supplier_n)s AND cost_center IS NULL
                            ''', {'nuevo_monto': str(valor_neto_iva), 'supplier_n': str(data_gl_entry[0]['supplier_name']),
                                'serie_original': invoice_name})
            # Valor Iva
            frappe.db.sql('''UPDATE `tabGL Entry` SET debit=%(nuevo_monto)s, debit_in_account_currency=%(nuevo_monto)s
                            WHERE account=%(tax_c)s AND voucher_no=%(serie_original)s
                            ''', {'nuevo_monto': str(valor_iva), 'tax_c': str(tax_rate[0]['account_head']),
                                'serie_original': invoice_name})
    except:
        frappe.msgprint(_('Error al actualizar los montos en GL Entry'))
    else:
        if invoice_type == 'Sales Invoice':
            # Actualiza el total de factura con el nuevo monto
            frappe.db.sql('''UPDATE `tabSales Invoice` SET total=%(nuevo_monto)s, 
                            base_net_total=%(nuevo_monto)s, total_taxes_and_charges=%(nuevo_valor_iva)s
                            WHERE name=%(serie_original)s''', {'nuevo_monto': str(total), 'nuevo_valor_iva': str(valor_iva), 'serie_original': invoice_name})

            frappe.db.sql('''UPDATE `tabSales Taxes and Charges` SET tax_amount=%(nuevo_monto)s,
                            base_tax_amount=%(nuevo_monto)s, base_tax_amount_after_discount_amount=%(nuevo_monto)s,
                            tax_amount_after_discount_amount=%(nuevo_monto)s  
                            WHERE parent=%(serie_original)s''', {'nuevo_monto': str(valor_iva), 'serie_original': invoice_name})

        if invoice_type == 'Purchase Invoice':
            # Actualiza el total de factura con el nuevo monto
            frappe.db.sql('''UPDATE `tabPurchase Invoice` SET total=%(nuevo_monto)s, 
                            base_net_total=%(nuevo_monto)s, total_taxes_and_charges=%(nuevo_valor_iva)s
                            WHERE name=%(serie_original)s''', {'nuevo_monto': str(total), 'nuevo_valor_iva': str(valor_iva), 'serie_original': invoice_name})

            frappe.db.sql('''UPDATE `tabPurchase Taxes and Charges` SET tax_amount=%(nuevo_monto)s,
                            base_tax_amount=%(nuevo_monto)s, base_tax_amount_after_discount_amount=%(nuevo_monto)s,
                            tax_amount_after_discount_amount=%(nuevo_monto)s  
                            WHERE parent=%(serie_original)s''', {'nuevo_monto': str(valor_iva), 'serie_original': invoice_name})


@frappe.whitelist()
def add_gl_entry_other_special_tax(invoice_name, accounts, invoice_type):
    '''Agrega entradas a Gl Entry de facturas con la cuenta especial asignada.
    
    Parametros:
    ----------
    * invoice_name (str) : Nombre de la factura
    * accounts (dict) : Diccionario de cuentas
    * invoice_type (str) : Tipo de factura
    '''

    account_names = eval(accounts)

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
                                                                'posting_date', 'total', 'shs_total_otros_imp_incl'], as_dict=1)
                # Obtiene el valor de iva utilizado en la factura de venta normalmente 12
                tax_rate = frappe.db.get_values('Sales Taxes and Charges', filters={'parent': invoice_name},
                                                fieldname=['rate', 'account_head'], as_dict=1)

            if invoice_type == 'Purchase Invoice':
                # Obtiene datos de Purchase Invoice
                data_gl_entry = frappe.db.get_values('Purchase Invoice', filters={'name': invoice_name},
                                                    fieldname=['company', 'supplier_name', 'party_account_currency',
                                                                'posting_date', 'total', 'shs_pi_total_otros_imp_incl'], as_dict=1)
                # Obtiene el valor de iva utilizado en la factura normalmente 12
                tax_rate = frappe.db.get_values('Purchase Taxes and Charges', filters={'parent': invoice_name},
                                                fieldname=['rate', 'account_head', 'cost_center'], as_dict=1)

            # Recorre el diccionario de cuentas, por cada cuenta inserta un nuevo registro en GL Entry
            for account_n in account_names:
                # Evita el ingreso de cuentas duplicadas
                if not frappe.db.exists('GL Entry', {'account': account_n, 'voucher_no': invoice_name}):
                    try:
                        new_gl_entry_tax = frappe.new_doc("GL Entry")
                        new_gl_entry_tax.fiscal_year = frappe.defaults.get_user_default("fiscal_year")
                        # new_gl_entry_tax.docstatus = '1'
                        new_gl_entry_tax.voucher_no = invoice_name
                        new_gl_entry_tax.company = data_gl_entry[0]['company']
                        new_gl_entry_tax.voucher_type = invoice_type
                        new_gl_entry_tax.is_advance = 'No'
                        new_gl_entry_tax.remarks = 'No Remarks'
                        new_gl_entry_tax.account_currency = data_gl_entry[0]['party_account_currency']
                        new_gl_entry_tax.account = account_n

                        if invoice_type == 'Sales Invoice':
                            new_gl_entry_tax.against = data_gl_entry[0]['customer_name']
                            new_gl_entry_tax.credit_in_account_currency = account_names[account_n]
                            new_gl_entry_tax.credit = account_names[account_n]

                        if invoice_type == 'Purchase Invoice':
                            new_gl_entry_tax.against = data_gl_entry[0]['supplier_name']
                            new_gl_entry_tax.debit_in_account_currency = account_names[account_n]
                            new_gl_entry_tax.debit = account_names[account_n]
                            new_gl_entry_tax.cost_center = tax_rate[0]['cost_center']
                        
                        new_gl_entry_tax.is_opening = 'No'
                        new_gl_entry_tax.posting_date = data_gl_entry[0]['posting_date']
                        
                        new_gl_entry_tax.save()
                    except:
                        frappe.msgprint(_('Error al insertar las cuentas de impuestos especiales en GL Entry'))

            # Funcion encargada de realizar calculos con los impuestos especiales, y actualizar la factura
            # con los monton correctos
            calculate_values_with_special_tax(data_gl_entry, tax_rate, invoice_type, invoice_name)
    else:
        frappe.msgprint(_('Error, se recibio un valor diferente de Sales Invoice o Purchase Invoice'))
