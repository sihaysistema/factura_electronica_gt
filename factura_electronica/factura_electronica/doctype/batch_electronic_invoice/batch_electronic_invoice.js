// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Batch Electronic Invoice', {
    refresh: function (frm) {

        // frm.set_intro(__(
        //     'NOTA PARA GENERADOR DE LOTES'
        // ));
        // Validador de funcion, que muestra el boton de import payments SOLAMENTE despues de Guardado.

        // Agrega clase bootstrap al boton
        frm.get_field("validate_invoices").$input.addClass("btn btn-primary");


        fel_generator(frm);
    },
    validate_invoices: function (frm) {
        // Validacion a todas las facturas que se encuentren en la tabla hija
        frappe.call({
            method: 'factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice.submit_invoice',
            args: {
                invoices: frm.doc.batch_invoices
            },
            callback: function (r) {
                console.log(r.message);
            },
        });
    }
});


function fel_generator(frm) {
    frm.add_custom_button(__("Generate Electronic Invoice"), function () {

        // frappe.call({
        //     method: 'factura_electronica.batch_api.test_function',
        //     args: {
        //         references: frm.doc.expenses,
        //         docname: frm.doc.name,
        //     },
        //     callback: function (r) {
        //         frm.reload_doc();
        //     },
        // });

    }).addClass("btn-primary");
}