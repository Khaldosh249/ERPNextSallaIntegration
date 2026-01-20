import frappe
import requests


class SallaClient:
    
    def __init__(self):
        
        # self.api_key = frappe.get_doc("Salla Settings").api_key
        
        self.salla_settings = frappe.get_single("Salla Settings")
        self.api_key = self.salla_settings.get_password("access_token")
        self.refresh_token = self.salla_settings.get_password("refresh_token")
        self.token_expires_at = frappe.utils.get_datetime(self.salla_settings.token_expires_at) if self.salla_settings.token_expires_at else None
        
        self.base_url = "https://api.salla.dev/admin/v2"
    
    def _make_request(self, method, endpoint, data=None):
        
        if self.token_expires_at and frappe.utils.now_datetime() >= self.token_expires_at:
            print("Access token expired. Refreshing...")
            self.refresh_access_token(self.refresh_token)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/{endpoint}" 
        response = requests.request(method, url, headers=headers, json=data)
        return response
    
    def create_product(self, product_payload):
        if "product_type" not in product_payload:
            product_payload["product_type"] = "product"
        return self._make_request("POST", "products", data=product_payload)
    
    def update_product(self, product_id, product_payload):
        return self._make_request("PUT", f"products/{product_id}", data=product_payload)
    
    def get_product(self, product_id):
        return self._make_request("GET", f"products/{product_id}")
    
    def get_product_by_sku(self, sku):
        return self._make_request("GET", f"products/sku/{sku}")
    
    def get_products(self, params=None):
        return self._make_request("GET", "products", data=params or {})
    
    def create_or_update_product(self, product_payload):
        pass
    
    def refresh_access_token(self, refresh_token):
        
        response = requests.post(
            "https://accounts.salla.sa/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": self.salla_settings.client_id,
                "client_secret": self.salla_settings.client_secret,
                "refresh_token": refresh_token,
            },
            timeout=20
        )
        
        response.raise_for_status()
        token_data = response.json()
        
        self.api_key = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]
        self.token_expires_at = frappe.utils.add_to_date(
            frappe.utils.now_datetime(),
            seconds=token_data["expires_in"]
        )
        # Update settings
        self.salla_settings.access_token = self.api_key
        self.salla_settings.refresh_token = self.refresh_token
        self.salla_settings.token_expires_at = self.token_expires_at
        self.salla_settings.save(ignore_permissions=True)
        frappe.db.commit()
        return token_data
        
        
    
    def create_category(self, category_payload):
        return self._make_request("POST", "categories", data=category_payload)
    
    def update_category(self, category_id, category_payload):
        return self._make_request("PUT", f"categories/{category_id}", data=category_payload)
    
    



