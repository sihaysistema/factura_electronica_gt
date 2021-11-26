/**
 * Copyright (c) 2021 Si Hay Sistema and contributors
 * For license information, please see license.txt
 */

import { valNit } from './facelec.js';
import { goalSeek } from './goalSeek.js';

/**
 * @summary Realiza los calculos de impuestos de la factura que serviran para la generación de factura electrónica
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} row - Objeto que contiene todas las propiedades de la fila de items que se este manipulando
 */
function sales_invoice_calculations(frm, row) {
  console.log('Seleccionaste', row.item_code, 'Fila', row.idx);

  // INICIO validacion existencia tabla impuesto
  //   Guarda el monto de IVA puede ser 12% o 0% en caso de no incluir
  let this_company_sales_tax_var = 0;

  //   Si hay tabla de impuestos
  if (cur_frm.doc.taxes.length > 0) {
    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
  } else {
    // Muestra una notificacion para cargar una tabla de impuestos
    frappe.show_alert(
      {
        message: __('Tabla de impuestos no se encuentra cargada, por favor agregarla para que los calculos se generen correctamente'),
        indicator: 'red',
      },
      120
    );

    this_company_sales_tax_var = 0;
  }
  // FIN validacion existencia tabla impuesto

  frm.refresh_field('items');

  // We change the fields for other tax amount as per the complete row taxable amount.
  row.facelec_other_tax_amount = row.facelec_tax_rate_per_uom * (row.qty * row.conversion_factor);
  let tax_rate_per_uom_calc = row.stock_qty * row.facelec_tax_rate_per_uom;
  row.facelec_amount_minus_excise_tax = row.qty * row.rate - tax_rate_per_uom_calc; // row.facelec_other_tax_amount; //

  console.log('facelec_tax_rate_per_uom', row.facelec_tax_rate_per_uom);
  console.log('qty', row.qty);
  console.log('stock qty', row.stock_qty);
  console.log('test calculo', tax_rate_per_uom_calc);

  row.facelec_gt_tax_net_fuel_amt = 0;
  row.facelec_gt_tax_net_goods_amt = 0;
  row.facelec_gt_tax_net_services_amt = 0;

  // Verificacion Individual para verificar si es Fuel, Good o Service y realizar los calculos correspondientes
  if (row.factelecis_fuel) {
    row.facelec_gt_tax_net_fuel_amt = row.facelec_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100);
    row.facelec_sales_tax_for_this_row = row.facelec_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100);
  }

  if (row.facelec_is_good) {
    row.facelec_gt_tax_net_goods_amt = row.facelec_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100);
    row.facelec_sales_tax_for_this_row = row.facelec_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100);
  }

  if (row.facelec_is_service) {
    row.facelec_gt_tax_net_services_amt = row.facelec_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100);
    row.facelec_sales_tax_for_this_row = row.facelec_gt_tax_net_services_amt * (this_company_sales_tax_var / 100);
  }

  //   Por cada fila manipulada se vuelve a calcular el total de IVA para la factura
  let total_iva_factura = 0;
  $.each(frm.doc.items || [], function (i, d) {
    if (d.facelec_sales_tax_for_this_row) {
      total_iva_factura += flt(d.facelec_sales_tax_for_this_row);
    }
  });

  // Se asigna el total de IVA a la factura en custom field
  cur_frm.set_value('shs_total_iva_fac', total_iva_factura);
}

/**
 * @summary Obtiene los detalles de impuestos especiales de X item en caso sea de tipo Combustible
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} row - Objeto que contiene todas las propiedades de la fila de items que se este manipulando
 */
function get_special_tax_by_item(frm, row) {
  if (row.factelecis_fuel) {
    // Peticion para obtener el monto, cuenta venta de impuesto especial de combustible
    // en funcion de item_code y la compania
    frappe.call({
      method: 'factura_electronica.api.get_special_tax',
      args: {
        item_code: row.item_code,
        company: frm.doc.company,
      },
      callback: (r) => {
        if (r.message.facelec_tax_rate_per_uom_selling_account) {
          // on success
          row.facelec_tax_rate_per_uom = r.message.facelec_tax_rate_per_uom;
          row.facelec_tax_rate_per_uom_account = r.message.facelec_tax_rate_per_uom_selling_account;
          frm.refresh_field('items');
        } else {
          // Si no esta configurado el impuesto especial para el item
          frappe.show_alert(
            {
              message: __(
                `El item ${row.item_code}, Fila ${row.idx} de Tipo Combustible.
                    No tiene configuradas las cuentas y monto para Impuesto especiales, por favor configurelo para que se realicen correctamente los calculos`
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
    row.facelec_tax_rate_per_uom = 0;
    row.facelec_tax_rate_per_uom_account = '';
    frm.refresh_field('items');
  }
}

/**
 * @summary Ejecuta serialmente las funciones de calculos, para obtener siempre los ultimos valores cargados
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} cdt - Current DocType
 * @param {object} cdn - Current DocName
 */
function each_row(frm, cdt, cdn) {
  frappe.run_serially([
    () => {
      // Si la fila manipulada es un item tipo combustible
      let first_data_collection = frappe.get_doc(cdt, cdn);
      get_special_tax_by_item(frm, first_data_collection);
    },
    () => {
      //   console.log('Seleccionaste qty');
    },
    () => {
      // Se realizan los calculos de impuestos necesarios para factura electrónica
      let second_data_collection = frappe.get_doc(cdt, cdn);
      sales_invoice_calculations(frm, second_data_collection);
    },
  ]);
}

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

frappe.ui.form.on('Sales Invoice Item', {
  // Cuando se elimina una fila
  before_items_remove: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('before_items_remove', row);
  },
  //   Cuando se agrega una fila
  items_add: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('items_add', row);
  },
  //   Cuando se cambia de posicion una fila
  items_move: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('items_move', row);
  },
  //   Al cambiar el valor de item_code
  item_code: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  //   Al cambiar el valor de qty
  qty: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  stock_qty: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  //   Cuando se cambia el valor de rate
  rate: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  //   Si se marca/desmarca la casilla de descuento
  facelec_is_discount: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  //   Cuando se cmbia el valor de uom
  uom: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  //   Cuando se cambia el valor de conversion_factor
  conversion_factor: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  //   CUando se cambia manualmente la cuenta de impuesto especial
  facelec_tax_rate_per_uom_account: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  // Cuando se cambia el valor de shs_amount_for_back_calc (monto redondeo)
  shs_amount_for_back_calc: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);

    // Permite aplicar goalSeek
    let a = row.rate;
    let b = row.qty;
    let c = row.amount;

    let calcu = goalSeek({
      Func: funct_eval,
      aFuncParams: [b, a],
      oFuncArgTarget: {
        Position: 0,
      },
      Goal: row.shs_amount_for_back_calc,
      Tol: 0.001,
      maxIter: 10000,
    });

    row.qty = calcu;
    row.stock_qty = calcu;
    row.amount = calcu * a; // frm.doc.items[index].rate;
    frm.refresh_field('items');

    each_row(frm, cdt, cdn);
    console.log('Seleccionaste goalseek');
  },
});
