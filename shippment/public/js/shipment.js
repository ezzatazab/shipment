// Copyright (c) 2025, NSFSS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shipment", {
    onload: function (frm) {
        frm.fields_dict.shipment_services.grid.get_field("shipment_service").get_query = function () {
            return {
                filters: {
                    is_stock_item: 0,
                    disabled: 0
                }
            };
        };
    },

    refresh: function (frm) {
        if (frm.doc.docstatus < 2) {
            frm.add_custom_button(__("Sales Invoice"), function () {
                frappe.model.open_mapped_doc({
                    method: "shippment.overrides.shipment.create_sales_invoice",
                    frm: frm,
                    args: {
                        source_name: frm.doc.name
                    }
                });
            }, __("Create"));
        }
    }
});