from frappe import _


def get_data():
	return {
		# "heatmap": True,
		# "heatmap_message": _("This is based on the Time Sheets created against this shipment."),
		"fieldname": "customs_shipment",
		"non_standard_fieldnames": {
			"Payment Request": "reference_name",
		},
		"transactions": [
			{
				"label": _("Shipment"),
				# "items": ["Task", "Timesheet", "Issue", "Project Update"],
				"items": ["Task", "Shipment"],
			},
			# {"label": _("Material"), "items": ["Material Request", "BOM", "Stock Entry"]},
			{"label": _("Sales"), "items": ["Sales Order", "Delivery Note", "Sales Invoice"]},
			{"label": _("Purchase"), "items": ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]},
			{"label": _("Payments"), "items": ["Payment Request"]},
		],
	}