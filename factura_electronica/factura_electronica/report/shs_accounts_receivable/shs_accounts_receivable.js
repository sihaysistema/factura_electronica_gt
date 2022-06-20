// Copyright (c) 2020, Si Hay Sistema and and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["SHS-Accounts Receivable"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      reqd: 1,
      default: frappe.defaults.get_user_default("Company"),
    },
    {
      fieldname: "report_date",
      label: __("Posting Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      /*on_change: (report) => {
        const to_date = get_end_date(report);
        frappe.query_report.set_filter_value("to_date", to_date);
      },*/
    },
    /*{
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: get_end_date(),
    },*/
    {
      fieldname: "finance_book",
      label: __("Finance Book"),
      fieldtype: "Link",
      options: "Finance Book",
    },
    {
      fieldname: "cost_center",
      label: __("Cost Center"),
      fieldtype: "Link",
      options: "Cost Center",
      get_query: () => {
        var company = frappe.query_report.get_filter_value("company");
        return {
          filters: {
            company: company,
          },
        };
      },
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
      on_change: () => {
        var customer = frappe.query_report.get_filter_value("customer");
        var company = frappe.query_report.get_filter_value("company");
        if (customer) {
          frappe.db.get_value("Customer", customer, ["tax_id", "customer_name", "payment_terms"], function (value) {
            frappe.query_report.set_filter_value("tax_id", value["tax_id"]);
            frappe.query_report.set_filter_value("customer_name", value["customer_name"]);
            frappe.query_report.set_filter_value("payment_terms", value["payment_terms"]);
          });

          frappe.db.get_value(
            "Customer Credit Limit",
            { parent: customer, company: company },
            ["credit_limit"],
            function (value) {
              if (value) {
                frappe.query_report.set_filter_value("credit_limit", value["credit_limit"]);
              }
            },
            "Customer"
          );
        } else {
          frappe.query_report.set_filter_value("tax_id", "");
          frappe.query_report.set_filter_value("customer_name", "");
          frappe.query_report.set_filter_value("credit_limit", "");
          frappe.query_report.set_filter_value("payment_terms", "");
        }
      },
    },
    {
      fieldname: "ageing_based_on",
      label: __("Ageing Based On"),
      fieldtype: "Select",
      options: "Posting Date\nDue Date",
      default: "Due Date",
    },
    {
      fieldname: "range1",
      label: __("Ageing Range 1"),
      fieldtype: "Int",
      default: "30",
      reqd: 1,
    },
    {
      fieldname: "range2",
      label: __("Ageing Range 2"),
      fieldtype: "Int",
      default: "60",
      reqd: 1,
    },
    {
      fieldname: "range3",
      label: __("Ageing Range 3"),
      fieldtype: "Int",
      default: "90",
      reqd: 1,
    },
    {
      fieldname: "range4",
      label: __("Ageing Range 4"),
      fieldtype: "Int",
      default: "120",
      reqd: 1,
    },
    {
      fieldname: "customer_group",
      label: __("Customer Group"),
      fieldtype: "Link",
      options: "Customer Group",
    },
    {
      fieldname: "payment_terms_template",
      label: __("Payment Terms Template"),
      fieldtype: "Link",
      options: "Payment Terms Template",
    },
    {
      fieldname: "sales_partner",
      label: __("Sales Partner"),
      fieldtype: "Link",
      options: "Sales Partner",
    },
    {
      fieldname: "sales_person",
      label: __("Sales Person"),
      fieldtype: "Link",
      options: "Sales Person",
    },
    {
      fieldname: "territory",
      label: __("Territory"),
      fieldtype: "Link",
      options: "Territory",
    },
    {
      fieldname: "group_by_party",
      label: __("Group By Customer"),
      fieldtype: "Check",
    },
    {
      fieldname: "based_on_payment_terms",
      label: __("Based On Payment Terms"),
      fieldtype: "Check",
    },
    {
      fieldname: "show_future_payments",
      label: __("Show Future Payments"),
      fieldtype: "Check",
    },
    {
      fieldname: "show_delivery_notes",
      label: __("Show Linked Delivery Notes"),
      fieldtype: "Check",
    },
    {
      fieldname: "show_sales_person",
      label: __("Show Sales Person"),
      fieldtype: "Check",
    },
    {
      fieldname: "show_remarks",
      label: __("Show Remarks"),
      fieldtype: "Check",
    },
    {
      fieldname: "tax_id",
      label: __("Tax Id"),
      fieldtype: "Data",
      hidden: 1,
    },
    {
      fieldname: "customer_name",
      label: __("Customer Name"),
      fieldtype: "Data",
      hidden: 1,
    },
    {
      fieldname: "payment_terms",
      label: __("Payment Tems"),
      fieldtype: "Data",
      hidden: 1,
    },
    {
      fieldname: "credit_limit",
      label: __("Credit Limit"),
      fieldtype: "Currency",
      hidden: 1,
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    if (data && data.bold) {
      value = value.bold();
    }
    return value;
  },
  /*onload: function (report) {
    report.page.add_inner_button(__("Accounts Receivable Summary"), function () {
      var filters = report.get_values();
      frappe.set_route("query-report", "Accounts Receivable Summary", { company: filters.company });
    });
  },*/
};

erpnext.utils.add_dimensions("Accounts Receivable", 9);

function get_end_date(report = "") {
  let num_dias_mes = 0;
  let to_date = 0;

  if (report != "") {
    // Obtenemos el ultimo dia del mes actual, para el filtro de fecha final
    num_dias_mes =
      new Date(report.filters[1].value.substring(0, 4), report.filters[1].value.substring(5, 7), 0).getDate() -
      report.filters[1].value.substring(8, 10);

    // Agregamos los días del mes actual, para obtener el ultimo dia del mes.
    to_date = frappe.datetime.add_days(report.filters[1].value, num_dias_mes);
  } else {
    // Obtenemos el ultimo dia del mes actual, para el filtro de fecha final
    num_dias_mes =
      new Date(frappe.datetime.get_today().substring(0, 4), frappe.datetime.get_today().substring(5, 7), 0).getDate() -
      frappe.datetime.get_today().substring(8, 10);

    // Agregamos los días del mes actual, para obtener el ultimo dia del mes.
    to_date = frappe.datetime.add_days(frappe.datetime.get_today(), num_dias_mes);
  }

  return to_date;
}
