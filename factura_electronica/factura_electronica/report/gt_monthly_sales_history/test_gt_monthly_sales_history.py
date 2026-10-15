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
from datetime import date
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
    utils.getdate = lambda value=None: date(2027, 1, 1)
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

# Existing cases treat 2026 as a finished year. Incomplete-month tests pass
# their own date or patch report_today.
patch(
    "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
    "gt_monthly_sales_history.report_today",
    return_value=date(2027, 1, 1),
).start()


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
        columns, rows = execute({"company": "Acme", "year": "2026"})[:2]
        visible = [column for column in columns if not column.get("hidden")]
        self.assertEqual(
            [column["label"] for column in visible],
            [
                "Mes", "2021", "2022", "2023", "2024", "2025", "Promedio", "2026",
                "Diferencia", "% vs Promedio", "Dif. vs 2025", "% vs 2025",
            ],
        )
        self.assertEqual(len(visible), 12)
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
        })[:2]
        visible = [column["label"] for column in columns if not column.get("hidden")]
        self.assertEqual(
            visible,
            [
                "Mes", "2023", "2024", "2025", "Promedio", "2026",
                "Diferencia", "% vs Promedio", "Dif. vs 2025", "% vs 2025",
            ],
        )
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
        self.assertEqual(enero["diferencia"], -59.87)
        self.assertEqual(enero["vs_promedio"], -59.87)
        self.assertEqual(junio["diferencia"], -15.0)
        self.assertIsNone(junio["vs_promedio"])
        total = rows[-1]
        self.assertEqual(total["y_2026"], 25.13)
        self.assertEqual(total["promedio"], 100.0)
        self.assertEqual(total["diferencia"], -74.87)
        self.assertEqual(total["vs_promedio"], -74.87)

    def test_percent_is_blank_when_promedio_is_zero_and_rounds_half_up(self):
        rows = build_history(2026, [
            {"year_repo": 2025, "month_repo": 1, "total": 3},
            {"year_repo": 2026, "month_repo": 1, "total": 1},
            {"year_repo": 2026, "month_repo": 2, "total": 10},
        ], 2)
        # History window is 2024 (empty) and 2025. January Promedio is 3.
        # (1 - 3) / 3 * 100 = -66.666... -> -66.67
        enero = rows[0]
        self.assertEqual(enero["promedio"], 3.0)
        self.assertEqual(enero["y_2026"], 1.0)
        self.assertEqual(enero["diferencia"], -2.0)
        self.assertEqual(enero["vs_promedio"], -66.67)
        # February has no history invoices in a year that has data, so
        # Promedio is 0 and the percent stays blank. 10 / 3 would be wrong.
        febrero = rows[1]
        self.assertEqual(febrero["y_2026"], 10.0)
        self.assertEqual(febrero["promedio"], 0.0)
        self.assertEqual(febrero["diferencia"], 10.0)
        self.assertIsNone(febrero["vs_promedio"])
        total = rows[-1]
        self.assertEqual(total["y_2026"], 11.0)
        self.assertEqual(total["promedio"], 3.0)
        self.assertEqual(total["diferencia"], 8.0)
        # (11 - 3) / 3 * 100 = 266.666... -> 266.67, not the sum of monthly percents.
        self.assertEqual(total["vs_promedio"], 266.67)
        # Previous year is 2025, independent of the 2-year window.
        self.assertEqual(enero["dif_vs_prev"], -2.0)
        self.assertEqual(enero["pct_vs_prev"], -66.67)
        self.assertEqual(febrero["dif_vs_prev"], 10.0)
        self.assertIsNone(febrero["pct_vs_prev"])
        self.assertEqual(total["dif_vs_prev"], 8.0)
        self.assertEqual(total["pct_vs_prev"], 266.67)


