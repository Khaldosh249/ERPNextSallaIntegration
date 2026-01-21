"""
Customer synchronization manager.
Handles syncing customers from Salla to ERPNext.
"""

import frappe
from typing import Dict, Any, Optional

from salla_integration.synchronization.base.sync_manager import BaseSyncManager
from salla_integration.core.utils.helpers import get_default_company, get_default_customer_group, get_default_territory


class CustomerSyncManager(BaseSyncManager):
    """
    Manages customer synchronization from Salla to ERPNext.
    Customers are primarily synced FROM Salla TO ERPNext.
    """
    
    entity_type = "Customer"
    
    def sync_to_salla(self, doc) -> Dict[str, Any]:
        """
        Sync customer to Salla (not typically used).
        Customers are primarily synced from Salla.
        """
        return {"status": "skipped", "message": "Customer sync to Salla not supported"}
    
    def sync_from_salla(self, customer_data: Dict = None, **kwargs) -> Dict[str, Any]:
        """
        Sync a customer from Salla to ERPNext.
        
        Args:
            customer_data: Customer data from Salla webhook or API
            
        Returns:
            Result dict with status and details
        """
        # Handle kwargs for enqueue compatibility
        if customer_data is None:
            customer_data = kwargs.get("customer_data", {})
            
        salla_customer_id = str(customer_data.get("id", ""))
        
        if not salla_customer_id:
            return {"status": "error", "message": "No customer ID in data"}
        
        # # Check if customer already exists
        # existing_salla_customer = frappe.db.get_value(
        #     "Salla Customer",
        #     {"salla_customer_id": salla_customer_id},
        #     ["name", "customer"],
        #     as_dict=True
        # )
        
        try:
            
            # Create new customer
            result = self._create_customer(customer_data)
            operation = "Create"
            
            if result.get("status") == "success":
                self.handle_sync_success(
                    operation=operation,
                    reference_doctype="Customer",
                    reference_name=result.get("customer"),
                    salla_id=salla_customer_id
                )
            
            return result
            
        except Exception as e:
            self.handle_sync_error(
                operation="Sync from Salla",
                reference_doctype="Customer",
                reference_name="New",
                error=e,
                salla_id=salla_customer_id
            )
            return {"status": "error", "message": str(e)}
    
    def build_payload(self, doc) -> Dict[str, Any]:
        """Not used for customer sync (inbound only)."""
        return {}
    
    def create_or_get_customer(self, customer_data: Dict, order_options_details: list[Dict]) -> Dict[str, Any]:
        """
        Create a new ERPNext Customer from Salla data.
        
        Args:
            customer_data: Customer data from Salla
            order_options_details: Additional order options ( to Extract : customer_name, tax_id, custom_commercial_register)
        Returns:
            Result dict
        """
        
        # order_options schema 
        
        """
        product_type: only take when product_type is 'order_option'
        name: field name
        options: list of options: name and value
        
        
        
        name to ERPNext field mapping:
        السجل التجاري -> custom_commercial_register
        الرقم الضريبي -> tax_id
        اسم الشركة -> customer_name
        """
        
        custom_commercial_register = None
        tax_id = None
        company_name = None
        
        print("Extracting order options for customer...")
        print(order_options_details)
        for option in order_options_details:
            if option.get("product_type") == "order_option":
                field_name = option.get("name")
                for opt in option.get("options", []):
                    if field_name == "السجل التجاري":
                        custom_commercial_register = opt.get("value")
                    elif field_name == "الرقم الضريبي":
                        tax_id = opt.get("value")
                    elif field_name == "اسم الشركة":
                        company_name = opt.get("value")
        
        print("Extracted company_name:", company_name)
        print("Extracted tax_id:", tax_id)
        print("Extracted custom_commercial_register:", custom_commercial_register)
        
        # Extract customer info
        first_name = customer_data.get("first_name", "")
        last_name = customer_data.get("last_name", "")
        # full_name = f"{first_name} {last_name}".strip() or f"Salla Customer {customer_data.get('id')}"
        full_name = customer_data.get("full_name")
        email = customer_data.get("email")
        mobile_code = customer_data.get("mobile_code", "")
        mobile = customer_data.get("mobile")
        if mobile and mobile_code:
            mobile = f"{mobile_code}{mobile}"
        
        
        # Get customer From ERPNext if exists based on company_name if exists or full_name, or create new one
        
        exists = frappe.db.get_value(
            "Customer",
            {
                "customer_name": company_name or full_name
            },
            as_dict=True
        )
        
        if exists:
            print("Customer already exists with company_name:", company_name)
            return {
                "status": "exists",
                "customer": exists.name
            }
        
        default_customer_group = get_default_customer_group()
        default_territory = get_default_territory()
        
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": company_name or full_name,
            "customer_type": "Company",
            "customer_group": default_customer_group,
            "territory": default_territory,
            "tax_id": tax_id,
            "company": get_default_company(),
            "custom_commercial_register": custom_commercial_register
        })
        
        customer.insert(ignore_permissions=True)
        
        # Create linked Contact
        self._create_contact(
            customer_name=customer.name,
            first_name=first_name,
            last_name=last_name,
            email=email,
            mobile=mobile
        )
        
        
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "customer": customer.name,
            # "salla_customer": salla_customer.name
        }
    
    def _update_customer(self, salla_customer: Dict, customer_data: Dict) -> Dict[str, Any]:
        """
        Update an existing ERPNext Customer from Salla data.
        
        Args:
            salla_customer: Existing Salla Customer record
            customer_data: Updated customer data from Salla
            
        Returns:
            Result dict
        """
        # Update ERPNext Customer
        first_name = customer_data.get("first_name", "")
        last_name = customer_data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        
        if full_name and salla_customer.customer:
            frappe.db.set_value(
                "Customer",
                salla_customer.customer,
                "customer_name",
                full_name
            )
        
        # Update Salla Customer record
        salla_customer_doc = frappe.get_doc("Salla Customer", salla_customer.name)
        salla_customer_doc.first_name = first_name
        salla_customer_doc.last_name = last_name
        salla_customer_doc.email = customer_data.get("email")
        salla_customer_doc.mobile = customer_data.get("mobile")
        salla_customer_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "customer": salla_customer.customer,
            "salla_customer": salla_customer.name
        }
    
    def _create_contact(
        self,
        customer_name: str,
        first_name: str,
        last_name: str,
        email: Optional[str],
        mobile: Optional[str]
    ):
        """Create a Contact linked to the Customer."""
        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": first_name or "Customer",
            "last_name": last_name,
            "links": [{
                "link_doctype": "Customer",
                "link_name": customer_name
            }]
        })
        
        if email:
            contact.append("email_ids", {
                "email_id": email,
                "is_primary": 1
            })
        
        if mobile:
            contact.append("phone_nos", {
                "phone": mobile,
                "is_primary_mobile_no": 1
            })
        
        contact.insert(ignore_permissions=True)
    
    def import_all_customers(self) -> Dict[str, Any]:
        """
        Import all customers from Salla.
        
        Returns:
            Result dict with counts
        """
        try:
            response = self.client.get_customers()
            
            if not response.get("success"):
                return {"status": "error", "message": response.get("message")}
            
            customers = response.get("data", [])
            imported = 0
            updated = 0
            failed = 0
            
            for customer_data in customers:
                result = self.sync_from_salla(customer_data)
                if result["status"] == "success":
                    imported += 1
                elif result["status"] == "updated":
                    updated += 1
                else:
                    failed += 1
            
            return {
                "status": "success",
                "imported": imported,
                "updated": updated,
                "failed": failed,
                "total": len(customers)
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Convenience functions

@frappe.whitelist()
def import_customers_from_salla():
    """Import all customers from Salla."""
    sync_manager = CustomerSyncManager()
    return sync_manager.import_all_customers()
