"""
Salla Category event handlers.
Handles Salla Category DocType hooks for category sync.
"""

import frappe
from salla_integration.core.utils.helpers import get_salla_settings
from salla_integration.synchronization.categories.sync_manager import sync_category_to_salla


def on_salla_category_update(doc, method=None):
    """
    Handle Salla Category update event.
    Syncs category changes to Salla.
    
    Args:
        doc: Salla Category document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    
    sync_category_to_salla(doc.name)


def on_salla_category_insert(doc, method=None):
    """
    Handle Salla Category insert event.
    Can auto-sync to Salla if enabled.
    
    Args:
        doc: Salla Category document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    
    sync_category_to_salla(doc.name)


def before_salla_category_delete(doc, method=None):
    """
    Handle Salla Category delete event.
    Prevents deletion if category is synced to Salla and has products.
    
    Args:
        doc: Salla Category document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    
    # Check if category has linked products
    linked_products = frappe.db.count(
        "Salla Item Category",
        filters={
            "salla_category": doc.name,
            "parenttype": "Salla Product"
        }
    )
    
    if linked_products > 0:
        frappe.throw(
            f"Cannot delete Salla Category '{doc.category_name}' as it has "
            f"{linked_products} linked products. Remove the products first."
        )
    
    # Check for child categories
    child_categories = frappe.db.count(
        "Salla Category",
        filters={"parent_salla_category": doc.name}
    )
    
    if child_categories > 0:
        frappe.throw(
            f"Cannot delete Salla Category '{doc.category_name}' as it has "
            f"{child_categories} child categories. Remove the child categories first."
        )

