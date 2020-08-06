# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
from datetime import date

import frappe
from factura_electronica.utils.formulas import amount_converter, apply_formula_isr, number_of_decimals
from frappe import _


class JournalEntrySaleInvoice():
    def __init__(self, data_invoice, is_isr_ret, is_iva_ret, debit_in_acc_currency,
                 is_multicurrency=0, cost_center='', descr=''):
        self.company = data_invoice.get("company")
        self.posting_date = data_invoice.get("posting_date")
        self.posting_time = data_invoice.get("posting_time", "")
        self.grand_total = data_invoice.get("grand_total")
        self.grand_total_currency_company = data_invoice.get("base_grand_total")
        self.debit_to = data_invoice.get("debit_to")
        self.currency = data_invoice.get("currency")
        self.curr_exch = data_invoice.get("conversion_rate")  # Se usara el de la factura ya generada
        self.customer = data_invoice.get("customer")
        self.name_inv = data_invoice.get("name")
        self.base_net_total = data_invoice.get("base_total_taxes_and_charges")  # IVA EN moneda de company
        self.cost_center = cost_center or ''
        self.debit_in_acc_currency = debit_in_acc_currency
        self.is_multicurrency = is_multicurrency
        self.is_isr_retention = int(is_isr_ret)
        self.is_iva_retention = int(is_iva_ret)
        self.remarks = descr
        self.docstatus = 0
        self.rows_journal_entry = []
        self.decimals_ope = 2

    def create(self):
        '''Funcion encargada de crear journal entry haciendo referencia a x factura'''
        try:
            # Obtenemos el centro de costo default para la empresa, esto puede ser modifcado manualmente
            if not self.cost_center:
                self.cost_center = frappe.db.get_value("Company", {"name": self.company}, "cost_center")

            # VALIDAMOS LAS DEPENDENCIAS SEGUN ESCENARIO
            # Escenario 1 - POLIZA NORMAL, FACTURA DE VENTA
            if self.is_iva_retention == 0 and self.is_isr_retention == 0:
                status_dep = self.validate_dependencies()
                if status_dep[0] == False:
                    return False, status_dep[1]

                status_rows = self.apply_normal_scenario()
                if status_rows[0] == False:
                    return False, status_rows[1]

            # Escenario 2 - POLIZA CON RETENCION ISR, FACTURA DE VENTA
            elif self.is_iva_retention == 0 and self.is_isr_retention == 1:
                status_dep = self.validate_dependencies()
                if status_dep[0] == False:
                    return False, status_dep[1]

                status_rows = self.apply_isr_scenario()
                if status_rows[0] == False:
                    return False, status_rows[1]

            # ESCENARIO 3 - RETENCION ISR Y RETENCION IVA
            elif self.is_iva_retention == 1 and self.is_isr_retention == 1:
                status_dep = self.validate_dependencies()
                if status_dep[0] == False:
                    return False, status_dep[1]

                status_rows = self.apply_iva_isr_scenario()
                if status_rows[0] == False:
                    return False, status_rows[1]

            # ESCENARIO 4 - RETENCION IVA
            elif self.is_iva_retention == 1 and self.is_isr_retention == 0:
                status_dep = self.validate_dependencies()
                if status_dep[0] == False:
                    return False, status_dep[1]

                status_rows = self.apply_iva_retencion_scenario()
                if status_rows[0] == False:
                    return False, status_rows[1]

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

            if (self.is_isr_retention == 1) or (self.is_iva_retention == 1):
                ret = 'IVA' if self.is_iva_retention == 1 else ''
                ret = 'ISR' if self.is_isr_retention == 1 else ''

                # Registrar retencion
                register_withholding({
                    'retention_type': ret,
                    'party_type': 'Sales Invoice',
                    'company': self.company,
                    'tax_id': '',
                    'sales_invoice': self.name_inv,
                    'invoice_date': self.posting_date,
                    'grand_total': self.grand_total,
                    'currency': self.currency,
                    'retention_amount': self.ISR_PAYABLE_GTQ
                })

            return True, status_journal.name

    def validate_dependencies(self):
        """
        Validador dependencias necesarias para generar una poliza contable
        1. Validacion retenciones configuradas para company
        2. Validacion escenario a aplicar, ISR 5% o 7%
        3. Obtencion tasa IVA
        4. Obtencion cuenta isr por pagar (retencion)
        5. Obtencion cuenta iva por pagar (retencion)

        Returns:
            tuple: Boolean, descripcion de mensaje
        """
        try:
            # grand total en moneda de la compania, GTQ
            monto = self.grand_total_currency_company

            # obtenemos los rangos de retencion configurados en company
            self.retention_ranges = frappe.db.get_values('Tax Witholding Ranges', filters={'parent': self.company},
                                                         fieldname=['isr_account_payable', 'isr_account_receivable',
                                                                    'iva_account_payable', 'vat_account_receivable',
                                                                    'isr_percentage_rate', 'minimum_amount',
                                                                    'maximum_amount', 'iva_percentage_rate'], as_dict=1)
            # Si no hay configurados
            if len(self.retention_ranges) == 0:
                return False, 'No se puede procede con la operacion, no se encontraron rango de retencion configurados'

            # TODO: REFACTORIZAR
            # APLIQUE O NO APLIQUEN LOS ESCENARIO OBTENEMOS LOS DATOS AUTOMATICAMENTE,
            # Por cada retencion configurada, verificamos que escenario aplica
            for retention in self.retention_ranges:
                # Si aplica el primer escenario. Aplicamos el 5%
                if (monto > retention.get('minimum_amount')) and (monto <= retention.get('maximum_amount')):
                    # Obtenemos el porcentaje de impuesto usado en la factura
                    if not retention.get('iva_percentage_rate'):
                        return False, 'No se puede proceder con los calculos, no se encontro una tasa de IVA configurada'
                    self.vat_rate = (retention.get('iva_percentage_rate')/100)  # 0.12

                    # Cuenta ISR por pagar
                    if not retention.get('isr_account_payable'):
                        return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para ISR retencion configurada'
                    self.isr_account_payable = retention.get('isr_account_payable')

                    # Cuenta IVA por pagar
                    if not retention.get('iva_account_payable'):
                        return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para IVA retencion configurada'
                    self.iva_account_payable = retention.get('iva_account_payable')


                # Si aplica el escenario. Aplicamos el 7%
                if (monto >= retention.get('minimum_amount')) and (retention.get('maximum_amount') == 0):
                    # Obtenemos el porcentaje de impuesto usado en la factura
                    if not retention.get('iva_percentage_rate'):
                        return False, 'No se puede proceder con los calculos, no se encontro una tasa de IVA configurada'
                    self.vat_rate = (retention.get('iva_percentage_rate')/100)  # 0.12

                    # Cuenta ISR por pagar
                    if not retention.get('isr_account_payable'):
                        return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para ISR retencion configurada'
                    self.isr_account_payable = retention.get('isr_account_payable')

                    # Cuenta IVA por pagar
                    if not retention.get('iva_account_payable'):
                        return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para IVA retencion configurada'
                    self.iva_account_payable = retention.get('iva_account_payable')

            return True, 'OK'

        except:
            return False, str(frappe.get_traceback())

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

    def apply_isr_scenario(self):
        """
        Aplica los calculos necesarios para las filas que conformaran la poliza contable,
        para una factura con retencion ISR

        NOTA IMPORTANTE: LOS CALCULOS APLICADOS AQUI APLICAN PARA GUATEMALA, Y TOMANDO
        EN CUENTA QUE LAS CUENTAS QUE REGISTRAN LOS MONTOS ES EN QUETZALES :)

        Returns:
            tuple: Boolean, descripcion operacion
        """
        try:
            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 1: El monto a cobrar
            # obtenemos la moneda de la cuenta por cobrar
            curr_row_a = frappe.db.get_value("Account", {"name": self.debit_to}, "account_currency")

            # CALCULOS APLICABLES PARA IMPUESTOS GUATEMALA
            # Si la moneda de la cuenta es GTQ usamos 1, si es USD usamos el tipo cambio
            exch_rate_row = 1 if (curr_row_a == "GTQ") else self.curr_exch

            row_one = {
                "account": self.debit_to,  # Cuenta por cobrar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": round(amount_converter(self.grand_total, self.curr_exch,
                                                                     from_currency=self.currency,
                                                                     to_currency=curr_row_a), self.decimals_ope),  # convierte el monto a la moneda de la cuenta
                "debit_in_account_currency": 0,
                "exchange_rate": exch_rate_row,  # Tipo de cambio
                "account_currency": curr_row_a,  # Moneda de la cuenta
                "party_type": "Customer",  # Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
                "party": self.customer,
                "reference_name": self.name_inv,  # Referencia dada por sistema
                "reference_type": "Sales Invoice"
            }
            self.rows_journal_entry.append(row_one)



            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 2: MONTO QUE EN REALIDAD SE PAGARA, GRAND TOTAL MENOS ISR
            curr_row_b = frappe.db.get_value("Account", {"name": self.debit_in_acc_currency},
                                             "account_currency")

            # Validacion que tipo de cambio usar, segun moneda de la cuenta
            exch_rate_row_b = 1 if (curr_row_b == "GTQ") else self.curr_exch

            # VALIDACION GRAND TOTAL DE FACTURA
            # Para una correcta validacion usamos el grand total en la moneda de company "GTQ"
            grand_total_gtq = self.grand_total_currency_company

            # Obtenemos el monto sin IVA del grand total moneda de company "GTQ"
            GRAND_TOTAL_NO_IVA = round(grand_total_gtq/(self.vat_rate + 1), self.decimals_ope)

            # El monto en quetzales lo pasamos a la funcion que calcula automaticamente el ISR
            self.ISR_PAYABLE_GTQ = apply_formula_isr(GRAND_TOTAL_NO_IVA, self.company, decimals=self.decimals_ope)

            # El monto a pagar, restando el ISR a retener
            amt_without_isr = (grand_total_gtq - (self.ISR_PAYABLE_GTQ))

            # Se vuelve a validar la conversion a la moneda de la cuenta en caso aplique
            calc_row_two = round(amount_converter(amt_without_isr, self.curr_exch,
                                                  from_currency='GTQ', to_currency=curr_row_b), self.decimals_ope)

            row_two = {
                "account": self.debit_in_acc_currency,  # Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  # Valor del monto a acreditar
                "exchange_rate": exch_rate_row_b,  # Tipo de cambio
                "account_currency": curr_row_b,  # Moneda de la cuenta
                "debit_in_account_currency": calc_row_two,
            }
            self.rows_journal_entry.append(row_two)

            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 3: RETENCION ISR
            # moneda de la cuenta
            curr_row_d = frappe.db.get_value("Account", {"name": self.isr_account_payable}, "account_currency")
            # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
            # resultado = valor_si if condicion else valor_no
            exch_rate_row_d = 1 if (curr_row_d == "GTQ") else self.curr_exch
            isr_curr_acc = amount_converter(self.ISR_PAYABLE_GTQ, self.curr_exch, from_currency="GTQ", to_currency=curr_row_d)

            row_three = {
                "account": self.isr_account_payable,  # Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_d,  # Tipo de cambio
                "account_currency": curr_row_d,  # Moneda de la cuenta
                "debit_in_account_currency": round(isr_curr_acc, self.decimals_ope),  #Valor del monto a debitar
            }
            self.rows_journal_entry.append(row_three)

            # with open('special.json', 'w') as f:
            #     f.write(json.dumps(self.rows_journal_entry, default=str, indent=2))

        except:
            return False, str(frappe.get_traceback())

        else:
            return True, 'OK'

    def apply_iva_isr_scenario(self):
        """
        Aplica los calculos necesarios para las filas que conformaran la poliza contable,
        para una factura , con retencion IVA e ISR

        NOTA IMPORTANTE: LOS CALCULOS APLICADOS AQUI APLICAN PARA GUATEMALA, Y TOMANDO
        EN CUENTA QUE LAS CUENTAS QUE REGISTRAN LOS MONTOS ES EN QUETZALES :)

        Returns:
            tuple: Boolean, descripcion operacion
        """
        try:
            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 1: El monto acordado con supplier
            # obtenemos la moneda de la cuenta por pagar
            curr_row_a = frappe.db.get_value("Account", {"name": self.debit_to}, "account_currency")

            # CALCULOS APLICABLES PARA IMPUESTOS GUATEMALA
            # Si la moneda de la cuenta es GTQ usamos 1, si es USD usamos el tipo cambio
            exch_rate_row = 1 if (curr_row_a == "GTQ") else self.curr_exch

            row_one = {
                "account": self.debit_to,  # Cuenta por pagar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": round(amount_converter(self.grand_total, self.curr_exch,
                                                                     from_currency=self.currency,
                                                                     to_currency=curr_row_a), self.decimals_ope),  # convierte el monto a la moneda de la cuenta
                "debit_in_account_currency": 0,
                "exchange_rate": exch_rate_row,  # Tipo de cambio
                "account_currency": curr_row_a,  # Moneda de la cuenta
                "party_type": "Customer",  # Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
                "party": self.customer,
                "reference_name": self.name_inv,  # Referencia dada por sistema
                "reference_type": "Sales Invoice"
            }
            self.rows_journal_entry.append(row_one)



            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 2: MONTO QUE EN REALIDAD SE cobrara, GRAND TOTAL MENOS ISR, MENOS IVA
            curr_row_b = frappe.db.get_value("Account", {"name": self.debit_in_acc_currency},
                                             "account_currency")

            # Validacion que tipo de cambio usar, segun moneda de la cuenta
            exch_rate_row_b = 1 if (curr_row_b == "GTQ") else self.curr_exch

            # VALIDACION GRAND TOTAL DE FACTURA
            # Para una correcta validacion usamos el grand total en la moneda de company "GTQ"
            grand_total_gtq = self.grand_total_currency_company

            # Obtenemos el monto sin IVA del grand total moneda de company "GTQ"
            GRAND_TOTAL_NO_IVA = round(grand_total_gtq/(self.vat_rate + 1), self.decimals_ope)

            # Obtenemos el iva a retener GTQ
            self.IVA_OPE = round((GRAND_TOTAL_NO_IVA * self.vat_rate), self.decimals_ope)

            # El monto en quetzales lo pasamos a la funcion que calcula automaticamente el ISR
            self.ISR_PAYABLE_GTQ = apply_formula_isr(GRAND_TOTAL_NO_IVA, self.company, decimals=self.decimals_ope)

            # El monto a pagar, restando el IVA a retener, e ISR a retener
            amt_without_isr_iva = (grand_total_gtq - (self.IVA_OPE + self.ISR_PAYABLE_GTQ))

            # Se vuelve a validar la conversion a la moneda de la cuenta en caso aplique
            calc_row_two = round(amount_converter(amt_without_isr_iva, self.curr_exch,
                                                  from_currency='GTQ', to_currency=curr_row_b), self.decimals_ope)

            row_two = {
                "account": self.debit_in_acc_currency,  #Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_b,  # Tipo de cambio
                "account_currency": curr_row_b,  # Moneda de la cuenta
                "debit_in_account_currency": calc_row_two,
            }
            self.rows_journal_entry.append(row_two)



            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 3: IVA a retener
            # moneda de la cuenta
            curr_row_c = frappe.db.get_value("Account", {"name": self.iva_account_payable}, "account_currency")
            # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
            # resultado = valor_si if condicion else valor_no
            exch_rate_row_c = 1 if (curr_row_c == "GTQ") else self.curr_exch
            iva_curr_acc = amount_converter(self.IVA_OPE, self.curr_exch, from_currency="GTQ", to_currency=curr_row_c)

            row_three = {
                "account": self.iva_account_payable,  #Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_c,  # Tipo de cambio
                "account_currency": curr_row_c,  # Moneda de la cuenta
                "debit_in_account_currency": round(iva_curr_acc, self.decimals_ope),  #Valor del monto a debitar
            }
            self.rows_journal_entry.append(row_three)



            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 4: RETENCION ISR
            # moneda de la cuenta
            curr_row_d = frappe.db.get_value("Account", {"name": self.isr_account_payable}, "account_currency")
            # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
            # resultado = valor_si if condicion else valor_no
            exch_rate_row_d = 1 if (curr_row_d == "GTQ") else self.curr_exch
            isr_curr_acc = amount_converter(self.ISR_PAYABLE_GTQ, self.curr_exch, from_currency="GTQ", to_currency=curr_row_c)

            row_four = {
                "account": self.isr_account_payable,  # Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_d,  # Tipo de cambio
                "account_currency": curr_row_d,  # Moneda de la cuenta
                "debit_in_account_currency": round(isr_curr_acc, self.decimals_ope),  #Valor del monto a debitar
            }
            self.rows_journal_entry.append(row_four)

            # with open('special.json', 'w') as f:
            #     f.write(json.dumps(self.rows_journal_entry, default=str, indent=2))

        except:
            return False, str(frappe.get_traceback())

        else:
            return True, 'OK'

    def apply_iva_retencion_scenario(self):
        """
        Aplica los calculos necesarios para las filas que conformaran la poliza contable,
        para una factura con retencion IVA

        NOTA IMPORTANTE: LOS CALCULOS APLICADOS AQUI APLICAN PARA GUATEMALA, Y TOMANDO
        EN CUENTA QUE LAS CUENTAS QUE REGISTRAN LOS MONTOS ES EN QUETZALES :)

        Returns:
            tuple: Boolean, descripcion operacion
        """
        try:
            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 1: El monto acordado con supplier
            # obtenemos la moneda de la cuenta por pagar
            curr_row_a = frappe.db.get_value("Account", {"name": self.debit_to}, "account_currency")

            # CALCULOS APLICABLES PARA IMPUESTOS GUATEMALA
            # Si la moneda de la cuenta es GTQ usamos 1, si es USD usamos el tipo cambio
            exch_rate_row = 1 if (curr_row_a == "GTQ") else self.curr_exch

            row_one = {
                "account": self.debit_to,  # Cuenta por pagar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": round(amount_converter(self.grand_total, self.curr_exch,
                                                                     from_currency=self.currency,
                                                                     to_currency=curr_row_a), self.decimals_ope),  # convierte el monto a la moneda de la cuenta
                "debit_in_account_currency": 0,
                "exchange_rate": exch_rate_row,  # Tipo de cambio
                "account_currency": curr_row_a,  # Moneda de la cuenta
                "party_type": "Customer",  # Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
                "party": self.customer,
                "reference_name": self.name_inv,  # Referencia dada por sistema
                "reference_type": "Sales Invoice"
            }
            self.rows_journal_entry.append(row_one)



            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 2: MONTO QUE EN REALIDAD SE cobrara, GRAND TOTAL MENOS IVA
            curr_row_b = frappe.db.get_value("Account", {"name": self.debit_in_acc_currency},
                                             "account_currency")

            # Validacion que tipo de cambio usar, segun moneda de la cuenta
            exch_rate_row_b = 1 if (curr_row_b == "GTQ") else self.curr_exch

            # VALIDACION GRAND TOTAL DE FACTURA
            # Para una correcta validacion usamos el grand total en la moneda de company "GTQ"
            grand_total_gtq = self.grand_total_currency_company

            # Obtenemos el monto sin IVA del grand total moneda de company "GTQ"
            GRAND_TOTAL_NO_IVA = round(grand_total_gtq/(self.vat_rate + 1), self.decimals_ope)

            # Obtenemos el iva a retener GTQ
            self.IVA_OPE = round((GRAND_TOTAL_NO_IVA * self.vat_rate), self.decimals_ope)

            # El monto a pagar, restando el IVA a retener, e ISR a retener
            amt_without_isr_iva = (grand_total_gtq - (self.IVA_OPE))

            # Se vuelve a validar la conversion a la moneda de la cuenta en caso aplique
            calc_row_two = round(amount_converter(amt_without_isr_iva, self.curr_exch,
                                                  from_currency='GTQ', to_currency=curr_row_b), self.decimals_ope)

            row_two = {
                "account": self.debit_in_acc_currency,  #Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_b,  # Tipo de cambio
                "account_currency": curr_row_b,  # Moneda de la cuenta
                "debit_in_account_currency": calc_row_two,
            }
            self.rows_journal_entry.append(row_two)



            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 3: IVA a retener
            # moneda de la cuenta
            curr_row_c = frappe.db.get_value("Account", {"name": self.iva_account_payable}, "account_currency")
            # Si la moneda de la cuenta es usd usara el tipo cambio de la factura
            # resultado = valor_si if condicion else valor_no
            exch_rate_row_c = 1 if (curr_row_c == "GTQ") else self.curr_exch
            iva_curr_acc = amount_converter(self.IVA_OPE, self.curr_exch, from_currency="GTQ", to_currency=curr_row_c)

            row_three = {
                "account": self.iva_account_payable,  #Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "credit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_c,  # Tipo de cambio
                "account_currency": curr_row_c,  # Moneda de la cuenta
                "debit_in_account_currency": round(iva_curr_acc, self.decimals_ope),  #Valor del monto a debitar
            }
            self.rows_journal_entry.append(row_three)


        except:
            return False, str(frappe.get_traceback())

        else:
            return True, 'OK'


def register_withholding(data_ret):
    try:
        new_record = frappe.new_doc('Tax Retention Guatemala')
        new_record.date = str(date.today())
        new_record.retention_type = data_ret.get('retention_type')
        new_record.party_type = data_ret.get('daparty_typete')
        new_record.company = data_ret.get('company')
        new_record.tax_id = data_ret.get('tax_id')
        new_record.sales_invoice = data_ret.get('sales_invoice')
        new_record.invoice_date = data_ret.get('invoice_date')
        new_record.grand_total = data_ret.get('grand_total')
        new_record.currency = data_ret.get('currency')

        new_record.save()

    except:
        pass
        # return False, f'Ocurrio un problema al tratar de registrar la poliza contable: {frappe.get_traceback()}'
    else:
        return True, 'OK'
