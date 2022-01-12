/**
 * Copyright (c) 2021 Si Hay Sistema and contributors
 * For license information, please see license.txt
 */

import { valNit } from "./facelec.js";
import { goalSeek } from "./goalSeek.js";

/**
 * @summary Ejecuta serialmente las funciones de calculos, para obtener siempre los ultimos valores
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} cdt - Current DocType
 * @param {object} cdn - Current DocName
 */
function each_row(frm, cdt, cdn) {
  // console.log("Recalculando... Sales Invoice");

  if (cdt === "Sales Invoice Item") {
    // Si es una especifica fila de items
    get_special_tax_by_item(frm, cdt, cdn);
    sales_invoice_calculations(frm, cdt, cdn);
    get_other_tax(frm, cdt, cdn);

    recalculate_other_taxes(frm);
    shs_total_other_tax(frm);
    shs_total_iva(frm);
  } else {
    // var cdn;
    cdt = "Sales Invoice Item";
    // Si no es una fila especifica, se iteran todas y se realizan los calculos
    frm.refresh_field("items");
    frm.doc.items.forEach((item_row, index) => {
      cdn = item_row.name;
      // console.log("Recalculando... ", item_row.item_code);
      get_special_tax_by_item(frm, cdt, cdn);
      sales_invoice_calculations(frm, cdt, cdn);
      get_other_tax(frm, cdt, cdn);
    });

    recalculate_other_taxes(frm);
    shs_total_other_tax(frm);
    shs_total_iva(frm);
  }
  frm.refresh_field("items");
}

/**
 * @summary Realiza los calculos de impuestos de la factura que serviran para la generación de factura electrónica
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} row - Objeto que contiene todas las propiedades de la fila de items que se este manipulando
 */
