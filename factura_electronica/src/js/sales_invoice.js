/**
 * Copyright (c) 2021 Si Hay Sistema and contributors
 * For license information, please see license.txt
 */

// import { valNit } from "./facelec.js";
import { goalSeek } from "./goalSeek.js";

/**
 * @summary Limpia los campos con data no necesaria, al momento de duplicar
 * NOTE: Esta funcion altera el estado de doc haciendo que aparezca en Draft
 *
 * @param {*} frm
 */
function clean_fields(frm) {
  // Funcionalidad evita copiar CAE cuando se duplica una factura
  // LIMPIA/CLEAN, permite limpiar los campos cuando se duplica una factura
  if (frm.doc.status === "Draft" || frm.doc.docstatus == 0) {
    console.log("LImpiando campos");
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
    frm.refresh_fields();
  }
}

/**
 * @summary Generador tabla HTML con detalles de impuestos e impuestos especiales
 * de los items de la factura
 *
 * @param {*} frm
 */
function generar_tabla_html(frm) {
  if (frm.doc.items.length > 0) {
    const mi_array = frm.doc.items;
    const mi_array_dos = Array.from(mi_array);

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
 * @summary Calculador de montos para generar documentos electronicos
 * Se ejecuta despues de guardar los datos en la DB
 * @param {Object} frm - Propiedades del Doctype
 */
function sales_invoice_calc(frm) {
  frappe.call({
    method: "factura_electronica.utils.calculator.sales_invoice_calculator",
    args: {
      invoice_name: frm.doc.name,
    },
    freeze: true,
    freeze_message: __("Calculating") + " 📄📄📄",
    callback: (r) => {
      frm.reload_doc();
    },
  });
  frm.reload_doc();
}

// Valida que tipo de boton generador fel debe aparecer
function btn_validator(frm) {
  frappe.call({
    method: "factura_electronica.fel_api.btn_validator",
    args: {
      doctype: frm.doc.doctype,
      docname: frm.doc.name,
    },
    callback: function ({ message }) {
      btn_fel_generator(frm, message);
    },
  });
}

function btn_fel_generator(frm, msg) {
  const { type_doc, show_btn } = msg;

  console.log("El tipo de doc es", type_doc);
  // console.log("Status btn", show_btn);

  if (!type_doc) {
    // Si no hay dato no se muestra ningun btn generador
    return;
  }

  // Factura Venta Normal
  if (type_doc === "factura_fel") {
    generar_boton_factura(__("Generar Factura FEL"), frm);
    if (frm.doc.numero_autorizacion_fel) {
      // Si ya se genero se muestra el btn para ver pdf
      cur_frm.clear_custom_buttons();
      pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
    }
  }
  // Factura Exportacion
  if (type_doc === "exportacion") {
    btn_export_invoice(frm);
    // Si ya se genero se muestra el btn para ver pdf
    if (frm.doc.numero_autorizacion_fel) {
      cur_frm.clear_custom_buttons();
      pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
    }
  }
  // Nota de Credito
  if (type_doc === "nota_credito") {
    btn_credit_note(frm);
    // Si ya se genero se muestra el btn para ver pdf
    if (frm.doc.numero_autorizacion_fel) {
      cur_frm.clear_custom_buttons();
      pdf_credit_note(frm);
    }
  }
  // Factura Cambiaria
  if (type_doc === "cambiaria") {
    btn_exchange_invoice(frm);
    // Si ya se genero se muestra el btn para ver pdf
    if (frm.doc.numero_autorizacion_fel) {
      cur_frm.clear_custom_buttons();
      pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
    }
  }
  // Anulador de docs
  if (type_doc === "anulador_si") {
    if (show_btn == false) {
      // Si ya esta cancelada
      // Si ya se genero se muestra el btn para ver pdf
      if (frm.doc.numero_autorizacion_fel) {
        cur_frm.clear_custom_buttons();
        pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
      }
    }
    if (show_btn == true) {
      btn_canceller(frm);
    }
  }
}

/**
 * @summary Para impuestos especiales (OJO SOLO COMBUSTIBLES) crear entradas en GL Entry para cuadrar montos
 * @param {Object} frm
 */
function special_tax(frm) {
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
        is_return: frm.doc.is_return,
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
      // frm.reload_doc();
      // let serie_de_factura = frm.doc.name;
      // // Guarda la url actual
      // let mi_url = window.location.href;
      frappe.call({
        method: "factura_electronica.fel_api.fel_generator",
        args: {
          doctype: frm.doc.doctype,
          docname: frm.doc.name,
          type_doc: "factura_fel",
        },
        // El callback recibe como parametro el dato retornado por el script python del lado del servidor
        // para validar si se genero correctamente la factura electronica
        callback: function ({ message }) {
          // console.log(message);
          if (message.status === true && message.uuid) {
            // Crea una nueva url con el nombre del documento actualizado
            // let url_nueva = mi_url.replace(serie_de_factura, message.serie_fel);
            // // Asigna la nueva url a la ventana actual
            // window.location.assign(url_nueva);
            // // Recarga la pagina
            // Redirecciona a la nueva url
            frappe.set_route(`/app/sales-invoice/${message.serie_fel}`);
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
    .add_custom_button(__("Generar Factura Exportacion FEL"), function () {
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
    .add_custom_button(__("Generar Nota Credito FEL"), function () {
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
    .add_custom_button(__("Generar Factura Cambiaria FEL"), function () {
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
 * @summary Valida que existan los datos minimos necesarios para realizar calculos correctamente
 * @param {Object} frm
 */
function dependency_validator(frm) {
  let taxes = frm.doc.taxes || [];
  if (!taxes.length > 0) {
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
}

/* Factura de Ventas-------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Sales Invoice", {
  // Cuando se carga por primera vez una factura se asegura que active o no el redondeo
  // de decimales dependiendo de la configucion
  setup(frm) {
    if (frm.doc.docstatus == 0) {
      frappe.call("factura_electronica.utils.utilities_facelec.get_rounding_config").then(({ message }) => {
        frm.set_value("disable_rounded_total", message);
        frm.refresh_field("disable_rounded_total");
      });
    }
  },
  // Se ejecuta cuando se renderiza el doctype
  onload_post_render: function (frm, cdt, cdn) {
    // clean_fields(frm);
  },
  // Se ejecuta despues de guardar el doctype
  after_save: function (frm, cdt, cdn) {
    sales_invoice_calc(frm);
  },
  // Se ejecuta cuando hay alguna actualizacion de datos en el doctype
  refresh: function (frm, cdt, cdn) {
    if (frm.doc.docstatus != 0) {
      // btn_generator(frm);
      btn_validator(frm);
    }
  },
  // Se ejecuta al presionar el boton guardar
  validate: function (frm, cdt, cdn) {
    dependency_validator(frm);
    generar_tabla_html(frm);
  },
  discount_amount: function (frm, cdt, cdn) {},
  // Se ejecuta antes de guardar el documento
  before_save: function (frm, cdt, cdn) {},
  // Se ejecuta al validar el documento
  on_submit: function (frm, cdt, cdn) {
    // Ocurre cuando se presione el boton validar.
    special_tax(frm);
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
});

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

frappe.ui.form.on("Sales Invoice Item", {
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

    // frappe.model.set_value(row.doctype, row.name, "qty", calcu);
    // frappe.model.set_value(row.doctype, row.name, "stock_qty", calcu);
    // frappe.model.set_value(row.doctype, row.name, "amount", calcu * a);

    row.qty = calcu;
    row.stock_qty = calcu;
    row.amount = calcu * a;
    frm.refresh_field("items");
  },
});
