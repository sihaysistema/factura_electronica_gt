// Copyright (c) 2021, Si Hay Sistema and contributors
// For license information, please see license.txt

frappe.ui.form.on('Combination Of Phrases', {
    // es_para_la_compra: function (frm) {
    //     if (frm.doc.es_para_la_compra == 1) {
    //         // Se oculta
    //         cur_frm.toggle_display("es_exportacion", false);
    //         // cur_frm.toggle_display("combinacion_de_frase_section", false);

    //         // Se resetean los valores
    //         frm.set_value('codigo_incoterm', '');

    //         frm.set_value('tipo_frase', '');
    //         frm.set_value('descripcion_de_codigo_de_frase', '');
    //         frm.set_value('codigo_de_escenario', '');
    //         frm.set_value('descripcion_codigo_de_escenario', '');
    //         frm.set_value('descripcion_especifica', '');
    //     } else {
    //         // Se muestra
    //         cur_frm.toggle_display("es_exportacion", true);
    //         // cur_frm.toggle_display("combinacion_de_frase_section", true);
    //     }
    // },
    // es_exportacion: function (frm) {
    //     if (frm.doc.es_exportacion == 0) {
    //         // Se oculta
    //         cur_frm.toggle_display("frase_para_exportacion_section", false);
    //         // se muestra
    //         cur_frm.toggle_display("combinacion_de_frase_section", true);

    //         // Se resetean los valores
    //         frm.set_value('codigo_incoterm', '')
    //     } else {
    //         // Se muestra
    //         cur_frm.toggle_display("frase_para_exportacion_section", true);
    //         // se oculta
    //         cur_frm.toggle_display("combinacion_de_frase_section", false);

    //         // Se resetean los valores
    //         frm.set_value('tipo_frase', '');
    //         frm.set_value('descripcion_de_codigo_de_frase', '');
    //         frm.set_value('codigo_de_escenario', '');
    //         frm.set_value('descripcion_codigo_de_escenario', '');
    //         frm.set_value('descripcion_especifica', '');
    //     }
    // },
    // tipo_frase(frm, cdt, cdn) {
    //     // limpia los cambios codigo_de_escenario, descripcion_codigo_escenario, cada
    //     // vez que se cambia el valor de tipo frase, aplica para el resto de abajo
    //     let row = frappe.get_doc(cdt, cdn);
    //     row.descripcion_de_codigo_de_frase = ''
    //     row.codigo_de_escenario = ''
    //     row.descripcion_codigo_de_escenario = ''
    //     row.descripcion_especifica = ''

    //     frm.refresh();
    // },
    // codigo_de_escenario(frm, cdt, cdn) {
    //     let row = frappe.get_doc(cdt, cdn);
    //     let urlReq = "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_description_phrase_fel";

    //     frappe.call({
    //         method: urlReq,
    //         args: {
    //             frase_catalogo: row.tipo_frase,
    //             codigo_frase_hija: row.codigo_de_escenario
    //         },
    //         callback: function (r) {
    //             row.descripcion_codigo_de_escenario = r.message.descr;
    //             row.descripcion_especifica = r.message.descr_especi;
    //             cur_frm.refresh_field('descripcion_codigo_de_escenario');
    //             cur_frm.refresh_field('descripcion_especifica');

    //             frm.refresh();
    //         }
    //     });
    // },
});


frappe.ui.form.on('FEL Combinations', {
    tipo_frase(frm, cdt, cdn) {
        // limpia los cambios codigo_de_escenario, descripcion_codigo_escenario, cada
        // vez que se cambia el valor de tipo frase, aplica para el resto de abajo
        let row = frappe.get_doc(cdt, cdn);
        row.descripcion_de_codigo_de_frase = ''
        row.codigo_de_escenario = ''
        row.descripcion_codigo_de_escenario = ''
        row.descripcion_especifica = ''

        frm.refresh();
    },
    codigo_de_escenario(frm, cdt, cdn) {
        // Obtiene las descripciones de la frase y el escenario
        let row = frappe.get_doc(cdt, cdn);
        let urlReq = "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.get_description_phrase_fel";

        frappe.call({
            method: urlReq,
            args: {
                frase_catalogo: row.tipo_frase,
                codigo_frase_hija: row.codigo_de_escenario
            },
            callback: function (r) {
                row.descripcion_codigo_de_escenario = r.message.descr;
                row.descripcion_especifica = r.message.descr_especi;
                cur_frm.refresh_field('descripcion_codigo_de_escenario');
                cur_frm.refresh_field('descripcion_especifica');

                frm.refresh();
            }
        });
    },
});