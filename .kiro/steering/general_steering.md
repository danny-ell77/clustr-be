---
inclusion: always
---

# ClustR Estate Management Development Guidelines

## Project Architecture

ClustR follows a Django multi-app architecture with clear separation of concerns:

- **accounts**: User authentication, permissions, and profile management
- **core**: Shared models, utilities, and common functionality
- **members**: Resident-focused features and personal services
- **management**: Administrative functions and estate-wide operations

## Core Development Principles

### Lean Implementation
- Keep implementations minimal and focused on requirements in #[[file:.kiro/specs/clustr-estate-management/requirements.md]]
- Follow the task priorities outlined in #[[file:.kiro/specs/clustr-estate-management/tasks.md]]
- Adhere to architectural patterns defined in #[[file:.kiro/specs/clustr-estate-management/design.md]]
- Avoid unnecessary abstractions or over-engineering

### Multi-Tenant Architecture
- All data must be estate-scoped for proper tenant isolation
- Include estate filtering in all queries and API endpoints
- Use the existing estate context in authentication tokens
- Ensure proper data isolation between different estates

## Code Organization Patterns

### Model Placement
- **Core models**: Place shared models (Visitor, Announcement, IssueTicket, etc.) in `core/common/models.py`
- **User models**: Keep AccountUser and related models in `accounts` app
- **App-specific models**: Place models specific to management or members functionality in respective apps

### Utility Functions
- **Shared utilities**: Place in `core/common/utils.py` (file handling, notifications, code generation)
- **Authentication utilities**: Keep in `accounts` app
- **App-specific utilities**: Place in respective app directories

### API Endpoint Organization
- **Management endpoints**: Administrative functions, estate-wide operations
- **Members endpoints**: Resident-focused features, personal data management
- **Shared endpoints**: Use appropriate app based on primary user type

## Django Best Practices

### ViewSets and Permissions
- Use Django REST Framework ViewSets for consistent API patterns
- Implement proper permission classes for role-based access control
- Leverage existing permission system in `accounts.permissions`

### Database Patterns
- Use Django ORM efficiently with select_related and prefetch_related
- Implement proper indexing for estate-based queries
- Use Django migrations for all schema changes

### Error Handling
- Use consistent error response structure across all endpoints
- Implement proper validation using Django serializers
- Leverage existing error handling framework in core

## Security Requirements

### Authentication & Authorization
- Use existing JWT-based authentication system
- Implement proper role-based access control
- Ensure estate-level data isolation in all operations

### Data Protection
- Validate all user inputs to prevent injection attacks
- Use parameterized queries through Django ORM
- Implement proper file upload validation and storage

## Integration Patterns

### File Storage
- Use existing cloud storage integration for all file operations
- Implement secure file upload and retrieval mechanisms
- Store file metadata in database with proper estate scoping

### Notifications
- Leverage existing notification system in `core/common/utils.py`
- Support multiple notification channels (email, SMS, push)
- Implement notification preferences and opt-out mechanisms

### Payment Processing
- Use Paystack and Flutterwave integrations as specified
- Implement proper error handling for payment failures
- Maintain transaction history with proper audit trails

## Testing Standards

### Test Organization
- Place tests in respective app test directories
- Use Django's TestCase for database-dependent tests
- Implement proper test fixtures for multi-tenant scenarios

### Test Coverage
- Write unit tests for all business logic
- Implement integration tests for API endpoints
- Include security tests for authentication and authorization

## Performance Considerations

### Database Optimization
- Use appropriate database indexes for estate-based queries
- Implement pagination for large data sets
- Use Django's select_related and prefetch_related for efficient queries

### Caching Strategy
- Implement caching for frequently accessed data
- Use Redis for session storage and temporary data
- Cache static content and media files appropriately

## Development Workflow

### Code Quality
- Follow PEP 8 style guidelines for Python code
- Use meaningful variable and function names
- Implement proper docstrings for complex functions

### Version Control
- Make atomic commits with clear commit messages
- Use feature branches for new functionality
- Ensure all tests pass before merging

This steering document ensures consistent development practices while maintaining the lean, focused approach required for the ClustR estate management system.