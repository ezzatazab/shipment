# Copyright (c) 2025, NSFSS and contributors
# For license information, please see license.txt

import frappe
import re
from frappe import _
from frappe.utils import now_datetime, flt, get_link_to_form
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document


class CustomsShipment(Document):
	def onload(self):
		if self.is_new():
			shipment_mission = frappe.db.get_single_value("Shipment Settings", "shipment_mission")
			if shipment_mission and not self.shipment_missions:
				self.append("shipment_missions", {
					"shipment_mission": shipment_mission
				})

	def validate(self):
		self.validate_vessel_no()
		self.track_status_change()
		
	def track_status_change(self):
		# Get the previous status from the database
		previous_status = frappe.db.get_value(self.doctype, self.name, "status")

		# If the status has changed, create a new log entry
		if previous_status and previous_status != self.status:
			self.append("status_logs", {
				"status": self.status,
				"changed_on": now_datetime(),
				"changed_by": frappe.session.user
			})

	def validate_vessel_no(self):
		"""
		Validate vessel_no field in vessel_details child table
		- Must be unique
		- Must consist of exactly 4 letters and 7 numbers (in any order)
		- Total length must be 11 characters
		"""
		if not self.vessel_details:
			return
			
		for vessel in self.vessel_details:
			if not vessel.vessel_no:
				continue
			
			# Check total length
			if len(vessel.vessel_no) != 11:
				frappe.throw(
					_("Vessel Number {0} must be exactly 11 characters long (4 letters and 7 numbers)").format(vessel.vessel_no),
					title=_("Invalid Vessel Number Length")
				)
			
			# Count letters and numbers
			letters = sum(1 for c in vessel.vessel_no if c.isalpha())
			numbers = sum(1 for c in vessel.vessel_no if c.isdigit())
			
			# Check if it contains only letters and numbers
			if letters + numbers != 11:
				frappe.throw(
					_("Vessel Number {0} must contain only letters and numbers").format(vessel.vessel_no),
					title=_("Invalid Vessel Number Format")
				)
			
			# Check exact count of letters and numbers
			if letters != 4 or numbers != 7:
				frappe.throw(
					_("Vessel Number {0} must consist of exactly 4 letters and 7 numbers. "
					  "Current: {1} letters and {2} numbers").format(vessel.vessel_no, letters, numbers),
					title=_("Invalid Vessel Number Format")
				)


