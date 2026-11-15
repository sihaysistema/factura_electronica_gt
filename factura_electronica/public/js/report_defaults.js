// v14 Trial Balance lists gross opening and closing debit and credit unless
// "Show net values" is on. v13 showed net values. Default the filter to 1 so
// the report reads like v13. The report script loads later, so set the default
// when it registers itself on frappe.query_reports.
frappe.provide("frappe.query_reports");
(function () {
	const NET_DEFAULTS = { "Trial Balance": "show_net_values" };
	Object.keys(NET_DEFAULTS).forEach((report) => {
		let current = frappe.query_reports[report];
		Object.defineProperty(frappe.query_reports, report, {
			configurable: true,
			enumerable: true,
			get() { return current; },
			set(value) {
				(value && value.filters || []).forEach((f) => {
					if (f.fieldname === NET_DEFAULTS[report]) f.default = 1;
				});
				current = value;
			},
		});
	});
})();
