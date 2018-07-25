/**
 * Copyright (c) 2017, 2018 SHS and contributors
 * For license information, please see license.txt
 */

console.log("Se cargo exitosamente la aplicación de Factura Electronica");
var otro_impuesto = 0;
var valor_con_iva = 0;
var para_rate = 0;
/* 1 Funcion calculadora para Sales Invoice ------------------------------------------------------------------------ */
function facelec_tax_calc_new(frm, cdt, cdn) {
    // es-GT: Actualiza los datos en los campos de la tabla hija 'items'
    //console.log("ran facelec_tax_calc_new");
    // es-GT: Revisamos si ya quedo cargado y definido el rate (tasa) de impuesto en el DocType, el cual debe estar en la fila 0 de Sales Taxes & Charges.
    // es-GT: Si no ha sido definido, no se hace nada. Si ya fue definido, se asigna a una variable el valor que encuentre en la fila 0 de la tabla hija taxes.
    if (typeof (cur_frm.doc.taxes[0].rate) == "undefined") {
        //console.log("No se ha cargado impuesto, asi que no se hace nada.");
    } else {
        //console.log("Ahora que ya se especifico un cliente, ya existe impuesto en la hoja, por lo tanto, lo asignamos a una variable!");
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        //console.log("El IVA cargado es: " + this_company_sales_tax_var);
    }
    // es-GT: Ahora se hace con un event listener al primer teclazo del campo de cliente
    // es-GT: Sin embargo queda aqui para asegurar que el valor sea el correcto en todo momento.
    var this_row_qty = 0;
    var this_row_rate = 0;
    var this_row_amount = 0;
    var this_row_conversion_factor = 0;
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
            this_row_taxable_amount = (item_row.amount - (item_row.stock_qty * item_row.facelec_tax_rate_per_uom));
            // We change the fields for other tax amount as per the complete row taxable amount.
            frm.doc.items[index].facelec_other_tax_amount = ((item_row.facelec_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            frm.doc.items[index].facelec_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - (item_row.stock_qty * item_row.facelec_tax_rate_per_uom));
            // We refresh the items to recalculate everything to ensure proper math
            frm.refresh_field("items");
            console.log(item_row.qty + " " + item_row.uom + "es/son igual/es a " + item_row.stock_qty + " " + item_row.stock_uom);
            console.log("conversion_factor is: " + item_row.conversion_factor);
            // Probando refrescar el campo de converison factor, talvez asi queda todo nitido??  TODO
            frm.refresh_field("conversion_factor");
            console.log("Other tax amount = Q" + (item_row.stock_qty * item_row.facelec_tax_rate_per_uom));
            console.log("Amount - Other Tax Amount = Amount minus excise tax: " + item_row.amount + " - " + (item_row.stock_qty * item_row.facelec_tax_rate_per_uom) + " = " + item_row.facelec_amount_minus_excise_tax);
            console.log("Q" + item_row.amount + " - (" + item_row.stock_qty + " * " + item_row.facelec_tax_rate_per_uom + ") ")
            // Verificacion Individual para verificar si es Fuel, Good o Service
            if (item_row.factelecis_fuel) {
                frm.doc.items[index].facelec_gt_tax_net_fuel_amt = (item_row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
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
            };

            if (item_row.facelec_is_good) {
                frm.doc.items[index].facelec_gt_tax_net_goods_amt = (item_row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
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
            };

            if (item_row.facelec_is_service) {
                //console.log("The item you added is a SERVICE!" + item_row.facelec_is_service);// WORKS OK!
                //console.log("El valor en servicios para el libro de compras es: " + net_services_tally);// WORKS OK!
                // Estimamos el valor del IVA para esta linea
                //frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_amount_minus_excise_tax * (this_company_sales_tax_var / 100)).toFixed(2);
                //frm.doc.items[index].facelec_gt_tax_net_services_amt = (item_row.facelec_amount_minus_excise_tax - item_row.facelec_sales_tax_for_this_row).toFixed(2);
                frm.doc.items[index].facelec_gt_tax_net_services_amt = (item_row.facelec_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_sales_tax_for_this_row = (item_row.facelec_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));

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
            };

            // Para el calculo total de IVA, basado en la sumatoria de facelec_sales_tax_for_this_row de cada item
            var full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.facelec_sales_tax_for_this_row);
            });
            // Seccion Guatemala Tax: Se asigna al campo de IVA de la seccion
            // frm.doc.facelec_total_iva = full_tax_iva;
            cur_frm.set_value('facelec_total_iva', full_tax_iva);
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
        tax_before_calc = frm.doc.facelec_total_iva;
        //console.log("El descuento total es:" + frm.doc.discount_amount);
        //console.log("El IVA calculado anteriormente:" + frm.doc.facelec_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        if (typeof (cur_frm.doc.taxes[0].rate) == "NaN") {
            console.log("No hay descuento definido, calculando sin descuento.");
        } else {
            console.log("El descuento parece ser un numero definido, calculando con descuento.");
            console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_total_iva = (frm.doc.facelec_total_iva - discount_amount_tax_value);
            console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
        }
        facelec_tax_calc_new(frm, "Sales Invoice Item", item.name);
        facelec_otros_impuestos_fila(frm, "Sales Invoice Item", item.name);
    });
}

/* 2 --------------------------------------------------------------------------------------------------------------- */
// Permite agregar filas en la posicion que le especifiquemos
function agregar_fila(doc, table_name, doctype, position) {
    // item bigger than length
    if (position > doc[table_name].length) {
        var row = frappe.model.add_child(doc, doctype, table_name);
        return row;
    }
    // item less than first
    else if (position < doc[table_name][0].idx) {
        var row = frappe.model.add_child(doc, doctype, table_name);
        row.idx = position;
        return row;
    }
    // item in the middle
    else {
        for (var curr_pos = position; curr_pos < doc[table_name].length; curr_pos++) {
            doc[table_name][curr_pos].idx += 1;
        }
        var row = frappe.model.add_child(doc, doctype, table_name);
        row.idx = position;
        return row;
    }
}

/* 3 Funciones para otros impuestos IDP ... ------------------------------------------------------------------------ */

// FIXME: PARA LOS DEMAS, uno para todos en items
// Esta funcion suma si es combustible, bien o servicio, totalizando los montos
// cada uno
function facelec_add_taxes(frm, tax_account) {
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
        if (d.facelec_tax_rate_per_uom_account === tax_account) {
            total_sumatoria += flt(d.facelec_other_tax_amount);
        };
    });

    return total_sumatoria;
}

function sumar_otros_impuestos_shs(frm, cdt, cdn) {
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
            if (item_row_1.facelec_tax_rate_per_uom_account) {

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
    });
}

function shs_total_other_tax(frm) {
    /**
     * Parametros:
     * #1 frm = formulario que se esta trabajando
     *
     * Funcionamiento:
     * Recorre la tabla hija shs_otros_impuestos, realiza sumatoria de todos las filas
     * que tenga una cuenta, el valor totalizado se asigna al campo shs_total_otros_imp_incl
     */
    var total_tax = 0;

    $.each(frm.doc.shs_otros_impuestos || [], function (i, d) {
        if (d.account_head) {
            total_tax += flt(d.total);
        };
    });

    cur_frm.set_value('shs_total_otros_imp_incl', total_tax);
    frm.refresh_field("shs_total_otros_imp_incl");
}

function facelec_otros_impuestos_fila(frm, cdt, cdn) {
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
            this_row_tax_amount = (item_row_i.stock_qty * item_row_i.facelec_tax_rate_per_uom);
            //this_row_taxable_amount = (item_row_i.amount - (item_row_i.stock_qty * item_row_i.facelec_tax_rate_per_uom));
            shs_otro_impuesto = item_row_i.facelec_other_tax_amount;

            // Guarda el nombre de la cuenta del item seleccionado
            var cuenta = item_row_i.facelec_tax_rate_per_uom_account;
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
                    frappe.model.add_child(cur_frm.doc, "Otros Impuestos Factura Electronica", "shs_otros_impuestos");

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

                            // Actualiza los datos de la tabla hija
                            cur_frm.refresh_field("shs_otros_impuestos");

                            // Funcion que se encarda de sumar los valores por cuenta
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


function totalizar_valores(frm, cdn) {
    frm.doc.shs_otros_impuestos.forEach((item_row_1, index_1) => {

        if (item_row_1.account_head) {
            // console.log('------------------------> ');
            frm.doc.items.forEach((tax_row_2, index_2) => {

                if (tax_row_2.facelec_tax_rate_per_uom_account === item_row_1.account_head) {
                    console.log('------------------------> ');
                    let totalizador = 0;

                    console.log('La cuenta a eliminar es ------------> ' + tax_row_2.facelec_tax_rate_per_uom_account);
                    totalizador = facelec_add_taxes(frm, tax_row_2.facelec_tax_rate_per_uom_account);
                    console.log('El valor del totalizador es ------------ > ' + totalizador);
                    // frm.doc.shs_otros_impuestos[index_1].total = totalizador;

                    // cur_frm.refresh_field("shs_otros_impuestos");
                    // shs_total_other_tax(frm);

                    // cur_frm.refresh_field("shs_otros_impuestos");
                }

            });
        }

    });
}
/* 4 --------------------------------------------------------------------------------------------------------------- */

function buscar_account(frm, cuenta_b) {
    /**
     * Funcionamiento: recibe como parametro frm, y cuenta_b, lo que hace es, buscar en todas las filas de taxes
     * si existe ya una cuenta con el nombre de la cuenta recibida por parametro, en caso ya exista esa cuenta en
     * la tabla no hace nada, pero si encuentra que no hay una cuenta igual a la recibida en el parametro, entonces
     * la funcion encargada agregara una nueva fila con los datos correspondientes, esta funcion retorna true
     * en caso si encuentre una cuenta existente
     */
    var estado = false;

    $.each(frm.doc.shs_otros_impuestos || [], function (i, d) {
        if (d.account_head === cuenta_b) {
            // console.log('Si Existe en el indice ' + i)
            estado = true;
        }
    });

    return estado;
}

/* 5 --------------------------------------------------------------------------------------------------------------- */
function valNit(nit, cus_supp, frm) {
    /**
     * Funcionamiento: Valida que el Nit sea C/F o un numero de nit valido permitiendo
     * activar la opcion para guardar. Si el nit es invalido desactiva la funcion
     * guardar hasta que se ingrese uno correcto, esto permite no tener errores con
     * INFILE y tener los datos correctos.
     */
    if (nit === "C/F" || nit === "c/f") {
        frm.enable_save(); // Activa y Muestra el boton guardar de Sales Invoice
    } else {
        var nd, add = 0;
        if (nd = /^(\d+)\-?([\dk])$/i.exec(nit)) {
            nd[2] = (nd[2].toLowerCase() == 'k') ? 10 : parseInt(nd[2]);
            for (var i = 0; i < nd[1].length; i++) {
                add += ((((i - nd[1].length) * -1) + 1) * nd[1][i]);
            }
            nit_validado = ((11 - (add % 11)) % 11) == nd[2];
        } else {
            nit_validado = false;
        }

        if (nit_validado === false) {
            msgprint('NIT de: <b>' + cus_supp + '</b>, no es correcto. Si no tiene disponible el NIT modifiquelo a <b>C/F</b>');
            frm.disable_save(); // Desactiva y Oculta el boton de guardar en Sales Invoice
        }
        if (nit_validado === true) {
            frm.enable_save(); // Activa y Muestra el boton guardar de Sales Invoice
        }
    }
}

/* 6 Funciones creadoras de botones --------------------------------------------------------------------------------------- */
function pdf_button(cae_documento, frm) {
    // Esta funcion se encarga de mostrar el boton para obtener el pdf de la factura electronica generada
    frm.add_custom_button(__("VER PDF FACTURA ELECTRONICA"),
        function () {
            window.open("https://www.ingface.net/Ingfacereport/dtefactura.jsp?cae=" + cae_documento);
        }).addClass("btn-primary");
}

function guardar_pdf(frm) {
    /*
    Crea un boton que permite guardar el PDF de factura electronica generado en el servidor
    de forma privada, tras finalizar la ejecucion del script del lado del servidor en el
    callback se recarga la pagina para mostrar el archivo adjunto.
    */
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
    }).addClass("btn-primary"); //NOTA: Se puede crear una clase para el boton CSS
}

