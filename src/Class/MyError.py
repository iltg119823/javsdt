
class TooManyDirectoryLevelsError(Exception):
    pass


class DownloadFanartError(Exception):
    pass


class SpecifiedUrlError(Exception):
    pass


class SourceUnavailableError(Exception):
    """A source could not provide a usable page; other sources may continue."""
    pass
