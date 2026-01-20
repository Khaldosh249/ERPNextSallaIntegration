import frappe
from salla_integration.services.item_payload import build_salla_product_payload
from salla_integration.api.salla_client import SallaClient


@frappe.whitelist()
def create_salla_product_objects():
    """
    Create Salla Product objects for all items marked for Salla sync.
    """
    
    items = frappe.get_all(
        "Item",
        filters={"custom_sync_with_salla": 1},
        fields=["name", "item_code"]
    )
    
    salla_client = SallaClient()
    
    # Create Salla Product Docs and link to Items
    for item_entry in items:
        
        # Check if Salla Product already exists
        existing_salla_product = frappe.get_all(
            "Salla Product",
            filters={"item_code": item_entry.item_code},
            fields=["name"]
        )
        
        if existing_salla_product:
            print(f"Salla Product already exists for Item {item_entry.item_code}. Skipping...")
            continue
        
        remote_salla_product = salla_client.get_product_by_sku(item_entry.item_code)
        remote_salla_product = remote_salla_product.json()
        
        new_salla_product = {
            "doctype": "Salla Product",
            "item_code": item_entry.item_code,
            "sync_status": "Pending",
        }
        
        if remote_salla_product.get("success") == True:
            new_salla_product["salla_product_id"] = remote_salla_product["data"]["id"]
        else:
            new_salla_product["sync_status"] = "Not Found in Salla"
        
        
        # Create Salla Product Doc
        salla_product_doc = frappe.get_doc(new_salla_product)
        salla_product_doc.insert()
        print(f"Created Salla Product for Item {item_entry.item_code}.")


@frappe.whitelist()
def import_products_from_salla(page: int = 1, per_page: int = 50):
    """
    Import all products from Salla to ERPNext.
    Creates new Items if not found by SKU, or links existing Items.
    
    This enqueues a background job for the import.
    
    Args:
        page: Starting page number (default: 1)
        per_page: Products per page (default: 50)
    
    Returns:
        dict: Job enqueue confirmation
    """
    from salla_integration.jobs.product_jobs import enqueue_product_import
    
    enqueue_product_import()
    
    return {
        "success": True,
        "message": "Product import job has been enqueued. Check Salla Sync Log for progress."
    }


@frappe.whitelist()
def import_single_product(salla_product_id: str):
    """
    Import a single product from Salla by its ID.
    Creates new Item if not found by SKU, or links existing Item.
    
    Args:
        salla_product_id: The Salla product ID to import
    
    Returns:
        dict: Import result with created/linked item info
    """
    from salla_integration.jobs.product_jobs import enqueue_single_product_import
    
    if not salla_product_id:
        return {
            "success": False,
            "message": "salla_product_id is required"
        }
    
    enqueue_single_product_import(salla_product_id)
    
    return {
        "success": True,
        "message": f"Single product import job for {salla_product_id} has been enqueued."
    }


@frappe.whitelist()
def import_single_product_sync(salla_product_id: str):
    """
    Import a single product from Salla synchronously (not as background job).
    Useful for immediate import during testing or when importing few products.
    
    Args:
        salla_product_id: The Salla product ID to import
    
    Returns:
        dict: Import result with created/linked item info
    """
    from salla_integration.synchronization.products.sync_manager import ProductSyncManager
    
    if not salla_product_id:
        return {
            "success": False,
            "message": "salla_product_id is required"
        }
    
    try:
        sync_manager = ProductSyncManager()
        result = sync_manager.import_single_product(salla_product_id)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        frappe.log_error(f"Error importing product {salla_product_id}: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }
        
    





