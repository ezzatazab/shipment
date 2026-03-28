frappe.ui.form.on('Purchase Invoice', {
    refresh: function (frm) {
		if (frm.doc.docstatus === 0 && !frm.doc.is_return) {
			frm.add_custom_button(
			__("Shipment"),
			function () {
				erpnext.utils.map_current_doc({
					method: "shippment.overrides.shipment.create_purchase_invoice",
					source_doctype: "Shipment",
					target: frm,
					setters: [
						{
							fieldtype: "Link",
							label: __("Supplier"),
							options: "Supplier",
							fieldname: "delivery_supplier",
							default: frm.doc.supplier,
						},
					],
					get_query_filters: {

					}
				});
			},
			__("Get Items From")
		);
		}
	}
})