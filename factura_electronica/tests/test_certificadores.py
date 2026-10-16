# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Certificadores FEL: unicidad, deshabilitar, borrar, anulación y parche. #316

Los tests de unidad simulan frappe y corren sin sitio.
En un bench:
  bench --site <site> run-tests --module factura_electronica.tests.test_certificadores
"""

from __future__ import unicode_literals

import json
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


def _ensure_frappe_stub():
    if "frappe" in sys.modules and hasattr(sys.modules["frappe"], "db"):
        return
    frappe = types.ModuleType("frappe")
    frappe.db = MagicMock()
    frappe.get_all = MagicMock()
    frappe.get_doc = MagicMock()

    def _throw(msg, *args, **kwargs):
        raise Exception(msg)

    frappe.throw = _throw
    frappe.log_error = MagicMock()
    frappe._ = lambda msg: msg
    frappe.whitelist = lambda *args, **kwargs: (lambda fn: fn)
    sys.modules["frappe"] = frappe


_ensure_frappe_stub()

try:
    import requests  # noqa: F401
except ImportError:
    requests = types.ModuleType("requests")
    requests.post = MagicMock()
    sys.modules["requests"] = requests

import frappe  # noqa: E402

from factura_electronica.fel.certifiers.infile import InfileAdapter  # noqa: E402
from factura_electronica.fel.certifiers.registry import (  # noqa: E402
    get_adapter,
    message_not_implemented,
    register_adapter,
    resolve_adapter_class,
)
from factura_electronica.patches.backfill_certificador_infile import (  # noqa: E402
    backfill_infile_links,
    load_official_certificadores,
    seed_official_certificadores,
)
from factura_electronica.utils.fel_config import (  # noqa: E402
    active_config_filters,
    assert_certificador_selectable,
    ensure_single_default_for_company,
    get_active_config_for_company,
    normalize_nit,
    prevent_certificador_deletion,
    resolve_original_configuration,
)

register_adapter(InfileAdapter)


class _Config(object):
    def __init__(self, name, company, is_default, docstatus=1):
        self.name = name
        self.company = company
        self.certificador_predeterminado = is_default
        self.docstatus = docstatus


class TestOfficialCatalog(unittest.TestCase):
    def test_fixture_lists_sat_certifiers_including_infile(self):
        rows = load_official_certificadores()
        self.assertGreaterEqual(len(rows), 18)
        nits = [normalize_nit(row["nit"]) for row in rows]
        self.assertEqual(len(nits), len(set(nits)))
        names = [row["name"] for row in rows]
        self.assertEqual(len(names), len(set(names)))
        infile = [row for row in rows if row["name"] == "INFILE"]
        self.assertEqual(len(infile), 1)
        self.assertEqual(normalize_nit(infile[0]["nit"]), "12521337")
        self.assertIn("INFILE", infile[0]["razon_social"])
        for row in rows:
            self.assertTrue(row.get("razon_social"))
            self.assertTrue(row.get("nit"))

    def test_seed_skips_a_nit_that_already_exists(self):
        with patch.object(frappe.db, "table_exists", return_value=True), patch.object(
            frappe.db, "exists", return_value=False
        ), patch.object(frappe.db, "sql", return_value=[("YA-EXISTE",)]), patch(
            "factura_electronica.patches.backfill_certificador_infile.frappe.get_doc"
        ) as get_doc:
            result = seed_official_certificadores()
        self.assertEqual(result["created"], 0)
        self.assertGreaterEqual(result["skipped"], 18)
        get_doc.assert_not_called()

    def test_seed_inserts_missing_certifiers_by_name(self):
        doc = MagicMock()
        with patch.object(frappe.db, "table_exists", return_value=True), patch.object(
            frappe.db, "exists", return_value=False
        ), patch.object(frappe.db, "sql", return_value=()), patch(
            "factura_electronica.patches.backfill_certificador_infile.frappe.get_doc",
            return_value=doc,
        ):
            result = seed_official_certificadores()
        self.assertEqual(result["created"], 18)
        set_names = [call.kwargs.get("set_name") for call in doc.insert.call_args_list]
        self.assertIn("INFILE", set_names)


class TestSelectionRules(unittest.TestCase):
    def test_active_filter_is_company_and_certifier(self):
        self.assertEqual(
            active_config_filters("Comercial", "INFILE"),
            {"docstatus": 1, "company": "Comercial", "certificador": "INFILE"},
        )

    def test_explicit_configuration_wins_over_the_default(self):
        with patch.object(frappe.db, "get_value", return_value={
            "name": "CONF-OTRO",
            "regimen": "FEL",
            "company": "Comercial",
            "certificador": "DIGIFACT",
            "docstatus": 1,
        }):
            result = get_active_config_for_company("Comercial", configuracion="CONF-OTRO")
        self.assertTrue(result["ok"])
        self.assertEqual(result["name"], "CONF-OTRO")
        self.assertEqual(result["certificador"], "DIGIFACT")

    def test_explicit_configuration_must_belong_to_the_company(self):
        with patch.object(frappe.db, "get_value", return_value={
            "name": "CONF-OTRO",
            "regimen": "FEL",
            "company": "Otra",
            "certificador": "INFILE",
            "docstatus": 1,
        }):
            result = get_active_config_for_company("Comercial", configuracion="CONF-OTRO")
        self.assertFalse(result["ok"])
        self.assertIn("Comercial", result["message"])

    def test_second_default_clears_the_previous_one(self):
        doc = _Config("CONF-NUEVA", "Comercial", 1)
        rows = [{
            "name": "CONF-VIEJA",
            "certificador": "INFILE",
            "certificador_predeterminado": 1,
        }]
        with patch(
            "factura_electronica.utils.fel_config.get_active_fel_configs",
            return_value=rows,
        ), patch("factura_electronica.utils.fel_config.frappe.db.set_value") as set_value:
            ensure_single_default_for_company(doc)
        set_value.assert_called_with(
            "Configuracion Factura Electronica",
            "CONF-VIEJA",
            "certificador_predeterminado",
            0,
            update_modified=False,
        )

    def test_several_active_without_a_default_are_rejected(self):
        doc = _Config("CONF-NUEVA", "Comercial", 0)
        rows = [{
            "name": "CONF-VIEJA",
            "certificador": "INFILE",
            "certificador_predeterminado": 0,
        }]
        with patch(
            "factura_electronica.utils.fel_config.get_active_fel_configs",
            return_value=rows,
        ):
            with self.assertRaises(Exception) as raised:
                ensure_single_default_for_company(doc)
        self.assertIn("predeterminado", str(raised.exception))


class TestDisableAndDelete(unittest.TestCase):
    def test_disabled_certifier_cannot_be_newly_selected(self):
        with patch.object(frappe.db, "get_value", return_value=1):
            with self.assertRaises(Exception) as raised:
                assert_certificador_selectable("DIGIFACT", previous=None)
        self.assertIn("deshabilitado", str(raised.exception).lower())
        self.assertIn("DIGIFACT", str(raised.exception))

    def test_historical_link_to_a_disabled_certifier_can_stay(self):
        with patch.object(frappe.db, "get_value", return_value=1):
            assert_certificador_selectable("DIGIFACT", previous="DIGIFACT")

    def test_delete_is_blocked_when_envio_or_config_references_it(self):
        def _count(doctype, filters=None):
            if doctype == "Envio FEL":
                return 4
            return 1

        with patch.object(frappe.db, "table_exists", return_value=True), patch.object(
            frappe.db, "has_column", return_value=True
        ), patch.object(frappe.db, "count", side_effect=_count):
            with self.assertRaises(Exception) as raised:
                prevent_certificador_deletion("INFILE")
        message = str(raised.exception)
        self.assertIn("INFILE", message)
        self.assertIn("Deshabilítelo", message)
        self.assertIn("Envio FEL", message)

    def test_delete_is_allowed_when_nothing_references_it(self):
        with patch.object(frappe.db, "table_exists", return_value=True), patch.object(
            frappe.db, "has_column", return_value=True
        ), patch.object(frappe.db, "count", return_value=0):
            prevent_certificador_deletion("CERT-NUEVO")


class TestOriginalEnvioRouting(unittest.TestCase):
    def _route(self, envio, config, disabled=0):
        def get_value(doctype, name, fields=None, as_dict=False):
            if doctype == "Envio FEL":
                return envio
            if doctype == "Configuracion Factura Electronica":
                return config
            if doctype == "Certificador FEL":
                return disabled
            return None

        with patch(
            "factura_electronica.utils.fel_config.find_envio_fel_for_document",
            return_value="UUID-ORIGINAL",
        ), patch(
            "factura_electronica.utils.fel_config.frappe.db.get_value",
            side_effect=get_value,
        ):
            return resolve_original_configuration("Sales Invoice", "FAC-001")

    def test_cancellation_uses_the_original_config_not_the_current_default(self):
        result = self._route(
            envio={
                "name": "UUID-ORIGINAL",
                "configuracion": "CONF-ORIGINAL",
                "certificador": "DIGIFACT",
                "company": "Comercial",
            },
            config={
                "name": "CONF-ORIGINAL",
                "docstatus": 1,
                "certificador": "DIGIFACT",
                "company": "Comercial",
            },
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["name"], "CONF-ORIGINAL")
        self.assertEqual(result["certificador"], "DIGIFACT")

    def test_cancelled_original_config_is_a_spanish_error(self):
        result = self._route(
            envio={"name": "UUID-ORIGINAL", "configuracion": "CONF-ORIGINAL", "certificador": "INFILE"},
            config={"name": "CONF-ORIGINAL", "docstatus": 2, "certificador": "INFILE", "company": "Comercial"},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "cancelled")
        self.assertIn("cancelada", result["message"].lower())

    def test_disabled_original_certifier_is_a_spanish_error(self):
        result = self._route(
            envio={"name": "UUID-ORIGINAL", "configuracion": "CONF-ORIGINAL", "certificador": "DIGIFACT"},
            config={"name": "CONF-ORIGINAL", "docstatus": 1, "certificador": "DIGIFACT", "company": "Comercial"},
            disabled=1,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "certificador_disabled")
        self.assertIn("deshabilitado", result["message"].lower())

    def test_missing_original_envio_does_not_fall_back_to_the_default(self):
        with patch(
            "factura_electronica.utils.fel_config.find_envio_fel_for_document",
            return_value=None,
        ):
            result = resolve_original_configuration("Sales Invoice", "FAC-404")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "missing_envio")
        self.assertIn("Envio FEL", result["message"])


class TestCertifierDispatch(unittest.TestCase):
    def test_infile_resolves_by_name_and_by_nit(self):
        self.assertIs(resolve_adapter_class("INFILE", None), InfileAdapter)
        self.assertIs(resolve_adapter_class(None, "1252133-7"), InfileAdapter)
        self.assertIs(resolve_adapter_class("infile", "12521337"), InfileAdapter)

    def test_other_certifiers_are_not_implemented_yet(self):
        self.assertIsNone(resolve_adapter_class("DIGIFACT", "77454820"))
        message = message_not_implemented("DIGIFACT SERVICIOS, S. A.", "77454820")
        self.assertIn("implementado aún", message)
        with patch.object(frappe.db, "exists", return_value=True), patch.object(
            frappe.db, "get_value", return_value={
                "nit": "77454820",
                "razon_social": "DIGIFACT SERVICIOS, S. A.",
            }
        ):
            with self.assertRaises(Exception) as raised:
                get_adapter("DIGIFACT")
        self.assertIn("implementado aún", str(raised.exception))


class TestBackfillSql(unittest.TestCase):
    def test_backfill_uses_bulk_updates_and_does_not_overwrite(self):
        queries = []

        def sql(query, values=None, *args, **kwargs):
            queries.append((" ".join(str(query).split()), values))
            if "ROW_COUNT" in str(query):
                return ((2,),)
            return ()

        with patch.object(frappe.db, "table_exists", return_value=True), patch.object(
            frappe.db, "has_column", return_value=True
        ), patch.object(frappe.db, "exists", return_value=True), patch.object(
            frappe.db, "sql", side_effect=sql
        ):
            result = backfill_infile_links()

        texts = [query for query, _values in queries]
        updates = [query for query in texts if query.upper().startswith("UPDATE")]
        self.assertGreaterEqual(len(updates), 4)
        self.assertLess(len(updates), 20)
        self.assertTrue(any("tabConfiguracion Factura Electronica" in query and "certificador" in query for query in updates))
        self.assertTrue(any("`tabEnvio FEL`" in query and "SET certificador" in query for query in updates))
        self.assertTrue(any("tabSales Invoice" in query for query in updates))
        self.assertTrue(any("tabPurchase Invoice" in query for query in updates))
        for query in updates:
            if "SET certificador" in query or "SET envio.company" in query or "SET envio.configuracion" in query:
                self.assertIn("IFNULL", query)
        self.assertFalse(any(query.upper().startswith("INSERT") for query in texts))
        self.assertEqual(result["infile"], "INFILE")
        self.assertGreater(result["configs"], 0)
        self.assertGreater(result["envios"], 0)

    def test_fixture_json_is_a_list_of_documents(self):
        rows = load_official_certificadores()
        self.assertIsInstance(rows, list)
        self.assertTrue(all(row.get("doctype") == "Certificador FEL" for row in rows))
        json.dumps(rows)
