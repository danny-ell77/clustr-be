"""
Script to create email notification template files.
Run this from the clustr-be directory: python create_email_templates.py
"""

import os
from pathlib import Path

# Template directory - using core.notifications app since APP_DIRS=True
TEMPLATE_DIR = Path("core/notifications/templates/emails")

# Template files to create with their content
TEMPLATES = {
    "emergency_alert.html": """<!DOCTYPE html>
<html>
<head><title>Emergency Alert</title></head>
<body>
<h1>EMERGENCY ALERT</h1>

<p>{{ alert_message }}</p>

<p><strong>Location:</strong> {{ location }}</p>
<p><strong>Time:</strong> {{ formatted_alert_time }}</p>
<p><strong>Severity:</strong> {{ severity }}</p>

<p>Please take immediate action as required.</p>

<p>The ClustR Team</p>
</body>
</html>
""",
    
    "visitor_arrival.html": """<!DOCTYPE html>
<html>
<head><title>Visitor Arrival</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>Your visitor <strong>{{ visitor_name }}</strong> has arrived at the estate.</p>

{% if access_code %}<p><strong>Access Code:</strong> {{ access_code }}</p>{% endif %}
{% if formatted_arrival_time %}<p><strong>Arrival Time:</strong> {{ formatted_arrival_time }}</p>{% endif %}
{% if unit %}<p><strong>Unit:</strong> {{ unit }}</p>{% endif %}

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "visitor_overstay.html": """<!DOCTYPE html>
<html>
<head><title>Visitor Overstay Alert</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>Your visitor <strong>{{ visitor_name }}</strong> has exceeded their scheduled visit duration.</p>

{% if access_code %}<p><strong>Access Code:</strong> {{ access_code }}</p>{% endif %}
{% if formatted_departure_time %}<p><strong>Expected Departure:</strong> {{ formatted_departure_time }}</p>{% endif %}

<p>Please check on your visitor or update their visit duration if needed.</p>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "bill_reminder.html": """<!DOCTYPE html>
<html>
<head><title>Bill Payment Reminder</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>This is a reminder that you have a bill due for payment:</p>

{% if bill_number %}<p><strong>Bill Number:</strong> {{ bill_number }}</p>{% endif %}
{% if bill_title %}<p><strong>Title:</strong> {{ bill_title }}</p>{% endif %}
{% if formatted_amount %}<p><strong>Amount:</strong> {{ formatted_amount }}</p>{% endif %}
{% if formatted_due_date %}<p><strong>Due Date:</strong> {{ formatted_due_date }}</p>{% endif %}

{% if days_until_due %}<p>This bill is due in {{ days_until_due }} day(s).</p>{% endif %}
{% if days_overdue %}<p><strong>This bill is {{ days_overdue }} day(s) overdue.</strong></p>{% endif %}

<p>Please log in to your ClustR account to make payment.</p>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "payment_receipt.html": """<!DOCTYPE html>
<html>
<head><title>Payment Receipt</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>Thank you for your payment. Here are the details:</p>

{% if bill_number %}<p><strong>Bill Number:</strong> {{ bill_number }}</p>{% endif %}
{% if formatted_payment_amount %}<p><strong>Payment Amount:</strong> {{ formatted_payment_amount }}</p>{% endif %}
{% if transaction_id %}<p><strong>Transaction ID:</strong> {{ transaction_id }}</p>{% endif %}
{% if formatted_payment_date %}<p><strong>Payment Date:</strong> {{ formatted_payment_date }}</p>{% endif %}

<p>Thank you for using ClustR!</p>

<p>The ClustR Team</p>
</body>
</html>
""",
    
    "announcement.html": """<!DOCTYPE html>
<html>
<head><title>{{ announcement_title|default:"New Announcement" }}</title></head>
<body>
<p>Hello {{ user_name }},</p>

{% if announcement_title %}<h2>{{ announcement_title }}</h2>{% endif %}

{% if announcement_content %}<div>{{ announcement_content }}</div>{% endif %}

{% if announcement_date %}<p><em>Posted on: {{ announcement_date }}</em></p>{% endif %}

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "maintenance.html": """<!DOCTYPE html>
<html>
<head><title>Maintenance Notification</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>This is a notification regarding maintenance activities.</p>

<p><strong>Title:</strong> {{ title }}</p>
<p><strong>Message:</strong> {{ message }}</p>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "billing.html": """<!DOCTYPE html>
<html>
<head><title>Billing Notification</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>This is a notification regarding your billing.</p>

<p><strong>Title:</strong> {{ title }}</p>
<p><strong>Message:</strong> {{ message }}</p>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "issue.html": """<!DOCTYPE html>
<html>
<head><title>Issue Notification</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>This is a notification regarding an issue.</p>

<p><strong>Title:</strong> {{ title }}</p>
<p><strong>Message:</strong> {{ message }}</p>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "task.html": """<!DOCTYPE html>
<html>
<head><title>Task Notification</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>This is a notification regarding a task.</p>

<p><strong>Title:</strong> {{ title }}</p>
<p><strong>Message:</strong> {{ message }}</p>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "newsletter.html": """<!DOCTYPE html>
<html>
<head><title>ClustR Newsletter</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>Please find our latest newsletter below.</p>

<div>{{ content }}</div>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "system_update.html": """<!DOCTYPE html>
<html>
<head><title>System Update</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>This is a notification regarding a system update.</p>

<p><strong>Title:</strong> {{ title }}</p>
<p><strong>Message:</strong> {{ message }}</p>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "password_changed.html": """<!DOCTYPE html>
<html>
<head><title>Password Changed</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>Your ClustR account password was recently changed.</p>

<p>If you made this change, you can ignore this email.</p>

<p><strong>If you did not change your password, please contact support immediately.</strong></p>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "password_reset_requested.html": """<!DOCTYPE html>
<html>
<head><title>Password Reset Request</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>We received a request to reset your password.</p>

{% if otp %}<p><strong>Your verification code is:</strong> {{ otp }}</p>{% endif %}
{% if reset_link %}<p><a href="{{ reset_link }}">Click here to reset your password</a></p>{% endif %}

<p>If you did not request this, please ignore this email.</p>

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "email_verification.html": """<!DOCTYPE html>
<html>
<head><title>Verify Your Email</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p>Please verify your email address.</p>

{% if otp %}<p><strong>Your verification code is:</strong> {{ otp }}</p>{% endif %}
{% if verification_link %}<p><a href="{{ verification_link }}">Click here to verify</a></p>{% endif %}

<p>Thank you,<br>The ClustR Team</p>
</body>
</html>
""",
    
    "account_created.html": """<!DOCTYPE html>
<html>
<head><title>Welcome to ClustR!</title></head>
<body>
<p>Hello {{ user_name }},</p>

<p><strong>Welcome to ClustR!</strong> Your account has been successfully created.</p>

{% if otp %}<p><strong>Your verification code is:</strong> {{ otp }}</p>{% endif %}

<p>Thank you for joining us!</p>

<p>The ClustR Team</p>
</body>
</html>
""",
}

def main():
    # Create template directory
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {TEMPLATE_DIR}")
    
    # Create each template file
    for filename, content in TEMPLATES.items():
        filepath = TEMPLATE_DIR / filename
        filepath.write_text(content, encoding="utf-8")
        print(f"Created: {filepath}")
    
    print(f"\nSuccessfully created {len(TEMPLATES)} template files!")

if __name__ == "__main__":
    main()
