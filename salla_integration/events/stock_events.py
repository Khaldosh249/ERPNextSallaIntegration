"""
Stock entry event handlers.
Handles ERPNext Stock Entry hooks for Salla stock sync.
"""

import frappe
from salla_integration.core.utils.helpers import get_salla_settings
from salla_integration.synchronization.products.stock_sync import handle_stock_entry_cancel, handle_stock_entry_submit, handle_stock_reconciliation_submit, sync_stock_to_salla


# Done
def on_stock_entry_submit(doc, method=None):
    """
    Handle Stock Entry submit event.
    Syncs stock changes to Salla for affected items.
    
    Args:
        doc: Stock Entry document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    print("Stock Entry submit event triggered for:", doc.name)
    
    
    handle_stock_entry_submit(doc, method)
    
    

# Done
def on_stock_entry_cancel(doc, method=None):
    """
    Handle Stock Entry cancel event.
    Re-syncs stock to Salla to reflect reversed quantities.
    
    Args:
        doc: Stock Entry document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    handle_stock_entry_cancel(doc, method)
    


# TODO: Test this
def on_stock_reconciliation_submit(doc, method=None):
    """
    Handle Stock Reconciliation submit event.
    Syncs adjusted stock levels to Salla.
    
    Args:
        doc: Stock Reconciliation document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    
    handle_stock_reconciliation_submit(doc, method)

