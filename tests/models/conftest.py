"""Setups and cleanups procedures for Datastore related tests."""


import datetime
import os
import random
import time

import pytest
from truestory import settings
from truestory.models import (
    ArticleModel, BiasPairModel, PreferencesModel, SubscriberModel
)
from truestory.models.base import BaseModel, SideMixin, ndb


NO_CREDENTIALS = not bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

skip_no_datastore = pytest.mark.skipif(
    not settings.DATASTORE_ENV and NO_CREDENTIALS,
    reason="can't connect to local or remote Datastore"
)

TEST_DB = not skip_no_datastore.args[0]


class TrueStoryModel(BaseModel):

    bool_prop = ndb.BooleanProperty(default=False)
    str_prop = ndb.StringProperty(
        default="str_prop", choices=["str_prop", "string_prop"]
    )
    txt_prop = ndb.TextProperty(indexed=False)
    list_prop = ndb.IntegerProperty(repeated=True)
    auto_prop = ndb.ComputedProperty(lambda self: sum(self.list_prop))


class SideStoryModel(SideMixin, TrueStoryModel):

    link = ndb.StringProperty(default="https://truestory.one/article")


def wait_state(entities, exists=True):
    state_func = lambda: not entity.exists if exists else entity.exists

    if not isinstance(entities, (list, tuple)):
        entities = [entities]
    for entity in entities:
        while state_func():
            time.sleep(0.1)


@pytest.fixture
def truestory_ent():
    """Returns our default model in order to test the DB for basic functionality."""
    return TrueStoryModel()


def _article_ent(label, keywords=None, side=None):
    # Expired article.
    published = datetime.datetime.utcnow() - datetime.timedelta(days=3)
    article = ArticleModel(
        source_name=f"BBC {label}",
        link=f"https://truestory.one/article{label}",
        title=f"TrueStory {label}",
        content=f"True Story {label}",
        published=published,
        keywords=keywords,
        side=side,
    )
    return article


@pytest.fixture
def left_article_ent():
    return _article_ent(
        random.randint(1, 100), keywords=["trump", "money"], side=-2
    )


@pytest.fixture
def right_article_ent():
    return _article_ent(
        random.randint(101, 200), keywords=["trump", "money", "mad"], side=2
    )


@pytest.fixture
def bias_pair_ents(left_article_ent, right_article_ent):
    """Returns a pair of two biased articles."""
    bias_pair = BiasPairModel(
        left=left_article_ent.put(), right=right_article_ent.put()
    )
    bias_pair.put()
    return left_article_ent, right_article_ent, bias_pair


@pytest.fixture
def subscriber_ent():
    """Returns a mail object with a default mail string."""
    return SubscriberModel(mail="test@example.com")


CLEANUP_MODELS = [
    ArticleModel,
    BiasPairModel,
    # NOTE(cmiN): Do not clean global preferences here.
    # PreferencesModel,
    SideStoryModel,
    SubscriberModel,
    TrueStoryModel,
]


@pytest.fixture(autouse=True, scope="session")
def datastore_global_init():
    if not TEST_DB:
        return

    # Creation.
    prefs = PreferencesModel.instance()
    prefs.sites = {
        "truestory.one": {
            "side": "Center",
            "publisher": "https://truestory.one/news",
            "source": "TrueStory",
        }
    }
    prefs.put()
    wait_state(prefs)

    yield

    # Clean-up.
    prefs.remove()
    wait_state(prefs, exists=False)


@pytest.fixture(autouse=True)
def datastore_cleanup():
    if not TEST_DB:
        return

    yield

    # Clean-up.
    all_entities = []
    for Model in CLEANUP_MODELS:
        entities = Model.all(keys_only=True)
        all_entities.extend(entities)
    BaseModel.remove_multi([entity.key for entity in all_entities])
