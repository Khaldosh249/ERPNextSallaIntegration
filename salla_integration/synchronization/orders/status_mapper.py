"""
Order status mapping between Salla and ERPNext.
"""

from typing import Optional, Dict


# Salla order statuses to ERPNext Sales Order statuses
SALLA_TO_ERPNEXT_STATUS = {
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
    "on_hold": "On Hold",
}

# ERPNext Sales Order statuses to Salla
ERPNEXT_TO_SALLA_STATUS = {
    "Draft": "pending",
    "To Deliver and Bill": "in_progress",
    "To Bill": "shipped",
    "To Deliver": "in_transit",
    "Completed": "completed",
    "Cancelled": "cancelled",
    "Closed": "completed",
    "On Hold": "on_hold",
}


def map_salla_status_to_erpnext(salla_status: str) -> Optional[str]:
    """
    Map a Salla order status to ERPNext Sales Order status.
    
    Args:
        salla_status: The Salla order status
        
    Returns:
        ERPNext status or None if no mapping exists
    """
    if not salla_status:
        return None
    
    return SALLA_TO_ERPNEXT_STATUS.get(salla_status.lower())


def map_erpnext_status_to_salla(erpnext_status: str) -> Optional[str]:
    """
    Map an ERPNext Sales Order status to Salla order status.
    
    Args:
        erpnext_status: The ERPNext Sales Order status
        
    Returns:
        Salla status or None if no mapping exists
    """
    if not erpnext_status:
        return None
    
    return ERPNEXT_TO_SALLA_STATUS.get(erpnext_status)


def get_all_salla_statuses() -> list:
    """Get all known Salla order statuses."""
    return list(SALLA_TO_ERPNEXT_STATUS.keys())


def get_all_erpnext_statuses() -> list:
    """Get all known ERPNext Sales Order statuses."""
    return list(ERPNEXT_TO_SALLA_STATUS.keys())


def is_terminal_status(salla_status: str) -> bool:
    """
    Check if a Salla status is terminal (order completed or cancelled).
    
    Args:
        salla_status: The Salla order status
        
    Returns:
        True if status is terminal
    """
    terminal_statuses = ["completed", "delivered", "cancelled", "refunded"]
    return salla_status.lower() in terminal_statuses


def can_transition_to(current_status: str, new_status: str) -> bool:
    """
    Check if a status transition is valid.
    
    Args:
        current_status: Current Salla status
        new_status: Proposed new Salla status
        
    Returns:
        True if transition is valid
    """
    # Define valid transitions
    valid_transitions = {
        "pending": ["pending_payment", "pending_shipment", "in_progress", "cancelled"],
        "pending_payment": ["pending_shipment", "in_progress", "cancelled"],
        "pending_shipment": ["in_progress", "in_transit", "shipped", "cancelled"],
        "in_progress": ["in_transit", "shipped", "delivered", "cancelled"],
        "in_transit": ["shipped", "delivered", "cancelled"],
        "shipped": ["delivered", "completed"],
        "delivered": ["completed", "refunded"],
        "completed": ["refunded"],
        "cancelled": [],
        "refunded": [],
        "on_hold": ["pending", "in_progress", "cancelled"],
    }
    
    allowed = valid_transitions.get(current_status.lower(), [])
    return new_status.lower() in allowed
