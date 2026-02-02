"""
Base payload builder class.
Provides common functionality for building API payloads.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BasePayloadBuilder(ABC):
	"""
	Abstract base class for payload builders.
	Uses the builder pattern to construct API payloads.
	"""

	def __init__(self, doc):
		"""
		Initialize the payload builder.

		Args:
		    doc: The Frappe document to build payload from
		"""
		self.doc = doc
		self.payload = {}

	@abstractmethod
	def build(self) -> dict[str, Any]:
		"""
		Build and return the final payload.

		Returns:
		    The constructed payload dict
		"""
		pass

	def reset(self):
		"""Reset the payload to empty state."""
		self.payload = {}
		return self

	def add_field(self, key: str, value: Any) -> "BasePayloadBuilder":
		"""
		Add a field to the payload.

		Args:
		    key: The field key
		    value: The field value

		Returns:
		    self for chaining
		"""
		if value is not None:
			self.payload[key] = value
		return self

	def add_field_if(self, condition: bool, key: str, value: Any) -> "BasePayloadBuilder":
		"""
		Add a field to the payload if condition is true.

		Args:
		    condition: Whether to add the field
		    key: The field key
		    value: The field value

		Returns:
		    self for chaining
		"""
		if condition and value is not None:
			self.payload[key] = value
		return self

	def add_fields(self, fields: dict[str, Any]) -> "BasePayloadBuilder":
		"""
		Add multiple fields to the payload.

		Args:
		    fields: Dict of fields to add

		Returns:
		    self for chaining
		"""
		for key, value in fields.items():
			if value is not None:
				self.payload[key] = value
		return self

	def get_payload(self) -> dict[str, Any]:
		"""Get the current payload without building."""
		return self.payload.copy()
