"""Helpers for Payment Entry voucher print format (سند قبض / سند صرف)."""

from __future__ import annotations

import frappe
from frappe.utils import flt, getdate


EASTERN_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def to_eastern_numerals(value) -> str:
	"""Convert Western digits in a string/number to Eastern Arabic numerals."""
	if value is None:
		return ""
	return str(value).translate(EASTERN_DIGITS)


def gregorian_to_hijri(posting_date) -> tuple[int, int, int]:
	"""Convert a Gregorian date to Hijri (Kuwaiti algorithm). Returns (year, month, day)."""
	if not posting_date:
		return (0, 0, 0)

	g = getdate(posting_date)
	g_year, g_month, g_day = g.year, g.month, g.day

	jd1 = int((1461 * (g_year + 4800 + int((g_month - 14) / 12))) / 4)
	jd2 = int((367 * (g_month - 2 - 12 * (int((g_month - 14) / 12)))) / 12)
	jd3 = int((3 * int((g_year + 4900 + int((g_month - 14) / 12)) / 100)) / 4)
	jd = jd1 + jd2 - jd3 + g_day - 32075

	l = jd - 1948440 + 10632
	n = int((l - 1) / 10631)
	l = l - 10631 * n + 354
	j = int((10985 - l) / 5316) * int((50 * l) / 17719) + int(l / 5670) * int((43 * l) / 15238)
	l = l - int((30 - j) / 15) * int((17719 * j) / 50) - int(j / 16) * int((15238 * j) / 43) + 29
	m = int((24 * l) / 709)
	d = l - int((709 * m) / 24)
	y = 30 * n + j - 30
	return (y, m, d)


def format_hijri_date(posting_date, eastern: bool = True) -> str:
	"""Return Hijri date as DD / MM / YYYY هـ"""
	y, m, d = gregorian_to_hijri(posting_date)
	if not y:
		return ""
	text = f"{d:02d} / {m:02d} / {y}هـ"
	return to_eastern_numerals(text) if eastern else text


def format_gregorian_date(posting_date, eastern: bool = True) -> str:
	"""Return Gregorian date as DD / MM / YYYY م"""
	if not posting_date:
		return ""
	g = getdate(posting_date)
	text = f"{g.day:02d} / {g.month:02d} / {g.year}م"
	return to_eastern_numerals(text) if eastern else text


def split_riyal_halala(amount) -> tuple[int, int]:
	"""Split amount into riyals and halalas (2 decimal places)."""
	value = flt(amount)
	riyal = int(value)
	halala = int(round((value - riyal) * 100))
	if halala == 100:
		riyal += 1
		halala = 0
	return riyal, halala


def money_in_words_ar(amount, currency: str = "SAR") -> str:
	"""Arabic amount in words, e.g. ثلاثمائة وتسعة وخمسون ريال وتسعة وسبعون هللة"""
	from num2words import num2words

	riyal, halala = split_riyal_halala(amount)
	parts = []

	if riyal == 0 and halala == 0:
		return "صفر ريال"

	if riyal:
		try:
			words = num2words(riyal, lang="ar").replace(" و ", " و").replace("  ", " ")
		except Exception:
			words = str(riyal)
		# Grammar-ish unit
		if riyal == 1:
			unit = "ريال"
		elif riyal == 2:
			unit = "ريالان"
		elif 3 <= riyal <= 10:
			unit = "ريالات"
		else:
			unit = "ريال"
		parts.append(f"{words} {unit}")

	if halala:
		try:
			h_words = num2words(halala, lang="ar").replace(" و ", " و").replace("  ", " ")
		except Exception:
			h_words = str(halala)
		if halala == 1:
			h_unit = "هللة"
		elif halala == 2:
			h_unit = "هللتان"
		elif 3 <= halala <= 10:
			h_unit = "هللات"
		else:
			h_unit = "هللة"
		parts.append(f"{h_words} {h_unit}")

	return " و".join(parts)


