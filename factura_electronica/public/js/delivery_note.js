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
function dn_get_special_tax_by_item(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);

  frm.refresh_field('items');
  if (row.shs_dn_is_fuel && row.item_code) {
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
          frappe.model.set_value(row.doctype, row.name, "shs_dn_tax_rate_per_uom", flt(r.message.facelec_tax_rate_per_uom));
          frappe.model.set_value(row.doctype, row.name, "shs_dn_tax_rate_per_uom_account", r.message.facelec_tax_rate_per_uom_selling_account || '');
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

    return;
    // Si no es item de tipo combustible
  } else {
    frappe.model.set_value(row.doctype, row.name, "shs_dn_tax_rate_per_uom", flt(0));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_tax_rate_per_uom_account", '');
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
  if (cdt === 'Delivery Note Item') {
    dn_get_special_tax_by_item(frm, cdt, cdn);
    shs_delivery_note_calculation(frm, cdt, cdn);

    dn_total_by_item_type(frm);
  } else {
    cdt = "Delivery Note Item";
    // Si no es una fila especifica, se iteran todas y se realizan los calculos
    frm.refresh_field('items');
    frm.doc.items.forEach((item_row, index) => {
      cdn = item_row.name;

      dn_get_special_tax_by_item(frm, cdt, cdn);
      shs_delivery_note_calculation(frm, cdt, cdn);

    });
    dn_total_by_item_type(frm);
  }
}

/**
 * @summary Calcula los impuestos, montos de la factura para GT
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} row - Objecto con las propiedades de la fila que se este manipulando
 */
function shs_delivery_note_calculation(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);
  // console.log("Calculando...", row.item_code, "indice", row.idx);

  frm.refresh_field('items');
  let this_company_sales_tax_var = 0;
  const taxes_tbl = frm.doc.taxes || [];

  // Valida si la compania tiene carga una tabla de impuestos
  if (taxes_tbl.length > 0) {
    this_company_sales_tax_var = taxes_tbl[0].rate;
  } else {
    // Muestra una notificacion para cargar una tabla de impuestos
    frappe.show_alert({
      message: __('Tabla de impuestos no se encuentra cargada, por favor agregarla para que los calculos se generen correctamente'),
      indicator: 'red'
    }, 400);

    this_company_sales_tax_var = 0
    return;
  }

  let amount_minus_excise_tax = 0;
  let other_tax_amount = 0;
  let net_fuel = 0;
  let net_services = 0;
  let net_goods = 0;
  let tax_for_this_row = 0;

  other_tax_amount = flt(row.shs_dn_tax_rate_per_uom * row.qty * row.conversion_factor);
  frappe.model.set_value(row.doctype, row.name, "shs_dn_other_tax_amount", other_tax_amount);

  //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
  amount_minus_excise_tax = flt((row.qty * row.rate) - (row.qty * row.conversion_factor * row.shs_dn_tax_rate_per_uom));
  frappe.model.set_value(row.doctype, row.name, "shs_dn_amount_minus_excise_tax", amount_minus_excise_tax);

  if (row.shs_dn_is_fuel && row.item_code) {
    net_services = 0;
    net_goods = 0;
    net_fuel = flt(row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_gt_tax_net_fuel_amt", flt(net_fuel));

    tax_for_this_row = flt(row.shs_dn_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_sales_tax_for_this_row", tax_for_this_row);

    // Los campos de bienes y servicios se resetean a 0
    frappe.model.set_value(row.doctype, row.name, "shs_dn_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_gt_tax_net_services_amt", flt(net_services));
  };

  tax_for_this_row = 0;
  if (row.shs_dn_is_good && row.item_code) {
    net_services = 0;
    net_fuel = 0;
    net_goods = flt(row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_gt_tax_net_goods_amt", flt(net_goods));

    tax_for_this_row = flt(row.shs_dn_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de servicios y combustibles se resetean a 0
    frappe.model.set_value(row.doctype, row.name, "shs_dn_gt_tax_net_services_amt", flt(net_services));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_gt_tax_net_fuel_amt", flt(net_fuel));
  };

  tax_for_this_row = 0;
  if (row.shs_dn_is_service && row.item_code) {
    net_fuel = 0;
    net_goods = 0;
    net_services = flt(row.shs_dn_amount_minus_excise_tax / (1 + (this_company_sales_tax_var / 100)));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_gt_tax_net_services_amt", flt(net_services));

    tax_for_this_row = flt(row.shs_dn_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de bienes y combustibles se resetean a 0
    frappe.model.set_value(row.doctype, row.name, "shs_dn_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(row.doctype, row.name, "shs_dn_gt_tax_net_fuel_amt", flt(net_fuel));
  };

  frm.refresh_field('items');
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
  let fix_gt_tax_fuel = 0;
  let fix_gt_tax_goods = 0;
  let fix_gt_tax_services = 0;
  let fix_gt_tax_iva = 0;

  $.each(frm.doc.items || [], function (i, d) {
    fix_gt_tax_fuel += flt(d.shs_dn_gt_tax_net_fuel_amt);
    fix_gt_tax_goods += flt(d.shs_dn_gt_tax_net_goods_amt);
    fix_gt_tax_services += flt(d.shs_dn_gt_tax_net_services_amt);
    fix_gt_tax_iva += flt(d.shs_dn_sales_tax_for_this_row);
  });

  cur_frm.set_value("shs_dn_gt_tax_fuel", fix_gt_tax_fuel);
  frm.refresh_field("shs_dn_gt_tax_fuel");

  cur_frm.set_value("shs_dn_gt_tax_goods", fix_gt_tax_goods);
  frm.refresh_field("shs_dn_gt_tax_goods");

  cur_frm.set_value("shs_dn_gt_tax_services", fix_gt_tax_services);
  frm.refresh_field("shs_dn_gt_tax_services");

  cur_frm.set_value("shs_dn_total_iva", fix_gt_tax_iva);
  frm.refresh_field("shs_dn_total_iva");
}

frappe.ui.form.on("Delivery Note", {
  // Se ejecuta cuando se renderiza el formulario
  onload_post_render: function (frm, cdt, cdn) {

  },
  // El validdor de nit no esta habilitado, ya que pueden existir valores de identificacion internacional
  shs_dn_nit: function (frm) {
  },
  discount_amount: function (frm, cdt, cdn) {
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
  before_save: function (frm, cdt, cdn) {
    delivery_note_each_row(frm, cdt, cdn);
  },
  validate: function (frm, cdt, cdn) {
    // console.log("Validate");
    delivery_note_each_row(frm, cdt, cdn);

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
  // NOTA: SI el proceso se realentiza al momento de agregar/duplicar filas comentar este bloque de codigo
  items_add: function (frm, cdt, cdn) {
    delivery_note_each_row(frm, cdt, cdn);
  },
  before_items_remove: function (frm) {
    dn_total_by_item_type(frm);
  },
  items_remove: function (frm) {
    dn_total_by_item_type(frm);
  },
  items_move: function (frm) {
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
