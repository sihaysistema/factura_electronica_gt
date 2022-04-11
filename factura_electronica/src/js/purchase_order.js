import { valNit } from "./facelec.js";

// console.log("Hello world from Purchase Order");

/* Purchase Order------------------------------------------------------------------------------------------------------- */
function purchase_order_each_item(frm, cdt, cdn) {
  // console.log("Recalculando... Delivery Note");
  if (cdt === "Purchase Order Item") {
    pi_get_special_tax_by_item(frm, cdt, cdn);
    shs_purchase_order_calculation(frm, cdt, cdn);

    pi_total_by_item_type(frm);
  } else {
    cdt = "Purchase Order Item";
    // Si no es una fila especifica, se iteran todas y se realizan los calculos
    frm.refresh_field("items");
    frm.doc.items.forEach((item_row, index) => {
      cdn = item_row.name;

      pi_get_special_tax_by_item(frm, cdt, cdn);
      shs_purchase_order_calculation(frm, cdt, cdn);
    });
    pi_total_by_item_type(frm);
  }
}

/**
 * @summary Vuelve a calcular los totales de FUEL, GOODS, SERVICES e IVA
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 */
function pi_total_by_item_type(frm) {
  let fix_gt_tax_fuel = 0;
  let fix_gt_tax_goods = 0;
  let fix_gt_tax_services = 0;
  let fix_gt_tax_iva = 0;

  $.each(frm.doc.items || [], function (i, d) {
    fix_gt_tax_fuel += flt(d.facelec_po_gt_tax_net_fuel_amt);
    fix_gt_tax_goods += flt(d.facelec_po_gt_tax_net_goods_amt);
    fix_gt_tax_services += flt(d.facelec_po_gt_tax_net_services_amt);
    fix_gt_tax_iva += flt(d.facelec_po_sales_tax_for_this_row);
  });

  cur_frm.set_value("facelec_po_gt_tax_fuel", fix_gt_tax_fuel);
  frm.refresh_field("facelec_po_gt_tax_fuel");

  cur_frm.set_value("facelec_po_gt_tax_goods", fix_gt_tax_goods);
  frm.refresh_field("facelec_po_gt_tax_goods");

  cur_frm.set_value("facelec_po_gt_tax_services", fix_gt_tax_services);
  frm.refresh_field("facelec_po_gt_tax_services");

  cur_frm.set_value("facelec_po_total_iva", fix_gt_tax_iva);
  frm.refresh_field("facelec_po_total_iva");
}

/**
 * @summary Obtiene las cuenta configuradas y monto de impuestos especiales de X item en caso sea de tipo Combustible
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} row - Objeto que contiene todas las propiedades de la fila de items que se este manipulando
 */
