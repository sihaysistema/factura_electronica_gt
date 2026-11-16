# -*- coding: utf-8 -*-
# Copyright (c) 2026, Si Hay Sistema and contributors
# For license information, please see license.txt
"""English custom-field labels keep their fieldnames and have an es.csv line."""

from __future__ import unicode_literals

import csv
import json
import os
import unittest

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# record name, fieldname, old label, English label, Spanish
LABELS = [
    ("UOM-faceleccodigo_unidad_de_medida", "faceleccodigo_unidad_de_medida", "Codigo Unidad de Medida", "Unit of Measurement Code", "Código Unidad de Medida"),
    ("Supplier-facelec_nit_proveedor", "facelec_nit_proveedor", "NIT Proveedor", "Supplier NIT", "NIT Proveedor"),
    ("Purchase Invoice-facelec_nit_fproveedor", "facelec_nit_fproveedor", "NIT Proveedor", "Supplier NIT", "NIT Proveedor"),
    ("Purchase Receipt-facelec_nit_prproveedor", "facelec_nit_prproveedor", "NIT Proveedor", "Supplier NIT", "NIT Proveedor"),
    ("Purchase Invoice-es_factura_especial", "es_factura_especial", "Es Factura Especial", "Is Special Invoice", "Es Factura Especial"),
    ("Sales Invoice-es_nota_de_debito", "es_nota_de_debito", "Es Nota de Debito", "Is Debit Note", "Es Nota de Débito"),
    ("Sales Invoice-es_dpi", "es_dpi", "Es dpi", "Is DPI", "Es DPI"),
    ("Sales Invoice-es_pasaporte", "es_pasaporte", "Es Pasaporte", "Is Passport", "Es Pasaporte"),
    ("Sales Invoice-facelec_factura_asociada", "facelec_factura_asociada", "Factura Asociada para Nota de Debito", "Associated Invoice for Debit Note", "Factura Asociada para Nota de Débito"),
    ("Sales Invoice-serie_original_del_documento", "serie_original_del_documento", "Serie Original del Documento", "Original Document Series", "Serie Original del Documento"),
    ("Purchase Invoice-serie_original_del_documento", "serie_original_del_documento", "Serie Original Del Documento", "Original Document Series", "Serie Original del Documento"),
    ("Sales Invoice-shs_numero_resolucion", "shs_numero_resolucion", "Numero Resolucion", "Resolution Number", "Número Resolución"),
    ("Sales Invoice-numero_autorizacion_fel", "numero_autorizacion_fel", "Numero Autorizacion FEL", "FEL Authorization Number", "Número Autorización FEL"),
    ("Purchase Invoice-numero_autorizacion_fel", "numero_autorizacion_fel", "Numero Autorizacion FEL", "FEL Authorization Number", "Número Autorización FEL"),
    ("Sales Invoice-cae_factura_electronica", "cae_factura_electronica", "CAE Factura Electronica", "Electronic Invoice CAE", "CAE Factura Electrónica"),
    ("Sales Invoice-cae_nota_de_credito", "cae_nota_de_credito", "CAE Nota de Credito", "Credit Note CAE", "CAE Nota de Crédito"),
    ("Sales Invoice-cae_nota_de_debito", "cae_nota_de_debito", "CAE Nota de Debito", "Debit Note CAE", "CAE Nota de Débito"),
    ("Sales Invoice Item-shs_amount_for_back_calc", "shs_amount_for_back_calc", "Monto Para Redondeo", "Amount for Rounding", "Monto Para Redondeo"),
    ("Delivery Note Item-shs_amount_for_back_calc", "shs_amount_for_back_calc", "Monto Para Redondeo", "Amount for Rounding", "Monto Para Redondeo"),
    ("Purchase Invoice Item-shs_amount_for_back_calc", "shs_amount_for_back_calc", "Monto Para Redondeo", "Amount for Rounding", "Monto Para Redondeo"),
    ("Purchase Receipt Item-shs_amount_for_back_calc", "shs_amount_for_back_calc", "Monto Para Redondeo", "Amount for Rounding", "Monto Para Redondeo"),
    ("Supplier Quotation-shs_spq_total_iva", "shs_spq_total_iva", "Total IVA", "Total VAT", "Total IVA"),
    ("Quotation-facelec_qt_total_iva", "facelec_qt_total_iva", "Total IVA", "Total VAT", "Total IVA"),
    ("Sales Order-shs_so_total_iva", "shs_so_total_iva", "Total IVA", "Total VAT", "Total IVA"),
    ("Delivery Note-shs_dn_total_iva", "shs_dn_total_iva", "Total IVA", "Total VAT", "Total IVA"),
    ("Purchase Order-facelec_po_total_iva", "facelec_po_total_iva", "Total IVA", "Total VAT", "Total IVA"),
    ("Purchase Receipt-facelec_pr_total_iva", "facelec_pr_total_iva", "Total IVA", "Total VAT", "Total IVA"),
    ("Purchase Invoice-facelec_p_total_iva", "facelec_p_total_iva", "Total IVA", "Total VAT", "Total IVA"),
    ("Sales Invoice-shs_total_iva_fac", "shs_total_iva_fac", "Total IVA Factura", "Invoice Total VAT", "Total IVA Factura"),
    ("Customer-codigo_comprador", "codigo_comprador", "Codigo Comprador", "Buyer Code", "Código Comprador"),
    ("Customer-codigo_consignatario_comprador", "codigo_consignatario_comprador", "Codigo Consignatario Comprador", "Buyer Consignee Code", "Código Consignatario Comprador"),
    ("Company-codigo_exportador", "codigo_exportador", "Codigo Exportador", "Exporter Code", "Código Exportador"),
    ("Purchase Invoice-other_tax_facelec", "other_tax_facelec", "Otros Impuestos Tabla", "Other Taxes Table", "Otros Impuestos Tabla"),
    ("Sales Invoice-other_tax_facelec", "other_tax_facelec", "Otro Impuesto Tabla", "Other Tax Table", "Otro Impuesto Tabla"),
]


