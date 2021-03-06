"""Base views, routes and utilities used by the web app's views."""


import functools
import urllib.parse as urlparse

import addict
from flask import abort, redirect, request, session, url_for

from truestory import app, auth, get_remote_address, settings
from truestory.models import StatsModel


@app.context_processor
def _inject_common():
    """Objects available for each template."""
    return {
        "site": request.url_root,
        "mail": settings.DEFAULT_MAIL,
        "typeform_text": "What do you think?",
    }


@app.template_filter("usafe")
def usafe_filter(entity):
    """Returns the URL safe key string given an entity."""
    return entity.urlsafe


@app.template_filter("format_date")
def format_date_filter(date, time=False):
    """Returns a formatted date string out of a `datetime` object.

    Args:
        time (bool): Add to date the time too if this is True.
    """
    if not date:
        # NOTE(cmiN): Prefer to return empty string for missing dates (instead of N/A).
        return ""

    template = "%d-%b-%y"
    if time:
        template += " %H:%M"
    return date.strftime(template)


@app.template_filter("paragraph_split")
def paragraph_split_filter(content, full=False):
    """Truncates content to a maximum size.

    Returns:
        list: Of paragraphs.
    """
    size = settings.FULL_ARTICLE_MAX_SIZE if full else settings.HOME_ARTICLE_MAX_SIZE
    if len(content) > size:
        content = content[:size] + "..."
    return content.split("\n\n")


@app.template_filter("website")
def website_filter(link):
    """Returns the network location of a received URL."""
    return urlparse.urlsplit(link).netloc


@app.template_filter("ujoin")
def ujoin_filter(base, relative):
    """Joins two URLs together."""
    return urlparse.urljoin(base, relative)


@app.template_filter("join_authors")
def join_authors_filter(authors):
    """Limits and joins a list of authors."""
    string = ", ".join(authors)
    size = settings.AUTHORS_MAX_SIZE
    if len(string) > size:
        string = string[:size] + "..."
    return string


def require_auth(function):
    """Decorates endpoints which require authorization."""

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        token = session.get("token")
        if token:
            if not auth.authorize_with_token(token):
                del session["token"]
                abort(401, "Invalid token.")
        else:
            return redirect(url_for("login_view", next=request.url))

        return function(*args, **kwargs)

    return wrapper


class require_headers:

    """Basic check for headers presence."""

    def __init__(self, headers, error_message="Invalid headers."):
        if not isinstance(headers, (list, tuple)):
            headers = (headers,)
        self._headers = headers
        self._error_message = error_message

    def __call__(self, function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            good = all(header in request.headers for header in self._headers)
            if not good:
                abort(403, self._error_message)
            return function(*args, **kwargs)

        return wrapper


def save_thumbs(subject, *key_path, thumbs):
    stats = StatsModel.instance()
    root_dict = sub_dict = addict.Dict(getattr(stats, subject))
    key_path = (get_remote_address(),) + key_path
    for key in key_path[:-1]:
        sub_dict = sub_dict[key]
    sub_dict[key_path[-1]] = thumbs
    setattr(stats, subject, root_dict)
    stats.put()


def get_thumbs(subject, *key_path):
    stats = StatsModel.instance()
    sub_dict = addict.Dict(getattr(stats, subject))
    key_path = (get_remote_address(),) + key_path
    for key in key_path:
        sub_dict = sub_dict[key]
    if sub_dict == {}:
        return None
    return sub_dict
