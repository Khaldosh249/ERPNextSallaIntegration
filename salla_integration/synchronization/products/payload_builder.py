"""
Product payload builder for Salla API.
"""

from typing import Any

import frappe

from salla_integration.core.utils.helpers import get_default_price_list, get_item_price
from salla_integration.synchronization.base.payload_builder import BasePayloadBuilder


class ProductPayloadBuilder(BasePayloadBuilder):
	"""
	Builds API payloads for product synchronization with Salla.
	"""

	def build(self) -> dict[str, Any]:
		"""
		Build the complete product payload based on sync settings.

		Returns:
		    Product payload dict for Salla API
		"""
		item = self.doc

		# Add fields based on sync settings
		if getattr(item, "custom_sync_name", False):
			self.add_name()

		if getattr(item, "custom_sync_description", False):
			self.add_description()

		if getattr(item, "custom_sync_price", False):
			self.add_price()

		# if getattr(item, "custom_sync_sku", False):
		#     self.add_sku()

		if getattr(item, "custom_sync_weight", False):
			self.add_weight()

		if getattr(item, "custom_sync_categories", False):
			self.add_categories()

		# if getattr(item, "custom_sync_stock", False):
		#     self.add_stock()

		return self.payload

	def add_name(self) -> "ProductPayloadBuilder":
		"""Add product name to payload."""
		self.payload["name"] = self.doc.item_name
		return self

	def add_description(self) -> "ProductPayloadBuilder":
		"""Add product description to payload."""
		self.payload["description"] = self.doc.description or ""
		return self

	def add_price(self) -> "ProductPayloadBuilder":
		"""Add product price to payload."""
		price = self._get_item_price()
		if price is not None:
			self.payload["price"] = price
		return self

	def add_weight(self) -> "ProductPayloadBuilder":
		"""Add product weight and UOM to payload."""
		weight = self.doc.weight_per_unit or 0.0
		weight_uom = self.doc.weight_uom or "kg"
		self.payload["weight"] = weight
		self.payload["weight_unit"] = weight_uom
		print(f"Adding weight: {weight} {weight_uom}")
		return self

	# def add_sku(self) -> "ProductPayloadBuilder":
	#     """Add product SKU to payload."""
	#     self.payload["sku"] = self.doc.item_code
	#     return self

	def add_categories(self) -> "ProductPayloadBuilder":
		"""Add product categories to payload."""
		categories = self._get_category_ids()
		if categories:
			self.payload["categories"] = categories
		return self

	def _get_item_price(self) -> float:
		"""Get the item price from Item Price doctype."""
		price = get_item_price(self.doc.item_code)
		return price

	def _get_category_ids(self) -> list[int]:
		"""Get Salla category IDs for the item."""
		category_ids = []

		# Get categories from custom field
		categories = getattr(self.doc, "custom_salla_categories", [])

		for cat in categories:
			salla_category = cat.salla_category
			if salla_category:
				salla_category_id = frappe.db.get_value("Salla Category", salla_category, "salla_category_id")
				if salla_category_id:
					category_ids.append(int(salla_category_id))

		return category_ids


# Build english payload : only include name and description if synced
class ProductPayloadBuilderEn(ProductPayloadBuilder):
	"""
	Builds English product payload for Salla API.
	"""

	def build(self) -> dict[str, Any]:
		"""
		Build the complete English product payload based on sync settings.

		Returns:
		    Product payload dict for Salla API
		"""
		item = self.doc

		# Add fields based on sync settings
		if getattr(item, "custom_sync_name", False):
			self.add_name()

		if getattr(item, "custom_sync_description", False):
			self.add_description()

		return self.payload

	def add_name(self) -> "ProductPayloadBuilderEn":
		"""Add product name to payload."""
		self.payload["name"] = self.doc.custom_item_name_english
		# self.payload["name"] = self.doc.item_name_in_english_cf
		return self

	def add_description(self) -> "ProductPayloadBuilderEn":
		"""Add product description to payload."""
		self.payload["description"] = self.doc.custom_description_en or ""
		return self


def build_salla_product_payload(item) -> dict[str, Any]:
	"""
	Convenience function to build product payload.

	Args:
	    item: The Item document

	Returns:
	    Product payload dict
	"""
	builder = ProductPayloadBuilder(item)
	return builder.build()
