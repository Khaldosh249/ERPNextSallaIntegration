"""
Customer synchronization jobs.
Background jobs for customer sync operations.
"""

from typing import Any, Optional

import frappe

from salla_integration.jobs.base import job_handler
from salla_integration.synchronization.customers import CustomerSyncManager


@job_handler(job_type="Customer Import", queue="long", timeout=3600)
def import_customers_from_salla_job(page: int = 1, per_page: int = 50) -> dict[str, Any]:
	"""
	Import customers from Salla.

	Args:
	    page: Page number to start from
	    per_page: Customers per page

	Returns:
	    Result dict
	"""
	sync_manager = CustomerSyncManager()

	total_imported = 0
	total_updated = 0
	total_failed = 0
	current_page = page

	while True:
		response = sync_manager.client.get_customers(page=current_page, per_page=per_page)

		if not response.get("success") or not response.get("data"):
			break

		customers = response.get("data", [])

		for customer_data in customers:
			result = sync_manager.sync_from_salla(customer_data)

			if result.get("status") == "success":
				total_imported += 1
			elif result.get("status") == "updated":
				total_updated += 1
			else:
				total_failed += 1

		# Check if there are more pages
		pagination = response.get("pagination", {})
		if current_page >= pagination.get("total_pages", 1):
			break

		current_page += 1

	return {"status": "success", "imported": total_imported, "updated": total_updated, "failed": total_failed}


@job_handler(job_type="Customer Sync", queue="short")
def sync_customer_from_webhook_job(customer_data: dict[str, Any]) -> dict[str, Any]:
	"""
	Sync a customer from webhook data.

	Args:
	    customer_data: Customer data from webhook

	Returns:
	    Result dict
	"""
	sync_manager = CustomerSyncManager()
	return sync_manager.sync_from_salla(customer_data)


# Convenience functions for enqueuing jobs


def enqueue_customer_import():
	"""Enqueue a customer import job."""
	frappe.enqueue(
		"salla_integration.jobs.customer_jobs.import_customers_from_salla_job",
		queue="long",
		timeout=3600,
		job_name="salla_customer_import",
	)


def enqueue_customer_sync(customer_data: dict[str, Any]):
	"""Enqueue a customer sync job from webhook."""
	frappe.enqueue(
		"salla_integration.jobs.customer_jobs.sync_customer_from_webhook_job",
		customer_data=customer_data,
		queue="short",
		job_name=f"salla_customer_sync_{customer_data.get('id', 'unknown')}",
	)
