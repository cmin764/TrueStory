"""Common utilities and procedures used by any crawling technique."""


import urllib.parse as urlparse

from bs4 import BeautifulSoup


def strip_article_link(link, site=None):
    """Returns an article link without the query."""
    parsed = urlparse.urlsplit(link)
    netloc = parsed.netloc
    if site and site not in link:
        netloc = site
    parts = [parsed.scheme, netloc, parsed.path, None, None]
    return urlparse.urlunsplit(parts)


def strip_html(html):
    """Returns the text only out of any potential HTML content."""
    if not html:
        return html

    soup = BeautifulSoup(html, "html5lib")
    return soup.text.strip()
