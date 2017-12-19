var gt_tax_fuel_amount, gt_tax_goods_amount, gt_tax_services_amount;
//testing push to another branch
		
		frm.doc.items.forEach((item_row,index) => {
			if (item_row.is_fuel == TRUE){
				this_row_qty = item_row.qty;
				this_row_rate = item_row.rate;
				this_row_amount = (item_row.qty *item_row.rate);
				this_row_conversion_factor = item_row.conversion_factor;
				this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
				this_row_tax_rate = (item_row.tax_rate_per_uom);
				this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
				this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
				this_row_sales_tax_rate = 
				console.log("El campo qty es ahora de esta fila contiene: " + this_row_qty);
				console.log("El campo rate es ahora de esta fila contiene: " + this_row_rate);
				console.log("El campo conversion_factor de esta fila contiene: " + this_row_conversion_factor);
				console.log("El campo stock_qty de esta fila contiene: " + this_row_stock_qty);
				console.log("El campo tax_rate de esta fila contiene: " + this_row_tax_rate);
				console.log("El campo tax_amount de esta fila contiene: " + this_row_tax_amount);
				console.log("El campo taxable_amount de esta fila contiene: " + this_row_taxable_amount);
				frm.doc.items[index].other_tax_amount = Number(this_row_tax_rate * this_row_stock_qty);
				frm.doc.items[index].amount_minus_excise_tax = Number(this_row_amount - this_row_tax_amount);
				gt_tax_fuel_amount += this_row_taxable_amount
			};	
		});
		
		frm.doc.items.forEach((item_row,index) => {
			if (item_row.name == cdn){
				this_row_qty = item_row.qty;
				this_row_rate = item_row.rate;
				this_row_amount = (item_row.qty *item_row.rate);
				this_row_conversion_factor = item_row.conversion_factor;
				this_row_stock_qty = (item_row.qty * item_row.conversion_factor);
				this_row_tax_rate = (item_row.tax_rate_per_uom);
				this_row_tax_amount = (this_row_stock_qty * this_row_tax_rate);
				this_row_taxable_amount = (this_row_amount - this_row_tax_amount);
				console.log("El campo qty es ahora de esta fila contiene: " + this_row_qty);
				console.log("El campo rate es ahora de esta fila contiene: " + this_row_rate);
				console.log("El campo conversion_factor de esta fila contiene: " + this_row_conversion_factor);
				console.log("El campo stock_qty de esta fila contiene: " + this_row_stock_qty);
				console.log("El campo tax_rate de esta fila contiene: " + this_row_tax_rate);
				console.log("El campo tax_amount de esta fila contiene: " + this_row_tax_amount);
				console.log("El campo taxable_amount de esta fila contiene: " + this_row_taxable_amount);
				frm.doc.items[index].other_tax_amount = Number(this_row_tax_rate * this_row_stock_qty);
				frm.doc.items[index].amount_minus_excise_tax = Number(this_row_amount - this_row_tax_amount);
			};	
		});