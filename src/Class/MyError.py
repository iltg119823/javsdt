
class TooManyDirectoryLevelsError(Exception):
    pass


class DownloadFanartError(Exception):
    pass


class SpecifiedUrlError(Exception):
    pass


class SourceUnavailableError(Exception):
    """A source could not provide a usable page; mirror retry must be explicit."""
    def __init__(self, message, allow_mirror=False):
        super().__init__(message)
        self.allow_mirror = allow_mirror
