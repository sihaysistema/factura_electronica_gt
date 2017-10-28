// Copyright (c) 2017, Frappe and contributors
// For license information, please see license.txt
frappe.ui.form.on("Envios Facturas Electronicas", "ver_factura_original", function(frm) {
    frappe.set_route("Form", "Sales Invoice", frm.doc.serie_factura_original)
});

frappe.ui.form.on('Envios Facturas Electronicas', {
    refresh: function(frm) {
        frm.add_custom_button(__("Obtener PDF Factura Electronica"),
            function() {
                var cae_fac = frm.doc.cae;
                var link_cae_pdf = "https://www.ingface.net/Ingfacereport/dtefactura.jsp?cae=";
                window.open(link_cae_pdf + cae_fac);
            }).addClass("btn-primary");
    }
});