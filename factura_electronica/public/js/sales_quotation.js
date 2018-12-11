console.log("Hello world from Sales Quotation");

// TODO: CORREGIR BUGS MULTIPLES LINEAS, EN TABLA OTRO IMPUESTOS
// TODO: CORREGIR QUE NO SE ELIMINA LINEA EN TABLA OTROS IMPUESTOS, AL ELIMINAR ITEM

// cálculo de cotizaciones
function shs_quotation_calculation(frm, cdt, cdn) {
    // es-GT: Actualiza los datos en los campos de la tabla hija 'items'
    //console.log("ran shs_quotation_calculation");
    // es-GT: Revisamos si ya quedo cargado y definido el rate (tasa) de impuesto en el DocType, el cual debe estar en la fila 0 de Sales Taxes & Charges.
    // es-GT: Si no ha sido definido, no se hace nada. Si ya fue definido, se asigna a una variable el valor que encuentre en la fila 0 de la tabla hija taxes.
    if (typeof (cur_frm.doc.taxes[0].rate) == "undefined") {
        //console.log("No se ha cargado impuesto, asi que no se hace nada.");
    } else {
        //console.log("Ahora que ya se especifico un cliente, ya existe impuesto en la hoja, por lo tanto, lo asignamos a una variable!");
        var this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        //console.log("El IVA cargado es: " + this_company_sales_tax_var);
    }

    var this_row_amount = 0;
    var this_row_stock_qty = 0;
    var this_row_tax_rate = 0;
    var this_row_tax_amount = 0;
    var this_row_taxable_amount = 0;

    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name === cdn) {
            // first we calculate the amount total for this row and assign it to a variable
            //this_row_amount = (item_row.qty * item_row.rate);
            this_row_amount = item_row.amount;
            // Now, we get the quantity in terms of stock quantity by multiplying by conversion factor
            this_row_stock_qty = item_row.stock_qty;
            // We then assign the tax rate per stock UOM to a variable
            this_row_tax_rate = item_row.facelec_qt_tax_rate_per_uom;
            // We calculate the total amount of excise or special tax based on the stock quantity and tax rate per uom variables above.
            this_row_tax_amount = (item_row.stock_qty * item_row.facelec_qt_tax_rate_per_uom);
            // We then estimate the remainder taxable amount for which Other ERPNext configured taxes will apply.
            this_row_taxable_amount = (item_row.amount - (item_row.stock_qty * item_row.facelec_qt_tax_rate_per_uom));
            // We change the fields for other tax amount as per the complete row taxable amount.
            frm.doc.items[index].facelec_qt_other_tax_amount = ((item_row.facelec_qt_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            frm.doc.items[index].facelec_qt_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - (item_row.stock_qty * item_row.facelec_qt_tax_rate_per_uom));
            // We refresh the items to recalculate everything to ensure proper math
            // We refresh the items to recalculate everything to ensure proper math
            frm.refresh_field("items");
            frm.refresh_field("conversion_factor");

            // Verificacion Individual para verificar si es Fuel, Good o Service
            if (item_row.facelec_qt_is_fuel) {
                frm.doc.items[index].facelec_qt_gt_tax_net_fuel_amt = (item_row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_qt_sales_tax_for_this_row = (item_row.facelec_qt_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
            };

            if (item_row.facelec_qt_is_good) {
                frm.doc.items[index].facelec_qt_gt_tax_net_goods_amt = (item_row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_qt_sales_tax_for_this_row = (item_row.facelec_qt_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
            };

            if (item_row.facelec_qt_is_service) {
                frm.doc.items[index].facelec_qt_gt_tax_net_services_amt = (item_row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_qt_sales_tax_for_this_row = (item_row.facelec_qt_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
            };
        };
    });
}

// Esto soluciona el issue #18
function each_item_quotation(frm, cdt, cdn) {
    // es-GT: Esta permite ya que se calcule correctamente desde el INICIO!
    // es-GT: Sin necesidad de Guardar antes!
    frm.doc.items.forEach((item) => {
        // for each button press each line is being processed.
        //console.log("Item, from the each_item function contains: " + item);
        //Esato dice: object, object
        //Importante
        // tax_before_calc = frm.doc.facelec_total_iva;
        //console.log("El descuento total es:" + frm.doc.discount_amount);
        //console.log("El IVA calculado anteriormente:" + frm.doc.facelec_total_iva);
        var discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        if (typeof (cur_frm.doc.taxes[0].rate) == "NaN") {
            // console.log("No hay descuento definido, calculando sin descuento.");
        } else {
            // console.log("El descuento parece ser un numero definido, calculando con descuento.");
            // console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            // console.log("El IVA del descuento es:" + discount_amount_tax_value);
            // // frm.doc.facelec_total_iva = (frm.doc.facelec_total_iva - discount_amount_tax_value);
            // // console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
        }
        shs_quotation_calculation(frm, "Quotation Item", item.name);
        catizacion_otros_impuestos_fila(frm, "Quotation Item", item.name);
    });
}

function quotation_add_taxes(frm, tax_account) {
	/**
	 * Parametros:
	 * #1 frm = formulario que se esta trabajando
	 * #2 tax_account = nombre de la cuenta
	 *
	 * Funcionamiento:
	 * Recorre la tabla items, por cada item que encuentre con el nombre de
	 * cuenta recibido, lo ira concatenando en una variable que al finalizar
	 * el recorrido de la tabla lo retornara a quien haya invocado la fucnion
	 */
    var total_sumatoria = 0;

    $.each(frm.doc.items || [], function (i, d) {
        if (d.facelec_qt_tax_rate_per_uom_account === tax_account) {
            total_sumatoria += flt(d.facelec_qt_other_tax_amount);
        };
    });

    return total_sumatoria;
}

function sumar_otros_impuestos_cotizacion(frm, cdt, cdn) {
	/**
	 * Parametros:
	 * #1 frm = formulario que se esta trabajando
	 * #2 cdt = Doctype
	 * #3 cdn = Docname
	 *
	 * Funcionamiento:
	 * Recorre la tabla items, por cada item encontrado, si tiene una cuenta asignada,
	 * recorrera la tabla hija shs_otros_impuestos en busca de items con el mismo nombre
	 * de cuenta anteriormente encontrado, para totalizar el valor del impuestos, para todos
	 * los items con la misma cuenta.
	 */
    frm.doc.items.forEach((item_row_1, index_1) => {

        if (item_row_1.name === cdn) {
            if (item_row_1.facelec_qt_tax_rate_per_uom_account) {
                frm.doc.shs_tax_quotation.forEach((tax_row_2, index_2) => {
                    if (tax_row_2.account_head === item_row_1.facelec_qt_tax_rate_per_uom_account) {
                        var totalizador = 0;
                        totalizador = quotation_add_taxes(frm, tax_row_2.account_head)
                        cur_frm.doc.shs_tax_quotation[index_2].total = totalizador;
                        shs_total_other_tax_quotation(frm);
                    }
                });
            }

        }
    });
}

function shs_total_other_tax_quotation(frm) {
	/**
	 * Parametros:
	 * #1 frm = formulario que se esta trabajando
	 *
	 * Funcionamiento:
	 * Recorre la tabla hija shs_otros_impuestos, realiza sumatoria de todos las filas
	 * que tenga una cuenta, el valor totalizado se asigna al campo shs_total_otros_imp_incl
	 */
    var total_tax = 0;

    $.each(frm.doc.shs_tax_quotation || [], function (i, d) {
        if (d.account_head) {
            total_tax += flt(d.total);
        };
    });

    cur_frm.set_value('shs_qt_total_otros_imp_incl', total_tax);
    frm.refresh_field("shs_qt_total_otros_imp_incl");
}

function catizacion_otros_impuestos_fila(frm, cdt, cdn) {
	/**
	 * Parametros:
	 * #1 frm = formulario que se esta trabajando
	 * #2 cdt = Doctype
	 * #3 cdn = Docname
	 *
	 * Funcionamiento:
	 * Recorre la tabla items, por cada fila con una cuenta asignada buscara en la tabla hija
	 * shs_otros_impuestos por una fila con el mismo nombre de la cuenta anteriormente encontrada,
	 * si no la encuentra en shs_otros_impuestos creara una nueva fila, y le asignara los valores
	 * de nombre de cuenta y el total para esa cuenta. Si la cuenta ya se encuentra creada en
	 * shs_otros_impuestos le sumara los valores encontrados.
	 */
    var this_row_tax_amount = 0; // Valor IDP
    var this_row_taxable_amount = 0; // Valor todavía con IVA
    var shs_otro_impuesto = 0;
    var total_suma_impuesto = 0;

    frm.doc.items.forEach((item_row_i, indice) => {
        if (item_row_i.name === cdn) {
            // Calculos Alain
            this_row_tax_amount = (item_row_i.stock_qty * item_row_i.qt_tax_rate_per_uom);
            //this_row_taxable_amount = (item_row_i.amount - (item_row_i.stock_qty * item_row_i.facelec_tax_rate_per_uom));
            shs_otro_impuesto = item_row_i.facelec_qt_other_tax_amount;

            // Guarda el nombre de la cuenta del item seleccionado
            var cuenta = item_row_i.facelec_qt_tax_rate_per_uom_account;
            console.log('Cuenta de item encontrada es : ' + cuenta);

            // Refresh data de items y conversion_factor
            frm.refresh_field('items');
            frm.refresh_field('conversion_factor');

            if (cuenta) { // Si encuentra una cuenta con nombre procede
                otro_impuesto = this_row_tax_amount;
                //valor_con_iva = this_row_taxable_amount;

                if (!(buscar_account(frm, cuenta))) { // Si no encuentra una cuenta, procede.
                    // var fila_nueva = cur_frm.add_child("shs_otros_impuestos");
                    // var fila_nueva = frappe.model.add_child(cur_frm.doc, "Otros Impuestos Factura Electronica", "shs_otros_impuestos");
                    // Crea una nueva fila vacia en la tabla hija shs_otros_impuestos
                    frappe.model.add_child(cur_frm.doc, "Otros Impuestos Factura Electronica", "shs_tax_quotation");

                    // Refresh datos de la tabla hija items
                    cur_frm.refresh_field('items');
                    // otro_impuesto = this_row_tax_amount;
                    // valor_con_iva = this_row_taxable_amount;

                    // Recorre la tabla hija 'taxes' en busca de la nueva fila que se agrego anteriormente donde account_head
                    // sea undefined
                    frm.doc.shs_tax_quotation.forEach((tax_row, index) => {
                        // Si encuentra la fila anteriormente agregada procede
                        if (tax_row.account_head === undefined) {
                            // Asigna valores en la fila recien creada
                            cur_frm.doc.shs_tax_quotation[index].account_head = cuenta;
                            cur_frm.doc.shs_tax_quotation[index].total = shs_otro_impuesto;

                            // Actualiza los datos de la tabla hija
                            cur_frm.refresh_field("shs_tax_quotation");

                            // Funcion que se encarda de sumar los valores por cuenta
                            sumar_otros_impuestos_cotizacion(frm, cdt, cdn);
                            cur_frm.refresh_field("shs_tax_quotation");
                        }
                    });

                } else { // Si la cuenta ya esta agregada en shs_otros_impuestos, se procede a sumar sobre los valores
                    // ya existentes
                    // Funcion que se encarda de sumar los valores por cuenta
                    sumar_otros_impuestos_cotizacion(frm, cdt, cdn);
                    cur_frm.refresh_field("shs_tax_quotation");
                }
            }
        }
    });

}

/**
 * Se encarga de recalcular el total de otros impuestos cuando se elimina un item
 */
function totalizar_valores_quotation(frm, cdn, tax_account_n) {
    // recorre items
    frm.doc.items.forEach((item_row, i1) => {
        if (item_row.facelec_qt_tax_rate_per_uom_account === tax_account_n) {
            total = quotation_add_taxes(frm, tax_account_n);
            // recorre shs_otros_impuestos
            frm.doc.shs_tax_quotation.forEach((tax_row, i2) => {
                if (tax_row.account_head === tax_account_n) {
                    var total = 0;
                    cur_frm.refresh_field("shs_tax_quotation");
                    cur_frm.doc.shs_tax_quotation[i2].total = total;
                    shs_total_other_tax_quotation(frm);
                    cur_frm.refresh_field("shs_tax_quotation");

                    if (tax_row.total === 0) {
                        // Elimina la fila con valor 0
                        cur_frm.doc.shs_tax_quotation.splice(cur_frm.doc.shs_tax_quotation[i2], 1);
                        cur_frm.refresh_field("shs_tax_quotation");
                    }
                }
            });
        }
        //  else {
        //     frm.doc.shs_otros_impuestos.forEach((tax_row, i2) => {

        //     });
        // }

    });

}

function buscar_cuenta_cotizacion(frm, cuenta_b) {
	/**
	 * Funcionamiento: recibe como parametro frm, y cuenta_b, lo que hace es, buscar en todas las filas de taxes
	 * si existe ya una cuenta con el nombre de la cuenta recibida por parametro, en caso ya exista esa cuenta en
	 * la tabla no hace nada, pero si encuentra que no hay una cuenta igual a la recibida en el parametro, entonces
	 * la funcion encargada agregara una nueva fila con los datos correspondientes, esta funcion retorna true
	 * en caso si encuentre una cuenta existente
	 */
    var estado = false;

    $.each(frm.doc.shs_tax_quotation || [], function (i, d) {
        if (d.account_head === cuenta_b) {
            // console.log('Si Existe en el indice ' + i)
            estado = true;
        }
    });

    return estado;
}

/* Cotizacion ------------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Quotation", {
    onload_post_render: function (frm, cdt, cdn) {
        console.log('Funcionando Onload Post Render Trigger'); //SI FUNCIONA EL TRIGGER
        // Funciona unicamente cuando se carga por primera vez el documento y aplica unicamente para el form y no childtables

        // en-US: Enabling event listeners for child tables
        // es-GT: Habilitando escuchadores de eventos en las tablas hijas del tipo de documento principal
        // No corra KEY UP, KEY PRESS, KEY DOWN en este campo!   NO NO NO NO NONONO
        // FIXME FIXME FIXME
        // Objetivo, cuando se salga del campo mediante TAB, que quede registrado el producto.
        // estrategia 1:  Focus al campo de quantity?  NO SIRVE.  Como que hay OTRO campo antes, quizas la flechita de link?
        frm.fields_dict.items.grid.wrapper.on('click focusout blur', 'input[data-fieldname="item_code"][data-doctype="Quotation Item"]', function (e) {
            console.log("Clicked on the field Item Code");

            each_item_quotation(frm, cdt, cdn);
            shs_quotation_calculation(frm, cdt, cdn);
            // facelec_otros_impuestos_fila(frm, cdt, cdn);
        });

        // FIXME NO FUNCIONA CON TAB, SOLO HACIENDO CLICK Y ENTER.  Si se presiona TAB, SE BORRA!
		/*frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="item_code"][data-doctype="Sales Invoice Item"]', function(e) {
			console.log("Blurred away from the Item Code Field");
			each_item_quotation_quotation(frm, cdt, cdn);
			//shs_quotation_calculation(frm, cdt, cdn);
		});*/
        frm.fields_dict.items.grid.wrapper.on('click', 'input[data-fieldname="uom"][data-doctype="Quotation Item"]', function (e) {
            console.log("Click on the UOM field");
            each_item_quotation(frm, cdt, cdn);
        });
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="uom"][data-doctype="Quotation Item"]', function (e) {
            console.log("Blur or focusout from the UOM field");
            each_item_quotation(frm, cdt, cdn);
        });
        // Do not refresh with each_item_quotation in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('mouseleave', 'input[data-fieldname="uom"][data-doctype="Quotation Item"]', function (e) {
            console.log("Mouse left the UOM field");
            shs_quotation_calculation(frm, cdt, cdn);
        });
        // This part might seem counterintuitive, but it is the "next" field in tab order after item code, which helps for a "creative" strategy to update everything after pressing TAB out of the item code field.  FIXME
        frm.fields_dict.items.grid.wrapper.on('focus', 'input[data-fieldname="item_name"][data-doctype="Quotation Item"]', function (e) {
            console.log("Focusing with keyboard cursor through TAB on the Item Name Field");
            each_item_quotation(frm, cdt, cdn);
            catizacion_otros_impuestos_fila(frm, cdt, cdn);
        });
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="qty"][data-doctype="Quotation Item"]', function (e) {
            console.log("Blurring or focusing out from the Quantity Field");
            each_item_quotation(frm, cdt, cdn);
        });
        // Do not refresh with each_item_quotation in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('mouseleave', 'input[data-fieldname="qty"][data-doctype="Quotation Item"]', function (e) {
            console.log("Mouse leaving from the Quantity Field");
            each_item_quotation(frm, cdt, cdn);
            shs_quotation_calculation(frm, cdt, cdn);
        });
        // DO NOT USE Keyup, ??  FIXME FIXME FIXME FIXME FIXME  este hace calculos bien
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="conversion_factor"][data-doctype="Quotation Item"]', function (e) {
            console.log("Blurring or focusing out from the Conversion Factor Field");
            //  IMPORTANT! IMPORTANT!  This is the one that gets the calculations correct!
            // Trying to calc first, then refresh, or no refresh at all...
            each_item_quotation(frm, cdt, cdn);
            cur_frm.refresh_field("conversion_factor");
        });
        // This specific one is only for keyup events, to recalculate all. Only on blur will it refresh everything!
        // Do not refresh with each_item_quotation in Mouse leave OR keyup! just recalculate
        frm.fields_dict.items.grid.wrapper.on('keyup mouseleave focusout', 'input[data-fieldname="conversion_factor"][data-doctype="Quotation Item"]', function (e) {
            console.log("Key up, mouse leave or focus out from the Conversion Factor Field");
            // Trying to calc first, then refresh, or no refresh at all...
            shs_quotation_calculation(frm, cdt, cdn);
            each_item_quotation(frm, cdt, cdn);
            cur_frm.refresh_field("conversion_factor");
        });
        frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="rate"][data-doctype="Quotation Item"]', function (e) {
            console.log("Blurring from the Rate Field");
            // each_item_quotation(frm, cdt, cdn);
        });
        // en-US: Enabling event listeners in the main doctype
        // es-GT: Habilitando escuchadores de eventos en el tipo de documento principal
        // When ANY key is released after being pressed
        cur_frm.fields_dict.customer.$input.on("keyup", function (evt) {
            console.log("Se acaba de soltar una tecla del campo customer");
            shs_quotation_calculation(frm, cdt, cdn);
            each_item_quotation(frm, cdt, cdn);
            refresh_field('qty');
        });
        // When mouse leaves the field
        cur_frm.fields_dict.customer.$input.on("mouseleave blur focusout", function (evt) {
            console.log("Salió del campo customercon mouseleave, blur, focusout");
            shs_quotation_calculation(frm, cdt, cdn);
        });
        // Mouse clicks over the items field
        // cur_frm.fields_dict.items.$wrapper.on("click", function (evt) {
        //     console.log("Puntero de Ratón hizo click en el campo Items");
        //     each_item_quotation(frm, cdt, cdn);
        // });
        // Focusout from the field
        cur_frm.fields_dict.taxes_and_charges.$input.on("focusout", function (evt) {
            console.log("Campo taxes and charges perdió el enfoque via focusout");
            shs_quotation_calculation(frm, cdt, cdn);
            catizacion_otros_impuestos_fila(frm, cdt, cdn);
        });
    },
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        // Works OK!
        frm.add_custom_button("UOM Recalculation", function () {
            frm.doc.items.forEach((item) => {
                // for each button press each line is being processed.
                console.log("item contains: " + item);
                //Importante
                shs_quotation_calculation(frm, "Sales Invoice Item", item.name);
            });
        });
    },
    facelec_qt_nit: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.facelec_qt_nit, frm.doc.customer, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
    },
    customer: function (frm, cdt, cdn) {
        // Trigger Proveedor
    },
    before_save: function (frm, cdt, cdn) {
        // Trigger antes de guardar
        each_item_quotation(frm, cdt, cdn);
        catizacion_otros_impuestos_fila(frm, cdt, cdn);
    }
    //,
    // on_submit: function (frm, cdt, cdn) {
    //     // Ocurre cuando se presione el boton validar.
    //     // Cuando se valida el documento, se hace la consulta al servidor por medio de frappe.call

    //     // Creacion objeto vacio para guardar nombre y valor de las cuentas que se encuentren
    //     let cuentas_registradas = {};

    //     // Recorre la tabla hija en busca de cuentas
    //     frm.doc.shs_otros_impuestos.forEach((tax_row, index) => {
    //         if (tax_row.account_head) {
    //             // Agrega un nuevo valor al objeto (JSON-DICCIONARIO) con el
    //             // nombre, valor de la cuenta
    //             cuentas_registradas[tax_row.account_head] = tax_row.total;
    //         };
    //     });
    //     // console.log(cuentas_registradas);
    //     // console.log(Object.keys(cuentas_registradas).length);

    //     // Si existe por lo menos una cuenta, se ejecuta frappe.call
    //     if (Object.keys(cuentas_registradas).length > 0) {
    //         // llama al metodo python, el cual recibe de parametros el nombre de la factura y el objeto
    //         // con las ('cuentas encontradas
    //         console.log('---------------------- se encontro por lo menos una cuenta--------------------');
    //         frappe.call({
    //             method: "factura_electronica.special_tax.add_gl_entry_other_special_tax",
    //             args: {
    //                 invoice_name: frm.doc.name,
    //                 accounts: cuentas_registradas
    //             },
    //             // El callback se ejecuta tras finalizar la ejecucion del script python del lado
    //             // del servidor
    //             callback: function () {
    //                 // Busca la modalidad configurada, ya sea Manual o Automatica
    //                 // Esto para mostrar u ocultar los botones para la geneneracion de factura
    //                 // electronica
    //                 frappe.call({
    //                     method: "factura_electronica.api.obtenerConfiguracionManualAutomatica",
    //                     callback: function (data) {
    //                         console.log(data.message);
    //                         if (data.message === 'Manual') {
    //                             console.log('Configuracion encontrada: MANUAL');
    //                             // No es necesario tener activa esta parte, ya que cuando se ingresa a cualquier factura en el evento
    //                             // refresh, hay una funcion que se encarga de comprobar de que se haya generado exitosamente la
    //                             // factura electronica, en caso no sea asi, se mostrarán los botones correspondientes, para hacer
    //                             // la generacion de la factura electronica manualmente.
    //                             // generarFacturaBTN(frm, cdt, cdn);
    //                         }
    //                         if (data.message === 'Automatico') {
    //                             console.log('Configuracion encontrada: AUTOMATICO');
    //                             // generarFacturaSINBTN(frm, cdt, cdn);
    //                             verificacionCAE('automatico', frm, cdt, cdn);
    //                         }
    //                     }
    //                 });
    //             }
    //         });
    //     } else {
    //         // Busca la modalidad configurada, ya sea Manual o Automatica
    //         // Esto para mostrar u ocultar los botones para la geneneracion de factura
    //         // electronica
    //         frappe.call({
    //             method: "factura_electronica.api.obtenerConfiguracionManualAutomatica",
    //             callback: function (data) {
    //                 console.log(data.message);
    //                 if (data.message === 'Manual') {
    //                     console.log('Configuracion encontrada: MANUAL');
    //                     /* No es necesario tener activa esta parte, ya que cuando se ingresa a cualquier factura en el evento
    //                     refresh, hay una funcion que se encarga de comprobar de que se haya generado exitosamente la
    //                     factura electronica, en caso no sea asi, se mostrarán los botones correspondientes, para hacer
    //                     la generacion de la factura electronica manualmente.
    //                     generarFacturaBTN(frm, cdt, cdn); */
    //                 }
    //                 if (data.message === 'Automatico') {
    //                     console.log('Configuracion encontrada: AUTOMATICO');
    //                     // generarFacturaSINBTN(frm, cdt, cdn);
    //                     verificacionCAE('automatico', frm, cdt, cdn);
    //                 }
    //             }
    //         });
    //     }

    // }
});

frappe.ui.form.on("Quotation Item", {
    items_add: function (frm, cdt, cdn) { },
    items_move: function (frm, cdt, cdn) { },
    before_items_remove: function (frm, cdt, cdn) {
        frm.doc.items.forEach((item_row_1, index_1) => {
            if (item_row_1.name == cdn) {
                // console.log('La Fila a Eliminar es --------------> ' + item_row_1.item_code);
                totalizar_valores_quotation(frm, cdn, item_row_1.facelec_qt_tax_rate_per_uom_account)
            }
        });
    },
    items_remove: function (frm, cdt, cdn) { },
    item_code: function (frm, cdt, cdn) {
        each_item_quotation(frm, cdt, cdn);
    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_quotation_calculation(frm, cdt, cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        console.log("El disparador de factor de conversión se corrió.");
        shs_quotation_calculation(frm, cdt, cdn);
    },
    facelec_qt_tax_rate_per_uom_account: function (frm, cdt, cdn) { },
    rate: function (frm, cdt, cdn) {
        shs_quotation_calculation(frm, cdt, cdn);
    }
});