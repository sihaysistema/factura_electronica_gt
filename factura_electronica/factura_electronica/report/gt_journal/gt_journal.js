// Copyright (c) 2016, Si Hay Sistema and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GT Journal"] = {
    "filters": [
        {
            "fieldname":"",
            "label":__(""),
            "fieltype":"",
            "options":"",
            "default":"",
            "reqd":1,
            on_change: function () {
                frappe.db.get_value('Company', frappe.query_report.get_filter_value('company'), 'tax_id')
                    .then(r => {
                        // console.log(r.message.name)
                        frappe.query_report.set_filter_value('nit', r.message.tax_id);
                        frappe.db.get_value('Company', frappe.query_report.get_filter_value('company'), 'default_currency')
                            .then(r => {
                                frappe.query_report.set_filter_value('company_currency', r.message.default_currency);
                            })
                    })
            }
        },
        {
            "fieldname":"tipo_poliza",
            "label":__("Tipo Póliza"),
            "fieltype":"Link",
            "options":"Tipo Poliza",
            // "default":"",
            // "reqd":1
        },
        {
            "fieldname":"from_date",
            "label":__("From Date"),
            "fieltype":"Date",
            // "options":"",
            "default":frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd":1,
            "width":"60px"
        },
        {
            "fieldname":"to_date",
            "label":__("To Date"),
            "fieltype":"Date",
            // "options":"",
            "default":frappe.datetime.get_today(),
            "reqd":1,
            "width":"60px"
        },
        {
            "fieltype":"Break",
        },
        {
            "fieldname":"nit",
            "label":__("NIT"),
            "fieltype":"Data",
            "default":"",
            "read_only":1
        },
        {
            "fieldname":"company_currency",
            "label":__("Company Default Currency"),
            "fieltype":"Select",
            "options":erpnext.get_presentation_currency_list(),
            "default":"",
            "read_only":1
        }
    ]
};
