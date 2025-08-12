"""
Utility functions for ClustR application.
Refactored to use pure functions with module-scoped imports.
"""

from core.common.includes.file_storage import FileStorage
from core.common.includes.serializers import build_runtime_serializer
from core.common.includes import notifications
from core.common.includes import tasks
from core.common.includes import bills
from core.common.includes import recurring_payments
from core.common.includes import shifts
from core.common.includes import emergencies
from core.common.includes import maintenance
from core.common.includes import payments
from core.common.includes import helpdesk
from core.common.includes import cluster_wallet
from core.common.includes import utilities


# Function to convert snake_case or camelCase to sentence case
def to_sentence_case(text: str) -> str:
    """
    Convert snake_case or camelCase to sentence case.

    Args:
        text: The text to convert

    Returns:
        The text in sentence case
    """
    # Replace underscores with spaces
    text = text.replace("_", " ")

    # Insert space before capital letters
    result = ""
    for i, char in enumerate(text):
        if char.isupper() and i > 0 and text[i - 1] != " ":
            result += " " + char
        else:
            result += char

    # Capitalize the first letter and lowercase the rest
    return result.strip().capitalize()


__all__ = [
    "FileStorage",
    "to_sentence_case",
    "build_runtime_serializer",
    "notifications",
    "tasks",
    "bills",
    "recurring_payments",
    "shifts",
    "emergencies",
    "maintenance",
    "payments",
    "helpdesk",
    "cluster_wallet",
    "utilities",
]
