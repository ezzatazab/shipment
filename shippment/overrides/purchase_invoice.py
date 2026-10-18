import frappe


@frappe.whitelist()
def link_customs_shipment(doc, method):
    customs_shipment = doc.customs_shipment
    if not customs_shipment:
        customs_shipment = doc.items[0].customs_shipment
    if customs_shipment:
        shipment = frappe.get_doc("Customs Shipment", customs_shipment)
        for i in doc.get("items"):
            shipment.append("shipment_missions", {
                "shipment_mission": i.item_code,
                "purchase_invoice": doc.name
            })
        shipment.save()


def unlink_customs_shipment(doc, method):
    rows = frappe.get_all(
        "Customs Shipment Mission Detail",
        filters={"purchase_invoice": doc.name, "parenttype": "Customs Shipment"},
        pluck="parent",
    )
    for name in set(rows):
        shipment = frappe.get_doc("Customs Shipment", name)
        removed = False
        for row in list(shipment.shipment_missions):
            if row.purchase_invoice == doc.name:
                shipment.remove(row)
                removed = True
        if removed:
            shipment.save(ignore_permissions=True)