@frappe.whitelist()
def get_payment_voucher_print_context(name: str | None = None):
	"""Whitelisted entry for print format via frappe.call (no jinja-hooks reload needed)."""
	if not name:
		name = frappe.form_dict.get("name")
	doc = frappe.get_doc("Payment Entry", name)
	doc.check_permission("read")
	return get_payment_voucher_context(doc)


def get_payment_voucher_context(doc) -> dict:
	"""Build display context for Payment Entry voucher print."""
	is_receive = doc.payment_type == "Receive"
	amount = doc.received_amount if is_receive else doc.paid_amount
	riyal, halala = split_riyal_halala(amount)

	company = frappe.get_cached_doc("Company", doc.company)
	tax_id = company.tax_id or company.get("custom_commercial_register") or ""

	# Prefer primary company address
	address = _get_company_address(doc.company)

	mop = doc.mode_of_payment or ""
	mop_type = frappe.db.get_value("Mode of Payment", mop, "type") if mop else None
	mop_lower = mop.lower()
	is_cash = mop_type == "Cash" or "نقد" in mop or "cash" in mop_lower
	is_cheque = (
		"شيك" in mop
		or "cheque" in mop_lower
		or "check" in mop_lower
		or "مسودة" in mop
	)
	is_transfer = (not is_cash and not is_cheque) and (
		mop_type == "Bank" or "تحويل" in mop or "transfer" in mop_lower or "سداد" in mop
	)

	voucher_no = doc.name.split("-")[-1] if doc.name else ""

	# Purpose / description from remarks (first meaningful line) or references
	purpose = (doc.remarks or "").strip()
	if doc.get("references"):
		refs = []
		for row in doc.references:
			if row.reference_name:
				label = f"{row.reference_doctype} {row.reference_name}"
				if row.allocated_amount:
					label += f" ({flt(row.allocated_amount)})"
				refs.append(label)
		if refs and not purpose:
			purpose = "، ".join(refs)

	arabic_company = company.get("company_name_in_arabic") or company.company_name

	return {
		"is_receive": is_receive,
		"title_ar": "سند قبض" if is_receive else "سند صرف",
		"party_label_en": "Received From" if is_receive else "Paid To",
		"party_label_ar": "استلمنا من المكرم" if is_receive else "إصرفوا للمكرم",
		"sign_label_en": "Received By" if is_receive else "Paid By",
		"sign_label_ar": "المستلم" if is_receive else "الصراف",
		"amount": amount,
		"riyal": riyal,
		"halala": halala,
		"riyal_display": to_eastern_numerals(riyal),
		"halala_display": to_eastern_numerals(f"{halala:02d}"),
		"amount_in_words": money_in_words_ar(amount),
		"voucher_no": voucher_no,
		"voucher_no_display": to_eastern_numerals(voucher_no),
		"hijri_date": format_hijri_date(doc.posting_date),
		"gregorian_date": format_gregorian_date(doc.posting_date),
		"company_name": company.company_name,
		"company_name_ar": arabic_company,
		"company_logo": company.company_logo,
		"tax_id": tax_id,
		"tax_id_display": to_eastern_numerals(tax_id),
		"is_cash": is_cash,
		"is_cheque": is_cheque,
		"is_transfer": is_transfer,
		"mode_of_payment": mop,
		"reference_no": doc.reference_no or "",
		"reference_date": format_gregorian_date(doc.reference_date or doc.posting_date),
		"bank_label": mop if (is_transfer or is_cheque or mop_type == "Bank") else "",
		"purpose": purpose,
		"party_name": doc.party_name or doc.party or "",
		"footer_ar": _build_footer_ar(address, company),
		"footer_en": _build_footer_en(address, company),
	}


