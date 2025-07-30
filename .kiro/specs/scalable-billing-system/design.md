# Scalable Billing System - Design

## Architecture Overview

The scalable billing system redesigns the current Bill model to eliminate the one-to-many relationship that causes memory constraints with large estates. The new architecture uses estate-scoped bills with optional user targeting and ManyToMany acknowledgments.

## Database Design

### Modified Bill Model

```python
class Bill(AbstractClusterModel):
    # Core identification
    bill_number = CharField(max_length=50, unique=True)
    estate = ForeignKey(Estate)  # Always required
    user = ForeignKey(User, null=True, blank=True)  # Optional for user-specific bills
    
    # Bill details
    title = CharField(max_length=200)
    description = TextField(blank=True, null=True)
    amount = DecimalField(max_digits=15, decimal_places=2)
    due_date = DateTimeField()
    
    # Payment control
    allow_payment_after_due = BooleanField(default=True)
    
    # Acknowledgment tracking (only for estate-wide bills)
    acknowledged_by = ManyToManyField(User, blank=True)
    
    # Existing fields maintained
    type = CharField(choices=BillType.choices)
    currency = CharField(default="NGN")
    metadata = JSONField(blank=True, null=True)
```

### Key Changes from Current Model
1. **Removed**: `user_id` as required field
2. **Added**: `estate` as required foreign key
3. **Modified**: `user` as optional foreign key for user-specific bills
4. **Added**: `acknowledged_by` ManyToMany field
5. **Added**: `allow_payment_after_due` boolean flag
6. **Removed**: `status` field (derived from acknowledgments and transactions)

### Bill Types

#### Estate-wide Bills
- `user = null`
- Affects all estate members
- Uses `acknowledged_by` ManyToMany field
- Bulk notifications to all estate members

#### User-specific Bills
- `user = specific_user`
- Affects only the specified user
- Uses `acknowledged_by` for consistency
- Notification only to target user

## API Design

### Management Endpoints

#### Create Bill
```
POST /management/bills/
{
    "title": "Monthly Service Charge",
    "description": "Service charge for January 2025",
    "amount": "5000.00",
    "due_date": "2025-02-15T23:59:59Z",
    "type": "service_charge",
    "user_id": null,  // null for estate-wide, UUID for user-specific
    "allow_payment_after_due": true
}
```

#### List Users with Bill Status
```
GET /management/users/?include_bill_status=true
Response:
{
    "results": [
        {
            "id": "user-uuid",
            "name": "John Doe",
            "bill_status": {
                "unacknowledged_bills": 2,
                "unpaid_bills": 1,
                "failed_payments": 0
            }
        }
    ]
}
```

### Member Endpoints

#### List User Bills
```
GET /members/bills/
Response:
{
    "results": [
        {
            "id": "bill-uuid",
            "title": "Monthly Service Charge",
            "amount": "5000.00",
            "due_date": "2025-02-15T23:59:59Z",
            "is_acknowledged": false,
            "is_paid": false,
            "can_pay": false,  // false if not acknowledged
            "is_overdue": false
        }
    ]
}
```

#### Acknowledge Bill
```
POST /members/bills/{bill_id}/acknowledge/
Response:
{
    "success": true,
    "message": "Bill acknowledged successfully",
    "can_pay": true
}
```

#### Pay Bill
```
POST /members/bills/{bill_id}/pay/
{
    "payment_method": "wallet",
    "amount": "5000.00"
}
```

## Business Logic

### Bill Creation Logic

```python
def create_bill(estate, title, amount, due_date, user=None, **kwargs):
    """
    Create a new bill for estate or specific user.
    
    Args:
        estate: Estate instance
        user: Optional User instance for user-specific bills
        **kwargs: Additional bill fields
    """
    bill = Bill.objects.create(
        estate=estate,
        user=user,
        title=title,
        amount=amount,
        due_date=due_date,
        **kwargs
    )
    
    # Send notifications
    if user:
        # User-specific bill
        notify_user_specific_bill(bill, user)
    else:
        # Estate-wide bill
        notify_estate_wide_bill(bill, estate)
    
    return bill
```

### Acknowledgment Logic

```python
def acknowledge_bill(bill, user):
    """
    Acknowledge a bill for fraud protection.
    
    Args:
        bill: Bill instance
        user: User acknowledging the bill
    """
    # Validate user can acknowledge this bill
    if bill.user and bill.user != user:
        raise PermissionError("Cannot acknowledge bill for another user")
    
    if not bill.user and user.estate != bill.estate:
        raise PermissionError("Cannot acknowledge bill from different estate")
    
    # Add acknowledgment
    bill.acknowledged_by.add(user)
    
    # Send notification
    notify_bill_acknowledged(bill, user)
    
    return True
```

### Payment Logic

```python
def pay_bill(bill, user, amount, payment_method):
    """
    Process bill payment with acknowledgment check.
    
    Args:
        bill: Bill instance
        user: User making payment
        amount: Payment amount
        payment_method: Payment method
    """
    # Check acknowledgment
    if not bill.acknowledged_by.filter(id=user.id).exists():
        raise ValidationError("Bill must be acknowledged before payment")
    
    # Check due date if configured
    if not bill.allow_payment_after_due and bill.is_overdue:
        raise ValidationError("Payment not allowed after due date")
    
    # Process payment (existing logic)
    transaction = process_payment(user, amount, payment_method)
    
    # Link transaction to bill
    transaction.bill = bill
    transaction.save()
    
    return transaction
```

