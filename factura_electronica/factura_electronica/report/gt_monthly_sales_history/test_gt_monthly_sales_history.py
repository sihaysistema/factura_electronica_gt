# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""Unit tests for GT Monthly Sales History.

They do not need a Frappe site. Month amounts are the rows
``sales_invoices_monthly`` would return; the report only pivots and rounds
them the same way GT Sales Ledger's ``calculate_total`` rounds a monthly total.
"""

from __future__ import unicode_literals

import sys
import types
from unittest import TestCase, main
from unittest.mock import patch


def _ensure_import_stubs():
    try:
        import frappe  # noqa: F401
        return
    except ImportError:
        pass

    frappe = types.ModuleType("frappe")

    def _(text, *args, **kwargs):
        return text

    def throw(message, *args, **kwargs):
        raise ValueError(message)

    def whitelist(*args, **kwargs):
        def decorator(fn):
            return fn

        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorator

    class _dict(dict):
        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                raise AttributeError(name)

        def __setattr__(self, name, value):
            self[name] = value

    frappe._ = _
    frappe.throw = throw
    frappe.whitelist = whitelist
    frappe._dict = _dict
    frappe.defaults = types.SimpleNamespace(get_user_default=lambda key=None: None)
    frappe.db = types.SimpleNamespace(
        get_value=lambda *args, **kwargs: None,
        sql=lambda *args, **kwargs: [],
    )

    utils = types.ModuleType("frappe.utils")

    def flt(value, precision=None):
        from decimal import ROUND_HALF_UP, Decimal

        if value in (None, ""):
            return 0.0
        number = float(value)
        if precision is None:
            return number
        quant = Decimal("1").scaleb(-int(precision))
        return float(Decimal(str(number)).quantize(quant, rounding=ROUND_HALF_UP))

    utils.flt = flt
    frappe.utils = utils

    numinwords = types.ModuleType("numinwords")
    numinwords.numinwords = lambda *args, **kwargs: ""

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

from factura_electronica.factura_electronica.report.gt_monthly_sales_history.gt_monthly_sales_history import (  # noqa: E402
    SPANISH_MONTHS,
    TOTAL_LABEL,
    build_history,
    execute,
    history_years,
)


class TestHistoryLayout(TestCase):
    def test_history_years_shift_with_the_selector(self):
        self.assertEqual(history_years(2026), [2021, 2022, 2023, 2024, 2025])
        self.assertEqual(history_years(2025), [2020, 2021, 2022, 2023, 2024])

    def test_years_to_compare_shortens_the_window(self):
        self.assertEqual(history_years(2026, 4), [2022, 2023, 2024, 2025])
        self.assertEqual(history_years(2026, 3), [2023, 2024, 2025])
        self.assertEqual(history_years(2026, 2), [2024, 2025])
        self.assertEqual(history_years(2025, 3), [2022, 2023, 2024])

    def test_twelve_spanish_months_and_a_total_row(self):
        rows = build_history(2026, [])
        self.assertEqual([row["mes"] for row in rows], list(SPANISH_MONTHS) + [TOTAL_LABEL])
        self.assertEqual(len(rows), 13)

    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.sales_invoices_monthly",
        return_value=[],
    )
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.company_currency",
        return_value="GTQ",
    )
    def test_column_labels_are_the_year_numbers(self, _currency, _query):
        columns, rows = execute({"company": "Acme", "year": "2026"})
        visible = [column for column in columns if not column.get("hidden")]
        self.assertEqual(
            [column["label"] for column in visible],
            ["Mes", "2021", "2022", "2023", "2024", "2025", "Promedio", "2026"],
        )
        self.assertEqual(len(visible), 8)
        self.assertEqual(len(rows), 13)
        self.assertEqual(rows[0]["y_2026"], 0.0)

    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.sales_invoices_monthly",
        return_value=[],
    )
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.company_currency",
        return_value="GTQ",
    )
    def test_column_labels_follow_years_to_compare(self, _currency, _query):
        columns, rows = execute({
            "company": "Acme",
            "year": "2026",
            "years_to_compare": "3",
        })
        visible = [column["label"] for column in columns if not column.get("hidden")]
        self.assertEqual(visible, ["Mes", "2023", "2024", "2025", "Promedio", "2026"])
        self.assertEqual(len(rows), 13)
        self.assertNotIn("y_2022", rows[0])
        self.assertEqual(rows[0]["y_2026"], 0.0)


class TestLedgerTotals(TestCase):
    def test_month_cell_matches_rounded_ledger_total(self):
        # 100.126 is the SQL SUM the monthly ledger would round to 100.13.
        rows = build_history(2026, [{
            "year_repo": 2024,
            "month_repo": 1,
            "total": "100.126",
        }])
        enero = rows[0]
        self.assertEqual(enero["mes"], "Enero")
        self.assertEqual(enero["y_2024"], 100.13)
        self.assertEqual(enero["y_2021"], 0.0)
        self.assertEqual(enero["y_2025"], 0.0)

    def test_credit_note_total_stays_negative(self):
        rows = build_history(2026, [{
            "year_repo": 2025,
            "month_repo": 6,
            "total": -40.126,
        }])
        junio = rows[5]
        self.assertEqual(junio["mes"], "Junio")
        self.assertEqual(junio["y_2025"], -40.13)

    def test_empty_year_is_excluded_from_the_average(self):
        # 2021 has no invoices at all. 2023 has invoices, but not in January.
        rows = build_history(2026, [
            {"year_repo": 2022, "month_repo": 1, "total": 100},
            {"year_repo": 2023, "month_repo": 2, "total": 10},
            {"year_repo": 2024, "month_repo": 1, "total": 200},
            {"year_repo": 2025, "month_repo": 1, "total": 300},
        ])
        enero = rows[0]
        self.assertEqual(enero["y_2021"], 0.0)
        self.assertEqual(enero["y_2023"], 0.0)
        # (100 + 0 + 200 + 300) / 4. 2021 is left out; January 2023 counts as 0.
        self.assertEqual(enero["promedio"], 150.0)

    def test_promedio_rounds_half_up_from_the_displayed_cells(self):
        # 100.10 / 4 = 25.025. Half-up keeps v13 and v15 on 25.03.
        rows = build_history(2026, [
            {"year_repo": 2022, "month_repo": 1, "total": "100.10"},
            {"year_repo": 2023, "month_repo": 2, "total": 1},
            {"year_repo": 2024, "month_repo": 2, "total": 1},
            {"year_repo": 2025, "month_repo": 2, "total": 1},
        ])
        self.assertEqual(rows[0]["promedio"], 25.03)

    def test_promedio_averages_only_the_selected_years(self):
        # 2022 is outside a 3-year window ending in 2025, so 100 is not a column.
        # 2024 has invoices, but not in January, so January counts as 0.
        rows = build_history(2026, [
            {"year_repo": 2022, "month_repo": 1, "total": 100},
            {"year_repo": 2023, "month_repo": 1, "total": 40},
            {"year_repo": 2024, "month_repo": 6, "total": 10},
            {"year_repo": 2025, "month_repo": 1, "total": 30},
        ], 3)
        enero = rows[0]
        self.assertEqual(enero["y_2023"], 40.0)
        self.assertEqual(enero["y_2024"], 0.0)
        self.assertEqual(enero["y_2025"], 30.0)
        self.assertNotIn("y_2022", enero)
        self.assertEqual(enero["promedio"], 23.33)
        total = rows[-1]
        self.assertEqual(total["y_2023"], 40.0)
        self.assertEqual(total["y_2024"], 10.0)
        self.assertEqual(total["y_2025"], 30.0)
        self.assertNotIn("y_2022", total)

    def test_empty_year_inside_a_shorter_span_is_left_out_of_the_average(self):
        rows = build_history(2026, [
            {"year_repo": 2025, "month_repo": 1, "total": 80},
        ], 2)
        enero = rows[0]
        self.assertEqual(enero["y_2024"], 0.0)
        self.assertEqual(enero["y_2025"], 80.0)
        self.assertEqual(enero["promedio"], 80.0)

    def test_all_five_years_are_averaged_when_each_has_invoices(self):
        rows = build_history(2026, [
            {"year_repo": 2021, "month_repo": 3, "total": 10},
            {"year_repo": 2022, "month_repo": 3, "total": 20},
            {"year_repo": 2023, "month_repo": 3, "total": 30},
            {"year_repo": 2024, "month_repo": 3, "total": 40},
            {"year_repo": 2025, "month_repo": 3, "total": 50},
        ])
        marzo = rows[2]
        self.assertEqual(marzo["promedio"], 30.0)

    def test_promedio_is_zero_when_no_year_has_invoices(self):
        rows = build_history(2026, [])
        self.assertTrue(all(row["promedio"] == 0.0 for row in rows))

    def test_total_row_foots_the_rounded_months(self):
        rows = build_history(2026, [
            {"year_repo": 2025, "month_repo": 1, "total": 10.126},
            {"year_repo": 2025, "month_repo": 2, "total": 5},
            {"year_repo": 2024, "month_repo": 1, "total": 1},
        ])
        total = rows[-1]
        self.assertEqual(total["mes"], "Total")
        self.assertEqual(total["y_2025"], 15.13)
        self.assertEqual(total["y_2024"], 1.0)
        self.assertEqual(
            total["promedio"],
            round_half_up(sum(row["promedio"] for row in rows[:-1])),
        )
        self.assertEqual(total["y_2026"], 0.0)

    def test_selected_year_column_is_after_promedio_and_not_averaged(self):
        rows = build_history(2026, [
            {"year_repo": 2022, "month_repo": 1, "total": 100},
            {"year_repo": 2026, "month_repo": 1, "total": "40.126"},
            {"year_repo": 2026, "month_repo": 6, "total": -15},
        ])
        enero = rows[0]
        # 2022 is the only history year with invoices, so Promedio is 100,
        # not an average that includes January 2026.
        self.assertEqual(enero["promedio"], 100.0)
        self.assertEqual(enero["y_2026"], 40.13)
        self.assertEqual(rows[1]["y_2026"], 0.0)
        junio = rows[5]
        self.assertEqual(junio["y_2026"], -15.0)
        self.assertEqual(junio["promedio"], 0.0)
        total = rows[-1]
        self.assertEqual(total["y_2026"], 25.13)


class TestExecuteUsesSalesLedgerQuery(TestCase):
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.sales_invoices_monthly",
        return_value=[{
            "year_repo": 2024,
            "month_repo": 8,
            "total": 80,
        }],
    )
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.company_currency",
        return_value="GTQ",
    )
    def test_queries_the_five_calendar_years_before_the_selector(self, _currency, query):
        columns, rows = execute({"company": "Acme GT", "year": 2026})

        query.assert_called_once()
        filters = query.call_args[0][0]
        self.assertEqual(filters.company, "Acme GT")
        self.assertEqual(filters.company_currency, "GTQ")
        self.assertEqual(filters.from_date, "2021-01-01")
        self.assertEqual(filters.to_date, "2026-12-31")
        self.assertNotIn("customer", filters)

        agosto = rows[7]
        self.assertEqual(agosto["mes"], "Agosto")
        self.assertEqual(agosto["y_2024"], 80.0)
        self.assertEqual(agosto["currency"], "GTQ")
        self.assertEqual(columns[-1]["fieldname"], "currency")
        self.assertEqual(columns[-1]["hidden"], 1)

    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.sales_invoices_monthly",
        return_value=[],
    )
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.company_currency",
        return_value="GTQ",
    )
    def test_query_range_follows_years_to_compare(self, _currency, query):
        cases = (
            ("4", "2022-01-01", "2026-12-31"),
            ("3", "2023-01-01", "2026-12-31"),
            (2, "2024-01-01", "2026-12-31"),
        )
        for span, start, end in cases:
            execute({"company": "Acme GT", "year": 2026, "years_to_compare": span})
            filters = query.call_args[0][0]
            self.assertEqual(filters.from_date, start)
            self.assertEqual(filters.to_date, end)

    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.sales_invoices_monthly",
        return_value=[],
    )
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.default_company",
        return_value="Default Co",
    )
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.company_currency",
        return_value="GTQ",
    )
    def test_company_falls_back_to_the_user_default(self, _currency, _default_company, query):
        execute({"year": 2025})
        filters = query.call_args[0][0]
        self.assertEqual(filters.company, "Default Co")
        self.assertEqual(filters.from_date, "2020-01-01")
        self.assertEqual(filters.to_date, "2025-12-31")

    def test_invalid_year_is_rejected(self):
        with self.assertRaises(Exception):
            execute({"company": "Acme", "year": "nope"})

    def test_invalid_years_to_compare_is_rejected(self):
        for value in ("1", "6", "nope", 0):
            with self.assertRaises(Exception):
                execute({"company": "Acme", "year": 2026, "years_to_compare": value})

    def test_missing_company_returns_nothing(self):
        with patch(
            "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
            "gt_monthly_sales_history.default_company",
            return_value=None,
        ):
            self.assertEqual(execute({}), ([], []))


def round_half_up(value):
    from decimal import ROUND_HALF_UP, Decimal

    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


if __name__ == "__main__":
    main()
