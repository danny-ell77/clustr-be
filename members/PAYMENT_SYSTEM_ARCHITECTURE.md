# Payment System Architecture - Members App

## Overview

The ClustR payment system is a comprehensive, enterprise-grade financial management platform designed for multi-tenant estate/cluster management. It handles individual and shared bills, recurring payments, utility provider integrations, and wallet-based transactions.

---

## Core Components

### 1. Bill Management

#### Bill Categories
- **`USER_MANAGED`** - Individual bills assigned to specific users
  - Single payer model
  - Tracks payments via `paid_amount` field
  - Requires acknowledgment before payment
  - Examples: Personal rent, individual utility bills
  
- **`CLUSTER_MANAGED`** - Shared bills for entire cluster
  - Multi-payer model
  - Tracks payments via `Transaction` aggregation
  - No acknowledgment required
  - Examples: Security fees, common area maintenance

#### Bill Types
- `ELECTRICITY`, `WATER`, `SECURITY`, `MAINTENANCE`
- `ELECTRICITY_UTILITY`, `WATER_UTILITY`, `GAS_UTILITY` (for direct provider payments)
- `RENT`, `SERVICE_CHARGE`, `WASTE_MANAGEMENT`, `INTERNET`

#### Bill Status Flow
```
DRAFT → PENDING_ACKNOWLEDGMENT → ACKNOWLEDGED → PENDING → PAID
                                      ↓
                                  DISPUTED → (resolution) → PENDING
                                      ↓
                                  OVERDUE (if past due date)
                                      ↓
                                PARTIALLY_PAID → PAID
```

#### Key Bill Methods
- `acknowledge()` - User acknowledges receipt of bill
- `dispute(reason)` - Create dispute for incorrect bill
- `can_be_paid_by(user)` - Check if user can pay (acknowledgment, due date, authorization)
- `mark_as_paid()` - Mark bill as fully paid
- `add_payment(amount, transaction)` - Record payment
- `is_overdue` - Check if past due date
- `is_fully_paid` - Check if total paid equals amount
- `remaining_amount` - Calculate outstanding balance

---

### 2. Bill Disputes

#### Dispute Status Flow
```
OPEN → UNDER_REVIEW → RESOLVED
                   → REJECTED
                   → WITHDRAWN (by user)
```

#### Key Features
- **Unique Constraint**: One active dispute per user per bill
- **Time Tracking**: `days_since_created` property
- **Status Methods**: `resolve()`, `reject()`, `withdraw()`, `set_under_review()`
- **Active Check**: `is_active` property (OPEN or UNDER_REVIEW)

---

### 3. Recurring Payments

#### Payment Frequencies
- `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`, `YEARLY`

#### Payment Status
- `ACTIVE` - Processing payments on schedule
- `PAUSED` - Temporarily stopped (manual or auto after failures)
- `CANCELLED` - Permanently stopped
- `EXPIRED` - Reached end date

#### Two Payment Types

**A. Bill-Linked Recurring Payments**
- Tied to specific `Bill` (USER_MANAGED or CLUSTER_MANAGED)
- Automatically pays bill on schedule
- Uses wallet balance
- Example: Auto-pay monthly rent

**B. Utility Recurring Payments**
- Linked to `UtilityProvider` instead of bill
- Direct purchases from external providers
- Requires `customer_id` (meter number)
- Example: Auto-purchase electricity monthly

#### Key Features
- **Failure Handling**: Tracks `failed_attempts`, auto-pauses after `max_failed_attempts` (default: 3)
- **Spending Limits**: Optional `spending_limit` to cap payments
- **Payment Sources**: `wallet` or `direct` (external provider)
- **Schedule Management**: `calculate_next_payment_date()` based on frequency
- **Control Methods**: `pause()`, `resume()`, `cancel()`

---

### 4. Wallet System

#### Wallet Fields
- `balance` - Total wallet balance
- `available_balance` - Balance minus frozen amounts
- `currency` - Currency code (default: NGN)
- `status` - `ACTIVE`, `SUSPENDED`, `FROZEN`
- `is_pin_set` - Security PIN configured
- `last_transaction_at` - Last activity timestamp

#### Key Operations
- **Deposit**: Initialize payment via external provider (Paystack/Flutterwave)
- **Payment**: Deduct from balance for bills
- **Freeze/Unfreeze**: Lock funds temporarily
- **Balance Updates**: Automatic via transactions

---

### 5. Transactions

