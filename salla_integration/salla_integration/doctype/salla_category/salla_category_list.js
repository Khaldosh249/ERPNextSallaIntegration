// Copyright (c) 2026, Khaldosh249 and contributors
// For license information, please see license.txt

frappe.listview_settings["Salla Category"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Import Salla Categories"), function () {
			frappe.call({
				method: "salla_integration.synchronization.categories.sync_manager.import_categories_from_salla",
				freeze: true,
				freeze_message: __("Importing categories from Salla..."),
				callback: function (r) {
					if (!r.exc) {
						frappe.msgprint(__("Categories imported successfully"));
						listview.refresh();
					}
				},
			});
		});
	},
};
