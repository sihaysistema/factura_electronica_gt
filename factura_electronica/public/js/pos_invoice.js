/**
 * Copyright (c) 2021 Si Hay Sistema and contributors
 * For license information, please see license.txt
 */

// import { valNit } from "./facelec.js";
import { goalSeek } from "./goalSeek.js";

/**
 * @summary Limpia los campos con data no necesaria, al momento de duplicar
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
 * @param {Object} frm - Propiedades del Doctype
 */
function sales_invoice_calc(frm) {
  frappe.call({
    method: "factura_electronica.utils.calculator.sales_invoice_calculator",
    args: {
      invoice_name: frm.doc.name,
    },
    freeze: true,
    freeze_message: __("Calculating") + " ðŸ“„ðŸ“„ðŸ“„",
    callback: (r) => {
      frm.reload_doc();
      // console.log("POS Invoice Calculated", r.message);
      // frm.save();
    },
    error: (r) => {
      // on error
      console.log("POS Invoice Calculated Error");
    },
  });
  frm.reload_doc();
}

/**
 * @summary Validador de que boton se debe generar para docs electronicos
 * @param {Object} frm
 */
function btn_generator(frm) {
  // El documento debe estar guardado para que la funcion is_valid_to_fel valide correctamente el escenario
  frappe.call({
    method: "factura_electronica.pos_fel_api.is_valid_to_fel",
    args: {
      doctype: frm.doc.doctype,
      docname: frm.doc.name,
    },
    callback: function (r) {
      if (r.message[1] === "anulador" && r.message[2]) {
        frappe
          .call("factura_electronica.api.btn_activator", {
            electronic_doc: "anulador_de_facturas_ventas_fel",
          })
          .then((r) => {
            if (r.message) {
              frappe
                .call("factura_electronica.api.invoice_exists", {
                  uuid: frm.doc.numero_autorizacion_fel,
                })
                .then((r) => {
                  if (r.message) {
                    cur_frm.clear_custom_buttons();
                    pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
                  } else {
                    btn_canceller(frm);
                    pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
                  }
                });
            }
          });
      }

      if (r.message[0] === "FACT" && r.message[2]) {
        generar_boton_factura(__("Factura ElectrÃ³nica FEL"), frm);
        if (frm.doc.numero_autorizacion_fel) {
          cur_frm.clear_custom_buttons();
          pdf_button_fel(frm.doc.numero_autorizacion_fel, frm);
        }
      }
    },
  });
}
  // FIN BOTONES GENERADORES DOCS ELECTRONICOS

  // INICIO GENERACION POLIZA CON RETENCIONES
  // TODO:AGREGAR VALIDACION EXISTENCIA DE JOURNA ENTRY
  // VALIDAR Y CREAR DOCUMENTACION DE RETENCIONES
  // if (frm.doc.docstatus === 1 && frm.doc.status !== "Paid") {
  //   btn_journal_entry_retention(frm);
  // }
  // FIN GENERACION POLIZA CON RETENCIONES
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
        invoice_type: "POS Invoice",
        is_return: frm.doc.is_return,
        /* OJO, El valor de este argumento debe ser "POS Invoice" en sales_invoice.js
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
                method: "factura_electronica.pos_fel_api.invoice_canceller",
                args: {
                  invoice_name: frm.doc.name,
                  reason_cancelation: values.reason_cancelation || "AnulaciÃ³n",
                  document: "POS Invoice",
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
        method: "factura_electronica.pos_fel_api.api_interface",
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
 * @summary Generador de boton que visualiza PDF doc electronico
 *
 * @param {*} cae_documento
 * @param {*} frm
 */
function pdf_button_fel(cae_documento, frm) {
  // Esta funcion se encarga de mostrar el boton para obtener el pdf de la factura electronica generada
  // aplica para fel, y anuladas
  frm
    .add_custom_button(__("VER PDF DOCUMENTO ELECTRÃ“NICO"), function () {
      window.open("https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" + cae_documento);
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

/* Factura de Ventas POS-------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("POS Invoice", {
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
      btn_generator(frm);
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

frappe.ui.form.on("POS Invoice Item", {
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
