// Copyright (c) 2017, Frappe and contributors
// For license information, please see license.txt

// SECCION SERIES FEL
frappe.ui.form.on('Configuracion Factura Electronica', {
    // en-US # Upon form refresh
    // es-GT # Al refrescar el formulario
    setup: function (frm) {
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
                // console.log("esto se asigno", r.message)
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
    tipo_frase(frm, cdt, cdn) {
        // limpia los cambios codigo_escenario, descripcion_codigo_escenario, cada
        // vez que se cambia el valor de tipo frase, aplica para el resto de abajo
        let row = frappe.get_doc(cdt, cdn);
        row.codigo_escenario = ''
        row.descripcion_codigo_escenario = ''
        row.descripcion_especifica = ''

        refresh_field("series_fel");
    },
    codigo_escenario(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_description_phrase_fel",
            args: {
                frase_catalogo: row.tipo_frase,
                codigo_frase_hija: row.codigo_escenario
            },
            callback: function (r) {
                // console.log(r.message);

                row.descripcion_codigo_escenario = r.message.descr;
                row.descripcion_especifica = r.message.descr_especi;
                cur_frm.refresh_field('descripcion_codigo_escenario');
                cur_frm.refresh_field('descripcion_especifica');

                refresh_field("series_fel");
            }
        });
    },
    codigo_escenario_factura_especial(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_description_phrase_fel",
            args: {
                frase_catalogo: row.tipo_frase_factura_especial,
                codigo_frase_hija: row.codigo_escenario_factura_especial
            },
            callback: function (r) {
                // console.log(r.message);

                row.descripcion_codigo_escenario_factura_especial = r.message.descr;
                cur_frm.refresh_field('descripcion_codigo_escenario_factura_especial');

                refresh_field("series_fel");
            }
        });
    },
    tipo_frase_factura_exportacion(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        row.codigo_escenario_factura_exportacion = ''
        row.descripcion_codigo_escenario_factura_exportacion = ''
        row.descripcion_especifica_factura_exportacion = ''

        refresh_field("series_fel");
    },
    codigo_escenario_factura_exportacion(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_description_phrase_fel",
            args: {
                frase_catalogo: row.tipo_frase_factura_exportacion,
                codigo_frase_hija: row.codigo_escenario_factura_exportacion
            },
            callback: function (r) {
                // console.log(r.message);

                row.descripcion_codigo_escenario_factura_exportacion = r.message.descr;
                row.descripcion_especifica_factura_exportacion = r.message.descr_especi;
                cur_frm.refresh_field('descripcion_codigo_escenario_factura_exportacion');
                cur_frm.refresh_field('descripcion_especifica_factura_exportacion');

                refresh_field("series_fel");
            }
        });
    },
    tipo_frase_factura_exenta(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        row.codigo_escenario_factura_exenta = ''
        row.descripcion_codigo_escenario_factura_exenta = ''
        row.descripcion_especifica_factura_exenta = ''

        refresh_field("series_fel");
    },
    codigo_escenario_factura_exenta(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_description_phrase_fel",
            args: {
                frase_catalogo: row.tipo_frase_factura_exenta,
                codigo_frase_hija: row.codigo_escenario_factura_exenta
            },
            callback: function (r) {
                // console.log(r.message);

                row.descripcion_codigo_escenario_factura_exenta = r.message.descr;
                row.descripcion_especifica_factura_exenta = r.message.descr_especi;
                cur_frm.refresh_field('descripcion_codigo_escenario_factura_exenta');
                cur_frm.refresh_field('descripcion_especifica_factura_exenta');

                refresh_field("series_fel");
            }
        });
    }
});


frappe.ui.form.on('Serial Configuration For Purchase Invoice', {
    tipo_frase_factura_especial(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        row.codigo_escenario_factura_especial = ''
        row.descripcion_codigo_escenario_factura_especial = ''
        row.descripcion_especifica_factura_especial = ''

        refresh_field("purchase_invoice_series");
    },
    codigo_escenario_factura_especial(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        frappe.call({
            method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_description_phrase_fel",
            args: {
                frase_catalogo: row.tipo_frase_factura_especial,
                codigo_frase_hija: row.codigo_escenario_factura_especial
            },
            callback: function (r) {
                // console.log(r.message);

                row.descripcion_codigo_escenario_factura_especial = r.message.descr;
                row.descripcion_especifica_factura_especial = r.message.descr_especi;
                cur_frm.refresh_field('descripcion_codigo_escenario_factura_especial');
                cur_frm.refresh_field('descripcion_especifica_factura_especial');

                refresh_field("purchase_invoice_series");
            }
        });
    }
});