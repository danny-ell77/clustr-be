"""
Example of using method_decorator for audit logging in Django views and viewsets.
"""

from django.utils.decorators import method_decorator
from rest_framework import viewsets, generics
from rest_framework.response import Response

from core.common.error_utils import audit_log
from core.common.decorators import audit_viewset


# Example 1: Using method_decorator directly on view methods
class ProductView(generics.ListCreateAPIView):
    """
    Example view using method_decorator for audit logging.
    """

    @method_decorator(audit_log(event_type="product.list", resource_type="product"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(audit_log(event_type="product.create", resource_type="product"))
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


# Example 2: Using the audit_viewset decorator for ModelViewSet
@audit_viewset("product")
class ProductViewSet(viewsets.ModelViewSet):
    """
    Example viewset using the audit_viewset decorator.

    This automatically adds audit logging to all standard viewset methods:
    - list: product.list
    - retrieve: product.view
    - create: product.create
    - update: product.update
    - partial_update: product.update
    - destroy: product.delete
    """

    # Your viewset implementation here
    pass


# Example 3: Using method_decorator for custom viewset actions
class OrderViewSet(viewsets.ModelViewSet):
    """
    Example viewset with custom actions using method_decorator.
    """

    @method_decorator(audit_log(event_type="order.fulfill", resource_type="order"))
    def fulfill(self, request, *args, **kwargs):
        """Custom action to fulfill an order"""
        # Implementation here
        return Response({"status": "fulfilled"})

    @method_decorator(audit_log(event_type="order.cancel", resource_type="order"))
    def cancel(self, request, *args, **kwargs):
        """Custom action to cancel an order"""
        # Implementation here
        return Response({"status": "cancelled"})


# Example 4: Using method_decorator for class-based views
class PaymentView(generics.CreateAPIView):
    """
    Example view for creating payments.
    """

    @method_decorator(
        audit_log(
            event_type="payment.process",
            resource_type="payment",
            get_resource_id=lambda *args, **kwargs: kwargs.get("payment_id"),
        )
    )
    def post(self, request, *args, **kwargs):
        # Process payment implementation
        return Response({"status": "payment processed"})
