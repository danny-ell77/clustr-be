"""
Utility functions for ClustR application.
"""

from core.common.utils.file_storage import FileStorage
from core.common.utils.notification_utils import NotificationManager
from core.common.utils.scheduled_tasks import ScheduledTaskManager
from core.common.utils.helpdesk_utils import HelpdeskManager
from core.common.utils.emergency_utils import EmergencyManager
from core.common.utils.shift_utils import ShiftManager, ShiftNotificationManager
from core.common.utils.task_utils import TaskManager, TaskNotificationManager, TaskFileManager
from core.common.utils.serializers import build_runtime_serializer
from core.common.utils.payment_utils import PaymentManager, PaymentError, initialize_deposit, process_bill_payment
from core.common.utils.bill_utils import BillManager, BillNotificationManager, create_monthly_service_charge, create_utility_bill
from core.common.utils.recurring_payment_utils import RecurringPaymentManager, RecurringPaymentNotificationManager, setup_monthly_service_charge, setup_utility_autopay
from core.common.utils.payment_error_utils import PaymentErrorHandler, PaymentErrorNotificationManager, handle_payment_error, get_payment_error_summary
from core.common.utils.cluster_wallet_utils import ClusterWalletManager, get_cluster_balance, credit_cluster_from_bill_payment

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
    text = text.replace('_', ' ')
    
    # Insert space before capital letters
    result = ''
    for i, char in enumerate(text):
        if char.isupper() and i > 0 and text[i-1] != ' ':
            result += ' ' + char
        else:
            result += char
    
    # Capitalize the first letter and lowercase the rest
    return result.strip().capitalize()

__all__ = [
    'FileStorage',
    'to_sentence_case',
    'NotificationManager',
    'ScheduledTaskManager',
    'HelpdeskManager',
    'EmergencyManager',
    'ShiftManager',
    'ShiftNotificationManager',
    'TaskManager',
    'TaskNotificationManager',
    'TaskFileManager',
    'build_runtime_serializer',
    'PaymentManager',
    'PaymentError',
    'initialize_deposit',
    'process_bill_payment',
    'BillManager',
    'BillNotificationManager',
    'create_monthly_service_charge',
    'create_utility_bill',
    'RecurringPaymentManager',
    'RecurringPaymentNotificationManager',
    'setup_monthly_service_charge',
    'setup_utility_autopay',
    'PaymentErrorHandler',
    'PaymentErrorNotificationManager',
    'handle_payment_error',
    'get_payment_error_summary',
    'ClusterWalletManager',
    'get_cluster_balance',
    'credit_cluster_from_bill_payment'
]