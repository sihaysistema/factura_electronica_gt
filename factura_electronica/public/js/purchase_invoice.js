import { valNit } from './facelec.js';
import { goalSeek } from './goalSeek.js';

//console.log("Hello world from Purchase Invoice");

/* Purchase Invoice (Factura de Compra) ------------------------------------------------------------------------------------------------------- */
function pi_each_item(frm, cdt, cdn) {
    frm.doc.items.forEach((item) => {
        shs_purchase_invoice_calculation(frm, "Purchase Invoice Item", item.name);
        pi_insertar_fila_otro_impuesto(frm, "Purchase Invoice Item", item.name);
    });
}

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
* Parametros:
* #1 frm = formulario que se esta trabajando
* #2 cdt = Doctype
* #3 cdn = Docname
*
* Funcionamiento:
* Recorre la tabla items, por cada item encontrado, si tiene una cuenta asignada,
* recorrera la tabla hija shs_pi_otros_impuestos en busca de items con el mismo nombre
* de cuenta anteriormente encontrado, para totalizar el valor del impuestos, para todos
* los items con la misma cuenta.
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
* Parametros:
* #1 frm = formulario que se esta trabajando
*
* Funcionamiento:
* Recorre la tabla hija shs_pi_otros_impuestos, realiza sumatoria de todos las filas
* que tenga una cuenta, el valor totalizado se asigna al campo shs_total_otros_imp_incl
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
* Parametros:
* #1 frm = formulario que se esta trabajando
* #2 cdt = Doctype
* #3 cdn = Docname
*
* Funcionamiento:
* Recorre la tabla items, por cada fila con una cuenta asignada buscara en la tabla hija
* shs_pi_otros_impuestos por una fila con el mismo nombre de la cuenta anteriormente encontrada,
* si no la encuentra en shs_pi_otros_impuestos creara una nueva fila, y le asignara los valores
* de nombre de cuenta y el total para esa cuenta. Si la cuenta ya se encuentra creada en
* shs_pi_otros_impuestos le sumara los valores encontrados.
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
* Se encarga de recalcular el total de otros impuestos cuando se elimina un item
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
* Funcionamiento: recibe como parametro frm, y cuenta_b, lo que hace es, buscar en todas las filas de taxes
* si existe ya una cuenta con el nombre de la cuenta recibida por parametro, en caso ya exista esa cuenta en
* la tabla no hace nada, pero si encuentra que no hay una cuenta igual a la recibida en el parametro, entonces
* la funcion encargada agregara una nueva fila con los datos correspondientes, esta funcion retorna true
* en caso si encuentre una cuenta existente
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

