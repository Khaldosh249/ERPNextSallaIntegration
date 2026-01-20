"""
Order entity mapper.
Maps between Salla order format and ERPNext Sales Order format.
"""

from typing import Dict, Any, Optional, List
import frappe


class OrderMapper:
    """
    Mapper for Order entities (Salla to ERPNext).
    Orders flow from Salla to ERPNext, not the reverse.
    """
    
    @staticmethod
    def salla_to_erpnext(
        salla_order: Dict[str, Any],
        customer_name: str,
        company: str
    ) -> Dict[str, Any]:
        """
        Map Salla order to ERPNext Sales Order format.
        
        Args:
            salla_order: Order data from Salla API
            customer_name: ERPNext Customer name
            company: ERPNext Company name
            
        Returns:
            Dict formatted for ERPNext Sales Order creation
        """
        items = OrderMapper._map_items(salla_order.get("items", []))
        
        return {
            "doctype": "Sales Order",
            "customer": customer_name,
            "company": company,
            "order_type": "Sales",
            "transaction_date": frappe.utils.today(),
            "delivery_date": frappe.utils.add_days(frappe.utils.today(), 7),
            "items": items,
            "_salla_id": str(salla_order.get("id")),
            "_salla_status": salla_order.get("status", {}).get("name", ""),
            "_salla_total": OrderMapper._get_total(salla_order),
        }
    
    @staticmethod
    def _map_items(salla_items: List[Dict]) -> List[Dict]:
        """
        Map Salla order items to ERPNext Sales Order Item format.
        
        Args:
            salla_items: List of item dicts from Salla order
            
        Returns:
            List of item dicts for Sales Order
        """
        items = []
        
        for salla_item in salla_items:
            item_code = OrderMapper._find_item_code(salla_item)
            
            if not item_code:
                continue
            
            # Get price
            price = salla_item.get("price", {})
            if isinstance(price, dict):
                rate = price.get("amount", 0)
            else:
                rate = price or 0
            
            items.append({
                "item_code": item_code,
                "qty": salla_item.get("quantity", 1),
                "rate": rate,
            })
        
        return items
    
    @staticmethod
    def _find_item_code(salla_item: Dict) -> Optional[str]:
        """
        Find ERPNext Item code for a Salla order item.
        
        Args:
            salla_item: Item data from Salla order
            
        Returns:
            Item code or None
        """
        # Try SKU first
        sku = salla_item.get("sku")
        if sku:
            item_code = frappe.db.get_value("Item", {"item_code": sku}, "item_code")
            if item_code:
                return item_code
        
        # Try Salla Product mapping
        product_id = salla_item.get("product_id")
        if product_id:
            item_code = frappe.db.get_value(
                "Salla Product",
                {"salla_product_id": str(product_id)},
                "item_code"
            )
            if item_code:
                return item_code
        
        return None
    
    @staticmethod
    def _get_total(salla_order: Dict) -> float:
        """
        Extract total amount from Salla order.
        
        Args:
            salla_order: Order data from Salla
            
        Returns:
            Total amount
        """
        amounts = salla_order.get("amounts", {})
        total = amounts.get("total", {})
        
        if isinstance(total, dict):
            return total.get("amount", 0)
        return total or 0
    
    @staticmethod
    def map_shipping_address(
        salla_order: Dict[str, Any],
        customer_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Map Salla order shipping address.
        
        Args:
            salla_order: Order data from Salla
            customer_name: ERPNext Customer name
            
        Returns:
            Address dict or None
        """
        shipping = salla_order.get("shipping", {})
        receiver = shipping.get("receiver", {})
        
        if not receiver:
            return None
        
        return {
            "doctype": "Address",
            "address_title": f"{customer_name} - Order {salla_order.get('id')}",
            "address_type": "Shipping",
            "address_line1": receiver.get("street", ""),
            "address_line2": receiver.get("street_number", ""),
            "city": receiver.get("city", ""),
            "state": receiver.get("region", ""),
            "country": OrderMapper._map_country(receiver.get("country_code", "SA")),
            "pincode": receiver.get("postal_code", ""),
            "phone": receiver.get("phone", ""),
            "links": [{
                "link_doctype": "Customer",
                "link_name": customer_name
            }]
        }
    
    @staticmethod
    def _map_country(country_code: str) -> str:
        """Map country code to name."""
        country_map = {
            "SA": "Saudi Arabia",
            "AE": "United Arab Emirates",
            "KW": "Kuwait",
            "BH": "Bahrain",
            "QA": "Qatar",
            "OM": "Oman",
        }
        return country_map.get(country_code.upper(), country_code)
    
    @staticmethod
    def get_status_mapping() -> Dict[str, str]:
        """
        Get Salla to ERPNext status mapping.
        
        Returns:
            Dict mapping Salla status to ERPNext status
        """
        return {
            "pending": "Draft",
            "pending_payment": "Draft",
            "pending_shipment": "To Deliver and Bill",
            "in_progress": "To Deliver and Bill",
            "in_transit": "To Deliver and Bill",
            "shipped": "To Bill",
            "delivered": "Completed",
            "completed": "Completed",
            "cancelled": "Cancelled",
            "refunded": "Cancelled",
        }
    
    @staticmethod
    def map_status(salla_status: str) -> str:
        """
        Map Salla order status to ERPNext Sales Order status.
        
        Args:
            salla_status: Salla order status
            
        Returns:
            ERPNext status
        """
        mapping = OrderMapper.get_status_mapping()
        return mapping.get(salla_status.lower(), "Draft")
