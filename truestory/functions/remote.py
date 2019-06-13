"""Calls and unpacks remote lambdas responses."""


import datetime
import re
from typing import Sequence

import attr
import cattr
import requests


RE_CLASS_NAME = re.compile(r"[A-Z][a-z\d]*")

cattr.register_structure_hook(
    datetime.datetime, lambda string, _: (
        datetime.datetime.fromisoformat(string) if string else None
    )
)


class BaseAttr:

    FUNCTION_ENDPOINT = None

    @classmethod
    def name(cls):
        camel_name = cls.__name__.replace("Attr", "")
        parts = RE_CLASS_NAME.findall(camel_name)
        for idx, part in enumerate(parts):
            part = part.lower()
            if len(part) > 1:
                part = f"_{part}"
            parts[idx] = part
        return "".join(parts).strip("_")

    @classmethod
    def unpack(cls, data):
        return cattr.structure(data, cls)

    @classmethod
    def get_remote(cls, **params):
        if not cls.FUNCTION_ENDPOINT:
            raise NotImplementedError("missing remote function endpoint")

        response = requests.get(cls.FUNCTION_ENDPOINT, params=params)
        response.raise_for_status()
        data = response.json()[cls.name()]
        return cls.unpack(data)


@attr.s
class NewsArticleAttr(BaseAttr):

    FUNCTION_ENDPOINT = (
        "https://europe-west1-truestory.cloudfunctions.net/parse_article"
    )

    url: str = attr.ib()
    title: str = attr.ib()
    text: str = attr.ib()
    summary: str = attr.ib()
    authors: Sequence[str] = attr.ib()
    publish_date: datetime.datetime = attr.ib()
    top_image: str = attr.ib()
    keywords: Sequence[str] = attr.ib()


def get_remote_article(link):
    return NewsArticleAttr.get_remote(link=link)
