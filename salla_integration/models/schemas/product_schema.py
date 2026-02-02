"""
Product validation schema.
Defines required fields and validation rules for products.
"""

from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional


@dataclass
class ProductSchema:
	"""
	Schema for product validation.
	"""

	# Required fields for Salla
	REQUIRED_FOR_SALLA: ClassVar[list[str]] = ["name", "price"]

	# Required fields for ERPNext
	REQUIRED_FOR_ERPNEXT: ClassVar[list[str]] = ["item_code", "item_name"]

	# Field mappings
	FIELD_MAP: ClassVar[dict[str, str]] = {
		"item_name": "name",
		"item_code": "sku",
		"standard_rate": "price",
		"description": "description",
	}

	@classmethod
	def validate_for_salla(cls, data: dict[str, Any]) -> dict[str, Any]:
		"""
		Validate product data for Salla API.

		Args:
		    data: Product data dict

		Returns:
		    Dict with is_valid and errors
		"""
		errors = []

		for field_name in cls.REQUIRED_FOR_SALLA:
			value = data.get(field_name)
			if not value:
				errors.append(f"Missing required field: {field_name}")

		# Validate price
		price = data.get("price")
		if price is not None:
			try:
				price_val = float(price)
				if price_val < 0:
					errors.append("Price cannot be negative")
			except (ValueError, TypeError):
				errors.append("Price must be a number")

		# Validate quantity
		quantity = data.get("quantity")
		if quantity is not None:
			try:
				qty_val = int(quantity)
				if qty_val < 0:
					errors.append("Quantity cannot be negative")
			except (ValueError, TypeError):
				errors.append("Quantity must be an integer")

		return {"is_valid": len(errors) == 0, "errors": errors}

	@classmethod
	def validate_for_erpnext(cls, data: dict[str, Any]) -> dict[str, Any]:
		"""
		Validate product data for ERPNext Item.

		Args:
		    data: Product data dict

		Returns:
		    Dict with is_valid and errors
		"""
		errors = []

		for field_name in cls.REQUIRED_FOR_ERPNEXT:
			value = data.get(field_name)
			if not value:
				errors.append(f"Missing required field: {field_name}")

		# Validate item_code format
		item_code = data.get("item_code", "")
		if item_code and len(item_code) > 140:
			errors.append("Item code cannot exceed 140 characters")

		return {"is_valid": len(errors) == 0, "errors": errors}

	@classmethod
	def get_salla_api_fields(cls) -> list[str]:
		"""Get list of fields accepted by Salla API."""
		return [
			"name",
			"description",
			"price",
			"sale_price",
			"cost_price",
			"quantity",
			"sku",
			"weight",
			"weight_type",
			"categories",
			"images",
			"options",
			"status",
			"require_shipping",
			"unlimited_quantity",
		]

	@classmethod
	def sanitize_for_salla(cls, data: dict[str, Any]) -> dict[str, Any]:
		"""
		Sanitize product data for Salla API.
		Removes unsupported fields.

		Args:
		    data: Raw product data

		Returns:
		    Sanitized data dict
		"""
		allowed_fields = cls.get_salla_api_fields()
		return {k: v for k, v in data.items() if k in allowed_fields and v is not None}
