"""
Integration tests for sync managers.
These tests require a Frappe environment.
"""

import unittest

import frappe


class TestProductSyncManager(unittest.TestCase):
	"""Integration tests for ProductSyncManager."""

	@classmethod
	def setUpClass(cls):
		"""Set up test data."""
		# Create test item if not exists
		if not frappe.db.exists("Item", "TEST-SALLA-001"):
			item = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "TEST-SALLA-001",
					"item_name": "Test Salla Product",
					"item_group": "Products",
					"stock_uom": "Nos",
					"is_sales_item": 1,
					"is_stock_item": 1,
				}
			)
			item.insert(ignore_permissions=True)
			frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		"""Clean up test data."""
		# Delete test item
		if frappe.db.exists("Item", "TEST-SALLA-001"):
			frappe.delete_doc("Item", "TEST-SALLA-001", force=True)
			frappe.db.commit()

	def test_sync_manager_initialization(self):
		"""Test sync manager initializes correctly."""
		from salla_integration.synchronization.products import ProductSyncManager

		manager = ProductSyncManager()

		self.assertIsNotNone(manager)
		self.assertEqual(manager.entity_type, "Product")

	def test_build_payload(self):
		"""Test payload building for an item."""
		from salla_integration.synchronization.products import ProductSyncManager

		manager = ProductSyncManager()
		item = frappe.get_doc("Item", "TEST-SALLA-001")

		payload = manager.build_payload(item)

		self.assertIn("name", payload)
		self.assertIn("sku", payload)
		self.assertEqual(payload["sku"], "TEST-SALLA-001")


class TestCategorySyncManager(unittest.TestCase):
	"""Integration tests for CategorySyncManager."""

	def test_sync_manager_initialization(self):
		"""Test sync manager initializes correctly."""
		from salla_integration.synchronization.categories import CategorySyncManager

		manager = CategorySyncManager()

		self.assertIsNotNone(manager)
		self.assertEqual(manager.entity_type, "Category")


if __name__ == "__main__":
	unittest.main()
