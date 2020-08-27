// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Batch Electronic Invoice', {
    refresh: function (frm) {

        frm.set_intro(__(
            '<b>Si el estatus de las facturas persiste como no generadas, se recomienda ir factura por factura generando factura electronica, tambien se recomienda un maximo de 1000 facturas por lote</b>'
        ));

        // Validador de funcion, que muestra el boton de import payments SOLAMENTE despues de Guardado.

        // Agrega clase bootstrap al boton
        frm.get_field("validate_invoices").$input.addClass("btn btn-primary");

        // Verifica si todas las facturas se encuentran validadas para mostrar el boton
        // que permite una generacion masiva de facturas electronicas
        frappe.call(
            'factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice.verify_validated_invoices', {
            invoices: frm.doc.batch_invoices || []
        }).then(r => {
            if (r.message === true) {
                fel_generator(frm);
            }
        })

        // Si hay datos en el campo details, el evento leera esa data, y la renderizara en una tabla HTML
        if (frm.doc.details) {
            frm.events.create_log_table(frm);
        } else {
            $(frm.fields_dict.log_table.wrapper).empty();
        }

    },
    validate_invoices: function (frm) {
        // Validacion a todas las facturas que se encuentren en la tabla hija
        frappe.call({
            method: 'factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice.submit_invoice',
            args: {
                invoices: frm.doc.batch_invoices || []
            },
            callback: function (r) {
                console.log(r.message);
                frm.reload_doc();
            },
        });
    },
    create_log_table: function (frm) {
        // NOTA: Usar esta funcionalidad cuando se almacene data de log en base de datos
        // Conversion a json y renderizado de template mostrando detalles de template
        let msg = JSON.parse(frm.doc.details);
        var $log_wrapper = $(frm.fields_dict.log_table.wrapper).empty();

        $(frappe.render_template("log", {
            data: msg
        })).appendTo($log_wrapper);

    },
});


function fel_generator(frm) {
    frm.add_custom_button(__("Generate Electronic Invoice"), function () {

        frappe.call({
            method: 'factura_electronica.factura_electronica.doctype.batch_electronic_invoice.batch_electronic_invoice.electronic_invoices_batch',
            args: {
                invoice_list: frm.doc.batch_invoices || [],
                doc_name: frm.doc.name,
                doct: frm.doc.doctype
            },
            callback: function (r) {
                // console.log(r.message);
                frm.reload_doc();
            },
        });

    }).addClass("btn-primary");
}