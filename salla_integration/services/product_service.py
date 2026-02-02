"""
Product service layer.
Provides high-level product operations and business logic.
"""

from typing import Any, Optional

import frappe

from salla_integration.core.utils.helpers import get_salla_settings
from salla_integration.jobs.product_jobs import enqueue_bulk_product_sync, enqueue_product_import
from salla_integration.models.mappers import ProductMapper
from salla_integration.models.schemas import ProductSchema
from salla_integration.synchronization.products import ProductSyncManager
from salla_integration.synchronization.products.stock_sync import sync_stock_to_salla


class ProductService:
	"""
	High-level service for product operations.
	Orchestrates sync, validation, and business logic.
	"""

	def __init__(self):
		self.sync_manager = ProductSyncManager()
		self.settings = get_salla_settings()

	def sync_item_to_salla(self, item_code: str) -> dict[str, Any]:
		"""
		Sync a single item to Salla.

		Args:
		    item_code: ERPNext Item code

		Returns:
		    Result dict
		"""
		item = frappe.get_doc("Item", item_code)

		# Validate item
		item_data = ProductMapper.erpnext_to_salla(item)
		validation = ProductSchema.validate_for_salla(item_data)

		if not validation["is_valid"]:
			return {"status": "error", "message": "Validation failed", "errors": validation["errors"]}

		return self.sync_manager.sync_to_salla(item)

	def sync_item_from_salla(self, product_data: dict[str, Any]) -> dict[str, Any]:
		"""
		Sync a product from Salla to ERPNext.

		Args:
		    product_data: Product data from Salla

		Returns:
		    Result dict
		"""
		return self.sync_manager.sync_from_salla(product_data)

	def bulk_sync_to_salla(self, filters: dict | None = None, enqueue: bool = True) -> dict[str, Any]:
		"""
		Sync multiple items to Salla.

		Args:
		    filters: Optional filters for Item query
		    enqueue: Whether to enqueue as background job

		Returns:
		    Result dict or job info
		"""
		if enqueue:
			enqueue_bulk_product_sync(filters)
			return {"status": "enqueued", "message": "Bulk sync job enqueued"}

		query_filters = filters or {}
		query_filters["is_sales_item"] = 1

		items = frappe.get_all("Item", filters=query_filters, fields=["name"])

		success = 0
		failed = 0

		for item_data in items:
			result = self.sync_item_to_salla(item_data.name)
			if result.get("status") == "success":
				success += 1
			else:
				failed += 1

		return {"status": "success", "synced": success, "failed": failed, "total": len(items)}

	def import_from_salla(self, enqueue: bool = True) -> dict[str, Any]:
		"""
		Import all products from Salla.

		Args:
		    enqueue: Whether to enqueue as background job

		Returns:
		    Result dict or job info
		"""
		if enqueue:
			enqueue_product_import()
			return {"status": "enqueued", "message": "Import job enqueued"}

		return self.sync_manager.import_all_products()

	def update_stock(self, item_code: str, warehouse: str | None = None) -> dict[str, Any]:
		"""
		Sync stock levels for an item to Salla.

		Args:
		    item_code: ERPNext Item code
		    warehouse: Optional warehouse

		Returns:
		    Result dict
		"""

		return sync_stock_to_salla(item_code, warehouse)

	def get_sync_status(self, item_code: str) -> dict[str, Any]:
		"""
		Get the sync status for an item.

		Args:
		    item_code: ERPNext Item code

		Returns:
		    Status dict
		"""
		salla_product = frappe.db.get_value(
			"Salla Product",
			{"item_code": item_code},
			["name", "salla_product_id", "sync_status", "last_synced"],
			as_dict=True,
		)

		if not salla_product:
			return {"synced": False, "status": "not_synced"}

		return {
			"synced": True,
			"status": salla_product.sync_status,
			"salla_product_id": salla_product.salla_product_id,
			"last_synced": salla_product.last_synced,
		}

	def get_pending_sync_items(self, limit: int = 100) -> list[str]:
		"""
		Get items that need to be synced.

		Args:
		    limit: Maximum number of items to return

		Returns:
		    List of item codes
		"""
		# Get items not yet synced
		synced_items = frappe.get_all(
			"Salla Product", filters={"sync_status": "Synced"}, fields=["item_code"]
		)
		synced_codes = [p.item_code for p in synced_items]

		# Get sales items not synced
		filters = {"is_sales_item": 1}
		if synced_codes:
			filters["name"] = ["not in", synced_codes]

		items = frappe.get_all("Item", filters=filters, fields=["name"], limit=limit)

		return [i.name for i in items]
