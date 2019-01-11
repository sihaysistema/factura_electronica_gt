// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Impuestos Especiales', {
	refresh: function (frm) {
		// Aplica para Purchase Invoice
		frappe.call({
			method: "factura_electronica.factura_electronica.doctype.impuestos_especiales.impuestos_especiales.series_factura_especial",

			callback: function (r) {
				// console.log(r.message);
				frappe.meta.get_docfield('Series Factura Especial', 'serie', cur_frm.doc.name).options = r.message
				cur_frm.refresh_field('serie');
			}
		});
	}
});
