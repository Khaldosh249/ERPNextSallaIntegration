"""
Stock synchronization for Salla products.
"""

from typing import Any

import frappe

from salla_integration.core.client import SallaClient
from salla_integration.core.utils.helpers import (
	get_default_warehouse,
	get_item_stock,
	get_secondary_warehouse,
)


def sync_stock_to_salla(item_code: str) -> dict[str, Any]:
	"""
	Sync stock quantity for an item to Salla.

	Args:
	    item_code: The ERPNext item code

	Returns:
	    Result dict with status and details
	"""
	print("Starting stock sync for item:", item_code)
	# Check if item is synced with Salla
	salla_product = frappe.db.get_value(
		"Salla Product", {"item_code": item_code}, ["salla_product_id", "name"], as_dict=True
	)

	if not salla_product or not salla_product.salla_product_id:
		return {"status": "skipped", "message": "Item not synced with Salla"}

	# Get current stock
	try:
		quantity = get_item_stock(item_code)
	except Exception as e:
		return {"status": "error", "message": f"Failed to get stock: {e!s}"}

	print(f"Syncing stock for {item_code}: {quantity}")

	# Update stock in Salla
	client = SallaClient()

	try:
		print("Updating stock on Salla for product ID:", salla_product.salla_product_id)
		response = client.update_stock(salla_product.salla_product_id, int(quantity))

		print("Stock sync response for", item_code, ":", response)

		if response.get("success"):
			# Update custom_sync_stock for item and stock_sync_status in Salla Product
			frappe.db.set_value("Item", item_code, "custom_stock_sync_status", "Synced")
			frappe.db.set_value("Salla Product", salla_product.name, "stock_sync_status", "Synced")

			return {
				"status": "success",
				"quantity": quantity,
				"salla_product_id": salla_product.salla_product_id,
			}
		else:
			return {"status": "error", "message": response.get("message")}

	except Exception as e:
		frappe.log_error(f"Failed to sync stock for {item_code}: {e!s}", "Salla Stock Sync Error")
		print("Exception during stock sync for Item:", item_code, "Error:", str(e))
		return {"status": "error", "message": str(e)}


def sync_stock_entry_items(stock_entry) -> list[dict[str, Any]]:
	"""
	Sync stock for all items in a stock entry.

	Args:
	    stock_entry: The Stock Entry document

	Returns:
	    List of result dicts for each item
	"""
	results = []
	default_warehouse = get_default_warehouse()
	secondary_warehouse = get_secondary_warehouse()

	if not default_warehouse:
		return [{"status": "error", "message": "No default warehouse configured"}]

	# Get unique items that affect the default warehouse
	items_to_sync = set()

	for item in stock_entry.items:
		if item.t_warehouse == default_warehouse or item.t_warehouse == secondary_warehouse:
			# Check if custom_sync_with_salla and custom_sync_stock both are enabled
			custom_sync_stock = frappe.db.get_value("Item", item.item_code, "custom_sync_stock")
			custom_sync_with_salla = frappe.db.get_value("Item", item.item_code, "custom_sync_with_salla")
			if custom_sync_stock and custom_sync_with_salla:
				items_to_sync.add(item.item_code)
				# Set item custom_stock_sync_status to "Not Synced" before syncing and salla_product stock_sync_status to "Not Synced"
				frappe.db.set_value("Item", item.item_code, "custom_stock_sync_status", "Not Synced")
				salla_product_name = frappe.db.get_value(
					"Salla Product", {"item_code": item.item_code}, "name"
				)
				if salla_product_name:
					frappe.db.set_value(
						"Salla Product", salla_product_name, "stock_sync_status", "Not Synced"
					)
			# custom_sync_with_salla = frappe.db.get_value("Item", item.item_code, "custom_sync_with_salla")
			# if custom_sync_with_salla:
			#     items_to_sync.add(item.item_code)

	# Sync each item
	for item_code in items_to_sync:
		result = sync_stock_to_salla(item_code)
		result["item_code"] = item_code
		results.append(result)

	return results


def handle_stock_entry_submit(doc, method=None):
	"""
	Handle Stock Entry submit event.
	Triggers stock sync for affected items.

	Args:
	    doc: The Stock Entry document
	    method: The hook method name
	"""
	frappe.enqueue(
		"salla_integration.synchronization.products.stock_sync._sync_stock_entry_background",
		stock_entry_name=doc.name,
		queue="default",
		job_name=f"salla_stock_sync_{doc.name}",
	)
	# _sync_stock_entry_background(doc.name)


def handle_stock_entry_cancel(doc, method=None):
	"""
	Handle Stock Entry cancel event.
	Triggers stock sync for affected items.

	Args:
	    doc: The Stock Entry document
	    method: The hook method name
	"""
	frappe.enqueue(
		"salla_integration.synchronization.products.stock_sync._sync_stock_entry_background",
		stock_entry_name=doc.name,
		queue="default",
		job_name=f"salla_stock_sync_cancel_{doc.name}",
	)


def _sync_stock_entry_background(stock_entry_name: str):
	"""
	Background job to sync stock for a stock entry.

	Args:
	    stock_entry_name: The Stock Entry document name
	"""
	stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
	results = sync_stock_entry_items(stock_entry)
	print("Stock sync results for Stock Entry", stock_entry_name, ":", results)
	# Log any errors
	for result in results:
		if result.get("status") == "error":
			frappe.log_error(
				f"Stock sync failed for {result.get('item_code')}: {result.get('message')}",
				"Salla Stock Sync Error",
			)


def _sync_stock_reconciliation_background(stock_reconciliation_name: str):
	"""
	Background job to sync stock for a stock reconciliation.

	Args:
	    stock_reconciliation_name: The Stock Reconciliation document name
	"""
	stock_reconciliation = frappe.get_doc("Stock Reconciliation", stock_reconciliation_name)
	items_to_sync = set()

	for item in stock_reconciliation.items:
		salla_product = frappe.db.get_value("Salla Product", {"item_code": item.item_code}, "name")

		if salla_product:
			items_to_sync.add(item.item_code)

	for item_code in items_to_sync:
		result = sync_stock_to_salla(item_code)
		if result.get("status") == "error":
			frappe.log_error(
				f"Stock sync failed for {item_code}: {result.get('message')}", "Salla Stock Sync Error"
			)


def handle_stock_reconciliation_submit(doc, method=None):
	"""
	Handle Stock Reconciliation submit event.
	Triggers stock sync for affected items.

	Args:
	    doc: The Stock Reconciliation document
	    method: The hook method name
	"""
	frappe.enqueue(
		"salla_integration.synchronization.products.stock_sync._sync_stock_reconciliation_background",
		stock_reconciliation_name=doc.name,
		queue="default",
		job_name=f"salla_stock_reconcile_{doc.name}",
	)
