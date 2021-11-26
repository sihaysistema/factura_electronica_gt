function sales_invoice_calculations(frm, row) {
  console.log('Seleccionaste', row.item_code, 'Fila', row.idx);

  // INICIO validacion existencia tabla impuesto
  //   Guarda el monto de IVA puede ser 12% o 0% en caso de no incluir
  let this_company_sales_tax_var = 0;

  if (cur_frm.doc.taxes.length > 0) {
    this_company_sales_tax_var = cur_frm.doc.taxes[0].rate;
  } else {
    // Muestra una notificacion para cargar una tabla de impuestos
    frappe.show_alert(
      {
        message: __('Tabla de impuestos no se encuentra cargada, por favor agregarla para que los calculos se generen correctamente'),
        indicator: 'red',
      },
      50
    );

    this_company_sales_tax_var = 0;
  }
  // FIN validacion existencia tabla impuesto

  frm.refresh_field('items');

  // We change the fields for other tax amount as per the complete row taxable amount.
  row.facelec_other_tax_amount = row.facelec_tax_rate_per_uom * (row.qty * row.conversion_factor);
  row.facelec_amount_minus_excise_tax = row.qty * row.rate - row.facelec_other_tax_amount; //row.stock_qty * row.facelec_tax_rate_per_uom;

  console.log(row.facelec_amount_minus_excise_tax);
  console.log(row.qty);
  console.log(row.facelec_tax_rate_per_uom);

  row.facelec_gt_tax_net_fuel_amt = 0;
  row.facelec_gt_tax_net_goods_amt = 0;
  row.facelec_gt_tax_net_services_amt = 0;

  // Verificacion Individual para verificar si es Fuel, Good o Service
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

  let total_iva_factura = 0;
  $.each(frm.doc.items || [], function (i, d) {
    if (d.facelec_sales_tax_for_this_row) {
      total_iva_factura += flt(d.facelec_sales_tax_for_this_row);
    }
  });

  // console.log("El total de iva acumulado para la factura es: " + total_iva_factura);
  cur_frm.set_value('shs_total_iva_fac', total_iva_factura);
}

function get_special_tax_by_item(frm, row) {
  // Si el item iterado es combustible: se obtiene sus detalles de impuestos especiales
  if (row.factelecis_fuel) {
    console.log('Has selecciona un producto de tipo FUEL', row.item_code);
    frappe.call({
      method: 'factura_electronica.api.get_special_tax',
      args: {
        item_code: row.item_code,
        company: frm.doc.company,
      },
      callback: (r) => {
        // on success
        row.facelec_tax_rate_per_uom = r.message.facelec_tax_rate_per_uom;
        row.facelec_tax_rate_per_uom_account = r.message.facelec_tax_rate_per_uom_selling_account;
        frm.refresh_field('items');
      },
      error: (r) => {
        console.log('Problema con petición', r.message);
      },
    });
  } else {
    // frm.refresh_field('items');
    row.facelec_tax_rate_per_uom = 0;
    row.facelec_tax_rate_per_uom_account = '';
    frm.refresh_field('items');
  }
}

frappe.ui.form.on('Sales Invoice Item', {
  before_items_remove: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('before_items_remove', row);
  },
  items_add: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('items_add', row);
  },
  items_move: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('items_move', row);
  },
  item_code: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('Seleccionaste item_code', row);

    get_special_tax_by_item(frm, row);

    row = frappe.get_doc(cdt, cdn);
    sales_invoice_calculations(frm, row);
  },
  qty: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('Seleccionaste qty', row);

    get_special_tax_by_item(frm, row);

    row = frappe.get_doc(cdt, cdn);
    sales_invoice_calculations(frm, row);
  },
  facelec_is_discount: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('facelec_is_discount', row);

    get_special_tax_by_item(frm, row);
    sales_invoice_calculations(frm, row);
  },
  uom: function (frm, cdt, cdn) {
    // Trigger UOM
    //console.log("The unit of measure field was changed and the code from the trigger was run");
    let row = frappe.get_doc(cdt, cdn);
    console.log('Seleccionaste uom', row);

    get_special_tax_by_item(frm, row);
    sales_invoice_calculations(frm, row);
  },
  conversion_factor: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('Seleccionaste conversion_factor', row);

    get_special_tax_by_item(frm, row);
    sales_invoice_calculations(frm, row);
  },
  facelec_tax_rate_per_uom_account: function (frm, cdt, cdn) {
    //facelec_otros_impuestos_fila(frm, cdt,cdn);
    // esto debe correr aqui?

    get_special_tax_by_item(frm, row);
    sales_invoice_calculations(frm, row);
  },
  rate: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('Seleccionaste rate', row);

    get_special_tax_by_item(frm, row);
    sales_invoice_calculations(frm, row);
  },
  shs_amount_for_back_calc: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    console.log('Seleccionaste goalseek', row);

    // // Permite aplicar goalSeek
    // frm.doc.items.forEach((row, index) => {
    //     var a = row.rate;
    //     var b = row.qty;
    //     var c = row.amount;
    //     let calcu = goalSeek({
    //         Func: funct_eval,
    //         aFuncParams: [b, a],
    //         oFuncArgTarget: {
    //             Position: 0,
    //         },
    //         Goal: row.shs_amount_for_back_calc,
    //         Tol: 0.001,
    //         maxIter: 10000,
    //     });
    //     // console.log(calcu);

    //     frm.doc.items[index].qty = calcu;
    //     frm.doc.items[index].stock_qty = calcu;
    //     frm.doc.items[index].amount = calcu * frm.doc.items[index].rate;
    //     frm.refresh_field("items");
    // });
  },
});
