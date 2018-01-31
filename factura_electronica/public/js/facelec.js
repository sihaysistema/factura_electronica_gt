// Funcion para los calculos necesarios.
facelec_tax_calculation_conversion = function(frm, cdt, cdn) {

    refresh_field('items');
    //cur_frm.refresh();

    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

    console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);

    var this_row_qty, this_row_rate, this_row_amount, this_row_conversion_factor, this_row_stock_qty, this_row_tax_rate, this_row_tax_amount, this_row_taxable_amount;

    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name == cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.facelec_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
            // Convert a number into a string, keeping only two decimals:
            frm.doc.items[index].facelec_other_tax_amount = ((item_row.facelec_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].facelec_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.facelec_tax_rate_per_uom));
            console.log("uom that just changed is: " + item_row.uom);
            console.log("stock qty is: " + item_row.stock_qty); // se queda con el numero anterior.  multiplicar por conversion factor (si existiera!)
            console.log("conversion_factor is: " + item_row.conversion_factor);
            if (item_row.factelecis_fuel == 1) {
                //console.log("The item you added is FUEL!" + item_row.facelec_is_good);// WORKS OK!
                // Estimamos el valor del IVA para esta linea
                //frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_amount_minus_excise_tax * (1 + (this_company_sales_tax_var / 100))).toFixed(2);
                //frm.doc.items[index].facelec_gt_tax_net_fuel_amt = (item_row.facelec_amount_minus_excise_tax - item_row.facelec_sales_tax_for_this_row).toFixed(2);
                frm.doc.items[index].facelec_gt_tax_net_fuel_amt = (item_row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                total_fuel = 0;
                $.each(frm.doc.items || [], function(i, d) {
                    // total_qty += flt(d.qty);
                    if (d.factelecis_fuel == true) {
                        total_fuel += flt(d.facelec_gt_tax_net_fuel_amt);
                    };
                });
                //console.log("El total neto de fuel es:" + total_fuel); // WORKS OK!
                frm.doc.facelec_gt_tax_fuel = total_fuel;
                frm.refresh_field("factelecis_fuel");
            };
            if (item_row.facelec_is_good == 1) {
                //console.log("The item you added is a GOOD!" + item_row.facelec_is_good);// WORKS OK!
                //console.log("El valor en bienes para el libro de compras es: " + net_goods_tally);// WORKS OK!
                // Estimamos el valor del IVA para esta linea
                //frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_amount_minus_excise_tax * (this_company_sales_tax_var / 100)).toFixed(2);
                //frm.doc.items[index].facelec_gt_tax_net_goods_amt = (item_row.facelec_amount_minus_excise_tax - item_row.facelec_sales_tax_for_this_row).toFixed(2);
                frm.doc.items[index].facelec_gt_tax_net_goods_amt = (item_row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                total_goods = 0;
                $.each(frm.doc.items || [], function(i, d) {
                    // total_qty += flt(d.qty);
                    if (d.facelec_is_good == true) {
                        total_goods += flt(d.facelec_gt_tax_net_goods_amt);
                    };
                });
                //console.log("El total neto de bienes es:" + total_goods);// WORKS OK!
                frm.doc.facelec_gt_tax_goods = total_goods;
            };
            if (item_row.facelec_is_service == 1) {
                //console.log("The item you added is a SERVICE!" + item_row.facelec_is_service);// WORKS OK!
                //console.log("El valor en servicios para el libro de compras es: " + net_services_tally);// WORKS OK!
                // Estimamos el valor del IVA para esta linea
                //frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_amount_minus_excise_tax * (this_company_sales_tax_var / 100)).toFixed(2);
                //frm.doc.items[index].facelec_gt_tax_net_services_amt = (item_row.facelec_amount_minus_excise_tax - item_row.facelec_sales_tax_for_this_row).toFixed(2);
                frm.doc.items[index].facelec_gt_tax_net_service_amt = (item_row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_gt_tax_net_service_amt * (this_company_sales_tax_var / 100));
                total_servi = 0;
                $.each(frm.doc.items || [], function(i, d) {
                    if (d.facelec_is_service == true) {
                        total_servi += flt(d.facelec_gt_tax_net_services_amt);
                    };
                });
                // console.log("El total neto de servicios es:" + total_servi); // WORKS OK!
                frm.doc.facelec_gt_tax_services = total_servi;
            };

            // Para el calculo total de IVA, basado en la sumatoria de facelec_sales_tax_for_this_row de cada item
            full_tax_iva = 0;
            $.each(frm.doc.items || [], function(i, d) {
                full_tax_iva += flt(d.facelec_sales_tax_for_this_row);
            });
            frm.doc.facelec_total_iva = full_tax_iva;
        };
    });
}

