frappe.listview_settings["Sales Invoice"] = frappe.listview_settings["Sales Invoice"] || {};

const previous_sales_invoice_onload = frappe.listview_settings["Sales Invoice"].onload;

frappe.listview_settings["Sales Invoice"].onload = function (listview) {
  if (typeof previous_sales_invoice_onload === "function") {
    previous_sales_invoice_onload.call(this, listview);
  }

  listview.page.add_action_item(__("Create GT Electronic Invoice Batch"), function () {
    const checked = listview.get_checked_items() || [];
    const selected = checked.map(function (row) {
      const name = typeof row === "string" ? row : row.name;
      return { invoice: name };
    });

    frappe.call({
      method: "factura_electronica.api_erp.batch_generator_api",
      freeze: true,
      args: {
        invoices: JSON.stringify(selected),
      },
    });
  });
};
