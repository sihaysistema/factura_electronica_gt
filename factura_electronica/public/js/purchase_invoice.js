import { valNit } from './facelec.js';
import { goalSeek } from './goalSeek.js';


/* Purchase Invoice (Factura de Compra) ------------------------------------------------------------------------------------------------------- */
/**
 * Genera iteraciones extra sobre los items, y asegurar calculos mas
 * precisos
 *
 * @param {Object} frm
 * @param {String} cdt
 * @param {String} cdn
 */
function pi_each_item(frm, cdt, cdn) {
    frm.doc.items.forEach((item) => {
        shs_purchase_invoice_calculation(frm, "Purchase Invoice Item", item.name);
        pi_insertar_fila_otro_impuesto(frm, "Purchase Invoice Item", item.name);
    });
}


/**
 * Genera la suma total de impuestos especiales
 * por cuenta
 *
 * @param {Object} frm
 * @param {String} tax_account - Nombre cuenta impuesto especial
 * @return {float}
 */
function pi_sumatoria_por_cuenta_items(frm, tax_account) {
    var total_sumatoria = 0;

    $.each(frm.doc.items || [], function (i, d) {
        if (d.facelec_p_tax_rate_per_uom_account === tax_account) {
            total_sumatoria += flt(d.facelec_p_other_tax_amount);
        };
    });

    return total_sumatoria;
}


/**
 * Recorre items, en busca de impuestos especiales, para luego ser sumados
 * con los que sean del mismo tipo, para luego ser agrega la cuenta y monto
 * a la tabla hija de otros impuestos
 *
 * @param {Object} frm
 * @param {String} cdt
 * @param {String} cdn
 */
function pi_sumatoria_otros_impuestos_por_cuenta(frm, cdt, cdn) {
    frm.doc.items.forEach((item_row_1, index_1) => {
        if (item_row_1.name === cdn) {
            if (item_row_1.facelec_p_tax_rate_per_uom_account) {

                frm.doc.shs_pi_otros_impuestos.forEach((tax_row_2, index_2) => {

                    if (tax_row_2.account_head === item_row_1.facelec_p_tax_rate_per_uom_account) {
                        var totalizador = 0;
                        totalizador = pi_sumatoria_por_cuenta_items(frm, tax_row_2.account_head)
                        cur_frm.doc.shs_pi_otros_impuestos[index_2].total = totalizador;
                        pi_total_de_otros_impuestos(frm);
                    }

                });

            }
        }
    });
}


/**
 * Suma el total de montos que se encuentren en Otros Impuestos Especiales
 *
 * @param {*} frm
 */
function pi_total_de_otros_impuestos(frm) {
    var total_tax = 0;

    $.each(frm.doc.shs_pi_otros_impuestos || [], function (i, d) {
        if (d.account_head) {
            total_tax += flt(d.total);
        };
    });

    cur_frm.set_value('shs_pi_total_otros_imp_incl', total_tax);
    frm.refresh_field("shs_pi_total_otros_imp_incl");
}


/**
 * Recorre la tabla items, por cada fila con una cuenta asignada buscara en la tabla hija
 * shs_pi_otros_impuestos por una fila con el mismo nombre de la cuenta anteriormente encontrada,
 * si no la encuentra en shs_pi_otros_impuestos creara una nueva fila, y le asignara los valores
 * de nombre de cuenta y el total para esa cuenta. Si la cuenta ya se encuentra creada en
 * shs_pi_otros_impuestos le sumara los valores encontrados.
 *
 * @param {Object} frm
 * @param {String} cdt
 * @param {String} cdn
 */
