"""
Customer service layer.
Provides high-level customer operations and business logic.
"""

import frappe
from typing import Dict, Any, Optional, List

from salla_integration.synchronization.customers import CustomerSyncManager
from salla_integration.models.mappers import CustomerMapper
from salla_integration.models.schemas import CustomerSchema
from salla_integration.jobs.customer_jobs import enqueue_customer_import

class CustomerService:
    """
    High-level service for customer operations.
    Customers are synced FROM Salla TO ERPNext.
    """
    
    def __init__(self):
        self.sync_manager = CustomerSyncManager()
    
    def import_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import a single customer from Salla.
        
        Args:
            customer_data: Customer data from Salla
            
        Returns:
            Result dict
        """
        # Validate
        validation = CustomerSchema.validate_salla_customer(customer_data)
        
        if not validation["is_valid"]:
            return {
                "status": "error",
                "message": "Validation failed",
                "errors": validation["errors"]
            }
        
        return self.sync_manager.sync_from_salla(customer_data)
    
    def import_all_customers(self, enqueue: bool = True) -> Dict[str, Any]:
        """
        Import all customers from Salla.
        
        Args:
            enqueue: Whether to enqueue as background job
            
        Returns:
            Result dict
        """
        if enqueue:
            
            enqueue_customer_import()
            return {"status": "enqueued", "message": "Import job enqueued"}
        
        return self.sync_manager.import_all_customers()
    
    def get_customer_by_salla_id(self, salla_customer_id: str) -> Optional[str]:
        """
        Get ERPNext Customer by Salla customer ID.
        
        Args:
            salla_customer_id: Salla customer ID
            
        Returns:
            Customer name or None
        """
        return CustomerMapper.get_erpnext_customer(salla_customer_id)
    
    def get_salla_id_for_customer(self, customer_name: str) -> Optional[str]:
        """
        Get Salla customer ID for an ERPNext Customer.
        
        Args:
            customer_name: ERPNext Customer name
            
        Returns:
            Salla customer ID or None
        """
        return CustomerMapper.get_salla_customer_id(customer_name)
    
    def get_sync_status(self, customer_name: str) -> Dict[str, Any]:
        """
        Get sync status for a customer.
        
        Args:
            customer_name: ERPNext Customer name
            
        Returns:
            Status dict
        """
        salla_customer = frappe.db.get_value(
            "Salla Customer",
            {"customer": customer_name},
            ["name", "salla_customer_id", "sync_status"],
            as_dict=True
        )
        
        if not salla_customer:
            return {"synced": False, "status": "not_synced"}
        
        return {
            "synced": True,
            "status": salla_customer.sync_status,
            "salla_customer_id": salla_customer.salla_customer_id
        }
    
    def get_salla_customers(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get list of Salla customers.
        
        Args:
            filters: Optional filters
            
        Returns:
            List of customer records
        """
        query_filters = filters or {}
        
        return frappe.get_all(
            "Salla Customer",
            filters=query_filters,
            fields=["name", "salla_customer_id", "customer", "first_name", "last_name", "email", "sync_status"]
        )
