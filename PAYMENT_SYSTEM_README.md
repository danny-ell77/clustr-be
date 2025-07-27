# ClustR Payment System

This document provides a comprehensive overview of the ClustR payment system implementation.

## Overview

The ClustR payment system provides a complete payment solution for estate management with advanced security and flexibility features:

- **Wallet Management**: User wallets with balance tracking and PIN security
- **Payment Processing**: Integration with Paystack and Flutterwave payment providers
- **Bill Management**: Estate bill creation, acknowledgment, and payment processing
- **Bill Acknowledgment System**: Fraud prevention through mandatory bill acknowledgment
- **Direct Payment Options**: Pay bills directly via payment providers or wallet balance
- **Cluster Wallet System**: Automatic crediting of estate revenue from bill payments
- **Recurring Payments**: Automated recurring payment processing with failure handling
- **Error Handling**: Comprehensive error categorization and recovery options
- **Notifications**: Email notifications for all payment events
- **Scheduled Tasks**: Automated processing of recurring payments and bill reminders
- **Audit Trail**: Complete tracking of all payment operations and admin actions

## Architecture

### Models (`core/common/models/wallet.py`)

#### Wallet
- User wallet with balance tracking
- PIN security for transactions
- Balance freeze/unfreeze functionality
- Multi-tenant support with estate isolation

#### Transaction
- All payment transactions with provider integration
- Status tracking (pending, processing, completed, failed)
- Provider response storage and metadata
- Automatic transaction ID generation

#### Bill
- Estate bills with comprehensive lifecycle management
- **Bill Acknowledgment System**: Mandatory user acknowledgment before payment
- **Dispute Resolution**: Users can dispute bills with reasons
- **Multiple Payment Options**: Wallet balance or direct provider payment
- **Status Tracking**: From creation → acknowledgment → payment → completion
- Overdue detection and automated status management
- Partial payment support with automatic cluster wallet crediting
- Bill numbering and categorization by type

#### ClusterWalletOperation
- Audit trail for all cluster wallet operations
- Admin accountability tracking
- Operation categorization (bill payments, transfers, adjustments)
- Complete metadata storage for compliance

#### RecurringPayment
- Scheduled recurring payments
- Frequency management (daily, weekly, monthly, quarterly, yearly)
- Failure handling with automatic pause after max attempts
- Payment history tracking

### Utilities

#### Payment Processing (`core/common/utils/payment_utils.py`)
- `PaystackPaymentProcessor`: Paystack API integration
- `FlutterwavePaymentProcessor`: Flutterwave API integration
- `PaymentManager`: Main payment orchestration
- Payment initialization, verification, and webhook processing
- Receipt generation and storage

#### Bill Management (`core/common/utils/bill_utils.py`)
- `BillManager`: Comprehensive bill lifecycle management
- `BillNotificationManager`: Bill-related notifications including acknowledgments and disputes
- **Bill acknowledgment and dispute handling**
- **Fraud prevention through mandatory acknowledgment**
- Bulk bill creation and status updates
- Overdue bill detection and reminders

#### Cluster Wallet Management (`core/common/utils/cluster_wallet_utils.py`)
- `ClusterWalletManager`: Estate revenue management
- **Automatic crediting from bill payments**
- **Admin accountability tracking**
- Revenue analytics and reporting
- Transfer and withdrawal capabilities

#### Recurring Payments (`core/common/utils/recurring_payment_utils.py`)
- `RecurringPaymentManager`: Recurring payment operations
- `RecurringPaymentNotificationManager`: Recurring payment notifications
- Automated payment processing with failure handling
- Payment schedule management

#### Error Handling (`core/common/utils/payment_error_utils.py`)
- `PaymentErrorHandler`: Error categorization and handling
- `PaymentErrorNotificationManager`: Error notifications
- Recovery options and retry mechanisms
- Admin alerts for critical errors

### API Endpoints

#### Management App (Administrators)
**Base URL**: `/management/payments/`

- `GET /dashboard/` - Payment dashboard with statistics and cluster wallet info
- `POST /create_bill/` - Create a new bill (starts in PENDING_ACKNOWLEDGMENT status)
- `POST /create_bulk_bills/` - Create multiple bills
- `GET /bills/` - List bills with filtering
- `GET /transactions/` - List transactions with filtering
- `GET /recurring_payments/` - List recurring payments
- `POST /update_bill_status/` - Update bill status
- `POST /pause_recurring_payment/` - Pause recurring payment
- `GET /cluster_wallet/` - Get cluster wallet analytics and transactions
- `POST /cluster_wallet_transfer/` - Transfer funds from cluster wallet
- `POST /cluster_wallet_credit/` - Manually add credit to cluster wallet