class TestIncompleteMonths(TestCase):
    def test_current_month_keeps_promedio_and_blanks_comparisons(self):
        today = date(2026, 10, 15)
        rows = build_history(2026, [
            {"year_repo": 2022, "month_repo": 1, "total": 100},
            {"year_repo": 2025, "month_repo": 1, "total": 40},
            {"year_repo": 2025, "month_repo": 3, "total": 10},
            {"year_repo": 2025, "month_repo": 10, "total": 30},
            {"year_repo": 2025, "month_repo": 11, "total": 80},
            {"year_repo": 2026, "month_repo": 1, "total": 50},
            {"year_repo": 2026, "month_repo": 3, "total": 20},
            {"year_repo": 2026, "month_repo": 10, "total": 7},
            {"year_repo": 2026, "month_repo": 11, "total": 999},
        ], today=today)

        enero = rows[0]
        self.assertEqual(enero["promedio"], 70.0)
        self.assertEqual(enero["y_2026"], 50.0)
        self.assertEqual(enero["diferencia"], -20.0)
        self.assertEqual(enero["vs_promedio"], -28.57)
        self.assertEqual(enero["dif_vs_prev"], 10.0)
        self.assertEqual(enero["pct_vs_prev"], 25.0)

        marzo = rows[2]
        self.assertEqual(marzo["promedio"], 5.0)
        self.assertEqual(marzo["diferencia"], 15.0)
        self.assertEqual(marzo["vs_promedio"], 300.0)
        self.assertEqual(marzo["dif_vs_prev"], 10.0)
        self.assertEqual(marzo["pct_vs_prev"], 100.0)

        octubre = rows[9]
        self.assertEqual(octubre["mes"], "Octubre")
        self.assertEqual(octubre["promedio"], 15.0)
        self.assertEqual(octubre["y_2026"], 7.0)
        self.assertIsNone(octubre["diferencia"])
        self.assertIsNone(octubre["vs_promedio"])
        self.assertIsNone(octubre["dif_vs_prev"])
        self.assertIsNone(octubre["pct_vs_prev"])

        noviembre = rows[10]
        self.assertEqual(noviembre["y_2025"], 80.0)
        self.assertIsNone(noviembre["promedio"])
        self.assertIsNone(noviembre["y_2026"])
        self.assertIsNone(noviembre["diferencia"])
        self.assertIsNone(noviembre["vs_promedio"])
        self.assertIsNone(noviembre["dif_vs_prev"])
        self.assertIsNone(noviembre["pct_vs_prev"])

        total = rows[-1]
        # 2025 still sums all 12 months, including October and November.
        self.assertEqual(total["y_2025"], 160.0)
        # October's 7 and Promedio 15 stay on the row and out of the totals.
        # Completed months: Jan-Sep selected 70 vs Promedio 75, vs 2025's 50.
        self.assertEqual(total["y_2026"], 70.0)
        self.assertEqual(total["promedio"], 75.0)
        self.assertEqual(total["diferencia"], -5.0)
        self.assertEqual(total["vs_promedio"], -6.67)
        self.assertEqual(total["dif_vs_prev"], 20.0)
        self.assertEqual(total["pct_vs_prev"], 40.0)
        self.assertEqual(total["promedio"] + total["diferencia"], total["y_2026"])

    def test_previous_year_comparison_ignores_years_to_compare(self):
        rows = build_history(2026, [
            {"year_repo": 2023, "month_repo": 1, "total": 999},
            {"year_repo": 2025, "month_repo": 1, "total": 40},
            {"year_repo": 2026, "month_repo": 1, "total": 50},
        ], 2, today=date(2027, 1, 1))
        enero = rows[0]
        self.assertNotIn("y_2023", enero)
        self.assertEqual(enero["promedio"], 40.0)
        self.assertEqual(enero["dif_vs_prev"], 10.0)
        self.assertEqual(enero["pct_vs_prev"], 25.0)

    def test_past_year_compares_all_twelve_months(self):
        rows = build_history(2025, [
            {"year_repo": 2025, "month_repo": 12, "total": 75},
            {"year_repo": 2024, "month_repo": 12, "total": 25},
        ], today=date(2026, 10, 15))
        diciembre = rows[11]
        self.assertEqual(diciembre["y_2025"], 75.0)
        self.assertEqual(diciembre["promedio"], 25.0)
        self.assertEqual(diciembre["diferencia"], 50.0)
        self.assertEqual(diciembre["dif_vs_prev"], 50.0)
        self.assertEqual(diciembre["pct_vs_prev"], 200.0)
        total = rows[-1]
        self.assertEqual(total["y_2025"], 75.0)
        self.assertEqual(total["diferencia"], 50.0)

    def test_future_selected_year_blanks_every_month(self):
        rows = build_history(2027, [
            {"year_repo": 2027, "month_repo": 1, "total": 10},
        ], today=date(2026, 10, 15))
        self.assertTrue(all(row["promedio"] is None for row in rows[:-1]))
        self.assertTrue(all(row["y_2027"] is None for row in rows[:-1]))
        self.assertTrue(all(row["diferencia"] is None for row in rows))
        total = rows[-1]
        self.assertEqual(total["y_2027"], 0.0)
        self.assertEqual(total["promedio"], 0.0)
        self.assertIsNone(total["pct_vs_prev"])

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
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.report_today",
        return_value=date(2026, 10, 15),
    )
    def test_message_is_shown_only_for_the_current_year(self, _today, _currency, _query):
        _columns, _rows, current = execute({"company": "Acme", "year": 2026})
        self.assertIn("Octubre", current)
        self.assertIn("meses completos", current)
        self.assertIn("Totales", current)
        self.assertIn("no entra en los totales", current)
        _columns, _rows, past = execute({"company": "Acme", "year": 2025})
        self.assertIsNone(past)


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
        columns, rows = execute({"company": "Acme GT", "year": 2026})[:2]

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
            self.assertEqual(execute({})[:2], ([], []))


def round_half_up(value):
    from decimal import ROUND_HALF_UP, Decimal

    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


if __name__ == "__main__":
    main()
