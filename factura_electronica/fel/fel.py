# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict

import json, xmltodict
import base64
import requests
import datetime


# NOTAS:
# 1. INSTANCIA FACT

# 2. BUILD
# 2.1 VALIDATOR

# 3. FIRMAR FACTURA
# 3.1 VALIDAR RESPUESTAS

# 4. SOLICITAR FEL
# 4.1 VALIDAR RESPUESTAS

# 5 GUARDAR REGISTROS ENVIOS, LOG
# 5.1 ACTUALIZAR REGISTROS

class ElectronicInvoice:
    def __init__(self, invoice_code, conf_name):
        self.__invoice_code = ''
        self.__config_name = ''
        self.__log_error = []
        # self.__general_data = {}
        # self.__data_sender = {}
        # self.__data_receiver = {}
        # self.__data_phrases = {}
        # self.__items = {}
        # self.__totals = {}

    @property
    def invoice_code(self):
        return self.__invoice_code

    @__invoice_code.setter
    def __invoice_code(self, invoice_code):
        pass

    def build_invoice(self):
        pass

    def validator(self):
        pass

    def general_data(self):
        pass

    def sender(self):
        pass

    def receiver(self):
        pass

    def phrases(self):
        pass

    def items(self):
        pass

    def totals(self):
        pass

    def sign_invoice(self):
        pass

    def request_electronic_invoice(self):
        pass

    def response_validator(self):
        pass

    def save_answers(self):
        pass

    def upgrade_records(self):
        pass

    def save_deliveries(self):
        pass

    def send_email(self):
        pass
