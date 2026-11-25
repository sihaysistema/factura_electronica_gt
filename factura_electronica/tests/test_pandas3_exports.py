# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""pandas 3 StringDtype must not leak 'nan' into SAT exports.

No Frappe site is required.
"""

from __future__ import unicode_literals

import json
import sys
import types
import unittest


def _ensure_import_stubs():
    if "frappe" not in sys.modules:
        frappe = types.ModuleType("frappe")

        def whitelist(*args, **kwargs):
            if len(args) == 1 and callable(args[0]) and not kwargs:
                return args[0]

            def decorator(fn):
                return fn

            return decorator

        frappe.whitelist = whitelist
        frappe._ = lambda message, *args, **kwargs: message
        utils = types.ModuleType("frappe.utils")
        utils.cint = lambda value, *args, **kwargs: value
        utils.flt = lambda value, *args, **kwargs: value
        utils.get_site_name = lambda value: value
        utils.now = lambda: ""
        frappe.utils = utils
        file_manager = types.ModuleType("frappe.utils.file_manager")
        file_manager.save_file = lambda *args, **kwargs: None
        sys.modules["frappe"] = frappe
        sys.modules["frappe.utils"] = utils
        sys.modules["frappe.utils.file_manager"] = file_manager
    if "numinwords" not in sys.modules:
        numinwords = types.ModuleType("numinwords")
        numinwords.numinwords = lambda *args, **kwargs: ""
        sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

import pandas as pd  # noqa: E402
from factura_electronica.utils.utilities_facelec import (  # noqa: E402
    fill_blank_text,
    fill_numeric_zeros,
)


class TestPandas3Exports(unittest.TestCase):
    def _frame(self):
        return pd.DataFrame(
            {
                "nombre": pd.Series(["Ana", pd.NA], dtype="string"),
                "total_valor_doc": pd.Series([10.5, pd.NA], dtype="Float64"),
            }
        )

    def test_string_columns_do_not_export_nan(self):
        df = fill_blank_text(self._frame())
        self.assertEqual(df.loc[1, "nombre"], "")
        record = df.to_dict(orient="records")[1]
        line = "{0}|{1}".format(record.get("nombre"), record.get("total_valor_doc"))
        self.assertNotIn("nan", line.lower())
        self.assertNotIn("<NA>", line)
        dumped = json.dumps(df.to_dict(orient="records"), default=str)
        self.assertNotIn("nan", dumped.lower())
        self.assertNotIn("<NA>", dumped)

    def test_zero_fill_is_limited_to_numeric_columns(self):
        df = fill_numeric_zeros(self._frame())
        self.assertEqual(df.loc[1, "total_valor_doc"], 0)
        self.assertTrue(pd.isna(df.loc[1, "nombre"]))
        filled = fill_blank_text(df)
        self.assertEqual(filled.loc[1, "nombre"], "")
        self.assertNotIn("nan", json.dumps(filled.to_dict(orient="records"), default=str).lower())


if __name__ == "__main__":
    unittest.main()