#### Members App (Residents)
**Base URL**: `/members/`

##### Wallet Endpoints (`/wallet/`)
- `GET /balance/` - Get wallet balance
- `POST /deposit/` - Initialize wallet deposit
- `GET /transactions/` - Get transaction history

##### Bill Endpoints (`/bills/`)
- `GET /my_bills/` - Get user's bills (all statuses)
- `GET /summary/` - Get bills summary
- `POST /acknowledge_bill/` - **Acknowledge a bill (required before payment)**
- `POST /dispute_bill/` - **Dispute a bill with reason**
- `POST /pay_bill/` - Pay bill using wallet balance
- `POST /pay_bill_direct/` - **Pay bill directly via Paystack/Flutterwave**

##### Recurring Payment Endpoints (`/recurring-payments/`)
- `GET /my_payments/` - Get user's recurring payments
- `GET /summary/` - Get recurring payments summary
- `POST /create/` - Create new recurring payment
- `POST /pause/` - Pause recurring payment
- `POST /resume/` - Resume recurring payment
- `POST /cancel/` - Cancel recurring payment

#### Webhook Endpoints
**Base URL**: `/payments/`

- `POST /webhooks/paystack/` - Paystack webhook handler
- `POST /webhooks/flutterwave/` - Flutterwave webhook handler
- `POST /verify-payment/` - Manual payment verification

## Scheduled Tasks

The payment system includes automated scheduled tasks managed by `ScheduledTaskManager`:

### Payment Tasks
- `process_recurring_payments()` - Process due recurring payments
- `send_recurring_payment_reminders()` - Send payment reminders
- `check_overdue_bills()` - Mark overdue bills
- `send_bill_reminders()` - Send bill payment reminders

### Management Command
```bash
python manage.py process_payments --task all
python manage.py process_payments --task recurring_payments
python manage.py process_payments --task bill_reminders
```

## Configuration

### Payment Provider Settings
```python
# settings.py
PAYSTACK_SECRET_KEY = 'your_paystack_secret_key'
PAYSTACK_PUBLIC_KEY = 'your_paystack_public_key'

FLUTTERWAVE_SECRET_KEY = 'your_flutterwave_secret_key'
FLUTTERWAVE_PUBLIC_KEY = 'your_flutterwave_public_key'
FLUTTERWAVE_WEBHOOK_SECRET = 'your_webhook_secret'
```

### Webhook URLs
- Paystack: `https://yourdomain.com/payments/webhooks/paystack/`
- Flutterwave: `https://yourdomain.com/payments/webhooks/flutterwave/`

## Bill Acknowledgment & Payment Flow

### 🔒 Security-First Bill Processing

The ClustR payment system implements a security-first approach to bill processing to prevent fraud and ensure transparency:

#### Bill Lifecycle:
1. **Admin Creates Bill** → Status: `PENDING_ACKNOWLEDGMENT`
2. **User Reviews Bill** → User can acknowledge or dispute
3. **If Acknowledged** → Status: `ACKNOWLEDGED` → Ready for payment
4. **If Disputed** → Status: `DISPUTED` → Requires admin review
5. **Payment Processing** → Multiple payment options available
6. **Completion** → Cluster wallet automatically credited

#### Bill Statuses:
- `PENDING_ACKNOWLEDGMENT` - Waiting for user to review and acknowledge
- `ACKNOWLEDGED` - User has approved the bill, ready for payment
- `DISPUTED` - User has disputed the bill, requires admin attention
- `PENDING` - Ready for payment (legacy status)
- `OVERDUE` - Past due date, requires immediate attention
- `PARTIALLY_PAID` - Partial payment made, balance remaining
- `PAID` - Fully paid, cluster wallet credited
- `CANCELLED` - Bill cancelled by admin

### 💳 Dual Payment Options

#### Option 1: Wallet Balance Payment
- Use existing wallet balance
- Instant processing
- No additional fees

#### Option 2: Direct Provider Payment
- Pay directly via Paystack or Flutterwave
- No wallet top-up required
- Real-time payment processing
- Automatic bill completion

### 🏢 Cluster Wallet System

All successful bill payments automatically credit the cluster's main wallet:
- **Immediate crediting** upon payment completion
- **Full audit trail** with admin accountability
- **Revenue analytics** and reporting
- **Transfer capabilities** for estate management

## Usage Examples

