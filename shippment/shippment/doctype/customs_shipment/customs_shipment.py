# Copyright (c) 2025, NSFSS and contributors
# For license information, please see license.txt

import frappe
import re
from frappe import _
from frappe.utils import now_datetime, flt, get_link_to_form, today
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

	def before_insert(self):
		self.apply_customer_portal_defaults()

	def validate(self):
		self.apply_customer_portal_defaults()
		self.set_shipping_line_details()
		self.validate_vessel_no()
		self.track_status_change()

	def set_shipping_line_details(self):
		if not self.shipping_line:
			self.bl_prefix = None
		else:
			self.bl_prefix = frappe.db.get_value("Shipping Line", self.shipping_line, "bl_prefix")
			agents = [row.name for row in get_agents_for_shipping_line(self.shipping_line)]
			if self.shipping_agent and self.shipping_agent not in agents:
				frappe.throw(
					_("Shipping Agent {0} does not handle Shipping Line {1}").format(
						self.shipping_agent, self.shipping_line
					)
				)
			if not self.shipping_agent and len(agents) == 1:
				self.shipping_agent = agents[0]

		if self.shipping_agent:
			self.agent_prefix = frappe.db.get_value("Shipping Agent", self.shipping_agent, "agent_prefix")
		else:
			self.agent_prefix = None

	def apply_customer_portal_defaults(self):
		if not _is_customer_portal_user():
			return

		customers = get_portal_customers(frappe.session.user)
		if not customers:
			frappe.throw(_("Your user is not linked to a Customer"))

		if not self.customer or self.customer not in customers:
			self.customer = customers[0]

		self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")

		if self.is_new():
			if not self.naming_series:
				self.naming_series = "SHPT-.####"
			if not self.date:
				self.date = today()
			if not self.status:
				self.status = get_portal_status()
			return

		previous = frappe.db.get_value(self.doctype, self.name, ["customer", "status"], as_dict=True)
		if not previous:
			return
		if self.customer != previous.customer:
			frappe.throw(_("You cannot change the customer on this shipment"))
		if self.status != previous.status:
			self.status = previous.status
		
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


def get_list_context(context=None):
	return {
		"title": _("Customs Shipments"),
		"get_list": get_customs_shipment_list,
		"show_sidebar": True,
		"show_search": True,
		"no_breadcrumbs": True,
	}


def get_customs_shipment_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by=None):
	from frappe.www.list import get_list

	filters = filters or {}
	if _is_customer_portal_user():
		customers = get_portal_customers(frappe.session.user)
		if not customers:
			return []
		filters["customer"] = ["in", customers]

	return get_list(
		doctype,
		txt,
		filters,
		limit_start,
		limit_page_length,
		ignore_permissions=False,
		order_by=order_by,
	)


def has_website_permission(doc, ptype, user, verbose=False):
	if not _is_customer_portal_user(user):
		return False
	return doc.customer in get_portal_customers(user)


def has_permission(doc, ptype="read", user=None, debug=False):
	user = user or frappe.session.user
	if not _is_customer_portal_user(user):
		return None
	if ptype == "create" and not doc.get("customer"):
		return None
	if doc.get("customer") in get_portal_customers(user):
		return None
	return False


def get_permission_query_conditions(user, doctype=None):
	if not _is_customer_portal_user(user):
		return ""

	customers = get_portal_customers(user)
	if not customers:
		return "1=0"

	escaped = ", ".join(frappe.db.escape(name) for name in customers)
	return f"`tabCustoms Shipment`.`customer` in ({escaped})"


def get_portal_customers(user):
	customers = frappe.db.sql_list(
		"""select parent from `tabPortal User`
		where user=%s and parenttype='Customer'""",
		user,
	)
	if customers:
		return customers

	contact = frappe.db.get_value("Contact", {"user": user}, "name")
	if not contact:
		return []

	linked = frappe.db.get_value(
		"Dynamic Link",
		{"parenttype": "Contact", "parent": contact, "link_doctype": "Customer"},
		"link_name",
	)
	return [linked] if linked else []


def get_agents_for_shipping_line(shipping_line):
	if not shipping_line:
		return []

	return frappe.db.sql(
		"""
		select sa.name, sa.agent_name
		from `tabShipping Agent` sa
		inner join `tabShipping Agent Line` sal
			on sal.parent = sa.name and sal.parenttype = 'Shipping Agent'
		where sal.shipping_line = %s and ifnull(sa.disabled, 0) = 0
		group by sa.name, sa.agent_name
		order by sa.agent_name
		""",
		shipping_line,
		as_dict=True,
	)


@frappe.whitelist()
def get_shipping_line_agents(shipping_line):
	return get_agents_for_shipping_line(shipping_line)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_shipping_agents(doctype, txt, searchfield, start, page_len, filters):
	shipping_line = (filters or {}).get("shipping_line")
	conditions = ["ifnull(sa.disabled, 0) = 0"]
	values = {
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len,
	}
	if shipping_line:
		conditions.append(
			"""exists (
				select 1 from `tabShipping Agent Line` sal
				where sal.parent = sa.name
					and sal.parenttype = 'Shipping Agent'
					and sal.shipping_line = %(shipping_line)s
			)"""
		)
		values["shipping_line"] = shipping_line

	return frappe.db.sql(
		f"""
		select sa.name, sa.agent_name
		from `tabShipping Agent` sa
		where {" and ".join(conditions)}
			and (sa.name like %(txt)s or ifnull(sa.agent_name, '') like %(txt)s)
		order by sa.agent_name
		limit %(start)s, %(page_len)s
		""",
		values,
	)


def get_portal_status():
	for status in ("مسودة", "New"):
		if frappe.db.exists("Shipping Status", status):
			return status
	frappe.throw(_("Shipping Status is not configured"))


def _is_customer_portal_user(user=None):
	user = user or frappe.session.user
	if user in ("Guest", "Administrator"):
		return False
	roles = set(frappe.get_roles(user))
	if "System Manager" in roles:
		return False
	return "Customer" in roles


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