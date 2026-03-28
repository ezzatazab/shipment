// Copyright (c) 2025, NSFSS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shipment Settings", {
	setup(frm) {
        frm.set_query("shipment_mission", function () {
            return {
                filters: {
                    disabled: 0,
                    is_stock_item: 0
                }
            };
        });
        frm.set_query("shipment_service", function () {
            return {
                filters: {
                    disabled: 0,
                    is_stock_item: 0
                }
            };
        });
	},
});
