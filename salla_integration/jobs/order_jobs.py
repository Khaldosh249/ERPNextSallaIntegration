"""
Order synchronization jobs.
Background jobs for order sync operations.
"""

from typing import Any, Optional

import frappe

from salla_integration.jobs.base import job_handler
from salla_integration.synchronization.orders import OrderSyncManager


@job_handler(job_type="Order Import", queue="long", timeout=7200)
def import_orders_from_salla_job(
	page: int = 1, per_page: int = 50, status: str | None = None
) -> dict[str, Any]:
	"""
	Import orders from Salla.

	Args:
	    page: Page number to start from
	    per_page: Orders per page
	    status: Optional filter by order status

	Returns:
	    Result dict
	"""
	sync_manager = OrderSyncManager()

	total_imported = 0
	total_failed = 0
	current_page = page

	while True:
		response = sync_manager.client.get_orders(page=current_page, per_page=per_page, status=status)

		if not response.get("success") or not response.get("data"):
			break

		orders = response.get("data", [])

		for order_data in orders:
			result = sync_manager.sync_from_salla(order_data)

			if result.get("status") == "success":
				total_imported += 1
			else:
				total_failed += 1

		# Check if there are more pages
		pagination = response.get("pagination", {})
		if current_page >= pagination.get("total_pages", 1):
			break

		current_page += 1

	return {"status": "success", "imported": total_imported, "failed": total_failed}


@job_handler(job_type="Order Sync", queue="short")
def sync_order_from_webhook_job(order_data: dict[str, Any]) -> dict[str, Any]:
	"""
	Sync an order from webhook data.

	Args:
	    order_data: Order data from webhook

	Returns:
	    Result dict
	"""
	sync_manager = OrderSyncManager()
	return sync_manager.sync_from_salla(order_data)


@job_handler(job_type="Order Status Update", queue="short")
def update_order_status_job(order_data: dict[str, Any]) -> dict[str, Any]:
	"""
	Update order status from webhook.

	Args:
	    order_data: Order data with status update

	Returns:
	    Result dict
	"""
	sync_manager = OrderSyncManager()
	return sync_manager.update_order_status(order_data)


# Convenience functions for enqueuing jobs


def enqueue_order_import(status: str | None = None):
	"""Enqueue an order import job."""
	frappe.enqueue(
		"salla_integration.jobs.order_jobs.import_orders_from_salla_job",
		status=status,
		queue="long",
		timeout=7200,
		job_name="salla_order_import",
	)


def enqueue_order_sync(order_data: dict[str, Any]):
	"""Enqueue an order sync job from webhook."""
	frappe.enqueue(
		"salla_integration.jobs.order_jobs.sync_order_from_webhook_job",
		order_data=order_data,
		queue="short",
		job_name=f"salla_order_sync_{order_data.get('id', 'unknown')}",
	)


def enqueue_order_status_update(order_data: dict[str, Any]):
	"""Enqueue an order status update job from webhook."""
	frappe.enqueue(
		"salla_integration.jobs.order_jobs.update_order_status_job",
		order_data=order_data,
		queue="short",
		job_name=f"salla_order_status_{order_data.get('id', 'unknown')}",
	)


def enqueue_fulfillment_update(
	sales_order_name: str,
	status: str,
	tracking_number: str | None = None,
	shipping_company: str | None = None,
):
	"""Enqueue a fulfillment update job."""
	frappe.enqueue(
		"salla_integration.jobs.order_jobs.update_fulfillment_job",
		sales_order_name=sales_order_name,
		status=status,
		tracking_number=tracking_number,
		shipping_company=shipping_company,
		queue="short",
		job_name=f"salla_fulfillment_{sales_order_name}",
	)
