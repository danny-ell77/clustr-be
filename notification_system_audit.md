# Notification System Audit - Existing Methods and Mapping

## Overview

This document provides a comprehensive audit of all existing notification methods in the ClustR codebase and their mapping to the new NotificationEvents system.

## Current Notification System Structure

The current system uses multiple specialized notification manager classes:

1. **TaskNotificationManager** (core/common/utils/task_utils.py)
2. **ShiftNotificationManager** (core/common/utils/shift_utils.py)
3. **BillNotificationManager** (core/common/utils/bill_utils.py)
4. **RecurringPaymentNotificationManager** (core/common/utils/recurring_payment_utils.py)
5. **PaymentErrorNotificationManager** (core/common/utils/payment_error_utils.py)
6. **EmergencyNotificationManager** (core/common/utils/emergency_utils.py)
7. **MaintenanceNotificationManager** (core/common/utils/maintenance_utils.py)

## Existing Notification Methods and New Event Mappings

### 1. Task-Related Notifications (TaskNotificationManager)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_task_assignment_notification()` | `ISSUE_ASSIGNED` | MEDIUM | ✅ Already using new system |
| `send_task_status_notification()` | `ISSUE_STATUS_CHANGED` | MEDIUM | ✅ Already using new system |
| `send_task_completion_notification()` | `ISSUE_STATUS_CHANGED` | MEDIUM | ✅ Already using new system |
| `send_task_escalation_notification()` | `ISSUE_ESCALATED` | HIGH | ❌ Need new event |
| `send_task_overdue_notification()` | `ISSUE_OVERDUE` | HIGH | ❌ Need new event |
| `send_automatic_escalation_notification()` | `ISSUE_AUTO_ESCALATED` | HIGH | ❌ Need new event |
| `send_task_comment_notification()` | `COMMENT_REPLY` | LOW | ✅ Event exists |

### 2. Shift-Related Notifications (ShiftNotificationManager)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_shift_assignment_notification()` | `SHIFT_ASSIGNED` | MEDIUM | ❌ Need new event |
| `send_shift_reminder_notification()` | `SHIFT_REMINDER` | MEDIUM | ❌ Need new event |
| `send_missed_shift_notification()` | `SHIFT_MISSED` | HIGH | ❌ Need new event |
| `send_swap_request_notification()` | `SHIFT_SWAP_REQUEST` | MEDIUM | ❌ Need new event |
| `send_swap_response_notification()` | `SHIFT_SWAP_RESPONSE` | MEDIUM | ❌ Need new event |

### 3. Bill-Related Notifications (BillNotificationManager)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_new_bill_notification()` | `PAYMENT_DUE` | MEDIUM | ✅ Event exists |
| `send_overdue_bill_notification()` | `PAYMENT_OVERDUE` | MEDIUM | ✅ Event exists |
| `send_payment_confirmation_notification()` | `PAYMENT_CONFIRMED` | MEDIUM | ✅ Already using new system |
| `send_bill_cancelled_notification()` | `BILL_CANCELLED` | MEDIUM | ❌ Need new event |
| `send_bill_acknowledged_notification()` | `BILL_ACKNOWLEDGED` | LOW | ❌ Need new event |
| `send_bill_disputed_notification()` | `BILL_DISPUTED` | HIGH | ❌ Need new event |

### 4. Recurring Payment Notifications (RecurringPaymentNotificationManager)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_payment_processed_notification()` | `PAYMENT_CONFIRMED` | MEDIUM | ✅ Event exists |
| `send_payment_failed_notification()` | `PAYMENT_FAILED` | HIGH | ❌ Need new event |
| `send_payment_paused_notification()` | `PAYMENT_PAUSED` | MEDIUM | ❌ Need new event |
| `send_payment_resumed_notification()` | `PAYMENT_RESUMED` | MEDIUM | ❌ Need new event |
| `send_payment_cancelled_notification()` | `PAYMENT_CANCELLED` | MEDIUM | ❌ Need new event |
| `send_payment_updated_notification()` | `PAYMENT_UPDATED` | LOW | ❌ Need new event |

### 5. Payment Error Notifications (PaymentErrorNotificationManager)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_payment_failed_notification()` | `PAYMENT_FAILED` | HIGH | ❌ Need new event |
| `send_recurring_payment_failed_notification()` | `PAYMENT_FAILED` | HIGH | ❌ Need new event |

### 6. Emergency Notifications (EmergencyNotificationManager)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_sos_alert_notifications()` | `EMERGENCY_ALERT` | CRITICAL | ✅ Event exists |
| `send_alert_status_notification()` | `EMERGENCY_STATUS_CHANGED` | HIGH | ❌ Need new event |

### 7. Maintenance Notifications (MaintenanceNotificationManager)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_assignment_notification()` | `MAINTENANCE_SCHEDULED` | MEDIUM | ✅ Event exists |

