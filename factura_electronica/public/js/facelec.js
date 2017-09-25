frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {

        if (frm.doc.status === "Submitted" || frm.doc.status === "Unpaid") {
            frm.add_custom_button(__('Factura Electronica'), function() {
                frappe.call({
                    method: "factura_electronica.api.generar_factura_electronica",
                    args: {
                        serie_factura: frm.doc.name,
                        nombre_cliente: frm.doc.customer
                    },
                })
            }).addClass("btn-primary");
        }
    }
});