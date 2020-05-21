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
    }
});


function fel_generator(frm) {
    frm.add_custom_button(__("Generate Electronic Invoice"), function () {
        // frappe.call({
        //     method: "factura_electronica.batch_api.test_function",
        //     args: {
        //         references: frm.doc.expenses,
        //         docname: frm.doc.name,
        //         compa: frm.doc.company,
        //         posting_date: frm.doc.posting_date,
        //         je_reference: frm.doc.journal_entry_reference || "",
        //     },
        //     callback: function (r) {
        //         frm.reload_doc();
        //     },
        // });
    }).addClass("btn-primary");
}