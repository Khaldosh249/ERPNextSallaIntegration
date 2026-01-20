"""
Category entity mapper.
Maps between Salla category format and Salla Category DocType.
"""

from typing import Dict, Any, Optional, List
import frappe


class CategoryMapper:
    """
    Bidirectional mapper for Salla Category entities.
    Uses Salla Category DocType (tree structure with nested set model).
    """
    
    @staticmethod
    def salla_to_erpnext(salla_category: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Salla category API data to Salla Category DocType format.
        
        Args:
            salla_category: Category data from Salla API
            
        Returns:
            Dict formatted for Salla Category DocType creation
        """
        # Extract name (handle localized names)
        name = salla_category.get("name", "")
        if isinstance(name, dict):
            name = name.get("en", name.get("ar", ""))
        
        # Determine parent category
        parent_id = salla_category.get("parent_id")
        parent_salla_category = None
        
        if parent_id:
            # Look up parent by Salla ID
            parent_salla_category = frappe.db.get_value(
                "Salla Category",
                {"salla_category_id": str(parent_id)},
                "name"
            )
        
        return {
            "doctype": "Salla Category",
            "category_name": name,
            "salla_category_id": str(salla_category.get("id")),
            "parent_salla_category": parent_salla_category,
            "is_group": 0,
            "is_active": salla_category.get("status", "active") == "active",
            "_salla_parent_id": str(parent_id) if parent_id else None,
        }
    
    @staticmethod
    def erpnext_to_salla(salla_category: Any) -> Dict[str, Any]:
        """
        Map Salla Category DocType to Salla API category format.
        
        Args:
            salla_category: Salla Category document or dict
            
        Returns:
            Dict formatted for Salla API
        """
        # Handle both document and dict
        if hasattr(salla_category, "as_dict"):
            cat_data = salla_category.as_dict()
        else:
            cat_data = salla_category
        
        category = {
            "name": cat_data.get("category_name"),
        }
        
        # Map parent
        parent_category = cat_data.get("parent_salla_category")
        if parent_category:
            parent_salla_id = frappe.db.get_value(
                "Salla Category",
                parent_category,
                "salla_category_id"
            )
            if parent_salla_id:
                category["parent_id"] = int(parent_salla_id)
        
        return category
    
    @staticmethod
    def build_hierarchy_map(categories: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Build a hierarchy map from flat category list.
        
        Args:
            categories: List of category dicts from Salla
            
        Returns:
            Dict mapping parent_id to list of children
        """
        hierarchy = {"root": []}
        
        for cat in categories:
            parent_id = cat.get("parent_id")
            key = str(parent_id) if parent_id else "root"
            
            if key not in hierarchy:
                hierarchy[key] = []
            
            hierarchy[key].append(cat)
        
        return hierarchy
    
    @staticmethod
    def get_category_path(salla_category_id: str) -> List[str]:
        """
        Get the full path from root to a category.
        
        Args:
            salla_category_id: Salla category ID
            
        Returns:
            List of category names from root to target
        """
        path = []
        current_id = salla_category_id
        
        # Traverse up the hierarchy using Salla Category
        while current_id:
            salla_cat = frappe.db.get_value(
                "Salla Category",
                {"salla_category_id": current_id},
                ["category_name", "parent_salla_category"],
                as_dict=True
            )
            
            if not salla_cat:
                break
            
            path.insert(0, salla_cat.category_name)
            
            # Get parent's salla_category_id
            if salla_cat.parent_salla_category:
                current_id = frappe.db.get_value(
                    "Salla Category",
                    salla_cat.parent_salla_category,
                    "salla_category_id"
                )
            else:
                current_id = None
        
        return path
    
    @staticmethod
    def find_or_create_salla_category(
        category_name: str,
        salla_category_id: str = None,
        parent_salla_category: str = None
    ) -> str:
        """
        Find or create a Salla Category.
        
        Args:
            category_name: Category name
            salla_category_id: Salla category ID (optional)
            parent_salla_category: Parent Salla Category name (optional)
            
        Returns:
            Salla Category name
        """
        # Try to find by salla_category_id first
        if salla_category_id:
            existing = frappe.db.get_value(
                "Salla Category",
                {"salla_category_id": salla_category_id},
                "name"
            )
            if existing:
                return existing
        
        # Try to find by name
        existing = frappe.db.get_value(
            "Salla Category",
            {"category_name": category_name, "parent_salla_category": parent_salla_category},
            "name"
        )
        if existing:
            return existing
        
        # Create new Salla Category
        salla_category = frappe.get_doc({
            "doctype": "Salla Category",
            "category_name": category_name,
            "salla_category_id": salla_category_id,
            "parent_salla_category": parent_salla_category,
            "is_group": 0,
            "is_active": 1
        })
        salla_category.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return salla_category.name
    
    @staticmethod
    def get_category_by_salla_id(salla_category_id: str) -> Optional[str]:
        """
        Get Salla Category name by Salla category ID.
        
        Args:
            salla_category_id: Salla category ID
            
        Returns:
            Salla Category name or None
        """
        return frappe.db.get_value(
            "Salla Category",
            {"salla_category_id": salla_category_id},
            "name"
        )
    
    @staticmethod
    def get_all_children(salla_category_name: str) -> List[str]:
        """
        Get all child categories using nested set model.
        
        Args:
            salla_category_name: Parent Salla Category name
            
        Returns:
            List of child category names
        """
        lft, rgt = frappe.db.get_value(
            "Salla Category",
            salla_category_name,
            ["lft", "rgt"]
        ) or (0, 0)
        
        if not lft or not rgt:
            return []
        
        children = frappe.db.get_all(
            "Salla Category",
            filters={"lft": [">", lft], "rgt": ["<", rgt]},
            pluck="name"
        )
        
        return children
    
    @staticmethod
    def get_ancestors(salla_category_name: str) -> List[str]:
        """
        Get all ancestor categories using nested set model.
        
        Args:
            salla_category_name: Salla Category name
            
        Returns:
            List of ancestor category names (from root to parent)
        """
        lft, rgt = frappe.db.get_value(
            "Salla Category",
            salla_category_name,
            ["lft", "rgt"]
        ) or (0, 0)
        
        if not lft or not rgt:
            return []
        
        ancestors = frappe.db.get_all(
            "Salla Category",
            filters={"lft": ["<", lft], "rgt": [">", rgt]},
            order_by="lft asc",
            pluck="name"
        )
        
        return ancestors
