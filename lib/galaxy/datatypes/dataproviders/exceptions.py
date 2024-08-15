"""
DataProvider related exceptions.
"""


class InvalidDataProviderSource(TypeError):
    """
    Raised when a unusable source is passed to a provider.
    """

    def __init__(self, source=None, msg=""):
        msg = msg or f"Invalid source for provider: {source}"
        super().__init__(msg)


class NoProviderAvailable(TypeError):
    """
    Raised when no provider is found for the given `format_requested`.

    :param factory_source:      the item that the provider was requested from
    :param format_requested:    the format_requested (a hashable key to access
        `factory_source.datatypes` with)

    Both params are attached to this class and accessible to the try-catch
    receiver.

    Meant to be used within a class that builds dataproviders (e.g. a Datatype)
    """

    def __init__(self, factory_source, format_requested=None, msg=""):
        self.factory_source = factory_source
        self.format_requested = format_requested
        msg = msg or f'No provider available in factory_source "{str(factory_source)}" for format requested'
        if self.format_requested:
            msg += f': "{self.format_requested}"'
        super().__init__(msg)
