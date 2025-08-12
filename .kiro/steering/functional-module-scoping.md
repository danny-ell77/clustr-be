---
inclusion: always
---

# 🎯 MANDATORY: Function-Based Module Scoping

## For AI Agents & Developers: ALWAYS Use Function-Based Utilities

### ⚠️ **CRITICAL RULE:**
**Never use Manager.method() patterns. Always use function-based modules from `@core/common/utils/**`**

### ✅ **CORRECT Pattern (ALWAYS use this):**
```python
from core.common.includes import notifications, payments, bills, maintenance

# Use module.function() syntax
notifications.send(event_name, recipients, cluster, context)
payments.initialize(transaction, user_email, callback_url) 
bills.create_cluster_wide(cluster, title, amount, bill_type, due_date)
maintenance.create_log(cluster, requested_by, title, description)
```

### ❌ **FORBIDDEN Pattern (NEVER use this):**
```python
# Don't do this - Manager classes are deprecated
NotificationManager.send(...)
PaymentManager.initialize(...) 
BillManager.create_bill(...)
MaintenanceManager.create_log(...)
```

### 📋 **Available Function Modules:**

| Domain | Import | Key Functions |
|--------|--------|---------------|
| **Notifications** | `from core.common.includes import notifications` | `send()`, `send_sync()`, `send_with_retry()` |
| **Payments** | `from core.common.includes import payments` | `initialize()`, `process()`, `validate_data()` |
| **Bills** | `from core.common.includes import bills` | `create_cluster_wide()`, `create_user_specific()`, `get_summary()` |
| **Maintenance** | `from core.common.includes import maintenance` | `create_log()`, `assign_log()`, `get_analytics()` |
| **Emergencies** | `from core.common.includes import emergencies` | `create_alert()`, `cancel_alert()`, `get_user_alerts()` |
| **Shifts** | `from core.common.includes import shifts` | `create()`, `clock_in()`, `clock_out()` |
| **Tasks** | `from core.common.includes import tasks` | `create()`, `assign()`, `start()`, `complete()` |
| **Recurring Payments** | `from core.common.includes import recurring_payments` | `create()`, `process_due_payments()` |
| **Cluster Wallet** | `from core.common.includes import cluster_wallet` | `get_balance()`, `credit()`, `debit()` |

### 🔧 **Implementation Example:**
```python
# ✅ CORRECT: Function-based approach
def create_maintenance_request(request):
    # Create maintenance log
    log = maintenance.create_log(
        cluster=request.cluster_context,
        requested_by=request.user,
        title=request.data['title'],
        description=request.data['description'],
        priority=request.data.get('priority', 'MEDIUM')
    )
    
    # Send notification to maintenance team
    notifications.send(
        event_name=NotificationEvents.MAINTENANCE_REQUESTED,
        recipients=get_maintenance_staff(request.cluster_context),
        cluster=request.cluster_context,
        context={
            'maintenance_title': log.title,
            'requested_by': request.user.name,
            'priority': log.priority
        }
    )
    
    return log
```

### 🚨 **AI Agent Instructions:**
1. **ALWAYS** check for Manager.method() patterns in existing code
2. **ALWAYS** replace with module.function() equivalents
3. **ALWAYS** import the module, not a class: `from core.common.includes import module_name`
4. **NEVER** create new Manager classes - extend function modules instead
5. **ALWAYS** use the reference table above for correct function names

**This pattern is MANDATORY for all new code and refactoring tasks.**
