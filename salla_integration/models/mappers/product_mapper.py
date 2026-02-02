"""
Product entity mapper.
Maps between Salla product format and ERPNext Item format.
Uses Salla Item Category child table for category links.
"""

from typing import Any, Optional

import frappe


class ProductMapper:
	"""
	Bidirectional mapper for Product/Item entities.
	Uses Salla Item Category for product-category relationships.
	"""

	@staticmethod
	def salla_to_erpnext(
		salla_product: dict[str, Any], english_salla_product: dict[str, Any]
	) -> dict[str, Any]:
		"""
		Map Salla product to ERPNext Item format.

		Args:
		    salla_product: Product data from Salla API

		Returns:
		    Dict formatted for ERPNext Item creation
		"""

		english_product_item = english_salla_product

		# Extract basic info
		name_in_ar = salla_product.get("name", "")

		name_in_en = english_product_item.get("name", "")

		description_in_ar = salla_product.get("description", "")

		description_in_en = english_product_item.get("description", "")

		sku = salla_product.get("sku") or f"SALLA-{salla_product.get('id')}"

		# Price handling
		price = salla_product.get("price", {})
		item_price = price.get("amount", 0)

		# Stock handling
		quantity = int(salla_product.get("quantity") or 0)

		# Map categories to Salla Item Category format
		salla_item_categories = ProductMapper._map_salla_categories(salla_product.get("categories", []))

		erpnext_item = {
			"doctype": "Item",
			"item_code": sku,
			"item_name": name_in_ar,
			"item_name_in_english_cf": name_in_en,
			"description": description_in_ar,
			"custom_description_en": description_in_en,
			"standard_rate": item_price,
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"is_sales_item": 1,
			"item_group": "Products",  # Default item group
			"custom_salla_categories": ProductMapper._map_salla_categories(
				salla_product.get("categories", [])
			),
			"_salla_id": str(salla_product.get("id")),
			"_salla_quantity": quantity,
			"_salla_item_categories": salla_item_categories,
		}

		print(erpnext_item)

		return erpnext_item

	@staticmethod
	def erpnext_to_salla(item: Any) -> dict[str, Any]:
		"""
		Map ERPNext Item to Salla product format.

		Args:
		    item: ERPNext Item document or dict

		Returns:
		    Dict formatted for Salla API
		"""
		# Handle both document and dict
		if hasattr(item, "as_dict"):
			item_data = item.as_dict()
		else:
			item_data = item

		product = {
			"name": item_data.get("item_name", item_data.get("name")),
			"description": item_data.get("description", ""),
			"sku": item_data.get("item_code"),
		}

		# Add price if available
		price = item_data.get("standard_rate") or item_data.get("_price")
		if price:
			product["price"] = float(price)

		# Add stock if available
		stock = item_data.get("_stock_qty")
		if stock is not None:
			product["quantity"] = int(stock)

		# Get categories from Salla Product linked categories
		categories = ProductMapper._get_item_salla_categories(item_data)
		if categories:
			product["categories"] = categories

		return product

	@staticmethod
	def _map_salla_categories(salla_categories: list[dict]) -> list[dict]:
		"""
		Map Salla categories to Salla Item Category child table format.

		Args:
		    salla_categories: List of category dicts from Salla

		Returns:
		    List of Salla Item Category dicts
		"""
		item_categories = []

		for i, cat in enumerate(salla_categories):
			salla_cat_id = str(cat.get("id", ""))
			if not salla_cat_id:
				continue

			# Find or note the Salla Category
			salla_category_name = frappe.db.get_value(
				"Salla Category", {"salla_category_id": salla_cat_id}, "name"
			)

			if salla_category_name:
				item_categories.append(
					{"salla_category": salla_category_name, "is_primary": 1 if i == 0 else 0}
				)

		return item_categories

	@staticmethod
	def _get_item_salla_categories(item_data: dict) -> list[int]:
		"""
		Get Salla category IDs for an item from Salla Product.

		Args:
		    item_data: Item data dict

		Returns:
		    List of Salla category IDs
		"""
		categories = []
		item_code = item_data.get("item_code") or item_data.get("name")

		if not item_code:
			return categories

		# Get Salla Product for this item
		salla_product = frappe.db.get_value("Salla Product", {"item_code": item_code}, "name")

		if not salla_product:
			return categories

		# Get linked Salla Item Categories from Salla Product
		item_categories = frappe.get_all(
			"Salla Item Category",
			filters={"parent": salla_product, "parenttype": "Salla Product"},
			fields=["salla_category"],
		)

		for cat in item_categories:
			if cat.salla_category:
				salla_cat_id = frappe.db.get_value("Salla Category", cat.salla_category, "salla_category_id")
				if salla_cat_id:
					try:
						categories.append(int(salla_cat_id))
					except (ValueError, TypeError):
						pass

		return categories

	@staticmethod
	def link_item_to_categories(item_code: str, salla_categories: list[dict]) -> None:
		"""
		Link an item to Salla Categories via Salla Product.

		Args:
		    item_code: ERPNext Item code
		    salla_categories: List of category dicts with salla_category_id
		"""
		# Get or create Salla Product
		salla_product = frappe.db.get_value("Salla Product", {"item_code": item_code}, "name")

		if not salla_product:
			return

		# Get the document
		salla_product_doc = frappe.get_doc("Salla Product", salla_product)

		# Clear existing categories if any
		if hasattr(salla_product_doc, "salla_item_categories"):
			salla_product_doc.salla_item_categories = []

		# Add new categories
		for i, cat_data in enumerate(salla_categories):
			salla_cat_id = str(cat_data.get("id", cat_data.get("salla_category_id", "")))

			if not salla_cat_id:
				continue

			# Find Salla Category
			salla_category_name = frappe.db.get_value(
				"Salla Category", {"salla_category_id": salla_cat_id}, "name"
			)

			if salla_category_name and hasattr(salla_product_doc, "salla_item_categories"):
				salla_product_doc.append(
					"salla_item_categories",
					{"salla_category": salla_category_name, "is_primary": 1 if i == 0 else 0},
				)

		salla_product_doc.save(ignore_permissions=True)
		frappe.db.commit()

	@staticmethod
	def map_images(salla_images: list[dict]) -> list[str]:
		"""
		Extract image URLs from Salla product images.

		Args:
		    salla_images: List of image dicts from Salla

		Returns:
		    List of image URLs
		"""
		urls = []
		for img in salla_images:
			url = img.get("url") or img.get("original_url")
			if url:
				urls.append(url)
		return urls

	@staticmethod
	def map_variants(salla_variants: list[dict]) -> list[dict]:
		"""
		Map Salla product variants to ERPNext variant format.

		Args:
		    salla_variants: List of variant dicts from Salla

		Returns:
		    List of variant data dicts
		"""
		variants = []
		for var in salla_variants:
			variants.append(
				{
					"sku": var.get("sku"),
					"price": var.get("price", {}).get("amount", 0),
					"quantity": var.get("stock_quantity", 0),
					"options": var.get("options", []),
				}
			)
		return variants

	@staticmethod
	def get_primary_category(item_code: str) -> str | None:
		"""
		Get the primary Salla Category for an item.

		Args:
		    item_code: ERPNext Item code

		Returns:
		    Salla Category name or None
		"""
		salla_product = frappe.db.get_value("Salla Product", {"item_code": item_code}, "name")

		if not salla_product:
			return None

		primary_cat = frappe.db.get_value(
			"Salla Item Category",
			{"parent": salla_product, "parenttype": "Salla Product", "is_primary": 1},
			"salla_category",
		)

		return primary_cat
