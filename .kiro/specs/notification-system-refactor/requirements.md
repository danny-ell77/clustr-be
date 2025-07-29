# Notification System Refactor - Requirements Document

## Introduction

The current notification system in ClustR is bloated with many hardcoded methods, placeholder email types, and lacks proper structure. This refactor aims to create an ultra-lean, priority-based notification system that supports email notifications with user preferences, proper estate-scoped multi-tenancy, and easy extensibility for future channels.

## Requirements

### Requirement 1: Priority-Based Event System

**User Story:** As a system administrator, I want notifications to be prioritized so that critical alerts bypass user preferences while regular notifications respect user settings.

#### Acceptance Criteria

1. WHEN a notification event is defined THEN it SHALL have an integer priority value where lower numbers indicate higher priority
2. WHEN a critical event (priority ≤ 10) is triggered THEN the system SHALL bypass user notification preferences
3. WHEN a non-critical event (priority > 10) is triggered THEN the system SHALL respect user notification preferences
4. WHEN an event is processed THEN the system SHALL be able to determine its priority level (CRITICAL, HIGH, MEDIUM, LOW)

### Requirement 2: Estate-Scoped Multi-Tenant Notifications

**User Story:** As an estate management system, I want all notifications to be properly scoped to estates to ensure data isolation between different properties.

#### Acceptance Criteria

1. WHEN a notification is sent THEN it SHALL include estate context for proper tenant isolation
2. WHEN user preferences are checked THEN they SHALL be filtered by the user's estate membership
3. WHEN notification logs are created THEN they SHALL be associated with the appropriate estate
4. WHEN notifications are queried THEN they SHALL be filtered by estate scope

### Requirement 3: User Preference Management

**User Story:** As a resident or management user, I want to control which types of notifications I receive via email so that I'm not overwhelmed with unwanted messages.

#### Acceptance Criteria

1. WHEN a user sets notification preferences THEN they SHALL be able to enable/disable specific notification types
2. WHEN a non-critical notification is sent THEN the system SHALL check user preferences before sending
3. WHEN a user has disabled a notification type THEN they SHALL NOT receive that type of notification
4. WHEN user preferences don't exist THEN the system SHALL use sensible defaults

### Requirement 4: Clean Email Channel Implementation

**User Story:** As a developer, I want a clean email notification implementation that handles templates and sending without code duplication.

#### Acceptance Criteria

1. WHEN an email notification is sent THEN it SHALL use a consistent template system
2. WHEN email context is provided THEN it SHALL be properly formatted for the email template
3. WHEN email sending fails THEN the system SHALL log the error and return appropriate status
4. WHEN multiple recipients are specified THEN the system SHALL handle bulk sending efficiently

### Requirement 5: Notification Logging and Audit

**User Story:** As a system administrator, I want to track all notification attempts for debugging and audit purposes.

#### Acceptance Criteria

1. WHEN a notification is sent THEN the system SHALL log the attempt with timestamp, recipient, event type, and success status
2. WHEN a notification fails THEN the system SHALL log the error message
3. WHEN notification logs are queried THEN they SHALL be filterable by estate, user, event type, and date range
4. WHEN notification logs are created THEN they SHALL include all relevant context for debugging

### Requirement 6: Lean API Design

**User Story:** As a developer, I want a simple API for sending notifications that doesn't require knowledge of internal implementation details.

#### Acceptance Criteria

1. WHEN sending a notification THEN the API SHALL require only event type, recipients, estate context, and message context
2. WHEN the notification manager is called THEN it SHALL handle all routing, preference checking, and channel selection internally
3. WHEN different notification events are triggered THEN they SHALL use the same consistent API
4. WHEN the system needs to be extended THEN new channels SHALL be addable without changing the core API

### Requirement 7: Clean System Replacement

**User Story:** As a developer, I want to completely replace the existing bloated notification system with a clean, lean implementation.

#### Acceptance Criteria

1. WHEN the new system is implemented THEN it SHALL replace all existing notification utilities
2. WHEN the old notification code is removed THEN all references SHALL be updated to use the new system
3. WHEN the refactor is complete THEN there SHALL be no placeholder email types or hardcoded methods
4. WHEN the new system is deployed THEN it SHALL have a clean, minimal codebase focused only on essential functionality