### Creating a Bill (Management)
```python
POST /management/payments/create_bill/
{
    "user_id": "user-uuid",
    "title": "Monthly Service Charge",
    "amount": "5000.00",
    "type": "service_charge",
    "due_date": "2025-02-28T23:59:59Z",
    "description": "Monthly estate service charge"
}
# Response: Bill created with status "PENDING_ACKNOWLEDGMENT"
```

### Bill Acknowledgment (Members)
```python
POST /members/bills/acknowledge_bill/
{
    "bill_id": "bill-uuid"
}
# Response: Bill status changed to "ACKNOWLEDGED", ready for payment
```

### Bill Dispute (Members)
```python
POST /members/bills/dispute_bill/
{
    "bill_id": "bill-uuid",
    "reason": "Amount seems incorrect for this month's usage"
}
# Response: Bill status changed to "DISPUTED", admins notified
```

### Wallet Deposit (Members)
```python
POST /members/wallet/deposit/
{
    "amount": "10000.00",
    "provider": "paystack",
    "callback_url": "https://yourapp.com/payment/callback"
}
```

### Bill Payment Options (Members)

#### Option 1: Wallet Balance Payment
```python
POST /members/bills/pay_bill/
{
    "bill_id": "bill-uuid",
    "amount": "5000.00"  # Optional, defaults to remaining amount
}
# Uses wallet balance, instant processing
```

#### Option 2: Direct Provider Payment
```python
POST /members/bills/pay_bill_direct/
{
    "bill_id": "bill-uuid",
    "provider": "paystack",  # or "flutterwave"
    "amount": "5000.00",     # Optional, defaults to remaining amount
    "callback_url": "https://yourapp.com/payment/callback"
}
# Response includes payment_url for redirect to provider
```

### Creating Recurring Payment (Members)
```python
POST /members/recurring-payments/create/
{
    "title": "Monthly Service Charge",
    "amount": "5000.00",
    "frequency": "monthly",
    "start_date": "2025-02-01T00:00:00Z",
    "description": "Automated monthly service charge payment"
}
```

## Error Handling

The system provides comprehensive error handling with:

### Error Types
- `INSUFFICIENT_FUNDS` - Not enough balance
- `INVALID_CARD` - Invalid card details
- `EXPIRED_CARD` - Card has expired
- `DECLINED_CARD` - Card declined by bank
- `NETWORK_ERROR` - Network connectivity issues
- `PROVIDER_ERROR` - Payment provider errors
- `TIMEOUT_ERROR` - Request timeout
- `AUTHENTICATION_ERROR` - Authentication failures

### Recovery Options
- Retry mechanisms with exponential backoff
- Alternative payment methods
- User-friendly error messages
- Admin notifications for critical errors

## Notifications

The system sends email notifications for:

### Bill Notifications
- New bill created (pending acknowledgment)
- **Bill acknowledgment confirmations**
- **Bill dispute alerts to admins**
- Bill payment reminders
- Overdue bill alerts
- Payment confirmations (wallet and direct payments)
- **Cluster wallet credit notifications**
- Bill cancellations

### Recurring Payment Notifications
- Setup confirmations
- Payment reminders
- Payment processed confirmations
- Payment failures
- Payment paused/resumed/cancelled

### Error Notifications
- Payment failures with recovery options
- Recurring payment failures
- Admin alerts for critical errors

## Security Features

- **Wallet PINs**: Optional PIN protection for transactions
- **Transaction validation**: Amount and balance validation
- **Webhook signature verification**: Secure webhook processing
- **Multi-tenant isolation**: Estate-based data separation
- **Permission-based access**: Role-based API access control
- **Audit trails**: Complete transaction history tracking

## Testing

Comprehensive test suite included in `core/common/tests/test_wallet_models.py`:

- Wallet operations and balance management
- Transaction processing and status updates
- Bill creation and payment processing
- Recurring payment automation
- Error handling and recovery options

Run tests:
```bash
python manage.py test core.common.tests.test_wallet_models
```

## Monitoring and Maintenance

### Logging
All payment operations are logged with appropriate levels:
- INFO: Successful operations
- WARNING: Recoverable issues
- ERROR: Failed operations
- CRITICAL: System-level failures

### Metrics
Track key metrics:
- Transaction success/failure rates
- Payment processing times
- Recurring payment success rates
- Error frequency by type

### Maintenance Tasks
Regular maintenance includes:
- Processing recurring payments (every hour)
- Sending payment reminders (daily)
- Checking overdue bills (daily)
- Cleaning up old transaction logs (monthly)

## Future Enhancements

Potential improvements:
- Mobile money integration
- Cryptocurrency payments
- Payment analytics dashboard
- Automated reconciliation
- Multi-currency support
- Payment splitting for shared bills
- Installment payment plans