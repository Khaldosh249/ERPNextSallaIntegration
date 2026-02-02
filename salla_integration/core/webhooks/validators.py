"""
Webhook signature validation for Salla webhooks.
"""

import hashlib
import hmac
from typing import Optional

import frappe


def validate_webhook_signature(payload: bytes, signature: str | None) -> bool:
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

	# Calculate expected signature
	expected_signature = hmac.new(webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

	# Compare signatures using constant-time comparison
	return hmac.compare_digest(signature, expected_signature)


def generate_webhook_signature(payload: dict, secret: str) -> str:
	"""
	Generate a webhook signature for testing purposes.

	Args:
	    payload: The webhook payload
	    secret: The webhook secret

	Returns:
	    The generated signature
	"""
	payload_string = frappe.as_json(payload)
	return hmac.new(secret.encode("utf-8"), payload_string.encode("utf-8"), hashlib.sha256).hexdigest()
