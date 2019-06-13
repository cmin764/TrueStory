"""Tests articles and bias pairs."""


import pytest
from truestory.models import ArticleModel, BiasPairModel
from truestory.models.base import ndb
from truestory.tasks.article import clean_articles, pair_article

from .conftest import skip_no_datastore, wait_state


pytestmark = skip_no_datastore


def test_bias_pair_save(bias_pair_ents):
    left, right, bias_pair = bias_pair_ents

    # Check data directly from the DB (not using the local entity).
    new_bias_pair = bias_pair.myself
    assert new_bias_pair.left.get().title.startswith("TrueStory")
    assert new_bias_pair.right.get().source_name.startswith("BBC")


def test_related_articles(bias_pair_ents):
    left, right, bias_pair = bias_pair_ents

    rev_bias_pair = BiasPairModel(left=bias_pair.right, right=bias_pair.left)
    rev_bias_pair.put()

    articles = ArticleModel.get_related_articles(left.key)
    assert len(articles) == 1, "duplicate articles"

    article_date = list(articles)[0]["created_at"].replace(tzinfo=None)
    assert article_date == max(
        bias.created_at for bias in (bias_pair, rev_bias_pair)
    ), "outdated bias pair"


def test_cleanup(bias_pair_ents):
    clean_articles()
    any_alive = any(ent.exists for ent in bias_pair_ents)
    assert not any_alive, "entities aren't cleaned up"


def test_duplicate(left_article_ent, right_article_ent):
    left_article_ent.put()
    wait_state(left_article_ent)

    right_article_ent.link = left_article_ent.link
    right_article_ent.put()

    assert left_article_ent.myself.title == \
           right_article_ent.title, "original not updated"
    assert not right_article_ent.exists, "saved duplicate"


def test_duplicate_multi(left_article_ent, right_article_ent):
    left_article_ent.put()
    wait_state(left_article_ent)

    right_article_ent.link = left_article_ent.link
    ArticleModel.put_multi([left_article_ent, right_article_ent])

    assert left_article_ent.myself.title == \
           right_article_ent.title, "original not updated"
    assert len(ArticleModel.all()) == 1, "saved duplicate"


def test_pair_article(left_article_ent, right_article_ent):
    left_article_ent.put()
    wait_state(left_article_ent)

    assert len(ArticleModel.get_related_articles(left_article_ent.key)) == 0, (
        "dirty datastore (with bias pairs)"
    )

    right_article_ent.put()
    wait_state(right_article_ent)
    # NOTE(cmiN): A previous pair is created automatically when the second article is
    # put. Still, the following line solves duplicates by itself.
    pair_article(left_article_ent.urlsafe)

    related_articles = ArticleModel.get_related_articles(left_article_ent.key)
    assert len(related_articles) == 1, (
        "duplicate or no bias pairs created when it should"
    )
    assert list(related_articles)[0]["article"].key == right_article_ent.key, (
        "wrong bias pair created"
    )


def test_article_side(bias_pair_ents):
    wait_state(bias_pair_ents)
    assert bias_pair_ents[0].side == -2
    assert bias_pair_ents[1].side == 2


def test_article_missing_side(left_article_ent):
    left_article_ent.side = None
    with pytest.raises(ndb.datastore_errors.BadValueError):
        left_article_ent.put()
