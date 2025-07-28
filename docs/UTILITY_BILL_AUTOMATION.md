# Utility Bill Automation Feature

## Overview

This document outlines the plan for implementing automated utility bill payments in the ClustR application, allowing users to automate payments for electricity, water, internet, and other utility services directly from their wallets.

## Current State

### Existing Infrastructure
- **Payment Providers**: Paystack and Flutterwave integrations
- **Bill System**: Cluster-based bills only (`AbstractClusterModel`)
- **Recurring Payments**: Limited to cluster bills with wallet debiting
- **Transaction Handling**: Comprehensive transaction and error handling system
- **Bill Types**: Includes `ELECTRICITY` and `WATER` in `BillType` choices

### Current Limitations
- All bills are cluster-scoped
- No direct utility provider integration
- No differentiation between cluster bills and personal utility bills
- Missing utility-specific metadata (meter numbers, customer IDs, etc.)

## Proposed Solution

### Phase 1: Model Extensions

#### Enhanced Bill Types
```python
class BillType(models.TextChoices):
    # Existing cluster-based bills
    SECURITY = "security", _("Security")
    MAINTENANCE = "maintenance", _("Maintenance")
    SERVICE_CHARGE = "service_charge", _("Service Charge")
    WASTE_MANAGEMENT = "waste_management", _("Waste Management")
    
    # New utility bills (user-managed)
    ELECTRICITY_UTILITY = "electricity_utility", _("Electricity (Direct)")
    WATER_UTILITY = "water_utility", _("Water (Direct)")
    INTERNET_UTILITY = "internet_utility", _("Internet")
    CABLE_TV_UTILITY = "cable_tv_utility", _("Cable TV")
    OTHER = "other", _("Other")
```

#### Bill Category Classification
```python
class BillCategory(models.TextChoices):
    CLUSTER_MANAGED = "cluster_managed", _("Cluster Managed")
    USER_MANAGED = "user_managed", _("User Managed")
```

#### Enhanced Bill Model
- Add `category` field to distinguish cluster vs user bills
- Add `utility_provider` field for external providers
- Extend `metadata` to include utility-specific data
- Add `is_automated` flag for recurring utility payments

#### New UtilityProvider Model
```python
class UtilityProvider(models.Model):
    name = models.CharField(max_length=100)
    provider_type = models.CharField(choices=BillType.choices)
    api_provider = models.CharField(choices=[('paystack', 'Paystack'), ('flutterwave', 'Flutterwave')])
    provider_code = models.CharField(max_length=50)  # e.g., 'ikeja-electric'
    is_active = models.BooleanField(default=True)
```

### Phase 2: API Integration Layer

#### Utility Service Interface
```python
class UtilityServiceInterface(ABC):
    @abstractmethod
    def validate_customer(self, customer_id: str, provider_code: str) -> Dict[str, Any]
    
    @abstractmethod
    def get_customer_info(self, customer_id: str, provider_code: str) -> Dict[str, Any]
    
    @abstractmethod
    def purchase_utility(self, customer_id: str, amount: Decimal, provider_code: str) -> Dict[str, Any]
    
    @abstractmethod
    def get_utility_providers(self, service_type: str) -> List[Dict[str, Any]]
```

#### Provider-Specific Implementations
- **PaystackUtilityService**: Implement electricity/water purchases via Paystack Bills API  
- **FlutterwaveUtilityService**: Implement via Flutterwave Bills Payment API

### Phase 3: Enhanced Recurring Payment System

#### Extended RecurringPayment Model
- Add `utility_provider` foreign key
- Add `customer_id` field for utility accounts
- Add `payment_source` field (wallet vs direct payment)
- Enhance `process_payment()` method to handle utility payments

#### Utility-Specific Payment Processing
```python
class UtilityRecurringPayment(RecurringPayment):
    def process_utility_payment(self):
        # 1. Validate customer account
        # 2. Check wallet balance
        # 3. Process payment via utility API
        # 4. Handle success/failure
        # 5. Create transaction record
        # 6. Update payment history
```

### Phase 4: Business Logic Implementation

#### UtilityPaymentManager (New)
```python
class UtilityPaymentManager:
    @staticmethod
    def setup_recurring_utility_payment(user, utility_provider, customer_id, amount, frequency)
    
    @staticmethod
    def process_one_time_utility_payment(user, utility_provider, customer_id, amount)
    
    @staticmethod
    def validate_utility_customer(utility_provider, customer_id)
    
    @staticmethod
    def get_user_utility_bills(user, bill_type=None, status=None)
```