def _load_json(name):
    with open(os.path.join(_APP_ROOT, name), encoding="utf-8") as handle:
        return json.load(handle)


class TestCustomFieldLabels(unittest.TestCase):
    def test_labels_are_english_and_fieldnames_stay(self):
        rows = {row["name"]: row for row in _load_json("fixtures/custom_field.json")}
        for name, fieldname, old, english, _spanish in LABELS:
            row = rows[name]
            self.assertEqual(row["fieldname"], fieldname)
            self.assertEqual(row["label"], english)
            self.assertNotEqual(row["label"], old)
            self.assertTrue(row["modified"] >= "2026-11-16")

    def test_es_csv_has_each_english_source_once(self):
        path = os.path.join(_APP_ROOT, "translations", "es.csv")
        with open(path, encoding="utf-8", newline="") as handle:
            parsed = list(csv.reader(handle))
        sources = [row[0] for row in parsed if row]
        pairs = {(row[0], row[1]) for row in parsed if len(row) >= 2}
        expected = {(english, spanish) for _n, _f, _o, english, spanish in LABELS}
        self.assertTrue(expected <= pairs)
        for source in {english for _n, _f, _o, english, _s in LABELS}:
            self.assertEqual(sources.count(source), 1)
        self.assertNotIn("Is Exempt", sources)

    def test_exempt_translation_fixture_is_es_exenta(self):
        rows = _load_json("fixtures/translation.json")
        exempt = [row for row in rows if row.get("name") == "fb33b8c6b4"]
        question = [row for row in rows if row.get("name") == "03b0ad38c4"]
        special = [row for row in rows if row.get("source_text") == "Is Special Invoice" and row.get("language") == "es"]
        self.assertEqual(exempt[0]["translated_text"], "Es exenta")
        self.assertEqual(exempt[0]["source_text"], "Is Exempt")
        self.assertEqual(question[0]["translated_text"], "Es Excento")
        self.assertEqual(question[0]["source_text"], "Is Exempt?")
        self.assertEqual(special[0]["translated_text"], "Es Factura Especial")


if __name__ == "__main__":
    unittest.main()