function pi_insertar_fila_otro_impuesto(frm, cdt, cdn) {
    var shs_otro_impuesto = 0;

    frm.doc.items.forEach((item_row_i, indice) => {
        if (item_row_i.name === cdn) {
            shs_otro_impuesto = item_row_i.facelec_p_other_tax_amount;

            // Guarda el nombre de la cuenta del item seleccionado
            var cuenta = item_row_i.facelec_p_tax_rate_per_uom_account;
            // console.log('Cuenta de item encontrada es : ' + cuenta);

            frm.refresh_field('items');
            frm.refresh_field('conversion_factor');

            if (cuenta) { // Si encuentra una cuenta con nombre procede
                if (!(pi_buscar_cuenta(frm, cuenta))) { // Si no encuentra una cuenta, procede.

                    frappe.model.add_child(cur_frm.doc, "Otros Impuestos Factura Electronica", "shs_pi_otros_impuestos");
                    // Refresh datos de la tabla hija items
                    cur_frm.refresh_field('items');
                    // Recorre la tabla hija 'taxes' en busca de la nueva fila que se agrego anteriormente donde account_head
                    // sea undefined
                    frm.doc.shs_pi_otros_impuestos.forEach((tax_row, index) => {

                        // Si encuentra la fila anteriormente agregada procede
                        if (tax_row.account_head === undefined) {
                            // Asigna valores en la fila recien creada
                            cur_frm.doc.shs_pi_otros_impuestos[index].account_head = cuenta;
                            cur_frm.doc.shs_pi_otros_impuestos[index].total = shs_otro_impuesto;
                            // Actualiza los datos de la tabla hija
                            cur_frm.refresh_field("shs_pi_otros_impuestos");
                            // Funcion que se encarda de sumar los valores por cuenta
                            pi_sumatoria_otros_impuestos_por_cuenta(frm, cdt, cdn);
                            cur_frm.refresh_field("shs_pi_otros_impuestos");
                        }

                    });

                } else { // Si la cuenta ya esta agregada en shs_pi_otros_impuestos, se procede a sumar sobre los valores
                    // ya existentes
                    // Funcion que se encarda de sumar los valores por cuenta
                    pi_sumatoria_otros_impuestos_por_cuenta(frm, cdt, cdn);
                    cur_frm.refresh_field("shs_pi_otros_impuestos");
                }
            }
        }
    });

}


/**
 * Recalculo los montos de impuestos especiales, cuando se eliminan n filas
 *
 * @param {*} frm
 * @param {*} cdn
 * @param {*} tax_account_n - Nombre cuenta impuestos especial
 * @param {*} otro_impuesto - Monto impuesto que se esta eliminando
 */
function pi_total_otros_impuestos_eliminacion(frm, tax_account_n, otro_impuesto) {
    // Recorre items
    frm.doc.items.forEach((item_row, i1) => {
        if (item_row.facelec_p_tax_rate_per_uom_account === tax_account_n) {
            var total = (pi_sumatoria_por_cuenta_items(frm, tax_account_n) - otro_impuesto);
            // recorre shs_pi_otros_impuestos

            if (frm.doc.shs_pi_otros_impuestos !== undefined) {
                frm.doc.shs_pi_otros_impuestos.forEach((tax_row, i2) => {
                    if (tax_row.account_head === tax_account_n) {
                        cur_frm.doc.shs_pi_otros_impuestos[i2].total = total;
                        cur_frm.refresh_field("shs_pi_otros_impuestos");
                        pi_total_de_otros_impuestos(frm);
                        cur_frm.refresh_field("shs_pi_otros_impuestos");

                        if (!tax_row.total) {
                            // Elimina la fila con valor 0
                            cur_frm.doc.shs_pi_otros_impuestos.splice(cur_frm.doc.shs_pi_otros_impuestos[i2], 1);
                            cur_frm.refresh_field("shs_pi_otros_impuestos");
                        }
                    }
                });
            }

        }
    });

}


/**
 * Buscador de cuentas en tabla hija de otros impuestos
 *
 * @param {*} frm
 * @param {*} cuenta_b
 * @return {*}
 */
function pi_buscar_cuenta(frm, cuenta_b) {

    var estado = false;

    $.each(frm.doc.shs_pi_otros_impuestos || [], function (i, d) {
        if (d.account_head === cuenta_b) {
            estado = true;
        }
    });

    return estado;
}


/**
 * Funcion central encargada de los calculos realtime y para
 * usar en generación de docs electrónicos
 *
 * @param {Object} frm
 * @param {String} cdt
 * @param {String} cdn
 */
