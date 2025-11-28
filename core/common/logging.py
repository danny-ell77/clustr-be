"""
Minimal logging for ClustR.
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings


def get_logger(name='clustr'):
    """Get a logger instance."""
    return logging.getLogger(name)


logger = get_logger()


def log_audit(
    event_type: str,
    user_id: Optional[str] = None,
    cluster_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Log audit event (only in DEBUG mode for performance)."""
    if not settings.DEBUG:
        return
    
    logger.debug(
        f"AUDIT: {event_type} user={user_id} cluster={cluster_id} resource={resource_type}:{resource_id}"
    )


def log_performance(
    operation: str,
    duration: float,
    success: bool,
    details: Optional[Dict[str, Any]] = None
):
    """Log performance metrics (only slow operations in production)."""
    if not settings.DEBUG and duration < 1.0:
        return
    
    status = 'OK' if success else 'FAIL'
    logger.debug(f"PERF: {operation} {duration:.3f}s {status}")


def log_error(
    message: str,
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None
):
    """Log error with context."""
    if exception:
        logger.error(f"{message}: {str(exception)}", exc_info=settings.DEBUG)
    else:
        logger.error(message)