function pi_get_special_tax_by_item(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);

  frm.refresh_field("items");
  if (row.shs_po_is_fuel && row.item_code) {
    // Peticion para obtener el monto, cuenta venta de impuesto especial de combustible
    // en funcion de item_code y la compania
    frappe.call({
      method: "factura_electronica.api.get_special_tax",
      args: {
        item_code: row.item_code,
        company: frm.doc.company,
      },
      callback: (r) => {
        // Si existe una cuenta configurada para el item
        if (r.message.facelec_tax_rate_per_uom_selling_account) {
          // on success
          frappe.model.set_value(row.doctype, row.name, "shs_po_tax_rate_per_uom", flt(r.message.facelec_tax_rate_per_uom));
          frappe.model.set_value(
            row.doctype,
            row.name,
            "shs_po_tax_rate_per_uom_account",
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
    frappe.model.set_value(row.doctype, row.name, "shs_po_tax_rate_per_uom", flt(0));
    frappe.model.set_value(row.doctype, row.name, "shs_po_tax_rate_per_uom_account", "");
    frm.refresh_field("items");
  }
}

// Calculos para Orden de Compra
function shs_purchase_order_calculation(frm, cdt, cdn) {
  let item_row = frappe.get_doc(cdt, cdn);
  cur_frm.refresh_fields();

  frm.refresh_field("items");
  let this_company_sales_tax_var = 0;
  const taxes_tbl = frm.doc.taxes || [];

  // Valida si la compania tiene carga una tabla de impuestos
  if (taxes_tbl.length > 0) {
    this_company_sales_tax_var = taxes_tbl[0].rate;
  } else {
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

    this_company_sales_tax_var = 0;
    return;
  }

  let amount_minus_excise_tax = 0;
  let other_tax_amount = 0;
  let net_fuel = 0;
  let net_services = 0;
  let net_goods = 0;
  let tax_for_this_row = 0;

  other_tax_amount = flt(item_row.facelec_po_tax_rate_per_uom * (item_row.qty * item_row.conversion_factor));
  frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_other_tax_amount", other_tax_amount);

  //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
  amount_minus_excise_tax = flt(
    item_row.qty * item_row.rate - item_row.qty * item_row.conversion_factor * item_row.facelec_po_tax_rate_per_uom
  );
  frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_amount_minus_excise_tax", amount_minus_excise_tax);

  if (item_row.facelec_po_is_fuel && item_row.item_code) {
    net_services = 0;
    net_goods = 0;
    net_fuel = flt(item_row.facelec_po_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_gt_tax_net_fuel_amt", flt(net_fuel));

    tax_for_this_row = flt(item_row.facelec_po_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_sales_tax_for_this_row", tax_for_this_row);

    // Los campos de bienes y servicios se resetean a 0
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_gt_tax_net_services_amt", flt(net_services));
  }

  tax_for_this_row = 0;
  if (item_row.facelec_po_is_good && item_row.item_code) {
    net_services = 0;
    net_fuel = 0;
    net_goods = flt(item_row.facelec_po_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_gt_tax_net_goods_amt", flt(net_goods));

    tax_for_this_row = flt(item_row.facelec_po_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de servicios y combustibles se resetean a 0
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_gt_tax_net_services_amt", flt(net_services));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_gt_tax_net_fuel_amt", flt(net_fuel));
  }

  tax_for_this_row = 0;
  if (item_row.facelec_po_is_service && item_row.item_code) {
    net_fuel = 0;
    net_goods = 0;
    net_services = flt(item_row.facelec_po_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_gt_tax_net_services_amt", flt(net_services));

    tax_for_this_row = flt(item_row.facelec_po_gt_tax_net_services_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de bienes y combustibles se resetean a 0
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(item_row.doctype, item_row.name, "facelec_po_gt_tax_net_fuel_amt", flt(net_fuel));
  }

  frm.refresh_field("items");
}

/**
 * @summary Calculador de montos para generar documentos electronicos
 * @param {Object} frm - Propiedades del Doctype
 */
function purchase_order_calc(frm) {
  frappe.call({
    method: "factura_electronica.utils.calculator.purchase_order_calculator",
    args: {
      invoice_name: frm.doc.name,
    },
    freeze: true,
    freeze_message: __("Calculating") + " 📄📄📄",
    callback: (r) => {
      frm.reload_doc();
      // console.log("Purchase Order Calculated", r.message);
      // frm.save();
    },
    error: (r) => {
      // on error
      console.log("Purchase Order Calculated Error");
    },
  });
  frm.reload_doc();
}

frappe.ui.form.on("Purchase Order", {
  onload_post_render: function (frm, cdt, cdn) {},
  validate: function (frm, cdt, cdn) {
    // purchase_order_each_item(frm, cdt, cdn);

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
  facelec_po_nit: function (frm) {
    // Funcion para validar NIT: Se ejecuta cuando exista un cambio en el campo de NIT
    valNit(frm.doc.facelec_po_nit, frm.doc.supplier, frm);
  },
  discount_amount: function (frm) {
    // Trigger Monto de descuento
    var tax_before_calc = frm.doc.facelec_po_total_iva;
    // es-GT: Este muestra el IVA que se calculo por medio de nuestra aplicación.
    var discount_amount_net_value = frm.doc.discount_amount / (1 + cur_frm.doc.taxes[0].rate / 100);

    if (discount_amount_net_value == NaN || discount_amount_net_value == undefined) {
    } else {
      discount_amount_tax_value = discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100);
      frm.doc.facelec_po_total_iva = frm.doc.facelec_po_total_iva - discount_amount_tax_value;
    }
  },
  before_save: function (frm, cdt, cdn) {
    // purchase_order_each_item(frm, cdt, cdn);
  },
  // Se ejecuta despues de guardar el doctype
  after_save: function (frm, cdt, cdn) {
    purchase_order_calc(frm);
  },
});

// frappe.ui.form.on("Purchase Order Item", {
//   before_items_remove: function (frm) {
//     pi_total_by_item_type(frm);
//   },
//   items_remove: function (frm) {
//     pi_total_by_item_type(frm);
//   },
//   items_remove: function (frm) {
//     pi_total_by_item_type(frm);
//   },
//   // NOTA: SI el proceso se realentiza al momento de agregar/duplicar filas comentar este bloque de codigo
//   items_add: function (frm) {
//     purchase_order_each_item(frm, cdt, cdn);
//   },
//   item_code: function (frm, cdt, cdn) {
//     purchase_order_each_item(frm, cdt, cdn);
//   },
//   qty: function (frm, cdt, cdn) {
//     // Trigger cantidad
//     purchase_order_each_item(frm, cdt, cdn);
//   },
//   conversion_factor: function (frm, cdt, cdn) {
//     // Trigger factor de conversion
//     purchase_order_each_item(frm, cdt, cdn);
//   },
//   rate: function (frm, cdt, cdn) {
//     purchase_order_each_item(frm, cdt, cdn);
//   },
// });

/* ----------------------------------------------------------------------------------------------------------------- */