function generar_boton_factura(tipo_factura, frm) {
    frm.add_custom_button(__(tipo_factura), function () {
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
                // console.log('Serie generada: ' + data.message);
                // console.log('serie original: ' + serie_de_factura);
                if (data.message !== undefined) {
                    // Crea una nueva url con el nombre del documento actualizado
                    let url_nueva = mi_url.replace(serie_de_factura, data.message);
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
            // console.log('Serie generada: ' + data.message);
            // console.log('serie original: ' + serie_de_factura);
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
function verificacionCAE(modalidad, frm, cdt, cdn) {
    /* ------------------------------ COMPROBACIONES DE CAE ------------------------------ */
    // FACTURAS FACE, CFACE
    // Este codigo entra en funcionamiento cuando la generacion automatica de la factura no es exitosa.
    // esto permite volver intentarlo hasta obtener el cae de la factura en que se estre trabajando.
    if (frm.doc.status === "Paid" || frm.doc.status === "Unpaid" || frm.doc.status === "Submitted" || frm.doc.status === "Overdue") {
        // SI en el campo de 'cae_factura_electronica' ya se encuentra el dato correspondiente, ocultara el boton
        // para generar el documento, para luego mostrar el boton para obtener el PDF del documento ya generado.
        if (frm.doc.cae_factura_electronica) {
            cur_frm.clear_custom_buttons();
            pdf_button(frm.doc.cae_factura_electronica, frm);
            guardar_pdf(frm);
        } else {
            // Si la modalidad recibida es manual se genera un boton para hacer la factura electronica manualmente
            if (modalidad === 'manual') {
                generar_boton_factura('Factura Electronica', frm);
            }
            // Si la modalidad recibida es automatica se realiza la factura electronica directamente
            if (modalidad === 'automatico') {
                generar_factura_sin_btn(frm);
            }
        }
    }

    // Codigo para Notas de Credito NCE
    // El codigo se ejecutara segun el estado del documento, puede ser: Retornar
    if (frm.doc.status === "Return") {
        //var nombre = 'Nota Credito';
        // SI en el campo de 'cae_nota_de_credito' ya se encuentra el dato correspondiente, ocultara el boton
        // para generar el documento, para luego mostrar el boton para obtener el PDF del documento ya generado.
        if (frm.doc.cae_factura_electronica) {
            cur_frm.clear_custom_buttons();
            pdf_button(frm.doc.cae_factura_electronica, frm);
            guardar_pdf(frm);
        } else {
            // Si la modalidad recibida es manual se genera un boton para hacer la factura electronica manualmente
            if (modalidad === 'manual') {
                generar_boton_factura('Nota Credito Electronica', frm);
            }
            // Si la modalidad recibida es automatica se realiza la factura electronica directamente
            if (modalidad === 'automatico') {
                generar_factura_sin_btn(frm);
            }
        }
    }

    // Codigo para notas de debito
    // Codigo para Notas de Credito NDE
    if (frm.doc.status === "Paid" || frm.doc.status === "Unpaid" || frm.doc.status === "Submitted" || frm.doc.status === "Overdue") {
        //var nombre = 'Nota Debito';
        if (frm.doc.es_nota_de_debito) {
            cur_frm.clear_custom_buttons('Factura Electronica');
            if (frm.doc.cae_factura_electronica) {
                cur_frm.clear_custom_buttons();
                pdf_button(frm.doc.cae_factura_electronica, frm);
                guardar_pdf(frm);
            } else {
                // Si la modalidad recibida es manual se genera un boton para hacer la factura electronica manualmente
                if (modalidad === 'manual') {
                    generar_boton_factura('Nota Debito Electronica', frm);
                }
                // Si la modalidad recibida es automatica se realiza la factura electronica directamente
                if (modalidad === 'automatico') {
                    generar_factura_sin_btn(frm);
                }
            }
        }
    }
    /* -------------------------------------------------------------------------------------- */
    // Funcionalidad evita copiar CAE cuando se duplica una factura
    if (frm.doc.status === 'Draft') {
        // console.log('No Guardada');
        cur_frm.set_value("cae_factura_electronica", '');
        cur_frm.set_value("serie_original_del_documento", '');
        // frm.doc.cae_factura_electronica = '';
        // frm.doc.serie_original_del_documento = '';
    }
}

/* 8 Funciones Calculadoras -------------------------------------------------------------------------------------------------- */

// Factura de Compra
function shs_purchase_invoice_calculation(frm, cdt, cdn) {

    refresh_field('items');

    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

    var this_row_qty, this_row_rate, this_row_amount, this_row_conversion_factor, this_row_stock_qty, this_row_tax_rate, this_row_tax_amount, this_row_taxable_amount;

    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name == cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.facelec_p_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
            // Convert a number into a string, keeping only two decimals:
            frm.doc.items[index].facelec_p_other_tax_amount = ((item_row.facelec_p_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].facelec_p_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.facelec_p_tax_rate_per_uom));
            console.log("uom that just changed is: " + item_row.uom);
            console.log("stock qty is: " + item_row.stock_qty); // se queda con el numero anterior.  multiplicar por conversion factor (si existiera!)
            // Por alguna razón esta multiplicando y obteniendo valores negativos  FIXME
            // absoluto? FIXME
            // Que sucedera con una nota de crédito? FIXME
            // Absoluto y luego NEGATIVIZADO!? FIXME
            console.log("conversion_factor is: " + item_row.conversion_factor);
            if (item_row.facelec_p_is_fuel == 1) {
                frm.doc.items[index].facelec_p_gt_tax_net_fuel_amt = (item_row.facelec_p_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_p_sales_tax_for_this_row = (item_row.facelec_p_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    // total_qty += flt(d.qty);
                    if (d.facelec_p_is_fuel == true) {
                        total_fuel += flt(d.facelec_p_gt_tax_net_fuel_amt);
                    };
                });
                frm.doc.facelec_p_gt_tax_fuel = total_fuel;
                //frm.refresh_field("factelec_p_is_fuel");
            };
            if (item_row.facelec_p_is_good == 1) {
                frm.doc.items[index].facelec_p_gt_tax_net_goods_amt = (item_row.facelec_p_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_p_sales_tax_for_this_row = (item_row.facelec_p_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_p_is_good == true) {
                        total_goods += flt(d.facelec_p_gt_tax_net_goods_amt);
                    };
                });
                frm.doc.facelec_p_gt_tax_goods = total_goods;
            };
            if (item_row.facelec_p_is_service == 1) {
                frm.doc.items[index].facelec_p_gt_tax_net_services_amt = (item_row.facelec_p_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_p_sales_tax_for_this_row = (item_row.facelec_p_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check servicios
                total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_p_is_service == true) {
                        total_servi += flt(d.facelec_p_gt_tax_net_services_amt);
                    };
                });
                frm.doc.facelec_p_gt_tax_services = total_servi;
            };
            full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.facelec_p_sales_tax_for_this_row);
            });
            frm.doc.facelec_p_total_iva = full_tax_iva;
        };
    });
}

