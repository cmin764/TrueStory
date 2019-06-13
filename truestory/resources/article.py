"""API exposing article related data."""


import logging

import addict
from flask_restful import abort, request

from truestory import settings
from truestory.crawlers import RssCrawler
from truestory.crawlers.common import strip_article_link
from truestory.models import ArticleModel
from truestory.models.base import key_to_urlsafe
from truestory.resources import base
from truestory.views.base import exc_to_str


# Lazily loaded.
pair_article = None


def _pair_article(article_usafe):
    global pair_article
    if not pair_article:
        from truestory.tasks import pair_article
    return pair_article(article_usafe)


def _extract_article(link, site, site_info):
    feed_entry = addict.Dict({
        "link": link,
    })
    target = addict.Dict({
        "source_name": site_info["source"],
        "site": site,
        "side": ArticleModel.SIDE_MAPPING[site_info["side"]],
    })
    logging.info(
        "Crawling new article from %s: %s...", target.source_name, feed_entry.link
    )
    return RssCrawler.extract_article(feed_entry, target)


class BaseArticleResource(base.DatastoreMixin, base.BaseResource):

    """Base class for all article related resources."""

    URL_PREFIX = "/article"

    @staticmethod
    def _get_schemas():
        # Required due to circular import.
        from truestory.schemas.article import (
            article_schema, articles_schema
        )
        schemas = {
            "article": article_schema,
            "articles": articles_schema,
        }
        return schemas


class CounterArticleResource(BaseArticleResource):

    """Handles opposite articles."""

    ENDPOINT = "counter"

    def get(self):
        """Returns a list of opposite articles for the provided one."""
        link = request.args.get("link", "").strip()
        if not link:
            abort(400, message="Article 'link' not supplied.")

        link = strip_article_link(link)
        article_query = ArticleModel.query(("link", "=", link))
        main_articles = ArticleModel.all(query=article_query, keys_only=True, limit=1)
        if not main_articles:
            abort(404, message="Article not found in the database.")

        main_article = main_articles[0]
        related_articles = ArticleModel.get_related_articles(main_article.key)
        if not related_articles:
            abort(404, message="No related articles found.")

        articles = [
            article["article"] for article in related_articles
        ][:settings.API_MAX_RELATED_ARTICLES]
        main_article_url = self._make_response(
            "articles", [main_article]
        ).json["articles"][0]
        return self._make_response("articles", articles, main=main_article_url)

    def post(self):
        link = request.get_json().get("link", "").strip()
        if not link:
            abort(400, message="Article 'link' not supplied.")

        link = strip_article_link(link)
        try:
            site, site_info = ArticleModel.get_site_info(link)
        except Exception as exc:
            abort(403, message=exc_to_str(exc))

        article = _extract_article(link, site, site_info)
        article_key = article.put()
        _pair_article(key_to_urlsafe(article_key))
        return self._make_response("article", article)


class DataArticleResource(BaseArticleResource):

    """Handles a full article."""

    ENDPOINT = "data"

    @classmethod
    def get_route(cls):
        return f"{super().get_route()}/<article_usafe>"

    def get(self, article_usafe):
        """Returns contents of an article."""
        try:
            article = ArticleModel.get(article_usafe)
        except Exception as exc:
            abort(404, message=exc_to_str(exc))

        return self._make_response("article", article)
