"""
Category payload builder for Salla API.
"""

import frappe
from typing import Dict, Any, Optional

from salla_integration.synchronization.base.payload_builder import BasePayloadBuilder


class CategoryPayloadBuilder(BasePayloadBuilder):
    """
    Builds API payloads for category synchronization with Salla.
    """
    
    def build(self) -> Dict[str, Any]:
        """
        Build the complete category payload.
        
        Returns:
            Category payload dict for Salla API
        """
        category = self.doc
        
        # Category name is required
        self.payload["name"] = category.category_name
        
        # Add parent category if exists
        self.add_parent()
        
        # Add sort order if specified
        if hasattr(category, "sort_order") and category.sort_order:
            self.payload["sort_order"] = category.sort_order
        
        return self.payload
    
    def add_parent(self) -> "CategoryPayloadBuilder":
        """Add parent category to payload."""
        category = self.doc
        
        if hasattr(category, "parent_salla_category") and category.parent_salla_category:
            parent_salla_id = frappe.db.get_value(
                "Salla Category",
                category.parent_salla_category,
                "salla_category_id"
            )
            if parent_salla_id:
                self.payload["parent_id"] = int(parent_salla_id)
        
        return self



class CategoryPayloadBuilderEn(BasePayloadBuilder):
    """
    Builds API payloads for category in English synchronization with Salla.
    """
    
    def build(self) -> Dict[str, Any]:
        """
        Build the complete category payload.
        
        Returns:
            Category payload dict for Salla API
        """
        category = self.doc
        
        # Category name is required
        self.payload["name"] = category.category_name_en
        
        return self.payload
    


def build_salla_category_payload(category) -> Dict[str, Any]:
    """
    Convenience function to build category payload.
    
    Args:
        category: The Salla Category document
        
    Returns:
        Category payload dict
    """
    builder = CategoryPayloadBuilder(category)
    builder_en = CategoryPayloadBuilderEn(category)
    return {
        "ar": builder.build(),
        "en": builder_en.build()
    }
