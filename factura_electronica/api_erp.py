# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice import \
    batch_generator
from frappe import _

import json


# USAR ESTE SCRIPT COMO API PARA COMUNICAR APPS DEL ECOSISTEMA FRAPPE/ERPNEXT :)

@frappe.whitelist()
def batch_generator_api(invoices):
    try:
        status_invoices = batch_generator(invoices)
        frappe.msgprint(_(str(status_invoices)))

    except:
        pass


@frappe.whitelist()
def journal_entry_isr(data_invoice):
    """
    Funciona llamada desde boton Sales Invoice, encargada de crear Journal
    Entry, en funcion a los parametros pasados

    Args:
        data_invoice (dict): Diccionario con las propiedades de la factura
    """
    try:
        new_je = JournalEntryISR(json.loads(data_invoice))  # Creamos una nueva instancia
        new_je.validate_dependencies()  # Aplicamos validaciones
        new_je.generate_je_accounts()  # Generamos las filas para el journal entry
        new_je.create_journal_entry()  # Guardamos registro
    except:
        frappe.msgprint(str(frappe.get_traceback()))


class JournalEntryISR:
    """
    Clase de uso general, API interna y API Externa
    """
    def __init__(self, data_invoice):
        """
        Constructor de la clase

        Args:
            data_invoice (dict): Propiedades de la factura procesada
        """
        self.company = str(data_invoice.get("company")).strip()
        self.posting_date = str(data_invoice.get("posting_date"))
        self.posting_time = str(data_invoice.get("posting_time", ""))
        self.grand_total = float(data_invoice.get("grand_total"))
        self.debit_to = str(data_invoice.get("debit_to")).strip()
        self.currency = str(data_invoice.get("currency")).strip()
        self.curr_exch = float(data_invoice.get("curr_exch"))
        self.customer = str(data_invoice.get("customer")).strip()
        self.name_inv = str(data_invoice.get("name_inv")).strip()
        self.cheque_no = str(data_invoice.get("cheque_no", "")).strip()
        self.cheque_date = str(data_invoice.get("cheque_date", ""))
        self.remarks = str(data_invoice.get("user_remark", ""))
        self.docstatus = int(data_invoice.get("docstatus", 0))
        self.cost_center = str(data_invoice.get("cost_center", "")).strip()

    def validate_dependencies(self):
        """
        Se encarga de validar las dependencias, necesarias para generar un Journal Entry con ISR
        Dolares, Quetzales
        """
        # TODO: API
        # Validamos cuenta debit_to: debe ya estar configurado en company en caso ocurran errores
        # Si la company maneja quetzales la cuenta debe ser de quetzales, etc...
        # if not frappe.db.exists("Account", {"name": self.debit_to}):
        #     self.debit_to = frappe.db.get_value("Company", {"name": self.company}, "default_receivable_account")

        # Validamos el centro de costo, si no existe se usara el default configurado en la company
        # tambien existe la posiblidad de que el usario haga la modificaciones manualmente en el Journal Entry
        if not frappe.db.exists("Cost Center", {"name": self.cost_center, "company": self.company}):
            self.cost_center = frappe.db.get_value("Company", {"name": self.company}, "cost_center")

        # Para segunda fila
        # Validamos Bank Account Default por cliente, si es USD, GTQ, etc ...
        # SI SE FACTURA en dolares, se buscara la cuenta default de cobros configurada por cliente,
        # si la cuenta es de dolares, se usara, si no existe TODO: se buscara la defaulta configurada
        # Si se cobra en quetzales se buscara la default de la compania sino se data una alerta

        self.default_bank_acc_customer = frappe.db.get_value("Customer", {"name": self.customer},
                                                             "default_bank_account")
        if not self.default_bank_acc_customer:
            frappe.msgprint("NO")
        else:
            self.default_bank_acc = frappe.db.get_value("Bank Account", {"name": self.default_bank_acc_customer},
                                                        "account")

        # ISR
        # Si existe algun registo para la compania en:
        if frappe.db.exists("Tax Witholding Ranges", {"company": self.company}):
            self.isr_account_payable = frappe.db.get_values("Tax Witholding Ranges", {"company": self.company},
                                                            "isr_account_payable")

    def generate_je_accounts(self):
        """
        Genera las filas para Journal Entry, detecta si es necesario aplicar conversion dolares, quetzales,
        aplicar IVA, ISR
        """
        isr_amt = apply_formula_isr(self.grand_total, self.curr_exch)

        # Logica posible fila 1
        curr_row_a = frappe.db.get_value("Account", {"name": self.debit_to}, "account_currency")
        # Aplicamos equivalente operador ternario, if en uan sola linea
        # resultado = valor_si if condicion else valor_no
        exch_rate_je = 1 if (curr_row_a == "GTQ") else self.curr_exch

        row_one = {
            "account": self.debit_to,  # Cuenta a que se va a utilizar
            "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
            "credit_in_account_currency": amount_converter(self.grand_total, self.curr_exch, self.currency, curr_row_a),  #Valor del monto a acreditar
            "debit_in_account_currency": 0,  #Valor del monto a debitar
            "exchange_rate": exch_rate_je,  # Tipo de cambio
            "account_currency": curr_row_a,
            "party_type": "Customer",  #Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
            "party": self.customer,  #Nombre del cliente
            "reference_name": self.name_inv,  #Referencia dada por sistema
            "reference_type": "Sales Invoice"
        }

        # Logica posible fila 2
        curr_row_b = frappe.db.get_value("Account", {"name": self.default_bank_acc}, "account_currency")
        # Aplicamos equivalente operador ternario, if en uan sola linea
        # resultado = valor_si if condicion else valor_no
        exch_rate_je = 1 if (curr_row_a == "GTQ") else self.curr_exch

        row_two = {
            "account": self.default_bank_acc,  #Cuenta a que se va a utilizar
            "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
            "credit_in_account_currency": 0,  #Valor del monto a acreditar
            "exchange_rate": exch_rate_je,  # Tipo de cambio
            "account_currency": curr_row_b,  # Moneda de la cuenta
            "debit_in_account_currency": apply_calcl(self.grand_total, self.curr_exch, isr_amt),  #Valor del monto a debitar
        }


        self.accounts_je = [
            {
                "account": self.isr_account_payable[0][0],  #Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  #Valor del monto a acreditar
                "debit_in_account_currency": isr_amt,  #Valor del monto a debitar
            }
        ]

        # with open('filas.json', 'w') as f:
        #     f.write(json.dumps(self.accounts_je, indent=2))

    def create_journal_entry(self):
        """
        Inserta los registros en la base de datos, creando un objeto de la clase Journal Entry
        de frappe, aplicando los validadores internos de frappe
        """
        try:
            JOURNALENTRY = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "cheque_no": self.cheque_no,
                "cheque_date": self.posting_date,
                "company": self.company,
                "posting_date": self.posting_date,
                # "user_remark": self.user_remark,
                "accounts": list(self.accounts_je),
                "docstatus": 0,
                "multi_currency": 1
            })

            status_journal = JOURNALENTRY.insert(ignore_permissions=True)

            frappe.msgprint(str(status_journal))

        except:
            frappe.msgprint(str(frappe.get_traceback()))


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
    if from_currency == "GTQ" and to_currency == "GTQ":
        return monto

    # Si hay que convertir de GTQ a USD
    if from_currency == "GTQ" and to_currency == "USD":
        return monto * 1/currency_exchange

    # Si hay que convertir de USD a GTQ
    if from_currency == "USD" and to_currency == "GTQ":
        return monto * currency_exchange


def apply_formula_isr(monto, curr_exch):
    am_gtq = monto * curr_exch
    # NOTE: JALAR LAS TASAS CONFIGURADAS
    # IVA: SALES/PURCHASE INVOICE TAXES AND CHARGES
    # ISR: TABLA HIJA EN COMPANY, TASA ISR
    salida = (am_gtq - (am_gtq / 1.12) * (5/100))
    return salida


def apply_calcl(monto, curr_exch, isr):
    am_gtq = monto * (curr_exch)
    x = ((am_gtq - isr) * 1/curr_exch)
    return x
