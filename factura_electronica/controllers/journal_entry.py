# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from factura_electronica.utils.formulas import amount_converter, apply_formula_isr
import json


class JournalEntryISR():
    def __init__(self, data_invoice, is_isr_ret, is_iva_ret, cost_center,
                 debit_in_acc_currency, is_multicurrency, descr):
        """
        Constructor de la clase

        Args:
            data_factura (Object Class Invoice): Instancia de la clase Sales Invoice
            no_ref (str): Numero de autorizacion
            f_ref (str): Fecha de autorizacion
            id_f (str): Referencia a factura
            centro_costo (str): Centro de costo a utilizar en poliza
        """
        self.company = data_invoice.get("company")
        self.posting_date = data_invoice.get("posting_date")
        self.posting_time = data_invoice.get("posting_time", "")
        self.grand_total = data_invoice.get("grand_total")
        self.debit_to = data_invoice.get("debit_to")
        self.currency = data_invoice.get("currency")
        self.curr_exch = data_invoice.get("conversion_rate")  # Se usara el de la factura ya generada
        self.customer = data_invoice.get("customer")
        self.name_inv = data_invoice.get("name")
        self.cost_center = cost_center
        self.debit_in_acc_currency = debit_in_acc_currency
        self.is_multicurrency = is_multicurrency
        self.remarks = descr
        self.docstatus = 0
        self.rows_journal_entry = []
        self.is_isr_retention = is_isr_ret
        self.is_iva_retention = is_iva_ret

    def create(self):
        '''Funcion encargada de crear journal entry haciendo referencia a x factura'''
        try:
            # Obtenemos el centro de costo default para la empresa, esto puede ser modifcado manualmente
            if not self.cost_center:
                self.cost_center = frappe.db.get_value("Company", {"name": self.company}, "cost_center")

            # VALIDAMOS LAS DEPENDENCIAS

            # Escenario 1 - POLIZA NORMAL
            if self.is_iva_retention == 0 and self.is_isr_retention == 0:
                status_dep = self.validate_dependencies()
                if status_dep[0] == False:
                    return False, status_dep[1]

                status_rows = self.apply_normal_scenario()

            # Escenario 2 - POLIZA CON RETENCION ISR
            elif self.is_iva_retention == 0 and self.is_isr_retention == 1:
                status_dep = self.validate_dependencies()
                if status_dep[0] == False:
                    return False, status_dep[1]

                status_rows = self.apply_isr_scenario()

            else:
                return False, 'No se recibio ninguna opcion para generar Poliza contable'

            JOURNALENTRY = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "company": self.company,
                "posting_date": self.posting_date,
                "user_remark": self.remarks,
                "accounts": self.rows_journal_entry,
                "multi_currency": self.is_multicurrency,
                "docstatus": 0
            })
            status_journal = JOURNALENTRY.insert(ignore_permissions=True)

        except:
            return False, 'Error datos para crear journal entry '+str(frappe.get_traceback())

        else:
            return True, status_journal.name

    def validate_dependencies(self):
        try:

            # Obtenemos la cuenta para retencion isr configurada en company
            if frappe.db.exists("Tax Witholding Ranges", {"parent": self.company}):
                self.isr_account_payable = frappe.db.get_value("Tax Witholding Ranges", {"parent": self.company},
                                                               "isr_account_payable")
            else:
                return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para ISR retencion configurada'

            # Obtenemos la cuenta para retencion iva configurada en company
            if frappe.db.exists("Tax Witholding Ranges", {"parent": self.company}):
                self.iva_account_payable = frappe.db.get_values("Tax Witholding Ranges", {"parent": self.company},
                                                                "iva_account_payable")
            else:
                return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para IVA retencion configurada'

            return True, 'OK'

        except:
            return False, str(frappe.get_traceback())

    def apply_isr_scenario(self):
        try:
            # Logica posible fila 1
            # Moneda de la cuenta por cobrar
            curr_row_a = frappe.db.get_value("Account", {"name": self.debit_to}, "account_currency")

            # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
            # resultado = valor_si if condicion else valor_no
            exch_rate_row = 1 if (curr_row_a == "GTQ") else self.curr_exch

            row_one = {
                "account": self.debit_to,  # Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": '{0:.2f}'.format(amount_converter(self.grand_total, self.curr_exch,
                                                                                from_currency=self.currency,
                                                                                to_currency=curr_row_a)),  #Valor del monto a acreditar
                "debit_in_account_currency": 0,  #Valor del monto a debitar
                "exchange_rate": exch_rate_row,  # Tipo de cambio
                "account_currency": curr_row_a,
                "party_type": "Customer",  #Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
                "party": self.customer,  #Nombre del cliente
                "reference_name": self.name_inv,  #Referencia dada por sistema
                "reference_type": "Sales Invoice"
            }
            self.rows_journal_entry.append(row_one)

            # Logica posible fila 2
            # moneda de la cuenta
            curr_row_b = frappe.db.get_value("Account", {"name": self.debit_in_acc_currency},
                                             "account_currency")
            # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
            # resultado = valor_si if condicion else valor_no
            exch_rate_row_b = 1 if (curr_row_b == "GTQ") else self.curr_exch

            # Calculo fila dos
            ISR_PAYABLE = apply_formula_isr(self.grand_total, self.name_inv, self.company)
            amt_without_isr = (self.grand_total - ISR_PAYABLE)
            calc_row_two = amount_converter(amt_without_isr, self.curr_exch,
                                            from_currency=self.currency, to_currency=curr_row_b)

            row_two = {
                "account": self.debit_in_acc_currency,  #Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_b,  # Tipo de cambio
                "account_currency": curr_row_b,  # Moneda de la cuenta
                "debit_in_account_currency": '{0:.2f}'.format(calc_row_two),  #Valor del monto a debitar
            }
            self.rows_journal_entry.append(row_two)

            # Logica posible fila 3
            # moneda de la cuenta
            curr_row_c = frappe.db.get_value("Account", {"name": self.isr_account_payable}, "account_currency")
            # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
            # resultado = valor_si if condicion else valor_no
            exch_rate_row_c = 1 if (curr_row_c == "GTQ") else self.curr_exch
            isr_curr_acc = amount_converter(ISR_PAYABLE, self.curr_exch, from_currency=self.currency, to_currency=curr_row_c)

            row_three = {
                "account": self.isr_account_payable,  #Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_c,  # Tipo de cambio
                "account_currency": curr_row_c,  # Moneda de la cuenta
                "debit_in_account_currency": '{0:.2f}'.format(isr_curr_acc),  #Valor del monto a debitar
            }
            self.rows_journal_entry.append(row_three)

        except:
            return False, str(frappe.get_traceback())

        else:
            return True, 'OK'

    def apply_isr_iva_scenario(self):
        pass

    def apply_normal_scenario(self):

        # En el escenario normal, generamos filas simples
        self.rows_journal_entry = [
            {
                'account': self.debit_to, 'party_type': 'Customer', 'party': self.customer,
                'reference_type': 'Sales Invoice', 'reference_name': self.name_inv,
                'credit_in_account_currency': self.grand_total, 'cost_center': self.cost_center
            },
            {
                'account': self.debit_in_acc_currency, 'debit_in_account_currency': self.grand_total,
                'cost_center': self.cost_center
            }
        ]

        return True, 'OK'