def _get_company_address(company: str):
	addresses = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "Company", "link_name": company, "parenttype": "Address"},
		pluck="parent",
	)
	if not addresses:
		return None

	preferred = None
	for addr_name in addresses:
		addr = frappe.get_cached_doc("Address", addr_name)
		if addr.disabled:
			continue
		if addr.is_primary_address or addr.is_your_company_address:
			preferred = addr
			break
		if not preferred:
			preferred = addr
	return preferred


def _build_footer_ar(address, company) -> str:
	parts = ["المملكة العربية السعودية"]
	if address:
		city = address.city or ""
		area = address.get("custom_area") or address.county or address.address_line2 or ""
		line = address.address_line1 or ""
		if city:
			parts.append(city)
		if area:
			parts.append(area)
		elif line:
			parts.append(line)
		phone = address.phone or company.phone_no
		if phone:
			parts.append(f"ت: {to_eastern_numerals(phone)}")
	return " - ".join(parts)


def _build_footer_en(address, company) -> str:
	parts = ["SAUDI ARABIA"]
	if address:
		city = (address.city or "").upper()
		# Prefer English address line when available
		line = address.address_line1 or address.address_line2 or ""
		if city:
			parts.append(city)
		if line and line.upper() not in parts:
			parts.append(line.upper())
		phone = address.phone or company.phone_no
		if phone:
			parts.append(f"TEL: {phone}")
	return " - ".join(parts)


def get_invoice_qr_image_src(doc) -> str:
	"""QR image for print: prefer invoice image attachment, then ZATCA SIAF / phase-1 QR."""
	import base64
	from io import BytesIO

	# 1) Image attached to Sales Invoice (prefer filename containing qr)
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
		fields=["file_url", "file_name"],
		order_by="creation desc",
	)
	image_exts = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")
	preferred = None
	fallback = None
	for f in files:
		name = (f.file_name or "").lower()
		url = f.file_url or ""
		if not any(name.endswith(ext) or url.lower().endswith(ext) for ext in image_exts):
			continue
		if "qr" in name:
			preferred = url
			break
		if not fallback:
			fallback = url
	if preferred or fallback:
		return preferred or fallback

	# 2) Sales Invoice Additional Fields QR (phase 2)
	siaf_name = frappe.db.get_value(
		"Sales Invoice Additional Fields", {"sales_invoice": doc.name}, "name"
	)
	if siaf_name:
		siaf = frappe.get_doc("Sales Invoice Additional Fields", siaf_name)
		if getattr(siaf, "qr_image_src", None):
			return siaf.qr_image_src
		if siaf.qr_code:
			try:
				import pyqrcode

				qr = pyqrcode.create(siaf.qr_code)
				with BytesIO() as buffer:
					qr.png(buffer, scale=6)
					buffer.seek(0)
					return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
			except Exception:
				pass

	# 3) Phase 1 generated QR
	try:
		from ksa_compliance.jinja import get_zatca_phase_1_qr_for_invoice

		b64 = get_zatca_phase_1_qr_for_invoice(doc.name)
		if b64:
			return "data:image/png;base64," + b64
	except Exception:
		pass

	return ""


def _classify_service_bucket(item_name: str, item_code: str, has_tax: bool) -> str:
	text = f"{item_name or ''} {item_code or ''}".lower()
	text_ar = f"{item_name or ''} {item_code or ''}"
	if "تخزين" in text_ar and "اضاف" not in text_ar and "تأخير" not in text_ar and "تمديد" not in text_ar:
		return "storage"
	if any(k in text_ar for k in ("تأخير", "تمديد", "اضاف")) or "storage" in text and "add" in text:
		return "additional_storage"
	if has_tax:
		return "taxable"
	return "non_taxable"


