class FCEAError(Exception):
    """Expected, reportable domain error; never a successful scientific result."""


class ValidationError(FCEAError):
    pass


class IntegrityError(FCEAError):
    pass


class ConflictError(FCEAError):
    pass


class NotFoundError(FCEAError):
    pass


class AuthorizationError(FCEAError):
    pass
