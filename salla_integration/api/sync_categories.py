import frappe
import requests
from salla_integration.api.salla_client import SallaClient


def build_salla_category_payload(category):
    """
    Build the payload for Salla category creation or update.
    """
    
    payload = {
        "name": category.category_name,
    }
    
    if category.get("parent_salla_category"):
        parent_category = frappe.get_doc("Salla Category", category.parent_salla_category)
        payload["parent_id"] = parent_category.salla_category_id
    
    return payload


@frappe.whitelist()
def sync_a_category_to_salla(category):
    
    """
    Sync a single category to Salla.
    """
    
    salla_client = SallaClient()
    payload = build_salla_category_payload(category)
    
    print(payload)
    
    if not category.salla_category_id:
        # Create new category in Salla
        response = salla_client.create_category(payload)
        print(response.json())
        if response.status_code == 201:
            data = response.json()
            print(data)
            category.salla_category_id = data["data"]["id"]
            category.save()
            frappe.db.commit()
    else:
        # Update existing category in Salla
        salla_category_id = category.salla_category_id
        response = salla_client.update_category(salla_category_id, payload)
        print(response.status_code)
        if response.status_code == 200:
            print(response.json())
            category.save()
            frappe.db.commit()


@frappe.whitelist()
def sync_categories_to_salla():
    """
    Sync all categories to Salla.
    """
    categories = frappe.get_all("Salla Category", filters={"sync_to_salla": 1}, order_by="modified asc")
    
    for cat in categories:
        category = frappe.get_doc("Salla Category", cat.name)
        try:
            sync_a_category_to_salla(category)
        except requests.RequestException as e:
            frappe.log_error(f"Failed to sync category {category.name} to Salla: {str(e)}", "Salla Category Sync Error")


@frappe.whitelist()
def bulk_sync(category_ids):
    """
    Bulk sync selected categories to Salla.
    """
    category_ids = frappe.parse_json(category_ids)
    for cat_id in category_ids:
        category = frappe.get_doc("Salla Category", cat_id)
        try:
            sync_a_category_to_salla(category)
        except requests.RequestException as e:
            frappe.log_error(f"Failed to sync category {category.category_name} to Salla: {str(e)}", "Salla Category Bulk Sync Error")


@frappe.whitelist()
def import_categories_from_salla():
    """
    Import categories from Salla into ERPNext.
    """
    salla_client = SallaClient()
    response = salla_client._make_request("GET", "categories")
    
    if response.status_code == 200:
        data = response.json()
        for category_data in data.get("data", []):
            existing_category = frappe.get_all(
                "Salla Category",
                filters={"salla_category_id": category_data["id"]},
                fields=["name"]
            )
            if not existing_category:
                new_category = frappe.get_doc({
                    "doctype": "Salla Category",
                    "category_name": category_data["name"],
                    "salla_category_id": category_data["id"],
                    "is_active": True,
                })
                new_category.insert()
                frappe.db.commit()
    else:
        frappe.log_error(f"Failed to import categories from Salla: {response.text}", "Salla Category Import Error")


"""### App Versions
### App Versions
```
{
	"frappe": "17.0.0-dev",
	"erpnext": "17.0.0-dev",
	"salla_integration": "0.0.1"
}
```
### Route
```
Form/Salla Category/2g6r08d8q6
```
### Traceback
```
Traceback (most recent call last):
  File "apps/frappe/frappe/app.py", line 121, in application
    response = frappe.api.handle(request)
  File "apps/frappe/frappe/api/__init__.py", line 63, in handle
    data = endpoint(**arguments)
  File "apps/frappe/frappe/api/v1.py", line 40, in handle_rpc_call
    return frappe.handler.handle()
           ~~~~~~~~~~~~~~~~~~~~~^^
  File "apps/frappe/frappe/handler.py", line 53, in handle
    data = execute_cmd(cmd)
  File "apps/frappe/frappe/handler.py", line 86, in execute_cmd
    return frappe.call(method, **frappe.form_dict)
           ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "apps/frappe/frappe/__init__.py", line 1124, in call
    return fn(*args, **newargs)
  File "apps/frappe/frappe/utils/typing_validations.py", line 36, in wrapper
    return func(*args, **kwargs)
  File "apps/salla_integration/salla_integration/api/sync_categories.py", line 30, in sync_a_category_to_salla
    payload = build_salla_category_payload(category)
  File "apps/salla_integration/salla_integration/api/sync_categories.py", line 12, in build_salla_category_payload
    "name": category.category_name,
            ^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'str' object has no attribute 'category_name'

```
### Request Data
```
{
	"type": "POST",
	"args": {
		"category": "{\"name\":\"2g6r08d8q6\",\"owner\":\"Administrator\",\"creation\":\"2026-01-14 17:25:43.031432\",\"modified\":\"2026-01-14 17:25:48.801739\",\"modified_by\":\"Administrator\",\"docstatus\":0,\"idx\":0,\"category_name\":\"Bedroom\",\"is_active\":1,\"lft\":3,\"rgt\":4,\"is_group\":0,\"old_parent\":\"\",\"doctype\":\"Salla Category\",\"__last_sync_on\":\"2026-01-16T06:12:26.442Z\"}"
	},
	"headers": {},
	"error_handlers": {},
	"url": "/api/method/salla_integration.api.sync_categories.sync_a_category_to_salla",
	"request_id": null
}
```
### Response Data
```
{
	"exception": "AttributeError: 'str' object has no attribute 'category_name'",
	"exc_type": "AttributeError",
	"_exc_source": "salla_integration (app)"
}
``````"""