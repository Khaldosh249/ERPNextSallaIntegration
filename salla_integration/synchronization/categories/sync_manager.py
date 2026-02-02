"""
Category synchronization manager.
Handles syncing categories between ERPNext and Salla.
"""

from typing import Any, Optional

import frappe

from salla_integration.synchronization.base.sync_manager import BaseSyncManager
from salla_integration.synchronization.categories.payload_builder import (
	CategoryPayloadBuilder,
	CategoryPayloadBuilderEn,
	build_salla_category_payload,
)


class CategorySyncManager(BaseSyncManager):
	"""
	Manages category synchronization between ERPNext and Salla.
	Supports bidirectional sync.
	"""

	entity_type = "Category"

	def sync_to_salla(self, category) -> dict[str, Any]:
		"""
		Sync a Salla Category to Salla.

		Args:
		    category: The Salla Category document or name

		Returns:
		    Result dict with status and details
		"""
		# Get category document if string passed
		if isinstance(category, str):
			category = frappe.get_doc("Salla Category", category)

		if getattr(category.flags, "sync_in_progress", False):
			print("Sync already in progress for category:", category.name)
			return {"status": "skipped", "message": "Sync already in progress"}
		category.flags.sync_in_progress = True

		# Build payload
		payload = self.build_payload(category)
		print(payload)
		try:
			if category.salla_category_id:
				print("Updating existing category in Salla")
				# Update existing category
				response = self.client.update_category(
					category.salla_category_id, payload.get("ar", {}), lang="ar"
				)
				self.client.update_category(category.salla_category_id, payload.get("en", {}), lang="en")
				operation = "Update"
			else:
				print("Creating new category in Salla")
				# Create new category
				response = self.client.create_category(payload.get("ar", {}))
				operation = "Create"

				if response.get("success") and response.get("data"):
					salla_category_id = response["data"]["id"]
					self.client.update_category(salla_category_id, payload.get("en", {}), lang="en")
					category.salla_category_id = salla_category_id

					frappe.db.set_value(
						"Salla Category",
						category.name,
						"salla_category_id",
						salla_category_id,
						update_modified=False,
					)

					frappe.db.commit()

			if response.get("success"):
				self.handle_sync_success(
					operation=operation,
					reference_doctype="Salla Category",
					reference_name=category.name,
					salla_id=category.salla_category_id,
				)
				return {"status": "success", "salla_category_id": category.salla_category_id}
			else:
				error_msg = response.get("message", "Unknown error")
				return {"status": "error", "message": error_msg}

		except Exception as e:
			self.handle_sync_error(
				operation="Sync to Salla",
				reference_doctype="Salla Category",
				reference_name=category.name,
				error=e,
				salla_id=category.salla_category_id,
			)
			return {"status": "error", "message": str(e)}

	def sync_from_salla(self, category_data: dict | None = None, **kwargs) -> dict[str, Any]:
		"""
		Sync a category from Salla to ERPNext.

		Args:
		    category_data: Category data from Salla

		Returns:
		    Result dict with status and details
		"""
		# Handle kwargs for enqueue compatibility
		if category_data is None:
			category_data = kwargs.get("category_data", {})

		salla_category_id = category_data.get("id")

		if not salla_category_id:
			return {"status": "error", "message": "No category ID in data"}

		# Check if category exists
		existing = frappe.db.get_value("Salla Category", {"salla_category_id": salla_category_id}, "name")

		try:
			if existing:
				salla_category_data = {
					"category_name": category_data.get("name"),
					"category_name_en": category_data.get("name_en"),
				}
				frappe.db.set_value(
					"Salla Category",
					existing,
					"category_name",
					category_data.get("name"),
					update_modified=False,
				)
				frappe.db.set_value(
					"Salla Category",
					existing,
					"category_name_en",
					category_data.get("name_en"),
					update_modified=False,
				)
				parent_id = category_data.get("parent_id")
				if parent_id:
					parent_name = frappe.db.get_value(
						"Salla Category", {"salla_category_id": parent_id}, "name"
					)
					if parent_name:
						frappe.db.set_value("Salla Category", existing, "parent_salla_category", parent_name)
				operation = "Update"
				frappe.db.commit()
				doc = frappe.get_doc("Salla Category", existing)
				print("Updated category from Salla:", doc.name)
			else:
				# Create new category
				salla_category_data = {
					"doctype": "Salla Category",
					"category_name": category_data.get("name"),
					"salla_category_id": salla_category_id,
					"category_name_en": category_data.get("name_en"),
				}
				parent_id = category_data.get("parent_id")
				if parent_id:
					parent_name = frappe.db.get_value(
						"Salla Category", {"salla_category_id": parent_id}, "name"
					)
					if parent_name:
						salla_category_data["parent_salla_category"] = parent_name
				doc = frappe.get_doc(salla_category_data)
				doc.flags.from_salla_import = True
				doc.insert(ignore_permissions=True)
				operation = "Create"

			frappe.db.commit()

			self.handle_sync_success(
				operation=operation,
				reference_doctype="Salla Category",
				reference_name=doc.name,
				salla_id=salla_category_id,
			)

			return {"status": "success", "category_name": doc.name}

		except Exception as e:
			self.handle_sync_error(
				operation="Sync from Salla",
				reference_doctype="Salla Category",
				reference_name=existing or "New",
				error=e,
				salla_id=salla_category_id,
			)
			print(str(e))

			return {"status": "error", "message": str(e)}

	def build_payload(self, category) -> dict[str, Any]:
		"""Build the Salla API payload for a category in ar and en."""

		builder = build_salla_category_payload(category)

		return builder

	def import_all_categories(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
		"""
		Import all categories from Salla.

		Returns:
		    Result dict with counts
		"""

		try:
			has_more = True
			total_imported = 0
			total_failed = 0
			page = page
			per_page = per_page

			while has_more:
				params = {"page": page, "per_page": per_page, "with": "items,translations"}

				response_in_ar = self.client.get_categories(params=params)
				print(response_in_ar)
				if not response_in_ar.get("success"):
					return {"status": "error", "message": "Failed to fetch categories from Salla"}

				categories_data = response_in_ar.get("data", [])

				for category in categories_data:
					self.import_category_with_items_recursively(category)

				# Check if more pages
				pagination = response_in_ar.get("pagination", {})
				per_page = pagination.get("perPage", per_page)
				current_page = pagination.get("currentPage", 1)
				total_pages = pagination.get("totalPages", 1)

				if current_page < total_pages:
					page += 1
					has_more = True
				else:
					has_more = False

			return {
				"status": "success",
				"imported": total_imported,
				"failed": total_failed,
				"total": total_imported + total_failed,
			}

		except Exception as e:
			print(str(e))

			import traceback

			traceback.print_exc()

			return {"status": "error", "message": str(e)}

	def import_category_with_items_recursively(self, category_data: dict[str, Any]) -> dict[str, Any]:
		salla_category_id = category_data.get("id")

		category_translation = category_data.get("translations", {})
		name_ar = category_translation.get("ar", {}).get("name")
		name_en = category_translation.get("en", {}).get("name")

		category_doc_data = {
			"id": salla_category_id,
			"name": name_ar,
			"name_en": name_en if name_en else name_ar,
			"parent_id": category_data.get("parent_id"),
		}

		result = self.sync_from_salla(category_data=category_doc_data)

		if result.get("status") != "success":
			return result

		items = category_data.get("items", [])

		for item in items:
			self.import_category_with_items_recursively(item)

	def sync_from_salla_by_category_id(self, salla_category_id: str) -> dict[str, Any]:
		"""
		Sync a category from Salla by its Salla category ID in ar and en.

		Args:
		    salla_category_id: The Salla category ID
		"""

		try:
			response_in_ar = self.client.get_category(salla_category_id, lang="ar")
			response_in_en = self.client.get_category(salla_category_id, lang="en")

			if not response_in_ar.get("success") or not response_in_en.get("success"):
				return {"status": "error", "message": "Failed to fetch category from Salla"}

			category_data = {
				"id": salla_category_id,
				"name": response_in_ar.get("data", {}).get("name"),
				"parent_id": response_in_ar.get("data", {}).get("parent_id"),
				"name_en": response_in_en.get("data", {}).get("name"),
			}

			return self.sync_from_salla(category_data=category_data)

		except Exception as e:
			print(str(e))
			return {"status": "error", "message": str(e)}


# Convenience functions


@frappe.whitelist()
def sync_category_to_salla(category):
	"""
	Sync a single category to Salla.
	Whitelisted method for use from frontend.

	Args:
	    category: Category name or JSON string
	"""

	sync_manager = CategorySyncManager()

	return sync_manager.sync_to_salla(category)


@frappe.whitelist()
def import_categories_from_salla():
	"""Import all categories from Salla."""
	sync_manager = CategorySyncManager()

	return sync_manager.import_all_categories()
