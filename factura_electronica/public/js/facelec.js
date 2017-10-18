//cur_frm.add_fetch("customer", "nit", "nit");
frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {

        frappe.call({
            method: "factura_electronica.obtener_cae.obtenerDatoSales",
            args: {
                factura: frm.doc.name
            },
            callback: function(r) {
                //console.log(r);
                //frappe.msgprint(r);
                frm.doc.cae_factura_electronica = r.message
            }
        })
    }
});

frappe.ui.form.on("Sales Invoice", {

    refresh: function(frm) {

        if ((frm.doc.status === "Paid" || frm.doc.status === "Unpaid" || frm.doc.status === "Submitted")) {
            if (frm.doc.cae_factura_electronica != " ") {
                //frappe.msgprint("BOTON OCULTADO");
                cur_frm.clear_custom_buttons();
            } else {
                frm.add_custom_button(__('Factura Electronica'), function() {
                    frappe.call({
                        method: "factura_electronica.api.generar_factura_electronica",
                        args: {
                            serie_factura: frm.doc.name,
                            nombre_cliente: frm.doc.customer
                        },
                        callback: function(r) {
                            //console.log(r);
                            //frappe.msgprint(r);
                            //frm.doc.cae = r.message
                            frm.reload_doc()
                        }
                    })
                }).addClass("btn-primary");
            }
        }

    }
});