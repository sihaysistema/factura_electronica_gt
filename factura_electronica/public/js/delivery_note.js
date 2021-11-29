/**
 * Copyright (c) 2021 Si Hay Sistema and contributors
 * For license information, please see license.txt
 */

import { valNit } from './facelec.js';
import { goalSeek } from './goalSeek.js';

/**
 * @summary Obtiene las cuenta configuradas y monto de impuestos especiales de X item en caso sea de tipo Combustible
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} row - Objeto que contiene todas las propiedades de la fila de items que se este manipulando
 */
function dn_get_special_tax_by_item(frm, row) {
  if (row.shs_dn_is_fuel) {
    // Peticion para obtener el monto, cuenta venta de impuesto especial de combustible
    // en funcion de item_code y la compania
    frappe.call({
      method: 'factura_electronica.api.get_special_tax',
      args: {
        item_code: row.item_code,
        company: frm.doc.company,
      },
      callback: (r) => {
        // Si existe una cuenta configurada para el item
        if (r.message.facelec_tax_rate_per_uom_selling_account) {
          // on success
          row.shs_dn_tax_rate_per_uom = r.message.facelec_tax_rate_per_uom;
          row.shs_dn_tax_rate_per_uom_account = r.message.facelec_tax_rate_per_uom_selling_account;
          frm.refresh_field('items');
        } else {
          // Si no esta configurado el impuesto especial para el item
          frappe.show_alert(
            {
              message: __(
                `El item ${row.item_code}, Fila ${row.idx} de Tipo Combustible.
                     No tiene configuradas las cuentas y monto para Impuesto especiales, por favor configurelo
                     para que se realicen correctamente los calculos o si no es un producto de tipo combustible cambielo a Bien o Servicio`
              ),
              indicator: 'red',
            },
            120
          );
        }
      },
    });
    // Si no es item de tipo combustible
  } else {
    row.shs_dn_tax_rate_per_uom = 0;
    row.shs_dn_tax_rate_per_uom_account = '';
    frm.refresh_field('items');
  }
}

/**
 * @summary Ejecuta serialmente las funciones de calculos, para obtener siempre los ultimos valores
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} cdt - Current DocType
 * @param {object} cdn - Current DocName
 */
function delivery_note_each_row(frm, cdt, cdn) {
  // console.log("Recalculando... Delivery Note");

  frm.doc.items.forEach((item_row, index) => {
    if (item_row.name === cdn) {
      frappe.run_serially([
        () => {
          // Si la fila manipulada es un item tipo combustible
          let first_data_collection = frappe.get_doc(cdt, cdn);
          dn_get_special_tax_by_item(frm, first_data_collection);
        },
        () => {
          //   console.log('Seleccionaste', item_row);
        },
        () => {
          // Se realizan los calculos de impuestos necesarios
          let second_data_collection = frappe.get_doc(cdt, cdn);
          shs_delivery_note_calculation(frm, second_data_collection);
        },
      ]);
    }
  });
}

/**
 * @summary Calcula los impuestos, montos de la factura para GT
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} row - Objecto con las propiedades de la fila que se este manipulando
 */
