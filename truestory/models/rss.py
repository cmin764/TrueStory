"""RSS related models."""


from truestory.models.base import BaseModel, SideMixin, ndb


class RssTargetModel(SideMixin, BaseModel):

    """RSS feed source used by the RSS crawler."""

    source_name = ndb.StringProperty(required=True)
    link = ndb.StringProperty(required=True)
    site = ndb.StringProperty(required=True)

    last_modified = ndb.DateTimeProperty()
    etag = ndb.StringProperty()
    gone = ndb.BooleanProperty(default=False)
    auth_required = ndb.BooleanProperty(default=False)
    enabled = ndb.BooleanProperty(default=True)

    def checkpoint(self, modified, etag):
        """Called after each successful crawl in order to know from where to start
        next time.
        """
        self.last_modified = modified
        self.etag = etag
        self.put()

    def has_gone(self):
        """Marks this feed as dead; do not crawl it again."""
        self.gone = True
        self.put()

    def needs_auth(self):
        """Marks this feed with required authentication in order to skip it if auth is
        not supported.
        """
        self.auth_required = True
        self.put()

    def moved_to(self, link):
        """Saves the new address when the target URL permanently moves."""
        self.link = link
        self.put()
