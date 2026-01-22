"""
Image synchronization for Salla products.
"""

import frappe
from typing import List, Optional

from salla_integration.core.client import SallaClient
from salla_integration.core.client.exceptions import SallaNotFoundError


def sync_product_images(item_code: str, salla_product_id: str) -> dict:
    """
    Sync images for a product to Salla.
    
    Args:
        item_code: The ERPNext item code
        salla_product_id: The Salla product ID
        
    Returns:
        Result dict with status and details
    """
    item = frappe.get_doc("Item", item_code)
    salla_product_doc = frappe.db.get_value(
        "Salla Product",
        {"item_code": item_code},
        ["name", "salla_product_id", "images_variance"],
        as_dict=True
    )
    """
    images_variance: json field storing last synced image URLs mapped with ids to allow deletion and addition
    to track changes, deletions, additions.
    """
    
    if not salla_product_doc:
        return {"status": "skipped", "message": "Item not linked to Salla Product"}
    
    
    if not item.custom_sync_images:
        return {"status": "skipped", "message": "Image sync not enabled for this item"}
    
    image_variance = get_image_variance(item, salla_product_doc)
    
    client = SallaClient()
    
    try:
        new_variance = {}
        
        # Handle added images
        for url in image_variance["added"]:
            
            # Get file full path to upload as binary
            file_path = frappe.get_site_path("public", url.lstrip("/"))
            print("Uploading image from path:", file_path)
            response = client.upload_product_image(
                salla_product_id,
                file_path,
            )
            print("Upload response for image", url, ":", response)
            if response.get("success") and response.get("data"):
                image_id = response["data"]["id"]
                new_variance[url] = image_id
            
        # Handle removed images
        for image_id in image_variance["removed"]:
            try:
                client.delete_product_image(
                    image_id
                )
            except SallaNotFoundError:
                # Image already deleted on Salla side
                pass
        # Handle unchanged images
        for url in image_variance["unchanged"]:
            last_synced_images = frappe.parse_json(salla_product_doc.get("images_variance") or "{}")
            image_id = last_synced_images.get(url)
            new_variance[url] = image_id
        
        # Update the Salla Product doc with new variance
        salla_product = frappe.get_doc("Salla Product", salla_product_doc.name)
        salla_product.images_variance = new_variance
        salla_product.image_sync_status = "Synced"
        salla_product.save(ignore_permissions=True)
        # item.custom_images_sync_status = "Synced"
        print("Setting Item image_sync_status to Synced for", item_code)
        frappe.db.set_value(
            "Item",
            item_code,
            {"custom_images_sync_status": "Synced"}
        )
        frappe.db.commit()
        
        
        return {
            "status": "success",
            "added": len(image_variance["added"]),
            "removed": len(image_variance["removed"]),
            "unchanged": len(image_variance["unchanged"])
        }
    except Exception as e:
        
        
        frappe.log_error(
            f"Failed to sync images for {item_code}: {str(e)}",
            "Salla Image Sync Error"
        )
        # print traceback
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
        
    
    




def get_item_image_paths(item) -> List[str]:
    """
    Get list of image file paths for the item.
    
    Args:
        item: The Item document 
    Returns:
        List of image file paths
    """
    image_paths = []
    
    if item.image:
        image_paths.append(item.image)
    
    # Check for additional images in Item attachments
    attachments = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Item", "attached_to_name": item.name},
        fields=["file_url"]
    )
    for att in attachments:
        image_paths.append(att.file_url)
    
    return image_paths


def get_image_variance(item, salla_product_doc) -> dict:
    """
    Determine image changes (added, removed, unchanged) since last sync.
    
    Args:
        item: The Item document
        salla_product_doc: The linked Salla Product document
        
    Returns:
        Dict with lists of 'added', 'removed', 'unchanged' image URLs
    """
    
    current_images = set(get_item_image_paths(item))
    # last_synced_images = salla_product_doc.get("images_variance") or {}
    # Parse the JSON field
    last_synced_images = frappe.parse_json(salla_product_doc.get("images_variance") or "{}")
    
    
    print("Current Images:", current_images)
    print("Last Images:", last_synced_images)
    
    last_images_set = set(last_synced_images.keys())
    
    # For added and unchanged, we use urls
    # For removed, we use ids stored in last synced
    added = list(current_images - last_images_set)
    removed = [last_synced_images[url] for url in (last_images_set - current_images)]
    unchanged = list(current_images & last_images_set)
    
    print("Image Variance - Added:", added)
    print("Image Variance - Removed:", removed)
    print("Image Variance - Unchanged:", unchanged)
    
    return {
        "added": added,
        "removed": removed,
        "unchanged": unchanged
    }



def add_skipped_images(item_code: str, salla_product_id: str):
    """
    Mark images as added without actual sync.
    
    Args:
        item_code: The ERPNext item code
        salla_product_id: The Salla product ID
    """
    
    salla_product_doc = frappe.db.get_value(
        "Salla Product",
        {"item_code": item_code},
        ["name", "salla_product_id"],
        as_dict=True
    )
    
    if not salla_product_doc:
        return
    salla_product = frappe.get_doc("Salla Product", salla_product_doc.name)
    
    item = frappe.get_doc("Item", item_code)
    current_images = get_item_image_paths(item)
    new_variance = {}
    last_synced_images = frappe.parse_json(salla_product.get("images_variance") or "{}")
    
    last_synced_images_set = set(last_synced_images.keys())
    
    # Mark all current images as unchanged if they were previously synced
    for url in current_images:
        if url in last_synced_images_set:
            new_variance[url] = last_synced_images[url]
        else:
            new_variance[url] = None  # No image ID since not synced
    
    salla_product.images_variance = new_variance
    salla_product.image_sync_status = "Synced"
    salla_product.save(ignore_permissions=True)
    print("Setting Item image_sync_status to Synced for", item_code)
    frappe.db.set_value(
        "Item",
        item_code,
        {"custom_images_sync_status": "Synced"}
    )
    frappe.db.commit()
    
    




def enqueue_image_sync(item_code: str, salla_product_id: str):
    """
    Enqueue image sync as a background job.
    
    Args:
        item_code: The ERPNext item code
        salla_product_id: The Salla product ID
    """
    frappe.enqueue(
        "salla_integration.synchronization.products.image_sync.sync_product_images",
        item_code=item_code,
        salla_product_id=salla_product_id,
        queue="default",
        job_name=f"salla_image_sync_{item_code}"
    )
