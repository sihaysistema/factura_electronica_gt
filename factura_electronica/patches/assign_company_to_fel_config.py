# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Asigna compañía a Configuracion Factura Electronica existentes. #315"""

from __future__ import unicode_literals


def execute():
    from factura_electronica.utils.fel_config import assign_company_to_existing_configurations

    assign_company_to_existing_configurations()
