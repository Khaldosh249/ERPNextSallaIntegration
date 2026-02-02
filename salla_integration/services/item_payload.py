import frappe

from salla_integration.core.utils.helpers import get_default_price_list, get_item_price


def build_salla_product_payload(item):
	payload = {}

	if item.custom_sync_name:
		payload["name"] = item.item_name

	if item.custom_sync_description:
		payload["description"] = item.description or ""

	if item.custom_sync_price:
		# payload["price"] = item.standard_rate
		# Getting price from Item Price doctype
		price_list_rate = get_item_price(item.item_code)
		if price_list_rate is not None:
			payload["price"] = price_list_rate

	if item.custom_sync_sku:
		payload["sku"] = item.item_code

	if item.custom_sync_categories:
		payload["categories"] = map_item_categories(item)

	return payload


def map_item_categories(item):
	category_ids = item.custom_salla_categories

	category_ids_list = []

	for cat in category_ids:
		cat_doc = frappe.get_doc("Salla Category", cat.salla_category)

		if cat_doc.salla_category_id:
			category_ids_list.append(cat_doc.salla_category_id)

	print("Mapped Category IDs:", category_ids_list)
	return category_ids_list
