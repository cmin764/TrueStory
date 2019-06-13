"""API exposing miscellaneous information."""


import operator

from truestory.models import PreferencesModel, RssTargetModel
from truestory.resources import base


# Lazily inited.
prefs = None


class BaseInfoResource(base.BaseResource):

    """Base class for all info related resources."""

    URL_PREFIX = "/info"


class SitesInfoResource(BaseInfoResource):

    """Whitelisted news sites."""

    ENDPOINT = "sites"

    @staticmethod
    def _get_prefs():
        global prefs
        if not prefs:
            prefs = PreferencesModel.instance()
        return prefs

    def get(self):
        """Returns a list of accepted trusted sources (news websites)."""
        enabled_targets = RssTargetModel.all(
            RssTargetModel.query(("enabled", "=", True))
        )
        crawled_sites = {target.site for target in enabled_targets}
        prefs = self._get_prefs()
        head_list, tail_list = [], []

        for site, details in prefs.sites.items():
            site_item = details.copy()
            del site_item["side"]
            site_item["crawled"] = crawled = site in crawled_sites
            if crawled:
                head_list.append(site_item)
            else:
                tail_list.append(site_item)

        site_list = []
        for current_list in (head_list, tail_list):
            current_list.sort(key=operator.itemgetter("agree"), reverse=True)
            for site_item in current_list:
                del site_item["agree"]
            site_list.extend(current_list)

        return {"sites": site_list}