def build_tax_invoice_rows(doc) -> list[dict]:
	"""One row per Customs Shipment (or loose item), with amount buckets."""
	import json

	tax_map: dict = {}
	if doc.get("taxes"):
		raw = doc.taxes[0].item_wise_tax_detail
		if raw:
			try:
				tax_map = json.loads(raw) if isinstance(raw, str) else raw
			except Exception:
				tax_map = {}

	groups: dict[str, dict] = {}
	order: list[str] = []

	for item in doc.items:
		key = item.customs_shipment or f"__loose_{item.idx}"
		if key not in groups:
			order.append(key)
			cs = None
			entry_date = exit_date = container = ""
			ref = item.customs_shipment or (item.item_code or item.item_name or "")
			if item.customs_shipment and frappe.db.exists("Customs Shipment", item.customs_shipment):
				cs = frappe.get_cached_doc("Customs Shipment", item.customs_shipment)
				ref = cs.name
				entry_date = (
					cs.actual_arrival_date
					or cs.customs_declaration_date
					or cs.date
					or cs.expected_arrival_date
				)
				exit_date = cs.delivery_permit_date or ""
				vessels = [v.vessel_no for v in (cs.vessel_details or []) if v.vessel_no]
				container = ", ".join(vessels) if vessels else (cs.shipment_type or "")
			groups[key] = {
				"ref": ref,
				"entry_date": entry_date,
				"exit_date": exit_date,
				"container": container,
				"storage": 0.0,
				"additional_storage": 0.0,
				"taxable": 0.0,
				"non_taxable": 0.0,
				"vat": 0.0,
				"total": 0.0,
			}

		row = groups[key]
		amount = flt(item.net_amount or item.amount)
		item_tax = 0.0
		code = item.item_code or item.item_name
		if code and code in tax_map:
			vals = tax_map[code]
			if isinstance(vals, (list, tuple)) and len(vals) >= 2:
				item_tax = flt(vals[1])
			elif isinstance(vals, dict):
				item_tax = flt(vals.get("amount"))
		has_tax = item_tax > 0 or bool(item.item_tax_template)
		bucket = _classify_service_bucket(item.item_name, item.item_code, has_tax)
		row[bucket] = flt(row[bucket]) + amount
		row["vat"] = flt(row["vat"]) + item_tax
		row["total"] = flt(row["total"]) + amount + item_tax

	return [groups[k] for k in order]


def get_company_bank_details(company: str) -> dict:
	"""Best-effort company bank details for the invoice footer."""
	banks = frappe.get_all(
		"Bank Account",
		filters={"company": company, "disabled": 0},
		fields=["account_name", "bank", "bank_account_no", "iban", "is_default", "is_company_account"],
		order_by="is_company_account desc, is_default desc, modified desc",
		limit=5,
	)
	if not banks:
		return {"bank_name": "", "account_no": "", "iban": ""}
	# Prefer company account / default
	ba = banks[0]
	for b in banks:
		if b.get("is_company_account") or b.get("is_default"):
			ba = b
			break
	return {
		"bank_name": ba.get("bank") or ba.get("account_name") or "",
		"account_no": ba.get("bank_account_no") or "",
		"iban": ba.get("iban") or "",
	}


def get_sales_invoice_tax_print_context(doc) -> dict:
	"""Context for Sales Invoice Tax Invoice print format."""
	return {
		"qr_src": get_invoice_qr_image_src(doc),
		"rows": build_tax_invoice_rows(doc),
		"hijri_date": format_hijri_date(doc.posting_date, eastern=False).replace("هـ", "").strip(),
		"gregorian_date": frappe.utils.formatdate(doc.posting_date, "yyyy/MM/dd")
		if doc.posting_date
		else "",
		"hijri_slash": _hijri_slash(doc.posting_date),
		"bank": get_company_bank_details(doc.company),
		"client_name": doc.customer_name or doc.customer or "",
		"net_total": flt(doc.net_total),
		"tax_total": flt(doc.total_taxes_and_charges),
		"grand_total": flt(doc.grand_total),
	}


def _hijri_slash(posting_date) -> str:
	y, m, d = gregorian_to_hijri(posting_date)
	if not y:
		return ""
	return f"{y}/{m:02d}/{d:02d}"
