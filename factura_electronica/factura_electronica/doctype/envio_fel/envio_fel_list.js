frappe.listview_settings['Envio FEL'] = {

    get_indicator: function (doc) {
        var status_color = {
            "Valid": "green",
            "Cancelled": "red",
            // "Unpaid": "orange",
            // "Paid": "green",
            // "Return": "darkgrey",
            // "Credit Note Issued": "darkgrey",
            // "Unpaid and Discounted": "orange",
            // "Overdue and Discounted": "red",
            // "Overdue": "red"

        };
        return [__(doc.status), status_color[doc.status], "status,=," + doc.status];
    }
};