#### Transaction Types
- `DEPOSIT` - Adding funds to wallet
- `WITHDRAWAL` - Removing funds from wallet
- `PAYMENT` - Paying bills
- `BILL_PAYMENT` - Specific bill payment
- `REFUND` - Reversing payment
- `TRANSFER` - Moving funds between wallets

#### Transaction Status
- `PENDING` - Initiated but not processed
- `PROCESSING` - Being processed
- `COMPLETED` - Successfully processed
- `FAILED` - Processing failed
- `CANCELLED` - Cancelled before completion
- `REVERSED` - Completed but reversed

#### Key Features
- **Idempotency**: Prevents duplicate transactions
- **Audit Trail**: Complete history of all financial operations
- **Filtering**: By type, status, date range
- **Pagination**: For large transaction histories

---

### 6. Utility Provider Integration

#### Provider Fields
- `provider_type` - Type of utility (electricity, water, gas)
- `provider_code` - Unique identifier
- `api_endpoint` - External API URL
- `min_amount` / `max_amount` - Payment limits
- `is_active` - Provider availability

#### Key Operations
- `validate_customer(customer_id)` - Verify meter/account number
- `purchase_utility(customer_id, amount)` - Direct purchase
- `is_amount_valid(amount)` - Check against limits
- `setup_recurring_utility_payment()` - Enable automation

---

## Payment Workflows

### Workflow 1: User-Managed Bill Payment (Wallet)
```
1. Admin creates USER_MANAGED bill for user
2. Bill status: PENDING_ACKNOWLEDGMENT
3. User acknowledges bill → status: ACKNOWLEDGED
4. User pays from wallet → creates Transaction
5. Bill.add_payment() updates paid_amount
6. If fully paid → status: PAID
```

### Workflow 2: Cluster-Managed Bill Payment
```
1. Admin creates CLUSTER_MANAGED bill (user_id = NULL)
2. Bill status: PENDING
3. Multiple users can pay portions
4. Each payment creates Transaction linked to bill
5. System aggregates transactions to track total paid
6. When total >= bill amount → status: PAID
```

### Workflow 3: Direct Bill Payment (External Provider)
```
1. User initiates direct payment
2. System creates PENDING transaction
3. Calls payments.initialize() → returns payment URL
4. User completes payment on provider site
5. Webhook verifies payment
6. Transaction status: COMPLETED
7. Bill marked as paid
```

### Workflow 4: Recurring Payment Processing
```
1. Cron job checks for due recurring payments
2. For each due payment:
   - Check wallet balance
   - If sufficient → create transaction
   - Update bill or purchase utility
   - Update next_payment_date
   - Increment total_payments
3. On failure:
   - Increment failed_attempts
   - If >= max_failed_attempts → PAUSE
```

### Workflow 5: Bill Dispute Resolution
```
1. User disputes bill with reason
2. BillDispute created with OPEN status
3. Admin reviews → set_under_review()
4. Admin decision:
   - resolve() → Bill can be paid again
   - reject() → Dispute closed, bill remains
5. User can withdraw() at any time before resolution
```

---

## API Endpoints (ViewSets)

### BillViewSet
- `GET /bills/my-bills/` - List user's bills (with filters)
- `GET /bills/summary/` - Get bill summary (pending, paid, overdue)
- `POST /bills/{id}/acknowledge-bill/` - Acknowledge bill
- `POST /bills/{id}/dispute-bill/` - Dispute bill
- `POST /bills/{id}/pay-bill/` - Pay from wallet
- `POST /bills/pay-bill-direct/` - Pay via external provider

### RecurringPaymentViewSet
- `POST /recurring-payments/` - Create recurring payment
- `GET /recurring-payments/my-payments/` - List user's recurring payments
- `POST /recurring-payments/pause-payment/` - Pause recurring payment
- `POST /recurring-payments/resume-payment/` - Resume paused payment
- `POST /recurring-payments/cancel-payment/` - Cancel recurring payment

### WalletViewSet
- `GET /wallets/balance/` - Get wallet balance
- `POST /wallets/deposit/` - Initialize wallet deposit
- `GET /wallets/transactions/` - Get transaction history (with filters)

---

## Key Business Rules

### Payment Authorization
- **USER_MANAGED Bills**: Only assigned user can pay
- **CLUSTER_MANAGED Bills**: Any cluster member can pay
- **Acknowledgment**: Required for USER_MANAGED before payment
- **Due Date**: Configurable `allow_payment_after_due` flag

