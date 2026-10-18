frappe.ui.form.on('Sales Invoice', {
    refresh: function (frm) {
		if (frm.doc.docstatus === 0 && !frm.doc.is_return) {
			frm.add_custom_button(
			__("Customs Shipment"),
			function () {
				erpnext.utils.map_current_doc({
					method: "shippment.shippment.doctype.customs_shipment.customs_shipment.create_sales_invoice",
					source_doctype: "Customs Shipment",
					target: frm,
					setters: [
						{
							fieldtype: "Link",
							label: __("Customer"),
							options: "Customer",
							fieldname: "customer",
							default: frm.doc.customer,
						},
					],
					get_query_filters: {

					}
				});
			},
			__("Get Items From")
		);
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__('Print with Attachments'), function () {
				print_sales_invoice_with_attachments(frm);
			});

			frm.add_custom_button(__('Print new design with attachments'), function () {
				print_sales_invoice_with_attachments(frm, "Bayani Sales Invoice");
			});
		}
	}
});

function print_sales_invoice_with_attachments(frm, print_format) {
	const args = {
		doctype: "Sales Invoice",
		name: frm.doc.name,
	};
	if (print_format) {
		args.print_format = print_format;
	}

	frappe.call({
		method: 'shippment.utils.download_related_docs',
		args: args,
		freeze: true,
		freeze_message: __("Generating...."),
		callback: function (r) {
			if (r && r.message) {
				let file_url = r.message;
				file_url = file_url.replace(/#/g, "%23");
				window.open(file_url);
			}
		},
		error: function () {
			frappe.msgprint(__('Failed to generate PDF.'));
		}
	});
}