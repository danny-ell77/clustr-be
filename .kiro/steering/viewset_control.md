---
inclusion: always
fileMatchPattern: ['**/views*.py', '**/serializers*.py']
---

# Django REST Framework Viewset Guidelines

## Required Decorators
- **Always** apply `@audit_viewset` decorator to every Django REST framework viewset you create
- This decorator is mandatory for audit logging and tracking purposes

## Data Handling Rules
- **Never** use `request.data` directly in viewsets to access request data
- **Always** define and use a proper serializer for data validation and processing
- This ensures proper validation, error handling, and data transformation

## Query Parameter Handling
- **Never** use `request.data` to define parameters for querying viewsets
- **Always** use `django_filters.FilterSet` to define and validate query parameters
- This provides proper parameter validation, type conversion, and filtering capabilities

## Code Style Requirements
- Follow these patterns consistently across all viewset implementations
- Ensure proper error handling and validation through serializers and filters
- Maintain separation of concerns between data validation (serializers) and query filtering (FilterSets)