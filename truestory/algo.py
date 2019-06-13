"""Algorithms and API calls for getting the similarity and contradiction between
the articles.
"""


import logging

from truestory.models import PreferencesModel


# NOTE(cmiN): Lazy preferences instance.
prefs = None


def _get_preferences():
    global prefs
    if not prefs:
        prefs = PreferencesModel.instance()
    return prefs


def _get_similarity_score(main, candidate):
    main_kw, candidate_kw = set(main.keywords), set(candidate.keywords)
    min_count, max_count = map(
        lambda func: func(len(main_kw), len(candidate_kw)),
        (min, max)
    )
    miss_weight = 1 / max_count / 2
    match_weight = (1 - miss_weight * (max_count - min_count)) / min_count
    common_count = len(main_kw & candidate_kw)
    score = common_count * match_weight
    return score


def _get_contradiction_score(main, candidate):
    delta = abs(main.side - candidate.side)
    return delta * 0.25


def get_bias_score(main, candidate):
    """Returns a tuple of (status, score) telling if the articles are similar and
    opposed and with what score.
    """
    prefs = _get_preferences()

    contradiction_score = _get_contradiction_score(main, candidate)
    logging.debug(
        "%r vs. %r -> contradiction score: %f",
        main.link, candidate.link, contradiction_score
    )
    if contradiction_score < prefs.contradiction_threshold:
        return False, 0

    similarity_score = _get_similarity_score(main, candidate)
    logging.debug(
        "%r vs. %r -> similarity score: %f",
        main.link, candidate.link, similarity_score
    )
    if similarity_score < prefs.similarity_threshold:
        return False, 0

    return True, (contradiction_score + similarity_score) / 2