// Calculos para Factura de Compra
function shs_purchase_invoice_calculation(frm, cdt, cdn) {
    cur_frm.refresh_fields();
    var this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;

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

            frm.doc.items[index].facelec_p_other_tax_amount = ((item_row.facelec_p_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor)));
            //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
            frm.doc.items[index].facelec_p_amount_minus_excise_tax = ((item_row.qty * item_row.rate) - ((item_row.qty * item_row.conversion_factor) * item_row.facelec_p_tax_rate_per_uom));

            if (item_row.facelec_p_is_fuel) {
                frm.doc.items[index].facelec_p_gt_tax_net_fuel_amt = (item_row.facelec_p_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_p_sales_tax_for_this_row = (item_row.facelec_p_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
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
                frm.doc.items[index].facelec_p_gt_tax_net_goods_amt = (item_row.facelec_p_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_p_sales_tax_for_this_row = (item_row.facelec_p_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
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
                frm.doc.items[index].facelec_p_gt_tax_net_services_amt = (item_row.facelec_p_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
                frm.doc.items[index].facelec_p_sales_tax_for_this_row = (item_row.facelec_p_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
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

// Funcion para generar tabla HTML + Jinja
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
        // Por ahora se mostrara solo si la factura de copra se encuentra validada, Factura Especial?
        if (frm.doc.docstatus === 1) {

            cur_frm.page.add_action_item(__("AUTOMATED RETENTION"), function () {
                frappe.msgprint("WORK IN PROGRESS");
            });
            frm.add_custom_button(__("Generate Special Invoice FEL"), function () {
                frappe.confirm(__('Are you sure you want to proceed to generate a Special Invoice?'),
                    () => {
                        frappe.call({
                            method: 'factura_electronica.fel_api.generate_special_invoice',
                            args: {
                                invoice_code: frm.doc.name,
                                naming_series: frm.doc.naming_series
                            },
                            callback: function (r) {
                                console.log(r.message);
                            },
                        });
                    }, () => {
                        // action to perform if No is selected
                        console.log('Selecciono NO')
                    });
            }).addClass("btn-warning");

            cur_frm.page.add_action_item(__("SPECIAL INVOICE"), function () {

                let d = new frappe.ui.Dialog({
                    title: 'New Journal Entry with Withholding Tax',
                    fields: [
                        {
                            label: 'Cost Center',
                            fieldname: 'cost_center',
                            fieldtype: 'Link',
                            options: 'Cost Center',
                            "get_query": function () {
                                return {
                                    filters: { 'company': frm.doc.company }
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
                                    filters: { 'company': frm.doc.company }
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
                                is_iva_ret: 0,
                                is_isr_ret: 0,
                                cost_center: values.cost_center,
                                credit_in_acc_currency: values.credit_in_acc_currency,
                                is_multicurrency: values.is_multicurrency,
                                description: values.description,
                                is_special_inv: 1
                            },
                            callback: function (r) {
                                console.log(r.message);
                                d.hide();
                                frm.refresh()
                            },
                        });
                    }
                });

                d.show();
            });
        }
    },
    onload_post_render: function (frm, cdt, cdn) {
        // Funciona unicamente cuando se carga por primera vez el documento y aplica unicamente para el form y no childtables

        // en-US: Enabling event listeners for child tables
        // es-GT: Habilitando escuchadores de eventos en las tablas hijas del tipo de documento principal
        // No corra KEY UP, KEY PRESS, KEY DOWN en este campo!   NO NO NO NO NONONO
        frm.fields_dict.items.grid.wrapper.on('focusout blur', 'input[data-fieldname="item_code"][data-doctype="Purchase Invoice Item"]', function (e) {
            shs_purchase_invoice_calculation(frm, cdt, cdn);
            pi_each_item(frm, cdt, cdn);
        });

        // frm.fields_dict.items.grid.wrapper.on('click focusout blur', 'input[data-fieldname="shs_amount_for_back_calc"][data-doctype="Purchase Invoice Item"]', function (e) {
        //     shs_purchase_invoice_calculation(frm, cdt, cdn);
        //     pi_each_item(frm, cdt, cdn);
        // });

        // FIXME NO FUNCIONA CON TAB, SOLO HACIENDO CLICK Y ENTER.  Si se presiona TAB, SE BORRA!
		/*frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="item_code"][data-doctype="Sales Invoice Item"]', function(e) {
			console.log("Blurred away from the Item Code Field");
			each_item(frm, cdt, cdn);
			//facelec_tax_calc_new(frm, cdt, cdn);
		});*/
        frm.fields_dict.items.grid.wrapper.on('click', 'input[data-fieldname="uom"][data-doctype="Purchase Invoice Item"]', function (e) {
            pi_each_item(frm, cdt, cdn);
        });

        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="uom"][data-doctype="Purchase Invoice Item"]', function (e) {
            pi_each_item(frm, cdt, cdn);
        });

        // Do not refresh with each_item in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="uom"][data-doctype="Purchase Invoice Item"]', function (e) {
            shs_purchase_invoice_calculation(frm, cdt, cdn);
        });

        // This part might seem counterintuitive, but it is the "next" field in tab order after item code, which helps for a "creative" strategy to update everything after pressing TAB out of the item code field.  FIXME
        frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="item_name"][data-doctype="Purchase Invoice Item"]', function (e) {
            pi_each_item(frm, cdt, cdn);
            pi_insertar_fila_otro_impuesto(frm, cdt, cdn);
        });

        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="qty"][data-doctype="Purchase Invoice Item"]', function (e) {
            pi_each_item(frm, cdt, cdn);
        });

        // Do not refresh with each_item in Mouse leave! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur', 'input[data-fieldname="qty"][data-doctype="Purchase Invoice Item"]', function (e) {
            pi_each_item(frm, cdt, cdn);
            shs_purchase_invoice_calculation(frm, cdt, cdn);
        });

        // DO NOT USE Keyup, ??  FIXME FIXME FIXME FIXME FIXME  este hace calculos bien
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="conversion_factor"][data-doctype="Purchase Invoice Item"]', function (e) {
            //  IMPORTANT! IMPORTANT!  This is the one that gets the calculations correct!
            // Trying to calc first, then refresh, or no refresh at all...
            pi_each_item(frm, cdt, cdn);
            cur_frm.refresh_field("conversion_factor");
        });

        // This specific one is only for keyup events, to recalculate all. Only on blur will it refresh everything!
        // Do not refresh with each_item in Mouse leave OR keyup! just recalculate
        frm.fields_dict.items.grid.wrapper.on('blur focusout', 'input[data-fieldname="conversion_factor"][data-doctype="Purchase Invoice Item"]', function (e) {
            // Trying to calc first, then refresh, or no refresh at all...
            shs_purchase_invoice_calculation(frm, cdt, cdn);
            pi_each_item(frm, cdt, cdn);
            cur_frm.refresh_field("conversion_factor");
        });

        // When mouse leaves the field
        cur_frm.fields_dict.supplier.$input.on("blur focusout", function (evt) {
            shs_purchase_invoice_calculation(frm, cdt, cdn);
        });

        // Mouse clicks over the items field
        cur_frm.fields_dict.items.$wrapper.on("blur", function (evt) {
            pi_each_item(frm, cdt, cdn);
        });

        // Focusout from the field
        cur_frm.fields_dict.taxes_and_charges.$input.on("focusout", function (evt) {
            shs_purchase_invoice_calculation(frm, cdt, cdn);
            pi_insertar_fila_otro_impuesto(frm, cdt, cdn);
        });
    },
    facelec_nit_fproveedor: function (frm, cdt, cdn) {
        // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
        valNit(frm.doc.facelec_nit_fproveedor, frm.doc.supplier, frm);
    },
    discount_amount: function (frm, cdt, cdn) {
        // Trigger Monto de descuento
        var tax_before_calc = frm.doc.facelec_total_iva;;
        // es-GT: Este muestra el IVA que se calculo por medio de nuestra aplicación.
        var discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));

        if (discount_amount_net_value == NaN || discount_amount_net_value == undefined) {
        } else {
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

        // TODO: EN QUE QUEDO ESTO?
        // Si existe por lo menos una cuenta, se ejecuta frappe.call
        // if (Object.keys(cuentas_registradas).length > 0) {
        //     frappe.call({
        //         method: "factura_electronica.utils.special_tax.add_gl_entry_other_special_tax",
        //         args: {
        //             invoice_name: frm.doc.name,
        //             accounts: cuentas_registradas,
        //             invoice_type: "Purchase Invoice"
        //         },
        //         // El callback se ejecuta tras finalizar la ejecucion del script python del lado
        //         // del servidor
        //         callback: function () {
        //             // frm.reload_doc();
        //         }
        //     });
        // }
    },
    naming_series: function (frm, cdt, cdn) {
        // frappe call
        // verifica si la serie es de factura especial
        // si es verdadero
        //obtiene la tabla de purchase taxes and charges
        // borra la existente
        // carga la nueva
        // actualiza un campo read only de tipo chequecito que diga: "Factura Especial"
        console.log(frm.doc.naming_series);

        frappe.call({
            method: "factura_electronica.utils.special_invoice.verificar_existencia_series",
            args: {
                serie: frm.doc.naming_series
            },
            callback: function (r) {
                // frm.reload_doc();
                console.log(r.message);

                if (r.message != 'fail') {
                    // Limpia la tabla hija de Purchase Taxes and Charges
                    cur_frm.clear_table("taxes");
                    cur_frm.refresh_fields();

                    // Asigna el nombre de la plantilla de impuestos a utilizar configurada
                    frm.set_value('taxes_and_charges', r.message[2]);
                    frm.refresh_field("taxes_and_charges");
                }
            }
        });
    }
});

