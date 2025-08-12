"""
NotificationManager - Central orchestrator for the ClustR notification system.

This module provides the main API for sending notifications across different channels
with proper event validation, channel routing, and error handling.
"""

import typing
import logging
import concurrent.futures
from typing import List, Any, Optional

from django.contrib.auth import get_user_model

from core.notifications.events import (
    NotificationEvents,
    NotificationEvent,
    NOTIFICATION_EVENTS,
    NotificationChannel,
)
from core.common.models.cluster import Cluster

if typing.TYPE_CHECKING:
    User = get_user_model()

logger = logging.getLogger(__name__)


