"""
Product payload builder for Salla API.
"""

import frappe
from typing import Dict, Any, List

from salla_integration.synchronization.base.payload_builder import BasePayloadBuilder


class ProductPayloadBuilder(BasePayloadBuilder):
    """
    Builds API payloads for product synchronization with Salla.
    """
    
    def build(self) -> Dict[str, Any]:
        """
        Build the complete product payload based on sync settings.
        
        Returns:
            Product payload dict for Salla API
        """
        item = self.doc
        
        # Add fields based on sync settings
        if getattr(item, "custom_sync_name", False):
            self.add_name()
        
        if getattr(item, "custom_sync_description", False):
            self.add_description()
        
        if getattr(item, "custom_sync_price", False):
            self.add_price()
        
        # if getattr(item, "custom_sync_sku", False):
        #     self.add_sku()
        
        if getattr(item, "custom_sync_categories", False):
            self.add_categories()
        
        # if getattr(item, "custom_sync_stock", False):
        #     self.add_stock()
        
        return self.payload
    
    def add_name(self) -> "ProductPayloadBuilder":
        """Add product name to payload."""
        self.payload["name"] = self.doc.item_name
        return self
    
    def add_description(self) -> "ProductPayloadBuilder":
        """Add product description to payload."""
        self.payload["description"] = self.doc.description or ""
        return self
    
    def add_price(self) -> "ProductPayloadBuilder":
        """Add product price to payload."""
        price = self._get_item_price()
        if price is not None:
            self.payload["price"] = price
        return self
    
    # def add_sku(self) -> "ProductPayloadBuilder":
    #     """Add product SKU to payload."""
    #     self.payload["sku"] = self.doc.item_code
    #     return self
    
    def add_categories(self) -> "ProductPayloadBuilder":
        """Add product categories to payload."""
        categories = self._get_category_ids()
        if categories:
            self.payload["categories"] = categories
        return self
    
    def _get_item_price(self) -> float:
        """Get the item price from Item Price doctype."""
        price = frappe.db.get_value(
            "Item Price",
            {"item_code": self.doc.item_code, "price_list": "Standard Selling"},
            "price_list_rate"
        )
        return price
    
    def _get_category_ids(self) -> List[int]:
        """Get Salla category IDs for the item."""
        category_ids = []
        
        # Get categories from custom field
        categories = getattr(self.doc, "custom_salla_categories", [])
        
        for cat in categories:
            salla_category = cat.salla_category
            if salla_category:
                salla_category_id = frappe.db.get_value(
                    "Salla Category",
                    salla_category,
                    "salla_category_id"
                )
                if salla_category_id:
                    category_ids.append(int(salla_category_id))
        
        return category_ids


# Build english payload : only include name and description if synced
class ProductPayloadBuilderEn(ProductPayloadBuilder):
    """
    Builds English product payload for Salla API.
    """
    
    def build(self) -> Dict[str, Any]:
        """
        Build the complete English product payload based on sync settings.
        
        Returns:
            Product payload dict for Salla API
        """
        item = self.doc
        
        # Add fields based on sync settings
        if getattr(item, "custom_sync_name", False):
            self.add_name()
        
        if getattr(item, "custom_sync_description", False):
            self.add_description()
        
        return self.payload
    
    def add_name(self) -> "ProductPayloadBuilderEn":
        """Add product name to payload."""
        self.payload["name"] = self.doc.custom_item_name_english
        return self
    
    def add_description(self) -> "ProductPayloadBuilderEn":
        """Add product description to payload."""
        self.payload["description"] = self.doc.custom_description_en or ""
        return self



def build_salla_product_payload(item) -> Dict[str, Any]:
    """
    Convenience function to build product payload.
    
    Args:
        item: The Item document
        
    Returns:
        Product payload dict
    """
    builder = ProductPayloadBuilder(item)
    return builder.build()
