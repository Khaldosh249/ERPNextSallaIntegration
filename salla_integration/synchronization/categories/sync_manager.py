"""
Category synchronization manager.
Handles syncing categories between ERPNext and Salla.
"""

import frappe
from typing import Dict, Any, Optional, List

from salla_integration.synchronization.base.sync_manager import BaseSyncManager
from salla_integration.synchronization.categories.payload_builder import CategoryPayloadBuilder, CategoryPayloadBuilderEn, build_salla_category_payload


class CategorySyncManager(BaseSyncManager):
    """
    Manages category synchronization between ERPNext and Salla.
    Supports bidirectional sync.
    """
    
    entity_type = "Category"
    
    def sync_to_salla(self, category) -> Dict[str, Any]:
        """
        Sync a Salla Category to Salla.
        
        Args:
            category: The Salla Category document or name
            
        Returns:
            Result dict with status and details
        """
        # Get category document if string passed
        if isinstance(category, str):
            category = frappe.get_doc("Salla Category", category)
        
        if getattr(category.flags, "sync_in_progress", False):
            print("Sync already in progress for category:", category.name)
            return {"status": "skipped", "message": "Sync already in progress"}
        category.flags.sync_in_progress = True
        
        # Build payload
        payload = self.build_payload(category)
        print(payload)
        try:
            if category.salla_category_id:
                print("Updating existing category in Salla")
                # Update existing category
                response = self.client.update_category(category.salla_category_id, payload.get("ar", {}), lang="ar")
                response_en = self.client.update_category(category.salla_category_id, payload.get("en", {}), lang="en")
                operation = "Update"
            else:
                print("Creating new category in Salla")
                # Create new category
                response = self.client.create_category(payload.get("ar", {}))
                operation = "Create"
                
                if response.get("success") and response.get("data"):
                    salla_category_id = response["data"]["id"]
                    response_en = self.client.update_category(salla_category_id, payload.get("en", {}), lang="en")
                    category.salla_category_id = salla_category_id
                    
                    frappe.db.set_value(
                        "Salla Category",
                        category.name,
                        "salla_category_id",
                        salla_category_id,
                        update_modified=False
                    )
                    
                    frappe.db.commit()
            
            if response.get("success"):
                self.handle_sync_success(
                    operation=operation,
                    reference_doctype="Salla Category",
                    reference_name=category.name,
                    salla_id=category.salla_category_id
                )
                return {"status": "success", "salla_category_id": category.salla_category_id}
            else:
                error_msg = response.get("message", "Unknown error")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            self.handle_sync_error(
                operation="Sync to Salla",
                reference_doctype="Salla Category",
                reference_name=category.name,
                error=e,
                salla_id=category.salla_category_id
            )
            return {"status": "error", "message": str(e)}
    
    def sync_from_salla(self, category_data: Dict = None, **kwargs) -> Dict[str, Any]:
        """
        Sync a category from Salla to ERPNext.
        
        Args:
            category_data: Category data from Salla
            
        Returns:
            Result dict with status and details
        """
        # Handle kwargs for enqueue compatibility
        if category_data is None:
            category_data = kwargs.get("category_data", {})
        
        salla_category_id = category_data.get("id")
        
        if not salla_category_id:
            return {"status": "error", "message": "No category ID in data"}
        
        # Check if category exists
        existing = frappe.db.get_value(
            "Salla Category",
            {"salla_category_id": salla_category_id},
            "name"
        )
        
        try:
            if existing:
                salla_category_data = {
                    "category_name": category_data.get("name"),
                    "category_name_en": category_data.get("name_en"),
                }
                parent_id = category_data.get("parent_id")
                if parent_id:
                    parent_name = frappe.db.get_value(
                        "Salla Category",
                        {"salla_category_id": parent_id},
                        "name"
                    )
                    if parent_name:
                        salla_category_data["parent_salla_category"] = parent_name
                operation = "Update"
                frappe.db.set_value(
                    "Salla Category",
                    existing,
                    salla_category_data
                )
                frappe.db.commit()
                doc = frappe.get_doc("Salla Category", existing)
            else:
                # Create new category
                salla_category_data = {
                    "doctype": "Salla Category",
                    "category_name": category_data.get("name"),
                    "salla_category_id": salla_category_id,
                    "category_name_en": category_data.get("name_en"),
                }
                parent_id = category_data.get("parent_id")
                if parent_id:
                    parent_name = frappe.db.get_value(
                        "Salla Category",
                        {"salla_category_id": parent_id},
                        "name"
                    )
                    if parent_name:
                        salla_category_data["parent_salla_category"] = parent_name
                doc = frappe.get_doc(salla_category_data)
                doc.insert(ignore_permissions=True)
                operation = "Create"
            
            frappe.db.commit()
            
            self.handle_sync_success(
                operation=operation,
                reference_doctype="Salla Category",
                reference_name=doc.name,
                salla_id=salla_category_id
            )
            
            return {"status": "success", "category_name": doc.name}
            
        except Exception as e:
            self.handle_sync_error(
                operation="Sync from Salla",
                reference_doctype="Salla Category",
                reference_name=existing or "New",
                error=e,
                salla_id=salla_category_id
            )
            print(str(e))
            
            return {"status": "error", "message": str(e)}
    
    def build_payload(self, category) -> Dict[str, Any]:
        """Build the Salla API payload for a category in ar and en."""
        
        builder = build_salla_category_payload(category)
        
        return builder
    
    def import_all_categories(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """
        Import all categories from Salla.
        
        Returns:
            Result dict with counts
        """
        
        # Use pagination to fetch all categories in ar and en
        
        try:
            
            has_more = True
            total_imported = 0
            total_failed = 0
            page = page
            per_page = per_page
            
            while has_more:
                
                params = {"page": page, "per_page": per_page}
                
                
                response_in_ar = self.client.get_categories(params=params, lang="ar")
                print(response_in_ar)
                response_in_en = self.client.get_categories(params=params, lang="en")
                print(response_in_en)
                if not response_in_ar.get("success") or not response_in_en.get("success"):
                    return {"status": "error", "message": "Failed to fetch categories from Salla"}
                
                categories_ar = response_in_ar.get("data", [])
                categories_en = response_in_en.get("data", [])
                
                # Merge categories by ID
                categories_dict = {}
                for cat in categories_ar:
                    categories_dict[cat["id"]] = {"ar": cat}
                for cat in categories_en:
                    if cat["id"] in categories_dict:
                        categories_dict[cat["id"]]["en"] = cat
                    else:
                        categories_dict[cat["id"]] = {"en": cat}
                    
                
                categories = list(categories_dict.values())
                
                
                for category_pair in categories:
                    # category_data = category_pair.get("ar") or category_pair.get("en")
                    
                    category_data = {
                        "id": category_pair.get("ar", {}).get("id") or category_pair.get("en", {}).get("id"),
                        "name": category_pair.get("ar", {}).get("name"),
                        "parent_id": category_pair.get("ar", {}).get("parent_id"),
                        "name_en": category_pair.get("en", {}).get("name")
                    }
                    print("Importing category:", category_data)
                    result = self.sync_from_salla(category_data=category_data)
                    
                    
                    if category_pair.get("ar").get("sub_categories", []):
                        
                        print("Has subcategories in AR:", category_pair.get("ar").get("sub_categories"))
                        
                        for sub_cat in category_pair.get("ar").get("sub_categories", []):
                            
                            self.sync_from_salla_by_category_id(sub_cat.get("id"))
                            
                        
                    
                    
                    if result.get("status") == "success":
                        total_imported += 1
                    else:
                        total_failed += 1
                    
                
                # Check if more pages
                pagination = response_in_ar.get("pagination", {})
                per_page = pagination.get("perPage", per_page)
                current_page = pagination.get("currentPage", 1)
                total_pages = pagination.get("totalPages", 1)
                
                if current_page < total_pages:
                    print("Has more pages")
                    page += 1
                    has_more = True
                else:
                    print("No more pages")
                    has_more = False
                print(f"Imported page {current_page} of {total_pages}")
            
            return {
                "status": "success",
                "imported": total_imported,
                "failed": total_failed,
                "total": total_imported + total_failed
            }
        
        except Exception as e:
            print(str(e))
            # print traceback
            
            import traceback
            traceback.print_exc()
            
            return {"status": "error", "message": str(e)}
        
        
    
    
    def sync_from_salla_by_category_id(self, salla_category_id: str) -> Dict[str, Any]:
        """
        Sync a category from Salla by its Salla category ID in ar and en.
        
        Args:
            salla_category_id: The Salla category ID
        """
        
        try:
            response_in_ar = self.client.get_category(salla_category_id, lang="ar")
            response_in_en = self.client.get_category(salla_category_id, lang="en")
            
            if not response_in_ar.get("success") or not response_in_en.get("success"):
                return {"status": "error", "message": "Failed to fetch category from Salla"}
            
            category_data = {
                "id": salla_category_id,
                "name": response_in_ar.get("data", {}).get("name"),
                "parent_id": response_in_ar.get("data", {}).get("parent_id"),
                "name_en": response_in_en.get("data", {}).get("name")
            }
            
            return self.sync_from_salla(category_data=category_data)
            
        except Exception as e:
            print(str(e))
            return {"status": "error", "message": str(e)}
        

# Convenience functions

@frappe.whitelist()
def sync_category_to_salla(category):
    """
    Sync a single category to Salla.
    Whitelisted method for use from frontend.
    
    Args:
        category: Category name or JSON string
    """
    
    sync_manager = CategorySyncManager()
    
    return sync_manager.sync_to_salla(category)



@frappe.whitelist()
def import_categories_from_salla():
    """Import all categories from Salla."""
    sync_manager = CategorySyncManager()
    
    
    return sync_manager.import_all_categories()


