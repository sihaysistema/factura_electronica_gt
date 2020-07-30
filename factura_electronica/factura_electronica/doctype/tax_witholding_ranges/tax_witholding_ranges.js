// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tax Witholding Ranges', {
    refresh: function (frm) {
        // Agregando filtros
        frm.set_query('isr_account_payable', () => {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });

        frm.set_query('iva_account_payable', () => {
            return {
                filters: {
                    company: frm.doc.company
                }
            }
        });
    }
});
