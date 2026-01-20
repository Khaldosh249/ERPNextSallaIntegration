// Copyright (c) 2026, Khaldosh249 and contributors
// For license information, please see license.txt

frappe.ui.form.on("Salla Category", {
	refresh(frm) {
        frm.add_custom_button("Sync Categories from Salla", () => {
            frappe.call({
                method: "salla_integration.api.sync_categories.sync_a_category_to_salla",
                args: {
                    category: frm.doc
                },
                callback: function(response) {
                    frappe.msgprint("Categories synced successfully!");
                }
            });
        });
	},
});

