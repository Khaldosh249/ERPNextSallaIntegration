"""
Webhook signature validation for Salla webhooks.
"""

import hmac
import hashlib
import frappe
from typing import Dict, Optional


def validate_webhook_signature(payload: bytes, signature: Optional[str]) -> bool:
    """
    Validate the webhook signature from Salla.
    
    Args:
        payload: The webhook payload
        signature: The X-Salla-Signature header value
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature:
        return False
    
    settings = frappe.get_single("Salla Settings")
    webhook_secret = settings.get_password("webhook_secret") if hasattr(settings, "webhook_secret") else None
    
    if not webhook_secret:
        # If no webhook secret is configured, skip validation
        # This allows for easier development but should be enforced in production
        frappe.log_error(
            "Webhook secret not configured. Signature validation skipped.",
            "Salla Webhook Warning"
        )
        return True
    
    # Calculate expected signature
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    
    # Compare signatures using constant-time comparison
    return hmac.compare_digest(signature, expected_signature)


def generate_webhook_signature(payload: Dict, secret: str) -> str:
    """
    Generate a webhook signature for testing purposes.
    
    Args:
        payload: The webhook payload
        secret: The webhook secret
        
    Returns:
        The generated signature
    """
    payload_string = frappe.as_json(payload)
    return hmac.new(
        secret.encode("utf-8"),
        payload_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
