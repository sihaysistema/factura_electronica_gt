console.log("Se cargo exitosamente la aplicación de Factura Electrónica");
/* 1 --------------------------------------------------------------------------------------------------------------- */
/**
 * Funcionamiento: Valida que el Nit sea C/F o un numero de nit valido permitiendo
 * activar la opcion para guardar. Si el nit es invalido desactiva la funcion
 * guardar hasta que se ingrese uno correcto, esto permite no tener errores con
 * INFILE y tener los datos correctos.
 */
export function valNit(nit, cus_supp, frm) {
	if (nit === "C/F" || nit === "c/f") {
		frm.enable_save(); // Activa y Muestra el boton guardar de Sales Invoice
	} else {
		var nd, add = 0;
		if (nd = /^(\d+)\-?([\dk])$/i.exec(nit)) {
			nd[2] = (nd[2].toLowerCase() == 'k') ? 10 : parseInt(nd[2]);
			for (var i = 0; i < nd[1].length; i++) {
				add += ((((i - nd[1].length) * -1) + 1) * nd[1][i]);
			}
			var nit_validado = ((11 - (add % 11)) % 11) == nd[2];
		} else {
			var nit_validado = false;
		}

		if (nit_validado === false) {
			msgprint('NIT de: <b>' + cus_supp + '</b>, no es correcto. Si no tiene disponible el NIT modifiquelo a <b>C/F</b>');
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

/* en-US: INDIVIDUAL SOURCE CODE FROM .js FILES IN THIS DIRECTORY WILL BE ADDED WHEN DOING A BENCH BUILD
   es-GT: CODIGO FUENTE INDIVIDUAL DE ARCHIVOS .js EN ESTE DIRECTORIO SE AGREGARAN ABAJO AL HACER BENCH BUILD */

// ================================================================================================================ //
