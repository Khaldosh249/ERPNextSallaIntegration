"""
Category validation schema.
Defines required fields and validation rules for categories.
"""

from typing import Any, ClassVar


class CategorySchema:
	"""
	Schema for Salla Category validation.
	"""

	# Required fields for Salla API
	REQUIRED_FOR_SALLA: ClassVar[list[str]] = ["name"]

	# Required fields for Salla Category DocType
	REQUIRED_FOR_ERPNEXT: ClassVar[list[str]] = ["category_name"]

	@classmethod
	def validate_for_salla(cls, data: dict[str, Any]) -> dict[str, Any]:
		"""
		Validate category data for Salla API.

		Args:
		    data: Category data dict

		Returns:
		    Dict with is_valid and errors
		"""
		errors = []

		for field_name in cls.REQUIRED_FOR_SALLA:
			value = data.get(field_name)
			if not value:
				errors.append(f"Missing required field: {field_name}")

		# Validate name length
		name = data.get("name", "")
		if name and len(name) > 255:
			errors.append("Category name cannot exceed 255 characters")

		# Validate parent_id if provided
		parent_id = data.get("parent_id")
		if parent_id is not None:
			try:
				int(parent_id)
			except (ValueError, TypeError):
				errors.append("parent_id must be an integer")

		return {"is_valid": len(errors) == 0, "errors": errors}

	@classmethod
	def validate_for_erpnext(cls, data: dict[str, Any]) -> dict[str, Any]:
		"""
		Validate category data for Salla Category DocType.

		Args:
		    data: Category data dict

		Returns:
		    Dict with is_valid and errors
		"""
		errors = []

		for field_name in cls.REQUIRED_FOR_ERPNEXT:
			value = data.get(field_name)
			if not value:
				errors.append(f"Missing required field: {field_name}")

		return {"is_valid": len(errors) == 0, "errors": errors}

	@classmethod
	def get_salla_api_fields(cls) -> list[str]:
		"""Get list of fields accepted by Salla API."""
		return [
			"name",
			"parent_id",
			"image",
			"status",
		]

	@classmethod
	def sanitize_for_salla(cls, data: dict[str, Any]) -> dict[str, Any]:
		"""
		Sanitize category data for Salla API.

		Args:
		    data: Raw category data

		Returns:
		    Sanitized data dict
		"""
		allowed_fields = cls.get_salla_api_fields()
		return {k: v for k, v in data.items() if k in allowed_fields and v is not None}