### 8. Visitor Notifications (Already Updated)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_visitor_arrival_notification()` | `VISITOR_ARRIVAL` | HIGH | ✅ Already using new system |
| `send_visitor_overstay_notification()` | `VISITOR_OVERSTAY` | HIGH | ✅ Event exists |

### 9. Announcement Notifications (Already Updated)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_announcement_notification()` | `ANNOUNCEMENT_POSTED` | MEDIUM | ✅ Already using new system |
| `send_comment_notification()` | `COMMENT_REPLY` | LOW | ✅ Already using new system |

### 10. Child Safety Notifications (Already Updated)

| Old Method | New Event | Priority | Status |
|------------|-----------|----------|---------|
| `send_child_exit_notification()` | `CHILD_EXIT_ALERT` | HIGH | ✅ Already using new system |
| `send_child_entry_notification()` | `CHILD_ENTRY_ALERT` | HIGH | ✅ Already using new system |
| `send_child_overdue_notification()` | `CHILD_OVERDUE_ALERT` | HIGH | ❌ Need new event |

## Files Using New Notification System

The following files are already using the new NotificationManager.send() method:

1. **management/views_visitor.py** - VISITOR_ARRIVAL
2. **management/views_helpdesk.py** - ISSUE_ASSIGNED, ISSUE_ESCALATED
3. **management/views_child.py** - CHILD_EXIT_ALERT, CHILD_ENTRY_ALERT, CHILD_OVERDUE_ALERT
4. **management/views_announcement.py** - ANNOUNCEMENT_POSTED, COMMENT_REPLY
5. **core/common/utils/task_utils.py** - ISSUE_ASSIGNED, ISSUE_STATUS_CHANGED
6. **core/common/utils/bill_utils.py** - PAYMENT_CONFIRMED

## Files Using Old Notification System

The following files still use the old notification manager classes:

1. **core/common/utils/shift_utils.py** - ShiftNotificationManager methods
2. **core/common/utils/recurring_payment_utils.py** - RecurringPaymentNotificationManager methods
3. **core/common/utils/payment_error_utils.py** - PaymentErrorNotificationManager methods
4. **core/common/utils/emergency_utils.py** - EmergencyNotificationManager methods
5. **core/common/utils/maintenance_utils.py** - MaintenanceNotificationManager methods
6. **core/common/utils/bill_utils.py** - Some BillNotificationManager methods
7. **management/views_task.py** - TaskNotificationManager.send_task_comment_notification
8. **management/views_shift.py** - ShiftNotificationManager methods

## Missing NotificationEvents

The following events need to be added to support all existing functionality:

### High Priority Events
- `ISSUE_ESCALATED`
- `ISSUE_OVERDUE`
- `ISSUE_AUTO_ESCALATED`
- `SHIFT_MISSED`
- `PAYMENT_FAILED`
- `BILL_DISPUTED`
- `EMERGENCY_STATUS_CHANGED`
- `CHILD_OVERDUE_ALERT`

### Medium Priority Events
- `SHIFT_ASSIGNED`
- `SHIFT_REMINDER`
- `SHIFT_SWAP_REQUEST`
- `SHIFT_SWAP_RESPONSE`
- `BILL_CANCELLED`
- `PAYMENT_PAUSED`
- `PAYMENT_RESUMED`
- `PAYMENT_CANCELLED`

### Low Priority Events
- `BILL_ACKNOWLEDGED`
- `PAYMENT_UPDATED`

## Custom Notification Logic to Preserve

### 1. Emergency Notifications
- SOS alerts need to notify multiple user types (admins, security, emergency contacts)
- Critical priority that bypasses all preferences

### 2. Child Safety Notifications
- Parent notifications for exit/entry
- Admin notifications for overdue children
- Multiple recipient handling

### 3. Payment Notifications
- Different contexts for different payment types
- Error handling and recovery options
- Transaction details formatting

### 4. Shift Notifications
- Staff-specific notifications
- Swap request workflows
- Reminder scheduling

## Implementation Strategy

### Phase 1: Add Missing Events
1. Add all missing NotificationEvents to events.py
2. Update NOTIFICATION_EVENTS registry with proper priorities and channels

### Phase 2: Replace by Category
1. **Visitor notifications** - ✅ Already done
2. **Announcement notifications** - ✅ Already done  
3. **Child safety notifications** - ✅ Already done
4. **Issue/Task notifications** - Partially done, complete remaining
5. **Payment notifications** - Replace bill and recurring payment methods
6. **Shift notifications** - Replace all shift-related methods
7. **Emergency notifications** - Replace emergency alert methods
8. **Maintenance notifications** - Replace maintenance methods

### Phase 3: Clean Up
1. Remove old notification manager classes
2. Update imports throughout codebase
3. Remove unused email template mappings
4. Update documentation

## Notes

- Most files are already partially migrated to the new system
- The new NotificationManager.send() API is being used in many places
- Main work is adding missing events and replacing remaining old method calls
- Context data structures are generally compatible between old and new systems