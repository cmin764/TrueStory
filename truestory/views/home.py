"""Handles the '/home' page."""


from flask import jsonify, render_template, request, url_for

from truestory import app, settings
from truestory.models.article import BiasPairModel
from truestory.views import base as views_base


def _get_serializable_article(key):
    """JSON serializable article format used by the front-end ajax calls."""
    paragraph_split = lambda text: (
        "\n".join(views_base.paragraph_split_filter(text)) if text else ""
    )

    article = key.get()
    details = article.to_dict()
    details.update({
        "usafe": url_for("article_view", article_usafe=article.urlsafe),
        "link": views_base.website_filter(details["link"]),
        "content": paragraph_split(details["content"]),
        "summary": paragraph_split(details["summary"]),
        "authors": views_base.join_authors_filter(details["authors"]),
        "published": views_base.format_date_filter(details["published"], time=True),
    })
    return details


@app.route("/home")
@views_base.require_auth
def home_view():
    """Home page displaying news and available app components."""
    search = request.args.get("querySearch", "").strip().lower()
    cursor = request.args.get("queryCursor")

    query = BiasPairModel.query()
    if search:
        tokens = search.split()
        for token in tokens:
            query.add_filter("keywords", "=", token)
    query.order = ["-score", "-created_at"]
    query_iter = query.fetch(start_cursor=cursor, limit=3)
    page = next(query_iter.pages)
    bias_pairs = list(page)
    next_cursor = (query_iter.next_page_token or b"").decode(settings.ENCODING)

    if cursor:
        pairs = []
        for pair in bias_pairs:
            left_dict, right_dict = map(
                _get_serializable_article, (pair.left, pair.right)
            )
            pairs.append((left_dict, right_dict))
        return jsonify({"bias_pairs": pairs, "new_cursor": next_cursor})

    return render_template(
        "home.html",
        title="Search results" if search else None,
        bias_pairs=bias_pairs,
        query_search=search,
        query_cursor=next_cursor,
    )
