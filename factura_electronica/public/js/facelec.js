frappe.ui.form.on("Sales Invoice", "refresh", function(frm) {
    // es-GT: Obtiene el numero de Identificacion tributaria ingresado en la hoja del cliente.
    // en-US: Fetches the Taxpayer Identification Number entered in the Customer doctype.
    cur_frm.add_fetch("customer", "nit_face_customer", "nit_face_customer");

    function pdf_button() {
        frappe.call({
            // Este metodo verifica, el modo de generacion de PDF para la factura electronica
            // retornara 'Manul' o 'Automatico'
            method: "factura_electronica.api.save_url_pdf",

            callback: function(data) {

                if (data.message === 'Manual') {
                    // Si en la configuracion se encuentra que la generacion de PDF debe ser manual
                    // Se realizara lo siguiente
                    //cur_frm.clear_custom_buttons();
                    console.log(data.message);
                    frm.add_custom_button(__("Obtener PDF"),
                        function() {
                            var cae_fac = frm.doc.cae_factura_electronica;
                            var link_cae_pdf = "https://www.ingface.net/Ingfacereport/dtefactura.jsp?cae=";
                            //console.log(cae_fac)
                            window.open(link_cae_pdf + cae_fac);
                        }).addClass("btn-primary");
                } else {
                    // Si en la configuracion se encuentra que la generacion de PDF debe ser Automatico
                    // Se realizara lo siguiente
                    console.log(data.message);
                    var cae_fac = frm.doc.cae_factura_electronica;
                    var link_cae_pdf = "https://www.ingface.net/Ingfacereport/dtefactura.jsp?cae=";

                    frappe.call({
                        method: "factura_electronica.api.save_pdf_server",
                        args: {
                            file_url: link_cae_pdf + cae_fac,
                            filename: frm.doc.name,
                            dt: 'Sales Invoice',
                            dn: frm.doc.name,
                            folder: 'Home/Facturas Electronicas',
                            is_private: 1
                        }
                    });

                }
            }
        });
    }

    // Codigo para Factura Electronica FACE, CFACE
    if (frm.doc.status === "Paid" || frm.doc.status === "Unpaid" || frm.doc.status === "Submitted" || frm.doc.status === "Overdue") {
        if (frm.doc.cae_factura_electronica) {
            cur_frm.clear_custom_buttons();
            pdf_button();
        } else {
            var nombre = 'Factura Electronica';
            frm.add_custom_button(__(nombre), function() {
                frappe.call({
                    method: "factura_electronica.api.generar_factura_electronica",
                    args: {
                        serie_factura: frm.doc.name,
                        nombre_cliente: frm.doc.customer
                    },
                    callback: function(data) {

                        cur_frm.set_value("cae_factura_electronica", data.message);

                        if (frm.doc.cae_factura_electronica) {
                            cur_frm.clear_custom_buttons();
                            pdf_button();
                        }
                    }
                });
            }).addClass("btn-primary");
        }
    }

    // Codigo para Notas de Credito NCE
    if (frm.doc.status === "Return") {
        //var nombre = 'Nota Credito';
        if (frm.doc.cae_nota_de_credito) {
            cur_frm.clear_custom_buttons();
            pdf_button();
        } else {
            frm.add_custom_button(__('Nota Credito'), function() {
                frappe.call({
                    method: "factura_electronica.api.generar_factura_electronica",
                    args: {
                        serie_factura: frm.doc.name,
                        nombre_cliente: frm.doc.customer
                    },
                    callback: function(data) {
                        cur_frm.set_value("cae_nota_de_credito", data.message);
                        if (frm.doc.cae_nota_de_credito) {
                            cur_frm.clear_custom_buttons();
                            pdf_button();
                        }
                    }
                });
            }).addClass("btn-primary");
        }
    }
});


// es-GT: Obtiene un valor para un campo que pertenece a la Tabla Hija "Sales Invoice Item" o "Producto de la Factura de Venta"
// en-US: Code for fetching a value for a field within the Child Table "Sales Invoice Item"
frappe.ui.form.on("Sales Invoice", "refresh", function(frm) {
    frappe.ui.form.on("Sales Invoice Item", {
        "item_code": function item_code(frm, cdt, cdn) {
            frm.add_fetch("item_code", "tax_rate_per_uom", "tasa_otro_impuesto");

            var d = locals[cdt][cdn];
            //var total = 0;
            //frappe.model.set_value(d.doctype, d.name, "importe_otros_impuestos", (d.amount * 2));
            //frm.doc.table.forEach(function(d) { total += d.area; });
            //frm.set_value('valor_otro_impuesto', (d.amount * 2));
            //cur_frm.refresh();
        }
    });
});

/*
frappe.ui.form.on("Sales Invoice", "refresh", function(frm) {
    frm.add_fetch("item_code", "tax_rate_per_uom", "tasa_otro_impuesto");
});
*/