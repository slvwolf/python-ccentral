from .client import CCentral as Client


class CCentralException(Exception):
    pass


class ConfigNotDefined(CCentralException):
    pass


class ConfigPullFailed(CCentralException):
    pass
