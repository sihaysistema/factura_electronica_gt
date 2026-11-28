// Copyright (c) 2026, Si Hay Sistema and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GT Item Sales Analytics"] = {
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
      on_change: function () {
        gt_item_sales_refresh_period(frappe.query_report, false, true);
      },
    },
    {
      fieldname: "year",
      label: __("Year"),
      fieldtype: "Select",
      options: gt_item_sales_year_options(),
      default: String(gt_item_sales_current_period("Monthly").year),
      reqd: 1,
      on_change: function () {
        gt_item_sales_refresh_period(frappe.query_report, true, true);
      },
    },
    {
      fieldname: "period",
      label: __("Period"),
      fieldtype: "Select",
      options: gt_item_sales_period_options("Monthly", new Date().getFullYear()),
      default: String(gt_item_sales_current_period("Monthly").index),
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
      fieldname: "item_group",
      label: __("Item Group"),
      fieldtype: "Link",
      options: "Item Group",
    },
    {
      fieldname: "group_by_item_group",
      label: __("Group by Item Group"),
      fieldtype: "Check",
      default: 0,
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
  onload: function (report) {
    // Saved or routed filters can bring a Weekly period; rebuild the list
    // for the loaded period type and year, keeping a valid period.
    gt_item_sales_refresh_period(report, true, false);
  },
  tree: true,
  name_field: "item_name",
  parent_field: "parent_item_group",
  initial_depth: 1,
  formatter: function (value, row, column, data, default_formatter) {
    if (column && column.fieldname === "item_name" && data && !data.is_total_row && value) {
      var key = data.is_group ? "item_group" : "item_code";
      var target = data.is_group ? data.item_group : data.item_code;
      // The onclick runs in the page, not inside this script. Frappe evals
      // report JS with `new Function`, so the handler has to be on window.
      var html = "<a href='#' title='" + frappe.utils.escape_html(__("Open history")) +
        "' onclick='return window.gt_item_sales_open_history(" +
        JSON.stringify(key).replace(/'/g, "&#39;") + "," +
        JSON.stringify(target).replace(/'/g, "&#39;") + ")'>" +
        frappe.utils.escape_html(value) + "</a>";
      return data.is_group ? "<b>" + html + "</b>" : html;
    }
    return gt_item_sales_format(value, row, column, data, default_formatter);
  },
};

window.gt_item_sales_open_history = function (key, target) {
  var values = frappe.query_report.get_filter_values();
  var options = {
    company: values.company,
    year: values.year,
    years_to_compare: values.years_to_compare,
    period_type: values.period_type,
    metric: values.metric,
    include_iva: values.include_iva ? 1 : 0,
    item_code: "",
    item_group: "",
  };
  // One target only: an item, or a whole group from the grouped view.
  options[key] = target;
  frappe.route_options = options;
  frappe.set_route("query-report", "GT Item Sales History");
  return false;
};

// ISO week helpers (Monday to Sunday). December 28 is always in the last
// ISO week of its year.
function gt_item_sales_iso_week(date) {
  var day = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  var weekday = day.getUTCDay() || 7;
  day.setUTCDate(day.getUTCDate() + 4 - weekday);
  var yearStart = new Date(Date.UTC(day.getUTCFullYear(), 0, 1));
  return {
    year: day.getUTCFullYear(),
    index: Math.ceil(((day - yearStart) / 86400000 + 1) / 7),
  };
}

function gt_item_sales_weeks_in_year(year) {
  return gt_item_sales_iso_week(new Date(Number(year), 11, 28)).index;
}

function gt_item_sales_today() {
  var parts = frappe.datetime.get_today().split("-");
  return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
}

function gt_item_sales_current_period(type) {
  var today = gt_item_sales_today();
  if (type === "Weekly") {
    return gt_item_sales_iso_week(today);
  }
  if (type === "Quarterly") {
    return { year: today.getFullYear(), index: Math.floor(today.getMonth() / 3) + 1 };
  }
  return { year: today.getFullYear(), index: today.getMonth() + 1 };
}

function gt_item_sales_period_options(type, year) {
  var months = ["January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December"];
  var options = [];
  if (type === "Weekly") {
    var weeks = gt_item_sales_weeks_in_year(year);
    for (var w = 1; w <= weeks; w++) {
      options.push({ value: String(w), label: __("W{0}", [(w < 10 ? "0" : "") + w]) });
    }
  } else if (type === "Quarterly") {
    for (var q = 1; q <= 4; q++) {
      options.push({ value: String(q), label: __("Q{0}", [q]) });
    }
  } else {
    for (var m = 1; m <= 12; m++) {
      options.push({ value: String(m), label: __(months[m - 1]) });
    }
  }
  return options;
}

// keep_valid: keep the chosen period when it exists in the new list (year
// change, page load). refresh_if_same: refresh the report when the period
// value does not change (a changed value refreshes by itself).
function gt_item_sales_refresh_period(report, keep_valid, refresh_if_same) {
  var type = report.get_filter_value("period_type") || "Monthly";
  var year = Number(report.get_filter_value("year")) || new Date().getFullYear();
  var filter = report.get_filter("period");
  if (!filter) {
    return;
  }
  var options = gt_item_sales_period_options(type, year);
  var current = gt_item_sales_current_period(type);
  var value = String(filter.get_value() || "");
  var valid = Number(value) >= 1 && Number(value) <= options.length;
  var wanted = String(current.year === year ? current.index : (year < current.year ? options.length : 1));
  if (keep_valid && valid) {
    wanted = value;
  }
  filter.df.options = options;
  if (filter.set_options) {
    filter.set_options(options);
  }
  if (value !== wanted) {
    filter.set_value(wanted);
  } else if (refresh_if_same) {
    report.refresh();
  }
}

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
