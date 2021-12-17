// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GT Sales Ledger"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: "",
      reqd: 1,
      on_change: function () {
        frappe.db.get_value("Company", frappe.query_report.get_filter_value("company"), "tax_id").then((r) => {
          // console.log(r.message.name)
          frappe.query_report.set_filter_value("nit", r.message.tax_id);
          frappe.db.get_value("Company", frappe.query_report.get_filter_value("company"), "default_currency").then((r) => {
            frappe.query_report.set_filter_value("company_currency", r.message.default_currency);
          });
        });
      },
    },
    {
      fieldname: "nit",
      label: __("NIT"),
      fieldtype: "Data",
      default: "",
      read_only: 1,
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer",
      default: "",
      reqd: 0,
      depends_on: 'eval:doc.options=="No Subtotal"',
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "company_currency",
      label: __("Company Default Currency"),
      default: "",
      fieldtype: "Select",
      read_only: 1,
      options: erpnext.get_presentation_currency_list(),
    },
    {
      fieldname: "language",
      label: __("Display Language"),
      default: "es",
      fieldtype: "Link",
      options: "Language",
    },
    {
      fieldname: "group",
      label: __("Group?"),
      default: "",
      fieldtype: "Check",
      depends_on: 'eval:doc.options=="No Subtotal"',
    },
    {
      fieldtype: "Break",
    },
    {
      fieldname: "note_report",
      label: __("Note"),
      default: "No se incluyen descripcion de facturas con items no configurados, ni items de combustibles",
      fieldtype: "Data",
      read_only: 1,
      width: "40px",
    },
    {
      fieldname: "options",
      label: __("Options"),
      default: "No Subtotal",
      fieldtype: "Select",
      options: ["No Subtotal", "Weekly", "Monthly", "Quarterly"],
    },
  ],
  onload: function (report) {
    report.page.add_inner_button(__("Download Report"), function () {
      if (report.data.length > 0) {
        let d = new frappe.ui.Dialog({
          title: __("Download Report"),
          fields: [
            {
              label: __("Select Format"),
              fieldname: "format",
              fieldtype: "Select",
              options: ["Excel", "JSON"],
            },
          ],
          primary_action_label: __("Generate and download"),
          primary_action(values) {
            d.hide();
            // Se ejecuta la funcion para generar y guardar archivos
            frappe.call({
              method: "factura_electronica.factura_electronica.report.gt_sales_ledger.gt_sales_ledger.generate_report_files",
              args: {
                data: report.data,
                col_idx: report.filters[9].value, // El rango
                f_type: values.format,
              },
              freeze: true,
              freeze_message: __("Generating and saving file 📄📄📄"),
              callback: (r) => {
                // on success
                console.log(r.message);

                // Si el archivo se genera/guarda correctamente se descarga automaticamente
                if (r.message[0]) {
                  file_url = r.message[1].replace(/#/g, "%23");
                  window.open(file_url);
                }

                // Sucess MSG
                frappe.show_alert(
                  {
                    message: __("File Generated!"),
                    indicator: "green",
                  },
                  60
                );
                // frappe.utils.play_sound("submit");
              },
              error: (r) => {
                // on error
                console.log(r.message);
              },
            });
          },
        });

        d.show();
      } else {
        frappe.show_alert(
          {
            message: __("No es posible generar y descargar archivo, aun no ha generado el reporte"),
            indicator: "yellow",
          },
          5
        );
      }
    });
  },
};