### Dispute Rules
- Cannot dispute fully paid bills
- One active dispute per user per bill
- Disputed bills cannot be paid until resolved
- Users can withdraw disputes before resolution

### Recurring Payment Rules
- Always tied to specific user (even for cluster bills)
- Auto-pauses after 3 consecutive failures (configurable)
- Respects spending limits for utility payments
- Expires automatically if end_date reached

### Transaction Rules
- Idempotency keys prevent duplicates
- All wallet operations create transactions
- Transactions are immutable (use REVERSED status for corrections)
- Complete audit trail maintained

---

## Database Schema Highlights

### Critical Relationships
```
Cluster
  ├── Bills (many)
  │     ├── BillDisputes (many)
  │     └── RecurringPayments (many, optional)
  ├── Wallets (many, one per user)
  │     ├── Transactions (many)
  │     └── RecurringPayments (many)
  └── UtilityProviders (many)
        └── RecurringPayments (many, for utility automation)
```

### Important Indexes
- `Bill`: `(cluster, user_id)`, `(status)`, `(due_date)`
- `RecurringPayment`: `(user_id, cluster)`, `(status)`, `(next_payment_date)`
- `Transaction`: `(wallet)`, `(status)`, `(type)`, `(created_at)`

---

## Testing Strategy

### Unit Tests (TestCase)
- Bill model methods (acknowledge, dispute, payment calculations)
- BillDispute status transitions
- RecurringPayment scheduling logic
- Utility provider validation

### Integration Tests (APITestCase)
- BillViewSet endpoints (full request/response cycle)
- RecurringPaymentViewSet workflows
- WalletViewSet operations
- Authentication and authorization
- End-to-end payment flows

### Test Coverage Areas
1. **Bill Categories**: USER_MANAGED vs CLUSTER_MANAGED differences
2. **Payment Paths**: Wallet, direct, recurring
3. **Status Transitions**: All valid state changes
4. **Error Handling**: Insufficient balance, invalid amounts, unauthorized access
5. **Edge Cases**: Partial payments, concurrent payments, expired schedules
6. **Utility Integration**: Provider validation, amount limits, automation

---

## Security Considerations

### Financial Safety
- **Idempotency Keys**: Prevent duplicate charges
- **Spending Limits**: Cap recurring payment amounts
- **Balance Checks**: Verify sufficient funds before processing
- **Transaction Immutability**: No direct edits, use reversals

### Access Control
- **User Isolation**: Users only see/pay their own USER_MANAGED bills
- **Cluster Scoping**: All queries filtered by cluster context
- **Authorization Checks**: `can_be_paid_by()` validates permissions
- **Dispute Constraints**: One active dispute per user per bill

### Audit & Compliance
- **Complete Transaction History**: Every financial operation logged
- **Status Tracking**: Full lifecycle of bills and payments
- **Metadata Storage**: Additional context in JSON fields
- **Timestamp Tracking**: Created, modified, processed timestamps

---

## Future Enhancements (Potential)

- Multi-currency support expansion
- Payment plan/installment scheduling
- Automated late fee calculation
- Bill splitting for roommates
- Integration with more utility providers
- Mobile money support
- Cryptocurrency payments
- Export financial reports
- Tax document generation

---

## Related Files

### Models
- `core/common/models/payments/bill.py` - Bill and BillDispute models
- `core/common/models/payments/recurring_payment.py` - RecurringPayment model
- `core/common/models/payments/wallet.py` - Wallet model
- `core/common/models/payments/transaction.py` - Transaction model
- `core/common/models/payments/utility_provider.py` - UtilityProvider model

### Business Logic
- `core/common/includes/bills.py` - Bill management functions
- `core/common/includes/recurring_payments.py` - Recurring payment functions
- `core/common/includes/payments.py` - Payment processing functions
- `core/common/includes/utilities.py` - Utility provider integration

### API Layer
- `members/views_payment.py` - BillViewSet, RecurringPaymentViewSet, WalletViewSet

### Tests
- `members/tests/test_payments.py` - Bill payment integration tests
- `members/tests/test_recurring_payments.py` - Recurring payment tests
- `members/tests/test_wallets.py` - Wallet operation tests
- `members/tests/test_bill_models.py` - Bill model unit tests
- `members/tests/test_bill_dispute_models.py` - Dispute model unit tests
- `members/tests/test_recurring_payment_models.py` - Recurring payment model tests
- `members/tests/test_utility_bills.py` - Utility-specific tests

---

**Last Updated**: 2026-01-03  
**Documentation Version**: 1.0  
**System Status**: Production-Ready