function sales_invoice_calculations(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);

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
  // FIN validacion existencia tabla impuesto

  let amount_minus_excise_tax = 0;
  let other_tax_amount = 0;
  let net_fuel = 0;
  let net_services = 0;
  let net_goods = 0;
  let tax_for_this_row = 0;

  // We change the fields for other tax amount as per the complete row taxable amount.
  other_tax_amount = flt(row.facelec_tax_rate_per_uom * row.qty * row.conversion_factor);
  frappe.model.set_value(row.doctype, row.name, "facelec_other_tax_amount", other_tax_amount);

  // * row.stock_qty --> Al usar stock_qty los calculos no se realizan correctamente ya que se carga demasiado lento el valor
  amount_minus_excise_tax = flt(row.qty * row.rate - row.qty * flt(row.facelec_tax_rate_per_uom));
  frappe.model.set_value(row.doctype, row.name, "facelec_amount_minus_excise_tax", amount_minus_excise_tax);

  // Verificacion Individual para verificar si es Fuel, Good o Service y realizar los calculos correspondientes
  if (row.factelecis_fuel && row.item_code) {
    net_services = 0;
    net_goods = 0;
    net_fuel = flt(row.facelec_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100));
    frappe.model.set_value(row.doctype, row.name, "facelec_gt_tax_net_fuel_amt", flt(net_fuel));

    tax_for_this_row = flt(row.facelec_gt_tax_net_fuel_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(row.doctype, row.name, "facelec_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de bienes y servicios se resetean a 0
    frappe.model.set_value(row.doctype, row.name, "facelec_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(row.doctype, row.name, "facelec_gt_tax_net_services_amt", flt(net_services));
  }

  tax_for_this_row = 0;
  if (row.facelec_is_good && row.item_code) {
    net_services = 0;
    net_fuel = 0;
    net_goods = flt(row.facelec_amount_minus_excise_tax / (1 + this_company_sales_tax_var / 100));
    frappe.model.set_value(row.doctype, row.name, "facelec_gt_tax_net_goods_amt", flt(net_goods));

    tax_for_this_row = flt(row.facelec_gt_tax_net_goods_amt * (this_company_sales_tax_var / 100));
    frappe.model.set_value(row.doctype, row.name, "facelec_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de servicios y combustibles se resetean a 0
    frappe.model.set_value(row.doctype, row.name, "facelec_gt_tax_net_services_amt", flt(net_services));
    frappe.model.set_value(row.doctype, row.name, "facelec_gt_tax_net_fuel_amt", flt(net_fuel));
  }

  tax_for_this_row = 0;
  if (row.facelec_is_service && row.item_code) {
    net_fuel = 0;
    net_goods = 0;
    net_services = flt(row.facelec_amount_minus_excise_tax / flt(1 + this_company_sales_tax_var / 100));
    frappe.model.set_value(row.doctype, row.name, "facelec_gt_tax_net_services_amt", flt(net_services));

    // frm.refresh_field('items');

    tax_for_this_row = flt(row.facelec_gt_tax_net_services_amt * flt(this_company_sales_tax_var / 100));
    frappe.model.set_value(row.doctype, row.name, "facelec_sales_tax_for_this_row", flt(tax_for_this_row));

    // Los campos de bienes y combustibles se resetean a 0
    frappe.model.set_value(row.doctype, row.name, "facelec_gt_tax_net_goods_amt", flt(net_goods));
    frappe.model.set_value(row.doctype, row.name, "facelec_gt_tax_net_fuel_amt", flt(net_fuel));
  }

  frm.refresh_field("items");
}

/**
 * @summary Obtiene las cuenta configuradas y monto de impuestos especiales de X item en caso sea de tipo Combustible
 * @param {object} frm - Objeto que contiene todas las propiedades del doctype
 * @param {object} row - Objeto que contiene todas las propiedades de la fila de items que se este manipulando
 */
function get_special_tax_by_item(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);

  frm.refresh_field("items");
  if (row.factelecis_fuel && row.item_code) {
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
          frappe.model.set_value(row.doctype, row.name, "facelec_tax_rate_per_uom", flt(r.message.facelec_tax_rate_per_uom));
          frappe.model.set_value(
            row.doctype,
            row.name,
            "facelec_tax_rate_per_uom_account",
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
    frappe.model.set_value(row.doctype, row.name, "facelec_tax_rate_per_uom", flt(0));
    frappe.model.set_value(row.doctype, row.name, "facelec_tax_rate_per_uom_account", "");
    frm.refresh_field("items");
  }
}

/**
 * @summary Funcion para evaluar goalseek
 *
 * @param {*} a
 * @param {*} b
 * @return {*} monto
 */
function funct_eval(a, b) {
  return a * b;
}

/**
 * @summary Limpia los campos con data no necesaria, al momento de duplicar
 *
 * @param {*} frm
 */
function clean_fields(frm) {
  // Funcionalidad evita copiar CAE cuando se duplica una factura
  // LIMPIA/CLEAN, permite limpiar los campos cuando se duplica una factura
  if (frm.doc.status === "Draft" || frm.doc.docstatus == 0) {
    // console.log('No Guardada');
    frm.set_value("cae_factura_electronica", "");
    frm.set_value("serie_original_del_documento", "");
    frm.set_value("numero_autorizacion_fel", "");
    frm.set_value("facelec_s_vat_declaration", "");
    // cur_frm.set_value("ag_invoice_id", '');
    frm.set_value("facelec_tax_retention_guatemala", "");
    frm.set_value("facelec_export_doc", "");
    frm.set_value("facelec_export_record", "");
    frm.set_value("facelec_record_type", "");
    frm.set_value("facelec_consumable_record_type", "");
    frm.set_value("facelec_record_number", "");
    frm.set_value("facelec_record_value", "");
    frm.set_value("access_number_fel", "");
    // frm.refresh_fields();
  }
}

/**
 * @summary Generador boton para anular documentos electronicos
 *
 * @param {*} frm
 */
function btn_canceller(frm) {
  cur_frm.clear_custom_buttons();
  frm
    .add_custom_button(__("Electronic Document Canceller"), function () {
      // Permite hacer confirmaciones
      frappe.confirm(
        __("Are you sure to cancel the current electronic document?"),
        () => {
          let d = new frappe.ui.Dialog({
            title: __("Electronic Document Canceller"),
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
                method: "factura_electronica.fel_api.invoice_canceller",
                args: {
                  invoice_name: frm.doc.name,
                  reason_cancelation: values.reason_cancelation || "Anulación",
                  document: "Sales Invoice",
                },
                callback: function (data) {
                  // console.log(data.message);
                  frm.reload_doc();
                },
              });

              d.hide();
            },
          });

          d.show();
        },
        () => {
          // action to perform if No is selected
          // console.log('Selecciono NO')
        }
      );
    })
    .addClass("btn-danger");
}

