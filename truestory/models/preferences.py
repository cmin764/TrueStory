"""Global admin settings, options and preferences."""


import logging

from truestory.models.base import BaseModel, ndb


class PreferencesModel(BaseModel):

    """Singleton preferences and resources model."""

    sites = ndb.JsonProperty(default={})
    contradiction_threshold = ndb.FloatProperty(default=0.5)
    similarity_threshold = ndb.FloatProperty(default=0.5)

    @classmethod
    def instance(cls):
        entities = cls.all()
        if not entities:
            logging.info("Creating preferences model for the first time.")
            prefs = cls()
            prefs.put()
            entities = cls.all()
        assert len(entities) == 1, "duplicate preferences objects"
        return entities[0]
