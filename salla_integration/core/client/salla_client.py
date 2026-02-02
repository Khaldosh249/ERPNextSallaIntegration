"""
Salla API Client.
Provides methods for interacting with the Salla e-commerce API.
"""

import os
from typing import Any, Optional

import frappe
import requests

from salla_integration.core.client.auth import SallaAuth
from salla_integration.core.client.exceptions import (
	SallaAPIError,
	SallaAuthenticationError,
	SallaConnectionError,
	SallaNotFoundError,
	SallaRateLimitError,
	SallaTimeoutError,
	SallaValidationError,
)


class SallaClient:
	"""
	Client for interacting with the Salla API.
	Handles authentication, request building, and response parsing.
	"""

	BASE_URL = "https://api.salla.dev/admin/v2"
	DEFAULT_TIMEOUT = 30

	def __init__(self):
		self.auth = SallaAuth()

	def _make_request(
		self,
		method: str,
		endpoint: str,
		data: dict | None = None,
		params: dict | None = None,
		timeout: int | None = None,
		custom_headers: dict | None = None,
	) -> requests.Response:
		"""
		Make an authenticated request to the Salla API.

		Args:
		    method: HTTP method (GET, POST, PUT, DELETE)
		    endpoint: API endpoint (without base URL)
		    data: Request body data (for POST, PUT)
		    params: Query parameters (for GET)
		    timeout: Request timeout in seconds

		Returns:
		    requests.Response object

		Raises:
		    SallaAPIError: On API errors
		"""
		url = f"{self.BASE_URL}/{endpoint}"
		headers = self.auth.get_auth_headers()
		timeout = timeout or self.DEFAULT_TIMEOUT

		if custom_headers:
			headers.update(custom_headers)
		print(f"final Headers: {headers}")
		try:
			response = requests.request(
				method=method, url=url, headers=headers, json=data, params=params, timeout=timeout
			)

			self._handle_response_errors(response)
			return response

		except requests.Timeout:
			raise SallaTimeoutError(message=f"Request to {endpoint} timed out after {timeout} seconds")
		except requests.ConnectionError as e:
			raise SallaConnectionError(message=f"Failed to connect to Salla API: {e!s}")

	def _handle_response_errors(self, response: requests.Response):
		"""Handle API response errors and raise appropriate exceptions."""
		if response.status_code == 200 or response.status_code == 201:
			return

		try:
			error_data = response.json()
		except ValueError:
			error_data = {"message": response.text}

		error_message = error_data.get("message", "Unknown error")
		print(f"Validation errors: {error_data.get('error')}")

		print(f"Response Status Code: {response.status_code}")
		print(f"Error message: {error_message}")

		if response.status_code == 401:
			raise SallaAuthenticationError(
				message=error_message, status_code=response.status_code, response_data=error_data
			)
		elif response.status_code == 404:
			raise SallaNotFoundError(
				message=error_message, status_code=response.status_code, response_data=error_data
			)
		elif response.status_code == 422:
			raise SallaValidationError(
				message=error_message,
				status_code=response.status_code,
				response_data=error_data,
				errors=error_data.get("errors", {}),
			)
		elif response.status_code == 429:
			retry_after = response.headers.get("Retry-After")
			raise SallaRateLimitError(
				message=error_message,
				status_code=response.status_code,
				response_data=error_data,
				retry_after=int(retry_after) if retry_after else None,
			)
		elif response.status_code >= 400:
			raise SallaAPIError(
				message=error_message, status_code=response.status_code, response_data=error_data
			)

	# ==================== Product Methods ====================

	def create_product(self, payload: dict) -> dict:
		"""
		Create a new product in Salla.

		Args:
		    payload: Product data

		Returns:
		    Created product data from Salla
		"""
		if "product_type" not in payload:
			payload["product_type"] = "product"

		response = self._make_request("POST", "products", data=payload)
		return response.json()

	def update_product(self, product_id: str, payload: dict, lang: str = "ar") -> dict:
		"""
		Update an existing product in Salla.

		Args:
		    product_id: Salla product ID
		    payload: Updated product data

		Returns:
		    Updated product data from Salla
		"""
		lang_header = {"ACCEPT-LANGUAGE": lang}
		response = self._make_request(
			"PUT", f"products/{product_id}", data=payload, custom_headers=lang_header
		)
		return response.json()

	def get_product(self, product_id: str) -> dict:
		"""
		Get a product by ID from Salla.

		Args:
		    product_id: Salla product ID

		Returns:
		    Product data from Salla
		"""
		response = self._make_request("GET", f"products/{product_id}")
		return response.json()

	def get_product_by_sku(self, sku: str) -> dict:
		"""
		Get a product by SKU from Salla.

		Args:
		    sku: Product SKU

		Returns:
		    Product data from Salla
		"""
		response = self._make_request("GET", f"products/sku/{sku}")
		return response.json()

	def get_products(self, lang: str = "ar", params: dict | None = None) -> dict:
		"""
		Get list of products from Salla.

		Args:
		    params: Query parameters (pagination, filters)

		Returns:
		    List of products from Salla
		"""
		lang_header = {"ACCEPT-LANGUAGE": lang}
		print(f"Custom Headers: {lang_header}")
		response = self._make_request("GET", "products", params=params, custom_headers=lang_header)
		return response.json()

	def delete_product(self, product_id: str) -> dict:
		"""
		Delete a product from Salla.

		Args:
		    product_id: Salla product ID

		Returns:
		    Deletion confirmation from Salla
		"""
		response = self._make_request("DELETE", f"products/{product_id}")
		return response.json()

	def upload_product_image(self, product_id: str, image_path: str, form_data=None) -> dict:
		"""
		Upload an image to a product in Salla by uploading via multipart/form-data.

		Args:
		    product_id: Salla product ID
		    image_path: Path of the image to upload
		    form_data: Additional form data if needed like main image flag
		Returns:
		    Uploaded image data from Salla
		"""

		if form_data is None:
			form_data = {}
		print(f"File Exists: {os.path.exists(image_path)}")

		with open(image_path, "rb") as f:
			files = {"photo": (os.path.basename(image_path), f, "image/jpeg")}

			request_headers = self.auth.get_auth_headers()
			request_headers.pop("Content-Type", None)  # requests will set this boundary for multipart

			url = f"{self.BASE_URL}/products/{product_id}/images"

			print(f"Upload Image URL: {url}")
			response = requests.post(url, headers=request_headers, files=files, data={})
			print("Upload Image Response Status Code:", response.status_code)
			print("Upload Image Response Body:", response.json())
			self._handle_response_errors(response)
			return response.json()

	def delete_product_image(self, image_id: str) -> dict:
		"""
		Delete an image from a product in Salla.

		Args:
		    image_id: Salla image ID
		Returns:
		    Deletion confirmation from Salla
		"""
		response = self._make_request("DELETE", f"products/images/{image_id}")
		return response.json()

	# ==================== Category Methods ====================

	def create_category(self, payload: dict) -> dict:
		"""
		Create a new category in Salla.

		Args:
		    payload: Category data

		Returns:
		    Created category data from Salla
		"""
		response = self._make_request("POST", "categories", data=payload)
		return response.json()

	def update_category(self, category_id: str, payload: dict, lang: str = "ar") -> dict:
		"""
		Update an existing category in Salla.

		Args:
		    category_id: Salla category ID
		    payload: Updated category data
		    lang: Language code for the update

		Returns:
		    Updated category data from Salla
		"""
		lang_header = {"ACCEPT-LANGUAGE": lang}
		response = self._make_request(
			"PUT", f"categories/{category_id}", data=payload, custom_headers=lang_header
		)
		return response.json()

	def get_category(self, category_id: str, lang: str = "ar") -> dict:
		"""
		Get a category by ID from Salla.

		Args:
		    category_id: Salla category ID

		Returns:
		    Category data from Salla
		"""
		lang_header = {"ACCEPT-LANGUAGE": lang}
		response = self._make_request("GET", f"categories/{category_id}", custom_headers=lang_header)
		return response.json()

	def get_categories(self, params: dict | None = None, lang: str = "ar") -> dict:
		"""
		Get list of categories from Salla.

		Args:
		    params: Query parameters (pagination, filters)

		Returns:
		    List of categories from Salla
		"""
		lang_header = {"ACCEPT-LANGUAGE": lang}
		response = self._make_request("GET", "categories", params=params, custom_headers=lang_header)
		return response.json()

	def delete_category(self, category_id: str) -> dict:
		"""
		Delete a category from Salla.

		Args:
		    category_id: Salla category ID

		Returns:
		    Deletion confirmation from Salla
		"""
		response = self._make_request("DELETE", f"categories/{category_id}")
		return response.json()

	# ==================== Customer Methods ====================

	def get_customer(self, customer_id: str) -> dict:
		"""
		Get a customer by ID from Salla.

		Args:
		    customer_id: Salla customer ID

		Returns:
		    Customer data from Salla
		"""
		response = self._make_request("GET", f"customers/{customer_id}")
		return response.json()

	def get_customers(self, params: dict | None = None) -> dict:
		"""
		Get list of customers from Salla.

		Args:
		    params: Query parameters (pagination, filters)

		Returns:
		    List of customers from Salla
		"""
		response = self._make_request("GET", "customers", params=params)
		return response.json()

	# ==================== Order Methods ====================

	def get_order(self, order_id: str) -> dict:
		"""
		Get an order by ID from Salla.

		Args:
		    order_id: Salla order ID

		Returns:
		    Order data from Salla
		"""
		response = self._make_request("GET", f"orders/{order_id}")
		return response.json()

	def get_orders(self, params: dict | None = None) -> dict:
		"""
		Get list of orders from Salla.

		Args:
		    params: Query parameters (pagination, filters)

		Returns:
		    List of orders from Salla
		"""
		response = self._make_request("GET", "orders", params=params)
		return response.json()

	def update_order_status(self, order_id: str, status_id: str) -> dict:
		"""
		Update order status in Salla.

		Args:
		    order_id: Salla order ID
		    status: New order status

		Returns:
		    Updated order data from Salla
		"""

		update_status_payload = {
			"operations": [
				{
					"action_name": "change_status",
					"value": {
						"status": status_id,
						"send_status_sms": True,
						"return_police": True,
						"restore_items": True,
						# "note": "one note",
						# "branch_id": 21123
					},
				},
			],
			"filters": {"order_ids": [order_id], "order_status": []},
		}

		response = self._make_request("POST", "orders/actions", data=update_status_payload)
		return response.json()

	def get_order_items(self, order_id: str) -> dict:
		"""
		Get items of an order from Salla.

		Args:
		    order_id: Salla order ID

		Returns:
		    Order items data from Salla
		"""
		response = self._make_request("GET", f"orders/items?order_id={order_id}")
		return response.json()

	# ==================== Stock Methods ====================

	def update_stock(self, product_id: str, quantity: int) -> dict:
		"""
		Update product stock quantity in Salla.

		Args:
		    product_id: Salla product ID
		    quantity: New stock quantity

		Returns:
		    Updated product data from Salla
		"""
		response = self._make_request("PUT", f"products/{product_id}", data={"quantity": quantity})
		print("Update Stock Response Status Code:", response.status_code)
		print("Update Stock Response Body:", response.json())
		return response.json()

	# ==================== Order Status Methods ====================

	def get_order_statuses(self, params: dict | None = None) -> dict:
		"""
		Get list of order statuses from Salla.

		Args:
		    params: Query parameters (pagination, filters)

		Returns:
		    List of order statuses from Salla
		"""
		response = self._make_request("GET", "orders/statuses", params=params)
		return response.json()
