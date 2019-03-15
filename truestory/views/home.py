"""Handles the home page."""


from flask import jsonify, render_template, request

from truestory import app, settings
from truestory.models.article import BiasPairModel
from truestory.views import base as views_base


def _get_serializable_article(key):
    """JSON serializable article format used by the front-end ajax calls."""
    details = key.get().to_dict()
    details["published"] = views_base.format_date_filter(
        details["published"], time=True
    )
    return details


@app.route("/home")
def home():
    """Home page displaying news and available app components."""
    search = request.args.get("querySearch", "").strip().lower()
    cursor = request.args.get("queryCursor")

    query = BiasPairModel.query()
    if search:
        query.add_filter("keywords", "=", search)
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