// Copyright (c) 2017, Frappe and contributors
// For license information, please see license.txt

// SECCION SERIES FEL
frappe.ui.form.on('Configuracion Factura Electronica', {
    // en-US # Upon form refresh
    // es-GT # Al refrescar el formulario
    setup: function (frm) {
        // en-US # Call the python method indicated
        // es-GT # Llame al modulo python indicado

        // NOTE: Llamados a funcion python para obtener los `naming_series` configurados
        // para Sales Invoice y Purchase Invoice

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
                refresh_field("series_fel");
            }
        });

        // Aplica para series FEL - Sales invoice
        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.series_sales_invoice",
            callback: function (r) {
                frappe.meta.get_docfield('Configuracion Series FEL', 'serie', cur_frm.doc.name).options = r.message
                // console.log("esto se asigno", r.message)
                cur_frm.refresh_field('serie');
                refresh_field("series_fel");
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
                refresh_field("purchase_invoice_series");
            }
        });

    }
});


frappe.ui.form.on('Configuracion Series FEL', {
    es_exportacion(frm, cdt, cdn) {
        // Obtiene los detalles de la fila seleccionada
        let row = frappe.get_doc(cdt, cdn);

        if (row.es_exportacion == 1) {
            // Se limpia el valor del campo
            row.combination_of_phrases = "";
            refresh_field("series_fel");
        } else {
            // Se limpia el valor del campo
            row.codigo_incoterm = "";
            refresh_field("series_fel");
        }
    },
});


// Forma antigua de usar frases, cuando solo se podia selecciona 1 frase
// frappe.ui.form.on('Serial Configuration For Purchase Invoice', {
//     tipo_frase_factura_especial(frm, cdt, cdn) {
//         let row = frappe.get_doc(cdt, cdn);
//         row.codigo_escenario_factura_especial = ''
//         row.descripcion_codigo_escenario_factura_especial = ''
//         row.descripcion_especifica_factura_especial = ''

//         refresh_field("purchase_invoice_series");
//     },
//     codigo_escenario_factura_especial(frm, cdt, cdn) {
//         let row = frappe.get_doc(cdt, cdn);

//         frappe.call({
//             method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_description_phrase_fel",
//             args: {
//                 frase_catalogo: row.tipo_frase_factura_especial,
//                 codigo_frase_hija: row.codigo_escenario_factura_especial
//             },
//             callback: function (r) {
//                 // console.log(r.message);

//                 row.descripcion_codigo_escenario_factura_especial = r.message.descr;
//                 row.descripcion_especifica_factura_especial = r.message.descr_especi;
//                 cur_frm.refresh_field('descripcion_codigo_escenario_factura_especial');
//                 cur_frm.refresh_field('descripcion_especifica_factura_especial');

//                 refresh_field("purchase_invoice_series");
//             }
//         });
//     }
// });