// cálculo de cotizaciones
function shs_quotation_calculation(frm, cdt, cdn) {

    refresh_field('items');

    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

    var this_row_qty, this_row_rate, this_row_amount, this_row_conversion_factor, this_row_stock_qty, this_row_tax_rate, this_row_tax_amount, this_row_taxable_amount;

    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name == cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.facelec_qt_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
            // Convert a number into a string, keeping only two decimals:
            frm.doc.items[index].facelec_qt_other_tax_amount = ((item_row.facelec_qt_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].facelec_qt_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.facelec_qt_tax_rate_per_uom));
            console.log("uom that just changed is: " + item_row.uom);
            console.log("stock qty is: " + item_row.stock_qty); // se queda con el numero anterior.  multiplicar por conversion factor (si existiera!)
            // Por alguna razón esta multiplicando y obteniendo valores negativos  FIXME
            // absoluto? FIXME
            // Que sucedera con una nota de crédito? FIXME
            // Absoluto y luego NEGATIVIZADO!? FIXME
            console.log("conversion_factor is: " + item_row.conversion_factor);
            if (item_row.facelec_qt_is_fuel == 1) {
                frm.doc.items[index].facelec_qt_gt_tax_net_fuel_amt = (item_row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_qt_sales_tax_for_this_row = (item_row.facelec_qt_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    // total_qty += flt(d.qty);
                    if (d.facelec_qt_is_fuel == true) {
                        total_fuel += flt(d.facelec_qt_gt_tax_net_fuel_amt);
                    };
                });
                frm.doc.facelec_qt_gt_tax_fuel = total_fuel;
                //frm.refresh_field("factelec_p_is_fuel");
            };
            if (item_row.facelec_qt_is_good == 1) {
                frm.doc.items[index].facelec_qt_gt_tax_net_goods_amt = (item_row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_qt_sales_tax_for_this_row = (item_row.facelec_qt_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_qt_is_good == true) {
                        total_goods += flt(d.facelec_qt_gt_tax_net_goods_amt);
                    };
                });
                frm.doc.facelec_qt_gt_tax_goods = total_goods;
            };
            if (item_row.facelec_qt_is_service == 1) {
                frm.doc.items[index].facelec_qt_gt_tax_net_services_amt = (item_row.facelec_qt_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_qt_sales_tax_for_this_row = (item_row.facelec_qt_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check servicios
                total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_qt_is_service == true) {
                        total_servi += flt(d.facelec_qt_gt_tax_net_services_amt);
                    };
                });
                frm.doc.facelec_qt_gt_tax_services = total_servi;
            };
            full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.facelec_qt_sales_tax_for_this_row);
            });
            frm.doc.facelec_qt_total_iva = full_tax_iva;
        };
    });
}

// cálculo de orden de compra
function shs_purchase_order_calculation(frm, cdt, cdn) {
    // es-GT: Actualiza los campos de la tabla hija 'items'
    refresh_field('items');
    // es-GT: Asigna a la variable el valor rate de la tabla hija 'taxes' en la posicion 0
    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

    var this_row_qty, this_row_rate, this_row_amount, this_row_conversion_factor, this_row_stock_qty, this_row_tax_rate, this_row_tax_amount, this_row_taxable_amount;
    // es-GT: Funcion que permite realizar los calculos necesarios dependiendo de la linea en la que se este trabajando
    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name == cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.facelec_po_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
            // Convert a number into a string, keeping only two decimals:
            frm.doc.items[index].facelec_po_other_tax_amount = ((item_row.facelec_po_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].facelec_po_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.facelec_po_tax_rate_per_uom));
            console.log("uom that just changed is: " + item_row.uom);
            console.log("stock qty is: " + item_row.stock_qty); // se queda con el numero anterior.  multiplicar por conversion factor (si existiera!)
            // Por alguna razón esta multiplicando y obteniendo valores negativos  FIXME
            // absoluto? FIXME
            // Que sucedera con una nota de crédito? FIXME
            // Absoluto y luego NEGATIVIZADO!? FIXME
            console.log("conversion_factor is: " + item_row.conversion_factor);
            // es-GT: Verificacion de si esta seleccionado el check Combustible
            if (item_row.facelec_po_is_fuel == 1) {
                frm.doc.items[index].facelec_po_gt_tax_net_fuel_amt = (item_row.facelec_po_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_po_sales_tax_for_this_row = (item_row.facelec_po_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    // total_qty += flt(d.qty);
                    if (d.facelec_po_is_fuel == true) {
                        total_fuel += flt(d.facelec_po_gt_tax_net_fuel_amt);
                    };
                });
                frm.doc.facelec_po_gt_tax_fuel = total_fuel;
                //frm.refresh_field("factelec_p_is_fuel");
            };
            // es-GT: Verificacion de si esta seleccionado el check Bienes
            if (item_row.facelec_po_is_good == 1) {
                frm.doc.items[index].facelec_po_gt_tax_net_goods_amt = (item_row.facelec_po_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_po_sales_tax_for_this_row = (item_row.facelec_po_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_po_is_good == true) {
                        total_goods += flt(d.facelec_po_gt_tax_net_goods_amt);
                    };
                });
                frm.doc.facelec_po_gt_tax_goods = total_goods;
            };
            // es-GT: Verificacion de si esta seleccionado el check Servicios
            if (item_row.facelec_po_is_service == 1) {
                frm.doc.items[index].facelec_po_gt_tax_net_services_amt = (item_row.facelec_po_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_po_sales_tax_for_this_row = (item_row.facelec_po_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check servicios
                total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_po_is_service == true) {
                        total_servi += flt(d.facelec_po_gt_tax_net_services_amt);
                    };
                });
                frm.doc.facelec_po_gt_tax_services = total_servi;
            };
            // es-GT: Sumatoria para obtener el IVA total
            full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.facelec_po_sales_tax_for_this_row);
            });
            frm.doc.facelec_po_total_iva = full_tax_iva;
        };
    });
}

// cálculo de recibo de compra
function shs_purchase_receipt_calculation(frm, cdt, cdn) {

    refresh_field('items');

    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

    var this_row_qty, this_row_rate, this_row_amount, this_row_conversion_factor, this_row_stock_qty, this_row_tax_rate, this_row_tax_amount, this_row_taxable_amount;

    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name == cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.facelec_pr_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
            // Convert a number into a string, keeping only two decimals:
            frm.doc.items[index].facelec_pr_other_tax_amount = ((item_row.facelec_pr_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].facelec_pr_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.facelec_pr_tax_rate_per_uom));
            console.log("uom that just changed is: " + item_row.uom);
            console.log("stock qty is: " + item_row.stock_qty); // se queda con el numero anterior.  multiplicar por conversion factor (si existiera!)
            // Por alguna razón esta multiplicando y obteniendo valores negativos  FIXME
            // absoluto? FIXME
            // Que sucedera con una nota de crédito? FIXME
            // Absoluto y luego NEGATIVIZADO!? FIXME
            console.log("conversion_factor is: " + item_row.conversion_factor);
            if (item_row.facelec_pr_is_fuel == 1) {
                frm.doc.items[index].facelec_pr_gt_tax_net_fuel_amt = (item_row.facelec_pr_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_pr_sales_tax_for_this_row = (item_row.facelec_pr_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    // total_qty += flt(d.qty);
                    if (d.facelec_pr_is_fuel == true) {
                        total_fuel += flt(d.facelec_pr_gt_tax_net_fuel_amt);
                    };
                });
                frm.doc.facelec_pr_gt_tax_fuel = total_fuel;
                //frm.refresh_field("factelec_p_is_fuel");
            };
            if (item_row.facelec_pr_is_good == 1) {
                frm.doc.items[index].facelec_pr_gt_tax_net_goods_amt = (item_row.facelec_pr_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_pr_sales_tax_for_this_row = (item_row.facelec_pr_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_pr_is_good == true) {
                        total_goods += flt(d.facelec_pr_gt_tax_net_goods_amt);
                    };
                });
                frm.doc.facelec_pr_gt_tax_goods = total_goods;
            };
            if (item_row.facelec_pr_is_service == 1) {
                frm.doc.items[index].facelec_pr_gt_tax_net_services_amt = (item_row.facelec_pr_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_pr_sales_tax_for_this_row = (item_row.facelec_pr_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check servicios
                total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.facelec_pr_is_service == true) {
                        total_servi += flt(d.facelec_pr_gt_tax_net_services_amt);
                    };
                });
                frm.doc.facelec_pr_gt_tax_services = total_servi;
            };
            full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.facelec_pr_sales_tax_for_this_row);
            });
            frm.doc.facelec_pr_total_iva = full_tax_iva;
        };
    });
}

// cálculo de orden de ventas
function shs_sales_order_calculation(frm, cdt, cdn) {

    refresh_field('items');

    let this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

    let this_row_qty, this_row_rate, this_row_amount, this_row_conversion_factor, this_row_stock_qty, this_row_tax_rate, this_row_tax_amount, this_row_taxable_amount;

    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name === cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.shs_so_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
            // Convert a number into a string, keeping only two decimals:
            frm.doc.items[index].shs_so_other_tax_amount = ((item_row.shs_so_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].shs_so_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.shs_so_tax_rate_per_uom));
            console.log("uom that just changed is: " + item_row.uom);
            console.log("stock qty is: " + item_row.stock_qty); // se queda con el numero anterior.  multiplicar por conversion factor (si existiera!)
            // Por alguna razón esta multiplicando y obteniendo valores negativos  FIXME
            // absoluto? FIXME
            // Que sucedera con una nota de crédito? FIXME
            // Absoluto y luego NEGATIVIZADO!? FIXME
            console.log("conversion_factor is: " + item_row.conversion_factor);
            if (item_row.shs_so_is_fuel === 1) {
                frm.doc.items[index].shs_so_gt_tax_net_fuel_amt = (item_row.shs_so_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].shs_so_sales_tax_for_this_row = (item_row.shs_so_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                let total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    // total_qty += flt(d.qty);
                    if (d.shs_so_is_fuel === 1) {
                        total_fuel += flt(d.shs_so_gt_tax_net_fuel_amt);
                    };
                });
                frm.doc.shs_gt_tax_fuel = total_fuel;
                //frm.refresh_field("factelec_p_is_fuel");
            };
            if (item_row.shs_so_is_good === 1) {
                frm.doc.items[index].shs_so_gt_tax_net_goods_amt = (item_row.shs_so_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].shs_so_sales_tax_for_this_row = (item_row.shs_so_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                let total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.shs_so_is_good === 1) {
                        total_goods += flt(d.shs_so_gt_tax_net_goods_amt);
                    };
                });
                frm.doc.shs_so_gt_tax_goods = total_goods;
            };
            if (item_row.shs_so_is_service === 1) {
                frm.doc.items[index].shs_so_gt_tax_net_services_amt = (item_row.shs_so_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].shs_so_sales_tax_for_this_row = (item_row.shs_so_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check servicios
                let total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.shs_so_is_service === 1) {
                        total_servi += flt(d.shs_so_gt_tax_net_services_amt);
                    };
                });
                frm.doc.shs_so_gt_tax_services = total_servi;
            };
            let full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.shs_so_sales_tax_for_this_row);
            });
            frm.doc.shs_so_total_iva = full_tax_iva;
        };
    });
}

