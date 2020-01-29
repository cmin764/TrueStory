"""Main script execution logic."""


import argparse
import json
import logging
import operator
import re
import urllib.parse as urlparse
import urllib.request as urlopen
from datetime import date, datetime

import truestory
from truestory import auth, datautil
from truestory.crawlers import RssCrawler
from truestory.models import (
    ArticleModel,
    NAMESPACE as DATASTORE_NAMESPACE,
    PreferencesModel,
    RssTargetModel,
)
from truestory.models.base import key_to_urlsafe
from truestory.settings import SERVER
from truestory.tasks import pair_article
from truestory.tasks.article import shorten_source


RSS_TARGETS_PATH = "data/rss_targets.json"
SOURCES_PATH = "data/media-bias.csv"
RE_PORT = re.compile(r":\d+")


def run_server(args):
    truestory.app.run(host=SERVER.HOST, port=SERVER.PORT, debug=SERVER.DEBUG)


def _json_serializer(obj):
    """JSON serializer for objects not serializable by default `json` module."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()


def crawl_articles(args):
    """Crawls and possibly saves articles into DB."""
    rss_targets = RssTargetModel.all(RssTargetModel.query(("enabled", "=", True)))
    for rss_target in rss_targets:
        rss_crawler = RssCrawler([rss_target], limit=args.limit)
        articles_dict = rss_crawler.crawl_targets()
        articles = sum(articles_dict.values(), [])
        for article in articles:
            print(json.dumps(article.to_dict(), indent=4, default=_json_serializer))
        if args.save:
            logging.info("Saving these %d shown article(s).", len(articles))
            article_keys = ArticleModel.put_multi(articles)
            for article_key in article_keys:
                pair_article(key_to_urlsafe(article_key))


def compute_token(args):
    """Returns a 128bit token string used for authorization."""
    token = auth.compute_token(args.mail)
    print(f"Token: {token}")
    status = auth.authorize_with_token(token)
    print(f"Authorized: {status}")


def update_rss_targets(args):
    """Updates into the database the loaded list of RSS targets."""
    logging.info("Saving rss targets into Datastore: %s", DATASTORE_NAMESPACE)

    missing = lambda item: item == {}
    normalize_site = lambda url: RssTargetModel.normalize_site(
        urlparse.urlsplit(url).netloc
    )

    normed_sites = {}
    new_sites = {}
    enabled_sites = set()
    disabled_sites = set()

    targets = datautil.get_json_data(args.targets_path).targets
    for target in targets:
        old_rss_targets = RssTargetModel.all(
            RssTargetModel.query(("link", "=", target.link)), order=False
        )
        if old_rss_targets:
            assert len(old_rss_targets) == 1, (
                "duplicate RSS targets found in the database"
            )
            old_rss_target = old_rss_targets[0]
            if not args.all:
                logging.debug(
                    "Skipping already existing target %r.", old_rss_target.source_name
                )
                continue

            logging.info(
                "Removing old target %r from the DB.", old_rss_target.source_name
            )
            old_rss_target.remove()

        src_name = shorten_source(target.source_name)
        if src_name not in normed_sites:
            logging.debug("Normalizing site for %s.", src_name)
            site = normalize_site(target.link)
            publisher = RE_PORT.sub("", urlopen.urlopen("http://" + site).url)
            site = normalize_site(publisher)
            normed_sites[src_name] = (site, publisher)
        site, publisher = normed_sites[src_name]

        custom_side = target.side or None
        rss_target = RssTargetModel(
            source_name=target.source_name,
            link=target.link,
            site=site,
            enabled=True if missing(target.enabled) else target.enabled,
            side=RssTargetModel.SIDE_MAPPING[custom_side] if custom_side else None,
        )
        logging.info("Adding new target into the DB: %s", rss_target.source_name)
        rss_target.put()

        if custom_side:
            logging.warning(
                "Adding/Replacing whitelisted site %r as being %s.", site, custom_side
            )
            new_sites[site] = {
                "side": custom_side,
                "publisher": publisher,
                "source": src_name,
                "agree": -1,
            }

        if rss_target.enabled:
            enabled_sites.add(site)
        elif not target.accepted:
            disabled_sites.add(site)

    prefs = PreferencesModel.instance()
    sites = prefs.sites
    sites.update(new_sites)
    for site in disabled_sites - enabled_sites:
        logging.warning("Removing potential existing whitelisted site %r.", site)
        sites.pop(site, None)
    prefs.sites = sites
    prefs.put()


def update_sources(args):
    """Updates into the database a list of accepted input sources along their side."""
    logging.info("Saving sources into Datastore: %s", DATASTORE_NAMESPACE)

    reader = datautil.get_csv_data(args.sources_path).reader
    side_dict = {}
    int_keys = ["agree", "disagree"]
    for row in reader:
        for key in int_keys:
            row[key] = int(row[key])
        side_dict.setdefault(row["site"], []).append(row)

    prefs = PreferencesModel.instance()
    sites = {}
    for site, sides in side_dict.items():
        best_side = max(sides, key=operator.itemgetter("agree"))
        sites[RssTargetModel.normalize_site(site)] = {
            "side": best_side["label"],
            "publisher": best_side["publisher"],
            "source": best_side["source"],
            "agree": best_side["agree"],
        }
    prefs.sites = sites
    prefs.put()


def main():
    # Main parser with common flags.
    parser = argparse.ArgumentParser(description="Be your own journalist.")
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="show debugging messages"
    )
    subparser = parser.add_subparsers(dest="command", title="commands", required=True)

    # Basic Flask server run.
    run_parser = subparser.add_parser("run", help="run server")
    run_parser.set_defaults(function=run_server)

    # Articles crawling & saving.
    crawl_parser = subparser.add_parser("crawl", help="crawl articles")
    crawl_parser.add_argument(
        "-l", "--limit", metavar="NUMBER", type=int,
        help="how many results to return for each target"
    )
    crawl_parser.add_argument(
        "-s", "--save", action="store_true",
        help=f"save results into Datastore ({DATASTORE_NAMESPACE})"
    )
    crawl_parser.set_defaults(function=crawl_articles)

    # RSS targets management.
    rss_parser = subparser.add_parser("rss", help="manage RSS targets")
    rss_subparser = rss_parser.add_subparsers(
        dest="command", title="commands", required=True
    )
    rss_update_parser = rss_subparser.add_parser(
        "update", help="load a list of RSS targets into the database"
    )
    rss_update_parser.add_argument(
        "-a", "--all", action="store_true",
        help="replace existing targets too (instead of just adding the new ones only)"
    )
    rss_update_parser.add_argument(
        "targets_path", metavar="TARGETS_FILE",
        default=RSS_TARGETS_PATH, nargs="?",
        help=f"JSON file containing a list of RSS targets ({RSS_TARGETS_PATH})"
    )
    rss_update_parser.set_defaults(function=update_rss_targets)

    # Publishers whitelisting.
    source_parser = subparser.add_parser("source", help="manage trusted sources")
    source_subparser = source_parser.add_subparsers(
        dest="command", title="commands", required=True
    )
    src_update_parser = source_subparser.add_parser(
        "update",
        help="create & save a white list of accepted input sources for articles"
    )
    src_update_parser.add_argument(
        "sources_path", metavar="SOURCES_FILE",
        default=SOURCES_PATH, nargs="?",
        help=(f"CSV file containing a table of enabled and labeled sources "
              f"({SOURCES_PATH})")
    )
    src_update_parser.set_defaults(function=update_sources)

    # Token generation (by e-mail) and check.
    token_parser = subparser.add_parser("token", help="compute token")
    token_parser.add_argument(
        "mail", metavar="E-MAIL",
        help="e-mail address for which you want to provide access"
    )
    token_parser.set_defaults(function=compute_token)

    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.root.handlers.clear()
    logging.basicConfig(
        format="%(levelname)s - %(name)s - %(asctime)s - %(message)s",
        filename=truestory.LOGFILE,
        level=level
    )

    try:
        args.function(args)
    except Exception as exc:
        logging.exception(exc)
    else:
        logging.info("Operation completed successfully.")
