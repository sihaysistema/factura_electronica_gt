frappe.ui.form.on("Sales Invoice Item", {

    items_add: function(frm, cdt, cdn) {
        // es-GT: Este disparador corre al agregar una nueva fila
        // en-US: This trigger runs when adding a new row.
        //AB: Solo asegurarse que el indice de la fila se refiera a la correcta (la anterior, no la actual!??) FIXME
        console.log('Trigger add en tabla hija');
    },
    items_move: function(frm, cdt, cdn) {
        // es-GT: Este disparador corre al mover una nueva fila
        // en-US: This trigger runs when moving a new row.
        console.log('Trigger move en tabla hija');
    },
    items_before_remove: function(frm, cdt, cdn) {
        // es-GT: Este disparador corre antes de eliminar una fila (FIXME:  Averiguar????)  
        // en-US: This trigger runs before eliminating a row (not sure exactly how!!?)

        // Este trigger no funciona en la tabla hija, buscar funcionamiento correcto!
    },
    items_remove: function(frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        console.log('Trigger remove en tabla hija');
    },
    item_code: function(frm, cdt, cdn) {
        //console.log("item_code was triggered");
        // FIXME :  Obtener el valor del IVA desde la base datos.
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        //cur_frm.add_fetch("Item", "three_digit_uom", "three_digit_uom");
    },
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

                // FIXME: EL RESULTADO DEL CALCULO ES DEMASIADO ELEVADO
				//frm.doc.items[index].sales_tax_this_row = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom))) - ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var / 100)))));
                
                if (item_row.is_fuel == 1) {
                    //console.log("The item you added is FUEL!" + item_row.is_good);// WORKS OK!
                    frm.doc.items[index].gt_tax_net_fuel_amt = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var / 100))).toFixed(2));
	                // Estimamos el valor del IVA para esta linea
					frm.doc.items[index].sales_tax_this_row = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom))) - ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var / 100)))));
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
                    frm.doc.items[index].gt_tax_net_goods_amt = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var / 100))).toFixed(2));
	                // Estimamos el valor del IVA para esta linea
					frm.doc.items[index].sales_tax_this_row = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom))) - ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var / 100)))));
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
                    frm.doc.items[index].gt_tax_net_services_amt = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var / 100))).toFixed(2));
	                // Estimamos el valor del IVA para esta linea
					frm.doc.items[index].sales_tax_this_row = ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom))) - ((((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.tax_rate_per_uom)) / (1 + (this_company_sales_tax_var / 100)))));
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

                // Para el calculo total de IVA, basado en la sumatoria de sales_tax_this_row de cada item
                full_tax_iva = 0;
                $.each(frm.doc.items || [], function(i, d) {
                    full_tax_iva += flt(d.sales_tax_this_row);
                });
                console.log("El total de IVA" + full_tax_iva);
                frm.doc.total_iva = full_tax_iva;
            };
        });
    },
    uom: function(frm, cdt, cdn) {
        console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function(frm, cdt, cdn) {
        console.log("El disparador de factor de conversión se corrió.");
    }
});

frappe.ui.form.on("Sales Invoice", "refresh", function(frm) {
    // es-GT: Obtiene el numero de Identificacion tributaria ingresado en la hoja del cliente.
    // en-US: Fetches the Taxpayer Identification Number entered in the Customer doctype.
    cur_frm.add_fetch("customer", "nit_face_customer", "nit_face_customer");

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
    // Funcion para la obtencion del PDF, segun el documento generado.
    function pdf_button() {
        console.log('Se ejecuto la funcion demas');
        frappe.call({
            // Este metodo verifica, el modo de generacion de PDF para la factura electronica
            // retornara 'Manul' o 'Automatico'
            method: "factura_electronica.api.save_url_pdf",
            callback: function(data) {
                console.log(data.message);
                if (data.message === 'Manual') {
                    // Si en la configuracion se encuentra que la generacion de PDF debe ser manual
                    // Se realizara lo siguiente
                    //cur_frm.clear_custom_buttons();

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
                    //console.log(data.message);
                    /*var cae_fac = frm.doc.cae_factura_electronica;
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
                    });*/

                }
            }
        });
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
});