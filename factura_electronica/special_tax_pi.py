# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _

from valida_errores import normalizar_texto

# Permite trabajar con acentos, ñ, simbolos, etc
import os, sys
reload(sys)
sys.setdefaultencoding('utf-8')

@frappe.whitelist()
def update_purchase_taxes_charges(purchase_invoice_name):
    '''Crear n registros en GL Entry, dependiendo del numero de cuentas-impuestos
       detectadas, aplica cuando se valida una factura (Sales Invoice) '''
    pass
    # if frappe.db.exists('Purchase Invoice', {'voucher_no': purchase_invoice_name}):
    #     # Obtiene datos de Sales Invoice
    #     data_purchase_invoice = frappe.db.get_values('Purchase Invoice', filters={'name': purchase_invoice_name},
    #                                                 fieldname=['supplier', 'party_account_currency',
    #                                                             'due_date', 'total', 'shs_total_otros_imp_incl'], as_dict=1)

    #     # Obtiene el valor de iva utilizado en la factura normalmente 12
    #     tasa_imp_factura = frappe.db.get_values('Purchase Taxes and Charges', filters={'parent': invoice_name},
    #                                             fieldname=['rate', 'account_head'], as_dict=1)

    #     # Calculos actulizar impuesto
    #     total = '{0:.2f}'.format(float(data_purchase_invoice[0]['total']))
    #     total_tasable = '{0:.2f}'.format(float(data_purchase_invoice[0]['total'] - data_purchase_invoice[0]['shs_total_otros_imp_incl']))
    #     valor_neto_iva = '{0:.2f}'.format(float(float(total_tasable) / ((tasa_imp_factura[0]['rate'] / 100) + 1)))
    #     valor_iva = float(total_tasable) - float(valor_neto_iva)

    #     try:
    #         # Actualiza el total de factura con el nuevo monto
    #         frappe.db.sql('''UPDATE `tabPurchase Invoice` SET total=%(nuevo_monto)s, base_net_total=%(nuevo_monto)s,
    #                          total_taxes_and_charges=%(nuevo_valor_iva)s WHERE name=%(serie_original)s''',
    #                          {'nuevo_monto': str(total), 'nuevo_valor_iva': str(valor_iva),
    #                          'serie_original': invoice_name})

    #     except:
    #         frappe.msgprint(_('NO FUNCIONO :('))
