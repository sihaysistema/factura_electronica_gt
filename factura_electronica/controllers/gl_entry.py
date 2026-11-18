# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals


def purchase_gl_lines(items, taxes=None, payable_account="Creditors"):
    """GL ERPNext already builds for a Purchase Invoice.

    One debit per expense account, the sum of the line amounts on that
    account. Each tax row is its own debit. The payable credit equals the
    debits. ``facelec_p_gt_tax_net_fuel_amt`` is not an amount to post: it
    is the FEL taxable base.
    """
    expenses = {}
    for item in items:
        account = item.get("expense_account")
        amount = float(item.get("amount") or 0)
        expenses[account] = expenses.get(account, 0.0) + amount
    lines = [
        {"account": account, "debit": amount, "credit": 0.0}
        for account, amount in expenses.items()
    ]
    for tax in taxes or []:
        lines.append({
            "account": tax.get("account"),
            "debit": float(tax.get("amount") or 0),
            "credit": 0.0,
        })
    total = sum(line["debit"] for line in lines)
    lines.append({"account": payable_account, "debit": 0.0, "credit": total})
    return lines


def gl_is_balanced(lines):
    debits = sum(line["debit"] for line in lines)
    credits = sum(line["credit"] for line in lines)
    return round(debits - credits, 6) == 0.0


def item_expense_acct_excise_tax_gl_correction(doc, event):
    """Do not rewrite GL Entry after submit.

    The old hook set the expense debit to one fuel line's
    ``facelec_p_gt_tax_net_fuel_amt`` and never touched the credit. On
    ERPNext 16 the item amount and the IDP tax row are already in the GL
    map, so that absolute update added IDP again, wiped other lines that
    share the account, and left the voucher unbalanced.
    """
    return None


def tax_correction(dict_row):
    """Old per-line entry point. It no longer runs SQL."""
    return None
