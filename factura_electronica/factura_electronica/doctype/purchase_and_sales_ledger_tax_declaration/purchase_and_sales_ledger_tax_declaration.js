// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase and Sales Ledger Tax Declaration', {

    refresh: function (frm) {
        frm.get_field("generate").$input.addClass("btn btn-primary btn-lg btn-block");
        frm.get_field("verify").$input.addClass("btn btn-warning btn-lg btn-block");
    }

});
