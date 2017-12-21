/* frappe.ui.form.on("Sales Invoice", "refresh", function(frm){});*/
var net_fuel_tally = 0;
var net_goods_tally = 0;
var net_services_tally = 0;
var sales_tax_temp = 12;

frappe.ui.form.on("Sales Invoice", "onload_post_render", function(frm){
	// console.log("Post Render has been triggered"); // WORKS OK
});

frappe.ui.form.on("Sales Invoice", {
	customer: function(frm) {
		//console.log("Customer has been triggered");// WORKS OK!
		// DO NOT TRY TO FETCH TAXES AT THIS POINT, THEY HAVE NOT LOADED.
	},
	onload: function(frm) {
		//console.log("Onload has been triggered");// WORKS OK!
	},
	/* onload_post_render: function(frm) {
		// Esta funcion se llama cuando se carga el sales invoice item, despues de hacer render FUNCIONA OK
		//console.log("AFUERA: Se acaba de correr onload_post_render de Sales Invoice");
		//frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom");
		//console.log("Setting the tax rate to a variable:" + sales_tax_var);
		if(frm.doc.taxes[0].rate <= 0 || frm.doc.taxes[0].rate === undefined || frm.doc.taxes[0].rate < 0 || isNaN(frm.doc.taxes[0].rate)){
			sales_tax_var = 0;
			} else {
				sales_tax_var = frm.doc.taxes[0].rate;
			};
	},*/
	items: function(frm) {
		console.log("Items have been updated, showing this!");
	},
});

