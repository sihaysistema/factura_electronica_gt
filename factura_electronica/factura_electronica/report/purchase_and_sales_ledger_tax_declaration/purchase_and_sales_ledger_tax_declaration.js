// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Purchase and Sales Ledger Tax Declaration"] = {
    filters: [
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
                        frappe.db
                            .get_value(
                                "Company",
                                frappe.query_report.get_filter_value("company"),
                                "default_currency"
                            )
                            .then((r) => {
                                frappe.query_report.set_filter_value(
                                    "company_currency",
                                    r.message.default_currency
                                );
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
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            options: [__("January"), __("February"), __("March"), __("April"),
            __("May"), __("Jun"), __("July"), __("August"), __("September"),
            __("November"), __("December")],
            reqd: 1,
        },
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Link",
            options: "Fiscal Year",
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
            fieldname: "address",
            label: __("Address"),
            fieldtype: "Data",
            default: "",
            read_only: 1,
            hidden: 1,
        },
    ],
    onload: function (report) {
        report.page.add_inner_button(__("Download Excel"), function () {
            window.open("/api/method/factura_electronica.api_erp.download_asl");
            // window.open("sihaysistema.com", "_blank");
        });
    },
};
