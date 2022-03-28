/**
 * Copyright (c) 2021 Si Hay Sistema and contributors
 * For license information, please see license.txt
 */

import { valNit } from "./facelec.js";

/* Sales Quotation (Cotizacion) ------------------------------------------------------------------------------------------------------- */
function quotation_each_row(frm, cdt, cdn) {
  if (cdt === "Quotation Item") {
    // Si es una especifica fila de items
    qo_get_special_tax_by_item(frm, cdt, cdn);
    shs_quotation_calculation(frm, cdt, cdn);
    qo_get_other_tax(frm, cdt, cdn);

    qo_recalculate_other_taxes(frm);
    qo_shs_total_other_tax(frm);
    qo_shs_total_by_item_type(frm);
  } else {
    // var cdn;
    cdt = "Quotation Item";
    // Si no es una fila especifica, se iteran todas y se realizan los calculos
    frm.refresh_field("items");
    frm.doc.items.forEach((item_row, index) => {
      cdn = item_row.name;
      qo_get_special_tax_by_item(frm, cdt, cdn);
      shs_quotation_calculation(frm, cdt, cdn);
      qo_get_other_tax(frm, cdt, cdn);
    });

    qo_recalculate_other_taxes(frm);
    qo_shs_total_other_tax(frm);
    qo_shs_total_by_item_type(frm);
  }
  frm.refresh_field("items");
}

/**
 * @summary Suma el total de montos que se encuentren en Otros Impuestos Especiales
 *
 * @param {*} frm
 */
function qo_shs_total_other_tax(frm) {
  frm.refresh_field("shs_tax_quotation");

  let otros_impuestos = frm.doc.shs_tax_quotation || [];

  if (otros_impuestos.length > 0) {
    let total_tax = otros_impuestos
      .map((o) => o.total)
      .reduce((a, c) => {
        return a + c;
      });
    cur_frm.set_value("shs_qt_total_otros_imp_incl", flt(total_tax));
    frm.refresh_field("shs_qt_total_otros_imp_incl");
  } else {
    cur_frm.set_value("shs_qt_total_otros_imp_incl", 0);
    frm.refresh_field("shs_qt_total_otros_imp_incl");
  }
}

/**
 * @summary Si la fila de items que se esta manipulando tiene una cuenta de impuesto especial,
 * se recalcula el total de impuesto y se agrega a la tabla hija shs_tax_quotation
 * Solo y solo si no esta agregada en la tabla hija shs_tax_quotation
 *
 * @param {*} frm
 * @param {*} cdt
 * @param {*} cdn
 */
function qo_get_other_tax(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);

  // 1. Se valida que la fila que se esta manipulando tenga una cuenta de impuesto especial
  frm.refresh_field("items");

  if (row.facelec_qt_tax_rate_per_uom_account) {
    // 2. Se valida si la cuenta ya existe en shs_tax_quotation si no existe se agrega
    // Si ya existe se iteran todos los items en busca de aquellas filas que tenga una
    // cuenta de impuesto especial para recalcular el total por cuenta y por fila de shs_tax_quotation
    let otros_impuestos = frm.doc.shs_tax_quotation || [];

    // Validador si la cuenta iterada existe en shs_tax_quotation True/False
    let acc_check = otros_impuestos.some(function (el) {
      return el.account_head === row.facelec_qt_tax_rate_per_uom_account && row.facelec_qt_tax_rate_per_uom_account;
    });

    let shs_otro_impuesto = row.facelec_qt_other_tax_amount;

    // Si no existe en la tabla hija shs_tax_quotation se agrega
    if (!acc_check) {
      frm.add_child("shs_tax_quotation", {
        account_head: row.facelec_qt_tax_rate_per_uom_account,
        total: shs_otro_impuesto,
      });

      frm.refresh_field("shs_tax_quotation");
    }
  }
}

