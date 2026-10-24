# Copyright (c) 2026, NSFSS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address


class ShippingAgent(Document):
	def validate(self):
		self.validate_shipping_lines()
		self.set_primary_contact("mobile_nos", "mobile_no", "primary_mobile")
		self.set_primary_contact("emails", "email_id", "primary_email")
		self.validate_emails()

	def validate_shipping_lines(self):
		names = []
		for row in self.shipping_lines or []:
			name = (row.shipping_line or "").strip()
			if not name:
				continue
			if name in names:
				frappe.throw(_("Shipping Line {0} is added more than once").format(name))
			names.append(name)
			row.bl_prefix = frappe.db.get_value("Shipping Line", name, "bl_prefix")

	def set_primary_contact(self, table_field, value_field, target_field):
		rows = self.get(table_field) or []
		label = _(self.meta.get_field(table_field).label)
		values = []
		for row in rows:
			value = (row.get(value_field) or "").strip()
			if not value:
				continue
			branch = (row.get("branch") or "").strip()
			key = (value, branch)
			if key in values:
				frappe.throw(_("{0} {1} is added more than once for branch {2}").format(label, value, branch or _("empty")))
			values.append(key)

		primary_rows = [row for row in rows if row.is_primary]
		if len(primary_rows) > 1:
			frappe.throw(_("Select only one primary row in {0}").format(label))
		if rows and not primary_rows:
			rows[0].is_primary = 1
			primary_rows = [rows[0]]

		self.set(target_field, primary_rows[0].get(value_field) if primary_rows else None)

	def validate_emails(self):
		for row in self.emails or []:
			if row.email_id:
				validate_email_address(row.email_id, throw=True)
