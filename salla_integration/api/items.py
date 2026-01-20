import frappe
from salla_integration.services.item_payload import build_salla_product_payload
from salla_integration.api.salla_client import SallaClient
from erpnext.stock.utils import get_bin


@frappe.whitelist()
def sync_item_to_salla(doc, method):
    """
    Sync a single item to Salla based on the provided item_code.
    """
    # item = 
    
    # Doc can be either Item or Item Price
    if doc.doctype == "Item":
        item = doc
    elif doc.doctype == "Item Price":
        item_code = doc.item_code
        item = frappe.get_doc("Item", item_code)
    else:
        return {"status": "error", "message": "Unsupported document type for Salla sync."}
    
    # payload = build_salla_product_payload(item)
    
    bin = get_bin(item.item_code, "SS - K")
    actual_qty = bin.actual_qty
    
    print(f"Item: {item.item_code}, Actual Qty in SS - K: {actual_qty}")
    
    if not item.custom_sync_with_salla:
        print("Item not marked for Salla sync. Skipping.")
        return {"status": "skipped", "message": "Item is not marked for Salla sync."}
    
    salla_client = SallaClient()
    # response = salla_client.create_or_update_product(payload)
    
    salla_product = salla_client.get_product_by_sku(item.item_code)
    salla_product = salla_product.json()
    
    sku_changed = False
    
    if salla_product.get("data"):
        
        if item.custom_sync_sku and item.item_code != salla_product["data"]["sku"]:
            # SKU has changed, Update the sku in Salla
            sku_changed = True
            
        
        product_id = salla_product["data"]["id"]
        payload = build_salla_product_payload(item)
        response = salla_client.update_product(product_id, payload)
    else:
        print("Creating new product in Salla...")
        
        payload = build_salla_product_payload(item)
        print("Payload:", payload)
        response = salla_client.create_product(payload)
    
    
    response = response.json()
    print("Salla API Response:", response)
    if response.get("success"):
        return {"status": "success", "message": "Item synced successfully."}
    else:
        return {"status": "error", "message": response.get("error_message", "Unknown error occurred.")}
    



# Get products for testing
@frappe.whitelist(allow_guest=True)
def get_salla_products():
    # salla_client = SallaClient()
    # products = salla_client.get_products()
    # return products
    
    item = frappe.get_doc("Item", "K233")
    print("Item:", item.custom_salla_categories)
    
    for cat in item.custom_salla_categories:
        print("Category:", cat.salla_category)
        cat_doc = frappe.get_doc("Salla Category", cat.salla_category)
        print("Category Doc:", cat_doc.category_name)
    
