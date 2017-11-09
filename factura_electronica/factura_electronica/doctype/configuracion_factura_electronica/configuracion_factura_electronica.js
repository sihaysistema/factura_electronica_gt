// Copyright (c) 2017, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Configuracion Factura Electronica', {
    refresh: function(frm) {

        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.series_sales_invoice",
            callback: function(r) {
                frappe.meta.get_docfield('Configuracion Series', 'serie', cur_frm.doc.name).options = r.message
                cur_frm.refresh_field('serie');
            }
        });

    }
});