class PlatformError(RuntimeError):
    """Base platform API failure."""


class AuthenticationError(PlatformError):
    pass


class PermissionError(PlatformError):
    pass


class RateLimitError(PlatformError):
    pass


class ProviderError(PlatformError):
    pass
