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

		// Aplica para series FEL
		frappe.call({
			method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.series_sales_invoice",
			callback: function (r) {
				frappe.meta.get_docfield('Configuracion Series FEL', 'serie', cur_frm.doc.name).options = r.message
				cur_frm.refresh_field('serie');
			}
		});

		// Aplica para Purchase Invoice
		frappe.call({
			method: "factura_electronica.factura_electronica.doctype.configuracion_factura_electronica.configuracion_factura_electronica.series_factura_especial",

			callback: function (r) {
				// console.log(r.message);
				frappe.meta.get_docfield('Series Factura Especial', 'serie', cur_frm.doc.name).options = r.message
				cur_frm.refresh_field('serie');
			}
		});
	}
});