/**
 * @summary Obtiene las cuenta configuradas y monto de impuestos especiales de X item en caso sea de tipo Combustible
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} row - Objeto que contiene todas las propiedades de la fila de items que se este manipulando
 */
function qo_get_special_tax_by_item(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);

  frm.refresh_field("items");
  if (row.facelec_qt_is_fuel && row.item_code) {
    // Peticion para obtener el monto, cuenta venta de impuesto especial de combustible
    // en funcion de item_code y la compania
    frappe.call({
      method: "factura_electronica.api.get_special_tax",
      args: {
        item_code: row.item_code,
        company: frm.doc.company,
      },
      callback: (r) => {
        // Si hay una respuesta valida
        if (r.message.facelec_tax_rate_per_uom_selling_account) {
          frappe.model.set_value(
            row.doctype,
            row.name,
            "facelec_qt_tax_rate_per_uom",
            flt(r.message.facelec_tax_rate_per_uom)
          );
          frappe.model.set_value(
            row.doctype,
            row.name,
            "facelec_qt_tax_rate_per_uom_account",
            r.message.facelec_tax_rate_per_uom_selling_account || ""
          );
          frm.refresh_field("items");
        } else {
          // Si no esta configurado el impuesto especial para el item
          frappe.show_alert(
            {
              message: __(
                `El item ${row.item_code}, Fila ${row.idx} de Tipo Combustible.
                    No tiene configuradas las cuentas y monto para Impuesto especiales, por favor configurelo
                    para que se realicen correctamente los calculos o si no es un producto de tipo combustible cambielo a Bien o Servicio`
              ),
              indicator: "red",
            },
            120
          );
        }
      },
    });

    return;
    // Si no es item de tipo combustible
  } else {
    frappe.model.set_value(row.doctype, row.name, "facelec_qt_tax_rate_per_uom", flt(0));
    frappe.model.set_value(row.doctype, row.name, "facelec_qt_tax_rate_per_uom_account", "");
    frm.refresh_field("items");
  }
}

/**
 * @summary Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 */
function qo_shs_total_by_item_type(frm) {
  let fix_gt_tax_fuel = 0;
  let fix_gt_tax_goods = 0;
  let fix_gt_tax_services = 0;
  let fix_gt_tax_iva = 0;

  $.each(frm.doc.items || [], function (i, d) {
    fix_gt_tax_fuel += flt(d.facelec_qt_gt_tax_net_fuel_amt);
    fix_gt_tax_goods += flt(d.facelec_qt_gt_tax_net_goods_amt);
    fix_gt_tax_services += flt(d.facelec_qt_gt_tax_net_services_amt);
    fix_gt_tax_iva += flt(d.facelec_qt_sales_tax_for_this_row);
  });

  cur_frm.set_value("facelec_qt_gt_tax_fuel", fix_gt_tax_fuel);
  frm.refresh_field("facelec_qt_gt_tax_fuel");

  cur_frm.set_value("facelec_qt_gt_tax_goods", fix_gt_tax_goods);
  frm.refresh_field("facelec_qt_gt_tax_goods");

  cur_frm.set_value("facelec_qt_gt_tax_services", fix_gt_tax_services);
  frm.refresh_field("facelec_qt_gt_tax_services");

  cur_frm.set_value("facelec_qt_total_iva", fix_gt_tax_iva);
  frm.refresh_field("facelec_qt_total_iva");
}

