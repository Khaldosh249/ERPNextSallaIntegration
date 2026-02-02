"""
Unit tests for ProductMapper.
"""

import unittest
from unittest.mock import MagicMock, patch

from salla_integration.models.mappers.product_mapper import ProductMapper


class TestProductMapper(unittest.TestCase):
	"""Test cases for ProductMapper."""

	def test_salla_to_erpnext_basic(self):
		"""Test basic Salla to ERPNext mapping."""
		salla_product = {
			"id": 12345,
			"name": "Test Product",
			"description": "A test product",
			"sku": "TEST-001",
			"price": {"amount": 100},
			"quantity": 50,
			"categories": [],
		}

		result = ProductMapper.salla_to_erpnext(salla_product)

		self.assertEqual(result["item_code"], "TEST-001")
		self.assertEqual(result["item_name"], "Test Product")
		self.assertEqual(result["description"], "A test product")
		self.assertEqual(result["standard_rate"], 100)
		self.assertEqual(result["_salla_id"], "12345")
		self.assertEqual(result["_salla_quantity"], 50)

	def test_salla_to_erpnext_localized_name(self):
		"""Test mapping with localized name."""
		salla_product = {"id": 12345, "name": {"en": "English Name", "ar": "اسم عربي"}, "price": 50}

		result = ProductMapper.salla_to_erpnext(salla_product)

		self.assertEqual(result["item_name"], "English Name")

	def test_salla_to_erpnext_generates_sku(self):
		"""Test SKU generation when not provided."""
		salla_product = {"id": 99999, "name": "No SKU Product", "price": 25}

		result = ProductMapper.salla_to_erpnext(salla_product)

		self.assertEqual(result["item_code"], "SALLA-99999")

	@patch("salla_integration.models.mappers.product_mapper.frappe")
	def test_erpnext_to_salla_basic(self, mock_frappe):
		"""Test basic ERPNext to Salla mapping."""
		item = {
			"item_name": "ERPNext Item",
			"item_code": "ERP-001",
			"description": "An item from ERPNext",
			"standard_rate": 75,
			"_stock_qty": 100,
		}

		mock_frappe.db.get_value.return_value = None

		result = ProductMapper.erpnext_to_salla(item)

		self.assertEqual(result["name"], "ERPNext Item")
		self.assertEqual(result["sku"], "ERP-001")
		self.assertEqual(result["price"], 75.0)
		self.assertEqual(result["quantity"], 100)

	def test_map_images(self):
		"""Test image URL extraction."""
		images = [
			{"url": "https://example.com/img1.jpg"},
			{"original_url": "https://example.com/img2.jpg"},
			{"other_field": "ignored"},
		]

		result = ProductMapper.map_images(images)

		self.assertEqual(len(result), 2)
		self.assertIn("https://example.com/img1.jpg", result)
		self.assertIn("https://example.com/img2.jpg", result)


if __name__ == "__main__":
	unittest.main()
