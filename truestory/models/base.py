"""Base models and utilities used by the derived ones."""


import datetime
import functools
import logging
import os
import urllib.parse as urlparse
from collections import OrderedDict

import ndb_orm as ndb
from google.auth.credentials import Credentials
from google.cloud import datastore

from truestory import app, settings


# Datastore default client settings.
PROJECT = settings.PROJECT_ID
NAMESPACE = app.config["DATASTORE_NAMESPACE"]
NDB_KWARGS = {"project": PROJECT, "namespace": NAMESPACE}
# Number of entities to be put/removed at once.
MAX_BATCH_SIZE = 500

# Module level singleton client used in all DB interactions. This is lazy inited when
# is used only, so we don't have any issues with the Datastore agnostic tests or
# debugging, because creating a client will require valid credentials.
client = None
# Lazily loaded due to circular import (under SideMixin).
PreferencesModel = None


def key_to_urlsafe(key):
    """Returns entity `key` as a string."""
    return key.to_legacy_urlsafe().decode(settings.ENCODING)


def batch_process(function, iterable, size=MAX_BATCH_SIZE):
    batch_returns = []
    iterable = list(iterable)
    for idx in range(0, len(iterable), size):
        subiter = iterable[idx:idx + size]
        batch_returns.append(function(subiter))
    return tuple(batch_returns)


# NOTE(cmiN): This is copied from ndb-orm library's tests.
class EmulatorCredentials(Credentials):

    def __init__(self):
        """A mock credentials object.

        Used to avoid unnecessary token refreshing or reliance on the network while an
        emulator is running.
        """
        super().__init__()
        self.token = b"seekrit"
        self.expiry = None

    @property
    def valid(self):
        """Would-be validity check of the credentials. Always is True."""
        return True

    def refresh(self, _unused_request):
        """Off-limits implementation for abstract method."""
        raise RuntimeError("Should never be refreshed.")


class BaseModel(ndb.Model):

    """Common model properties and functionality."""

    # String used for properties with no available data (None).
    NOT_SET = "N/A"

    created_at = ndb.DateTimeProperty(auto_now_add=True)

    def __init__(self, *args, **kwargs):
        self._get_client()  # Activates all NDB ORM required features.
        kwargs.update(NDB_KWARGS)
        super().__init__(*args, **kwargs)

    @classmethod
    def get_model_name(cls):
        """Returns the model name (without suffix)."""
        return cls.__name__.replace("Model", "")

    @classmethod
    def normalize(cls, value):
        """Normalizes a property value which needs to be rendered."""
        if value is None:
            return cls.NOT_SET
        return value

    @staticmethod
    def _get_client():
        """Singleton for the Datastore client."""
        global client
        if not client:
            Client = functools.partial(datastore.Client, **NDB_KWARGS)
            if settings.DATASTORE_ENV or os.getenv("GAE_ENV") == "localdev":
                # Even if the emulator is on, the client will still ask for
                # credentials, therefore we mock them (because they aren't really
                # used).
                logging.warning(
                    "Connecting to the Datastore emulator with mocked credentials."
                )
                client = Client(credentials=EmulatorCredentials())
            else:
                client = Client()
            ndb.enable_use_with_gcd(client=client, **NDB_KWARGS)
        return client

    @classmethod
    def query(cls, *args, **kwargs):
        """Creates a Datastore query out of this model."""
        query = cls._get_client().query(kind=cls._get_kind(), **kwargs)
        for arg in args:
            query.add_filter(*arg)
        return query

    @classmethod
    def all(cls, query=None, keys_only=False, order=True, **kwargs):
        """Returns all the items in the DB created by this model.

        Args:
            query: Optionally you can supply a custom `query`.
            keys_only (bool): Keep the Key properties only if this is True.
            order (bool): Implicit by the time it was created in descending order.
        Returns:
            list: Fetched items.
        """
        query = query or cls.query()
        if order:
            query.order = ["-created_at"]
        if keys_only:
            query.keys_only()
        return list(query.fetch(**kwargs))

    @property
    def myself(self):
        """Returns the current DB version of the same object."""
        return self.key.get()

    @property
    def exists(self):
        """Checks if the entity is saved into the Datastore."""
        try:
            return bool(self.myself) if self.key and self.key.id else False
        except Exception:
            return False

    def put(self):
        """Saves the entity into the Datastore."""
        self._get_client().put(self)
        return self.key

    @classmethod
    def put_multi(cls, entities):
        """Multiple save in the DB without interfering with the `cls.put` function."""
        batch_process(cls._get_client().put_multi, entities)
        return [entity.key for entity in entities]

    def remove(self):
        """Removes current entity and its dependencies (if covered and any)."""
        self.key.delete()

    @classmethod
    def remove_multi(cls, keys):
        """Multiple removal of entities based on the given `keys`."""
        batch_process(cls._get_client().delete_multi, keys)

    @property
    def urlsafe(self):
        """Returns an URL safe Key string which uniquely identifies this entity."""
        return key_to_urlsafe(self.key)

    @classmethod
    def get(cls, urlsafe_or_key):
        """Retrieves an entity object based on an URL safe Key string or Key object."""
        cls._get_client()
        if isinstance(urlsafe_or_key, (str, bytes)):
            key = ndb.Key(cls, **NDB_KWARGS)
            complete_key = key.from_legacy_urlsafe(urlsafe_or_key)
        else:
            complete_key = urlsafe_or_key

        item = complete_key.get()
        if not item:
            raise Exception("item doesn't exist")
        return item


