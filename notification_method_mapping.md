# Notification Method Mapping Table

## Old Method → New Event Mapping

This table provides the exact mapping from old notification methods to new NotificationEvents for the replacement process.

| File | Old Method | New Event | Priority | Channels | Status |
|------|------------|-----------|----------|----------|---------|
| **Task Notifications** |
| task_utils.py | `TaskNotificationManager.send_task_assignment_notification()` | `ISSUE_ASSIGNED` | MEDIUM | EMAIL | ✅ Using new system |
| task_utils.py | `TaskNotificationManager.send_task_status_notification()` | `ISSUE_STATUS_CHANGED` | MEDIUM | EMAIL | ✅ Using new system |
| task_utils.py | `TaskNotificationManager.send_task_completion_notification()` | `ISSUE_STATUS_CHANGED` | MEDIUM | EMAIL | ✅ Using new system |
| task_utils.py | `TaskNotificationManager.send_task_escalation_notification()` | `ISSUE_ESCALATED` | HIGH | EMAIL, SMS | ❌ Need new event |
| task_utils.py | `TaskNotificationManager.send_task_overdue_notification()` | `ISSUE_OVERDUE` | HIGH | EMAIL, SMS | ❌ Need new event |
| task_utils.py | `TaskNotificationManager.send_automatic_escalation_notification()` | `ISSUE_AUTO_ESCALATED` | HIGH | EMAIL, SMS | ❌ Need new event |
| management/views_task.py | `TaskNotificationManager.send_task_comment_notification()` | `COMMENT_REPLY` | LOW | EMAIL | ✅ Event exists |
| **Shift Notifications** |
| shift_utils.py | `ShiftNotificationManager.send_shift_assignment_notification()` | `SHIFT_ASSIGNED` | MEDIUM | EMAIL | ❌ Need new event |
| shift_utils.py | `ShiftNotificationManager.send_shift_reminder_notification()` | `SHIFT_REMINDER` | MEDIUM | EMAIL, SMS | ❌ Need new event |
| shift_utils.py | `ShiftNotificationManager.send_missed_shift_notification()` | `SHIFT_MISSED` | HIGH | EMAIL, SMS | ❌ Need new event |
| shift_utils.py | `ShiftNotificationManager.send_swap_request_notification()` | `SHIFT_SWAP_REQUEST` | MEDIUM | EMAIL | ❌ Need new event |
| shift_utils.py | `ShiftNotificationManager.send_swap_response_notification()` | `SHIFT_SWAP_RESPONSE` | MEDIUM | EMAIL | ❌ Need new event |
| management/views_shift.py | `ShiftNotificationManager.send_missed_shift_notification()` | `SHIFT_MISSED` | HIGH | EMAIL, SMS | ❌ Need new event |
| management/views_shift.py | `ShiftNotificationManager.send_swap_response_notification()` | `SHIFT_SWAP_RESPONSE` | MEDIUM | EMAIL | ❌ Need new event |
| **Bill Notifications** |
| bill_utils.py | `BillNotificationManager.send_new_bill_notification()` | `PAYMENT_DUE` | MEDIUM | EMAIL | ✅ Event exists |
| bill_utils.py | `BillNotificationManager.send_overdue_bill_notification()` | `PAYMENT_OVERDUE` | MEDIUM | EMAIL, SMS | ✅ Event exists |
| bill_utils.py | `BillNotificationManager.send_payment_confirmation_notification()` | `PAYMENT_CONFIRMED` | MEDIUM | EMAIL | ✅ Using new system |
| bill_utils.py | `BillNotificationManager.send_bill_cancelled_notification()` | `BILL_CANCELLED` | MEDIUM | EMAIL | ❌ Need new event |
| bill_utils.py | `BillNotificationManager.send_bill_acknowledged_notification()` | `BILL_ACKNOWLEDGED` | LOW | EMAIL | ❌ Need new event |
| bill_utils.py | `BillNotificationManager.send_bill_disputed_notification()` | `BILL_DISPUTED` | HIGH | EMAIL, SMS | ❌ Need new event |
| **Recurring Payment Notifications** |
| recurring_payment_utils.py | `RecurringPaymentNotificationManager.send_payment_processed_notification()` | `PAYMENT_CONFIRMED` | MEDIUM | EMAIL | ✅ Event exists |
| recurring_payment_utils.py | `RecurringPaymentNotificationManager.send_payment_failed_notification()` | `PAYMENT_FAILED` | HIGH | EMAIL, SMS | ❌ Need new event |
| recurring_payment_utils.py | `RecurringPaymentNotificationManager.send_payment_paused_notification()` | `PAYMENT_PAUSED` | MEDIUM | EMAIL | ❌ Need new event |
| recurring_payment_utils.py | `RecurringPaymentNotificationManager.send_payment_resumed_notification()` | `PAYMENT_RESUMED` | MEDIUM | EMAIL | ❌ Need new event |
| recurring_payment_utils.py | `RecurringPaymentNotificationManager.send_payment_cancelled_notification()` | `PAYMENT_CANCELLED` | MEDIUM | EMAIL | ❌ Need new event |
| recurring_payment_utils.py | `RecurringPaymentNotificationManager.send_payment_updated_notification()` | `PAYMENT_UPDATED` | LOW | EMAIL | ❌ Need new event |
| **Payment Error Notifications** |
| payment_error_utils.py | `PaymentErrorNotificationManager.send_payment_failed_notification()` | `PAYMENT_FAILED` | HIGH | EMAIL, SMS | ❌ Need new event |
| payment_error_utils.py | `PaymentErrorNotificationManager.send_recurring_payment_failed_notification()` | `PAYMENT_FAILED` | HIGH | EMAIL, SMS | ❌ Need new event |
| **Emergency Notifications** |
| emergency_utils.py | `EmergencyNotificationManager.send_sos_alert_notifications()` | `EMERGENCY_ALERT` | CRITICAL | EMAIL, SMS, WEBSOCKET, APP | ✅ Event exists |
| emergency_utils.py | `EmergencyNotificationManager.send_alert_status_notification()` | `EMERGENCY_STATUS_CHANGED` | HIGH | EMAIL, SMS, WEBSOCKET | ❌ Need new event |
| **Maintenance Notifications** |
| maintenance_utils.py | `MaintenanceNotificationManager.send_assignment_notification()` | `MAINTENANCE_SCHEDULED` | MEDIUM | EMAIL | ✅ Event exists |
| **Visitor Notifications** |
| management/views_visitor.py | `send_visitor_arrival_notification()` | `VISITOR_ARRIVAL` | HIGH | EMAIL, WEBSOCKET, APP | ✅ Using new system |
| N/A | `send_visitor_overstay_notification()` | `VISITOR_OVERSTAY` | HIGH | EMAIL, SMS, WEBSOCKET | ✅ Event exists |
| **Announcement Notifications** |
| management/views_announcement.py | `send_announcement_notification()` | `ANNOUNCEMENT_POSTED` | MEDIUM | EMAIL, WEBSOCKET, APP | ✅ Using new system |
| management/views_announcement.py | `send_comment_notification()` | `COMMENT_REPLY` | LOW | EMAIL | ✅ Using new system |
| **Child Safety Notifications** |
| management/views_child.py | `send_child_exit_notification()` | `CHILD_EXIT_ALERT` | HIGH | EMAIL, SMS, WEBSOCKET, APP | ✅ Using new system |
| management/views_child.py | `send_child_entry_notification()` | `CHILD_ENTRY_ALERT` | HIGH | EMAIL, SMS, WEBSOCKET, APP | ✅ Using new system |
| management/views_child.py | `send_child_overdue_notification()` | `CHILD_OVERDUE_ALERT` | HIGH | EMAIL, SMS, WEBSOCKET, APP | ❌ Need new event |

