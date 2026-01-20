import frappe
from frappe.utils import now_datetime, add_to_date
import urllib.parse
import requests


@frappe.whitelist()
def start():
    settings = frappe.get_single("Salla Settings")
    
    params = {
        "client_id": settings.client_id,
        "response_type": "code",
        "redirect_uri": get_redirect_uri(),
        "state": frappe.generate_hash(length=16)
    }
    
    print(params)
    
    url = "https://accounts.salla.sa/oauth2/auth?" + urllib.parse.urlencode(params)
    
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = url
    

def get_redirect_uri():
    # return frappe.utils.get_url(
    #     "/api/method/salla_integration.api.oauth.callback"
    # )
    return "https://erpnext.khaldosh.dev/api/method/salla_integration.api.oauth.callback"


@frappe.whitelist(allow_guest=True)
def callback(code=None, **kwargs):
    
    if not code:
        frappe.throw("Authorization code missing")
    
    settings = frappe.get_single("Salla Settings")
    
    token_response = requests.post(
        "https://accounts.salla.sa/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "redirect_uri": get_redirect_uri(),
            "code": code,
        },
        timeout=20
    ).json()
    
    settings.access_token = token_response["access_token"]
    settings.refresh_token = token_response["refresh_token"]
    settings.token_expires_at = add_to_date(
        now_datetime(),
        seconds=token_response["expires_in"]
    )
    
    settings.save(ignore_permissions=True)
    frappe.db.commit()
    
    
    frappe.msgprint("Salla connected successfully 🎉")
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/app/salla-settings"





