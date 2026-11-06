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
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
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
    CONSERVATIVE_FIELD,
    TREND_FIELD,
    SPANISH_MONTHS,
    TOTAL_LABEL,
    build_history,
    build_year_projection,
    conservative_day_parts,
    elapsed_days,
    execute,
    guatemala_today,
    history_years,
    month_forecast_days,
    remaining_days,
    report_today as unpatched_report_today,
    round_money,
    sales_invoices_by_day,
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
                "With the trend", "Conservative",
            ],
        )
        self.assertEqual(len(visible), 14)
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
                "With the trend", "Conservative",
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
        self.assertIn("31 de diciembre", current)
        self.assertIn("pronóstico", current)
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


class TestProjections(TestCase):
    def test_guatemala_date_lags_utc_in_the_evening(self):
        utc = timezone(timedelta(hours=0))
        # 02:00 UTC on 7 Nov is still 20:00 on 6 Nov in Guatemala.
        self.assertEqual(
            guatemala_today(datetime(2026, 11, 7, 2, 0, tzinfo=utc)),
            date(2026, 11, 6),
        )
        # 05:30 UTC is 23:30 the previous evening.
        self.assertEqual(
            guatemala_today(datetime(2026, 11, 6, 5, 30, tzinfo=utc)),
            date(2026, 11, 5),
        )
        # The Guatemala day starts at 06:00 UTC.
        self.assertEqual(
            guatemala_today(datetime(2026, 11, 6, 6, 0, tzinfo=utc)),
            date(2026, 11, 6),
        )

    def test_report_today_uses_the_guatemala_calendar(self):
        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                base = datetime(2026, 11, 7, 2, 0, tzinfo=timezone.utc)
                if tz is not None:
                    return base.astimezone(tz)
                return base

        with patch(
            "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
            "gt_monthly_sales_history.datetime",
            FixedDatetime,
        ):
            self.assertEqual(unpatched_report_today(), date(2026, 11, 6))

    def test_cutoff_excludes_today_and_future_posting_dates(self):
        today = date(2026, 3, 15)
        yesterday = date(2026, 3, 14)
        daily = each_day(2026, date(2026, 1, 1), yesterday, 10)
        # Today's 999 and a later posting date must not become actuals.
        daily.append(day_row(2026, date(2026, 3, 15), 999))
        daily.append(day_row(2026, date(2026, 3, 20), 500))
        daily.append(day_row(2026, date(2026, 11, 1), 999))
        ledger = [
            {"year_repo": 2025, "month_repo": 1, "total": 40},
            {"year_repo": 2026, "month_repo": 1, "total": 310},
            {"year_repo": 2026, "month_repo": 2, "total": 280},
            # Monthly March includes today and the future posting date.
            {"year_repo": 2026, "month_repo": 3, "total": 1639},
            {"year_repo": 2026, "month_repo": 11, "total": 999},
        ]
        rows = build_history(2026, ledger, today=today, daily_rows=daily)
        enero, febrero, marzo = rows[0], rows[1], rows[2]
        noviembre = rows[10]
        total = rows[-1]

        # The existing actual column is unchanged, including today's invoices.
        self.assertEqual(enero["y_2026"], 310.0)
        self.assertEqual(enero["promedio"], 40.0)
        self.assertEqual(enero["diferencia"], 270.0)
        self.assertEqual(marzo["y_2026"], 1639.0)
        self.assertIsNone(marzo["diferencia"])
        self.assertIsNone(noviembre["y_2026"])
        self.assertEqual(total["y_2026"], 590.0)

        # Finished months keep that actual. March replaces today onward.
        self.assertEqual(enero[TREND_FIELD], 310.0)
        self.assertEqual(febrero[TREND_FIELD], 280.0)
        self.assertEqual(marzo[TREND_FIELD], 310.0)
        self.assertEqual(rows[3][TREND_FIELD], 300.0)
        self.assertEqual(noviembre[TREND_FIELD], 300.0)
        self.assertEqual(rows[11][TREND_FIELD], 310.0)
        self.assertEqual(total[TREND_FIELD], 3650.0)
        self.assertEqual(
            total[TREND_FIELD],
            round_money(sum(Decimal(str(row[TREND_FIELD])) for row in rows[:-1])),
        )
        # No history on the pending days, so conservative adds nothing.
        self.assertEqual(marzo[CONSERVATIVE_FIELD], 140.0)
        self.assertEqual(noviembre[CONSERVATIVE_FIELD], 0.0)
        self.assertEqual(total[CONSERVATIVE_FIELD], 730.0)
        self.assertNotEqual(total[TREND_FIELD], total["y_2026"])

        info = build_year_projection(
            2026, today, history_years(2026), {2025, 2026},
            {(2026, 1): 310, (2026, 2): 280, (2026, 3): 1639, (2026, 11): 999,
             (2025, 1): 40},
            daily,
        )
        self.assertEqual(info["elapsed_days"], 73)
        self.assertEqual(info["remaining_days"], 292)
        self.assertEqual(info["ytd_actual"], Decimal("730"))
        self.assertEqual(info["daily_rate"], Decimal("10"))
        exact = sum((month["trend_exact"] for month in info["months"]), Decimal("0"))
        self.assertEqual(
            exact,
            info["ytd_actual"] + info["daily_rate"] * info["remaining_days"],
        )
        conservative_exact = sum(
            (month["conservative_exact"] for month in info["months"]), Decimal("0")
        )
        self.assertEqual(conservative_exact, Decimal("730"))

    def test_years_to_compare_changes_conservative_only(self):
        today = date(2026, 12, 31)
        # No elapsed-day sales, so the trend rate is zero for every span.
        # Today's 999 is the whole December ledger cell and must stay out.
        daily = [day_row(2026, today, 999)]
        history_amounts = {2021: 50, 2022: 40, 2023: 30, 2024: 20, 2025: 10}
        for year, amount in history_amounts.items():
            daily.append(day_row(year, date(year, 12, 31), amount))
        ledger = [{"year_repo": year, "month_repo": 1, "total": 1} for year in history_amounts]
        ledger.append({"year_repo": 2026, "month_repo": 12, "total": 999})

        expected = {5: 30.0, 4: 25.0, 3: 20.0, 2: 15.0}
        trend_totals = set()
        for span, average in expected.items():
            rows = build_history(
                2026, ledger, span, today=today, daily_rows=daily
            )
            diciembre = rows[11]
            total = rows[-1]
            self.assertEqual(diciembre["y_2026"], 999.0)
            self.assertEqual(diciembre[TREND_FIELD], 0.0)
            self.assertEqual(diciembre[CONSERVATIVE_FIELD], average)
            self.assertEqual(total[TREND_FIELD], 0.0)
            self.assertEqual(total[CONSERVATIVE_FIELD], average)
            self.assertEqual(
                total[CONSERVATIVE_FIELD],
                round_money(sum(Decimal(str(row[CONSERVATIVE_FIELD])) for row in rows[:-1])),
            )
            trend_totals.add(total[TREND_FIELD])
            self.assertNotIn("y_{0}".format(2026 - span - 1), rows[0])
        self.assertEqual(trend_totals, {0.0})

    def test_january_first_leaves_the_trend_blank(self):
        today = date(2026, 1, 1)
        daily = [
            day_row(2026, today, 500),
            day_row(2025, date(2025, 1, 1), 10),
        ]
        ledger = [
            {"year_repo": 2024, "month_repo": 6, "total": 1},
            {"year_repo": 2025, "month_repo": 6, "total": 1},
            {"year_repo": 2026, "month_repo": 1, "total": 500},
        ]
        rows = build_history(2026, ledger, 2, today=today, daily_rows=daily)
        self.assertEqual(rows[0]["y_2026"], 500.0)
        self.assertTrue(all(row[TREND_FIELD] is None for row in rows))
        # Jan 1 is 10 and 0 across the two covered years. Later days are 0.
        self.assertEqual(rows[0][CONSERVATIVE_FIELD], 5.0)
        self.assertEqual(rows[-1][CONSERVATIVE_FIELD], 5.0)
        self.assertEqual(rows[-1]["y_2026"], 0.0)

        info = build_year_projection(
            2026, today, history_years(2026, 2), {2024, 2025, 2026}, {}, daily
        )
        self.assertEqual(info["elapsed_days"], 0)
        self.assertIsNone(info["daily_rate"])
        self.assertEqual(info["ytd_actual"], Decimal("0"))
        self.assertEqual(info["remaining_days"], 365)

    def test_leap_day_is_a_real_trend_day_and_a_narrow_history_day(self):
        self.assertEqual(elapsed_days(2024, date(2024, 3, 1)), 60)
        self.assertEqual(elapsed_days(2025, date(2025, 3, 1)), 59)
        self.assertEqual(elapsed_days(2026, date(2026, 1, 1)), 0)
        self.assertEqual(remaining_days(2024, date(2024, 1, 1)), 366)
        self.assertEqual(remaining_days(2026, date(2026, 1, 1)), 365)
        self.assertEqual(month_forecast_days(2024, 2, date(2024, 2, 1)), 29)
        self.assertEqual(month_forecast_days(2025, 2, date(2025, 2, 1)), 28)

        # Feb 29 contributes its own sales and its own calendar day.
        today = date(2024, 3, 1)
        daily = each_day(2024, date(2024, 1, 1), date(2024, 2, 28), 10)
        daily.append(day_row(2024, date(2024, 2, 29), 70))
        ledger = [
            {"year_repo": 2024, "month_repo": 1, "total": 310},
            {"year_repo": 2024, "month_repo": 2, "total": 350},
        ]
        rows = build_history(2024, ledger, today=today, daily_rows=daily)
        self.assertEqual(rows[1][TREND_FIELD], 350.0)
        self.assertEqual(rows[2][TREND_FIELD], 341.0)
        info = build_year_projection(
            2024, today, history_years(2024), {2024},
            {(2024, 1): 310, (2024, 2): 350}, daily,
        )
        self.assertEqual(info["elapsed_days"], 60)
        self.assertEqual(info["ytd_actual"], Decimal("660"))
        self.assertEqual(info["daily_rate"], Decimal("11"))

        # On the leap day itself the 29th is forecast, not actual.
        on_leap = date(2024, 2, 29)
        pace = each_day(2024, date(2024, 1, 1), date(2024, 2, 28), 10)
        pace.append(day_row(2024, on_leap, 999))
        leap_rows = build_history(2024, [
            {"year_repo": 2024, "month_repo": 1, "total": 310},
            {"year_repo": 2024, "month_repo": 2, "total": 280 + 999},
        ], today=on_leap, daily_rows=pace)
        self.assertEqual(leap_rows[1]["y_2024"], 1279.0)
        self.assertEqual(leap_rows[1][TREND_FIELD], 290.0)
        self.assertEqual(elapsed_days(2024, on_leap), 59)

        # 2025 has no Feb 29. The last day of February is only the 28th.
        non_leap = date(2025, 2, 28)
        non_leap_rows = build_history(2025, [
            {"year_repo": 2025, "month_repo": 1, "total": 310},
            {"year_repo": 2025, "month_repo": 2, "total": 270},
        ], today=non_leap, daily_rows=each_day(2025, date(2025, 1, 1), date(2025, 2, 27), 10))
        self.assertEqual(non_leap_rows[1][TREND_FIELD], 280.0)
        self.assertEqual(elapsed_days(2025, non_leap), 58)

    def test_leap_day_history_ignores_years_where_it_did_not_exist(self):
        today = date(2028, 2, 29)
        # 2023..2027. Only 2024 has a February 29.
        years = [2023, 2024, 2025, 2026, 2027]
        ledger = [{"year_repo": year, "month_repo": 1, "total": 1} for year in years]
        daily = [day_row(2024, date(2024, 2, 29), 100)]
        covered = set(years)
        index_years = history_years(2028, 5)
        amount, observations = conservative_day_parts(2, 29, index_years, covered, {
            (2024, 2, 29): Decimal("100"),
        })
        self.assertEqual(observations, 1)
        self.assertEqual(amount, Decimal("100"))

        rows = build_history(2028, ledger, 5, today=today, daily_rows=daily)
        # Dividing by all five years would show 20. Non-leap years are not zeros.
        self.assertEqual(rows[1][CONSERVATIVE_FIELD], 100.0)

        short = history_years(2028, 2)
        amount, observations = conservative_day_parts(2, 29, short, covered, {
            (2024, 2, 29): Decimal("100"),
        })
        self.assertEqual((amount, observations), (Decimal("0"), 0))
        short_rows = build_history(2028, ledger, 2, today=today, daily_rows=daily)
        self.assertEqual(short_rows[1][CONSERVATIVE_FIELD], 0.0)

        # A covered leap year with no invoice that day is a zero, one observation.
        amount, observations = conservative_day_parts(2, 29, index_years, covered, {})
        self.assertEqual((amount, observations), (Decimal("0"), 1))

        # The leap year itself has no invoices, so it is not coverage.
        uncovered = set(years) - {2024}
        amount, observations = conservative_day_parts(
            2, 29, index_years, uncovered, {(2024, 2, 29): Decimal("100")}
        )
        self.assertEqual((amount, observations), (Decimal("0"), 0))

    def test_zero_sale_stays_in_the_denominator_and_a_missing_year_does_not(self):
        today = date(2026, 4, 10)
        # 2023 = 30, 2024 = no invoice (zero), 2025 = no year at all.
        ledger = [
            {"year_repo": 2023, "month_repo": 1, "total": 1},
            {"year_repo": 2024, "month_repo": 1, "total": 1},
        ]
        daily = [day_row(2023, date(2023, 4, 10), 30)]
        years = history_years(2026, 3)
        covered = {2023, 2024}
        amount, observations = conservative_day_parts(4, 10, years, covered, {
            (2023, 4, 10): Decimal("30"),
        })
        self.assertEqual(observations, 2)
        self.assertEqual(amount, Decimal("15"))

        rows = build_history(2026, ledger, 3, today=today, daily_rows=daily)
        self.assertEqual(rows[3][CONSERVATIVE_FIELD], 15.0)
        self.assertEqual(rows[-1][CONSERVATIVE_FIELD], 15.0)

        # A year whose invoices net to zero still counts as coverage.
        ledger.append({"year_repo": 2022, "month_repo": 3, "total": 0})
        # Span 5 reaches 2021..2025. 2021 is absent. 2022 is present and zero
        # on April 10. Average of 2022 (0), 2023 (30), 2024 (0) is 10, not 15
        # and not 30/4.
        wider = build_history(2026, ledger, 5, today=today, daily_rows=daily)
        self.assertEqual(wider[3][CONSERVATIVE_FIELD], 10.0)

    def test_returns_make_a_negative_rate_and_a_negative_day_average(self):
        today = date(2026, 2, 1)
        daily = each_day(2026, date(2026, 1, 1), date(2026, 1, 31), -5)
        daily.append(day_row(2026, today, -999))
        daily.append(day_row(2025, date(2025, 2, 1), -80))
        daily.append(day_row(2024, date(2024, 2, 1), -40))
        ledger = [
            {"year_repo": 2024, "month_repo": 1, "total": 1},
            {"year_repo": 2025, "month_repo": 1, "total": 1},
            {"year_repo": 2026, "month_repo": 1, "total": -155},
            {"year_repo": 2026, "month_repo": 2, "total": -999},
        ]
        rows = build_history(2026, ledger, 2, today=today, daily_rows=daily)
        self.assertEqual(rows[0][TREND_FIELD], -155.0)
        self.assertEqual(rows[1]["y_2026"], -999.0)
        self.assertEqual(rows[1][TREND_FIELD], -140.0)
        self.assertEqual(rows[1][CONSERVATIVE_FIELD], -60.0)
        self.assertEqual(rows[-1][TREND_FIELD], -1825.0)
        info = build_year_projection(
            2026, today, history_years(2026, 2), {2024, 2025, 2026},
            {(2026, 1): -155, (2026, 2): -999, (2024, 1): 1, (2025, 1): 1},
            daily,
        )
        self.assertEqual(info["daily_rate"], Decimal("-5"))
        self.assertLess(info["daily_rate"], 0)

    def test_calendar_days_stay_in_the_trend_denominator_when_there_was_no_sale(self):
        today = date(2026, 2, 1)
        # One invoice in the whole elapsed month. The other 30 days still count.
        daily = [day_row(2026, date(2026, 1, 31), "10.01")]
        ledger = [{"year_repo": 2026, "month_repo": 1, "total": "10.01"}]
        rows = build_history(2026, ledger, today=today, daily_rows=daily)
        info = build_year_projection(
            2026, today, history_years(2026), {2026}, {(2026, 1): Decimal("10.01")}, daily
        )
        self.assertEqual(info["elapsed_days"], 31)
        self.assertEqual(info["ytd_actual"], Decimal("10.01"))
        self.assertEqual(info["daily_rate"], Decimal("10.01") / Decimal(31))
        self.assertEqual(rows[0][TREND_FIELD], 10.01)
        self.assertEqual(rows[-1][TREND_FIELD], 117.87)
        exact = sum((month["trend_exact"] for month in info["months"]), Decimal("0"))
        self.assertEqual(
            exact,
            info["ytd_actual"] + info["daily_rate"] * info["remaining_days"],
        )
        # The footer sums rounded months. Rounding the exact year once is 117.86.
        self.assertEqual(round_money(exact), 117.86)
        self.assertNotEqual(rows[-1][TREND_FIELD], round_money(exact))
        self.assertEqual(
            rows[-1][TREND_FIELD],
            round_money(sum(Decimal(str(row[TREND_FIELD])) for row in rows[:-1])),
        )

    def test_tax_inclusive_company_amount_is_the_whole_grand_total(self):
        today = date(2026, 3, 2)
        # 112 is 100 plus tax. The projection does not strip the tax back out.
        daily = [day_row(2026, date(2026, 3, 1), "112.00")]
        daily.append(day_row(2026, today, "50.00"))
        info = build_year_projection(
            2026, today, history_years(2026), set(), {}, daily
        )
        self.assertEqual(info["ytd_actual"], Decimal("112.00"))
        self.assertNotEqual(info["ytd_actual"], Decimal("100"))
        march = info["months"][2]
        self.assertEqual(
            march["trend_exact"],
            Decimal("112.00") + info["daily_rate"] * 30,
        )

    def test_closed_year_repeats_actuals_and_a_future_year_stays_blank(self):
        ledger = [
            {"year_repo": 2024, "month_repo": 1, "total": 10},
            {"year_repo": 2024, "month_repo": 6, "total": -15.126},
        ]
        rows = build_history(
            2024, ledger, today=date(2026, 5, 1),
            daily_rows=[day_row(2024, date(2024, 6, 1), 999999)],
        )
        junio = rows[5]
        total = rows[-1]
        self.assertEqual(junio["y_2024"], -15.13)
        self.assertEqual(junio[TREND_FIELD], -15.13)
        self.assertEqual(junio[CONSERVATIVE_FIELD], -15.13)
        self.assertEqual(total[TREND_FIELD], total["y_2024"])
        self.assertEqual(total[CONSERVATIVE_FIELD], total["y_2024"])
        self.assertEqual(total["y_2024"], -5.13)

        future = build_history(2027, [
            {"year_repo": 2027, "month_repo": 1, "total": 10},
        ], today=date(2026, 10, 15))
        self.assertTrue(all(row[TREND_FIELD] is None for row in future))
        self.assertTrue(all(row[CONSERVATIVE_FIELD] is None for row in future))
        self.assertEqual(future[-1]["y_2027"], 0.0)

    def test_duplicate_day_rows_are_summed_before_the_rate(self):
        today = date(2026, 1, 3)
        daily = [
            day_row(2026, date(2026, 1, 1), 40),
            day_row(2026, date(2026, 1, 1), 60),
            day_row(2026, date(2026, 1, 2), -10),
        ]
        info = build_year_projection(2026, today, history_years(2026), set(), {}, daily)
        self.assertEqual(info["ytd_actual"], Decimal("90"))
        self.assertEqual(info["elapsed_days"], 2)
        self.assertEqual(info["daily_rate"], Decimal("45"))

    def test_open_year_uses_one_parameterized_day_query(self):
        captured = {}

        def fake_sql(query, params=None, *args, **kwargs):
            captured["query"] = query
            captured["params"] = params
            captured["kwargs"] = kwargs
            captured["calls"] = captured.get("calls", 0) + 1
            return []

        with patch(
            "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
            "gt_monthly_sales_history.frappe.db.sql",
            fake_sql,
        ):
            sales_invoices_by_day(
                "O'Brien GT", "2021-01-01", "2026-12-31", 2026, date(2026, 3, 15)
            )

        query = captured["query"]
        params = captured["params"]
        self.assertEqual(captured["calls"], 1)
        self.assertEqual(params["company"], "O'Brien GT")
        self.assertNotIn("O'Brien", query)
        self.assertNotIn("2026-03-15", query)
        self.assertIn("SUM(SI.grand_total * SI.conversion_rate)", query)
        self.assertNotIn("net_total", query)
        self.assertNotIn("base_grand_total", query)
        self.assertNotIn("is_return", query)
        self.assertIn("SI.docstatus = 1", query)
        self.assertIn("SI.posting_date < %(today)s", query)
        self.assertIn("GROUP BY year_repo, month_repo, day_repo", query)
        self.assertEqual(params["today"], "2026-03-15")
        self.assertEqual(params["year_start"], "2026-01-01")
        self.assertEqual(params["month"], 3)
        self.assertEqual(params["day"], 15)
        self.assertEqual(captured["kwargs"].get("as_dict"), True)

    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.sales_invoices_by_day",
        return_value=[],
    )
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.sales_invoices_monthly",
        return_value=[{
            "year_repo": 2026,
            "month_repo": 1,
            "total": "112.50",
        }],
    )
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.company_currency",
        return_value="USD",
    )
    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.report_today",
        return_value=date(2026, 6, 15),
    )
    def test_execute_scopes_one_day_query_to_the_company(self, _today, _currency, monthly, daily):
        columns, rows, message = execute({
            "company": "Compania GT",
            "year": 2026,
            "years_to_compare": "4",
        })
        self.assertEqual(daily.call_count, 1)
        company, start, end, year, today = daily.call_args[0]
        self.assertEqual(company, "Compania GT")
        self.assertEqual(start, "2022-01-01")
        self.assertEqual(end, "2026-12-31")
        self.assertEqual(year, 2026)
        self.assertEqual(today, date(2026, 6, 15))
        monthly_filters = monthly.call_args[0][0]
        self.assertEqual(monthly_filters.company, "Compania GT")
        self.assertEqual(monthly_filters.company_currency, "USD")
        self.assertEqual(monthly_filters.from_date, "2022-01-01")
        self.assertEqual(rows[0]["currency"], "USD")
        self.assertEqual(rows[0]["y_2026"], 112.5)
        self.assertIn("pronóstico", message)
        labels = [column["label"] for column in columns if not column.get("hidden")]
        self.assertEqual(labels[-2:], ["With the trend", "Conservative"])
        self.assertEqual(columns[-1]["fieldname"], "currency")

    @patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.sales_invoices_by_day",
        side_effect=AssertionError("closed and future years do not need a day query"),
    )
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
    def test_closed_and_future_years_do_not_query_days(self, _currency, _monthly, daily):
        with patch(
            "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
            "gt_monthly_sales_history.report_today",
            return_value=date(2026, 6, 15),
        ):
            past_columns, past_rows = execute({"company": "Acme GT", "year": 2025})[:2]
            future_columns, future_rows = execute({"company": "Acme GT", "year": 2027})[:2]
        self.assertEqual(daily.call_count, 0)
        self.assertEqual(past_rows[0][TREND_FIELD], 0.0)
        self.assertEqual(past_rows[-1][CONSERVATIVE_FIELD], past_rows[-1]["y_2025"])
        self.assertIsNone(future_rows[0][TREND_FIELD])
        self.assertIsNone(future_rows[-1][CONSERVATIVE_FIELD])
        self.assertEqual(
            [column["fieldname"] for column in past_columns if column["fieldname"] in (
                TREND_FIELD, CONSERVATIVE_FIELD
            )],
            [TREND_FIELD, CONSERVATIVE_FIELD],
        )
        self.assertEqual(
            [column["fieldname"] for column in future_columns if column["fieldname"] in (
                TREND_FIELD, CONSERVATIVE_FIELD
            )],
            [TREND_FIELD, CONSERVATIVE_FIELD],
        )


def each_day(year, start, end, amount):
    rows = []
    day = start
    while day <= end:
        rows.append(day_row(year, day, amount))
        day += timedelta(days=1)
    return rows


def day_row(year, posted, amount):
    return {
        "year_repo": year,
        "month_repo": posted.month,
        "day_repo": posted.day,
        "total": amount,
    }


def round_half_up(value):
    from decimal import ROUND_HALF_UP, Decimal

    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


if __name__ == "__main__":
    main()
