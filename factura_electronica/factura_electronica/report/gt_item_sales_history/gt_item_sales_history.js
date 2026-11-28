// Copyright (c) 2026, Si Hay Sistema and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GT Item Sales History"] = {
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
      options: gt_item_sales_year_options(),
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
    {
      fieldname: "period_type",
      label: __("Period type"),
      fieldtype: "Select",
      options: [
        { value: "Weekly", label: __("Weekly") },
        { value: "Monthly", label: __("Monthly") },
        { value: "Quarterly", label: __("Quarterly") },
      ],
      default: "Monthly",
      reqd: 1,
    },
    {
      fieldname: "metric",
      label: __("Metric"),
      fieldtype: "Select",
      options: [
        { value: "Units", label: __("Units") },
        { value: "Amount", label: __("Amount") },
      ],
      default: "Units",
      reqd: 1,
    },
    {
      fieldname: "include_iva",
      label: __("Include IVA"),
      fieldtype: "Check",
      default: 0,
      depends_on: "eval:doc.metric=='Amount'",
    },
    {
      fieldname: "item_code",
      label: __("Item"),
      fieldtype: "Link",
      options: "Item",
    },
    {
      fieldname: "item_group",
      label: __("Item Group"),
      fieldtype: "Link",
      options: "Item Group",
    },
  ],
  formatter: function (value, row, column, data, default_formatter) {
    return gt_item_sales_format(value, row, column, data, default_formatter);
  },
};

// Shared by GT Item Sales History and GT Item Sales Analytics. Both report
// scripts define the same helpers; the last one loaded wins, and they are
// identical.
function gt_item_sales_year_options() {
  var current = new Date().getFullYear();
  var years = [];
  for (var year = current + 1; year >= current - 20; year--) {
    years.push(String(year));
  }
  return years.join("\n");
}

function gt_item_sales_format(value, row, column, data, default_formatter) {
  var fieldname = column && column.fieldname;
  var html;
  if (fieldname === "vs_promedio" || fieldname === "pct_vs_prev") {
    html = gt_item_sales_percent(value);
  } else {
    html = default_formatter(value, row, column, data);
  }
  if (fieldname === "diferencia" || fieldname === "dif_vs_prev" ||
      fieldname === "vs_promedio" || fieldname === "pct_vs_prev") {
    html = gt_item_sales_colorize(html, value, data, fieldname);
  }
  if (data && (data.is_total_row || data.is_group) && html) {
    html = "<b>" + html + "</b>";
  }
  return html;
}

function gt_item_sales_percent(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  var number = Number(value);
  if (isNaN(number)) {
    return "";
  }
  return "<div style='text-align: right'>" + (number < 0 ? "-" : "") +
    Math.abs(number).toFixed(2) + "%</div>";
}

function gt_item_sales_colorize(html, value, data, fieldname) {
  if (!html) {
    return html;
  }
  var number = Number(value);
  if (value === null || value === undefined || value === "" || isNaN(number) || number === 0) {
    return html;
  }
  // A positive result over a negative base is not a gain when the period
  // itself is still at or below zero (net returns). Leave it uncolored.
  if (number > 0 && gt_item_sales_negative_base_not_ahead(data, fieldname)) {
    return html;
  }
  return "<span style='color:" + (number > 0 ? "green" : "red") + "'>" + html + "</span>";
}

function gt_item_sales_negative_base_not_ahead(data, fieldname) {
  if (!data || data.selected === null || data.selected === undefined || data.selected === "") {
    return false;
  }
  var selected = Number(data.selected);
  if (!(selected <= 0)) {
    return false;
  }
  var base;
  if (fieldname === "diferencia" || fieldname === "vs_promedio") {
    base = data.promedio;
  } else if (fieldname === "dif_vs_prev" || fieldname === "pct_vs_prev") {
    base = data.last_year;
  } else {
    return false;
  }
  return base !== null && base !== undefined && base !== "" && Number(base) < 0;
}