// Funcion para evitar realizar calculos con cuentas duplicadas
buscar_account = function(frm, cuenta_b) {
    /* Funcionamiento: recibe como parametro frm, y cuenta_b, lo que hace es, buscar en todas las filas de taxes
       si existe ya una cuenta con el nombre de la cuenta recibida por parametro, en caso ya exista esa cuenta en
       la tabla no hace nada, pero si encuentra que no hay una cuenta igual a la recibida en el parametro, entonces
       la funcion encargada agregara una nueva fila con los datos correspondientes, esta funcion retorna true
       en caso si encuentre una cuenta existente
    */
    var estado = ''
    $.each(frm.doc.taxes || [], function(i, d) {
        if (d.account_head === cuenta_b) {
            console.log('Si Existe en el indice ' + i)
            estado = true
        }
    });
    return estado;
}

// Funcion para validar el NIT
function valNit(nit) {
    var nd, add = 0;
    if (nd = /^(\d+)\-?([\dk])$/i.exec(nit)) {
        nd[2] = (nd[2].toLowerCase() == 'k') ? 10 : parseInt(nd[2]);
        for (var i = 0; i < nd[1].length; i++) {
            add += ((((i - nd[1].length) * -1) + 1) * nd[1][i]);
        }
        return ((11 - (add % 11)) % 11) == nd[2];
    } else {
        return false;
    }
}

frappe.ui.form.on("Sales Invoice", "nit_face_customer", function(frm) {
    //console.log('NIT de cliente ' + frm.doc.nit_face_customer);
    // Validacion de NIT: Cuando se carga el NIT en el campo nit_face_customer, realiza la comprobacion
    // En caso de que el NIT sea incorrecto, no le permitira guardar la factura. Se habilitara la opcion guardar
    // Hasta que exista un nit valido o sea C/F (Consumidor FInal)
    if (frm.doc.nit_face_customer === "C/F" || frm.doc.nit_face_customer === "c/f") {
        frm.enable_save(); // Activa y Muestra el boton guardar de Sales Invoice
    } else {
        nit_validado = (valNit(frm.doc.nit_face_customer));
        if (nit_validado === false) {
            msgprint('NIT de cliente: <b>' + frm.doc.customer + '</b>, no es correcto. Si no tiene disponible el NIT modifiquelo a <b>C/F</b>');
            frm.disable_save(); // Desactiva y Oculta el boton de guardar en Sales Invoice
        }
        if (nit_validado === true) {
            frm.enable_save(); // Activa y Muestra el boton guardar de Sales Invoice
        }
    }
});


frappe.ui.form.on("Sales Invoice", "discount_amount", function(frm) {
    tax_before_calc = frm.doc.facelec_total_iva;
    console.log("El descuento total es:" + frm.doc.discount_amount);
    console.log("El IVA calculado anteriormente:" + frm.doc.facelec_total_iva);
    discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
    console.log("El neto sin iva del descuento es" + discount_amount_net_value);
    discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
    console.log("El IVA del descuento es:" + discount_amount_tax_value);
    frm.doc.facelec_total_iva = (frm.doc.facelec_total_iva - discount_amount_tax_value);
    console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
});

frappe.ui.form.on("Sales Invoice", "customer", function(frm) {
    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
    console.log('Corrio customer trigger y se cargo el IVA, el cual es ' + this_company_sales_tax_var);
    // facelec_tax_calculation_conversion(); // Provoca que no se cargue la fecha ni la cuenta
});
/*
frappe.ui.form.on("Sales Invoice Item", "uom", function(frm, cdt, cdn) {
		this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
		console.log('Corrio trigger en funcion externa para campo UOM ');
		facelec_tax_calculation_conversion(frm, cdt, cdn);
});*/

