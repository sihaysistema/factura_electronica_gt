# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""Frappe v13 + MariaDB integration tests for GT Monthly Sales History.

These tests boot a disposable Frappe site and run the report through
``frappe.database.mariadb.database.MariaDBDatabase.sql`` against a local
MariaDB. Redis is the Frappe cache. Rows are inserted with SQL into the
columns the report reads. ERPNext's Sales Invoice controller is not part of
this run: version-13 of that app is not installed here.

Run with the Frappe 13 virtualenv, not the system interpreter::

    PYTHONPATH=/workspace /tmp/frappe13-venv/bin/python \\
        factura_electronica/factura_electronica/report/gt_monthly_sales_history/test_gt_monthly_sales_history_frappe.py

The database user is a localhost-only account created for this disposable
database (override with GT_TEST_DB_NAME / GT_TEST_DB_PASSWORD /
GT_TEST_DB_HOST / GT_TEST_DB_PORT). It is not a production credential.
"""

from __future__ import unicode_literals

import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal

import frappe
from pymysql.err import OperationalError

from factura_electronica.factura_electronica.report.gt_monthly_sales_history.gt_monthly_sales_history import (  # noqa: E501
    CONSERVATIVE_FIELD,
    TREND_FIELD,
    execute,
    round_money,
    sales_invoices_by_day,
)

# Local disposable MariaDB account. Not used outside 127.0.0.1.
DB_NAME = os.environ.get("GT_TEST_DB_NAME", "gt_proj_test")
DB_PASSWORD = os.environ.get("GT_TEST_DB_PASSWORD", "gt_proj_test")
DB_HOST = os.environ.get("GT_TEST_DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("GT_TEST_DB_PORT", "3306"))


class TestFrappeMariaDBProjections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not getattr(frappe, "__version__", None):
            raise RuntimeError("Refusing to run: frappe is a stub, not Frappe v13.")
        if not str(frappe.__version__).startswith("13."):
            raise RuntimeError("Expected Frappe v13, found {0}".format(frappe.__version__))

        cls.sites_path = tempfile.mkdtemp(prefix="gt-proj-sites-")
        site = "gt.local"
        os.makedirs(os.path.join(cls.sites_path, site))
        with open(os.path.join(cls.sites_path, "apps.txt"), "w") as handle:
            handle.write("frappe\n")
        with open(os.path.join(cls.sites_path, "common_site_config.json"), "w") as handle:
            json.dump({
                "redis_cache": "redis://127.0.0.1:6379",
                "redis_queue": "redis://127.0.0.1:6379",
                "redis_socketio": "redis://127.0.0.1:6379",
                "socketio_port": 9000,
            }, handle)
        with open(os.path.join(cls.sites_path, site, "site_config.json"), "w") as handle:
            json.dump({
                "db_name": DB_NAME,
                "db_password": DB_PASSWORD,
                "db_type": "mariadb",
                "db_host": DB_HOST,
                "db_port": DB_PORT,
            }, handle)

        frappe.init(site=site, sites_path=cls.sites_path)
        frappe.connect()
        cls.frappe_version = frappe.__version__
        cls.mariadb_version = frappe.db.sql("SELECT VERSION()")[0][0]
        cls.default_sql_mode = frappe.db.sql("SELECT @@sql_mode")[0][0]
        cls._create_tables()
        # Prove the cache configured above is the live Redis, not an in-process dict.
        frappe.cache().set_value("gt_proj_probe", "ok")
        if frappe.cache().get_value("gt_proj_probe") != "ok":
            raise RuntimeError("Frappe cache did not round-trip through Redis")

    @classmethod
    def tearDownClass(cls):
        if getattr(frappe.local, "db", None):
            frappe.db.sql("DROP TABLE IF EXISTS `tabSales Invoice`")
            frappe.db.sql("DROP TABLE IF EXISTS `tabCompany`")
            frappe.db.commit()
        frappe.destroy()

    @classmethod
    def _create_tables(cls):
        frappe.db.sql("DROP TABLE IF EXISTS `tabSales Invoice`")
        frappe.db.sql("DROP TABLE IF EXISTS `tabCompany`")
        # ``modified`` exists because Frappe get_value orders by it.
        frappe.db.sql("""
            CREATE TABLE `tabCompany` (
                name varchar(140) NOT NULL PRIMARY KEY,
                default_currency varchar(140) NULL,
                modified datetime(6) NULL
            ) ENGINE=InnoDB
        """)
        frappe.db.sql("""
            CREATE TABLE `tabSales Invoice` (
                name varchar(140) NOT NULL PRIMARY KEY,
                posting_date date NOT NULL,
                docstatus int(1) NOT NULL,
                company varchar(140) NOT NULL,
                grand_total decimal(21,9) NOT NULL,
                conversion_rate decimal(21,9) NOT NULL,
                currency varchar(140) NULL,
                modified datetime(6) NULL
            ) ENGINE=InnoDB
        """)
        frappe.db.commit()

    def setUp(self):
        frappe.db.sql("SET SESSION sql_mode=%s", (self.default_sql_mode,))
        frappe.db.sql("DELETE FROM `tabSales Invoice`")
        frappe.db.sql("DELETE FROM `tabCompany`")
        frappe.db.commit()
        self._sql_calls = []
        self._original_sql = frappe.db.sql

        def counting_sql(query, *args, **kwargs):
            self._sql_calls.append(query)
            return self._original_sql(query, *args, **kwargs)

        frappe.db.sql = counting_sql

    def tearDown(self):
        frappe.db.sql = self._original_sql

    def test_versions_are_real_frappe_and_mariadb(self):
        self.assertTrue(str(self.frappe_version).startswith("13."))
        self.assertIn("MariaDB", self.mariadb_version)
        self.assertNotIn("ONLY_FULL_GROUP_BY", self.default_sql_mode)

    def test_parameter_binding_isolates_companies_and_groups_one_day(self):
        self._company("O'Brien GT", "GTQ")
        self._company("Acme GT", "USD")
        self._invoice("OB-1", "2026-01-15", "O'Brien GT", "40.00")
        self._invoice("OB-2", "2026-01-15", "O'Brien GT", "60.50")
        self._invoice("AC-1", "2026-01-15", "Acme GT", "99999.00")
        frappe.db.commit()

        self._sql_calls[:] = []
        rows = sales_invoices_by_day(
            "O'Brien GT", "2021-01-01", "2026-12-31", 2026, date(2026, 3, 15)
        )

        daily = self._daily_calls()
        self.assertEqual(len(daily), 1)
        self.assertIn("%(company)s", daily[0])
        self.assertNotIn("O'Brien", daily[0])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["year_repo"], 2026)
        self.assertEqual(rows[0]["month_repo"], 1)
        self.assertEqual(rows[0]["day_repo"], 15)
        # Frappe v13 converts MariaDB DECIMAL to float. 40 + 60.50 = 100.50.
        self.assertIsInstance(rows[0]["total"], float)
        self.assertEqual(rows[0]["total"], 100.50)

    def test_cutoff_returns_docstatus_and_full_execute(self):
        today = date(2026, 3, 15)
        self._company("Acme GT", "GTQ")
        self._company("Other GT", "USD")
        posted = date(2026, 1, 1)
        yesterday = date(2026, 3, 14)
        serial = 0
        while posted <= yesterday:
            serial += 1
            self._invoice("AC-{0}".format(serial), posted.isoformat(), "Acme GT", "10.00")
            posted += timedelta(days=1)
        # Contaminants. None of these may enter the daily actuals.
        self._invoice("TODAY", "2026-03-15", "Acme GT", "999.00")
        self._invoice("FUTURE", "2026-03-20", "Acme GT", "500.00")
        self._invoice("NOV", "2026-11-01", "Acme GT", "999.00")
        self._invoice("DRAFT", "2026-01-05", "Acme GT", "10000.00", docstatus=0)
        self._invoice("CANCEL", "2026-01-06", "Acme GT", "10000.00", docstatus=2)
        self._invoice("OTHER", "2026-01-02", "Other GT", "50000.00")
        frappe.db.commit()

        self._sql_calls[:] = []
        with self._today(today):
            columns, rows, message = execute({
                "company": "Acme GT",
                "year": 2026,
                "years_to_compare": "5",
            })

        self.assertEqual(len(self._daily_calls()), 1)
        self.assertEqual(len(self._monthly_calls()), 1)
        self.assertEqual(rows[0]["currency"], "GTQ")
        self.assertIn(TREND_FIELD, [column["fieldname"] for column in columns])
        self.assertIn("pronóstico", message)
        marzo = rows[2]
        noviembre = rows[10]
        # The monthly ledger still shows today and the later March posting.
        self.assertEqual(marzo["y_2026"], 1639.0)
        self.assertEqual(marzo[TREND_FIELD], 310.0)
        self.assertEqual(marzo[CONSERVATIVE_FIELD], 140.0)
        self.assertIsNone(noviembre["y_2026"])
        self.assertEqual(noviembre[TREND_FIELD], 300.0)
        self.assertEqual(rows[-1]["y_2026"], 590.0)
        self.assertEqual(rows[-1][TREND_FIELD], 3650.0)
        self.assertEqual(rows[-1][CONSERVATIVE_FIELD], 730.0)
        self.assertEqual(rows[0][TREND_FIELD], 310.0)

        # The same connection, asked for the other company, does not see Acme.
        other = sales_invoices_by_day(
            "Other GT", "2021-01-01", "2026-12-31", 2026, today
        )
        self.assertEqual(len(other), 1)
        self.assertEqual(other[0]["total"], 50000.0)

    def test_credit_note_and_conversion_rate_net_in_sql(self):
        today = date(2026, 2, 1)
        self._company("Acme GT", "GTQ")
        self._company("Other GT", "USD")
        # 50 * 2 and a credit note -80 * 2 on the same day. Tax stays inside grand_total.
        self._invoice("SALE", "2026-01-15", "Acme GT", "50.00", conversion_rate="2.0")
        self._invoice("RETURN", "2026-01-15", "Acme GT", "-80.00", conversion_rate="2.0")
        self._invoice("DRAFT", "2026-01-15", "Acme GT", "1000.00", docstatus=0)
        self._invoice("CANCEL", "2026-01-15", "Acme GT", "-500.00", docstatus=2)
        self._invoice("OTHER", "2026-01-15", "Other GT", "9999.00", conversion_rate="2.0")
        frappe.db.commit()

        rows = sales_invoices_by_day(
            "Acme GT", "2026-01-01", "2026-12-31", 2026, today
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total"], -60.0)

        with self._today(today):
            report_rows = execute({
                "company": "Acme GT",
                "year": 2026,
                "years_to_compare": "2",
            })[1]
        self.assertEqual(report_rows[0][TREND_FIELD], -60.0)
        self.assertLess(report_rows[1][TREND_FIELD], 0)

    def test_leap_day_history_and_rejected_non_leap_date(self):
        today = date(2028, 2, 29)
        self._company("Acme GT", "GTQ")
        self._company("Other GT", "USD")
        for year in (2023, 2024, 2025, 2026, 2027):
            self._invoice(
                "COVER-{0}".format(year), "{0}-01-15".format(year), "Acme GT", "1.00"
            )
        self._invoice("LEAP", "2024-02-29", "Acme GT", "100.00")
        self._invoice("LEAP-OTHER", "2024-02-29", "Other GT", "999.00")
        frappe.db.commit()
        with self.assertRaises(OperationalError):
            self._invoice("BAD-LEAP", "2026-02-29", "Acme GT", "5.00")
        frappe.db.rollback()

        with self._today(today):
            rows = execute({
                "company": "Acme GT",
                "year": 2028,
                "years_to_compare": "5",
            })[1]
            short = execute({
                "company": "Acme GT",
                "year": 2028,
                "years_to_compare": "2",
            })[1]
        self.assertEqual(rows[1][CONSERVATIVE_FIELD], 100.0)
        self.assertEqual(short[1][CONSERVATIVE_FIELD], 0.0)

    def test_zero_sale_stays_in_the_denominator(self):
        today = date(2026, 4, 10)
        self._company("Acme GT", "GTQ")
        self._invoice("Y2023", "2023-01-10", "Acme GT", "1.00")
        self._invoice("Y2024", "2024-01-10", "Acme GT", "1.00")
        self._invoice("APR", "2023-04-10", "Acme GT", "30.00")
        frappe.db.commit()

        with self._today(today):
            rows = execute({
                "company": "Acme GT",
                "year": 2026,
                "years_to_compare": "3",
            })[1]
        # 2023 = 30, 2024 = no invoice (zero), 2025 = no coverage. Average 15.
        self.assertEqual(rows[3][CONSERVATIVE_FIELD], 15.0)
        self.assertEqual(rows[-1][CONSERVATIVE_FIELD], 15.0)

    def test_january_first_trend_stays_blank(self):
        today = date(2026, 1, 1)
        self._company("Acme GT", "GTQ")
        self._invoice("TODAY", "2026-01-01", "Acme GT", "500.00")
        # Zero-value invoices mark 2024 and 2025 as covered without adding a forecast.
        self._invoice("H2024", "2024-01-02", "Acme GT", "0.00")
        self._invoice("H2025", "2025-01-02", "Acme GT", "0.00")
        self._invoice("JAN", "2025-01-01", "Acme GT", "10.00")
        frappe.db.commit()

        with self._today(today):
            rows = execute({
                "company": "Acme GT",
                "year": 2026,
                "years_to_compare": "2",
            })[1]
        self.assertEqual(rows[0]["y_2026"], 500.0)
        self.assertTrue(all(row[TREND_FIELD] is None for row in rows))
        self.assertEqual(rows[0][CONSERVATIVE_FIELD], 5.0)
        self.assertEqual(rows[-1][CONSERVATIVE_FIELD], 5.0)

    def test_float_decimal_from_frappe_keeps_the_locked_rounding(self):
        # Frappe hands the DECIMAL sum back as a float. The locked footer is 117.87.
        today = date(2026, 2, 1)
        self._company("Acme GT", "GTQ")
        self._invoice("ONE", "2026-01-31", "Acme GT", "10.01")
        frappe.db.commit()
        with self._today(today):
            rows = execute({"company": "Acme GT", "year": 2026})[1]
        self.assertEqual(rows[0][TREND_FIELD], 10.01)
        self.assertEqual(rows[-1][TREND_FIELD], 117.87)

    def test_daily_query_survives_only_full_group_by(self):
        self._company("Acme GT", "GTQ")
        self._invoice("ONE", "2026-01-15", "Acme GT", "10.00")
        self._invoice("TWO", "2026-01-15", "Acme GT", "5.00", currency="USD")
        frappe.db.commit()
        frappe.db.sql(
            "SET SESSION sql_mode=%s",
            ("ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,"
             "NO_ENGINE_SUBSTITUTION",),
        )
        rows = sales_invoices_by_day(
            "Acme GT", "2026-01-01", "2026-12-31", 2026, date(2026, 3, 15)
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total"], 15.0)

    def test_closed_year_does_not_run_the_daily_query(self):
        self._company("Acme GT", "GTQ")
        self._invoice("OLD", "2024-06-02", "Acme GT", "-15.13")
        frappe.db.commit()
        self._sql_calls[:] = []
        with self._today(date(2026, 5, 1)):
            rows = execute({"company": "Acme GT", "year": 2024})[1]
        self.assertEqual(self._daily_calls(), [])
        self.assertEqual(len(self._monthly_calls()), 1)
        self.assertEqual(rows[5][TREND_FIELD], -15.13)
        self.assertEqual(rows[-1][TREND_FIELD], rows[-1]["y_2024"])

    def _company(self, name, currency):
        self._original_sql(
            """INSERT INTO `tabCompany` (name, default_currency, modified)
               VALUES (%(name)s, %(currency)s, '2026-01-01 00:00:00')""",
            {"name": name, "currency": currency},
        )

    def _invoice(self, name, posting_date, company, grand_total, conversion_rate="1.0",
                 docstatus=1, currency="GTQ"):
        self._original_sql(
            """INSERT INTO `tabSales Invoice`
               (name, posting_date, docstatus, company, grand_total, conversion_rate, currency)
               VALUES (%(name)s, %(posting_date)s, %(docstatus)s, %(company)s,
                       %(grand_total)s, %(conversion_rate)s, %(currency)s)""",
            {
                "name": name,
                "posting_date": posting_date,
                "docstatus": docstatus,
                "company": company,
                "grand_total": grand_total,
                "conversion_rate": conversion_rate,
                "currency": currency,
            },
        )

    def _daily_calls(self):
        return [query for query in self._sql_calls if "day_repo" in query]

    def _monthly_calls(self):
        return [
            query for query in self._sql_calls
            if "month_repo" in query and "day_repo" not in query
        ]

    def _today(self, today):
        from unittest.mock import patch
        return patch(
            "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
            "gt_monthly_sales_history.report_today",
            return_value=today,
        )


class TestErpNextSalesInvoiceSchema(unittest.TestCase):
    """Same report SQL against the Sales Invoice table ERPNext v13 actually migrated."""

    SITE_PATH = os.environ.get("GT_ERPNEXT_SITES", "/tmp/gt-bench/sites")
    SITE = os.environ.get("GT_ERPNEXT_SITE", "gt-erp.local")

    @classmethod
    def setUpClass(cls):
        config = os.path.join(cls.SITE_PATH, cls.SITE, "site_config.json")
        if not os.path.exists(config):
            raise unittest.SkipTest("ERPNext site is not provisioned at {0}".format(config))
        if getattr(frappe.local, "initialised", None):
            frappe.destroy()
        frappe.init(site=cls.SITE, sites_path=cls.SITE_PATH)
        frappe.connect()
        doctype = frappe.db.sql(
            "SELECT name FROM `tabDocType` WHERE name=%s", ("Sales Invoice",)
        )
        if not doctype:
            raise RuntimeError("ERPNext did not migrate the Sales Invoice DocType")
        import erpnext
        cls.erpnext_version = erpnext.__version__

    @classmethod
    def tearDownClass(cls):
        if getattr(frappe.local, "db", None):
            frappe.db.sql("DELETE FROM `tabSales Invoice` WHERE name LIKE 'GTPROJ-%'")
            frappe.db.sql("DELETE FROM `tabCompany` WHERE name LIKE 'GTPROJ %'")
            frappe.db.commit()
        frappe.destroy()

    def setUp(self):
        frappe.db.sql("DELETE FROM `tabSales Invoice` WHERE name LIKE 'GTPROJ-%'")
        frappe.db.sql("DELETE FROM `tabCompany` WHERE name LIKE 'GTPROJ %'")
        frappe.db.commit()

    def test_real_sales_invoice_table_matches_projection_rules(self):
        import erpnext
        self.assertTrue(str(erpnext.__version__).startswith("13."))
        self.assertTrue(str(frappe.__version__).startswith("13."))
        self._company("GTPROJ Acme", "GTQ")
        self._company("GTPROJ Other", "USD")
        today = date(2026, 3, 15)
        posted = date(2026, 1, 1)
        serial = 0
        yesterday = date(2026, 3, 14)
        while posted <= yesterday:
            serial += 1
            self._invoice("GTPROJ-{0}".format(serial), posted.isoformat(), "GTPROJ Acme", "10.00")
            posted += timedelta(days=1)
        self._invoice("GTPROJ-TODAY", "2026-03-15", "GTPROJ Acme", "999.00")
        self._invoice("GTPROJ-FUTURE", "2026-03-20", "GTPROJ Acme", "500.00")
        self._invoice("GTPROJ-DRAFT", "2026-01-08", "GTPROJ Acme", "10000.00", docstatus=0)
        self._invoice("GTPROJ-CANCEL", "2026-01-09", "GTPROJ Acme", "10000.00", docstatus=2)
        self._invoice("GTPROJ-RETURN", "2026-01-10", "GTPROJ Acme", "-4.00")
        self._invoice("GTPROJ-OTHER", "2026-01-04", "GTPROJ Other", "80000.00")
        frappe.db.commit()

        calls = []
        original = frappe.db.sql

        def counting_sql(query, *args, **kwargs):
            calls.append(query)
            return original(query, *args, **kwargs)

        frappe.db.sql = counting_sql
        try:
            with patch_today(today):
                rows = execute({
                    "company": "GTPROJ Acme",
                    "year": 2026,
                    "years_to_compare": "5",
                })[1]
        finally:
            frappe.db.sql = original

        daily = [query for query in calls if "day_repo" in query]
        monthly = [query for query in calls if "month_repo" in query and "day_repo" not in query]
        self.assertEqual(len(daily), 1)
        self.assertEqual(len(monthly), 1)
        self.assertIn("%(company)s", daily[0])
        # January is 31 days at 10, minus the credit note of 4 on the 10th.
        self.assertEqual(rows[0][TREND_FIELD], 306.0)
        # The month column still includes today and the later March posting.
        self.assertEqual(rows[2]["y_2026"], 1639.0)
        self.assertEqual(
            rows[-1][TREND_FIELD],
            round_money(sum((Decimal(str(row[TREND_FIELD])) for row in rows[:-1]), Decimal("0"))),
        )
        # The credit note lowers the full-year trend below 10 per calendar day.
        self.assertLess(rows[-1][TREND_FIELD], 3650.0)
        self.assertEqual(rows[0]["currency"], "GTQ")

        other = sales_invoices_by_day(
            "GTPROJ Other", "2021-01-01", "2026-12-31", 2026, today
        )
        self.assertEqual([(row["total"], row["day_repo"]) for row in other], [(80000.0, 4)])

    def _company(self, name, currency):
        frappe.db.sql(
            """INSERT INTO `tabCompany` (name, default_currency, modified)
               VALUES (%(name)s, %(currency)s, '2026-01-01 00:00:00.000000')""",
            {"name": name, "currency": currency},
        )

    def _invoice(self, name, posting_date, company, grand_total, docstatus=1):
        frappe.db.sql(
            """INSERT INTO `tabSales Invoice`
               (name, posting_date, docstatus, company, grand_total, conversion_rate, currency)
               VALUES (%(name)s, %(posting_date)s, %(docstatus)s, %(company)s,
                       %(grand_total)s, 1, 'GTQ')""",
            {
                "name": name,
                "posting_date": posting_date,
                "docstatus": docstatus,
                "company": company,
                "grand_total": grand_total,
            },
        )


def patch_today(today):
    from unittest.mock import patch
    return patch(
        "factura_electronica.factura_electronica.report.gt_monthly_sales_history."
        "gt_monthly_sales_history.report_today",
        return_value=today,
    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
