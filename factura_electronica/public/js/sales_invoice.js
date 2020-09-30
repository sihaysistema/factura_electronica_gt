/**
 * Copyright (c) 2017, 2018, 2019 SHS and contributors
 * For license information, please see license.txt
 */

import {
    valNit
} from './facelec.js';
import {
    goalSeek
} from './goalSeek.js';

/* 1 Funcion calculadora para Sales Invoice ------------------------------------------------------------------------ */
function facelec_tax_calc_new(frm, cdt, cdn) {
    // es-GT: Actualiza los datos en los campos de la tabla hija 'items'
    //console.log("ran facelec_tax_calc_new");
    // es-GT: Revisamos si ya quedo cargado y definido el rate (tasa) de impuesto en el DocType, el cual debe estar en la fila 0 de Sales Taxes & Charges.
    // es-GT: Si no ha sido definido, no se hace nada. Si ya fue definido, se asigna a una variable el valor que encuentre en la fila 0 de la tabla hija taxes.
    var this_company_sales_tax_var;
    if (cur_frm.doc.taxes[0].rate !== "undefined") {
        //console.log("Ahora que ya se especifico un cliente, ya existe impuesto en la hoja, por lo tanto, lo asignamos a una variable!");
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        //console.log("El IVA cargado es: " + this_company_sales_tax_var);
    }
    // es-GT: Ahora se hace con un event listener al primer teclazo del campo de cliente
    // es-GT: Sin embargo queda aqui para asegurar que el valor sea el correcto en todo momento.
    // var this_row_qty = 0;
    // var this_row_rate = 0;
    var this_row_amount = 0;
    // var this_row_conversion_factor = 0;
    var this_row_stock_qty = 0;
    var this_row_tax_rate = 0;
    var this_row_tax_amount = 0;
    var this_row_taxable_amount = 0;
    // var total_fuel = 0;
    // var total_goods = 0;
    // var total_servi = 0;

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
            this_row_taxable_amount = (item_row.amount - (item_row.stock_qty * item_row
                .facelec_tax_rate_per_uom));
            // We change the fields for other tax amount as per the complete row taxable amount.
            frm.doc.items[index].facelec_other_tax_amount = ((item_row.facelec_tax_rate_per_uom * (
                item_row.qty * item_row.conversion_factor)));
            frm.doc.items[index].facelec_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - (
                item_row.stock_qty * item_row.facelec_tax_rate_per_uom));
            // We refresh the items to recalculate everything to ensure proper math
            frm.refresh_field("items");
            //console.log(item_row.qty + " " + item_row.uom + "es/son igual/es a " + item_row.stock_qty + " " + item_row.stock_uom);
            //console.log("conversion_factor is: " + item_row.conversion_factor);
            // Probando refrescar el campo de converison factor, talvez asi queda todo nitido??  TODO
            frm.refresh_field("conversion_factor");
            //console.log("Other tax amount = Q" + (item_row.stock_qty * item_row.facelec_tax_rate_per_uom));
            //console.log("Amount - Other Tax Amount = Amount minus excise tax: " + item_row.amount + " - " + (item_row.stock_qty * item_row.facelec_tax_rate_per_uom) + " = " + item_row.facelec_amount_minus_excise_tax);
            //console.log("Q" + item_row.amount + " - (" + item_row.stock_qty + " * " + item_row.facelec_tax_rate_per_uom + ") ")

            // Verificacion Individual para verificar si es Fuel, Good o Service
            if (item_row.factelecis_fuel) {
                frm.doc.items[index].facelec_gt_tax_net_fuel_amt = (item_row
                    .facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row
                    .facelec_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                /*
                var total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    // total_qty += flt(d.qty);
                    if (d.factelecis_fuel) {
                        total_fuel += flt(d.facelec_gt_tax_net_fuel_amt);
                    };
                });
                //console.log("El total neto de fuel es:" + total_fuel); // WORKS OK!
                // cur_frm.doc.facelec_gt_tax_fuel = total_fuel;
                cur_frm.set_value('facelec_gt_tax_fuel', total_fuel);
                frm.refresh_field("factelecis_fuel");
                */
            };
            if (item_row.facelec_is_good) {
                frm.doc.items[index].facelec_gt_tax_net_goods_amt = (item_row
                    .facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row
                    .facelec_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                /*
                var total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    // total_qty += flt(d.qty);
                    if (d.facelec_is_good) {
                        total_goods += flt(d.facelec_gt_tax_net_goods_amt);
                    };
                });
                console.log("El total neto de bienes es:" + total_goods); // WORKS OK!
                // cur_frm.doc.facelec_gt_tax_goods = total_goods;
                cur_frm.set_value('facelec_gt_tax_goods', total_goods);
                */
            };
            if (item_row.facelec_is_service) {
                //console.log("The item you added is a SERVICE!" + item_row.facelec_is_service);// WORKS OK!
                //console.log("El valor en servicios para el libro de compras es: " + net_services_tally);// WORKS OK!
                // Estimamos el valor del IVA para esta linea
                //frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_amount_minus_excise_tax * (this_company_sales_tax_var / 100)).toFixed(2);
                //frm.doc.items[index].facelec_gt_tax_net_services_amt = (item_row.facelec_amount_minus_excise_tax - item_row.facelec_sales_tax_for_this_row).toFixed(2);
                frm.doc.items[index].facelec_gt_tax_net_services_amt = (item_row
                    .facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row
                    .facelec_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
                /*
                var total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_is_service) {
                        total_servi += flt(d.facelec_gt_tax_net_services_amt);
                        console.log("se detecto cheque de servicio"); // WORKS!
                    };
                });
                console.log("El total neto de servicios es:" + total_servi); // WORKS OK!
                // cur_frm.doc.facelec_gt_tax_services = total_servi;
                cur_frm.set_value('facelec_gt_tax_services', total_servi);
                */
            };
            // Para el calculo total de IVA, basado en la sumatoria de facelec_sales_tax_for_this_row de cada item
            /*
            var full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.facelec_sales_tax_for_this_row);
            });
            // Seccion Guatemala Tax: Se asigna al campo de IVA de la seccion
            // frm.doc.facelec_total_iva = full_tax_iva;
            cur_frm.set_value('facelec_total_iva', full_tax_iva);
            */

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

// Sin necesidad de guardar el formulario.  Esto costo una buenas horas de trabajo!!
// Se lanza con un evento disparado por un escuchador
// FIXME: Lo unico es que solo se puede poner item code con ENTER o CLICK. Tab no funciona.  Quizas aqui si sirve usar un listener de keypress para guardarlo en una variable que lo hace permanecer mientras se escribe el item.
// Esto soluciona el issue #18
function each_item(frm, cdt, cdn) {
    // es-GT: Esta permite ya que se calcule correctamente desde el INICIO!
    // es-GT: Sin necesidad de Guardar antes!
    frm.doc.items.forEach((item) => {
        // for each button press each line is being processed.
        //console.log("Item, from the each_item function contains: " + item);
        //Esato dice: object, object
        //Importante
        var tax_before_calc = frm.doc.facelec_total_iva;
        //console.log("El descuento total es:" + frm.doc.discount_amount);
        //console.log("El IVA calculado anteriormente:" + frm.doc.facelec_total_iva);
        var discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate /
            100)));
        if (typeof (cur_frm.doc.taxes[0].rate) == "NaN") {
            //console.log("No hay descuento definido, calculando sin descuento.");
        } else {
            //console.log("El descuento parece ser un numero definido, calculando con descuento.");
            //console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            var discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate /
                100));
            //console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_total_iva = (frm.doc.facelec_total_iva - discount_amount_tax_value);
            //console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
        }
        facelec_tax_calc_new(frm, "Sales Invoice Item", item.name);
        facelec_otros_impuestos_fila(frm, "Sales Invoice Item", item.name);
    });
}

