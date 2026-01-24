"""
Order synchronization manager.
Handles syncing orders from Salla to ERPNext.
"""

import frappe
from typing import Dict, Any, Optional

from salla_integration.synchronization.base.sync_manager import BaseSyncManager
# from salla_integration.synchronization.orders.status_mapper import map_salla_status_to_erpnext
from salla_integration.core.utils.helpers import get_default_company, get_default_currency, get_default_price_list, get_default_taxes_and_charges, get_default_warehouse, get_order_status_after_deivery_note_submission, get_secondary_warehouse, get_item_stock_in_warehouse, get_taxes_from_sales_taxes_template
from salla_integration.synchronization.customers.sync_manager import CustomerSyncManager
from salla_integration.synchronization.products.stock_sync import sync_stock_to_salla

class OrderSyncManager(BaseSyncManager):
    """
    Manages order synchronization from Salla to ERPNext.
    Orders are synced FROM Salla TO ERPNext.
    """
    
    entity_type = "Order"
    
    
    # FOR ABSTRACTION PURPOSES
    def sync_to_salla(self, sales_order_name: str) -> Dict[str, Any]:
        """
        Sync an ERPNext Sales Order to Salla.
        
        Args:
            sales_order_name: Name of the Sales Order to sync
            
        Returns:
            Result dict with status and details
        """
        # Currently not implemented
        return {
            "status": "error",
            "message": "Sync to Salla not implemented for orders."
        }
    
    # FOR ABSTRACTION PURPOSES
    def build_payload(self, sales_order_name: str) -> Dict[str, Any]:
        """
        Build payload for syncing Sales Order to Salla.
        
        Args:
            sales_order_name: Name of the Sales Order
        Returns:
            Payload dict
        """
        # Currently not implemented
        return {}
    
    def sync_from_salla(self, order_data: Dict = None, **kwargs) -> Dict[str, Any]:
        """
        Sync an order from Salla to ERPNext.
        
        Args:
            order_data: Order data from Salla webhook or API
            
        Returns:
            Result dict with status and details
        """
        # Handle kwargs for enqueue compatibility
        if order_data is None:
            order_data = kwargs.get("order_data", {})
            
        salla_order_id = str(order_data.get("id", ""))
        print(f"Syncing order from Salla: {salla_order_id}")
        if not salla_order_id:
            return {"status": "error", "message": "No order ID in data"}
        
        # Check if order already exists
        existing_salla_order = frappe.db.get_value(
            "Salla Order",
            {"salla_order_id": salla_order_id},
            ["name", "sales_order"],
            as_dict=True
        )
        print(f"Existing Salla Order: {existing_salla_order}")
        try:
            if existing_salla_order:
                print("Updating existing order...")
                # Update existing order
                result = self._update_order(existing_salla_order, order_data)
                operation = "Update"
            else:
                print("Creating new order...")
                # Create new order
                result = self.create_order(order_data)
                operation = "Create"
            
            if result.get("status") == "success":
                print("Sync successful.")
                self.handle_sync_success(
                    operation=operation,
                    reference_doctype="Sales Order",
                    reference_name=result.get("sales_order"),
                    salla_id=salla_order_id
                )
            
            return result
            
        except Exception as e:
            self.handle_sync_error(
                operation="Sync from Salla",
                reference_doctype="Sales Order",
                reference_name=existing_salla_order.sales_order if existing_salla_order else "New",
                error=e,
                salla_id=salla_order_id
            )
            print(str(e))
            return {"status": "error", "message": str(e)}
    
    
    def create_order(self, order_data: Dict) -> Dict[str, Any]:
        """
        Create a new ERPNext Sales Order from Salla order data.
        
        Args:
            order_data: Order data from Salla
            
        Returns:
            Result dict
        """
        
        
        # Get or create customer
        customer = self._get_or_create_customer(
            order_data.get("customer", {}),
            order_data.get("options", [])
            )
        
        # Get Deliverable Address
        deliverable_address = self._get_deliverable_address(order_data)
        
        company = get_default_company()
        if not company:
            return {"status": "error", "message": "No default company configured"}
        
        print(f"Creating Sales Order for customer: {customer} in company: {company}")
        
        # Get order items from Salla Client
        items_data = self.client.get_order_items(order_data.get("id"))
        
        default_price_list = get_default_price_list()
        default_currency = get_default_currency()
        default_taxes_and_charges_template = get_default_taxes_and_charges()
        default_taxes = get_taxes_from_sales_taxes_template(default_taxes_and_charges_template) if default_taxes_and_charges_template else []
        
        # Sales Order Data
        sales_order_data = {
            "doctype": "Sales Order",
            "customer": customer,
            "company": company,
            "order_type": "Sales",
            "transaction_date": frappe.utils.today(),
            # Delivery after 7 days from order date
            "delivery_date": frappe.utils.add_days(frappe.utils.today(), 7),
            "items": self._build_order_items(items_data.get("data", [])),
            "selling_price_list": default_price_list,
            "price_list_currency": default_currency,
            "taxes_and_charges": default_taxes_and_charges_template,
            "taxes": default_taxes,
            "custom_delivery_location_الموقع_التوريد_": deliverable_address,
            "conversion_rate": 1,
            "plc_conversion_rate": 1,
        }
        
        # Create Sales Order
        sales_order = frappe.get_doc(sales_order_data)
        
        print("Inserting Sales Order...")
        print(sales_order_data)
        
        sales_order.insert(ignore_permissions=True)
        
        print(f"Created Sales Order: {sales_order.name}")
        
        
        # Create Salla Order record
        salla_order = frappe.get_doc({
            "doctype": "Salla Order",
            "salla_order_id": str(order_data.get("id")),
            "sales_order": sales_order.name,
            "order_status": order_data.get("status", {}).get("name", ""),
            "total": order_data.get("amounts", {}).get("total", {}).get("amount", 0),
            "sync_status": "Synced"
        })
        salla_order.insert(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "sales_order": sales_order.name,
            "salla_order": salla_order.name
        }
    
    
    def _get_or_create_customer(self, customer_data: Dict, order_options: list[Dict]) -> str:
        """
        Get or create a customer for the order.
        
        Args:
            customer_data: Customer data from order
            
        Returns:
            Customer name
        """
        
        print("Getting or creating customer...")
        
        sync_manager = CustomerSyncManager()
        result = sync_manager.create_or_get_customer(
            customer_data,
            order_options
        )
        
        if result.get("status") == "success" or result.get("status") == "exists":
            return result.get("customer")
        
        # Fallback to a default customer
        return self._get_default_customer()
    
    def _get_deliverable_address(self, order_data: Dict) -> Optional[str]:
        """
        Get or create a deliverable address for the order.
        
        Args:
            order_data: Order data from Salla
        Returns:
            Address name or None
        """
        
        if not order_data.get("shipping"):
            return None
        
        shipping_data = order_data.get("shipping", {})
        
        if not shipping_data.get("address"):
            return None
        
        address = shipping_data.get("address", {})
        
        address_title = f"{address.get('shipping_address', '')}"
        
        return address_title
    
    def _get_default_customer(self) -> str:
        """Get or create a default Salla customer."""
        default_customer_name = "Salla Walk-in Customer"
        
        if not frappe.db.exists("Customer", default_customer_name):
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": default_customer_name,
                "customer_type": "Individual",
                "customer_group": "Individual",
                "territory": "All Territories",
            })
            customer.insert(ignore_permissions=True)
            frappe.db.commit()
        
        return default_customer_name
    
    def _build_order_items(self, items_data: list) -> list:
        """
        Build Sales Order items from Salla order items.
        
        Args:
            items_data: List of items from Salla order
            
        Returns:
            List of item dicts for Sales Order
        """
        items = []
        default_warehouse = get_default_warehouse()
        secondary_warehouse = get_secondary_warehouse()
        
        for item_data in items_data:
            
            print(f"Processing order item: ")
            
            sku = item_data.get("sku", "")
            
            # Find ERPNext item by SKU
            item_code = frappe.db.get_value("Item", {"item_code": sku}, "item_code")
            
            if not item_code:
                # Try to find by Salla Product
                item_code = frappe.db.get_value(
                    "Salla Product",
                    {"salla_product_id": str(item_data.get("product_id", ""))},
                    "item_code"
                )
            
            if item_code:
                # items.append({
                #     "item_code": item_code,
                #     "qty": item_data.get("quantity", 1),
                #     "rate": item_data.get("price", {}).get("amount", 0),
                #     "warehouse": warehouse
                # })
                
                # Check stock in both warehouses
                stock_in_default = get_item_stock_in_warehouse(item_code, default_warehouse) if default_warehouse else 0
                stock_in_secondary = get_item_stock_in_warehouse(item_code, secondary_warehouse) if secondary_warehouse else 0
                total_stock = stock_in_default + stock_in_secondary
                allocated_qty = item_data.get("quantity", 1)
                selected_warehouse = None
                if total_stock >= allocated_qty:
                    selected_warehouse = default_warehouse
                elif stock_in_default >= allocated_qty:
                    selected_warehouse = default_warehouse
                elif stock_in_secondary >= allocated_qty:
                    selected_warehouse = secondary_warehouse
                else:
                    selected_warehouse = default_warehouse  # Default to primary warehouse
                
                item_price = item_data.get("amounts", {}).get("original_price", {}).get("amount", 0)
                
                items.append({
                    "item_code": item_code,
                    "qty": allocated_qty,
                    "rate": item_price,
                    "warehouse": selected_warehouse
                })
                print(f"Added item: {item_code}, Qty: {allocated_qty}, Warehouse: {selected_warehouse}")
            else:
                print(f"Item with SKU {sku} not found in ERPNext.")
                
        
        print(f"Built {len(items)} order items.")
        return items
    
    
    def update_order_status_when_delivery_note_created(self, sales_order_name: str) -> None:
        """
        Update Salla order status when a Delivery Note is created against the Sales Order.
        
        Args:
            sales_order_name: Name of the Sales Order
        """
        salla_order = frappe.db.get_value(
            "Salla Order",
            {"sales_order": sales_order_name},
            ["name", "salla_order_id"],
            as_dict=True
        )
        
        if not salla_order:
            print(f"No Salla Order linked to Sales Order: {sales_order_name}")
            
            # ! Handle Non-salla orders -> Handle Stock Update in Salla for affected items
            
            self.handle_non_salla_order_delivery_note(sales_order_name)
            
            
            return
        
        salla_order_status_name = get_order_status_after_deivery_note_submission()
        
        salla_order_status_record = frappe.get_doc(
            "Salla Order Status",
            salla_order_status_name
        ) if salla_order_status_name else None
        
        if not salla_order_status_record:
            print(f"No Salla Order Status configured for Delivery Note submission.")
            return
        
        salla_order_id = salla_order.salla_order_id
        
        print(f"Updating Salla order status for Salla Order ID: {salla_order_id}")
        
        try:
            response = self.client.update_order_status(
                salla_order_id,
                str(salla_order_status_record.salla_status_id)
            )
            
            if response.get("success"):
                print(f"Salla order {salla_order_id} status updated successfully.")
                
                # Update local Salla Order record
                # salla_order_doc = frappe.get_doc("Salla Order", salla_order.name)
                # salla_order_doc.order_status = "delivered"
                # salla_order_doc.sync_status = "Synced"
                # salla_order_doc.save(ignore_permissions=True)
                frappe.db.commit()
            else:
                print(f"Failed to update Salla order {salla_order_id} status: {response.get('message')}")
                
        except Exception as e:
            print(f"Error updating Salla order status: {str(e)}")
    
    
    def handle_non_salla_order_delivery_note(self, sales_order_name: str) -> None:
        
        sales_order = frappe.get_doc("Sales Order", sales_order_name)
        print(f"Handling stock update for non-Salla linked Sales Order: {sales_order_name}")
        
        for item in sales_order.items:
            
            item_doc = frappe.get_doc("Item", item.item_code)
            
            if not item_doc.custom_sync_with_salla or not item_doc.custom_sync_stock:
                continue
            
            
            result = sync_stock_to_salla(item.item_code)
            print(f"Stock sync result for item {item.item_code}: {result}")
            
            
        
    
    
    def import_all_orders(self) -> Dict[str, Any]:
        """
        Import all orders from Salla.
        
        Returns:
            Result dict with counts
        """
        try:
            response = self.client.get_orders()
            
            if not response.get("success"):
                return {"status": "error", "message": response.get("message")}
            
            # print(response)
            
            orders = response.get("data", [])
            imported = 0
            updated = 0
            failed = 0
            
            print(f"Found {len(orders)} orders to import.")
            
            for order_data in orders:
                result = self.sync_from_salla(order_data)
                if result["status"] == "success":
                    imported += 1
                else:
                    print(f"Failed to import order {order_data.get('id')}: {result.get('message')}")
                    failed += 1
            
            return {
                "status": "success",
                "imported": imported,
                "updated": updated,
                "failed": failed,
                "total": len(orders)
            }
            
        except Exception as e:
            print(str(e))
            return {"status": "error", "message": str(e)}
    
    
    # ========================= Get all Order Statuses from Salla =========================
    def get_all_order_statuses(self) -> Dict[str, Any]:
        """
        Get all order statuses from Salla.
        
        Returns:
            Result dict with statuses
        """
        try:
            response = self.client.get_order_statuses()
            
            if not response.get("success"):
                return {"status": "error", "message": response.get("message")}
            
            statuses = response.get("data", [])
            print(f"Retrieved {len(statuses)} order statuses from Salla.")
            
            # Create Salla Order Status records
            for status in statuses:
                salla_status_id = str(status.get("id", ""))
                existing = frappe.db.get_value(
                    "Salla Order Status",
                    {"salla_status_id": salla_status_id},
                    "name"
                )
                if not existing:
                    salla_order_status = frappe.get_doc({
                        "doctype": "Salla Order Status",
                        "salla_status_id": salla_status_id,
                        "status_name": status.get("name", ""),
                        "status_slug": status.get("slug", "")
                    })
                    salla_order_status.insert(ignore_permissions=True)
                    print(f"Created Salla Order Status: {salla_status_id} - {status.get('name', '')}")
                else:
                    print(f"Salla Order Status already exists: {salla_status_id}, Updating...")
                    salla_order_status = frappe.get_doc("Salla Order Status", existing)
                    salla_order_status.status_name = status.get("name", "")
                    salla_order_status.status_slug = status.get("slug", "")
                    salla_order_status.save(ignore_permissions=True)
            frappe.db.commit()
            return {
                "status": "success",
                "total_statuses": len(statuses)
            }
        except Exception as e:
            print(str(e))
            return {"status": "error", "message": str(e)}
        
    


# Convenience functions

@frappe.whitelist()
def import_orders_from_salla():
    """Import all orders from Salla."""
    print("Importing orders from Salla...")
    sync_manager = OrderSyncManager()
    # return sync_manager.import_all_orders()
    
    order = sync_manager.client.get_order("1585558442")
    # print(order) 
    sync_manager.create_order(order.get("data", {}))
    


@frappe.whitelist()
def get_salla_order_statuses():
    """Get all order statuses from Salla."""
    print("Getting Salla order statuses...")
    sync_manager = OrderSyncManager()
    return sync_manager.get_all_order_statuses()



@frappe.whitelist()
def update_salla_order_status_on_delivery_note(sales_order_name: str):
    """Update Salla order status when a Delivery Note is created."""
    print(f"Updating Salla order status for Sales Order: {sales_order_name}")
    sync_manager = OrderSyncManager()
    sync_manager.update_order_status_when_delivery_note_created(sales_order_name)
    return {"status": "success", "message": "Salla order status update attempted."}
