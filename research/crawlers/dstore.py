import datetime
import logging
import random
import sys

from google.cloud import datastore

from truestory import functions
from truestory.crawlers import RssCrawler
from truestory.models import ArticleModel, BiasPairModel, RssTargetModel, base
from truestory.tasks import clean_articles


client = None

logging.basicConfig(
    format="%(levelname)s - %(name)s - %(asctime)s - %(message)s",
    level=logging.DEBUG
)


def add_rss_link(link):
    key = client.key("Test")

    rss_target = datastore.Entity(
        key, exclude_from_indexes=["link"])

    rss_target.update({
        "link": link,
        "auth_required": False
    })

    client.put(rss_target)

    return rss_target.id


def mark_auth_required(id):
    with client.transaction():
        key = client.key("Test", id)
        rss_target = client.get(key)

        if not rss_target:
            raise ValueError(
                "Rss target {} does not exist.".format(id))

        rss_target["auth_required"] = True

        client.put(rss_target)


def delete_rss_target(id):
    key = client.key("Test", id)
    client.delete(key)


def list_rss_targets():
    query = client.query(kind="Test")

    return list(query.fetch())


def add_remove_rss():
    rid = add_rss_link("http://feeds.feedburner.com/TechCrunch/")
    mark_auth_required(rid)
    print(list_rss_targets())
    delete_rss_target(rid)
    print(list_rss_targets())


def rss_feed():
    rss_targets = RssTargetModel.all()
    target = rss_targets[0]
    print(target)
    crawler = RssCrawler(rss_targets)
    article_dict = crawler.crawl_targets()
    print(article_dict)
    articles = sum(article_dict.values(), [])
    ArticleModel.put_multi(articles)


def test_model():
    target = RssTargetModel(source_name="test")
    print("model name", target.get_model_name())
    key = target.put()
    print("with key", key)
    usafe = target.urlsafe
    print("urlsafe", usafe)
    target = RssTargetModel.get(usafe)
    print("target", target)
    target.remove()
    print("removed; remaining", RssTargetModel.all(keys_only=True))
    # items = globals()
    # items.update(locals())
    # import code; code.interact(local=items)


def add_bias():
    articles = ArticleModel.all(keys_only=True)
    for _ in range(10):
        left, right = random.sample(articles, 2)
        score = random.uniform(0.375, 1)
        bias_pair = BiasPairModel(left=left.key, right=right.key, score=score)
        bias_pair.put()


def copy_entities():
    query = BiasPairModel.query(("score", ">", 10.0))
    pairs = list(query.fetch())

    assert len(pairs) == 5

    base.NDB_KWARGS["namespace"] = "production"
    base.client = None
    articles = {}

    for pair in pairs:
        left_article = pair.left.get()
        left_key = articles.get(left_article.urlsafe)
        if not left_key:
            left_key = articles[left_article.urlsafe] = ArticleModel(
                **left_article.to_dict()
            ).put()

        right_article = pair.right.get()
        right_key = articles.get(right_article.urlsafe)
        if not right_key:
            right_key = articles[right_article.urlsafe] = ArticleModel(
                **right_article.to_dict()
            ).put()

        to_save = pair.to_dict()
        del to_save["left"]
        del to_save["right"]
        del to_save["keywords"]
        new_pair = BiasPairModel(**to_save)
        new_pair.left = left_key
        new_pair.right = right_key
        key = new_pair.put()
        print(f"Saved new bias: {key}")


def bump_article_dates():
    base.NDB_KWARGS["namespace"] = "production"
    base.client = None
    delta = datetime.timedelta(days=365)

    articles = ArticleModel.all()
    print(f"Bumping dates for {len(articles)} articles.")
    for article in articles:
        article.published += delta
        # print(article.published)
    ArticleModel.put_multi(articles)


def cleanup():
    base.NDB_KWARGS["namespace"] = "production"
    base.client = None

    ret = clean_articles()
    print(ret)


def article_function():
    try:
        article = functions.get_article("https://www.cnn.com/collections/tillerson-meeting/")
    except Exception as exc:
        # import code; code.interact(local={**globals(), **locals()})
        logging.exception(exc)
    else:
        print(article)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} FUNC")
        return

    global client
    client = datastore.Client(project="truestory", namespace="development")

    funcs = {
        "rss": add_remove_rss,
        "rss_feed": rss_feed,
        "test_model": test_model,
        "add_bias": add_bias,
        "copy_entities": copy_entities,
        "bump_article_dates": bump_article_dates,
        "cleanup": cleanup,
        "article_function": article_function,
    }
    funcs[sys.argv[1]]()


if __name__ == "__main__":
    main()

# Example: $ python dstore.py article_function