// cálculo de nota de entrega
function shs_delivery_note_calculation(frm, cdt, cdn) {

    refresh_field('items');

    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

    var this_row_qty, this_row_rate, this_row_amount, this_row_conversion_factor, this_row_stock_qty, this_row_tax_rate, this_row_tax_amount, this_row_taxable_amount;

    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name == cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.shs_dn_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
            // Convert a number into a string, keeping only two decimals:
            frm.doc.items[index].shs_dn_other_tax_amount = ((item_row.shs_dn_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].shs_dn_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.shs_dn_tax_rate_per_uom));
            console.log("uom that just changed is: " + item_row.uom);
            console.log("stock qty is: " + item_row.stock_qty); // se queda con el numero anterior.  multiplicar por conversion factor (si existiera!)
            // Por alguna razón esta multiplicando y obteniendo valores negativos  FIXME
            // absoluto? FIXME
            // Que sucedera con una nota de crédito? FIXME
            // Absoluto y luego NEGATIVIZADO!? FIXME
            console.log("conversion_factor is: " + item_row.conversion_factor);
            if (item_row.shs_dn_is_fuel == 1) {
                frm.doc.items[index].shs_dn_gt_tax_net_fuel_amt = (item_row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].shs_dn_sales_tax_for_this_row = (item_row.shs_dn_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    // total_qty += flt(d.qty);
                    if (d.shs_dn_is_fuel == true) {
                        total_fuel += flt(d.shs_dn_gt_tax_net_fuel_amt);
                    };
                });
                frm.doc.shs_dn_gt_tax_fuel = total_fuel;
                //frm.refresh_field("factelec_p_is_fuel");
            };
            if (item_row.shs_dn_is_good == 1) {
                frm.doc.items[index].shs_dn_gt_tax_net_goods_amt = (item_row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].shs_dn_sales_tax_for_this_row = (item_row.shs_dn_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.shs_dn_is_good == true) {
                        total_goods += flt(d.shs_dn_gt_tax_net_goods_amt);
                    };
                });
                frm.doc.shs_dn_gt_tax_goods = total_goods;
            };
            if (item_row.shs_dn_is_service == 1) {
                frm.doc.items[index].shs_dn_gt_tax_net_services_amt = (item_row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].shs_dn_sales_tax_for_this_row = (item_row.shs_dn_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check servicios
                total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.shs_dn_is_service == true) {
                        total_servi += flt(d.shs_dn_gt_tax_net_services_amt);
                    };
                });
                frm.doc.shs_dn_gt_tax_services = total_servi;
            };
            full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.shs_dn_sales_tax_for_this_row);
            });
            frm.doc.shs_dn_total_iva = full_tax_iva;
        };
    });
}

// cálculo de cotizacion del proveedor
function shs_supplier_quotation_calculation(frm, cdt, cdn) {

    refresh_field('items');

    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

    var this_row_qty, this_row_rate, this_row_amount, this_row_conversion_factor, this_row_stock_qty, this_row_tax_rate, this_row_tax_amount, this_row_taxable_amount;

    frm.doc.items.forEach((item_row, index) => {
        if (item_row.name == cdn) {
            this_row_amount = (item_row.qty * item_row.rate);
            this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
            this_row_tax_rate = (item_row.shs_spq_tax_rate_per_uom);
            this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
            this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
            // Convert a number into a string, keeping only two decimals:
            frm.doc.items[index].shs_spq_other_tax_amount = ((item_row.shs_spq_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].shs_spq_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.shs_spq_tax_rate_per_uom));
            console.log("uom that just changed is: " + item_row.uom);
            console.log("stock qty is: " + item_row.stock_qty); // se queda con el numero anterior.  multiplicar por conversion factor (si existiera!)
            // Por alguna razón esta multiplicando y obteniendo valores negativos  FIXME
            // absoluto? FIXME
            // Que sucedera con una nota de crédito? FIXME
            // Absoluto y luego NEGATIVIZADO!? FIXME
            console.log("conversion_factor is: " + item_row.conversion_factor);
            if (item_row.shs_spq_is_fuel == 1) {
                frm.doc.items[index].shs_spq_gt_tax_net_fuel_amt = (item_row.shs_spq_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].shs_spq_sales_tax_for_this_row = (item_row.shs_spq_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check combustibles
                total_fuel = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    // total_qty += flt(d.qty);
                    if (d.shs_spq_is_fuel == true) {
                        total_fuel += flt(d.shs_spq_gt_tax_net_fuel_amt);
                    };
                });
                frm.doc.shs_spq_gt_tax_fuel = total_fuel;
                //frm.refresh_field("factelec_p_is_fuel");
            };
            if (item_row.shs_spq_is_good == 1) {
                frm.doc.items[index].shs_spq_gt_tax_net_goods_amt = (item_row.shs_spq_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].shs_spq_sales_tax_for_this_row = (item_row.shs_spq_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check bienes
                total_goods = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.shs_spq_is_good == true) {
                        total_goods += flt(d.shs_spq_gt_tax_net_goods_amt);
                    };
                });
                frm.doc.shs_spq_gt_tax_goods = total_goods;
            };
            if (item_row.shs_spq_is_service == 1) {
                frm.doc.items[index].shs_spq_gt_tax_net_services_amt = (item_row.shs_spq_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].shs_spq_sales_tax_for_this_row = (item_row.shs_spq_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
                // Sumatoria de todos los que tengan el check servicios
                total_servi = 0;
                $.each(frm.doc.items || [], function (i, d) {
                    if (d.shs_spq_is_service == true) {
                        total_servi += flt(d.shs_spq_gt_tax_net_services_amt);
                    };
                });
                frm.doc.shs_spq_gt_tax_services = total_servi;
            };
            full_tax_iva = 0;
            $.each(frm.doc.items || [], function (i, d) {
                full_tax_iva += flt(d.shs_spq_sales_tax_for_this_row);
            });
            frm.doc.shs_spq_total_iva = full_tax_iva;
        };
    });
}

/* 9 Eventos en Doctypes---------------------------------------------------------------------------------------------- */