function shs_purchase_invoice_calculation(frm, cdt, cdn) {
    cur_frm.refresh_fields();
    // INICIO validacion existencia tabla impuesto
    var this_company_sales_tax_var = 0;

    if ((cur_frm.doc.taxes.length > 0) && (cur_frm.doc.taxes[0].rate !== "undefined")) {
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
    } else {
        // Muestra una notificacion para cargar una tabla de impuestos
        frappe.show_alert({
            message: __('Tabla de impuestos no se encuentra cargada, por favor agregarla para que los calculos se generen correctamente'),
            indicator: 'red'
        }, 5);

        this_company_sales_tax_var = 0
    }
    // FIN validacion existencia tabla impuesto

    var this_row_amount = 0;
    var this_row_stock_qty = 0;
    var this_row_tax_rate = 0;
    var this_row_tax_amount = 0;
    var this_row_taxable_amount = 0;

    frm.doc.items.forEach((item_row, index) => {

        if (item_row.name == cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.facelec_p_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);

            frm.doc.items[index].facelec_p_other_tax_amount = ((item_row.facelec_p_tax_rate_per_uom * (item_row.qty *
                item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].facelec_p_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty *
                item_row.conversion_factor) * item_row.facelec_p_tax_rate_per_uom));

            if (item_row.facelec_p_is_fuel) {
                frm.doc.items[index].facelec_p_gt_tax_net_fuel_amt = (item_row.facelec_p_amount_minus_excise_tax / (1 + (
                    this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_p_sales_tax_for_this_row = (item_row.facelec_p_gt_tax_net_fuel_amt * (
                    this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                let total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_p_is_fuel == true) {
                        total_fuel += flt(d.facelec_p_gt_tax_net_fuel_amt);
                    };
                });
                frm.doc.facelec_p_gt_tax_fuel = total_fuel;
            };

            if (item_row.facelec_p_is_good) {
                frm.doc.items[index].facelec_p_gt_tax_net_goods_amt = (item_row.facelec_p_amount_minus_excise_tax / (1 + (
                    this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_p_sales_tax_for_this_row = (item_row.facelec_p_gt_tax_net_goods_amt * (
                    this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                let total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_p_is_good == true) {
                        total_goods += flt(d.facelec_p_gt_tax_net_goods_amt);
                    };
                });
                frm.doc.facelec_p_gt_tax_goods = total_goods;
            };

            if (item_row.facelec_p_is_service == 1) {
                frm.doc.items[index].facelec_p_gt_tax_net_services_amt = (item_row.facelec_p_amount_minus_excise_tax / (
                    1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_p_sales_tax_for_this_row = (item_row.facelec_p_gt_tax_net_services_amt * (
                    this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check servicios
                let total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_p_is_service == true) {
                        total_servi += flt(d.facelec_p_gt_tax_net_services_amt);
                    };
                });
                frm.doc.facelec_p_gt_tax_services = total_servi;
            };

            let full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.facelec_p_sales_tax_for_this_row);
            });
            frm.doc.facelec_p_total_iva = full_tax_iva;
        };
    });
}


/**
 * Renderiza tabla HTML con detalles de impuestos e impuestos especiales
 *
 * @param {*} frm
 */
function generar_tabla_html_factura_compra(frm) {
    // PURCHASE INVOICE
    if (frm.doc.items.length > 0) {
        const mi_array = frm.doc.items;
        const mi_array_dos = Array.from(mi_array);
        // console.log(mi_array_dos);
        frappe.call({
            method: "factura_electronica.api.generar_tabla_html_factura_compra",
            args: {
                tabla: JSON.stringify(mi_array_dos)
            },
            callback: function (data) {
                frm.set_value('other_tax_facelec', data.message);
                frm.refresh_field("other_tax_facelec");
            }
        });
    }
}