#### Enhanced Error Handling
- Extend `PaymentErrorType` with utility-specific errors
- Add utility provider error mapping
- Implement retry logic for utility payment failures

### Phase 5: User Interface & Control

#### User Management Methods
```python
# In Bill model
def is_utility_bill(self) -> bool:
    return self.category == BillCategory.USER_MANAGED

def can_automate_payment(self) -> bool:
    return self.is_utility_bill() and self.utility_provider is not None

# In RecurringPayment model  
def process_payment(self):
    if self.is_utility_payment():
        return self.process_utility_payment()
    else:
        return self.process_cluster_payment()  # existing logic
```

#### Automation Controls
- User can enable/disable automation per utility
- Set spending limits for automated payments
- Configure notification preferences
- View payment history and upcoming payments

## API Integration Details

### Flutterwave Bills Payment API
- **Endpoint**: `/bills`
- **Features**: Supports multiple utility providers, real-time transactions, verification
- **Supported Services**: Electricity, Water, Internet, Cable TV

### Paystack Bills API
- **Endpoint**: `/bill`
- **Features**: Direct billing integration with utility companies
- **Supported Services**: Electricity, Water, Internet, Cable TV

## Implementation Considerations

### Data Requirements
- Store utility-specific metadata (meter numbers, customer IDs, account numbers)
- Maintain payment history and transaction records
- Support multiple utility accounts per user

### Payment Logic
- Implement priority-based payment processing
- Handle failed automated payments with retry logic
- Set minimum wallet balance thresholds
- Support partial payments where applicable

### User Experience
- Opt-in feature with granular controls
- Spending limits per utility type
- Calendar-based and interval-based scheduling
- Comprehensive notification system

### Security & Reliability
- Secure storage of customer IDs and account numbers
- Transaction logging and audit trails
- Error handling and recovery mechanisms
- Rate limiting and fraud detection

## Technical Architecture

### Database Schema Changes
1. Add `category` and `utility_provider` fields to Bill model
2. Create UtilityProvider model
3. Extend RecurringPayment model for utility-specific fields
4. Add utility-specific error types

### API Layer
1. Create UtilityServiceInterface and implementations
2. Extend payment error handling for utility-specific errors
3. Add utility validation and customer lookup endpoints

### Business Logic
1. Implement UtilityPaymentManager
2. Extend existing payment processing workflows
3. Add automation controls and user management features

## Migration Strategy

### Phase 1: Foundation (Week 1-2)
- Create new models and extend existing ones
- Implement basic utility service interfaces
- Set up database migrations

### Phase 2: Core Functionality (Week 3-4)
- Implement utility payment processing
- Add recurring payment automation
- Create user management interfaces

### Phase 3: Integration & Testing (Week 5-6)
- Integrate with Paystack/Flutterwave APIs
- Implement comprehensive error handling
- Add logging and monitoring

### Phase 4: User Interface & Polish (Week 7-8)
- Create user-facing controls and settings
- Add notification systems
- Perform end-to-end testing

## Future Enhancements

### Advanced Features
- Smart scheduling based on usage patterns
- Integration with IoT devices for automatic meter readings
- Predictive analytics for bill amount estimation
- Multi-currency support for international utilities

### Additional Integrations
- Support for more utility providers
- Integration with bank APIs for direct debiting
- Mobile money integration (M-Pesa, etc.)
- Government utility subsidies handling

## Success Metrics

### Technical Metrics
- Payment success rate > 95%
- API response time < 2 seconds
- Error recovery rate > 90%
- Zero data loss incidents

### Business Metrics
- User adoption rate
- Automated payment volume
- Customer satisfaction scores
- Reduction in manual payment processing

## Risk Management

### Technical Risks
- API downtime from utility providers
- Payment processing failures
- Data synchronization issues
- Security vulnerabilities

### Mitigation Strategies
- Implement robust retry mechanisms
- Maintain backup payment methods
- Regular security audits
- Comprehensive monitoring and alerting

## Conclusion

The Utility Bill Automation feature will significantly enhance the ClustR platform by providing users with convenient, reliable, and secure automated utility payment capabilities. The phased implementation approach ensures minimal disruption to existing functionality while providing a solid foundation for future enhancements.

## Next Steps

1. Finalize technical specifications based on stakeholder feedback
2. Create detailed implementation timeline
3. Set up development environment and testing frameworks
4. Begin Phase 1 implementation

---

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: ClustR Development Team  
**Status**: Planning Phase
