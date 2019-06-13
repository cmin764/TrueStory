"""Utilities playing with data files."""


import io
import pkg_resources

from truestory import settings


def get_string(path):
    """Returns string content from `path` file."""
    content = pkg_resources.resource_string(settings.PROJECT_NAME, path)
    return content.decode(settings.ENCODING).strip()


def get_stream(path, binary=True):
    """Returns a file-like object for the one pointed by `path`."""
    stream = pkg_resources.resource_stream(settings.PROJECT_NAME, path)
    if not binary:
        stream = io.TextIOWrapper(stream)
    return stream
