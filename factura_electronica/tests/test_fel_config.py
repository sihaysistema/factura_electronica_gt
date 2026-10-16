# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""Selección y validación de Configuración Factura Electrónica por compañía. #315

Los tests de unidad simulan frappe y corren sin sitio.
En un bench:
  bench --site <site> run-tests --module factura_electronica.tests.test_fel_config
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
    def _throw(msg, *args, **kwargs):
        raise Exception(msg)

    frappe.throw = _throw
    frappe.log_error = MagicMock()
    frappe._ = lambda msg: msg
    frappe.defaults = MagicMock()
    sys.modules["frappe"] = frappe


_ensure_frappe_stub()

import frappe  # noqa: E402

from factura_electronica.utils.fel_config import (  # noqa: E402
    assign_company_to_existing_configurations,
    ensure_single_active_configuration,
    get_active_config_for_company,
    match_company_by_nit,
    normalize_nit,
)


class TestGetActiveConfigForCompany(unittest.TestCase):
    def test_missing_company_message_is_spanish(self):
        result = get_active_config_for_company(None)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "missing_company")
        self.assertIn("compañía", result["message"].lower())

    def test_no_active_config_names_the_company(self):
        with patch("factura_electronica.utils.fel_config.get_active_fel_configs", return_value=[]):
            result = get_active_config_for_company("Comercial Uno")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "none")
        self.assertIn("Comercial Uno", result["message"])
        self.assertIn("no tiene", result["message"].lower())

    def test_returns_the_single_active_config(self):
        rows = [{"name": "CONFIG-FAC-00001", "regimen": "FEL"}]
        with patch("factura_electronica.utils.fel_config.get_active_fel_configs", return_value=rows):
            result = get_active_config_for_company("Comercial Uno")
        self.assertTrue(result["ok"])
        self.assertEqual(result["name"], "CONFIG-FAC-00001")
        self.assertEqual(result["regimen"], "FEL")

    def test_two_companies_do_not_share_a_lookup(self):
        def rows_for(company, certificador=None):
            if company == "Compania A":
                return [{"name": "CONF-A", "regimen": "FEL"}]
            if company == "Compania B":
                return [{"name": "CONF-B", "regimen": "FEL"}]
            return []

        with patch(
            "factura_electronica.utils.fel_config.get_active_fel_configs",
            side_effect=rows_for,
        ):
            config_a = get_active_config_for_company("Compania A")
            config_b = get_active_config_for_company("Compania B")

        self.assertEqual(config_a["name"], "CONF-A")
        self.assertEqual(config_b["name"], "CONF-B")
        self.assertNotEqual(config_a["name"], config_b["name"])

    def test_several_active_configs_without_default_are_ambiguous(self):
        rows = [
            {"name": "CONF-1", "regimen": "FEL", "certificador": "INFILE", "certificador_predeterminado": 0},
            {"name": "CONF-2", "regimen": "FEL", "certificador": "DIGIFACT", "certificador_predeterminado": 0},
        ]
        with patch("factura_electronica.utils.fel_config.get_active_fel_configs", return_value=rows):
            result = get_active_config_for_company("Compania A")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "no_default")
        self.assertIn("Compania A", result["message"])
        self.assertIn("predeterminado", result["message"])

    def test_several_active_configs_use_the_default(self):
        rows = [
            {"name": "CONF-INFILE", "regimen": "FEL", "certificador": "INFILE", "certificador_predeterminado": 0},
            {"name": "CONF-DIGI", "regimen": "FEL", "certificador": "DIGIFACT", "certificador_predeterminado": 1},
        ]
        with patch("factura_electronica.utils.fel_config.get_active_fel_configs", return_value=rows):
            result = get_active_config_for_company("Compania A")
        self.assertTrue(result["ok"])
        self.assertEqual(result["name"], "CONF-DIGI")
        self.assertEqual(result["certificador"], "DIGIFACT")