class DuplicateMixin:

    """Adds support for updating same entities when similar ones are added."""

    @property
    def primary_key(self):
        """Returns the property name holding an unique value among the others."""
        raise NotImplementedError(
            f"{self.get_model_name()} primary key not specified"
        )

    @property
    def primary_value(self):
        return getattr(self, self.primary_key)

    def get_existing(self):
        """Returns already existing entities based on the chosen `self.primary_key`.

        An existing entity is one that has the same primary key attribute value as the
        candidate's one.
        """
        query = self.query((self.primary_key, "=", self.primary_value))
        entities = self.all(query=query, keys_only=True, order=False)
        return entities

    def update(self, duplicates):
        """Updates itself without creating another entry in the database."""
        logging.debug("Updating already existing entity: %s.", self.primary_value)
        assert len(duplicates) == 1, "found duplicate entity in the DB"
        entity = duplicates[0].myself
        properties = self.to_dict()
        properties["created_at"] = datetime.datetime.utcnow()
        entity.populate(**properties)
        return entity

    def put(self):
        """Check if this is already existing and if yes, just update with the new
        values.
        """
        # These are keys only entities.
        duplicates = self.get_existing()

        if self.exists or not duplicates:
            # Save the newly created entity or the already present one (self update).
            return super().put()

        return self.update(duplicates).put()

    @classmethod
    def put_multi(cls, entities):
        unique_entities = OrderedDict()
        for entity in entities:
            unique_entities[entity.primary_value] = entity

        for primary_value, entity in unique_entities.items():
            if entity.exists:
                continue

            duplicates = entity.get_existing()
            if duplicates:
                unique_entities[primary_value] = entity.update(duplicates)

        return super().put_multi(unique_entities.values())


class SideMixin:

    """Adds side info to a model."""

    LEFT = -2
    LEAN_LEFT = -1
    CENTER = 0
    LEAN_RIGHT = 1
    RIGHT = 2
    SIDE_MAPPING = {
        "Left": LEFT,
        "Lean Left": LEAN_LEFT,
        "Center": CENTER,
        "Lean Right": LEAN_RIGHT,
        "Right": RIGHT
    }
    SITE_REPLACE = ["www.", "rss.", "feeds."]
    _prefs = None

    side = ndb.IntegerProperty(required=True, choices=list(SIDE_MAPPING.values()))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.side is None:
            self.side = self._get_side(self.link, site=getattr(self, "site", None))

    @classmethod
    def normalize_site(cls, site):
        for repl in cls.SITE_REPLACE:
            site = site.replace(repl, "", 1)
        return site

    @classmethod
    def _get_prefs(cls):
        if not cls._prefs:
            global PreferencesModel
            if not PreferencesModel:
                from truestory.models.preferences import PreferencesModel
            cls._prefs = PreferencesModel.instance()
        return cls._prefs

    @classmethod
    def get_site_info(cls, link, site=None):
        site = site or cls.normalize_site(urlparse.urlsplit(link).netloc)
        site_info = cls._get_prefs().sites.get(site)
        if not site_info:
            raise Exception(f"item coming from unrecognized source {site!r}")

        return site, site_info

    @classmethod
    def _get_side(cls, link, site):
        if not link:
            return None

        _, site_info = cls.get_site_info(link, site=site)
        return cls.SIDE_MAPPING[site_info["side"]]