/**
 * @summary Generador boton para FEL normal
 *
 * @param {*} tipo_factura
 * @param {*} frm
 */
function generar_boton_factura(tipo_factura, frm) {
  frm
    .add_custom_button(__(tipo_factura), function () {
      // frm.reload(); permite hacer un refresh de todo el documento
      frm.reload_doc();
      let serie_de_factura = frm.doc.name;
      // Guarda la url actual
      let mi_url = window.location.href;
      frappe.call({
        method: "factura_electronica.fel_api.api_interface",
        args: {
          invoice_code: frm.doc.name,
          naming_series: frm.doc.naming_series,
        },
        // El callback recibe como parametro el dato retornado por el script python del lado del servidor
        // para validar si se genero correctamente la factura electronica
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
        },
      });
    })
    .addClass("btn-primary"); //NOTA: Se puede crear una clase para el boton CSS
}

/**
 * @summary Generador de boton para factura de exportacion, cuando se pulsa
 * hace una peticion a la funcion generate_export_invoice y esta a la
 * vez genera la peticion a INFILE con los datos de la factura
 *
 * @param {*} frm
 */
function btn_export_invoice(frm) {
  cur_frm.clear_custom_buttons(); // Limpia otros customs buttons para generar uno nuevo
  frm
    .add_custom_button(__("FACTURA ELECTRONICA EXPORTACION FEL"), function () {
      frappe.call({
        method: "factura_electronica.fel_api.api_interface_export",
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
          }
        },
      });
    })
    .addClass("btn-primary");
}

/**
 * @summary Render para boton notas de credito electronicas
 *
 * @param {*} frm
 */
function btn_credit_note(frm) {
  cur_frm.clear_custom_buttons();
  frm
    .add_custom_button(__("CREDIT NOTE FEL"), function () {
      // Permite hacer confirmaciones
      frappe.confirm(
        __("Are you sure you want to proceed to generate a credit note?"),
        () => {
          let d = new frappe.ui.Dialog({
            title: __("Generate Credit Note"),
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
              let serie_de_factura = frm.doc.name;
              // Guarda la url actual
              let mi_url = window.location.href;

              frappe.call({
                method: "factura_electronica.fel_api.generate_credit_note",
                args: {
                  invoice_code: frm.doc.name,
                  naming_series: frm.doc.naming_series,
                  reference_inv: frm.doc.return_against,
                  reason: values.reason_adjust,
                },
                callback: function (data) {
                  console.log(data.message);
                  if (data.message[0] === true) {
                    // Crea una nueva url con el nombre del documento actualizado
                    let url_nueva = mi_url.replace(serie_de_factura, data.message[1]);
                    // Asigna la nueva url a la ventana actual
                    window.location.assign(url_nueva);
                    // Recarga la pagina
                    frm.reload_doc();
                  }
                },
              });

              d.hide();
            },
          });

          d.show();
        },
        () => {
          // action to perform if No is selected
          // console.log('Selecciono NO')
        }
      );
    })
    .addClass("btn-primary");
}

/**
 * @summary Generador de boton para factura exenta de impuestos
 *
 * @param {*} frm
 */
function btn_exempt_invoice(frm) {
  cur_frm.clear_custom_buttons(); // Limpia otros customs buttons para generar uno nuevo

  frm
    .add_custom_button(__("FACTURA ELECTRONICA EXENTA"), function () {
      show_alert("Trabajo en progreso, opcion no disponible", 5);

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
    })
    .addClass("btn-primary");
}

/**
 * @summary Generador de boton retenciones de impuestos IVA/ISR
 *
 * @param {*} frm
 */
