# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice import \
    batch_generator
from frappe import _

# USAR ESTE SCRIPT COMO API PARA COMUNICAR APPS DEL ECOSISTEMA FRAPPE/ERPNEXT :)

@frappe.whitelist()
def batch_generator_api(invoices):
    try:
        status_invoices = batch_generator(invoices)
        frappe.msgprint(_(str(status_invoices)))

    except:
        pass


@frappe.whitelist()
def journal_entry_isr(cheque_on, cheque_date, company, posting_date, user_remark, total_debit,
                      total_credit, accounts, docstatus, posting_time, debit_to, names,
                      currency, curr_exch, customer, name_inv):
    pass



class JournalEntryISR:
    def __init__(self, company, posting_date, total_debit, total_credit, posting_time, debit_to,
                 currency, curr_exch, customer, name_inv, cheque_no="", cheque_date="",
                 user_remark="", docstatus=0, cost_center=""):

        self.company = str(company).strip()
        self.posting_date = str(posting_date)
        self.posting_time = str(posting_time)
        self.total_debit = float(total_debit)
        self.total_credit = float(total_credit)
        self.debit_to = str(debit_to).strip()
        self.currency = str(currency).strip()
        self.curr_exch = float(curr_exch)
        self.customer = str(customer).strip()
        self.name_inv = str(name_inv).strip()
        self.cheque_no = str(cheque_no).strip()
        self.cheque_date = str(cheque_date)
        self.remarks = str(user_remark)
        self.docstatus = int(docstatus)
        self.cost_center = str(cost_center).strip()


        def validate_dependencies(self):
            # TODO: API
            # Validamos cuenta debit_to: debe ya estar configurado en company en caso ocurran errores
            # Si la company maneja quetzales la cuenta debe ser de quetzales, etc...
            # if not frappe.db.exists("Account", {"name": self.debit_to}):
            #     self.debit_to = frappe.db.get_value("Company", {"name": self.company}, "default_receivable_account")

            # Validamos el centro de costo, si no existe se usara el default configurado en la company
            # tambien existe la posiblidad de que el usario haga la modificaciones manualmente en el Journal Entry
            if not frappe.db.exists("Cost Center", {"name": self.cost_center, "company": self.company}):
                self.cost_center = frappe.db.get_value("Company", {"name": self.company}, "default_cost_center")

            # Para segunda fila
            # Validamos Bank Account Default por cliente, si es USD, GTQ, etc ...
            # SI SE FACTURA en dolares, se buscara la cuenta default de cobros configurada por cliente,
            # si la cuenta es de dolares, se usara, si no existe TODO: se buscara la defaulta configurada
            # Si se cobra en quetzales se buscara la default de la compania sino se data una alerta

            self.default_bank_acc = frappe.db.get_value("Customer", {"customer_name": self.customer}, "default_bank_account")
            if not self.default_bank_acc:
                frappe.msgprint("NO")

            # ISR
            # Si existe algun registo para la compania en:
            if frappe.db.exists("Tax Witholding Ranges", {"company": self.company}):
                self.isr_account_payable = frappe.db.get_values("Tax Witholding Ranges", {"company": self.company},
                                                                "isr_account_payable")


        def generate_je_accounts(self):
            self.accounts_je = [
                {
                    "account": self.debit_to,  #Cuenta a que se va a utilizar
                    "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                    "credit_in_account_currency": amount_converter(self),  #Valor del monto a acreditar
                    "debit_in_account_currency": 0,  #Valor del monto a debitar
                    "exchange_rate": self.curr_exch,  #Tipo decambio
                    "party_type": "Customer",  #Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
                    "party": self.customer,  #Nombre del cliente
                    "reference_name": self.name_inv,  #Referencia dada por sistema
                    "reference_type": "Sales Invoice"
                },
                {
                    "account": self.default_bank_acc,  #Cuenta a que se va a utilizar
                    "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                    "credit_in_account_currency": 0,  #Valor del monto a acreditar
                    "debit_in_account_currency": amount_converter(self),  #Valor del monto a debitar
                    "exchange_rate": self.curr_exch,  #Tipo decambio
                    "party_type": "Customer",  #Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
                    "party": self.customer,  #Nombre del cliente
                    "reference_name": self.name_inv,  #Referencia dada por sistema
                    "reference_type": "Sales Invoice"
                },
                {
                    "account": self.default_bank_acc,  #Cuenta a que se va a utilizar
                    "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                    "credit_in_account_currency": 0,  #Valor del monto a acreditar
                    "debit_in_account_currency": amount_converter(self),  #Valor del monto a debitar
                    "exchange_rate": self.curr_exch,  #Tipo decambio
                    "party_type": "Customer",  #Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
                    "party": self.customer,  #Nombre del cliente
                    "reference_name": self.name_inv,  #Referencia dada por sistema
                    "reference_type": "Sales Invoice"
                }
            ]

        def create_journal_entry(self):
            try:
                JOURNALENTRY = frappe.get_doc({"doctype": "Journal Entry",
                                            "voucher_type": "Journal Entry",
                                            "cheque_on": cheque_on,
                                            "cheque_date": cheque_date,
                                            "company": company,
                                            "posting_date": posting_date,
                                            "user_remark": user_remark,
                                            "total_debit": total_debit,
                                            "total_credit": total_credit,
                                            "accounts": accounts,
                                            "docstatus": 0,
                                            "customer_group": "Comercial",
                                            "posting_time": "17:57:12",
                                            "debit_to": "",
                                            "name": "Poliza ISR"
                                            })

                status_journal = JOURNALENTRY.insert(ignore_permissions=True)

                frappe.msgprint('exito')

            except:
                frappe.msgprint(str(frappe.get_traceback()))

        def amount_converter(self):
            return self.total_credit * self.curr_exch