// Tres formas de obtener la tasa de impuestos:
// 1. Obtener tasa de impuestos de la hoja actual
// 2. En caso de ausencia, obtener impuestos de hoja de Sales Taxes and Charges
// 3. Si todo falla, hacemos un default a 12.
//Go to sales taxes and charges, and return the rate field if tax is set as default.
// la tasa de impuesto se debe obtener automaticamente de la línea 0, de Sales Taxes And Charges
frappe.ui.form.on("Sales Invoice Item", {
	// Add a trigger for when you ADD a new row. In this particular case, the user did NOT touch the qty field, meaning that the default value of "1" was left, so we estimate with "1" as the qty, stock qty, etc.
	// es-GT: Disparadores especifico para 
	// en-US: Child Table triggers
	fieldname_add: function(frm, cdt, cdn) {
		// es-GT: Este disparador corre al agregar una nueva fila
		// en-US: This trigger runs when adding a new row.
		//AB: Solo asegurarse que el indice de la fila se refiera a la correcta (la anterior, no la actual!??) FIXME
	},
	fieldname_move: function(frm, cdt, cdn) {
		// es-GT: Este disparador corre al mover una nueva fila
		// en-US: This trigger runs when moving a new row.
	},
	fieldname_before_remove: function(frm, cdt, cdn) {
		// es-GT: Este disparador corre antes de eliminar una fila (FIXME:  Averiguar????)  
		// en-US: This trigger runs before eliminating a row (not sure exactly how!!?)
	},
	fieldname_remove: function(frm, cdt, cdn) {
		// es-GT: Este disparador corre al momento de eliminar una nueva fila.
		// en-US: This trigger runs when removing a row.
	},
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
		// Esta funcion se llama cuando se refresca la linea de sales invoice item line
		console.log("Fields were refreshed");
		//frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom");
		// Since we have  the field with data, we can pull it onto a variable
		//var test_variable = frm.doc.tax_rate_per_uom;
		//console.log(" the variable now contains: " + test_variable);
	},
	item_code: function(frm, cdt, cdn) {
		//console.log("item_code was triggered");
		// FIXME :  Obtener el valor del IVA desde la base datos.
		this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
		console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
		frappe.run_serially([
			// es-GT: Usando la pseudo funcion para serializar: () =>, en este caso, obteniendo el valor de el campo tax_rate_per_uom del artículo, usando item_code como llave primaria para enlace.
			// en-US: Using the pseudo function to run serially: () =>, in this case fetching the value of the tax_rate_per_uom from the Item, using Item code as primary key for linking.
			// Testing asynchronicity, remove the code comment lines below.
			//() => console.log("item_code was triggered, running serially."),
		]);
		/*iffy code, not sure it runs...*/
		//frappe.model.add_child(cur_frm.doc, "Sales Invoice Item", "importe_otro_impuesto");
		/*OLD CODE, IT worked, but the problem is that it was being run asynchronously and not serially*/
		//frm.set_value('item_row.importe_otros_impuestos', test2 * item_row.stock_qty)
		// Esta funcion se llama cuando se cambia el sales invoice item code 
		//console.log("Item tax pulled upon change of ITEM CODE field");
		//frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom");
		// Since we have  the field with data, we can pull it onto a variable
		//var test_variable = frm.doc.tax_rate_per_uom;
		//console.log("the variable now contains: " + test_variable);
	},

	/*On each change of field, we have to iterate over the cur_frm.doc.items list.  Find the row in the list, that refers to the currently created item.
	ideally:  find if "New Sales invoice Item #, or find another parameter that identifies as the bran new line being added. then refer to it, with the field name that you desire, assigned to the variable.  Do the calculation, then set the reulsting field value accordingly and then it's done.*/
	// () =>  a pseudo function, whatever is inside the curly braces, is getting executed one after the other...
	//  frm.doc.items.length

	// es-GT: Para que funcione adecuadamente, es importante que el se le agregue la opción de item_code.tax_rate_per_uom en "Customize Form" al campo tax_rate_per_uom
	// en-US: For this to work properly, make sure that in the "Customize form" doctype, the field for tax_rate_per_uom has this text in the options dialog: item_code.tax_rate_per_uom

	// es-GT: El disparador para calcular el importe del impuesto por articulo es al modificar la cantidad. Logicamente, al instante que el usuario ingresa la cantidad de articulos en la linea, el calculo es realizado (o actualizado). Esto afecta unicamente a todas las lineas.
	// en-US: The trigger to calculate the amount of item tax to be added is when the quantity field is changed. Logically, as soon as the user enters the quantity of items on that line, the calculation is made (or updated)
	qty: function(frm, cdt, cdn) {
		//console.log("The quantity field was changed");// WORKS OK!
		// es-GT: Previo a correr en serie, tomamos los valores recien actualizados en los campos qty y conversion_factor.
		// en-US: Prior to running anything serially, we take the recently updated values in the qty and conversion_factor fields.
		// it seems to pull qty and conversion factor OK.  But stock_qty is not properly pulled, because it is calculated post reload.  Thus we will try to calculate it separately.
		
		var this_row_qty, this_row_rate, this_row_amount, this_row_conversion_factor, this_row_stock_qty, this_row_tax_rate, this_row_tax_amount, this_row_taxable_amount;
		
		frm.doc.items.forEach((item_row, index) => {
			if (item_row.name == cdn) {
				this_row_amount = (item_row.qty * item_row.rate);
				this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
				this_row_tax_rate = (item_row.tax_rate_per_uom);
				this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
				this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
				// Convert a number into a string, keeping only two decimals:
				frm.doc.items[index].other_tax_amount = ((item_row.tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)).toFixed(2));
				frm.doc.items[index].amount_minus_excise_tax = (((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)).toFixed(2));
				
				if (item_row.is_fuel == 1) {
					//console.log("The item you added is FUEL!" + item_row.is_good);// WORKS OK!
					frm.doc.items[index].gt_tax_net_fuel_amt = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var/100))).toFixed(2));
					// Sumatoria de todos los que tengan el check combustibles
					total_fuel = 0;
					$.each(frm.doc.items || [], function(i, d) {
						// total_qty += flt(d.qty);
						if (d.is_fuel == true) {
							total_fuel += flt(d.gt_tax_net_fuel_amt);
						};
					});
					console.log("El total de fuel es:" + total_fuel);
					frm.doc.gt_tax_fuel = total_fuel;
				};
				if (item_row.is_good == 1) {
					//console.log("The item you added is a GOOD!" + item_row.is_good);// WORKS OK!
					//console.log("El valor en bienes para el libro de compras es: " + net_goods_tally);// WORKS OK!
					frm.doc.items[index].gt_tax_net_goods_amt = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var/100))).toFixed(2));
					// Sumatoria de todos los que tengan el check bienes
					total_goods = 0;
					$.each(frm.doc.items || [], function(i, d) {
						// total_qty += flt(d.qty);
						if (d.is_good == true) {
							total_goods += flt(d.gt_tax_net_goods_amt);
						};
					});
					console.log("El total de bienes es:" + total_goods);
					frm.doc.gt_tax_goods = total_goods;
				};
				if (item_row.is_service == 1) {
					//console.log("The item you added is a SERVICE!" + item_row.is_service);// WORKS OK!
					//console.log("El valor en servicios para el libro de compras es: " + net_services_tally);// WORKS OK!
					frm.doc.items[index].gt_tax_net_services_amt = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var/100))).toFixed(2));
					total_servi = 0;
					$.each(frm.doc.items || [], function(i, d) {
						if (d.is_service == true) {
							total_servi += flt(d.gt_tax_net_services_amt);
						};
					});
					console.log("El total de servicios es:" + total_servi);
					frm.doc.gt_tax_services = total_servi;
				};
				//console.log("FUEL Item evaluates to:" + item_row.is_fuel);//WORKS OK!
				//console.log("GOODS Item evaluates to:" + item_row.is_goods);//WORKS OK!
				//console.log("SERVICES Item evaluates to:" + item_row.is_service);//WORKS OK!
				//console.log("El campo qty es ahora de esta fila contiene: " + item_row.qty);//WORKS OK!
				//console.log("El campo rate es ahora de esta fila contiene: " + item_row.rate);//WORKS OK!
				//console.log("El campo conversion_factor de esta fila contiene: " + item_row.conversion_factor);//WORKS OK!
				//console.log("El campo stock_qty de esta fila contiene: " + this_row_stock_qty);//WORKS OK!
				//console.log("El campo tax_rate de esta fila contiene: " + this_row_tax_rate);//WORKS OK!
				//console.log("El campo tax_amount de esta fila contiene: " + this_row_tax_amount);//WORKS OK!
				//console.log("El campo taxable_amount de esta fila contiene: " + this_row_taxable_amount);//WORKS OK!
				//frm.doc.items[index].other_tax_amount = Number(this_row_tax_rate * this_row_stock_qty);
				//frm.doc.items[index].amount_minus_excise_tax = Number(this_row_amount - this_row_tax_amount);
			};	
		});
		// es-GT: Como JavaScript es asincrónico, es necesario correr en serie lo siguiente
		// en-US: Since JavaScript is asynchronous, it is necessary to run the following serially
		frappe.run_serially([
			// es-GT: Usando la pseudo funcion para serializar: () =>, en este caso, obteniendo el valor de el campo tax_rate_per_uom del artículo, usando item_code como llave primaria para enlace.
			// en-US: Using the pseudo function to run serially: () =>, in this case fetching the value of the tax_rate_per_uom from the Item, using Item code as primary key for linking.
			// testing asynchronicity, remove the code comment lines below.
			//() => frm.add_fetch("item_code", "tax_rate_per_uom", "tax_rate_per_uom"),
			// es-GT: Ahora iteramos por cada fila de la tabla hija, usando dos argumentos: item_row, declarado alli, que representa cada fila, e index, también declarado aqui, que representa el numero de fila
			// en-US: Now, we iterate through each row in the child table, using two arguments: item_row, delcared here, which represents each row, and index, also declared here, which represents the row number.
			() => {
				frm.doc.items.forEach((item_row, index) => {
					// es-GT: Si la fila cuyo campo "name" es igual al "cdn" o current docname, entonces corra el codigo fuente adentro. Esto apunta al nuevo articulo que se esta agregando en esa fila.
					// en-US: If the row whose field "name" is equal to "cdn" or current docname, then run the code inside. This points to the new item being added to the row in the child table.
					if (item_row.name == cdn) {
						//console.log("Running serially for each row in items child table.");// WORKS OK!
						// es-GT: Asignamos el contenido del campo "tax_rate_per_uom" de esa fila, a una variable "this_row_tax_rate".
						// en-US: We assign the contents of the field "tax_rate_per_uom" from this row, to a variable called "this_row_tax_rate".
						// #####     var this_row_tax_rate = item_row.tax_rate_per_uom;
						// es-GT: Mostramos en la consola el contenido de la variable "this_row_tax_rate"
						// en-US: We log on the console the contents of the variable "this_row_tax_rate"
						//console.log("Serially: The tax rate for this row " + this_row_tax_rate);
						// es-GT: Mostramos en la consola el contenido del campo "stock_qty". OJO: si se corre con otro trigger antes de que haya terminado de cargar al cambiar item_code, evaluara a undefined, por eso se corre la funcion AQUI al cambiar la cantidad. Si corre est alinea de codigo en otro lugar, no cargara.
						// en-US: We log on the console the contents of the field "stock_qty". NOTE: if this code is run with another trigger before the form has finished loading when changin item_code, it will evaluate to undefined, this is why the function is run here when changing the quantity. if you run this line of code elsewhere, it will not load.
						// FIXED:  The data being gathered is "lagging" the previous update.  Must find way to make it get THIS data NOW.  Data is best obtained upon updating quantity field.
						//console.log("Serially: The stock quantity for this row is now: " + frm.doc.items[index].stock_qty);
						// es-GT: ¡Aquí es donde sucede la MAGIA! Esta línea establece el valor del campo "other_tax_amount" como el producto de stock_qty (cantidad de artículos en stock vendidos) y la tasa de impuestos por unidad de medida en stock.
						// en-US: This is where the MAGIC happens! This line of code sets the value of the field "other_tax_amount" as the product of stock_qty (number of stock quantity items being sold) and the tax rate per stock unit of measure.
						// This was a test that worked when running directly on the console: setting the value of a field  THIS WORKS! (cur_frm.doc.items[4].tax_rate_per_uom * cur_frm.doc.items[4].stock_qty)
						//frm.doc.items[index].other_tax_amount = Number(item_row.tax_rate_per_uom * frm.doc.items[index].stock_qty);
						// es-GT: Ahora calculamos la cantidad de la fila, sin el total de impuestos estimado, puesto que esta cantidad estará afecta al impuesto al valor agregado (IVA)
						// en-US: Now we calculate the amount for the row, minus the excise taxes for the row, because this quantity will be subject for application of Sales Tax
						//frm.doc.items[index].amount_minus_excise_tax = Number(frm.doc.items[index].amount - (Number(item_row.tax_rate_per_uom * frm.doc.items[index].stock_qty)));
						// es-GT: Refrescamos todos los campos adentro de la tabla hija
						// en-US: Refresh all the fields within the child table
						//frm.refresh_fields('items');
						// es-GT: Pruebas para mostrar valores en la consola
						// en-US: Tests to show values on the console
						//console.log("The index value (representing the actual row being iterated or worked upon) is: " + index);// WORKS OK!
						//console.log(this_row_tax_rate * frm.doc.items[index].stock_qty);// WORKS OK!
						}
					})
					// en-US:  This test code logs to the console the variable amounts. It works OK.
					//var test_variable = frm.doc.items[frm.doc.items.length-1].tax_rate_per_uom;
					//console.log("The variable after item_code update now contains: " + test_variable);
					//console.log(" cdt and cdn are " + cdn + " " +cdt)
			},
		]); // en-US: Ending the run serially brackets es-GT: Terminan los brackets de correr en serie.

		// es-GT: Esta funcion se llama cuando se cambia el sales invoice item quantity
		//var cantidad = formulario.stock_qty;
		// console.log("Item tax pulled upon change of QUANTITY field");
		// Since we have  the field with data, we can pull it onto a variable
		//var test_variable = frm.doc.tax_rate_per_uom;
		//console.log("the variable now contains: " + test_variable);
	},
	uom: function(frm, cdt, cdn) {
		console.log("The unit of measure field was changed and the code from the trigger was run");
	},
	conversion_factor: function(frm, cdt, cdn) {
		console.log("El disparador de factor de conversión se corrió.");
	},
});

// SUM CHILD TABLE CONDITIONALLY AND SET THE FIELD VALUES FOR SALES INVOICE
//net_fuel_tally = ((this_row_taxable_amount / (1 + (sales_tax_var/100))).toFixed(2));
//console.log("El valor en combustibles para el libro de compras es: " + net_fuel_tally);// WORKS OK!

// ADD TAX ACCOUNT INFORMATION TO THE SALES TAXES AND CHARGES TABLE


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