frappe.ui.form.on("Purchase Invoice", {
    refresh: function (frm, cdt, cdn) {
        // Limpieza de campos cuando se duplique una factura de compra
        clean_fields(frm);

        // Validador para mostrar botones segun escenario invoice
        if (frm.doc.docstatus != 0) {
            frappe.call({
                method: 'factura_electronica.fel_api.is_valid_to_fel',
                args: {
                    doctype: frm.doc.doctype,
                    docname: frm.doc.name,
                },
                callback: function (data) {
                    console.log(data.message);

                    // FACTURA ESPECIAL
                    if (data.message[0] == 'FESP' && data.message[1]) {
                        btn_factura_especial(frm);
                        if (frm.doc.numero_autorizacion_fel) {
                            cur_frm.clear_custom_buttons();
                            pdf_electronic_doc(frm);
                            btn_poliza_factura_especial(frm);
                        }
                    }

                    // NOTA DE DEBITO
                    if (data.message[0] == 'NDEB' && data.message[1]) {
                        btn_debit_note(frm);
                        if (frm.doc.numero_autorizacion_fel) {
                            cur_frm.clear_custom_buttons();
                            pdf_electronic_doc(frm);
                        }
                    }
                },
            });
        }

    },
    onload_post_render: function (frm, cdt, cdn) {

        // Activa los listener cuando se carga el documento
        frm.fields_dict.items.grid.wrapper.on('focusout blur',
            'input[data-fieldname="item_code"][data-doctype="Purchase Invoice Item"]',
            function (e) {
                shs_purchase_invoice_calculation(frm, cdt, cdn);
                pi_each_item(frm, cdt, cdn);
            });

        frm.fields_dict.items.grid.wrapper.on('blur focusout click',
            'input[data-fieldname="uom"][data-doctype="Purchase Invoice Item"]',
            function (e) {
                shs_purchase_invoice_calculation(frm, cdt, cdn);
                pi_each_item(frm, cdt, cdn);
            });

        // This part might seem counterintuitive, but it is the "next" field in tab order after item code, which helps for a "creative" strategy to update everything after pressing TAB out of the item code field.  FIXME
        frm.fields_dict.items.grid.wrapper.on('blur',
            'input[data-fieldname="item_name"][data-doctype="Purchase Invoice Item"]',
            function (e) {
                pi_each_item(frm, cdt, cdn);
                pi_insertar_fila_otro_impuesto(frm, cdt, cdn);
            });

        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="qty"][data-doctype="Purchase Invoice Item"]',
            function (e) {
                pi_each_item(frm, cdt, cdn);
                shs_purchase_invoice_calculation(frm, cdt, cdn);
            });

        // This specific one is only for keyup events, to recalculate all. Only on blur will it refresh everything!
        // Do not refresh with each_item in Mouse leave OR keyup! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="conversion_factor"][data-doctype="Purchase Invoice Item"]',
            function (e) {
                // Trying to calc first, then refresh, or no refresh at all...
                shs_purchase_invoice_calculation(frm, cdt, cdn);
                pi_each_item(frm, cdt, cdn);
                cur_frm.refresh_field("conversion_factor");
            });

        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="shs_amount_for_back_calc"][data-doctype="Purchase Invoice Item"]',
            function (e) {
                //console.log("Blurring or focusing out from the Quantity Field");
                pi_each_item(frm, cdt, cdn);
                shs_purchase_invoice_calculation(frm, cdt, cdn);
            });

        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="facelec_p_other_tax_amount"][data-doctype="Purchase Invoice Item"]',
            function (e) {
                //console.log("Blurring or focusing out from the Quantity Field");
                pi_each_item(frm, cdt, cdn);
                shs_purchase_invoice_calculation(frm, cdt, cdn);
            });

        // Focusout from the field
        if (cur_frm.fields_dict.taxes_and_charges.$input) {  // Asegura no mostrar errores innecesarios
            cur_frm.fields_dict.taxes_and_charges.$input.on("blur focusout click", function (evt) {
                pi_each_item(frm, cdt, cdn);
                shs_purchase_invoice_calculation(frm, cdt, cdn);
                pi_insertar_fila_otro_impuesto(frm, cdt, cdn);
            });
        }
    },
    facelec_nit_fproveedor: function (frm, cdt, cdn) {
        // Para evitar muchos mensajes de error, la validacion se hace desde el cliente
        // valNit(frm.doc.facelec_nit_fproveedor, frm.doc.supplier, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        var tax_before_calc = frm.doc.facelec_total_iva;;
        // es-GT: Este muestra el IVA que se calculo por medio de nuestra aplicación.
        var discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));

        if (discount_amount_net_value == NaN || discount_amount_net_value == undefined) { } else {
            // console.log("El descuento parece ser un numero definido, calculando con descuento.");
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            // console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_total_iva = (frm.doc.facelec_total_iva - discount_amount_tax_value);
            // console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
        }
    },
    before_save: function (frm, cdt, cdn) {
        pi_each_item(frm, cdt, cdn);
        pi_insertar_fila_otro_impuesto(frm, cdt, cdn);
        // Trigger antes de guardar
    },
    validate: function (frm) {
        generar_tabla_html_factura_compra(frm);
    },
    on_submit: function (frm, cdt, cdn) {
        // Ocurre cuando se presione el boton validar.
        // Cuando se valida el documento, se hace la consulta al servidor por medio de frappe.call

        // Creacion objeto vacio para guardar nombre y valor de las cuentas que se encuentren
        let cuentas_registradas = {};

        // Recorre la tabla hija en busca de cuentas
        frm.doc.shs_pi_otros_impuestos.forEach((tax_row, index) => {
            if (tax_row.account_head) {
                // Agrega un nuevo valor al objeto (JSON-DICCIONARIO) con el
                // nombre, valor de la cuenta
                cuentas_registradas[tax_row.account_head] = tax_row.total;
            };
        });
        // console.log(cuentas_registradas);
        // console.log(Object.keys(cuentas_registradas).length);

        // Si existe por lo menos una cuenta, se ejecuta frappe.call
        if (Object.keys(cuentas_registradas).length > 0) {
            frappe.call({
                method: "factura_electronica.utils.special_tax.add_gl_entry_other_special_tax",
                args: {
                    invoice_name: frm.doc.name,
                    accounts: cuentas_registradas,
                    invoice_type: "Purchase Invoice"
                },
                // El callback se ejecuta tras finalizar la ejecucion del script python del lado
                // del servidor
                callback: function () {
                    frm.reload_doc();
                }
            });
        }
    },
    naming_series: function (frm, cdt, cdn) {

        // console.log(frm.doc.naming_series);

        /* No aplica para FEL
        // frappe.call({
        //     method: "factura_electronica.utils.special_invoice.verificar_existencia_series",
        //     args: {
        //         serie: frm.doc.naming_series
        //     },
        //     callback: function (r) {
        //         // frm.reload_doc();
        //         console.log(r.message);

        //         if (r.message != 'fail') {
        //             // Limpia la tabla hija de Purchase Taxes and Charges
        //             cur_frm.clear_table("taxes");
        //             cur_frm.refresh_fields();

        //             // Asigna el nombre de la plantilla de impuestos a utilizar configurada
        //             frm.set_value('taxes_and_charges', r.message[2]);
        //             frm.refresh_field("taxes_and_charges");
        //         }
        //     }
        // });
        **/
    }
});

