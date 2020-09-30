// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('VAT Declaration', {
    validate: function (frm) {
        get_total(frm);
    }
});


frappe.ui.form.on('Invoice Declaration', {
    declaration_items_add: function (frm) {
        get_total(frm);
    },
    declaration_items_remove: function (frm) {
        get_total(frm);
    },
    link_doctype: function (frm) {
        get_total(frm);
    },
    link_name: function (frm) {
        get_total(frm);
    },
});



/**
 * Llama al server para obtener un total mas preciso de las facturas que se estan trabajando
 * una vez se tiene el total se guardar en el campo `total`, este calculo se hace realtime
 * en funcion a los eventos arriba escritos
 *
 * @param {object} frm
 */
function get_total(frm) {
    frappe.call({
        method: 'factura_electronica.factura_electronica.doctype.vat_declaration.vat_declaration.calculate_total',
        args: {
            invoices: frm.doc.declaration_items || []
        },
        freeze: false,
        callback: (r) => {
            // on success
            frm.set_value('total', r.message);
            frm.refresh_field('total');
            // frm.refresh();
        }
    });
}