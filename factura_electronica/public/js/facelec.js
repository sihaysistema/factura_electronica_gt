frappe.ui.form.on("Sales Invoice", "refresh", function(frm) {
    // es-GT: Obtiene el numero de Identificacion tributaria ingresado en la hoja del cliente.
    // en-US: Fetches the Taxpayer Identification Number entered in the Customer doctype.
    cur_frm.add_fetch("customer", "nit_face_customer", "nit_face_customer");

    // Funcion para la obtencion del PDF, segun el documento generado.
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
    // El codigo se ejecutara segun el estado del documento, puede ser: Pagado, No Pagado, Validado, Atrasado
    if (frm.doc.status === "Paid" || frm.doc.status === "Unpaid" || frm.doc.status === "Submitted" || frm.doc.status === "Overdue") {
        // SI en el campo de 'cae_factura_electronica' ya se encuentra el dato correspondiente, ocultara el boton
        // para generar el documento, para luego mostrar el boton para obtener el PDF del documento ya generado.
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
                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                    callback: function(data) {
                        // Asignacion del valor retornado por el script python del lado del servidor en el campo
                        // 'cae_factura_electronica' para ser mostrado del lado del cliente y luego guardado en la DB
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
    // El codigo se ejecutara segun el estado del documento, puede ser: Retornar
    if (frm.doc.status === "Return") {
        //var nombre = 'Nota Credito';
        // SI en el campo de 'cae_nota_de_credito' ya se encuentra el dato correspondiente, ocultara el boton
        // para generar el documento, para luego mostrar el boton para obtener el PDF del documento ya generado.
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
                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                    callback: function(data) {
                        // Asignacion del valor retornado por el script python del lado del servidor en el campo
                        // 'cae_nota_de_credito' para ser mostrado del lado del cliente y luego guardado en la DB
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
	frappe.ui.form.on("Sales Invoice Item", {
	    // Cuando exista un cambio en la seleccion de codigo de producto, se ejecutara la funcion que recibe como parametros
	    // frm = El Formulario, cdt = Current Doctype, cdn = Current docname
		/*FIXME:  Por el momento, el usuario TIENE QUE Refrescar el campo de item_code, 
		desde la ventanita de Sales invoice Item para que funcione. Si lo refresca usando el
		grid edtiable de Sales Invoice Item mostrado en Sales invoice, no jala la data.
		Para arreglarlo el objetivo es como hacer trigger de tal forma, que sea irrelevante en donde
		actualiza, coloca, o simplemente LEE el Sales Invoice.
		*/
	    item_code: function(frm, cdt, cdn) {
			frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom");
	        // A la variable d se cargan todos los datos disponibles en el formulario
			// # Locals es un array, y los parametros [cdt][cdn] sirven para ubicar, los campos de este documento cargado en pantalla
	        // # Locals se refiere a los campos del documento actual en pantalla, o "local".
	        // # let es lo mismo que var
	        let d = locals[cdt][cdn];
	        //Para acceder a un campo en especifico, se colola:
	        // d.valor_de_campo_que_se_desea_saber
	        var monto = d.amount;
	        var cantidad = d.stock_qty;
			var prueba_impuesto = d.tax_rate_per_uom;
	        //frappe.msgprint(d);
	        console.log(d);
			//console.log("Usando trigger de Item code");
			console.log("El valor de impuesto es:" + prueba_impuesto);
	        // Agregar logica para realizar calculos
	        // frappe.model.set_value, establece un valor al campo que se desee
	        // recibe como parametros; frappe.model.set_value('doctype', 'docname', 'campo_a_asignar_valor', valor);
	        frappe.model.set_value(cdt, cdn, 'campo_de_prueba', flt(monto) * flt(cantidad));
	        cur_frm.refresh_fields();
	    },
	    uom: function(frm, cdt, cdn) {
	        let d = locals[cdt][cdn];

	        var monto = d.amount;
	        var cantidad = d.stock_qty;
	        //frappe.msgprint(d);
	        console.log(d);
			console.log("Usando trigger de UOM");

	        // Agregar logica para realizar calculos
	        frappe.model.set_value(cdt, cdn, 'campo_de_prueba', flt(monto) * flt(cantidad));
	        cur_frm.refresh_fields();
	    },
	    conversion_factor: function(frm, cdt, cdn) {
	        let d = locals[cdt][cdn];

	        var monto = d.amount;
	        var cantidad = d.stock_qty;
	        //frappe.msgprint(d);
	        console.log(d);
			console.log("Usando trigger de conversion_factor");
	        // Agregar logica para realizar calculos
	        frappe.model.set_value(cdt, cdn, 'campo_de_prueba', flt(monto) * flt(cantidad));
	        cur_frm.refresh_fields();
	    }

	});

});


// es-GT: Obtiene un valor para un campo que pertenece a la Tabla Hija "Sales Invoice Item" o "Producto de la Factura de Venta"
// en-US: Code for fetching a value for a field within the Child Table "Sales Invoice Item"
/*
    frappe.ui.form.on("Sales Invoice Item", "item_code", function(frm, cdt, cdn) {
        var resultado = locals[cdt][cdn];
        resultado = locals[cdt][cdn];
        var monto = resultado.amount;
        console.log(resultado);
        console.log(frm.doc.amount);
        frappe.model.set_value(cdt, cdn, 'campo_de_prueba', (flt(resultado.amount) * flt(2)))

    });
    */
/*
        item_code: function(frm, cdt, cdn) {
            var row = locals[cdt][cdn];
            console.log(row);
            console.log(row.item_code);
            console.log(row.item_name);
            console.log(row.amount);
            console.log(row.qty);
        }
 */



/*'item_code': function(frm) {
        var resultado = frm.doc.amount * 2;
        console.log(resultado);
        //cur_frm.set_value("campo_de_prueba", resultado);
        */
/*
frappe.ui.form.on("Sales Invoice", "refresh", function(frm) {
    frm.add_fetch("item_code", "tax_rate_per_uom", "tasa_otro_impuesto");
});
*/



