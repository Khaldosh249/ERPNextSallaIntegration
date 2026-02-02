"""
Centralized logging utilities for Salla Integration.
"""

from enum import Enum
from typing import Any, Optional

import frappe


class SyncStatus(Enum):
	"""Sync operation status."""

	SUCCESS = "Success"
	FAILED = "Failed"
	PENDING = "Pending"
	SKIPPED = "Skipped"


class EntityType(Enum):
	"""Entity types for sync operations."""

	PRODUCT = "Product"
	CATEGORY = "Category"
	CUSTOMER = "Customer"
	ORDER = "Order"
	STOCK = "Stock"


class OperationType(Enum):
	"""Operation types for sync."""

	CREATE = "Create"
	UPDATE = "Update"
	DELETE = "Delete"
	SYNC_TO_SALLA = "Sync to Salla"
	SYNC_FROM_SALLA = "Sync from Salla"


def log_sync_operation(
	entity_type: str,
	operation: str,
	status: str,
	details: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	salla_id: str | None = None,
	error_message: str | None = None,
):
	"""
	Log a synchronization operation to Salla Sync Log.

	Args:
	    entity_type: Type of entity (Product, Category, etc.)
	    operation: Operation performed (Create, Update, etc.)
	    status: Status of operation (Success, Failed, etc.)
	    details: Additional details about the operation
	    reference_doctype: Related ERPNext doctype
	    reference_name: Related ERPNext document name
	    salla_id: Related Salla ID
	    error_message: Error message if operation failed
	"""
	try:
		log_doc = frappe.get_doc(
			{
				"doctype": "Salla Sync Log",
				"entity_type": entity_type,
				"operation": operation,
				"status": status,
				"details": details,
				"reference_doctype": reference_doctype,
				"reference_name": reference_name,
				"salla_id": salla_id,
				"error_message": error_message,
			}
		)
		log_doc.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		# Don't let logging errors break the main flow
		frappe.log_error(f"Failed to create sync log: {e!s}", "Salla Sync Log Error")


class SyncLogger:
	"""
	Context manager for logging sync operations.
	Automatically handles success/failure logging.

	Usage:
	    with SyncLogger("Product", "Update", item_code="ITEM-001") as logger:
	        # Perform sync operation
	        logger.set_salla_id("12345")
	"""

	def __init__(
		self,
		entity_type: str,
		operation: str,
		reference_doctype: str | None = None,
		reference_name: str | None = None,
		**kwargs,
	):
		self.entity_type = entity_type
		self.operation = operation
		self.reference_doctype = reference_doctype
		self.reference_name = reference_name
		self.salla_id = None
		self.details = None
		self.extra_data = kwargs

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		if exc_type is None:
			# Success
			log_sync_operation(
				entity_type=self.entity_type,
				operation=self.operation,
				status=SyncStatus.SUCCESS.value,
				details=self.details,
				reference_doctype=self.reference_doctype,
				reference_name=self.reference_name,
				salla_id=self.salla_id,
			)
		else:
			# Failure
			log_sync_operation(
				entity_type=self.entity_type,
				operation=self.operation,
				status=SyncStatus.FAILED.value,
				details=self.details,
				reference_doctype=self.reference_doctype,
				reference_name=self.reference_name,
				salla_id=self.salla_id,
				error_message=str(exc_val),
			)

		# Don't suppress exceptions
		return False

	def set_salla_id(self, salla_id: str):
		"""Set the Salla ID for the log."""
		self.salla_id = salla_id

	def set_details(self, details: str):
		"""Set additional details for the log."""
		self.details = details


def log_error(message: str, title: str = "Salla Integration Error"):
	"""Log an error message."""
	frappe.log_error(message, title)


def log_info(message: str, title: str = "Salla Integration"):
	"""Log an info message (uses error log for persistence)."""
	frappe.log_error(message, title)