frappe.ui.form.on("Sales Invoice Item", {

    items_add: function(frm, cdt, cdn) {
        // es-GT: Este disparador corre al agregar una nueva fila
        // en-US: This trigger runs when adding a new row.
        // console.log('Trigger add en tabla hija');

    },
    items_move: function(frm, cdt, cdn) {
        // es-GT: Este disparador corre al mover una nueva fila
        // en-US: This trigger runs when moving a new row.
        // console.log('Trigger move en tabla hija');
    },
    before_items_remove: function(frm, cdt, cdn) {
        //facelec_tax_calculation(frm, cdt, cdn);
        // Este trigger no funciona en la tabla hija, buscar funcionamiento correcto!
        /*
        fix_prueba = 0;
        $.each(frm.doc.items || [], function(i, d) {
            fix_prueba += flt(d.facelec_gt_tax_net_fuel_amt);
        });
        console.log("Recalculo en before remove row" + fix_prueba);
        frm.doc.facelec_gt_tax_fuel = fix_prueba;
        */
    },
    items_remove: function(frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // console.log('Trigger remove en tabla hija');

        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.
        fix_gt_tax_fuel = 0;
        fix_gt_tax_goods = 0;
        fix_gt_tax_services = 0;
        fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function(i, d) {

            fix_gt_tax_fuel += flt(d.facelec_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.facelec_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.facelec_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.facelec_sales_tax_for_this_row);

        });

        cur_frm.set_value("facelec_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("facelec_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("facelec_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("facelec_total_iva", fix_gt_tax_iva);
    },
    item_code: function(frm, cdt, cdn) {
        //console.log("item_code was triggered");
        // FIXME :  Obtener el valor del IVA desde la base datos.
        //this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        //console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        //cur_frm.add_fetch("Item", "three_digit_uom", "three_digit_uom");
        //facelec_tax_calculation_conversion(frm, cdt, cdn);
        // IVA se carga aqui, para aquellas facturas que ya tengan articulos y no se les vaya a agregar.  (aunque puede cargarse justo a tiempo en la funcion, lo cargamos aqui por redundancia y seguridad.)
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
    },
    qty: function(frm, cdt, cdn) {
        //facelec_tax_calculation(frm, cdt, cdn);
        facelec_tax_calculation_conversion(frm, cdt, cdn);
        console.log("cdt contains: " + cdt);
        console.log("cdn contains: " + cdn);
    },
    uom: function(frm, cdt, cdn) {
        console.log("The unit of measure field was changed and the code from the trigger was run");
        // agarras el valor del precio o rate existente hasta este momento.
        // lo multiplicas por el factor de conversion
        //facelec_tax_calculation_conversion(frm, cdt, cdn);
        //facelec_tax_calculation(frm, cdt, cdn);
    },
    conversion_factor: function(frm, cdt, cdn) {
        console.log("El disparador de factor de conversión se corrió.");
        facelec_tax_calculation_conversion(frm, cdt, cdn);
        //facelec_tax_calculation(frm, cdt, cdn);
    },
    facelec_tax_rate_per_uom_account: function(frm, cdt, cdn) {

        // Eleccion de este trigger para la adicion de filas en taxes con sus respectivos valores.

        frm.doc.items.forEach((item_row_i, index_i) => {
            if (item_row_i.name == cdn) {
                // Forma 1: Para agregar filas
                // var tabla_hija = cur_frm.add_child('taxes');

                // Forma 2: Para agregar filas
                //frappe.model.add_child(frm.doc, "Sales Taxes and Charges", "taxes")

                var cuenta = item_row_i.facelec_tax_rate_per_uom_account;
                //console.log(item_row_i.facelec_tax_rate_per_uom_account);
                //xx = (frappe.db.get_value("Account", { "name": cuenta }, "account_number", "tax_rate"));
                //console.log(xx["account_number"])

                if (cuenta !== null) {
                    if (buscar_account(frm, cuenta)) {
                        console.log('La cuenta ya existe');
                    } else {
                        console.log('La cuenta no existe, se agregara una nueva fila en taxes');
                        // Agrega una nueva fila en la tabla taxes con campos vacios
                        frappe.model.add_child(frm.doc, "Sales Taxes and Charges", "taxes");
                        // Se posiciona en el indice correcto de la fila anteriormente agregada para asignar
                        // los valores correspondientes correctamente
                        frm.doc.taxes.forEach((item_row, index) => {
                            if (item_row.account_head == undefined) {
                                frappe.call({
                                    method: "factura_electronica.api.get_data_tax_account",
                                    args: {
                                        name_account_tax_gt: cuenta
                                    },
                                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                                    callback: function(data) {
                                        // Asigna los valores retornados del servidor
                                        frm.doc.taxes[index].charge_type = 'On Net Total'; // Opcion 1: Actual, Opcion 2: On Net Total, Opcion 3: On Previous Row Amount, Opcion 4: On Previous Row Total
                                        frm.doc.taxes[index].account_head = cuenta;
                                        frm.doc.taxes[index].rate = data.message;
                                        //item_row.account_head = cuenta;
                                        //refresh_field("taxes");
                                        frm.doc.taxes[index].description = 'Impuesto';
                                    }
                                });
                            }
                        });
                    }
                } else {
                    console.log('El producto seleccionado no tiene una cuenta asociada')
                }
            }
        });

    },
    rate: function(frm, cdt, cdn) {
        facelec_tax_calculation(frm, cdt, cdn);
    }
});

frappe.ui.form.on("Sales Invoice", "before_save", function(frm) {
    frm.doc.items.forEach((item) => {
        // for each button press each line is being processed.
        console.log("item contains: " + item);
        //Importante
        facelec_tax_calculation_conversion(frm, "Sales Invoice Item", item.name);
        tax_before_calc = frm.doc.facelec_total_iva;
        console.log("El descuento total es:" + frm.doc.discount_amount);
        console.log("El IVA calculado anteriormente:" + frm.doc.facelec_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        console.log("El neto sin iva del descuento es" + discount_amount_net_value);
        discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
        console.log("El IVA del descuento es:" + discount_amount_tax_value);
        frm.doc.facelec_total_iva = (frm.doc.facelec_total_iva - discount_amount_tax_value);
        console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
    });
});

frappe.ui.form.on("Sales Invoice", "refresh", function(frm) {
    // es-GT: Obtiene el numero de Identificacion tributaria ingresado en la hoja del cliente.
    // en-US: Fetches the Taxpayer Identification Number entered in the Customer doctype.
    cur_frm.add_fetch("customer", "nit_face_customer", "nit_face_customer");

    // WORKS OK!
    frm.add_custom_button("UOM Recalculation", function() {
        frm.doc.items.forEach((item) => {
            // for each button press each line is being processed.
            console.log("item contains: " + item);
            //Importante
            facelec_tax_calculation_conversion(frm, "Sales Invoice Item", item.name);
        });
    });

    // Codigo para Factura Electronica FACE, CFACE
    // El codigo se ejecutara segun el estado del documento, puede ser: Pagado, No Pagado, Validado, Atrasado
    if (frm.doc.status === "Paid" || frm.doc.status === "Unpaid" || frm.doc.status === "Submitted" || frm.doc.status === "Overdue") {
        // SI en el campo de 'cae_factura_electronica' ya se encuentra el dato correspondiente, ocultara el boton
        // para generar el documento, para luego mostrar el boton para obtener el PDF del documento ya generado.
        if (frm.doc.cae_factura_electronica) {
            cur_frm.clear_custom_buttons();
            pdf_button(frm.doc.cae_factura_electronica);
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
                            pdf_button(frm.doc.cae_factura_electronica);
                        }
                    }
                });
            }).addClass("btn-primary");
        }
    }

    // Funcion para la obtencion del PDF, segun el documento generado.
    function pdf_button(cae_documento) {
        //console.log('Se ejecuto la funcion demas');
        frappe.call({
            // Este metodo verifica, el modo de generacion de PDF para la factura electronica
            // retornara 'Manual' o 'Automatico' segun lo que encuentre en la configuracion de factura electronica
            method: "factura_electronica.api.save_url_pdf",
            callback: function(data) {
                console.log(data.message);
                if (data.message === 'Manual') {
                    // Si en la configuracion se encuentra que la generacion de PDF debe ser manual
                    // Se realizara lo siguiente
                    //cur_frm.clear_custom_buttons();
                    frm.add_custom_button(__("Obtener PDF"),
                        function() {
                            //console.log(cae_fac)
                            window.open("https://www.ingface.net/Ingfacereport/dtefactura.jsp?cae=" + cae_documento);
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
            pdf_button(frm.doc.cae_nota_de_credito);
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
                            pdf_button(frm.doc.cae_nota_de_credito);
                        }
                    }
                });
            }).addClass("btn-primary");
        }
    }

    // Codigo para notas de debito
    // Codigo para Notas de Credito NDE
    if (frm.doc.status === "Paid" || frm.doc.status === "Unpaid" || frm.doc.status === "Submitted" || frm.doc.status === "Overdue") {

        //var nombre = 'Nota Debito';
        if (frm.doc.es_nota_de_debito == 1) {
            cur_frm.clear_custom_buttons('Factura Electronica');
            if (frm.doc.cae_nota_de_debito) {
                cur_frm.clear_custom_buttons();
                pdf_button(frm.doc.cae_nota_de_debito);
            } else {
                frm.add_custom_button(__('Nota Debito'), function() {
                    frappe.call({
                        method: "factura_electronica.api.generar_factura_electronica",
                        args: {
                            serie_factura: frm.doc.name,
                            nombre_cliente: frm.doc.customer
                        },
                        // El callback recibe como parametro el dato retornado por script python del lado del servidor
                        callback: function(data) {

                            cur_frm.set_value("cae_nota_de_debito", data.message);
                            if (frm.doc.cae_nota_de_debito) {
                                cur_frm.clear_custom_buttons();
                                pdf_button(frm.doc.cae_nota_de_debito);
                            }
                        }
                    });
                }).addClass("btn-primary");
            }
        }
    }
});