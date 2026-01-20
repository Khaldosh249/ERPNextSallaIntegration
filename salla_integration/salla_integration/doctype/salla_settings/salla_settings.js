// Copyright (c) 2026, Khaldosh249 and contributors
// For license information, please see license.txt

frappe.ui.form.on("Salla Settings", {
  refresh(frm) {
    frm.add_custom_button("Connect Salla", () => {
      window.open(
        "/api/method/salla_integration.api.oauth.start",
        "_blank"
      );
    });

    // Add a button to sync orders
    frm.add_custom_button(__("Sync Orders"), () => {
      frappe.call({
        method: "salla_integration.synchronization.orders.sync_manager.import_orders_from_salla",
        args: {},
        callback: function (r) {
          if (r.message) {
            frappe.msgprint(__("Order synchronization started."));
          }
        },
      });
    }, __("Sync"));

    // Add a button to import all products from Salla
    frm.add_custom_button(__("Import Products from Salla"), () => {
      frappe.confirm(
        __("This will import all products from Salla. New Items will be created for products not found by SKU, and existing Items will be linked. Continue?"),
        () => {
          frappe.call({
            method: "salla_integration.jobs.product_jobs.import_products_from_salla_job",
            args: {},
            freeze: true,
            freeze_message: __("Enqueueing product import..."),
            callback: function (r) {
              if (r.message && r.message.status === "success") {
                frappe.msgprint({
                  title: __("Product Import"),
                  message: `Product import job has been enqueued successfully. Total Products to process: ${r.message.created}.`,
                  indicator: "green"
                });
              } else {
                frappe.msgprint({
                  title: __("Error"),
                  message: r.message ? r.message.message : __("Unknown error occurred"),
                  indicator: "red"
                });
              }
            },
          });
        }
      );
    }, __("Sync"));

    // Add a button to link existing items with Salla products
    frm.add_custom_button(__("Link Existing Items with Salla Products"), () => {
      frappe.confirm(
        __("This will link existing Items in ERPNext with Salla Products based on SKU. Continue?"),
        () => {
          frappe.call({
            method: "salla_integration.synchronization.products.sync_manager.link_existing_items_with_salla_products",
            args: {},
            freeze: true,
            freeze_message: __("Linking existing items..."),
            callback: function (r) {
              if (r.message) {
                // frappe.msgprint({
                //   title: __("Linking Completed"),
                //   message: `Linking completed. Total Items linked: ${r.message.linked_count}.`,
                //   indicator: "green"
                // });
                if(r.message.status == "success"){
                  frappe.msgprint({
                    title: __("Linking Completed"),
                    message: `Linking completed. Total Items linked: ${r.message.linked}.`,
                    indicator: "green"
                  });
                } else {
                  frappe.msgprint({
                    title: __("Error"),
                    message: r.message.message || __("Unknown error occurred"),
                    indicator: "red"
                  });
                }
              }
            },
          });
        }
      );
    }, __("Sync"));

    // Add a button to sync categories from Salla
    frm.add_custom_button(__("Sync Categories from Salla"), () => {
      frappe.call({
        method: "salla_integration.synchronization.categories.sync_manager.sync_all_categories_from_salla",
        args: {},
        freeze: true,
        freeze_message: __("Syncing categories..."),
        callback: function (r) {
          if (r.message) {
            frappe.msgprint({
              title: __("Category Sync"),
              message: __("Category synchronization completed."),
              indicator: "green"
            });
          }
        },
      });
    }, __("Sync"));
  }
});
