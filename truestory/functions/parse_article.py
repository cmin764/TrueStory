"""Handles news article parsing."""


import logging
import os

from flask import abort, current_app
from flask_json import FlaskJSON, as_json
from newspaper import Article as NewsArticle, ArticleException


NLP_ENABLED = bool(int(os.getenv("NLP_ENABLED", "0")))

if current_app:
    app_json = FlaskJSON(current_app)
if NLP_ENABLED:
    import nltk
    nltk.download("punkt")


def get_article(link):
    GAE_PRODUCTION = os.getenv("GAE_ENV", "").startswith("standard")
    if GAE_PRODUCTION:
        # This will not run under Cloud Functions (it is App Engine only).
        from truestory.functions.remote import get_remote_article
        return get_remote_article(link)

    article = NewsArticle(link)
    article.download()
    article.parse()
    if NLP_ENABLED:
        article.nlp()
    return article


@as_json
def parse_article(request):
    """Parses a given article `link` and returns its JSON details."""
    gae_ip = request.headers.get("X-Appengine-User-Ip", "").startswith("2600:1900")
    internal_country = request.headers.get("X-Appengine-Country") == "ZZ"
    if not any([gae_ip, internal_country]):
        abort(403)

    data = request.get_json() or request.args
    link = data.get("link")
    if not link:
        abort(400, "Link not supplied.")

    try:
        article = get_article(link)
    except ArticleException as exc:
        logging.exception(exc)
        abort(404)

    news_article = {
        "url": article.url,
        "title": article.title,
        "text": article.text,
        "summary": article.summary,
        "authors": article.authors,
        "publish_date": article.publish_date,
        "top_image": article.top_image,
        "keywords": article.keywords,
    }
    response = {
        "news_article": news_article
    }
    return response
