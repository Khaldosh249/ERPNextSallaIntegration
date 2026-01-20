"""
Fulfillment synchronization for orders.
Handles shipping and delivery status updates.
"""

import frappe
from typing import Dict, Any, Optional

from salla_integration.core.client import SallaClient


def update_fulfillment_status(
    salla_order_id: str,
    status: str,
    tracking_number: Optional[str] = None,
    shipping_company: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update fulfillment status for an order in Salla.
    
    Args:
        salla_order_id: The Salla order ID
        status: The new fulfillment status
        tracking_number: Optional tracking number
        shipping_company: Optional shipping company name
        
    Returns:
        Result dict
    """
    client = SallaClient()
    
    try:
        payload = {"status": status}
        
        if tracking_number:
            payload["tracking_number"] = tracking_number
        
        if shipping_company:
            payload["shipping_company"] = shipping_company
        
        response = client.update_order_status(salla_order_id, status)
        
        if response.get("success"):
            # Update local record
            salla_order = frappe.db.get_value(
                "Salla Order",
                {"salla_order_id": salla_order_id},
                "name"
            )
            if salla_order:
                frappe.db.set_value("Salla Order", salla_order, "order_status", status)
                frappe.db.commit()
            
            return {"status": "success", "new_status": status}
        else:
            return {"status": "error", "message": response.get("message")}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}


def mark_order_shipped(
    sales_order_name: str,
    tracking_number: Optional[str] = None,
    shipping_company: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mark an order as shipped and sync to Salla.
    
    Args:
        sales_order_name: The ERPNext Sales Order name
        tracking_number: Optional tracking number
        shipping_company: Optional shipping company
        
    Returns:
        Result dict
    """
    # Get Salla Order
    salla_order = frappe.db.get_value(
        "Salla Order",
        {"sales_order": sales_order_name},
        ["name", "salla_order_id"],
        as_dict=True
    )
    
    if not salla_order:
        return {"status": "error", "message": "No Salla order found for this Sales Order"}
    
    return update_fulfillment_status(
        salla_order.salla_order_id,
        "shipped",
        tracking_number,
        shipping_company
    )


def mark_order_delivered(sales_order_name: str) -> Dict[str, Any]:
    """
    Mark an order as delivered and sync to Salla.
    
    Args:
        sales_order_name: The ERPNext Sales Order name
        
    Returns:
        Result dict
    """
    # Get Salla Order
    salla_order = frappe.db.get_value(
        "Salla Order",
        {"sales_order": sales_order_name},
        ["name", "salla_order_id"],
        as_dict=True
    )
    
    if not salla_order:
        return {"status": "error", "message": "No Salla order found for this Sales Order"}
    
    return update_fulfillment_status(salla_order.salla_order_id, "delivered")


def handle_delivery_note_submit(doc, method=None):
    """
    Handle Delivery Note submission to update Salla order status.
    
    Args:
        doc: The Delivery Note document
        method: Hook method name
    """
    # Get linked Sales Order
    for item in doc.items:
        if item.against_sales_order:
            # Check if this Sales Order is linked to Salla
            salla_order = frappe.db.get_value(
                "Salla Order",
                {"sales_order": item.against_sales_order},
                "salla_order_id"
            )
            
            if salla_order:
                frappe.enqueue(
                    "salla_integration.synchronization.orders.fulfillment_sync.update_fulfillment_status",
                    salla_order_id=salla_order,
                    status="shipped",
                    queue="default",
                    job_name=f"salla_fulfillment_{salla_order}"
                )
            break
