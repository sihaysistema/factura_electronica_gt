// Copyright (c) 2026, Si Hay Sistema and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GT Monthly Sales History"] = {
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
      fieldname: "year",
      label: __("Year"),
      fieldtype: "Select",
      options: gt_monthly_sales_history_year_options(),
      default: String(new Date().getFullYear()),
      reqd: 1,
    },
    {
      fieldname: "years_to_compare",
      label: __("Years to compare"),
      fieldtype: "Select",
      options: "5\n4\n3\n2",
      default: "5",
      reqd: 1,
    },
  ],
};

function gt_monthly_sales_history_year_options() {
  var current = new Date().getFullYear();
  var years = [];
  for (var year = current + 1; year >= current - 20; year--) {
    years.push(String(year));
  }
  return years.join("\n");
}
