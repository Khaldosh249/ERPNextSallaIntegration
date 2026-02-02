"""
Category service layer.
Provides high-level category operations and business logic.
"""

from typing import Any, Optional

import frappe

from salla_integration.jobs.category_jobs import enqueue_category_import
from salla_integration.models.mappers import CategoryMapper
from salla_integration.models.schemas import CategorySchema
from salla_integration.synchronization.categories import CategorySyncManager


class CategoryService:
	"""
	High-level service for category operations.
	Uses Salla Category DocType exclusively.
	"""

	def __init__(self):
		self.sync_manager = CategorySyncManager()

	def sync_category_to_salla(self, salla_category_name: str) -> dict[str, Any]:
		"""
		Sync a single Salla Category to Salla.

		Args:
		    salla_category_name: Salla Category document name

		Returns:
		    Result dict
		"""
		salla_category = frappe.get_doc("Salla Category", salla_category_name)

		# Validate
		category_data = CategoryMapper.erpnext_to_salla(salla_category)
		validation = CategorySchema.validate_for_salla(category_data)

		if not validation["is_valid"]:
			return {"status": "error", "message": "Validation failed", "errors": validation["errors"]}

		return self.sync_manager.sync_to_salla(salla_category)

	def import_from_salla(self, enqueue: bool = True) -> dict[str, Any]:
		"""
		Import all categories from Salla.

		Args:
		    enqueue: Whether to enqueue as background job

		Returns:
		    Result dict
		"""
		if enqueue:
			enqueue_category_import()
			return {"status": "enqueued", "message": "Import job enqueued"}

		return self.sync_manager.import_all_categories()

	def get_category_tree(self) -> list[dict]:
		"""
		Get the Salla Category tree structure.

		Returns:
		    Nested list of categories
		"""

		def build_tree(parent: str | None = None) -> list[dict]:
			filters = (
				{"parent_salla_category": parent} if parent else {"parent_salla_category": ["is", "not set"]}
			)

			children = frappe.get_all(
				"Salla Category",
				filters=filters,
				fields=["name", "category_name", "salla_category_id", "is_active"],
				order_by="lft",
			)

			result = []
			for child in children:
				result.append(
					{
						"name": child.name,
						"label": child.category_name,
						"synced": bool(child.salla_category_id),
						"salla_id": child.salla_category_id,
						"is_active": child.is_active,
						"children": build_tree(child.name),
					}
				)

			return result

		return build_tree()

	def get_sync_status(self, salla_category_name: str) -> dict[str, Any]:
		"""
		Get sync status for a Salla Category.

		Args:
		    salla_category_name: Salla Category name

		Returns:
		    Status dict
		"""
		salla_cat = frappe.db.get_value(
			"Salla Category", salla_category_name, ["name", "salla_category_id", "is_active"], as_dict=True
		)

		if not salla_cat:
			return {"synced": False, "status": "not_found"}

		return {
			"synced": bool(salla_cat.salla_category_id),
			"status": "synced" if salla_cat.salla_category_id else "not_synced",
			"salla_category_id": salla_cat.salla_category_id,
			"is_active": salla_cat.is_active,
		}

	def get_products_in_category(self, salla_category_name: str) -> list[str]:
		"""
		Get all products linked to a Salla Category.

		Args:
		    salla_category_name: Salla Category name

		Returns:
		    List of item codes
		"""
		# Find Salla Products with this category
		salla_products = frappe.get_all(
			"Salla Item Category",
			filters={"salla_category": salla_category_name, "parenttype": "Salla Product"},
			fields=["parent"],
		)

		item_codes = []
		for sp in salla_products:
			item_code = frappe.db.get_value("Salla Product", sp.parent, "item_code")
			if item_code:
				item_codes.append(item_code)

		return item_codes
