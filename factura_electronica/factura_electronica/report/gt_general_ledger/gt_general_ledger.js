// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GT General Ledger"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": "",
            "reqd": 1,
            on_change: function () {
                frappe.db.get_value('Company', frappe.query_report.get_filter_value('company'), 'tax_id')
                    .then(r => {
                        console.log(r)
                        frappe.query_report.set_filter_value('nit', r.message.tax_id);
                        frappe.query_report.set_filter_value('tax_id', r.message.tax_id);
                    })
            }
        },
        {
            "fieldname": "finance_book",
            "label": __("Finance Book"),
            "fieldtype": "Link",
            "options": "Finance Book"
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1,
            "width": "60px"
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1,
            "width": "60px"
        },
        {
            "fieldname": "account",
            "label": __("Account"),
            "fieldtype": "Link",
            "options": "Account",
            "get_query": function () {
                var company = frappe.query_report.get_filter_value('company');
                return {
                    "doctype": "Account",
                    "filters": {
                        "company": company,
                    }
                }
            }
        },
        {
            "fieldtype": "Break",
        },
        {
            "fieldname": "party_type",
            "label": __("Party Type"),
            "fieldtype": "Link",
            "options": "Party Type",
            "default": "",
            on_change: function () {
                frappe.query_report.set_filter_value('party', "");
            }
        },
        {
            "fieldname": "party",
            "label": __("Party"),
            "fieldtype": "MultiSelectList",
            get_data: function (txt) {
                if (!frappe.query_report.filters) return;

                let party_type = frappe.query_report.get_filter_value('party_type');
                if (!party_type) return;

                return frappe.db.get_link_options(party_type, txt);
            },
            on_change: function () {
                var party_type = frappe.query_report.get_filter_value('party_type');
                var parties = frappe.query_report.get_filter_value('party');

                if (!party_type || parties.length === 0 || parties.length > 1) {
                    frappe.query_report.set_filter_value('party_name', "");
                    frappe.query_report.set_filter_value('tax_id', "");
                    return;
                } else {
                    var party = parties[0];
                    var fieldname = erpnext.utils.get_party_name(party_type) || "name";
                    frappe.db.get_value(party_type, party, fieldname, function (value) {
                        frappe.query_report.set_filter_value('party_name', value[fieldname]);
                    });

                    if (party_type === "Customer" || party_type === "Supplier") {
                        frappe.db.get_value(party_type, party, "tax_id", function (value) {
                            frappe.query_report.set_filter_value('tax_id', value["tax_id"]);
                        });
                    }
                }
            }
        },
        {
            "fieldname": "party_name",
            "label": __("Party Name"),
            "fieldtype": "Data",
            "hidden": 1
        },
        {
            "fieldname": "group_by",
            "label": __("Group by"),
            "fieldtype": "Select",
            "options": ["", __("Group by Voucher"), __("Group by Voucher (Consolidated)"),
                __("Group by Account"), __("Group by Party")],
            "default": __("Group by Voucher (Consolidated)")
        },
        {
            "fieldname": "tax_id",
            "label": __("Tax Id"),
            "fieldtype": "Data",
            "hidden": 1
        },
        {
            "fieldname": "presentation_currency",
            "label": __("Currency"),
            "fieldtype": "Select",
            "options": erpnext.get_presentation_currency_list()
        },
        {
            "fieldname": "cost_center",
            "label": __("Cost Center"),
            "fieldtype": "MultiSelectList",
            get_data: function (txt) {
                return frappe.db.get_link_options('Cost Center', txt);
            }
        },
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "MultiSelectList",
            get_data: function (txt) {
                return frappe.db.get_link_options('Project', txt);
            }
        },
        {
            "fieldname": "show_opening_entries",
            "label": __("Show Opening Entries"),
            "fieldtype": "Check"
        },
        {
            "fieldname": "include_default_book_entries",
            "label": __("Include Default Book Entries"),
            "fieldtype": "Check",
            "default": 1
        },
        {
            "fieldname": "nit",
            "label": __("NIT"),
            "fieldtype": "Data",
            "default": "",
            "read_only": 1
        },
    ]
};

erpnext.utils.add_dimensions('GT General Ledger', 15)