class JournalEntryISROld:
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
        self.taxes_template = str(data_invoice.get("taxes_and_charges", "")).strip()
        self.accounts_je = []

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

        # Validamos el centro de costo, si no existe se usara el default configurado en company
        # tambien existe la posiblidad de que el usario haga la modificaciones manualmente en el Journal Entry
        if not frappe.db.exists("Cost Center", {"name": self.cost_center, "company": self.company}):
            self.cost_center = frappe.db.get_value("Company", {"name": self.company}, "cost_center")

        # Para segunda fila
        # Validamos Bank Account Default por cliente, si es USD, GTQ, etc ...
        # SI SE FACTURA en dolares, se buscara la cuenta default a la que el cliente pagara,
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

    def generate_je_accounts(self, opt=2):
        """
        Genera las filas para Journal Entry, detecta si es necesario aplicar conversion dolares, quetzales,
        aplicar IVA, ISR
        """

        # Logica posible fila 1
        # Moneda de la cuenta
        curr_row_a = frappe.db.get_value("Account", {"name": self.debit_to}, "account_currency")
        # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
        # resultado = valor_si if condicion else valor_no
        exch_rate_row = 1 if (curr_row_a == "GTQ") else self.curr_exch

        row_one = {
            "account": self.debit_to,  # Cuenta a que se va a utilizar
            "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
            "credit_in_account_currency": amount_converter(self.grand_total, self.curr_exch,
                                                           from_currency=self.currency, to_currency=curr_row_a),  #Valor del monto a acreditar
            "debit_in_account_currency": 0,  #Valor del monto a debitar
            "exchange_rate": exch_rate_row,  # Tipo de cambio
            "account_currency": curr_row_a,
            "party_type": "Customer",  #Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
            "party": self.customer,  #Nombre del cliente
            "reference_name": self.name_inv,  #Referencia dada por sistema
            "reference_type": "Sales Invoice"
        }
        self.accounts_je.append(row_one)

        # Logica posible fila 2
        # moneda de la cuenta
        curr_row_b = frappe.db.get_value("Account", {"name": self.default_bank_acc}, "account_currency")
        # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
        # resultado = valor_si if condicion else valor_no
        exch_rate_row = 1 if (curr_row_b == "GTQ") else self.curr_exch

        # Calculo fila dos
        ISR_PAYABLE = apply_formula_isr(self.grand_total, self.name_inv, self.company)
        amt_without_isr = (self.grand_total - ISR_PAYABLE)
        calc_row_two = amount_converter(amt_without_isr, self.curr_exch,
                                        from_currency=self.currency, to_currency=curr_row_b)

        row_two = {
            "account": self.default_bank_acc,  #Cuenta a que se va a utilizar
            "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
            "credit_in_account_currency": 0,  #Valor del monto a acreditar
            "exchange_rate": exch_rate_row,  # Tipo de cambio
            "account_currency": curr_row_b,  # Moneda de la cuenta
            "debit_in_account_currency": calc_row_two,  #Valor del monto a debitar
        }
        self.accounts_je.append(row_two)

        # Logica posible fila 3
        # moneda de la cuenta
        curr_row_c = frappe.db.get_value("Account", {"name": self.isr_account_payable[0][0]}, "account_currency")
        # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
        # resultado = valor_si if condicion else valor_no
        exch_rate_row = 1 if (curr_row_c == "GTQ") else self.curr_exch
        isr_curr_acc = amount_converter(ISR_PAYABLE, self.curr_exch, from_currency=self.currency, to_currency=curr_row_c)

        row_three = {
            "account": self.isr_account_payable[0][0],  #Cuenta a que se va a utilizar
            "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
            "credit_in_account_currency": 0,  #Valor del monto a acreditar
            "exchange_rate": exch_rate_row,  # Tipo de cambio
            "account_currency": curr_row_c,  # Moneda de la cuenta
            "debit_in_account_currency": isr_curr_acc,  #Valor del monto a debitar
        }
        self.accounts_je.append(row_three)

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

            frappe.msgprint(_('Journal Entry generado con exito'))

        except:
            frappe.msgprint(str(frappe.get_traceback()))

