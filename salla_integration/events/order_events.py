"""
Order event handlers.
Handles ERPNext order-related document hooks for Salla sync.
"""

import frappe
from salla_integration.core.utils.helpers import get_salla_settings
from salla_integration.synchronization.orders.sync_manager import update_salla_order_status_on_delivery_note


def on_delivery_note_submit(doc, method=None):
    """
    Handle Delivery Note submit event.
    Updates order fulfillment status in Salla.
    
    Args:
        doc: Delivery Note document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    # Check if order sync is enabled
    sales_orders = set()
    
    
    for item in doc.items:
        
        if item.against_sales_order:
            
            sales_orders.add(item.against_sales_order)
            
        
    
    results = []
    for sales_order_name in sales_orders:
        
        result = update_salla_order_status_on_delivery_note(sales_order_name)
        results.append(result)
        
    
    
    


def on_sales_invoice_submit(doc, method=None):
    """
    Handle Sales Invoice submit event.
    Can update order status if invoice completes the order.
    
    Args:
        doc: Sales Invoice document
        method: Hook method name
    """
    settings = get_salla_settings()
    
    if not settings or not settings.enabled:
        return
    
    # if not getattr(settings, "sync_orders", True):
    #     return
    
    # Check if linked to a Sales Order that's linked to Salla
    for item in doc.items:
        if item.sales_order:
            salla_order = frappe.db.get_value(
                "Salla Order",
                {"sales_order": item.sales_order},
                ["name", "salla_order_id", "order_status"],
                as_dict=True
            )
            
            if salla_order and salla_order.order_status == "shipped":
                # Order has been shipped and invoiced - consider it delivered
                frappe.enqueue(
                    "salla_integration.synchronization.orders.fulfillment_sync.update_fulfillment_status",
                    salla_order_id=salla_order.salla_order_id,
                    status="delivered",
                    queue="short",
                    job_name=f"salla_delivered_{salla_order.salla_order_id}"
                )
            break


