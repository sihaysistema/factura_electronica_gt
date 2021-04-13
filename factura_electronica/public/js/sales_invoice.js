/**
 * Copyright (c) 2017, 2018, 2019 SHS and contributors
 * For license information, please see license.txt
 */

import { valNit } from './facelec.js';
import { goalSeek } from './goalSeek.js';


/**
 * Funcion central encargada de los calculos realtime y para
 * usar en generación de docs electrónicos
 *
 * @param {Object} frm
 * @param {String} cdt
 * @param {String} cdn
 */
function facelec_tax_calc_new(frm, cdt, cdn) {

    // es-GT: Valida que exista una tabla de impuestos, sea 0 con rate 12
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

    // es-GT: Ahora se hace con un event listener al primer teclazo del campo de cliente
    // es-GT: Sin embargo queda aqui para asegurar que el valor sea el correcto en todo momento.
    var this_row_amount = 0;
    var this_row_stock_qty = 0;
    var this_row_tax_rate = 0;
    var this_row_tax_amount = 0;
    var this_row_taxable_amount = 0;

    // es-GT: Esta funcion permite trabajar linea por linea de la tabla hija items
    //OJO! FIXME Queda pendiente trabajar la forma de que el control o pop up que contiene estos datos, a la hora de cambiar conversion factor, funcione adecuadamente sin depender en un mouse click fuera del campo o que se tenga que guardar. Por ahora solo con hacer click afuera del campo o guardar o ingresar a otro campo con la funcion each_item, se actualiza correctamente.  Es un fix temporal, aunque se debe siempre guardar cualquier documento, y al validar tambien se debe correr correctamente!
    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name === cdn) {
            // first we calculate the amount total for this row and assign it to a variable
            //this_row_amount = (item_row.qty * item_row.rate);
            this_row_amount = item_row.amount;

            // Now, we get the quantity in terms of stock quantity by multiplying by conversion factor
            this_row_stock_qty = item_row.stock_qty;

            // We then assign the tax rate per stock UOM to a variable
            this_row_tax_rate = item_row.facelec_tax_rate_per_uom;

            // We calculate the total amount of excise or special tax based on the stock quantity and tax rate per uom variables above.
            this_row_tax_amount = (item_row.stock_qty * item_row.facelec_tax_rate_per_uom);

            // We then estimate the remainder taxable amount for which Other ERPNext configured taxes will apply.
            this_row_taxable_amount = (item_row.amount - (item_row.stock_qty * item_row.facelec_tax_rate_per_uom));

            // We change the fields for other tax amount as per the complete row taxable amount.
            frm.doc.items[index].facelec_other_tax_amount = ((item_row.facelec_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            frm.doc.items[index].facelec_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - (item_row.stock_qty * item_row.facelec_tax_rate_per_uom));

            // We refresh the items to recalculate everything to ensure proper math
            frm.refresh_field("items");
            frm.refresh_field("conversion_factor");

            // Verificacion Individual para verificar si es Fuel, Good o Service
            if (item_row.factelecis_fuel) {
                frm.doc.items[index].facelec_gt_tax_net_fuel_amt = (item_row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
            };

            if (item_row.facelec_is_good) {
                frm.doc.items[index].facelec_gt_tax_net_goods_amt = (item_row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
            };

            if (item_row.facelec_is_service) {
                frm.doc.items[index].facelec_gt_tax_net_services_amt = (item_row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
            };

            var total_iva_factura = 0;
            $.each(frm.doc.items || [], function (i, d) {
                if (d.facelec_sales_tax_for_this_row) {
                    total_iva_factura += flt(d.facelec_sales_tax_for_this_row);
                };
            });
            // console.log("El total de iva acumulado para la factura es: " + total_iva_factura);
            cur_frm.set_value('shs_total_iva_fac', total_iva_factura);
        };
    });
}


/**
 * Genera iteraciones extra sobre los items, y asegurar calculos mas
 * precisos
 *
 * @param {Object} frm
 * @param {String} cdt
 * @param {String} cdn
 */
function each_item(frm, cdt, cdn) {
    // es-GT: Esta permite ya que se calcule correctamente desde el INICIO!
    // es-GT: Sin necesidad de Guardar antes!
    frm.doc.items.forEach((item) => {
        facelec_tax_calc_new(frm, "Sales Invoice Item", item.name);
        facelec_otros_impuestos_fila(frm, "Sales Invoice Item", item.name);
    });
}


/* Funciones para otros impuestos IDP ... ------------------------------------------------------------------------ */

/**
 * Genera la suma total de impuestos especiales
 * por cuenta
 *
 * @param {Object} frm
 * @param {String} tax_account - Nombre cuenta impuesto especial
 * @return {float}
 */
function facelec_add_taxes(frm, tax_account) {
    var total_sumatoria = 0;

    $.each(frm.doc.items || [], function (i, d) {
        if (d.facelec_tax_rate_per_uom_account === tax_account) {
            total_sumatoria += flt(d.facelec_other_tax_amount);
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
function sumar_otros_impuestos_shs(frm, cdt, cdn) {
    frm.doc.items.forEach((item_row_1, index_1) => {

        if (item_row_1.name === cdn) {
            if (item_row_1.facelec_tax_rate_per_uom_account) {
                if (frm.doc.shs_otros_impuestos !== undefined) {
                    frm.doc.shs_otros_impuestos.forEach((tax_row_2, index_2) => {
                        if (tax_row_2.account_head === item_row_1.facelec_tax_rate_per_uom_account) {
                            var totalizador = 0;
                            totalizador = facelec_add_taxes(frm, tax_row_2.account_head)
                            cur_frm.doc.shs_otros_impuestos[index_2].total = totalizador;
                            shs_total_other_tax(frm);
                        }
                    });
                }

            }
        }
    });
}


/**
 * Suma el total de montos que se encuentren en Otros Impuestos Especiales
 *
 * @param {*} frm
 */
function shs_total_other_tax(frm) {
    var total_tax = 0;

    $.each(frm.doc.shs_otros_impuestos || [], function (i, d) {
        if (d.account_head) {
            total_tax += flt(d.total);
        };
    });

    cur_frm.set_value('shs_total_otros_imp_incl', total_tax);
    frm.refresh_field("shs_total_otros_imp_incl");
}


/**
 * Recorre items en busca de impuestos especiales, para agregarlo en la tabla del otros impuestos
 * sumar, y acumular por tipo
 *
 * @param {Object} frm
 * @param {String} cdt
 * @param {String} cdn
 */
function facelec_otros_impuestos_fila(frm, cdt, cdn) {
    cur_frm.refresh_field("shs_otros_impuestos");

    var this_row_tax_amount = 0; // Valor IDP
    var shs_otro_impuesto = 0;

    frm.doc.items.forEach((item_row_i, indice) => {
        if (item_row_i.name === cdn) {
            // Refresh data de la tabla hija items y conversion_factor
            frm.refresh_field('items');
            frm.refresh_field('conversion_factor');

            // Guarda el nombre de la cuenta del item seleccionado
            var cuenta = item_row_i.facelec_tax_rate_per_uom_account;

            if (cuenta) { // Si encuentra una cuenta con nombre procede
                // Calculos Alain
                this_row_tax_amount = (item_row_i.stock_qty * item_row_i.facelec_tax_rate_per_uom);
                shs_otro_impuesto = item_row_i.facelec_other_tax_amount;

                if (!(buscar_account(frm, cuenta))) { // Si no encuentra una cuenta, procede.
                    // Crea una nueva fila vacia en la tabla hija shs_otros_impuestos
                    frappe.model.add_child(cur_frm.doc, "Otros Impuestos Factura Electronica", "shs_otros_impuestos");

                    // Refresh datos de la tabla hija items
                    cur_frm.refresh_field('items');
                    // Recorre la tabla hija 'taxes' en busca de la nueva fila que se agrego anteriormente donde account_head
                    // sea undefined
                    frm.doc.shs_otros_impuestos.forEach((tax_row, index) => {
                        // Si encuentra la fila anteriormente agregada procede
                        if (tax_row.account_head === undefined) {
                            // Asigna valores en la fila recien creada
                            cur_frm.doc.shs_otros_impuestos[index].account_head = cuenta;
                            cur_frm.doc.shs_otros_impuestos[index].total = shs_otro_impuesto;

                            // Actualiza los datos de la tabla hija
                            cur_frm.refresh_field("shs_otros_impuestos");

                            // Funcion que se encarga de sumar los valores por cuenta
                            sumar_otros_impuestos_shs(frm, cdt, cdn);
                            cur_frm.refresh_field("shs_otros_impuestos");
                        }
                    });

                } else { // Si la cuenta ya esta agregada en shs_otros_impuestos, se procede a sumar sobre los valores
                    // ya existentes
                    // Funcion que se encarda de sumar los valores por cuenta
                    sumar_otros_impuestos_shs(frm, cdt, cdn);
                    cur_frm.refresh_field("shs_otros_impuestos");
                }
            }
        }
    });

}



/**
 * Recorre items, si no hay filas con cuentas de impuesto especiales
 * limpia y recalcula la tabla de otros impuestos
 *
 * @param {*} frm
 * @param {*} cdt
 * @param {*} cdn
 */
function validate_items_acc(frm, cdt, cdn) {
    var items_acc = [];
    frm.doc.items.forEach((item_row_i, indice) => {
        if (item_row_i.facelec_tax_rate_per_uom_account) {
            items_acc.push(true);
        }
    });

    if (!items_acc.length) {
        // console.log('No hay items con impuestos especiales');
        frm.doc.shs_otros_impuestos = [];
        shs_total_other_tax(frm)
        cur_frm.refresh_field("shs_otros_impuestos");
    } else {
        // console.log('Si hay items con impuestos especiales');
    }
}


/**
 * Recalculo los montos de impuestos especiales, cuando se eliminan n filas
 *
 * @param {*} frm
 * @param {*} cdn
 * @param {*} tax_account_n - Nombre cuenta impuestos especial
 * @param {*} otro_impuesto - Monto impuesto que se esta eliminando
 */
function totalizar_valores(frm, cdn, tax_account_n, otro_impuesto) {
    // recorre items
    frm.doc.items.forEach((item_row, i1) => {
        if (item_row.facelec_tax_rate_per_uom_account === tax_account_n) {
            var total = (facelec_add_taxes(frm, tax_account_n) - otro_impuesto);
            if (frm.doc.shs_otros_impuestos.length != 0) {
                frm.doc.shs_otros_impuestos.forEach((tax_row, i2) => {
                    if (tax_row.account_head === tax_account_n) {
                        cur_frm.doc.shs_otros_impuestos[i2].total = total;
                        cur_frm.refresh_field("shs_otros_impuestos");
                        shs_total_other_tax(frm);
                        cur_frm.refresh_field("shs_otros_impuestos");
                        // console.log('Total tax', tax_row.total);
                        if (!tax_row.total) {
                            // console.log('SE ELIMINARA LA FILA ---------------->');
                            // Elimina la fila con valor 0
                            cur_frm.doc.shs_otros_impuestos.splice(cur_frm.doc.shs_otros_impuestos[i2], 1);
                            cur_frm.refresh_field("shs_otros_impuestos");
                        }
                    }
                });
            }
        }
    });
}


function clean_other_tax(frm) {
    // cur_frm.refresh_field("shs_otros_impuestos");
    // Recorre las tablas hijas descritar en los for, para limpiar cuentas no usadas
    var to_iter = frm.doc.shs_otros_impuestos || [];
    to_iter.forEach((tax_row, index) => {
        let status = [];
        frm.doc.items.forEach((item_row, index_i) => {
            if (tax_row.account_head == item_row.facelec_tax_rate_per_uom_account) {
                status.push(true);
            }
        });

        // delete here
        if (!status.length) {
            cur_frm.get_field("shs_otros_impuestos").grid.grid_rows[index].remove();
        }
    });
}
/* --------------------------------------------------------------------------------------------------------------- */


/**
 * Buscador de cuentas en tabla hija de otros impuestos
 *
 * @param {*} frm
 * @param {*} cuenta_b
 * @return {*}
 */
function buscar_account(frm, cuenta_b) {
    var estado = false;

    $.each(frm.doc.shs_otros_impuestos || [], function (i, d) {
        if (d.account_head === cuenta_b) {
            // console.log('Si Existe en el indice ' + i)
            estado = true;
        }
    });

    return estado;
}


/**
 * Renderiza tabla HTML con detalles de impuestos e impuestos especiales
 *
 * @param {*} frm
 */
function generar_tabla_html(frm) {
    if (frm.doc.items.length > 0) {
        const mi_array = frm.doc.items;
        const mi_array_dos = Array.from(mi_array);
        // console.log(mi_array_dos);
        frappe.call({
            method: "factura_electronica.api.generar_tabla_html",
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


/* Factura de Ventas-------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Sales Invoice", {
    onload_post_render: function (frm, cdt, cdn) {

        frm.fields_dict.items.grid.wrapper.on('focusout blur',
            'input[data-fieldname="item_code"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Clicked on the field Item Code");
                each_item(frm, cdt, cdn);
                facelec_tax_calc_new(frm, cdt, cdn);
                validate_items_acc(frm, cdt, cdn);
            });

        frm.fields_dict.items.grid.wrapper.on('click blur focusout',
            'input[data-fieldname="uom"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Blur or focusout from the UOM field");
                each_item(frm, cdt, cdn);
                facelec_tax_calc_new(frm, cdt, cdn);
            });

        // This part might seem counterintuitive, but it is the "next" field in tab order after item code, which helps for a "creative" strategy to update everything after pressing TAB out of the item code field.  FIXME
        frm.fields_dict.items.grid.wrapper.on('blur',
            'input[data-fieldname="item_name"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Focusing with keyboard cursor through TAB on the Item Name Field");
                each_item(frm, cdt, cdn);
                facelec_otros_impuestos_fila(frm, cdt, cdn);
            });

        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="qty"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Blurring or focusing out from the Quantity Field");
                each_item(frm, cdt, cdn);
                facelec_tax_calc_new(frm, cdt, cdn);
            });

        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="shs_amount_for_back_calc"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Blurring or focusing out from the Quantity Field");
                each_item(frm, cdt, cdn);
                facelec_tax_calc_new(frm, cdt, cdn);
            });

        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="facelec_other_tax_amount"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Blurring or focusing out from the Quantity Field");
                each_item(frm, cdt, cdn);
                facelec_tax_calc_new(frm, cdt, cdn);
            });

        // This specific one is only for keyup events, to recalculate all. Only on blur will it refresh everything!
        // Do not refresh with each_item in Mouse leave OR keyup! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="conversion_factor"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Key up, mouse leave or focus out from the Conversion Factor Field");
                // Trying to calc first, then refresh, or no refresh at all...
                facelec_tax_calc_new(frm, cdt, cdn);
                each_item(frm, cdt, cdn);
                cur_frm.refresh_field("conversion_factor");
            });

        // !NOTE: Generar una pequena sensacion de retardo en calculos, esto porque se ejecuta varias veces
        // frm.fields_dict.items.grid.wrapper.on('blur', '[data-doctype="Sales Invoice Item"]',
        //     function (e) {
        //         // facelec_tax_calc_new(frm, cdt, cdn);
        //         console.log('Ejecutando')
        //         each_item(frm, cdt, cdn);
        //         validate_items_acc(frm, cdt, cdn);
        //     });

        // en-US: Enabling event listeners in the main doctype
        // es-GT: Habilitando escuchadores de eventos en el tipo de documento principal
        // When ANY key is released after being pressed
        // cur_frm.fields_dict.customer.$input.on("blur", function (e) {
        //     //console.log("Se acaba de soltar una tecla del campo customer");
        //     facelec_tax_calc_new(frm, cdt, cdn);
        //     each_item(frm, cdt, cdn);
        //     refresh_field('qty');
        // });

        // When mouse leaves the field NO APLICA
        // cur_frm.fields_dict.customer.$input.on("blur focusout", function (e) {
        //     //console.log("Salió del campo customercon mouseleave, blur, focusout");
        //     facelec_tax_calc_new(frm, cdt, cdn);
        // });

        // Focusout from the field
        if (cur_frm.fields_dict.taxes_and_charges.$input) {
            cur_frm.fields_dict.taxes_and_charges.$input.on("blur focusout", function (e) {
                //console.log("Campo taxes and charges perdió el enfoque via focusout");
                facelec_tax_calc_new(frm, cdt, cdn);
                each_item(frm, cdt, cdn);
                facelec_otros_impuestos_fila(frm, cdt, cdn);
            });
        }
    },
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        // es-GT: Obtiene el numero de Identificacion tributaria ingresado en la hoja del cliente.
        // en-US: Fetches the Taxpayer Identification Number entered in the Customer doctype.
        cur_frm.add_fetch("customer", "nit_face_customer", "nit_face_customer");

        clean_fields(frm);

        if (frm.doc.docstatus != 0) {
            // INICIO BOTONES GENERADORES DOCS ELECTRONICOS
            frappe.call({
                method: 'factura_electronica.fel_api.is_valid_to_fel',
                args: {
                    doctype: frm.doc.doctype,
                    docname: frm.doc.name,
                },
                callback: function (r) {
                    // console.log(r.message);

                    // Anulador docs electronicos para el DT Sales Invoice
                    if (r.message[1] === 'anulador' && r.message[2]) {
                        frappe.call('factura_electronica.api.btn_activator', {
                            electronic_doc: 'anulador_de_facturas_ventas_fel'
                        }).then(r => {
                            // console.log(r.message)
                            if (r.message) {
                                // Si la anulacion electronica ya fue realizada, se mostrara boton para ver pdf doc anulado
                                frappe.call('factura_electronica.api.invoice_exists', {
                                    uuid: frm.doc.numero_autorizacion_fel
                                }).then(r => {
                                    // console.log(r.message)
                                    if (r.message) {
                                        cur_frm.clear_custom_buttons();
                                        pdf_button_fel(frm.doc.numero_autorizacion_fel, frm)
                                    } else {
                                        // SI no aplica lo anterior se muestra btn para anular doc
                                        btn_canceller(frm);
                                        pdf_button_fel(frm.doc.numero_autorizacion_fel, frm)
                                    }
                                })
                            }
                        });
                    }

                    // Generación Facturas Electrónicas FEL - Normal Type
                    if (r.message[0] === 'FACT' && r.message[2]) {
                        generar_boton_factura(__('Factura Electrónica FEL'), frm)
                        if (frm.doc.numero_autorizacion_fel) {
                            cur_frm.clear_custom_buttons();
                            pdf_button_fel(frm.doc.numero_autorizacion_fel, frm)
                        }
                    }

                    // Generación Facturas Electrónicas FEL - Export
                    if (r.message[0] === 'FACT' && r.message[1] == 'export') {
                        btn_export_invoice(frm);
                        if (frm.doc.numero_autorizacion_fel) {
                            cur_frm.clear_custom_buttons();
                            pdf_button_fel(frm.doc.numero_autorizacion_fel, frm)
                        }
                    }

                    // Generación Nota Credito Electronica
                    if (r.message[0] === 'NCRE' && r.message[1] === 'valido' && r.message[2]) {
                        btn_credit_note(frm);
                        if (frm.doc.numero_autorizacion_fel) {
                            cur_frm.clear_custom_buttons();
                            pdf_credit_note(frm);
                        }
                    }
                },
            });
            // FIN BOTONES GENERADORES DOCS ELECTRONICOS

            // INICIO GENERACION POLIZA CON RETENCIONES
            // TODO:AGREGAR VALIDACION EXISTENCIA EN JOURNA ENTRY
            if (frm.doc.docstatus === 1 && frm.doc.status !== 'Paid') {
                btn_journal_entry_retention(frm)
            }
            // FIN GENERACION POLIZA CON RETENCIONES
        }
    },
    validate: function (frm, cdt, cdn) {
        generar_tabla_html(frm);
        facelec_tax_calc_new(frm, cdt, cdn);
        each_item(frm, cdt, cdn);
        facelec_otros_impuestos_fila(frm, cdt, cdn);
        // Trigger antes de guardar
        clean_other_tax(frm);
    },
    nit_face_customer: function (frm, cdt, cdn) {
        // Para evitar retrasos la validacion se realiza desde customer dt
        // valNit(frm.doc.nit_face_customer, frm.doc.customer, frm);
    },
    additional_discount_percentage: function (frm, cdt, cdn) {
        // Pensando en colocar un trigger aqui para cuando se actualice el campo de descuento adicional
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        var tax_before_calc = frm.doc.facelec_total_iva;
        //console.log("El descuento total es:" + frm.doc.discount_amount);
        // es-GT: Este muestra el IVA que se calculo por medio de nuestra aplicación.
        //console.log("El IVA calculado anteriormente:" + frm.doc.facelec_total_iva);
        var discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0]
            .rate / 100)));

        if (discount_amount_net_value == NaN || discount_amount_net_value == undefined) {
            //console.log("No hay descuento definido, calculando sin descuento.");
        } else {
            //console.log("El descuento parece ser un numero definido, calculando con descuento.");
            var discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0]
                .rate / 100));
            //console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_total_iva = (frm.doc.facelec_total_iva - discount_amount_tax_value);
            //console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
        }
    },
    before_save: function (frm, cdt, cdn) {
        facelec_tax_calc_new(frm, cdt, cdn);
        each_item(frm, cdt, cdn);
        facelec_otros_impuestos_fila(frm, cdt, cdn);
        // Trigger antes de guardar
        clean_other_tax(frm);
    },
    on_submit: function (frm, cdt, cdn) {
        // Ocurre cuando se presione el boton validar. para agregar al GL los impuestos especiales

        // Creacion objeto vacio para guardar nombre y valor de las cuentas que se encuentren
        let cuentas_registradas = {};

        // Recorre la tabla hija en busca de cuentas
        frm.doc.shs_otros_impuestos.forEach((tax_row, index) => {
            if (tax_row.account_head) {
                // Agrega un nuevo valor al objeto (JSON-DICCIONARIO) con el
                // nombre, valor de la cuenta
                cuentas_registradas[tax_row.account_head] = tax_row.total;
            };
        });

        // Si existe por lo menos una cuenta, se ejecuta frappe.call
        if (Object.keys(cuentas_registradas).length > 0) {
            // llama al metodo python, el cual recibe de parametros el nombre de la factura y el objeto
            // con las ('cuentas encontradas
            //console.log('---------------------- se encontro por lo menos una cuenta--------------------');
            frappe.call({
                method: "factura_electronica.utils.special_tax.add_gl_entry_other_special_tax",
                args: {
                    invoice_name: frm.doc.name,
                    accounts: cuentas_registradas,
                    invoice_type: "Sales Invoice"
                    /* OJO, El valor de este argumento debe ser "Sales Invoice" en sales_invoice.js
                    En el caso de purchase_invoice.js el valor del argumento debe de ser: invoice_type: "Purchase Invoice"
                    */
                },
                // El callback se ejecuta tras finalizar la ejecucion del script python del lado
                // del servidor
                callback: function () {
                    // Busca la modalidad configurada, ya sea Manual o Automatica
                    // Esto para mostrar u ocultar los botones para la geneneracion de factura
                    // electronica
                    frm.reload_doc();
                }
            });
        }
    },
    naming_series: function (frm, cdt, cdn) {
        // Aplica solo para FS
        if (frm.doc.naming_series) {
            frappe.call({
                method: "factura_electronica.api.obtener_numero_resolucion",
                args: {
                    nombre_serie: frm.doc.naming_series
                },
                // El callback se ejecuta tras finalizar la ejecucion del script python del lado
                // del servidor
                callback: function (numero_resolucion) {
                    if (numero_resolucion.message === undefined) {
                        // cur_frm.set_value('shs_numero_resolucion', '');
                    } else {
                        cur_frm.set_value('shs_numero_resolucion', numero_resolucion.message);
                    }
                }
            });
        }
    },
    es_nota_de_debito: function (frm) {
        // !GFACE: YA NO APLICA
        // buscar en la rama FS si es necesario
        // if (frm.doc.es_nota_de_debito) {
        //     // console.log('Es nota de debito');
        //     cur_frm.set_df_property("naming_series", "read_only", 1);

        //     frappe.call({
        //         method: 'factura_electronica.api.obtener_serie_doc',
        //         args: {
        //             opt: 'debit'
        //         },
        //         callback: function (r) {
        //             // console.log(r.message);

        //             if (r.message) {
        //                 // cur_frm.set_value('naming_series', '');
        //                 cur_frm.set_value('naming_series', r.message);
        //             }
        //         }
        //     });
        // } else {
        //     cur_frm.set_df_property("naming_series", "read_only", 0);
        // }
    },
    is_return: function (frm) {
        // !GFACE: YA NO APLICA
        // Asignacion serie configurada para notas de credito
        // if (frm.doc.is_return) {
        //     // console.log('Es retorno');
        //     cur_frm.set_df_property("naming_series", "read_only", 1);

        //     frappe.call({
        //         method: 'factura_electronica.api.obtener_serie_doc',
        //         args: {
        //             opt: 'credit'
        //         },
        //         callback: function (r) {
        //             // console.log(r.message);
        //             if (r.message) {
        //                 cur_frm.set_value('naming_series', '');
        //                 cur_frm.set_value('naming_series', r.message);
        //             }

        //         }
        //     });
        // } else {
        //     cur_frm.set_df_property("naming_series", "read_only", 0);
        //     // cur_frm.set_value('naming_series', '');
        // }
    }
});

frappe.ui.form.on("Sales Invoice Item", {
    before_items_remove: function (frm, cdt, cdn) {
        // Se ejecuta antes de eliminar la fila
        // Recalcula el total IVA y otros impuestos (IDP)
        clean_other_tax(frm);

        let row = frappe.get_doc(cdt, cdn);
        totalizar_valores(frm, cdn, row.facelec_tax_rate_per_uom_account, row.facelec_other_tax_amount);

        // frm.doc.items.forEach((item_row_1, index_1) => {
        //     if (item_row_1.name == cdn) {
        //         // console.log('La Fila a Eliminar es --------------> ' + item_row_1.item_code);
        //         totalizar_valores(frm, cdn, item_row_1.facelec_tax_rate_per_uom_account, item_row_1.facelec_other_tax_amount);
        //     }
        // });
        // cur_frm.refresh_field("shs_otros_impuestos");
    },
    items_add: function (frm, cdt, cdn) {
        facelec_otros_impuestos_fila(frm, cdt, cdn);
    },
    items_move: function (frm, cdt, cdn) {
        facelec_otros_impuestos_fila(frm, cdt, cdn);
    },
    item_code: function (frm, cdt, cdn) {
        each_item(frm, cdt, cdn);
        validate_items_acc(frm, cdt, cdn);

        let row = frappe.get_doc(cdt, cdn);

        clean_other_tax(frm);
    },
    qty: function (frm, cdt, cdn) {
        //facelec_tax_calculation(frm, cdt, cdn);
        facelec_tax_calc_new(frm, cdt, cdn);
        //console.log("cdt contains: " + cdt);
        //console.log("cdn contains: " + cdn);
    },
    facelec_is_discount: function (frm, cdt, cdn) {
        facelec_tax_calc_new(frm, cdt, cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        //console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        //console.log("El disparador de factor de conversión se corrió.");
        facelec_tax_calc_new(frm, cdt, cdn);
    },
    facelec_tax_rate_per_uom_account: function (frm, cdt, cdn) {
        //facelec_otros_impuestos_fila(frm, cdt,cdn);
        // esto debe correr aqui?
    },
    rate: function (frm, cdt, cdn) {
        facelec_tax_calc_new(frm, cdt, cdn);
    },
    shs_amount_for_back_calc: function (frm, cdt, cdn) {
        // Permite aplicar goalSeek
        frm.doc.items.forEach((row, index) => {
            var a = row.rate;
            var b = row.qty;
            var c = row.amount;
            let calcu = goalSeek({
                Func: funct_eval,
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
            frm.doc.items[index].amount = (calcu * frm.doc.items[index].rate);
            frm.refresh_field("items");
        });

        facelec_tax_calc_new(frm, cdt, cdn);
    }
});


/**
 * Funcion para evaluar goalseek
 *
 * @param {*} a
 * @param {*} b
 * @return {*} monto
 */
function funct_eval(a, b) {
    return a * b;
}


/**
 * Limpia los campos con data no necesaria, al momento de duplicar
 *
 * @param {*} frm
 */
function clean_fields(frm) {
    // Funcionalidad evita copiar CAE cuando se duplica una factura
    // LIMPIA/CLEAN, permite limpiar los campos cuando se duplica una factura
    if (frm.doc.status === 'Draft' || frm.doc.docstatus == 0) {
        // console.log('No Guardada');
        frm.set_value("cae_factura_electronica", '');
        frm.set_value("serie_original_del_documento", '');
        frm.set_value("numero_autorizacion_fel", '');
        frm.set_value("facelec_s_vat_declaration", '');
        // cur_frm.set_value("ag_invoice_id", '');
        frm.set_value("facelec_tax_retention_guatemala", '');
        frm.set_value("facelec_export_doc", '');
        frm.set_value("facelec_export_record", '');
        frm.set_value("facelec_record_type", '');
        frm.set_value("facelec_consumable_record_type", '');
        frm.set_value("facelec_record_number", '');
        frm.set_value("facelec_record_value", '');
        frm.refresh_fields();

        // console.log('Hay que limpiar')
    }
}


/**
 * Render boton para anular docs en SI
 *
 * @param {*} frm
 */
function btn_canceller(frm) {
    cur_frm.clear_custom_buttons();
    frm.add_custom_button(__("CANCEL DOCUMENT FEL"), function () {
        // Permite hacer confirmaciones
        frappe.confirm(__('Are you sure to cancel the current electronic document?'),
            () => {
                let d = new frappe.ui.Dialog({
                    title: __('Cancel electronic document'),
                    fields: [{
                        label: __('Reason for cancellation?'),
                        fieldname: 'reason_cancelation',
                        fieldtype: 'Data',
                        reqd: 1
                    }],
                    primary_action_label: 'Submit',
                    primary_action(values) {
                        frappe.call({
                            method: 'factura_electronica.fel_api.invoice_canceller',
                            args: {
                                invoice_name: frm.doc.name,
                                reason_cancelation: values.reason_cancelation || 'Anulación',
                                document: 'Sales Invoice',
                            },
                            callback: function (data) {
                                // console.log(data.message);
                                frm.reload_doc();
                            },
                        });

                        d.hide();
                    }
                });

                d.show();
            }, () => {
                // action to perform if No is selected
                // console.log('Selecciono NO')
            })
    }).addClass("btn-danger");
}


/**
 * Render boton para FEL normal
 *
 * @param {*} tipo_factura
 * @param {*} frm
 */
function generar_boton_factura(tipo_factura, frm) {
    frm.add_custom_button(__(tipo_factura), function () {
        // frm.reload(); permite hacer un refresh de todo el documento
        frm.reload_doc();
        let serie_de_factura = frm.doc.name;
        // Guarda la url actual
        let mi_url = window.location.href;
        frappe.call({
            method: "factura_electronica.fel_api.api_interface",
            args: {
                invoice_code: frm.doc.name,
                naming_series: frm.doc.naming_series
            },
            // El callback recibe como parametro el dato retornado por el script python del lado del servidor
            callback: function (data) {
                // console.log(data.message);
                if (data.message[0] === true) {
                    // Crea una nueva url con el nombre del documento actualizado
                    let url_nueva = mi_url.replace(serie_de_factura, data.message[1]);
                    // Asigna la nueva url a la ventana actual
                    window.location.assign(url_nueva);
                    // Recarga la pagina
                    frm.reload_doc();
                }
            }
        });
    }).addClass("btn-primary"); //NOTA: Se puede crear una clase para el boton CSS
}


/**
 * Generador de boton para factura de exportacion, cuando se pulsa
 * hace una peticion a la funcion generate_export_invoice y esta a la
 * vez genera la peticion a INFILE con los datos de la factura
 *
 * @param {*} frm
 */
function btn_export_invoice(frm) {
    cur_frm.clear_custom_buttons(); // Limpia otros customs buttons para generar uno nuevo
    frm.add_custom_button(__("FACTURA ELECTRONICA EXPORTACION FEL"),
        function () {
            frappe.call({
                method: 'factura_electronica.fel_api.api_interface_export',
                args: {
                    invoice_code: frm.doc.name,
                    naming_series: frm.doc.naming_series,
                },
                callback: function (data) {
                    // console.log(data.message);
                    let serie_de_factura = frm.doc.name;
                    // Guarda la url actual
                    let mi_url = window.location.href;

                    if (data.message[0] === true) {
                        // Crea una nueva url con el nombre del documento actualizado
                        let url_nueva = mi_url.replace(serie_de_factura, data.message[1]);
                        // Asigna la nueva url a la ventana actual
                        window.location.assign(url_nueva);
                        // Recarga la pagina
                        frm.reload_doc();
                    };
                },
            });
        }).addClass("btn-primary");
};


/**
 * Render para boton notas de credito electronicas
 *
 * @param {*} frm
 */
function btn_credit_note(frm) {
    cur_frm.clear_custom_buttons();
    frm.add_custom_button(__("CREDIT NOTE FEL"), function () {
        // Permite hacer confirmaciones
        frappe.confirm(__('Are you sure you want to proceed to generate a credit note?'),
            () => {
                let d = new frappe.ui.Dialog({
                    title: __('Generate Credit Note'),
                    fields: [{
                        label: __('Reason Adjusment?'),
                        fieldname: 'reason_adjust',
                        fieldtype: 'Data',
                        reqd: 1
                    }],
                    primary_action_label: __('Submit'),
                    primary_action(values) {
                        let serie_de_factura = frm.doc.name;
                        // Guarda la url actual
                        let mi_url = window.location.href;

                        frappe.call({
                            method: 'factura_electronica.fel_api.generate_credit_note',
                            args: {
                                invoice_code: frm.doc.name,
                                naming_series: frm.doc.naming_series,
                                reference_inv: frm.doc.return_against,
                                reason: values.reason_adjust
                            },
                            callback: function (data) {
                                console.log(data.message);
                                if (data.message[0] === true) {
                                    // Crea una nueva url con el nombre del documento actualizado
                                    let url_nueva = mi_url.replace(
                                        serie_de_factura, data
                                            .message[1]);
                                    // Asigna la nueva url a la ventana actual
                                    window.location.assign(url_nueva);
                                    // Recarga la pagina
                                    frm.reload_doc();
                                }
                            },
                        });

                        d.hide();
                    }
                });

                d.show();
            }, () => {
                // action to perform if No is selected
                // console.log('Selecciono NO')
            })
    }).addClass("btn-warning");
}


/**
 * Generador de boton para factura exenta de impuestos
 *
 * @param {*} frm
 */
function btn_exempt_invoice(frm) {
    cur_frm.clear_custom_buttons(); // Limpia otros customs buttons para generar uno nuevo

    frm.add_custom_button(__("FACTURA ELECTRONICA EXENTA"),
        function () {

            show_alert('Trabajo en progreso, opcion no disponible', 5);

            // frappe.call({
            //     method: 'factura_electronica.fel_api.generate_exempt_electronic_invoice',
            //     args: {
            //         invoice_code: frm.doc.name,
            //         naming_series: frm.doc.naming_series,
            //     },
            //     callback: function (data) {
            //         console.log(data.message);

            //         if (data.message[0] === true) {
            //             // Crea una nueva url con el nombre del documento actualizado
            //             let url_nueva = mi_url.replace(serie_de_factura, data.message[1]);
            //             // Asigna la nueva url a la ventana actual
            //             window.location.assign(url_nueva);
            //             // Recarga la pagina
            //             frm.reload_doc();
            //         };

            //     },
            // });

        }).addClass("btn-primary");
};


/**
 * Render para boton retenciones de impuestos IVA/ISR
 *
 * @param {*} frm
 */
function btn_journal_entry_retention(frm) {
    cur_frm.page.add_action_item(__("AUTOMATED RETENTION"), function () {

        let d = new frappe.ui.Dialog({
            title: __('New Journal Entry with Withholding Tax'),
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
                label: 'Target account',
                fieldname: 'debit_in_acc_currency',
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
                label: 'Applies for VAT withholding',
                fieldname: 'is_iva_withholding',
                fieldtype: 'Check'
            },
            {
                label: 'Applies for ISR withholding',
                fieldname: 'is_isr_withholding',
                fieldtype: 'Check'
            },
            {
                label: 'NOTE',
                fieldname: 'note',
                fieldtype: 'Data',
                read_only: 1,
                default: 'Los cálculos se realizaran correctamente si se encuentran configurados en company, y si el IVA va incluido en la factura'
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
                    method: 'factura_electronica.api_erp.journal_entry_isr',
                    args: {
                        invoice_name: frm.doc.name,
                        debit_in_acc_currency: values.debit_in_acc_currency,
                        cost_center: values.cost_center,
                        is_isr_ret: parseInt(values.is_isr_withholding),
                        is_iva_ret: parseInt(values.is_iva_withholding),
                        is_multicurrency: parseInt(values.is_multicurrency),
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
 * Render para boton que visualiza PDF doc electronico
 *
 * @param {*} cae_documento
 * @param {*} frm
 */
function pdf_button_fel(cae_documento, frm) {
    // Esta funcion se encarga de mostrar el boton para obtener el pdf de la factura electronica generada
    // aplica para fels, y anuladas
    frm.add_custom_button(__("VER PDF DOCUMENTO ELECTRÓNICO"),
        function () {
            window.open("https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" +
                cae_documento);
        }).addClass("btn-primary");
}


/**
 * Render boton para visualizar pdf nota credito electronica
 *
 * @param {*} frm
 */
function pdf_credit_note(frm) {
    cur_frm.clear_custom_buttons();
    frm.add_custom_button(__("VER PDF NOTA CREDITO ELECTRONICA"),
        function () {
            window.open("https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" +
                frm.doc.numero_autorizacion_fel);
        }).addClass("btn-primary");
}
