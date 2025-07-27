"""
Decorators for ClustR application.
"""

from typing import Callable, Optional

from django.utils.decorators import method_decorator

from core.common.error_utils import audit_log

import time
from typing import Optional, Dict, List, Any, Tuple
from django.conf import settings
from core.common.logging import log_audit, log_performance


def get_pk_from_kwargs(**kwargs) -> Optional[str]:
    """
    Extract primary key from URL kwargs.
    Common patterns: pk, id, user_id, etc.
    """
    for key in ['pk', 'id']:
        if key in kwargs:
            return str(kwargs[key])
    
    # Look for any key ending with '_id'
    for key, value in kwargs.items():
        if key.endswith('_id'):
            return str(value)
    
    return None

def _extract_nested_attribute(obj: Any, attribute_path: str, max_depth: int = 5) -> Any:
    """
    Extract a nested attribute from an object using dot notation.
    
    This function safely extracts attributes up to a specified depth,
    handling cases where intermediate attributes don't exist.
    
    Args:
        obj: The object to extract the attribute from
        attribute_path: Dot-separated path to the attribute (e.g., 'user.profile.name')
        max_depth: Maximum depth to traverse (default: 5)
        
    Returns:
        The extracted attribute value or None if not found/accessible
    """
    if not attribute_path or max_depth <= 0:
        return None
        
    try:
        path_components = attribute_path.split('.')
        
        if len(path_components) > max_depth:
            path_components = path_components[:max_depth]
        
        current_object = obj
        
        for component in path_components:
            if current_object is None:
                return None
                
            # Handle dictionary-like access
            if hasattr(current_object, '__getitem__') and not isinstance(current_object, str):
                try:
                    current_object = current_object[component]
                    continue
                except (KeyError, TypeError, IndexError):
                    pass
            
            # Handle attribute access
            if hasattr(current_object, component):
                current_object = getattr(current_object, component)
            else:
                return None
        
        return current_object
        
    except (AttributeError, TypeError, KeyError, IndexError):
        return None