function shs_delivery_note_calculation(frm, row) {
  cur_frm.refresh_fields();

  let this_company_sales_tax_var = 0;

  // Valida si la compania tiene carga una tabla de impuestos
  if (cur_frm.doc.taxes.length > 0) {
    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
  } else {
    // Muestra una notificacion para cargar una tabla de impuestos
    frappe.show_alert({
      message: __('Tabla de impuestos no se encuentra cargada, por favor agregarla para que los calculos se generen correctamente'),
      indicator: 'red'
    }, 400);

    this_company_sales_tax_var = 0
  }

  row.shs_dn_other_tax_amount = ((row.shs_dn_tax_rate_per_uom * (row.qty * row.conversion_factor)));
  //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
  row.shs_dn_amount_minus_excise_tax = ((row.qty * row.rate) - (row.qty * row.conversion_factor * row.shs_dn_tax_rate_per_uom));

  if (row.shs_dn_is_fuel) {
    row.shs_dn_gt_tax_net_fuel_amt = (row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
    row.shs_dn_sales_tax_for_this_row = (row.shs_dn_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
    // Sumatoria de todos los que tengan el check combustibles
    let total_fuel = 0;
    $.each(frm.doc.items || [], function (i, d) {
      if (d.shs_dn_is_fuel == true) {
        total_fuel += flt(d.shs_dn_gt_tax_net_fuel_amt);
      };
    });
    frm.doc.shs_dn_gt_tax_fuel = total_fuel;
  };

  if (row.shs_dn_is_good) {
    row.shs_dn_gt_tax_net_goods_amt = (row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
    row.shs_dn_sales_tax_for_this_row = (row.shs_dn_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
    // Sumatoria de todos los que tengan el check bienes
    let total_goods = 0;
    $.each(frm.doc.items || [], function (i, d) {
      if (d.shs_dn_is_good == true) {
        total_goods += flt(d.shs_dn_gt_tax_net_goods_amt);
      };
    });
    frm.doc.shs_dn_gt_tax_goods = total_goods;
  };

  if (row.shs_dn_is_service) {
    row.shs_dn_gt_tax_net_services_amt = (row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
    row.shs_dn_sales_tax_for_this_row = (row.shs_dn_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
    // Sumatoria de todos los que tengan el check servicios
    let total_servi = 0;
    $.each(frm.doc.items || [], function (i, d) {
      if (d.shs_dn_is_service == true) {
        total_servi += flt(d.shs_dn_gt_tax_net_services_amt);
      };
    });
    frm.doc.shs_dn_gt_tax_services = total_servi;
  };

  // Totaliza el valor de IVA
  let full_tax_iva = 0;
  $.each(frm.doc.items || [], function (i, d) {
    full_tax_iva += flt(d.shs_dn_sales_tax_for_this_row);
  });
  frm.doc.shs_dn_total_iva = full_tax_iva;
}

/**
 * @summary Funcion para evaluar GoalSeek
 * @param {object} a - Precio te producto
 * @param {object} b - Cantidad de producto
 */
function redondeo_delivery_note(a, b) {
  return a * b;
}

/**
 * @summary Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 */
function dn_total_by_item_type(frm) {
  var fix_gt_tax_fuel = 0;
  var fix_gt_tax_goods = 0;
  var fix_gt_tax_services = 0;
  var fix_gt_tax_iva = 0;

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
}

frappe.ui.form.on("Delivery Note", {
  // Se ejecuta cuando se renderiza el formulario
  onload_post_render: function (frm, cdt, cdn) {

  },
  // El validdor de nit no esta habilitado, ya que pueden existir valores de identificacion internacional
  shs_dn_nit: function (frm) {
  },
  discount_amount: function (frm) {
    // Trigger Monto de descuento
    var tax_before_calc = frm.doc.shs_dn_total_iva;
    // es-GT: Este muestra el IVA que se calculo por medio de nuestra aplicación.
    var discount_amount_net_value = (frm.doc.discount_amount / (1 + (cur_frm.doc.taxes[0].rate / 100)));

    if (discount_amount_net_value == NaN || discount_amount_net_value == undefined) {
    } else {
      discount_amount_tax_value = (discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100));
      frm.doc.shs_dn_total_iva = (frm.doc.shs_dn_total_iva - discount_amount_tax_value);
    }
  },
  validate: function (frm) {
    let taxes = frm.doc.taxes || [];
    if (taxes.length == 0) {
      // Muestra una notificacion para cargar una tabla de impuestos
      frappe.show_alert({
        message: __('Tabla de impuestos no se encuentra cargada, por favor agregarla para que los calculos se generen correctamente'),
        indicator: 'red'
      }, 400);
    }
  }
});

frappe.ui.form.on("Delivery Note Item", {
  items_add: function (frm, cdt, cdn) {
    dn_total_by_item_type(frm);
  },
  items_remove: function (frm) {
    dn_total_by_item_type(frm);
  },
  // Cuando se cambia el valor de item_code
  item_code: function (frm, cdt, cdn) {
    delivery_note_each_row(frm, cdt, cdn);
  },
  // CUando se cambia el valor de quantity
  qty: function (frm, cdt, cdn) {
    delivery_note_each_row(frm, cdt, cdn);
  },
  // Cuando se cambia el valor de conversion_factor
  conversion_factor: function (frm, cdt, cdn) {
    delivery_note_each_row(frm, cdt, cdn);
  },
  // Cuando se cambia el valor de rate
  rate: function (frm, cdt, cdn) {
    delivery_note_each_row(frm, cdt, cdn);
  },
  // Cuando se cambia el valor de stock_qty
  stock_qty: function (frm, cdt, cdn) {
    delivery_note_each_row(frm, cdt, cdn);
  },
  // Cuando se cambia el valor de uom
  uom: function (frm, cdt, cdn) {
    delivery_note_each_row(frm, cdt, cdn);
  },
  shs_amount_for_back_calc: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);

    let a = row.rate;
    let b = row.qty;
    let c = row.amount;

    let calcu = goalSeek({
      Func: redondeo_delivery_note,
      aFuncParams: [b, a],
      oFuncArgTarget: {
        Position: 0
      },
      Goal: row.shs_amount_for_back_calc,
      Tol: 0.001,
      maxIter: 10000
    });

    row.qty = calcu;
    row.stock_qty = calcu;
    row.amount = calcu * a;
    frm.refresh_field("items");

    delivery_note_each_row(frm, cdt, cdn);
  }
});
