"""
Product synchronization manager.
Handles syncing products between ERPNext Items and Salla Products.
"""

import frappe
from typing import Dict, Any, Optional, List

from salla_integration.synchronization.base.sync_manager import BaseSyncManager
from salla_integration.synchronization.products.image_sync import add_skipped_images, sync_product_images
from salla_integration.synchronization.products.payload_builder import ProductPayloadBuilder, ProductPayloadBuilderEn
from salla_integration.core.client.exceptions import SallaNotFoundError
from salla_integration.models.mappers.product_mapper import ProductMapper
from salla_integration.synchronization.products.stock_sync import sync_stock_to_salla

class ProductSyncManager(BaseSyncManager):
    """
    Manages product synchronization between ERPNext and Salla.
    """
    
    entity_type = "Product"
    
    def sync_to_salla(self, item) -> Dict[str, Any]:
        """
        Sync an ERPNext Item to Salla.
        sync status are:
        - Synced
        - Failed to Sync
        - Not Synced
        for each field separately:
        - custom_name_sync_status
        - custom_description_sync_status
        - custom_price_sync_status
        - custom_sku_sync_status
        - custom_categories_sync_status
        - custom_images_sync_status
        - custom_stock_sync_status
        
        Args:
            item: The Item document or item_code string
            
        Returns:
            Result dict with status and details
        """
        # Get item document if string passed
        if isinstance(item, str):
            item = frappe.get_doc("Item", item)
        
        # Validate
        if not self.should_sync(item):
            return {"status": "skipped", "message": "Item is not marked for Salla sync"}
        
        validation = self.validate_before_sync(item)
        if not validation["valid"]:
            return {"status": "error", "errors": validation["errors"]}
        
        check_any_field_requires_sync = self.any_field_requires_sync(item)
        if not check_any_field_requires_sync:
            print("No fields marked for Salla sync for Item:", item.item_code)
            return {"status": "skipped", "message": "No fields marked for Salla sync"}
        
        # Build payload
        payload = self.build_payload(item)
        """
        Payload sync:
            - Name
            - Description
            - Price
            - Categories
            
        Custom Funcs Sync:
            - Images
            - Stock
        """
        
        # Get existing Salla Product
        salla_product_id = self._get_salla_product_id(item.item_code)
        
        print("Payload: ",payload)
        
        try:
            if salla_product_id:
                print("Existing Salla Product ID found, updating product")
                # ? Mark fields as Not Synced before starting
                self.mark_sync_status_as_not_synced_before_start(item.item_code, salla_product_id)
                # ? Update existing product in ar and en
                response = self.client.update_product(salla_product_id, payload.get("ar", {}), lang="ar")
                response = self.client.update_product(salla_product_id, payload.get("en", {}), lang="en")
                operation = "Update"
                # ? Update images
                # sync_product_images(item.item_code, salla_product_id)
                self._sync_product_images(item, salla_product_id)
                # ? Update stock
                # sync_stock_to_salla(item.item_code)
                self._sync_product_stock(item, salla_product_id)
            else:
                # ? Check if product exists in Salla by SKU
                try:
                    print("Checking if product exists in Salla by SKU")
                    existing = self.client.get_product_by_sku(item.item_code)
                    # ? Product exists in Salla, link it
                    print("Product with SKU exists in Salla, linking it")
                    salla_product_id = existing["data"]["id"]
                    
                    # ? Create Salla Product record
                    self._create_salla_product_record(item.item_code, salla_product_id)
                    # ? Mark fields as Not Synced before starting
                    self.mark_sync_status_as_not_synced_before_start(item.item_code, salla_product_id)
                    # ? Update product in ar and en
                    response = self.client.update_product(salla_product_id, payload.get("ar", {}), lang="ar")
                    response = self.client.update_product(salla_product_id, payload.get("en", {}), lang="en")
                    operation = "Update"
                    # ? Update images
                    self._sync_product_images(item, salla_product_id)
                    # ? Update stock
                    self._sync_product_stock(item, salla_product_id)
                
                # ? If not found, create new product
                except SallaNotFoundError:
                    # ? Create new product in Salla
                    print("Creating new product in Salla2")
                    # ? Create in Arabic first
                    response = self.client.create_product(payload.get("ar", {}))
                    operation = "Create"
                    print("Create Product Response for Arabic:", response)
                    if response.get("success") and response.get("data"):
                        print("Arabic product created, now creating English version")
                        salla_product_id = response["data"]["id"]
                        # ? Create Salla Product record
                        self._create_salla_product_record(item.item_code, salla_product_id)
                        print("Created Salla Product record for Item:", item.item_code)
                        # ? Mark fields as Not Synced before starting
                        self.mark_sync_status_as_not_synced_before_start(item.item_code, salla_product_id)
                        # ? Create in English
                        response = self.client.update_product(salla_product_id, payload.get("en", {}), lang="en")
                        # ? Upload images
                        self._sync_product_images(item, salla_product_id)
                        # ? Update stock
                        self._sync_product_stock(item, salla_product_id)
            
            if response.get("success"):
                print("Item synced to Salla successfully:", item.item_code, "Marking statuses...")
                self.mark_sync_status_after_finish(item.item_code, salla_product_id, success=True)
                self.handle_sync_success(
                    operation=operation,
                    reference_doctype="Item",
                    reference_name=item.item_code,
                    salla_id=salla_product_id
                )
                return {"status": "success", "salla_product_id": salla_product_id}
            else:
                print("Failed to sync Item to Salla:", item.item_code)
                self.mark_sync_status_after_finish(item.item_code, salla_product_id, success=False)
                error_msg = response.get("message", "Unknown error")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            self.mark_sync_status_after_finish(item.item_code, salla_product_id, success=False)
            self.handle_sync_error(
                operation="Sync to Salla",
                reference_doctype="Item",
                reference_name=item.item_code,
                error=e,
                salla_id=salla_product_id
            )
            print("Exception during sync to Salla for Item:", item.item_code, "Error:", str(e))
            # Print traceback for debugging
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    
    def mark_sync_status_as_not_synced_before_start(self, item_code: str, salla_product_id: str):
        
        item = frappe.get_doc("Item", item_code)
        salla_product = frappe.get_doc("Salla Product", {"item_code": item_code})
        
        # Mark all sync status fields as Not Synced if field requires sync
        if getattr(item, "custom_sync_with_salla", False):
            salla_product.sync_status = "Pending"
            salla_product.item_name_sync_status = "Not Synced"
            salla_product.description_sync_status = "Not Synced"
            salla_product.price_sync_status = "Not Synced"
            salla_product.sku_sync_status = "Not Synced"
            salla_product.categories_sync_status = "Not Synced"
            salla_product.save(ignore_permissions=True)
            
            
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_name_sync_status": "Not Synced",
                    "custom_description_sync_status": "Not Synced",
                    "custom_price_sync_status": "Not Synced",
                    "custom_sku_sync_status": "Not Synced",
                    "custom_categories_sync_status": "Not Synced",
                }
            )
            
            frappe.db.commit()
            
            return True
        
        if item.custom_sync_name:
            salla_product.item_name_sync_status = "Not Synced"
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_name_sync_status": "Not Synced"
                }
            )
        
        if item.custom_sync_description:
            salla_product.description_sync_status = "Not Synced"
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_description_sync_status": "Not Synced"
                }
            )
        
        if item.custom_sync_price:
            salla_product.price_sync_status = "Not Synced"
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_price_sync_status": "Not Synced"
                }
            )
        
        if item.custom_sync_sku:
            salla_product.sku_sync_status = "Not Synced"
            item.custom_sku_sync_status = "Not Synced"
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_sku_sync_status": "Not Synced"
                }
            )
        
        if item.custom_sync_categories:
            salla_product.categories_sync_status = "Not Synced"
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_categories_sync_status": "Not Synced"
                }
            )
        
        
        salla_product.save(ignore_permissions=True)
        frappe.db.commit()
        return True
    
    def mark_sync_status_after_finish(self, item_code: str, salla_product_id: str, success: bool):
        item = frappe.get_doc("Item", item_code)
        salla_product = frappe.get_doc("Salla Product", {"item_code": item_code})
        
        status = "Synced" if success else "Failed to Sync"
        
        if item.custom_sync_name:
            salla_product.item_name_sync_status = status
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_name_sync_status": status
                }
            )
        
        if item.custom_sync_description:
            salla_product.description_sync_status = status
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_description_sync_status": status
                }
            )
        
        if item.custom_sync_price:
            salla_product.price_sync_status = status
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_price_sync_status": status
                }
            )
        
        # if item.custom_sync_sku: # ! Syncing SKU should be impelemented carefully
        #     salla_product.sku_sync_status = status
        #     # item.custom_sku_sync_status = status
        #     frappe.db.set_value(
        #         "Item",
        #         item_code,
        #         {
        #             "custom_sku_sync_status": status
        #         }
        #     )
        
        if item.custom_sync_categories:
            salla_product.categories_sync_status = status
            frappe.db.set_value(
                "Item",
                item_code,
                {
                    "custom_categories_sync_status": status
                }
            )
        
        
        salla_product.save(ignore_permissions=True)
        # item.save(ignore_permissions=True)
        frappe.db.commit()
        return True
    
    
    def _sync_product_images(self, item, salla_product_id: str) -> Dict[str, Any]:
        """
        Sync product images for an item to Salla.
        
        Args:
            item: The ERPNext item document
            salla_product_id: The Salla product ID
        Returns:
            Result dict with status and details
        """
        print("Starting image sync for item:", item.item_code)
        if not item.custom_sync_images:
            print("Image sync not enabled for item:", item.item_code)
            print("Skipping image sync for item:", item.item_code)
            add_skipped_images(item.item_code, salla_product_id)
            return {"status": "skipped", "message": "Image sync not enabled for this item"}
        
        return sync_product_images(item.item_code, salla_product_id)
    
    
    def _sync_product_stock(sellf, item, salla_product_id: str) -> Dict[str, Any]:
        """
        Sync product stock for an item to Salla.
        
        Args:
            item: The ERPNext item document
            salla_product_id: The Salla product ID
        Returns:
            Result dict with status and details
        """
        print("Starting stock sync for item:", item.item_code)
        
        if not item.custom_sync_stock:
            print("Stock sync not enabled for item:", item.item_code)
            return {"status": "skipped", "message": "Stock sync not enabled for this item"}
        
        return sync_stock_to_salla(item.item_code)
    
    def sync_from_salla(self, product_data_ar: Dict, product_data_en: Dict, **kwargs) -> Dict[str, Any]:
        """
        Sync a product from Salla to ERPNext.
        Creates Item if not exists, or links existing Item by SKU.
        
        Args:
            salla_data: Product data from Salla
            
        Returns:
            Result dict with status and details
        """
        
        # Handle kwargs for enqueue compatibility
        if not product_data_ar:
            product_data_ar = kwargs.get("product_data_ar", {})
        
        if not product_data_en:
            product_data_en = kwargs.get("product_data_en", {})
        
        
        salla_product_id = str(product_data_ar.get("id", ""))
        
        if not salla_product_id:
            return {"status": "error", "message": "No product ID in data"}
        
        # Check if Salla Product record already exists
        existing_salla_product = frappe.db.get_value(
            "Salla Product",
            {"salla_product_id": salla_product_id},
            ["name", "item_code"],
            as_dict=True
        )
        
        if existing_salla_product and existing_salla_product.item_code:
            # Already linked, update if needed
            return {
                "status": "success",
                "operation": "Existing",
                "item_code": existing_salla_product.item_code,
                "salla_product_id": salla_product_id
            }
        
        try:
            # Map Salla product to ERPNext Item format
            
            
            item_data = ProductMapper.salla_to_erpnext(
                product_data_ar,
                product_data_en
            )
            sku = item_data.get("item_code")
            salla_item_categories = item_data.pop("_salla_item_categories", [])
            salla_id = item_data.pop("_salla_id", None)
            salla_quantity = item_data.pop("_salla_quantity", 0)
            
            # Check if Item already exists by SKU
            existing_item = frappe.db.exists("Item", sku)
            
            if existing_item:
                # Link existing item
                operation = "Linked"
                item_code = sku
            else:
                # Create new Item
                item_doc = frappe.get_doc(item_data)
                item_doc.insert(ignore_permissions=True)
                operation = "Created"
                item_code = item_doc.item_code
            
            # Create or update Salla Product record
            if existing_salla_product:
                # Update existing Salla Product
                frappe.db.set_value(
                    "Salla Product",
                    existing_salla_product.name,
                    {
                        "item_code": item_code,
                        "sync_status": "Synced"
                    }
                )
                salla_product_name = existing_salla_product.name
            else:
                # Create new Salla Product
                salla_product_doc = frappe.get_doc({
                    "doctype": "Salla Product",
                    "salla_product_id": salla_product_id,
                    "item_code": item_code,
                    "sync_status": "Synced"
                })
                salla_product_doc.insert(ignore_permissions=True)
                salla_product_name = salla_product_doc.name
            
            # Link categories if any
            if salla_item_categories:
                self._link_product_categories(salla_product_name, salla_item_categories)
            
            frappe.db.commit()
            
            self.handle_sync_success(
                operation=operation,
                reference_doctype="Item",
                reference_name=item_code,
                salla_id=salla_product_id
            )
            
            return {
                "status": "success",
                "operation": operation,
                "item_code": item_code,
                "salla_product_id": salla_product_id
            }
            
        except Exception as e:
            self.handle_sync_error(
                operation="Import from Salla",
                reference_doctype="Salla Product",
                reference_name=salla_product_id,
                error=e,
                salla_id=salla_product_id
            )
            
            # Print traceback for debugging
            import traceback
            traceback.print_exc()
            
            return {"status": "error", "message": str(e)}
    
    def import_all_products(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """
        Import all products from Salla.
        Creates Items if not exist, or links existing Items by SKU.
        
        Args:
            page: Starting page number
            per_page: Products per page (max 50)
            
        Returns:
            Result dict with counts
        """
        try:
            created = 0
            linked = 0
            failed = 0
            total_processed = 0
            
            current_page = page
            has_more = True
            
            while has_more:
                # Fetch products from Salla
                params = {
                    "page": current_page,
                    "per_page": per_page
                }
                
                response_in_arabic = self.client.get_products(params=params)
                response_in_english = self.client.get_products(lang="en", params=params)
                
                if not response_in_arabic.get("success") or not response_in_english.get("success"):
                    return {
                        "status": "error",
                        "message": response_in_arabic.get("message", "Failed to fetch products") + " / " + response_in_english.get("message", "Failed to fetch products"),
                        "created": created,
                        "linked": linked,
                        "failed": failed
                    }
                
                products_ar = response_in_arabic.get("data", [])
                products_en = response_in_english.get("data", [])
                products_dict_en = {str(prod.get("id")): prod for prod in products_en}
                
                for product_data_ar in products_ar:
                    
                    product_id = str(product_data_ar.get("id"))
                    product_data_en = products_dict_en.get(product_id, {})
                    
                    
                    print(f"Syncing Salla product ID: {product_data_ar.get('id')}")
                    result = self.sync_from_salla(
                        product_data_ar,
                        product_data_en
                    )
                    total_processed += 1
                    
                    if result.get("status") == "success":
                        if result.get("operation") == "Created":
                            created += 1
                            print(f"Created Item for Salla product ID: {product_data_ar.get('id')}")
                        elif result.get("operation") in ("Linked", "Existing"):
                            linked += 1
                            print(f"Linked existing Item for Salla product ID: {product_data_ar.get('id')}")
                    else:
                        failed += 1
                        print(f"Failed to import Salla product ID: {product_data_ar.get('id')}. Error: {result.get('message')}")
                
                # products = response.get("data", [])
                
                # if not products:
                #     has_more = False
                #     break
                
                # for product_data in products:
                #     print(f"Syncing Salla product ID: {product_data.get('id')}")
                #     result = self.sync_from_salla(product_data)
                #     total_processed += 1
                    
                #     if result.get("status") == "success":
                #         if result.get("operation") == "Created":
                #             created += 1
                #             print(f"Created Item for Salla product ID: {product_data.get('id')}")
                #         elif result.get("operation") in ("Linked", "Existing"):
                #             linked += 1
                #             print(f"Linked existing Item for Salla product ID: {product_data.get('id')}")
                #     else:
                #         failed += 1
                #         print(f"Failed to import Salla product ID: {product_data.get('id')}. Error: {result.get('message')}")
                
                # Check pagination
                pagination = response_in_arabic.get("pagination", {})
                total_pages = pagination.get("totalPages", 1)
                
                if current_page >= total_pages:
                    has_more = False
                else:
                    current_page += 1
            
            return {
                "status": "success",
                "created": created,
                "linked": linked,
                "failed": failed,
                "total": total_processed
            }
            
        except Exception as e:
            frappe.log_error(f"Error importing products from Salla: {e}")
            return {
                "status": "error",
                "message": str(e),
                "created": created if 'created' in dir() else 0,
                "linked": linked if 'linked' in dir() else 0,
                "failed": failed if 'failed' in dir() else 0
            }
    
    # def link_salla_product_to_item(self, salla_product_data: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     Link a Salla Product to an existing ERPNext Item by SKU.
    #     Creating new Salla Product records only.
    #     Args:
    #         salla_product_data: Salla product data dict
    #     Returns:
    #         Result dict
    #     """
        
    #     try:
            
    #         salla_product_id = str(salla_product_data.get("id", ""))
            
    #         self._create_salla_product_record(
            
            
        
        
    
    def link_salla_products_to_items(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """
        Link Salla Products to existing ERPNext Items by SKU.
        
        Args:
            page: Page number to start from
            per_page: Products per page
            
        Returns:
            Result dict with counts
        """
        
        try:
            
            current_page = page
            has_more = True
            linked = 0
            total_processed = 0
            while has_more:
                # Fetch products from Salla
                params = {
                    "page": current_page,
                    "per_page": per_page
                }
                
                response = self.client.get_products(params=params)
                
                if not response.get("success"):
                    return {
                        "status": "error",
                        "message": response.get("message", "Failed to fetch products"),
                        "linked": linked
                    }
                
                products = response.get("data", [])
                
                if not products:
                    has_more = False
                    break
                
                for product_data in products:
                    total_processed += 1
                    
                    # Get SKU
                    sku = product_data.get("sku")
                    if not sku:
                        continue
                    
                    # Check if Item exists
                    existing_item = frappe.db.exists("Item", sku)
                    if not existing_item:
                        continue
                    
                    # Check if Salla Product record already exists
                    existing_salla_product = frappe.db.get_value(
                        "Salla Product",
                        {"salla_product_id": str(product_data.get("id"))},
                        "name"
                    )
                    
                    # Create Salla Product record
                    if not existing_salla_product:
                        self._create_salla_product_record(
                        item_code=sku,
                        salla_product_id=str(product_data.get("id"))
                        )
                        linked += 1
                    
                    # Update custom_open_public_page_in_salla and custom_open_admin_page_in_salla fields in Item
                    
                    custom_open_public_page_in_salla = product_data.get("urls", {}).get("customer", "")
                    custom_open_admin_page_in_salla = product_data.get("urls", {}).get("admin", "")
                    
                    if custom_open_public_page_in_salla:
                        frappe.db.set_value(
                            "Item",
                            sku,
                            "custom_open_public_page_in_salla",
                            custom_open_public_page_in_salla
                        )
                    
                    if custom_open_admin_page_in_salla:
                        frappe.db.set_value(
                            "Item",
                            sku,
                            "custom_open_admin_page_in_salla",
                            custom_open_admin_page_in_salla
                        )
                    
                    print(f"Linked Salla product ID {product_data.get('id')} to Item {sku}")
                    
                    frappe.db.commit()
                    
                
                # Check pagination
                pagination = response.get("pagination", {})
                total_pages = pagination.get("totalPages", 1)
                print(f"Total pages: {total_pages}, Current page: {current_page}")
                print(f"Total products in page: {len(products)}")
                if current_page >= total_pages:
                    has_more = False
                else:
                    current_page += 1
            
            return {
                "status": "success",
                "linked": linked,
                "total_processed": total_processed
            }
        except Exception as e:
            frappe.log_error(f"Error linking Salla products to Items: {e}")
            return {
                "status": "error",
                "message": str(e),
                "linked": linked if 'linked' in dir() else 0
            }
    
    
    def import_single_product(self, salla_product_id: str) -> Dict[str, Any]:
        """
        Import a single product from Salla by ID.
        
        Args:
            salla_product_id: Salla product ID
            
        Returns:
            Result dict
        """
        try:
            response = self.client.get_product(salla_product_id)
            
            if not response.get("success"):
                return {
                    "status": "error",
                    "message": response.get("message", "Product not found")
                }
            
            product_data = response.get("data", {})
            return self.sync_from_salla(product_data)
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _link_product_categories(self, salla_product_name: str, categories: List[Dict]):
        """
        Link Salla Item Categories to a Salla Product.
        
        Args:
            salla_product_name: Salla Product document name
            categories: List of category dicts with salla_category and is_primary
        """
        salla_product = frappe.get_doc("Salla Product", salla_product_name)
        
        # Clear existing categories
        if hasattr(salla_product, "salla_item_categories"):
            salla_product.salla_item_categories = []
        
        # Add new categories
        for cat in categories:
            if hasattr(salla_product, "salla_item_categories"):
                salla_product.append("salla_item_categories", {
                    "salla_category": cat.get("salla_category"),
                    "is_primary": cat.get("is_primary", 0)
                })
        
        salla_product.save(ignore_permissions=True)
    
    def build_payload(self, item) -> Dict[str, Any]:
        """Build the Salla API payload for an item."""
        
        builder = ProductPayloadBuilder(item)
        builder.build()
        
        builder_en = ProductPayloadBuilderEn(item)
        builder_en.build()
        
        return {
            "ar": builder.payload,
            "en": builder_en.payload
        }
    
    def should_sync(self, item) -> bool:
        """Check if an item should be synced to Salla."""
        return bool(getattr(item, "custom_sync_with_salla", False))
    
    def should_sync_sku(self, item) -> bool:
        """Check if the SKU field should be synced."""
        return bool(getattr(item, "custom_sync_sku", False))
    
    def any_field_requires_sync(self, item) -> bool:
        """Check if any field of the item requires syncing."""
        return any([
            getattr(item, "custom_sync_name", False),
            getattr(item, "custom_sync_description", False),
            getattr(item, "custom_sync_price", False),
            getattr(item, "custom_sync_sku", False),
            getattr(item, "custom_sync_categories", False),
            getattr(item, "custom_sync_images", False),
            getattr(item, "custom_sync_stock", False)
        ])
    
    def validate_before_sync(self, item) -> Dict[str, Any]:
        """Validate an item before syncing."""
        errors = []
        
        if not item.item_name:
            errors.append("Item name is required")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def _get_salla_product_id(self, item_code: str) -> Optional[str]:
        """Get the Salla product ID for an item."""
        return frappe.db.get_value(
            "Salla Product",
            {"item_code": item_code},
            "salla_product_id"
        )
    
    def _create_salla_product_record(self, item_code: str, salla_product_id: str):
        """Create a Salla Product record."""
        doc = frappe.get_doc({
            "doctype": "Salla Product",
            "item_code": item_code,
            "salla_product_id": salla_product_id,
            "sync_status": "Pending",
            "item_name_sync_status": "Not Synced",
            "description_sync_status": "Not Synced",
            "price_sync_status": "Not Synced",
            "sku_sync_status": "Not Synced",
            "categories_sync_status": "Not Synced",
            "image_sync_status": "Not Synced",
            "stock_sync_status": "Not Synced"
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    
    def _update_salla_product_record(self, item_code: str, salla_product_id: str):
        """Update a Salla Product record with Salla ID."""
        salla_product_name = frappe.db.get_value(
            "Salla Product",
            {"item_code": item_code},
            "name"
        )
        
        if salla_product_name:
            frappe.db.set_value(
                "Salla Product",
                salla_product_name,
                {
                    "salla_product_id": salla_product_id,
                    "sync_status": "Synced"
                }
            )
            frappe.db.commit()
    
    
    def handle_item_rename(self, doc, method, old_name, new_name):
        """Handle renaming of an Item.
        Update the Salla Product record to reflect the new item code.
        Update sku in Salla if synced.
        """
        
        salla_product = frappe.db.get_value(
            "Salla Product",
            {"item_code": new_name},
            ["name", "salla_product_id"],
            as_dict=True
        )
        
        
        
        if salla_product:
            # Update item_code in Salla Product record
            frappe.db.set_value(
                "Salla Product",
                salla_product.name,
                "item_code",
                new_name
            )
            frappe.db.commit()
            
            # Update SKU in Salla if product is synced
            if salla_product.salla_product_id:
                sync_manager = ProductSyncManager()
                item = frappe.get_doc("Item", new_name)
                if sync_manager.should_sync(item) and sync_manager.should_sync_sku(item):
                    payload = {
                        "sku": new_name
                    }
                    print(f"Updating SKU in Salla for Item {new_name}")
                    try:
                        response = sync_manager.client.update_product(
                            salla_product.salla_product_id,
                            payload
                        )
                        print(f"Salla SKU Update Response for Item {new_name}:", response)
                        if not response.get("success"):
                            frappe.log_error(
                                f"Failed to update SKU in Salla for Item {new_name}: {response.get('message')}",
                                "Salla SKU Update Error"
                            )
                    except Exception as e:
                        frappe.log_error(
                            f"Exception while updating SKU in Salla for Item {new_name}: {str(e)}",
                            "Salla SKU Update Exception"
                        )
        
        
        
    


# Convenience function for use in hooks
@frappe.whitelist()
def sync_item_to_salla(doc, method=None):
    """
    Sync an item to Salla. Used as a hook handler.
    
    Args:
        doc: The Item or Item Price document
        method: The hook method name
    """
    # Handle both Item and Item Price doctypes
    if doc.doctype == "Item":
        item = doc
    elif doc.doctype == "Item Price":
        item = frappe.get_doc("Item", doc.item_code)
    else:
        return
    
    if not getattr(item, "custom_sync_with_salla", False):
        return
    
    _sync_item_background(item.item_code)
    
    # Use background job for async processing
    # frappe.enqueue(
    #     "salla_integration.synchronization.products.sync_manager._sync_item_background",
    #     item_code=item.item_code,
    #     queue="default",
    #     job_name=f"salla_sync_{item.item_code}"
    # )


@frappe.whitelist()
def sync_item_sku_on_rename(doc, method, old_name, new_name):
    """Sync item SKU to Salla on item rename."""
    sync_manager = ProductSyncManager()
    sync_manager.handle_item_rename(doc, method, old_name, new_name)


@frappe.whitelist()
def link_existing_items_with_salla_products():
    """Link existing Items with Salla Products by SKU."""
    sync_manager = ProductSyncManager()
    result = sync_manager.link_salla_products_to_items(page=1, per_page=5)
    
    if result["status"] == "error":
        frappe.log_error(
            f"Failed to link Salla products to Items: {result.get('message')}",
            "Salla Product Link Error"
        )
    return result




def _sync_item_background(item_code: str):
    """Background job to sync item to Salla."""
    sync_manager = ProductSyncManager()
    result = sync_manager.sync_to_salla(item_code)
    
    if result["status"] == "error":
        frappe.log_error(
            f"Failed to sync item {item_code} to Salla: {result.get('message')}",
            "Salla Product Sync Error"
        )
