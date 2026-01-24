"""
Common helper functions for Salla Integration.
"""

import frappe
from typing import Optional, Any
from erpnext.stock.utils import get_bin

def get_salla_settings():
    """
    Get the Salla Settings singleton document.
    
    Returns:
        Salla Settings document
    """
    return frappe.get_single("Salla Settings")


def get_default_warehouse() -> Optional[str]:
    """
    Get the default warehouse from Salla Settings.
    
    Returns:
        Default warehouse name or None
    """
    settings = get_salla_settings()
    return settings.default_warehouse if hasattr(settings, "default_warehouse") else None

def get_secondary_warehouse() -> Optional[str]:
    """
    Get the secondary warehouse from Salla Settings.
    
    Returns:
        Secondary warehouse name or None
    """
    settings = get_salla_settings()
    return settings.secondary_warehouse if hasattr(settings, "secondary_warehouse") else None

def get_default_company() -> Optional[str]:
    """
    Get the default company from Salla Settings.
    
    Returns:
        Default company name or None
    """
    settings = get_salla_settings()
    return settings.company if hasattr(settings, "company") else None


def is_sync_enabled() -> bool:
    """
    Check if Salla synchronization is enabled.
    
    Returns:
        True if sync is enabled, False otherwise
    """
    settings = get_salla_settings()
    return bool(settings.enabled)


def is_incoming_orders_sync_enabled() -> bool:
    """
    Check if incoming orders synchronization from Salla is enabled.
    
    Returns:
        True if incoming orders sync is enabled, False otherwise
    """
    settings = get_salla_settings()
    return bool(settings.enable_order_sync)


def get_default_price_list() -> Optional[str]:
    """
    Get the default price list from Salla Settings.
    
    Returns:
        Default price list name or None
    """
    settings = get_salla_settings()
    return settings.default_price_list if hasattr(settings, "default_price_list") else None


def get_price_list_for_importing_prices_from_salla() -> Optional[str]:
    """
    Get the price list for importing prices from Salla Settings.
    
    Returns:
        Price list name or None
    """
    settings = get_salla_settings()
    return settings.default_price_list_for_importing_prices_from_salla if hasattr(settings, "default_price_list_for_importing_prices_from_salla") else None


def get_default_currency() -> Optional[str]:
    """
    Get the default currency from Salla Settings.
    
    Returns:
        Default currency code or None
    """
    settings = get_salla_settings()
    return settings.default_currency if hasattr(settings, "default_currency") else None


def get_default_taxes_and_charges() -> Optional[str]:
    """
    Get the default taxes and charges template from Salla Settings.
    
    Returns:
        Default taxes and charges template name or None
    """
    settings = get_salla_settings()
    return settings.default_taxes_and_charges if hasattr(settings, "default_taxes_and_charges") else None


def get_taxes_from_sales_taxes_template(template_name: str) -> list:
    """
    Get the list of taxes from a Sales Taxes and Charges Template.
    
    Args:
        template_name: The name of the Sales Taxes and Charges Template
    Returns:
        List of tax dicts
    """
    tax_template = frappe.get_doc("Sales Taxes and Charges Template", template_name)
    return tax_template.taxes if tax_template else []


def get_default_customer_group() -> Optional[str]:
    """
    Get the default customer group from Salla Settings.
    
    Returns:
        Default customer group name or None
    """
    settings = get_salla_settings()
    return settings.default_customer_group if hasattr(settings, "default_customer_group") else None


def get_default_territory() -> Optional[str]:
    """
    Get the default territory from Salla Settings.
    
    Returns:
        Default territory name or None
    """
    settings = get_salla_settings()
    return settings.default_territory if hasattr(settings, "default_territory") else None


def get_item_stock(item_code: str) -> float:
    """
    Get the current stock quantity for an item.
    
    Args:
        item_code: The item code
    Returns:
        Current stock quantity
    """
    
    
    default_warehouse = get_default_warehouse()
    secondary_warehouse = get_secondary_warehouse()
    
    # Item stock is the sum of stock in default and secondary warehouses
    total_quantity = 0.0
    for wh in [default_warehouse, secondary_warehouse]:
        if wh:
            bin_doc = get_bin(item_code, wh)
            if bin_doc:
                total_quantity += bin_doc.actual_qty
    
    return total_quantity


def get_item_stock_in_warehouse(item_code: str, warehouse: str) -> float:
    """
    Get the current stock quantity for an item in a specific warehouse.
    
    Args:
        item_code: The item code
        warehouse: The warehouse name
        
    Returns:
        Current stock quantity in the specified warehouse
    """
    bin_doc = get_bin(item_code, warehouse)
    return bin_doc.actual_qty if bin_doc else 0


def get_item_price(item_code: str) -> Optional[float]:
    """
    Get the price for an item from the specified price list.
    
    Args:
        item_code: The item code
        price_list: The price list name
        
    Returns:
        Item price or None
    """
    price_list = get_default_price_list()
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": price_list},
        "price_list_rate"
    )
    return price


def get_order_status_after_deivery_note_submission() -> Optional[str]:
    """
    Get the order status to set after Delivery Note submission.
    
    Returns:
        Order status or None
    """
    settings = get_salla_settings()
    return settings.salla_order_status_after_submitting_delivery_note if hasattr(settings, "salla_order_status_after_submitting_delivery_note") else None



def safe_get(data: dict, *keys, default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary.
    
    Args:
        data: The dictionary to search
        *keys: The keys to traverse
        default: Default value if not found
        
    Returns:
        The value or default
    """
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return default
        if result is None:
            return default
    return result


def format_currency(amount: float, currency: str = "SAR") -> str:
    """
    Format an amount as currency.
    
    Args:
        amount: The amount to format
        currency: The currency code
        
    Returns:
        Formatted currency string
    """
    return f"{amount:.2f} {currency}"


def is_item_synced_with_salla(item_code: str) -> bool:
    """
    Check if an item is marked for Salla sync.
    
    Args:
        item_code: The item code
        
    Returns:
        True if item is synced with Salla
    """
    return frappe.db.get_value("Item", item_code, "custom_sync_with_salla") or False


def get_salla_product_by_item(item_code: str) -> Optional[str]:
    """
    Get the Salla Product document name for an item.
    
    Args:
        item_code: The item code
        
    Returns:
        Salla Product document name or None
    """
    return frappe.db.get_value(
        "Salla Product",
        {"item_code": item_code},
        "name"
    )


def get_salla_product_id(item_code: str) -> Optional[str]:
    """
    Get the Salla Product ID for an item.
    
    Args:
        item_code: The item code
        
    Returns:
        Salla Product ID or None
    """
    return frappe.db.get_value(
        "Salla Product",
        {"item_code": item_code},
        "salla_product_id"
    )