frappe.ui.form.on("Purchase Invoice Item", {
    before_items_remove: function (frm, cdt, cdn) {
        // let row = frappe.get_doc(cdt, cdn);
        // pi_total_otros_impuestos_eliminacion(frm, row.facelec_p_tax_rate_per_uom_account, row.facelec_p_other_tax_amount);

        let row = frappe.get_doc(cdt, cdn);  // Asegura mas precisio de que data se debe trabajar
        pi_total_otros_impuestos_eliminacion(frm, row.facelec_p_tax_rate_per_uom_account, row.facelec_p_other_tax_amount);

        // frm.doc.items.forEach((item_row_1, index_1) => {
        //     if (item_row_1.name == cdn) {
        //         pi_total_otros_impuestos_eliminacion(frm, item_row_1.facelec_p_tax_rate_per_uom_account, item_row_1.facelec_p_other_tax_amount);
        //     }
        // });
    },
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.

        var fix_gt_tax_fuel = 0;
        var fix_gt_tax_goods = 0;
        var fix_gt_tax_services = 0;
        var fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function (i, d) {
            fix_gt_tax_fuel += flt(d.facelec_p_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.facelec_p_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.facelec_p_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.facelec_p_sales_tax_for_this_row);
        });

        cur_frm.set_value("facelec_p_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("facelec_p_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("facelec_p_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("facelec_p_total_iva", fix_gt_tax_iva);
    },
    item_code: function (frm, cdt, cdn) {
        // Trigger codigo de producto
        // var this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        // console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
        pi_each_item(frm, cdt, cdn);
    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_purchase_invoice_calculation(frm, cdt, cdn);
        // console.log("cdt contains: " + cdt);
        // console.log("cdn contains: " + cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        // console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        // console.log("El disparador de factor de conversión se corrió.");
        shs_purchase_invoice_calculation(frm, cdt, cdn);
    },
    rate: function (frm, cdt, cdn) {
        shs_purchase_invoice_calculation(frm, cdt, cdn);
    },
    shs_amount_for_back_calc: function (frm, cdt, cdn) {
        frm.doc.items.forEach((row, index) => {
            var a = row.rate;
            var b = row.qty;
            var c = row.amount;

            let calcu = goalSeek({
                Func: redondeo_sales_invoice,
                aFuncParams: [b, a],
                oFuncArgTarget: {
                    Position: 0
                },
                Goal: row.shs_amount_for_back_calc,
                Tol: 0.001,
                maxIter: 10000
            });
            // console.log(calcu);

            frm.doc.items[index].qty = calcu;
            frm.doc.items[index].stock_qty = calcu;
            frm.doc.items[index].amount = calcu * frm.doc.items[index].rate;
            // frm.doc.items[index].qty = calcu;

            // frm.set_value('qty', calcu);
            frm.refresh_field("items");

            pi_each_item(frm, cdt, cdn);
            pi_insertar_fila_otro_impuesto(frm, cdt, cdn);
        });
    }
});


