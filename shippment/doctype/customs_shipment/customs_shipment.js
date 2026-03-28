// Copyright (c) 2025, NSFSS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Customs Shipment", {
    onload: function (frm) {
        const so = frm.get_docfield("sales_order");
        so.get_route_options_for_new_doc = () => {
            if (frm.is_new()) return {};
            return {
                customer: frm.doc.customer,
                customs_shipment: frm.doc.name
            };
        };

        const si = frm.get_docfield("sales_invoice");
        si.get_route_options_for_new_doc = () => {
            if (frm.is_new()) return {};
            return {
                customer: frm.doc.customer,
                customs_shipment: frm.doc.name
            };
        };

        frm.set_query("port", function () {
            return {
                filters: {
                    type_of_shipping: frm.doc.type_of_shipping,
                    disabled: 0
                }
            };
        });

        frm.set_query("port_location", function () {
            return {
                filters: {
                    port: frm.doc.port,
                    disabled: 0
                }
            };
        });

        frm.fields_dict.shipment_missions.grid.get_field("shipment_mission").get_query = function () {
            return {
                filters: {
                    is_stock_item: 0,
                    disabled: 0
                }
            };
        };

        frm.set_query("sales_order", function () {
            return {
                filters: {
                    customer: frm.doc.customer,
                    docstatus: ['!=', 2]
                }
            };
        });

        frm.set_query("sales_invoice", function () {
            return {
                filters: {
                    customer: frm.doc.customer,
                    docstatus: ['!=', 2]
                }
            };
        });
    },

    refresh: function (frm) {
        frm.trigger("set_custom_buttons");
        frm.events.hide_status_logs_btns(frm);
        // apply_status_background(frm);

        if (!frm.is_new()) {
            frm.add_custom_button('Print with Attachments', function () {
				frappe.call({
					method: 'shippment.utils.download_related_docs',
					args: {
						doctype: "Customs Shipment",
						name: frm.doc.name
					},
					freeze: true,
					freeze_message: __("Generating...."),
					callback: function (r) {
						if (r && r.message) {
							let file_url = r.message;
							file_url = file_url.replace(/#/g, "%23");
							window.open(file_url);
							frm.reload_doc();
						} else {
							frappe.msgprint(__('Failed to generate PDF.'));
						}
					},
				});
			});
        }
    },

    // status: function (frm) {
    //     apply_status_background(frm);
    // },

    hide_status_logs_btns: function (frm) {
        const grid = frm.fields_dict.status_logs.grid;

        grid.wrapper.find('.grid-add-row').hide();
        grid.wrapper.find('.grid-add-multiple-rows').hide();
        grid.wrapper.find('.grid-move-row').hide();
        grid.wrapper.find('.grid-duplicate-row').hide();

        grid.wrapper.find('.grid-delete-row').hide();
        grid.wrapper.find('.grid-remove-rows').hide();
        grid.wrapper.find('.grid-remove-all-rows').hide();
    },

    type_of_shipping: function (frm) {
        frm.set_value({
            "port": "",
            "port_location": ""
        });
    },

    port: function (frm) {
        if (frm.doc.port) {
            if (frm.doc.type_of_shipping == "Sea Freight") {
                frappe.db.get_value("Port Location", { "port": frm.doc.port }, "name", function (v) {
                    if (v.name) {
                        frm.set_value("port_location", v.name);
                    }else {
                        frm.set_value("port_location", "");
                    }
                });
            }
            frappe.db.get_value("Ports", frm.doc.port, "type_of_shipping", function (v) {
                if (v.type_of_shipping != frm.doc.type_of_shipping) {
                    frm.set_value("type_of_shipping", v.type_of_shipping);
                };
            });
        }else {
            frm.set_value("port_location", "");
        }
    },

    actual_arrival_date: function (frm) {
        if (frm.doc.actual_arrival_date) {
            frm.set_value("policy_date", frappe.datetime.add_days(frm.doc.actual_arrival_date, 3));
        }
    },

    set_custom_buttons: function (frm) {
        if (!frm.is_new()) {
            // Create Task
            frm.add_custom_button(__('Task'), function () {
                frappe.new_doc("Task", {
                    customs_shipment: frm.doc.name
                });
            }, __('Create'));

            frm.add_custom_button(__('Sales Order'), function () {
                frappe.model.open_mapped_doc({
                    method: "shippment.shippment.doctype.customs_shipment.customs_shipment.create_sales_order",
                    frm: frm,
                });
            }, __('Create'));

            frm.add_custom_button(__('Sales Invoice'), function () {
                frappe.model.open_mapped_doc({
                    method: "shippment.shippment.doctype.customs_shipment.customs_shipment.create_sales_invoice",
                    frm: frm,
                });
            }, __('Create'));

            frm.add_custom_button(__('Payment Request'), function () {
                frappe.prompt([
                    {
                        fieldname: 'transaction_date',
                        fieldtype: 'Date',
                        label: __('Transaction Date'),
                    },
                    {
                        fieldname: 'amount',
                        fieldtype: 'Currency',
                        label: __('Amount'),
                        reqd: 1,
                    },
                    {
                        fieldname: 'column_breakdown',
                        fieldtype: 'Column Break',
                    },
                    {
                        fieldname: 'mode_of_payment',
                        fieldtype: 'Link',
                        label: __('Mode of Payment'),
                        options: 'Mode of Payment',
                    },
                    {
                        fieldname: 'payment_url',
                        fieldtype: 'Data',
                        label: __('Payment URL'),
                    }
                ],
                    function (values) {
                        frappe.model.open_mapped_doc({
                            method: "shippment.shippment.doctype.customs_shipment.customs_shipment.create_payment_request",
                            frm: frm,
                            args: {
                                transaction_date: values.transaction_date,
                                amount: values.amount,
                                mode_of_payment: values.mode_of_payment,
                                payment_url: values.payment_url,
                            }
                        });
                    },
                    __('Payment Request'),
                    __('Submit'),
                    'medium'
                );
            }, __('Create'));

            if (frm.doc.status == "Fully Released") {
                frm.add_custom_button(__('Shipment'), function () {
                    let container = null;
                    if (frm.doc.shipment_type == "Container" && frm.doc.vessel_details) {
                        const vesselNos = (frm.doc.vessel_details || []).map(d => d.vessel_no).filter(Boolean);
                        if (vesselNos.length) {
                            if (vesselNos.length === 1) {
                                // Only one vessel_no available, use it directly
                                container = vesselNos[0];
                                frappe.model.open_mapped_doc({
                                    method: "shippment.shippment.doctype.customs_shipment.customs_shipment.create_shipment",
                                    frm: frm,
                                    args: {
                                        container: container,
                                    }
                                });
                            } else {
                                // Multiple vessel_nos -> ask user to choose
                                frappe.prompt([
                                    {
                                        fieldname: 'vessel_no',
                                        fieldtype: 'Select',
                                        label: __('Vessel Number'),
                                        options: vesselNos
                                    }
                                ],
                                    function (values) {
                                        container = values.vessel_no;
                                        // optionally persist selection on the form
                                        // frm.set_value('selected_vessel_no', container);
                                        frappe.model.open_mapped_doc({
                                            method: "shippment.shippment.doctype.customs_shipment.customs_shipment.create_shipment",
                                            frm: frm,
                                            args: {
                                                container: container,
                                            }
                                        });
                                    },
                                    __('Select Vessel'),
                                    __('Select'));
                            }
                        }
                    } else {
                        frappe.model.open_mapped_doc({
                            method: "shippment.shippment.doctype.customs_shipment.customs_shipment.create_shipment",
                            frm: frm,
                            args: {
                                container: container,
                            }
                        });
                    }
                }, __('Create'));
            }

            frm.events.create_purchase_invoice(frm);

            frm.events.get_items_from_sales_order(frm);
            frm.events.get_items_from_sales_invoice(frm);
        }
    },

    create_purchase_invoice: function (frm) {
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Shipment Settings"
            },
            callback: function (r) {
                frm.add_custom_button(__('Purchase Invoice'), function () {
                    frappe.prompt([
                        {
                            fieldname: 'supplier',
                            fieldtype: 'Link',
                            label: __('Supplier'),
                            options: 'Supplier',
                            default: r.message.default_supplier,
                            reqd: 1,
                        },
                        {
                            fieldname: 'column_breakd_1',
                            fieldtype: 'Column Break'
                        },
                        {
                            fieldname: 'mode_of_payment',
                            fieldtype: 'Link',
                            label: __('Mode of Payment'),
                            options: 'Mode of Payment',
                            reqd: 1
                        },
                        {
                            fieldname: 'section_break_1',
                            fieldtype: 'Section Break'
                        },
                        {
                            fieldname: 'items',
                            fieldtype: 'Table',
                            label: __('Items'),
                            reqd: 1,
                            cannot_add_rows: false,
                            in_place_edit: true,
                            fields: [
                                {
                                    fieldname: 'item_code',
                                    fieldtype: 'Link',
                                    options: 'Item',
                                    label: __('Item Code'),
                                    reqd: 1,
                                    in_list_view: 1,
                                    get_query: function () {
                                        return {
                                            filters: {
                                                is_stock_item: 0,
                                                disabled: 0
                                            }
                                        };
                                    }
                                },
                                {
                                    fieldname: 'qty',
                                    fieldtype: 'Float',
                                    label: __('Quantity'),
                                    default: 1,
                                    reqd: 1,
                                    in_list_view: 1,
                                },
                                {
                                    fieldname: 'rate',
                                    fieldtype: 'Currency',
                                    label: __('Rate'),
                                    reqd: 1,
                                    in_list_view: 1,
                                },
                            ],
                        }
                    ],
                        function (values) {
                            frappe.model.open_mapped_doc({
                                method: "shippment.shippment.doctype.customs_shipment.customs_shipment.create_purchase_invoice",
                                frm: frm,
                                freeze: true,
                                freeze_message: __("Creating Purchase Invoice..."),
                                args: {
                                    supplier: values.supplier,
                                    mode_of_payment: values.mode_of_payment,
                                    items: values.items
                                },
                                callback: function () {
                                    frm.reload_doc();
                                }
                            });
                        },
                        __('Purchase Invoice'),
                        __('Create'));
                }, __('Create'));
            }
        });
    },

    customs_declaration: function (frm) {
        if (frm.doc.customs_declaration && frm.doc.status != "Transaction Submitted") {
            frm.set_value("status", "Transaction Submitted");
        }
    },

    get_items_from_sales_order: function (frm) {
        frm.add_custom_button(
            __("Sales Order"),
            function () {
                erpnext.utils.map_current_doc({
                    method: "shippment.shippment.doctype.customs_shipment.customs_shipment.get_items_from_sales_order",
                    source_doctype: "Sales Order",
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
                        docstatus: 1
                    }
                });
            },
            __("Get Items From")
        );
    },

    get_items_from_sales_invoice: function (frm) {
        frm.add_custom_button(
            __("Sales Invoice"),
            function () {
                erpnext.utils.map_current_doc({
                    method: "shippment.shippment.doctype.customs_shipment.customs_shipment.get_items_from_sales_invoice",
                    source_doctype: "Sales Invoice",
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
                        docstatus: 1
                    }
                });
            },
            __("Get Items From")
        );
    }
});