/* Factura de Ventas-------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Sales Invoice", {
    onload_post_render: function (frm, cdt, cdn) {
        console.log('Funcionando Onload Post Render Trigger'); //SI FUNCIONA EL TRIGGER
        // Funciona unicamente cuando se carga por primera vez el documento y aplica unicamente para el form y no childtables

        // en-US: Enabling event listeners for child tables
        // es-GT: Habilitando escuchadores de eventos en las tablas hijas del tipo de documento principal
        // No corra KEY UP, KEY PRESS, KEY DOWN en este campo!   NO NO NO NO NONONO
        // FIXME FIXME FIXME
        // Objetivo, cuando se salga del campo mediante TAB, que quede registrado el producto.
        // estrategia 1:  Focus al campo de quantity?  NO SIRVE.  Como que hay OTRO campo antes, quizas la flechita de link?
        frm.fields_dict.items.grid.wrapper.on('click focusout blur', 'input[data-fieldname="item_code"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Clicked on the field Item Code");

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
        frm.fields_dict.items.grid.wrapper.on('click', 'input[data-fieldname="uom"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Click on the UOM field");
            each_item(frm, cdt, cdn);
        });
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="uom"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Blur or focusout from the UOM field");
            each_item(frm, cdt, cdn);
        });
        // Do not refresh with each_item in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('mouseleave', 'input[data-fieldname="uom"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Mouse left the UOM field");
            facelec_tax_calc_new(frm, cdt, cdn);
        });
        // This part might seem counterintuitive, but it is the "next" field in tab order after item code, which helps for a "creative" strategy to update everything after pressing TAB out of the item code field.  FIXME
        frm.fields_dict.items.grid.wrapper.on('focus', 'input[data-fieldname="item_name"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Focusing with keyboard cursor through TAB on the Item Name Field");
            each_item(frm, cdt, cdn);
            facelec_otros_impuestos_fila(frm, cdt, cdn);
        });
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="qty"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Blurring or focusing out from the Quantity Field");
            each_item(frm, cdt, cdn);
        });
        // Do not refresh with each_item in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('mouseleave', 'input[data-fieldname="qty"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Mouse leaving from the Quantity Field");
            each_item(frm, cdt, cdn);
            facelec_tax_calc_new(frm, cdt, cdn);
        });
        // DO NOT USE Keyup, ??  FIXME FIXME FIXME FIXME FIXME  este hace calculos bien
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="conversion_factor"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Blurring or focusing out from the Conversion Factor Field");
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
        frm.fields_dict.items.grid.wrapper.on('keyup mouseleave focusout', 'input[data-fieldname="conversion_factor"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Key up, mouse leave or focus out from the Conversion Factor Field");
            // Trying to calc first, then refresh, or no refresh at all...
            facelec_tax_calc_new(frm, cdt, cdn);
            each_item(frm, cdt, cdn);
            cur_frm.refresh_field("conversion_factor");
        });
        frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="rate"][data-doctype="Sales Invoice Item"]', function (e) {
            console.log("Blurring from the Rate Field");
            // each_item(frm, cdt, cdn);
        });
        // en-US: Enabling event listeners in the main doctype
        // es-GT: Habilitando escuchadores de eventos en el tipo de documento principal
        // When ANY key is released after being pressed
        cur_frm.fields_dict.customer.$input.on("keyup", function (evt) {
            console.log("Se acaba de soltar una tecla del campo customer");
            facelec_tax_calc_new(frm, cdt, cdn);
            each_item(frm, cdt, cdn);
            refresh_field('qty');
        });
        // When mouse leaves the field
        cur_frm.fields_dict.customer.$input.on("mouseleave blur focusout", function (evt) {
            console.log("Salió del campo customercon mouseleave, blur, focusout");
            facelec_tax_calc_new(frm, cdt, cdn);
        });
        // Mouse clicks over the items field
        cur_frm.fields_dict.items.$wrapper.on("click", function (evt) {
            console.log("Puntero de Ratón hizo click en el campo Items");
            each_item(frm, cdt, cdn);
        });
        // Focusout from the field
        cur_frm.fields_dict.taxes_and_charges.$input.on("focusout", function (evt) {
            console.log("Campo taxes and charges perdió el enfoque via focusout");
            facelec_tax_calc_new(frm, cdt, cdn);
            facelec_otros_impuestos_fila(frm, cdt, cdn);
        });
    },
    customer: function (frm, cdt, cdn) {
        // Trigger Proveedor
    },
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        // es-GT: Obtiene el numero de Identificacion tributaria ingresado en la hoja del cliente.
        // en-US: Fetches the Taxpayer Identification Number entered in the Customer doctype.
        cur_frm.add_fetch("customer", "nit_face_customer", "nit_face_customer");

        // Works OK!
        frm.add_custom_button("UOM Recalculation", function () {
            frm.doc.items.forEach((item) => {
                // for each button press each line is being processed.
                console.log("item contains: " + item);
                //Importante
                facelec_tax_calc_new(frm, "Sales Invoice Item", item.name);
            });
        });

        // Cuando el documento se actualiza, la funcion verificac de que exista un cae.
        // En caso exista un cae, mostrara un boton para ver el PDF de la factura electronica generada.
        // En caso no exista un cae mostrara el boton para generar la factura electronica
        // correspondiente a su serie.
        verificacionCAE('manual', frm, cdt, cdn);
    },
    nit_face_customer: function (frm, cdt, cdn) {
        // if (frm.doc.nit_face_customer === null) {
        //     console.log('EL NIT ES NULL')
        // }
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.nit_face_customer, frm.doc.customer, frm);
    },
    taxes_and_charges: function (frm, cdt, cdn) {
        // es-GT: Se corre aqui en caso se seleccione una tabla de impuestos nueva.
        // facelec_otros_impuestos_fila(cur_frm, cdt,cdn); // NO SIRVE!!
    },
    additional_discount_percentage: function (frm, cdt, cdn) {
        // Pensando en colocar un trigger aqui para cuando se actualice el campo de descuento adicional
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        tax_before_calc = frm.doc.facelec_total_iva;
        console.log("El descuento total es:" + frm.doc.discount_amount);
        // es-GT: Este muestra el IVA que se calculo por medio de nuestra aplicación.
        console.log("El IVA calculado anteriormente:" + frm.doc.facelec_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));

        if (discount_amount_net_value == NaN || discount_amount_net_value == undefined) {
            console.log("No hay descuento definido, calculando sin descuento.");
        } else {
            console.log("El descuento parece ser un numero definido, calculando con descuento.");
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_total_iva = (frm.doc.facelec_total_iva - discount_amount_tax_value);
            console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
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
            // con las cuentas encontradas
            frappe.call({
                method: "factura_electronica.special_tax.add_gl_entry_other_special_tax",
                args: {
                    invoice_name: frm.doc.name,
                    accounts: cuentas_registradas
                },
                // El callback se ejecuta tras finalizar la ejecucion del script python del lado
                // del servidor
                callback: function () {
                    // Busca la modalidad configurada, ya sea Manual o Automatica
                    // Esto para mostrar u ocultar los botones para la geneneracion de factura
                    // electronica
                    frappe.call({
                        method: "factura_electronica.api.obtenerConfiguracionManualAutomatica",
                        callback: function (data) {
                            console.log(data.message);
                            if (data.message === 'Manual') {
                                console.log('Configuracion encontrada: MANUAL');
                                // No es necesario tener activa esta parte, ya que cuando se ingresa a cualquier factura en el evento
                                // refresh, hay una funcion que se encarga de comprobar de que se haya generado exitosamente la
                                // factura electronica, en caso no sea asi, se mostrarán los botones correspondientes, para hacer
                                // la generacion de la factura electronica manualmente.
                                // generarFacturaBTN(frm, cdt, cdn);
                            }
                            if (data.message === 'Automatico') {
                                console.log('Configuracion encontrada: AUTOMATICO');
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
                    console.log(data.message);
                    if (data.message === 'Manual') {
                        console.log('Configuracion encontrada: MANUAL');
                        /* No es necesario tener activa esta parte, ya que cuando se ingresa a cualquier factura en el evento
                        refresh, hay una funcion que se encarga de comprobar de que se haya generado exitosamente la
                        factura electronica, en caso no sea asi, se mostrarán los botones correspondientes, para hacer
                        la generacion de la factura electronica manualmente.
                        generarFacturaBTN(frm, cdt, cdn); */
                    }
                    if (data.message === 'Automatico') {
                        console.log('Configuracion encontrada: AUTOMATICO');
                        // generarFacturaSINBTN(frm, cdt, cdn);
                        verificacionCAE('automatico', frm, cdt, cdn);
                    }
                }
            });
        }

    }
});

frappe.ui.form.on("Sales Invoice Item", {
    items_add: function (frm, cdt, cdn) {},
    items_move: function (frm, cdt, cdn) {},
    before_items_remove: function (frm, cdt, cdn) {
        // totalizar_valores(frm, cdn);
        frm.doc.items.forEach((item_row_1, index_1) => {
            if (item_row_1.name == cdn) {
                console.log('La Fila a Eliminar es --------------> ' + item_row_1.item_code);
                var numero = facelec_add_taxes(frm, item_row_1.facelec_p_tax_rate_per_uom_account);
                console.log(numero);
            }
            // if (item_row_1.account_head) {
            //     // console.log('------------------------> ');
            //     frm.doc.items.forEach((tax_row_2, index_2) => {

            //         if (tax_row_2.facelec_tax_rate_per_uom_account === item_row_1.account_head) {
            //             console.log('------------------------> ');
            //             let totalizador = 0;

            //             console.log('La cuenta a eliminar es ------------> ' + tax_row_2.facelec_tax_rate_per_uom_account);
            //             totalizador = facelec_add_taxes(frm, tax_row_2.facelec_tax_rate_per_uom_account);
            //             console.log('El valor del totalizador es ------------ > ' + totalizador);
            //             // frm.doc.shs_otros_impuestos[index_1].total = totalizador;

            //             // cur_frm.refresh_field("shs_otros_impuestos");
            //             // shs_total_other_tax(frm);

            //             // cur_frm.refresh_field("shs_otros_impuestos");
            //         }

            //     });
            // }

        });
    },
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // console.log('Trigger remove en tabla hija');

        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.
        fix_gt_tax_fuel = 0;
        fix_gt_tax_goods = 0;
        fix_gt_tax_services = 0;
        fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function (i, d) {
            fix_gt_tax_fuel += flt(d.facelec_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.facelec_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.facelec_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.facelec_sales_tax_for_this_row);
        });

        cur_frm.set_value("facelec_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("facelec_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("facelec_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("facelec_total_iva", fix_gt_tax_iva);

        // totalizar_valores(frm, cdn);
    },
    item_code: function (frm, cdt, cdn) {
        each_item(frm, cdt, cdn);
        //facelec_tax_calc_new(frm, cdt, cdn);
    },
    qty: function (frm, cdt, cdn) {
        //facelec_tax_calculation(frm, cdt, cdn);
        facelec_tax_calc_new(frm, cdt, cdn);
        console.log("cdt contains: " + cdt);
        console.log("cdn contains: " + cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        console.log("El disparador de factor de conversión se corrió.");
        facelec_tax_calc_new(frm, cdt, cdn);
    },
    facelec_tax_rate_per_uom_account: function (frm, cdt, cdn) {
        //facelec_otros_impuestos_fila(frm, cdt,cdn);
        // esto debe correr aqui?
    },
    rate: function (frm, cdt, cdn) {
        facelec_tax_calc_new(frm, cdt, cdn);
    },
    /*onload_post_render: function(frm, cdt, cdn){
		console.log('Funcionando Onload Post Render Trigger'); //SI FUNCIONA EL TRIGGER
    }*/
});

/* Factura de Compra ------------------------------------------------------------------------------------------------ */
frappe.ui.form.on("Purchase Invoice", {
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        console.log('Exito Script In Purchase Invoice');
        // Boton para recalcular
        frm.add_custom_button("UOM Recalculation", function () {
            frm.doc.items.forEach((item) => {
                // for each button press each line is being processed.
                console.log("item contains: " + item);
                //Importante
                shs_purchase_invoice_calculation(frm, "Purchase Invoice Item", item.name);
            });
        });
    },
    facelec_nit_fproveedor: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.facelec_nit_fproveedor, frm.doc.supplier, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        tax_before_calc = frm.doc.facelec_p_total_iva;
        console.log("El descuento total es:" + frm.doc.discount_amount);
        console.log("El IVA calculado anteriormente:" + frm.doc.facelec_p_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        console.log("El neto sin iva del descuento es" + discount_amount_net_value);
        discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
        console.log("El IVA del descuento es:" + discount_amount_tax_value);
        frm.doc.facelec_p_total_iva = (frm.doc.facelec_p_total_iva - discount_amount_tax_value);
        console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_p_total_iva);
    },
    supplier: function (frm, cdt, cdn) {
        // Trigger Proveedor
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log('Corrio supplier trigger y se cargo el IVA, el cual es ' + this_company_sales_tax_var);
    },
    before_save: function (frm, cdt, cdn) {
        // Trigger antes de guardar
        frm.doc.items.forEach((item) => {
            // for each button press each line is being processed.
            console.log("item contains: " + item);
            //Importante
            shs_purchase_invoice_calculation(frm, "Purchase Invoice Item", item.name);
            tax_before_calc = frm.doc.facelec_p_total_iva;
            console.log("El descuento total es:" + frm.doc.discount_amount);
            console.log("El IVA calculado anteriormente:" + frm.doc.facelec_p_total_iva);
            discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
            console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_p_total_iva = (frm.doc.facelec_p_total_iva - discount_amount_tax_value);
            console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_p_total_iva);
        });
    },
});