class TestUniquenessRule(unittest.TestCase):
    def test_company_is_required(self):
        with self.assertRaises(Exception):
            ensure_single_active_configuration("")

    def test_blocks_another_active_config_for_the_same_certifier(self):
        rows = [{"name": "CONF-EXISTENTE", "regimen": "FEL", "certificador": "INFILE"}]
        with patch("factura_electronica.utils.fel_config.get_active_fel_configs", return_value=rows) as lookup:
            with self.assertRaises(Exception) as raised:
                ensure_single_active_configuration("Compania A", "INFILE", "CONF-NUEVA")
        lookup.assert_called_with("Compania A", "INFILE")
        self.assertIn("CONF-EXISTENTE", str(raised.exception))
        self.assertIn("Compania A", str(raised.exception))
        self.assertIn("INFILE", str(raised.exception))

    def test_resaving_the_same_config_is_allowed(self):
        rows = [{"name": "CONF-A", "regimen": "FEL", "certificador": "INFILE"}]
        with patch("factura_electronica.utils.fel_config.get_active_fel_configs", return_value=rows):
            ensure_single_active_configuration("Compania A", "INFILE", "CONF-A")

    def test_certificador_is_required_for_uniqueness(self):
        with self.assertRaises(Exception) as raised:
            ensure_single_active_configuration("Compania A", "")
        self.assertIn("certificador", str(raised.exception).lower())


class TestCompanyAssignmentPatch(unittest.TestCase):
    def test_normalize_nit(self):
        self.assertEqual(normalize_nit(" 123456-7 "), "1234567")
        self.assertEqual(normalize_nit(None), "")

    def test_nit_matches_tax_id_or_facelec_nit(self):
        companies = [
            {"name": "A", "tax_id": "111-1", "nit_face_company": ""},
            {"name": "B", "tax_id": "", "nit_face_company": "222-2"},
        ]
        self.assertEqual(match_company_by_nit("1111", companies), "A")
        self.assertEqual(match_company_by_nit("2222", companies), "B")
        self.assertIsNone(match_company_by_nit("999", companies))

    def _run_patch(self, rows, companies, default_company):
        updates = []
        fake_db = MagicMock()
        fake_db.table_exists.return_value = True
        fake_db.has_column.return_value = True
        fake_db.sql.return_value = rows

        def set_value(doctype, name, field, value, update_modified=False):
            updates.append((name, field, value))

        fake_db.set_value.side_effect = set_value
        with patch("factura_electronica.utils.fel_config.frappe.db", fake_db), \
                patch("factura_electronica.utils.fel_config.frappe.get_all", return_value=companies), \
                patch("factura_electronica.utils.fel_config.frappe.log_error"), \
                patch(
                    "factura_electronica.utils.fel_config.default_company_name",
                    return_value=default_company,
                ):
            result = assign_company_to_existing_configurations()
        return result, updates

    def test_single_company_site_uses_that_company(self):
        result, updates = self._run_patch(
            rows=[{"name": "CONF-LEGACY", "nit_gface": "999"}],
            companies=[{"name": "Mi Empresa", "tax_id": "111", "nit_face_company": "111"}],
            default_company="Otra",
        )
        self.assertEqual(result["updated"], 1)
        self.assertEqual(updates, [("CONF-LEGACY", "company", "Mi Empresa")])

    def test_nit_match_when_several_companies(self):
        result, updates = self._run_patch(
            rows=[{"name": "CONF-B", "nit_gface": "55-55"}],
            companies=[
                {"name": "Norte", "tax_id": "111", "nit_face_company": ""},
                {"name": "Sur", "tax_id": "5555", "nit_face_company": ""},
            ],
            default_company="Norte",
        )
        self.assertEqual(updates, [("CONF-B", "company", "Sur")])
        self.assertEqual(result["skipped"], 0)

    def test_falls_back_to_default_company(self):
        result, updates = self._run_patch(
            rows=[{"name": "CONF-X", "nit_gface": ""}],
            companies=[
                {"name": "Norte", "tax_id": "111", "nit_face_company": ""},
                {"name": "Sur", "tax_id": "222", "nit_face_company": ""},
            ],
            default_company="Norte",
        )
        self.assertEqual(updates, [("CONF-X", "company", "Norte")])
        self.assertEqual(result["updated"], 1)

    def test_skips_when_company_cannot_be_resolved(self):
        result, updates = self._run_patch(
            rows=[{"name": "CONF-Y", "nit_gface": ""}],
            companies=[
                {"name": "Norte", "tax_id": "111", "nit_face_company": ""},
                {"name": "Sur", "tax_id": "222", "nit_face_company": ""},
            ],
            default_company=None,
        )
        self.assertEqual(updates, [])
        self.assertEqual(result["skipped"], 1)


