// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GT Sales Ledger"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: "",
      reqd: 1,
      on_change: function () {
        frappe.db.get_value("Company", frappe.query_report.get_filter_value("company"), "tax_id").then((r) => {
          // console.log(r.message.name)
          frappe.query_report.set_filter_value("nit", r.message.tax_id);
          frappe.db.get_value("Company", frappe.query_report.get_filter_value("company"), "default_currency").then((r) => {
            frappe.query_report.set_filter_value("company_currency", r.message.default_currency);
          });
        });
      },
    },
    {
      fieldname: "nit",
      label: __("NIT"),
      fieldtype: "Data",
      default: "",
      read_only: 1,
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
      default: "",
      reqd: 0,
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "company_currency",
      label: __("Company Default Currency"),
      default: "",
      fieldtype: "Select",
      read_only: 1,
      options: erpnext.get_presentation_currency_list(),
    },
    {
      fieldname: "language",
      label: __("Display Language"),
      default: "es",
      fieldtype: "Link",
      options: "Language",
    },
    {
      fieldname: "group",
      label: __("Group?"),
      default: "",
      fieldtype: "Check",
    },
    {
      fieldtype: "Break",
    },
    {
      fieldname: "note_report",
      label: __("Note"),
      default: "No se incluyen descripcion de facturas con items no configurados, ni items de combustibles",
      fieldtype: "Data",
      read_only: 1,
      width: "400px",
    },
  ],
  // onload: function (report) {
  //     report.page.add_inner_button(__("Download Excel"), function () {
  //         window.open("/api/method/factura_electronica.api.download_excel_sales_ledger");
  //         // window.open("sihaysistema.com", "_blank");
  //     });
  // },
};
