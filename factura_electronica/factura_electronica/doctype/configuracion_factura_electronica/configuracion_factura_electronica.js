// Copyright (c) 2017, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Configuracion Factura Electronica', {
    // en-US # Upon form refresh
    // es-GT # Al refrescar el formulario
    refresh: function (frm) {
        // en-US # Call the python method indicated
        // es-GT # Llame al modulo python indicado
        // Aplica para Sales Invoice
        frappe.call({
            // en-US # Call the series_sales_invoice  method.
            // es-GT # Llame al metodo  series_sales_invoice.
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.series_sales_invoice",
            // en-US # Obtains the field 'serie' from the Configuracion Series DocType
            // es-GT # Obtiene el campo 'serie' del DocType "Configuracion Series"
            callback: function (r) {
                frappe.meta.get_docfield('Configuracion Series', 'serie', cur_frm.doc.name).options = r.message
                // en-US # Updates the current form field 'serie' with the previously obtained data
                // es-GT # Actualiza el campo 'serie' del formulario actual, con la data obtenida anteriormente
                cur_frm.refresh_field('serie');
            }
        });

        // Aplica para series FEL - Sales invoice
        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.series_sales_invoice",
            callback: function (r) {
                frappe.meta.get_docfield('Configuracion Series FEL', 'serie', cur_frm.doc.name).options = r.message
                cur_frm.refresh_field('serie');
            }
        });

        // Aplica para Purchase Invoice
        // NOTA: Se esta usando la misma funcion de facturas especiales
        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.series_factura_especial",
            callback: function (r) {
                // console.log(r.message);
                frappe.meta.get_docfield('Serial Configuration For Purchase Invoice', 'serie', cur_frm.doc.name).options = r.message
                cur_frm.refresh_field('serie');
            }
        });

    }
});


frappe.ui.form.on('Configuracion Series FEL', {
    // cdt is Child DocType name i.e Quotation Item
    // cdn is the row name for e.g bbfcb8da6a
    tipo_frase(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        // console.log('Esto es row', row);

        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_phrases_fel",
            args: {
                code_type: row.tipo_frase
            },
            callback: function (r) {
                console.log(r.message.join("\n"));

                // frappe.meta.get_docfield('Configuracion Series FEL', 'codigo_escenario', frm.doc.name).options = r.message.join("\n")

                // const field = frappe.meta.get_docfield("Configuracion Series FEL", "codigo_escenario", frm.doc.name);
                // field.fieldtype = 'Select';
                // field.options = r.message.join("\n");

                // // frm.fields_dict.filter_fields.grid.refresh();

                // refresh_field("series_fel");
                // cur_frm.refresh_field('codigo_escenario');
            }
        });
    },
    codigo_escenario(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        // console.log('Esto es row', row);

        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_description_phrase_fel",
            args: {
                frase_catalogo: row.tipo_frase,
                codigo_frase_hija: row.codigo_escenario
            },
            callback: function (r) {
                console.log(r.message);
                row.descripcion_codigo_escenario = r.message;
                cur_frm.refresh_field('descripcion_codigo_escenario');
                refresh_field("series_fel");
            }
        });
    }
})