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
  formatter: function (value, row, column, data, default_formatter) {
    if (column && column.fieldname === "vs_promedio") {
      var percent = gt_monthly_sales_history_format_percent(value);
      return gt_monthly_sales_history_colorize(percent, value);
    }
    var formatted = default_formatter(value, row, column, data);
    if (column && column.fieldname === "diferencia") {
      return gt_monthly_sales_history_colorize(formatted, value);
    }
    return formatted;
  },
};

function gt_monthly_sales_history_format_percent(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  var number = Number(value);
  if (isNaN(number)) {
    return "";
  }
  var negative = number < 0;
  var text = Math.abs(number).toFixed(2);
  return "<div style='text-align: right'>" + (negative ? "-" : "") + text + "%</div>";
}

function gt_monthly_sales_history_colorize(html, value) {
  if (!html) {
    return html;
  }
  var number = Number(value);
  if (isNaN(number) || number === 0) {
    return html;
  }
  var color = number > 0 ? "green" : "red";
  return "<span style='color:" + color + "'>" + html + "</span>";
}

function gt_monthly_sales_history_year_options() {
  var current = new Date().getFullYear();
  var years = [];
  for (var year = current + 1; year >= current - 20; year--) {
    years.push(String(year));
  }
  return years.join("\n");
}
