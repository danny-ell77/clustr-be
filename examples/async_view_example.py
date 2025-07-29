"""
Example async views demonstrating request context handling.

This module shows different approaches to handle request context in async views.
"""

import asyncio
from typing import Any, Dict

from django.http import HttpRequest, JsonResponse
from django.views import View
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from core.common.async_utils import (
    async_with_request_context,
    get_async_current_request,
    get_async_current_user_id,
    get_async_current_cluster_id,
    run_async_in_request_context,
)
from core.common.error_utils import log_exception


# Example 1: Simple async view with context variables
async def simple_async_view(request: HttpRequest) -> JsonResponse:
    """
    Simple async view that uses context variables.

    This approach works when the async middleware is properly configured.
    """
    try:
        # Get current request context
        current_request = get_async_current_request()
        user_id = get_async_current_user_id()
        cluster_id = get_async_current_cluster_id()

        # Simulate some async work
        await asyncio.sleep(0.1)

        return JsonResponse(
            {
                "message": "Async view with context variables",
                "request_id": getattr(current_request, "id", None),
                "user_id": user_id,
                "cluster_id": cluster_id,
            }
        )
    except Exception as exc:
        log_exception(exc)
        return JsonResponse({"error": str(exc)}, status=500)


# Example 2: Async view with explicit context management
async def async_view_with_context(request: HttpRequest) -> JsonResponse:
    """
    Async view that explicitly manages request context.

    This approach is more reliable when context might be lost.
    """

    async def process_data() -> dict[str, Any]:
        # This function will have access to the request context
        current_request = get_async_current_request()
        user_id = get_async_current_user_id()
        cluster_id = get_async_current_cluster_id()

        # Simulate async work
        await asyncio.sleep(0.1)

        return {
            "request_id": getattr(current_request, "id", None),
            "user_id": user_id,
            "cluster_id": cluster_id,
            "data": "Processed with explicit context",
        }

    try:
        # Run the async function with request context
        result = await run_async_in_request_context(process_data, request)

        return JsonResponse(
            {"message": "Async view with explicit context management", **result}
        )
    except Exception as exc:
        log_exception(exc)
        return JsonResponse({"error": str(exc)}, status=500)


# Example 3: Async view using context manager
async def async_view_with_context_manager(request: HttpRequest) -> JsonResponse:
    """
    Async view using context manager for request context.

    This approach gives you fine-grained control over context.
    """
    try:
        async with async_with_request_context(request):
            # All code in this block has access to the request context
            current_request = get_async_current_request()
            user_id = get_async_current_user_id()
            cluster_id = get_async_current_cluster_id()

            # Simulate async work
            await asyncio.sleep(0.1)

            return JsonResponse(
                {
                    "message": "Async view with context manager",
                    "request_id": getattr(current_request, "id", None),
                    "user_id": user_id,
                    "cluster_id": cluster_id,
                }
            )
    except Exception as exc:
        log_exception(exc)
        return JsonResponse({"error": str(exc)}, status=500)


# Example 4: DRF async view
@api_view(["GET"])
async def drf_async_view(request: Request) -> Response:
    """
    DRF async view with request context.

    This shows how to handle request context in DRF async views.
    """
    try:
        # Get current context
        current_request = get_async_current_request()
        user_id = get_async_current_user_id()
        cluster_id = get_async_current_cluster_id()

        # Simulate async work
        await asyncio.sleep(0.1)

        return Response(
            {
                "message": "DRF async view with context",
                "request_id": getattr(current_request, "id", None),
                "user_id": user_id,
                "cluster_id": cluster_id,
            }
        )
    except Exception as exc:
        log_exception(exc)
        return Response({"error": str(exc)}, status=500)


# Example 5: Class-based async view
class AsyncClassView(View):
    """
    Class-based async view with request context.
    """

    async def get(self, request: HttpRequest) -> JsonResponse:
        """
        Handle GET requests asynchronously.
        """
        try:
            # Get current context
            current_request = get_async_current_request()
            user_id = get_async_current_user_id()
            cluster_id = get_async_current_cluster_id()

            # Simulate async work
            await asyncio.sleep(0.1)

            return JsonResponse(
                {
                    "message": "Class-based async view",
                    "request_id": getattr(current_request, "id", None),
                    "user_id": user_id,
                    "cluster_id": cluster_id,
                }
            )
        except Exception as exc:
            log_exception(exc)
            return JsonResponse({"error": str(exc)}, status=500)

    async def post(self, request: HttpRequest) -> JsonResponse:
        """
        Handle POST requests asynchronously.
        """
        try:
            # Get current context
            current_request = get_async_current_request()
            user_id = get_async_current_user_id()
            cluster_id = get_async_current_cluster_id()

            # Process request data
            data = request.POST.dict()

            # Simulate async work
            await asyncio.sleep(0.1)

            return JsonResponse(
                {
                    "message": "POST processed asynchronously",
                    "request_id": getattr(current_request, "id", None),
                    "user_id": user_id,
                    "cluster_id": cluster_id,
                    "data": data,
                }
            )
        except Exception as exc:
            log_exception(exc)
            return JsonResponse({"error": str(exc)}, status=500)


# Example 6: Background task with request context
async def background_task_with_context(request: HttpRequest) -> JsonResponse:
    """
    Example of running background tasks with request context.
    """

    async def background_work() -> dict[str, Any]:
        # This function runs in the background but still has access to request context
        current_request = get_async_current_request()
        user_id = get_async_current_user_id()
        cluster_id = get_async_current_cluster_id()

        # Simulate long-running background work
        await asyncio.sleep(2.0)

        return {
            "request_id": getattr(current_request, "id", None),
            "user_id": user_id,
            "cluster_id": cluster_id,
            "status": "completed",
        }

    try:
        # Start the background task
        task = asyncio.create_task(
            run_async_in_request_context(background_work, request)
        )

        # Return immediately with task info
        return JsonResponse(
            {
                "message": "Background task started",
                "task_running": True,
            }
        )
    except Exception as exc:
        log_exception(exc)
        return JsonResponse({"error": str(exc)}, status=500)
