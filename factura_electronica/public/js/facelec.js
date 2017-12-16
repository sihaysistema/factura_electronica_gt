/* frappe.ui.form.on("Sales Invoice", "refresh", function(frm){});*/

frappe.ui.form.on("Sales Invoice", {
	onload: function(frm) {
		// Esta funcion se llama cuando se carga el sales invoice item.  FUNCIONA OK
		//console.log("AFUERA: Se acaba de correr onload de Sales Invoice");
	},
	onload_post_render: function(frm) {
		// Esta funcion se llama cuando se carga el sales invoice item, despues de hacer render FUNCIONA OK
		//console.log("AFUERA: Se acaba de correr onload_post_render de Sales Invoice");
		//frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom");
	},
		
});

frappe.ui.form.on("Sales Invoice Item", {
	// When loading the Sales Invoice Items
	onload: function(frm, cdt, cdn) {
		// Fetch the tax rate per unit of measure using item_code as primary key
		
		/* frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom");
		console.log("Se acaba de cargar el impuesto por unidad de medida");
		// Since we have  the field with data, we can pull it onto a variable
		var test_variable = frm.doc.tax_rate_per_uom;
		console.log("La variable ahora contiene " + test_variable); */
		// A la variable d se cargan todos los datos disponibles en el formulario (dialogo)
		// # Locals es un array, y los parametros [cdt][cdn] sirven para ubicar, los campos de este documento cargado en pantalla
		// # Locals se refiere a los campos del documento actual en pantalla, o "local".
        // # let es lo mismo que var
		//var formulario = locals[cdt][cdn];
		//var cantidad = formulario.stock_qty;
	},
	
	refresh: function(frm, cdt, cdn) {
		// Esta funcion se llama cuando se refresca el sales invoice item line
		console.log("Item tax pulled upon refresh trigger");

		// Since javascript is asynchronous, we cannot add to a variable before fetching
		//frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom");
		// Since we have  the field with data, we can pull it onto a variable
		//var test_variable = frm.doc.tax_rate_per_uom;
		//console.log(" the variable now contains: " + test_variable);
		
	},
	item_code: function(frm, cdt, cdn) {
		
		//frappe.model.add_child(cur_frm.doc, "Sales Invoice Item", "importe_otro_impuesto");
		//frm.set_value('item_row.importe_otros_impuestos', test2 * item_row.stock_qty)
		
		/*On each change of field, we have to iterate over the cur_frm.doc.items list.  Find the row in the list, that refers to the currently created item.
		ideally:  find if "New Sales invoice Item #, or find another parameter that identifies as the bran new line being added. then refer to it, with the field name that you desire, assigned to the variable.  Do the calculation, then set the reulsting field value accordingly and then it's done.*/
		
		
		
		// () =>  a pseudo function, whatever is inside the curly braces, is getting executed one after the other...
		//  frm.doc.items.length
		
		
		// Esta funcion se llama cuando se cambia el sales invoice item code 
		//console.log("Item tax pulled upon change of ITEM CODE field");
		//frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom");
		// Since we have  the field with data, we can pull it onto a variable
		//var test_variable = frm.doc.tax_rate_per_uom;
		//console.log("the variable now contains: " + test_variable);
	},
	qty: function(frm, cdt, cdn) {
		frappe.run_serially([
			() => frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom"),
			() => {
				frm.doc.items.forEach((item_row, index) => {
					if (item_row.name == cdn){
						var test2 = item_row.tax_rate_per_uom;
						console.log("Now the variable in the new line equals" + test2);
						// will evaluate to undefined we need to run it after it has loaded somehow, or force it to load at this point.
						console.log("The stock quantity is now: " + frm.doc.items[index].stock_qty);
						// setting the value of a field  THIS WORKS! (cur_frm.doc.items[4].tax_rate_per_uom * cur_frm.doc.items[4].stock_qty)
						frm.doc.items[index].importe_otros_impuestos = Number(item_row.tax_rate_per_uom * frm.doc.items[index].stock_qty);
						//frm.refresh_fields("items");
						console.log("The index value is: " + index);
						console.log(test2 * frm.doc.items[index].stock_qty);
					}
				})
				var test_variable = frm.doc.items[frm.doc.items.length-1].tax_rate_per_uom;
				console.log("The variable after item_code update now contains: " + test_variable);
				console.log(" cdt and cdn are " + cdn + " " +cdt)
			}
		]);
		
		// Esta funcion se llama cuando se cambia el sales invoice item quantity
		//var cantidad = formulario.stock_qty;
		//console.log("Item tax pulled upon change of QUANTITY field");
		// Since we have  the field with data, we can pull it onto a variable
		//var test_variable = frm.doc.tax_rate_per_uom;
		//console.log("the variable now contains: " + test_variable);
		
	},
});

/*cambiar valor en el campo del formulario
frm.set_value(fieldname, value);*/

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



