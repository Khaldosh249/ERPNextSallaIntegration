"""
Item document event handlers.
Handles ERPNext Item hooks for Salla sync.
"""

import frappe
from salla_integration.core.utils.helpers import get_salla_settings
from salla_integration.synchronization.products.sync_manager import sync_item_sku_on_rename, sync_item_to_salla

# Done
def on_item_update(doc, method=None):
    """
    Handle Item update event.
    Syncs item changes to Salla if enabled.
    
    Args:
        doc: Item document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    print("Item update event triggered for:", doc.name)
    
    if not settings or not settings.enabled:
        print("Salla integration disabled or settings not found.")
        return
    
    # Check if item is a sales item
    if not doc.is_sales_item:
        print("Item is not a sales item. Skipping Salla sync.")
        return
    
    
    print("Enqueueing Salla sync for Item update:", doc.name)
    # Enqueue sync
    # frappe.enqueue(
    #     "salla_integration.synchronization.products.sync_manager.sync_item_to_salla",
    #     doc=doc,
    #     queue="short",
    #     job_name=f"salla_item_update_{doc.name}"
    # )
    sync_item_to_salla(doc, method="item_update")

# Done
def on_item_insert(doc, method=None):
    """
    Handle Item insert event.
    Can auto-create Salla product if enabled.
    
    Args:
        doc: Item document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    
    # Check if item is a sales item
    if not doc.is_sales_item:
        return
    
    
    frappe.enqueue(
        "salla_integration.synchronization.products.sync_manager.sync_item_to_salla",
        doc=doc,
        queue="short",
        job_name=f"salla_price_update_{doc.name}"
    )
    

# TODO: Test this
def before_item_delete(doc, method=None):
    """
    Handle Item delete event.
    Prevents deletion if linked to Salla or handles cleanup.
    
    Args:
        doc: Item document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    # Check if item is linked to Salla
    salla_product = frappe.db.get_value(
        "Salla Product",
        {"item_code": doc.name},
        ["name", "salla_product_id"],
        as_dict=True
    )
    
    if not salla_product:
        return
    
    # Option 1: Prevent deletion
    if getattr(settings, "prevent_deletion_if_synced", True):
        frappe.throw(
            f"Cannot delete Item {doc.name} as it is linked to Salla Product {salla_product.salla_product_id}. "
            "Please unlink or delete the Salla Product first."
        )
    
    # Option 2: Delete from Salla too (if configured)
    # This would require API call to delete product from Salla


# Done
def on_item_price_update(doc, method=None):
    """
    Handle Item Price update event.
    Syncs price changes to Salla.
    
    Args:
        doc: Item Price document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    # Get Item document
    item = frappe.get_doc("Item", doc.item_code)
    
    # sync_item_to_salla(item, method="price_update")
    
    frappe.enqueue(
        "salla_integration.synchronization.products.sync_manager.sync_item_to_salla",
        doc=item,
        queue="short",
        job_name=f"salla_price_update_{item.name}"
    )
    




def after_rename_item(doc, method, old_name, new_name, merge=False):
    """
    Handle Item rename event.
    Updates Salla product linkage if item code changes.
    
    Args:
        doc: Item document
        method: Hook method name
        old_name: Previous item code
        new_name: New item code
        merge: Whether items were merged
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    print(f"Item renamed from {old_name} to {new_name}")
    
    # Update Salla Product linkage
    salla_product = frappe.db.get_value(
        "Salla Product",
        {"item_code": new_name},
        ["name"],
        as_dict=True
    )
    
    
    if salla_product:
        sync_item_sku_on_rename(doc, method, old_name, new_name)