frappe.ui.form.on("Purchase Invoice Item", {
    items_add: function (frm, cdt, cdn) {},
    items_move: function (frm, cdt, cdn) {},
    before_items_remove: function (frm, cdt, cdn) {},
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.
        fix_gt_tax_fuel = 0;
        fix_gt_tax_goods = 0;
        fix_gt_tax_services = 0;
        fix_gt_tax_iva = 0;

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
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_purchase_invoice_calculation(frm, cdt, cdn);
        console.log("cdt contains: " + cdt);
        console.log("cdn contains: " + cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        console.log("El disparador de factor de conversión se corrió.");
        shs_purchase_invoice_calculation(frm, cdt, cdn);
    },
    facelec_p_tax_rate_per_uom_account: function (frm, cdt, cdn) {
        // Eleccion de este trigger para la adicion de filas en taxes con sus respectivos valores.
        frm.doc.items.forEach((item_row_i, index_i) => {
            if (item_row_i.name == cdn) {
                var cuenta = item_row_i.facelec_p_tax_rate_per_uom_account;
                if (cuenta !== null) {
                    if (buscar_account(frm, cuenta)) {
                        console.log('La cuenta de impuestos y cargos ya existe en la tabla Taxes and Charges');
                    } else {
                        console.log('La cuenta de impuestos y cargos no existe, se agregara una nueva fila en Taxes and Charges');
                        frappe.model.add_child(frm.doc, "Sales Taxes and Charges", "taxes");
                        frm.doc.taxes.forEach((item_row, index) => {
                            if (item_row.account_head == undefined) {
                                frappe.call({
                                    method: "factura_electronica.api.get_data_tax_account",
                                    args: {
                                        name_account_tax_gt: cuenta
                                    },
                                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                                    callback: function (data) {
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
                    console.log('El producto seleccionado no tiene una cuenta asociada');
                }
            }
        });
    },
    rate: function (frm, cdt, cdn) {
        shs_purchase_invoice_calculation(frm, cdt, cdn);
    }
});

/* Cotizacion ------------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Quotation", {
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        console.log('Exito Script In Quotation');
        // Boton para recalcular
        frm.add_custom_button("UOM Recalculation", function () {
            frm.doc.items.forEach((item) => {
                // for each button press each line is being processed.
                console.log("item contains: " + item);
                //Importante
                shs_quotation_calculation(frm, "Quotation Item", item.name);
            });
        });
    },
    facelec_qt_nit: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.facelec_qt_nit, frm.doc.customer, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        tax_before_calc = frm.doc.facelec_qt_total_iva;
        console.log("El descuento total es:" + frm.doc.discount_amount);
        console.log("El IVA calculado anteriormente:" + frm.doc.facelec_qt_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        console.log("El neto sin iva del descuento es" + discount_amount_net_value);
        discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
        console.log("El IVA del descuento es:" + discount_amount_tax_value);
        frm.doc.facelec_qt_total_iva = (frm.doc.facelec_qt_total_iva - discount_amount_tax_value);
        console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_qt_total_iva);
    },
    customer: function (frm, cdt, cdn) {
        // Trigger Proveedor
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log('Corrio customer trigger y se cargo el IVA, el cual es ' + this_company_sales_tax_var);
    },
    before_save: function (frm, cdt, cdn) {
        // Trigger antes de guardar
        frm.doc.items.forEach((item) => {
            // for each button press each line is being processed.
            console.log("item contains: " + item);
            //Importante
            shs_quotation_calculation(frm, "Quotation Item", item.name);
            tax_before_calc = frm.doc.facelec_qt_total_iva;
            console.log("El descuento total es:" + frm.doc.discount_amount);
            console.log("El IVA calculado anteriormente:" + frm.doc.facelec_qt_total_iva);
            discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
            console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_qt_total_iva = (frm.doc.facelec_qt_total_iva - discount_amount_tax_value);
            console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_qt_total_iva);
        });
    },
});

frappe.ui.form.on("Quotation Item", {
    items_add: function (frm, cdt, cdn) {},
    items_move: function (frm, cdt, cdn) {},
    before_items_remove: function (frm, cdt, cdn) {},
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.
        fix_gt_tax_fuel = 0;
        fix_gt_tax_goods = 0;
        fix_gt_tax_services = 0;
        fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function (i, d) {
            fix_gt_tax_fuel += flt(d.facelec_qt_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.facelec_qt_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.facelec_qt_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.facelec_qt_sales_tax_for_this_row);
        });

        cur_frm.set_value("facelec_qt_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("facelec_qt_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("facelec_qt_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("facelec_qt_total_iva", fix_gt_tax_iva);
    },
    item_code: function (frm, cdt, cdn) {
        // Trigger codigo de producto
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_quotation_calculation(frm, cdt, cdn);
        console.log("cdt contains: " + cdt);
        console.log("cdn contains: " + cdn);
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
    facelec_qt_tax_rate_per_uom_account: function (frm, cdt, cdn) {
        // Eleccion de este trigger para la adicion de filas en taxes con sus respectivos valores.
        frm.doc.items.forEach((item_row_i, index_i) => {
            if (item_row_i.name == cdn) {
                var cuenta = item_row_i.facelec_qt_tax_rate_per_uom_account;
                if (cuenta !== null) {
                    if (buscar_account(frm, cuenta)) {
                        console.log('La cuenta de impuestos y cargos ya existe en la tabla Taxes and Charges');
                    } else {
                        console.log('La cuenta no existe, se agregara una nueva fila en taxes');
                        frappe.model.add_child(frm.doc, "Sales Taxes and Charges", "taxes");
                        frm.doc.taxes.forEach((item_row, index) => {
                            if (item_row.account_head == undefined) {
                                frappe.call({
                                    method: "factura_electronica.api.get_data_tax_account",
                                    args: {
                                        name_account_tax_gt: cuenta
                                    },
                                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                                    callback: function (data) {
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
    rate: function (frm, cdt, cdn) {
        shs_quotation_calculation(frm, cdt, cdn);
    }
});

/* Orden de Compra -------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Purchase Order", {
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        console.log('Exito Script In Purchase Order');
        // Boton para recalcular
        frm.add_custom_button("UOM Recalculation", function () {
            frm.doc.items.forEach((item) => {
                // for each button press each line is being processed.
                console.log("item contains: " + item);
                //Importante
                shs_purchase_order_calculation(frm, "Purchase Order Item", item.name);
            });
        });
    },
    facelec_po_nit: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.facelec_po_nit, frm.doc.supplier, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        tax_before_calc = frm.doc.facelec_po_total_iva;
        console.log("El descuento total es:" + frm.doc.discount_amount);
        console.log("El IVA calculado anteriormente:" + frm.doc.facelec_po_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        console.log("El neto sin iva del descuento es" + discount_amount_net_value);
        discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
        console.log("El IVA del descuento es:" + discount_amount_tax_value);
        frm.doc.facelec_po_total_iva = (frm.doc.facelec_po_total_iva - discount_amount_tax_value);
        console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_po_total_iva);
    },
    supplier: function (frm, cdt, cdn) {
        // Trigger Proveedor
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log('Corrio supplier trigger y se cargo el IVA, el cual es ' + this_company_sales_tax_var);
    },
    before_save: function (frm, cdt, cdn) {
        // Trigger antes de guardar
        frm.doc.items.forEach((item) => {
            // for each button press each line is being processed.
            console.log("item contains: " + item);
            //Importante
            shs_purchase_order_calculation(frm, "Purchase Order Item", item.name);
            tax_before_calc = frm.doc.facelec_po_total_iva;
            console.log("El descuento total es:" + frm.doc.discount_amount);
            console.log("El IVA calculado anteriormente:" + frm.doc.facelec_po_total_iva);
            discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
            console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_po_total_iva = (frm.doc.facelec_po_total_iva - discount_amount_tax_value);
            console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_po_total_iva);
        });
    },
});

frappe.ui.form.on("Purchase Order Item", {
    items_add: function (frm, cdt, cdn) {},
    items_move: function (frm, cdt, cdn) {},
    before_items_remove: function (frm, cdt, cdn) {},
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.
        fix_gt_tax_fuel = 0;
        fix_gt_tax_goods = 0;
        fix_gt_tax_services = 0;
        fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function (i, d) {
            fix_gt_tax_fuel += flt(d.facelec_po_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.facelec_po_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.facelec_po_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.facelec_po_sales_tax_for_this_row);
        });

        cur_frm.set_value("facelec_po_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("facelec_po_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("facelec_po_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("facelec_po_total_iva", fix_gt_tax_iva);
    },
    item_code: function (frm, cdt, cdn) {
        // Trigger codigo de producto
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_purchase_order_calculation(frm, cdt, cdn);
        console.log("cdt contains: " + cdt);
        console.log("cdn contains: " + cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        console.log("El disparador de factor de conversión se corrió.");
        shs_purchase_order_calculation(frm, cdt, cdn);
    },
    facelec_po_tax_rate_per_uom_account: function (frm, cdt, cdn) {
        // Eleccion de este trigger para la adicion de filas en taxes con sus respectivos valores.
        frm.doc.items.forEach((item_row_i, index_i) => {
            if (item_row_i.name == cdn) {
                var cuenta = item_row_i.facelec_po_tax_rate_per_uom_account;
                if (cuenta !== null) {
                    if (buscar_account(frm, cuenta)) {
                        console.log('La cuenta de impuestos y cargos ya existe en la tabla Taxes and Charges');
                    } else {
                        console.log('La cuenta no existe, se agregara una nueva fila en taxes');
                        frappe.model.add_child(frm.doc, "Sales Taxes and Charges", "taxes");
                        frm.doc.taxes.forEach((item_row, index) => {
                            if (item_row.account_head == undefined) {
                                frappe.call({
                                    method: "factura_electronica.api.get_data_tax_account",
                                    args: {
                                        name_account_tax_gt: cuenta
                                    },
                                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                                    callback: function (data) {
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
                    console.log('El producto seleccionado no tiene una cuenta asociada');
                }
            }
        });
    },
    rate: function (frm, cdt, cdn) {
        shs_purchase_order_calculation(frm, cdt, cdn);
    }
});

/* Recibo de compra ------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Purchase Receipt", {
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        console.log('Exito Script In Purchase Receipt');
        // Boton para recalcular
        frm.add_custom_button("UOM Recalculation", function () {
            frm.doc.items.forEach((item) => {
                // for each button press each line is being processed.
                console.log("item contains: " + item);
                //Importante
                shs_purchase_receipt_calculation(frm, "Purchase Receipt Item", item.name);
            });
        });
    },
    facelec_nit_prproveedor: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.facelec_nit_prproveedor, frm.doc.supplier, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        tax_before_calc = frm.doc.facelec_pr_total_iva;
        console.log("El descuento total es:" + frm.doc.discount_amount);
        console.log("El IVA calculado anteriormente:" + frm.doc.facelec_pr_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        console.log("El neto sin iva del descuento es" + discount_amount_net_value);
        discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
        console.log("El IVA del descuento es:" + discount_amount_tax_value);
        frm.doc.facelec_pr_total_iva = (frm.doc.facelec_pr_total_iva - discount_amount_tax_value);
        console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_pr_total_iva);
    },
    supplier: function (frm, cdt, cdn) {
        // Trigger Proveedor
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log('Corrio supplier trigger y se cargo el IVA, el cual es ' + this_company_sales_tax_var);
    },
    before_save: function (frm, cdt, cdn) {
        // Trigger antes de guardar
        frm.doc.items.forEach((item) => {
            // for each button press each line is being processed.
            console.log("item contains: " + item);
            //Importante
            shs_purchase_receipt_calculation(frm, "Purchase Receipt Item", item.name);
            tax_before_calc = frm.doc.facelec_pr_total_iva;
            console.log("El descuento total es:" + frm.doc.discount_amount);
            console.log("El IVA calculado anteriormente:" + frm.doc.facelec_pr_total_iva);
            discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
            console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.facelec_pr_total_iva = (frm.doc.facelec_pr_total_iva - discount_amount_tax_value);
            console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_pr_total_iva);
        });
    },
});

frappe.ui.form.on("Purchase Receipt Item", {
    items_add: function (frm, cdt, cdn) {},
    items_move: function (frm, cdt, cdn) {},
    before_items_remove: function (frm, cdt, cdn) {},
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.
        fix_gt_tax_fuel = 0;
        fix_gt_tax_goods = 0;
        fix_gt_tax_services = 0;
        fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function (i, d) {
            fix_gt_tax_fuel += flt(d.facelec_pr_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.facelec_pr_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.facelec_pr_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.facelec_pr_sales_tax_for_this_row);
        });

        cur_frm.set_value("facelec_pr_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("facelec_pr_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("facelec_pr_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("facelec_pr_total_iva", fix_gt_tax_iva);
    },
    item_code: function (frm, cdt, cdn) {
        // Trigger codigo de producto
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_purchase_receipt_calculation(frm, cdt, cdn);
        console.log("cdt contains: " + cdt);
        console.log("cdn contains: " + cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        console.log("El disparador de factor de conversión se corrió.");
        shs_purchase_order_calculation(frm, cdt, cdn);
    },
    facelec_pr_tax_rate_per_uom_account: function (frm, cdt, cdn) {
        // Eleccion de este trigger para la adicion de filas en taxes con sus respectivos valores.
        frm.doc.items.forEach((item_row_i, index_i) => {
            if (item_row_i.name == cdn) {
                var cuenta = item_row_i.facelec_pr_tax_rate_per_uom_account;
                if (cuenta !== null) {
                    if (buscar_account(frm, cuenta)) {
                        console.log('La cuenta de impuestos y cargos ya existe en la tabla Taxes and Charges');
                    } else {
                        console.log('La cuenta no existe, se agregara una nueva fila en taxes');
                        frappe.model.add_child(frm.doc, "Sales Taxes and Charges", "taxes");
                        frm.doc.taxes.forEach((item_row, index) => {
                            if (item_row.account_head == undefined) {
                                frappe.call({
                                    method: "factura_electronica.api.get_data_tax_account",
                                    args: {
                                        name_account_tax_gt: cuenta
                                    },
                                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                                    callback: function (data) {
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
                    console.log('El producto seleccionado no tiene una cuenta asociada');
                }
            }
        });
    },
    rate: function (frm, cdt, cdn) {
        shs_purchase_receipt_calculation(frm, cdt, cdn);
    }
});

/* Orden de Venta ------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Sales Order", {
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        console.log('Exito Script In Sales Order');
        // Boton para recalcular
        frm.add_custom_button("UOM Recalculation", function () {
            frm.doc.items.forEach((item) => {
                // for each button press each line is being processed.
                console.log("item contains: " + item);
                //Importante
                shs_sales_order_calculation(frm, "Sales Order Item", item.name);
            });
        });
    },
    shs_so_nit: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.shs_so_nit, frm.doc.customer, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        tax_before_calc = frm.doc.shs_so_total_iva;
        console.log("El descuento total es:" + frm.doc.discount_amount);
        console.log("El IVA calculado anteriormente:" + frm.doc.shs_so_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        console.log("El neto sin iva del descuento es" + discount_amount_net_value);
        discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
        console.log("El IVA del descuento es:" + discount_amount_tax_value);
        frm.doc.shs_so_total_iva = (frm.doc.shs_so_total_iva - discount_amount_tax_value);
        console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.shs_so_total_iva);
    },
    customer: function (frm, cdt, cdn) {
        // Trigger Proveedor
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log('Corrio supplier trigger y se cargo el IVA, el cual es ' + this_company_sales_tax_var);
    },
    before_save: function (frm, cdt, cdn) {
        // Trigger antes de guardar
        frm.doc.items.forEach((item) => {
            // for each button press each line is being processed.
            console.log("item contains: " + item);
            //Importante
            shs_sales_order_calculation(frm, "Sales Order Item", item.name);
            tax_before_calc = frm.doc.shs_so_total_iva;
            console.log("El descuento total es:" + frm.doc.discount_amount);
            console.log("El IVA calculado anteriormente:" + frm.doc.shs_so_total_iva);
            discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
            console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.shs_so_total_iva = (frm.doc.shs_so_total_iva - discount_amount_tax_value);
            console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.shs_so_total_iva);
        });
    },
});

frappe.ui.form.on("Sales Order Item", {
    items_add: function (frm, cdt, cdn) {},
    items_move: function (frm, cdt, cdn) {},
    before_items_remove: function (frm, cdt, cdn) {},
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.
        fix_gt_tax_fuel = 0;
        fix_gt_tax_goods = 0;
        fix_gt_tax_services = 0;
        fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function (i, d) {
            fix_gt_tax_fuel += flt(d.shs_so_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.shs_so_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.shs_so_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.shs_so_sales_tax_for_this_row);
        });

        cur_frm.set_value("shs_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("shs_so_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("shs_so_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("shs_so_total_iva", fix_gt_tax_iva);
    },
    item_code: function (frm, cdt, cdn) {
        // Trigger codigo de producto
        // cur_frm.add_fetch("item_code", "facelec_three_digit_uom", "shs_so_facelec_three_digit_uom_code");
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_sales_order_calculation(frm, cdt, cdn);
        console.log("cdt contains: " + cdt);
        console.log("cdn contains: " + cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        console.log("El disparador de factor de conversión se corrió.");
        shs_sales_order_calculation(frm, cdt, cdn);
    },
    shs_so_tax_rate_per_uom_account: function (frm, cdt, cdn) {
        // Eleccion de este trigger para la adicion de filas en taxes con sus respectivos valores.
        frm.doc.items.forEach((item_row_i, index_i) => {
            if (item_row_i.name == cdn) {
                var cuenta = item_row_i.shs_so_tax_rate_per_uom_account;
                if (cuenta !== null) {
                    if (buscar_account(frm, cuenta)) {
                        console.log('La cuenta de impuestos y cargos ya existe en la tabla Taxes and Charges');
                    } else {
                        console.log('La cuenta no existe, se agregara una nueva fila en taxes');
                        frappe.model.add_child(frm.doc, "Sales Taxes and Charges", "taxes");
                        frm.doc.taxes.forEach((item_row, index) => {
                            if (item_row.account_head == undefined) {
                                frappe.call({
                                    method: "factura_electronica.api.get_data_tax_account",
                                    args: {
                                        name_account_tax_gt: cuenta
                                    },
                                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                                    callback: function (data) {
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
                    console.log('El producto seleccionado no tiene una cuenta asociada');
                }
            }
        });
    },
    rate: function (frm, cdt, cdn) {
        shs_sales_order_calculation(frm, cdt, cdn);
    }
});

/* Nota de Entrega ------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Delivery Note", {
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        console.log('Exito Script In Delivery Note');
        // Boton para recalcular
        frm.add_custom_button("UOM Recalculation", function () {
            frm.doc.items.forEach((item) => {
                // for each button press each line is being processed.
                console.log("item contains: " + item);
                //Importante
                shs_delivery_note_calculation(frm, "Delivery Note Item", item.name);
            });
        });
    },
    shs_dn_nit: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.shs_dn_nit, frm.doc.customer, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        tax_before_calc = frm.doc.shs_dn_total_iva;
        console.log("El descuento total es:" + frm.doc.discount_amount);
        console.log("El IVA calculado anteriormente:" + frm.doc.shs_dn_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        console.log("El neto sin iva del descuento es" + discount_amount_net_value);
        discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
        console.log("El IVA del descuento es:" + discount_amount_tax_value);
        frm.doc.shs_dn_total_iva = (frm.doc.shs_dn_total_iva - discount_amount_tax_value);
        console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.shs_dn_total_iva);
    },
    customer: function (frm, cdt, cdn) {
        // Trigger Proveedor
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log('Corrio customer trigger y se cargo el IVA, el cual es ' + this_company_sales_tax_var);
    },
    before_save: function (frm, cdt, cdn) {
        // Trigger antes de guardar
        frm.doc.items.forEach((item) => {
            // for each button press each line is being processed.
            console.log("item contains: " + item);
            //Importante
            shs_delivery_note_calculation(frm, "Delivery Note Item", item.name);
            tax_before_calc = frm.doc.shs_dn_total_iva;
            console.log("El descuento total es:" + frm.doc.discount_amount);
            console.log("El IVA calculado anteriormente:" + frm.doc.shs_dn_total_iva);
            discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
            console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.shs_dn_total_iva = (frm.doc.shs_dn_total_iva - discount_amount_tax_value);
            console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.shs_dn_total_iva);
        });
    },
});

frappe.ui.form.on("Delivery Note Item", {
    items_add: function (frm, cdt, cdn) {},
    items_move: function (frm, cdt, cdn) {},
    before_items_remove: function (frm, cdt, cdn) {},
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.
        fix_gt_tax_fuel = 0;
        fix_gt_tax_goods = 0;
        fix_gt_tax_services = 0;
        fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function (i, d) {
            fix_gt_tax_fuel += flt(d.shs_dn_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.shs_dn_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.shs_dn_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.shs_dn_sales_tax_for_this_row);
        });

        cur_frm.set_value("shs_dn_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("shs_dn_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("shs_dn_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("shs_dn_total_iva", fix_gt_tax_iva);
    },
    item_code: function (frm, cdt, cdn) {
        // Trigger codigo de producto
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_delivery_note_calculation(frm, cdt, cdn);
        console.log("cdt contains: " + cdt);
        console.log("cdn contains: " + cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        console.log("El disparador de factor de conversión se corrió.");
        shs_delivery_note_calculation(frm, cdt, cdn);
    },
    shs_dn_tax_rate_per_uom_account: function (frm, cdt, cdn) {
        // Eleccion de este trigger para la adicion de filas en taxes con sus respectivos valores.
        frm.doc.items.forEach((item_row_i, index_i) => {
            if (item_row_i.name == cdn) {
                var cuenta = item_row_i.shs_dn_tax_rate_per_uom_account;
                if (cuenta !== null) {
                    if (buscar_account(frm, cuenta)) {
                        console.log('La cuenta de impuestos y cargos ya existe en la tabla Taxes and Charges');
                    } else {
                        console.log('La cuenta no existe, se agregara una nueva fila en taxes');
                        frappe.model.add_child(frm.doc, "Sales Taxes and Charges", "taxes");
                        frm.doc.taxes.forEach((item_row, index) => {
                            if (item_row.account_head == undefined) {
                                frappe.call({
                                    method: "factura_electronica.api.get_data_tax_account",
                                    args: {
                                        name_account_tax_gt: cuenta
                                    },
                                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                                    callback: function (data) {
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
                    console.log('El producto seleccionado no tiene una cuenta asociada');
                }
            }
        });
    },
    rate: function (frm, cdt, cdn) {
        shs_delivery_note_calculation(frm, cdt, cdn);
    }
});

/* Cotizacion del proveedor ---------------------------------------------------------------------------------------- */
frappe.ui.form.on("Supplier Quotation", {
    refresh: function (frm, cdt, cdn) {
        // Trigger refresh de pagina
        console.log('Exito Script In Supplier Quotation');
        // Boton para recalcular
        frm.add_custom_button("UOM Recalculation", function () {
            frm.doc.items.forEach((item) => {
                // for each button press each line is being processed.
                console.log("item contains: " + item);
                //Importante
                shs_supplier_quotation_calculation(frm, "Supplier Quotation Item", item.name);
            });
        });
    },
    shs_spq_nit: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.shs_spq_nit, frm.doc.supplier, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        tax_before_calc = frm.doc.shs_spq_total_iva;
        console.log("El descuento total es:" + frm.doc.discount_amount);
        console.log("El IVA calculado anteriormente:" + frm.doc.shs_spq_total_iva);
        discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
        console.log("El neto sin iva del descuento es" + discount_amount_net_value);
        discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
        console.log("El IVA del descuento es:" + discount_amount_tax_value);
        frm.doc.shs_spq_total_iva = (frm.doc.shs_spq_total_iva - discount_amount_tax_value);
        console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.shs_spq_total_iva);
    },
    supplier: function (frm, cdt, cdn) {
        // Trigger Proveedor
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log('Corrio customer trigger y se cargo el IVA, el cual es ' + this_company_sales_tax_var);
    },
    before_save: function (frm, cdt, cdn) {
        // Trigger antes de guardar
        frm.doc.items.forEach((item) => {
            // for each button press each line is being processed.
            console.log("item contains: " + item);
            //Importante
            shs_supplier_quotation_calculation(frm, "Supplier Quotation Item", item.name);
            tax_before_calc = frm.doc.shs_spq_total_iva;
            console.log("El descuento total es:" + frm.doc.discount_amount);
            console.log("El IVA calculado anteriormente:" + frm.doc.shs_spq_total_iva);
            discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));
            console.log("El neto sin iva del descuento es" + discount_amount_net_value);
            discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
            console.log("El IVA del descuento es:" + discount_amount_tax_value);
            frm.doc.shs_spq_total_iva = (frm.doc.shs_spq_total_iva - discount_amount_tax_value);
            console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.shs_spq_total_iva);
        });
    },
    onload: function (frm, cdt, cdn) {
        // console.log('Funcionando Onload Trigger'); SI FUNCIONA EL TRIGGER
        // Funciona unicamente cuando se carga por primera vez el documento y aplica unicamente para el form y no childtables
    },
});

frappe.ui.form.on("Supplier Quotation Item", {
    items_add: function (frm, cdt, cdn) {},
    items_move: function (frm, cdt, cdn) {},
    before_items_remove: function (frm, cdt, cdn) {},
    items_remove: function (frm, cdt, cdn) {
        // es-GT: Este disparador corre al momento de eliminar una nueva fila.
        // en-US: This trigger runs when removing a row.
        // Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA cuando se elimina una fila.
        fix_gt_tax_fuel = 0;
        fix_gt_tax_goods = 0;
        fix_gt_tax_services = 0;
        fix_gt_tax_iva = 0;

        $.each(frm.doc.items || [], function (i, d) {
            fix_gt_tax_fuel += flt(d.shs_spq_gt_tax_net_fuel_amt);
            fix_gt_tax_goods += flt(d.shs_spq_gt_tax_net_goods_amt);
            fix_gt_tax_services += flt(d.shs_spq_gt_tax_net_services_amt);
            fix_gt_tax_iva += flt(d.shs_spq_sales_tax_for_this_row);
        });

        cur_frm.set_value("shs_spq_gt_tax_fuel", fix_gt_tax_fuel);
        cur_frm.set_value("shs_spq_gt_tax_goods", fix_gt_tax_goods);
        cur_frm.set_value("shs_spq_gt_tax_services", fix_gt_tax_services);
        cur_frm.set_value("shs_spq_total_iva", fix_gt_tax_iva);
    },
    item_code: function (frm, cdt, cdn) {

        // Trigger codigo de producto
        this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');

    },
    qty: function (frm, cdt, cdn) {
        // Trigger cantidad
        shs_supplier_quotation_calculation(frm, cdt, cdn);
        console.log("cdt contains: " + cdt);
        console.log("cdn contains: " + cdn);
    },
    uom: function (frm, cdt, cdn) {
        // Trigger UOM
        console.log("The unit of measure field was changed and the code from the trigger was run");
    },
    conversion_factor: function (frm, cdt, cdn) {
        // Trigger factor de conversion
        console.log("El disparador de factor de conversión se corrió.");
        shs_supplier_quotation_calculation(frm, cdt, cdn);
    },
    shs_spq_tax_rate_per_uom_account: function (frm, cdt, cdn) {
        // Eleccion de este trigger para la adicion de filas en taxes con sus respectivos valores.
        frm.doc.items.forEach((item_row_i, index_i) => {
            if (item_row_i.name == cdn) {
                var cuenta = item_row_i.shs_spq_tax_rate_per_uom_account;
                if (cuenta !== null) {
                    if (buscar_account(frm, cuenta)) {
                        console.log('La cuenta de impuestos y cargos ya existe en la tabla Taxes and Charges');
                    } else {
                        console.log('La cuenta no existe, se agregara una nueva fila en taxes');
                        frappe.model.add_child(frm.doc, "Sales Taxes and Charges", "taxes");
                        frm.doc.taxes.forEach((item_row, index) => {
                            if (item_row.account_head == undefined) {
                                frappe.call({
                                    method: "factura_electronica.api.get_data_tax_account",
                                    args: {
                                        name_account_tax_gt: cuenta
                                    },
                                    // El callback recibe como parametro el dato retornado por script python del lado del servidor
                                    callback: function (data) {
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
                    console.log('El producto seleccionado no tiene una cuenta asociada');
                }
            }
        });
    },
    rate: function (frm, cdt, cdn) {
        shs_supplier_quotation_calculation(frm, cdt, cdn);
    }
});

/* ----------------------------------------------------------------------------------------------------------------- */
/** Verificacion para que exista un solo check */
frappe.ui.form.on("Item", {
    facelec_is_fuel: function (frm, cdt, cdn) {
        if (frm.doc.facelec_is_fuel) {
            cur_frm.set_value("facelec_is_good", 0);
            cur_frm.set_value("facelec_is_service", 0);
        }
    },
    facelec_is_good: function (frm, cdt, cdn) {
        if (frm.doc.facelec_is_good) {
            cur_frm.set_value("facelec_is_fuel", 0);
            cur_frm.set_value("facelec_is_service", 0);
        }
    },
    facelec_is_service: function (frm, cdt, cdn) {
        if (frm.doc.facelec_is_service) {
            cur_frm.set_value("facelec_is_fuel", 0);
            cur_frm.set_value("facelec_is_good", 0);
        }
    }
});