//	frappe.ui.form.on("Sales Invoice Item", {
		// Cuando exista un cambio en la seleccion de codigo de producto, se ejecutara la funcion que recibe como parametros
		// frm = El Formulario, cdt = Current Doctype, cdn = Current docname
		
		/*FIXME:  Por el momento, el usuario TIENE QUE Refrescar el campo de item_code, 
		desde la ventanita de Sales invoice Item para que funcione. Si lo refresca usando el
		grid edtiable de Sales Invoice Item mostrado en Sales invoice, no jala la data.
		Para arreglarlo el objetivo es como hacer trigger de tal forma, que sea irrelevante en donde
		actualiza, coloca, o simplemente LEE el Sales Invoice.
		*/
	
		/*PRUEBA PARA VER EL TRIGGER DEL CAMPO QTY O cantidad*/
		/*item_code: function(frm, cdt, cdn) {

			//frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom");
			// A la variable d se cargan todos los datos disponibles en el formulario
			// # Locals es un array, y los parametros [cdt][cdn] sirven para ubicar, los campos de este documento cargado en pantalla
			// # Locals se refiere a los campos del documento actual en pantalla, o "local".
	        // # let es lo mismo que var
            var d = locals[cdt][cdn];
            
	        //Para acceder a un campo en especifico, se colola:
            // d.valor_de_campo_que_se_desea_saber
           
            // Accediendo a los Valores que tiene el objeto cargado.
            //console.log(Object.values(d));

            //Utilizando JQUERY
            // Funciona utilizar JQUERY?

	        var monto = d.amount;
			console.log("La cantidad de articulos por unidad de stock es: " + cantidad);
			var excise_tax = d.tax_rate_per_uom;
			console.log("El impuesto es: " + excise_tax);
			var prueba_impuesto = excise_tax * cantidad;
			console.log("El valor total del impuesto es: " + prueba_impuesto);
            //frappe.msgprint(d);
            //console.log(d.amount);
	        console.log(d);
			//console.log("Usando trigger de Item code");
			console.log("El valor total del impuesto es: " + prueba_impuesto);
	        // frappe.model.set_value, establece un valor al campo que se desee
	        // recibe como parametros; frappe.model.set_value('doctype', 'docname', 'campo_a_asignar_valor', valor);
            //frappe.model.set_value(cdt, cdn, 'campo_de_prueba', flt(monto) * flt(cantidad));
            frappe.model.set_value(cdt, cdn, 'valor_otro_impuesto', flt(monto) * flt(cantidad));
            
            // Actualiza el valor de los campos
            cur_frm.refresh_fields();
        },*/
       /* qty: function(frm, cdt, cdn){
            var d = locals[cdt][cdn];
            
	        //Para acceder a un campo en especifico, se colola:
            // d.valor_de_campo_que_se_desea_saber
           
            // Accediendo a los Valores que tiene el objeto cargado.
            //console.log(Object.values(d));

            //Utilizando JQUERY
            // Funciona utilizar JQUERY?

	        var monto = d.amount;
	        var cantidad = d.stock_qty;
			console.log("La cantidad de articulos por unidad de stock es: " + cantidad);
			var excise_tax = d.tax_rate_per_uom;
			console.log("El impuesto es: " + excise_tax);
			var prueba_impuesto = excise_tax * cantidad;
			console.log("El valor total del impuesto es: " + prueba_impuesto);
            //frappe.msgprint(d);
            //console.log(d.amount);
	        console.log(d);
			//console.log("Usando trigger de Item code");
			console.log("El valor total del impuesto es: " + prueba_impuesto);
	        // frappe.model.set_value, establece un valor al campo que se desee
	        // recibe como parametros; frappe.model.set_value('doctype', 'docname', 'campo_a_asignar_valor', valor);
            //frappe.model.set_value(cdt, cdn, 'campo_de_prueba', flt(monto) * flt(cantidad));
            frappe.model.set_value(cdt, cdn, 'valor_otro_impuesto', flt(monto) * flt(cantidad));
            
            // Actualiza el valor de los campos
            cur_frm.refresh_fields();
        },*/
	    /*uom: function(frm, cdt, cdn) {
	        let d = locals[cdt][cdn];

	        var monto = d.amount;
	        var cantidad = d.stock_qty;
	        //frappe.msgprint(d);
	        console.log(d);
			console.log("Usando trigger de UOM");

	        // Agregar logica para realizar calculos
	        frappe.model.set_value(cdt, cdn, 'campo_de_prueba', flt(monto) * flt(cantidad));
	        cur_frm.refresh_fields();
	    },*/
	    /*conversion_factor: function(frm, cdt, cdn) {
	        let d = locals[cdt][cdn];

	        var monto = d.amount;
	        var cantidad = d.stock_qty;
	        //frappe.msgprint(d);
	        console.log(d);
			console.log("Usando trigger de conversion_factor");
	        // Agregar logica para realizar calculos
	        frappe.model.set_value(cdt, cdn, 'campo_de_prueba', flt(monto) * flt(cantidad));
	        cur_frm.refresh_fields();
	    }*/
//	}); 



    // Agregando nueva forma para hacer los calculos.

    /* frappe.ui.form.on('Sales Invoice Item', 'item_code', function(frm, cdt, cdn){
        var dd = locals[cdt][cdn];
        frappe.model.set_value(dd.cdt, dd.cdn, 'valor_otro_impuesto', (dd.amount * dd.qty));
        console.log('Mostrando Calculos: ', dd.amount*dd.qty);
    }); */ 
// The next bracket has to be available!
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



