# Scalable Billing System - Requirements

## Overview
Redesign the billing system to handle large estates (2,000-5,000 users) efficiently by eliminating the current one-to-many Bill→User relationship that causes memory constraints during bulk bill creation.

## Current Problem
- Bills are created individually for each user (2,000-5,000 records per billing cycle)
- Causes memory constraints and database performance issues
- Inefficient storage with duplicate bill data

## Proposed Solution
- Bills are estate-scoped with optional user targeting
- Use ManyToMany relationship for acknowledgments only
- Maintain transaction linking for actual payments

## Core Requirements

### 1. Bill Model Restructure
**ID**: REQ-001  
**Priority**: High  
**Description**: Modify Bill model to support both estate-wide and user-specific bills

#### Acceptance Criteria
1. WHEN creating a bill THEN it MUST be linked to an estate
2. WHEN creating a user-specific bill THEN it MAY be linked to a specific user (nullable)
3. WHEN user field is null THEN the bill applies to all estate members
4. WHEN user field is set THEN the bill applies only to that specific user

### 2. Acknowledgment System
**ID**: REQ-002  
**Priority**: High  
**Description**: Implement acknowledgment tracking for both bill types

#### Acceptance Criteria
1. WHEN a bill is estate-wide THEN users MUST acknowledge before payment
2. WHEN a bill is user-specific THEN the target user MUST acknowledge before payment
3. WHEN a user acknowledges THEN they are added to acknowledged_by ManyToMany field
4. WHEN acknowledgment is recorded THEN it serves as fraud protection

### 3. Payment Control
**ID**: REQ-003  
**Priority**: Medium  
**Description**: Allow admins to control payment timing

#### Acceptance Criteria
1. WHEN admin creates a bill THEN they CAN set allow_payment_after_due flag
2. WHEN due date passes AND allow_payment_after_due is false THEN payment MUST be blocked
3. WHEN due date passes AND allow_payment_after_due is true THEN payment MUST be allowed
4. WHEN payment is attempted THEN system MUST check due date and flag

### 4. Permission System
**ID**: REQ-004  
**Priority**: High  
**Description**: Secure bill management with proper permissions

#### Acceptance Criteria
1. WHEN a user tries to create a bill THEN the system SHALL verify they have PaymentsPermissions.ManageBill permission
2. WHEN a user tries to modify a bill THEN the system SHALL verify they have PaymentsPermissions.ManageBill permission
3. WHEN a user without ManageBill permission tries to access bill management THEN the system SHALL deny access
4. WHEN an admin or cluster staff has ManageBill permission THEN the system SHALL allow bill management operations

### 5. Notification Integration
**ID**: REQ-005  
**Priority**: Medium  
**Description**: Integrate with existing NotificationManager for bill events

#### Acceptance Criteria
1. WHEN an estate-wide bill is created THEN all estate members MUST be notified
2. WHEN a user-specific bill is created THEN only the target user MUST be notified
3. WHEN a bill is acknowledged THEN admin SHOULD be notified
4. WHEN a bill is disputed THEN admin MUST be notified with high priority
5. WHEN payment fails THEN user MUST be notified with retry options

### 6. API Design
**ID**: REQ-006  
**Priority**: High  
**Description**: Design efficient APIs for bill management and user interactions

#### Acceptance Criteria
1. WHEN admin fetches user list THEN system MUST provide bill status for hover display
2. WHEN user fetches bills THEN system MUST show only relevant bills (estate-wide + user-specific)
3. WHEN user acknowledges bill THEN system MUST update acknowledgment status
4. WHEN user pays bill THEN system MUST create transaction and update bill status

### 7. Data Migration
**ID**: REQ-007  
**Priority**: Low  
**Description**: Handle transition from current system (not applicable - new development)

#### Acceptance Criteria
1. WHEN system is deployed THEN no existing data migration is required
2. WHEN new bill structure is implemented THEN it MUST be compatible with existing transaction system

### 8. Performance Requirements
**ID**: REQ-008  
**Priority**: High  
**Description**: Ensure system performs well with large user bases

#### Acceptance Criteria
1. WHEN creating estate-wide bill THEN system MUST create only 1 record regardless of user count
2. WHEN 5,000 users acknowledge bill THEN system MUST handle ManyToMany updates efficiently
3. WHEN admin views user list THEN bill status queries MUST complete within 2 seconds
4. WHEN user views bills THEN response time MUST be under 500ms

## Business Rules

### Bill Types
- **Estate-wide bills**: `user=null`, affects all estate members
- **User-specific bills**: `user=specific_user`, affects only that user

### Acknowledgment Rules
- Both bill types require acknowledgment before payment
- Acknowledgment serves as fraud protection
- Only target users can acknowledge their bills

### Payment Rules
- Payments create Transaction records linking user to bill
- Failed payments can be retried (existing retry mechanism continues)
- Due date enforcement is configurable per bill

### Notification Rules
- Estate-wide bills notify all members
- User-specific bills notify only target user
- Use existing NotificationEvents: PAYMENT_DUE, BILL_ACKNOWLEDGED, BILL_DISPUTED, PAYMENT_FAILED

## Technical Constraints

### Database
- Use existing Django ORM patterns
- Maintain referential integrity
- Optimize for estate-based queries

### Security
- Maintain estate-level data isolation
- Use existing permission system
- Validate user access to bills

### Integration
- Compatible with existing Transaction model
- Use existing NotificationManager
- Maintain existing payment provider integrations

## Success Metrics

### Performance
- Bill creation time: < 100ms regardless of estate size
- User bill list query: < 500ms
- Admin dashboard query: < 2 seconds

### Scalability
- Support estates with 5,000+ users
- Handle 100+ concurrent bill acknowledgments
- Process 1,000+ simultaneous payments

### User Experience
- Clear bill status visibility
- Intuitive acknowledgment process
- Reliable payment retry mechanism