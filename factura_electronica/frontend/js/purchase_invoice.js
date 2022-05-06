/**
 * Copyright (c) 2021 Si Hay Sistema and contributors
 * For license information, please see license.txt
 */

// import { valNit } from "./facelec.js";
import { msg_generator } from "./facelec.js";
import { goalSeek } from "./goalSeek.js";

/* Purchase Invoice (Factura de Compra) ------------------------------------------------------------------------------------------------------- */

/**
 * @summary Funcion principal encargada de los calculos realtime de impuestos y monto
 * por tipo de de producto para usar en generación de docs electrónicos
 *
 * @param {Object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {String} cdt - Nombre del doctype
 * @param {String} cdn - Nombre del documento
 */
function shs_purchase_invoice_calculation(frm, cdt, cdn) {
  // Obtiene los datos de la fila que se esta iterando
  let row = frappe.get_doc(cdt, cdn);

  frm.refresh_field("items");

  // INICIO validacion existencia tabla impuesto
  let this_company_sales_tax_var = 0;
  const taxes_tbl = frm.doc.taxes || [];

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
  }
  // FIN validacion existencia tabla impuesto

  // INICIO CALCULOS
  let amount_minus_excise_tax = 0;
  let other_tax_amount = 0;
  let net_fuel = 0;
  let net_goods = 0;
  let net_services = 0;
  let tax_for_this_row = 0;

  other_tax_amount = flt(row.facelec_p_tax_rate_per_uom * row.qty * row.conversion_factor);
  frappe.model.set_value(row.doctype, row.name, "facelec_p_other_tax_amount", other_tax_amount);

  //OJO!  No s epuede utilizar stock_qty en los calculos, debe de ser qty a puro tubo!
  // MONTO - IDP
  amount_minus_excise_tax = row.qty * row.rate - row.qty * row.conversion_factor * row.facelec_p_tax_rate_per_uom;
  frappe.model.set_value(row.doctype, row.name, "facelec_p_amount_minus_excise_tax", flt(amount_minus_excise_tax));

  // SI es combustible
  if (row.facelec_p_is_fuel && row.item_code) {
    net_services = 0;
    net_goods = 0;
    net_fuel = row.facelec_p_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100);
    frappe.model.set_value(row.doctype, row.name, "facelec_p_gt_tax_net_fuel_amt", flt(net_fuel));

    tax_for_this_row = row.facelec_p_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100);
    frappe.model.set_value(row.doctype, row.name, "facelec_p_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de bienes y servicios se resetean a 0
    frappe.model.set_value(row.doctype, row.name, "facelec_p_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(row.doctype, row.name, "facelec_p_gt_tax_net_services_amt", flt(net_services));
  }
  // Si es bienes
  tax_for_this_row = 0;
  if (row.facelec_p_is_good && row.item_code) {
    net_services = 0;
    net_fuel = 0;
    net_goods = row.facelec_p_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100);
    frappe.model.set_value(row.doctype, row.name, "facelec_p_gt_tax_net_goods_amt", flt(net_goods));

    tax_for_this_row = row.facelec_p_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100);
    frappe.model.set_value(row.doctype, row.name, "facelec_p_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de servicios y combustibles se resetean a 0
    frappe.model.set_value(row.doctype, row.name, "facelec_p_gt_tax_net_services_amt", flt(net_services));
    frappe.model.set_value(row.doctype, row.name, "facelec_p_gt_tax_net_fuel_amt", flt(net_fuel));
  }
  // Si es servicios
  tax_for_this_row = 0;
  if (row.facelec_p_is_service && row.item_code) {
    net_fuel = 0;
    net_goods = 0;
    net_services = row.facelec_p_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100);
    frappe.model.set_value(row.doctype, row.name, "facelec_p_gt_tax_net_services_amt", flt(net_services));

    tax_for_this_row = row.facelec_p_gt_tax_net_services_amt * (this_company_sales_tax_var / 100);
    frappe.model.set_value(row.doctype, row.name, "facelec_p_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de servicios y combustibles se resetean a 0
    frappe.model.set_value(row.doctype, row.name, "facelec_p_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(row.doctype, row.name, "facelec_p_gt_tax_net_fuel_amt", flt(net_fuel));
  }

  frm.refresh_field("items");
}

