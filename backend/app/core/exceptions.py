class ResourceNotFoundError(LookupError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(f"{resource} {resource_id} was not found.")
        self.resource = resource
        self.resource_id = resource_id


class ResourceConflictError(ValueError):
    pass


class ProviderConfigurationError(ValueError):
    pass
