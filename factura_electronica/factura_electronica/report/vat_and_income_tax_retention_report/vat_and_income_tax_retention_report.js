// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["VAT and Income Tax Retention Report"] = {
    "filters": [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: "",
            reqd: 1,
            on_change: function () {
                frappe.db
                    .get_value("Company", frappe.query_report.get_filter_value("company"), "tax_id")
                    .then((r) => {
                        // console.log(r.message.name)
                        frappe.query_report.set_filter_value("nit", r.message.tax_id);
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
            fieldname: "Tipo de Factura",
            label: __("tipo_de_factura"),
            fieldtype: "Select",
            options: ["", "Supplier", "Customer"],
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
    ]
};