/**
 * @summary Obtiene la cuenta configuradas y monto de impuesto especiale de X item en caso sea de tipo Combustible
 * @param {Object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {cdt} String - Objeto que contiene todas las propiedades de la fila de items que se este manipulando
 * @param {cdn} String - indice de la fila iterada de items
 */
function pi_get_special_tax_by_item(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);

  if (row.facelec_p_is_fuel && row.item_code) {
    // Peticion para obtener el monto, cuenta venta de impuesto especial de combustible
    // en funcion de item_code y la compania
    frappe.call({
      method: "factura_electronica.api.get_special_tax",
      args: {
        item_code: row.item_code,
        company: frm.doc.company,
      },
      callback: (r) => {
        // Si hay respuesta valida
        if (r.message.facelec_tax_rate_per_uom_purchase_account) {
          frappe.model.set_value(
            row.doctype,
            row.name,
            "facelec_p_tax_rate_per_uom",
            flt(r.message.facelec_tax_rate_per_uom)
          );
          frappe.model.set_value(
            row.doctype,
            row.name,
            "facelec_p_tax_rate_per_uom_account",
            r.message.facelec_tax_rate_per_uom_purchase_account || ""
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
    frappe.model.set_value(row.doctype, row.name, "facelec_p_tax_rate_per_uom", 0);
    frappe.model.set_value(row.doctype, row.name, "facelec_p_tax_rate_per_uom_account", "");
    frm.refresh_field("items");
  }
}

/**
 * @summary Si la fila de items que se esta manipulando tiene una cuenta de impuesto especial,
 * se recalcula el total de impuesto por cuenta y se agrega a la tabla hija shs_pi_otros_impuestos
 * Solo y solo si no esta agregada en la tabla hija shs_pi_otros_impuestos
 *
 * @param {*} frm
 * @param {*} cdt
 * @param {*} cdn
 */
function pi_get_other_tax(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);

  // 1. Se valida que la fila que se esta manipulando tenga una cuenta de impuesto especial
  frm.refresh_field("items");

  if (row.facelec_p_tax_rate_per_uom_account) {
    // 2. Se valida si la cuenta ya existe en shs_pi_otros_impuestos si no existe se agrega
    // Si ya existe se iteran todos los items en busca de aquellas filas que tenga una
    // cuenta de impuesto especial para recalcular el total por cuenta y por fila de shs_pi_otros_impuestos
    let otros_impuestos = frm.doc.shs_pi_otros_impuestos || [];

    // Validador si la cuenta iterada existe en shs_pi_otros_impuestos True/False
    let acc_check = otros_impuestos.some(function (el) {
      return el.account_head === row.facelec_p_tax_rate_per_uom_account && row.facelec_p_tax_rate_per_uom_account;
    });

    let shs_otro_impuesto = row.facelec_p_other_tax_amount;

    // Si no existe en la tabla hija shs_pi_otros_impuestos se agrega
    if (!acc_check) {
      frm.add_child("shs_pi_otros_impuestos", {
        account_head: row.facelec_p_tax_rate_per_uom_account,
        total: shs_otro_impuesto,
      });

      frm.refresh_field("shs_pi_otros_impuestos");
    }
  }
}

/**
 * @summary Si ya existe una cuenta en shs_pi_otros_impuestos se iteran todos los items en busca de aquellas filas que tenga una
 * una cuenta de impuesto especial y recalcular el total por cuenta
 * y asi asegurar que esten correctos los valores si el usuario hace cambios
 *
 * @param {object} frm - Objeto con las propiedades del doctype
 */
function pi_recalculate_other_taxes(frm) {
  frm.refresh_field("shs_pi_otros_impuestos");
  frm.refresh_field("items");

  let items_invoice = frm.doc.items || [];

  items_invoice.forEach((item_row, index) => {
    // console.log("Esta es la cuenta en la iteracion", item_row.facelec_p_tax_rate_per_uom_account)
    // Si la fila iterada tiene una cuenta de impuesto especial y en la tabla hija de shs_pi_otros_impuestos hay filas
    if (item_row.facelec_p_tax_rate_per_uom_account && frm.doc.shs_pi_otros_impuestos) {
      // Busca si la cuenta iterada existe en shs_pi_otros_impuestos, si existe se volvera a iterar items y totalizar por cuenta
      // si no existe se eliminara de shs_pi_otros_impuestos
      let total_by_account = 0;
      let idx_acc_check = frm.doc.shs_pi_otros_impuestos.find(
        (el) => el["account_head"] === item_row.facelec_p_tax_rate_per_uom_account
      );

      // Si se encuentra una fila con la cuenta
      if (idx_acc_check) {
        frm.refresh_field("shs_pi_otros_impuestos");
        frappe.model.set_value("Otros Impuestos Factura Electronica", idx_acc_check.name, "total", total_by_account);

        items_invoice.forEach((item_row_x, index_x) => {
          if (item_row_x.facelec_p_tax_rate_per_uom_account === item_row.facelec_p_tax_rate_per_uom_account) {
            total_by_account += flt(item_row_x.facelec_p_other_tax_amount);
          }
        });

        frm.refresh_field("shs_pi_otros_impuestos");
        frappe.model.set_value("Otros Impuestos Factura Electronica", idx_acc_check.name, "total", total_by_account);
      }
    }
  });
}

/**
 * @summary Suma el total de montos que se encuentren en Otros Impuestos Especiales
 *
 * @param {*} frm
 */
function pi_shs_total_other_tax(frm) {
  frm.refresh_field("shs_pi_otros_impuestos");

  let otros_impuestos = frm.doc.shs_pi_otros_impuestos || [];

  if (otros_impuestos.length > 0) {
    let total_tax = otros_impuestos
      .map((o) => o.total)
      .reduce((a, c) => {
        return a + c;
      });
    cur_frm.set_value("shs_pi_total_otros_imp_incl", flt(total_tax));
    frm.refresh_field("shs_pi_total_otros_imp_incl");
  } else {
    cur_frm.set_value("shs_pi_total_otros_imp_incl", 0);
    frm.refresh_field("shs_pi_total_otros_imp_incl");
  }
}

/**
 * @summary Cada vez que se elimina una fila, recorre la tabla hija shs_pi_otros_impuestos
 * y los compara con las filas existentes en items, si la cuenta que se esta iterando
 * no existe en items, se elimina
 *
 * @param {*} frm
 */
function pi_remove_non_existing_taxes(frm) {
  frm.refresh_field("shs_pi_otros_impuestos");
  let otros_impuestos = frm.doc.shs_pi_otros_impuestos || [];
  // Se vuelve a verificar que existan filas en shs_pi_otros_impuestos, si no hay se retorna
  if (otros_impuestos.length === 0) return;

  // Se itera shs_pi_otros_impuestos y cada fila se compara con items, si la cuenta de la fila no existe en items se elimina
  frm.refresh_field("items");
  let idx_special_acc_check;
  otros_impuestos.forEach((tax_row, index) => {
    idx_special_acc_check = frm.doc.items.find((el) => el["facelec_p_tax_rate_per_uom_account"] === tax_row.account_head);

    // Si la fila iterada no tiene ninguna relacion con la tabla hija items se elimina de shs_pi_otros_impuestos
    if (idx_special_acc_check === undefined) {
      // frm.doc.shs_pi_otros_impuestos.splice(frm.doc.shs_pi_otros_impuestos[index], 1);
      frm.get_field("shs_pi_otros_impuestos").grid.grid_rows[index].remove();
      frm.refresh_field("shs_pi_otros_impuestos");
    }
  });

  frm.refresh_field("shs_pi_otros_impuestos");
  pi_recalculate_other_taxes(frm);
}

/**
 * Genera iteraciones extra sobre los items, y asegurar calculos mas
 * precisos
 *
 * @param {Object} frm
 * @param {String} cdt
 * @param {String} cdn
 */
function pi_each_item(frm, cdt, cdn) {
  // console.log("Entro a pi_each_item", cdt);
  // Si se trabaja una fila individual se trabaja directamente sobre la fila manipulada
  if (cdt === "Purchase Invoice Item") {
    // console.log("Aplica para una sola fila");
    pi_get_special_tax_by_item(frm, cdt, cdn);
    shs_purchase_invoice_calculation(frm, cdt, cdn);
    pi_get_other_tax(frm, cdt, cdn);

    pi_recalculate_other_taxes(frm);
    pi_shs_total_other_tax(frm);
    pi_total_amount_by_item_type(frm);
  } else {
    // Si no es sobre una fila especifica, se itera cada fila de items y se recalcula
    // Aplica cuando se guarda un documento
    // var cdn
    cdt = "Purchase Invoice Item";
    frm.refresh_field("items");
    frm.doc.items.forEach((item_row, index) => {
      cdn = item_row.name;
      pi_get_special_tax_by_item(frm, cdt, cdn);
      shs_purchase_invoice_calculation(frm, cdt, cdn);
      pi_get_other_tax(frm, cdt, cdn);
    });

    pi_recalculate_other_taxes(frm);
    pi_shs_total_other_tax(frm);
    pi_total_amount_by_item_type(frm);
  }
  frm.refresh_field("items");
}

// ---------------------------------------------------------------------------------------------------------------------

/**
 * Funcion a evaluar por goalseek
 *
 * @param {*} a
 * @param {*} b
 * @return {*}
 */
function redondeo_sales_invoice(a, b) {
  return a * b;
}

/**
 * Agrega boton para generar facturas especiales electronicas, si ocurre un error
 * mostrara un mensaje con la descripcion, si todo va bien automaticamente se reemplazara
 * la pagina con los datos correctos
 *
 * @param {object} frm
 */
function btn_factura_especial(frm) {
  cur_frm.clear_custom_buttons();
  frm
    .add_custom_button(__("GENERAR FACTURA ESPECIAL ELECTRONICA FEL"), function () {
      frappe.confirm(__("Are you sure you want to proceed to generate a Electronic Special Invoice?"), () => {
        frappe.call({
          method: "factura_electronica.fel_api.fel_generator",
          args: {
            doctype: frm.doc.doctype,
            docname: frm.doc.name,
            type_doc: "factura_especial",
          },
          freeze: true,
          freeze_message: __("Generando Factura Especial FEL"),
          callback: function ({ message }) {
            // console.log(r.message);
            msg_generator(frm, message, "Purchase Invoice");
          },
        });
      });
    })
    .addClass("btn-warning");
}

// NOTA: REVISAR ESTA FUNCIONALIDAD CON UN CONTADOR
/**
 * Agrega un boton para generar especificamente polizas contables para facturas especiales
 *
 * @param {object} frm
 */
function btn_poliza_factura_especial(frm) {
  cur_frm.page.add_action_item(__("Journal Entry for Special Invoice"), function () {
    let d = new frappe.ui.Dialog({
      title: "New Journal Entry with Withholding Tax for special invoice",
      fields: [
        {
          label: "Cost Center",
          fieldname: "cost_center",
          fieldtype: "Link",
          options: "Cost Center",
          get_query: function () {
            return {
              filters: {
                company: frm.doc.company,
              },
            };
          },
          default: "",
        },
        {
          label: "Source account",
          fieldname: "credit_in_acc_currency",
          fieldtype: "Link",
          options: "Account",
          reqd: 1,
          get_query: function () {
            return {
              filters: {
                company: frm.doc.company,
              },
            };
          },
        },
        {
          fieldname: "col_br_asdffg",
          fieldtype: "Column Break",
        },
        {
          label: "Is Multicurrency",
          fieldname: "is_multicurrency",
          fieldtype: "Check",
        },
        {
          label: "NOTE",
          fieldname: "note",
          fieldtype: "Data",
          read_only: 1,
          default:
            "Los cálculos se realizaran correctamente si se encuentran configurados en company, y si el iva va incluido en la factura",
        },
        {
          label: "Description",
          fieldname: "section_asdads",
          fieldtype: "Section Break",
          collapsible: 1,
        },
        {
          label: "Description",
          fieldname: "description",
          fieldtype: "Long Text",
        },
      ],
      primary_action_label: "Create",
      primary_action(values) {
        frappe.call({
          method: "factura_electronica.api_erp.journal_entry_isr_purchase_inv",
          args: {
            invoice_name: frm.doc.name,
            cost_center: values.cost_center,
            credit_in_acc_currency: values.credit_in_acc_currency,
            is_multicurrency: values.is_multicurrency,
            description: values.description,
          },
          callback: function (r) {
            // console.log(r.message);
            d.hide();
            frm.refresh();
          },
        });
      },
    });

    d.show();
  });
}

/**
 * Render para boton nota de debito electronica
 *
 * @param {*} frm
 */
function btn_debit_note(frm) {
  // INICIO BOTON NOTA DE DEBITO
  cur_frm.clear_custom_buttons();
  frm
    .add_custom_button(__("GENERAR NOTA DE DEBITO ELECTRONICA FEL"), function () {
      // Permite hacer confirmaciones
      frappe.confirm(__("Are you sure you want to proceed to generate a electronic debit note?"), () => {
        let d = new frappe.ui.Dialog({
          title: __("Generate Electronic Debit Note"),
          fields: [
            {
              label: __("Reason Adjusment?"),
              fieldname: "reason_adjust",
              fieldtype: "Data",
              reqd: 1,
            },
          ],
          primary_action_label: __("Submit"),
          primary_action(values) {
            frappe.call({
              method: "factura_electronica.fel_api.fel_generator",
              args: {
                doctype: frm.doc.doctype,
                docname: frm.doc.name,
                type_doc: "nota_debito",
                reason: values.reason_adjust,
                uuid_purch_inv: frm.doc.bill_no,
                date_inv_origin: frm.doc.bill_date,
              },
              freeze: true,
              freeze_message: __("Generando Nota de Debito FEL"),
              callback: function ({ message }) {
                console.log(message);
                msg_generator(frm, message, "Purchase Invoice");
              },
            });

            d.hide();
          },
        });

        d.show();
      });
    })
    .addClass("btn-primary");
  // FIN BOTON NOTA DE DEBITO
}

/**
 * Render para boton pdf doc electronico
 *
 * @param {*} frm
 */
function pdf_electronic_doc(frm) {
  frm
    .add_custom_button(__("VER PDF DOCUMENTO ELECTRONICO"), function () {
      window.open(
        "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" + frm.doc.numero_autorizacion_fel
      );
    })
    .addClass("btn-primary");
}

/**
 * LLimpia campos con data no necesaria al momento de duplicar
 *
 * @param {*} frm
 */
function clean_fields(frm) {
  // Funcionalidad evita copiar CAE cuando se duplica una factura
  // LIMPIA/CLEAN, permite limpiar los campos cuando se duplica una factura
  if (frm.doc.status === "Draft" || frm.doc.docstatus == 0) {
    // console.log('No Guardada');
    frm.set_value("facelec_tax_retention_guatemala", "");
    frm.set_value("numero_autorizacion_fel", "");
    frm.set_value("serie_original_del_documento", "");

    // frm.refresh_fields();
  }
}

/**
 * Render boton para anular docs en SI
 *
 * @param {*} frm
 */
function btn_pi_canceller(frm) {
  cur_frm.clear_custom_buttons();
  frm
    .add_custom_button(__("CANCEL DOCUMENT FEL"), function () {
      // Permite hacer confirmaciones
      frappe.confirm(__("Are you sure to cancel the current electronic document?"), () => {
        let d = new frappe.ui.Dialog({
          title: __("Cancel electronic document"),
          fields: [
            {
              label: __("Reason for cancellation?"),
              fieldname: "reason_cancelation",
              fieldtype: "Data",
              reqd: 1,
            },
          ],
          primary_action_label: __("Submit"),
          primary_action(values) {
            frappe.call({
              method: "factura_electronica.fel_api.fel_doc_canceller",
              args: {
                company: frm.doc.company,
                invoice_name: frm.doc.name,
                reason_cancelation: values.reason_cancelation || "Anulación",
                document: "Purchase Invoice",
              },
              freeze: true,
              freeze_message: __("Anulando Documento Electronico FEL"),
              callback: function (data) {
                console.log(data.message);
                // frm.reload_doc();
              },
            });

            d.hide();
          },
        });

        d.show();
      });
    })
    .addClass("btn-danger");
}

/**
 * Totaliza los montos de Combustible, Bienes, Servicio y otros impuestos especiales
 *
 * @param {*} frm
 */
function pi_total_amount_by_item_type(frm) {
  let fix_gt_tax_fuel = 0;
  let fix_gt_tax_goods = 0;
  let fix_gt_tax_services = 0;
  let fix_gt_tax_iva = 0;

  $.each(frm.doc.items || [], function (i, d) {
    fix_gt_tax_fuel += flt(d.facelec_p_gt_tax_net_fuel_amt);
    fix_gt_tax_goods += flt(d.facelec_p_gt_tax_net_goods_amt);
    fix_gt_tax_services += flt(d.facelec_p_gt_tax_net_services_amt);
    fix_gt_tax_iva += flt(d.facelec_p_sales_tax_for_this_row);
  });

  cur_frm.set_value("facelec_p_gt_tax_fuel", fix_gt_tax_fuel);
  frm.refresh_field("facelec_p_gt_tax_fuel");
  cur_frm.set_value("facelec_p_gt_tax_goods", fix_gt_tax_goods);
  frm.refresh_field("facelec_p_gt_tax_goods");
  cur_frm.set_value("facelec_p_gt_tax_services", fix_gt_tax_services);
  frm.refresh_field("facelec_p_gt_tax_services");
  cur_frm.set_value("facelec_p_total_iva", fix_gt_tax_iva);
  frm.refresh_field("facelec_p_total_iva");
}

/**
 * Renderiza tabla HTML con detalles de impuestos e impuestos especiales
 *
 * @param {*} frm
 */
function generar_tabla_html_factura_compra(frm) {
  // PURCHASE INVOICE
  if (frm.doc.items.length > 0) {
    const mi_array = frm.doc.items;
    const mi_array_dos = Array.from(mi_array);

    frappe.call({
      method: "factura_electronica.api.generar_tabla_html_factura_compra",
      args: {
        tabla: JSON.stringify(mi_array_dos),
        currency: frm.doc.currency,
      },
      callback: function (data) {
        frm.set_value("other_tax_facelec", data.message);
        frm.refresh_field("other_tax_facelec");
      },
    });
  }
}

/**
 * @summary Calculador de montos para generar documentos electronicos
 * @param {Object} frm - Propiedades del Doctype
 */
function purchase_invoice_calc(frm) {
  frappe.call({
    method: "factura_electronica.utils.calculator.purchase_invoice_calculator",
    args: {
      invoice_name: frm.doc.name,
    },
    freeze: true,
    freeze_message: __("Ejecutando Calculos..."),
    callback: (r) => {
      frm.reload_doc();
      // console.log("Purchase Invoice Calculated", r.message);
      // frm.save();
    },
    error: (r) => {
      // on error
      console.log("Purchase Invoice Calculated Error");
    },
  });
  frm.reload_doc();
}

/**
 * @summary Funcion para insertar cuentas de impuestos especiales y cuadrar en GL Entry
 * @param {Object} frm
 */
function special_pi_tax(frm) {
  // Creacion objeto vacio para guardar nombre y valor de las cuentas que se encuentren
  let cuentas_registradas = {};
  let otrosImpuestos = frm.doc.shs_pi_otros_impuestos || [];

  // Recorre la tabla hija en busca de cuentas
  otrosImpuestos.forEach((tax_row, index) => {
    if (tax_row.account_head) {
      // Agrega un nuevo valor al objeto (JSON-DICCIONARIO) con el
      // nombre, valor de la cuenta
      cuentas_registradas[tax_row.account_head] = tax_row.total;
    }
  });

  // Si existe por lo menos una cuenta, se ejecuta frappe.call
  if (Object.keys(cuentas_registradas).length > 0) {
    frappe.call({
      method: "factura_electronica.utils.special_tax.add_gl_entry_other_special_tax",
      args: {
        invoice_name: frm.doc.name,
        accounts: cuentas_registradas,
        invoice_type: "Purchase Invoice",
        is_return: frm.doc.is_return,
      },
      // El callback se ejecuta tras finalizar la ejecucion del script python del lado
      // del servidor
      callback: function () {
        frm.reload_doc();
      },
    });
  }
}

/**
 * @summary Validador escenario para generar botones segun la serie seleccionada
 * @param {Object} frm
 */
function btn_pi_generator(frm) {
  frappe.call({
    method: "factura_electronica.fel_api.btn_validator",
    args: {
      doctype: frm.doc.doctype,
      docname: frm.doc.name,
    },
    callback: function ({ message }) {
      const { type_doc, show_btn } = message;

      console.log("Tipo de Doc: ", type_doc, "Mostrar Boton: ", show_btn);

      if (!type_doc) {
        // Si no hay dato no se muestra ningun btn generador
        return;
      }

      // Factura Especial
      if (type_doc === "factura_especial") {
        btn_factura_especial(frm);
        if (frm.doc.numero_autorizacion_fel) {
          cur_frm.clear_custom_buttons();
          pdf_electronic_doc(frm);

          // nota: revisar este generador con un contador
          // btn_poliza_factura_especial(frm);
        }
      }

      // Nota de Debito
      if (type_doc === "nota_debito") {
        btn_debit_note(frm);
        if (frm.doc.numero_autorizacion_fel) {
          cur_frm.clear_custom_buttons();
          pdf_electronic_doc(frm);
        }
      }

      // Anulador de docs
      if (type_doc === "anulador_pi") {
        if (show_btn == false) {
          // Si ya esta cancelada
          // Si ya se genero se muestra el btn para ver pdf
          if (frm.doc.numero_autorizacion_fel) {
            cur_frm.clear_custom_buttons();
            pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
          }
        }
        if (show_btn == true) {
          btn_pi_canceller(frm);
          pdf_electronic_doc(frm);
        }
      }
    },
  });
}

frappe.ui.form.on("Purchase Invoice", {
  refresh: function (frm, cdt, cdn) {
    frm.set_df_property(
      "bill_no",
      "description",
      __("<b>FEL: UUID de factura original</b>, dato necesario para Nota de Debito Electronica")
    );
    frm.set_df_property(
      "bill_date",
      "description",
      __("<b>FEL: Fecha de factura original</b>, dato necesario para Nota de Debito Electronica")
    );
    // frm.set_df_property("shs_pi_otros_impuestos", "read_only", 1); NOTA: si se descomenta no se agregaran correctamente las filas de otros impuestos

    // Validador para mostrar botones segun el escenario que aplique
    if (frm.doc.docstatus != 0) {
      btn_pi_generator(frm);
    }
  },
  onload_post_render: function (frm, cdt, cdn) {
    // NOTA: LOS LISTENER YA NO TIENE EL MISMO FUNCIONAMIENTO QUE EN VERSIONES ANTERIORES
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
    // pi_each_item(frm, cdt, cdn);
    generar_tabla_html_factura_compra(frm);
  },
  // Se ejecuta despues de guardar
  after_save: function (frm, cdt, cdn) {
    purchase_invoice_calc(frm);
  },
  validate: function (frm, cdt, cdn) {
    generar_tabla_html_factura_compra(frm);

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
  on_submit: function (frm, cdt, cdn) {
    // Ocurre cuando se presione el boton validar.
    // Cuando se valida el documento, se hace la consulta al servidor por medio de frappe.call
    special_pi_tax(frm);
  },
});

frappe.ui.form.on("Purchase Invoice Item", {
  shs_amount_for_back_calc: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    var a = row.rate;
    var b = row.qty;
    var c = row.amount;

    let calcu = goalSeek({
      Func: redondeo_sales_invoice,
      aFuncParams: [b, a],
      oFuncArgTarget: {
        Position: 0,
      },
      Goal: row.shs_amount_for_back_calc,
      Tol: 0.001,
      maxIter: 10000,
    });
    // console.log(calcu);

    // frm.doc.items[index].qty = calcu;
    frappe.model.set_value(row.doctype, row.name, "qty", flt(calcu));
    // frm.doc.items[index].stock_qty = calcu;
    frappe.model.set_value(row.doctype, row.name, "stock_qty", flt(calcu));
    // frm.doc.items[index].amount = calcu * frm.doc.items[index].rate;
    frappe.model.set_value(row.doctype, row.name, "amount", flt(calcu * a));

    frm.refresh_field("items");

    pi_calc_row_discount(frm, cdt, cdn);
  },
  facelec_discount_amount: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    let new_rate = row.rate - row.facelec_discount_amount;
    row.rate = new_rate;
    frm.refresh_field("items");

    pi_calc_row_discount(frm, cdt, cdn);
  },
  qty: function (frm, cdt, cdn) {
    pi_calc_row_discount(frm, cdt, cdn);
  },
  rate: function (frm, cdt, cdn) {
    // Si hay algun cambio en el precio se vuelve a establecer a 0 el descuento
    let row = frappe.get_doc(cdt, cdn);
    row.facelec_discount_amount = 0;
    row.facelec_row_discount = 0;
    row.facelec_discount_account = "";
    frm.refresh_field("items");

    pi_calc_row_discount(frm, cdt, cdn);
  },
});

/**
 * @summary Calcula el descuento por fila
 * @param {frm}
 * @param {cdt}
 * @param {cdn}
 */
function pi_calc_row_discount(frm, cdt, cdn) {
  // console.log("calculos desc por fila");
  let row = frappe.get_doc(cdt, cdn);
  // Se calcula el descuento por fila
  row.facelec_row_discount = row.facelec_discount_amount * row.qty;
  frm.refresh_field("items");
}
