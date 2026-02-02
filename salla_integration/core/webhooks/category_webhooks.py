"""
Category webhook handlers for Salla.
"""

import frappe

from salla_integration.core.webhooks.registry import WebhookRegistry
from salla_integration.synchronization.categories.sync_manager import CategorySyncManager


@WebhookRegistry.register("category.created")
def handle_category_created(payload: dict):
	"""Handle category created webhook from Salla."""

	category_data = payload.get("data", {})
	if not category_data:
		frappe.log_error("No category data in webhook payload", "Salla Webhook Error")
		return

	sync_manager = CategorySyncManager()
	frappe.enqueue(
		sync_manager.sync_from_salla,
		category_data=category_data,
		queue="default",
		job_name=f"salla_category_created_{category_data.get('id')}",
	)


@WebhookRegistry.register("category.updated")
def handle_category_updated(payload: dict):
	"""Handle category updated webhook from Salla."""

	category_data = payload.get("data", {})
	if not category_data:
		frappe.log_error("No category data in webhook payload", "Salla Webhook Error")
		return

	sync_manager = CategorySyncManager()
	frappe.enqueue(
		sync_manager.sync_from_salla,
		category_data=category_data,
		queue="default",
		job_name=f"salla_category_updated_{category_data.get('id')}",
	)
