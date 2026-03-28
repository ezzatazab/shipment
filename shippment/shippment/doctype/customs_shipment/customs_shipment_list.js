frappe.listview_settings['Customs Shipment'] = {
    get_indicator: function (doc) {
        const status_map = {
            "New": {
                label: __("New"),
                color: "blue"
            },
            "Transaction Submitted": {
                label: __("Transaction Submitted"),
                color: "purple"
            },
            "Inspection and Examination": {
                label: __("Inspection & Examination"),
                color: "orange"
            },
            "Special Sections": {
                label: __("Special Sections"),
                color: "red"
            },
            "Collection": {
                label: __("Collection"),
                color: "yellow"
            },
            "Ready for Release": {
                label: __("Ready for Release"),
                color: "green"
            },
            "Fully Released": {
                label: __("Fully Released"),
                color: "green"
            },
            "Transport": {
                label: __("Transport"),
                color: "cyan"
            },
            "Delivered to Finance": {
                label: __("Delivered to Finance"),
                color: "dark gray"
            },
            "Request Closed": {
                label: __("Request Closed"),
                color: "gray"
            }
        };

        if (status_map[doc.status]) {
            return [
                status_map[doc.status].label,
                status_map[doc.status].color,
                "status,=," + doc.status
            ];
        }
    }
};