function btn_journal_entry_retention(frm) {
  cur_frm.page.add_action_item(__("AUTOMATED RETENTION"), function () {
    let d = new frappe.ui.Dialog({
      title: __("New Journal Entry with Withholding Tax"),
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
          label: "Target account",
          fieldname: "debit_in_acc_currency",
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
          label: "Applies for VAT withholding",
          fieldname: "is_iva_withholding",
          fieldtype: "Check",
        },
        {
          label: "Applies for ISR withholding",
          fieldname: "is_isr_withholding",
          fieldtype: "Check",
        },
        {
          label: "NOTE",
          fieldname: "note",
          fieldtype: "Data",
          read_only: 1,
          default:
            "Los cálculos se realizaran correctamente si se encuentran configurados en company, y si el IVA va incluido en la factura",
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
          method: "factura_electronica.api_erp.journal_entry_isr",
          args: {
            invoice_name: frm.doc.name,
            debit_in_acc_currency: values.debit_in_acc_currency,
            cost_center: values.cost_center,
            is_isr_ret: parseInt(values.is_isr_withholding),
            is_iva_ret: parseInt(values.is_iva_withholding),
            is_multicurrency: parseInt(values.is_multicurrency),
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
 * @summary Generador de boton facturas cambiarias
 *
 * @param {*} frm
 */
function btn_exchange_invoice(frm) {
  cur_frm.clear_custom_buttons(); // Limpia otros customs buttons para generar uno nuevo
  frm
    .add_custom_button(__("FACTURA CAMBIARIA FEL"), function () {
      frappe.call({
        method: "factura_electronica.fel_api.generate_exchange_invoice_si",
        args: {
          invoice_code: frm.doc.name,
          naming_series: frm.doc.naming_series,
        },
        callback: function (data) {
          console.log(data.message);
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
          }
        },
      });
    })
    .addClass("btn-primary");
}

/**
 * @summary Generador de boton que visualiza PDF doc electronico
 *
 * @param {*} cae_documento
 * @param {*} frm
 */
function pdf_button_fel(cae_documento, frm) {
  // Esta funcion se encarga de mostrar el boton para obtener el pdf de la factura electronica generada
  // aplica para fel, y anuladas
  frm
    .add_custom_button(__("VER PDF DOCUMENTO ELECTRÓNICO"), function () {
      window.open("https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" + cae_documento);
    })
    .addClass("btn-primary");
}

/**
 * @summary Generador de boton para visualizar pdf nota credito electronica
 *
 * @param {*} frm
 */
function pdf_credit_note(frm) {
  cur_frm.clear_custom_buttons();
  frm
    .add_custom_button(__("VER PDF NOTA CREDITO ELECTRONICA"), function () {
      window.open(
        "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" + frm.doc.numero_autorizacion_fel
      );
    })
    .addClass("btn-primary");
}

/**
 * @summary Generador tabla HTML con detalles de impuestos e impuestos especiales
 *
 * @param {*} frm
 */
function generar_tabla_html(frm) {
  if (frm.doc.items.length > 0) {
    const mi_array = frm.doc.items;
    const mi_array_dos = Array.from(mi_array);
    // console.log(mi_array_dos);
    frappe.call({
      method: "factura_electronica.api.generar_tabla_html",
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
 * @summary Si ya existe una cuenta en shs_otros_impuestos se iteran todos los items en busca de aquellas filas que tenga una
 * una cuenta de impuesto especial y recalcular el total por cuenta
 * y asi asegurar que esten correctos los valores si el usuario hace cambios
 *
 * @param {object} frm - Objeto con las propiedades del doctype
 */
function recalculate_other_taxes(frm) {
  frm.refresh_field("shs_otros_impuestos");
  frm.refresh_field("items");

  let items_invoice = frm.doc.items || [];
  items_invoice.forEach((item_row, index) => {
    // console.log("Esta es la cuenta en la iteracion", item_row.facelec_tax_rate_per_uom_account)
    // Si la fila iterada tiene una cuenta de impuesto especial y en la tabla hija de shs_otros_impuestos hay filas
    if (item_row.facelec_tax_rate_per_uom_account && frm.doc.shs_otros_impuestos) {
      // Busca si la cuenta iterada existe en shs_otros_impuestos, si existe se volvera a iterar items y totalizar por cuenta
      // si no existe se eliminara de shs_otros_impuestos
      let total_by_account = 0;
      let idx_acc_check = frm.doc.shs_otros_impuestos.find(
        (el) => el["account_head"] === item_row.facelec_tax_rate_per_uom_account
      );

      if (idx_acc_check) {
        frm.refresh_field("shs_otros_impuestos");
        frappe.model.set_value("Otros Impuestos Factura Electronica", idx_acc_check.name, "total", total_by_account);

        items_invoice.forEach((item_row_x, index_x) => {
          if (item_row_x.facelec_tax_rate_per_uom_account === item_row.facelec_tax_rate_per_uom_account) {
            total_by_account += flt(item_row_x.facelec_other_tax_amount);
          }
        });

        frm.refresh_field("shs_otros_impuestos");
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
function shs_total_other_tax(frm) {
  frm.refresh_field("shs_otros_impuestos");

  let otros_impuestos = frm.doc.shs_otros_impuestos || [];

  if (otros_impuestos.length > 0) {
    let total_tax = otros_impuestos
      .map((o) => o.total)
      .reduce((a, c) => {
        return a + c;
      });
    cur_frm.set_value("shs_total_otros_imp_incl", flt(total_tax));
    frm.refresh_field("shs_total_otros_imp_incl");
  } else {
    cur_frm.set_value("shs_total_otros_imp_incl", 0);
    frm.refresh_field("shs_total_otros_imp_incl");
  }
}

/**
 * @summary Suma el total de IVA
 *
 * @param {*} frm
 */
function shs_total_iva(frm) {
  frm.refresh_field("items");
  frm.refresh_field("shs_total_iva_fac");

  let items_ok = frm.doc.items || [];
  if (items_ok.length > 0) {
    let total_iva = items_ok
      .map((o) => o.facelec_sales_tax_for_this_row)
      .reduce((a, c) => {
        return a + c;
      });
    cur_frm.set_value("shs_total_iva_fac", flt(total_iva) || 0);
    frm.refresh_field("shs_total_iva_fac");
  } else {
    cur_frm.set_value("shs_total_iva_fac", 0);
    frm.refresh_field("shs_total_iva_fac");
  }
}

/**
 * @summary Si la fila de items que se esta manipulando tiene una cuenta de impuesto especial,
 * se recalcula el total de impuesto y se agrega a la tabla hija shs_otros_impuestos
 * Solo y solo si no esta agregada en la tabla hija shs_otros_impuestos
 *
 * @param {*} frm
 * @param {*} cdt
 * @param {*} cdn
 */
function get_other_tax(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);

  // 1. Se valida que la fila que se esta manipulando tenga una cuenta de impuesto especial
  frm.refresh_field("items");

  if (row.facelec_tax_rate_per_uom_account) {
    // 2. Se valida si la cuenta ya existe en shs_otros_impuestos si no existe se agrega
    // Si ya existe se iteran todos los items en busca de aquellas filas que tenga una
    // cuenta de impuesto especial para recalcular el total por cuenta y por fila de shs_otros_impuestos
    let otros_impuestos = frm.doc.shs_otros_impuestos || [];

    // Validador si la cuenta iterada existe en shs_otros_impuestos True/False
    let acc_check = otros_impuestos.some(function (el) {
      return el.account_head === row.facelec_tax_rate_per_uom_account && row.facelec_tax_rate_per_uom_account;
    });

    let shs_otro_impuesto = row.facelec_other_tax_amount;

    // Si no existe en la tabla hija shs_otros_impuestos se agrega
    if (!acc_check) {
      frm.add_child("shs_otros_impuestos", {
        account_head: row.facelec_tax_rate_per_uom_account,
        total: shs_otro_impuesto,
      });

      frm.refresh_field("shs_otros_impuestos");
    }
  }
}

/**
 * @summary Cada vez que se elimina una fila, recorre la tabla hija shs_otros_impuestos
 * y los compara con las filas existentes en items, si la cuenta que se esta iterando
 * no existe en items, se elimina
 *
 * @param {*} frm
 */
function remove_non_existing_taxes(frm) {
  // Se vuelve a verificar que existan filas en shs_otros_impuestos, si no hay se retorna
  frm.refresh_field("shs_otros_impuestos");
  let otros_impuestos = frm.doc.shs_otros_impuestos || [];
  if (otros_impuestos.length == 0) return;

  // Se itera shs_otros_impuestos y cada fila se compara con items, si la cuenta de la fila no existe en items se elimina
  frm.refresh_field("items");

  let idx_special_acc_check;
  otros_impuestos.forEach((tax_row, index) => {
    idx_special_acc_check = frm.doc.items.find((el) => el["facelec_tax_rate_per_uom_account"] === tax_row.account_head);

    // Si la fila iterada no tiene ninguna relacion con la tabla hija items se elimina de shs_otros_impuestos
    if (idx_special_acc_check === undefined) {
      // console.log("Hay que eliminar", otros_impuestos[index].account_head)
      frm.get_field("shs_otros_impuestos").grid.grid_rows[index].remove();
      frm.refresh_field("shs_otros_impuestos");
    }
  });
  frm.refresh_field("shs_otros_impuestos");
  recalculate_other_taxes(frm);
}

/* Factura de Ventas-------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Sales Invoice", {
  // Se ejecuta cuando se renderiza el doctype
  onload_post_render: function (frm, cdt, cdn) {
    // Limpia los campos con datos no necesarios cuando se duplica una factura
    clean_fields(frm);
  },
  // Se ejecuta cuando hay alguna actualizacion de datos en el doctype
  refresh: function (frm, cdt, cdn) {
    // es-GT: Obtiene el numero de Identificacion tributaria ingresado en la hoja del cliente.
    // en-US: Fetches the Taxpayer Identification Number entered in the Customer doctype.
    cur_frm.add_fetch("customer", "nit_face_customer", "nit_face_customer");
    // frm.set_df_property("shs_otros_impuestos", "read_only", 1);

    if (frm.doc.docstatus != 0) {
      // INICIO VALIDACION DE ESCENARIOS PARA MOSTRAR LOS BOTOTNES GENERADORES DOCS ELECTRONICOS ADECUADOS
      // El documento debe estar guardado para que la funcion is_valid_to_fel valide correctamente el escenario
      frappe.call({
        method: "factura_electronica.fel_api.is_valid_to_fel",
        args: {
          doctype: frm.doc.doctype,
          docname: frm.doc.name,
        },
        callback: function (r) {
          // DEBUG: usar para ver si aplica
          // console.log(r.message);

          // SI APLICA EL ESCENARIO MUESTRA EL BOTON PARA ANULAR DOCS ELECTRONICOS
          // Solo si el documento actual ya fue generado anteriormente como electronico
          if (r.message[1] === "anulador" && r.message[2]) {
            frappe
              .call("factura_electronica.api.btn_activator", {
                electronic_doc: "anulador_de_facturas_ventas_fel",
              })
              .then((r) => {
                // console.log(r.message)
                if (r.message) {
                  // Si la anulacion electronica ya fue realizada, se mostrara boton para ver pdf doc anulado
                  frappe
                    .call("factura_electronica.api.invoice_exists", {
                      uuid: frm.doc.numero_autorizacion_fel,
                    })
                    .then((r) => {
                      // console.log(r.message)
                      if (r.message) {
                        cur_frm.clear_custom_buttons();
                        pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
                      } else {
                        // SI no aplica lo anterior se muestra btn para anular doc
                        btn_canceller(frm);
                        pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
                      }
                    });
                }
              });
          }

          // SI APLICA EL ESCENARIO MUESTRA EL BOTON PARA Generación Facturas Electrónicas FEL - Normal Type
          if (r.message[0] === "FACT" && r.message[2]) {
            generar_boton_factura(__("Factura Electrónica FEL"), frm);
            if (frm.doc.numero_autorizacion_fel) {
              cur_frm.clear_custom_buttons();
              pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
            }
          }

          // SI APLICA EL ESCENARIO MUESTRA EL BOTON PARA Generación Facturas Electrónicas FEL - Exportación
          if (r.message[0] === "FACT" && r.message[1] == "export") {
            btn_export_invoice(frm);
            if (frm.doc.numero_autorizacion_fel) {
              cur_frm.clear_custom_buttons();
              pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
            }
          }

          // SI APLICA EL ESCENARIO MUESTRA EL BOTON PARA Generación Nota Credito Electronica
          if (r.message[0] === "NCRE" && r.message[1] === "valido" && r.message[2]) {
            btn_credit_note(frm);
            if (frm.doc.numero_autorizacion_fel) {
              cur_frm.clear_custom_buttons();
              pdf_credit_note(frm);
            }
          }

          // SI APLICA EL ESCENARIO MUESTRA EL BOTON PARA  Generación Factura Cambiaria
          if (r.message[0] === "FCAM" && r.message[1] === "valido" && r.message[2]) {
            btn_exchange_invoice(frm);
            if (frm.doc.numero_autorizacion_fel) {
              cur_frm.clear_custom_buttons();
              pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
            }
          }
        },
      });
      // FIN BOTONES GENERADORES DOCS ELECTRONICOS

      // INICIO GENERACION POLIZA CON RETENCIONES
      // TODO:AGREGAR VALIDACION EXISTENCIA DE JOURNA ENTRY
      if (frm.doc.docstatus === 1 && frm.doc.status !== "Paid") {
        btn_journal_entry_retention(frm);
      }
      // FIN GENERACION POLIZA CON RETENCIONES
    }
  },
  // Se ejecuta al presionar el boton guardar
  validate: function (frm, cdt, cdn) {
    // console.log('validate');
    // Asegura que los montos de impuestos especiales se calculen correctamente
    each_row(frm, cdt, cdn);
    remove_non_existing_taxes(frm);
    generar_tabla_html(frm);

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
  // Se ejecuta si se modifica el nit del cliente
  // NOTA: No se tiene activo, ya que pueden haber docs de clientes de otros paises
  nit_face_customer: function (frm, cdt, cdn) {
    // Para evitar retrasos la validacion se realiza desde customer dt
    // valNit(frm.doc.nit_face_customer, frm.doc.customer, frm);
  },
  // TODO: PROBAR
  additional_discount_percentage: function (frm, cdt, cdn) {
    // Pensando en colocar un trigger aqui para cuando se actualice el campo de descuento adicional
  },
  discount_amount: function (frm, cdt, cdn) {
    // Trigger Monto de descuento
    var tax_before_calc = frm.doc.facelec_total_iva;
    //console.log("El descuento total es:" + frm.doc.discount_amount);
    // es-GT: Este muestra el IVA que se calculo por medio de nuestra aplicación.
    //console.log("El IVA calculado anteriormente:" + frm.doc.facelec_total_iva);
    var discount_amount_net_value = frm.doc.discount_amount / (1 + cur_frm.doc.taxes[0].rate / 100);

    if (discount_amount_net_value == NaN || discount_amount_net_value == undefined) {
      //console.log("No hay descuento definido, calculando sin descuento.");
    } else {
      //console.log("El descuento parece ser un numero definido, calculando con descuento.");
      var discount_amount_tax_value = discount_amount_net_value * (cur_frm.doc.taxes[0].rate / 100);
      //console.log("El IVA del descuento es:" + discount_amount_tax_value);
      frm.doc.facelec_total_iva = frm.doc.facelec_total_iva - discount_amount_tax_value;
      //console.log("El IVA ya sin el iva del descuento es ahora:" + frm.doc.facelec_total_iva);
    }
  },
  // Se ejecuta antes de guardar el documento
  before_save: function (frm, cdt, cdn) {
    // each_row(frm, cdt, cdn);
  },
  // Se ejecuta al validar el documento
  on_submit: function (frm, cdt, cdn) {
    // Ocurre cuando se presione el boton validar. para agregar al GL los impuestos especiales
    // console.log('on submit')

    // Creacion objeto vacio para guardar nombre y valor de las cuentas que se encuentren
    let cuentas_registradas = {};
    let otrosimpuestos = frm.doc.shs_otros_impuestos || [];
    // Recorre la tabla hija en busca de cuentas
    otrosimpuestos.forEach((tax_row, index) => {
      if (tax_row.account_head) {
        // Agrega un nuevo valor al objeto (JSON-DICCIONARIO) con el
        // nombre, valor de la cuenta
        cuentas_registradas[tax_row.account_head] = tax_row.total;
      }
    });

    // Si existe por lo menos una cuenta, se ejecuta frappe.call
    if (Object.keys(cuentas_registradas).length > 0) {
      // llama al metodo python, el cual recibe de parametros el nombre de la factura y el objeto
      // con las ('cuentas encontradas
      //console.log('---------------------- se encontro por lo menos una cuenta--------------------');
      frappe.call({
        method: "factura_electronica.utils.special_tax.add_gl_entry_other_special_tax",
        args: {
          invoice_name: frm.doc.name,
          accounts: cuentas_registradas,
          invoice_type: "Sales Invoice",
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
        },
      });
    }

    frm.refresh_field("access_number_fel");
    frm.reload_doc();
  },
  naming_series: function (frm, cdt, cdn) {
    // Aplica solo para FS
    if (frm.doc.naming_series) {
      frappe.call({
        method: "factura_electronica.api.obtener_numero_resolucion",
        args: {
          nombre_serie: frm.doc.naming_series,
        },
        // El callback se ejecuta tras finalizar la ejecucion del script python del lado
        // del servidor
        callback: function (numero_resolucion) {
          if (numero_resolucion.message === undefined) {
            // cur_frm.set_value('shs_numero_resolucion', '');
          } else {
            cur_frm.set_value("shs_numero_resolucion", numero_resolucion.message);
          }
        },
      });
    }
  },
  es_nota_de_debito: function (frm) {},
  is_return: function (frm) {},
});

frappe.ui.form.on("Sales Invoice Item", {
  // Despues de que se elimina una fila
  before_items_remove: function (frm, cdt, cdn) {
    remove_non_existing_taxes(frm);
    shs_total_other_tax(frm);
    shs_total_iva(frm);
  },
  // Cuando se elimina una fila
  items_remove: function (frm, cdt, cdn) {
    remove_non_existing_taxes(frm);
    shs_total_other_tax(frm);
    shs_total_iva(frm);
  },
  // NOTA: SI el proceso se realentiza al momento de agregar/duplicar filas comentar este bloque de codigo
  items_add: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  //   Cuando se cambia de posicion una fila
  items_move: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  //   Al cambiar el valor de item_code
  item_code: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
    remove_non_existing_taxes(frm);
  },
  // item_name: function (frm, cdt, cdn) {
  //   each_row(frm, cdt, cdn);
  // },
  //   Al cambiar el valor de qty
  qty: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  // NOTA: ESTE EVENTO NO SE EJECUTA PORQUE EL CAMPO ES READ ONLY
  stock_qty: function (frm, cdt, cdn) {
    // console.log('stock_qty')
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
  discount_percentage: function (frm, cdt, cdn) {
    each_row(frm, cdt, cdn);
  },
  discount_amount: function (frm, cdt, cdn) {
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

    // row.qty = calcu;
    frappe.model.set_value(row.doctype, row.name, "qty", flt(calcu));
    // row.stock_qty = calcu;
    frappe.model.set_value(row.doctype, row.name, "stock_qty", flt(calcu));
    // row.amount = calcu * a; // frm.doc.items[index].rate;
    frappe.model.set_value(row.doctype, row.name, "amount", flt(calcu * a));
    frm.refresh_field("items");

    each_row(frm, cdt, cdn);
  },
});

frappe.ui.form.on("Otros Impuestos Factura Electronica", {
  // Despues de que se elimina una fila
  before_shs_otros_impuestos_remove: function (frm, cdt, cdn) {
    shs_total_other_tax(frm);
  },
  // Cuando se elimina una fila
  shs_otros_impuestos_remove: function (frm, cdt, cdn) {
    shs_total_other_tax(frm);
  },
  //  Cuando se agrega una fila
  shs_otros_impuestos_add: function (frm, cdt, cdn) {
    shs_total_other_tax(frm);
  },
  //   Cuando se cambia de posicion una fila
  shs_otros_impuestos_move: function (frm, cdt, cdn) {
    shs_total_other_tax(frm);
  },
});
