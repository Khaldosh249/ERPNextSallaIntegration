"""
Custom exceptions for Salla API errors.
Provides specific exception types for different error scenarios.
"""


class SallaAPIError(Exception):
	"""Base exception for all Salla API errors."""

	def __init__(self, message: str, status_code: int | None = None, response_data: dict | None = None):
		self.message = message
		self.status_code = status_code
		self.response_data = response_data or {}
		super().__init__(self.message)

	def __str__(self):
		if self.status_code:
			return f"[{self.status_code}] {self.message}"
		return self.message


class SallaAuthenticationError(SallaAPIError):
	"""Raised when OAuth or token authentication fails."""

	def __init__(self, message: str = "Authentication failed", **kwargs):
		super().__init__(message, **kwargs)


class SallaRateLimitError(SallaAPIError):
	"""Raised when API rate limit is exceeded."""

	def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None, **kwargs):
		self.retry_after = retry_after
		super().__init__(message, **kwargs)


class SallaValidationError(SallaAPIError):
	"""Raised when invalid data is sent to Salla API."""

	def __init__(self, message: str = "Validation error", errors: dict | None = None, **kwargs):
		self.errors = errors or {}
		super().__init__(message, **kwargs)


class SallaNotFoundError(SallaAPIError):
	"""Raised when a requested resource is not found in Salla."""

	def __init__(
		self,
		message: str = "Resource not found",
		resource_type: str | None = None,
		resource_id: str | None = None,
		**kwargs,
	):
		self.resource_type = resource_type
		self.resource_id = resource_id
		super().__init__(message, **kwargs)


class SallaConnectionError(SallaAPIError):
	"""Raised when connection to Salla API fails."""

	def __init__(self, message: str = "Connection to Salla API failed", **kwargs):
		super().__init__(message, **kwargs)


class SallaTimeoutError(SallaAPIError):
	"""Raised when request to Salla API times out."""

	def __init__(self, message: str = "Request timed out", **kwargs):
		super().__init__(message, **kwargs)
