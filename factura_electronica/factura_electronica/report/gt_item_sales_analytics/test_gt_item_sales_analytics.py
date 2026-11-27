# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""Unit tests for the item sales engine, GT Item Sales History and
GT Item Sales Analytics. No Frappe site needed: SQL results are faked.

Run::

    PYTHONPATH=. python3 \\
        factura_electronica/factura_electronica/report/gt_item_sales_analytics/test_gt_item_sales_analytics.py
"""

from __future__ import unicode_literals

import sys
import types
from datetime import date
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

    class _dict(dict):
        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                raise AttributeError(name)

        def __setattr__(self, name, value):
            self[name] = value

    def throw(message, *args, **kwargs):
        raise ValueError(message)

    frappe._ = lambda text, *args, **kwargs: text
    frappe._dict = _dict
    frappe.throw = throw
    frappe.whitelist = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda fn: fn))
    frappe.defaults = types.SimpleNamespace(get_user_default=lambda key=None: None)
    frappe.db = types.SimpleNamespace(
        get_value=lambda *args, **kwargs: None,
        sql=lambda *args, **kwargs: [],
    )

    utils = types.ModuleType("frappe.utils")

    def flt(value, precision=None):
        from decimal import ROUND_HALF_UP

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
    sys.modules.setdefault("numinwords", numinwords)


_ensure_import_stubs()

import frappe  # noqa: E402

from factura_electronica.utils import item_sales_analytics as engine  # noqa: E402
from factura_electronica.factura_electronica.report.gt_item_sales_history import (  # noqa: E402
    gt_item_sales_history as history,
)
from factura_electronica.factura_electronica.report.gt_item_sales_analytics import (  # noqa: E402
    gt_item_sales_analytics as analytics,
)

ENGINE = "factura_electronica.utils.item_sales_analytics."


def row(item, year, period, qty, amount=None, name=None, group="G1"):
    return {
        "item_code": item,
        "item_name": name or item,
        "item_group": group,
        "year": year,
        "period": period,
        "qty": qty,
        "amount": amount if amount is not None else qty * 10,
    }


class TestCalendar(TestCase):
    def test_iso_53_week_years(self):
        self.assertEqual(engine.iso_weeks_in_year(2020), 53)
        self.assertEqual(engine.iso_weeks_in_year(2026), 53)
        self.assertEqual(engine.iso_weeks_in_year(2025), 52)
        self.assertEqual(engine.iso_weeks_in_year(2021), 52)

    def test_iso_week_bounds_cross_the_calendar_year(self):
        self.assertEqual(engine.period_bounds("Weekly", 2026, 1),
                         (date(2025, 12, 29), date(2026, 1, 4)))
        self.assertEqual(engine.period_bounds("Weekly", 2026, 53),
                         (date(2026, 12, 28), date(2027, 1, 3)))
        self.assertEqual(engine.year_bounds("Weekly", 2021),
                         (date(2021, 1, 4), date(2022, 1, 2)))

    def test_month_and_quarter_bounds(self):
        self.assertEqual(engine.period_bounds("Monthly", 2024, 2),
                         (date(2024, 2, 1), date(2024, 2, 29)))
        self.assertEqual(engine.period_bounds("Quarterly", 2026, 4),
                         (date(2026, 10, 1), date(2026, 12, 31)))
        self.assertEqual(engine.year_bounds("Monthly", 2026),
                         (date(2026, 1, 1), date(2026, 12, 31)))

    def test_current_period_uses_iso_year_for_weeks(self):
        self.assertEqual(engine.current_period("Weekly", date(2027, 1, 1)), (2026, 53))
        self.assertEqual(engine.current_period("Weekly", date(2026, 11, 27)), (2026, 48))
        self.assertEqual(engine.current_period("Monthly", date(2026, 11, 27)), (2026, 11))
        self.assertEqual(engine.current_period("Quarterly", date(2026, 11, 27)), (2026, 4))

    def test_period_state(self):
        today = date(2026, 11, 27)
        self.assertEqual(engine.period_state("Monthly", 2026, 10, today), engine.COMPLETE)
        self.assertEqual(engine.period_state("Monthly", 2026, 11, today), engine.CURRENT)
        self.assertEqual(engine.period_state("Monthly", 2026, 12, today), engine.FUTURE)
        self.assertEqual(engine.period_state("Monthly", 2025, 12, today), engine.COMPLETE)
        self.assertEqual(engine.period_state("Weekly", 2026, 48, today), engine.CURRENT)

    def test_parse_period_defaults_and_limits(self):
        today = date(2026, 11, 27)
        self.assertEqual(engine.parse_period("", "Monthly", 2026, today), 11)
        self.assertEqual(engine.parse_period(None, "Monthly", 2025, today), 12)
        self.assertEqual(engine.parse_period(None, "Weekly", 2020, today), 53)
        self.assertEqual(engine.parse_period(None, "Monthly", 2027, today), 1)
        self.assertEqual(engine.parse_period("53", "Weekly", 2026, today), 53)
        with self.assertRaises(ValueError):
            engine.parse_period("53", "Weekly", 2025, today)
        with self.assertRaises(ValueError):
            engine.parse_period("13", "Monthly", 2025, today)

    def test_filter_parsers(self):
        self.assertEqual(engine.parse_metric(None), "Units")
        self.assertEqual(engine.parse_period_type(None), "Monthly")
        with self.assertRaises(ValueError):
            engine.parse_metric("Weight")
        with self.assertRaises(ValueError):
            engine.parse_period_type("Daily")
        with self.assertRaises(ValueError):
            engine.parse_years_to_compare("7")
        self.assertFalse(engine.parse_check("0"))
        self.assertTrue(engine.parse_check(1))
        self.assertEqual(engine.history_years(2026, 3), [2023, 2024, 2025])

    def test_labels(self):
        self.assertEqual(engine.period_label("Weekly", 5, 2026), "W05 2026")
        self.assertEqual(engine.period_label("Monthly", 11, 2025), "Nov 2025")
        self.assertEqual(engine.period_label("Quarterly", 4), "Q4")
        self.assertEqual(engine.period_name("Monthly", 1), "January")


class TestAverages(TestCase):
    def test_uncovered_year_is_left_out_but_zero_counts(self):
        values = {(2021, 1): Decimal("10"), (2023, 1): Decimal("20")}
        covered = {2021, 2022, 2023}
        # 2022 covered with no sales = 0; 2020 not covered.
        self.assertEqual(engine.average_for(values, "Monthly", [2020, 2021, 2022, 2023], covered, 1), 10.0)

    def test_no_covered_year_is_blank(self):
        self.assertIsNone(engine.average_for({}, "Monthly", [2024, 2025], set(), 1))

    def test_week_53_only_uses_years_with_week_53(self):
        values = {(2020, 53): Decimal("9"), (2021, 52): Decimal("5")}
        covered = {2020, 2021, 2022, 2023, 2024, 2025}
        self.assertEqual(engine.average_for(values, "Weekly", [2020, 2021], covered, 53), 9.0)
        self.assertIsNone(engine.average_for(values, "Weekly", [2021, 2022, 2023, 2024, 2025], covered, 53))

    def test_last_year_week_53(self):
        values = {(2025, 52): Decimal("4")}
        self.assertIsNone(engine.last_year_value(values, "Weekly", 2026, 53))
        self.assertEqual(engine.last_year_value(values, "Weekly", 2026, 52), 4.0)
        self.assertEqual(engine.last_year_value(values, "Monthly", 2026, 3), 0.0)

    def test_rounding_half_up(self):
        self.assertEqual(engine.round_value(Decimal("1.005")), 1.01)
        self.assertEqual(engine.average_for({(2024, 1): Decimal("1"), (2025, 1): Decimal("2")},
                                            "Monthly", [2024, 2025], {2024, 2025}, 1), 1.5)


class TestComparisons(TestCase):
    def test_complete_period_shows_losses(self):
        cells = engine.comparison_cells(80, 100, 90, engine.COMPLETE)
        self.assertEqual(cells, {"diferencia": -20.0, "vs_promedio": -20.0,
                                 "dif_vs_prev": -10.0, "pct_vs_prev": -11.11})

    def test_open_period_below_or_equal_is_blank(self):
        blank = {"diferencia": None, "vs_promedio": None, "dif_vs_prev": None, "pct_vs_prev": None}
        self.assertEqual(engine.comparison_cells(80, 100, 90, engine.CURRENT), blank)
        self.assertEqual(engine.comparison_cells(100, 100, 100, engine.CURRENT), blank)

    def test_open_period_each_pair_on_its_own(self):
        cells = engine.comparison_cells(95, 100, 90, engine.CURRENT)
        self.assertIsNone(cells["diferencia"])
        self.assertIsNone(cells["vs_promedio"])
        self.assertEqual(cells["dif_vs_prev"], 5.0)
        self.assertEqual(cells["pct_vs_prev"], 5.56)

    def test_open_period_percent_blank_over_non_positive_base(self):
        cells = engine.comparison_cells(10, 0, -5, engine.CURRENT)
        self.assertEqual(cells["diferencia"], 10.0)
        self.assertIsNone(cells["vs_promedio"])
        self.assertEqual(cells["dif_vs_prev"], 15.0)
        self.assertIsNone(cells["pct_vs_prev"])

    def test_open_period_missing_comparison_stays_blank(self):
        cells = engine.comparison_cells(10, None, None, engine.CURRENT)
        self.assertTrue(all(value is None for value in cells.values()))

    def test_future_is_blank(self):
        cells = engine.comparison_cells(None, 100, 90, engine.FUTURE)
        self.assertTrue(all(value is None for value in cells.values()))

    def test_closed_percent_blank_on_zero_base(self):
        cells = engine.comparison_cells(10, 0, 0, engine.COMPLETE)
        self.assertEqual(cells["diferencia"], 10.0)
        self.assertIsNone(cells["vs_promedio"])


class TestQuery(TestCase):
    def setUp(self):
        self.calls = []

        def fake_sql(query, values=None, as_dict=False):
            self.calls.append((query, values))
            return [{"item_code": "A", "item_name": "A", "item_group": "G", "bucket": 202648,
                     "qty": 3, "amount": 30}]

        self.sql = patch.object(frappe.db, "sql", side_effect=fake_sql)
        self.sql.start()

    def tearDown(self):
        self.sql.stop()

    def test_weekly_bucket_and_split(self):
        rows = engine.fetch_period_rows("C", "Weekly", date(2021, 1, 4), date(2027, 1, 3))
        self.assertEqual(rows[0]["year"], 2026)
        self.assertEqual(rows[0]["period"], 48)
        query, values = self.calls[0]
        self.assertIn("YEARWEEK(si.posting_date, 3)", query)
        self.assertIn("si.docstatus = 1", query)
        self.assertIn("SUM(sii.stock_qty)", query)
        self.assertIn("SUM(sii.base_net_amount)", query)
        self.assertIn("GROUP BY sii.item_code, bucket", query)
        self.assertNotIn("base_grand_total", query)
        self.assertEqual(values["from_date"], "2021-01-04")

    def test_period_only_grouping(self):
        engine.fetch_period_rows("C", "Monthly", date(2026, 1, 1), date(2026, 12, 31), by_item=False)
        query, _values = self.calls[0]
        self.assertIn("GROUP BY bucket", query)
        self.assertIn("'' AS item_code", query)
        self.assertNotIn("GROUP BY sii.item_code", query)

    def test_include_iva_scales_by_invoice_grand_total(self):
        engine.fetch_period_rows("C", "Monthly", date(2026, 1, 1), date(2026, 12, 31), include_iva=True)
        query, _values = self.calls[0]
        self.assertIn("si.base_grand_total / si.base_net_total", query)

    def test_date_ranges_and_item_filters(self):
        with patch.object(frappe.db, "get_value", return_value={"lft": 2, "rgt": 9}), \
                patch(ENGINE + "item_codes_in_group", return_value=["X", "Y"]):
            engine.fetch_period_rows(
                "C", "Monthly", date(2025, 11, 1), date(2026, 11, 30), item_code="X",
                item_group="Produce",
                date_ranges=[(date(2025, 11, 1), date(2025, 11, 30)), (date(2026, 11, 1), date(2026, 11, 30))],
            )
        query, values = self.calls[0]
        self.assertIn("si.posting_date BETWEEN %(span_from_0)s AND %(span_to_0)s OR "
                      "si.posting_date BETWEEN %(span_from_1)s AND %(span_to_1)s", query)
        self.assertEqual(values["span_to_1"], "2026-11-30")
        self.assertEqual(values["item_code"], "X")
        self.assertEqual(values["item_codes"], ("X", "Y"))
        self.assertIn("sii.item_code IN %(item_codes)s", query)

    def test_item_group_lookup_uses_tree_bounds(self):
        with patch.object(frappe.db, "get_value", return_value={"lft": 2, "rgt": 9}):
            engine.item_codes_in_group("Produce")
        query, values = self.calls[0]
        self.assertIn("ig.lft >= %(lft)s AND ig.rgt <= %(rgt)s", query)
        self.assertEqual(values, {"lft": 2, "rgt": 9})

    def test_empty_item_group_skips_the_sales_query(self):
        with patch(ENGINE + "item_codes_in_group", return_value=[]):
            rows = engine.fetch_period_rows("C", "Monthly", date(2026, 1, 1), date(2026, 1, 31),
                                            item_group="Empty")
        self.assertEqual(rows, [])
        self.assertEqual(self.calls, [])

    def test_unknown_item_group_throws(self):
        with patch.object(frappe.db, "get_value", return_value=None):
            with self.assertRaises(ValueError):
                engine.fetch_period_rows("C", "Monthly", date(2026, 1, 1), date(2026, 1, 31),
                                         item_group="Nope")

    def test_aggregate_by_metric(self):
        rows = [row("A", 2026, 1, 2, 25), row("A", 2026, 1, 3, 30), row("B", 2026, 2, 1, 5)]
        units, info = engine.aggregate(rows, "Units")
        self.assertEqual(units["A"][(2026, 1)], Decimal("5"))
        amounts, _info = engine.aggregate(rows, "Amount")
        self.assertEqual(amounts["A"][(2026, 1)], Decimal("55"))
        self.assertEqual(engine.total_series(units)[(2026, 1)], Decimal("5"))
        self.assertEqual(sorted(info), ["A", "B"])


def _history_patches(rows, today, covered):
    return [
        patch(ENGINE + "fetch_period_rows", return_value=rows),
        patch(ENGINE + "covered_years", return_value=covered),
        patch(ENGINE + "report_today", return_value=today),
        patch(ENGINE + "company_currency", return_value="GTQ"),
    ]


class _Patched(TestCase):
    def run_with(self, module, filters, rows, today, covered=None):
        covered = covered if covered is not None else set(range(2015, 2028))
        patches = _history_patches(rows, today, covered)
        for item in patches:
            item.start()
        try:
            return module.execute(filters)
        finally:
            for item in patches:
                item.stop()


class TestHistoryReport(_Patched):
    def monthly_rows(self):
        rows = []
        for year in range(2021, 2026):
            for month in range(1, 13):
                rows.append(row("A", year, month, 10))
        for month in range(1, 11):
            rows.append(row("A", 2026, month, 12))
        rows.append(row("A", 2026, 11, 8))  # month to date, below 10
        return rows

    def test_monthly_layout_and_open_month(self):
        columns, data, message, chart = self.run_with(
            history, {"company": "C", "year": "2026", "metric": "Units"},
            self.monthly_rows(), date(2026, 11, 27),
        )
        labels = [column["label"] for column in columns]
        self.assertEqual(labels[:2], ["Period", "From"])
        self.assertEqual(labels[2:7], ["2021", "2022", "2023", "2024", "2025"])
        self.assertEqual(labels[7:9], ["Average", "2026"])
        self.assertIn("Diff. vs 2025", labels)
        self.assertEqual(len(data), 13)
        october, november, december, total = data[9], data[10], data[11], data[12]
        self.assertEqual(october["diferencia"], 2.0)
        self.assertEqual(october["vs_promedio"], 20.0)
        self.assertEqual(november["selected"], 8.0)
        self.assertEqual(november["promedio"], 10.0)
        self.assertIsNone(november["diferencia"])
        self.assertIsNone(november["pct_vs_prev"])
        self.assertIsNone(december["selected"])
        self.assertIsNone(december["promedio"])
        self.assertIsNone(december["diferencia"])
        # Totals: history years all 12 months; selected and average completed months only.
        self.assertEqual(total["y_2025"], 120.0)
        self.assertEqual(total["selected"], 120.0)
        self.assertEqual(total["promedio"], 100.0)
        self.assertEqual(total["diferencia"], 20.0)
        self.assertEqual(total["vs_promedio"], 20.0)
        self.assertEqual(total["dif_vs_prev"], 20.0)
        self.assertEqual(chart["type"], "axis-mixed")
        self.assertEqual(len(chart["data"]["labels"]), 12)
        self.assertEqual(chart["data"]["datasets"][0]["values"][10], 8.0)
        self.assertEqual(chart["data"]["datasets"][0]["values"][11], 0)
        self.assertIn("in progress", message)
        self.assertNotIn("fieldtype", chart)

    def test_open_month_turns_green_when_ahead(self):
        rows = self.monthly_rows() + [row("A", 2026, 11, 5)]  # 13 now > 10
        _c, data, _m, _chart = self.run_with(
            history, {"company": "C", "year": "2026"}, rows, date(2026, 11, 27))
        november = data[10]
        self.assertEqual(november["selected"], 13.0)
        self.assertEqual(november["diferencia"], 3.0)
        self.assertEqual(november["vs_promedio"], 30.0)
        self.assertEqual(november["dif_vs_prev"], 3.0)

    def test_closed_year_uses_every_period(self):
        _c, data, message, _chart = self.run_with(
            history, {"company": "C", "year": "2025", "metric": "Amount"},
            self.monthly_rows(), date(2026, 11, 27))
        total = data[-1]
        self.assertEqual(total["selected"], 1200.0)
        self.assertEqual(data[0]["currency"], "GTQ")
        self.assertIn("without IVA", message)

    def test_weekly_2026_has_53_weeks_and_blank_week_53_average(self):
        rows = [row("A", 2025, 52, 4), row("A", 2026, 52, 6)]
        _c, data, message, _chart = self.run_with(
            history, {"company": "C", "year": "2026", "period_type": "Weekly"},
            rows, date(2027, 1, 2))
        self.assertEqual(len(data), 54)
        week52, week53 = data[51], data[52]
        self.assertEqual(week52["from_date"], "2026-12-21")
        self.assertEqual(week52["dif_vs_prev"], 2.0)
        self.assertEqual(week53["state"], engine.CURRENT)
        self.assertIsNone(week53["promedio"])
        self.assertIsNone(week53["dif_vs_prev"])
        for year in range(2021, 2026):
            self.assertIsNone(week53["y_{0}".format(year)])
        self.assertIn("ISO", message)

    def test_quarterly_and_years_to_compare(self):
        rows = [row("A", 2024, 1, 10), row("A", 2025, 1, 20), row("A", 2026, 1, 30)]
        columns, data, _m, _chart = self.run_with(
            history, {"company": "C", "year": "2026", "period_type": "Quarterly",
                      "years_to_compare": "2"}, rows, date(2026, 11, 27))
        self.assertEqual(len(data), 5)
        self.assertEqual(data[0]["promedio"], 15.0)
        self.assertEqual([c["label"] for c in columns][2:4], ["2024", "2025"])
        self.assertEqual(data[3]["state"], engine.CURRENT)

    def test_no_company_returns_empty(self):
        self.assertEqual(history.execute({}), ([], []))


class TestAnalyticsReport(_Patched):
    def rows(self):
        rows = []
        for year in range(2021, 2026):
            rows += [row("A", year, 11, 100, name="Arugula 1Lb", group="Arugula"),
                     row("B", year, 11, 50, name="Arugula 8Oz", group="Arugula"),
                     row("C", year, 11, 30, name="Spinach", group="Spinach")]
        rows += [row("A", 2026, 11, 120, name="Arugula 1Lb", group="Arugula"),
                 row("B", 2026, 11, 40, name="Arugula 8Oz", group="Arugula"),
                 row("C", 2026, 11, 30, name="Spinach", group="Spinach"),
                 row("D", 2026, 11, 10, name="New", group="Spinach")]
        return rows

    def test_ranking_open_period(self):
        filters = {"company": "C", "year": "2026", "period": "11", "period_type": "Monthly"}
        columns, data, message, chart, summary = self.run_with(
            analytics, filters, self.rows(), date(2026, 11, 27))
        names = [r["item_name"] for r in data]
        self.assertEqual(names, ["Arugula 1Lb", "Arugula 8Oz", "Spinach", "New", "Total"])
        top = data[0]
        self.assertEqual((top["selected"], top["promedio"], top["last_year"]), (120.0, 100.0, 100.0))
        self.assertEqual(top["diferencia"], 20.0)
        self.assertEqual(top["vs_promedio"], 20.0)
        behind = data[1]
        self.assertIsNone(behind["diferencia"])
        self.assertIsNone(behind["vs_promedio"])
        tie = data[2]
        self.assertIsNone(tie["diferencia"])
        new = data[3]
        self.assertEqual(new["promedio"], 0.0)
        self.assertEqual(new["diferencia"], 10.0)
        self.assertIsNone(new["vs_promedio"])
        self.assertEqual(top["share"], 60.0)
        self.assertEqual(data[3]["cumulative"], 100.0)
        total = data[-1]
        self.assertEqual(total["selected"], 200.0)
        self.assertEqual(total["promedio"], 180.0)
        self.assertEqual(total["diferencia"], 20.0)
        labels = [c["label"] for c in columns]
        self.assertIn("Nov 2026", labels)
        self.assertIn("Nov 2025", labels)
        self.assertEqual(chart["type"], "bar")
        self.assertEqual(chart["data"]["labels"][0], "Arugula 1Lb")
        self.assertEqual(len(chart["data"]["datasets"]), 3)
        self.assertIn("in progress", message)
        indicators = {card["label"]: card["indicator"] for card in summary}
        self.assertEqual(indicators["% vs Average"], "Green")
        self.assertNotIn("Red", indicators.values())

    def test_open_period_never_red_in_summary(self):
        rows = [r for r in self.rows() if not (r["year"] == 2026 and r["item_code"] == "A")]
        _c, data, _m, _chart, summary = self.run_with(
            analytics, {"company": "C", "year": "2026", "period": "11"}, rows, date(2026, 11, 27))
        self.assertIsNone(data[-1]["diferencia"])
        self.assertNotIn("Red", [card["indicator"] for card in summary])

    def test_closed_period_shows_losses_and_red_card(self):
        rows = [r for r in self.rows() if not (r["year"] == 2026 and r["item_code"] == "A")]
        _c, data, _m, _chart, summary = self.run_with(
            analytics, {"company": "C", "year": "2026", "period": "11"}, rows, date(2026, 12, 2))
        self.assertLess(data[-1]["diferencia"], 0)
        self.assertIn("Red", [card["indicator"] for card in summary])

    def test_future_period_sorts_by_average(self):
        _c, data, message, _chart, _s = self.run_with(
            analytics, {"company": "C", "year": "2026", "period": "11"}, self.rows(), date(2026, 10, 5))
        self.assertIsNone(data[0]["selected"])
        self.assertEqual(data[0]["promedio"], 100.0)
        self.assertIsNone(data[0]["diferencia"])
        self.assertIsNone(data[0]["share"])
        self.assertNotIn("New", [r["item_name"] for r in data])
        self.assertIn("not started", message)

    def test_group_by_item_group_tree(self):
        _c, data, _m, chart, _s = self.run_with(
            analytics, {"company": "C", "year": "2026", "period": "11", "group_by_item_group": 1},
            self.rows(), date(2026, 11, 27))
        self.assertEqual([(r["item_name"], r["indent"]) for r in data],
                         [("Arugula", 0), ("Arugula 1Lb", 1), ("Arugula 8Oz", 1),
                          ("Spinach", 0), ("Spinach", 1), ("New", 1), ("Total", 0)])
        arugula = data[0]
        self.assertEqual(arugula["is_group"], 1)
        self.assertEqual(arugula["selected"], 160.0)
        self.assertEqual(arugula["promedio"], 150.0)
        self.assertEqual(arugula["diferencia"], 10.0)
        self.assertEqual(data[1]["parent_item_group"], "Arugula")
        self.assertEqual(arugula["share"], 80.0)
        self.assertEqual(chart["data"]["labels"][0], "Arugula 1Lb")

    def test_chart_top_and_date_spans(self):
        captured = {}

        def fake_fetch(*args, **kwargs):
            captured.update(kwargs)
            captured["args"] = args
            return self.rows()

        patches = [
            patch(ENGINE + "fetch_period_rows", side_effect=fake_fetch),
            patch(ENGINE + "covered_years", return_value=set(range(2015, 2028))),
            patch(ENGINE + "report_today", return_value=date(2026, 11, 27)),
            patch(ENGINE + "company_currency", return_value="GTQ"),
        ]
        for item in patches:
            item.start()
        try:
            _c, _d, _m, chart, _s = analytics.execute(
                {"company": "C", "year": "2026", "period": "11", "chart_top": "5", "metric": "Amount"})
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(len(captured["date_ranges"]), 6)
        self.assertEqual(captured["date_ranges"][0], (date(2021, 11, 1), date(2021, 11, 30)))
        self.assertEqual(captured["date_ranges"][-1], (date(2026, 11, 1), date(2026, 11, 30)))
        self.assertEqual(chart["fieldtype"], "Currency")
        self.assertLessEqual(len(chart["data"]["labels"]), 5)

    def test_week_53_spans_skip_years_without_it(self):
        captured = {}

        def fake_fetch(*args, **kwargs):
            captured.update(kwargs)
            return []

        patches = [
            patch(ENGINE + "fetch_period_rows", side_effect=fake_fetch),
            patch(ENGINE + "covered_years", return_value=set()),
            patch(ENGINE + "report_today", return_value=date(2026, 11, 27)),
            patch(ENGINE + "company_currency", return_value="GTQ"),
        ]
        for item in patches:
            item.start()
        try:
            _c, data, _m, chart, _s = analytics.execute(
                {"company": "C", "year": "2026", "period": "53", "period_type": "Weekly"})
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(captured["date_ranges"], [(date(2026, 12, 28), date(2027, 1, 3))])
        self.assertEqual([r["item_name"] for r in data], ["Total"])
        self.assertIsNone(chart)

    def test_invalid_chart_top(self):
        with self.assertRaises(ValueError):
            analytics.parse_chart_top("7")

    def test_short_label(self):
        self.assertEqual(analytics.short_label("x" * 40)[-1], "…")
        self.assertEqual(len(analytics.short_label("x" * 40)), 28)


if __name__ == "__main__":
    main()