/**
 * Funcion a evaluar por goalseek
 *
 * @param {*} a
 * @param {*} b
 * @return {*}
 */
function redondeo_sales_invoice(a, b) {
    return a * b;
}


/**
 * Agrega boton para generar facturas especiales electronicas, si ocurre un error
 * mostrara un mensaje con la descripcion, si todo va bien automaticamente se reemplazara
 * la pagina con los datos correctos
 *
 * @param {object} frm
 */
function btn_factura_especial(frm) {
    cur_frm.clear_custom_buttons();
    frm.add_custom_button(__("GENERAR FACTURA ESPECIAL ELECTRONICA FEL"), function () {
        frappe.confirm(__('Are you sure you want to proceed to generate a Electronic Special Invoice?'),
            () => {
                let serie_de_factura = frm.doc.name;
                // Guarda la url actual
                let mi_url = window.location.href;
                frappe.call({
                    method: 'factura_electronica.fel_api.generate_special_invoice',
                    args: {
                        invoice_code: frm.doc.name,
                        naming_series: frm.doc.naming_series
                    },
                    callback: function (r) {
                        // console.log(r.message);
                        if (r.message[0] === true) {
                            // Crea una nueva url con el nombre del documento actualizado
                            let url_nueva = mi_url.replace(serie_de_factura, r.message[1]);
                            // Asigna la nueva url a la ventana actual
                            window.location.assign(url_nueva);
                            // Recarga la pagina
                            frm.reload_doc();
                        }
                    },
                });
            }, () => {
                // action to perform if No is selected
                // console.log('Selecciono NO')
            });
    }).addClass("btn-warning");
}


/**
 * Agrega un boton para generar especificamente polizas contables para facturas especiales
 *
 * @param {object} frm
 */
