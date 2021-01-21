# Copyright (c) 2013, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict
from datetime import datetime


def execute(filters=None):
    if not filters:
        return [], []

    columns = get_columns()
    data = get_all_data(filters)

    return columns, data


def get_columns():
    """
    Assigns the properties for each column to be displayed in the report

    Args:
        filters (dict): Front end filters

    Returns:
        list: List of dictionaries
    """
    columns = [
        {
            "label": _("Fecha"),
            "fieldname": "fecha",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Póliza"),
            "fieldname": "poliza",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("Explicación"),
            "fieldname": "explicacion",
            "fieldtype": "Data",
            "width": 310
        },
        {
            "label": _("Débitos"),
            "fieldname": "debito",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },
        {
            "label": _("Créditos"),
            "fieldname": "credito",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },
        {
            "label": _("Currency"),
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            # "width": 250,
            "hidden": 1
        }
    ]

    return columns


def get_all_data(filters):
    """Function to obtain and process the data.

    Args:
        filters ([type]): [description]

    Returns:
        dicitonary list: A list of dictionaries, in ascending order, each key corresponds to a
        column name as declared in the function above, and the value is what will be shown.

    """
    # --------- EMPTY ROW ----------
    data = []

    if filters.tipo_poliza:  # Whether or not a filter is applied
        journal_entries = frappe.db.sql('''SELECT name, total_debit, total_credit, posting_date, tipo_poliza
                                        FROM `tabJournal Entry`
                                        WHERE posting_date BETWEEN %(fecha_inicio)s
                                        AND %(fecha_final)s AND company=%(compa)s AND tipo_poliza=%(tipo_poliza)s''',
                                        {'fecha_inicio': str(filters.from_date),
                                            'fecha_final': str(filters.to_date),
                                            'compa': str(filters.company),
                                            'tipo_poliza': str(filters.tipo_poliza)}, as_dict=True)
    else:
        journal_entries = frappe.db.sql('''SELECT name, total_debit, total_credit, posting_date, tipo_poliza
                                        FROM `tabJournal Entry`
                                        WHERE posting_date BETWEEN %(fecha_inicio)s
                                        AND %(fecha_final)s AND company=%(compa)s''',
                                        {'fecha_inicio': str(filters.from_date),
                                            'fecha_final': str(filters.to_date),
                                            'compa': str(filters.company)}, as_dict=True)

    # For each Journal Entry, obtain and prepare the accounts that belong to it.
    for je in journal_entries:
        data_d = {
            "fecha": "<b>Tipo póliza</b>",
            "poliza": "<b>{}</b>".format(je['tipo_poliza'] or '')
        }
        data.append(data_d)

        data.extend(get_account_data(je['name'], je['posting_date'], filters))

        # Generates totals rows
        data.append({
            'explicacion': '<b>Sub-Total</b>',
            'debito': je['total_debit'],
            'credito': je['total_credit'],
            'currency': filters.company_currency  # Adds the company currency, to display the formatted values
        })
        data.append({}) # Generate blank row to separate Journal Entries

    return data


def get_account_data(parent, fecha, filters):
    """
    Function to obtain the detail of the accounts

    Args:
        parent :
        fecha :
        filters ([type]): [description]

    Returns:
        dicitonary list: A list of dictionaries, in each key corresponds to a
        column name as declared in the function above, and the value is what will be shown.

    """

    account_detail = frappe.db.sql('''SELECT account as poliza, user_remark as explicacion,
                                      debit as debito, credit as credito, %(moneda)s AS currency
                                      FROM `tabJournal Entry Account`
                                      WHERE parent=%(parent_)s''',
                                   {'parent_': str(parent), 'moneda': filters.company_currency}, as_dict=True)
    account_detail[0]['fecha'] = datetime.strftime(fecha, '%d/%m/%Y')  # str(fecha)

    return account_detail
