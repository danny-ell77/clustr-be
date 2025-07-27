# Cron Jobs for ClustR Payment System

This document provides example cron job configurations for automating the ClustR payment system scheduled tasks.

## Cron Job Examples

### 1. Process Recurring Payments (Every Hour)
```bash
# Process recurring payments every hour at minute 0
0 * * * * cd /path/to/clustr && python manage.py process_payments --task recurring_payments >> /var/log/clustr/recurring_payments.log 2>&1
```

### 2. Send Bill Reminders (Daily at 9 AM)
```bash
# Send bill reminders daily at 9:00 AM
0 9 * * * cd /path/to/clustr && python manage.py process_payments --task bill_reminders >> /var/log/clustr/bill_reminders.log 2>&1
```

### 3. Check Overdue Bills (Daily at 1 AM)
```bash
# Check and mark overdue bills daily at 1:00 AM
0 1 * * * cd /path/to/clustr && python manage.py process_payments --task overdue_bills >> /var/log/clustr/overdue_bills.log 2>&1
```

### 4. Send Recurring Payment Reminders (Daily at 8 AM)
```bash
# Send recurring payment reminders daily at 8:00 AM
0 8 * * * cd /path/to/clustr && python manage.py process_payments --task recurring_reminders >> /var/log/clustr/recurring_reminders.log 2>&1
```

### 5. Run All Payment Tasks (Daily at 2 AM)
```bash
# Run all payment tasks daily at 2:00 AM
0 2 * * * cd /path/to/clustr && python manage.py process_payments --task all >> /var/log/clustr/all_payments.log 2>&1
```

## Complete Crontab Configuration

Add these lines to your crontab (`crontab -e`):

```bash
# ClustR Payment System Scheduled Tasks

# Process recurring payments every hour
0 * * * * cd /path/to/clustr && /path/to/venv/bin/python manage.py process_payments --task recurring_payments >> /var/log/clustr/recurring_payments.log 2>&1

# Send recurring payment reminders daily at 8 AM
0 8 * * * cd /path/to/clustr && /path/to/venv/bin/python manage.py process_payments --task recurring_reminders >> /var/log/clustr/recurring_reminders.log 2>&1

# Send bill reminders daily at 9 AM
0 9 * * * cd /path/to/clustr && /path/to/venv/bin/python manage.py process_payments --task bill_reminders >> /var/log/clustr/bill_reminders.log 2>&1

# Check overdue bills daily at 1 AM
0 1 * * * cd /path/to/clustr && /path/to/venv/bin/python manage.py process_payments --task overdue_bills >> /var/log/clustr/overdue_bills.log 2>&1

# Run all other scheduled tasks daily at 3 AM
0 3 * * * cd /path/to/clustr && /path/to/venv/bin/python manage.py run_scheduled_tasks >> /var/log/clustr/scheduled_tasks.log 2>&1
```

## Environment Setup

### 1. Create Log Directory
```bash
sudo mkdir -p /var/log/clustr
sudo chown www-data:www-data /var/log/clustr  # Adjust user as needed
```

### 2. Set Environment Variables
Create a script to set environment variables:

```bash
# /path/to/clustr/run_payment_task.sh
#!/bin/bash
cd /path/to/clustr
source /path/to/venv/bin/activate
export DJANGO_SETTINGS_MODULE=clustr.settings.production
export DATABASE_URL="your_database_url"
export PAYSTACK_SECRET_KEY="your_paystack_key"
export FLUTTERWAVE_SECRET_KEY="your_flutterwave_key"

python manage.py process_payments --task $1 >> /var/log/clustr/payments_$1.log 2>&1
```

Make it executable:
```bash
chmod +x /path/to/clustr/run_payment_task.sh
```

Then use in crontab:
```bash
# Process recurring payments every hour
0 * * * * /path/to/clustr/run_payment_task.sh recurring_payments

# Send bill reminders daily at 9 AM
0 9 * * * /path/to/clustr/run_payment_task.sh bill_reminders
```

## Monitoring and Alerts

### 1. Log Rotation
Create logrotate configuration (`/etc/logrotate.d/clustr-payments`):

```
/var/log/clustr/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
```

### 2. Email Alerts on Failure
Add email notification to cron jobs:

```bash
# Send email on failure
0 * * * * cd /path/to/clustr && python manage.py process_payments --task recurring_payments >> /var/log/clustr/recurring_payments.log 2>&1 || echo "Recurring payments failed at $(date)" | mail -s "ClustR Payment Task Failed" admin@clustr.com
```

### 3. Health Check Script
Create a health check script (`/path/to/clustr/check_payment_health.sh`):

```bash
#!/bin/bash
LOG_FILE="/var/log/clustr/recurring_payments.log"
LAST_RUN=$(tail -n 1 $LOG_FILE | grep "completed successfully")

if [ -z "$LAST_RUN" ]; then
    echo "Payment tasks may be failing - check logs" | mail -s "ClustR Payment Health Alert" admin@clustr.com
fi
```

Run health check daily:
```bash
0 10 * * * /path/to/clustr/check_payment_health.sh
```

## Alternative: Using Celery Beat

For more advanced scheduling, consider using Celery Beat:

### 1. Install Celery
```bash
pip install celery redis
```

### 2. Create Celery Tasks
```python
# clustr/celery_tasks.py
from celery import Celery
from core.common.utils.scheduled_tasks import ScheduledTaskManager

app = Celery('clustr')

@app.task
def process_recurring_payments():
    ScheduledTaskManager.process_recurring_payments()

@app.task
def send_bill_reminders():
    ScheduledTaskManager.send_bill_reminders()

@app.task
def check_overdue_bills():
    ScheduledTaskManager.check_overdue_bills()
```

### 3. Configure Celery Beat Schedule
```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'process-recurring-payments': {
        'task': 'clustr.celery_tasks.process_recurring_payments',
        'schedule': crontab(minute=0),  # Every hour
    },
    'send-bill-reminders': {
        'task': 'clustr.celery_tasks.send_bill_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'check-overdue-bills': {
        'task': 'clustr.celery_tasks.check_overdue_bills',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
}
```

## Best Practices

1. **Use absolute paths** for Python executable and project directory
2. **Set proper environment variables** for Django settings and secrets
3. **Log all output** for debugging and monitoring
4. **Set up log rotation** to prevent disk space issues
5. **Monitor cron job execution** with health checks
6. **Use email alerts** for critical failures
7. **Test cron jobs** in staging environment first
8. **Use proper file permissions** for scripts and log files

## Troubleshooting

### Common Issues:
1. **Environment variables not set** - Use wrapper script
2. **Python path issues** - Use absolute path to Python in virtualenv
3. **Django settings not found** - Set DJANGO_SETTINGS_MODULE
4. **Permission issues** - Check file and directory permissions
5. **Database connection issues** - Ensure database is accessible from cron environment

### Debug Commands:
```bash
# Test command manually
cd /path/to/clustr && python manage.py process_payments --task recurring_payments

# Check cron logs
tail -f /var/log/cron
tail -f /var/log/clustr/recurring_payments.log

# List current cron jobs
crontab -l
```