function btn_poliza_factura_especial(frm) {
    cur_frm.page.add_action_item(__("Journal Entry for Special Invoice"), function () {

        let d = new frappe.ui.Dialog({
            title: 'New Journal Entry with Withholding Tax for special invoice',
            fields: [{
                label: 'Cost Center',
                fieldname: 'cost_center',
                fieldtype: 'Link',
                options: 'Cost Center',
                "get_query": function () {
                    return {
                        filters: {
                            'company': frm.doc.company
                        }
                    }
                },
                default: ""
            },
            {
                label: 'Source account',
                fieldname: 'credit_in_acc_currency',
                fieldtype: 'Link',
                options: 'Account',
                "reqd": 1,
                "get_query": function () {
                    return {
                        filters: {
                            'company': frm.doc.company
                        }
                    }
                }
            },
            {
                fieldname: 'col_br_asdffg',
                fieldtype: 'Column Break'
            },
            {
                label: 'Is Multicurrency',
                fieldname: 'is_multicurrency',
                fieldtype: 'Check'
            },
            {
                label: 'NOTE',
                fieldname: 'note',
                fieldtype: 'Data',
                read_only: 1,
                default: 'Los cálculos se realizaran correctamente si se encuentran configurados en company, y si el iva va incluido en la factura'
            },
            {
                label: 'Description',
                fieldname: 'section_asdads',
                fieldtype: 'Section Break',
                "collapsible": 1
            },
            {
                label: 'Description',
                fieldname: 'description',
                fieldtype: 'Long Text'
            }
            ],
            primary_action_label: 'Create',
            primary_action(values) {
                frappe.call({
                    method: 'factura_electronica.api_erp.journal_entry_isr_purchase_inv',
                    args: {
                        invoice_name: frm.doc.name,
                        cost_center: values.cost_center,
                        credit_in_acc_currency: values.credit_in_acc_currency,
                        is_multicurrency: values.is_multicurrency,
                        description: values.description
                    },
                    callback: function (r) {
                        // console.log(r.message);
                        d.hide();
                        frm.refresh()
                    },
                });
            }
        });

        d.show();
    });
}


/**
 * Render para boton nota de debito electronica
 *
 * @param {*} frm
 */
function btn_debit_note(frm) {
    // INICIO BOTON NOTA DE DEBITO
    cur_frm.clear_custom_buttons();
    frm.add_custom_button(__("GENERAR NOTA DE DEBITO ELECTRONICA FEL"), function () {
        // Permite hacer confirmaciones
        frappe.confirm(
            __("Are you sure you want to proceed to generate a electronic debit note?"),
            () => {
                let d = new frappe.ui.Dialog({
                    title: __("Generate Electronic Debit Note"),
                    fields: [{
                        label: __("Reason Adjusment?"),
                        fieldname: "reason_adjust",
                        fieldtype: "Data",
                        reqd: 1,
                    },],
                    primary_action_label: __("Submit"),
                    primary_action(values) {
                        frappe.call({
                            method: "factura_electronica.fel_api.generate_debit_note",
                            args: {
                                invoice_code: frm.doc.name,
                                naming_series: frm.doc.naming_series,
                                uuid_purch_inv: frm.doc.bill_no,
                                date_inv_origin: frm.doc.bill_date,
                                reason: values.reason_adjust,
                            },
                            callback: function (r) {
                                console.log(r.message);

                                // if (r.message[0] === true) {
                                //     // Crea una nueva url con el nombre del documento actualizado
                                //     let url_nueva = mi_url.replace(serie_de_factura, r.message[1]);
                                //     // Asigna la nueva url a la ventana actual
                                //     window.location.assign(url_nueva);
                                //     // Recarga la pagina
                                //     frm.reload_doc();
                                // }
                            },
                        });
                        d.hide();
                    },
                });

                d.show();
            },
            () => {
                // action to perform if No is selected
                // console.log("Selecciono NO");
            }
        );
    }).addClass("btn-warning");
    // FIN BOTON NOTA DE DEBITO
}


/**
 * Render para boton pdf doc electronico
 *
 * @param {*} frm
 */
function pdf_electronic_doc(frm) {
    frm.add_custom_button(__("VER PDF DOCUMENTO ELECTRONICO"),
        function () {
            window.open("https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" +
                frm.doc.numero_autorizacion_fel);
        }).addClass("btn-primary");
}


/**
 * LLimpia campos con data no necesaria al momento de duplicar
 *
 * @param {*} frm
 */
function clean_fields(frm) {
    // Funcionalidad evita copiar CAE cuando se duplica una factura
    // LIMPIA/CLEAN, permite limpiar los campos cuando se duplica una factura
    if (frm.doc.status === 'Draft' || frm.doc.docstatus == 0) {
        // console.log('No Guardada');
        frm.set_value("facelec_tax_retention_guatemala", '');
        frm.set_value("numero_autorizacion_fel", '');
        frm.set_value("serie_original_del_documento", '');

        frm.refresh_fields();
    }
}