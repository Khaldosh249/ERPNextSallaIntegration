// Copyright (c) 2026, Khaldosh249 and contributors
// For license information, please see license.txt

frappe.listview_settings["Salla Order Status"] = {
	onload: function (listview) {
		// Import all products from Salla
		listview.page.add_inner_button(__("Import All from Salla"), function () {
			frappe.confirm(
				__(
					"This will import all Order Statuses from Salla. New Items will be created for Salla Order Statuses, and existing Order Statuses will be Updates. Continue?"
				),
				() => {
					frappe.call({
						method: "salla_integration.synchronization.orders.sync_manager.get_salla_order_statuses",
						freeze: true,
						freeze_message: __("Importing all..."),
						callback: function (r) {
							if (r.message && r.message.success) {
								frappe.msgprint({
									title: __("Salla Order Status Import"),
									message: r.message.message,
									indicator: "green",
								});
							} else {
								frappe.msgprint({
									title: __("Error"),
									message: r.message
										? r.message.message
										: __("Unknown error occurred"),
									indicator: "red",
								});
							}
						},
					});
				}
			);
		});
	},
};