frappe.ui.form.on("Customs Shipment Mission Detail", {
    before_shipment_missions_remove: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        if (d.shipment_mission && d.purchase_invoice) {
            frappe.throw(__("You cannot remove the Transaction Document if the purchase invoice is already created."));
        }
    }
});


frappe.ui.form.on("Customs Shipment Status Log", {
    form_render: function (frm, cdt, cdn) {
        frm.events.hide_status_logs_btns(frm);
    }
});


function apply_status_background(frm) {
    if (!frm.doc.status) return;

    const status_colors = {
        "New": "#dbeafe",                     // blue
        "Submission": "#ede9fe",              // purple
        "Inspection and Examination": "#ffedd5", // orange
        "Special Sections": "#fee2e2",        // red
        "Collection": "#fef9c3",              // yellow
        "Ready for Release": "#dcfce7",       // green
        "Fully Released": "#bbf7d0",          // dark green
        "Transport": "#cffafe",               // cyan
        "Delivered to Finance": "#f5cdecff",
        "Request Closed": "#f3f4f6"            // gray
    };

    const color = status_colors[frm.doc.status];
    if (!color) return;

    // Get status field wrapper
    const field = frm.get_field('status');
    if (!field || !field.$wrapper) return;

    // Apply background color
    field.$wrapper.find('.control-value, select, input')
        .css({
            'background-color': color,
            'font-weight': 'bold'
        });
}
