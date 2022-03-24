// /**
//  * Copyright (c) 2021 Si Hay Sistema and contributors
//  * For license information, please see license.txt
//  */

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

function sales_invoice_calc(frm) {
  frappe.call({
    method: "factura_electronica.utils.calculator.sales_invoice_calculator",
    args: {
      invoice_name: frm.doc.name,
    },
    freeze: true,
    callback: (r) => {
      frm.reload_doc();
      console.log("Sales Invoice Calculated", r.message);
    },
    error: (r) => {
      // on error
      console.log("Sales Invoice Calculated Error");
    },
  });
}

function btn_generator(frm) {
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
  // VALIDAR Y CREAR DOCUMENTACION DE RETENCIONES
  // if (frm.doc.docstatus === 1 && frm.doc.status !== "Paid") {
  //   btn_journal_entry_retention(frm);
  // }
  // FIN GENERACION POLIZA CON RETENCIONES
}

/* Factura de Ventas-------------------------------------------------------------------------------------------------- */
frappe.ui.form.on("Sales Invoice", {
  // Se ejecuta cuando se renderiza el doctype
  onload_post_render: function (frm, cdt, cdn) {
    clean_fields(frm);
  },
  // Se ejecuta despues de guardar el doctype
  after_save: function (frm, cdt, cdn) {
    sales_invoice_calc(frm);
  },
  // Se ejecuta cuando hay alguna actualizacion de datos en el doctype
  refresh: function (frm, cdt, cdn) {
    // es-GT: Obtiene el numero de Identificacion tributaria ingresado en la hoja del cliente.
    // en-US: Fetches the Taxpayer Identification Number entered in the Customer doctype.
    // cur_frm.add_fetch("customer", "nit_face_customer", "nit_face_customer");
    // frm.set_df_property("shs_otros_impuestos", "read_only", 1);

    if (frm.doc.docstatus != 0) {
      btn_generator(frm);
    }
  },
  // Se ejecuta al presionar el boton guardar
  validate: function (frm, cdt, cdn) {
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

    generar_tabla_html(frm);
  },

  discount_amount: function (frm, cdt, cdn) {},
  // Se ejecuta antes de guardar el documento
  before_save: function (frm, cdt, cdn) {},
  // Se ejecuta al validar el documento
  on_submit: function (frm, cdt, cdn) {
    // Ocurre cuando se presione el boton validar.

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
});

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

    frappe.model.set_value(row.doctype, row.name, "qty", flt(calcu));
    frappe.model.set_value(row.doctype, row.name, "stock_qty", flt(calcu));
    frappe.model.set_value(row.doctype, row.name, "amount", flt(calcu * a));

    frm.refresh_field("items");
  },
});
