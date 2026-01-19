import re
from drf_yasg.generators import OpenAPISchemaGenerator


class ClustRSchemaGenerator(OpenAPISchemaGenerator):
    """
    Custom schema generator to organize API endpoints by their functional groups
    instead of raw URL segments.
    """

    def get_operation(self, view, path, prefix, method, components, request):
        operation = super().get_operation(view, path, prefix, method, components, request)
        
        # Parse the path to find the functional group
        # Example: /api/v1/accounts/login/ -> ['api', 'v1', 'accounts', 'login']
        # Example: /api/health/ -> ['api', 'health']
        path_segments = [s for s in path.strip("/").split("/") if s]

        tag_mappings = {
            "auth": "Authentication",
            "accounts": "Accounts",
            "roles": "Roles",
            "core": "Core",
            "members": "Members",
            # "management": "Management",
            # "health": "System Health",
        }

        # Logic to find the main "app" or "module" segment
        # By returning the first segment after the api version
        target_key = None
        if "api" in path_segments:
            idx = path_segments.index("api")
            # If 'v1' follows 'api', look at the next segment
            if idx + 1 < len(path_segments):
                next_segment = path_segments[idx + 1]
                if next_segment == "v1":
                    if idx + 2 < len(path_segments):
                        target_key = path_segments[idx + 2]
                else:
                    target_key = next_segment

        # Assign the tag if a match is found
        if target_key:
            tag = tag_mappings.get(target_key, target_key.replace("-", " ").title())
            operation.tags = [tag]
        
        # Generate plain English operation_id from view action and class name
        action = getattr(view, 'action', None)
        view_name = self.format_view_name(view.__class__.__name__)
        
        # Standard CRUD actions that need method prefix for clarity
        standard_actions = {'list', 'create', 'retrieve', 'update', 'partial_update', 'destroy'}
        
        # Map standard actions to plain English
        action_names = {
            'list': 'List',
            'create': 'Create',
            'retrieve': 'Get',
            'update': 'Update',
            'partial_update': 'Patch',
            'destroy': 'Delete',
        }
        
        if action:
            if action in standard_actions:
                # Standard CRUD: use mapped name + view name
                readable_action = action_names[action]
                operation.operation_id = f"{readable_action} {view_name}"
            else:
                # Custom @action: action name already has semantic meaning
                readable_action = action.replace('_', ' ').title()
                readable_method = "Fetch" if method.upper() == "GET" else ""
                operation.operation_id = f"{view_name} - {readable_method} {readable_action}"
        else:
            # Fallback for non-ViewSet views: use method + view name
            method_names = {
                'GET': 'Get',
                'POST': 'Create',
                'PUT': 'Update',
                'PATCH': 'Patch',
                'DELETE': 'Delete',
            }
            readable_method = method_names.get(method.upper(), method.title())
            operation.operation_id = f"{readable_method} {view_name}"

        return operation


    def format_view_name(self, name):
        name = re.sub(r'(ViewSet|APIView|View)$', '', name)
        
        name = re.sub(r'Members?$', "Member's", name)
        name = re.sub(r'Managements?$', "Management's", name)
        
        # Split PascalCase into words
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        
        return name