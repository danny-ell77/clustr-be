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

        # Tag Mappings for descriptive titles
        tag_mappings = {
            "auth": "Authentication",
            "accounts": "Accounts",
            "roles": "Roles",
            "core": "Core",
            "members": "Members",
            "management": "Management",
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
        
        # Ensure operation_id is clean and consistent
        # We use path segments to generate a unique ID
        operation.operation_id = f"{method.lower()}_{'_'.join(path_segments)}"

        return operation