frappe.ui.form.on("Purchase Invoice Item", {
    before_items_remove: function (frm, cdt, cdn) {
        frm.doc.items.forEach((item_row_1, index_1) => {
            if (item_row_1.name == cdn) {
                pi_total_otros_impuestos_eliminacion(frm, item_row_1.facelec_p_tax_rate_per_uom_account, item_row_1.facelec_p_other_tax_amount);
            }
        });
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
        var this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
        // console.log("If you can see this, tax rate variable now exists, and its set to: " + this_company_sales_tax_var);
        refresh_field('qty');
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
            // console.log(row.rate);
            // console.log(row.qty);
            // console.log(row.amount);
            var a = row.rate;
            var b = row.qty;
            var c = row.amount;

            //let test = flt(row.shs_amount_for_back_calc) - flt(c);
            //let testB = test / 2;

            // Usando metodologia GoalSeek.js
            // https://github.com/adam-hanna/goalSeek.js/blob/master/goalSeek.js
            // console.log(goalSeek({
            //     Func: calculo_prueba,
            //     aFuncParams: [b, a],
            //     oFuncArgTarget: {
            //         Position: 0
            //     },
            //     Goal: row.shs_amount_for_back_calc,
            //     Tol: 0.001,
            //     maxIter: 10000
            // }));
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
            console.log(calcu);

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


function redondeo_sales_invoice(a, b) {
    return a * b;
}
/* ----------------------------------------------------------------------------------------------------------------- */