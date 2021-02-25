// this will help prevent duplicate calls
let added = false;

// This function is called any time the page is updated
$(document).bind('DOMSubtreeModified', function () {
    if ('List/Sales Invoice/List' in frappe.pages && frappe.pages['List/Sales Invoice/List'].page && !added) {
        added = true;
        frappe.pages['List/Sales Invoice/List'].page.add_action_item(__('Crear Lote Factura Electronica GT'), function (event) {
            // Convert list of UI checks to list of IDs
            let selected = [];
            for (let check of event.view.cur_list.$checks) {
                selected.push({ 'invoice': check.dataset.name });
            }
            // Do action
            // console.log(selected); // View selected

            // batch creator
            frappe
                .call({
                    method: 'factura_electronica.api_erp.batch_generator_api',
                    freeze: true,
                    args: {
                        invoices: JSON.stringify(selected)
                    }
                });
        });

    }
});