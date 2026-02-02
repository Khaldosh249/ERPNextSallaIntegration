"""
Product synchronization jobs.
Background jobs for product sync operations.
"""

from typing import Any, Optional

import frappe

from salla_integration.jobs.base import job_handler
from salla_integration.synchronization.products import ProductSyncManager


@job_handler(job_type="Product Sync", queue="default")
def sync_product_to_salla_job(item_code: str) -> dict[str, Any]:
	"""
	Sync a single product to Salla.

	Args:
	    item_code: The ERPNext Item code

	Returns:
	    Result dict
	"""
	sync_manager = ProductSyncManager()
	item = frappe.get_doc("Item", item_code)
	return sync_manager.sync_to_salla(item)


@job_handler(job_type="Product Bulk Sync", queue="long", timeout=7200)
def sync_all_products_job(filters: dict | None = None, batch_size: int = 50) -> dict[str, Any]:
	"""
	Sync all products to Salla.

	Args:
	    filters: Optional filters for Item query
	    batch_size: Number of items to process per batch

	Returns:
	    Result dict with counts
	"""
	sync_manager = ProductSyncManager()

	query_filters = filters or {}
	query_filters["is_sales_item"] = 1

	items = frappe.get_all("Item", filters=query_filters, fields=["name"], limit=1000)

	success = 0
	failed = 0
	skipped = 0

	for item_data in items:
		try:
			item = frappe.get_doc("Item", item_data.name)
			result = sync_manager.sync_to_salla(item)

			if result.get("status") == "success":
				success += 1
			elif result.get("status") == "skipped":
				skipped += 1
			else:
				failed += 1

		except Exception as e:
			failed += 1
			frappe.log_error(f"Error syncing item {item_data.name}: {e}")

	return {
		"status": "success",
		"success": success,
		"failed": failed,
		"skipped": skipped,
		"total": len(items),
	}


# @job_handler(job_type="Product Import", queue="long", timeout=7200)
@frappe.whitelist()
def import_products_from_salla_job(page: int = 1, per_page: int = 50) -> dict[str, Any]:
	"""
	Import all products from Salla.
	Creates Items if not exist, or links existing Items by SKU.

	Args:
	    page: Page number to start from
	    per_page: Products per page

	Returns:
	    Result dict
	"""
	sync_manager = ProductSyncManager()
	return sync_manager.import_all_products(page=page, per_page=per_page)


@job_handler(job_type="Single Product Import", queue="default")
def import_single_product_job(salla_product_id: str) -> dict[str, Any]:
	"""
	Import a single product from Salla by ID.

	Args:
	    salla_product_id: Salla product ID

	Returns:
	    Result dict
	"""
	sync_manager = ProductSyncManager()
	return sync_manager.import_single_product(salla_product_id)


@job_handler(job_type="Stock Sync", queue="short")
def sync_stock_to_salla_job(item_code: str, warehouse: str | None = None) -> dict[str, Any]:
	"""
	Sync stock levels for an item to Salla.

	Args:
	    item_code: The ERPNext Item code
	    warehouse: Optional specific warehouse

	Returns:
	    Result dict
	"""
	from salla_integration.synchronization.products.stock_sync import sync_stock_to_salla

	return sync_stock_to_salla(item_code, warehouse)


@job_handler(job_type="Price Sync", queue="short")
def sync_price_to_salla_job(item_code: str) -> dict[str, Any]:
	"""
	Sync price for an item to Salla.

	Args:
	    item_code: The ERPNext Item code

	Returns:
	    Result dict
	"""
	sync_manager = ProductSyncManager()

	# Get Salla Product
	salla_product = frappe.db.get_value(
		"Salla Product", {"item_code": item_code}, ["name", "salla_product_id"], as_dict=True
	)

	if not salla_product:
		return {"status": "skipped", "message": "Item not synced to Salla"}

	# Get price
	from salla_integration.core.utils.helpers import get_item_price

	price = get_item_price(item_code)

	if not price:
		return {"status": "skipped", "message": "No price found"}

	# Update on Salla
	response = sync_manager.client.update_product(salla_product.salla_product_id, {"price": price})

	return {
		"status": "success" if response.get("success") else "error",
		"message": response.get("message"),
		"price": price,
	}


# Convenience functions for enqueuing jobs


def enqueue_product_sync(item_code: str):
	"""Enqueue a single product sync job."""
	frappe.enqueue(
		"salla_integration.jobs.product_jobs.sync_product_to_salla_job",
		item_code=item_code,
		queue="default",
		job_name=f"salla_product_sync_{item_code}",
	)


def enqueue_bulk_product_sync(filters: dict | None = None):
	"""Enqueue a bulk product sync job."""
	frappe.enqueue(
		"salla_integration.jobs.product_jobs.sync_all_products_job",
		filters=filters,
		queue="long",
		timeout=7200,
		job_name="salla_bulk_product_sync",
	)


def enqueue_product_import():
	"""Enqueue a product import job."""
	frappe.enqueue(
		"salla_integration.jobs.product_jobs.import_products_from_salla_job",
		queue="long",
		timeout=7200,
		job_name="salla_product_import",
	)


def enqueue_single_product_import(salla_product_id: str):
	"""Enqueue a single product import job."""
	frappe.enqueue(
		"salla_integration.jobs.product_jobs.import_single_product_job",
		salla_product_id=salla_product_id,
		queue="default",
		job_name=f"salla_product_import_{salla_product_id}",
	)
