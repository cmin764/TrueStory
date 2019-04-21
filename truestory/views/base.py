"""Base views, routes and utilities used by the web app's views."""


import functools
import urllib.parse as urlparse

from flask import abort, redirect, request, session, url_for

from truestory import app, auth, settings
from truestory.models import base as models_base


@app.context_processor
def _inject_common():
    """Objects available for each template."""
    return {
        "site": request.url_root,
    }


@app.template_filter("norm")
def norm_filter(value):
    """Normalizes the None value (check if property is empty/missing)."""
    return models_base.BaseModel.normalize(value)


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
        return date
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
            return redirect(url_for("login_view"))

        return function(*args, **kwargs)

    return wrapper
