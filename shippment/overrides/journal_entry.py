import frappe


@frappe.whitelist()
def get_party_name(party_type, party):
    if party_type == "Customer":
        return frappe.db.get_value("Customer", party, "customer_name")
    elif party_type == "Supplier":
        return frappe.db.get_value("Supplier", party, "supplier_name")
    elif party_type == "Employee":
        return frappe.db.get_value("Employee", party, "employee_name")
    elif party_type == "Shareholder":
        return frappe.db.get_value("Shareholder", party, "title")


def set_party_name(doc, method):
    for acc in doc.get("accounts"):
        if acc.party_type and acc.party:
            acc.party_name = get_party_name(acc.party_type, acc.party)
        else:
            acc.party_name = ""        