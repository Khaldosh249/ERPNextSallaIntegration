"""
Base synchronization manager class.
Provides common functionality for all entity sync managers.
"""

import frappe
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from salla_integration.core.client import SallaClient
from salla_integration.core.utils.logger import log_sync_operation, SyncLogger


class BaseSyncManager(ABC):
    """
    Abstract base class for synchronization managers.
    Provides common methods and enforces interface for sync operations.
    """
    
    # Override in subclasses
    entity_type: str = "Unknown"
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self) -> SallaClient:
        """Lazy-load the Salla client."""
        if self._client is None:
            self._client = SallaClient()
        return self._client
    
    @abstractmethod
    def sync_to_salla(self, doc) -> Dict[str, Any]:
        """
        Sync a document to Salla.
        
        Args:
            doc: The Frappe document to sync
            
        Returns:
            Result dict with status and details
        """
        pass
    
    @abstractmethod
    def sync_from_salla(self, salla_data: Dict) -> Dict[str, Any]:
        """
        Sync data from Salla to ERPNext.
        
        Args:
            salla_data: Data from Salla API or webhook
            
        Returns:
            Result dict with status and details
        """
        pass
    
    @abstractmethod
    def build_payload(self, doc) -> Dict[str, Any]:
        """
        Build the API payload for a document.
        
        Args:
            doc: The Frappe document
            
        Returns:
            Dict payload for Salla API
        """
        pass
    
    def handle_sync_success(
        self,
        operation: str,
        reference_doctype: str,
        reference_name: str,
        salla_id: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Log a successful sync operation."""
        log_sync_operation(
            entity_type=self.entity_type,
            operation=operation,
            status="Success",
            reference_doctype=reference_doctype,
            reference_name=reference_name,
            salla_id=salla_id,
            details=details
        )
    
    def handle_sync_error(
        self,
        operation: str,
        reference_doctype: str,
        reference_name: str,
        error: Exception,
        salla_id: Optional[str] = None
    ):
        """Log a failed sync operation."""
        log_sync_operation(
            entity_type=self.entity_type,
            operation=operation,
            status="Failed",
            reference_doctype=reference_doctype,
            reference_name=reference_name,
            salla_id=salla_id,
            error_message=str(error)
        )
    
    def get_sync_logger(
        self,
        operation: str,
        reference_doctype: Optional[str] = None,
        reference_name: Optional[str] = None
    ) -> SyncLogger:
        """Get a sync logger context manager."""
        return SyncLogger(
            entity_type=self.entity_type,
            operation=operation,
            reference_doctype=reference_doctype,
            reference_name=reference_name
        )
    
    def validate_before_sync(self, doc) -> Dict[str, Any]:
        """
        Validate a document before syncing.
        Override in subclasses for entity-specific validation.
        
        Args:
            doc: The document to validate
            
        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        return {"valid": True, "errors": []}
    
    def should_sync(self, doc) -> bool:
        """
        Determine if a document should be synced.
        Override in subclasses for entity-specific logic.
        
        Args:
            doc: The document to check
            
        Returns:
            True if document should be synced
        """
        return True
