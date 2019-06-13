"""Article related models."""


import functools

from truestory.models.base import (
    BaseModel, DuplicateMixin, SideMixin, key_to_urlsafe, ndb
)


class ArticleModel(SideMixin, DuplicateMixin, BaseModel):

    """Extracted and processed article."""

    source_name = ndb.StringProperty(required=True)
    link = ndb.StringProperty(required=True)
    title = ndb.StringProperty(required=True)
    content = ndb.TextProperty(required=True, indexed=False)

    summary = ndb.StringProperty(indexed=False)
    authors = ndb.StringProperty(repeated=True)
    published = ndb.DateTimeProperty()
    image = ndb.StringProperty()
    keywords = ndb.StringProperty(repeated=True)

    @staticmethod
    def get_related_articles(main_article_key, meta_func=None):
        """Returns a list of unique related articles given a main one and looking over
        all the biased pairs containing it.

        Args:
            main_article_key (KeyProperty): Queried main article's key.
            meta_func (callable): If this is provided, then `meta_return` will be the
                return value of calling `meta_func` over each related pair of articles.
        Returns:
            dict_values: Of dictionaries containing the article, meta_return and other
                info.
        """
        related_articles = {}

        complementary = {"left": "right", "right": "left"}
        for side in complementary:
            query = BiasPairModel.query((side, "=", main_article_key))
            pairs = list(query.fetch())

            for pair in pairs:
                # Keep unique related articles only (choose the newest one if
                # duplicates are found).
                article_key = getattr(pair, complementary[side])
                usafe = key_to_urlsafe(article_key)
                seen_date = related_articles.get(usafe, {}).get("created_at")
                if seen_date and pair.created_at <= seen_date:
                    continue

                meta = meta_func(pair) if meta_func else None
                if seen_date:
                    related_articles[usafe].update({
                        "created_at": pair.created_at,
                        "meta": meta,
                    })
                else:
                    article = article_key.get()
                    related_articles[usafe] = {
                        "article": article,
                        "created_at": pair.created_at,
                        "meta": meta,
                    }

        return related_articles.values()

    @property
    def primary_key(self):
        return "link"


class BiasPairModel(BaseModel):

    """A pair of two biased articles."""

    left = ndb.KeyProperty(kind=ArticleModel, required=True)
    right = ndb.KeyProperty(kind=ArticleModel, required=True)
    score = ndb.FloatProperty()
    published = ndb.DateTimeProperty()

    @functools.partial(ndb.ComputedProperty, repeated=True)
    def keywords(self):
        """Combines all the keywords into an unique list."""
        all_keywords = set()

        article_keys = [self.left, self.right]
        for article_key in article_keys:
            keywords = article_key.get().keywords or []
            for keyword in keywords:
                all_keywords.add(keyword.strip().lower())

        return list(filter(None, all_keywords))

    def _max_date(self):
        """The newest article establishes the date of the entire pair."""
        dates = self.left.get().published, self.right.get().published
        if all(dates):
            return max(dates)
        return dates[0] or dates[1]

    def put(self):
        if not self.exists:
            self.published = self._max_date()
        return super().put()
