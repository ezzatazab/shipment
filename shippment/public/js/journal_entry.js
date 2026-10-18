frappe.ui.form.on("Journal Entry Account", {
    party: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        if (d.party_type && d.party) {
            frappe.call({
                method: "shippment.overrides.journal_entry.get_party_name",
                args: {
                    party_type: d.party_type,
                    party: d.party
                },
                callback: function (r) {
                    frappe.model.set_value(cdt, cdn, "party_name", r.message);
                }
            });
        }else {
            frappe.model.set_value(cdt, cdn, "party_name", "");
        }
    }
});