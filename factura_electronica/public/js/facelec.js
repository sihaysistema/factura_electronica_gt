console.log("Se cargo exitosamente la aplicación de Factura Electrónica");
/* 1 --------------------------------------------------------------------------------------------------------------- */
/**
 * Funcionamiento: Valida que el Nit sea C/F o un numero de nit valido permitiendo
 * activar la opcion para guardar. Si el nit es invalido desactiva la funcion
 * guardar hasta que se ingrese uno correcto, esto permite no tener errores con
 * INFILE y tener los datos correctos.
 */
export function valNit(nit, cus_supp, frm) {
    var nit_validado;
    if (nit === "C/F" || nit === "c/f") {
        frm.enable_save(); // Activa y Muestra el boton guardar de Sales Invoice
    } else {
        var nd, add = 0;
        if (nd = /^(\d+)\-?([\dk])$/i.exec(nit)) {
            nd[2] = (nd[2].toLowerCase() == 'k') ? 10 : parseInt(nd[2]);
            for (var i = 0; i < nd[1].length; i++) {
                add += ((((i - nd[1].length) * -1) + 1) * nd[1][i]);
            }
            nit_validado = ((11 - (add % 11)) % 11) == nd[2];
        } else {
            nit_validado = false;
        }

        if (nit_validado === false) {
            frappe.show_alert({
                indicator: 'orange',
                message: __(`
                NIT de <a href= '#Form/Customer/${cus_supp}'><b>${cus_supp}</b></a> no es correcto. Si no tiene disponible el NIT modifiquelo a C/F.
                `)
            });

            frm.disable_save(); // Desactiva y Oculta el boton de guardar en Sales Invoice
        }
        if (nit_validado === true) {
            frm.enable_save(); // Activa y Muestra el boton guardar de Sales Invoice
        }
    }
}

/* ----------------------------------------------------------------------------------------------------------------- */
/** Verificacion para que exista un solo check */
frappe.ui.form.on("Item", {
    facelec_is_fuel: function (frm, cdt, cdn) {
        if (frm.doc.facelec_is_fuel) {
            cur_frm.set_value("facelec_is_good", 0);
            cur_frm.set_value("facelec_is_service", 0);
        }
    },
    facelec_is_good: function (frm, cdt, cdn) {
        if (frm.doc.facelec_is_good) {
            cur_frm.set_value("facelec_is_fuel", 0);
            cur_frm.set_value("facelec_is_service", 0);
        }
    },
    facelec_is_service: function (frm, cdt, cdn) {
        if (frm.doc.facelec_is_service) {
            cur_frm.set_value("facelec_is_fuel", 0);
            cur_frm.set_value("facelec_is_good", 0);
        }
    }
});

// Validador NIT para customer
frappe.ui.form.on("Customer", {
    nit_face_customer: function (frm) {
        valNit(frm.doc.nit_face_customer, frm.doc.name, frm);
        frm.set_value('tax_id', frm.doc.nit_face_customer);
    },
    tax_id: function (frm) {
        valNit(frm.doc.tax_id, frm.doc.name, frm);
        frm.set_value('nit_face_customer', frm.doc.tax_id);
    }
});
// Validador NIT para Supplier
frappe.ui.form.on("Supplier", {
    facelec_nit_proveedor: function (frm) {
        valNit(frm.doc.facelec_nit_proveedor, frm.doc.name, frm);
        frm.set_value('tax_id', frm.doc.facelec_nit_proveedor);
    },
    tax_id: function (frm) {
        valNit(frm.doc.tax_id, frm.doc.name, frm);
        frm.set_value('facelec_nit_proveedor', frm.doc.tax_id);
    }
});

// frappe.ui.form.on("Company", {
//     nit_face_company: function (frm) {
//         valNit(frm.doc.nit_face_company, frm.doc.name, frm);
//         frm.set_value('tax_id', frm.doc.nit_face_company);
//     },
//     tax_id: function (frm) {
//         valNit(frm.doc.tax_id, frm.doc.name, frm);
//         frm.set_value('nit_face_company', frm.doc.tax_id);
//     }
// });
/* en-US: INDIVIDUAL SOURCE CODE FROM .js FILES IN THIS DIRECTORY WILL BE ADDED WHEN DOING A BENCH BUILD
   es-GT: CODIGO FUENTE INDIVIDUAL DE ARCHIVOS .js EN ESTE DIRECTORIO SE AGREGARAN ABAJO AL HACER BENCH BUILD */

// ================================================================================================================ //

// descripciones campos address
frappe.ui.form.on("Address", {
    refresh: function (frm) {
        frm.set_df_property("city", "description", __("<b>Departamento</b>"));
        frm.set_df_property("state", "description", __("<b>Municipio</b>"));
        frm.set_df_property("address_line1", "description", __("<b>Direccion Comercial 1</b>"));
        frm.set_df_property("address_line2", "description", __("<b>Direccion Comercial 2</b>"));
        frm.set_df_property("country", "description", __("<b>Pais</b>"));
    }
});