"""
Simplified logging configuration for ClustR application.
"""

import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings


class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs log records as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
            }
        
        # Add extra fields
        for attr in ['request_id', 'user_id', 'cluster_id', 'duration']:
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)
        
        return json.dumps(log_data)


class RequestAdapter(logging.LoggerAdapter):
    """Logger adapter that adds request information to log records."""
    
    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple:
        extra = kwargs.get('extra', {})
        
        if hasattr(self, 'request'):
            extra.update({
                'request_id': getattr(self.request, 'id', None),
                'user_id': getattr(self.request.user, 'id', None) if hasattr(self.request, 'user') else None,
                'path': self.request.path,
                'method': self.request.method,
            })
        
        kwargs['extra'] = extra
        return msg, kwargs


def get_request_logger(request) -> logging.Logger:
    """Get a logger with request context."""
    logger = logging.getLogger('clustr')
    adapter = RequestAdapter(logger)
    adapter.request = request
    return adapter


def configure_logging():
    """Configure logging for the application."""
    # Create logs directory
    logs_dir = Path(settings.BASE_DIR) / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Configure main app logger
    app_logger = logging.getLogger('clustr')
    app_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    app_logger.propagate = False
    
    # Create formatters
    verbose_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter('%(levelname)s %(message)s')
    json_formatter = JsonFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(verbose_formatter if settings.DEBUG else simple_formatter)
    
    # App file handler
    app_file_handler = RotatingFileHandler(
        logs_dir / 'app.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    app_file_handler.setLevel(logging.INFO)
    app_file_handler.setFormatter(verbose_formatter)
    
    # Error file handler
    error_file_handler = RotatingFileHandler(
        logs_dir / 'error.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(verbose_formatter)
    
    # JSON structured logging handler
    json_file_handler = RotatingFileHandler(
        logs_dir / 'structured.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    json_file_handler.setLevel(logging.INFO)
    json_file_handler.setFormatter(json_formatter)
    
    # Add handlers to app logger
    app_logger.addHandler(console_handler)
    app_logger.addHandler(app_file_handler)
    app_logger.addHandler(error_file_handler)
    app_logger.addHandler(json_file_handler)
    
    # Configure Django loggers
    django_loggers = [
        ('django', logging.INFO),
        ('django.request', logging.ERROR),
        ('django.db.backends', logging.WARNING),
        ('rest_framework', logging.WARNING),
    ]
    
    for logger_name, level in django_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.addHandler(console_handler)
        if level >= logging.ERROR:
            logger.addHandler(error_file_handler)
        else:
            logger.addHandler(app_file_handler)
    
    # Configure audit logger
    audit_logger = logging.getLogger('clustr.audit')
    audit_logger.setLevel(logging.INFO)
    audit_logger.addHandler(json_file_handler)
    audit_logger.propagate = False


def log_audit(
    event_type: str,
    user_id: Optional[str] = None,
    cluster_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None
) -> None:
    """Log an audit event."""
    logger = logging.getLogger('clustr.audit')
    
    extra = {
        'event_type': event_type,
        'user_id': user_id,
        'cluster_id': cluster_id,
        'resource_type': resource_type,
        'resource_id': resource_id,
    }
    
    if details:
        extra.update(details)
    
    logger.info(f"AUDIT: {event_type}", extra=extra)


def log_performance(
    operation: str,
    duration: float,
    success: bool = True,
    details: Optional[dict[str, Any]] = None
) -> None:
    """Log a performance metric."""
    logger = logging.getLogger('clustr')
    
    extra = {
        'operation': operation,
        'duration': duration,
        'success': success,
    }
    
    if details:
        extra.update(details)
    
    logger.info(f"PERF: {operation} took {duration:.3f}s", extra=extra)