import frappe
from frappe.model.mapper import get_mapped_doc


def set_shipment_service(doc, method=None):
    shipment_service = frappe.db.get_single_value("Shipment Settings", "shipment_mission")
    if shipment_service and doc.shipment_service != shipment_service:
        doc.shipment_service = shipment_service


def update_vessel_detail(doc, method=None):
    if doc.customs_shipment and doc.container:
        customs_shipment = frappe.get_doc("Customs Shipment", doc.customs_shipment)
        for vessel in customs_shipment.vessel_details:
            if vessel.vessel_no == doc.container and vessel.shipment != doc.name:
                vessel.shipment = doc.name
        customs_shipment.save()


@frappe.whitelist()
def create_purchase_invoice(source_name, target_doc=None):
	def set_missing_values(source, target):
		for service in source.get("shipment_services"):
			target.append("items", {
				"item_code": service.shipment_service,
				"qty": 1,
				"customs_shipment": source.customs_shipment
			})
			
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	doc = get_mapped_doc(
		"Shipment",
		source_name,
		{
			"Shipment": {
				"doctype": "Purchase Invoice",
				"field_map": {
					"delivery_supplier": "supplier",
				},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doc


@frappe.whitelist()
def create_sales_invoice(source_name, target_doc=None):
	def set_missing_values(source, target):
		for service in source.get("shipment_services"):
			target.append("items", {
				"item_code": service.shipment_service,
				"qty": 1,
				"customs_shipment": source.customs_shipment,
				"sales_order": source.sales_order
			})

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	doc = get_mapped_doc(
		"Shipment",
		source_name,
		{
			"Shipment": {
				"doctype": "Sales Invoice",
				"field_map": {
					"delivery_customer": "customer",
					"customs_shipment": "customs_shipment"
				},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doc