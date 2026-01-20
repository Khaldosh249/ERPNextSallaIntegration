"""
Webhook registry for handling Salla webhook events.
Routes incoming webhooks to appropriate handlers.
"""

import frappe
from typing import Callable, Dict, Optional
from salla_integration.core.webhooks.validators import validate_webhook_signature

class WebhookRegistry:
    """
    Registry for webhook event handlers.
    Allows registration and dispatch of webhook handlers by event type.
    """
    
    _handlers: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, event_type: str):
        """
        Decorator to register a webhook handler for an event type.
        
        Usage:
            @WebhookRegistry.register("order.created")
            def handle_order_created(payload):
                pass
        """
        def decorator(func: Callable):
            cls._handlers[event_type] = func
            return func
        return decorator
    
    @classmethod
    def get_handler(cls, event_type: str) -> Optional[Callable]:
        """Get the handler for a specific event type."""
        return cls._handlers.get(event_type)
    
    @classmethod
    def dispatch(cls, event_type: str, payload: Dict) -> bool:
        """
        Dispatch a webhook event to its handler.
        
        Args:
            event_type: The webhook event type
            payload: The webhook payload
            
        Returns:
            True if handler was found and executed, False otherwise
        """
        handler = cls.get_handler(event_type)
        if handler:
            try:
                handler(payload)
                return True
            except Exception as e:
                frappe.log_error(
                    f"Webhook handler error for {event_type}: {str(e)}",
                    "Salla Webhook Error"
                )
                raise
        return False
    
    @classmethod
    def list_registered_events(cls) -> list:
        """List all registered event types."""
        return list(cls._handlers.keys())


@frappe.whitelist(allow_guest=True)
def handle_webhook():
    """
    Main webhook endpoint for receiving Salla webhooks.
    Validates signature and dispatches to appropriate handler.
    """
    
    
    # Get request data
    payload = frappe.request.get_json()
    
    if not payload:
        frappe.throw("No payload received", frappe.ValidationError)
    
    # Validate webhook signature
    signature = frappe.request.headers.get("X-Salla-Signature")
    if not validate_webhook_signature(payload, signature):
        frappe.throw("Invalid webhook signature", frappe.AuthenticationError)
    
    # Get event type
    event_type = payload.get("event")
    if not event_type:
        frappe.throw("No event type in payload", frappe.ValidationError)
    
    # Log the webhook
    log_webhook(event_type, payload)
    
    # Dispatch to handler
    handled = WebhookRegistry.dispatch(event_type, payload)
    
    if not handled:
        frappe.log_error(
            f"No handler registered for event: {event_type}",
            "Salla Webhook Warning"
        )
    
    return {"status": "received", "event": event_type}


def log_webhook(event_type: str, payload: Dict):
    """Log webhook event to Salla Webhook Log doctype."""
    try:
        # Check if Salla Webhook Log doctype exists
        if frappe.db.exists("DocType", "Salla Webhook Log"):
            frappe.get_doc({
                "doctype": "Salla Webhook Log",
                "event_type": event_type,
                "payload": frappe.as_json(payload),
                "status": "Received"
            }).insert(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        # Don't fail webhook handling if logging fails
        frappe.log_error(
            f"Failed to log webhook: {str(e)}",
            "Salla Webhook Log Error"
        )
