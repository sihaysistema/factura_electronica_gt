// Copyright (c) 2026, Si Hay Sistema and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GT Sales Item Ranking"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
      reqd: 1,
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today().substr(0, 4) + "-01-01",
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
    },
    {
      fieldname: "item_group",
      label: __("Item Group"),
      fieldtype: "Link",
      options: "Item Group",
    },
    {
      fieldname: "rank_by",
      label: __("Rank by"),
      fieldtype: "Select",
      options: "Monto\nCantidad\nPrecio",
      default: "Monto",
      reqd: 1,
    },
    {
      fieldname: "chart_top",
      label: __("Chart top"),
      fieldtype: "Select",
      options: "5\n10\n15\n20\n25",
      default: "10",
      reqd: 1,
    },
  ],
};
