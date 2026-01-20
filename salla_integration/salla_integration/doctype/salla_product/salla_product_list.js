frappe.listview_settings['Salla Product'] = {
    onload: function(listview) {
        // Import all products from Salla
        listview.page.add_inner_button(__('Import All from Salla'), function() {
            frappe.confirm(
                __('This will import all products from Salla. New Items will be created for products not found by SKU, and existing Items will be linked. Continue?'),
                () => {
                    frappe.call({
                        method: 'salla_integration.api.products.import_products_from_salla',
                        freeze: true,
                        freeze_message: __('Enqueueing product import...'),
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.msgprint({
                                    title: __('Product Import'),
                                    message: r.message.message,
                                    indicator: 'green'
                                });
                            } else {
                                frappe.msgprint({
                                    title: __('Error'),
                                    message: r.message ? r.message.message : __('Unknown error occurred'),
                                    indicator: 'red'
                                });
                            }
                        }
                    });
                }
            );
        });

        // Import single product by Salla ID
        listview.page.add_inner_button(__('Import by Salla ID'), function() {
            frappe.prompt([
                {
                    label: __('Salla Product ID'),
                    fieldname: 'salla_product_id',
                    fieldtype: 'Data',
                    reqd: 1,
                    description: __('Enter the Salla Product ID to import')
                }
            ],
            (values) => {
                frappe.call({
                    method: 'salla_integration.api.products.import_single_product_sync',
                    args: {
                        salla_product_id: values.salla_product_id
                    },
                    freeze: true,
                    freeze_message: __('Importing product...'),
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('Product Import'),
                                message: __('Product imported successfully'),
                                indicator: 'green'
                            });
                            listview.refresh();
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message ? r.message.message : __('Unknown error occurred'),
                                indicator: 'red'
                            });
                        }
                    }
                });
            },
            __('Import Single Product'),
            __('Import')
            );
        });

        // Sync ERP products to Salla
        listview.page.add_inner_button(__('Sync ERP Products to Salla'), function() {
            frappe.call({
                method: 'salla_integration.api.products.create_salla_product_objects',
                freeze: true,
                freeze_message: __('Creating Salla Product objects...'),
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint({
                            title: __('Sync Complete'),
                            message: __('Salla Product objects created for Items marked for sync'),
                            indicator: 'green'
                        });
                        listview.refresh();
                    }
                }
            });
        });
    }
};