class audit_viewset:
    """
    Class decorator to add comprehensive audit logging to all viewset actions.
    
    This decorator automatically logs all viewset actions including custom actions,
    with support for ignoring specific URL names and logging custom attributes
    from request and response objects.

    Usage:
    ```python
    @audit_viewset(
        resource_type='user',
        ignore=['user-list', 'user-detail'],
        log_attributes={
            'request': ['user.id', 'data.name', 'META.HTTP_USER_AGENT'],
            'response': ['data.id', 'data.email', 'status_code']
        }
    )
    class UserViewSet(ModelViewSet):
        queryset = User.objects.all()
        serializer_class = UserSerializer
    ```
    
    Args:
        resource_type: The type of resource being audited (e.g., 'user')
        ignore: List of URL names to ignore for audit logging (e.g., ['user-list'])
        log_attributes: Dictionary specifying custom attributes to log from request/response
                       Format: {'request': ['attr1', 'attr2'], 'response': ['attr3']}
    """
    
    def __init__(
        self,
        resource_type: str,
        ignore: Optional[List[str]] = None,
        log_attributes: Optional[Dict[str, List[str]]] = None
    ):
        """
        Initialize the audit viewset decorator with configuration parameters.
        
        Args:
            resource_type: The type of resource being audited (e.g., 'user')
            ignore: List of URL names to ignore for audit logging
            log_attributes: Dictionary specifying custom attributes to log
        """
        self.resource_type = resource_type
        self.ignore = ignore or []
        self.log_attributes = log_attributes or {}

    def _extract_custom_attributes(self, source_object: Any, attribute_list: List[str], source_type: str) -> Dict[str, Any]:
        """
        Extract custom attributes from a source object (request or response).
        
        This method processes a list of attribute paths and extracts their values
        from the source object, handling nested attributes and missing values gracefully.
        
        Args:
            source_object: The object to extract attributes from (request/response)
            attribute_list: List of attribute paths to extract
            source_type: Type of source ('request' or 'response') for logging context
            
        Returns:
            Dictionary containing extracted attributes with their values
        """
        extracted_attributes = {}
        
        if not attribute_list or not source_object:
            return extracted_attributes
        
        for attribute_path in attribute_list:
            try:
                # Extract the attribute value using nested extraction
                attribute_value = _extract_nested_attribute(
                    source_object, 
                    attribute_path, 
                    max_depth=5
                )
                
                # Only include the attribute if it has a meaningful value
                if attribute_value is not None:
                    # Create a safe key name for logging
                    safe_key = f"{source_type}_{attribute_path.replace('.', '_')}"
                    extracted_attributes[safe_key] = attribute_value
                    
            except Exception as extraction_error:
                # In development, we want to know about extraction issues
                if settings.DEBUG:
                    raise extraction_error
                # In production, silently continue without this attribute
                continue
        
        return extracted_attributes

    def _determine_event_type_and_resource_id(self, request, action_name: str) -> Tuple[str, Optional[str]]:
        """
        Determine the appropriate event type and resource ID for the current action.
        
        This method maps viewset actions to their corresponding audit event types
        and determines whether a resource ID should be extracted.
        
        Args:
            request: The Django request object
            action_name: The name of the action being performed
            
        Returns:
            Tuple of (event_type, resource_id) where resource_id may be None
        """
        # Standard DRF viewset action mappings
        standard_action_mappings = {
            'list': 'list',
            'retrieve': 'view', 
            'create': 'create',
            'update': 'update',
            'partial_update': 'update',
            'destroy': 'delete',
        }
        
        # Determine the event type
        if action_name in standard_action_mappings:
            event_type = f"{self.resource_type}.{standard_action_mappings[action_name]}"
        else:
            # For custom actions, use the action name directly
            event_type = f"{self.resource_type}.{action_name}"
        
        # Determine resource ID extraction
        resource_id = None
        
        # Actions that typically don't have a specific resource ID
        actions_without_resource_id = ['list', 'create']
        
        if action_name not in actions_without_resource_id:
            try:
                # Try to extract resource ID from URL kwargs
                resource_id = get_pk_from_kwargs(**request.resolver_match.kwargs)
            except (AttributeError, TypeError):
                # Gracefully handle missing resolver match or kwargs
                pass
        
        return event_type, resource_id

    def _should_ignore_request(self, request) -> bool:
        """
        Determine whether the current request should be ignored for audit logging.
        
        This method checks if the current request's URL name is in the ignore list.
        
        Args:
            request: The Django request object
            
        Returns:
            Boolean indicating whether to ignore this request
        """
        if not self.ignore:
            return False
            
        try:
            # Get the URL name from the request's resolver match
            url_name = request.resolver_match.url_name
            
            # Check if this URL name should be ignored
            return url_name in self.ignore
            
        except (AttributeError, TypeError):
            # If we can't determine the URL name, don't ignore by default
            return False

    def _get_user_and_cluster_info(self, request) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract user and cluster information from the request.
        
        Args:
            request: The Django request object
            
        Returns:
            Tuple of (user_id, cluster_id)
        """
        user_id = None
        cluster_id = None
        
        try:
            # Extract user ID if user is authenticated
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = str(request.user.id)
            
            # Extract cluster ID if available in request
            if hasattr(request, 'cluster_id'):
                cluster_id = str(request.cluster_id)
            elif hasattr(request, 'cluster') and hasattr(request.cluster, 'id'):
                cluster_id = str(request.cluster.id)
                
        except (AttributeError, TypeError):
            # Gracefully handle missing attributes
            pass
        
        return user_id, cluster_id

    def __call__(self, viewset_class):
        """
        The main decorator method that wraps the viewset class with audit logging.
        
        This method is called when the decorator is applied to a viewset class.
        It replaces the viewset's dispatch method with an enhanced version that
        includes comprehensive audit logging and performance tracking.
        
        Args:
            viewset_class: The viewset class to be decorated
            
        Returns:
            The decorated viewset class with audit logging capabilities
        """
        # Store reference to the original dispatch method
        original_dispatch = viewset_class.dispatch
        
        # Create a reference to self for use in the nested function
        decorator_instance = self
        
        def enhanced_dispatch_with_audit_logging(viewset_instance, request, *args, **kwargs):
            """
            Enhanced dispatch method that wraps the original dispatch with comprehensive audit logging.
            
            This method intercepts all requests to the viewset, performs audit logging
            before and after the action execution, and includes performance tracking.
            
            Args:
                viewset_instance: The viewset instance
                request: The Django request object
                *args: Positional arguments passed to the original dispatch
                **kwargs: Keyword arguments passed to the original dispatch
                
            Returns:
                The response from the original dispatch method
            """
            # Record the start time for performance tracking
            start_time = time.time()
            
            try:
                # Check if this request should be ignored for audit logging
                if decorator_instance._should_ignore_request(request):
                    # Skip audit logging and call original dispatch directly
                    return original_dispatch(viewset_instance, request, *args, **kwargs)
                
                # Determine the action being performed
                action_name = getattr(viewset_instance, 'action', 'unknown')
                
                # Determine event type and resource ID for this action
                event_type, resource_id = decorator_instance._determine_event_type_and_resource_id(request, action_name)
                
                # Extract user and cluster information from the request
                user_id, cluster_id = decorator_instance._get_user_and_cluster_info(request)
                
                # Extract custom attributes from the request
                request_attributes = decorator_instance._extract_custom_attributes(
                    request, 
                    decorator_instance.log_attributes.get('request', []), 
                    'request'
                )
                
                # Prepare initial audit details
                audit_details = {
                    'action': action_name,
                    'method': request.method,
                    'path': request.path,
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT'),
                    **request_attributes
                }
                
                # Log the audit event before action execution
                log_audit(
                    event_type=f"{event_type}.started",
                    user_id=user_id,
                    cluster_id=cluster_id,
                    resource_type=decorator_instance.resource_type,
                    resource_id=resource_id,
                    details=audit_details
                )
                
                # Execute the original dispatch method
                response = original_dispatch(viewset_instance, request, *args, **kwargs)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Extract custom attributes from the response
                response_attributes = decorator_instance._extract_custom_attributes(
                    response,
                    decorator_instance.log_attributes.get('response', []),
                    'response'
                )
                
                # Update audit details with response information
                audit_details.update({
                    'status_code': getattr(response, 'status_code', None),
                    'execution_time': execution_time,
                    **response_attributes
                })
                
                # Log the successful completion of the action
                log_audit(
                    event_type=f"{event_type}.completed",
                    user_id=user_id,
                    cluster_id=cluster_id,
                    resource_type=decorator_instance.resource_type,
                    resource_id=resource_id,
                    details=audit_details
                )
                
                # Log performance metrics for successful request
                log_performance(
                    operation=f"{decorator_instance.resource_type}.{action_name}",
                    duration=execution_time,
                    success=True,
                    details={
                        'resource_type': decorator_instance.resource_type,
                        'action': action_name,
                        'status_code': getattr(response, 'status_code', None),
                        'user_id': user_id,
                        'cluster_id': cluster_id
                    }
                )
                
                return response
                
            except Exception as error:
                # Calculate execution time even for failed requests
                execution_time = time.time() - start_time
                
                # Get action information for error logging
                action_name = getattr(viewset_instance, 'action', 'unknown')
                event_type, resource_id = decorator_instance._determine_event_type_and_resource_id(request, action_name)
                user_id, cluster_id = decorator_instance._get_user_and_cluster_info(request)
                
                # Prepare error details
                error_details = {
                    'action': action_name,
                    'method': request.method,
                    'path': request.path,
                    'error_type': type(error).__name__,
                    'error_message': str(error),
                    'execution_time': execution_time
                }
                
                # Log the failed action
                log_audit(
                    event_type=f"{event_type}.failed",
                    user_id=user_id,
                    cluster_id=cluster_id,
                    resource_type=decorator_instance.resource_type,
                    resource_id=resource_id,
                    details=error_details
                )
                
                # Log performance metrics for failed request
                log_performance(
                    operation=f"{decorator_instance.resource_type}.{action_name}",
                    duration=execution_time,
                    success=False,
                    details={
                        'resource_type': decorator_instance.resource_type,
                        'action': action_name,
                        'error_type': type(error).__name__,
                        'error_message': str(error),
                        'user_id': user_id,
                        'cluster_id': cluster_id
                    }
                )
                
                raise error
        
        # Replace the viewset's dispatch method with our enhanced version
        viewset_class.dispatch = enhanced_dispatch_with_audit_logging
        
        return viewset_class