def _running_on_site():
    try:
        return bool(getattr(frappe.local, "site", None))
    except Exception:
        return False


@unittest.skipUnless(_running_on_site(), "requiere un sitio Frappe")
class TestFelConfigOnSite(unittest.TestCase):
    """Dos compañías, cada una con su configuración, y el payload FEL usa sus credenciales."""

    def setUp(self):
        frappe.set_user("Administrator")
        self._cleanup = []

    def tearDown(self):
        for doctype, name in reversed(self._cleanup):
            try:
                if frappe.db.exists(doctype, name):
                    doc = frappe.get_doc(doctype, name)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc(doctype, name, force=1)
            except Exception:
                frappe.db.rollback()
        frappe.db.commit()

    def _track(self, doc):
        self._cleanup.append((doc.doctype, doc.name))
        return doc

    def _make_company(self, company_name, abbr, nit):
        if frappe.db.exists("Company", company_name):
            return frappe.get_doc("Company", company_name)
        doc = frappe.get_doc({
            "doctype": "Company",
            "company_name": company_name,
            "abbr": abbr,
            "default_currency": "USD",
            "country": "Guatemala",
            "nit_face_company": nit,
            "facelec_trade_name": company_name,
            "tax_id": nit,
        })
        doc.insert(ignore_permissions=True)
        if frappe.db.has_column("Company", "nit_face_company"):
            frappe.db.set_value("Company", doc.name, "nit_face_company", nit, update_modified=False)
        frappe.db.set_value("Company", doc.name, "tax_id", nit, update_modified=False)
        self._track(doc)
        return doc

    def _ensure_root(self, doctype, name_field, name):
        existing = frappe.db.get_value(doctype, {name_field: name}, "name")
        if existing:
            return existing
        doc = frappe.get_doc({
            "doctype": doctype,
            name_field: name,
            "is_group": 1,
        })
        doc.insert(ignore_permissions=True)
        self._track(doc)
        return doc.name

    def _ensure_leaf(self, doctype, name_field, name, parent_field, parent):
        existing = frappe.db.get_value(doctype, {name_field: name}, "name")
        if existing:
            return existing
        doc = frappe.get_doc({
            "doctype": doctype,
            name_field: name,
            "is_group": 0,
            parent_field: parent,
        })
        doc.insert(ignore_permissions=True)
        self._track(doc)
        return doc.name

    def _customer_group(self):
        root = self._ensure_root("Customer Group", "customer_group_name", "All Customer Groups")
        return self._ensure_leaf("Customer Group", "customer_group_name", "Commercial", "parent_customer_group", root)

    def _territory(self):
        root = self._ensure_root("Territory", "territory_name", "All Territories")
        return self._ensure_leaf("Territory", "territory_name", "Guatemala", "parent_territory", root)

    def _item_group(self):
        root = self._ensure_root("Item Group", "item_group_name", "All Item Groups")
        return self._ensure_leaf("Item Group", "item_group_name", "Products", "parent_item_group", root)

    def _uom(self):
        for name in ("Nos", "Unidad", "Unit"):
            if frappe.db.exists("UOM", name):
                return name
        return frappe.db.get_value("UOM", {}, "name")

    def _price_list(self, currency):
        name = "FEL Selling {0}".format(currency)
        existing = frappe.db.get_value("Price List", {"price_list_name": name}, "name")
        if existing:
            return existing
        doc = frappe.get_doc({
            "doctype": "Price List",
            "price_list_name": name,
            "currency": currency,
            "selling": 1,
            "enabled": 1,
        })
        doc.insert(ignore_permissions=True)
        self._track(doc)
        return doc.name

    def _make_invoice(self, company_name, series):
        customer = self._track(frappe.get_doc({
            "doctype": "Customer",
            "customer_name": "Cliente {0}".format(company_name),
            "customer_group": self._customer_group(),
            "territory": self._territory(),
        }).insert(ignore_permissions=True))
        item_code = "FEL-ITEM-{0}".format(company_name[:8].replace(" ", ""))
        if not frappe.db.exists("Item", item_code):
            self._track(frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "item_group": self._item_group(),
                "stock_uom": self._uom(),
                "is_stock_item": 0,
            }).insert(ignore_permissions=True))
        receivable = frappe.db.get_value("Company", company_name, "default_receivable_account")
        income = frappe.db.get_value("Company", company_name, "default_income_account")
        if not income:
            income = frappe.db.get_value(
                "Account", {"company": company_name, "root_type": "Income", "is_group": 0}, "name"
            )
        cost_center = frappe.db.get_value("Company", company_name, "cost_center")
        if not cost_center:
            cost_center = frappe.db.get_value(
                "Cost Center", {"company": company_name, "is_group": 0}, "name"
            )
        currency = frappe.db.get_value("Company", company_name, "default_currency") or "USD"
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": company_name,
            "customer": customer.name,
            "naming_series": series,
            "currency": currency,
            "conversion_rate": 1,
            "selling_price_list": self._price_list(currency),
            "price_list_currency": currency,
            "plc_conversion_rate": 1,
            "debit_to": receivable,
            "update_stock": 0,
            "items": [{
                "item_code": item_code,
                "qty": 1,
                "rate": 100,
                "income_account": income,
                "cost_center": cost_center,
            }],
        })
        invoice.insert(ignore_permissions=True)
        self._track(invoice)
        return invoice

    def _ensure_infile(self):
        if frappe.db.exists("Certificador FEL", "INFILE"):
            return "INFILE"
        doc = frappe.get_doc({
            "doctype": "Certificador FEL",
            "razon_social": "INFILE, S. A.",
            "nit": "12521337",
            "nombre_comercial": "INFILE",
            "sitio_web": "https://www.infile.com",
        })
        doc.insert(ignore_permissions=True, set_name="INFILE")
        self._track(doc)
        return doc.name

    def _ensure_certifier(self, name, nit, razon_social):
        if frappe.db.exists("Certificador FEL", name):
            return name
        doc = frappe.get_doc({
            "doctype": "Certificador FEL",
            "razon_social": razon_social,
            "nit": nit,
            "nombre_comercial": name,
        })
        doc.insert(ignore_permissions=True, set_name=name)
        self._track(doc)
        return doc.name

    def _submit_config(self, company_name, alias, llave_ws, llave_pfx, series, certificador=None, predeterminado=1):
        config = frappe.get_doc({
            "doctype": "Configuracion Factura Electronica",
            "company": company_name,
            "regimen": "FEL",
            "url_descarga_pdf": "https://infile.test/pdf/",
            "alias": alias,
            "llave_ws": llave_ws,
            "llave_pfx": llave_pfx,
            "url_firma": "https://infile.test/firma",
            "url_dte": "https://infile.test/dte",
            "es_anulacion": "N",
            "correo_copia": "{0}@test.example".format(alias.lower()),
            "factura_venta_fel": 1,
            "nit_gface": frappe.db.get_value("Company", company_name, "tax_id"),
            "certificador": certificador or self._ensure_infile(),
            "certificador_predeterminado": predeterminado,
        })
        config.insert(ignore_permissions=True)
        config.submit()
        self._track(config)
        frappe.db.sql(
            """
            INSERT INTO `tabConfiguracion Series FEL`
                (name, creation, modified, modified_by, owner, docstatus,
                 parent, parenttype, parentfield, serie, tipo_documento, idx)
            VALUES (%s, NOW(), NOW(), 'Administrator', 'Administrator', 0,
                    %s, 'Configuracion Factura Electronica', 'series_fel', %s, 'FACT', 1)
            """,
            ("SER-{0}".format(config.name), config.name, series),
        )
        return config

    def test_one_active_config_per_company_and_payload_credentials(self):
        from factura_electronica.fel.fel import ElectronicInvoice
        from factura_electronica.fel_api import generate_electronic_invoice, validate_configuration

        company_a = self._make_company("FEL Compania A 315", "FELA", "1111111")
        company_b = self._make_company("FEL Compania B 315", "FELB", "2222222")
        options = frappe.get_meta("Sales Invoice").get_field("naming_series").options or ""
        series = [line for line in options.split("\n") if line.strip()][0]
        invoice_a = self._make_invoice(company_a.name, series)
        invoice_b = self._make_invoice(company_b.name, series)
        config_a = self._submit_config(company_a.name, "ALIAS-A", "LLAVE-WS-A", "LLAVE-PFX-A", series)
        config_b = self._submit_config(company_b.name, "ALIAS-B", "LLAVE-WS-B", "LLAVE-PFX-B", series)

        self.assertEqual(validate_configuration(company_a.name), (True, config_a.name))
        self.assertEqual(validate_configuration(company_b.name), (True, config_b.name))

        duplicate = frappe.get_doc({
            "doctype": "Configuracion Factura Electronica",
            "company": company_a.name,
            "certificador": "INFILE",
            "regimen": "FEL",
            "url_descarga_pdf": "https://infile.test/pdf/",
        })
        duplicate.insert(ignore_permissions=True)
        self._track(duplicate)
        with self.assertRaises(Exception) as raised:
            duplicate.submit()
        self.assertIn(company_a.name, str(raised.exception))

        calls = []

        class _Response(object):
            def __init__(self, payload):
                self.content = json.dumps(payload).encode("utf-8")

        def fake_post(url, data=None, headers=None, **kwargs):
            calls.append({"url": url, "data": json.loads(data), "headers": headers or {}})
            if "firma" in str(url):
                return _Response({"resultado": True, "archivo": "SIGNED"})
            return _Response({
                "resultado": True,
                "cantidad_errores": 0,
                "uuid": "UUID-TEST",
                "serie": "A",
                "numero": "1",
            })

        def fake_build(invoice):
            invoice._ElectronicInvoice__base_peticion = {"dte:GTDocumento": {"@Version": "0.1"}}
            company = frappe.db.get_value("Sales Invoice", invoice._ElectronicInvoice__invoice_code, "company")
            invoice.dat_fac = [{"company": company}]
            return True, "OK"

        with patch("factura_electronica.fel.certifiers.infile.requests.post", side_effect=fake_post), \
                patch.object(ElectronicInvoice, "build_invoice", fake_build):
            generate_electronic_invoice(invoice_a.name, series)
            generate_electronic_invoice(invoice_b.name, series)

        sign_calls = [call for call in calls if "firma" in call["url"]]
        dte_calls = [call for call in calls if "dte" in call["url"]]
        self.assertEqual(len(sign_calls), 2)
        self.assertEqual(len(dte_calls), 2)
        self.assertEqual(sign_calls[0]["data"]["alias"], "ALIAS-A")
        self.assertEqual(sign_calls[0]["data"]["llave"], "LLAVE-PFX-A")
        self.assertEqual(sign_calls[1]["data"]["alias"], "ALIAS-B")
        self.assertEqual(sign_calls[1]["data"]["llave"], "LLAVE-PFX-B")
        self.assertEqual(dte_calls[0]["headers"]["usuario"], "ALIAS-A")
        self.assertEqual(dte_calls[0]["headers"]["llave"], "LLAVE-WS-A")
        self.assertEqual(dte_calls[0]["headers"]["identificador"], invoice_a.name)
        self.assertEqual(dte_calls[1]["headers"]["usuario"], "ALIAS-B")
        self.assertEqual(dte_calls[1]["headers"]["llave"], "LLAVE-WS-B")
        self.assertEqual(dte_calls[1]["headers"]["identificador"], invoice_b.name)
        self.assertIn("1111111", dte_calls[0]["data"]["nit_emisor"])
        self.assertIn("2222222", dte_calls[1]["data"]["nit_emisor"])

    def test_two_certifiers_default_and_original_envio_routing(self):
        from factura_electronica.utils.fel_config import (
            get_active_config_for_company,
            resolve_original_configuration,
        )
        from factura_electronica.patches.backfill_certificador_infile import backfill_infile_links

        company = self._make_company("FEL Compania Cert 316", "F316", "3333316")
        options = frappe.get_meta("Sales Invoice").get_field("naming_series").options or ""
        series = [line for line in options.split("\n") if line.strip()][0]
        self._ensure_infile()
        self._ensure_certifier("CERT316", "999316316", "Certificador de prueba 316")
        config_infile = self._submit_config(
            company.name, "ALIAS-IN", "LLAVE-WS-IN", "LLAVE-PFX-IN", series,
            certificador="INFILE", predeterminado=1,
        )
        config_other = self._submit_config(
            company.name, "ALIAS-OT", "LLAVE-WS-OT", "LLAVE-PFX-OT", series,
            certificador="CERT316", predeterminado=0,
        )

        active = get_active_config_for_company(company.name)
        self.assertTrue(active["ok"])
        self.assertEqual(active["name"], config_infile.name)
        explicit = get_active_config_for_company(company.name, configuracion=config_other.name)
        self.assertEqual(explicit["name"], config_other.name)

        envio = frappe.get_doc({
            "doctype": "Envio FEL",
            "uuid": "UUID-316-ORIGINAL",
            "serie_factura_original": "FAC-316-ORIGINAL",
            "company": company.name,
            "configuracion": config_other.name,
            "certificador": "CERT316",
            "resultado": "true",
        })
        envio.insert(ignore_permissions=True)
        self._track(envio)

        routed = resolve_original_configuration("Sales Invoice", "FAC-316-ORIGINAL")
        self.assertTrue(routed["ok"])
        self.assertEqual(routed["name"], config_other.name)
        self.assertEqual(routed["certificador"], "CERT316")
        self.assertNotEqual(routed["name"], config_infile.name)

        frappe.db.set_value("Certificador FEL", "CERT316", "disabled", 1, update_modified=False)
        disabled = resolve_original_configuration("Sales Invoice", "FAC-316-ORIGINAL")
        self.assertFalse(disabled["ok"])
        self.assertIn("deshabilitado", disabled["message"].lower())
        frappe.db.set_value("Certificador FEL", "CERT316", "disabled", 0, update_modified=False)

        config_other.cancel()
        cancelled = resolve_original_configuration("Sales Invoice", "FAC-316-ORIGINAL")
        self.assertFalse(cancelled["ok"])
        self.assertIn("cancelada", cancelled["message"].lower())

        with self.assertRaises(Exception) as raised:
            frappe.delete_doc("Certificador FEL", "CERT316")
        self.assertIn("Deshabilítelo", str(raised.exception))

        frappe.db.sql(
            """
            UPDATE `tabConfiguracion Factura Electronica`
            SET certificador = '', certificador_predeterminado = 0
            WHERE name = %s
            """,
            (config_infile.name,),
        )
        frappe.db.sql(
            """
            INSERT INTO `tabEnvio FEL`
                (name, uuid, serie_factura_original, company, configuracion, certificador,
                 docstatus, creation, modified, owner, modified_by)
            VALUES (%s, %s, %s, %s, '', '', 0, NOW(), NOW(), 'Administrator', 'Administrator')
            """,
            ("UUID-316-LEGACY", "UUID-316-LEGACY", "SIN-FACTURA-316", company.name),
        )
        self._cleanup.append(("Envio FEL", "UUID-316-LEGACY"))
        backfill_infile_links()
        self.assertEqual(
            frappe.db.get_value("Configuracion Factura Electronica", config_infile.name, "certificador"),
            "INFILE",
        )
        legacy = frappe.db.get_value(
            "Envio FEL", "UUID-316-LEGACY", ["certificador", "configuracion", "company"], as_dict=True
        )
        self.assertEqual(legacy.certificador, "INFILE")
        self.assertEqual(legacy.company, company.name)
        self.assertEqual(legacy.configuracion, config_infile.name)

    def test_legacy_config_without_company_is_assigned_on_single_company_site(self):
        companies = [row.name for row in frappe.get_all("Company", fields=["name"])]
        if len(companies) != 1:
            self.skipTest("el parche de sitio único se prueba con bench migrate")
        from factura_electronica.utils.fel_config import assign_company_to_existing_configurations

        name = "CONF-LEGACY-315"
        if frappe.db.exists("Configuracion Factura Electronica", name):
            frappe.db.sql(
                "UPDATE `tabConfiguracion Factura Electronica` SET company = '' WHERE name = %s",
                (name,),
            )
        else:
            self._insert_legacy_config(name)
        result = assign_company_to_existing_configurations()
        company = frappe.db.get_value("Configuracion Factura Electronica", name, "company")
        self.assertGreaterEqual(result["updated"], 1)
        self.assertEqual(company, companies[0])

    def _insert_legacy_config(self, name):
        frappe.db.sql(
            """
            INSERT INTO `tabConfiguracion Factura Electronica`
                (name, docstatus, regimen, url_descarga_pdf, company, creation, modified, owner, modified_by)
            VALUES (%s, 1, 'FEL', 'https://infile.test/pdf/', '', NOW(), NOW(), 'Administrator', 'Administrator')
            """,
            (name,),
        )
