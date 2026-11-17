# -*- coding: utf-8 -*-
"""Migrate hooks that must not ship as full-record fixtures.

UOM FEL codes used to live in fixtures/uom.json. Frappe deletes and
reinserts every JSON file in fixtures/ on migrate. Those rows had no
enabled key, so v15 stored enabled=0. The codes are applied here and
never change enabled on a UOM that already exists.
"""

from __future__ import unicode_literals

from factura_electronica.utils.uom_fel_codes import sync_uom_fel_codes


def after_install():
    sync_uom_fel_codes()


def after_migrate():
    sync_uom_fel_codes()
