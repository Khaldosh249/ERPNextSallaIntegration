"""
Category synchronization jobs.
Background jobs for category sync operations.
Uses Salla Category DocType exclusively.
"""

import frappe
from typing import Dict, Any, Optional

from salla_integration.jobs.base import job_handler
from salla_integration.synchronization.categories import CategorySyncManager


@job_handler(job_type="Category Sync", queue="default")
def sync_category_to_salla_job(salla_category_name: str) -> Dict[str, Any]:
    """
    Sync a single Salla Category to Salla.
    
    Args:
        salla_category_name: The Salla Category document name
        
    Returns:
        Result dict
    """
    sync_manager = CategorySyncManager()
    salla_category = frappe.get_doc("Salla Category", salla_category_name)
    return sync_manager.sync_to_salla(salla_category)


@job_handler(job_type="Category Bulk Sync", queue="long", timeout=3600)
def sync_all_categories_job() -> Dict[str, Any]:
    """
    Sync all Salla Categories to Salla.
    
    Returns:
        Result dict with counts
    """
    sync_manager = CategorySyncManager()
    
    # Get all Salla Categories marked for sync, ordered by hierarchy (parents first)
    categories = frappe.get_all(
        "Salla Category",
        filters={"sync_to_salla": 1},
        fields=["name"],
        order_by="lft asc"
    )
    
    success = 0
    failed = 0
    
    for cat in categories:
        try:
            salla_category = frappe.get_doc("Salla Category", cat.name)
            result = sync_manager.sync_to_salla(salla_category)
            
            if result.get("status") == "success":
                success += 1
            else:
                failed += 1
                
        except Exception as e:
            failed += 1
            frappe.log_error(f"Error syncing category {cat.name}: {e}")
    
    return {
        "status": "success",
        "success": success,
        "failed": failed,
        "total": len(categories)
    }


@job_handler(job_type="Category Import", queue="long", timeout=3600)
def import_categories_from_salla_job() -> Dict[str, Any]:
    """
    Import all categories from Salla.
    
    Returns:
        Result dict
    """
    sync_manager = CategorySyncManager()
    
    response = sync_manager.client.get_categories()
    
    if not response.get("success"):
        return {"status": "error", "message": response.get("message")}
    
    categories = response.get("data", [])
    imported = 0
    failed = 0
    
    # Process categories in hierarchy order (parents first)
    sorted_categories = _sort_by_hierarchy(categories)
    
    for category_data in sorted_categories:
        result = sync_manager.sync_from_salla(category_data)
        
        if result.get("status") == "success":
            imported += 1
        else:
            failed += 1
    
    return {
        "status": "success",
        "imported": imported,
        "failed": failed,
        "total": len(categories)
    }


def _sort_by_hierarchy(categories: list) -> list:
    """
    Sort categories so parents come before children.
    
    Args:
        categories: List of category data
        
    Returns:
        Sorted list
    """
    # Build a map of category IDs to their data
    category_map = {cat.get("id"): cat for cat in categories}
    
    # Separate root categories and child categories
    roots = []
    children = []
    
    for cat in categories:
        parent_id = cat.get("parent_id")
        if not parent_id or parent_id not in category_map:
            roots.append(cat)
        else:
            children.append(cat)
    
    # Simple approach: roots first, then children
    # For deeper hierarchies, would need recursive sorting
    return roots + children



# Convenience functions for enqueuing jobs

def enqueue_category_sync(salla_category_name: str):
    """Enqueue a single category sync job."""
    frappe.enqueue(
        "salla_integration.jobs.category_jobs.sync_category_to_salla_job",
        salla_category_name=salla_category_name,
        queue="default",
        job_name=f"salla_category_sync_{salla_category_name}"
    )


def enqueue_bulk_category_sync():
    """Enqueue a bulk category sync job."""
    frappe.enqueue(
        "salla_integration.jobs.category_jobs.sync_all_categories_job",
        queue="long",
        timeout=3600,
        job_name="salla_bulk_category_sync"
    )


def enqueue_category_import():
    """Enqueue a category import job."""
    frappe.enqueue(
        "salla_integration.jobs.category_jobs.import_categories_from_salla_job",
        queue="long",
        timeout=3600,
        job_name="salla_category_import"
    )
