"""
Customer validation schema.
Defines required fields and validation rules for customers.
"""

import re
from typing import Any, ClassVar


class CustomerSchema:
	"""
	Schema for customer validation.
	"""

	# Required fields for ERPNext
	REQUIRED_FOR_ERPNEXT: ClassVar[list[str]] = ["customer_name"]

	@classmethod
	def validate_for_erpnext(cls, data: dict[str, Any]) -> dict[str, Any]:
		"""
		Validate customer data for ERPNext Customer.

		Args:
		    data: Customer data dict

		Returns:
		    Dict with is_valid and errors
		"""
		errors = []

		for field_name in cls.REQUIRED_FOR_ERPNEXT:
			value = data.get(field_name)
			if not value:
				errors.append(f"Missing required field: {field_name}")

		# Validate email if provided
		email = data.get("email") or data.get("_email")
		if email and not cls._is_valid_email(email):
			errors.append("Invalid email format")

		# Validate mobile if provided
		mobile = data.get("mobile") or data.get("_mobile")
		if mobile and not cls._is_valid_phone(mobile):
			errors.append("Invalid mobile number format")

		return {"is_valid": len(errors) == 0, "errors": errors}

	@classmethod
	def validate_salla_customer(cls, data: dict[str, Any]) -> dict[str, Any]:
		"""
		Validate customer data from Salla.

		Args:
		    data: Customer data from Salla

		Returns:
		    Dict with is_valid and errors
		"""
		errors = []

		# Must have ID
		if not data.get("id"):
			errors.append("Missing customer ID")

		# Should have at least name or email
		has_name = data.get("first_name") or data.get("last_name")
		has_email = data.get("email")

		if not has_name and not has_email:
			errors.append("Customer must have name or email")

		return {"is_valid": len(errors) == 0, "errors": errors}

	@staticmethod
	def _is_valid_email(email: str) -> bool:
		"""Check if email format is valid."""
		pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
		return bool(re.match(pattern, email))

	@staticmethod
	def _is_valid_phone(phone: str) -> bool:
		"""Check if phone format is valid."""
		# Remove common formatting characters
		cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)
		# Should be digits only and reasonable length
		return cleaned.isdigit() and 7 <= len(cleaned) <= 15

	@classmethod
	def get_contact_fields(cls) -> list[str]:
		"""Get fields for Contact creation."""
		return ["first_name", "last_name", "email", "mobile", "phone"]

	@classmethod
	def get_address_fields(cls) -> list[str]:
		"""Get fields for Address creation."""
		return ["street", "street_number", "city", "region", "country_code", "postal_code", "phone"]
