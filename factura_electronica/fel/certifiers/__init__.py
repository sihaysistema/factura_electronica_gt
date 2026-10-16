# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Despacho de certificadores FEL.

El mapa NIT/nombre -> adaptador vive en registry. Hoy solo INFILE
implementa firma, certificación y anulación. Cualquier otro certificador
autorizado por la SAT levanta un error claro de que aún no está implementado.
"""

from __future__ import unicode_literals

from factura_electronica.fel.certifiers.infile import InfileAdapter
from factura_electronica.fel.certifiers.registry import (
    cancel_dte,
    certify_dte,
    get_adapter,
    get_adapter_for_config,
    post_json,
    register_adapter,
    resolve_adapter_class,
    sign_xml,
)

register_adapter(InfileAdapter)

__all__ = [
    "cancel_dte",
    "certify_dte",
    "get_adapter",
    "get_adapter_for_config",
    "post_json",
    "register_adapter",
    "resolve_adapter_class",
    "sign_xml",
]