/* 2 --------------------------------------------------------------------------------------------------------------- */

/* 3 Funciones para otros impuestos IDP ... ------------------------------------------------------------------------ */
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
 * Parametros:
 * #1 frm = formulario que se esta trabajando
 * #2 cdt = Doctype
 * #3 cdn = Docname
 *
 * Funcionamiento:
 * Recorre la tabla items, por cada item encontrado, si tiene una cuenta asignada,
 * recorrera la tabla hija shs_otros_impuestos en busca de cuentas con el mismo nombre
 * de cuenta anteriormente encontrado, para totalizar el valor del impuestos, para todos
 * los items que tienen la misma cuenta configurada.
 */
function sumar_otros_impuestos_shs(frm, cdt, cdn) {
    frm.doc.items.forEach((item_row_1, index_1) => {

        if (item_row_1.name === cdn) {
            if (item_row_1.facelec_tax_rate_per_uom_account) {
                if (frm.doc.shs_otros_impuestos !== undefined) {
                    frm.doc.shs_otros_impuestos.forEach((tax_row_2, index_2) => {
                        if (tax_row_2.account_head === item_row_1
                            .facelec_tax_rate_per_uom_account) {
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
 * Parametros:
 * #1 frm = formulario que se esta trabajando
 *
 * Funcionamiento:
 * Recorre la tabla hija shs_otros_impuestos, realiza sumatoria de todos las filas
 * que tenga una cuenta, el valor totalizado se asigna al campo shs_total_otros_imp_incl
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
function facelec_otros_impuestos_fila(frm, cdt, cdn) {
    var this_row_tax_amount = 0; // Valor IDP
    var this_row_taxable_amount = 0; // Valor todavía con IVA
    var shs_otro_impuesto = 0;
    var total_suma_impuesto = 0;

    frm.doc.items.forEach((item_row_i, indice) => {
        if (item_row_i.name === cdn) {
            // Calculos Alain
            this_row_tax_amount = (item_row_i.stock_qty * item_row_i.facelec_tax_rate_per_uom);
            //this_row_taxable_amount = (item_row_i.amount - (item_row_i.stock_qty * item_row_i.facelec_tax_rate_per_uom));
            shs_otro_impuesto = item_row_i.facelec_other_tax_amount;

            // Guarda el nombre de la cuenta del item seleccionado
            var cuenta = item_row_i.facelec_tax_rate_per_uom_account;
            //console.log('Cuenta de item encontrada es : ' + cuenta);

            // Refresh data de la tabla hija items y conversion_factor
            frm.refresh_field('items');
            frm.refresh_field('conversion_factor');

            if (cuenta) { // Si encuentra una cuenta con nombre procede
                var otro_impuesto = this_row_tax_amount;
                //valor_con_iva = this_row_taxable_amount;

                if (!(buscar_account(frm, cuenta))) { // Si no encuentra una cuenta, procede.
                    // var fila_nueva = cur_frm.add_child("shs_otros_impuestos");
                    // var fila_nueva = frappe.model.add_child(cur_frm.doc, "Otros Impuestos Factura Electronica", "shs_otros_impuestos");
                    // Crea una nueva fila vacia en la tabla hija shs_otros_impuestos
                    frappe.model.add_child(cur_frm.doc, "Otros Impuestos Factura Electronica",
                        "shs_otros_impuestos");

                    // Refresh datos de la tabla hija items
                    cur_frm.refresh_field('items');
                    // otro_impuesto = this_row_tax_amount;
                    // valor_con_iva = this_row_taxable_amount;

                    // Recorre la tabla hija 'taxes' en busca de la nueva fila que se agrego anteriormente donde account_head
                    // sea undefined
                    frm.doc.shs_otros_impuestos.forEach((tax_row, index) => {
                        // Si encuentra la fila anteriormente agregada procede
                        if (tax_row.account_head === undefined) {
                            // Asigna valores en la fila recien creada
                            cur_frm.doc.shs_otros_impuestos[index].account_head = cuenta;
                            cur_frm.doc.shs_otros_impuestos[index].total = shs_otro_impuesto;
                            // cur_frm.doc.shs_otros_impuestos[index].doctype_type = 'Sales Invoice';
                            // cur_frm.doc.shs_otros_impuestos[index].doctype_no = cdn;

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

function totalizar_valores(frm, cdn, tax_account_n, otro_impuesto) {
    /**
     * Se encarga de recalcular el total de otros impuestos cuando se elimina un item
     */
    // console.log('Otro Impuesto recibido es : ' + otro_impuesto);
    // recorre items
    frm.doc.items.forEach((item_row, i1) => {
        if (item_row.facelec_tax_rate_per_uom_account === tax_account_n) {
            var total = (facelec_add_taxes(frm, tax_account_n) - otro_impuesto);
            // recorre shs_otros_impuestos
            //console.log('1. El nuevo total calculado es: ' + total);
            //console.log('1. El valor de la fila que se borra es: ' + otro_impuesto);

            if (frm.doc.shs_otros_impuestos !== undefined) {
                frm.doc.shs_otros_impuestos.forEach((tax_row, i2) => {
                    if (tax_row.account_head === tax_account_n) {
                        cur_frm.doc.shs_otros_impuestos[i2].total = total;
                        cur_frm.refresh_field("shs_otros_impuestos");
                        shs_total_other_tax(frm);
                        cur_frm.refresh_field("shs_otros_impuestos");

                        if (!tax_row.total) {
                            // console.log('SE ELIMINARA LA FILA ---------------->');
                            // Elimina la fila con valor 0
                            cur_frm.doc.shs_otros_impuestos.splice(cur_frm.doc
                                .shs_otros_impuestos[i2], 1);
                            cur_frm.refresh_field("shs_otros_impuestos");
                        }
                    }
                });
            }

        }
    });

}
/* 4 --------------------------------------------------------------------------------------------------------------- */
/**
 * Funcionamiento: recibe como parametro frm, y cuenta_b, lo que hace es, buscar en todas las filas de taxes
 * si existe ya una cuenta con el nombre de la cuenta recibida por parametro, en caso ya exista esa cuenta en
 * la tabla no hace nada, pero si encuentra que no hay una cuenta igual a la recibida en el parametro, entonces
 * la funcion encargada agregara una nueva fila con los datos correspondientes, esta funcion retorna true
 * en caso si encuentre una cuenta existente
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

/* 6 Funciones creadoras de botones --------------------------------------------------------------------------------------- */
function pdf_button(cae_documento, frm) {
    // Esta funcion se encarga de mostrar el boton para obtener el pdf de la factura electronica generada
    frm.add_custom_button(__("VER PDF FACTURA ELECTRONICA"),
        function () {
            window.open("https://www.ingface.net/Ingfacereport/dtefactura.jsp?cae=" + cae_documento);
        }).addClass("btn-primary");
}


function pdf_button_fel(cae_documento, frm) {
    // Esta funcion se encarga de mostrar el boton para obtener el pdf de la factura electronica generada
    frm.add_custom_button(__("VER PDF FACTURA ELECTRONICA"),
        function () {
            window.open("https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" +
                cae_documento);
        }).addClass("btn-primary");
}
/*
Crea un boton que permite guardar el PDF de factura electronica generado en el servidor
de forma privada, tras finalizar la ejecucion del script del lado del servidor en el
callback se recarga la pagina para mostrar el archivo adjunto.
*/
function guardar_pdf(frm) {
    frm.add_custom_button(__('GUARDAR PDF'), function () {
        frappe.call({
            method: "factura_electronica.api.guardar_pdf_servidor",
            args: {
                nombre_archivo: frm.doc.name,
                cae_de_factura_electronica: frm.doc.cae_factura_electronica
            },
            callback: function () {
                frm.reload_doc();
            }
        });
    }).addClass("btn-primary"); //NOTA: Se puede crear una clase para el boton CSS
}

// FIXME: MODIFICAR PARA QUE PERMITE ELIMINAR EL PDF
function eliminar_pdf() {
    frm.add_custom_button(__('ELIMINAR PDF'), function () {
        frappe.call({
            method: "factura_electronica.api.guardar_pdf_servidor",
            args: {
                nombre_archivo: frm.doc.name,
                cae_de_factura_electronica: frm.doc.cae_factura_electronica
            },
            callback: function () {
                frm.reload_doc();
            }
        });
    }).addClass("btn-primary");
}

// Funcion antigua para generar factura electronica GFACE
// function generar_boton_factura(tipo_factura, frm) {
//     frm.add_custom_button(__(tipo_factura), function () {
//         // frm.reload(); permite hacer un refresh de todo el documento
//         frm.reload_doc();
//         let serie_de_factura = frm.doc.name;
//         // Guarda la url actual
//         let mi_url = window.location.href;
//         frappe.call({
//             method: "factura_electronica.api.generar_factura_electronica",
//             args: {
//                 serie_factura: frm.doc.name,
//                 nombre_cliente: frm.doc.customer,
//                 pre_se: frm.doc.naming_series
//             },
//             // El callback recibe como parametro el dato retornado por el script python del lado del servidor
//             callback: function (data) {
//                 if (data.message !== undefined) {
//                     // Crea una nueva url con el nombre del documento actualizado
//                     let url_nueva = mi_url.replace(serie_de_factura, data.message);
//                     // Asigna la nueva url a la ventana actual
//                     window.location.assign(url_nueva);
//                     // Recarga la pagina
//                     frm.reload_doc();
//                 }
//             }
//         });
//     }).addClass("btn-primary"); //NOTA: Se puede crear una clase para el boton CSS
// }

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

// Realiza la funcionalidad del boton automaticamente
function generar_factura_sin_btn(frm) {
    // frm.reload(); permite hacer un refresh de todo el documento
    frm.reload_doc();
    let serie_de_factura = frm.doc.name;
    // Guarda la url actual
    let mi_url = window.location.href;
    frappe.call({
        method: "factura_electronica.api.generar_factura_electronica",
        args: {
            serie_factura: frm.doc.name,
            nombre_cliente: frm.doc.customer,
            pre_se: frm.doc.naming_series
        },
        // El callback recibe como parametro el dato retornado por el script python del lado del servidor
        callback: function (data) {
            if (data.message !== undefined) {
                // Crea una nueva url con el nombre del documento actualizado
                let url_nueva = mi_url.replace(serie_de_factura, data.message);
                // Asigna la nueva url a la ventana actual
                window.location.assign(url_nueva);
                frm.reload_doc();
            } else {
                frm.reload_doc();
            }
        }
    });
}

/* 7 Funciones Verificadoras ------------------------------------------------------------------------------------------------- */
// DEFINICION: Se encarga de validar si hay existencia de UUID o CAE en Factura de Venta
// Si no lo hay mostrara el boton de Factura Electronica, Factura Exportacion o Factura Exenta segun el escenario al que
// aplique
function verificacionCAE(modalidad, frm, cdt, cdn) {

    /* ------------------------------ COMPROBACIONES DE CAE ------------------------------ */
    // FACTURAS FACE, CFACE, FACTURA EXPORTACION
    // Este codigo entra en funcionamiento cuando la generacion automatica de la factura no es exitosa.
    // esto permite volver intentarlo hasta obtener el cae de la factura en que se estre trabajando.
    if (frm.doc.status === "Paid" || frm.doc.status === "Unpaid" || frm.doc.status === "Submitted" ||
        frm.doc.status === "Overdue" || frm.doc.status != "Credit Note Issued") {
        // SI en el campo de 'cae_factura_electronica' ya se encuentra el dato correspondiente, ocultara el boton
        // para generar el documento, para luego mostrar el boton para obtener el PDF del documento ya generado.

        // Si hay ya un identificador para facelec, muestra boton para ver pdf en linea
        if (frm.doc.cae_factura_electronica) {
            cur_frm.clear_custom_buttons();
            pdf_button(frm.doc.cae_factura_electronica, frm);

            // Si hay ya un identificador para facelec, muestra boton para ver pdf en linea
        } else if (frm.doc.numero_autorizacion_fel) {
            cur_frm.clear_custom_buttons();
            pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);

            // Si no aplica ninguno de los anteiores, se muestra los respectivos botones para generar
        } else {
            // Si la modalidad recibida es manual se genera un boton para hacer la factura electronica manualmente
            // NOTA: Se dejo por default solo para hacerlo manualmente, si se quiere automatico
            // hay que desarrollarlo :D
            if (modalidad === 'manual') {
                // NOTA: Por default mostrara la opcion de generar factura electronica normal,
                // pero si no aplica se borrara y mostrara el que si aplica
                generar_boton_factura('Factura Electronica', frm);

                // inicio factura exportacion
                // aplica solo si la factura esta validada y si la opcion international is active
                // NOTA: Debe tener la cuenta de impuestos con Rate 0, El nit de cliente por defualt
                // se usara CF aunque tenga uno asignado
                if (frm.doc.docstatus == 1 && cur_frm.doc.is_it_an_international_invoice == 1) {
                    btn_export_invoice(frm);

                    // NOTA: USAR EN CASO SE BASE EN DIRECCION DE CLIENTE
                    // Si el pais en la direccion de cliente es diferente a Guatemala se mostrara
                    // frappe.call({
                    //     method: 'factura_electronica.api.validate_address',
                    //     args: {
                    //         address_name: frm.doc.customer_address,
                    //     },
                    //     callback: function (r) {
                    //         if (r.message == true) {
                    //             console.log('Si aplica a exportacion')
                    //             btn_export_invoice(frm)
                    //             // frm.reload_doc();
                    //         }
                    //         if (r.message == false) {
                    //             console.log('No aplica a exportacion, pero si a fel normal')
                    //         }
                    //     },
                    // });

                }
                // final factura exportacion

                // INICIO FACTURA EXENTA DE IMPUESTOS
                // Para llevar un mejor registro, cargar una tabla de impuestos con rate
                // Ya que se mostrara solo y solo el rate del iva es 0
                if (cur_frm.doc.is_it_an_international_invoice == 0 && frm.doc.docstatus == 1 && frm.doc.taxes.length > 0) {
                    if (frm.doc.taxes[0].rate == 0) {
                        btn_exempt_invoice(frm);
                    }
                }
                // FIN FACTURA EXENTA DE IMPUESTOS
            }
            // Si la modalidad recibida es automatica se realiza la factura electronica directamente
            // if (modalidad === 'automatico') {
            //     generar_factura_sin_btn(frm);
            // }
        }
    }

    // NO APLICA PARA FEL
    // Codigo para Notas de Credito NCE
    // El codigo se ejecutara segun el estado del documento, puede ser: Retornar
    // if (frm.doc.status === "Return") {
    //     //var nombre = 'Nota Credito';
    //     // SI en el campo de 'cae_nota_de_credito' ya se encuentra el dato correspondiente, ocultara el boton
    //     // para generar el documento, para luego mostrar el boton para obtener el PDF del documento ya generado.
    //     if (frm.doc.cae_factura_electronica) {
    //         cur_frm.clear_custom_buttons();
    //         pdf_button(frm.doc.cae_factura_electronica, frm);
    //         // guardar_pdf(frm);
    //     } else {
    //         // Si la modalidad recibida es manual se genera un boton para hacer la factura electronica manualmente
    //         if (modalidad === 'manual') {
    //             generar_boton_factura('Nota Credito Electronica', frm);
    //         }
    //         // Si la modalidad recibida es automatica se realiza la factura electronica directamente
    //         if (modalidad === 'automatico') {
    //             generar_factura_sin_btn(frm);
    //         }
    //     }
    // }

    // NO APLICA PARA FEL
    // Codigo para notas de debito
    // Codigo para Notas de Credito NDE
    // if (frm.doc.status === "Paid" || frm.doc.status === "Unpaid" || frm.doc.status === "Submitted" || frm.doc
    //     .status === "Overdue") {
    //     //var nombre = 'Nota Debito';
    //     if (frm.doc.es_nota_de_debito) {
    //         cur_frm.clear_custom_buttons('Factura Electronica');
    //         if (frm.doc.cae_factura_electronica) {
    //             cur_frm.clear_custom_buttons();
    //             pdf_button(frm.doc.cae_factura_electronica, frm);
    //             // guardar_pdf(frm);
    //         } else {
    //             // Si la modalidad recibida es manual se genera un boton para hacer la factura electronica manualmente
    //             if (modalidad === 'manual') {
    //                 generar_boton_factura('Nota Debito Electronica', frm);
    //             }
    //             // Si la modalidad recibida es automatica se realiza la factura electronica directamente
    //             if (modalidad === 'automatico') {
    //                 generar_factura_sin_btn(frm);
    //             }
    //         }
    //     }
    // }
    /* -------------------------------------------------------------------------------------- */
}

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
/* 9 Eventos en Doctypes---------------------------------------------------------------------------------------------- */

/* Factura de Ventas-------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Sales Invoice", {
    onload_post_render: function (frm, cdt, cdn) {
        // var section_head = $('.section-head').find("a").filter(function () { return $(this).text() == "TAX FACELEC"; }).parent()
        // section_head.on("click", function () {
        //     console.log('Hizo click en la seccion');
        //     generar_tabla_html(frm);
        // })
        //console.log('Funcionando Onload Post Render Trigger'); //SI FUNCIONA EL TRIGGER
        // Funciona unicamente cuando se carga por primera vez el documento y aplica unicamente para el form y no childtables

        // en-US: Enabling event listeners for child tables
        // es-GT: Habilitando escuchadores de eventos en las tablas hijas del tipo de documento principal
        // No corra KEY UP, KEY PRESS, KEY DOWN en este campo!   NO NO NO NO NONONO
        // FIXME FIXME FIXME
        // Objetivo, cuando se salga del campo mediante TAB, que quede registrado el producto.
        // estrategia 1:  Focus al campo de quantity?  NO SIRVE.  Como que hay OTRO campo antes, quizas la flechita de link?
        frm.fields_dict.items.grid.wrapper.on('focusout blur',
            'input[data-fieldname="item_code"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Clicked on the field Item Code");

                each_item(frm, cdt, cdn);
                facelec_tax_calc_new(frm, cdt, cdn);
                // facelec_otros_impuestos_fila(frm, cdt, cdn);
            });

        // FIXME NO FUNCIONA CON TAB, SOLO HACIENDO CLICK Y ENTER.  Si se presiona TAB, SE BORRA!
        /*frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="item_code"][data-doctype="Sales Invoice Item"]', function(e) {
            console.log("Blurred away from the Item Code Field");
            each_item(frm, cdt, cdn);
            //facelec_tax_calc_new(frm, cdt, cdn);
        });*/
        frm.fields_dict.items.grid.wrapper.on('click',
            'input[data-fieldname="uom"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Click on the UOM field");
                each_item(frm, cdt, cdn);
            });
        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="uom"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Blur or focusout from the UOM field");
                each_item(frm, cdt, cdn);
            });
        // Do not refresh with each_item in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur',
            'input[data-fieldname="uom"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Mouse left the UOM field");
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
            });
        // Do not refresh with each_item in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur',
            'input[data-fieldname="qty"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Mouse leaving from the Quantity Field");
                each_item(frm, cdt, cdn);
                facelec_tax_calc_new(frm, cdt, cdn);
            });
        // DO NOT USE Keyup, ??  FIXME FIXME FIXME FIXME FIXME  este hace calculos bien
        frm.fields_dict.items.grid.wrapper.on('blur focusout',
            'input[data-fieldname="conversion_factor"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Blurring or focusing out from the Conversion Factor Field");
                //  IMPORTANT! IMPORTANT!  This is the one that gets the calculations correct!
                // Trying to calc first, then refresh, or no refresh at all...
                each_item(frm, cdt, cdn);
                cur_frm.refresh_field("conversion_factor");
                //facelec_tax_calc_new(frm, cdt, cdn);
                //setTimeout(function() { facelec_tax_calc_new(frm, cdt, cdn); }, 100);
                // Running it twice, does not help to clear the variables our when calculating based on new conversion factor. It lags. FIXME
                //fields_dict.items.wrapper.innerText or FIXME
                //fields_dict.items.$wrapper.innerText FIXME
                // find a way to realod this wrapper once more, so that proper data is set with innerHTML. FIXME
                //setTimeout(function() { facelec_tax_calc_new(frm, cdt, cdn) }, 100);
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
        frm.fields_dict.items.grid.wrapper.on('blur',
            'input[data-fieldname="rate"][data-doctype="Sales Invoice Item"]',
            function (e) {
                //console.log("Blurring from the Rate Field");
                // each_item(frm, cdt, cdn);
            });
        // en-US: Enabling event listeners in the main doctype
        // es-GT: Habilitando escuchadores de eventos en el tipo de documento principal
        // When ANY key is released after being pressed
        cur_frm.fields_dict.customer.$input.on("blur", function (evt) {
            //console.log("Se acaba de soltar una tecla del campo customer");
            facelec_tax_calc_new(frm, cdt, cdn);
            each_item(frm, cdt, cdn);
            refresh_field('qty');
        });
        // When mouse leaves the field
        cur_frm.fields_dict.customer.$input.on("blur focusout", function (evt) {
            //console.log("Salió del campo customercon mouseleave, blur, focusout");
            facelec_tax_calc_new(frm, cdt, cdn);
        });
        // Mouse clicks over the items field
        // cur_frm.fields_dict.items.$wrapper.on("click", function (evt) {
        //     console.log("Puntero de Ratón hizo click en el campo Items");
        //     each_item(frm, cdt, cdn);
        // });
        // Focusout from the field
        cur_frm.fields_dict.taxes_and_charges.$input.on("focusout", function (evt) {
            //console.log("Campo taxes and charges perdió el enfoque via focusout");
            facelec_tax_calc_new(frm, cdt, cdn);
            facelec_otros_impuestos_fila(frm, cdt, cdn);
        });
    },
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        // es-GT: Obtiene el numero de Identificacion tributaria ingresado en la hoja del cliente.
        // en-US: Fetches the Taxpayer Identification Number entered in the Customer doctype.
        cur_frm.add_fetch("customer", "nit_face_customer", "nit_face_customer");

        clean_fields(frm);

        // Works OK! No es necesario?
        // frm.add_custom_button("UOM Recalculation", function () {
        //     frm.doc.items.forEach((item) => {
        //         // for each button press each line is being processed.
        //         //console.log("item contains: " + item);
        //         //Importante
        //         facelec_tax_calc_new(frm, "Sales Invoice Item", item.name);
        //     });
        // });

        // Cuando el documento se actualiza, la funcion verificac que exista un cae.
        // En caso exista un cae, mostrara un boton para ver el PDF de la factura electronica generada.
        // En caso no exista un cae mostrara el boton para generar la factura electronica
        // correspondiente a su serie.
        // Se mostrara solo si esta validado el doc
        if (frm.doc.docstatus === 1) {
            verificacionCAE('manual', frm, cdt, cdn);
        }

        // INICIO BOTON PARA GENERAR NOTA DE CREDITO ELECTRONICA
        // Si la factura de venta se convierte a nota de credito,
        // para cumplir esta debe ser una factura electronica ya generada, segun esquema XML
        if (frm.doc.is_return && frm.doc.docstatus == 1 && (frm.doc.status === "Paid" ||
                frm.doc.status === "Unpaid" || frm.doc.status === "Submitted" || frm.doc.status === "Overdue" ||
                frm.doc.status === "Return")) { //  && frm.doc.numero_autorizacion_fel

            // APLICA SOLO PARA NOTAS DE CREDITO, PARA VER PDF
            if (frm.doc.status === "Return") {
                // SI en el campo de 'cae_factura_electronica' ya se encuentra el dato correspondiente, ocultara el boton
                // para generar el documento, para luego mostrar el boton para obtener el PDF del documento ya generado.
                if (frm.doc.numero_autorizacion_fel) {
                    cur_frm.clear_custom_buttons();
                    frm.add_custom_button(__("VER PDF NOTA CREDITO ELECTRONICA"),
                        function () {
                            window.open("https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" +
                                frm.doc.numero_autorizacion_fel);
                        }).addClass("btn-primary");

                } else {
                    cur_frm.clear_custom_buttons();
                    frm.add_custom_button(__("CREDIT NOTE FEL"), function () {
                        // Permite hacer confirmaciones
                        frappe.confirm(__('Are you sure you want to proceed to generate a credit note?'),
                            () => {
                                let d = new frappe.ui.Dialog({
                                    title: __('Generate Credit Note'),
                                    fields: [{
                                        label: 'Reason Adjusment?',
                                        fieldname: 'reason_adjust',
                                        fieldtype: 'Data',
                                        reqd: 1
                                    }],
                                    primary_action_label: 'Submit',
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
                                console.log('Selecciono NO')
                            })

                    }).addClass("btn-warning");
                }
            }

        } else {
            cur_frm.set_df_property("naming_series", "read_only", 0);
        }
        // FIN BOTON PARA GENERAR NOTA DE CREDITO ELECTRONICA


        // INICIO GENERACION POLIZA CON RETENCIONES
        // Se mostrara mientras la factura se enceuntre validada y su estatus sea diferente de Paid
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Paid') {

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
        // FIN GENERACION POLIZA CON RETENCIONES


    },
    validate: function (frm) {
        generar_tabla_html(frm);
    },
    nit_face_customer: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.nit_face_customer, frm.doc.customer, frm);
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
        each_item(frm, cdt, cdn);
        facelec_otros_impuestos_fila(frm, cdt, cdn);
        // Trigger antes de guardar
    },
    on_submit: function (frm, cdt, cdn) {
        // Ocurre cuando se presione el boton validar.
        // Cuando se valida el documento, se hace la consulta al servidor por medio de frappe.call

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
        // console.log(cuentas_registradas);
        // console.log(Object.keys(cuentas_registradas).length);

        // Si existe por lo menos una cuenta, se ejecuta frappe.call
        if (Object.keys(cuentas_registradas).length > 0) {
            // llama al metodo python, el cual recibe de parametros el nombre de la factura y el objeto
            // con las ('cuentas encontradas
            //console.log('---------------------- se encontro por lo menos una cuenta--------------------');
            frappe.call({
                method: "factura_electronica.resources_facelec.special_tax.add_gl_entry_other_special_tax",
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
                    frappe.call({
                        method: "factura_electronica.api.obtenerConfiguracionManualAutomatica",
                        callback: function (data) {
                            //console.log(data.message);
                            if (data.message === 'Manual') {
                                //console.log('Configuracion encontrada: MANUAL');
                                // No es necesario tener activa esta parte, ya que cuando se ingresa a cualquier factura en el evento
                                // refresh, hay una funcion que se encarga de comprobar de que se haya generado exitosamente la
                                // factura electronica, en caso no sea asi, se mostrarán los botones correspondientes, para hacer
                                // la generacion de la factura electronica manualmente.
                                // generarFacturaBTN(frm, cdt, cdn);
                            }
                            if (data.message === 'Automatico') {
                                //console.log('Configuracion encontrada: AUTOMATICO');
                                // generarFacturaSINBTN(frm, cdt, cdn);
                                verificacionCAE('automatico', frm, cdt, cdn);
                            }
                        }
                    });
                }
            });
        } else {
            // Busca la modalidad configurada, ya sea Manual o Automatica
            // Esto para mostrar u ocultar los botones para la geneneracion de factura
            // electronica
            frappe.call({
                method: "factura_electronica.api.obtenerConfiguracionManualAutomatica",
                callback: function (data) {
                    //console.log(data.message);
                    if (data.message === 'Manual') {
                        //console.log('Configuracion encontrada: MANUAL');
                        /* No es necesario tener activa esta parte, ya que cuando se ingresa a cualquier factura en el evento
                        refresh, hay una funcion que se encarga de comprobar de que se haya generado exitosamente la
                        factura electronica, en caso no sea asi, se mostrarán los botones correspondientes, para hacer
                        la generacion de la factura electronica manualmente.
                        generarFacturaBTN(frm, cdt, cdn); */
                    }
                    if (data.message === 'Automatico') {
                        //console.log('Configuracion encontrada: AUTOMATICO');
                        // generarFacturaSINBTN(frm, cdt, cdn);
                        verificacionCAE('automatico', frm, cdt, cdn);
                    }
                }
            });
        }
    },
    naming_series: function (frm, cdt, cdn) {
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
                        cur_frm.set_value('shs_numero_resolucion', numero_resolucion
                            .message);
                    }
                }
            });
        }
    },
    es_nota_de_debito: function (frm) {
        if (frm.doc.es_nota_de_debito) {
            console.log('Es nota de debito');
            cur_frm.set_df_property("naming_series", "read_only", 1);

            frappe.call({
                method: 'factura_electronica.api.obtener_serie_doc',
                args: {
                    opt: 'debit'
                },
                callback: function (r) {
                    console.log(r.message);

                    if (r.message) {
                        // cur_frm.set_value('naming_series', '');
                        cur_frm.set_value('naming_series', r.message);
                    }
                }
            });
        } else {
            cur_frm.set_df_property("naming_series", "read_only", 0);
        }
    },
    is_return: function (frm) {
        // Asignacion serie configurada para notas de credito
        if (frm.doc.is_return) {
            console.log('Es retorno');
            cur_frm.set_df_property("naming_series", "read_only", 1);

            frappe.call({
                method: 'factura_electronica.api.obtener_serie_doc',
                args: {
                    opt: 'credit'
                },
                callback: function (r) {
                    console.log(r.message);
                    if (r.message) {
                        cur_frm.set_value('naming_series', '');
                        cur_frm.set_value('naming_series', r.message);
                    }

                }
            });
        } else {
            cur_frm.set_df_property("naming_series", "read_only", 0);
            // cur_frm.set_value('naming_series', '');
        }
    }
});

frappe.ui.form.on("Sales Invoice Item", {
    items_add: function (frm, cdt, cdn) {},
    items_move: function (frm, cdt, cdn) {},
    before_items_remove: function (frm, cdt, cdn) {
        frm.doc.items.forEach((item_row_1, index_1) => {
            if (item_row_1.name == cdn) {
                // console.log('La Fila a Eliminar es --------------> ' + item_row_1.item_code);
                totalizar_valores(frm, cdn, item_row_1.facelec_tax_rate_per_uom_account,
                    item_row_1.facelec_other_tax_amount)
                // facelec_tax_calc_new(frm, cdt, cdn);
            }
        });
    },
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
    },
    item_code: function (frm, cdt, cdn) {
        each_item(frm, cdt, cdn);
        //facelec_tax_calc_new(frm, cdt, cdn);
    },
    qty: function (frm, cdt, cdn) {
        //facelec_tax_calculation(frm, cdt, cdn);
        facelec_tax_calc_new(frm, cdt, cdn);
        //console.log("cdt contains: " + cdt);
        //console.log("cdn contains: " + cdn);
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
        frm.doc.items.forEach((row, index) => {
            var a = row.rate;
            var b = row.qty;
            var c = row.amount;

            //let test = flt(row.shs_amount_for_back_calc) - flt(c);
            //let testB = test / 2;

            // Usando metodologia GoalSeek.js
            // https://github.com/adam-hanna/goalSeek.js/blob/master/goalSeek.js
            // console.log(goalSeek({
            //     Func: calculo_redondeo_pi,
            //     aFuncParams: [b, a],
            //     oFuncArgTarget: {
            //         Position: 0
            //     },
            //     Goal: row.shs_amount_for_back_calc,
            //     Tol: 0.001,
            //     maxIter: 10000
            // }));
            let calcu = goalSeek({
                Func: calculo_redondeo_pi,
                aFuncParams: [b, a],
                oFuncArgTarget: {
                    Position: 0
                },
                Goal: row.shs_amount_for_back_calc,
                Tol: 0.001,
                maxIter: 10000
            });
            console.log(calcu);

            frm.doc.items[index].qty = calcu;
            frm.doc.items[index].stock_qty = calcu;
            frm.doc.items[index].amount = (calcu * frm.doc.items[index].rate);
            frm.refresh_field("items");
        });
    }
    /*onload_post_render: function(frm, cdt, cdn){
        console.log('Funcionando Onload Post Render Trigger'); //SI FUNCIONA EL TRIGGER
    }*/
});

function calculo_redondeo_pi(a, b) {
    return a * b;
}

/* ----------------------------------------------------------------------------------------------------------------- */

function redondear(value, decimals) {
    return Number(Math.round(value + 'e' + decimals) + 'e-' + decimals);
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

    frm.add_custom_button(__("FACTURA ELECTRONICA EXPORTACION"),
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

        console.log('Hay que limpiar')
    }
}