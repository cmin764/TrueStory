"""RSS feed crawler capable of extracting and parsing found articles."""


import calendar
import collections
import logging
import urllib.request as urlopen
from datetime import datetime, timezone
from http import HTTPStatus

import feedparser

from truestory import functions
from truestory.crawlers.common import strip_article_link, strip_html
from truestory.models.article import ArticleModel


class RssCrawler:

    """Crawler for any type of RSS feed targets."""

    ALLOWED_EXCEPTIONS = (
        feedparser.CharacterEncodingOverride,
    )

    def __init__(self, rss_targets, limit=None):
        """Instantiates with a RSS target list to crawl.

        Args:
            rss_targets (list): List of `RssTargetModel` objects.
            limit (int): How many results to crawl within each target.
        """
        self._rss_targets = rss_targets
        self._limit = limit

    @staticmethod
    def _time_to_date(parsed_time):
        """Converts `parsed_time` to a datetime object."""
        if not parsed_time:
            return parsed_time
        return datetime.fromtimestamp(calendar.timegm(parsed_time), tz=timezone.utc)

    @staticmethod
    def _normalize_date(date):
        """Corrects dates potentially from the future."""
        if not date:
            return None

        if date.tzinfo:
            date = date.replace(tzinfo=None) - date.tzinfo.utcoffset(date)
        return min(date, datetime.utcnow())

    @classmethod
    def extract_article(cls, feed_entry, target):
        """Extracts all the information needed from a `feed_entry` and returns it as
        an `ArticleModel` object.
        """
        # Link is a mandatory field in the RSS. If missing, we cannot parse the
        # article.
        link = feed_entry.get("link")
        if not link:
            raise KeyError("link missing from the feed article")

        news_article = functions.get_article(link)
        link = urlopen.urlopen(news_article.url).url
        title = feed_entry.get("title") or news_article.title
        # The 'description' value seems to be an alternative tag for summary.
        summary = (
            feed_entry.get("summary") or
            feed_entry.get("description") or
            news_article.summary
        )
        publish_date = (
            cls._time_to_date(feed_entry.get("published_parsed")) or
            news_article.publish_date
        )
        to_lower = lambda strings: list(
            filter(None, [string.lower().strip() for string in strings])
        )

        article_ent = ArticleModel(
            source_name=target.source_name,
            # NOTE(cmiN): Use the final URL (after redirects), because based on this
            # we uniquely identify articles (primary key is `link`).
            link=strip_article_link(link, site=target.site),
            title=title,
            content=news_article.text,
            summary=strip_html(summary),
            authors=news_article.authors,
            published=cls._normalize_date(publish_date),
            image=news_article.top_image,
            keywords=to_lower(news_article.keywords or []),
            side=target.side,
        )
        return article_ent

    @staticmethod
    def _manage_status(response, target):
        """Handles some of the possible problematic feed statuses and updates `target`
        accordingly.

        Returns:
            bool: True if we can crawl the target, False otherwise.
        """
        name = target.link

        # We shall never crawl it again.
        if response.status == HTTPStatus.GONE:
            logging.warning("RSS is dead for %r.", name)
            target.has_gone()
            return False

        # Becomes aware that it requires auth and must support it in the future.
        if response.status == HTTPStatus.UNAUTHORIZED:
            logging.warning("RSS requires auth for %r.", name)
            target.needs_auth()
            return False

        # Nothing new received from it.
        if response.status == HTTPStatus.NOT_MODIFIED:
            logging.info("RSS has no data for %r.", name)
            return False

        # URL has permanently moved, so we have to update target with the new one.
        if response.status == HTTPStatus.MOVED_PERMANENTLY:
            logging.info("RSS has moved for %r.", name)
            target.moved_to(response.href)

        return True

    @classmethod
    def _entries_after_date(cls, entries, date):
        """Filters the `entries` which are older than the given `date`.

        Returns:
            tuple: A list of new entries and a new date to crawl afterwards.
        """
        new_entries = []
        max_date = date

        for entry in entries:
            entry_date = cls._time_to_date(entry.get("published_parsed"))
            if not max_date:
                # `max_date` could be None if target's last modified date is not
                # initialized yet.
                max_date = entry_date
            if all([entry_date, date]) and entry_date <= date:
                continue

            new_entries.append(entry)
            if entry_date and entry_date > max_date:
                max_date = entry_date

        return new_entries, max_date

    @classmethod
    def _get_recent_feed(cls, target):
        """Retrieves the RSS feed through `feedparser` and updates the timestamp of
        the last retrieval in order to avoid getting banned or having duplicate data.

        Returns:
            tuple: Article, its modified date and the e-tag.
        """
        response = feedparser.parse(
            target.link, modified=target.last_modified, etag=target.etag
        )

        # Some of the feeds offer one of these two tags and others none of them.
        modified = cls._time_to_date(response.get("modified_parsed"))
        etag = response.get("etag")

        # In case RSS feed doesn't support modified tag, we compute it artificially.
        if not modified:
            response.entries, modified = cls._entries_after_date(
                response.entries, target.last_modified
            )

        return response, modified, etag

    def _extract_articles(self, target):
        """Parses the given RSS target, then extracts and returns all found articles.
        """
        feed_response, modified, etag = self._get_recent_feed(target)

        # Bozo is a tag which tells that the RSS hasn't been parsed correctly.
        if feed_response.bozo:
            exc = feed_response.bozo_exception
            if not isinstance(exc, self.ALLOWED_EXCEPTIONS):
                raise feed_response.bozo_exception

        articles = []
        count = 0
        if self._manage_status(feed_response, target):
            for feed_entry in feed_response.entries:
                if self._limit and count >= self._limit:
                    logging.info(
                        "Crawling limit of %d article(s) was reached for this target.",
                        count
                    )
                    break
                try:
                    article = self.extract_article(feed_entry, target)
                except Exception as exc:
                    # NOTE(cmiN): On Stackdriver Error Reporting we don't want to catch
                    # (with `logging.exception`) "Not Found" errors, because they are
                    # pretty frequent and usual, therefore ignore-able.
                    log_function = (
                        logging.error if "404" in str(exc) else logging.exception
                    )
                    log_function("Got %s while parsing %r.", exc, feed_entry.id)
                else:
                    articles.append(article)
                    count += 1
            target.checkpoint(modified, etag)

        return articles

    def crawl_targets(self):
        """Crawls the most recent feed from each of the given RSS targets.

        Returns:
            dict: A list of articles by each target URL.
        """
        extracted_articles = collections.defaultdict(list)

        if not self._rss_targets:
            logging.warning("No targets available, check database.")
            return extracted_articles

        for target in self._rss_targets:
            link = target.link
            logging.debug(
                "Crawling target URL %r for articles newer than %s.",
                link, target.last_modified
            )
            try:
                articles = self._extract_articles(target)
            except Exception as exc:
                logging.exception("RSS target error with %r: %s", link, exc)
            else:
                extracted_articles[link].extend(articles)

        return extracted_articles
