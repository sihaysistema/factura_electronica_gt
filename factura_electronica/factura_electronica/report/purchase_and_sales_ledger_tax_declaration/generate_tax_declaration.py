# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import xmltodict
from datetime import datetime, date, time
import os

# TODO
# Crear Vat declaration
# Se agrega al vat declararion el item de cada factura presente en esta declaracion
# Al guardar se agrega a cada una de las facturas el Doctype, Doctype ID o title en el campo de child table Dynamic Link
# A cada factura de las que tocamos, le agregamos al campo custom field, el titulo de ESTA VAT Declaration que creamos.
