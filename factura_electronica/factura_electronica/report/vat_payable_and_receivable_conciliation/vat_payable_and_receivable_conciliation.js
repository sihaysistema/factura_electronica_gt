// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["VAT Payable and Receivable Conciliation"] = {
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
            default: get_start_yr_mo().month,
            options: [__("January"), __("February"), __("March"), __("April"),
            __("May"), __("June"), __("July"), __("August"), __("September"), __("October"),
            __("November"), __("December")],
            reqd: 1,
        },
        {
            fieldname: "year",
            label: __("Year"),
            default: get_start_yr_mo().year,
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
        report.page.add_inner_button(__("Generate Journal Entry"), function () {
            // window.open("/api/method/factura_electronica.api_erp.download_asl_files");
            window.open("sihaysistema.com", "_blank");
        });
    },
};

function get_start_yr_mo() {
    var today = new Date(); // Obtiene la fecha actual
    const word_month = {
        1: __("January"),
        2: __("February"),
        3: __("March"),
        4: __("April"),
        5: __("May"),
        6: __("June"),
        7: __("July"),
        8: __("August"),
        9: __("September"),
        10: __("October"),
        11: __("November"),
        12: __("December")
    };
    var yr_mo = {
        "year": today.getFullYear(),
        "month": word_month[today.getMonth()+1],
    }
    return yr_mo;
};

/*
var today = new Date();
var dd = today.getDate();
var mm = today.getMonth()+1;
var yyyy = today.getFullYear();
if(dd<10){
    dd='0'+dd;
} 
if(mm<10){
    mm='0'+mm;
} 
var today = dd+'-'+mm+'-'+yyyy;
*/