@frappe.whitelist()
def create_sales_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.delivery_date = source.actual_arrival_date or source.expected_arrival_date

		for mission in source.get("shipment_missions"):
			target.append("items", {
				"item_code": mission.shipment_mission,
				"qty": 1,
				"customs_shipment": source.name
			})

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	doc = get_mapped_doc(
		"Customs Shipment",
		source_name,
		{
			"Customs Shipment": {
				"doctype": "Sales Order",
				"field_map": {
					"customer": "customer"
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
		for mission in source.get("shipment_missions"):
			target.append("items", {
				"item_code": mission.shipment_mission,
				"qty": 1,
				"customs_shipment": source.name
			})
			
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	doc = get_mapped_doc(
		"Customs Shipment",
		source_name,
		{
			"Customs Shipment": {
				"doctype": "Sales Invoice",
				"field_map": {
					"customer": "customer",
					"beneficiary": "beneficiary"
				},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doc


@frappe.whitelist()
def create_shipment(source_name, target_doc=None):
	container = frappe.flags.args.container
	def set_missing_values(source, target):
		if container:
			target.container = container

	doc = get_mapped_doc(
		"Customs Shipment",
		source_name,
		{
			"Customs Shipment": {
				"doctype": "Shipment",
				"field_map": {
					"name": "customs_shipment",
					"customer": "delivery_customer",
					"remarks": "remarks",
					"truck_type": "truck_type",
					"shipment_type": "shipment_type",
				},
			},
			"Shipment Parcel": {
				"doctype": "Shipment Parcel"
			}
		},
		target_doc,
		set_missing_values
	)

	return doc


@frappe.whitelist()
def create_payment_request(source_name, target_doc=None):
	args = frappe.flags.args or {}
	payment_url = args.get("payment_url", "")
	def set_missing_values(source, target):
		target.reference_doctype = source.doctype
		target.reference_name = source.name
		target.payment_request_type = "Inward"
		target.party_type = "Customer"
		target.party = source.customer

		target.transaction_date = args.get("transaction_date") or now_datetime()
		target.mode_of_payment = args.get("mode_of_payment", "")

		amount = flt(args.get("amount", 0))
		target.grand_total = amount
		target.message = f"""
<p>Hello,</p>

<p>Requesting payment against Shipment {source_name} for amount {amount}/p>

<a href="{payment_url}">Make Payment</a>

<p>If you have any questions, please get back to us.</p>

<p>Thank you for your business!</p>
"""

	doc = get_mapped_doc(
		"Customs Shipment",
		source_name,
		{
			"Customs Shipment": {
				"doctype": "Payment Request",
				"field_map": {
				},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doc


@frappe.whitelist()
def get_items_from_sales_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		for item in source.get("items"):
			target.append("shipment_missions", {
				"shipment_mission": item.item_code
			})

	doc = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {
				"doctype": "Customs Shipment",
			}
		},
		target_doc,
		set_missing_values,
	)

	return doc


@frappe.whitelist()
def get_items_from_sales_invoice(source_name, target_doc=None):
	def set_missing_values(source, target):
		for item in source.get("items"):
			target.append("shipment_missions", {
				"shipment_mission": item.item_code
			})

	doc = get_mapped_doc(
		"Sales Invoice",
		source_name,
		{
			"Sales Invoice": {
				"doctype": "Customs Shipment",
			}
		},
		target_doc,
		set_missing_values,
	)

	return doc


@frappe.whitelist()
def create_purchase_invoice(source_name, target_doc=None):
	args = frappe.flags.args or {}
	supplier = args.get("supplier", "")
	mode_of_payment = args.get("mode_of_payment", "")
	items = args.get("items", [])

	def set_missing_values(source, target):
		target.is_paid = 1
		target.supplier = supplier
		target.sales_invoice = source.sales_invoice

		shipment_types = ""
		if source.shipment_type == "Truck":
			shipment_types = "Truck Details: "
			for truck in source.get("truck_details"):
				shipment_types += f"<br> {truck.truck_type} - {truck.truck_name} - {truck.model}"

		elif source.shipment_type == "Container":
			shipment_types = "Container Details: "
			for container in source.get("vessel_details"):
				shipment_types += f"<br> {container.vessel_no} - {container.vessel_type} - {container.weight} - {container.goods_type}"

		elif source.shipment_type == "Parcel":
			shipment_types = "Parcel Details: "
			for parcel in source.get("shipment_parcel"):
				shipment_types += f"<br> {parcel.length} - {parcel.width} - {parcel.height} - {parcel.weight} - {parcel.count}"

		for item in items:
			target.append("items", {
				"item_code": item.get("item_code"),
				"qty": flt(item.get("qty")),
				"rate": flt(item.get("rate")),
				"customs_shipment": source_name,
				"sales_invoice": source.sales_invoice,
				"shipment_types": shipment_types
			})
		
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

		target.mode_of_payment = mode_of_payment
		target.cash_bank_account = get_payment_mode_account(mode_of_payment)
		target.paid_amount = target.grand_total

	doc = get_mapped_doc(
		"Customs Shipment",
		source_name,
		{
			"Customs Shipment": {
				"doctype": "Purchase Invoice"
			}
		},
		target_doc,
		set_missing_values,
	)

	doc.insert(ignore_permissions=True)
	doc_link = get_link_to_form(doc.doctype, doc.name)

	frappe.msgprint(
		msg=_("Purchase Invoice {0} created successfully.").format(doc_link),
		title=_("Success"),
		indicator="green"
	)


def get_payment_mode_account(mode_of_payment):
	payment_mode_account = frappe.db.get_value("Mode of Payment Account", {"parent": mode_of_payment}, "default_account")
	if not payment_mode_account:
		frappe.throw(
			_("Please set a Default Account for Mode of Payment: {0}").format(mode_of_payment),
			title=_("Missing Default Account")
		)
	return payment_mode_account