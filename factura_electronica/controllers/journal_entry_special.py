# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
from datetime import date

import frappe
from factura_electronica.utils.formulas import amount_converter, apply_formula_isr, number_of_decimals
from frappe import _, _dict
from frappe.utils import flt


# PARA FACTURA ESPECIAL - PURCHASE INVOICE
class JournalEntrySpecialISR():
    def __init__(self, data_invoice, credit_in_acc_currency, is_multicurrency=0, descr='', cost_center=''):
        """
        Constructor de la clase

        Args:
            data_factura (Object Class Invoice): Instancia de la clase Purchase Invoice
            cost_center (str): Centro de costo a utilizar
            credit_in_acc_currency (str): Nombre de la cuenta que saldara la factura de compra
            is_multicurrency (int): 1 = multimoneda else not
            descr (str): Descripcion opcion para agregar en user remarks
        """
        self.company = data_invoice.get("company")
        self.posting_date = data_invoice.get("posting_date")
        self.posting_time = data_invoice.get("posting_time", "")
        self.grand_total = data_invoice.get("grand_total")
        self.grand_total_currency_company = data_invoice.get("base_grand_total")
        self.credit_to = data_invoice.get("credit_to")
        self.currency = data_invoice.get("currency")
        self.curr_exch = data_invoice.get("conversion_rate")  # Se usara el de la factura ya generada
        self.supplier = data_invoice.get("supplier")
        self.name_inv = data_invoice.get("name")
        self.base_net_total = data_invoice.get("base_total_taxes_and_charges")  # IVA EN moneda de company
        self.cost_center = cost_center or ''
        self.credit_in_acc_currency = credit_in_acc_currency  # CAJA
        self.is_multicurrency = is_multicurrency
        self.remarks = descr
        self.docstatus = 0
        self.rows_journal_entry = []
        self.decimals_ope = 2

    def create(self):
        '''Funcion encargada de crear journal entry haciendo referencia a x factura de compra especial'''
        try:
            # Si no se detecta ningun centro de costo usamos el default de la compania
            # tambien queda la posibilidad de que el usuario lo cambie manualmente
            if not self.cost_center:
                self.cost_center = frappe.db.get_value("Company", {"name": self.company}, "cost_center")

            # Validamos las dependencias necesarias para crear el journal entry
            status_dep = self.validate_dependencies()
            if status_dep[0] == False:
                return False, status_dep[1]

            # Aplicamos los calculos para el escenario factura especial, con retencion ISR e IVA
            status_rows = self.apply_special_inv_scenario()
            if status_rows[0] == False:
                return False, status_rows[1]

            # Creamos un nuevo objeto de la clase Journal Entry
            JOURNALENTRY = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "company": self.company,
                "posting_date": self.posting_date,
                "user_remark": self.remarks,
                "accounts": self.rows_journal_entry,
                "multi_currency": self.is_multicurrency,
                "docstatus": 0  # la deja en draft :D
            })
            status_journal = JOURNALENTRY.insert(ignore_permissions=True)

        except:
            return False, 'Error datos para crear journal entry '+str(frappe.get_traceback())

        else:
            for retention in self.list_retentions:  # Por cada retencion capturada
                new_retention = frappe.get_doc({
                    'doctype': 'Tax Retention Guatemala',
                    'date': frappe.db.get_value('Purchase Invoice', {'name': self.name_inv}, 'posting_date'),
                    'retention_type': retention.get('tax'),
                    'party_type': 'Purchase Invoice',
                    'purchase_invoice': self.name_inv,
                    'company': self.company,
                    'tax_id': frappe.db.get_value('Purchase Invoice', {'name': self.name_inv}, 'facelec_nit_fproveedor'),
                    'grand_total': self.grand_total,
                    'currency': frappe.db.get_value('Purchase Invoice', {'name': self.name_inv}, 'currency'),
                    'retention_amount': retention.get('retention_amount'),
                    'retention_status': '',
                    'docstatus': 0
                })
                new_retention.save()

            return True, status_journal.name

    def validate_dependencies(self):
        """
        Validador dependencias necesarias para generar una poliza contable
        1. Validacion retenciones configuradas para company
        2. Validacion escenario a aplicar, ISR 5% o 7%
        3. Obtencion tasa IVA
        4. Obtencion cuenta isr por cobrar (retencion)
        5. Obtencion cuenta iva por cobrar (retencion)

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
                                                                    'maximum_amount', 'iva_percentage_rate',
                                                                    'vat_retention_to_compensate', 'vat_retention_payable',
                                                                    'income_tax_retention_payable_account'], as_dict=1)

            # El IVA tendra un valor constante en cada fila
            self.grand_total_sin_iva = monto/((self.retention_ranges[0]['iva_percentage_rate']/100)+1)  # monto / 1.12

            # Si no hay configurados
            if len(self.retention_ranges) == 0:
                return False, 'No se puede proceder con la operacion, no se encontraron rango de retencion configurados'

            # TODO: REFACTORIZAR
            # Por cada retencion configurada, verificamos que escenario aplica, en funcion al monto
            # para obtener el nombre correcto de las cuentas a usar en la poliza

            for retention in self.retention_ranges:
                # Si aplica el primer escenario. Aplicamos el 5%
                if (self.grand_total_sin_iva > retention.get('minimum_amount')) and (self.grand_total_sin_iva <= retention.get('maximum_amount')):
                    # Obtenemos el porcentaje de impuesto usado en la factura
                    if not retention.get('iva_percentage_rate'):
                        return False, 'No se puede proceder con los calculos, no se encontro una tasa de IVA configurada'
                    self.vat_rate = (retention.get('iva_percentage_rate')/100)  # 0.12

                    # Cuenta ISR por pagar
                    if not retention.get('income_tax_retention_payable_account'):
                        return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para ISR retencion configurada'
                    self.isr_account_payable = retention.get('income_tax_retention_payable_account')

                    # Cuenta IVA por pagar
                    if not retention.get('vat_retention_to_compensate'):
                        return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para IVA retencion configurada'
                    self.iva_account_payable = retention.get('vat_retention_to_compensate')


                # Si aplica el escenario. Aplicamos el 7%
                if (self.grand_total_sin_iva  >= retention.get('minimum_amount')) and (retention.get('maximum_amount') == 0):
                    # Obtenemos el porcentaje de impuesto usado en la factura
                    if not retention.get('iva_percentage_rate'):
                        return False, 'No se puede proceder con los calculos, no se encontro una tasa de IVA configurada'
                    self.vat_rate = (retention.get('iva_percentage_rate')/100)  # 0.12

                    # Cuenta ISR por pagar
                    if not retention.get('income_tax_retention_payable_account'):
                        return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para ISR retencion configurada'
                    self.isr_account_payable = retention.get('income_tax_retention_payable_account')

                    # Cuenta IVA por pagar
                    if not retention.get('vat_retention_to_compensate'):
                        return False, 'No se puede proceder con la generacion de poliza contable, no se encontro ninguna cuenta para IVA retencion configurada'
                    self.iva_account_payable = retention.get('vat_retention_to_compensate')

            return True, 'OK'

        except:
            return False, str(frappe.get_traceback())

    def apply_special_inv_scenario(self):
        """
        Aplica los calculos necesarios para las filas que conformaran la poliza contable,
        para una factura especial, con retencion IVA e ISR

        NOTA IMPORTANTE: LOS CALCULOS APLICADOS AQUI APLICAN PARA GUATEMALA, Y TOMANDO
        EN CUENTA QUE LAS CUENTAS QUE REGISTRAN LOS MONTOS ES EN QUETZALES :)

        Returns:
            tuple: Boolean, descripcion operacion
        """

        try:
            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 1: El monto acordado con supplier
            # obtenemos la moneda de la cuenta por pagar, este dato se obtiene de la factura de compra
            curr_row_a = frappe.db.get_value("Account", {"name": self.credit_to}, "account_currency")

            # CALCULOS APLICABLES PARA IMPUESTOS GUATEMALA
            # Si la moneda de la cuenta es GTQ usamos 1, si es USD usamos el tipo cambio
            exch_rate_row = 1 if (curr_row_a == "GTQ") else self.curr_exch

            row_one = {
                "account": self.credit_to,  # Cuenta por pagar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "debit_in_account_currency": round(amount_converter(self.grand_total, self.curr_exch,
                                                                    from_currency=self.currency,
                                                                    to_currency=curr_row_a), self.decimals_ope),  # convierte el monto a la moneda de la cuenta
                "credit_in_account_currency": 0,
                "exchange_rate": exch_rate_row,  # Tipo de cambio
                "account_currency": curr_row_a,  # Moneda de la cuenta
                "party_type": "Supplier",  # Tipo de tercero: Proveedor, Cliente, Estudiante, Accionista, Etc. SE USARA CUSTOMER UA QUE VIENE DE SALES INVOICE
                "party": self.supplier,
                "reference_name": self.name_inv,  # Referencia dada por sistema
                "reference_type": "Purchase Invoice"
            }
            self.rows_journal_entry.append(row_one)



            # -------------------------------------------------------------------------------------------------------------------------
            # FILA 2: MONTO QUE EN REALIDAD SE PAGARA, GRAND TOTAL MENOS ISR, MENOS IVA, que saldra de caja
            curr_row_b = frappe.db.get_value("Account", {"name": self.credit_in_acc_currency},
                                             "account_currency")

            # Validacion que tipo de cambio usar, segun moneda de la cuenta
            exch_rate_row_b = 1 if (curr_row_b == "GTQ") else self.curr_exch

            # VALIDACION GRAND TOTAL DE FACTURA
            # Para una correcta validacion usamos el grand total en la moneda de company "GTQ"
            grand_total_gtq = self.grand_total_currency_company

            # Obtenemos el monto sin IVA del grand total moneda de company "GTQ"
            GRAND_TOTAL_NO_IVA = round(self.grand_total_sin_iva, self.decimals_ope)

            # Obtenemos el iva a retener GTQ
            self.IVA_OPE = round((GRAND_TOTAL_NO_IVA * self.vat_rate), self.decimals_ope)

            # El monto en quetzales lo pasamos a la funcion que calcula automaticamente el ISR
            # NOTA: a pesar de que se esta pasando el numero de decimales, no lo estamos aplicando, puede servir
            # para facilitar futuras modifcaiones, EL CALCULO SE HARA CON TODOS LOS DECIMALES
            self.ISR_PAYABLE_GTQ = apply_formula_isr(GRAND_TOTAL_NO_IVA, self.company, decimals=self.decimals_ope)

            # El monto a pagar, restando el IVA a retener, y el ISR a retener
            self.amt_without_isr_iva = (grand_total_gtq - (self.IVA_OPE + self.ISR_PAYABLE_GTQ))

            # Se vuelve a validar la conversion a la moneda de la cuenta en caso aplique
            calc_row_two = round(amount_converter(self.amt_without_isr_iva, self.curr_exch,
                                                  from_currency='GTQ', to_currency=curr_row_b), self.decimals_ope)

            row_two = {
                "account": self.credit_in_acc_currency,  #Cuenta a que se va a utilizar
                "cost_center": self.cost_center,  # Otra cuenta que revisa si esta dentro del presupuesto
                "debit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_b,  # Tipo de cambio
                "account_currency": curr_row_b,  # Moneda de la cuenta
                "credit_in_account_currency": calc_row_two,
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
                "debit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_c,  # Tipo de cambio
                "account_currency": curr_row_c,  # Moneda de la cuenta
                "credit_in_account_currency": round(iva_curr_acc, self.decimals_ope),  #Valor del monto a debitar
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
                "debit_in_account_currency": 0,  #Valor del monto a acreditar
                "exchange_rate": exch_rate_row_d,  # Tipo de cambio
                "account_currency": curr_row_d,  # Moneda de la cuenta
                "credit_in_account_currency": round(isr_curr_acc, self.decimals_ope),  #Valor del monto a debitar
            }
            self.rows_journal_entry.append(row_four)

            # Establecemos el numero de retenciones a registrar, guardandola en variable de la clase
            self.list_retentions = [
                {
                    'tax': 'ISR',
                    'retention_amount': self.ISR_PAYABLE_GTQ
                }
            ]

            # with open('special.json', 'w') as f:
            #     f.write(json.dumps(self.rows_journal_entry, default=str, indent=2))



            # -------------------------------------------------------------------------------------------------------------------------S
            # FILA 5: SI POR ALGUNA RAZON SE EJECUTA EL ESCENARIO DE DESCUADRE POR CENTAVOS, APLICAMOS GOALSEEK
            # VALIDACION SI ES NECESARIO AGREGAR UNA FILA PARA CUADRE DE CENTAVOS
            # convierte de GTQ -> USD, y luego de USD -> GTQ, para obtener correctamente todos
            # los decimales, para hacer aproximacion

            # NOTA: SE HACE LA COMPARACION EVALUANDO PRIMERO EL MONTO SIN IVA E ISR

            INT_GTQ = flt(amount_converter(flt(amount_converter(self.amt_without_isr_iva, self.curr_exch,
                          from_currency='GTQ', to_currency=self.currency), 2), self.curr_exch,
                          from_currency=self.currency, to_currency='GTQ'), 2)

            r = lambda f: f - f % 0.01
            # s = lambda f: f - f % 0.001

            total_debit = flt(float(INT_GTQ + flt(self.ISR_PAYABLE_GTQ, 2) + flt(self.IVA_OPE, 2)))  # LO QUE HAY QUE PAGAR
            total_credit = flt(self.grand_total_currency_company)  # El monto original a pagar, excluyendo impuestos ...

            with open('balance.txt', 'w') as f:
                f.write(f'{total_debit} -- {total_credit}')

            # El monto que meta, que quiero obtener
            goal = total_debit
            x0 = 3  # estimacion

            def fun(x):  # con la evaluacion encontramos la incognita x que son los centavos para cuadrar
                amt_ok = total_credit - x
                return amt_ok

            if total_debit != total_credit:

                centavos = GoalSeek(fun ,goal, x0, MaxIter=1000000)

                # otra forma FACIL es hacer resta y el resultado son los centavos
                # centavos = r(total_debit) - r(total_credit)

                row_five = {
                    "account": frappe.db.get_value('Company', {'name': self.company}, 'round_off_account'),  #'Round Off - B',
                    "cost_center": self.cost_center,
                    "credit_in_account_currency": 0,
                    "exchange_rate": 1,
                    "account_currency": 'GTQ',  # Moneda de la cuenta
                }

                # Validamos si el cuadre va en debit o credit
                if centavos>0:
                    row_five.update({
                        "credit_in_account_currency": flt(centavos),
                        "credit": flt(centavos),
                    })
                    self.rows_journal_entry.append(row_five)

                elif centavos<0:
                    row_five.update({
                        "debit_in_account_currency": flt(abs(centavos)),
                        "debit": flt(abs(centavos)),
                    })
                    self.rows_journal_entry.append(row_five)


                with open('centavos.txt', 'w') as f:
                    f.write(str(abs(centavos)))

        except:
            return False, str(frappe.get_traceback())

        else:
            return True, 'OK'

