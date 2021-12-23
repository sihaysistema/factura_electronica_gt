// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Prepared Report Facelec", {
  onload: function (frm) {
    var wrapper = $(frm.fields_dict["filter_values"].wrapper).empty();

    let filter_table = $(`<table class="table table-bordered">
			<thead>
				<tr>
					<td>${__("Filter")}</td>
					<td>${__("Value")}</td>
				</tr>
			</thead>
			<tbody></tbody>
		</table>`);

    const filters = JSON.parse(frm.doc.filters);

    Object.keys(filters).forEach((key) => {
      const filter_row = $(`<tr>
				<td>${frappe.model.unscrub(key)}</td>
				<td>${filters[key]}</td>
			</tr>`);
      filter_table.find("tbody").append(filter_row);
    });

    wrapper.append(filter_table);
  },
});
