"""
Order webhook handlers for Salla.
"""

import frappe
from salla_integration.core.webhooks.registry import WebhookRegistry
from salla_integration.synchronization.orders.sync_manager import OrderSyncManager
from salla_integration.core.utils.helpers import is_incoming_orders_sync_enabled

@WebhookRegistry.register("order.created")
def handle_order_created(payload: dict):
    """Handle order created webhook from Salla."""
    
    
    order_data = payload.get("data", {})
    if not order_data:
        frappe.log_error("No order data in webhook payload", "Salla Webhook Error")
        return
    
    if not is_incoming_orders_sync_enabled():
        frappe.log_message("Incoming order sync is disabled in Salla Settings.", "Salla Webhook Info")
        return
    
    sync_manager = OrderSyncManager()
    sync_manager.create_order(order_data)
    # frappe.enqueue(
    #     sync_manager.sync_from_salla,
    #     order_data=order_data,
    #     queue="default",
    #     job_name=f"salla_order_created_{order_data.get('id')}"
    # )


# @WebhookRegistry.register("order.updated")
# def handle_order_updated(payload: dict):
#     """Handle order updated webhook from Salla."""
    
    
#     order_data = payload.get("data", {})
#     if not order_data:
#         frappe.log_error("No order data in webhook payload", "Salla Webhook Error")
#         return
    
#     sync_manager = OrderSyncManager()
#     frappe.enqueue(
#         sync_manager.sync_from_salla,
#         order_data=order_data,
#         queue="default",
#         job_name=f"salla_order_updated_{order_data.get('id')}"
#     )


# @WebhookRegistry.register("order.status.updated")
# def handle_order_status_updated(payload: dict):
#     """Handle order status updated webhook from Salla."""
    
    
#     order_data = payload.get("data", {})
#     if not order_data:
#         frappe.log_error("No order data in webhook payload", "Salla Webhook Error")
#         return
    
#     sync_manager = OrderSyncManager()
#     frappe.enqueue(
#         sync_manager.update_order_status,
#         order_data=order_data,
#         queue="default",
#         job_name=f"salla_order_status_{order_data.get('id')}"
#     )