## Summary

### ✅ Already Using New System (9 methods)
- Task assignment, status, completion notifications
- Visitor arrival notifications  
- Announcement and comment notifications
- Child exit/entry notifications
- Bill payment confirmation

### ✅ Events Exist, Need Replacement (6 methods)
- Bill new/overdue notifications
- Recurring payment processed notifications
- Emergency SOS alerts
- Maintenance assignment notifications
- Visitor overstay notifications

### ❌ Need New Events (20 methods)
- Task escalation and overdue notifications (3)
- All shift notifications (5)
- Bill cancelled/acknowledged/disputed notifications (3)
- Recurring payment status notifications (4)
- Payment error notifications (2)
- Emergency status change notifications (1)
- Child overdue notifications (1)
- Task comment notifications (1)

## New Events to Add

```python
# High Priority Events
ISSUE_ESCALATED = "issue_escalated"
ISSUE_OVERDUE = "issue_overdue" 
ISSUE_AUTO_ESCALATED = "issue_auto_escalated"
SHIFT_MISSED = "shift_missed"
PAYMENT_FAILED = "payment_failed"
BILL_DISPUTED = "bill_disputed"
EMERGENCY_STATUS_CHANGED = "emergency_status_changed"
CHILD_OVERDUE_ALERT = "child_overdue_alert"

# Medium Priority Events  
SHIFT_ASSIGNED = "shift_assigned"
SHIFT_REMINDER = "shift_reminder"
SHIFT_SWAP_REQUEST = "shift_swap_request"
SHIFT_SWAP_RESPONSE = "shift_swap_response"
BILL_CANCELLED = "bill_cancelled"
PAYMENT_PAUSED = "payment_paused"
PAYMENT_RESUMED = "payment_resumed"
PAYMENT_CANCELLED = "payment_cancelled"

# Low Priority Events
BILL_ACKNOWLEDGED = "bill_acknowledged"
PAYMENT_UPDATED = "payment_updated"
```