import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.utils import get_currency_precision
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest, get_amount, get_existing_payment_request_amount


class CustomPaymentRequest(PaymentRequest):
    def validate_payment_request_amount(self):
        if self.grand_total == 0:
            frappe.throw(
                _("{0} cannot be zero").format(self.get_label_from_fieldname("grand_total")),
                title=_("Invalid Amount"),
            )

        if self.reference_doctype == "Customs Shipment":
            return

        ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
        if not hasattr(ref_doc, "order_type") or ref_doc.order_type != "Shopping Cart":
            ref_amount = get_amount(ref_doc, self.payment_account)
            if not ref_amount:
                frappe.throw(_("Payment Entry is already created"))

            existing_payment_request_amount = flt(get_existing_payment_request_amount(ref_doc))

            if (
                flt(
                    existing_payment_request_amount + flt(self.grand_total, self.precision("grand_total")),
                    get_currency_precision(),
                )
                > ref_amount
            ):
                frappe.throw(
                    _("Total Payment Request amount cannot be greater than {0} amount").format(
                        self.reference_doctype
                    )
                )