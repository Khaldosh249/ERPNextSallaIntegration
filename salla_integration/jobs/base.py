"""
Base job class for background processing.
Provides common functionality for all sync jobs.
"""

import frappe
from typing import Dict, Any, Optional, Callable
from functools import wraps


class BaseJob:
    """
    Base class for background sync jobs.
    Provides common job handling, logging, and error management.
    """
    
    job_type = "Generic"
    
    def __init__(self, job_name: Optional[str] = None):
        """
        Initialize the job.
        
        Args:
            job_name: Optional custom job name
        """
        self.job_name = job_name or f"salla_{self.job_type.lower()}_job"
        self.start_time = None
        self.end_time = None
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the job. Override in subclasses.
        
        Returns:
            Result dict with status and details
        """
        raise NotImplementedError("Subclasses must implement run()")
    
    def enqueue(
        self,
        queue: str = "default",
        timeout: int = 3600,
        **kwargs
    ) -> str:
        """
        Enqueue the job for background processing.
        
        Args:
            queue: The queue to use (short, default, long)
            timeout: Job timeout in seconds
            **kwargs: Arguments to pass to run()
            
        Returns:
            Job ID
        """
        from frappe.utils.background_jobs import enqueue
        
        job = enqueue(
            method=self._execute_job,
            queue=queue,
            timeout=timeout,
            job_name=self.job_name,
            **kwargs
        )
        
        return job.id if job else None
    
    def _execute_job(self, **kwargs):
        """Internal job executor with error handling."""
        import datetime
        
        self.start_time = datetime.datetime.now()
        
        try:
            result = self.run(**kwargs)
            self._log_job_completion(result)
            return result
            
        except Exception as e:
            self._log_job_error(e)
            raise
            
        finally:
            self.end_time = datetime.datetime.now()
    
    def _log_job_completion(self, result: Dict[str, Any]):
        """Log successful job completion."""
        frappe.get_doc({
            "doctype": "Salla Sync Log",
            "sync_type": self.job_type,
            "status": result.get("status", "unknown"),
            "message": result.get("message", "Job completed"),
            "details": frappe.as_json(result)
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    
    def _log_job_error(self, error: Exception):
        """Log job error."""
        frappe.get_doc({
            "doctype": "Salla Sync Log",
            "sync_type": self.job_type,
            "status": "error",
            "message": f"Job failed: {str(error)}",
            "details": frappe.get_traceback()
        }).insert(ignore_permissions=True)
        frappe.db.commit()


def job_handler(job_type: str = "Sync", queue: str = "default", timeout: int = 3600):
    """
    Decorator to turn a function into a job handler with automatic logging.
    
    Args:
        job_type: Type of job for logging
        queue: Default queue
        timeout: Default timeout
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import datetime
            
            start_time = datetime.datetime.now()
            job_name = f"salla_{job_type.lower()}_{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                
                # Log success
                frappe.get_doc({
                    "doctype": "Salla Sync Log",
                    "sync_type": job_type,
                    "status": result.get("status", "success") if isinstance(result, dict) else "success",
                    "message": f"{job_type} job completed",
                    "details": frappe.as_json(result) if result else None
                }).insert(ignore_permissions=True)
                frappe.db.commit()
                
                return result
                
            except Exception as e:
                # Log error
                frappe.get_doc({
                    "doctype": "Salla Sync Log",
                    "sync_type": job_type,
                    "status": "error",
                    "message": f"{job_type} job failed: {str(e)}",
                    "details": frappe.get_traceback()
                }).insert(ignore_permissions=True)
                frappe.db.commit()
                
                raise
        
        # Add enqueue method to the wrapper
        def enqueue_wrapper(*args, _queue=queue, _timeout=timeout, **kwargs):
            return frappe.enqueue(
                method=wrapper,
                queue=_queue,
                timeout=_timeout,
                job_name=f"salla_{job_type.lower()}_{func.__name__}",
                *args,
                **kwargs
            )
        
        wrapper.enqueue = enqueue_wrapper
        return wrapper
    
    return decorator
