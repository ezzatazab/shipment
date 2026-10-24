frappe.ready(function () {
frappe.web_form.on("shipping_line", (field, value) => {
	if (!value) {
		frappe.web_form.set_value("bl_prefix", "");
		frappe.web_form.set_value("shipping_agent", "");
		frappe.web_form.set_value("agent_prefix", "");
		return;
	}

	frappe.db.get_value("Shipping Line", value, "bl_prefix").then((r) => {
		frappe.web_form.set_value("bl_prefix", (r.message && r.message.bl_prefix) || "");
	});

	frappe.call({
		method: "shippment.shippment.doctype.customs_shipment.customs_shipment.get_shipping_line_agents",
		args: { shipping_line: value },
		callback(r) {
			const agents = r.message || [];
			const agent_field = frappe.web_form.fields_dict.shipping_agent;
			if (agent_field && agent_field.set_data) {
				agent_field.set_data(
					agents.map((row) => ({
						value: row.name,
						label: row.agent_name || row.name,
					}))
				);
			}
			const names = agents.map((row) => row.name);
			if (names.length === 1) {
				frappe.web_form.set_value("shipping_agent", names[0]);
				set_agent_prefix(names[0]);
			} else if (!names.includes(frappe.web_form.get_value("shipping_agent"))) {
				frappe.web_form.set_value("shipping_agent", "");
				frappe.web_form.set_value("agent_prefix", "");
			}
		},
	});
});

frappe.web_form.on("shipping_agent", (field, value) => {
	set_agent_prefix(value);
});

function set_agent_prefix(value) {
	if (!value) {
		frappe.web_form.set_value("agent_prefix", "");
		return;
	}
	frappe.db.get_value("Shipping Agent", value, "agent_prefix").then((r) => {
		frappe.web_form.set_value("agent_prefix", (r.message && r.message.agent_prefix) || "");
	});
}
});