// Calculos para Factura de Compra
function shs_quotation_calculation(frm, cdt, cdn) {
  let item_row = frappe.get_doc(cdt, cdn);

  frm.refresh_field("items");
  let this_company_sales_tax_var = 0;
  const taxes_tbl = frm.doc.taxes || [];

  // Si hay tabla de impuestos
  if (taxes_tbl.length > 0) {
    this_company_sales_tax_var = taxes_tbl[0].rate;
  } else {
    // Muestra una notificacion para que se cargue una tabla de impuestos
    frappe.show_alert(
      {
        message: __(
          "Tabla de impuestos no se encuentra cargada, por favor agregarla para que los calculos se generen correctamente"
        ),
        indicator: "red",
      },
      400
    );

    this_company_sales_tax_var = 0;
    return;
  }

  let amount_minus_excise_tax = 0;
  let other_tax_amount = 0;
  let net_fuel = 0;
  let net_services = 0;
  let net_goods = 0;
  let tax_for_this_row = 0;

  other_tax_amount = flt(item_row.facelec_qt_tax_rate_per_uom * item_row.qty * item_row.conversion_factor);
  frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_other_tax_amount", other_tax_amount);

  //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
  // * row.stock_qty --> Al usar stock_qty los calculos no se realizan correctamente ya que se carga demasiado lento el valor
  amount_minus_excise_tax = flt(
    item_row.qty * item_row.rate - item_row.qty * item_row.conversion_factor * item_row.facelec_qt_tax_rate_per_uom
  );
  frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_amount_minus_excise_tax", amount_minus_excise_tax);

  if (item_row.facelec_qt_is_fuel && item_row.item_code) {
    net_services = 0;
    net_goods = 0;
    net_fuel = flt(item_row.facelec_qt_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_gt_tax_net_fuel_amt", flt(net_fuel));

    tax_for_this_row = flt(item_row.facelec_qt_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de bienes y servicios se resetean a 0
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_gt_tax_net_services_amt", flt(net_services));
  }

  tax_for_this_row = 0;
  if (item_row.facelec_qt_is_good && item_row.item_code) {
    net_services = 0;
    net_fuel = 0;
    net_goods = flt(item_row.facelec_qt_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_gt_tax_net_goods_amt", flt(net_goods));

    tax_for_this_row = flt(item_row.facelec_qt_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de servicios y combustibles se resetean a 0
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_gt_tax_net_services_amt", flt(net_services));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_gt_tax_net_fuel_amt", flt(net_fuel));
  }

  tax_for_this_row = 0;
  if (item_row.facelec_qt_is_service && item_row.item_code) {
    net_fuel = 0;
    net_goods = 0;
    net_services = flt(item_row.facelec_qt_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_gt_tax_net_services_amt", flt(net_services));

    tax_for_this_row = flt(item_row.facelec_qt_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de bienes y combustibles se resetean a 0
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_qt_gt_tax_net_fuel_amt", flt(net_fuel));
  }

  frm.refresh_field("items");
}

function shs_quotation_total_other_tax(frm) {
  frm.refresh_field("shs_tax_quotation");

  let otros_impuestos = frm.doc.shs_tax_quotation || [];

  if (otros_impuestos.length > 0) {
    let total_tax = otros_impuestos
      .map((o) => o.total)
      .reduce((a, c) => {
        return a + c;
      });
    cur_frm.set_value("shs_qt_total_otros_imp_incl", flt(total_tax));
    frm.refresh_field("shs_qt_total_otros_imp_incl");
  } else {
    cur_frm.set_value("shs_qt_total_otros_imp_incl", 0);
    frm.refresh_field("shs_qt_total_otros_imp_incl");
  }
}

/**
 * @summary Si ya existe una cuenta en shs_tax_quotation se iteran todos los items en busca de aquellas filas que tenga una
 * una cuenta de impuesto especial y recalcular el total por cuenta
 * y asi asegurar que esten correctos los valores si el usuario hace cambios
 *
 * @param {object} frm - Objeto con las propiedades del doctype
 */
function qo_recalculate_other_taxes(frm) {
  frm.refresh_field("shs_tax_quotation");
  frm.refresh_field("items");

  let items_invoice = frm.doc.items || [];
  items_invoice.forEach((item_row, index) => {
    // console.log("Esta es la cuenta en la iteracion", item_row.facelec_tax_rate_per_uom_account)
    // Si la fila iterada tiene una cuenta de impuesto especial y en la tabla hija de shs_tax_quotation hay filas
    if (item_row.facelec_qt_tax_rate_per_uom_account && frm.doc.shs_tax_quotation) {
      // Busca si la cuenta iterada existe en shs_tax_quotation, si existe se volvera a iterar items y totalizar por cuenta
      // si no existe se eliminara de shs_tax_quotation
      let total_by_account = 0;
      let idx_acc_check = frm.doc.shs_tax_quotation.find(
        (el) => el["account_head"] === item_row.facelec_qt_tax_rate_per_uom_account
      );

      if (idx_acc_check) {
        frm.refresh_field("shs_tax_quotation");
        frappe.model.set_value("Otros Impuestos Factura Electronica", idx_acc_check.name, "total", total_by_account);

        items_invoice.forEach((item_row_x, index_x) => {
          if (item_row_x.facelec_qt_tax_rate_per_uom_account === item_row.facelec_qt_tax_rate_per_uom_account) {
            total_by_account += flt(item_row_x.facelec_qt_other_tax_amount);
          }
        });

        frm.refresh_field("shs_tax_quotation");
        frappe.model.set_value("Otros Impuestos Factura Electronica", idx_acc_check.name, "total", total_by_account);
      }
    }
  });
}

function qo_remove_non_existing_taxes(frm) {
  // Se vuelve a verificar que existan filas en shs_tax_quotation, si no hay se retorna
  frm.refresh_field("shs_tax_quotation");
  let otros_impuestos = frm.doc.shs_tax_quotation || [];
  if (otros_impuestos.length == 0) return;

  // Se itera shs_tax_quotation y cada fila se compara con items, si la cuenta de la fila no existe en items se elimina
  frm.refresh_field("items");

  let idx_special_acc_check;
  otros_impuestos.forEach((tax_row, index) => {
    // retorna un objecto o undefined
    idx_special_acc_check = frm.doc.items.find((el) => el["facelec_qt_tax_rate_per_uom_account"] === tax_row.account_head);

    // Si la fila iterada no tiene ninguna relacion con la tabla hija items se elimina de shs_tax_quotation
    if (idx_special_acc_check === undefined) {
      // console.log("Hay que eliminar", otros_impuestos[index].account_head)
      frm.get_field("shs_tax_quotation").grid.grid_rows[index].remove();
      frm.refresh_field("shs_tax_quotation");
    }
  });
  frm.refresh_field("shs_tax_quotation");
  qo_recalculate_other_taxes(frm);
}

/**
 * @summary Calculador de montos para generar documentos electronicos
 * @param {Object} frm - Propiedades del Doctype
 */
function quotation_calc(frm) {
  frappe.call({
    method: "factura_electronica.utils.calculator.sales_quotation_calculator",
    args: {
      invoice_name: frm.doc.name,
    },
    freeze: true,
    freeze_message: __("Calculating") + " 📄📄📄",
    callback: (r) => {
      frm.reload_doc();
      // console.log("Sales Quotation Calculated", r.message);
      // frm.save();
    },
    error: (r) => {
      // on error
      console.log("Sales Quotation Calculated Error");
    },
  });
  frm.reload_doc();
}

frappe.ui.form.on("Quotation", {
  onload_post_render: function (frm, cdt, cdn) {
    // Funciona unicamente cuando se carga por primera vez el documento y aplica unicamente para el form y no childtables
  },
  facelec_qt_nit: function (frm, cdt, cdn) {
    // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
    // valNit(frm.doc.facelec_qt_nit, frm.doc.customer, frm);
  },
  discount_amount: function (frm, cdt, cdn) {
    // Trigger Monto de descuento
    var tax_before_calc = frm.doc.facelec_total_iva;
    // es-GT: Este muestra el IVA que se calculo por medio de nuestra aplicación.
    var discount_amount_net_value = frm.doc.discount_amount / (1 + cur_frm.doc.taxes[0].rate / 100);

    if (discount_amount_net_value == NaN || discount_amount_net_value == undefined) {
    } else {
      // console.log("El descuento parece ser un numero definido, calculando con descuento.");
      discount_amount_tax_value = discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100);
      // console.log("El IVA del descuento es:" + discount_amount_tax_value);
      frm.doc.facelec_total_iva = frm.doc.facelec_total_iva - discount_amount_tax_value;
      // console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
    }
  },
  before_save: function (frm, cdt, cdn) {
    // quotation_each_row(frm, cdt, cdn);
  },
  after_save: function (frm, cdt, cdn) {
    quotation_calc(frm);
  },
  // Se ejecuta al presionar el boton guardar
  validate: function (frm, cdt, cdn) {
    // console.log('validate');
    // Asegura que los montos de impuestos especiales se calculen correctamente
    // quotation_each_row(frm, cdt, cdn);
    // qo_remove_non_existing_taxes(frm);

    let taxes = frm.doc.taxes || [];
    if (taxes.length == 0) {
      // Muestra una notificacion para cargar una tabla de impuestos
      frappe.show_alert(
        {
          message: __(
            "Tabla de impuestos no se encuentra cargada, por favor agregarla para que los calculos se generen correctamente"
          ),
          indicator: "red",
        },
        400
      );
    }
  },
});

// frappe.ui.form.on("Quotation Item", {
//   before_items_remove: function (frm, cdt, cdn) {
//     qo_remove_non_existing_taxes(frm);
//     qo_shs_total_other_tax(frm);
//     qo_shs_total_by_item_type(frm);
//   },
//   items_remove: function (frm, cdt, cdn) {
//     qo_remove_non_existing_taxes(frm);
//     qo_shs_total_by_item_type(frm);
//     shs_quotation_total_other_tax(frm);
//   },
//   // NOTA: SI el proceso se realentiza al momento de agregar/duplicar filas comentar este bloque de codigo
//   items_add: function (frm, cdt, cdn) {
//     quotation_each_row(frm, cdt, cdn);
//   },
//   item_code: function (frm, cdt, cdn) {
//     quotation_each_row(frm, cdt, cdn);
//   },
//   discount_percentage: function (frm, cdt, cdn) {
//     quotation_each_row(frm, cdt, cdn);
//   },
//   discount_amount: function (frm, cdt, cdn) {
//     quotation_each_row(frm, cdt, cdn);
//   },
//   qty: function (frm, cdt, cdn) {
//     quotation_each_row(frm, cdt, cdn);
//   },
//   uom: function (frm, cdt, cdn) {
//     quotation_each_row(frm, cdt, cdn);
//   },
//   conversion_factor: function (frm, cdt, cdn) {
//     quotation_each_row(frm, cdt, cdn);
//   },
//   rate: function (frm, cdt, cdn) {
//     quotation_each_row(frm, cdt, cdn);
//   },
//   facelec_qt_tax_rate_per_uom_account: function (frm, cdt, cdn) {
//     quotation_each_row(frm, cdt, cdn);
//   },
// });

// frappe.ui.form.on("Otros Impuestos Factura Electronica", {
//   // Despues de que se elimina una fila
//   before_shs_tax_quotation_remove: function (frm, cdt, cdn) {
//     shs_quotation_total_other_tax(frm);
//   },
//   // Cuando se elimina una fila
//   shs_tax_quotation_remove: function (frm, cdt, cdn) {
//     shs_quotation_total_other_tax(frm);
//   },
//   //  Cuando se agrega una fila
//   shs_tax_quotation_add: function (frm, cdt, cdn) {
//     shs_quotation_total_other_tax(frm);
//   },
//   //   Cuando se cambia de posicion una fila
//   shs_tax_quotation_move: function (frm, cdt, cdn) {
//     shs_quotation_total_other_tax(frm);
//   },
// });
/* ----------------------------------------------------------------------------------------------------------------- */