## Query Optimization

### Admin Dashboard Queries

```python
def get_users_with_bill_status(estate):
    """
    Efficient query for admin dashboard user list with bill status.
    """
    users = User.objects.filter(estate=estate).select_related('profile')
    
    # Get estate bills
    estate_bills = Bill.objects.filter(estate=estate, user__isnull=True)
    
    # Annotate users with bill status
    users = users.annotate(
        unacknowledged_bills=Count(
            'estate__bills',
            filter=Q(estate__bills__user__isnull=True) & 
                   ~Q(estate__bills__acknowledged_by=F('id'))
        ),
        unpaid_bills=Count(
            'transactions',
            filter=Q(transactions__bill__estate=estate) &
                   Q(transactions__status='failed')
        )
    )
    
    return users
```

### User Bill Queries

```python
def get_user_bills(user):
    """
    Get all bills relevant to a user (estate-wide + user-specific).
    """
    estate_bills = Q(estate=user.estate, user__isnull=True)
    user_bills = Q(user=user)
    
    bills = Bill.objects.filter(estate_bills | user_bills).annotate(
        is_acknowledged=Exists(
            Bill.acknowledged_by.through.objects.filter(
                bill=OuterRef('pk'),
                user=user
            )
        ),
        is_paid=Exists(
            Transaction.objects.filter(
                bill=OuterRef('pk'),
                wallet__user_id=user.id,
                status='completed'
            )
        )
    )
    
    return bills
```

## Notification Integration

### Estate-wide Bill Notifications

```python
def notify_estate_wide_bill(bill, estate):
    """
    Notify all estate members about new bill.
    """
    recipients = User.objects.filter(estate=estate)
    
    NotificationManager.send(
        event_name=NotificationEvents.PAYMENT_DUE,
        recipients=list(recipients),
        cluster=estate.cluster,
        context={
            'bill_id': str(bill.id),
            'bill_title': bill.title,
            'amount': str(bill.amount),
            'due_date': bill.due_date.isoformat(),
            'estate_name': estate.name
        }
    )
```

### User-specific Bill Notifications

```python
def notify_user_specific_bill(bill, user):
    """
    Notify specific user about their bill.
    """
    NotificationManager.send(
        event_name=NotificationEvents.PAYMENT_DUE,
        recipients=[user],
        cluster=bill.estate.cluster,
        context={
            'bill_id': str(bill.id),
            'bill_title': bill.title,
            'amount': str(bill.amount),
            'due_date': bill.due_date.isoformat(),
            'is_user_specific': True
        }
    )
```

## Security Considerations

### Permission Checks

```python
class BillPermissionMixin:
    """
    Mixin for bill-related permission checks.
    """
    
    def check_bill_management_permission(self, user):
        """Check if user can manage bills."""
        return user.has_perm(f'payments.{PaymentsPermissions.ManageBill}')
    
    def check_bill_access_permission(self, user, bill):
        """Check if user can access specific bill."""
        if bill.user:
            # User-specific bill
            return bill.user == user
        else:
            # Estate-wide bill
            return user.estate == bill.estate
```

### Data Isolation

```python
class BillQuerySet(models.QuerySet):
    """
    Custom queryset for estate-scoped bill queries.
    """
    
    def for_estate(self, estate):
        """Filter bills for specific estate."""
        return self.filter(estate=estate)
    
    def for_user(self, user):
        """Filter bills accessible to specific user."""
        estate_bills = Q(estate=user.estate, user__isnull=True)
        user_bills = Q(user=user)
        return self.filter(estate_bills | user_bills)
```

## Performance Optimizations

### Database Indexes

```python
class Bill(AbstractClusterModel):
    class Meta:
        indexes = [
            models.Index(fields=['estate', 'user']),
            models.Index(fields=['estate', 'due_date']),
            models.Index(fields=['user', 'due_date']),
            models.Index(fields=['due_date', 'allow_payment_after_due']),
        ]
```

### Caching Strategy

```python
def get_user_bill_status(user):
    """
    Get user bill status with caching.
    """
    cache_key = f"user_bill_status:{user.id}"
    status = cache.get(cache_key)
    
    if status is None:
        status = calculate_user_bill_status(user)
        cache.set(cache_key, status, timeout=300)  # 5 minutes
    
    return status
```

## Migration Strategy

Since this is new development, no data migration is required. The new Bill model will be created with the updated structure from the start.

## Testing Strategy

### Unit Tests
- Bill creation (estate-wide and user-specific)
- Acknowledgment logic
- Payment validation
- Permission checks

### Integration Tests
- API endpoints
- Notification integration
- Query performance
- Security validation

### Performance Tests
- Large estate bill creation
- Concurrent acknowledgments
- Admin dashboard queries
- User bill list queries

## Monitoring and Metrics

### Key Metrics
- Bill creation time
- Acknowledgment rate
- Payment success rate
- Query response times
- Memory usage during bill operations

### Alerts
- High bill creation latency
- Low acknowledgment rates
- Payment failures
- Database query timeouts