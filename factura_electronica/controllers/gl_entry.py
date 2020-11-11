# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
from datetime import date

import frappe
from frappe import _, _dict
from frappe.utils import flt


def item_expense_acct_excise_tax_gl_correction(doc, event):
    """
    Itera las lineas de Purchase Invoice Item, para ejecutar la funcion
    que actualiza registros en GL Entry, esto aplica solo para facturas
    combustible

    Args:
        doc (Object): De la clase Purchase Invoice
        event (str): Evento ejecutor
    """
    try:

        for item_row in doc.items:
            tax_correction(item_row)

    except:
        frappe.msgprint(f'Ocurrio un problema al tratar de iterar las cuentas para actualizar registros en GL Entry: <code>{frappe.get_traceback()}</code>')


def tax_correction(dict_row):
    """
    Corrige los montos en GL Entry, por `facelec_p_gt_tax_net_fuel_amt`
    esta actualizacion hace posible el cuadre, pueden existir casos donde no cuadre
    por los centavos ejemplo: 16.63 -- 16.64 esto se debe a los calculos del JS

    Args:
        dict_row (Object): De la clase Purchase Invoice
    """
    try:
        # aplica para purchase invoice
        # Por cada fila de items de Purchase Invoice Item, si es combustible
        # Actualiza el monto en aquellos registros en GL ENTRY que tenga en comun,
        # voucher_no, account, y el monto, se hace tambien por monto ya que pueden
        # existir multiples registros en el mismo, esto para evitar actualizaciones
        # no necesaria que pueden influir en la conta
        if dict_row.facelec_p_is_fuel == 1:
            frappe.db.sql(
                f'''
                    UPDATE `tabGL Entry` SET debit="{dict_row.facelec_p_gt_tax_net_fuel_amt}",
                    debit_in_account_currency="{dict_row.facelec_p_gt_tax_net_fuel_amt}"
                    WHERE voucher_no="{dict_row.parent}" AND
                    account="{dict_row.expense_account}" AND
                    voucher_type="Purchase Invoice"
                ''')

        # debit_in_account_currency="{round(dict_row.net_amount, 2)}" AND

    except:
        frappe.msgprint(f'Ocurrio un problema al tratar de actualizar registros en GL Entry: <code>{frappe.get_traceback()}</code>')

